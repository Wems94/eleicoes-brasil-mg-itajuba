# Proposal

## Why

O mapa atual da visão Brasil é um tile grid com um quadrado por UF, que só mostra o vencedor de Presidente em cada estado. Ele não deixa ver a votação dentro dos estados, não cobre os outros cargos e não mostra abstenção. O usuário quer um mapa coroplético por município, como os mapas eleitorais da imprensa, com filtro de cargo, cores dos partidos e um aprofundamento por zona eleitoral e por abstenção. O pipeline já carrega no staging os dados por município e zona (`votacao_munzona` e `detalhe_munzona`), então a informação existe. Hoje ela só é agregada por UF.

## What Changes

- **BREAKING (site):** o tile map de UFs (`MapaUfs`) é substituído por um mapa coroplético dos 5.570 municípios, desenhado com a geometria oficial do IBGE e o MapLibre que o projeto já usa.
- Filtro de cargo no mapa: Presidente, Governador, Senador, Deputado Federal e Deputado Estadual (Distrital no DF).
- **BREAKING (regra de design D8):** as cores passam a ser as **cores dos partidos**. Antes, o site usava cores neutras atribuídas pela ordem de votação. Quando dois partidos da mesma disputa têm cores próximas, uma delas é ajustada para os dois continuarem distinguíveis. A regra vale para o mapa e também para as barras de resultado do site.
- Camada "Mais votado": o município fica com a cor do partido do candidato mais votado, mais forte quanto maior a % dele. Para Deputado, a cor é a do **partido** mais votado no município (votos nominais mais legenda).
- Camada "Abstenção": mapa de calor da abstenção por município, numa escala sequencial de uma cor só.
- Navegação em três níveis: a visão Brasil mostra todos os municípios; clicar numa UF aproxima o mapa dela; clicar num município abre um **painel** com o total do município e cada **zona eleitoral** (votos por candidato ou partido, aptos, comparecimento, abstenção, brancos e nulos). O TSE não publica polígonos de zona, por isso a zona aparece no painel e não no mapa.
- Fotos oficiais de divulgação do TSE **só para os candidatos a Presidente**, no resultado nacional e no painel.
- Pipeline:
  - marts por município e por município × zona, para todos os cargos;
  - correspondência entre o código de município do TSE e o do IBGE;
  - geometria municipal simplificada, gerada a partir da malha do IBGE;
  - nova fonte do TSE com a votação por partido, município e zona, necessária para somar os votos de legenda por partido nos cargos de Deputado;
  - download das fotos dos presidenciáveis.
- **BREAKING (contrato dos snapshots):** o contrato passa para `schema_versao` 2, com arquivos novos por eleição (camada do mapa por cargo e detalhe por UF × cargo, carregado sob demanda). Os arquivos atuais continuam iguais.

## Capabilities

### New Capabilities
- `mapa-municipal`: o mapa coroplético por município do site, com seletor de cargo, camadas de mais votado e de abstenção, navegação Brasil → UF → município, painel por zona eleitoral, legenda e tabela equivalente.
- `cores-partidarias`: a atribuição de cores por partido em todo o site, com paleta, cor de reserva para partido sem cor definida, regra de distinção entre partidos da mesma disputa e contraste do texto sobre a cor.

### Modified Capabilities
- `site-resultados`:
  - "Visão Brasil por UF" passa a usar o mapa municipal no lugar do mapa de UFs;
  - o resultado de Presidente ganha as fotos dos candidatos.
- `transformacao-dados`:
  - "Modelos analíticos" ganha resultado e comparecimento por município e por município × zona;
  - nova correspondência entre os códigos de município do TSE e do IBGE.
- `ingestao-tse`:
  - novas fontes: a malha municipal e a lista de municípios do IBGE, e as fotos de candidatos do TSE;
  - as fotos são opcionais.
- `publicacao-dados`:
  - o manifesto passa ao schema 2;
  - novos snapshots: camada do mapa, detalhe por município e zona, geometria e fotos.
- `qualidade-dados`:
  - o gate de publicação passa a exigir que todo município do TSE tenha código IBGE;
  - também exige que a soma dos municípios bata com o total da UF.
- `protecao-dados-pessoais`:
  - a foto de candidato só pode ser publicada para Presidente;
  - a verificação automática confere isso.

## Impact

- **Pipeline** (`pipeline/src/eleicoes/`):
  - `marts.py`: novos marts;
  - `snapshots.py`: novos arquivos e schema 2;
  - `qualidade.py` e `lgpd.py`: novas verificações;
  - `fontes.py`, `download.py` e `config/fontes.yaml`: fontes do IBGE e fotos;
  - novo módulo de geometria e de códigos IBGE.
  - Dependências possíveis: Pillow, para reduzir as fotos, e uma lib de simplificação de geometria, se a malha do IBGE na qualidade mínima não bastar.
- **Site** (`web/`):
  - novo componente de mapa municipal no lugar de `components/MapaUfs.tsx`;
  - `lib/cores.ts` e `app/globals.css` passam a usar a paleta partidária, o que afeta `BarrasTabela`, `BrasilVisao`, a página da UF e Itajubá;
  - `lib/tipos.ts` e `lib/dados.ts` aceitam o schema 2;
  - novas rotas estáticas sob `app/dados/` para os arquivos carregados sob demanda.
- **Dados publicados:** o tamanho de `web/data/` cresce. A geometria e as fotos ficam em `web/public/`. Os snapshots precisam ser regenerados pelo workflow ETL no GitHub Actions; nada é processado com dados reais localmente.
- **Specs e design:** reverte a parte da D8 que fala do "tile-grid map sem geometria" e de "nenhuma cor partidária".
- **Workflow `etl.yml`:** ganha a opção de abrir o PR de snapshots contra outra branch além da `main`. Assim, o código novo e os dados no schema 2 chegam juntos à `main` (ver a seção de migração no design.md).
- **Sem impacto:** banco no MotherDuck (só tabelas novas nos marts) e páginas de Itajubá (exceto as cores).
