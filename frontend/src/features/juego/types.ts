/** Formas de la API del juego (`/api/juego/*`). Ver backend/app/sim/motor/partida.py (vista) y gemelos.py (comparar). */

export type Calidad = "dato" | "mixto" | "sintetico" | "supuesto";
export type Tono = "bueno" | "malo" | "neutro";
export type Sexo = "h" | "m";
export type Educacion = "media" | "tecnica" | "universitaria" | "postgrado";
export type TipoEmpleador = "grande" | "pyme" | "startup" | "publico" | "extranjero";

export type Perfil = {
  edad: number;
  sexo: Sexo;
  edu: Educacion;
  carrera_id: number; // -1 = sin carrera
  rubro: string;
  tipo_empleador: TipoEmpleador;
  nivel: number;
  sueldo: number;
  riesgo: number;
  // No están en el formulario: los deduce Claude del texto de la persona y se mandan tal cual a la API.
  ocupacion?: number | null;
  antiguedad?: number;
  region?: "rm" | "otra";
  ahorro?: number | null;
  /** 1 si trabaja en inglés (intermedio o más). Mueve remoto y emigrar. */
  ingles?: 0 | 1;
  /** Habilidad y red de contactos (0 a 100), deducidas del CV. Sin dato, el motor usa 50 y 30. */
  skill?: number | null;
  red?: number | null;
  /** Su situación de hoy y su historia, del CV. Sin dato, empleado a jornada completa, presencial. */
  estado?: "empleado" | "independiente" | "fundador" | "buscando" | "estudiando";
  meses_cesante?: number;
  parcial?: 0 | 1;
  remoto?: 0 | 1;
  usa_ia?: 0 | 1;
  empresa_anos?: number;
  empresa_fondos?: 0 | 1;
  /** Cada cuántos años se ha cambiado de pega: sus gemelos aceptan ofertas a ese ritmo. */
  anos_por_empleo?: number | null;
  /** Si estudia: semestres que le faltan y años que lleva en la carrera. Sin dato, se suponen por su edad. */
  semestres_restantes?: number | null;
  anos_en_carrera?: number | null;
  /** Cómo salió de sus cesantías (1 = sí): sus gemelos responden igual si quedan cesantes. */
  volvio_a_su_nivel?: 0 | 1;
  freelance_entre_pegas?: 0 | 1;
  emprendio_antes?: 0 | 1;
  /** Si trabaja por su cuenta: hace cuántos años. Con 5 o más, sus gemelos vuelven menos a un empleo. */
  anos_independiente?: number | null;
  /** Si estudia o busca su primera pega: dónde hizo la práctica. Grande o Estado pesa en su primera pega. */
  practica?: "" | "grande" | "pyme" | "startup" | "publico";
  /** Si todos sus empleos fueron en el Estado o en startups: al cambiar de pega, sus gemelos vuelven ahí más seguido. */
  toda_su_carrera_en?: "" | "publico" | "startup";
  /** Ascensos dentro de una misma empresa por año de experiencia. Si es más rápido que lo típico, asciende más. */
  ascensos_por_ano?: number | null;
  /** Empresas propias que ya cerró: si sus gemelos tienen empresa, la cierran más seguido. */
  empresas_cerradas?: number;
  /** universidad_id del catálogo; "" si no lo dice. */
  universidad_id?: string;
  /** El rubro al que se cambiaría, según su Claude: "¿a qué rubro?" parte ahí. */
  rubro_sonado?: string | null;
};

export type DudaSugerida = { decision: string; nombre?: string; por_que: string };

/** Respuesta de `POST /api/juego/perfil`: el perfil que Claude llenó desde un texto. */
export type PerfilLeido = {
  perfil: Perfil;
  /** Campos que el texto no decía y quedaron con un valor por defecto. */
  supuestos: { campo: string; nombre: string }[];
  /** Frases cortas: qué dedujo Claude y de dónde. */
  inferido: string[];
  /** Valores del documento que no se pudieron usar. */
  avisos: string[];
  /** La duda que el documento trae, si es una posible para este perfil. */
  duda: string | null;
  /** Hasta 3 dudas que le calzan a esta persona según su CV, con el porqué. Solo si Claude leyó un texto o PDF. */
  dudas_sugeridas?: DudaSugerida[];
  /** Su empleador actual, si está en la nómina del SII. */
  empresa?: { nombre: string; tamano: string; rubro: string; trabajadores: number; fuente: string } | null;
  /** Lo que contó su Claude (solo por el prompt): temas que le apasionan y su proyecto paralelo. */
  intereses?: string[];
  proyecto?: string | null;
  /** Campos del perfil que el texto dijo de verdad (el resto son valores por defecto). */
  dados?: string[];
  /** Lo que su gemelo sabe de ella, en una línea. */
  retrato?: string | null;
  /** "documento" si venía en el formato del prompt; "api" o "comando" si Claude leyó un texto libre. */
  via: string;
};

export type Carrera = { carrera_id: number; carrera: string; tipo_institucion: string; area: string };

export type Catalogo = {
  rubros: string[];
  tipos_empleador: TipoEmpleador[];
  niveles: { nivel: number; nombre: string }[];
  educacion: Educacion[];
  ocupaciones: { grupo: number; nombre: string }[];
  carreras: Carrera[];
  /** Sueldo líquido por estudios y banda de edad (ESI 2025): la referencia del sueldo. */
  sueldos_ref: { educacion: Educacion; banda: string; p25: number; p50: number; p75: number }[];
  /** Dónde estudió: chilenas (U, IP, CFT) y extranjeras. */
  universidades?: Universidad[];
};

export type Duda = { decision: string; nombre: string; pregunta: string; categoria: string; calidad: Calidad };

export type Eleccion = { decision?: string | null; opcion: string; parametros?: Record<string, string | number> };

/** Lo que el cliente guarda y manda completo en cada llamada. */
export type Partida = { perfil: Perfil; semilla: number; duda: string | null; elecciones: Eleccion[] };

export type Estado = {
  edad: number;
  estado: string;
  sueldo: number;
  sueldo_ref: number;
  nivel: number;
  cargo: string;
  tipo_empleador: string;
  rubro: string;
  edu: string;
  antiguedad: number;
  ahorro: number;
  empresa_id?: number;
  /** Empresa del catálogo donde trabaja y su cargo; null si su empleo no es del catálogo. */
  empresa?: string | null;
  rol?: string | null;
  ia_adopcion?: number;
};

/** La historia de la carta: qué empresa, quién te escribe. Solo texto; los números vienen aparte. */
export type Narrativa = { situacion: string } | null;

export type DecisionTomada = {
  decision: string;
  nombre: string;
  pregunta: string;
  narrativa?: Narrativa;
  origen: string;
  opcion: string;
  opcion_nombre: string;
  resultado: string;
  texto: string;
  tono: Tono;
  prob: number;
};

export type Evento = {
  evento: string;
  nombre: string;
  resultado: string;
  texto: string;
  tono: Tono;
  /** Probabilidad de que pase el evento y salga este resultado. */
  prob: number;
  prob_evento?: number;
  /** Gatillado por otra regla: no tiene probabilidad propia que mostrar. */
  directo?: boolean;
  rutina?: boolean;
};

export type Anio = {
  /** Número de ronda, no de año: para el año usa la edad. */
  anio: number;
  edad: number;
  recesion: boolean;
  decisiones: DecisionTomada[];
  eventos: Evento[];
  /** Solo en los años cerrados. */
  fin?: Estado;
};

export type Rango = { p10: number; p50: number; p90: number };

/** Frente a la opción base, con la misma suerte: proporciones que suman 1 (null en la base). "Igual" = a menos de 0,5%. */
export type ContraBase = {
  gana_mas_que_base: number | null;
  igual_que_base: number | null;
  gana_menos_que_base: number | null;
  /** Mediana de la diferencia con la base, en pesos al mes. */
  diferencia_tipica: number | null;
  diferencia_si_cambia?: number | null;
};

export type PorResultado = ContraBase & {
  resultado: string;
  texto: string;
  tono: Tono;
  gemelos: number;
  prob: number;
};

export type OpcionComparada = ContraBase & {
  opcion: string;
  nombre: string;
  detalle: string;
  calidad: Calidad;
  es_base: boolean;
  sueldo: Rango;
  ingreso_total: Rango;
  paso_por_cesantia: number;
  meses_sin_trabajo: number;
  sin_trabajo_al_final: number;
  cargo_mas_probable: string;
  cargos: { cargo: string; prob: number }[];
  /** Lo que se supuso dentro de la opción (rubro, región…). */
  parametros?: Record<string, string | number>;
  por_resultado: PorResultado[];
  trayectoria: { edad: number; p10: number; p50: number; p90: number; sin_trabajo: number }[];
};

export type Comparacion = {
  decision: string;
  nombre: string;
  pregunta: string;
  gemelos: number;
  anios: number;
  base: string;
  opciones: OpcionComparada[];
  /** En cada mundo (el índice), con qué opción terminas ganando más; null si dos quedan a menos de 0,5%. */
  ganador_por_mundo?: (string | null)[];
};

export type Suceso = { tipo: "decision" | "evento"; nombre: string; opcion?: string; texto: string; tono: Tono };

export type AnioMundo = {
  anio: number;
  edad: number;
  recesion: boolean;
  sucesos: Suceso[];
  fin: {
    sueldo: number; sueldo_ref: number; cargo: string; estado: string; tipo_empleador: string;
    empresa?: string | null; rol?: string | null; rubro?: string;
  } | null;
};

/** Qué tan rápido llega la IA en un mundo: se sortea por gemelo dentro del rango con fuente de IA_JOVEN. */
export type EscenarioIA = { adopcion: number; escenario: "lento" | "medio" | "rapido"; castigo_joven: number };

/** Respuesta de `POST /api/juego/mundo`: un mundo, con su historia por opción. */
export type MundoDetalle = {
  mundo: number;
  decision: string;
  ganador: string | null;
  ia?: EscenarioIA;
  opciones: {
    opcion: string; nombre: string; sueldo_final: number; estado_final: string;
    empresa_final?: string | null; rol_final?: string | null; anios: AnioMundo[];
  }[];
};

export type EleccionInterna = {
  variable: string;
  pregunta: string;
  alternativas: { valor: string | number; nombre: string; prob?: number }[];
};

/** La empresa real y el cargo que trae la opción: es la misma que vive tu gemelo si la toma.
 *  Sus cifras NO son de la empresa: salen de su rubro y tamaño (calidad sintético). */
export type EmpresaOferta = {
  empresa_id: number;
  nombre: string;
  rubro: string;
  tipo: string;
  pais: string;
  dominio: string;
  logo: boolean;
  origen: string;
  cargo_id: number;
  cargo: string | null;
  /** Relativas al promedio de su tipo y rubro (1 = promedio), salvo exposición a IA (0 a 1) y horas. */
  cifras: { sueldo: number; despido: number; ascenso: number; cierre: number; exposicion_ia: number; horas: number };
  calidad: Calidad;
};

export type Universidad = {
  universidad_id: string;
  nombre: string;
  sigla: string;
  pais: string;
  tipo_institucion: "U" | "IP" | "CFT" | "EXT";
  logo: boolean;
  selectiva: boolean;
};

/** Un texto contado por Sonnet (o su plantilla si Sonnet no estaba). */
export type Narrado = { id: string; texto: string; via: "sonnet" | "plantilla" };

export type OpcionPendiente = {
  opcion: string;
  nombre: string;
  detalle: string;
  calidad: Calidad;
  elecciones_internas: EleccionInterna[];
  empresa?: EmpresaOferta | null;
};

/** Por qué te tocó esta decisión. */
export type PorQue =
  | { tipo: "sorteo"; prob: number; posibles: number }
  | { tipo: "obligada" }
  | { tipo: "consecuencia" }
  | { tipo: "elegida" };

export type Pendiente = {
  por_que?: PorQue;
  decision: string;
  nombre: string;
  pregunta: string;
  narrativa?: Narrativa;
  categoria: string;
  calidad: Calidad;
  creencia_vs_dato: string | null;
  evidencia: { fuente: string; cifra: string; uso: string }[];
  opciones: OpcionPendiente[];
  /** null cuando la decisión tiene demasiadas opciones para simular gemelos. */
  comparacion: Comparacion | null;
};

export type Cierre = {
  sueldo_final: number;
  estado: Estado;
  anios_sin_trabajo: number;
  mejor_que_gemelos?: number;
  primera_decision: { decision: string; pregunta: string; elegida: string; comparacion: Comparacion } | null;
};

export type Vista = {
  terminada: boolean;
  /** Años de edad transcurridos (tope `anios`). Una ronda puede ocupar varios (un doctorado, 5). */
  anio: number;
  edad_final: number;
  anios: number;
  estado: Estado;
  historia: Anio[];
  anio_en_curso: Anio | null;
  pendiente: Pendiente | null;
  cierre: Cierre | null;
};

/** Lo que se elige dentro de cada opción para comparar: {opción: {variable: valor}}. */
export type ParametrosComparar = Record<string, Record<string, string | number>>;

/** Una opción de la duda con un dato del CV y sin él, con los mismos dados. */
export type PesoOpcion = {
  opcion: string;
  nombre: string;
  /** Fracción de mundos donde esa opción termina ganando más. */
  gana_con: number;
  gana_sin: number;
  /** Sueldo típico (p50) al final. */
  sueldo_con: number;
  sueldo_sin: number;
};

export type CampoCv = "ingles" | "skill" | "red" | "usa_ia" | "remoto" | "anos_por_empleo" | "nivel" | "edu" | "parcial" | "empresa_fondos";

/** Una línea del CV: cuánto mueve la duda. `mueve` dice qué cambia más, y `opcion` es la que más cambia. */
export type PesoDato = {
  campo: CampoCv;
  tuyo: string | number;
  neutro: string | number | null;
  mueve: "gana" | "sueldo";
  opcion: string;
  cambio: number;
  opciones: PesoOpcion[];
};

/** Respuesta de `POST /api/juego/peso-cv`: las líneas del CV que más mueven la duda (hasta 4). */
export type PesoCv = {
  decision: string;
  nombre: string;
  pregunta: string;
  gemelos: number;
  semilla: number;
  base: string;
  datos: PesoDato[];
  /** Datos del CV que no cambian esta duda. */
  sin_efecto: CampoCv[];
  /** Datos que la mueven, pero menos que los que se muestran. */
  otros: CampoCv[];
};

/** Cuánto se juega la persona en una duda: el rango que abre entre la mala y la buena suerte. */
export type DudaEnJuego = {
  decision: string;
  nombre: string;
  pregunta: string;
  /** Peor sueldo de mala suerte (p10) entre todas las opciones. */
  mala: number;
  /** Mejor sueldo de buena suerte (p90) entre todas las opciones. */
  buena: number;
  /** Sueldo típico (p50) si te quedas como estás. */
  tipico: number;
  /** (buena − mala) / típico: lo que ordena. */
  dispersion: number;
  /** Distancia entre el sueldo típico de la mejor y la peor opción, sobre la peor. */
  entre_opciones: number;
};

/** Respuesta de `POST /api/juego/dudas-en-juego`. `mas_en_juego` es null si hay menos de dos dudas. */
export type EnJuego = { gemelos: number; semilla: number; mas_en_juego: string | null; dudas: DudaEnJuego[] };

