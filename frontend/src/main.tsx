import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import './styles/polish.css'
import './styles/official-widget.css'

// The embeddable widget (public/widget.js opens /?mode=widget) uses the official sru.edu.in look
// (styles/official-widget.css). Set before the first render so there is no flash of the other look.
try {
  const params = new URLSearchParams(window.location.search)
  if (params.get('mode') === 'widget' || /^\/widget\/?$/.test(window.location.pathname)) {
    document.documentElement.dataset.surface = 'widget'
  }
} catch {
  /* no URL API: keep the default look */
}

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
