import { describe, expect, it } from "vitest";

import {
  type EstadoMapa,
  caixasPorUf,
  corDoMunicipio,
  coresPorRecorte,
  escreverHash,
  legendaFaixas,
  legendaVencedores,
  lerHash,
  unirCaixas,
} from "./mapa";
import { NEUTRO, PALETA, corAbstencao, corIntensidade } from "./partidos";
import { CARGOS_MAPA, type CamadaMapa } from "./tipos";

const camada = (cargo: CamadaMapa["cargo"], municipios: CamadaMapa["municipios"]): CamadaMapa => ({
  ano: 2022,
  turno: 1,
  cargo,
  nome: cargo,
  por: "candidato",
  votaveis: [
    { chave: "1", numero: 13, nome: "A", partido: "PT" },
    { chave: "2", numero: 22, nome: "B", partido: "PL" },
    { chave: "3", numero: 44, nome: "C", partido: "UNIÃO" },
    { chave: "4", numero: 11, nome: "D", partido: "PP" },
  ],
  municipios,
  ufs: {},
  exterior: null,
});
const UF: Record<string, string> = { "1": "MG", "2": "MG", "3": "SP", "4": "SP", "5": "SP" };

describe("cores do mapa", () => {
  it("Presidente: uma disputa nacional; município colorido pela intensidade", () => {
    const c = camada("presidente", { "1": [0, 6200, 2000], "2": [1, 5100, 1800] });
    const cores = coresPorRecorte(c, (k) => UF[k]);
    expect([...cores.keys()]).toEqual(["BR"]);
    expect(corDoMunicipio(c.municipios["1"], "vencedor", cores.get("BR"), "claro")).toBe(
      corIntensidade(PALETA.PT, 62, "claro"),
    );
  });

  it("Governador: uma disputa por UF; concorrentes próximos afastados só dentro da UF", () => {
    const c = camada("governador", { "3": [2, 6000, 0], "4": [3, 5500, 0], "1": [3, 7000, 0] });
    const cores = coresPorRecorte(c, (k) => UF[k]);
    expect(cores.get("SP")!.get(2)!.fundo).not.toBe(cores.get("SP")!.get(3)!.fundo);
    expect(cores.get("MG")!.get(3)!.fundo).toBe(PALETA.PP); // em MG o PP não tem vizinho
  });

  it("empate, sem dados e abstenção", () => {
    const c = camada("presidente", { "1": [-1, 5000, 2100] });
    const cores = coresPorRecorte(c, (k) => UF[k]);
    expect(corDoMunicipio(c.municipios["1"], "vencedor", cores.get("BR"), "claro")).toBe(NEUTRO.empate.claro);
    expect(corDoMunicipio(undefined, "vencedor", cores.get("BR"), "escuro")).toBe(NEUTRO.semDados.escuro);
    expect(corDoMunicipio(c.municipios["1"], "abstencao", undefined, "claro")).toBe(corAbstencao(21, "claro"));
  });

  it("legenda lista os vencedores com a cor usada no mapa", () => {
    const c = camada("presidente", { "1": [0, 6200, 0], "2": [1, 5100, 0], "3": [0, 5000, 0] });
    const leg = legendaVencedores(c, coresPorRecorte(c, (k) => UF[k]), null);
    expect(leg.map((l) => [l.rotulo, l.detalhe])).toEqual([
      ["A", "PT"],
      ["B", "PL"],
    ]);
    expect(legendaFaixas("abstencao", "claro").map((l) => l.rotulo)).toEqual([
      "< 15%",
      "15–20%",
      "20–25%",
      "25–30%",
      "≥ 30%",
    ]);
  });
});

describe("estado na URL", () => {
  const padrao: EstadoMapa = { cargo: "presidente", camada: "vencedor", uf: null, mun: null };

  it("ida e volta", () => {
    const e: EstadoMapa = { cargo: "senador", camada: "abstencao", uf: "MG", mun: "3132404" };
    const h = escreverHash(e, padrao);
    expect(h).toBe("#cargo=senador&camada=abstencao&uf=MG&mun=3132404");
    expect(lerHash(h, padrao, CARGOS_MAPA)).toEqual(e);
  });

  it("estado padrão não suja a URL; valores inválidos são ignorados", () => {
    expect(escreverHash(padrao, padrao)).toBe("");
    expect(lerHash("#cargo=prefeito&camada=x&uf=mg&mun=12", padrao, CARGOS_MAPA)).toEqual(padrao);
  });

  it("cargo sem camada no turno cai no padrão", () => {
    expect(lerHash("#cargo=senador", padrao, ["presidente", "governador"]).cargo).toBe("presidente");
  });
});

describe("enquadramento", () => {
  it("caixa por UF a partir de polígonos e multipolígonos", () => {
    const caixas = caixasPorUf([
      { properties: { uf: "MG" }, geometry: { type: "Polygon", coordinates: [[[-45, -22], [-44, -21], [-45, -21]]] } },
      {
        properties: { uf: "MG" },
        geometry: { type: "MultiPolygon", coordinates: [[[[-43, -20], [-42, -19], [-43, -19]]]] },
      },
      { properties: { uf: null }, geometry: { type: "Polygon", coordinates: [[[0, 0], [1, 1], [0, 1]]] } },
    ]);
    expect(caixas.get("MG")).toEqual([-45, -22, -42, -19]);
    expect(caixas.size).toBe(1);
    expect(unirCaixas([[-1, -1, 0, 0], [0, 0, 2, 3]])).toEqual([-1, -1, 2, 3]);
  });
});
