import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

// Bootstrap CSS
import "bootstrap/dist/css/bootstrap.min.css";

// ⬇️ ADD THIS LINE
import "bootstrap/dist/js/bootstrap.bundle.min.js";

// Point @monaco-editor/react at the monaco-editor package already bundled by
// webpack (via monaco-editor-webpack-plugin in craco.config.js) instead of its
// default behaviour of fetching the editor from the jsDelivr CDN at runtime.
// Without this, the Template Editor page never loads when offline or when the
// CDN is unreachable — it just shows "Loading" forever.
import { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
loader.config({ monaco });


// Suppress benign ResizeObserver loop notifications from Monaco Editor.
window.addEventListener("error", (e) => {
  if (
    e.message === "ResizeObserver loop completed with undelivered notifications." ||
    e.message === "ResizeObserver loop limit exceeded"
  ) {
    e.stopImmediatePropagation();
  }
});

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
