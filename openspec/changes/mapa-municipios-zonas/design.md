# Design

## Context

- **Staging.** `staging.votacao_munzona` (votos por candidato) e `staging.detalhe_munzona` (aptos, comparecimento, abstenções, brancos e nulos) já guardam cada linha com `sg_uf`, `cd_municipio` (código **TSE**), `nm_municipio` e `nr_zona`, para todos os cargos e todas as UFs. Hoje os marts agregam isso só até a UF (`marts.resultado_uf`, `marts.comparecimento_uf`).
- **Site.** É exportação estática (D8): Next.js lê os snapshots em `web/data` no build. Os arquivos carregados sob demanda são servidos por rotas `force-static` em `web/app/dados/...`, como a lista de deputados. O MapLibre já é dependência (mapa de locais de Itajubá).
- **Cores.** Vêm de `web/lib/cores.ts`: 3 séries neutras mais "outros", atribuídas pela ordem de votação, com paleta validada para daltonismo em `globals.css`. Essa regra está sendo revogada (ver proposal.md).
- **Restrições do usuário.** Os dados reais só são processados no GitHub Actions (`etl.yml`). O usuário faz todos os commits. O ETL abre um PR que só contém `web/data`, sempre a partir da `main`.

## Goals / Non-Goals

**Goals:**
- A visão Brasil inteira (5.570 municípios) com payload inicial pequeno: geometria mais uma camada, perto de 1,5 MB comprimido no total.
- Trocar de cargo ou de camada sem recarregar a página nem baixar a geometria de novo.
- O detalhe por zona só vem quando alguém abre um município, e uma UF por vez.
- Uma única fonte de cores por partido para o site todo.

**Non-Goals:**
- Desenhar as zonas eleitorais no mapa. O TSE não publica polígonos de zona, e aproximações (como Voronoi dos locais de votação) seriam enganosas.
- Mapa de fundo com ruas ou relevo na visão nacional. O mapa é só a malha, como na referência.
- Comparar eleições no mapa (swing entre 2018, 2022 e 2026). Pode vir depois.
- Fotos de candidatos de outros cargos.

## Decisions

### M1. Código IBGE por correspondência de nome, com exceções versionadas
O TSE usa um código próprio de município, e a malha do IBGE usa o código de 7 dígitos.

**Decisão:** baixar a lista oficial do IBGE (API de localidades), normalizar os nomes (sem acento, maiúsculas, sem apóstrofo nem hífen) e casar por (UF, nome). Os casos que não casam vão para `pipeline/config/municipios_excecoes.yaml`, no formato `(UF, nome TSE) -> código IBGE`, versionado e revisado à mão. O gate (`qualidade-dados`) falha se sobrar município sem código.

**Alternativas:**
- Tabelas de terceiros com a correspondência TSE↔IBGE: têm origem não oficial e ficariam sem manutenção no repositório.
- Casar pelos locais de votação com lat/lon: só cobre MG no staging atual.

### M2. Geometria do IBGE em TopoJSON, publicada com os snapshots
**Decisão:**
- **Download:** baixar do IBGE (API de malhas v3, `qualidade=minima`) a malha municipal do Brasil inteiro, numa única requisição em TopoJSON já quantizado, e publicar em `web/data/geo/municipios.topo.json`, com o código IBGE como `id` e o nome e a UF de cada município nas propriedades.
- **Limites das UFs:** o site gera os limites com `topojson-client` (`mesh` entre municípios de UFs diferentes), sem arquivo extra.
- **Sem simplificação:** a malha do IBGE na qualidade mínima já vem quantizada. Medida em out/2026, depois de receber nome e UF, ficou em 1,57 MB, ou 445 KB com gzip: dentro do orçamento de 1,2 MB comprimido. O `validar_real.py` confere o orçamento a cada execução. Se um dia passar, a simplificação com preservação de topologia entra nesse ponto.
- **Publicação:** a geometria entra no manifesto (sha256) e na troca atômica dos snapshots. O PR do ETL continua tocando só `web/data`.

**Alternativas:**
- Vector tiles (PMTiles): melhor em zoom alto, mas exige ferramenta de geração (tippecanoe) e servidor com suporte a range requests. Exagero para 5.570 polígonos.
- GeoJSON puro: de 3 a 5 vezes maior que o TopoJSON quantizado.
- Commitar a malha manualmente em `web/public`: ficaria fora do controle de origem (sha256) e da trava de LGPD e qualidade.

### M3. Marts por município e por zona
Novos marts em `marts.py`, todos derivados do staging munzona, para todos os cargos:

| Mart | Conteúdo |
|---|---|
| `municipio_ibge` | `(sg_uf, cd_municipio) -> cd_ibge, nm_municipio`; o exterior fica de fora |
| `resultado_municipio` | votos e `pct_validos` por candidato e posição, por (ano, turno, município, cargo) |
| `resultado_zona` | o mesmo, por (ano, turno, município, zona, cargo) |
| `partido_municipio` / `partido_zona` | votos nominais mais legenda por partido nos cargos 6, 7 e 8 |
| `comparecimento_municipio` / `comparecimento_zona` | aptos, comparecimento, abstenções, brancos, nulos e percentuais |

- **Base de válidos:** é a mesma de `resultado_uf`, ou seja, `qt_votos_validos` de `detalhe_munzona`.
- **Votos de legenda por partido:** `votacao_munzona` só tem votos nominais por candidato, e `detalhe_munzona` só tem a legenda total, sem dividir por partido. Por isso entra uma fonte nova e obrigatória: `votacao_partido_munzona_{ano}.zip` (votos nominais e de legenda por partido, município e zona), com nova tabela de staging `votacao_partido_munzona`. Os nomes das colunas por ano são conferidos com dados reais na tarefa 1.3.

### M4. Contrato dos snapshots, schema 2
Novos arquivos, todos em `web/data`:

```
geo/municipios.topo.json                      malha (M2), uma só para todas as eleições
{ano}/{turno}/mapa/{cargo}.json               camada: 1 entrada por município
{ano}/{turno}/municipios/{UF}/{cargo}.json    detalhe por município e zona (sob demanda)
fotos/{ano}/{sq_candidato}.jpg                fotos dos presidenciáveis (M7)
```

- **`{cargo}`:** é um slug: `presidente`, `governador`, `senador`, `deputado-federal` ou `deputado-estadual`. O slug `deputado-estadual` inclui o Distrital do DF (cargo 8), para o filtro ter uma opção só.
- **Formato da camada:** é compacto, com dicionários e arrays em vez de objetos repetidos:
  ```json
  {"votaveis": [{"chave": "13", "nome": "LULA", "partido": "PT"}, ...],
   "municipios": {"3132404": [0, 5321, 2214]}}
  ```
  O array do município é `[índice do votável vencedor ou -1 para empate, pct×100, abstenção×100]`, em inteiros. Para Deputado, o votável é o partido (`chave` = sigla). O exterior vai num campo `exterior` à parte, mesmo formato.
- **Formato do detalhe:** por código IBGE, traz `total` e `zonas[]`. Cada um tem o comparecimento completo e os votáveis (todos os candidatos nos majoritários; nos proporcionais, todos os partidos mais os 10 candidatos mais votados).
- **Zonas compartilhadas:** cada zona marca `outros_municipios: n` quando atende mais de um município.
- **`brasil.json`:** cada candidato ganha `foto` (caminho relativo ou `null`).
- **`manifest.json`:** `municipio` ganha `ibge`.
- **Versão:** `schema_versao` passa a 2. Os arquivos atuais não mudam de formato, mas o site passa a depender dos novos, por isso a versão sobe.
- **Exposição no site:** os novos arquivos chegam ao navegador por rotas `force-static` em `web/app/dados/[...]`, que leem de `web/data` no build, no mesmo padrão dos deputados. As fotos também passam por uma rota que devolve os bytes com `Content-Type: image/jpeg`. Assim tudo continua vindo de um único diretório versionado, sem cópia para `public/`.

**Alternativa:** um arquivo por (UF, cargo) também para a camada, mas a visão Brasil precisaria de 27 requisições.

### M5. Renderização: MapLibre sem mapa de base, cor calculada no cliente
**Decisão:**
- **Fonte e camadas:** uma fonte GeoJSON (TopoJSON convertido uma vez), com `fill` para os municípios, `line` fina para os limites municipais (só a partir de certo zoom) e `line` mais grossa para os limites das UFs.
- **Cor:** a cor de cada feature é calculada em JS (M6) e gravada como propriedade `cor`. A troca de cargo ou de camada recalcula as propriedades e chama `setData`. O estilo usa `["get", "cor"]`.
- **Destaque:** hover e seleção usam `feature-state` com `promoteId` igual ao código IBGE.
- **Código no cliente:** o mapa é um componente client-only (`dynamic(..., { ssr: false })`), como o `MapaLocais`.
- **Estado:** fica no hash da URL (`#cargo=senador&camada=abstencao&uf=MG&mun=3132404`). O export estático não tem servidor para query string, e o hash evita o Suspense de `useSearchParams`.
- **Painel:** à direita no desktop e como folha inferior no celular, com a tabela de cada zona em `<details>`.
- **Página da UF:** usa o mesmo componente com `uf` inicial e `maxBounds` na UF.

**Alternativas:**
- Expressão `match` gigante no estilo, com 5.570 pares código → cor, a cada troca. Funciona, mas é mais lenta de compilar que um `setData`.
- SVG com d3-geo: mais simples, mas 5.570 caminhos com hover e zoom ficam pesados no celular.

### M6. Cores partidárias
**Decisão:**
- **Paleta:** `web/lib/partidos.ts` define a paleta `sigla -> cor base`, cobrindo todos os partidos de 2018 a 2026. As siglas antigas e renomeadas (PMDB/MDB, PR/PL, PRB/REPUBLICANOS, PPS/CIDADANIA, PTN/PODE, DEM e PSL/UNIÃO, PTB e PATRIOTA/PRD, PROS, PSC...) são mapeadas pela sigla que aparece em cada ano, sem fundir partidos. As cores seguem as convenções da imprensa e da identidade de cada partido.
- **Reserva:** é um matiz derivado de um hash da sigla em OKLCH, com luminosidade e croma fixos, longe dos cinzas.
- **Distinção:** para cada disputa exibida, os partidos são ordenados por votos. Se a distância ΔE (OKLab) entre um partido e um anterior ficar abaixo de um limiar, a luminosidade do partido com menos votos é ajustada em passos até passar do limiar. O matiz não muda. Na visão nacional dos cargos estaduais, a disputa é a UF: os partidos em UFs diferentes podem ter cores parecidas sem problema.
- **Intensidade:** a cor base é misturada com a cor de superfície em OKLab, em 4 faixas: < 50%, 50–60%, 60–70% e ≥ 70%.
- **Abstenção:** escala sequencial de um matiz com faixas fixas (< 15%, 15–20%, 20–25%, 25–30% e ≥ 30%), para comparar entre anos.
- **Texto:** a cor do texto é escolhida pelo maior contraste WCAG entre claro e escuro.
- **Implementação:** fica tudo num módulo puro com testes (Vitest). `BarrasTabela` e as demais telas passam a pedir a cor ao módulo. `coresPorEntidade` e as variáveis `--color-serie-*` saem.

**Alternativa:** cores pela ordem de votação (regra atual), descartada a pedido do usuário.

### M7. Fotos
**Decisão:**
- **Fonte:** o pacote `foto_cand{ano}_BR_div.zip` do TSE, opcional em `fontes.yaml`. A URL e o padrão dos nomes internos (por exemplo `FBR{sq}_div.jpg`) precisam ser confirmados com dados reais. Ver a tarefa 1.3.
- **Extração:** o pipeline extrai só os membros cujo `sq_candidato` é de um candidato a Presidente daquele ano, segundo `staging.votacao_munzona`.
- **Tratamento:** a foto é reduzida para 160×200 em JPEG com Pillow (nova dependência do pipeline) e publicada em `web/data/fotos/{ano}/{sq}.jpg`.
- **LGPD:** a verificação confere cada arquivo publicado contra os presidenciáveis do ano.

### M8. Migração com o PR de dados apontando para a branch da feature
Hoje o site exige o schema exato (`SCHEMA_VERSAO`), e o ETL sempre abre o PR contra a `main`. Se o código do schema 2 for para a `main` antes dos dados, o deploy falha.

**Decisão:**
- `etl.yml` ganha o input `base` (padrão `main`), usado tanto no `checkout` do job `pull-request` quanto no `base` do PR.
- O ETL é disparado **a partir da branch da feature** com `base` igual a essa branch.
- O PR de snapshots entra na branch da feature, e o PR da feature leva código e dados juntos para a `main`: um único deploy, já consistente.
- O site continua exigindo o schema exato.

**Alternativa:** aceitar os schemas 1 e 2 no site durante a transição. Deixaria um caminho de código morto e uma tela de mapa degradada no ar.

## Risks / Trade-offs

- [Cores partidárias perdem a validação para daltonismo da paleta atual] → a informação nunca depende só da cor (legenda, dica, painel e tabela, em `cores-partidarias`). A regra de distinção por ΔE separa os concorrentes da mesma disputa.
- [A geometria nacional passa do orçamento e o carregamento fica lento no 4G] → simplificar e quantizar no pipeline, com um teste de tamanho. Se ainda assim não couber, carregar primeiro o contorno das UFs e os municípios em seguida.
- [Nomes do TSE e do IBGE divergem mais que o esperado] → o gate lista todos os casos de uma vez, e a tabela de exceções é pequena e revisada à mão. O primeiro ETL pode falhar até que ela esteja completa: usar `validacao-real.yml` antes do ETL.
- [Municípios criados depois da malha do IBGE (caso real: Boa Esperança do Norte, MT, instalado em 2025 e presente em 2026)] → município sem polígono é erro do gate, a não ser que esteja na lista `sem_poligono` de `municipios_excecoes.yaml`. Os listados ficam fora do desenho, mas aparecem na tabela e no painel, com uma nota abaixo do mapa (`sem_geometria` na camada).
- [Arquivo de detalhe grande para SP e MG nos cargos de deputado] → limitar a 10 candidatos por zona e comprimir (a Vercel serve com gzip ou brotli). Medir no primeiro ETL real.
- [Senador com duas vagas (2018 e 2026)] → o mapa mostra o mais votado e o painel lista todos. A legenda informa "mais votado" e não "eleito".
- [O pacote de fotos do TSE muda de nome ou formato entre anos] → a fonte é opcional, e o site mostra iniciais quando a foto falta.
- [`web/data` cresce: geometria de ~1–2 MB, camadas de ~5 MB e detalhes de algumas dezenas de MB] → aceitável para o repositório. O PR de dados mostra o tamanho. Se crescer demais, o detalhe pode sair do Git e ir para um bucket depois.

## Migration Plan

1. Implementar numa branch `feat/mapa-municipal`, com o build e os testes rodando sobre a fixture (`pnpm fixture && pnpm build:fixture`).
2. Disparar `validacao-real.yml` na branch para conferir a correspondência IBGE, a URL das fotos e o tamanho dos arquivos com dados reais. Completar a tabela de exceções.
3. Disparar `etl.yml` na branch com `base=feat/mapa-municipal`. Revisar e fazer merge do PR de snapshots na branch.
4. Abrir o PR da branch para a `main`. O merge dispara um único deploy, já com código e dados no schema 2.
5. **Rollback:** reverter o merge na `main`. Código e dados voltam juntos para o schema 1, e o deploy roda de novo.

## Open Questions

- A lista exata de cores por partido pode ser ajustada no review visual sem mudar specs nem tarefas.
- Os limites exatos das faixas de intensidade e de abstenção podem ser calibrados com a distribuição real depois do primeiro ETL.
