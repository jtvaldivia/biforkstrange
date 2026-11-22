/**
 * Componentes de UI compartidos de Bifurca. Los estilos (styles/vida.css) se importan una vez
 * en main.tsx. Usa los componentes desde "@/shared/ui".
 */

export * from "./tokens";
export { useTheme, setTheme, THEME_STORAGE_KEY, type Theme } from "./theme";

export { Screen, ScreenHeader, ScreenFooter, Stack, Row, Panel, SunCard, NightBand, SlowReveal } from "./components/Layout";
export { Heading, Text, Meta, Pill, BigNumber, Narrative } from "./components/Typography";
export { Button, IconButton, type ButtonVariant } from "./components/Button";
export { Chip, Segmented, Slider, Tag } from "./components/Controls";
export { DecisionCard, DecisionList, type DecisionTag } from "./components/DecisionCard";
export { StationTimeline, YearTicker } from "./components/Timeline";
export { ChevronLeftIcon, CheckIcon, SunIcon, MoonIcon } from "./components/Icon";
export { ThemeToggle } from "./components/ThemeToggle";
export { BifurcaMark, BifurcaLogo } from "./components/Brand";

export { LifePathHero } from "./illustrations/LifePathHero";
export { DecisionArt, type DecisionArtKind } from "./illustrations/DecisionArt";
