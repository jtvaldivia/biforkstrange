import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@/shared/ui/styles/vida.css";
import App from "@/app/App";
import { despertarServidor } from "@/shared/lib/http";

despertarServidor();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
