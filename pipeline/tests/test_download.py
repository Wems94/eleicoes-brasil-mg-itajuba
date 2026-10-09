import hashlib
import json
import logging

import pytest

from eleicoes.download import FonteIndisponivel, Manifest, baixar, baixar_todas
from eleicoes.fontes import Fonte
from tests.servidor_http import servidor_http

CORPO = b"PK" + bytes(range(256)) * 400  # ~100 KB


@pytest.fixture
def srv():
    with servidor_http() as estado:
        yield estado


def _fonte(srv, caminho="votacao/arquivo_2022.zip", obrigatoria=True, nome="votacao") -> Fonte:
    return Fonte(
        nome=nome,
        ano=2022,
        descricao="",
        url=srv.base_url + caminho,
        membros=("*.csv",),
        excluir=(),
        obrigatoria=obrigatoria,
    )


def _sem_espera(_segundos: float) -> None:
    pass


def test_baixa_e_registra_no_manifest(srv, tmp_path):
    srv.arquivos["votacao/arquivo_2022.zip"] = CORPO
    fonte = _fonte(srv)

    res = baixar(fonte, tmp_path, sleep=_sem_espera)

    assert res.baixado
    assert res.caminho == tmp_path / "arquivo_2022.zip"
    assert res.caminho.read_bytes() == CORPO
    entrada = json.loads((tmp_path / "manifest.json").read_text())[fonte.url]
    assert entrada["sha256"] == hashlib.sha256(CORPO).hexdigest()
    assert entrada["tamanho"] == len(CORPO)
    assert entrada["arquivo"] == "arquivo_2022.zip"
    assert entrada["baixado_em"]
    assert not list(tmp_path.glob("*.part"))


def test_reexecucao_reutiliza_arquivo_integro(srv, tmp_path):
    srv.arquivos["votacao/arquivo_2022.zip"] = CORPO
    fonte = _fonte(srv)

    baixar(fonte, tmp_path, sleep=_sem_espera)
    segunda = baixar(fonte, tmp_path, sleep=_sem_espera)

    assert not segunda.baixado
    assert segunda.sha256 == hashlib.sha256(CORPO).hexdigest()
    assert srv.requisicoes["votacao/arquivo_2022.zip"] == 1


def test_arquivo_local_corrompido_e_baixado_de_novo(srv, tmp_path):
    srv.arquivos["votacao/arquivo_2022.zip"] = CORPO
    fonte = _fonte(srv)
    res = baixar(fonte, tmp_path, sleep=_sem_espera)
    res.caminho.write_bytes(b"lixo")

    novo = baixar(fonte, tmp_path, sleep=_sem_espera)

    assert novo.baixado
    assert novo.caminho.read_bytes() == CORPO
    assert srv.requisicoes["votacao/arquivo_2022.zip"] == 2


def test_forcar_baixa_novamente_e_atualiza_manifest(srv, tmp_path):
    srv.arquivos["votacao/arquivo_2022.zip"] = CORPO
    fonte = _fonte(srv)
    baixar(fonte, tmp_path, sleep=_sem_espera)
    srv.arquivos["votacao/arquivo_2022.zip"] = CORPO + b"atualizado"

    res = baixar(fonte, tmp_path, forcar=True, sleep=_sem_espera)

    assert res.baixado
    manifest = Manifest(tmp_path / "manifest.json")
    assert manifest.get(fonte.url)["sha256"] == hashlib.sha256(CORPO + b"atualizado").hexdigest()


def test_download_interrompido_e_retentado_com_backoff(srv, tmp_path):
    srv.arquivos["votacao/arquivo_2022.zip"] = CORPO
    srv.cortes["votacao/arquivo_2022.zip"] = 2
    esperas: list[float] = []

    res = baixar(_fonte(srv), tmp_path, tentativas=4, backoff=0.5, sleep=esperas.append)

    assert res.caminho.read_bytes() == CORPO
    assert srv.requisicoes["votacao/arquivo_2022.zip"] == 3
    assert esperas == [0.5, 1.0]
    assert not list(tmp_path.glob("*.part"))


def test_falha_persistente_nao_deixa_arquivo_parcial_valido(srv, tmp_path):
    srv.arquivos["votacao/arquivo_2022.zip"] = CORPO
    srv.cortes["votacao/arquivo_2022.zip"] = 99
    fonte = _fonte(srv)

    with pytest.raises(FonteIndisponivel, match="arquivo_2022.zip"):
        baixar(fonte, tmp_path, tentativas=3, sleep=_sem_espera)

    assert srv.requisicoes["votacao/arquivo_2022.zip"] == 3
    assert not (tmp_path / "arquivo_2022.zip").exists()
    assert not list(tmp_path.glob("*.part"))
    assert Manifest(tmp_path / "manifest.json").get(fonte.url) is None


def test_erro_5xx_e_retentado(srv, tmp_path):
    srv.arquivos["votacao/arquivo_2022.zip"] = CORPO
    srv.indisponivel["votacao/arquivo_2022.zip"] = 1

    res = baixar(_fonte(srv), tmp_path, sleep=_sem_espera)

    assert res.baixado
    assert srv.requisicoes["votacao/arquivo_2022.zip"] == 2


def test_404_em_arquivo_obrigatorio_falha_com_a_url(srv, tmp_path):
    fonte = _fonte(srv, caminho="votacao/nao_existe.zip")

    with pytest.raises(FonteIndisponivel) as exc:
        baixar(fonte, tmp_path, sleep=_sem_espera)

    assert fonte.url in str(exc.value)
    assert srv.requisicoes["votacao/nao_existe.zip"] == 1  # 404 não é retentado


def test_404_em_arquivo_opcional_avisa_e_segue(srv, tmp_path, caplog):
    fonte = _fonte(srv, caminho="locais/nao_existe.zip", obrigatoria=False, nome="locais")

    with caplog.at_level(logging.WARNING):
        res = baixar(fonte, tmp_path, sleep=_sem_espera)

    assert res.caminho is None
    assert not res.baixado
    assert "locais" in caplog.text
    assert fonte.url in caplog.text


def test_baixar_todas_para_no_primeiro_obrigatorio_ausente(srv, tmp_path):
    srv.arquivos["a/ok_2022.zip"] = CORPO
    fontes = [
        _fonte(srv, caminho="a/ok_2022.zip", nome="ok"),
        _fonte(srv, caminho="b/falta_2022.zip", nome="falta"),
    ]

    with pytest.raises(FonteIndisponivel, match="falta_2022.zip"):
        baixar_todas(fontes, tmp_path, sleep=_sem_espera)


def test_baixar_todas_devolve_resultado_por_fonte(srv, tmp_path):
    srv.arquivos["a/ok_2022.zip"] = CORPO
    fontes = [
        _fonte(srv, caminho="a/ok_2022.zip", nome="ok"),
        _fonte(srv, caminho="b/opcional_2022.zip", nome="opcional", obrigatoria=False),
    ]

    res = baixar_todas(fontes, tmp_path, sleep=_sem_espera)

    assert res["ok"].caminho == tmp_path / "ok_2022.zip"
    assert res["opcional"].caminho is None
