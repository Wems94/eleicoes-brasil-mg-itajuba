# Spec Delta

## ADDED Requirements

### Requirement: Municípios com código IBGE
O sistema SHALL verificar que todo município do TSE fora do exterior tem código IBGE único e presente na malha publicada. A verificação SHALL ter severidade erro.

#### Scenario: Município sem correspondência
- **WHEN** um município do TSE não é encontrado na lista do IBGE nem na tabela de exceções
- **THEN** a regra falha listando UF e nome do município, e nada é publicado

#### Scenario: Dois municípios no mesmo código
- **WHEN** dois municípios do TSE recebem o mesmo código IBGE
- **THEN** a regra falha

### Requirement: Soma dos municípios igual à UF
O sistema SHALL verificar, para cada UF e cargo, que a soma dos votos por candidato e do comparecimento nos municípios é igual ao total da UF. SHALL verificar também que a soma das zonas é igual ao total de cada município.

#### Scenario: Divergência entre níveis
- **WHEN** a soma dos municípios de MG para Governador difere do total de MG
- **THEN** a regra falha informando UF, cargo e a diferença
