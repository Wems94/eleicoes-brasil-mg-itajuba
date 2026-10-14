import path from "node:path";
import { describe, expect, it } from "vitest";

import { SnapshotsDados } from "./dados";
import { buscarSecao, historicoPorCargo, secoesDisponiveis, comparecimentoPorEleicao, resumoHistorico, variacaoPrimeiroTurno } from "./itajuba";

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

describe("comparação histórica", () => {
  const p = (ano: number, turno: number, cargo: number, partido: string, votos: number, pct: number) => ({
    ano,
    turno,
    cargo,
    nome_cargo: "x",
    partido,
    votos,
    pct,
  });
  const c = (ano: number, turno: number, cargo: number, pctc: number) => ({
    ano,
    turno,
    cargo,
    nome_cargo: "x",
    aptos: 100,
    comparecimento: pctc,
    abstencoes: 100 - pctc,
    brancos: 0,
    nulos: 0,
    pct_comparecimento: pctc,
    pct_abstencao: 100 - pctc,
  });
  const h = {
    partidos: [
      p(2018, 1, 1, "PT", 450, 45.62), p(2018, 1, 1, "PL", 420, 42.77), p(2018, 1, 1, "PSOL", 10, 1),
      p(2022, 1, 1, "PT", 460, 46.8), p(2022, 1, 1, "PL", 400, 40.39),
      p(2022, 2, 1, "PL", 512, 53.06), p(2022, 2, 1, "PT", 453, 46.94),
      p(2018, 1, 3, "NOVO", 587, 61.66), p(2022, 1, 3, "NOVO", 512, 58.99),
    ],
    comparecimento: [c(2018, 1, 1, 77.91), c(2018, 1, 3, 77.91), c(2022, 1, 1, 78.28), c(2022, 2, 1, 78.62)],
  };

  it("variação entre os dois últimos 1º turnos, só partidos presentes nos dois", () => {
    const v = variacaoPrimeiroTurno(historicoPorCargo(h, 1))!;
    expect([v.de, v.para]).toEqual([2018, 2022]);
    expect(v.partidos).toEqual([
      { partido: "PT", antes: 45.62, depois: 46.8, delta: 1.18 },
      { partido: "PL", antes: 42.77, depois: 40.39, delta: -2.38 },
    ]);
    expect(variacaoPrimeiroTurno(historicoPorCargo(h, 3).slice(0, 1))).toBeNull();
  });

  it("comparecimento uma vez por eleição", () => {
    expect(comparecimentoPorEleicao(h).map((x) => `${x.ano}/${x.turno}:${x.cargo}`)).toEqual([
      "2018/1:1",
      "2022/1:1",
      "2022/2:1",
    ]);
  });

  it("frase-resumo a partir dos dados", () => {
    expect(resumoHistorico(h)).toBe(
      "PL liderou para Presidente em 2022 (2º turno) com 53,06%. NOVO liderou para Governador em todas as eleições. O comparecimento variou entre 77,91% e 78,62%.",
    );
  });
});
