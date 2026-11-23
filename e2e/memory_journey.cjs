// Conversation memory journey in the real UI (Vite + full backend + PostgreSQL + Redis).
// "Time passing" is simulated by moving this session's saved message timestamps back in the database.
// Usage: node memory_ui.js <outdir> <width>x<height> [scale]
const { chromium } = require('playwright');
const { execSync } = require('child_process');
const crypto = require('crypto');
const [outdir, size = '390x844', scale = '1'] = process.argv.slice(2);
const [W, H] = size.split('x').map(Number);
const BASE = 'http://localhost:5173/?mode=widget';
const API = 'http://127.0.0.1:8080/api/v1';
const psql = (sql) => execSync(`psql -h 127.0.0.1 -p 5433 -U university_ai -d university_ai -tAc "${sql}"`).toString().trim();
const age = (sid, interval) => psql(`UPDATE messages SET created_at = created_at - interval '${interval}' WHERE conversation_id IN (SELECT id FROM conversations WHERE session_id='${sid}')`);
const results = [];
const check = (name, pass, detail = '') => results.push({ name, pass: !!pass, detail });

async function open(browser, sid, url = BASE) {
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: Number(scale), isMobile: W < 600, hasTouch: W < 600 });
  await ctx.addInitScript(([s]) => {
    localStorage.setItem('university_ai_session_id', s);
    localStorage.setItem('sru_student_lead', JSON.stringify({ name: 'Asha Rani', phone: '9876543210' }));
  }, [sid]);
  const page = await ctx.newPage();
  page.errors = [];
  page.on('pageerror', (e) => page.errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error' && !/TUNNEL|ERR_INTERNET|Failed to load resource/.test(m.text())) page.errors.push(m.text()); });
  await page.goto(url);
  await page.waitForSelector('.sru-widget-textarea');
  return { ctx, page };
}

async function send(page, text) {
  const before = await page.locator('.message-bubble-row.assistant').count();
  await page.fill('.sru-widget-textarea', text);
  await page.keyboard.press('Enter');
  await page.waitForFunction((n) => document.querySelectorAll('.message-bubble-row.assistant').length > n && !document.querySelector('.sru-typing-bubble'), before, { timeout: 30000 });
  await page.waitForTimeout(700);
  return (await page.locator('.message-bubble-row.assistant').last().innerText());
}

(async () => {
  const browser = await chromium.launch();
  const sid = 'memui-' + crypto.randomUUID();
  await fetch(`${API}/agent/profile`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ session_id: sid, name: 'Asha Rani', phone: '9876543210' }) });

  // 1. A first conversation with real context
  let { ctx, page } = await open(browser, sid);
  check('no previous conversation: normal welcome, no panel', (await page.locator('.wb-panel').count()) === 0 && (await page.locator('.message-bubble-row.assistant').count()) === 1);
  await send(page, 'B.Tech CSE fees');
  await send(page, 'hostel facilities');
  const firstConv = psql(`SELECT id FROM conversations WHERE session_id='${sid}'`);
  check('conversation saved in the database', /^[0-9a-f-]{36}$/.test(firstConv), firstConv);

  // 2. Refresh during the conversation: it stays, no question
  await page.reload();
  await page.waitForSelector('.message-bubble-row.user');
  await page.waitForTimeout(800);
  check('refresh: conversation stays on screen', (await page.locator('.message-bubble-row.user').count()) === 2);
  check('refresh: no welcome-back question', (await page.locator('.wb-panel').count()) === 0);
  await ctx.close();

  // 3. Browser closed and reopened after 10 minutes: continues quietly
  age(sid, '10 minutes');
  ({ ctx, page } = await open(browser, sid));
  await page.waitForSelector('.message-bubble-row.user', { timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(600);
  check('back after 10 min: conversation restored without asking', (await page.locator('.message-bubble-row.user').count()) === 2 && (await page.locator('.wb-panel').count()) === 0);
  await ctx.close();

  // 4. Back after 2 hours: the choice appears
  age(sid, '2 hours');
  ({ ctx, page } = await open(browser, sid));
  await page.waitForSelector('.wb-panel', { timeout: 8000 }).catch(() => {});
  const panelText = (await page.locator('.wb-panel').innerText().catch(() => '')) || '';
  check('back after 2 h: welcome-back choice shown', panelText.includes('Welcome back, Asha'), panelText.replace(/\n/g, ' | '));
  check('choice shows when and what', /2 hours ago/.test(panelText) && /hostel facilities/i.test(panelText));
  check('nothing restored or started before choosing', (await page.locator('.message-bubble-row.user').count()) === 0);
  await page.screenshot({ path: `${outdir}/1-welcome-back.png` });
  // a question typed before choosing waits for the choice
  await page.fill('.sru-widget-textarea', 'Is there a gym?');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(500);
  check('typed question waits for the choice', /answer “Is there a gym\?”/.test(await page.locator('.wb-panel').innerText()));
  await page.screenshot({ path: `${outdir}/2-pending-question.png` });
  // Continue
  await page.click('.wb-btn--primary');
  await page.waitForSelector('.wb-resume-divider', { timeout: 10000 }).catch(() => {});
  await page.waitForFunction(() => !document.querySelector('.sru-typing-bubble') && document.querySelectorAll('.message-bubble-row.assistant').length >= 4, null, { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(900);
  const lastAnswer = await page.locator('.message-bubble-row.assistant').last().innerText();
  check('continue: earlier messages restored', (await page.locator('.message-bubble-row.user').count()) === 3);
  check('continue: divider shows where it resumed', (await page.locator('.wb-resume-divider').count()) === 1);
  check('continue: pending question answered in the SAME conversation with its history', /received [1-9]\d* earlier turn/.test(lastAnswer), lastAnswer.slice(0, 160));
  const convCount1 = psql(`SELECT count(*) FROM conversations WHERE session_id='${sid}'`);
  check('continue: no duplicate conversation created', convCount1 === '1', convCount1);
  await page.screenshot({ path: `${outdir}/3-continued.png` });
  await ctx.close();

  // 5. Back the next day: start a new chat
  age(sid, '1 day');
  ({ ctx, page } = await open(browser, sid));
  await page.waitForSelector('.wb-panel', { timeout: 8000 });
  await page.click('.wb-btn--secondary');
  await page.waitForFunction(() => !document.querySelector('.wb-panel'), null, { timeout: 10000 });
  check('start new: welcome with quick actions', (await page.locator('.welcome-actions-card-wrapper, .welcome-actions-grid, [class*="welcome-action"]').count()) > 0);
  check('start new: old messages not shown', (await page.locator('.message-bubble-row.user').count()) === 0);
  const fresh = await send(page, 'Tell me about the library');
  check('start new: model got NO earlier turns', /received 0 earlier turn/.test(fresh), fresh.slice(0, 160));
  check('start new: no previous course carried over', !/btech_cse/.test(fresh), fresh.slice(0, 200));
  const convs = psql(`SELECT count(*) FROM conversations WHERE session_id='${sid}'`);
  const oldMsgs = psql(`SELECT count(*) FROM messages WHERE conversation_id='${firstConv}'`);
  check('start new: old conversation still saved with its messages', convs === '2' && Number(oldMsgs) >= 6, `conversations=${convs} old messages=${oldMsgs}`);
  await page.screenshot({ path: `${outdir}/4-new-chat.png` });
  await ctx.close();

  // 6. Reopen soon after: the NEW conversation continues; the old one is not offered
  ({ ctx, page } = await open(browser, sid));
  await page.waitForTimeout(1500);
  const users = await page.locator('.message-bubble-row.user').allInnerTexts();
  check('reopen: the new conversation continues, old one not offered', users.length === 1 && /library/.test(users[0]) && (await page.locator('.wb-panel').count()) === 0, users.join(' | '));
  await ctx.close();

  // 7. Connection drops while restoring: honest error, then retry works
  age(sid, '3 hours');
  ({ ctx, page } = await open(browser, sid));
  await page.waitForSelector('.wb-panel', { timeout: 8000 });
  await page.route('**/api/v1/conversations/**', (r) => r.abort('internetdisconnected'));
  await page.click('.wb-btn--primary');
  await page.waitForSelector('.wb-error', { timeout: 8000 }).catch(() => {});
  check('offline: error shown, nothing lost', /connection/i.test(await page.locator('.wb-error').innerText().catch(() => '')));
  await page.screenshot({ path: `${outdir}/5-offline-error.png` });
  await page.unroute('**/api/v1/conversations/**');
  await page.click('.wb-btn--primary');
  await page.waitForSelector('.wb-resume-divider', { timeout: 10000 }).catch(() => {});
  check('offline: retry restores the conversation', (await page.locator('.message-bubble-row.user').count()) === 1);
  check('no page errors in the journey', page.errors.length === 0, page.errors.join(' | '));
  await ctx.close();

  // 8. Another student never gets this conversation
  const other = 'memui-' + crypto.randomUUID();
  const ctxRes = await (await fetch(`${API}/agent/recovery-context?session_id=${other}`)).json();
  const read = await fetch(`${API}/conversations/${firstConv}?session_id=${other}`);
  check('another student: nothing offered and the chat cannot be read', ctxRes.has_resumable_conversation === false && read.status === 404, `offered=${ctxRes.has_resumable_conversation} read=${read.status}`);
  ({ ctx, page } = await open(browser, other, `http://localhost:5173/?mode=widget&chat=${firstConv}`));
  await page.waitForTimeout(1200);
  check('another student: shared link does not open it', (await page.locator('.message-bubble-row.user').count()) === 0);
  await ctx.close();

  await browser.close();
  for (const r of results) console.log(`${r.pass ? 'PASS' : 'FAIL'}  ${r.name}${r.detail ? '  [' + r.detail + ']' : ''}`);
  process.exit(results.every((r) => r.pass) ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(2); });
