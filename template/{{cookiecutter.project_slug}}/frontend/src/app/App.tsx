import { SimulationPage } from "@/features/simulation";

export default function App() {
  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 720, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>Bifurca</h1>
      <SimulationPage />
    </main>
  );
}
