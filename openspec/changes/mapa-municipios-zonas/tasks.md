# Tasks

## 1. Fontes novas (ingestão)

- [x] 1.1 Adicionar a fonte `votacao_partido_munzona` (obrigatória) em `config/fontes.yaml`, com a tabela de staging correspondente em `esquema.py` e `staging.py` e o CSV de fixture em `tests/fixtures/gerar_tse.py`. Verificar: `uv run pytest` passa com o staging da nova tabela preenchido para 2018 e 2022.
- [x] 1.2 Adicionar as fontes do IBGE (lista de municípios e malha municipal por UF em TopoJSON, `qualidade=minima`) ao download, com manifest e sha256 e com obrigatoriedade. Verificar: teste com `tests/servidor_http.py` servindo as respostas de fixture do IBGE, sem baixar de novo na segunda execução e com falha explícita quando o serviço responde 503.
- [x] 1.3 Adicionar a fonte opcional `foto_cand{ano}_BR_div.zip`. Disparar `validacao-real.yml` na branch para confirmar, com dados reais, a URL das fotos, o padrão dos nomes internos e os nomes das colunas de `votacao_partido_munzona` em cada ano. Ajustar aliases e padrões. Verificar: o log da execução mostra as três fontes lidas nos três anos.

## 2. Correspondência TSE ↔ IBGE

- [x] 2.1 Implementar o mart `municipio_ibge`, que casa (UF, nome normalizado) com a lista do IBGE e aplica `config/municipios_excecoes.yaml`, sem incluir o exterior. Verificar: testes cobrem um nome com acento, um caso resolvido por exceção e o exterior (ZZ) ignorado.
- [x] 2.2 Adicionar ao gate as regras "município sem código IBGE", "código IBGE duplicado" e "código fora da malha", todas com severidade erro. Verificar: testes de `qualidade.py` com um município sem correspondência fazem o gate falhar listando UF e nome.
- [x] 2.3 Rodar `validacao-real.yml` e completar `municipios_excecoes.yaml` até não sobrar município sem código em 2018, 2022 e 2026. Verificar: relatório do gate sem erros dessas regras.

## 3. Marts por município e zona

- [x] 3.1 Implementar os marts `resultado_municipio`, `resultado_zona`, `comparecimento_municipio` e `comparecimento_zona` para todos os cargos (com a mesma base de válidos de `resultado_uf`). Verificar: testes com a fixture conferem votos, percentuais e posição num município com duas zonas.
- [x] 3.2 Implementar `partido_municipio` e `partido_zona` (nominais mais legenda) para os cargos 6, 7 e 8. Verificar: teste em que o partido mais votado difere do partido do candidato mais votado.
- [x] 3.3 Adicionar as regras de qualidade "soma dos municípios igual à UF" e "soma das zonas igual ao município" (votos e comparecimento). Verificar: teste que adultera uma zona faz a regra falhar informando UF, cargo e diferença.
- [x] 3.4 Atualizar a spec de modelos em `pipeline/README.md` com os novos marts. Verificar: as tabelas listadas no README batem com `TABELAS_MARTS`.

## 4. Geometria

- [x] 4.1 Implementar a montagem do TopoJSON nacional: juntar as malhas das UFs, manter só o código IBGE e o nome nas propriedades, quantizar e, se preciso, simplificar com preservação de topologia (dependência `topojson` só se necessária). Verificar: teste com a malha de fixture e um teste de orçamento que falha se o arquivo comprimido passar de 1,2 MB com dados reais (marcado para rodar no `validacao-real.yml`).

## 5. Fotos e LGPD

- [x] 5.1 Extrair do pacote só as fotos dos candidatos a Presidente do ano (por `sq_candidato`) e reduzi-las a 160×200 JPEG com Pillow. Verificar: teste com um ZIP de fixture contendo fotos de presidente e de deputado; só as de presidente saem.
- [x] 5.2 Estender `lgpd.py` para falhar se alguma foto publicada não for de um presidenciável do ano indicado no caminho. Verificar: teste com uma foto indevida faz o verificador falhar, e o `ci.yml` continua chamando o verificador sobre `web/data`.

## 6. Snapshots (schema 2)

- [x] 6.1 Gerar `{ano}/{turno}/mapa/{cargo}.json` no formato compacto do design (M4), incluindo empate (-1), o partido para Deputado, o Distrital dentro de `deputado-estadual` e o exterior à parte. Verificar: testes de `snapshots.py` sobre a fixture e um teste de determinismo (duas gerações, mesmos bytes).
- [x] 6.2 Gerar `{ano}/{turno}/municipios/{UF}/{cargo}.json`, com total e zonas, `outros_municipios` e o top 10 de candidatos nos proporcionais. Verificar: teste de uma zona que atende dois municípios.
- [x] 6.3 Publicar `geo/municipios.topo.json` e `fotos/{ano}/{sq}.jpg` na troca atômica, adicionar `foto` aos candidatos de `brasil.json` e `ibge` ao `municipio` do manifesto, e subir `SCHEMA_VERSAO` para 2. Verificar: o teste de falha no meio da geração continua deixando o diretório anterior intacto, e `pnpm fixture` gera todos os arquivos novos.
- [x] 6.4 Atualizar o docstring do contrato em `snapshots.py` e o `pipeline/README.md`. Verificar: a lista de arquivos do docstring bate com o que `pnpm fixture` gera.

## 7. Cores partidárias (site)

- [x] 7.1 Criar `web/lib/partidos.ts` com a paleta sigla → cor (2018 a 2026), a cor de reserva por hash em OKLCH, a distinção por ΔE em OKLab, as faixas de intensidade, a escala de abstenção e a escolha de texto por contraste. Verificar: testes Vitest cobrindo dois azuis próximos sendo afastados, a reserva determinística, o contraste ≥ 4,5:1 e as faixas.
- [x] 7.2 Trocar `coresPorEntidade` pelo novo módulo em `BarrasTabela`, `BrasilVisao`, na página da UF e em Itajubá, e remover as variáveis `--color-serie-*`. Verificar: `pnpm typecheck && pnpm test`, e a inspeção visual em `pnpm build:fixture` mostra as cores partidárias nos dois temas.

## 8. Mapa municipal (site)

- [x] 8.1 Ler o schema 2 em `lib/tipos.ts` e `lib/dados.ts` e criar as rotas `force-static` em `app/dados/` para a geometria, as camadas, os detalhes por UF e cargo e as fotos. Verificar: `pnpm build:fixture` gera esses arquivos em `out/dados/`, e o build com schema 1 falha com a mensagem que manda rodar o ETL.
- [x] 8.2 Criar o componente client-only do mapa (MapLibre sem mapa de base) com a malha, os limites das UFs gerados por `topojson-client`, as camadas "Mais votado" e "Abstenção", o seletor de cargo (só os cargos com dados no turno), a legenda e a dica ao passar o cursor. Verificar: no build de fixture, trocar o cargo e a camada recolore o mapa sem novo download da geometria (aba Rede).
- [x] 8.3 Implementar a navegação Brasil → UF (enquadrar, voltar, zoom, tela cheia) e o estado no hash da URL. Verificar: abrir um link com `#cargo=senador&camada=abstencao&uf=MG&mun=<código de Itajubá>` restaura o estado.
- [x] 8.4 Implementar o painel do município com total e zonas (candidatos, ou partidos mais top 10 nos proporcionais), comparecimento, o aviso de zona compartilhada e o link para Itajubá, carregando o detalhe sob demanda com cache por UF e cargo. Verificar: na aba Rede, só o primeiro clique numa UF baixa o arquivo, e o layout funciona no celular (folha inferior).
- [x] 8.5 Implementar a tabela equivalente (por UF e, com uma UF aberta, por município) com busca que abre o mesmo painel, e o bloco do exterior. Verificar: navegação só por teclado encontra um município e lê o painel.
- [x] 8.6 Trocar `MapaUfs` pelo mapa na `BrasilVisao` e incluí-lo na página da UF já enquadrado. Remover `MapaUfs.tsx`. Verificar: `pnpm build:fixture` sem erros, as duas páginas mostram o mapa, e a página de metodologia explica a malha do IBGE, a correspondência de códigos e por que a zona não aparece desenhada.

## 9. Fotos no site

- [x] 9.1 Mostrar a foto (ou as iniciais na cor do partido) ao lado dos candidatos a Presidente no resultado nacional e no painel, com `alt` igual ao nome de urna, e nenhuma foto nos outros cargos. Verificar: no build de fixture, uma foto presente e uma ausente aparecem corretamente.

## 10. Workflow e integração

- [x] 10.1 Adicionar o input `base` (padrão `main`) ao `etl.yml` e usá-lo no `checkout` e no `base` do PR de snapshots. Documentar no README. Verificar: a revisão do YAML com `actionlint`, se disponível, e a execução da tarefa 10.2.
- [x] 10.2 Com o usuário: disparar `etl.yml` a partir de `feat/mapa-municipal` com `base=feat/mapa-municipal` e fazer merge do PR de snapshots na branch. Verificar: o PR contém só `web/data`, com o schema 2 e os arquivos novos, e o tamanho dos detalhes de SP e MG fica registrado na descrição do PR. Registro: PR #2 mesclado em 2026-10-13; `web/data` com 140 MB; maior detalhe MG Deputado Estadual 1,6 MB (cerca de 230 KB com gzip), SP 1,3 MB.
- [ ] 10.3 Verificação integrada no preview: visão Brasil com os 5.570 municípios nos cinco cargos e nas duas camadas, painel por zona de Belo Horizonte e de Itajubá, fotos dos presidenciáveis, temas claro e escuro, celular, e payload inicial (geometria mais camada) dentro do orçamento. Verificar: checklist anotado no PR da feature.

## 11. Ajustes do deep dive de Itajubá (pedido de 2026-10-13)

- [x] 11.1 Tirar da página de Itajubá os deputados e a comparação histórica, e mostrar as fotos dos presidenciáveis no card de Presidente. Verificar: `pnpm typecheck && pnpm test` e inspeção no build com dados reais.
- [x] 11.2 Mapa de votos por bairro ou local de votação (círculos sobre o mapa de ruas, cor do partido do mais votado, tamanho pelo eleitorado), ao lado do card de Presidente, com Governador e Senador lado a lado. Verificar: inspeção no build com dados reais (35 locais, 29 bairros).
- [x] 11.3 Mapa de abstenção, brancos e nulos com alternância bairro/local, filtro e tabela por seção. Verificar: teste de `lib/itajubaMapa.ts` (somas por local e bairro, bases das taxas) e inspeção no build.

## Workflow follow-up

- O usuário faz os commits e abre o PR de `feat/mapa-municipal` para a `main`. O merge dispara o deploy.
- Depois do deploy, arquivar o change com `/opsx:archive` e atualizar a D8 do design arquivado por referência (cores partidárias e mapa com geometria).
