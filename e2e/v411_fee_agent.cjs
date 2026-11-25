// v4.11.0 fee evaluation agent in the real UI (Vite + full backend + PostgreSQL + Redis; only Gemini replaced).
// Eligibility -> qualification -> concessions -> special consideration (pending) -> scholarship -> hostel -> final.
// Usage: node v411_fee_agent.cjs <outdir> <width>x<height>
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

const rows = (page) => page.locator('.message-bubble-row.assistant');
async function waitAnswer(page, before) {
  await page.waitForFunction((n) => document.querySelectorAll('.message-bubble-row.assistant').length > n
    && !document.querySelector('.sru-typing-bubble'), before, { timeout: 30000 });
  await page.waitForTimeout(800);
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
const chips = (row) => row.locator('.suggestion-chip-text').allInnerTexts();

async function open(browser) {
  const sid = 'v411-' + crypto.randomUUID();
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
  return { ctx, page };
}

async function main() {
  const browser = await chromium.launch();

  // ---------- 1. Eligibility -> concessions -> special consideration -> hostel -> final ----------
  let { ctx, page } = await open(browser);
  const tiles = await page.locator('.welcome-action-tile').allInnerTexts();
  check('1 fourth welcome tile is "Special Consideration"', /Special Consideration/.test(tiles[3] || ''), tiles[3]);
  for (const m of ['Calculate my scholarship', 'B.Tech CSE', 'Telangana State Board', 'Completed', '870']) await send(page, m);
  let row = await send(page, 'MPC');
  let t = await row.innerText();
  check('2 eligibility: meets the minimum (never promised admission)', /minimum/.test(t) && !/qualify for this programme/.test(t), t.split('\n')[0]);
  check('3 concessions introduced before the fee', /Before we finalise your fee/.test(t) && (await row.locator('.fp-concessions').count()) === 1);
  check('4 no fee card yet', (await row.locator('.fp-summary, .agent-fee-card, .fee-card').count()) === 0);
  check('5 options: none apply / show my final fee', JSON.stringify(await chips(row)) === JSON.stringify(['None of these apply', 'Show my final fee']), JSON.stringify(await chips(row)));
  await page.screenshot({ path: `${outdir}/1-qualified-concessions.png` });
  const table = row.locator('.fp-concessions');
  await table.locator('tbody tr', { hasText: 'Students from Andhra Pradesh' }).first().click();
  let before = await rows(page).count();
  await table.locator('.fp-apply').click();
  row = await waitAnswer(page, before);
  t = await row.innerText();
  check('6 picked: not applied, evaluated (pending)', /isn't applied yet/.test(t) && /supporting document/.test(t), t.split('\n')[0]);
  row = await chip(page, row, 'Yes, I have it');
  t = await row.innerText();
  const hostelChips = await chips(row);
  check('7 marks already known: scholarship not asked again; hostel asked', !/academic scholarship/.test(t) && /hostel/i.test(t));
  check('8 hostel options include "No hostel"', hostelChips.length === 5 && hostelChips.some((c) => /No hostel/.test(c)), JSON.stringify(hostelChips));
  row = await send(page, 'what is the hostel curfew');
  check('9 side question answered; progress kept (continue chip)', (await chips(row)).some((c) => /Continue my fee estimate/.test(c)), JSON.stringify(await chips(row)));
  row = await chip(page, row, 'Continue my fee estimate');
  t = await row.innerText();
  check('10 continue: back at the hostel step', /Picking up where we left off/.test(t) && /hostel/i.test(t));
  row = await chip(page, row, 'AC 4-sharing');
  const card = row.locator('.fp-summary');
  t = await row.innerText();
  check('11 final fee card shown', (await card.count()) === 1);
  check('12 confirmed payable 4,15,000 (2,55,000 + 5,000 + 15,000 + 5,000 + 1,25,000 + 10,000 deposit)', /4,15,000/.test(await card.locator('.fp-total-main').innerText()));
  check('13 after approval 4,00,000 shown apart, as an estimate', /4,00,000/.test(await card.locator('.fp-total-after').innerText()));
  check('14 concession row marked pending, scholarship row applied', (await card.locator('tr.is-pending .fp-pill--pending').count()) === 1 && (await card.locator('tr.is-discount .fp-pill--ok').count()) === 1);
  check('15 approved concessions = scholarship only (85,000)', /Approved concessions\s*₹85,000/.test((await card.locator('.fp-table tfoot').innerText()).replace(/\n/g, ' ')));
  check('16 share and WhatsApp', (await card.locator('button', { hasText: 'Share' }).count()) === 1 && (await card.locator('a.agent-card-wa-btn').count()) === 1);
  await card.screenshot({ path: `${outdir}/2-final-fee-card.png` });
  row = await send(page, 'how much will I pay after the scholarship?');
  check('17 "how much will I pay" answered from the evaluation', /25% scholarship/.test(await row.innerText()) && (await row.locator('.fp-summary').count()) === 1);
  check('no page errors (flow 1)', page.errors.length === 0, page.errors.join(' | '));
  await ctx.close();

  // ---------- 2. The Special Consideration tile ----------
  ({ ctx, page } = await open(browser));
  before = await rows(page).count();
  await page.locator('.welcome-action-tile').nth(3).click();
  row = await waitAnswer(page, before);
  t = await row.innerText();
  check('18 tile: evaluation explained, categories shown, nothing approved', /evaluated for an additional fee concession/.test(t) && (await row.locator('.fp-concessions').count()) === 1 && !/approved\b(?! only)/i.test(t.replace(/approved only after/i, '')));
  await page.screenshot({ path: `${outdir}/3-special-consideration.png` });
  const tbl = row.locator('.fp-concessions');
  await tbl.locator('tbody tr', { hasText: 'Lateral entry students' }).first().click();
  before = await rows(page).count();
  await tbl.locator('.fp-apply').click();
  row = await waitAnswer(page, before);
  check('19 programme asked (not known yet)', /Which programme/.test(await row.innerText()));
  row = await chip(page, row, 'B.Tech ECE');
  row = await chip(page, row, 'Not yet');
  t = await row.innerText();
  check('20 academic scholarship offered with Yes / No', /academic scholarship/.test(t) && JSON.stringify(await chips(row)) === JSON.stringify(['Yes, check my scholarship', 'No, skip it']));
  row = await chip(page, row, 'Yes, check my scholarship');
  t = await row.innerText();
  check('21 only the missing details: step 1, programme not asked again', /Step 1 of/.test(t) && /B\.Tech ECE/.test(t), t.split('\n')[0]);
  for (const m of ['CBSE', 'Completed', '92']) row = await send(page, m);
  row = await send(page, 'MPC');
  t = await row.innerText();
  check('22 scholarship result, then the next step (no concessions re-offer)', /30% scholarship/.test(t) && !/Before we finalise/.test(t) && /hostel/i.test(t));
  row = await send(page, 'thanks');
  t = await row.innerText();
  check('23 "thanks" with the fee unfinished: offer to finish', /Before you go/.test(t) && (await chips(row)).some((c) => /Show my final fee/.test(c)));
  row = await chip(page, row, "No hostel");
  row = await chip(page, row, 'Yes, add the bus');
  const c2 = row.locator('.fp-summary');
  check('24 final: ECE 92% CBSE + bus = 2,44,000 confirmed, 2,29,000 after approval',
    /2,44,000/.test(await c2.locator('.fp-total-main').innerText()) && /2,29,000/.test(await c2.locator('.fp-total-after').innerText()));
  check('25 proof still to be submitted shown as pending', /proof to be submitted/.test(await c2.innerText()));
  await c2.screenshot({ path: `${outdir}/4-final-special-consideration.png` });
  check('no page errors (flow 2)', page.errors.length === 0, page.errors.join(' | '));
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
  process.exit(failed.length ? 1 : 0);
})();
