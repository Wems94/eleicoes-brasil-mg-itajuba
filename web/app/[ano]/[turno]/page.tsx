import type { Metadata } from "next";

import { BrasilVisao } from "@/components/BrasilVisao";
import { eleicaoDosParams, type ParamsEleicao } from "@/lib/rotas";
import { dados } from "@/lib/dados";
import { nomeTurno } from "@/lib/formato";

export const dynamicParams = false; // só os anos/turnos do manifesto

export function generateStaticParams() {
  return dados.eleicoes().map((e) => ({ ano: String(e.ano), turno: String(e.turno) }));
}

export async function generateMetadata({ params }: { params: ParamsEleicao }): Promise<Metadata> {
  const { ano, turno } = await eleicaoDosParams(params);
  return { title: `Brasil ${ano}, ${nomeTurno(turno)}` };
}

export default async function Pagina({ params }: { params: ParamsEleicao }) {
  return <BrasilVisao {...await eleicaoDosParams(params)} />;
}
