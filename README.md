# eleicoes-brasil-mg-itajuba

Site público com os resultados das Eleições Gerais do Brasil (2018, 2022, 2026), com visão por UF e deep dive em **Itajubá-MG**. O desenvolvimento é guiado por specs ([OpenSpec](https://github.com/Fission-AI/OpenSpec)).

## Arquitetura (aprovada)

```
TSE Dados Abertos (ZIP/CSV) → pipeline Python (uv: DuckDB + Polars)
  → EXTRACT (manifest sha256) → TRANSFORM (allowlist de colunas, LGPD) → QUALITY GATE
  → LOAD MotherDuck (banco oficial) → PUBLISH snapshots JSON (web/data) via PR
  → Next.js estático (SSG) na Vercel
```

| Componente | Tecnologia |
|---|---|
| Specs | OpenSpec (`openspec/`) |
| Pipeline | Python 3.12, uv, httpx, DuckDB, Polars, Typer |
| Banco | DuckDB local + MotherDuck |
| Site | Next.js (export estático), Tailwind, shadcn/ui, ECharts, MapLibre |
| Orquestração/CI | GitHub Actions (`workflow_dispatch` com `ano`/`turno`) + Vercel |

Todas as decisões e os requisitos estão em `openspec/changes/bootstrap-plataforma-eleicoes/`:
`proposal.md` (por quê), `design.md` (como), `specs/*/spec.md` (requisitos testáveis) e `tasks.md` (checklist).

## Estado atual

- [x] OpenSpec inicializado (`openspec/config.yaml`, pt-BR) com o change `bootstrap-plataforma-eleicoes`
- [x] Pipeline em `pipeline/` (tarefas 2.x a 5.x): download, staging, marts, gate de qualidade, LGPD, MotherDuck, snapshots e CLI `eleicoes run`
- [x] Site em `web/` (tarefas 6.x): Next.js estático com Brasil, UF, Itajubá e metodologia
- [x] Workflows em `.github/workflows/` (tarefas 7.x): `ci.yml`, `etl.yml`, `deploy.yml` e `validacao-real.yml`
- [ ] Decodificador de BU validado com um BU real (tarefa 2.3)
- [x] Verificação integrada (tarefa 8.1): site no ar em https://eleicoes-brasil-mg-itajuba.vercel.app com 2018, 2022 e 2026 (1º turno)

## Comandos

```bash
# pipeline (de dentro de pipeline/)
uv run pytest                                   # testes
uv run eleicoes run --ano 2026 --turno 1        # ETL completo com dados reais (~1,5 GB por ano)

# site (de dentro de web/)
pnpm fixture && pnpm build:fixture              # build com dados de teste (fictícios)
pnpm build                                      # build com os snapshots publicados em web/data
```

## CI/CD

| Workflow | Quando roda | O que faz |
|---|---|---|
| `ci.yml` | push na `main` e PRs | ruff, pytest, LGPD em `web/data`, build do site (fixture e, se houver, dados reais), typecheck |
| `etl.yml` | manual (Actions → ETL) | `eleicoes run` para cada eleição informada, trava contra perda de eleições publicadas e **PR** com os snapshots |
| `deploy.yml` | push na `main` em `web/**` (ou seja, após o merge do PR do ETL) | build e deploy de produção na Vercel pela CLI |
| `validacao-real.yml` | manual | diagnóstico do pipeline com dados reais, sem publicar |

**Fluxo de publicação:** Actions → ETL → revisar e fazer merge do PR `dados/snapshots` → o deploy roda sozinho.

Sem `MOTHERDUCK_TOKEN`, o banco do runner começa vazio, então o ETL precisa processar **todas** as
eleições na mesma execução (é o padrão: `2018/1 2018/2 2022/1 2022/2 2026/1`). Com o token, o banco
vem do MotherDuck e basta informar o turno novo (ex.: `2026/2`). Se o TSE republicar um arquivo,
rode o ETL com "forcar" marcado.

### Secrets (Settings → Secrets and variables → Actions)

| Secret | Uso | Onde obter |
|---|---|---|
| `MOTHERDUCK_TOKEN` | opcional; persiste o banco entre execuções (D4) | MotherDuck → Settings → Access Tokens |
| `VERCEL_TOKEN` | deploy | Vercel → Account Settings → Tokens |
| `VERCEL_ORG_ID` | deploy | `web/.vercel/project.json` após `vercel link` (campo `orgId`) |
| `VERCEL_PROJECT_ID` | deploy | `web/.vercel/project.json` (campo `projectId`) |

Configurações necessárias:
- **GitHub:** Settings → Actions → General → "Allow GitHub Actions to create and approve pull requests" (o ETL abre o PR com o `GITHUB_TOKEN`).
- **Vercel:** o projeto é criado com `npx vercel@63.1.0 link` rodado dentro de `web/` (não precisa mudar nada no painel). O `web/vercel.json` desliga os deploys automáticos da integração Git: só o `deploy.yml` publica.
- PRs abertos pelo `GITHUB_TOKEN` não disparam o `ci.yml`; o gate de qualidade e o LGPD já rodam dentro do ETL antes da geração dos snapshots.

## Começando no VS Code

```bash
cd pipeline && uv sync          # cria o .venv
npm i -g @fission-ai/openspec   # CLI do OpenSpec
openspec list                   # changes em andamento
openspec show bootstrap-plataforma-eleicoes
```

Com o Claude Code, use os comandos instalados em `.claude/commands/opsx/` (`/opsx:apply` para implementar as tarefas do change, `/opsx:archive` ao concluir).

## Fontes TSE confirmadas (padrão de URL)

Base: `https://cdn.tse.jus.br/estatistica/sead/odsele/`

| Dataset | Arquivo | Uso |
|---|---|---|
| Votação por município/zona | `votacao_candidato_munzona/votacao_candidato_munzona_{ANO}.zip` | Visão por UF |
| Detalhe por município/zona | `detalhe_votacao_munzona/detalhe_votacao_munzona_{ANO}.zip` | Comparecimento, brancos, nulos |
| Votação por seção (MG) | `votacao_secao/votacao_secao_{ANO}_MG.zip` | Itajubá por seção |
| Votação por seção (Presidente) | `votacao_secao/votacao_secao_{ANO}_BR.zip` | Fallback de Presidente |
| Detalhe por seção | `detalhe_votacao_secao/detalhe_votacao_secao_{ANO}.zip` | Comparecimento por seção |
| Candidatos | `consulta_cand/consulta_cand_{ANO}.zip` | Atributos de candidatos (**contém CPF/e-mail: usar allowlist**) |
| Locais de votação | `eleitorado_locais_votacao/eleitorado_local_votacao_{ANO}.zip` | Mapa de locais (lat/long) |

Os arquivos de 2026 (1º turno) já estão listados em <https://dadosabertos.tse.jus.br/dataset/resultados-2026>.

## Notas para a implementação

- **Formato dos CSVs:** latin-1, separador `;`. Nulos vêm como `#NULO#`, `#NE#`, `-1` e `-3`. As colunas mudam entre os anos, por isso o mapeamento usa aliases (D3 no `design.md`).
- **Itajubá:** resolver o código TSE pelo nome (`ITAJUBÁ`/MG) nos próprios dados, sem fixar no código.
- **Senado:** 2018 e 2026 têm 2 vagas e 2022 tem 1. Na regra "soma dos votos = comparecimento × vagas", multiplicar pelas vagas.
- **Persistência do staging (resolvido, D4):** o staging vive no schema `staging` de `data/eleicoes.duckdb`, e a substituição é feita por `(ano, turno)` com `DELETE` + `INSERT` numa transação. Com token, o MotherDuck é a fonte da verdade. A execução começa com `COPY FROM DATABASE eleicoes TO local_db` (baixar), depois transforma e valida, e só então roda `CREATE OR REPLACE DATABASE eleicoes FROM 'data/eleicoes.duckdb'` (enviar). Sem token, o arquivo local é a única cópia. O `etl.yml` serializa as cargas com `concurrency`.
- **Boletim de Urna (opcional, D9):** os BUs (`.bu`/`.dat`) são ASN.1 BER. Um decodificador de referência está em `pipeline/scripts/bu_dump.py`.
- **Vercel Hobby:** apenas uso não comercial.
