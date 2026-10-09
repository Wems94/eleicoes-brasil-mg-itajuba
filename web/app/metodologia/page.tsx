import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Secao } from "@/components/base";
import { dados } from "@/lib/dados";
import { dataGeracao, nomeTurno, numero } from "@/lib/formato";

export const metadata: Metadata = { title: "Metodologia" };

const REPOSITORIO = "https://github.com/Wems94/eleicoes-brasil-mg-itajuba";

function Item({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 border-t border-borda py-4 md:grid-cols-[14rem_1fr] md:gap-8">
      <h3 className="text-lg font-semibold">{titulo}</h3>
      <div className="max-w-prose space-y-2 text-[15px] leading-relaxed">{children}</div>
    </div>
  );
}

export default function Metodologia() {
  const m = dados.manifesto();
  const tamanho = (b: number) =>
    b >= 1e6 ? `${numero(Math.round(b / 1e6))} MB` : `${numero(Math.max(1, Math.round(b / 1e3)))} KB`;
  return (
    <div className="space-y-12">
      <header className="space-y-4">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-texto-3">Transparência</p>
        <h1 className="text-4xl font-semibold tracking-tight sm:text-6xl">Metodologia</h1>
        <p className="max-w-prose text-lg text-texto-2">
          Como os números deste site são obtidos, validados e publicados. Dados gerados em{" "}
          <time dateTime={m.gerado_em} className="num">{dataGeracao(m.gerado_em)}</time>.
        </p>
      </header>

      <Secao id="fonte" titulo="Fonte" sobretitulo="Origem dos dados">
        <Item titulo="Dados oficiais">
          <p>
            Todos os resultados vêm do Portal de Dados Abertos do Tribunal Superior Eleitoral (
            <a className="underline" href="https://dadosabertos.tse.jus.br/">dadosabertos.tse.jus.br</a>
            ), nos arquivos de votação por município e zona, por seção eleitoral, de candidatos e de
            locais de votação. Não há projeções nem dados de pesquisas.
          </p>
          <p>
            Eleições disponíveis:{" "}
            {m.eleicoes.map((e) => `${e.ano} (${e.turnos.map(nomeTurno).join(" e ")})`).join("; ")}.
          </p>
        </Item>
        <Item titulo="Integridade">
          <p>
            Cada arquivo baixado tem o seu sha256 registrado. A tabela abaixo lista os arquivos usados
            em cada eleição, para que qualquer pessoa possa conferir que são os mesmos publicados pelo
            TSE.
          </p>
        </Item>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[44rem] text-sm">
            <caption className="mb-2 text-left text-xs text-texto-2">Arquivos de origem e sha256</caption>
            <thead>
              <tr className="border-b border-borda text-left text-xs text-texto-2">
                <th scope="col" className="py-1 font-medium">Eleição</th>
                <th scope="col" className="py-1 font-medium">Arquivo do TSE</th>
                <th scope="col" className="py-1 pr-3 text-right font-medium">Tamanho</th>
                <th scope="col" className="py-1 font-medium">sha256</th>
              </tr>
            </thead>
            <tbody>
              {m.origens.map((o) => (
                <tr key={`${o.ano}-${o.turno}-${o.fonte}`} className="border-b border-borda">
                  <td className="num py-1 pr-3">{o.ano}/{o.turno}</td>
                  <td className="py-1 pr-3">
                    <a className="underline decoration-borda hover:decoration-texto" href={o.url}>
                      {o.url.split("/").pop()}
                    </a>
                  </td>
                  <td className="num py-1 pr-3 text-right">{tamanho(o.tamanho)}</td>
                  <td className="num py-1 text-xs text-texto-2" title={o.sha256}>
                    {o.sha256.slice(0, 16)}…
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Secao>

      <Secao id="calculos" titulo="Como os números são calculados" sobretitulo="Regras">
        <Item titulo="Votos válidos">
          <p>
            Percentuais de candidatos são calculados sobre os votos válidos do cargo: votos nominais
            mais votos de legenda (estes só nos cargos proporcionais). Brancos e nulos não entram nos
            válidos; seus percentuais são calculados sobre o comparecimento.
          </p>
        </Item>
        <Item titulo="Senado">
          <p>
            Em 2018 e 2026 foram eleitos dois senadores por UF, e cada eleitor votou duas vezes; em
            2022, uma vaga. Por isso o total de votos para Senador é o comparecimento multiplicado pelo
            número de vagas.
          </p>
        </Item>
        <Item titulo="Candidaturas sub judice ou não aptas">
          <p>
            Votos em candidatos com a candidatura pendente de julgamento (sub judice) não entram nos
            válidos enquanto a situação não se resolve, como na totalização oficial. Votos em
            candidaturas não aptas aparecem no arquivo de seção, mas o TSE os conta como nulos; aqui
            eles também são contados como nulos.
          </p>
        </Item>
        <Item titulo="Itajubá">
          <p>
            O município é identificado pelo nome e pela UF nos próprios arquivos do TSE (código{" "}
            <span className="num">{m.municipio?.codigo ?? "—"}</span>). Os resultados por seção vêm do
            arquivo de seção de MG; como ele não traz o cargo de Presidente, esses votos vêm do arquivo
            nacional de seções, filtrado para Itajubá. A situação dos deputados (eleito, suplente) é a
            do candidato no estado.
          </p>
        </Item>
      </Secao>

      <Secao id="qualidade" titulo="Validação e publicação" sobretitulo="Controle">
        <Item titulo="Gate de qualidade">
          <p>
            Antes de qualquer publicação, um conjunto de regras confere os dados: a soma dos votos de
            cada seção e de cada município é igual ao comparecimento (vezes as vagas), não há linhas
            duplicadas nem votos negativos, todo voto nominal tem candidato, as 27 UFs e Itajubá estão
            presentes e os percentuais somam 100%. Se qualquer regra falhar, nada é publicado e o site
            continua com os dados anteriores.
          </p>
        </Item>
        <Item titulo="Dados pessoais (LGPD)">
          <p>
            Os arquivos de candidatos do TSE trazem CPF, e-mail, data de nascimento e título de
            eleitor. Esses campos nunca são lidos: o pipeline só lê as colunas que declara
            explicitamente. Uma verificação automática bloqueia a publicação se aparecer qualquer
            coluna ou valor com padrão de CPF ou e-mail.
          </p>
        </Item>
        <Item titulo="Site estático">
          <p>
            As páginas são geradas de antemão a partir de arquivos de dados versionados; o site não
            consulta banco de dados ao ser acessado. Novos dados entram por revisão pública no
            repositório antes de serem publicados.
          </p>
        </Item>
      </Secao>

      <Secao id="apresentacao" titulo="Apresentação" sobretitulo="Leitura">
        <Item titulo="Cores neutras">
          <p>
            O site não usa cores de partidos: no mapa, os candidatos são diferenciados por textura
            (sólido, hachurado, tracejado) e pelo número escrito em cada UF, para que nenhuma cor
            sugira apoio a candidato ou partido.
          </p>
        </Item>
        <Item titulo="Acessibilidade">
          <p>
            Todo gráfico é também uma tabela com os mesmos números, legível por leitores de tela.
          </p>
        </Item>
        <Item titulo="Mapas">
          <p>
            A visão por UF usa um mapa em grade, sem geometria. O mapa dos locais de votação usa tiles
            do OpenFreeMap, com dados © colaboradores do OpenStreetMap.
          </p>
        </Item>
        <Item titulo="Código aberto">
          <p>
            Todo o código, as regras de qualidade e a especificação estão em{" "}
            <a className="underline" href={REPOSITORIO}>{REPOSITORIO.replace("https://", "")}</a>.
          </p>
        </Item>
      </Secao>
    </div>
  );
}
