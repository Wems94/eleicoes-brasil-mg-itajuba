import type { Metadata } from "next";

import { ItajubaVisao } from "@/components/itajuba/ItajubaVisao";
import { dados } from "@/lib/dados";
import { nomeTurno } from "@/lib/formato";
import { eleicaoDosParams, type ParamsEleicao } from "@/lib/rotas";

export const dynamicParams = false;

export function generateStaticParams() {
  return dados.eleicoes().map((e) => ({ ano: String(e.ano), turno: String(e.turno) }));
}

export async function generateMetadata({ params }: { params: ParamsEleicao }): Promise<Metadata> {
  const { ano, turno } = await eleicaoDosParams(params);
  return { title: `Itajubá ${ano}, ${nomeTurno(turno)}` };
}

export default async function Pagina({ params }: { params: ParamsEleicao }) {
  return <ItajubaVisao {...await eleicaoDosParams(params)} />;
}
