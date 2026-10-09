import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import type { ReactNode } from "react";

import { dados } from "@/lib/dados";
import { dataGeracao } from "@/lib/formato";

import "./globals.css";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist", display: "swap" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono", display: "swap" });

export const metadata: Metadata = {
  title: { default: "Eleições Gerais — Brasil e Itajubá", template: "%s · Eleições Gerais" },
  description:
    "Resultados oficiais das eleições gerais de 2018, 2022 e 2026 por UF, com aprofundamento em Itajubá-MG. Fonte: TSE.",
};

const LINKS = [
  ["/", "Brasil"],
  ["/itajuba/", "Itajubá"],
  ["/metodologia/", "Metodologia"],
] as const;

export default function Layout({ children }: { children: ReactNode }) {
  const manifesto = dados.manifesto();
  return (
    <html lang="pt-BR" className={`${geist.variable} ${geistMono.variable}`}>
      <body className="min-h-screen font-sans">
        <a
          href="#conteudo"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-texto focus:px-3 focus:py-2 focus:text-superficie"
        >
          Pular para o conteúdo
        </a>
        <header className="sticky top-0 z-40 border-b border-borda bg-superficie/85 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4">
            <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
              <span className="grid size-7 place-items-center rounded-lg bg-texto text-xs font-bold text-superficie" aria-hidden="true">
                BR
              </span>
              Eleições Gerais
            </Link>
            <nav aria-label="Principal" className="flex gap-1 text-sm">
              {LINKS.map(([href, rotulo]) => (
                <Link
                  key={href}
                  href={href}
                  className="rounded-lg px-2.5 py-1.5 text-texto-2 transition-colors hover:bg-realce hover:text-texto sm:px-3"
                >
                  {rotulo}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main id="conteudo" className="mx-auto max-w-6xl px-4 py-8 sm:py-10">
          {children}
        </main>
        <footer className="mt-12 border-t border-borda bg-superficie">
          <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-6 text-xs text-texto-3 sm:flex-row sm:justify-between">
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
