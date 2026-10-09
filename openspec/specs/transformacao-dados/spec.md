# transformacao-dados Specification

## Purpose

Converter os arquivos heterogêneos do TSE em tabelas padronizadas, tipadas e particionadas, e em modelos analíticos prontos para consulta e publicação.

## Requirements

### Requirement: Padronização de schema entre anos
O sistema SHALL produzir, para cada tabela de staging, o mesmo conjunto de colunas com os mesmos tipos, independentemente do ano de origem; colunas inexistentes num ano SHALL ficar nulas.

#### Scenario: Federação em 2018
- **WHEN** os dados de 2018 são transformados
- **THEN** a coluna de número de federação existe e é nula em todas as linhas

#### Scenario: Coluna obrigatória ausente
- **WHEN** um arquivo não contém nenhum dos nomes aceitos para uma coluna obrigatória
- **THEN** a transformação falha informando a tabela, a coluna e os nomes procurados

### Requirement: Normalização de valores do TSE
O sistema SHALL converter os marcadores de ausência do TSE (`#NULO#`, `#NE#`, `#NULO`, `-1`, `-3` em campos de código) em nulos e SHALL ler os arquivos com a codificação latin-1.

#### Scenario: Nome com acento
- **WHEN** um arquivo contém o município `ITAJUBÁ`
- **THEN** o valor é armazenado em UTF-8 como `ITAJUBÁ`

### Requirement: Partições substituíveis
O sistema SHALL armazenar o staging particionado por ano e turno, e reprocessar um par (ano, turno) SHALL substituir apenas aquela partição.

#### Scenario: Reprocessamento
- **WHEN** o par (2026, 1) é processado duas vezes
- **THEN** a contagem de linhas da partição é a mesma após a segunda execução

### Requirement: Recorte de Itajubá por seção
O sistema SHALL manter dados por seção eleitoral apenas do município de Itajubá-MG, identificado pelo nome e pela UF nos próprios dados do TSE.

#### Scenario: Município identificado
- **WHEN** os dados de MG são processados
- **THEN** a tabela de seções contém apenas linhas do código TSE correspondente a `ITAJUBÁ`/MG

### Requirement: Modelos analíticos
O sistema SHALL disponibilizar marts com: resultado por UF e cargo; resultado nacional de Presidente; comparecimento por UF; e, para Itajubá, resultado por cargo, por zona, por local de votação e por seção.

#### Scenario: Percentual de votos válidos
- **WHEN** o mart de resultado por UF é consultado
- **THEN** cada candidato tem votos absolutos e percentual sobre votos válidos do cargo naquela UF
