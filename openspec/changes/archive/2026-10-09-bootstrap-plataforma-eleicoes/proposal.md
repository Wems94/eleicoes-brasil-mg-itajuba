# Proposal

## Why

Os resultados eleitorais do TSE são públicos, mas estão espalhados em dezenas de arquivos CSV e ZIP grandes, em latin-1, com colunas que mudam a cada eleição. Hoje, um jornalista ou cidadão de Itajubá (MG) não consegue ver de forma simples como a cidade votou, seção por seção, nem comparar 2018, 2022 e 2026. O 1º turno de 2026 acabou de acontecer, então este é o momento de publicar.

## What Changes

- Novo pipeline de dados que baixa, transforma, valida e carrega os resultados oficiais do TSE das eleições gerais de 2018, 2022 e 2026 (1º e 2º turnos).
- Visão geral por UF para todo o Brasil e deep dive em Itajubá-MG até o nível de seção eleitoral e local de votação.
- Execução sob demanda e parametrizada por `ano` e `turno`, o que permite carregar o 2º turno de 2026 quando ele acontecer, sem mudar código.
- Gate de qualidade: nada é publicado se uma regra falhar.
- Proteção de dados pessoais (LGPD): CPF, e-mail e título de eleitor de candidatos nunca entram no armazenamento derivado nem no site.
- Banco analítico DuckDB/MotherDuck como fonte oficial dos dados tratados.
- Site público estático (Next.js na Vercel) alimentado por snapshots versionados, com rollback instantâneo.

## Capabilities

### New Capabilities

- `ingestao-tse`: download idempotente e verificável dos arquivos oficiais do TSE e leitura de Boletins de Urna.
- `transformacao-dados`: padronização dos arquivos do TSE em tabelas tipadas e modelos analíticos (marts).
- `qualidade-dados`: regras de qualidade que bloqueiam a publicação.
- `protecao-dados-pessoais`: garantia de que dados pessoais sensíveis de candidatos não são armazenados nem publicados.
- `publicacao-dados`: carga no banco analítico e geração de snapshots para o site.
- `site-resultados`: site público com resultados por UF e deep dive de Itajubá.

### Modified Capabilities

(nenhuma; projeto novo)

## Impact

- Novo monorepo: `openspec/`, `pipeline/` (Python + uv), `web/` (Next.js), `.github/workflows/`.
- Dependências externas: Portal de Dados Abertos do TSE (cdn.tse.jus.br), MotherDuck (token em GitHub Secrets) e Vercel.
- Fora de escopo: eleições municipais (2020 e 2024), apuração em tempo real e mapas coropléticos por município (ficam para um change futuro).
