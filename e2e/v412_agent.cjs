// v4.12.0 in the real UI: the admin settings switch (grouped / full table), the lowest-fee agent and its plan,
// "talk to a counsellor" (admin accepts / nobody accepts), and the counsellor copilot.
// A student window and an admin window run side by side. Restores the default settings at the end.
// Usage: node v412_agent.cjs <outdir> <width>x<height>
const { chromium } = require('playwright');
const crypto = require('crypto');
const fs = require('fs');
const [outdir, size = '390x844'] = process.argv.slice(2);
const [W, H] = size.split('x').map(Number);
const BASE = 'http://localhost:5173/?mode=widget';
const ADMIN = 'http://localhost:5173/#sru-ops-9f4a7c2e';
const API = 'http://127.0.0.1:8080/api/v1';
const KEY = process.env.ADMIN_KEY || 'change-me-in-production';
const results = [];
const check = (name, pass, detail = '') => results.push({ name, pass: !!pass, detail: String(detail).slice(0, 300) });
fs.mkdirSync(outdir, { recursive: true });

const rows = (page) => page.locator('.message-bubble-row.assistant');
async function waitAnswer(page, before) {
  await page.waitForFunction((n) => document.querySelectorAll('.message-bubble-row.assistant').length > n
    && !document.querySelector('.sru-typing-bubble'), before, { timeout: 30000 });
  await page.waitForTimeout(700);
  const n = await rows(page).count();
  return rows(page).nth(n - 1);
}
async function send(page, text) {
  const before = await rows(page).count();
  await page.fill('.sru-widget-textarea', text);
  await page.keyboard.press('Enter');
  return waitAnswer(page, before);
}
async function chip(page, row, label) {
  const before = await rows(page).count();
  await row.locator('.suggestion-chip', { hasText: label }).first().click();
  return waitAnswer(page, before);
}
async function student(browser) {
  const sid = 'v412-' + crypto.randomUUID();
  await fetch(`${API}/agent/profile`, { method: 'PUT', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ session_id: sid, name: 'Asha Rani', phone: '9876543210' }) });
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, isMobile: W < 600, hasTouch: W < 600 });
  await ctx.addInitScript(([s]) => {
    if (!sessionStorage.getItem('seeded')) {
      localStorage.setItem('university_ai_session_id', s);
      localStorage.setItem('sru_student_lead', JSON.stringify({ name: 'Asha Rani', phone: '9876543210' }));
      sessionStorage.setItem('seeded', '1');
    }
  }, [sid]);
  const page = await ctx.newPage();
  page.errors = [];
  page.on('pageerror', (e) => page.errors.push(e.message));
  await page.goto(BASE);
  await page.waitForSelector('.sru-widget-textarea');
  return { ctx, page, sid };
}
const putSettings = (body) => fetch(`${API}/admin/settings`, { method: 'PUT',
  headers: { 'content-type': 'application/json', 'X-Admin-Key': KEY }, body: JSON.stringify(body) });

async function main() {
  const browser = await chromium.launch();
  // ---------- admin window ----------
  const actx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await actx.addInitScript(([k]) => sessionStorage.setItem('university_ai_admin_key', k), [KEY]);
  const admin = await actx.newPage();
  admin.errors = [];
  admin.on('pageerror', (e) => admin.errors.push(e.message));
  await admin.goto(ADMIN);
  await admin.locator('.admin-tab-btn', { hasText: 'Agent' }).click();
  await admin.waitForSelector('.agc-segment');
  check('A1 admin: Agent tab with the settings', (await admin.locator('.agc-setting-title').count()) >= 2);

  // 1. switch to the full table in the admin panel -> the chat shows the table
  await admin.locator('.agc-segment button', { hasText: 'Full table' }).click();
  await admin.waitForSelector('.agc-ok');
  check('A2 admin: switched to the full table (saved)', /Saved/.test(await admin.locator('.agc-ok').innerText()));
  await new Promise((r) => setTimeout(r, 300));
  let { ctx, page } = await student(browser);
  let row = await send(page, 'What are the special category fee concessions?');
  check('A3 chat follows the switch at once: full table (19 rows)', (await row.locator('.fp-select-table tbody tr').count()) === 19
    && (await row.locator('.fp-grouped').count()) === 0);
  await ctx.close();

  // 2. switch back to grouped -> grouped card, pick a category through a group
  await admin.locator('.agc-segment button', { hasText: 'Grouped' }).click();
  await admin.waitForTimeout(800);
  ({ ctx, page } = await student(browser));
  for (const m of ['Calculate my scholarship', 'B.Tech CSE', 'Telangana State Board', 'Completed', '870']) await send(page, m);
  row = await send(page, 'MPC');
  const grouped = row.locator('.fp-grouped');
  check('B1 grouped card: 5 folded groups, no option visible yet', (await grouped.locator('.fp-group').count()) === 5
    && (await grouped.locator('.fp-option').count()) === 0);
  check('B2 "None of these apply" button inside the card', (await grouped.locator('.fp-none').count()) === 1);
  await grouped.locator('.fp-group-head', { hasText: 'Your state' }).click();
  check('B3 opening a group shows only its options', (await grouped.locator('.fp-option').count()) === 5);
  await grouped.locator('.fp-group-head', { hasText: 'Other circumstances' }).click();
  check('B4 private group shows a privacy note', /You won't be asked about it/.test(await grouped.innerText()));
  await grouped.locator('.fp-group-head', { hasText: 'Your state' }).click();
  await grouped.locator('.fp-option', { hasText: 'Students from Andhra Pradesh' }).click();
  await page.screenshot({ path: `${outdir}/1-grouped-picked.png` });
  let before = await rows(page).count();
  await grouped.locator('.fp-apply').click();
  row = await waitAnswer(page, before);
  check('B5 picked from a group: evaluated as pending', /isn't applied yet/.test(await row.innerText()));
  await ctx.close();

  // 3. lowest-fee agent with its plan
  ({ ctx, page } = await student(browser));
  row = await send(page, 'Find me the lowest fee for B.Tech CSE');
  check('C1 lowest-fee goal: the plan card', (await row.locator('.ag-plan .ag-step').count()) === 6);
  for (const m of ['Telangana State Board', 'Completed', '720']) row = await send(page, m);
  row = await send(page, 'MPC');
  row = await send(page, 'my jee percentile is 96');
  check('C2 agent compares routes and picks the best (JEE 40%)', /40%/.test(await row.innerText()));
  row = await chip(page, row, 'Show my final fee');
  const plan = row.locator('.ag-plan');
  check('C3 final: summary card; plan finished (hostel skipped, not left "to do")', (await row.locator('.fp-summary').count()) === 1
    && (await plan.locator('.ag-step--done').count()) === 5 && (await plan.locator('.ag-step--skipped').count()) === 1
    && (await plan.locator('.ag-step--todo, .ag-step--now').count()) === 0, await plan.innerText().catch(() => ''));
  await row.locator('.ag-plan').screenshot({ path: `${outdir}/2-agent-plan.png` });
  await ctx.close();

  // 4. talk to a counsellor: in office hours for this test, short wait
  await putSettings({ office_days: [0, 1, 2, 3, 4, 5, 6], office_hours_start: '00:00', office_hours_end: '23:59',
    connect_wait_seconds: 20, connect_enabled: true });
  await admin.reload();
  await admin.locator('.admin-tab-btn', { hasText: 'Leads' }).click();
  ({ ctx, page } = await student(browser));
  row = await send(page, 'I want to talk to a counsellor');
  check('D1 student: "Connecting you…" with a countdown', (await row.locator('.ag-connect--waiting .ag-timer').count()) === 1);
  await page.screenshot({ path: `${outdir}/3-connecting.png` });
  await admin.waitForSelector('.agc-banner', { timeout: 10000 });
  check('D2 admin: banner rings on another tab', /wants to talk to a counsellor now/.test(await admin.locator('.agc-banner').innerText()));
  await admin.locator('.agc-banner button', { hasText: 'Open' }).click();
  await admin.waitForSelector('.agc-live');
  await admin.screenshot({ path: `${outdir}/4-admin-ringing.png` });
  await admin.locator('.agc-live button', { hasText: "I'll call now" }).click();
  await admin.waitForSelector('.agc-live.is-accepted');
  check('D3 admin: accepted, number to call shown', /98765\s?43210|9876543210/.test(await admin.locator('.agc-live-call').innerText()));
  await page.waitForSelector('.ag-connect--ok', { timeout: 10000 });
  check('D4 student: "A counsellor will call you now on ******3210"', /will call you now on \*{6}3210/.test(await row.innerText()));
  await page.screenshot({ path: `${outdir}/5-connected.png` });
  await ctx.close();

  // 5. nobody accepts -> busy + callback
  ({ ctx, page } = await student(browser));
  row = await send(page, 'can I speak to a real person');
  await page.waitForSelector('.ag-connect--busy', { timeout: 35000 });
  const busy = await row.innerText();
  check('E1 after the wait: "all our counsellors are busy" + callback on ******3210', /All our counsellors are busy/.test(busy) && /\*{6}3210/.test(busy));
  await page.screenshot({ path: `${outdir}/6-busy.png` });
  await ctx.close();

  // 6. copilot
  await admin.locator('.admin-tab-btn', { hasText: 'Agent' }).click();
  await admin.locator('button', { hasText: 'Who should I call first?' }).click();
  await admin.waitForSelector('.agc-lead', { timeout: 10000 });
  const first = await admin.locator('.agc-lead').first().innerText();
  check('F1 copilot: ranked leads with reasons', /asked|finished|talk to a counsellor/.test(first), first.slice(0, 160));
  await admin.locator('.agc-lead').first().locator('button', { hasText: 'Draft a message' }).click();
  await admin.waitForSelector('.agc-draft textarea');
  check('F2 copilot: draft written, nothing sent', /SR University Admissions/.test(await admin.locator('.agc-draft textarea').inputValue()));
  await admin.screenshot({ path: `${outdir}/7-copilot.png`, fullPage: true });
  check('no page errors', admin.errors.length === 0, admin.errors.join(' | '));
  await browser.close();
}

(async () => {
  try { await main(); } catch (e) { check('journey ran to the end', false, e.message.split('\n')[0]); }
  await putSettings({ concession_picker: 'grouped', connect_enabled: true, connect_wait_seconds: 30,
    office_hours_start: '09:00', office_hours_end: '18:00', office_days: [0, 1, 2, 3, 4, 5] }).catch(() => {});
  const failed = results.filter((r) => !r.pass);
  for (const r of results) console.log(`${r.pass ? 'PASS' : 'FAIL'}  ${r.name}${r.pass ? '' : '  -> ' + r.detail}`);
  console.log(`\n${results.length - failed.length}/${results.length} passed`);
  process.exit(failed.length ? 1 : 0);
})();
