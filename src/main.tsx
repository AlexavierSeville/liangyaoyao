import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import SettingsPanel from "./SettingsPanel";

const isSettingsWindow =
  new URLSearchParams(window.location.search).get("window") === "settings";

document.documentElement.dataset.window = isSettingsWindow ? "settings" : "pet";
document.body.dataset.window = isSettingsWindow ? "settings" : "pet";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    {isSettingsWindow ? <SettingsPanel /> : <App />}
  </React.StrictMode>,
);
