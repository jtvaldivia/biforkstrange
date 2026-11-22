/**
 * Kit de UI de Agarrar la pala (desde el Claude Design "Gemelo Laboral · simulador de vida").
 * Los estilos (styles/vida.css) se importan una vez en main.tsx. Usa los componentes desde "@/shared/ui".
 * Catálogo vivo en /ui (ver features/ui-kit).
 */

export * from "./tokens";
export * from "./scene";
export { useTheme, setTheme, THEME_STORAGE_KEY, type Theme } from "./theme";

export { Screen, ScreenHeader, ScreenFooter, Stack, Row, Panel, SunCard, NightBand, SlowReveal } from "./components/Layout";
export { Heading, Text, Meta, Pill, BigNumber, Narrative } from "./components/Typography";
export { Button, IconButton, type ButtonVariant } from "./components/Button";
export { Chip, ChipGroup, Segmented, Slider, Tag } from "./components/Controls";
export { Indicator, IndicatorGrid } from "./components/Indicators";
export { DecisionCard, DecisionList, type DecisionTag } from "./components/DecisionCard";
export { Avatar, Notification, Dot, DotRow, PeopleTally, DotLegend, MissedList, type DotKind } from "./components/People";
export { StationTimeline, YearTicker } from "./components/Timeline";
export { LinesChart, RangeCompare, VisitsTimeline, type Range } from "./components/Charts";
export { ChevronLeftIcon, CheckIcon, PhoneIcon, SunIcon, MoonIcon } from "./components/Icon";
export { ThemeToggle } from "./components/ThemeToggle";

export { LifePathHero } from "./illustrations/LifePathHero";
export { DecisionArt, DECISION_ART_KINDS, type DecisionArtKind } from "./illustrations/DecisionArt";
export { OfficeScene } from "./illustrations/OfficeScene";
export { TravelScene } from "./illustrations/TravelScene";
