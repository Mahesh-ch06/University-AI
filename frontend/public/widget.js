/*!
 * SRU Buddy chat widget (v3.0.0)
 *
 * Add SRU Buddy to any web page (for example the SR University admission page) with ONE line,
 * just before </body>:
 *
 *   <script src="https://university-ai-companion.vercel.app/widget.js" defer><\/script>
 *
 * Optional settings on the same tag:
 *   data-position="left"            bubble on the left (default: right)
 *   data-color="#1d4ed8"            bubble colour
 *   data-label="Ask SRU Buddy"      text next to the bubble on wide screens ("" hides it)
 *   data-greeting="Hi! ..."         the small greeting shown once per visit ("" turns it off)
 *   data-open="true"                open the chat straight away
 *
 * From the page's own JavaScript: window.SRUBuddy.open(), .close(), .toggle().
 *
 * The chat itself is the same SRU Buddy app (same answers, same fee calculator, same knowledge),
 * opened in compact "widget" mode, so every improvement to the website reaches the widget too.
 * Nothing is loaded until the student shows interest (hover / focus / tap), so the host page
 * stays fast.
 */
(function () {
  "use strict";
  if (window.SRUBuddy && window.SRUBuddy.__loaded) return;

  var PROD_BASE = "https://university-ai-companion.vercel.app";
  var script =
    document.currentScript ||
    (function () {
      var all = document.getElementsByTagName("script");
      for (var i = all.length - 1; i >= 0; i--) {
        if (/widget\.js(\?|$)/.test(all[i].src)) return all[i];
      }
      return null;
    })();
  var opt = function (name, fallback) {
    var v = script && script.getAttribute("data-" + name);
    return v === null || v === undefined ? fallback : v;
  };
  var base = opt("host", (function () {
    if (script && script.src) {
      try {
        var origin = new URL(script.src, location.href).origin;
        if (origin && origin !== "null" && origin.indexOf("sru.edu.in") === -1) {
          return origin;
        }
      } catch (e) {}
    }
    if (typeof location !== "undefined") {
      if (location.hostname === "localhost" || location.hostname === "127.0.0.1" || /vercel\.app$/.test(location.hostname)) {
        return location.origin;
      }
    }
    return PROD_BASE;
  })());
  var side = opt("position", "right") === "left" ? "left" : "right";
  var rawColor = opt("color", "#0055a4");
  var color = /^#(?:[0-9a-fA-F]{3}){1,2}$/.test(rawColor) ? rawColor : "#0055a4";
  var label = opt("label", "Ask SRU Buddy 👋");
  var greeting = opt("greeting", "Hi! Questions about admissions 2027-28? Ask me.");
  var startOpen = opt("open", "false") === "true";
  var rawAppUrl = opt("app-url", base + "/?mode=widget");
  var appUrl = (function () {
    try {
      var u = new URL(rawAppUrl, base);
      if (
        u.protocol === "https:" ||
        (u.protocol === "http:" && (u.hostname === "localhost" || u.hostname === "127.0.0.1"))
      ) {
        return u.href;
      }
    } catch (e) {}
    return base + "/?mode=widget";
  })();

  var host = document.createElement("div");
  host.id = "sru-buddy-widget";
  host.style.cssText = "position:fixed;z-index:2147483000;bottom:0;" + side + ":0;width:0;height:0;";
  var root = host.attachShadow ? host.attachShadow({ mode: "open" }) : host;

  var css =
    ":host{all:initial}" +
    "*{box-sizing:border-box;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}" +
    ".launcher-cluster{position:fixed;bottom:max(20px,env(safe-area-inset-bottom,20px));" + side + ":max(20px,env(safe-area-inset-" + side + ",20px));display:flex;align-items:center;gap:12px;" +
    "flex-direction:" + (side === "left" ? "row-reverse" : "row") + ";z-index:2147483000;-webkit-tap-highlight-color:transparent;touch-action:manipulation}" +
    ".register-btn{background:linear-gradient(135deg,#0055a4 0%,#2979e2 100%);color:#ffffff;border:none;border-radius:8px;padding:9px 13px;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:0.5px;cursor:pointer;box-shadow:0 4px 16px rgba(0,85,164,0.4);transition:all .2s ease;display:flex;flex-direction:column;align-items:center;line-height:1.15;user-select:none}" +
    ".register-btn:hover{background:linear-gradient(135deg,#004382 0%,#1c66c9 100%);transform:translateY(-2px);box-shadow:0 6px 22px rgba(0,85,164,0.55)}" +
    ".launcher{position:relative;border:0;background:none;padding:0;cursor:pointer;display:flex;align-items:center;justify-content:center;user-select:none;-webkit-tap-highlight-color:transparent;touch-action:manipulation}" +
    ".launcher .dot{width:62px;height:62px;border-radius:50%;background:" + color + ";border:3px solid #fff;display:flex;align-items:center;" +
    "justify-content:center;box-shadow:0 8px 24px rgba(0,85,164,.45);transition:transform .15s ease;" +
    "animation:sruPulse 2.5s infinite;padding:8px}" +
    "@keyframes sruPulse{0%{box-shadow:0 0 0 0 rgba(41,121,226,.7),0 8px 24px rgba(0,0,0,.3)}70%{box-shadow:0 0 0 16px rgba(41,121,226,0),0 8px 24px rgba(0,0,0,.3)}100%{box-shadow:0 0 0 0 rgba(41,121,226,0),0 8px 24px rgba(0,0,0,.3)}}" +
    ".launcher:hover .dot{transform:scale(1.08)}" +
    ".launcher .dot img{width:38px;height:auto;max-height:24px;object-fit:contain;display:block}" +
    ".tooltip{position:absolute;bottom:calc(100% + 10px);right:0;background:#ffffff;color:#0055a4;font-size:12px;font-weight:700;padding:5px 12px;border-radius:999px;box-shadow:0 4px 18px rgba(0,85,164,0.18);border:1px solid #e2e8f0;white-space:nowrap;animation:sruFloat 2.6s ease-in-out infinite alternate;pointer-events:auto;cursor:pointer;z-index:2;display:block!important}" +
    ".tooltip::after{content:'';position:absolute;top:100%;right:24px;border-width:5px;border-style:solid;border-color:#ffffff transparent transparent transparent}" +
    "@keyframes sruFloat{0%{transform:translateY(0)}100%{transform:translateY(-4px)}}" +
    ".launcher:focus-visible{outline:none}.launcher:focus-visible .dot{outline:3px solid #2979e2;outline-offset:3px}" +
    ".greet{position:fixed;bottom:calc(max(20px,env(safe-area-inset-bottom,20px)) + 74px);" + side + ":max(20px,env(safe-area-inset-" + side + ",20px));max-width:280px;background:#fff;color:#0f172a;font-size:14px;" +
    "line-height:1.4;padding:12px 34px 12px 14px;border-radius:14px;box-shadow:0 8px 28px rgba(15,23,42,.2);cursor:pointer;z-index:2147483000}" +
    ".greet button{position:absolute;top:6px;right:6px;border:0;background:none;font-size:16px;line-height:1;color:#64748b;" +
    "cursor:pointer;padding:4px}" +
    ".panel{position:fixed;bottom:calc(max(20px,env(safe-area-inset-bottom,20px)) + 74px);" + side + ":max(20px,env(safe-area-inset-" + side + ",20px));width:420px;max-width:calc(100vw - 32px);height:min(720px,calc(100dvh - 110px));" +
    "background:#ffffff;border:1px solid #e2e8f0;border-radius:18px;overflow:hidden;box-shadow:0 20px 50px rgba(0,50,110,.18),0 0 0 1px rgba(0,0,0,.04);display:none;z-index:2147483001}" +
    ".panel.open{display:block}.panel iframe{width:100%;height:100%;border:0;display:block;background:#ffffff}" +
    "@media (max-width:768px){" +
    ".panel{left:0!important;right:0!important;bottom:0!important;top:0!important;width:100%!important;width:100vw!important;height:100%!important;height:100dvh!important;height:-webkit-fill-available!important;max-width:none!important;max-height:none!important;border-radius:0!important;border:none!important;box-shadow:none!important;margin:0!important}" +
    ".launcher-cluster{bottom:max(16px,env(safe-area-inset-bottom,16px));" + side + ":max(16px,env(safe-area-inset-" + side + ",16px));gap:8px}" +
    ".register-btn{padding:7px 10px;font-size:10px;border-radius:6px;display:flex!important}" +
    ".launcher .dot{width:58px;height:58px}" +
    ".tooltip{display:block!important;font-size:11px;padding:4px 10px;bottom:calc(100% + 8px);right:0}" +
    ".tooltip::after{right:20px}" +
    ".open-mobile .launcher-cluster,.open-mobile .greet{display:none!important}}" +
    "@media (prefers-reduced-motion:reduce){.launcher .dot{transition:none}}";

  var style = document.createElement("style");
  style.textContent = css;
  root.appendChild(style);

  var wrap = document.createElement("div");
  root.appendChild(wrap);

  var cluster = document.createElement("div");
  cluster.className = "launcher-cluster";

  var regBtn = document.createElement("button");
  regBtn.className = "register-btn";
  regBtn.type = "button";
  regBtn.setAttribute("aria-label", "Register Now for SR University Admissions");
  var regSpan1 = document.createElement("span");
  regSpan1.textContent = "REGISTER";
  var regSpan2 = document.createElement("span");
  regSpan2.textContent = "NOW";
  regBtn.appendChild(regSpan1);
  regBtn.appendChild(regSpan2);

  var launcher = document.createElement("button");
  launcher.className = "launcher";
  launcher.type = "button";
  launcher.setAttribute("aria-label", "Open SRU Buddy, the SR University admissions assistant");
  launcher.setAttribute("aria-expanded", "false");
  launcher.setAttribute("aria-controls", "sru-buddy-panel");

  var tooltip = document.createElement("div");
  tooltip.className = "tooltip";
  tooltip.textContent = label || "Ask SRU Buddy 👋";

  var dotSpan = document.createElement("span");
  dotSpan.className = "dot";

  var logoImg = document.createElement("img");
  logoImg.alt = "SRU";
  logoImg.src = base + "/sru-logo-white.png";

  dotSpan.appendChild(logoImg);
  launcher.appendChild(tooltip);
  launcher.appendChild(dotSpan);

  cluster.appendChild(regBtn);
  cluster.appendChild(launcher);
  wrap.appendChild(cluster);

  var panel = document.createElement("div");
  panel.className = "panel";
  panel.id = "sru-buddy-panel";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", "SRU Buddy chat");
  wrap.appendChild(panel);

  var frame = null;
  function load() {
    if (frame) return;
    frame = document.createElement("iframe");
    frame.title = "SRU Buddy, SR University admissions assistant";
    frame.src = appUrl;
    frame.allow = "microphone; clipboard-write";
    frame.setAttribute("sandbox", "allow-scripts allow-same-origin allow-forms allow-popups");
    frame.setAttribute("loading", "eager");
    panel.appendChild(frame);
  }

  var greet = null;
  function hideGreeting() {
    if (greet && greet.parentNode) greet.parentNode.removeChild(greet);
    greet = null;
    try {
      sessionStorage.setItem("sru_buddy_greeted", "1");
    } catch (e) {
      /* storage blocked: fine */
    }
  }

  var isOpen = false;
  function open() {
    load();
    hideGreeting();
    isOpen = true;
    panel.classList.add("open");
    wrap.classList.add("open-mobile");
    launcher.setAttribute("aria-expanded", "true");
    launcher.setAttribute("aria-label", "Close SRU Buddy");
    setTimeout(function () {
      try {
        frame.focus();
      } catch (e) {
        /* ignore */
      }
    }, 50);
  }
  function close() {
    isOpen = false;
    panel.classList.remove("open");
    wrap.classList.remove("open-mobile");
    launcher.setAttribute("aria-expanded", "false");
    launcher.setAttribute("aria-label", "Open SRU Buddy, the SR University admissions assistant");
    launcher.focus();
  }
  function toggle() {
    if (isOpen) close();
    else open();
  }

  launcher.addEventListener("click", toggle);
  regBtn.addEventListener("click", function (e) {
    e.stopPropagation();
    load();
    open();
    setTimeout(function () {
      try {
        if (frame && frame.contentWindow) {
          frame.contentWindow.postMessage({ type: "sru-buddy:register" }, base);
        }
      } catch (err) {}
    }, 350);
  });
  // Start loading as soon as the student shows interest: the chat is ready when they click.
  ["pointerenter", "focus", "touchstart"].forEach(function (ev) {
    launcher.addEventListener(ev, load, { passive: true, once: true });
    regBtn.addEventListener(ev, load, { passive: true, once: true });
  });
  document.addEventListener("keydown", function (e) {
    if (isOpen && e.key === "Escape") close();
  });
  window.addEventListener("message", function (e) {
    if (e.origin !== base && e.origin !== PROD_BASE) return;
    if (!e.data || e.data.type !== "sru-buddy:close") return;
    close();
  });

  function mount() {
    document.body.appendChild(host);
    var greeted = false;
    try {
      greeted = sessionStorage.getItem("sru_buddy_greeted") === "1";
    } catch (e) {
      greeted = false;
    }
    if (startOpen) {
      open();
    } else if (greeting && !greeted) {
      setTimeout(function () {
        if (isOpen) return;
        greet = document.createElement("div");
        greet.className = "greet";
        greet.setAttribute("role", "status");
        var greetSpan = document.createElement("span");
        greetSpan.textContent = greeting;
        var dismissBtn = document.createElement("button");
        dismissBtn.type = "button";
        dismissBtn.setAttribute("aria-label", "Dismiss");
        dismissBtn.textContent = "×";
        greet.appendChild(greetSpan);
        greet.appendChild(dismissBtn);
        dismissBtn.addEventListener("click", function (e) {
          e.stopPropagation();
          hideGreeting();
        });
        greet.addEventListener("click", open);
        wrap.appendChild(greet);
      }, 4000);
    }
  }
  if (document.body) mount();
  else document.addEventListener("DOMContentLoaded", mount);

  window.SRUBuddy = { open: open, close: close, toggle: toggle, __loaded: true };
})();
