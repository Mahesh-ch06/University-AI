// Drive the real chat UI (Vite dev server + full backend) through messages that produce each card type and
// screenshot every answer. Usage: node ui_review.js <outdir> <width>x<height> [portal|widget] [scale]
const { chromium } = require('playwright');
const crypto = require('crypto');
const [outdir, size = '1440x900', mode = 'portal', scale = '1'] = process.argv.slice(2);
const [W, H] = size.split('x').map(Number);
const BASE = 'http://localhost:5173';
const API = 'http://127.0.0.1:8080/api/v1/agent';
const MESSAGES = (process.env.MSGS || [
  'How do I apply?', 'B.Tech CSE fees', 'Compare B.Tech fees for all branches', 'placement statistics',
  'What are the placement packages?', 'hostel facilities', 'B.Tech CSE curriculum', 'Am I eligible for B.Tech CSE?',
  'Show me campus videos', 'Who is the HOD of CSE?', 'What programmes do you offer?', 'I want to visit the campus',
].join('|')).split('|');

(async () => {
  const sid = 'uireview-' + crypto.randomUUID();
  await fetch(`${API}/profile`, { method: 'PUT', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ session_id: sid, name: 'Asha Rani', phone: '9876543210' }) });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: Number(scale),
    isMobile: W < 600, hasTouch: W < 600 });
  await ctx.addInitScript(([s]) => {
    localStorage.setItem('university_ai_session_id', s);
    localStorage.setItem('sru_student_lead', JSON.stringify({ name: 'Asha Rani', phone: '9876543210' }));
  }, [sid]);
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  await page.goto(BASE + (mode === 'widget' ? '/?mode=widget' : '/'));
  if (mode === 'portal') {
    await page.click('.sru-launcher-avatar-btn');
  }
  await page.waitForSelector('.sru-widget-textarea');
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${outdir}/00-welcome.png` });
  let i = 1;
  for (const msg of MESSAGES) {
    const before = await page.locator('.message-bubble-row.assistant').count();
    await page.fill('.sru-widget-textarea', msg);
    await page.keyboard.press('Enter');
    await page.waitForFunction((n) => document.querySelectorAll('.message-bubble-row.assistant').length > n &&
      !document.querySelector('.sru-typing-bubble'), before, { timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(900);
    const last = page.locator('.message-bubble-row.assistant').last();
    const name = `${String(i).padStart(2, '0')}-${msg.replace(/[^a-z0-9]+/gi, '-').toLowerCase().slice(0, 40)}`;
    try { await last.screenshot({ path: `${outdir}/${name}.png` }); } catch (e) { errors.push('shot ' + name + ': ' + e.message); }
    // horizontal overflow inside the chat body?
    const overflow = await page.evaluate(() => {
      const body = document.querySelector('.sru-widget-body');
      const out = [];
      if (!body) return out;
      const limit = body.getBoundingClientRect().right + 1;
      const clipped = (el) => {
        for (let p = el.parentElement; p && p !== body; p = p.parentElement) {
          const ox = getComputedStyle(p).overflowX;
          if (ox === 'auto' || ox === 'scroll' || ox === 'hidden') {
            const pr = p.getBoundingClientRect();
            if (pr.right <= limit) return true;
          }
        }
        return false;
      };
      for (const el of body.querySelectorAll('*')) {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.right > limit && !clipped(el)) out.push(`${typeof el.className === 'string' ? el.className : el.tagName} right=${Math.round(r.right)} > ${Math.round(limit)}`);
      }
      if (document.documentElement.scrollWidth > window.innerWidth + 1) out.push('PAGE horizontal scroll ' + document.documentElement.scrollWidth + ' > ' + window.innerWidth);
      const input = document.querySelector('.sru-widget-textarea');
      if (input) { const ir = input.getBoundingClientRect(); if (ir.bottom > window.innerHeight + 1 || ir.top < 0) out.push('INPUT not visible ' + Math.round(ir.top) + '-' + Math.round(ir.bottom)); }
      return [...new Set(out)].slice(0, 6);
    });
    if (overflow.length) errors.push(`overflow after "${msg}": ` + overflow.join(' | '));
    i++;
  }
  await page.screenshot({ path: `${outdir}/99-panel.png` });
  console.log(JSON.stringify({ size, mode, errors }, null, 1));
  await browser.close();
})();
