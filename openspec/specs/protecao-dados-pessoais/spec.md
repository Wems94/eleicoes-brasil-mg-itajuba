# protecao-dados-pessoais Specification

## Purpose

Cumprir a LGPD garantindo que dados pessoais de candidatos desnecessários à finalidade jornalística não sejam armazenados nas camadas derivadas nem publicados.

## Requirements

### Requirement: Campos pessoais proibidos
O sistema MUST NOT gravar em staging, marts, banco oficial ou snapshots os campos de CPF, e-mail, título de eleitor e data de nascimento de candidatos.

#### Scenario: Arquivo de candidatos com CPF
- **WHEN** o arquivo de candidatos do TSE contém a coluna de CPF
- **THEN** nenhuma tabela derivada e nenhum snapshot contém essa coluna nem valores com padrão de CPF

### Requirement: Verificação automática
O sistema SHALL executar, em toda execução do pipeline e em todo CI, uma verificação que falha se nomes de colunas proibidas ou valores com padrão de CPF ou e-mail aparecerem nos dados derivados ou nos snapshots.

#### Scenario: Vazamento introduzido por mudança de código
- **WHEN** uma alteração adiciona a coluna de e-mail a uma tabela derivada
- **THEN** a verificação falha e a publicação é bloqueada

### Requirement: Arquivos brutos fora do versionamento
O sistema SHALL manter os arquivos brutos do TSE apenas no armazenamento local ou no cache efêmero do CI, nunca no repositório Git nem no banco oficial.

#### Scenario: Commit acidental
- **WHEN** alguém tenta adicionar arquivos de `data/raw` ao Git
- **THEN** o arquivo é ignorado pelas regras de exclusão do repositório
