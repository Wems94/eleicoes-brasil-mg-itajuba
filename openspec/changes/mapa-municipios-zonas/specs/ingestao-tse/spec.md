# Spec Delta

## ADDED Requirements

### Requirement: Fontes do IBGE
O sistema SHALL obter do IBGE a lista oficial de municípios (código, nome e UF) e a malha municipal, com o mesmo registro de URL, tamanho, sha256 e data e a mesma reutilização de arquivo íntegro das fontes do TSE. Essas fontes SHALL ser obrigatórias.

#### Scenario: Reexecução
- **WHEN** o pipeline roda de novo sem mudanças no IBGE
- **THEN** a lista de municípios e a malha não são baixadas novamente

#### Scenario: IBGE fora do ar
- **WHEN** o serviço do IBGE não responde
- **THEN** a execução termina com erro identificando a URL e nada é publicado

### Requirement: Votação por partido, município e zona
O sistema SHALL obter do TSE, como fonte obrigatória, a votação por partido, município e zona, com os votos nominais e de legenda de cada partido, para calcular o partido mais votado nos cargos proporcionais.

#### Scenario: Legenda por partido
- **WHEN** os dados de 2022 são processados
- **THEN** o staging tem, para cada partido, município, zona e cargo proporcional, os votos de legenda do partido

### Requirement: Fotos dos candidatos a Presidente
O sistema SHALL obter do TSE o pacote de fotos de divulgação dos candidatos e SHALL extrair apenas as fotos dos candidatos a Presidente do ano processado. A fonte SHALL ser opcional.

#### Scenario: Fotos disponíveis
- **WHEN** o pacote de fotos de 2022 é processado
- **THEN** são extraídas só as fotos cujo candidato concorre a Presidente em 2022

#### Scenario: Pacote ausente
- **WHEN** o TSE ainda não publicou o pacote de fotos de um ano
- **THEN** a execução continua com aviso e o site mostra as iniciais no lugar das fotos
