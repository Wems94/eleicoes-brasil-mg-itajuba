# Spec Delta

## MODIFIED Requirements

### Requirement: Manifesto de snapshots
O sistema SHALL publicar um manifesto com a lista de eleições e turnos disponíveis, a data de geração, a versão do schema (2) e o sha256 de cada arquivo de origem usado, incluindo as fontes do IBGE e as fotos.

#### Scenario: Site lê o manifesto
- **WHEN** o site é construído
- **THEN** ele oferece apenas os anos e turnos presentes no manifesto

#### Scenario: Schema anterior
- **WHEN** o site é construído com snapshots do schema 1
- **THEN** o build falha com uma mensagem que manda regenerar os snapshots pelo workflow de ETL

## ADDED Requirements

### Requirement: Snapshots do mapa municipal
O sistema SHALL publicar, por eleição e cargo, um arquivo compacto com o vencedor (ou o partido vencedor), o percentual e a abstenção de cada município, identificado pelo código IBGE. SHALL publicar também, por eleição, UF e cargo, o detalhe de cada município e de cada zona.

#### Scenario: Tamanho da camada
- **WHEN** a camada de Presidente de um turno é gerada
- **THEN** o arquivo tem uma entrada por município com dados, e não inclui o detalhe por zona

#### Scenario: Determinismo
- **WHEN** os snapshots são gerados duas vezes com os mesmos dados
- **THEN** os arquivos do mapa são idênticos byte a byte

### Requirement: Geometria publicada
O sistema SHALL publicar a malha municipal simplificada, identificada pelo código IBGE e com os limites das UFs. A geometria SHALL ser compartilhada por todas as eleições.

#### Scenario: Município presente nos dados e na malha
- **WHEN** a geometria e as camadas são publicadas
- **THEN** todo código IBGE das camadas existe na geometria

### Requirement: Fotos publicadas
O sistema SHALL publicar as fotos dos candidatos a Presidente reduzidas a um tamanho fixo, identificadas pelo ano e pelo número sequencial do candidato.

#### Scenario: Foto reduzida
- **WHEN** uma foto do TSE é publicada
- **THEN** ela tem as dimensões fixas do site e é referenciada pelo snapshot do Brasil
