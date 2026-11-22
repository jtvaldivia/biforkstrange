import type { ReactNode } from "react";

/** Ilustraciones de 72×72 para las tarjetas de decisión. */
export type DecisionArtKind =
  | "viaje"
  | "consultora"
  | "invertir"
  | "magister"
  | "puerta"
  | "negociar"
  | "quedarte"
  | "cohete"
  | "chanchito"
  | "casa"
  | "corazon"
  | "lupa"
  | "subir"
  | "laptop"
  | "pausa"
  | "libros"
  | "ia"
  | "caja"
  | "rubros"
  | "oficio"
  | "maletin"
  | "mapa"
  | "avion";

const T = { stroke: "var(--tinta)", strokeWidth: 2, strokeLinejoin: "round" as const };

const arts: Record<DecisionArtKind, { fondo: string; dibujo: ReactNode }> = {
  viaje: {
    fondo: "var(--acento-suave)",
    dibujo: (
      <>
        <circle cx="52" cy="20" r="10" fill="var(--sol)" {...T} />
        <path d="M14 44 L30 22 L34 44Z" fill="var(--papel)" {...T} />
        <path d="M0 50 C9 44 18 56 27 50 S45 44 54 50 S68 54 72 50 V72 H0Z" fill="var(--acento)" />
        <path d="M0 60 C9 55 18 65 27 60 S45 55 54 60 S68 63 72 60" fill="none" stroke="var(--papel)" strokeWidth="2" strokeLinecap="round" />
      </>
    ),
  },
  consultora: {
    fondo: "var(--niebla)",
    dibujo: (
      <>
        <rect x="6" y="38" width="16" height="34" fill="var(--control)" />
        <rect x="52" y="30" width="16" height="42" fill="var(--control)" />
        <rect x="22" y="12" width="30" height="62" fill="var(--papel)" {...T} />
        {[20, 33, 46, 59].flatMap((y) =>
          [28, 39].map((x) =>
            x === 39 && y === 33 ? (
              <rect key={`${x}-${y}`} x={x} y={y} width="7" height="7" fill="var(--sol)" stroke="var(--tinta)" strokeWidth="1.5" />
            ) : (
              <rect key={`${x}-${y}`} x={x} y={y} width="7" height="7" fill="var(--tinta)" />
            ),
          ),
        )}
      </>
    ),
  },
  invertir: {
    fondo: "var(--papel)",
    dibujo: (
      <>
        <path d="M8 60 H64 M8 44 H64 M8 28 H64" stroke="var(--linea)" strokeWidth="2" strokeLinecap="round" />
        <path d="M40 26 L52 46 L64 58" fill="none" stroke="var(--control)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="1 6" />
        <path d="M8 52 L20 40 L30 48 L40 26 L52 34 L64 12" fill="none" stroke="var(--dinero)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="40" cy="26" r="5" fill="var(--sol)" {...T} />
      </>
    ),
  },
  magister: {
    fondo: "var(--acento-suave)",
    dibujo: (
      <>
        <path d="M-2 64 L22 26 L36 48 L48 32 L74 64Z" fill="var(--control)" {...T} />
        <path d="M22 26 L15 37 L21 41 L25 36 L29 40 L31 40Z" fill="var(--papel)" {...T} />
        <rect x="0" y="62" width="72" height="10" fill="var(--papel)" />
        <path d="M38 16 L52 9 L66 16 L52 23Z" fill="var(--tinta)" />
        <path d="M45 20 V27 C49 30 55 30 59 27 V20" fill="var(--tinta)" />
        <path d="M66 16 V26" stroke="var(--tinta)" strokeWidth="2" strokeLinecap="round" />
        <circle cx="66" cy="27" r="2.5" fill="var(--sol)" stroke="var(--tinta)" strokeWidth="1.5" />
      </>
    ),
  },
  /** Cambiarte, renunciar: una puerta abierta y la flecha hacia afuera. */
  puerta: {
    fondo: "var(--acento-suave)",
    dibujo: (
      <>
        <rect x="12" y="12" width="28" height="54" fill="var(--papel)" {...T} />
        <path d="M12 12 L28 18 V70 L12 66Z" fill="var(--control)" {...T} />
        <circle cx="24" cy="44" r="2.5" fill="var(--sol)" stroke="var(--tinta)" strokeWidth="1.5" />
        <path d="M38 40 H62 M54 32 L62 40 L54 48" fill="none" stroke="var(--acento)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      </>
    ),
  },
  /** Negociar, pedir: dos globos de diálogo y el visto bueno. */
  negociar: {
    fondo: "var(--niebla)",
    dibujo: (
      <>
        <path d="M14 34 L12 46 L26 35" fill="var(--papel)" {...T} />
        <rect x="6" y="10" width="40" height="26" rx="8" fill="var(--papel)" {...T} />
        <path d="M14 20 H38 M14 27 H30" stroke="var(--control)" strokeWidth="3" strokeLinecap="round" />
        <path d="M58 60 L60 70 L48 61" fill="var(--sol)" {...T} />
        <rect x="26" y="38" width="40" height="24" rx="8" fill="var(--sol)" {...T} />
        <path d="M37 50 L43 56 L56 44" fill="none" stroke="var(--tinta)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      </>
    ),
  },
  /** Quedarte: tu escritorio de siempre, con su planta. */
  quedarte: {
    fondo: "var(--papel)",
    dibujo: (
      <>
        <path d="M2 58 H70" stroke="var(--linea)" strokeWidth="2" />
        <rect x="10" y="20" width="32" height="22" rx="3" fill="var(--acento-suave)" {...T} />
        <path d="M26 42 V52 M18 52 H34" stroke="var(--tinta)" strokeWidth="2" strokeLinecap="round" />
        <rect x="4" y="52" width="46" height="6" fill="var(--control)" {...T} />
        <path d="M59 44 C55 36 50 34 48 27 C55 28 58 34 59 44 C60 34 64 28 70 26 C68 34 63 38 59 44Z" fill="var(--dinero)" {...T} />
        <path d="M52 58 L54 44 H64 L66 58Z" fill="var(--bienestar)" {...T} />
      </>
    ),
  },
  /** Emprender, startup. */
  cohete: {
    fondo: "var(--acento-suave)",
    dibujo: (
      <>
        <path d="M26 34 L17 48 L27 45Z M46 34 L55 48 L45 45Z" fill="var(--control)" {...T} />
        <path d="M30 46 C30 55 36 60 36 66 C36 60 42 55 42 46Z" fill="var(--sol)" {...T} />
        <path d="M36 6 C47 14 49 30 46 46 H26 C23 30 25 14 36 6Z" fill="var(--papel)" {...T} />
        <circle cx="36" cy="25" r="5" fill="var(--acento)" {...T} />
      </>
    ),
  },
  /** Ahorrar, financiar. */
  chanchito: {
    fondo: "var(--niebla)",
    dibujo: (
      <>
        <circle cx="38" cy="13" r="7" fill="var(--papel)" {...T} />
        <path d="M38 9 V17" stroke="var(--dinero)" strokeWidth="2" strokeLinecap="round" />
        <path d="M22 54 V63 H28 V56 M44 56 V63 H50 V54" fill="var(--sol)" {...T} />
        <path d="M23 33 L25 23 L33 30" fill="var(--sol)" {...T} />
        <ellipse cx="36" cy="44" rx="22" ry="15" fill="var(--sol)" {...T} />
        <rect x="54" y="38" width="9" height="10" rx="3" fill="var(--sol)" {...T} />
        <circle cx="46" cy="38" r="2" fill="var(--tinta)" />
        <path d="M31 31 H42" stroke="var(--tinta)" strokeWidth="2.5" strokeLinecap="round" />
      </>
    ),
  },
  /** Vivienda, familia, cuidar. */
  casa: {
    fondo: "var(--acento-suave)",
    dibujo: (
      <>
        <rect x="16" y="34" width="40" height="30" fill="var(--papel)" {...T} />
        <path d="M8 36 L36 12 L64 36Z" fill="var(--bienestar)" {...T} />
        <rect x="31" y="46" width="11" height="18" fill="var(--sol)" {...T} />
        <rect x="20" y="42" width="8" height="8" fill="var(--acento)" stroke="var(--tinta)" strokeWidth="1.5" />
        <rect x="46" y="42" width="8" height="8" fill="var(--acento)" stroke="var(--tinta)" strokeWidth="1.5" />
        <path d="M2 64 H70" stroke="var(--tinta)" strokeWidth="2" strokeLinecap="round" />
      </>
    ),
  },
  /** Salud, pareja. */
  corazon: {
    fondo: "var(--niebla)",
    dibujo: (
      <>
        <path d="M36 60 C14 46 8 34 12 24 C16 14 30 12 36 24 C42 12 56 14 60 24 C64 34 58 46 36 60Z" fill="var(--vida)" {...T} />
        <path d="M16 36 H28 L32 28 L38 44 L42 36 H56" fill="none" stroke="var(--papel)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      </>
    ),
  },
  /** Buscar trabajo. */
  lupa: {
    fondo: "var(--acento-suave)",
    dibujo: (
      <>
        <rect x="10" y="10" width="34" height="46" rx="3" fill="var(--papel)" {...T} />
        <path d="M17 20 H37 M17 28 H37 M17 36 H29" stroke="var(--control)" strokeWidth="3" strokeLinecap="round" />
        <path d="M51 51 L64 64" stroke="var(--tinta)" strokeWidth="6" strokeLinecap="round" />
        <circle cx="42" cy="42" r="13" fill="var(--sol)" stroke="var(--tinta)" strokeWidth="3" />
      </>
    ),
  },
  /** Ascender, pedir aumento. */
  subir: {
    fondo: "var(--papel)",
    dibujo: (
      <>
        <path d="M6 64 H22 V50 H38 V36 H54 V22 H66 V64Z" fill="var(--acento-suave)" {...T} />
        <path d="M12 42 L38 16 M26 16 H38 V28" fill="none" stroke="var(--acento)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="60" cy="13" r="5" fill="var(--sol)" {...T} />
      </>
    ),
  },
  /** Aprender, IA, trabajo remoto. */
  laptop: {
    fondo: "var(--niebla)",
    dibujo: (
      <>
        <rect x="12" y="14" width="48" height="32" rx="3" fill="var(--papel)" {...T} />
        <path d="M18 24 L24 29 L18 34 M28 36 H40" fill="none" stroke="var(--acento)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M4 56 L12 46 H60 L68 56Z" fill="var(--control)" {...T} />
        <path d="M52 19 L54 24 L59 26 L54 28 L52 33 L50 28 L45 26 L50 24Z" fill="var(--sol)" stroke="var(--tinta)" strokeWidth="1.5" strokeLinejoin="round" />
      </>
    ),
  },
  /** No, esperar: un reloj de arena. */
  pausa: {
    fondo: "var(--niebla)",
    dibujo: (
      <>
        <path d="M24 12 C24 28 34 30 34 36 C34 42 24 44 24 60 H48 C48 44 38 42 38 36 C38 30 48 28 48 12Z" fill="var(--acento-suave)" {...T} />
        <path d="M30 20 H42 C40 26 37 28 36 30 C35 28 32 26 30 20Z" fill="var(--sol)" />
        <path d="M28 58 C30 51 34 48 36 46 C38 48 42 51 44 58Z" fill="var(--sol)" stroke="var(--tinta)" strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M20 10 H52 M20 62 H52" stroke="var(--tinta)" strokeWidth="3" strokeLinecap="round" />
      </>
    ),
  },
  /** Doctorado: una pila de libros y una medalla. */
  libros: {
    fondo: "var(--acento-suave)",
    dibujo: (
      <>
        <rect x="10" y="50" width="52" height="12" fill="var(--control)" {...T} />
        <rect x="14" y="38" width="44" height="12" fill="var(--papel)" {...T} />
        <rect x="8" y="26" width="46" height="12" fill="var(--acento)" {...T} />
        <path d="M20 50 V62 M48 38 V50 M18 26 V38" stroke="var(--tinta)" strokeWidth="2" />
        <path d="M51 21 L47 30 M59 21 L63 30" stroke="var(--tinta)" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="55" cy="16" r="7" fill="var(--sol)" {...T} />
      </>
    ),
  },
  /** Aprender a trabajar con IA: un chip con un destello. */
  ia: {
    fondo: "var(--niebla)",
    dibujo: (
      <>
        <path d="M28 12 V20 M36 12 V20 M44 12 V20 M28 52 V60 M36 52 V60 M44 52 V60 M12 28 H20 M12 36 H20 M12 44 H20 M52 28 H60 M52 36 H60 M52 44 H60" stroke="var(--tinta)" strokeWidth="2.5" strokeLinecap="round" />
        <rect x="20" y="20" width="32" height="32" rx="4" fill="var(--papel)" {...T} />
        <rect x="28" y="28" width="16" height="16" rx="2" fill="var(--acento)" />
        <path d="M60 3 L62 9 L68 11 L62 13 L60 19 L58 13 L52 11 L58 9Z" fill="var(--sol)" stroke="var(--tinta)" strokeWidth="1.5" strokeLinejoin="round" />
      </>
    ),
  },
  /** Renunciar: la caja con tus cosas. */
  caja: {
    fondo: "var(--acento-suave)",
    dibujo: (
      <>
        <rect x="22" y="16" width="14" height="20" fill="var(--papel)" {...T} />
        <path d="M46 36 V18" stroke="var(--dinero)" strokeWidth="3" strokeLinecap="round" />
        <path d="M46 26 C40 24 38 18 40 13 C46 15 48 21 46 26Z" fill="var(--dinero)" stroke="var(--tinta)" strokeWidth="1.5" />
        <path d="M46 22 C52 20 54 14 52 9 C46 11 44 17 46 22Z" fill="var(--dinero)" stroke="var(--tinta)" strokeWidth="1.5" />
        <rect x="12" y="34" width="48" height="30" fill="var(--control)" {...T} />
        <path d="M12 34 L5 25 H21 L26 34" fill="var(--papel)" {...T} />
        <path d="M60 34 L67 25 H51 L46 34" fill="var(--papel)" {...T} />
        <rect x="28" y="44" width="16" height="8" fill="var(--papel)" stroke="var(--tinta)" strokeWidth="1.5" />
      </>
    ),
  },
  /** Cambiar de rubro: de un edificio a otro. */
  rubros: {
    fondo: "var(--papel)",
    dibujo: (
      <>
        <rect x="6" y="38" width="20" height="28" fill="var(--control)" {...T} />
        <path d="M11 45 H15 M17 45 H21 M11 53 H15 M17 53 H21" stroke="var(--papel)" strokeWidth="3" />
        <rect x="44" y="24" width="22" height="42" fill="var(--papel)" {...T} />
        {[31, 40, 49].flatMap((y) => [49, 57].map((x) => (
          <rect key={`${x}-${y}`} x={x} y={y} width="5" height="5" fill={x === 57 && y === 40 ? "var(--sol)" : "var(--tinta)"} />
        )))}
        <path d="M16 32 C20 14 34 10 42 14" fill="none" stroke="var(--acento)" strokeWidth="4" strokeLinecap="round" />
        <path d="M35 8 L43 14 L36 21" fill="none" stroke="var(--acento)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M2 66 H70" stroke="var(--tinta)" strokeWidth="2" strokeLinecap="round" />
      </>
    ),
  },
  /** Cambiar de oficio: dos herramientas cruzadas. */
  oficio: {
    fondo: "var(--niebla)",
    dibujo: (
      <>
        <g transform="rotate(-45 36 36)">
          <rect x="32" y="22" width="8" height="40" rx="4" fill="var(--control)" {...T} />
          <circle cx="36" cy="16" r="10" fill="var(--control)" {...T} />
          <rect x="32" y="4" width="8" height="11" fill="var(--niebla)" />
        </g>
        <g transform="rotate(45 36 36)">
          <rect x="30" y="8" width="12" height="44" fill="var(--sol)" {...T} />
          <rect x="30" y="8" width="12" height="7" fill="var(--vida)" {...T} />
          <path d="M30 52 L36 65 L42 52Z" fill="var(--papel)" {...T} />
        </g>
      </>
    ),
  },
  /** Trabajar por tu cuenta: un maletín propio. */
  maletin: {
    fondo: "var(--acento-suave)",
    dibujo: (
      <>
        <path d="M27 24 V17 C27 15 28 14 30 14 H42 C44 14 45 15 45 17 V24" fill="none" stroke="var(--tinta)" strokeWidth="3" />
        <rect x="10" y="24" width="52" height="36" rx="4" fill="var(--control)" {...T} />
        <path d="M10 38 H62" stroke="var(--tinta)" strokeWidth="2" />
        <rect x="31" y="34" width="10" height="8" rx="1.5" fill="var(--sol)" stroke="var(--tinta)" strokeWidth="1.5" />
      </>
    ),
  },
  /** Mudarte de región: un mapa y un pin. */
  mapa: {
    fondo: "var(--papel)",
    dibujo: (
      <>
        <path d="M8 20 L26 14 L46 20 L64 14 V56 L46 62 L26 56 L8 62Z" fill="var(--acento-suave)" {...T} />
        <path d="M26 14 V56 M46 20 V62" stroke="var(--tinta)" strokeWidth="2" />
        <path d="M14 52 C24 46 30 50 36 42 S46 34 50 32" fill="none" stroke="var(--acento)" strokeWidth="3" strokeLinecap="round" strokeDasharray="1 6" />
        <path d="M54 36 C48 28 46 24 46 20 A8 8 0 0 1 62 20 C62 24 60 28 54 36Z" fill="var(--vida)" {...T} />
        <circle cx="54" cy="20" r="3" fill="var(--papel)" />
      </>
    ),
  },
  /** Irte a otro país: un avión que despega. */
  avion: {
    fondo: "var(--acento-suave)",
    dibujo: (
      <>
        <path d="M4 62 C10 60 14 58 18 56" fill="none" stroke="var(--acento)" strokeWidth="3" strokeLinecap="round" strokeDasharray="1 6" />
        <path d="M16 47 L11 34 H18 L25 43Z" fill="var(--control)" {...T} />
        <path d="M14 48 L58 28 C63 26 67 28 65 31 L24 52 H16Z" fill="var(--papel)" {...T} />
        <path d="M34 41 L29 58 H37 L46 36Z" fill="var(--control)" {...T} />
        <circle cx="58" cy="12" r="7" fill="var(--sol)" {...T} />
      </>
    ),
  },
};

/** `llenar`: ocupa todo su contenedor (las tarjetas grandes) y el fondo cubre lo que sobra a los lados. */
export function DecisionArt({ kind, llenar = false }: { kind: DecisionArtKind; llenar?: boolean }) {
  const { fondo, dibujo } = arts[kind] ?? arts.consultora;
  return (
    <svg
      viewBox="0 0 72 72"
      width={llenar ? "100%" : 68}
      height={llenar ? "100%" : 68}
      preserveAspectRatio="xMidYMid meet"
      aria-hidden="true"
      style={{ display: "block", background: fondo }}
    >
      <rect width="72" height="72" fill={fondo} />
      {dibujo}
    </svg>
  );
}
