# ingestao-tse Specification

## Purpose

Obter, de forma idempotente e verificável, os arquivos oficiais de resultados, candidatos e locais de votação publicados pelo TSE para as eleições gerais de 2018, 2022 e 2026.

## Requirements

### Requirement: Execução parametrizada por ano e turno
O sistema SHALL aceitar `ano` (2018, 2022 ou 2026) e `turno` (1 ou 2) como parâmetros de execução e processar apenas os dados correspondentes.

#### Scenario: Carga do 2º turno de 2026
- **WHEN** o pipeline é executado com `ano=2026` e `turno=2`
- **THEN** apenas as linhas com `NR_TURNO=2` da eleição de 2026 são processadas e as partições de outros turnos permanecem inalteradas

#### Scenario: Ano não suportado
- **WHEN** o pipeline é executado com `ano=2020`
- **THEN** a execução termina com erro explicando quais anos são suportados

### Requirement: Download idempotente com verificação de integridade
O sistema SHALL registrar, para cada arquivo baixado, a URL, o tamanho, o sha256 e a data do download, e SHALL reutilizar o arquivo local quando ele já existir íntegro.

#### Scenario: Reexecução sem mudanças
- **WHEN** o pipeline é executado duas vezes seguidas para o mesmo ano
- **THEN** a segunda execução não baixa novamente arquivos já registrados no manifest com o mesmo sha256

#### Scenario: Download interrompido
- **WHEN** a conexão cai durante um download
- **THEN** nenhum arquivo parcial é tratado como válido e o download é tentado novamente com backoff

#### Scenario: Forçar atualização
- **WHEN** o pipeline é executado com a opção de atualização forçada
- **THEN** os arquivos são baixados novamente e o manifest é atualizado

### Requirement: Fonte indisponível
O sistema SHALL falhar de forma explícita quando um arquivo obrigatório não puder ser obtido, e SHALL seguir sem erro quando um arquivo opcional estiver indisponível.

#### Scenario: Arquivo obrigatório ausente
- **WHEN** o TSE responde 404 para o arquivo de votação por município e zona
- **THEN** a execução termina com erro identificando a URL e nada é publicado

#### Scenario: Arquivo opcional ausente
- **WHEN** o arquivo de locais de votação de um ano não existe
- **THEN** a execução continua, registra um aviso e o site exibe Itajubá sem o mapa de locais daquele ano

### Requirement: Leitura de Boletim de Urna
O sistema SHALL decodificar arquivos de Boletim de Urna do TSE fornecidos manualmente e extrair a identificação da seção, o comparecimento e os votos por cargo e votável.

#### Scenario: BU válido
- **WHEN** um arquivo de BU de uma seção é decodificado
- **THEN** a soma dos votos de cada cargo majoritário de vaga única é igual ao comparecimento da seção
