# Pipeline

ETL dos resultados do TSE: download → staging → marts → gate de qualidade → LGPD →
MotherDuck → snapshots JSON do site. Visão geral, comandos e CI no
[README da raiz](../README.md).

```bash
uv run pytest                                   # testes (fixtures fictícios)
uv run eleicoes run --ano 2026 --turno 1        # ETL completo com dados reais
uv run python scripts/validar_real.py --ano 2022 # diagnóstico com dados reais, sem publicar
```

## Fontes (`config/fontes.yaml`)

| Fonte | Origem | Obrigatória | Uso |
|---|---|---|---|
| `votacao_candidato_munzona` | TSE | sim | votos por candidato, município e zona |
| `votacao_partido_munzona` | TSE | sim | votos nominais + legenda por partido (Deputado no mapa) |
| `detalhe_votacao_munzona` | TSE | sim | aptos, comparecimento, abstenção, brancos e nulos |
| `votacao_secao_mg` / `_br`, `detalhe_votacao_secao` | TSE | sim | seções de Itajubá |
| `consulta_cand` | TSE | não | atributos de candidatos (lidos por allowlist) |
| `locais_votacao` | TSE | não | coordenadas dos locais de Itajubá |
| `fotos_presidente` | TSE | não | fotos de divulgação; só as de Presidente são extraídas |
| `ibge_municipios` | IBGE | sim | código, nome e UF de cada município |
| `ibge_malha` | IBGE | sim | malha municipal em TopoJSON (qualidade mínima) |

Nomes de município que não casam entre TSE e IBGE ficam em
`config/municipios_excecoes.yaml` (UF → nome no TSE → código IBGE). O gate lista os
que faltam, e o `scripts/validar_real.py` sugere o nome do IBGE mais parecido.

## Staging (schema `staging`)

Uma tabela por fonte do TSE (`esquema.py`), particionada por (`ano`, `turno`).
`votacao_partido_munzona` guarda só os cargos proporcionais. Também ficam no staging:

- `fotos_presidente` (`ano`, `turno`, `sq_candidato`, `jpeg`), com as fotos já reduzidas para 160×200;
- `ibge_municipios` e `ibge_malha`, substituídas a cada carga e sem partição.

## Marts (schema `marts`)

| Mart | Grão |
|---|---|
| `cargos` | ano × cargo (votos por eleitor do Senado) |
| `resultado_uf` / `resultado_brasil` | candidato por UF / Presidente no Brasil |
| `comparecimento_uf` | UF × cargo |
| `municipio_ibge` | município do TSE → código IBGE (`por_excecao` marca os resolvidos pela tabela) |
| `resultado_municipio` / `resultado_zona` | candidato por município / por município × zona |
| `comparecimento_municipio` / `comparecimento_zona` | município × cargo / município × zona × cargo |
| `partido_municipio` / `partido_zona` | partido nos cargos proporcionais (nominais + legenda) |
| `itajuba_resultado`, `itajuba_zona`, `itajuba_local`, `itajuba_secao` | votáveis de Itajubá |
| `itajuba_comparecimento` | seção de Itajubá × cargo |
| `historico_itajuba_partido` / `historico_itajuba_comparecimento` | Itajubá, todos os anos |

Os marts por município e zona usam o código do TSE (`cd_municipio`). Uma zona pode
atender mais de um município, e por isso a chave da zona é (`cd_municipio`, `nr_zona`).

## Snapshots (`web/data`, schema 2)

Gerados pelo `snapshots.py` a partir do banco, com troca atômica do diretório e
verificação de LGPD antes da troca. O contrato completo está na docstring do módulo.

| Arquivo | Conteúdo |
|---|---|
| `manifest.json` | eleições, origens (sha256), sha256 de cada arquivo, município do recorte (com `ibge`) |
| `geo/municipios.topo.json` | malha do IBGE: `id` = código IBGE, `nome`, `uf` |
| `fotos/{ano}/{sq}.jpg` | fotos dos candidatos a Presidente, referenciadas em `brasil.json` (`foto`) |
| `{ano}/{turno}/brasil.json`, `uf/{UF}.json` | Presidente nacional e cargos por UF |
| `{ano}/{turno}/mapa/{cargo}.json` | camada do mapa: `municipios[código IBGE] = [índice do vencedor ou -1 (empate), pct×100, abstenção×100]`, `ufs`, `exterior` |
| `{ano}/{turno}/municipios/{UF}/{cargo}.json` | painel: `total` e `zonas` de cada município (comparecimento, votos; nos proporcionais, partidos e top 10 candidatos) |
| `{ano}/{turno}/itajuba.json`, `itajuba_secoes.json`, `historico_itajuba.json` | deep dive de Itajubá |

`{cargo}` é `presidente`, `governador`, `senador`, `deputado-federal` ou `deputado-estadual`
(este inclui o Distrital do DF). Nos cargos proporcionais o vencedor é o partido.
