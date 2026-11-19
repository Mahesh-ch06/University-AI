import { lazy, Suspense, useEffect, useState } from "react";
import ChatPage from "./pages/ChatPage";
import { setChannel } from "./services/api";
import "./index.css";

const AdminPage = lazy(() => import("./pages/AdminPage"));

/**
 * The secret admin slug used to access the university staff console.
 * Can be overridden via VITE_ADMIN_PATH in Vercel / environment settings.
 * Defaults to an unguessable randomized token so no one can guess `/#admin`.
 */
const ADMIN_SECRET_SLUG = (
  (import.meta.env.VITE_ADMIN_PATH as string | undefined) || "sru-ops-9f4a7c2e"
)
  .replace(/^#\/?/, "")
  .trim();

function isAdminRoute(): boolean {
  try {
    const hash = window.location.hash.replace(/^#\/?/, "").trim().toLowerCase();
    const searchParams = new URLSearchParams(window.location.search);
    const querySlug = (searchParams.get("admin") || searchParams.get("admin_key") || "").trim().toLowerCase();
    const target = ADMIN_SECRET_SLUG.toLowerCase();
    return (hash.length > 0 && hash === target) || (querySlug.length > 0 && querySlug === target);
  } catch {
    return false;
  }
}

function staffMode(): boolean {
  try {
    if (isAdminRoute()) {
      sessionStorage.setItem("sru_staff_mode", "1");
      return true;
    }
    return sessionStorage.getItem("sru_staff_mode") === "1";
  } catch {
    return false;
  }
}

/** The embeddable widget (public/widget.js) opens this app with ?mode=widget. */
function isWidgetMode(): boolean {
  try {
    const params = new URLSearchParams(window.location.search);
    return params.get("mode") === "widget" || /^\/widget\/?$/.test(window.location.pathname);
  } catch {
    return false;
  }
}

function App() {
  const widget = isWidgetMode();
  const [isStaff, setIsStaff] = useState<boolean>(staffMode);
  const [view, setView] = useState<"chat" | "admin">(() =>
    isAdminRoute() ? "admin" : "chat"
  );

  useEffect(() => {
    const onHash = () => {
      if (isAdminRoute()) {
        setIsStaff(staffMode());
        setView("admin");
      }
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const backToChat = () => {
    if (window.location.hash) {
      history.replaceState(null, "", window.location.pathname + window.location.search);
    }
    setView("chat");
  };

  if (widget) {
    setChannel("widget");
    return <ChatPage variant="widget" />;
  }

  return view === "admin" ? (
    <Suspense fallback={null}>
      <AdminPage onBackToChat={backToChat} />
    </Suspense>
  ) : (
    <ChatPage onOpenAdmin={isStaff ? () => setView("admin") : undefined} />
  );
}

export default App;
