# Design

## Context

A motivação está em `proposal.md`. Restrições que moldam a solução:

- **Fonte única e oficial:** Portal de Dados Abertos do TSE (`https://cdn.tse.jus.br/estatistica/sead/odsele/`). Os arquivos vêm em ZIP com CSV em latin-1, separador `;` e marcadores de nulo (`#NULO#`, `#NE#`, `-1`, `-3`). As colunas variam entre 2018, 2022 e 2026; por exemplo, federações só existem a partir de 2022.
- **Volume:** os arquivos nacionais por município/zona têm centenas de MB. A votação por seção de MG tem milhões de linhas, mas só Itajubá precisa de granularidade de seção.
- **Público:** o site é aberto ao público, com picos de acesso em noites de eleição, e não pode cair nem exibir dados não validados.
- **Ambiente:** macOS + uv + Git localmente, GitHub Actions no CI e Vercel no plano Hobby (sem fins lucrativos).

## Goals / Non-Goals

**Goals**
- Uma única execução parametrizada (`ano`, `turno`) do pipeline, reexecutável sem efeitos colaterais.
- O site nunca depende do banco em tempo de requisição.

**Non-Goals**
- Apuração ao vivo e polling da API de resultados.
- Mapas coropléticos por município (exigem um de-para TSE→IBGE; ficam para um change futuro).
- Orquestrador dedicado (Airflow, Dagster).

## Decisions

### D1. Monorepo `openspec/` + `pipeline/` + `web/`
O pipeline e o site compartilham o contrato dos snapshots. Um só repositório deixa o PR de dados e o de código revisáveis juntos. A alternativa de dois repositórios foi descartada porque exigiria sincronizar versões de schema entre eles.

### D2. Leitura dos CSVs com DuckDB e manipulação pontual com Polars
O `read_csv` do DuckDB lê latin-1 em streaming, com `all_varchar` e filtros aplicados durante a leitura. Assim, as 20+ milhões de linhas de MG nunca vão inteiras para a memória. Polars fica para estruturas pequenas, como os votos de BU. O Pandas foi descartado por consumir mais memória e ser mais lento; o Spark, por ser desproporcional ao volume.

### D3. Colunas resolvidas por lista de candidatos (column aliasing)
Cada tabela de staging declara suas colunas de destino, cada uma com uma lista de nomes de origem possíveis. A primeira coluna existente é usada; se nenhuma existir, o valor fica `NULL` tipado. Isso absorve as mudanças entre anos e funciona também como **allowlist**: o que não está declarado nunca é lido, e é isso que implementa a proteção de dados pessoais por construção.

### D4. Partições `ano=/turno=` em Parquet e recarga por substituição
O staging é gravado como `data/staging/<tabela>/ano=YYYY/turno=N/part.parquet`. Recarregar um `(ano, turno)` substitui só aquela partição, e é isso que permite carregar o 2º turno de 2026 depois.

### D5. Recorte geográfico em duas resoluções
- **Brasil por UF:** `votacao_candidato_munzona` e `detalhe_votacao_munzona`, para todos os municípios.
- **Itajubá:** `votacao_secao_<ano>_MG` e `detalhe_votacao_secao` (membro MG), filtrados pelo código TSE do município. O código é resolvido pelo nome (`ITAJUBÁ`/MG) a partir dos próprios dados, e não fica fixo no código.
- Se o arquivo de seção de MG não trouxer o cargo Presidente, o pipeline usa `votacao_secao_<ano>_BR` filtrado.

### D6. Gate de qualidade antes de qualquer publicação
As regras rodam em SQL sobre o DuckDB recém-construído. Qualquer erro interrompe a execução, com código de saída diferente de zero, antes de carregar no MotherDuck ou de gerar snapshots.

### D7. Publicação em dois destinos
1. **MotherDuck:** `CREATE OR REPLACE DATABASE` a partir do arquivo DuckDB local validado. É o banco oficial, consultável por SQL.
2. **Snapshots JSON** em `web/data/`: gravados primeiro num diretório temporário e trocados de uma vez por renomeação. No CI, entram por Pull Request; o merge dispara o deploy na Vercel.

Alternativa descartada: o site consultar o MotherDuck em runtime, porque cria acoplamento a disponibilidade, custo e latência.

### D8. Site Next.js com exportação estática (`output: "export"`)
Todas as rotas são pré-geradas a partir dos snapshots. A interface usa Tailwind com componentes no estilo shadcn/ui, ECharts nos gráficos e MapLibre com tiles OpenFreeMap (sem chave) no mapa dos locais de Itajubá. A visão do Brasil usa um tile-grid map das UFs, que não exige geometria.

### D9. Decodificador de Boletim de Urna (opcional)
Lê arquivos `.bu`/`.dat` (ASN.1 BER do TSE) colocados em `data/manual/bu/`. Serve para auditar seções de Itajubá contra o CSV oficial. Não é fonte primária.

## Risks / Trade-offs

- [Mudança de layout dos CSVs do TSE] → O aliasing de colunas (D3) e os testes com fixtures de cada ano tratam isso; uma coluna obrigatória ausente gera erro explícito.
- [Arquivo de 2026 atualizado pelo TSE após a carga] → Basta reexecutar o mesmo `(ano, turno)`, já que a partição é substituída (D4).
- [Download grande ou instável] → Retentativas com backoff, download em arquivo `.part` e manifest com sha256; o cache de `data/raw` reaproveita o que já foi baixado.
- [Duplicidade entre o arquivo `_BR` e os arquivos por UF no munzona] → Só os membros por UF e `ZZ` (exterior) são lidos, e a regra de unicidade detecta qualquer sobreposição.
- [Plano Hobby da Vercel] → É adequado enquanto o projeto não tiver fins comerciais; o README registra essa condição.

## Migration Plan

Projeto novo, sem migração. Rollback:
- **Site:** "Promote" do deploy anterior na Vercel.
- **Dados:** reverter o PR de snapshots.
- **MotherDuck:** reexecutar o pipeline com o commit anterior.

## Open Questions

- Licenciamento e atribuição dos tiles do mapa: OpenFreeMap exige atribuição ao OSM, já incluída na interface.
