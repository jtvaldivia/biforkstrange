/** Formas de la API del juego (`/api/juego/*`). Ver backend/app/sim/motor/partida.py (vista) y gemelos.py (comparar). */

export type Calidad = "dato" | "mixto" | "sintetico" | "supuesto";
export type Tono = "bueno" | "malo" | "neutro";
export type Sexo = "h" | "m";
export type Educacion = "media" | "tecnica" | "universitaria" | "postgrado";
export type TipoEmpleador = "grande" | "pyme" | "startup" | "publico" | "extranjero";

export type Perfil = {
  edad: number;
  /** Hasta qué edad se juega (y miran los mundos). Sin dato: 10 años desde hoy. No es parte del perfil del motor. */
  edad_final?: number;
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
  /** Su empresa y su cargo de hoy, con el nombre que dio. Solo para contar la historia: no mueven números. */
  empresa_nombre?: string;
  cargo_nombre?: string;
  /** El rubro al que se cambiaría, según su Claude: "¿a qué rubro?" parte ahí. */
  rubro_sonado?: string | null;
  /** El rubro de su proyecto, según su Claude: "¿de qué rubro es tu empresa?" parte ahí. */
  rubro_proyecto?: string | null;
  /** 1 si busca su primer empleo (sin experiencia tras titularse): parte en la primera pega, no en cesantía. */
  primer_empleo?: 0 | 1;
  /** Cómo se describe con sus palabras: el narrador cuenta las cartas a su medida. */
  relato?: string;
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
  /** Su empleador actual en el catálogo de empresas, si está: para mostrar su logo. */
  empresa_catalogo?: { empresa_id: number; nombre: string; rubro: string; logo: boolean } | null;
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
  /** Fracción del sueldo que ahorra. */
  tasa_ahorro?: number;
  /** Meses que lleva buscando trabajo (0 si trabaja). */
  meses_cesante?: number;
  /** Lo ganado en sueldos desde que empezó la partida. */
  ingreso_total?: number;
  empresa_id?: number;
  /** Empresa y cargo donde trabaja: los del catálogo o, mientras siga en su pega de hoy, los que contó. */
  empresa?: string | null;
  rol?: string | null;
  ia_adopcion?: number;
  /** Con la incertidumbre de IA prendida: el ritmo de tu mundo, cómo te toca la IA y qué tan adaptable eres (0-1). */
  ia_ritmo?: Ritmo;
  ia_tipo?: "automatiza" | "aumenta" | "incognita" | "no_afectado";
  adaptabilidad?: number;
  usa_ia?: number;
};

export type Ritmo = "lento" | "medio" | "rapido";

/** Lo de la IA en un año de tu partida: el ritmo de tu mundo y el titular que leíste (si ese año hubo). */
export type AnioIA = { ritmo: Ritmo; titular?: string | null; burbuja?: boolean; auge_cobre?: boolean };

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
} & MovimientoPlata;

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
} & MovimientoPlata;

export type Anio = {
  /** Número de ronda, no de año: para el año usa la edad. */
  anio: number;
  edad: number;
  recesion: boolean;
  /** Solo con la incertidumbre de IA prendida. */
  ia?: AnioIA;
  decisiones: DecisionTomada[];
  eventos: Evento[];
  /** Solo en los años cerrados. */
  fin?: Estado;
  sueldo_inicio?: number;
  ahorro_inicio?: number;
  /** Cómo se movió la plata al cerrar el año (solo en los años cerrados). */
  plata?: Plata;
  /** Los meses de este año que se vivieron buscando trabajo (de 1 a 12). */
  meses_busqueda?: number[];
};

/** Lo que pasa con la plata al cerrar el año: lo que ahorraste, lo que gastaste sin sueldo y lo que rentó. */
export type Plata = {
  /** Fracción del sueldo que ahorras. */
  tasa_ahorro: number;
  /** Rentabilidad real anual del ahorro. */
  retorno_real: number;
  alza_extra?: number;
  /** Meses del año que pasaste buscando trabajo: esos meses no hubo sueldo. */
  meses_sin_sueldo?: number;
  /** Lo ganado en sueldos ese año. */
  ganado?: number;
  ahorrado?: number;
  deuda_estudios?: number;
  retorno?: number;
};

/** Cuánto movió el sueldo y el ahorro una decisión o un evento (solo si lo movió). */
export type MovimientoPlata = {
  sueldo_antes?: number;
  sueldo_despues?: number;
  ahorro_cambio?: number;
  /** Si pasó en un año que se vivió mes a mes (sin trabajo): el mes, de 1 a 12. */
  mes?: number;
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
  /** En los mundos donde te va mejor que con la base: por cuánto, típico (pesos al mes). */
  cuanto_mejor?: number | null;
  /** En los mundos donde te va peor que con la base: por cuánto, típico (pesos al mes, positivo). */
  cuanto_peor?: number | null;
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
  /** Fracción de mundos que terminan en un cargo más alto que el de hoy. */
  sube_de_cargo: number;
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
  /** El ritmo de la IA de cada mundo; null con la incertidumbre de IA apagada. */
  ia_por_mundo?: (Ritmo | null)[] | null;
  ia?: IAPorRitmo | null;
};

/** La comparación separada por ritmo de la IA (el cierre la usa para el sueldo con cada ritmo). */
export type IAPorRitmo = {
  ritmos: Partial<Record<Ritmo, { mundos: number; gana: Record<string, number>; sueldo_p50: Record<string, number> }>>;
};

export type ConFuente = { fuente: string; cita: string; url: string };
export type CierreIA = {
  ritmo: Ritmo;
  ritmos: Record<Ritmo, ConFuente & { nombre: string; que_es: string }>;
  voces: (ConFuente & { quien: string; tipo: string; dice: string })[];
  fuera_del_juego: string;
  por_ritmo: IAPorRitmo | null;
};

export type Suceso = { tipo: "decision" | "evento"; nombre: string; opcion?: string; texto: string; tono: Tono };

export type AnioMundo = {
  anio: number;
  edad: number;
  recesion: boolean;
  sucesos: Suceso[];
  fin: {
    /** Edad al cerrar el año (una ronda puede durar más de un año). */
    edad: number;
    sueldo: number; sueldo_ref: number; cargo: string; estado: string; tipo_empleador: string;
    empresa?: string | null; rol?: string | null; rubro?: string;
  } | null;
};

/** Qué tan rápido llega la IA en un mundo: se sortea por gemelo dentro del rango con fuente de IA_JOVEN. */
export type EscenarioIA = { adopcion: number; escenario: Ritmo; castigo_joven: number; activa?: boolean };

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

/** Un texto contado por Claude (o su plantilla si Claude no estaba). */
export type Narrado = { id: string; texto: string; via: "claude" | "plantilla" };

export type OpcionPendiente = {
  opcion: string;
  nombre: string;
  detalle: string;
  calidad: Calidad;
  elecciones_internas: EleccionInterna[];
  empresa?: EmpresaOferta | null;
  /** De dónde sale la probabilidad de cada resultado: fuente, calidad y su valor si no depende de tu situación. */
  respaldo?: Respaldo[];
};

export type Respaldo = {
  resultado: string;
  texto: string;
  fuentes: string[];
  calidad: Calidad;
  es_resto: boolean;
  /** Probabilidad del paquete; null si es una fórmula que depende de tu situación. */
  valor: number | null;
};

/** Por qué te tocó esta decisión. */
export type PorQue =
  | { tipo: "llega"; prob?: number; posibles?: number }
  | { tipo: "buscada" }
  | { tipo: "tranquilo" }
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
  /** Una oferta llega con su sueldo: el de hoy y el que tendrías si la aceptas, con la empresa nueva incluida. */
  oferta_sueldo?: { hoy: number; si_aceptas: number | null; cesante?: boolean } | null;
  /** Sin trabajo, el año pasa mes a mes: en qué mes vas, cuánto llevas y, si llegó una oferta, su riesgo y qué haría tu copia. */
  busqueda?: Busqueda | null;
  /** null cuando la decisión tiene demasiadas opciones para simular gemelos, o en un año tranquilo. */
  comparacion: Comparacion | null;
  /** En un año tranquilo: algo que gente como tú se plantea este año. */
  sugerida?: string | null;
  /** En un año tranquilo: la propuesta del año, con un dato del paquete que la respalda. */
  sugerencia?: {
    decision: string;
    nombre: string;
    pregunta: string;
    dato: string | null;
    fuente: string | null;
    /** true si el dato es la estadística oficial de qué tan seguido la gente hace esto. */
    es_frecuencia?: boolean;
    creencia_vs_dato: string | null;
  } | null;
};

export type Busqueda = {
  mes: number;
  meses_cesante: number;
  /** Lo que ganabas en tu último trabajo, al mes. */
  sueldo_ref: number;
  /** Trabajas informal mientras sigues buscando un empleo con contrato. */
  informal?: boolean;
  /** Probabilidad de que te despidan en un año en el trabajo que te ofrecen. */
  riesgo_despido?: number;
  /** Lo que haría tu copia con esta oferta, con su regla fija. */
  gemelo_acepta?: boolean;
};

export type Cierre = {
  sueldo_final: number;
  estado: Estado;
  anios_sin_trabajo: number;
  meses_sin_trabajo?: number;
  mejor_que_gemelos?: number;
  primera_decision: { decision: string; pregunta: string; elegida: string; comparacion: Comparacion } | null;
  ia?: CierreIA;
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


/** Un año en que seguiste igual y no pasó nada: no se muestra "qué te pasó", solo esta franja en el año siguiente. */
export type SinNovedad = { anio: number; sueldo: number; delta: number };
