# Spec Delta

## Purpose

Identificar candidatos e partidos no site pelas cores com que os partidos são reconhecidos, de forma consistente entre mapa, gráficos e tabelas e sem perder a distinção entre concorrentes.

## ADDED Requirements

### Requirement: Cor por partido
O site SHALL colorir candidatos e partidos pela cor do partido, definida numa paleta única do projeto indexada pela sigla, em todos os mapas e gráficos de resultados. O candidato SHALL usar a cor do seu partido, não a da federação.

#### Scenario: Mesmo partido em telas diferentes
- **WHEN** o PT aparece no mapa municipal, nas barras de Presidente e no resultado de Itajubá
- **THEN** a cor é a mesma nas três telas

### Requirement: Partido sem cor definida
Partidos sem cor na paleta SHALL receber uma cor de reserva determinística, derivada da sigla, distinta das cores neutras usadas para "sem dados" e "empate".

#### Scenario: Partido novo
- **WHEN** um partido criado depois da última atualização da paleta aparece nos resultados
- **THEN** ele recebe uma cor de reserva, sempre a mesma em todas as páginas e builds

### Requirement: Distinção entre concorrentes
Em cada disputa exibida (cargo, eleição e recorte), quando dois partidos presentes tiverem cores próximas demais para distinguir, o site SHALL ajustar a luminosidade da cor do partido com menos votos até que fiquem distinguíveis, mantendo o matiz.

#### Scenario: Dois partidos azuis
- **WHEN** os dois candidatos do 2º turno de uma UF são de partidos com tons de azul próximos
- **THEN** o segundo colocado aparece num azul visivelmente mais claro ou mais escuro, e a legenda mostra as duas cores como estão no mapa

### Requirement: Contraste do texto
Todo texto sobre uma cor partidária SHALL atingir contraste mínimo de 4,5:1, escolhendo texto claro ou escuro conforme a cor de fundo, nos temas claro e escuro.

#### Scenario: Cor clara
- **WHEN** um partido tem cor amarela
- **THEN** o rótulo sobre essa cor é escuro

### Requirement: Informação não depende só da cor
Todo elemento que usa cor partidária SHALL trazer também o nome ou a sigla do partido em texto (na legenda, na dica, no painel ou na tabela).

#### Scenario: Daltonismo
- **WHEN** um visitante não distingue duas cores partidárias
- **THEN** consegue identificar o partido pela legenda, pela dica e pela tabela equivalente
