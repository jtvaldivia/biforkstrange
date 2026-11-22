import "./apuesta.css";
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";

/**
 * Esperas con animaciones de apuestas: ruleta, tragamonedas, carrera de caballos, dado y naipes.
 * Cada sorteo muestra un solo juego: gira unos 2,5 s, se frena y se queda quieto en su resultado.
 * Si después siguen las esperas, solo rotan las frases.
 * El resultado sale de Math.random: es decoración y no dice nada de la simulación.
 */
export type Variante = "ruleta" | "tragamonedas" | "caballos" | "dado" | "naipes";

const ORDEN: Variante[] = ["ruleta", "tragamonedas", "caballos", "dado", "naipes"];

/**
 * Un sorteo: qué juego, su resultado y cuándo empezó a girar.
 * Las esperas encadenadas (cargando → Pensando) son el mismo sorteo: mientras haya una montada,
 * o se haya desmontado hace menos de PEGA_MS, la siguiente toma este y sigue desde donde iba.
 */
type Sorteo = { variante: Variante; azar: [number, number]; inicio: number };

const PEGA_MS = 1500;
let turno = 0;
let actual: Sorteo | null = null;
let montadas = 0;
let pegadoHasta = 0;

const ahora = () => performance.now();
const nuevoSorteo = (variante: Variante): Sorteo => ({ variante, azar: [Math.random(), Math.random()], inicio: ahora() });

function tomarSorteo(): Sorteo {
  const t = ahora();
  if (actual && (montadas > 0 || t < pegadoHasta)) return actual;
  actual = nuevoSorteo(ORDEN[turno++ % ORDEN.length]);
  // También cubre el doble render de StrictMode, que llama al inicializador antes de montar.
  pegadoHasta = t + PEGA_MS;
  return actual;
}

const cual = (azar: number, n: number) => Math.min(n - 1, Math.floor(azar * n));

const T = { stroke: "var(--tinta)", strokeWidth: 2, strokeLinejoin: "round" as const };
const FONDO = { x: 2, y: 2, width: 156, height: 116, rx: 18, ...T };

type Escena = (p: { azar: [number, number] }) => ReactNode;

/* Ruleta: 12 casillas de seis colores, sin dos iguales juntas. La rueda y la bola se frenan,
   la bola cae en la casilla que quedó bajo la flecha; esa casilla crece y las demás se apagan. */
const CX = 80;
const CY = 61;
const punto = (r: number, grados: number) => {
  const a = ((grados - 90) * Math.PI) / 180;
  return `${(CX + r * Math.cos(a)).toFixed(2)} ${(CY + r * Math.sin(a)).toFixed(2)}`;
};
const TONOS = ["var(--vida)", "var(--acento)", "var(--sol)", "var(--dinero)", "var(--bienestar)", "var(--violeta)"];
const CASILLAS = Array.from({ length: 12 }, (_, i) => ({
  d: `M${CX} ${CY} L${punto(42, i * 30)} A42 42 0 0 1 ${punto(42, (i + 1) * 30)}Z`,
  fill: TONOS[i % TONOS.length],
}));

const Ruleta: Escena = ({ azar }) => {
  const g = cual(azar[0], CASILLAS.length);
  const giro = 360 - (g * 30 + 15);
  return (
    <>
      <rect {...FONDO} fill="var(--acento-suave)" />
      <circle cx={CX} cy={CY} r="49" fill="var(--tinta)" {...T} />
      <g className="ap-ruleta-rueda" style={{ transform: `rotate(${giro}deg)` }}>
        <circle cx={CX} cy={CY} r="42" fill="var(--papel)" />
        <g className="ap-ruleta-otras">
          {CASILLAS.map((c, i) => i !== g && <path key={i} d={c.d} fill={c.fill} stroke="var(--tinta)" strokeWidth="1.5" strokeLinejoin="round" />)}
        </g>
        <path className="ap-ruleta-realce" d={CASILLAS[g].d} fill={CASILLAS[g].fill} stroke="var(--tinta)" strokeWidth="3" strokeLinejoin="round" />
        <circle cx={CX} cy={CY} r="18" fill="var(--papel)" {...T} />
        <path d={`M${CX - 11} ${CY} H${CX + 11} M${CX} ${CY - 11} V${CY + 11}`} stroke="var(--tinta)" strokeWidth="3" strokeLinecap="round" />
        <circle cx={CX} cy={CY} r="5" fill="var(--sol)" {...T} />
      </g>
      <g className="ap-ruleta-bola">
        <g className="ap-ruleta-cae">
          <circle cx={CX} cy={CY - 45.5} r="3.6" fill="var(--papel)" stroke="var(--tinta)" strokeWidth="1.5" />
        </g>
      </g>
      <path d={`M${CX - 6} 3 H${CX + 6} L${CX} 14Z`} fill="var(--sol)" {...T} />
    </>
  );
};

/* Tragamonedas: los rodillos se detienen uno por uno en el mismo símbolo y la línea se marca. */
const SIMBOLOS: ((y: number) => ReactNode)[] = [
  (y) => <circle cx="12" cy={y} r="8" fill="var(--sol)" {...T} />,
  (y) => <path d={`M12 ${y - 9} L20 ${y} L12 ${y + 9} L4 ${y}Z`} fill="var(--acento)" {...T} />,
  (y) => <rect x="3" y={y - 5} width="18" height="10" rx="3" fill="var(--tinta)" />,
  (y) => <path d={`M12 ${y - 8} L20 ${y + 7} H4Z`} fill="var(--bienestar)" {...T} />,
];
const PASO = 34;
/* El rodillo recorre VUELTAS símbolos y termina en el último; hay uno más abajo para el rebote. */
const VUELTAS = 8;

function tira(inicio: number, final: number) {
  return Array.from({ length: VUELTAS + 2 }, (_, n) =>
    n === VUELTAS ? final : n === VUELTAS + 1 ? (final + 1) % SIMBOLOS.length : (inicio + n) % SIMBOLOS.length,
  );
}

const Tragamonedas: Escena = ({ azar }) => {
  const s = cual(azar[0], SIMBOLOS.length);
  return (
    <>
      <rect {...FONDO} fill="var(--acento-suave)" />
      <rect x="22" y="12" width="104" height="96" rx="14" fill="var(--vida)" {...T} />
      <rect x="34" y="19" width="80" height="16" rx="8" fill="var(--sol)" {...T} />
      {[52, 64, 76, 88, 100].map((x, i) => (
        <circle key={x} className="ap-luz" style={{ "--d": `${i * 80}ms` } as CSSProperties} cx={x - 2} cy="27" r="2.6" fill="var(--papel)" />
      ))}
      <rect x="30" y="42" width="88" height="42" rx="7" fill="var(--papel)" {...T} />
      {[1, 3, 2].map((inicio, k) => (
        <svg key={k} x={36 + k * 28} y="46" width="24" height="34">
          <g className="ap-rodillo" style={{ transform: `translateY(${-VUELTAS * PASO}px)`, animationDuration: `${1.3 + k * 0.45}s` }}>
            {tira(inicio, s).map((sim, n) => (
              <g key={n}>{SIMBOLOS[sim](17 + n * PASO)}</g>
            ))}
          </g>
        </svg>
      ))}
      <path d="M62 46 V80 M90 46 V80" stroke="var(--linea)" strokeWidth="2" />
      <rect className="ap-premio" x="31.5" y="43.5" width="85" height="39" rx="6" fill="none" stroke="var(--acento)" strokeWidth="3" />
      <rect x="40" y="90" width="68" height="10" rx="5" fill="var(--tinta)" />
      <g className="ap-palanca">
        <path d="M134 70 L140 31" stroke="var(--tinta)" strokeWidth="3.5" strokeLinecap="round" />
        <circle cx="140" cy="31" r="6.5" fill="var(--sol)" {...T} />
      </g>
      <rect x="127" y="63" width="14" height="14" rx="4" fill="var(--control)" {...T} />
    </>
  );
};

/* Carrera: tres caballos se pasan, llega la meta y uno la cruza primero; la bandera toma su color. */
const COLORES = ["var(--acento)", "var(--vida)", "var(--bienestar)"];
const META = 126;

function Caballo({ color }: { color: string }) {
  const pata = { stroke: "var(--tinta)", strokeWidth: 2.5, strokeLinecap: "round" as const };
  return (
    <g className="ap-trote">
      <g className="ap-pata-a">
        <path d="M-7 -7 L-12 0 M-4 -7 L-7 0 M5 -7 L10 0 M8 -7 L13 -1" {...pata} />
      </g>
      <g className="ap-pata-b">
        <path d="M-7 -7 L-4 -1 M-4 -7 L-1 0 M5 -7 L3 0 M8 -7 L6 -1" {...pata} />
      </g>
      <path d="M-10 -13 Q-17 -13 -18 -6" fill="none" stroke="var(--tinta)" strokeWidth="2.5" strokeLinecap="round" />
      <ellipse cx="0" cy="-11" rx="11" ry="5.5" fill="var(--papel)" {...T} />
      <path d="M6 -14 L12 -23 Q14 -25 17 -23 L19 -19 Q19 -17 17 -17 L13 -18 L10 -9Z" fill="var(--papel)" {...T} />
      <rect x="-5" y="-17" width="9" height="6" rx="1.5" fill={color} stroke="var(--tinta)" strokeWidth="1.5" />
      <circle cx="0" cy="-21" r="3.6" fill={color} stroke="var(--tinta)" strokeWidth="1.5" />
    </g>
  );
}

const Caballos: Escena = ({ azar }) => {
  const gana = cual(azar[0], 3);
  const resto = [0, 1, 2].filter((i) => i !== gana);
  if (azar[1] < 0.5) resto.reverse();
  const puesto = (i: number) => (i === gana ? "ap-gana" : i === resto[0] ? "ap-segundo" : "ap-tercero");
  return (
    <>
      <rect {...FONDO} fill="var(--acento-suave)" />
      <svg x="2" y="2" width="156" height="116">
        <path className="ap-pasto" d="M0 34 H156 V98 A18 18 0 0 1 138 116 H18 A18 18 0 0 1 0 98Z" />
        <path d="M0 27 H156 M0 34 H156" stroke="var(--tinta)" strokeWidth="2" />
        <g className="ap-avanza">
          {Array.from({ length: 12 }, (_, i) => (
            <rect key={i} x={i * 16 + 4} y="22" width="4" height="15" rx="1" fill="var(--papel)" stroke="var(--tinta)" strokeWidth="1.5" />
          ))}
          <path d="M-8 59 H176 M-8 81 H176" stroke="var(--papel)" strokeWidth="2" strokeDasharray="8 8" />
        </g>
        <g className="ap-meta">
          <path d={`M${META + 3} 34 V8`} stroke="var(--tinta)" strokeWidth="2" strokeLinecap="round" />
          <g className="ap-bandera">
            <path d={`M${META + 3} 8 H${META + 19} L${META + 15} 13.5 L${META + 19} 19 H${META + 3}Z`} fill={COLORES[gana]} {...T} strokeWidth="1.5" />
          </g>
          <rect x={META} y="34" width="6" height="82" fill="var(--papel)" />
          {Array.from({ length: 21 }, (_, r) => (
            <rect key={r} x={META + (r % 2) * 3} y={34 + r * 4} width="3" height="4" fill="var(--tinta)" />
          ))}
        </g>
        {[55, 77, 99].map((y, i) => (
          <g key={y} transform={`translate(76 ${y}) scale(1.15)`}>
            <g className={`ap-corre ${puesto(i)}`}>
              <Caballo color={COLORES[i]} />
            </g>
          </g>
        ))}
      </svg>
      <rect {...FONDO} fill="none" />
    </>
  );
};

/* Dado: da cuatro saltos de un cuarto de vuelta, cambia de cara en el aire y cae en una. */
const PUNTOS: [number, number][][] = [
  [[0, 0]],
  [[-12, -12], [12, 12]],
  [[-12, -12], [0, 0], [12, 12]],
  [[-12, -12], [12, -12], [-12, 12], [12, 12]],
  [[-12, -12], [12, -12], [0, 0], [-12, 12], [12, 12]],
  [[-12, -12], [12, -12], [-12, 0], [12, 0], [-12, 12], [12, 12]],
];

const Dado: Escena = ({ azar }) => {
  const f = cual(azar[0], PUNTOS.length);
  // Una cara por salto, ninguna igual a la anterior; la última es la que queda.
  const caras = [2, 4, 1, 3, 0].map((d) => (f + d) % PUNTOS.length);
  return (
    <>
      <rect {...FONDO} fill="var(--acento)" />
      <ellipse className="ap-sombra" cx="80" cy="96" rx="24" ry="4.5" fill="var(--tinta)" opacity=".3" />
      <g className="ap-dado">
        <rect x="54" y="38" width="52" height="52" rx="11" fill="var(--sol)" {...T} />
        {caras.map((c, k) => (
          <g key={k} className={`ap-cara ap-cara-${k}`}>
            {PUNTOS[c].map(([x, y]) => (
              <circle key={`${x}${y}`} cx={80 + x} cy={64 + y} r="4.6" fill="var(--sobre-sol)" />
            ))}
          </g>
        ))}
      </g>
    </>
  );
};

/* Naipes: se reparten tres cartas boca abajo; una se levanta y se da vuelta. */
const PINTAS: { d: string; fill: string }[] = [
  { d: "M0 6 C-8 0 -8 -7 -3.5 -7 C-1.5 -7 0 -5.5 0 -4 C0 -5.5 1.5 -7 3.5 -7 C8 -7 8 0 0 6Z", fill: "var(--vida)" },
  { d: "M0 -8 L6 0 L0 8 L-6 0Z", fill: "var(--bienestar)" },
  { d: "M0 -8 C-8 -1 -7 5 -2.5 4 C-1.5 4 -1 3.5 -0.8 3 L-2 8 H2 L0.8 3 C1 3.5 1.5 4 2.5 4 C7 5 8 -1 0 -8Z", fill: "var(--tinta)" },
];

function Dorso({ x }: { x: number }) {
  return (
    <>
      <rect x={x - 19} y="34" width="38" height="56" rx="6" fill="var(--acento)" {...T} />
      <rect x={x - 13} y="40" width="26" height="44" rx="3" fill="none" stroke="var(--papel)" strokeWidth="1.5" />
      <path d={`M${x} 52 L${x + 7} 62 L${x} 72 L${x - 7} 62Z`} fill="var(--papel)" />
    </>
  );
}

const Naipes: Escena = ({ azar }) => {
  const c = cual(azar[0], 3);
  const p = PINTAS[cual(azar[1], PINTAS.length)];
  return (
    <>
      <rect {...FONDO} fill="var(--sol)" />
      {[44, 80, 116].map((x, i) => (
        <g key={x} transform={`rotate(${(i - 1) * 8} ${x} 62)`}>
          <g className="ap-reparte" style={{ "--d": `${i * 180}ms` } as CSSProperties}>
            {i !== c ? (
              <Dorso x={x} />
            ) : (
              <g className="ap-alza">
                <g className="ap-naipe">
                  <Dorso x={x} />
                  <g className="ap-frente">
                    <rect x={x - 19} y="34" width="38" height="56" rx="6" fill="var(--papel)" {...T} />
                    <path d={p.d} fill={p.fill} transform={`translate(${x} 62) scale(1.5)`} />
                    <path d={p.d} fill={p.fill} transform={`translate(${x - 11} 44) scale(.6)`} />
                    <path d={p.d} fill={p.fill} transform={`translate(${x + 11} 80) rotate(180) scale(.6)`} />
                  </g>
                </g>
              </g>
            )}
          </g>
        </g>
      ))}
    </>
  );
};

const ESCENAS: Record<Variante, Escena> = { ruleta: Ruleta, tragamonedas: Tragamonedas, caballos: Caballos, dado: Dado, naipes: Naipes };

/**
 * Espera entretenida mientras se simula, se tira el dado o Claude lee.
 * `texto` es una sola línea corta; con `frases` el texto va rotando cada `cada` ms.
 * `pantalla` la pone a pantalla completa, `compacto` la deja chica al lado del texto.
 * Sin `variante` comparte el sorteo con las esperas encadenadas; con `variante` (el catálogo) sortea solo la suya.
 */
export function Espera({
  texto,
  frases,
  cada = 2400,
  variante,
  titulo,
  pantalla = false,
  compacto = false,
}: {
  texto?: string;
  frases?: string[];
  cada?: number;
  variante?: Variante;
  titulo?: string;
  pantalla?: boolean;
  compacto?: boolean;
}) {
  const compartido = variante === undefined;
  // El desfase se fija al montar: si cambiara en cada render, la animación saltaría.
  const [{ sorteo, ya }] = useState(() => {
    const s = variante ? nuevoSorteo(variante) : tomarSorteo();
    return { sorteo: s, ya: Math.max(0, Math.round(ahora() - s.inicio)) };
  });
  useEffect(() => {
    if (!compartido) return;
    montadas++;
    return () => {
      montadas--;
      pegadoHasta = ahora() + PEGA_MS;
    };
  }, [compartido]);
  const [n, setN] = useState(0);
  const total = frases?.length ?? 0;
  useEffect(() => {
    if (total < 2) return;
    const id = window.setInterval(() => setN((x) => x + 1), cada);
    return () => window.clearInterval(id);
  }, [total, cada]);
  const linea = total ? frases![n % total] : texto;
  const Escena = ESCENAS[sorteo.variante];
  return (
    <div className="ap-espera" data-modo={pantalla ? "pantalla" : compacto ? "compacto" : "bloque"} role="status" aria-live="polite">
      {titulo && <span className="ap-titulo">{titulo}</span>}
      <svg
        className="ap-escena"
        data-variante={sorteo.variante}
        style={{ "--ap-ya": `${-ya}ms` } as CSSProperties}
        viewBox="0 0 160 120"
        aria-hidden="true"
        focusable="false"
      >
        <Escena azar={sorteo.azar} />
      </svg>
      {linea && (
        <p className="ap-texto" key={linea}>
          {linea}
        </p>
      )}
    </div>
  );
}
