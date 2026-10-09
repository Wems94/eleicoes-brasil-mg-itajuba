import type { Eleicao } from "./tipos";

export type ParamsEleicao = Promise<{ ano: string; turno: string }>;

export async function eleicaoDosParams(params: ParamsEleicao): Promise<Eleicao> {
  const { ano, turno } = await params;
  return { ano: Number(ano), turno: Number(turno) };
}
