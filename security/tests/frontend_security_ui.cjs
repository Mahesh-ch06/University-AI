// Usage: cd frontend && npx vite --port 5175 --strictPort &  then: node ../security/tests/frontend_security_ui.cjs
// Needs Playwright with Chromium (not a project dependency; pre-installed in CI images or `npm i -g playwright`).
// Browser checks for the frontend security fixes (run against the Vite dev server on :5175).
const { chromium } = require('playwright');
const BASE = 'http://localhost:5175';
(async () => {
  const browser = await chromium.launch();
  const results = [];
  const ok = (name, pass, detail = '') => { results.push({ name, pass, detail }); };

  // 1. Export to PDF escapes message HTML (SEC-05). Dev server has no CSP, so this tests the escaping alone.
  {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    await page.goto(BASE + '/');
    const popupPromise = ctx.waitForEvent('page');
    await page.evaluate(async () => {
      window.__xss = 0;
      const m = await import('/src/utils/exportChat.ts');
      m.exportToPDF('Test <b>title</b>', [
        { id: '1', role: 'user', content: '<img src=x onerror="window.opener.__xss=1">**bold** <script>window.opener.__xss=2</script>', created_at: new Date().toISOString() },
        { id: '2', role: 'assistant', content: 'Fees are **₹2,85,000**', created_at: new Date().toISOString(),
          sources: [{ title: '<svg onload="window.opener.__xss=3">', section: 'x', page: 2 }] },
      ]);
    });
    const popup = await popupPromise;
    await popup.waitForLoadState();
    await page.waitForTimeout(600);
    const imgs = await popup.locator('.msg-body img').count();
    const scripts = await popup.locator('script').count();
    const svgs = await popup.locator('.messages svg, .msg-body svg, .sources-box svg').count();
    const strong = await popup.locator('.msg-body strong').count();
    const text = await popup.locator('.msg-body').first().innerText();
    const xss = await page.evaluate(() => window.__xss);
    ok('export: injected HTML is not executed', xss === 0, `__xss=${xss}`);
    ok('export: no img/script/svg elements created', imgs === 0 && scripts === 0 && svgs === 0, `img=${imgs} script=${scripts} svg=${svgs}`);
    ok('export: text shown literally, bold still works', text.includes('<img src=x') && strong >= 1, text.slice(0, 60));
    await ctx.close();
  }

  // 2. Only the embedding parent may open the registration form (SEC-15).
  {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    await page.goto(BASE + '/');
    await page.waitForTimeout(800);
    await page.evaluate(() => window.postMessage({ type: 'sru-buddy:register' }, '*'));
    await page.waitForTimeout(800);
    ok('postMessage: top-level self-post does not open the form', (await page.locator('.lead-modal-card').count()) === 0);

    await page.setContent(`<iframe id="w" src="${BASE}/?mode=widget" style="width:420px;height:700px"></iframe>`);
    const frameEl = await page.waitForSelector('#w');
    const frame = await frameEl.contentFrame();
    await frame.waitForLoadState();
    await page.waitForTimeout(1200);
    await page.evaluate(() => document.getElementById('w').contentWindow.postMessage({ type: 'sru-buddy:register' }, '*'));
    await frame.waitForSelector('.lead-modal-card', { timeout: 5000 }).catch(() => null);
    ok('postMessage: the embedding parent still opens the form', (await frame.locator('.lead-modal-card').count()) === 1);
    await ctx.close();
  }

  // 3. An admin key in the URL is stripped and never sent in a URL (SEC-02).
  {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    const urls = [];
    page.on('request', (r) => urls.push(r.url()));
    const SECRET = 'SECRET-ADMIN-KEY-123456789';
    await page.goto(`${BASE}/?chat=00000000-0000-4000-8000-000000000001&admin_key=${SECRET}`);
    await page.waitForTimeout(1500);
    const leaked = urls.filter((u) => u.includes(SECRET) && !u.startsWith(BASE + '/?'));
    ok('admin key: removed from the address bar', !page.url().includes(SECRET), page.url());
    ok('admin key: not sent to the API in any URL', leaked.length === 0, leaked.join(' '));
    await ctx.close();
  }

  await browser.close();
  for (const r of results) console.log(`${r.pass ? 'PASS' : 'FAIL'}  ${r.name}${r.detail ? '  [' + r.detail + ']' : ''}`);
  process.exit(results.every((r) => r.pass) ? 0 : 1);
})();
