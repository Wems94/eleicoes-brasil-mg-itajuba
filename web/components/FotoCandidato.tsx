import type { Cor } from "@/lib/partidos";

/**
 * Foto oficial de divulgação do TSE, só para candidatos a Presidente. Sem foto
 * publicada, mostra as iniciais num círculo na cor do partido.
 */
export function FotoCandidato({
  src,
  nome,
  cor,
  tamanho = 40,
}: {
  src: string | null;
  nome: string;
  cor?: Cor;
  tamanho?: number;
}) {
  const estilo = { width: tamanho, height: tamanho };
  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- export estático, sem otimizador
      <img
        src={src}
        alt={nome}
        width={tamanho}
        height={tamanho}
        loading="lazy"
        className="shrink-0 rounded-full bg-realce object-cover object-top"
        style={{ ...estilo, boxShadow: cor ? `0 0 0 2px ${cor.fundo}` : undefined }}
      />
    );
  }
  return (
    <span
      role="img"
      aria-label={nome}
      className="flex shrink-0 items-center justify-center rounded-full text-xs font-semibold"
      style={{ ...estilo, background: cor?.fundo ?? "var(--color-realce)", color: cor?.texto }}
    >
      {iniciais(nome)}
    </span>
  );
}

export function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter((p) => p.length > 2 || /^[A-ZÀ-Ú]/.test(p));
  const letras = [partes[0], partes.length > 1 ? partes[partes.length - 1] : undefined]
    .filter(Boolean)
    .map((p) => p![0]);
  return letras.join("").toUpperCase() || "?";
}

/** URL pública de uma foto do snapshot (`fotos/{ano}/{numero}.jpg`). */
export const urlFoto = (caminho: string | null | undefined): string | null =>
  caminho ? `/dados/${caminho}` : null;
