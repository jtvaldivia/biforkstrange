import type { CSSProperties } from "react";

/** Permite pasar variables CSS (--algo) en `style` sin pelear con los tipos. */
export const cssVars = (vars: Record<string, string | number>) => vars as CSSProperties;

export const cx = (...xs: (string | false | null | undefined)[]) => xs.filter(Boolean).join(" ");
