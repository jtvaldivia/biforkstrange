import { AppShell } from "@/app/AppShell";
import { StoryPage } from "@/features/story";
import { TwinPage } from "@/features/twin";
import { UiKitPage } from "@/features/ui-kit";

export default function App() {
  // Rutas mínimas por pathname (sin router por ahora)
  const path = window.location.pathname;
  if (path.startsWith("/ui")) return <UiKitPage />;
  if (path.startsWith("/gemelo"))
    return (
      <AppShell active="gemelo">
        <TwinPage />
      </AppShell>
    );
  return (
    <AppShell active="historia">
      <StoryPage />
    </AppShell>
  );
}
