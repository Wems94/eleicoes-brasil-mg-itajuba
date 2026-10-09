# qualidade-dados Specification

## Purpose

Garantir que só dados consistentes com as regras da apuração cheguem ao banco oficial e ao site público.

## Requirements

### Requirement: Gate de publicação
O sistema SHALL executar todas as regras de qualidade antes da carga e da publicação, e SHALL interromper a execução sem publicar nada quando qualquer regra de severidade erro falhar.

#### Scenario: Regra violada
- **WHEN** uma regra de severidade erro falha
- **THEN** a execução termina com código diferente de zero, o relatório lista a regra e exemplos das linhas violadoras, e os snapshots publicados permanecem os anteriores

### Requirement: Votos por seção iguais ao comparecimento
O sistema SHALL verificar, para cada seção de Itajubá e cada cargo, que a soma de votos (nominais, legenda, brancos e nulos) é igual ao comparecimento multiplicado pelo número de vagas votadas por eleitor.

#### Scenario: Senado com duas vagas
- **WHEN** a eleição tem duas vagas de senador
- **THEN** a regra espera soma de votos igual a duas vezes o comparecimento da seção

### Requirement: Unicidade das chaves
O sistema SHALL verificar que não há linhas duplicadas para a chave natural de cada tabela de staging.

#### Scenario: Duplicidade entre arquivos
- **WHEN** o mesmo município e zona aparecem em dois arquivos de origem
- **THEN** a regra de unicidade falha

### Requirement: Integridade referencial e domínios
O sistema SHALL verificar que todo votável nominal tem candidato correspondente, que cargos pertencem ao domínio esperado e que quantidades de votos não são negativas.

#### Scenario: Votos negativos
- **WHEN** uma linha tem quantidade de votos negativa
- **THEN** a regra de domínio falha

### Requirement: Completude mínima
O sistema SHALL verificar que existem dados para todas as 27 UFs e para o município de Itajubá no par (ano, turno) processado, exceto UFs sem 2º turno.

#### Scenario: UF ausente no 1º turno
- **WHEN** uma UF não possui linhas no 1º turno
- **THEN** a regra de completude falha
