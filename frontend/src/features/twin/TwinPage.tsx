import { useEffect, useState } from "react";
import { Meta, Segmented, Stack } from "@/shared/ui";
import { AdaptiveTab } from "./components/AdaptiveTab";
import { ExamTab } from "./components/ExamTab";
import { PanelTab } from "./components/PanelTab";
import { ProfileTab } from "./components/ProfileTab";
import { Snapshot } from "./components/Snapshot";
import { clarityOf } from "./components/parts";
import { useTwin } from "./hooks/useTwin";
import "./twin.css";

type Tab = "preguntas" | "examen" | "panel" | "perfil";

const TABS: { value: Tab; label: string; hint: string }[] = [
  { value: "preguntas", label: "Preguntas", hint: "Enséñale cómo decides" },
  { value: "examen", label: "Examen", hint: "Ponlo a prueba a ciegas" },
  { value: "panel", label: "Panel", hint: "Cuánto te conoce" },
  { value: "perfil", label: "Perfil", hint: "Lo que sabe de ti" },
];

function readTab(): Tab {
  const h = window.location.hash.slice(1);
  return TABS.some((t) => t.value === h) ? (h as Tab) : "preguntas";
}

/**
 * Teléfono: columna única con pestañas arriba (como el kit).
 * Escritorio (≥1024px): navegación a la izquierda, contenido al centro y,
 * desde 1240px, "lo que sabe de ti" siempre visible a la derecha.
 */
export function TwinPage() {
  const twin = useTwin();
  const [tab, setTab] = useState<Tab>(readTab);

  useEffect(() => {
    const onHash = () => setTab(readTab());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const go = (t: Tab) => {
    setTab(t);
    history.replaceState(null, "", `#${t}`);
    window.scrollTo({ top: 0 });
  };

  const p = twin.profile;
  const counts: Record<Tab, string> = {
    preguntas: p ? `${p.qs.filter((q) => q.ans !== null).length} respondidas` : "",
    examen: p ? `${p.exam.filter((e) => e.ans !== null).length} preguntas` : "",
    panel: twin.summary?.examen.acierto != null ? `${twin.summary.examen.acierto}% de acierto` : "sin datos",
    perfil: p ? `${clarityOf(p.dims).pct}% de claridad` : "",
  };

  return (
    <div className="tw-layout">
      <aside className="tw-nav" aria-label="Secciones del gemelo">
        <Stack gap={4} className="tw-nav-head">
          <Meta>Tu gemelo</Meta>
          <span className="tw-nav-title">{p?.basics.nombre || "Sin nombre"}</span>
        </Stack>
        <nav className="tw-nav-list">
          {TABS.map((t) => (
            <button key={t.value} type="button" className="tw-nav-item" aria-current={tab === t.value ? "page" : undefined}
              onClick={() => go(t.value)}>
              <span className="tw-nav-label">{t.label}</span>
              <span className="tw-nav-hint">{t.hint}</span>
              <span className="tw-nav-count">{counts[t.value]}</span>
            </button>
          ))}
        </nav>
        {p && (
          <div className="tw-nav-foot">
            <span className="vd-meta">Perfil {p.id.slice(0, 8)} · v{p.version}</span>
            <button type="button" className="tw-link" onClick={twin.reset} disabled={twin.busy}>Empezar un gemelo nuevo</button>
          </div>
        )}
      </aside>

      <section className="tw-main">
        <div className="tw-tabs">
          <Segmented label="Secciones" options={TABS} value={tab} onChange={go} />
        </div>

        {twin.notice && <p className="tw-notice" role="status">{twin.notice}</p>}
        {twin.error && <p className="tw-error" role="alert">{twin.error}</p>}

        {!p ? (
          <p className="vd-p">Despertando a tu gemelo…</p>
        ) : (
          <div className="tw-sheet" key={tab}>
            {tab === "preguntas" && <AdaptiveTab twin={twin} />}
            {tab === "examen" && <ExamTab twin={twin} />}
            {tab === "panel" && <PanelTab twin={twin} />}
            {tab === "perfil" && <ProfileTab twin={twin} />}
          </div>
        )}

        {p && (
          <div className="tw-mobile-foot">
            <span className="vd-meta">Perfil {p.id.slice(0, 8)} · v{p.version}</span>
            <button type="button" className="tw-link" onClick={twin.reset} disabled={twin.busy}>Empezar un gemelo nuevo</button>
          </div>
        )}
      </section>

      <aside className="tw-side" aria-label="Lo que sabe de ti">
        <Snapshot twin={twin} />
      </aside>
    </div>
  );
}
