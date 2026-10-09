// Contrato dos snapshots (schema_versao 1), gerado por pipeline/src/eleicoes/snapshots.py.

export type Eleicao = { ano: number; turno: number };

export type Manifesto = {
  schema_versao: number;
  gerado_em: string;
  fonte: string;
  municipio: { codigo: number; nome: string; uf: string } | null;
  eleicoes: { ano: number; turnos: number[] }[];
  origens: {
    ano: number;
    turno: number;
    fonte: string;
    url: string;
    sha256: string;
    tamanho: number;
  }[];
  arquivos: Record<string, string>;
};

export type Candidato = {
  numero: number;
  nome: string;
  partido: string | null;
  federacao: string | null;
  votos: number;
  pct: number | null;
  situacao: string | null;
  posicao: number;
};

export type Comparecimento = {
  aptos: number;
  comparecimento: number;
  abstencoes: number;
  brancos: number;
  nulos: number;
  pct_comparecimento?: number | null;
  pct_abstencao?: number | null;
  pct_brancos?: number | null;
  pct_nulos?: number | null;
};

export type Brasil = Eleicao & {
  presidente: { votos_validos: number; candidatos: Candidato[] } | null;
  comparecimento: Comparecimento | null;
  ufs: {
    uf: string;
    vencedor: { numero: number; nome: string; partido: string | null; pct: number | null };
    pct_comparecimento: number | null;
  }[];
};

export type Uf = Eleicao & {
  uf: string;
  cargos: { codigo: number; nome: string; votos_validos: number; candidatos: Candidato[] }[];
  comparecimento: (Comparecimento & { codigo: number; nome: string })[];
};

export type TipoVotavel = "candidato" | "legenda" | "branco" | "nulo" | "anulado";

export type Votavel = {
  tipo: TipoVotavel;
  numero: number;
  nome: string | null;
  partido: string | null;
  votos: number;
  pct: number | null;
  posicao: number | null;
};

export type CargoVotaveis = { codigo: number; votaveis: Votavel[] };

export type Itajuba = Eleicao & {
  cargos: (CargoVotaveis & { nome: string | null; comparecimento: Comparecimento | null })[];
  zonas: { zona: number; cargos: CargoVotaveis[] }[];
  locais: {
    zona: number;
    local: number;
    nome: string | null;
    endereco: string | null;
    bairro: string | null;
    lat: number | null;
    lon: number | null;
    secoes: number[];
    cargos: CargoVotaveis[];
  }[];
};

export type ItajubaSecoes = Eleicao & {
  // cargo -> número do votável -> nome
  votaveis: Record<string, Record<string, string>>;
  secoes: {
    zona: number;
    secao: number;
    local: number | null;
    comparecimento: Record<string, Comparecimento>;
    // cargo -> [número do votável, votos]
    votos: Record<string, [number, number][]>;
  }[];
};

export type Historico = {
  partidos: {
    ano: number;
    turno: number;
    cargo: number;
    nome_cargo: string;
    partido: string | null;
    votos: number;
    pct: number | null;
  }[];
  comparecimento: (Comparecimento & {
    ano: number;
    turno: number;
    cargo: number;
    nome_cargo: string;
  })[];
};
