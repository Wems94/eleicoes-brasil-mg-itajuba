import { describe, expect, it } from "vitest";

import { dataGeracao, nomeTurno, numero, pct } from "./formato";

describe("formato pt-BR", () => {
  it("números com separador de milhar", () => {
    expect(numero(56104503)).toBe("56.104.503");
    expect(numero(0)).toBe("0");
  });

  it("percentual com duas casas e vírgula", () => {
    expect(pct(47.03)).toBe("47,03%");
    expect(pct(0.1)).toBe("0,10%");
    expect(pct(null)).toBe("—");
  });

  it("nome do turno", () => {
    expect(nomeTurno(1)).toBe("1º turno");
    expect(nomeTurno(2)).toBe("2º turno");
  });

  it("data de geração no fuso de Brasília", () => {
    expect(dataGeracao("2026-10-09T20:00:00+00:00")).toBe("09/10/2026, 17:00");
  });
});
