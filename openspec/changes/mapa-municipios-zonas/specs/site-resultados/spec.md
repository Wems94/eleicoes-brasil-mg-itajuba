# Spec Delta

## MODIFIED Requirements

### Requirement: Visão Brasil por UF
O site SHALL exibir, para cada ano e turno disponível, o resultado nacional de Presidente e o mapa municipal (capability `mapa-municipal`), que indica o mais votado em cada município e permite aproximar cada UF.

#### Scenario: Seleção de eleição
- **WHEN** o visitante seleciona 2022, 2º turno
- **THEN** a página mostra o resultado nacional e o mapa municipal daquele turno

## ADDED Requirements

### Requirement: Foto dos candidatos a Presidente
O site SHALL exibir a foto oficial de divulgação do TSE ao lado de cada candidato a Presidente no resultado nacional e no painel do município. Para os demais cargos, o site MUST NOT exibir fotos. Quando a foto não estiver disponível, o site SHALL mostrar as iniciais do candidato no lugar.

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
