import { describe, expect, it } from "vitest";

import {
  FAIXAS_ABSTENCAO,
  FAIXAS_VENCEDOR,
  NEUTRO,
  PALETA,
  contraste,
  corAbstencao,
  corBase,
  corIntensidade,
  corReserva,
  coresDaDisputa,
  deOklab,
  deltaE,
  DELTA_MINIMO,
  faixa,
  paraOklab,
  rotuloFaixas,
  textoSobre,
} from "./partidos";

describe("cor por partido", () => {
  it("usa a paleta pela sigla", () => {
    expect(corBase("PT")).toBe(PALETA.PT);
    expect(corBase("UNIÃO")).toBe(PALETA["UNIÃO"]);
  });

  it("partido sem cor recebe reserva determinística, longe dos neutros", () => {
    const a = corReserva("PARTIDO NOVO 2030");
    expect(corBase("PARTIDO NOVO 2030")).toBe(a);
    expect(corReserva("PARTIDO NOVO 2030")).toBe(a);
    expect(corReserva("OUTRO")).not.toBe(a);
    for (const n of [NEUTRO.semDados.claro, NEUTRO.empate.claro]) {
      expect(deltaE(a, n)).toBeGreaterThan(DELTA_MINIMO);
    }
  });

  it("OKLab ida e volta preserva a cor", () => {
    for (const hex of Object.values(PALETA)) expect(deOklab(paraOklab(hex))).toBe(hex);
  });
});

describe("distinção entre concorrentes", () => {
  it("dois azuis próximos são afastados; o mais votado não muda", () => {
    expect(deltaE(PALETA["UNIÃO"], PALETA.PP)).toBeLessThan(DELTA_MINIMO);
    const cores = coresDaDisputa(["UNIÃO", "PP"]);
    expect(cores.get("UNIÃO")!.fundo).toBe(PALETA["UNIÃO"]);
    expect(deltaE(cores.get("UNIÃO")!.fundo, cores.get("PP")!.fundo)).toBeGreaterThanOrEqual(
      DELTA_MINIMO,
    );
    // o matiz é mantido: só a luminosidade muda
    const [, a1, b1] = paraOklab(PALETA.PP);
    const [, a2, b2] = paraOklab(cores.get("PP")!.fundo);
    expect(Math.atan2(b2, a2)).toBeCloseTo(Math.atan2(b1, a1), 1);
  });

  it("partidos distantes ficam com a cor da paleta", () => {
    const cores = coresDaDisputa(["PT", "PL", "NOVO"]);
    expect([...cores.values()].map((c) => c.fundo)).toEqual([PALETA.PT, PALETA.PL, PALETA.NOVO]);
  });

  it("todos os pares de uma disputa grande ficam distinguíveis", () => {
    const siglas = ["PT", "PC do B", "PL", "UNIÃO", "PSDB", "PP", "MDB", "PV", "PSB", "PSOL"];
    const cores = [...coresDaDisputa(siglas).values()].map((c) => c.fundo);
    for (let i = 0; i < cores.length; i++)
      for (let j = i + 1; j < cores.length; j++)
        expect(deltaE(cores[i], cores[j])).toBeGreaterThanOrEqual(DELTA_MINIMO * 0.999);
  });

  it("repetir a sigla não muda a cor", () => {
    const cores = coresDaDisputa(["PT", "PL", "PT"]);
    expect(cores.size).toBe(2);
  });
});

describe("contraste do texto", () => {
  it("texto escuro sobre cor clara e claro sobre cor escura", () => {
    expect(textoSobre("#f2b705")).toBe("#000000");
    expect(textoSobre(PALETA.PL)).toBe("#ffffff");
  });

  it("todas as cores (paleta, ajustadas e reservas) passam de 4,5:1", () => {
    const fundos = [
      ...Object.values(PALETA),
      ...[...coresDaDisputa(Object.keys(PALETA)).values()].map((c) => c.fundo),
      ...["A", "B", "XYZ", "PARTIDO 99"].map(corReserva),
    ];
    for (const f of fundos) expect(contraste(f, textoSobre(f))).toBeGreaterThanOrEqual(4.5);
  });
});

describe("faixas do mapa", () => {
  it("faixa do vencedor", () => {
    expect([45, 50, 59.9, 60, 70, 99].map((p) => faixa(p, FAIXAS_VENCEDOR))).toEqual([
      0, 1, 1, 2, 3, 3,
    ]);
  });

  it("intensidade cresce com o percentual, nos dois temas", () => {
    for (const tema of ["claro", "escuro"] as const) {
      const sup = tema === "claro" ? "#ffffff" : "#1a1a19";
      const d = [45, 55, 65, 75].map((p) => deltaE(corIntensidade(PALETA.PT, p, tema), sup));
      expect(d).toEqual([...d].sort((a, b) => a - b));
      expect(corIntensidade(PALETA.PT, 75, tema)).toBe(PALETA.PT);
    }
  });

  it("abstenção em faixas fixas", () => {
    expect(corAbstencao(10)).not.toBe(corAbstencao(16));
    expect(corAbstencao(31)).toBe(corAbstencao(45));
    expect(rotuloFaixas(FAIXAS_ABSTENCAO)).toEqual(["< 15%", "15–20%", "20–25%", "25–30%", "≥ 30%"]);
  });
});
