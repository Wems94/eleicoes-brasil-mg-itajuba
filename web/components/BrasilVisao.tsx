import { BarrasTabela } from "@/components/BarrasTabela";
import { MapaUfs } from "@/components/MapaUfs";
import { Participacao, SeletorEleicao, Secao } from "@/components/base";
import { dados } from "@/lib/dados";
import { nomeTurno, numero, pct } from "@/lib/formato";
import type { Candidato, Eleicao } from "@/lib/tipos";

function mancheteDoPresidente(c: Candidato[]): string | null {
  const [a, b] = c;
  if (!a) return null;
  if (a.situacao === "ELEITO") return `${a.nome} é eleito Presidente com ${pct(a.pct)} dos válidos`;
  if (b && a.situacao === "2º TURNO" && b.situacao === "2º TURNO") {
    return `${a.nome} (${pct(a.pct)}) e ${b.nome} (${pct(b.pct)}) vão ao 2º turno`;
  }
  return `${a.nome} lidera para Presidente com ${pct(a.pct)} dos válidos`;
}

export function BrasilVisao({ ano, turno }: Eleicao) {
  const b = dados.brasil(ano, turno);
  const manchete = mancheteDoPresidente(b.presidente?.candidatos ?? []);
  return (
    <div className="space-y-12">
      <header className="space-y-5">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ocre">
          Resultado oficial · {nomeTurno(turno)}
        </p>
        <h1 className="max-w-3xl font-display text-4xl font-semibold leading-[1.05] tracking-tight sm:text-6xl">
          Eleições {ano}
          {manchete ? (
            <span className="block text-2xl font-normal italic text-tinta-2 sm:text-3xl">
              {manchete}
            </span>
          ) : null}
        </h1>
        <SeletorEleicao
          eleicoes={dados.eleicoes()}
          atual={{ ano, turno }}
          href={(e) => `/${e.ano}/${e.turno}/`}
        />
      </header>

      <div className="grid gap-12 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        {b.presidente ? (
          <Secao id="presidente" titulo="Presidente" sobretitulo="Brasil">
            <BarrasTabela
              legenda={`Presidente, ${ano}, ${nomeTurno(turno)}: percentual dos votos válidos`}
              ocultarLegenda
              linhas={b.presidente.candidatos.map((c) => ({
                chave: String(c.numero),
                rotulo: `${c.numero} · ${c.nome}`,
                detalhe: [c.partido, c.federacao, c.situacao].filter(Boolean).join(" · "),
                votos: c.votos,
                pct: c.pct,
                destaque: c.posicao === 1,
              }))}
            />
            <p className="num mt-3 text-xs text-tinta-2">
              {numero(b.presidente.votos_validos)} votos válidos
            </p>
          </Secao>
        ) : (
          <Secao titulo="Presidente" sobretitulo="Brasil">
            <p className="text-tinta-2">Sem disputa presidencial neste turno.</p>
          </Secao>
        )}

        {b.ufs.length ? (
          <Secao id="ufs" titulo="Por UF" sobretitulo="Mapa">
            <MapaUfs brasil={b} />
          </Secao>
        ) : null}
      </div>

      {b.comparecimento ? (
        <Secao id="participacao" titulo="Participação" sobretitulo="Eleitorado">
          <Participacao dados={b.comparecimento} />
          <p className="num mt-2 text-xs text-tinta-2">
            {numero(b.comparecimento.aptos)} eleitores aptos
          </p>
        </Secao>
      ) : null}
    </div>
  );
}
