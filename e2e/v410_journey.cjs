// v4.10.0 journey in the real UI (Vite + full backend + PostgreSQL + Redis; only Gemini is replaced).
// A: Start afresh  B: dynamic answers  C: knowledge retrieval  D: context, concessions, fee chart, chips.
// Usage: node v410_journey.cjs <outdir> <width>x<height>
const { chromium } = require('playwright');
const crypto = require('crypto');
const fs = require('fs');
const [outdir, size = '390x844'] = process.argv.slice(2);
const [W, H] = size.split('x').map(Number);
const BASE = 'http://localhost:5173/?mode=widget';
const API = 'http://127.0.0.1:8080/api/v1';
const results = [];
const check = (name, pass, detail = '') => results.push({ name, pass: !!pass, detail: String(detail).slice(0, 300) });
fs.mkdirSync(outdir, { recursive: true });

async function open(browser, sid) {
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
  return { ctx, page };
}

const assistantRows = (page) => page.locator('.message-bubble-row.assistant');
async function waitAnswer(page, before) {
  await page.waitForFunction((n) => document.querySelectorAll('.message-bubble-row.assistant').length > n
    && !document.querySelector('.sru-typing-bubble'), before, { timeout: 30000 });
  await page.waitForTimeout(800);
  const n = await assistantRows(page).count();
  return assistantRows(page).nth(n - 1);   // pinned: later answers do not change which row this is
}
async function send(page, text) {
  const before = await assistantRows(page).count();
  await page.fill('.sru-widget-textarea', text);
  await page.keyboard.press('Enter');
  return waitAnswer(page, before);
}
async function chip(page, label) {
  const before = await assistantRows(page).count();
  const n = await assistantRows(page).count();
  await assistantRows(page).nth(n - 1).locator('.suggestion-chip', { hasText: label }).first().click();
  return waitAnswer(page, before);
}
const chipsOf = async (row) => row.locator('.suggestion-chip-text').allInnerTexts();
const bullets = async (row) => (await row.locator('.message-text-bubble li').allInnerTexts()).map((l) => l.trim());
const sessionId = (page) => page.evaluate(() => localStorage.getItem('university_ai_session_id'));

async function main() {
  const browser = await chromium.launch();
  const sid = 'v410-' + crypto.randomUUID();
  await fetch(`${API}/agent/profile`, { method: 'PUT', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ session_id: sid, name: 'Asha Rani', phone: '9876543210' }) });
  const { ctx, page } = await open(browser, sid);

  // ---------------- A. Start afresh ----------------
  await send(page, 'cse fee with 85% in inter, state board');
  const oldUserCount = await page.locator('.message-bubble-row.user').count();
  // a question in flight when "new chat" is pressed must not land in the new chat
  await page.fill('.sru-widget-textarea', 'why should I choose SRU');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(150);
  await page.locator('button[aria-label="Reset Chat"]').first().click();
  await page.waitForTimeout(3500);
  const sid2 = await sessionId(page);
  check('A1 new chat: a new session ID', sid2 && sid2 !== sid, `${sid} -> ${sid2}`);
  check('A2 new chat: no old messages on screen', (await page.locator('.message-bubble-row.user').count()) === 0
    && (await assistantRows(page).count()) === 1, `${oldUserCount} user msgs before`);
  check('A3 the reply in flight did not land in the new chat', !(await page.locator('.messages-area, body').first().innerText()).includes('strengths at a glance')
    && !(await page.locator('body').innerText()).includes('A few reasons students choose SRU'));
  await page.screenshot({ path: `${outdir}/A-fresh.png` });
  let row = await send(page, 'calculate my scholarship');
  let t = await row.innerText();
  check('A4 fresh session: no old marks or programme offered', !/85|Use my saved details|B\.Tech CSE/i.test(t), t.replace(/\n/g, ' | '));
  check('A5 fresh session: the name is not used', !/Asha/.test(t));
  const prof = await (await fetch(`${API}/agent/profile?session_id=${encodeURIComponent(sid2)}`)).json();
  check('A6 new session on the server: contact kept, no marks or programme', prof.profile?.phone && !prof.profile?.percent && !prof.profile?.program_interest && !prof.profile?.board, JSON.stringify(prof.profile));
  await page.reload();
  await page.waitForSelector('.sru-widget-textarea');
  await page.waitForTimeout(1500);
  check('A7 after reload: still the new session, old chat not offered', (await sessionId(page)) === sid2 && (await page.locator('.wb-panel').count()) === 0);
  check('A8 contact form not asked again', (await page.locator('.chat-lead-form, .lead-auth-modal').count()) === 0);

  // ---------------- B. Dynamic answers ----------------
  row = await send(page, 'why should I choose SRU');
  const why1 = await row.innerText();
  const b1 = await bullets(row);
  row = await send(page, 'why should I choose SRU');
  const why2 = await row.innerText();
  const b2 = await bullets(row);
  check('B1 why SRU: 3-4 points from the facts', b1.length >= 3 && b1.length <= 4, b1.join(' / '));
  check('B2 asked again: new points, not the same text', b2.length > 0 && !b1.some((b) => b2.includes(b)), b2.join(' / '));
  check('B3 no unverified 95% claim', !/95\s*%/.test(why1 + why2));
  await page.screenshot({ path: `${outdir}/B-why-again.png` });

  // ---------------- C. Knowledge retrieval ----------------
  row = await send(page, 'is SRU ranked number one in india?');
  t = await row.innerText();
  check('C1 ranking question: ranks, no blunt "No"', /NIRF|QS Asia|THE World/.test(t) && !/^\s*no\b/i.test(t), t.split('\n')[0]);
  row = await send(page, 'is sru nba accredited');
  t = await row.innerText();
  check('C2 accreditation question answered with NBA', /NBA Tier-I/.test(t) && !/QS Asia/.test(t));
  await send(page, 'research at sru');
  row = await send(page, 'what is the hostel curfew');
  t = await row.innerText();
  check('C3 a new question is not mistaken for an answer to the last one', /curfew|in-time|9:00 PM|8:30/i.test(t) && !/Research Quality/.test(t), t.split('\n')[0]);

  // ---------------- D. Context, concessions, fee chart, chips ----------------
  row = await send(page, 'what special concessions are there?');
  const table = row.locator('.fp-concessions');
  check('D1 concessions: a table card with 19 rows', (await table.count()) === 1 && (await table.locator('tbody tr').count()) === 19);
  check('D2 concessions: short lead, list not repeated in text', (await row.locator('.message-text-bubble').first().innerText()).length < 260);
  check('D3 apply disabled until a row is picked', await table.locator('.fp-apply').isDisabled());
  await table.locator('tbody tr', { hasText: 'Students from Andhra Pradesh' }).first().click();
  await page.screenshot({ path: `${outdir}/D-concessions-picked.png` });
  let before = await assistantRows(page).count();
  await table.locator('.fp-apply').click();
  row = await waitAnswer(page, before);
  t = await row.innerText();
  check('D4 picked AP: asks which programme (none chosen yet)', /Which programme/.test(t) && /Students from Andhra Pradesh/.test(t), t.split('\n')[0]);
  check('D5 table locks after applying', await table.locator('.fp-apply').isDisabled());
  // v4.11.0: a picked concession is evaluated (pending), never applied straight away (see v411_fee_agent.cjs)
  row = await chip(page, 'B.Tech CSE');
  t = await row.innerText();
  check('D6 programme given: proof asked, no instant discount card', /supporting document/.test(t)
    && (await row.locator('.fp-concession-fee, .fp-summary').count()) === 0);
  row = await send(page, 'Show my final fee');
  const summary = row.locator('.fp-summary');
  t = await row.innerText();
  check('D7 "show my final fee": summary, concession pending (3,65,000 now; 3,50,000 if approved)',
    (await summary.count()) === 1 && /3,65,000/.test(t) && /3,50,000/.test(t) && /Pending verification/.test(t));
  check('D8 fee summary with Share and WhatsApp', (await summary.locator('button', { hasText: 'Share' }).count()) === 1
    && (await summary.locator('a.agent-card-wa-btn').count()) === 1);
  check('D9 open steps listed (scholarship, hostel)', /Still open/.test(t) && /Hostel: not chosen yet/.test(t));
  // a second fresh chat (the scholarship steps started in A4 are still waiting in the first one)
  await page.locator('button[aria-label="Reset Chat"]').first().click();
  await page.waitForTimeout(1500);
  check('D9b second new chat: empty again', (await page.locator('.message-bubble-row.user').count()) === 0);
  row = await send(page, 'my inter percentage is 85, state board. cse fee with ac hostel 4 sharing');
  t = await row.innerText();
  check('D10 fee with hostel: offers the complete fee chart', /complete fee chart/.test(t));
  check('D11 offer chips are Yes / No only', JSON.stringify(await chipsOf(row)) === JSON.stringify(['Yes, prepare my fee chart', 'No, thanks']), JSON.stringify(await chipsOf(row)));
  check('D12 one fee card (no generic table as well)', (await row.locator('.rich-card').count()) === 1, await row.locator('.rich-card').count());
  row = await chip(page, 'Yes, prepare my fee chart');
  t = await row.innerText();
  check('D13 summary includes hostel and the merit scholarship', /Hostel \(AC, 4-sharing\)/.test(t) && /Academic scholarship \(25%\)/.test(t));
  check('D14 chart total 4,05,000 = 2,55,000 + 20,000 + 5,000 + 1,25,000 (concession shown separately)', /4,05,000/.test(t), t.replace(/\n/g, ' | ').slice(0, 400));
  row = await send(page, 'please ask a counsellor to call me');
  const callbackChips = await chipsOf(row);
  t = await row.innerText();
  check('D15 after a callback request: no unrelated chips', callbackChips.every((c) => !/Why Choose SRU|Fee & Scholarship Info/.test(c)), JSON.stringify(callbackChips) + ' :: ' + t.split('\n')[0]);
  row = await send(page, 'thanks');
  check('D16 thanks: no chips', (await chipsOf(row)).length === 0, JSON.stringify(await chipsOf(row)));
  await page.screenshot({ path: `${outdir}/D-end.png`, fullPage: false });
  check('no page errors', page.errors.length === 0, page.errors.join(' | '));

  await ctx.close();
  await browser.close();
}

const setPicker = (mode) => fetch(`${API}/admin/settings`, { method: 'PUT',
  headers: { 'content-type': 'application/json', 'X-Admin-Key': process.env.ADMIN_KEY || 'change-me-in-production' },
  body: JSON.stringify({ concession_picker: mode }) });

(async () => {
  // These journeys click rows of the 19-row table: run them in "Full table" mode (v4.12.0 admin switch),
  // then put back the default (grouped). v412_agent.cjs covers the grouped picker.
  await setPicker('table').catch(() => {});
  try { await main(); } catch (e) { check('journey ran to the end', false, e.message.split('\n')[0]); }
  await setPicker('grouped').catch(() => {});
  const failed = results.filter((r) => !r.pass);
  for (const r of results) console.log(`${r.pass ? 'PASS' : 'FAIL'}  ${r.name}${r.pass ? '' : '  -> ' + r.detail}`);
  console.log(`\n${results.length - failed.length}/${results.length} passed`);
  fs.writeFileSync(`${outdir}/results.json`, JSON.stringify(results, null, 2));
  process.exit(failed.length ? 1 : 0);
})();
