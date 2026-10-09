import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { SnapshotsDados } from "./dados";

// Snapshots gerados pelo pipeline a partir dos fixtures (pnpm fixture).
const FIXTURE = path.resolve(import.meta.dirname, "..", ".snapshots-fixture");

describe("leitura dos snapshots", () => {
  const dados = new SnapshotsDados(FIXTURE);

  it("oferece só os anos e turnos do manifesto", () => {
    expect(dados.eleicoes()).toEqual([
      { ano: 2018, turno: 1 },
      { ano: 2022, turno: 1 },
      { ano: 2022, turno: 2 },
    ]);
    expect(dados.maisRecente()).toEqual({ ano: 2022, turno: 2 });
  });

  it("lista as UFs de cada eleição a partir do manifesto", () => {
    expect(dados.ufs(2022, 1)).toEqual(["MG", "SP", "ZZ"]);
  });

  it("lê os arquivos de cada eleição", () => {
    const b = dados.brasil(2022, 1);
    expect(b.presidente?.candidatos[0].numero).toBe(13);
    expect(dados.uf(2022, 1, "MG").cargos.map((c) => c.codigo)).toEqual([1, 3, 5, 6, 7]);
    expect(dados.itajuba(2022, 1).locais).toHaveLength(2);
    expect(dados.itajubaSecoes(2022, 1).secoes).toHaveLength(4);
    expect(dados.historico().partidos.length).toBeGreaterThan(0);
    expect(dados.manifesto().municipio?.nome).toBe("ITAJUBÁ");
  });

  it("recusa eleição que não está no manifesto", () => {
    expect(() => dados.brasil(2020, 1)).toThrow(/2020\/1 não está no manifesto/);
  });
});

describe("erros de configuração", () => {
  let dir: string;
  afterEach(() => rmSync(dir, { recursive: true, force: true }));

  it("diretório sem snapshots explica como gerar", () => {
    dir = mkdtempSync(path.join(tmpdir(), "snap-"));
    expect(() => new SnapshotsDados(dir).manifesto()).toThrow(/pnpm fixture/);
  });

  it("versão de schema incompatível falha no build", () => {
    dir = mkdtempSync(path.join(tmpdir(), "snap-"));
    mkdirSync(dir, { recursive: true });
    writeFileSync(path.join(dir, "manifest.json"), JSON.stringify({ schema_versao: 99 }));
    expect(() => new SnapshotsDados(dir).manifesto()).toThrow(/schema 99/);
  });
});
