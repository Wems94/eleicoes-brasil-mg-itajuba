// Camada do mapa municipal por cargo ({cargo}.json): vencedor e abstenção por município.
import { dados } from "@/lib/dados";
import type { CargoMapa } from "@/lib/tipos";

export const dynamic = "force-static";
export const dynamicParams = false;

type Params = Promise<{ ano: string; turno: string; arquivo: string }>;

export function generateStaticParams() {
  return dados.eleicoes().flatMap(({ ano, turno }) =>
    dados
      .cargosMapa(ano, turno)
      .map((c) => ({ ano: String(ano), turno: String(turno), arquivo: `${c}.json` })),
  );
}

export async function GET(_req: Request, { params }: { params: Params }) {
  const { ano, turno, arquivo } = await params;
  const cargo = arquivo.replace(/\.json$/, "") as CargoMapa;
  return Response.json(dados.mapa(Number(ano), Number(turno), cargo));
}
