# publicacao-dados Specification

## Purpose

Disponibilizar os dados validados no banco analítico oficial e como snapshots estáticos versionados que alimentam o site público.

## Requirements

### Requirement: Carga no banco oficial
O sistema SHALL substituir o banco oficial no MotherDuck pelo banco local validado quando houver token configurado, e SHALL pular essa etapa com aviso quando não houver.

#### Scenario: Execução local sem token
- **WHEN** o pipeline roda sem a variável de token do MotherDuck
- **THEN** o banco local é gerado, a carga remota é pulada com aviso e os snapshots são gerados normalmente

### Requirement: Snapshots atômicos
O sistema SHALL gerar os snapshots num diretório temporário e só substituir o diretório publicado depois que todos os arquivos forem gerados com sucesso.

#### Scenario: Falha no meio da geração
- **WHEN** a geração de um snapshot falha
- **THEN** o diretório publicado permanece idêntico ao anterior

### Requirement: Manifesto de snapshots
O sistema SHALL publicar um manifesto com a lista de eleições e turnos disponíveis, a data de geração, a versão do schema e o sha256 de cada arquivo de origem usado.

#### Scenario: Site lê o manifesto
- **WHEN** o site é construído
- **THEN** ele oferece apenas os anos e turnos presentes no manifesto

### Requirement: Publicação revisável
O sistema SHALL, quando executado no CI, propor os novos snapshots por Pull Request, e não por commit direto na branch principal.

#### Scenario: Carga do 2º turno
- **WHEN** o workflow de ETL é disparado para 2026, turno 2
- **THEN** um Pull Request com os snapshots atualizados é aberto e o deploy só ocorre após o merge
