import type { Metadata } from "next";

import { ItajubaVisao } from "@/components/itajuba/ItajubaVisao";
import { dados } from "@/lib/dados";

export const metadata: Metadata = { title: "Itajubá" };

export default function Itajuba() {
  return <ItajubaVisao {...dados.maisRecente()} />;
}
