import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import Link from "next/link";
import type { ReactNode } from "react";

import { dados } from "@/lib/dados";
import { dataGeracao } from "@/lib/formato";

import "./globals.css";

const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces", display: "swap" });
const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-sans",
  display: "swap",
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "Eleições Gerais — Brasil e Itajubá", template: "%s · Eleições Gerais" },
  description:
    "Resultados oficiais das eleições gerais de 2018, 2022 e 2026 por UF, com aprofundamento em Itajubá-MG. Fonte: TSE.",
};

export default function Layout({ children }: { children: ReactNode }) {
  const manifesto = dados.manifesto();
  return (
    <html lang="pt-BR" className={`${fraunces.variable} ${plexSans.variable} ${plexMono.variable}`}>
      <body className="min-h-screen font-sans">
        <a
          href="#conteudo"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:bg-tinta focus:px-3 focus:py-2 focus:text-papel"
        >
          Pular para o conteúdo
        </a>
        <header className="border-b border-regua">
          <div className="mx-auto flex max-w-6xl flex-wrap items-baseline justify-between gap-x-8 gap-y-2 px-4 py-4">
            <Link href="/" className="font-display text-xl font-semibold tracking-tight">
              Eleições <span className="italic text-ocre">Gerais</span>
            </Link>
            <nav aria-label="Principal" className="flex gap-5 text-sm">
              <Link href="/" className="hover:text-ocre">
                Brasil
              </Link>
              <Link href="/itajuba/" className="hover:text-ocre">
                Itajubá
              </Link>
              <Link href="/metodologia/" className="hover:text-ocre">
                Metodologia
              </Link>
            </nav>
          </div>
        </header>
        <main id="conteudo" className="mx-auto max-w-6xl px-4 py-8">
          {children}
        </main>
        <footer className="mt-16 border-t border-regua">
          <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-6 text-xs text-tinta-2 sm:flex-row sm:justify-between">
            <p>Fonte: {manifesto.fonte}. Dados oficiais, sem projeções.</p>
            <p>
              Dados gerados em{" "}
              <time dateTime={manifesto.gerado_em} className="num">
                {dataGeracao(manifesto.gerado_em)}
              </time>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
