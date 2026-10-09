import { BrasilVisao } from "@/components/BrasilVisao";
import { dados } from "@/lib/dados";

// A home mostra a eleição mais recente do manifesto.
export default function Inicio() {
  return <BrasilVisao {...dados.maisRecente()} />;
}
