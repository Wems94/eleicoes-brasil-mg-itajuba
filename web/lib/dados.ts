// Leitura dos snapshots em tempo de build (o site não consulta banco: D7/D8).
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

import type {
  Brasil,
  Eleicao,
  Historico,
  Itajuba,
  ItajubaSecoes,
  Manifesto,
  Uf,
} from "./tipos";

export const SCHEMA_VERSAO = 1;

export class SnapshotsDados {
  private cache = new Map<string, unknown>();

  constructor(readonly diretorio: string) {}

  private ler<T>(relativo: string): T {
    if (!this.cache.has(relativo)) {
      const arquivo = path.join(this.diretorio, relativo);
      this.cache.set(relativo, JSON.parse(readFileSync(arquivo, "utf8")));
    }
    return this.cache.get(relativo) as T;
  }

  manifesto(): Manifesto {
    if (!existsSync(path.join(this.diretorio, "manifest.json"))) {
      throw new Error(
        `Snapshots não encontrados em ${this.diretorio}. Gere com \`uv run eleicoes run\` ` +
          "(dados reais) ou `pnpm fixture` e `pnpm build:fixture` (dados de teste).",
      );
    }
    const m = this.ler<Manifesto>("manifest.json");
    if (m.schema_versao !== SCHEMA_VERSAO) {
      throw new Error(
        `Snapshots com schema ${m.schema_versao}; o site espera o schema ${SCHEMA_VERSAO}.`,
      );
    }
    return m;
  }

  eleicoes(): Eleicao[] {
    return this.manifesto().eleicoes.flatMap(({ ano, turnos }) =>
      turnos.map((turno) => ({ ano, turno })),
    );
  }

  maisRecente(): Eleicao {
    const todas = this.eleicoes();
    return todas[todas.length - 1];
  }

  private exigir(ano: number, turno: number): string {
    if (!this.eleicoes().some((e) => e.ano === ano && e.turno === turno)) {
      throw new Error(`Eleição ${ano}/${turno} não está no manifesto.`);
    }
    return `${ano}/${turno}`;
  }

  ufs(ano: number, turno: number): string[] {
    const prefixo = `${this.exigir(ano, turno)}/uf/`;
    return Object.keys(this.manifesto().arquivos)
      .filter((a) => a.startsWith(prefixo))
      .map((a) => a.slice(prefixo.length, -".json".length))
      .sort();
  }

  brasil(ano: number, turno: number): Brasil {
    return this.ler(`${this.exigir(ano, turno)}/brasil.json`);
  }

  uf(ano: number, turno: number, uf: string): Uf {
    return this.ler(`${this.exigir(ano, turno)}/uf/${uf}.json`);
  }

  itajuba(ano: number, turno: number): Itajuba {
    return this.ler(`${this.exigir(ano, turno)}/itajuba.json`);
  }

  itajubaSecoes(ano: number, turno: number): ItajubaSecoes {
    return this.ler(`${this.exigir(ano, turno)}/itajuba_secoes.json`);
  }

  historico(): Historico {
    this.manifesto();
    return this.ler("historico_itajuba.json");
  }
}

// SNAPSHOTS_DIR permite construir com os dados de fixture (pnpm build:fixture).
export const dados = new SnapshotsDados(
  path.resolve(process.cwd(), process.env.SNAPSHOTS_DIR ?? "data"),
);
