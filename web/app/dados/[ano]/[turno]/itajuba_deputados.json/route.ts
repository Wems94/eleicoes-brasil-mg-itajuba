// Lista completa dos deputados votados em Itajubá, carregada sob demanda.
import { dados } from "@/lib/dados";
import { deputadosDeItajuba } from "@/lib/deputados";
import { eleicaoDosParams, type ParamsEleicao } from "@/lib/rotas";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  return dados.eleicoes().map((e) => ({ ano: String(e.ano), turno: String(e.turno) }));
}

export async function GET(_req: Request, { params }: { params: ParamsEleicao }) {
  const { ano, turno } = await eleicaoDosParams(params);
  return Response.json(deputadosDeItajuba(ano, turno));
}
