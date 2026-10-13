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
    "Resultados oficiais das eleições gerais de 2018, 2022 e 2026: mapa por município e zona eleitoral, abstenção, UFs e aprofundamento em Itajubá-MG. Fonte: TSE.",
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
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-texto focus:px-3 focus:py-2 focus:text-fundo"
        >
          Pular para o conteúdo
        </a>
        <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-fundo/70 backdrop-blur-xl">
          <div className="mx-auto grid h-16 max-w-7xl grid-cols-[1fr_auto] items-center gap-4 px-4 md:grid-cols-[1fr_auto_1fr] sm:px-6">
            <Link href="/" className="flex items-center gap-2.5 font-semibold tracking-tight">
              <span
                className="grid size-8 place-items-center rounded-lg bg-gradient-to-b from-violet-400 to-violet-700 text-[11px] font-bold text-white shadow-[0_0_20px_-4px_rgb(139_92_246/0.8)]"
                aria-hidden="true"
              >
                BR
              </span>
              <span>
                Eleições <span className="text-texto-2">Gerais</span>
              </span>
            </Link>
            <nav aria-label="Principal" className="hidden gap-1 text-sm md:flex">
              {LINKS.map(([href, rotulo]) => (
                <Link
                  key={href}
                  href={href}
                  className="rounded-lg px-3 py-1.5 text-texto-2 transition-colors hover:bg-white/5 hover:text-texto"
                >
                  {rotulo}
                </Link>
              ))}
            </nav>
            <div className="flex items-center justify-end gap-2">
              <Link
                href="/metodologia/"
                className="hidden rounded-lg px-3 py-1.5 text-sm text-texto-2 hover:text-texto sm:block md:hidden"
              >
                Metodologia
              </Link>
              <Link
                href="/#mapa"
                className="rounded-xl border border-white/15 bg-white/[0.04] px-3.5 py-1.5 text-sm font-medium transition-colors hover:bg-white/10"
              >
                Abrir o mapa
              </Link>
            </div>
          </div>
          <nav aria-label="Principal (celular)" className="flex gap-1 border-t border-white/[0.06] px-4 py-1.5 text-sm md:hidden">
            {LINKS.map(([href, rotulo]) => (
              <Link key={href} href={href} className="rounded-lg px-2.5 py-1 text-texto-2 hover:text-texto">
                {rotulo}
              </Link>
            ))}
          </nav>
        </header>
        <main id="conteudo" className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-12">
          {children}
        </main>
        <footer className="mt-16 border-t border-white/[0.06]">
          <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-8 text-xs text-texto-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <p className="flex items-center gap-2">
              <span className="size-1.5 rounded-full bg-acento" aria-hidden="true" />
              Fonte: {manifesto.fonte}. Dados oficiais, sem projeções.
            </p>
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
