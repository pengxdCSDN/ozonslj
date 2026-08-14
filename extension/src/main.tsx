import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./styles.css";
import "./operations.css";
import "./desktop.css";
import "./frontend-design.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("缺少应用挂载节点");
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>
);
