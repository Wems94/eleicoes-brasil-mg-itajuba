# Spec Delta

## Purpose

Mostrar no site, num mapa coroplético de municípios, quem venceu e quanto se absteve em cada lugar do Brasil, por cargo, com aprofundamento até a zona eleitoral de cada município.

## ADDED Requirements

### Requirement: Mapa coroplético por município
O site SHALL exibir um mapa com todos os municípios do Brasil desenhados pela geometria oficial do IBGE, com os limites das UFs destacados, para cada ano e turno disponível.

#### Scenario: Visão inicial
- **WHEN** o visitante abre a página de 2022, 2º turno
- **THEN** o mapa mostra todos os municípios do Brasil coloridos e os limites das 27 UFs

#### Scenario: Município sem dados
- **WHEN** um município não tem resultado para o cargo e turno selecionados (por exemplo, Governador no 2º turno numa UF sem 2º turno)
- **THEN** o município aparece numa cor neutra identificada na legenda como "sem disputa neste turno"

### Requirement: Seletor de cargo
O mapa SHALL oferecer um seletor com os cargos Presidente, Governador, Senador, Deputado Federal e Deputado Estadual (Distrital no DF), mostrando apenas os cargos com dados no turno selecionado.

#### Scenario: Troca de cargo
- **WHEN** o visitante seleciona Governador no 1º turno de 2026
- **THEN** cada município passa a mostrar o resultado de Governador da sua UF, sem recarregar a página

#### Scenario: 2º turno
- **WHEN** o turno selecionado é o 2º
- **THEN** o seletor oferece apenas Presidente e Governador

### Requirement: Camada de mais votado
Na camada "Mais votado", cada município SHALL ter a cor do partido do candidato mais votado. Para Deputado, a cor SHALL ser a do partido com mais votos válidos (nominais mais legenda). A intensidade SHALL crescer com o percentual de votos válidos do vencedor, em faixas mostradas na legenda.

#### Scenario: Presidente
- **WHEN** o cargo é Presidente e um candidato do PT tem 62% dos válidos num município
- **THEN** o município aparece na cor do PT, na faixa de intensidade de 60% a 70%

#### Scenario: Deputado por partido
- **WHEN** o cargo é Deputado Federal e o partido com mais votos nominais e de legenda num município é o PL
- **THEN** o município aparece na cor do PL, mesmo que o deputado individualmente mais votado ali seja de outro partido

#### Scenario: Empate
- **WHEN** dois votáveis empatam em primeiro lugar num município
- **THEN** o município aparece na cor neutra de empate, indicada na legenda

### Requirement: Camada de abstenção
O mapa SHALL oferecer uma camada "Abstenção" que colore cada município pelo percentual de abstenção sobre os aptos do cargo selecionado, numa escala sequencial de uma única cor, em faixas mostradas na legenda.

#### Scenario: Alternar camada
- **WHEN** o visitante troca de "Mais votado" para "Abstenção"
- **THEN** o mapa passa a mostrar a escala de abstenção e a legenda passa a mostrar as faixas de percentual

### Requirement: Navegação Brasil, UF e município
O mapa SHALL permitir aproximar uma UF ao clicar nela na visão Brasil, voltar à visão Brasil, e SHALL oferecer zoom e enquadramento total por botões. O estado do mapa (cargo, camada, UF e município) SHALL ficar na URL, para ser compartilhável.

#### Scenario: Abrir UF
- **WHEN** o visitante clica em Minas Gerais na visão Brasil
- **THEN** o mapa enquadra MG, destaca seus municípios e mostra um controle para voltar ao Brasil

#### Scenario: Link compartilhado
- **WHEN** alguém abre um link com cargo Senador, camada Abstenção e município Itajubá
- **THEN** o mapa abre nesse cargo, nessa camada, enquadrado em MG e com o painel de Itajubá aberto

### Requirement: Dica ao passar o cursor
O mapa SHALL mostrar, ao passar o cursor ou tocar num município, o nome do município, a UF, o vencedor com partido e percentual (ou a abstenção, na camada de abstenção).

#### Scenario: Hover
- **WHEN** o visitante passa o cursor sobre um município
- **THEN** uma dica mostra o nome, a UF e o dado da camada ativa

### Requirement: Painel do município por zona eleitoral
Ao clicar num município, o site SHALL abrir um painel com o resultado do cargo selecionado no município (votos e percentual por candidato, ou por partido para Deputado, e comparecimento, abstenção, brancos e nulos) e o mesmo detalhamento para cada zona eleitoral do município.

#### Scenario: Município com várias zonas
- **WHEN** o visitante clica em Belo Horizonte com o cargo Presidente
- **THEN** o painel mostra o total de Belo Horizonte e uma seção por zona eleitoral, cada uma com votos por candidato, aptos, comparecimento, abstenção, brancos e nulos

#### Scenario: Zona que abrange vários municípios
- **WHEN** uma zona eleitoral atende a mais de um município
- **THEN** o painel mostra só os números daquela zona dentro do município clicado e informa que a zona também atende outros municípios

#### Scenario: Deputado no painel
- **WHEN** o cargo é Deputado Estadual
- **THEN** o painel mostra os votos por partido e os candidatos mais votados no município e em cada zona

#### Scenario: Itajubá
- **WHEN** o município do painel é Itajubá
- **THEN** o painel oferece um link para o deep dive de Itajubá

### Requirement: Carregamento sob demanda
O site SHALL carregar a geometria e os dados da camada do mapa uma vez por eleição e cargo, e SHALL carregar o detalhamento por zona só quando o visitante abrir um município da UF correspondente.

#### Scenario: Primeiro clique numa UF
- **WHEN** o visitante abre o painel de um município de SP pela primeira vez
- **THEN** o site baixa apenas o detalhe de SP para o cargo selecionado, e cliques seguintes em SP não repetem o download

### Requirement: Alternativa acessível ao mapa
O mapa SHALL ter legenda textual e uma tabela equivalente, com o vencedor (ou a abstenção) por UF e, ao abrir uma UF, por município, com busca por nome de município que abre o mesmo painel.

#### Scenario: Leitor de tela
- **WHEN** um visitante navega pelo teclado ou leitor de tela
- **THEN** consegue achar um município pela busca da tabela e ler o mesmo painel por zona, sem usar o mapa

### Requirement: Votos do exterior
O mapa SHALL informar à parte o resultado do exterior (ZZ), que não tem geometria, para Presidente.

#### Scenario: Exterior
- **WHEN** o cargo é Presidente
- **THEN** abaixo do mapa aparece o vencedor e a abstenção no exterior
