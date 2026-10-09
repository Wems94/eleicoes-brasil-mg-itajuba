# Tasks

## 1. Fundação do repositório

- [x] 1.1 Criar monorepo (`pipeline/`, `web/`, `.github/workflows/`), `.gitignore` com `data/` e `.env*`, `.env.example` e README; verificar com `git check-ignore pipeline/data/raw/x.zip`
- [x] 1.2 Inicializar projeto uv em `pipeline/` com dependências (duckdb, polars, httpx, pyyaml, typer) e dev (pytest, ruff); verificar com `uv run eleicoes --help`

## 2. Ingestão

- [x] 2.1 Catálogo de fontes TSE em `config/fontes.yaml` com URL por ano, membros do ZIP e obrigatoriedade; teste unitário de resolução de URLs
- [x] 2.2 Download com `.part`, retentativas, manifest sha256 e reutilização; testes com servidor HTTP local (idempotência, falha, 404 obrigatório/opcional)
- [ ] 2.3 Decodificador de Boletim de Urna; teste com o BU real de MG (soma = comparecimento)

## 3. Transformação

- [x] 3.1 Leitor de CSV TSE (latin-1, `;`, nulos) com aliasing de colunas e erro para coluna obrigatória ausente; testes com fixtures de layouts 2018 e 2022
- [x] 3.2 Staging em tabelas DuckDB (schema `staging`) com substituição de `(ano, turno)` por `DELETE`+`INSERT` transacional; teste de reprocessamento idempotente e de preservação das outras partições
- [x] 3.3 Resolução do código TSE de Itajubá e recorte por seção; fallback de Presidente via arquivo `_BR`; teste com fixture
- [x] 3.4 Marts (UF, Brasil, comparecimento, Itajubá por cargo/zona/local/seção, histórico); testes de percentuais

## 4. Qualidade e LGPD

- [ ] 4.1 Regras de qualidade (soma = comparecimento × vagas, unicidade, domínios, referencial, completude) com relatório e saída ≠ 0; testes que forçam cada falha
- [ ] 4.2 Verificador LGPD (colunas proibidas e padrões CPF/e-mail) sobre banco e snapshots; teste com vazamento injetado

## 5. Publicação

- [ ] 5.1 Sincronização MotherDuck opcional por token (D4): baixar `eleicoes` antes da transformação (`COPY FROM DATABASE`, tolerando banco inexistente) e enviar após o gate (`CREATE OR REPLACE DATABASE ... FROM`); testes de pulo sem token e de que o envio não ocorre se o gate falhar
- [ ] 5.2 Snapshots JSON atômicos + manifesto; teste de falha no meio preservando diretório anterior
- [ ] 5.3 CLI `eleicoes run --ano --turno` encadeando tudo; teste ponta a ponta com fixtures

## 6. Site

- [ ] 6.1 Next.js (export estático) + Tailwind + componentes base; `pnpm build` passa com dados de fixture
- [ ] 6.2 Home Brasil (resultado nacional + tile map de UFs) com seletor de ano/turno
- [ ] 6.3 Página por UF (cargos, comparecimento, deputados com situação)
- [ ] 6.4 Deep dive Itajubá (cargos, zonas, locais com mapa, busca de seção, comparação histórica)
- [ ] 6.5 Página de metodologia, fonte e data de geração; tabela equivalente a cada gráfico

## 7. CI/CD

- [ ] 7.1 `ci.yml`: ruff, pytest, verificador LGPD em `web/data`, typecheck e build do site
- [ ] 7.2 `etl.yml`: `workflow_dispatch` (ano, turno), `concurrency` única sem cancelamento, cache de `data/raw`, pipeline, PR de snapshots
- [ ] 7.3 `deploy.yml`: deploy Vercel na main via CLI com secrets documentados

## 8. Verificação integrada

- [ ] 8.1 Executar pipeline com fixtures → snapshots → `pnpm build`; `openspec validate --strict` passa
