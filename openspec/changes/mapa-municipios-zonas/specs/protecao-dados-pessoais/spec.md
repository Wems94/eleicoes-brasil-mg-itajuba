# Spec Delta

## ADDED Requirements

### Requirement: Fotos só de candidatos a Presidente
O sistema MUST NOT armazenar no repositório ou publicar fotos de candidatos que não concorram a Presidente. O pacote bruto de fotos SHALL ficar apenas no armazenamento local ou no cache efêmero do CI, como os demais arquivos brutos.

#### Scenario: Pacote com todas as fotos
- **WHEN** o pacote de fotos do TSE contém fotos de candidatos a deputado
- **THEN** nenhuma delas aparece nos snapshots, em `web/` ou no banco oficial

### Requirement: Verificação das fotos publicadas
A verificação automática de LGPD SHALL falhar se alguma foto publicada não corresponder a um candidato a Presidente da eleição indicada no nome do arquivo.

#### Scenario: Foto indevida
- **WHEN** uma alteração publica a foto de um candidato a Governador
- **THEN** a verificação falha e a publicação é bloqueada
