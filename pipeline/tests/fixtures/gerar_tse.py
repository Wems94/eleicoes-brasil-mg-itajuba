"""Gera os fixtures CSV do TSE em `tests/fixtures/tse/<ano>/`.

Uso: uv run python tests/fixtures/gerar_tse.py

Os cabeçalhos são os dos arquivos reais (conferidos em out/2026); os dados são
fictícios (candidatos inventados), pequenos e coerentes em todos os níveis:
a votação por seção é gerada primeiro e agregada para município/zona, de modo
que soma dos votos = comparecimento × votos por eleitor vale em toda parte.
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

SAIDA = Path(__file__).parent / "tse"

# --- cabeçalhos reais -----------------------------------------------------

_PREFIXO = [
    "DT_GERACAO",
    "HH_GERACAO",
    "ANO_ELEICAO",
    "CD_TIPO_ELEICAO",
    "NM_TIPO_ELEICAO",
    "NR_TURNO",
    "CD_ELEICAO",
    "DS_ELEICAO",
    "DT_ELEICAO",
    "TP_ABRANGENCIA",
    "SG_UF",
    "SG_UE",
    "NM_UE",
]


def _munzona(diploma: str) -> list[str]:
    return _PREFIXO + (
        "CD_MUNICIPIO;NM_MUNICIPIO;NR_ZONA;CD_CARGO;DS_CARGO;SQ_CANDIDATO;NR_CANDIDATO;"
        "NM_CANDIDATO;NM_URNA_CANDIDATO;NM_SOCIAL_CANDIDATO;CD_SITUACAO_CANDIDATURA;"
        "DS_SITUACAO_CANDIDATURA;CD_DETALHE_SITUACAO_CAND;DS_DETALHE_SITUACAO_CAND;"
        "CD_SITUACAO_JULGAMENTO;DS_SITUACAO_JULGAMENTO;CD_SITUACAO_CASSACAO;"
        f"DS_SITUACAO_CASSACAO;CD_SITUACAO_{diploma};DS_SITUACAO_{diploma};TP_AGREMIACAO;"
        "NR_PARTIDO;SG_PARTIDO;NM_PARTIDO;NR_FEDERACAO;NM_FEDERACAO;SG_FEDERACAO;"
        "DS_COMPOSICAO_FEDERACAO;SQ_COLIGACAO;NM_COLIGACAO;DS_COMPOSICAO_COLIGACAO;"
        "ST_VOTO_EM_TRANSITO;QT_VOTOS_NOMINAIS;NM_TIPO_DESTINACAO_VOTOS;"
        "QT_VOTOS_NOMINAIS_VALIDOS;CD_SIT_TOT_TURNO;DS_SIT_TOT_TURNO"
    ).split(";")


H_MUNZONA = {2018: _munzona("DIPLOMA"), 2022: _munzona("DCONST_DIPLOMA")}
H_DETALHE_MUNZONA = _PREFIXO + [
    "CD_MUNICIPIO",
    "NM_MUNICIPIO",
    "NR_ZONA",
    "CD_CARGO",
    "DS_CARGO",
    "QT_APTOS",
    "QT_SECOES_PRINCIPAIS",
    "QT_SECOES_AGREGADAS",
    "QT_SECOES_NAO_INSTALADAS",
    "QT_TOTAL_SECOES",
    "QT_COMPARECIMENTO",
    "QT_ELEITORES_SECOES_NAO_INSTALADAS",
    "QT_ABSTENCOES",
    "ST_VOTO_EM_TRANSITO",
    "QT_VOTOS",
    "QT_VOTOS_CONCORRENTES",
    "QT_TOTAL_VOTOS_VALIDOS",
    "QT_VOTOS_NOMINAIS_VALIDOS",
    "QT_TOTAL_VOTOS_LEG_VALIDOS",
    "QT_VOTOS_LEG_VALIDOS",
    "QT_VOTOS_NOM_CONVR_LEG_VALIDOS",
    "QT_TOTAL_VOTOS_ANULADOS",
    "QT_VOTOS_NOMINAIS_ANULADOS",
    "QT_VOTOS_LEGENDA_ANULADOS",
    "QT_TOTAL_VOTOS_ANUL_SUBJUD",
    "QT_VOTOS_NOMINAIS_ANUL_SUBJUD",
    "QT_VOTOS_LEGENDA_ANUL_SUBJUD",
    "QT_VOTOS_BRANCOS",
    "QT_TOTAL_VOTOS_NULOS",
    "QT_VOTOS_NULOS",
    "QT_VOTOS_NULOS_TECNICOS",
    "QT_VOTOS_ANULADOS_APU_SEP",
    "HH_ULTIMA_TOTALIZACAO",
    "DT_ULTIMA_TOTALIZACAO",
]
H_VOTACAO_SECAO = _PREFIXO + [
    "CD_MUNICIPIO",
    "NM_MUNICIPIO",
    "NR_ZONA",
    "NR_SECAO",
    "CD_CARGO",
    "DS_CARGO",
    "NR_VOTAVEL",
    "NM_VOTAVEL",
    "QT_VOTOS",
    "NR_LOCAL_VOTACAO",
    "SQ_CANDIDATO",
    "NM_LOCAL_VOTACAO",
    "DS_LOCAL_VOTACAO_ENDERECO",
]
H_DETALHE_SECAO = _PREFIXO + [
    "CD_MUNICIPIO",
    "NM_MUNICIPIO",
    "NR_ZONA",
    "NR_SECAO",
    "CD_CARGO",
    "DS_CARGO",
    "QT_APTOS",
    "QT_COMPARECIMENTO",
    "QT_ABSTENCOES",
    "QT_VOTOS_NOMINAIS",
    "QT_VOTOS_BRANCOS",
    "QT_VOTOS_NULOS",
    "QT_VOTOS_LEGENDA",
    "QT_VOTOS_ANULADOS_APU_SEP",
    "NR_LOCAL_VOTACAO",
    "NM_LOCAL_VOTACAO",
    "DS_LOCAL_VOTACAO_ENDERECO",
    "DT_RECEBIMENTO_BU_HOR_TSE",
    "DT_PRIM_TOT_PARCIAL_HOR_TSE",
    "DS_ORIGEM_VOTO",
    "ST_SECAO_INSTALADA",
    "ST_SECAO_ANULADA",
    "CD_MODELO_URNA",
    "DS_MODELO_URNA",
]
H_CONSULTA_CAND = [
    "DT_GERACAO",
    "HH_GERACAO",
    "ANO_ELEICAO",
    "CD_TIPO_ELEICAO",
    "NM_TIPO_ELEICAO",
    "NR_TURNO",
    "CD_ELEICAO",
    "DS_ELEICAO",
    "DT_ELEICAO",
    "TP_ABRANGENCIA",
    "SG_UF",
    "SG_UE",
    "NM_UE",
    "CD_CARGO",
    "DS_CARGO",
    "SQ_CANDIDATO",
    "NR_CANDIDATO",
    "NM_CANDIDATO",
    "NM_URNA_CANDIDATO",
    "NM_SOCIAL_CANDIDATO",
    "NR_CPF_CANDIDATO",
    "DS_EMAIL",
    "CD_SITUACAO_CANDIDATURA",
    "DS_SITUACAO_CANDIDATURA",
    "TP_AGREMIACAO",
    "NR_PARTIDO",
    "SG_PARTIDO",
    "NM_PARTIDO",
    "NR_FEDERACAO",
    "NM_FEDERACAO",
    "SG_FEDERACAO",
    "DS_COMPOSICAO_FEDERACAO",
    "SQ_COLIGACAO",
    "NM_COLIGACAO",
    "DS_COMPOSICAO_COLIGACAO",
    "SG_UF_NASCIMENTO",
    "DT_NASCIMENTO",
    "NR_TITULO_ELEITORAL_CANDIDATO",
    "CD_GENERO",
    "DS_GENERO",
    "CD_GRAU_INSTRUCAO",
    "DS_GRAU_INSTRUCAO",
    "CD_ESTADO_CIVIL",
    "DS_ESTADO_CIVIL",
    "CD_COR_RACA",
    "DS_COR_RACA",
    "CD_OCUPACAO",
    "DS_OCUPACAO",
    "CD_SIT_TOT_TURNO",
    "DS_SIT_TOT_TURNO",
]
H_LOCAIS = [
    "DT_GERACAO",
    "HH_GERACAO",
    "AA_ELEICAO",
    "DT_ELEICAO",
    "DS_ELEICAO",
    "NR_TURNO",
    "SG_UF",
    "CD_MUNICIPIO",
    "NM_MUNICIPIO",
    "NR_ZONA",
    "NR_SECAO",
    "CD_TIPO_SECAO_AGREGADA",
    "DS_TIPO_SECAO_AGREGADA",
    "NR_SECAO_PRINCIPAL",
    "NR_LOCAL_VOTACAO",
    "NM_LOCAL_VOTACAO",
    "CD_TIPO_LOCAL",
    "DS_TIPO_LOCAL",
    "DS_ENDERECO",
    "NM_BAIRRO",
    "NR_CEP",
    "NR_TELEFONE_LOCAL",
    "NR_LATITUDE",
    "NR_LONGITUDE",
    "CD_SITU_LOCAL_VOTACAO",
    "DS_SITU_LOCAL_VOTACAO",
    "CD_SITU_ZONA",
    "DS_SITU_ZONA",
    "CD_SITU_SECAO",
    "DS_SITU_SECAO",
    "CD_SITU_LOCALIDADE",
    "DS_SITU_LOCALIDADE",
    "CD_SITU_SECAO_ACESSIBILIDADE",
    "DS_SITU_SECAO_ACESSIBILIDADE",
    "QT_ELEITOR_SECAO",
    "QT_ELEITOR_ELEICAO_FEDERAL",
    "QT_ELEITOR_ELEICAO_ESTADUAL",
    "QT_ELEITOR_ELEICAO_MUNICIPAL",
    "NR_LOCAL_VOTACAO_ORIGINAL",
    "NM_LOCAL_VOTACAO_ORIGINAL",
    "DS_ENDERECO_LOCVT_ORIGINAL",
]

# --- universo fictício --------------------------------------------------------

UF_NOME = {"MG": "MINAS GERAIS", "SP": "SÃO PAULO"}
CARGO_NOME = {
    1: "Presidente",
    3: "Governador",
    5: "Senador",
    6: "Deputado Federal",
    7: "Deputado Estadual",
}
PROPORCIONAIS = {6, 7}
VAGAS_SENADO = {2018: 2, 2022: 1}
ELEICAO = {  # ano -> turno -> (cd federal, cd estadual, data)
    2018: {1: (295, 297, "07/10/2018"), 2: (296, 298, "28/10/2018")},
    2022: {1: (544, 546, "02/10/2022"), 2: (545, 547, "30/10/2022")},
}
PARTIDOS = {
    13: ("PT", "Partido dos Trabalhadores"),
    22: ("PL", "Partido Liberal"),
    15: ("MDB", "Movimento Democrático Brasileiro"),
    30: ("NOVO", "Partido Novo"),
    45: ("PSDB", "Partido da Social Democracia Brasileira"),
    50: ("PSOL", "Partido Socialismo e Liberdade"),
}
# Em 2022 o PT integra uma federação (para exercitar NR_FEDERACAO).
FEDERACAO_2022 = {13: (1, "Federação Brasil da Esperança", "FE BRASIL", "PT/PC do B/PV")}

SIT = {
    "ELEITO": 1,
    "ELEITO POR QP": 2,
    "ELEITO POR MÉDIA": 3,
    "NÃO ELEITO": 4,
    "SUPLENTE": 5,
    "2º TURNO": 6,
}


@dataclass(frozen=True)
class Secao:
    uf: str
    cd_mun: int
    nm_mun: str
    zona: int
    secao: int
    local: int
    nm_local: str
    endereco: str
    bairro: str
    lat: str
    lon: str


SECOES = [
    Secao(
        "MG",
        46477,
        "ITAJUBÁ",
        134,
        18,
        1155,
        "E.E. PROF. RAFAEL MAGALHÃES",
        "RUA DR. PEREIRA CABRAL, 1000",
        "PINHEIRINHO",
        "-22.4267816",
        "-45.461597",
    ),
    Secao(
        "MG",
        46477,
        "ITAJUBÁ",
        134,
        19,
        1155,
        "E.E. PROF. RAFAEL MAGALHÃES",
        "RUA DR. PEREIRA CABRAL, 1000",
        "PINHEIRINHO",
        "-22.4267816",
        "-45.461597",
    ),
    Secao(
        "MG",
        46477,
        "ITAJUBÁ",
        134,
        25,
        1058,
        "COLÉGIO XIX DE MARÇO",
        "AV. CEL. CARNEIRO JÚNIOR, 200",
        "CENTRO",
        "-22.4256",
        "-45.4527",
    ),
    Secao(
        "MG",
        46477,
        "ITAJUBÁ",
        134,
        26,
        1058,
        "COLÉGIO XIX DE MARÇO",
        "AV. CEL. CARNEIRO JÚNIOR, 200",
        "CENTRO",
        "-1",
        "-1",  # sem coordenada
    ),
    Secao(
        "MG",
        41238,
        "BELO HORIZONTE",
        32,
        38,
        1104,
        "ESCOLA ESTADUAL ISABEL DA SILVA POLCK",
        "RUA NELSON LEMOS DE CARVALHO, 198",
        "BARREIRO",
        "-19.97",
        "-44.02",
    ),
    Secao(
        "MG",
        41238,
        "BELO HORIZONTE",
        32,
        39,
        1104,
        "ESCOLA ESTADUAL ISABEL DA SILVA POLCK",
        "RUA NELSON LEMOS DE CARVALHO, 198",
        "BARREIRO",
        "-19.97",
        "-44.02",
    ),
    Secao(
        "SP",
        71072,
        "SÃO PAULO",
        1,
        10,
        1015,
        "EMEF JOÃO DE DEUS",
        "RUA DA CONSOLAÇÃO, 50",
        "CONSOLAÇÃO",
        "-23.55",
        "-46.65",
    ),
    Secao(
        "SP",
        71072,
        "SÃO PAULO",
        1,
        11,
        1015,
        "EMEF JOÃO DE DEUS",
        "RUA DA CONSOLAÇÃO, 50",
        "CONSOLAÇÃO",
        "-23.55",
        "-46.65",
    ),
    Secao(
        "ZZ",
        29530,
        "LISBOA",
        1,
        900,
        1031,
        "CONSULADO-GERAL DO BRASIL EM LISBOA",
        "PRAÇA LUÍS DE CAMÕES, 22",
        "CHIADO",
        "38.71",
        "-9.14",
    ),
]


@dataclass(frozen=True)
class Cand:
    cargo: int
    uf: str  # "BR" para Presidente
    numero: int
    nome: str
    urna: str
    peso: int

    @property
    def partido(self) -> int:
        return int(str(self.numero)[:2])


CANDIDATOS = [
    Cand(1, "BR", 13, "ANTÔNIO CARLOS BRAGA", "ANTÔNIO BRAGA", 45),
    Cand(1, "BR", 22, "JOSÉ AUGUSTO FERREIRA", "JOSÉ AUGUSTO", 43),
    Cand(1, "BR", 15, "LÚCIA HELENA MOTTA", "LÚCIA MOTTA", 12),
    Cand(3, "MG", 30, "JOÃO PAULO SANTANA", "JOÃO SANTANA", 60),
    Cand(3, "MG", 13, "CÉLIA REGINA ARAÚJO", "CÉLIA ARAÚJO", 25),
    Cand(3, "MG", 45, "MARCOS VINÍCIUS LEÃO", "MARCOS LEÃO", 15),
    Cand(3, "SP", 45, "RENATA CONCEIÇÃO DIAS", "RENATA DIAS", 42),
    Cand(3, "SP", 13, "PAULO HENRIQUE GUSMÃO", "PAULO GUSMÃO", 38),
    Cand(3, "SP", 22, "SÉRGIO LUÍS MONTEIRO", "SÉRGIO MONTEIRO", 20),
    Cand(5, "MG", 130, "ANA BEATRIZ FALCÃO", "ANA FALCÃO", 40),
    Cand(5, "MG", 222, "ROBERTO JOSÉ QUEIRÓS", "ROBERTO QUEIRÓS", 35),
    Cand(5, "MG", 455, "TÂNIA MARA LOBATO", "TÂNIA LOBATO", 25),
    Cand(5, "SP", 131, "FÁBIO AUGUSTO PRADO", "FÁBIO PRADO", 38),
    Cand(5, "SP", 221, "MÔNICA SIMÕES REIS", "MÔNICA REIS", 34),
    Cand(5, "SP", 456, "HÉLIO BATISTA CORRÊA", "HÉLIO CORRÊA", 28),
    Cand(6, "MG", 1310, "GERALDO MAGELA SOUZA", "GERALDO MAGELA", 35),
    Cand(6, "MG", 2210, "VÂNIA LÚCIA RIBEIRO", "VÂNIA RIBEIRO", 30),
    Cand(6, "MG", 3010, "OTÁVIO CÉSAR NUNES", "OTÁVIO NUNES", 20),
    Cand(6, "MG", 5010, "LARISSA GONÇALVES", "LARISSA", 15),
    Cand(6, "SP", 1320, "EDUARDO TAVARES", "EDU TAVARES", 33),
    Cand(6, "SP", 2220, "PRISCILA MOURÃO", "PRISCILA MOURÃO", 31),
    Cand(6, "SP", 4520, "WAGNER LIMA ASSUNÇÃO", "WAGNER LIMA", 21),
    Cand(6, "SP", 5020, "JÉSSICA CAMARGO", "JÉSSICA", 15),
    Cand(7, "MG", 13100, "RAIMUNDO NONATO ALVES", "RAIMUNDO NONATO", 34),
    Cand(7, "MG", 22100, "SÔNIA MARIA COELHO", "SÔNIA COELHO", 31),
    Cand(7, "MG", 30100, "DANIEL BRANDÃO", "DANIEL BRANDÃO", 20),
    Cand(7, "MG", 50100, "ÉRICA FONSECA", "ÉRICA", 15),
    Cand(7, "SP", 13200, "MAURÍCIO ESTEVÃO", "MAURÍCIO", 32),
    Cand(7, "SP", 22200, "LETÍCIA BARBOSA", "LETÍCIA", 30),
    Cand(7, "SP", 45200, "CLÁUDIO ROMÃO", "CLÁUDIO ROMÃO", 23),
    Cand(7, "SP", 50200, "NATÁLIA PIRES", "NATÁLIA", 15),
]
SEGUNDO_TURNO = {(1, "BR"): (13, 22), (3, "SP"): (45, 13)}


def _sq(ano: int, c: Cand) -> int:
    prefixo = {"BR": 28, "MG": 13, "SP": 25}[c.uf]
    base = 1600000 if ano == 2022 else 600000
    return int(f"{prefixo}000{base + CANDIDATOS.index(c):07d}")


def _cpf_ficticio(i: int) -> str:
    # 9 dígitos + DV válidos, para o verificador LGPD reconhecer o padrão
    d = [int(x) for x in f"{100000000 + i * 7919:09d}"[:9]]
    for n in (10, 11):
        s = sum(v * (n - k) for k, v in enumerate(d)) % 11
        d.append(0 if s < 2 else 11 - s)
    return "".join(map(str, d))


def _distribuir(total: int, pesos: list[float]) -> list[int]:
    soma = sum(pesos)
    partes = [int(total * p / soma) for p in pesos]
    partes[0] += total - sum(partes)
    return partes


def _cargos_do_turno(turno: int, uf: str) -> list[tuple[int, list[Cand]]]:
    out = []
    for cargo in CARGO_NOME:
        uf_cand = "BR" if cargo == 1 else uf
        if uf == "ZZ" and cargo != 1:
            continue
        cands = [c for c in CANDIDATOS if c.cargo == cargo and c.uf == uf_cand]
        if turno == 2:
            finalistas = SEGUNDO_TURNO.get((cargo, uf_cand))
            if not finalistas:
                continue
            cands = [c for c in cands if c.numero in finalistas]
        out.append((cargo, cands))
    return out


def _votos_por_eleitor(ano: int, cargo: int) -> int:
    return VAGAS_SENADO[ano] if cargo == 5 else 1


# --- simulação ----------------------------------------------------------------


def simular(ano: int):
    """Devolve (comparecimento por seção/turno, votos por seção/turno/cargo/votável)."""
    presenca = {}
    votos = defaultdict(int)  # (turno, secao, cargo, tipo, chave) -> qtd
    for turno in (1, 2):
        for s in SECOES:
            rng = random.Random(f"{ano}-{turno}-{s.cd_mun}-{s.zona}-{s.secao}")
            aptos = rng.randint(250, 400)
            comp = int(aptos * rng.uniform(0.74, 0.84))
            presenca[(turno, s)] = (aptos, comp)
            for cargo, cands in _cargos_do_turno(turno, s.uf):
                total = comp * _votos_por_eleitor(ano, cargo)
                brancos = round(total * rng.uniform(0.02, 0.05))
                nulos = round(total * rng.uniform(0.03, 0.06))
                legenda = round(total * 0.08) if cargo in PROPORCIONAIS else 0
                nominal = total - brancos - nulos - legenda
                pesos = [c.peso * rng.uniform(0.8, 1.2) for c in cands]
                for c, q in zip(cands, _distribuir(nominal, pesos), strict=True):
                    votos[(turno, s, cargo, "nominal", c.numero)] += q
                if legenda:
                    for c, q in zip(cands, _distribuir(legenda, pesos), strict=True):
                        votos[(turno, s, cargo, "legenda", c.partido)] += q
                votos[(turno, s, cargo, "branco", 95)] += brancos
                votos[(turno, s, cargo, "nulo", 96)] += nulos
    return presenca, votos


def _situacoes(ano: int, votos) -> dict[tuple[int, int, str, int], str]:
    """(turno, cargo, uf_cand, numero) -> DS_SIT_TOT_TURNO."""
    totais = defaultdict(int)
    for (turno, s, cargo, tipo, num), q in votos.items():
        if tipo == "nominal":
            totais[(turno, cargo, "BR" if cargo == 1 else s.uf, num)] += q
    grupos = defaultdict(list)
    for (turno, cargo, uf, num), q in totais.items():
        grupos[(turno, cargo, uf)].append((q, num))
    sit = {}
    for (turno, cargo, uf), lista in grupos.items():
        lista.sort(reverse=True)
        validos = sum(q for q, _ in lista)
        for i, (_q, num) in enumerate(lista):
            if cargo in PROPORCIONAIS:
                r = ["ELEITO POR QP", "ELEITO POR MÉDIA"][i] if i < 2 else "SUPLENTE"
            elif cargo == 5:
                r = "ELEITO" if i < VAGAS_SENADO[ano] else "NÃO ELEITO"
            elif turno == 2 or lista[0][0] * 2 > validos:
                r = "ELEITO" if i == 0 else "NÃO ELEITO"
            else:
                r = "2º TURNO" if i < 2 else "NÃO ELEITO"
            sit[(turno, cargo, uf, num)] = r
    return sit


# --- escrita -------------------------------------------------------------------


class Escritor:
    def __init__(self, ano: int) -> None:
        self.ano = ano
        self.nulo = "#NULO#" if ano == 2018 else "#NULO"
        self.arquivos: dict[str, tuple[list[str], list[list]]] = {}

    def linha(self, arquivo: str, header: list[str], valores: dict) -> None:
        _, linhas = self.arquivos.setdefault(arquivo, (header, []))
        linhas.append([valores.get(h, self.nulo) for h in header])

    def prefixo(self, turno: int, uf: str, federal: bool) -> dict:
        cd_fed, cd_est, data = ELEICAO[self.ano][turno]
        return {
            "DT_GERACAO": "09/10/2026",
            "HH_GERACAO": "03:16:47",
            "ANO_ELEICAO": self.ano,
            "CD_TIPO_ELEICAO": 2,
            "NM_TIPO_ELEICAO": "Eleição Ordinária",
            "NR_TURNO": turno,
            "CD_ELEICAO": cd_fed if federal else cd_est,
            "DS_ELEICAO": (
                f"Eleição Geral Federal {self.ano}"
                if federal
                else f"Eleições Gerais Estaduais {self.ano}"
            ),
            "DT_ELEICAO": data,
            "TP_ABRANGENCIA": "F" if federal else "E",
            "SG_UF": uf,
            "SG_UE": "BR" if federal else uf,
            "NM_UE": "BRASIL" if federal else UF_NOME[uf],
        }

    def gravar(self, destino: Path) -> None:
        destino.mkdir(parents=True, exist_ok=True)
        for nome, (header, linhas) in sorted(self.arquivos.items()):
            with (destino / nome).open("w", encoding="latin-1", newline="") as f:
                w = csv.writer(f, delimiter=";", quoting=csv.QUOTE_NONNUMERIC, lineterminator="\n")
                w.writerow(header)
                w.writerows(linhas)


def _membro(ano: int, cargo: int, uf: str) -> str:
    return "BR" if cargo == 1 else uf


def gerar(ano: int, destino: Path) -> None:
    presenca, votos = simular(ano)
    sit = _situacoes(ano, votos)
    e = Escritor(ano)
    cand_por_num = {(c.cargo, c.uf, c.numero): c for c in CANDIDATOS}

    def partido_cols(num_partido: int) -> dict:
        sg, nm = PARTIDOS[num_partido]
        fed = FEDERACAO_2022.get(num_partido) if ano == 2022 else None
        cols = {
            "TP_AGREMIACAO": "FEDERAÇÃO" if fed else "PARTIDO ISOLADO",
            "NR_PARTIDO": num_partido,
            "SG_PARTIDO": sg,
            "NM_PARTIDO": nm,
            "NR_FEDERACAO": fed[0] if fed else -1,
            "NM_COLIGACAO": "PARTIDO ISOLADO",
            "DS_COMPOSICAO_COLIGACAO": sg,
        }
        if fed:
            cols |= {
                "NM_FEDERACAO": fed[1],
                "SG_FEDERACAO": fed[2],
                "DS_COMPOSICAO_FEDERACAO": fed[3],
            }
        return cols

    # Seção (votação e detalhe) -------------------------------------------------
    for (turno, s), (aptos, comp) in presenca.items():
        for cargo, _cands in _cargos_do_turno(turno, s.uf):
            federal = cargo == 1
            m = _membro(ano, cargo, s.uf)
            base = e.prefixo(turno, s.uf, federal) | {
                "CD_MUNICIPIO": s.cd_mun,
                "NM_MUNICIPIO": s.nm_mun,
                "NR_ZONA": s.zona,
                "NR_SECAO": s.secao,
                "CD_CARGO": cargo,
                "DS_CARGO": CARGO_NOME[cargo].upper() if federal else CARGO_NOME[cargo],
                "NR_LOCAL_VOTACAO": s.local,
                "NM_LOCAL_VOTACAO": s.nm_local,
                "DS_LOCAL_VOTACAO_ENDERECO": s.endereco,
            }
            q = {
                tipo: sum(v for k, v in votos.items() if k[:4] == (turno, s, cargo, tipo))
                for tipo in ("nominal", "legenda", "branco", "nulo")
            }
            e.linha(
                f"detalhe_votacao_secao_{ano}_{m}.csv",
                H_DETALHE_SECAO,
                base
                | {
                    "QT_APTOS": aptos,
                    "QT_COMPARECIMENTO": comp,
                    "QT_ABSTENCOES": aptos - comp,
                    "QT_VOTOS_NOMINAIS": q["nominal"],
                    "QT_VOTOS_BRANCOS": q["branco"],
                    "QT_VOTOS_NULOS": q["nulo"],
                    "QT_VOTOS_LEGENDA": q["legenda"],
                    "QT_VOTOS_ANULADOS_APU_SEP": 0,
                    "DS_ORIGEM_VOTO": "Urna Eletrônica",
                    "ST_SECAO_INSTALADA": "Sim",
                    "ST_SECAO_ANULADA": "Não",
                    "CD_MODELO_URNA": "2020",
                    "DS_MODELO_URNA": "UE 2020",
                },
            )
            if m == "SP":
                continue  # o arquivo de votação por seção só é lido para MG e BR
            for (t, sec, cg, tipo, num), qtd in votos.items():
                if (t, sec, cg) != (turno, s, cargo) or qtd == 0:
                    continue
                if tipo == "nominal":
                    c = cand_por_num[(cargo, "BR" if federal else s.uf, num)]
                    nm, sq = c.nome, _sq(ano, c)
                elif tipo == "legenda":
                    nm, sq = PARTIDOS[num][0], -1
                else:
                    nm, sq = ("VOTO BRANCO" if tipo == "branco" else "VOTO NULO"), -1
                e.linha(
                    f"votacao_secao_{ano}_{m}.csv",
                    H_VOTACAO_SECAO,
                    base
                    | {"NR_VOTAVEL": num, "NM_VOTAVEL": nm, "QT_VOTOS": qtd, "SQ_CANDIDATO": sq},
                )

    # Município/zona ---------------------------------------------------------------
    zonas = sorted({(s.uf, s.cd_mun, s.nm_mun, s.zona) for s in SECOES})
    for turno in (1, 2):
        for uf, cd_mun, nm_mun, zona in zonas:
            secoes = [s for s in SECOES if (s.uf, s.cd_mun, s.zona) == (uf, cd_mun, zona)]
            for cargo, cands in _cargos_do_turno(turno, uf):
                federal = cargo == 1
                m = _membro(ano, cargo, uf)
                base = e.prefixo(turno, uf, federal) | {
                    "CD_MUNICIPIO": cd_mun,
                    "NM_MUNICIPIO": nm_mun,
                    "NR_ZONA": zona,
                    "CD_CARGO": cargo,
                    "DS_CARGO": CARGO_NOME[cargo],
                    "ST_VOTO_EM_TRANSITO": "N",
                }

                def soma(tipo, num=None, _turno=turno, _cargo=cargo, _secoes=secoes):
                    return sum(
                        v
                        for (t, s, cg, tp, n), v in votos.items()
                        if t == _turno
                        and s in _secoes
                        and cg == _cargo
                        and tp == tipo
                        and (num is None or n == num)
                    )

                nao_se_aplica = {  # julgamento/cassação/diploma vêm como -3/#NE nos reais
                    h: (-3 if h.startswith("CD_") else "#NE") for h in H_MUNZONA[ano][27:33]
                }
                for c in cands:
                    q = soma("nominal", c.numero)
                    situacao = sit[(turno, cargo, c.uf, c.numero)]
                    e.linha(
                        f"votacao_candidato_munzona_{ano}_{m}.csv",
                        H_MUNZONA[ano],
                        base
                        | nao_se_aplica
                        | partido_cols(c.partido)
                        | {
                            "SQ_CANDIDATO": _sq(ano, c),
                            "NR_CANDIDATO": c.numero,
                            "NM_CANDIDATO": c.nome,
                            "NM_URNA_CANDIDATO": c.urna,
                            "CD_SITUACAO_CANDIDATURA": 12,
                            "DS_SITUACAO_CANDIDATURA": "APTO",
                            "CD_DETALHE_SITUACAO_CAND": 2,
                            "DS_DETALHE_SITUACAO_CAND": "DEFERIDO",
                            "SQ_COLIGACAO": _sq(ano, c) + 50000,
                            "QT_VOTOS_NOMINAIS": q,
                            "NM_TIPO_DESTINACAO_VOTOS": "Válido",
                            "QT_VOTOS_NOMINAIS_VALIDOS": q,
                            "CD_SIT_TOT_TURNO": SIT[situacao],
                            "DS_SIT_TOT_TURNO": situacao,
                        },
                    )
                aptos = sum(presenca[(turno, s)][0] for s in secoes)
                comp = sum(presenca[(turno, s)][1] for s in secoes)
                nom, leg = soma("nominal"), soma("legenda")
                br, nu = soma("branco"), soma("nulo")
                e.linha(
                    f"detalhe_votacao_munzona_{ano}_{m}.csv",
                    H_DETALHE_MUNZONA,
                    base
                    | {
                        "QT_APTOS": aptos,
                        "QT_SECOES_PRINCIPAIS": len(secoes),
                        "QT_SECOES_AGREGADAS": 0,
                        "QT_SECOES_NAO_INSTALADAS": 0,
                        "QT_TOTAL_SECOES": len(secoes),
                        "QT_COMPARECIMENTO": comp,
                        "QT_ELEITORES_SECOES_NAO_INSTALADAS": 0,
                        "QT_ABSTENCOES": aptos - comp,
                        "QT_VOTOS": nom + leg + br + nu,
                        "QT_VOTOS_CONCORRENTES": nom + leg,
                        "QT_TOTAL_VOTOS_VALIDOS": nom + leg,
                        "QT_VOTOS_NOMINAIS_VALIDOS": nom,
                        "QT_TOTAL_VOTOS_LEG_VALIDOS": leg,
                        "QT_VOTOS_LEG_VALIDOS": leg,
                        "QT_VOTOS_NOM_CONVR_LEG_VALIDOS": 0,
                        "QT_TOTAL_VOTOS_ANULADOS": 0,
                        "QT_VOTOS_NOMINAIS_ANULADOS": 0,
                        "QT_VOTOS_LEGENDA_ANULADOS": 0,
                        "QT_TOTAL_VOTOS_ANUL_SUBJUD": 0,
                        "QT_VOTOS_NOMINAIS_ANUL_SUBJUD": 0,
                        "QT_VOTOS_LEGENDA_ANUL_SUBJUD": 0,
                        "QT_VOTOS_BRANCOS": br,
                        "QT_TOTAL_VOTOS_NULOS": nu,
                        "QT_VOTOS_NULOS": nu,
                        "QT_VOTOS_NULOS_TECNICOS": 0,
                        "QT_VOTOS_ANULADOS_APU_SEP": 0,
                        "HH_ULTIMA_TOTALIZACAO": "18:44:58",
                        "DT_ULTIMA_TOTALIZACAO": "25/10/2023",
                    },
                )

    # Candidatos (com campos pessoais, para testar a allowlist) --------------------
    for i, c in enumerate(CANDIDATOS):
        for turno in (1, 2):
            if turno == 2 and c.numero not in SEGUNDO_TURNO.get((c.cargo, c.uf), ()):
                continue
            uf = c.uf
            federal = c.cargo == 1
            pref = e.prefixo(turno, "MG" if federal else uf, federal)
            pref |= {"SG_UF": uf, "TP_ABRANGENCIA": "FEDERAL" if federal else "ESTADUAL"}
            situacao = sit[(turno, c.cargo, uf, c.numero)]
            e.linha(
                f"consulta_cand_{ano}_{uf}.csv",
                H_CONSULTA_CAND,
                pref
                | partido_cols(c.partido)
                | {
                    "CD_CARGO": c.cargo,
                    "DS_CARGO": CARGO_NOME[c.cargo].upper(),
                    "SQ_CANDIDATO": _sq(ano, c),
                    "NR_CANDIDATO": c.numero,
                    "NM_CANDIDATO": c.nome,
                    "NM_URNA_CANDIDATO": c.urna,
                    "NR_CPF_CANDIDATO": _cpf_ficticio(i),
                    "DS_EMAIL": f"candidato{i}@exemplo.com.br",
                    "CD_SITUACAO_CANDIDATURA": 12,
                    "DS_SITUACAO_CANDIDATURA": "APTO",
                    "SQ_COLIGACAO": _sq(ano, c) + 50000,
                    "SG_UF_NASCIMENTO": "MG",
                    "DT_NASCIMENTO": f"{1 + i % 28:02d}/0{1 + i % 9}/19{60 + i % 30}",
                    "NR_TITULO_ELEITORAL_CANDIDATO": f"{100000000000 + i * 7:012d}",
                    "CD_GENERO": 2 if i % 2 else 4,
                    "DS_GENERO": "MASCULINO" if i % 2 else "FEMININO",
                    "CD_GRAU_INSTRUCAO": 8,
                    "DS_GRAU_INSTRUCAO": "SUPERIOR COMPLETO",
                    "CD_ESTADO_CIVIL": 3,
                    "DS_ESTADO_CIVIL": "CASADO(A)",
                    "CD_COR_RACA": "03",
                    "DS_COR_RACA": "PARDA",
                    "CD_OCUPACAO": 999,
                    "DS_OCUPACAO": "OUTROS",
                    "CD_SIT_TOT_TURNO": SIT[situacao],
                    "DS_SIT_TOT_TURNO": situacao,
                },
            )

    # Locais de votação ----------------------------------------------------------------
    for (turno, s), (aptos, _comp) in presenca.items():
        if s.uf == "ZZ":
            continue
        e.linha(
            f"eleitorado_local_votacao_{ano}.csv",
            H_LOCAIS,
            {
                "DT_GERACAO": "30/09/2024",
                "HH_GERACAO": "02:00:32",
                "AA_ELEICAO": ano,
                "DT_ELEICAO": ELEICAO[ano][turno][2],
                "DS_ELEICAO": f"{turno}º Turno",
                "NR_TURNO": turno,
                "SG_UF": s.uf,
                "CD_MUNICIPIO": f"{s.cd_mun:05d}",
                "NM_MUNICIPIO": s.nm_mun,
                "NR_ZONA": s.zona,
                "NR_SECAO": s.secao,
                "CD_TIPO_SECAO_AGREGADA": 1,
                "DS_TIPO_SECAO_AGREGADA": "Principal",
                "NR_SECAO_PRINCIPAL": -1,
                "NR_LOCAL_VOTACAO": s.local,
                "NM_LOCAL_VOTACAO": s.nm_local,
                "CD_TIPO_LOCAL": 1,
                "DS_TIPO_LOCAL": "Convencional",
                "DS_ENDERECO": s.endereco,
                "NM_BAIRRO": s.bairro,
                "NR_CEP": "37500000",
                "NR_TELEFONE_LOCAL": "+5535999990000",
                "NR_LATITUDE": s.lat,
                "NR_LONGITUDE": s.lon,
                "QT_ELEITOR_SECAO": aptos,
            },
        )

    e.gravar(destino)


if __name__ == "__main__":
    for ano in (2018, 2022):
        gerar(ano, SAIDA / str(ano))
    print(f"Fixtures gerados em {SAIDA}")
