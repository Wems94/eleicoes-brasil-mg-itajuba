# Spec Delta

## MODIFIED Requirements

### Requirement: Visão Brasil por UF
O site SHALL exibir, para cada ano e turno disponível, o resultado nacional de Presidente e o mapa municipal (capability `mapa-municipal`), que indica o mais votado em cada município e permite aproximar cada UF.

#### Scenario: Seleção de eleição
- **WHEN** o visitante seleciona 2022, 2º turno
- **THEN** a página mostra o resultado nacional e o mapa municipal daquele turno

### Requirement: Deep dive Itajubá
O site SHALL ter uma página de Itajubá com os resultados dos cargos majoritários (Presidente, Governador e Senador), um mapa de votos e um mapa de abstenção, brancos e nulos por bairro e por local de votação, a tabela por zona e a busca por seção. A página MUST NOT exibir os cargos proporcionais nem a comparação histórica, para não poluir a leitura.

#### Scenario: Consulta de seção
- **WHEN** o visitante busca uma seção eleitoral de Itajubá
- **THEN** vê comparecimento e votos por cargo daquela seção

#### Scenario: Comparação histórica
- **WHEN** o visitante abre a página de Itajubá
- **THEN** a página não mostra a comparação entre eleições nem os deputados; as outras eleições ficam no seletor de ano e turno

#### Scenario: Mapa de votos
- **WHEN** o visitante abre o mapa de votos e escolhe Governador, agrupado por bairro
- **THEN** cada bairro aparece como um círculo sobre o mapa de ruas, na cor do partido do mais votado, com a intensidade pela margem e o tamanho pelo número de eleitores, e uma tabela traz os mesmos números

#### Scenario: Abstenção, brancos e nulos
- **WHEN** o visitante escolhe "Nulos", agrupa por local de votação e filtra um local
- **THEN** o mapa destaca e aproxima aquele local, e uma tabela mostra eleitores, abstenção, brancos e nulos de cada seção do local

#### Scenario: Zona única
- **WHEN** o município tem uma única zona eleitoral
- **THEN** o filtro dos mapas é por bairro ou local de votação, e não por zona

## ADDED Requirements

### Requirement: Foto dos candidatos a Presidente
O site SHALL exibir a foto oficial de divulgação do TSE ao lado de cada candidato a Presidente no resultado nacional, no painel do município e no deep dive de Itajubá. Para os demais cargos, o site MUST NOT exibir fotos. Quando a foto não estiver disponível, o site SHALL mostrar as iniciais do candidato no lugar.

#### Scenario: Resultado nacional
- **WHEN** o visitante abre o resultado de Presidente de 2022
- **THEN** cada candidato aparece com a foto oficial, com texto alternativo igual ao nome de urna

#### Scenario: Foto ausente
- **WHEN** o TSE ainda não publicou a foto de um candidato
- **THEN** o site mostra as iniciais do candidato num círculo, na cor do partido

#### Scenario: Governador
- **WHEN** o visitante vê o resultado de Governador
- **THEN** nenhum candidato aparece com foto

### Requirement: Mapa na página da UF
A página de cada UF SHALL exibir o mapa municipal já enquadrado naquela UF, com os mesmos controles de cargo, camada e painel por zona.

#### Scenario: Página de MG
- **WHEN** o visitante abre a página de MG em 2026, 1º turno
- **THEN** vê o mapa dos municípios de MG e pode abrir o painel por zona de qualquer município
