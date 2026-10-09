// Lista completa de deputados da UF, carregada sob demanda ("ver todos").
import { dados } from "@/lib/dados";
import { deputadosDaUf } from "@/lib/deputados";

export const dynamic = "force-static";
export const dynamicParams = false;

type Params = Promise<{ ano: string; turno: string; uf: string }>;

export function generateStaticParams() {
  return dados.eleicoes().flatMap(({ ano, turno }) =>
    dados.ufs(ano, turno).map((uf) => ({ ano: String(ano), turno: String(turno), uf })),
  );
}

export async function GET(_req: Request, { params }: { params: Params }) {
  const p = await params;
  return Response.json(deputadosDaUf(Number(p.ano), Number(p.turno), p.uf));
}
