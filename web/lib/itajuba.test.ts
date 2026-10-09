import path from "node:path";
import { describe, expect, it } from "vitest";

import { SnapshotsDados } from "./dados";
import { buscarSecao, historicoPorCargo, secoesDisponiveis } from "./itajuba";

const dados = new SnapshotsDados(path.resolve(import.meta.dirname, "..", ".snapshots-fixture"));
const secoes = dados.itajubaSecoes(2022, 1);

describe("busca de seção", () => {
  it("lista zonas e seções em ordem", () => {
    expect(secoesDisponiveis(secoes)).toEqual([
      { zona: 134, secao: 18 },
      { zona: 134, secao: 19 },
      { zona: 134, secao: 25 },
      { zona: 134, secao: 26 },
    ]);
  });

  it("devolve comparecimento e votos por cargo, com nomes", () => {
    const r = buscarSecao(secoes, 134, 18);
    expect(r).not.toBeNull();
    expect(r!.local).toBe(1155);
    const gov = r!.cargos.find((c) => c.codigo === 3)!;
    expect(gov.votos.reduce((s, v) => s + v.votos, 0)).toBe(gov.comparecimento!.comparecimento);
    expect(gov.votos.map((v) => v.nome)).toContain("JOÃO SANTANA"); // nome de urna
    expect(gov.votos.find((v) => v.numero === 95)!.nome).toBe("Brancos");
    expect(gov.votos.find((v) => v.numero === 96)!.nome).toBe("Nulos");
    // ordem: mais votado primeiro
    const votos = gov.votos.map((v) => v.votos);
    expect(votos).toEqual([...votos].sort((a, b) => b - a));
  });

  it("seção inexistente", () => {
    expect(buscarSecao(secoes, 134, 9999)).toBeNull();
    expect(buscarSecao(secoes, 1, 18)).toBeNull();
  });
});

describe("comparação histórica", () => {
  it("agrupa por eleição os partidos de um cargo majoritário", () => {
    const h = historicoPorCargo(dados.historico(), 1);
    expect(h.map((e) => `${e.ano}/${e.turno}`)).toEqual(["2018/1", "2022/1", "2022/2"]);
    for (const e of h) {
      expect(e.partidos.reduce((s, p) => s + (p.pct ?? 0), 0)).toBeCloseTo(100, 0);
      expect(e.comparecimento?.comparecimento).toBeGreaterThan(0);
    }
  });

  it("cargo sem disputa em um turno não aparece nesse turno", () => {
    // Governador de MG não teve 2º turno nos fixtures
    expect(historicoPorCargo(dados.historico(), 3).map((e) => `${e.ano}/${e.turno}`)).toEqual([
      "2018/1",
      "2022/1",
    ]);
  });
});
