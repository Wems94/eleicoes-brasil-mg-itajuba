import Link from "next/link";

import { BarrasTabela } from "@/components/BarrasTabela";
import { MapaUfs } from "@/components/MapaUfs";
import { CabecalhoPagina, Participacao, SeletorEleicao, Secao } from "@/components/base";
import { type Cor, coresPorEntidade } from "@/lib/cores";
import { dados } from "@/lib/dados";
import { nomeTurno, numero, pct } from "@/lib/formato";
import type { Candidato, Eleicao } from "@/lib/tipos";

function mancheteDoPresidente(c: Candidato[]): string | null {
  const [a, b] = c;
  if (!a) return null;
  if (a.situacao === "ELEITO") return `${a.nome} é eleito Presidente com ${pct(a.pct)} dos votos válidos.`;
  if (b && a.situacao === "2º TURNO" && b.situacao === "2º TURNO") {
    return `${a.nome} (${pct(a.pct)}) e ${b.nome} (${pct(b.pct)}) disputam o 2º turno.`;
  }
  return `${a.nome} lidera para Presidente com ${pct(a.pct)} dos votos válidos.`;
}

function DestaqueItajuba({ ano, turno, cores }: Eleicao & { cores: Map<string, Cor> }) {
  const it = dados.itajuba(ano, turno);
  const cargo = it.cargos.find((c) => c.codigo === 1) ?? it.cargos[0];
  if (!cargo) return null;
  const top = cargo.votaveis.filter((v) => v.tipo === "candidato").slice(0, 3);
  return (
    <Secao
      id="itajuba"
      titulo="Itajubá (MG)"
      sobretitulo={`Em destaque · ${cargo.nome}`}
      acao={
        <Link
          href={`/itajuba/${ano}/${turno}/`}
          className="shrink-0 rounded-lg border border-borda px-3 py-1.5 text-sm font-medium hover:bg-realce"
        >
          Ver Itajubá →
        </Link>
      }
    >
      <BarrasTabela
        legenda={`${cargo.nome} em Itajubá: percentual dos votos válidos`}
        ocultarLegenda
        linhas={top.map((v, i) => ({
          chave: String(v.numero),
          rotulo: v.nome ?? `Nº ${v.numero}`,
          detalhe: v.partido,
          votos: v.votos,
          pct: v.pct,
          destaque: i === 0,
          // no Presidente, a mesma cor do gráfico nacional desta página
          cor: cargo.codigo === 1 ? cores.get(String(v.numero)) : undefined,
        }))}
      />
      {cargo.comparecimento ? (
        <p className="num mt-3 text-xs text-texto-3">
          {numero(cargo.comparecimento.comparecimento)} eleitores compareceram ·{" "}
          {pct(cargo.comparecimento.pct_comparecimento)}
        </p>
      ) : null}
    </Secao>
  );
}

export function BrasilVisao({ ano, turno }: Eleicao) {
  const b = dados.brasil(ano, turno);
  const candidatos = b.presidente?.candidatos ?? [];
  const cores = coresPorEntidade(candidatos.map((c) => c.numero));
  return (
    <div className="space-y-6">
      <CabecalhoPagina
        sobretitulo={`Resultado oficial · ${nomeTurno(turno)}`}
        titulo={`Eleições ${ano}`}
        subtitulo={mancheteDoPresidente(candidatos)}
      >
        <SeletorEleicao eleicoes={dados.eleicoes()} atual={{ ano, turno }} href={(e) => `/${e.ano}/${e.turno}/`} />
      </CabecalhoPagina>

      {b.comparecimento ? <Participacao dados={b.comparecimento} /> : null}

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="space-y-6">
          <Secao id="presidente" titulo="Presidente" sobretitulo="Brasil">
            {b.presidente ? (
              <>
                <BarrasTabela
                  legenda={`Presidente, ${ano}, ${nomeTurno(turno)}: percentual dos votos válidos`}
                  ocultarLegenda
                  linhas={candidatos.map((c) => ({
                    chave: String(c.numero),
                    rotulo: c.nome,
                    detalhe: [`Nº ${c.numero}`, c.partido, c.federacao, c.situacao].filter(Boolean).join(" · "),
                    votos: c.votos,
                    pct: c.pct,
                    destaque: c.posicao === 1,
                    cor: cores.get(String(c.numero)),
                  }))}
                />
                <p className="num mt-3 text-xs text-texto-3">{numero(b.presidente.votos_validos)} votos válidos</p>
              </>
            ) : (
              <p className="text-texto-2">Sem disputa presidencial neste turno.</p>
            )}
          </Secao>
          <DestaqueItajuba ano={ano} turno={turno} cores={cores} />
        </div>

        {b.ufs.length ? (
          <Secao id="ufs" titulo="Mais votado por UF" sobretitulo="Mapa">
            <MapaUfs brasil={b} />
          </Secao>
        ) : null}
      </div>
    </div>
  );
}
