# Spec Delta

## MODIFIED Requirements

### Requirement: Modelos analíticos
O sistema SHALL disponibilizar marts com: resultado por UF e cargo; resultado nacional de Presidente; comparecimento por UF; resultado e comparecimento por município e por município × zona eleitoral, para todos os cargos; votos por partido (nominais mais legenda) por município e por município × zona para os cargos proporcionais; e, para Itajubá, resultado por cargo, por zona, por local de votação e por seção.

#### Scenario: Percentual de votos válidos
- **WHEN** o mart de resultado por UF é consultado
- **THEN** cada candidato tem votos absolutos e percentual sobre votos válidos do cargo naquela UF

#### Scenario: Resultado por município
- **WHEN** o mart de resultado por município é consultado para Presidente em 2022, 2º turno
- **THEN** cada município tem os votos e o percentual sobre os válidos de cada candidato, a posição e o comparecimento (aptos, comparecimento, abstenção, brancos e nulos)

#### Scenario: Partido em cargo proporcional
- **WHEN** o mart de votos por partido é consultado para Deputado Federal num município
- **THEN** cada partido tem a soma dos votos nominais dos seus candidatos mais os votos de legenda, e o percentual sobre os válidos do município

## ADDED Requirements

### Requirement: Código IBGE dos municípios
O sistema SHALL associar a cada município do TSE o código IBGE de 7 dígitos, pela UF e pelo nome normalizado (sem acento, sem diferenciar maiúsculas), com uma tabela versionada de exceções para os nomes que divergem entre TSE e IBGE.

#### Scenario: Nome divergente
- **WHEN** o TSE grafa um município de forma diferente do IBGE
- **THEN** a tabela de exceções resolve o código, e o município aparece no mapa

#### Scenario: Exterior
- **WHEN** o município pertence à UF ZZ (exterior)
- **THEN** ele não recebe código IBGE e fica fora da correspondência sem gerar erro
