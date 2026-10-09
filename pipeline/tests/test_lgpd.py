import json
import shutil

import duckdb
import pytest

from eleicoes.lgpd import cpf_valido, main, mascarar, verificar_banco, verificar_snapshots
from eleicoes.marts import construir_marts
from eleicoes.staging import carregar_particao
from tests.conftest import TSE, montar_zips

CPF_VALIDO = "52998224725"  # exemplo clássico de CPF com dígitos verificadores válidos
CPF_DV_ERRADO = "52998224726"


@pytest.fixture(scope="module")
def banco_base(tmp_path_factory):
    base = tmp_path_factory.mktemp("lgpd")
    caminho = base / "eleicoes.duckdb"
    con = duckdb.connect(str(caminho))
    carregar_particao(con, 2022, 1, montar_zips(2022, base / "raw"), base / "t")
    construir_marts(con)
    con.close()
    return caminho


@pytest.fixture
def db(banco_base, tmp_path):
    caminho = tmp_path / "eleicoes.duckdb"
    shutil.copy(banco_base, caminho)
    con = duckdb.connect(str(caminho))
    yield con
    con.close()


def _tipos(vazamentos) -> set[tuple[str, str]]:
    return {(v.local, v.tipo) for v in vazamentos}


# --- CPF -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (CPF_VALIDO, True),
        ("529.982.247-25", True),
        (CPF_DV_ERRADO, False),
        ("11111111111", False),  # dígitos repetidos são inválidos
        ("1234567890", False),
    ],
)
def test_cpf_valido(valor, esperado):
    assert cpf_valido(valor) is esperado


def test_mascara_nao_expoe_o_cpf():
    m = mascarar("cpf", CPF_VALIDO)
    assert CPF_VALIDO not in m
    assert m == "529.***.***-25"
    assert mascarar("email", "fulano.silva@exemplo.com.br") == "f***@exemplo.com.br"


# --- banco -----------------------------------------------------------------------


def test_banco_do_pipeline_esta_limpo(db):
    """Os fixtures de consulta_cand têm CPF, e-mail, nascimento e título válidos;
    nada disso pode chegar ao staging nem aos marts."""
    fonte = (TSE / "2022" / "consulta_cand_2022_MG.csv").read_text(encoding="latin-1")
    assert "@exemplo.com.br" in fonte and "NR_CPF_CANDIDATO" in fonte
    assert verificar_banco(db) == []


def test_coluna_proibida_adicionada_a_um_mart(db):
    db.execute("ALTER TABLE marts.resultado_uf ADD COLUMN ds_email VARCHAR")
    assert _tipos(verificar_banco(db)) == {("marts.resultado_uf.ds_email", "coluna proibida")}


@pytest.mark.parametrize(
    "coluna", ["nr_cpf_candidato", "cpf", "email", "dt_nascimento", "nr_titulo_eleitoral_candidato"]
)
def test_nomes_de_coluna_proibidos(db, coluna):
    db.execute(f"ALTER TABLE staging.candidatos ADD COLUMN {coluna} VARCHAR")
    assert (f"staging.candidatos.{coluna}", "coluna proibida") in _tipos(verificar_banco(db))


def test_cpf_dentro_de_um_texto(db):
    db.execute(
        f"""UPDATE staging.candidatos SET nm_candidato = 'FULANO {CPF_VALIDO[:3]}.'
            || '{CPF_VALIDO[3:6]}.{CPF_VALIDO[6:9]}-{CPF_VALIDO[9:]}'
            WHERE nr_candidato = 30"""
    )
    vaz = verificar_banco(db)
    assert _tipos(vaz) == {("staging.candidatos.nm_candidato", "cpf")}
    assert CPF_VALIDO not in str(vaz)  # o relatório não pode repetir o dado pessoal


def test_cpf_em_coluna_numerica(db):
    db.execute(
        f"ALTER TABLE marts.resultado_brasil ADD COLUMN documento BIGINT DEFAULT {CPF_VALIDO}"
    )
    assert ("marts.resultado_brasil.documento", "cpf") in _tipos(verificar_banco(db))


def test_onze_digitos_com_dv_invalido_nao_e_cpf(db):
    db.execute(f"UPDATE staging.candidatos SET nm_candidato = '{CPF_DV_ERRADO}'")
    assert verificar_banco(db) == []


def test_email_em_um_valor(db):
    db.execute(
        "UPDATE marts.itajuba_local SET ds_endereco = 'contato: escola@exemplo.org' "
        "WHERE nr_local_votacao = 1155"
    )
    assert _tipos(verificar_banco(db)) == {("marts.itajuba_local.ds_endereco", "email")}


# --- snapshots ---------------------------------------------------------------------


def _json(path, dados):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")


def test_snapshots_limpos(tmp_path):
    _json(tmp_path / "2022" / "1" / "brasil.json", {"candidatos": [{"nome": "LULA", "votos": 10}]})
    assert verificar_snapshots(tmp_path) == []


def test_snapshot_com_chave_proibida(tmp_path):
    _json(tmp_path / "uf" / "mg.json", {"candidatos": [{"nome": "X", "nr_cpf_candidato": None}]})
    assert _tipos(verificar_snapshots(tmp_path)) == {
        ("uf/mg.json:$.candidatos[0].nr_cpf_candidato", "coluna proibida")
    }


def test_snapshot_com_valores_pessoais(tmp_path):
    _json(
        tmp_path / "itajuba.json",
        {"locais": [{"contato": "diretoria@escola.mg.gov.br"}], "x": [int(CPF_VALIDO)]},
    )
    assert _tipos(verificar_snapshots(tmp_path)) == {
        ("itajuba.json:$.locais[0].contato", "email"),
        ("itajuba.json:$.x[0]", "cpf"),
    }


def test_diretorio_de_snapshots_inexistente_nao_e_vazamento(tmp_path):
    assert verificar_snapshots(tmp_path / "nao_existe") == []


# --- CLI ---------------------------------------------------------------------------


def test_cli(banco_base, tmp_path, capsys):
    _json(tmp_path / "ok.json", {"a": 1})
    assert main(["--db", str(banco_base), "--snapshots", str(tmp_path)]) == 0

    _json(tmp_path / "vazou.json", {"cpf": CPF_VALIDO})
    assert main(["--db", str(banco_base), "--snapshots", str(tmp_path)]) == 1
    saida = capsys.readouterr().out
    assert "vazou.json" in saida
    assert CPF_VALIDO not in saida


def test_cli_so_snapshots(tmp_path):
    """No CI (7.1) o verificador roda só sobre web/data, sem banco."""
    _json(tmp_path / "ok.json", {"a": 1})
    assert main(["--snapshots", str(tmp_path)]) == 0


def test_totais_eleitorais_nao_sao_confundidos_com_cpf(db):
    """~1% dos números de 9 dígitos passa no DV por acaso; totais nacionais têm 9."""
    falsos = [n for n in range(155_000_000, 155_002_000) if cpf_valido(f"{n:011d}")]
    assert falsos  # existem totais plausíveis que "parecem" CPF
    db.execute(f"UPDATE marts.resultado_brasil SET votos_validos = {falsos[0]}")
    assert verificar_banco(db) == []
