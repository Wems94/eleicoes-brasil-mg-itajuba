// Detalhe por município e zona de uma UF ({cargo}.json), carregado ao abrir um município.
import { dados } from "@/lib/dados";
import type { CargoMapa } from "@/lib/tipos";

export const dynamic = "force-static";
export const dynamicParams = false;

type Params = Promise<{ ano: string; turno: string; uf: string; arquivo: string }>;

export function generateStaticParams() {
  return dados.eleicoes().flatMap(({ ano, turno }) =>
    dados.detalhes(ano, turno).map(({ uf, cargo }) => ({
      ano: String(ano),
      turno: String(turno),
      uf,
      arquivo: `${cargo}.json`,
    })),
  );
}

export async function GET(_req: Request, { params }: { params: Params }) {
  const { ano, turno, uf, arquivo } = await params;
  const cargo = arquivo.replace(/\.json$/, "") as CargoMapa;
  return Response.json(dados.detalhe(Number(ano), Number(turno), uf, cargo));
}
