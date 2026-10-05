import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";
async function start() {
  if (import.meta.env.VITE_API_MODE !== "live") {
    const { worker } = await import("./mocks/browser");
    await worker.start({ onUnhandledRequest: "bypass", quiet: true });
  }
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}
start().catch((error) => {
  document.getElementById("root")!.textContent =
    `Không khởi tạo được môi trường demo: ${error.message}`;
});
