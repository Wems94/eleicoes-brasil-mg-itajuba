# Spec Delta

## Purpose

Oferecer a jornalistas e cidadãos um site público, rápido e acessível com os resultados das eleições gerais por UF e um aprofundamento em Itajubá-MG.

## ADDED Requirements

### Requirement: Visão Brasil por UF
O site SHALL exibir, para cada ano e turno disponível, o resultado nacional de Presidente e um mapa das UFs indicando o candidato mais votado em cada uma.

#### Scenario: Seleção de eleição
- **WHEN** o visitante seleciona 2022, 2º turno
- **THEN** a página mostra o resultado nacional e o mapa de UFs daquele turno

### Requirement: Página por UF
O site SHALL ter uma página por UF com resultados de Governador, Senador, Deputado Federal e Deputado Estadual (ou Distrital), comparecimento, abstenção, brancos e nulos.

#### Scenario: Deputados
- **WHEN** o visitante abre a página de MG em 2026
- **THEN** vê os candidatos a deputado mais votados com situação de totalização (eleito, suplente, não eleito) quando disponível

### Requirement: Deep dive Itajubá
O site SHALL ter uma página de Itajubá com resultados por cargo, por zona, por local de votação (com mapa quando houver coordenadas) e por seção, e a comparação histórica entre 2018, 2022 e 2026.

#### Scenario: Consulta de seção
- **WHEN** o visitante busca uma seção eleitoral de Itajubá
- **THEN** vê comparecimento e votos por cargo daquela seção

#### Scenario: Comparação histórica
- **WHEN** o visitante abre a aba de comparação
- **THEN** vê comparecimento e votação por partido nos cargos majoritários em cada ano disponível

### Requirement: Disponibilidade independente do banco
O site SHALL ser servido inteiramente como arquivos estáticos, sem consultas ao banco em tempo de requisição.

#### Scenario: Banco indisponível
- **WHEN** o MotherDuck está fora do ar
- **THEN** todas as páginas do site continuam acessíveis

### Requirement: Transparência e acessibilidade
O site SHALL exibir a fonte (TSE), a data de geração dos dados e uma página de metodologia, e SHALL oferecer tabelas acessíveis como alternativa a todo gráfico.

#### Scenario: Leitor de tela
- **WHEN** um gráfico de resultados é exibido
- **THEN** existe uma tabela equivalente com os mesmos números na página
