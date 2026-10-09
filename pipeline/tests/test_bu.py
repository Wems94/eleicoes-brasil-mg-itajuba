from pathlib import Path

import pytest

from eleicoes.bu import VOTOS_POR_ELEITOR, BoletimUrna, decodificar, ler

FIXTURES_BU = Path(__file__).parent / "fixtures" / "bu"


# --- encoder BER mínimo, só para montar o fixture sintético -----------------


def _tlv(tag: int, conteudo: bytes) -> bytes:
    n = len(conteudo)
    if n < 0x80:
        tam = bytes([n])
    else:
        b = n.to_bytes((n.bit_length() + 7) // 8, "big")
        tam = bytes([0x80 | len(b)]) + b
    return bytes([tag]) + tam + conteudo


def _int(tag_n: int, v: int) -> bytes:
    return _tlv(0x80 | tag_n, v.to_bytes((v.bit_length() + 8) // 8 or 1, "big", signed=True))


def _seq(tag_n: int, *itens: bytes) -> bytes:
    return _tlv(0xA0 | tag_n, b"".join(itens))


def _useq(*itens: bytes) -> bytes:  # SEQUENCE universal
    return _tlv(0x30, b"".join(itens))


def _voto(tipo: int, qtd: int, partido: int | None = None, numero: int | None = None) -> bytes:
    campos = [_int(1, tipo), _int(2, qtd)]
    if numero is not None:
        campos.append(_seq(3, _int(0, partido), _int(1, numero)))
    return _useq(*campos)


def _cargo(codigo: int, ordem: int, votos: list[bytes]) -> bytes:
    return _useq(_int(0, codigo), _int(1, ordem), _seq(2, *votos))


def _bu_sintetico(comparecimento: int = 250) -> bytes:
    presidente = _cargo(
        1,
        1,
        [
            _voto(1, 120, 13, 13),
            _voto(1, 100, 22, 22),
            _voto(1, 10, 15, 15),
            _voto(2, 8),
            _voto(3, 12),
        ],
    )
    governador = _cargo(3, 2, [_voto(1, 200, 30, 30), _voto(2, 20), _voto(3, 30)])
    dep_federal = _cargo(
        6,
        3,
        [
            _voto(1, 150, 13, 1313),
            _voto(4, 60, 22, 22),
            _voto(2, 15),
            _voto(3, comparecimento - 225),
        ],
    )
    resultados_votacao = [
        _useq(_int(0, 1), _int(1, comparecimento), _seq(2, presidente)),  # majoritário federal
        _useq(_int(0, 1), _int(1, comparecimento), _seq(2, governador)),  # majoritário estadual
        _useq(_int(0, 2), _int(1, comparecimento), _seq(2, dep_federal)),  # proporcional
    ]
    eleicao = _useq(
        _int(0, 544), _int(1, 300), _int(2, 0), _int(3, 0), _seq(4, *resultados_votacao)
    )
    identificacao = _seq(3, _seq(0, _int(0, 46477), _int(1, 134)), _int(1, 1155), _int(2, 18))
    campos = [
        _seq(0),  # cabecalho
        _int(1, 2),  # fase
        _seq(2),  # urna
        identificacao,
        _int(4, 0),  # dataHoraEmissao
        _int(5, 0),
        _int(6, 0),
        _int(7, 0),
        _seq(8, eleicao),
    ]
    bu = _useq(*campos)
    envelope = _useq(_seq(0), _int(1, 0), _int(2, 0), _int(3, 0), _tlv(0x84, bu))
    return envelope


# --- testes ------------------------------------------------------------------


@pytest.fixture
def bu() -> BoletimUrna:
    return decodificar(_bu_sintetico())


def test_identificacao_da_secao(bu):
    assert (bu.municipio, bu.zona, bu.local, bu.secao) == (46477, 134, 1155, 18)


def test_comparecimento_e_aptos(bu):
    (eleicao,) = bu.eleicoes
    assert eleicao.id_eleicao == 544
    assert eleicao.aptos == 300
    assert {c.comparecimento for c in eleicao.cargos} == {250}


def test_votos_por_cargo_e_votavel(bu):
    presidente = bu.cargo(1)
    assert presidente.nome == "Presidente"
    assert presidente.total == 250
    nominais = {v.numero: v.quantidade for v in presidente.votos if v.tipo == "nominal"}
    assert nominais == {13: 120, 22: 100, 15: 10}
    assert {v.tipo for v in presidente.votos} == {"nominal", "branco", "nulo"}


def test_soma_dos_cargos_de_vaga_unica_igual_ao_comparecimento(bu):
    for cargo in bu.cargos():
        assert VOTOS_POR_ELEITOR[cargo.codigo] == 1
        assert cargo.total == cargo.comparecimento, cargo.nome
    assert bu.divergencias() == []


def test_divergencia_e_reportada():
    bu = decodificar(_bu_sintetico(comparecimento=260))
    # dep. federal fecha com qualquer comparecimento; presidente/governador ficam 10 abaixo
    assert {d.cargo for d in bu.divergencias()} == {"Presidente", "Governador"}


def test_votos_em_dataframe_polars(bu):
    df = bu.votos_df()
    assert df.columns == [
        "municipio",
        "zona",
        "secao",
        "id_eleicao",
        "cd_cargo",
        "nm_cargo",
        "tipo_voto",
        "nr_partido",
        "nr_votavel",
        "qt_votos",
    ]
    assert df.filter(df["cd_cargo"] == 6)["qt_votos"].sum() == 250


@pytest.mark.parametrize(
    "arquivo",
    sorted(FIXTURES_BU.glob("*.bu")) + sorted(FIXTURES_BU.glob("*.dat")) or [None],
    ids=lambda p: p.name if p else "sem-bu-real",
)
def test_bu_real(arquivo):
    if arquivo is None:
        pytest.skip("coloque BUs reais (.bu/.dat) em tests/fixtures/bu/ para validar")
    bu = ler(arquivo)
    assert bu.cargos()
    assert bu.divergencias() == []
