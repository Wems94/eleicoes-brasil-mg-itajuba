// JSON estático das seções de Itajubá, carregado pela busca de seção no navegador.
import { dados } from "@/lib/dados";
import { eleicaoDosParams, type ParamsEleicao } from "@/lib/rotas";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  return dados.eleicoes().map((e) => ({ ano: String(e.ano), turno: String(e.turno) }));
}

export async function GET(_req: Request, { params }: { params: ParamsEleicao }) {
  const { ano, turno } = await eleicaoDosParams(params);
  return Response.json(dados.itajubaSecoes(ano, turno));
}
