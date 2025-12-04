import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
// IMPORTAR O TOASTER
import { Toaster } from "./components/ui/sonner"; 

createRoot(document.getElementById("root")!).render(
  <>
    <App />
    {/* O Toaster fica aqui à espera de receber mensagens para mostrar */}
    <Toaster />
  </>
);