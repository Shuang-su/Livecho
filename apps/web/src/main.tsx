import { createRoot } from "react-dom/client";
import { App } from "./ui/App";
import { registerServiceWorker } from "./pwa/register";
import "./app.css";

const container = document.getElementById("root");
if (container === null) throw new Error("missing #root element");
createRoot(container).render(<App />);

registerServiceWorker();
