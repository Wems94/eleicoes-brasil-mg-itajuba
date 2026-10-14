// Fotos de divulgação do TSE, só dos candidatos a Presidente (LGPD).
import { dados } from "@/lib/dados";

export const dynamic = "force-static";
export const dynamicParams = false;

type Params = Promise<{ ano: string; arquivo: string }>;

export function generateStaticParams() {
  return dados.fotos();
}

export async function GET(_req: Request, { params }: { params: Params }) {
  const { ano, arquivo } = await params;
  return new Response(new Uint8Array(dados.bruto(`fotos/${ano}/${arquivo}`)), {
    headers: { "Content-Type": "image/jpeg" },
  });
}
