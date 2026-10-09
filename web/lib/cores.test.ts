import { describe, expect, it } from "vitest";

import { corDaPosicao, coresPorEntidade } from "./cores";

describe("cores dos candidatos", () => {
  it("três cores de série e o resto em 'outros'", () => {
    expect(corDaPosicao(0).fundo).toBe("var(--color-serie-1)");
    expect(corDaPosicao(2).fundo).toBe("var(--color-serie-3)");
    expect(corDaPosicao(3).fundo).toBe("var(--color-serie-outros)");
    expect(corDaPosicao(-1).fundo).toBe("var(--color-serie-outros)");
  });

  it("a cor segue a entidade, mesmo que ela apareça de novo", () => {
    const m = coresPorEntidade(["PT", "PL", "PT", "MDB", "NOVO"]);
    expect(m.get("PT")).toEqual(corDaPosicao(0));
    expect(m.get("PL")).toEqual(corDaPosicao(1));
    expect(m.get("MDB")).toEqual(corDaPosicao(2));
    expect(m.get("NOVO")).toEqual(corDaPosicao(3));
  });
});
