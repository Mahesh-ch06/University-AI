import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import './styles/polish.css'

// Production Anti-Inspection & Console Protection
if (import.meta.env.PROD) {
  // 1. Neutralize all console logging and tracking methods
  const noop = () => {};
  const methods = [
    'log', 'debug', 'info', 'warn', 'error', 'table', 'trace',
    'dir', 'dirxml', 'group', 'groupCollapsed', 'groupEnd',
    'time', 'timeLog', 'timeEnd', 'count', 'countReset', 'assert'
  ] as const;

  methods.forEach((method) => {
    try {
      (window.console as any)[method] = noop;
    } catch {}
  });

  // 2. Clear console continuously to prevent memory inspection or backtracking
  try {
    window.console.clear();
    setInterval(() => {
      try {
        window.console.clear();
      } catch {}
    }, 2000);
  } catch {}

  // 3. Block right-click context menu (Inspect Element)
  document.addEventListener('contextmenu', (e) => {
    e.preventDefault();
  });

  // 4. Block common developer tools shortcut keys (F12, Ctrl+Shift+I/J/C, Ctrl+U)
  document.addEventListener('keydown', (e) => {
    if (
      e.key === 'F12' ||
      (e.ctrlKey && e.shiftKey && ['I', 'i', 'J', 'j', 'C', 'c'].includes(e.key)) ||
      (e.metaKey && e.altKey && ['I', 'i', 'J', 'j', 'C', 'c', 'U', 'u'].includes(e.key)) ||
      (e.ctrlKey && ['U', 'u', 'S', 's'].includes(e.key))
    ) {
      e.preventDefault();
      e.stopPropagation();
    }
  });
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
