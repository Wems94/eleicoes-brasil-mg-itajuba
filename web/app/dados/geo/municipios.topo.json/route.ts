// Malha municipal do IBGE (TopoJSON), baixada uma vez pelo mapa municipal.
import { dados } from "@/lib/dados";

export const dynamic = "force-static";

export function GET() {
  return new Response(new Uint8Array(dados.bruto("geo/municipios.topo.json")), {
    headers: { "Content-Type": "application/json" },
  });
}
