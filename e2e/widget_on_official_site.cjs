// Screenshots of the SRU Buddy widget ON the official website (sru.edu.in), for UI reviews.
// Loads the live sru.edu.in (through the session's proxy), injects the local widget.js (http://localhost:5173),
// and captures: the closed bubble, the open chat (welcome), the contact form, and a conversation with cards.
// Usage: node widget_on_official_site.cjs <outdir> [desktop|mobile]
// Optional CDN_MIRROR=<dir>: where cdn.jsdelivr.net is blocked (as in the review sandbox), the site's Bootstrap and
// Swiper are served from <dir>/<pkg>_<version>/package/... (made with `npm pack bootstrap@5.3.3` etc.); without
// them the official page lays out wider than a phone and the bubble ends up off-screen.
const { chromium } = require('playwright');
const fs = require('fs');
const [outdir, kind = 'desktop'] = process.argv.slice(2);
fs.mkdirSync(outdir, { recursive: true });
const LOCAL = 'http://localhost:5173';
const mobile = kind === 'mobile';

(async () => {
  const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY, bypass: 'localhost,127.0.0.1' } : undefined;
  const browser = await chromium.launch({ proxy });
  const ctx = await browser.newContext(mobile
    ? { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }
    : { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  if (process.env.CDN_MIRROR) {
    const path = require('path');
    await page.route(/^https:\/\/cdn\.jsdelivr\.net\/npm\/([^@/]+)@([^/]+)\/([^?]+)/, (route) => {
      const [, pkg, ver, file] = route.request().url().match(/npm\/([^@/]+)@([^/]+)\/([^?]+)/);
      const local = path.join(process.env.CDN_MIRROR, `${pkg}_${ver}`, 'package', file);
      if (fs.existsSync(local)) return route.fulfill({ path: local });
      return route.abort();
    });
  }
  try {
    await page.goto('https://sru.edu.in/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  } catch (e) {
    await page.goto(`${LOCAL}/widget-demo.html`);   // offline fallback
  }
  await page.waitForTimeout(3000);
  await page.evaluate((local) => {
    const s = document.createElement('script');
    s.src = `${local}/widget.js`;
    s.setAttribute('data-host', local);
    s.setAttribute('data-app-url', `${local}/?mode=widget`);
    document.body.appendChild(s);
  }, LOCAL);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${outdir}/${kind}-1-closed.png` });

  await page.locator('#sru-buddy-widget .launcher .dot').click();
  const frame = page.frameLocator('#sru-buddy-widget iframe');
  await frame.locator('.sru-widget-textarea').waitFor({ timeout: 30000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${outdir}/${kind}-2-open-welcome.png` });

  const assistants = () => frame.locator('.message-bubble-row.assistant').count();
  const waitAnswer = async (before) => {
    for (let i = 0; i < 160; i++) {
      if ((await assistants()) > before && !(await frame.locator('.sru-typing-bubble').count())) break;
      await page.waitForTimeout(250);
    }
    await page.waitForTimeout(900);
  };
  let leadDone = false;
  const send = async (text) => {
    const before = await assistants();
    await frame.locator('.sru-widget-textarea').fill(text);
    await frame.locator('.sru-widget-textarea').press('Enter');
    if (!leadDone) {
      // the two-step contact form (name, then mobile) appears before the first answer
      const nameBox = frame.locator('.chat-lead-form input[type="text"]');
      try { await nameBox.waitFor({ timeout: 6000 }); } catch (e) { leadDone = true; }
      if (!leadDone) {
        await page.screenshot({ path: `${outdir}/${kind}-3a-contact-name.png` });
        await nameBox.fill('Asha Rani');
        await frame.locator('.chat-lead-submit-btn').click();
        const tel = frame.locator('.chat-lead-form input[type="tel"]');
        await tel.waitFor({ timeout: 10000 });
        await page.screenshot({ path: `${outdir}/${kind}-3b-contact-phone.png` });
        await tel.fill('9876543210');
        await frame.locator('.chat-lead-submit-btn').click();
        leadDone = true;
      }
    }
    await waitAnswer(before);
  };
  await send('Calculate my scholarship');
  for (const m of ['B.Tech CSE', 'Telangana State Board', 'Completed', '885', 'MPC']) await send(m);
  await page.screenshot({ path: `${outdir}/${kind}-4-result-concessions.png` });
  await frame.locator('.fp-group-head', { hasText: 'Family link to SRU' }).click().catch(() => {});
  await frame.locator('.fp-option', { hasText: 'SR Junior College student' }).click().catch(() => {});
  await page.screenshot({ path: `${outdir}/${kind}-5-picked.png` });
  { const b = await assistants(); await frame.locator('.fp-apply').click().catch(() => {}); await waitAnswer(b); }
  await page.screenshot({ path: `${outdir}/${kind}-5b-pending.png` });
  await send('Yes, I have it');
  await send("No hostel, I'm a day scholar");
  await send("No, I'll manage");
  await page.screenshot({ path: `${outdir}/${kind}-6-final.png` });
  const card = frame.locator('.fp-summary').last();
  if (await card.count()) await card.screenshot({ path: `${outdir}/${kind}-7-fee-card.png` }).catch(() => {});
  await browser.close();
})();
