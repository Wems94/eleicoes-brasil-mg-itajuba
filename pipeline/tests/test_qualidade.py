import shutil

import duckdb
import pytest

from eleicoes import esquema
from eleicoes.marts import construir_marts
from eleicoes.qualidade import QualidadeReprovada, executar, gate, main
from eleicoes.staging import carregar_particao
from tests.conftest import montar_zips

UFS_FIXTURE = ("MG", "SP")  # os fixtures só têm MG e SP (e ZZ)


@pytest.fixture(scope="module")
def banco_base(tmp_path_factory):
    """Banco válido com 2018/1, 2022/1 e 2022/2 (staging + marts)."""
    base = tmp_path_factory.mktemp("qualidade")
    caminho = base / "eleicoes.duckdb"
    con = duckdb.connect(str(caminho))
    z2022 = montar_zips(2022, base / "raw" / "2022")
    carregar_particao(con, 2018, 1, montar_zips(2018, base / "raw" / "2018"), base / "t")
    carregar_particao(con, 2022, 1, z2022, base / "t")
    carregar_particao(con, 2022, 2, z2022, base / "t")
    construir_marts(con)
    con.close()
    return caminho


@pytest.fixture
def db(banco_base, tmp_path):
    """Cópia do banco válido, para cada teste poder corrompê-la à vontade."""
    caminho = tmp_path / "eleicoes.duckdb"
    shutil.copy(banco_base, caminho)
    con = duckdb.connect(str(caminho))
    yield con
    con.close()


def _rodar(con, ano=2022, turno=1, ufs=UFS_FIXTURE):
    return executar(con, ano, turno, ufs=ufs)


def _falhas(relatorio) -> set[str]:
    return {r.regra.nome for r in relatorio.resultados if r.falhou and r.regra.severidade == "erro"}


@pytest.mark.parametrize(("ano", "turno"), [(2018, 1), (2022, 1), (2022, 2)])
def test_banco_valido_passa_em_todas_as_regras(db, ano, turno):
    rel = _rodar(db, ano, turno)
    assert rel.ok, rel.texto()
    assert _falhas(rel) == set()


def test_soma_por_secao_diferente_do_comparecimento(db):
    db.execute(
        """UPDATE staging.votacao_secao SET qt_votos = qt_votos + 1
           WHERE (ano, turno, nr_secao, cd_cargo, nr_votavel) = (2022, 1, 18, 3, 95)"""
    )
    rel = _rodar(db)
    assert _falhas(rel) == {"soma_secao_itajuba"}
    (res,) = [r for r in rel.resultados if r.regra.nome == "soma_secao_itajuba"]
    assert res.violacoes == 1
    assert res.exemplos[0]["nr_secao"] == 18
    assert res.exemplos[0]["votos"] == res.exemplos[0]["esperado"] + 1


def test_senado_com_duas_vagas_espera_o_dobro_do_comparecimento(db):
    # 2018 tem 2 vagas: os fixtures somam 2 × comparecimento e passam. Se o
    # pipeline "esquecesse" as vagas (1 voto por eleitor), a regra tem de falhar.
    assert _rodar(db, 2018, 1).ok
    db.execute("UPDATE marts.cargos SET votos_por_eleitor = 1 WHERE ano = 2018 AND cd_cargo = 5")
    rel = _rodar(db, 2018, 1)
    assert "soma_secao_itajuba" in _falhas(rel)
    assert "soma_munzona" in _falhas(rel)


def test_soma_por_municipio_zona(db):
    db.execute(
        """UPDATE staging.detalhe_munzona SET qt_votos_brancos = qt_votos_brancos + 3
           WHERE ano = 2022 AND turno = 1 AND sg_uf = 'SP' AND cd_cargo = 6"""
    )
    assert _falhas(_rodar(db)) == {"soma_munzona"}


@pytest.mark.parametrize("tabela", [t.nome for t in esquema.TABELAS])
def test_unicidade_das_chaves(db, tabela):
    db.execute(f"INSERT INTO staging.{tabela} SELECT * FROM staging.{tabela} LIMIT 1")
    assert f"unicidade_{tabela}" in _falhas(_rodar(db))


def test_mesmo_municipio_e_zona_em_dois_arquivos(db):
    """Cenário da spec: o _BRASIL (ou outro arquivo) duplicaria município/zona."""
    db.execute(
        """INSERT INTO staging.votacao_munzona
           SELECT * FROM staging.votacao_munzona WHERE ano = 2022 AND turno = 1 AND sg_uf = 'SP'"""
    )
    rel = _rodar(db)
    assert "unicidade_votacao_munzona" in _falhas(rel)


def test_cargo_fora_do_dominio(db):
    db.execute(
        "UPDATE staging.detalhe_secao SET cd_cargo = 99 WHERE nr_secao = 18 AND cd_cargo = 7"
    )
    assert "dominio_cargo" in _falhas(_rodar(db))


def test_votos_negativos(db):
    db.execute(
        "UPDATE staging.votacao_munzona SET qt_votos_nominais = -5 WHERE sq_candidato = "
        "(SELECT min(sq_candidato) FROM staging.votacao_munzona)"
    )
    assert "votos_nao_negativos" in _falhas(_rodar(db))


def test_votavel_nominal_sem_candidato(db):
    db.execute(
        """INSERT INTO staging.votacao_secao
           SELECT * REPLACE (9999 AS nr_votavel, 999999999999 AS sq_candidato, 0 AS qt_votos)
           FROM staging.votacao_secao WHERE ano = 2022 AND turno = 1 LIMIT 1"""
    )
    assert _falhas(_rodar(db)) == {"referencial_votavel"}


def test_candidato_fora_da_totalizacao_e_so_aviso(db):
    """Caso real de 2026 (nº 28, candidatura não apta): existe no consulta_cand,
    mas não no munzona. O mart conta como nulo; o gate só avisa."""
    db.execute(
        """INSERT INTO staging.candidatos
           SELECT * REPLACE (28 AS nr_candidato, 280001699999 AS sq_candidato)
           FROM staging.candidatos WHERE ano = 2022 AND turno = 1 AND cd_cargo = 1 LIMIT 1"""
    )
    db.execute(
        """INSERT INTO staging.votacao_secao
           SELECT * REPLACE (28 AS nr_votavel, 280001699999 AS sq_candidato, 0 AS qt_votos)
           FROM staging.votacao_secao WHERE ano = 2022 AND turno = 1 AND cd_cargo = 1 LIMIT 1"""
    )
    rel = _rodar(db)
    assert rel.ok
    (aviso,) = [r for r in rel.resultados if r.regra.nome == "votavel_fora_da_totalizacao"]
    assert aviso.regra.severidade == "aviso"
    assert aviso.violacoes == 1
    assert "[AVISO]" in rel.texto()


def test_uf_ausente_no_primeiro_turno(db):
    rel = _rodar(db, ufs=("MG", "SP", "RJ"))
    assert _falhas(rel) == {"completude_ufs"}
    (res,) = [r for r in rel.resultados if r.regra.nome == "completude_ufs"]
    assert [e["sg_uf"] for e in res.exemplos] == ["RJ"]


def test_segundo_turno_nao_exige_todas_as_ufs(db):
    # no 2º turno dos fixtures só há Presidente (MG/SP/ZZ) e Governador de SP
    assert _rodar(db, 2022, 2, ufs=("MG", "SP", "RJ")).ok


def test_itajuba_ausente(db):
    db.execute("DELETE FROM staging.votacao_secao WHERE ano = 2022 AND turno = 1")
    assert "completude_itajuba" in _falhas(_rodar(db))


def test_presidente_ausente_em_itajuba(db):
    """Se o fallback do arquivo _BR falhar, Itajubá ficaria sem Presidente."""
    db.execute("DELETE FROM staging.votacao_secao WHERE ano = 2022 AND turno = 1 AND cd_cargo = 1")
    db.execute("DELETE FROM staging.detalhe_secao WHERE ano = 2022 AND turno = 1 AND cd_cargo = 1")
    rel = _rodar(db)
    assert _falhas(rel) == {"completude_itajuba"}
    (res,) = [r for r in rel.resultados if r.regra.nome == "completude_itajuba"]
    assert {(e["tabela"], e["cd_cargo"]) for e in res.exemplos} == {
        ("votacao_secao", 1),
        ("detalhe_secao", 1),
    }


def test_percentuais_dos_majoritarios(db):
    db.execute(
        """UPDATE marts.resultado_uf SET pct_validos = pct_validos + 1
           WHERE ano = 2022 AND turno = 1 AND sg_uf = 'MG' AND cd_cargo = 3 AND posicao = 1"""
    )
    assert _falhas(_rodar(db)) == {"percentuais_validos"}


def test_relatorio_lista_regra_e_exemplos(db):
    db.execute("UPDATE staging.votacao_munzona SET qt_votos_nominais = -1 WHERE nr_candidato = 30")
    texto = _rodar(db).texto()
    assert "[ERRO] votos_nao_negativos" in texto
    assert "qt_votos_nominais" in texto
    assert "[OK] soma_secao_itajuba" in texto


def test_gate_interrompe_com_excecao(db):
    db.execute("UPDATE staging.detalhe_secao SET qt_comparecimento = 0 WHERE nr_secao = 18")
    with pytest.raises(QualidadeReprovada) as exc:
        gate(db, 2022, 1, ufs=UFS_FIXTURE)
    assert "soma_secao_itajuba" in str(exc.value)
    assert not exc.value.relatorio.ok


def test_gate_aprovado_devolve_o_relatorio(db):
    assert gate(db, 2022, 1, ufs=UFS_FIXTURE).ok


def test_cli_codigo_de_saida(banco_base, tmp_path, capsys):
    args = ["--db", str(banco_base), "--ano", "2022", "--turno", "1", "--ufs", "MG", "SP"]
    assert main(args) == 0
    assert main([*args[:-2], "MG", "SP", "RJ"]) == 1
    assert "completude_ufs" in capsys.readouterr().out


def test_soma_munzona_considera_votos_anulados_apurados_em_separado(db):
    db.execute(
        """UPDATE staging.detalhe_munzona
           SET qt_votos_validos = qt_votos_validos - 9, qt_votos_anulados_apu_sep = 9
           WHERE ano = 2022 AND turno = 1 AND sg_uf = 'SP' AND cd_cargo = 3"""
    )
    assert _rodar(db).ok
