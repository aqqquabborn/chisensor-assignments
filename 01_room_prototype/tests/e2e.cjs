/**
 * Browser checks for the six flows named in the brief, at 390 px width.
 *   npm run build && npm run test:e2e
 * Needs Playwright with Chromium: `npm i -D playwright && npx playwright install chromium`
 * if it is not installed globally.
 */
const { spawn } = require('node:child_process');
const assert = require('node:assert/strict');
const path = require('node:path');

let chromium;
try { ({ chromium } = require('playwright')); } catch {
  console.error('Playwright not found. Run: npm i -D playwright && npx playwright install chromium');
  process.exit(2);
}

const PORT = 4174;
const URL = `http://localhost:${PORT}`;
const results = [];

async function check(name, fn, page) {
  const t = Date.now();
  try { await fn(page); results.push([name, 'PASS', Date.now() - t]); }
  catch (e) { results.push([name, 'FAIL', Date.now() - t, e.message]); }
}

const store = (p) => p.evaluate(() => JSON.parse(localStorage.getItem('chisensor_app_store') || 'null'));
const state = (p) => p.getByTestId('state').innerText();
const waitState = (p, s, timeout = 15000) => p.waitForFunction((want) => document.querySelector('[data-testid=state]')?.textContent === want, s, { timeout });
const noOverflow = async (p, where) => {
  const w = await p.evaluate(() => document.scrollingElement.scrollWidth);
  assert.ok(w <= 390, `horizontal overflow on ${where}: ${w}px`);
};
const scenario = async (p, label) => {
  await p.getByTestId('panel-toggle').click();
  await p.getByRole('button', { name: label }).click();
  await p.getByTestId('panel-toggle').click();
};
const debug = async (p) => {
  await p.getByTestId('panel-toggle').click();
  const d = JSON.parse(await p.getByTestId('debug').innerText());
  await p.getByTestId('panel-toggle').click();
  return d;
};

(async () => {
  const server = spawn(process.platform === 'win32' ? 'npx.cmd' : 'npx', ['vite', 'preview', '--port', String(PORT), '--strictPort'],
    { cwd: path.join(__dirname, '..'), stdio: 'ignore' });
  await new Promise((r) => setTimeout(r, 1500));
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
  // Fail loudly if anything tries to use the camera or a payment API.
  await ctx.addInitScript(() => {
    window.__forbidden = [];
    const deny = (n) => () => { window.__forbidden.push(n); return Promise.reject(new Error('forbidden')); };
    if (navigator.mediaDevices) navigator.mediaDevices.getUserMedia = deny('getUserMedia');
    window.PaymentRequest = function () { window.__forbidden.push('PaymentRequest'); };
  });
  const p = await ctx.newPage();
  const errors = [];
  p.on('pageerror', (e) => errors.push(e.message));
  await p.goto(URL);

  await check('1 happy path: scan → analysis → free action → pay → verify → deliver', async () => {
    await scenario(p, '① happy');
    await p.getByText('Goal:').waitFor();                         // room goal and constraints shown first
    await p.getByText('The bed stays where it is').waitFor();
    await noOverflow(p, 'start');
    await p.getByRole('button', { name: /Start scan/ }).click();
    for (const n of ['entry', 'bedside_path', 'bed_outline']) await p.check(`input[name=${n}]`);
    await noOverflow(p, 'scan');
    await p.getByRole('button', { name: 'Submit scan' }).click();
    await waitState(p, 'analyzing');
    await p.getByText('SIMULATED').first().waitFor();
    await noOverflow(p, 'analysis');
    await waitState(p, 'free_action');
    assert.match(await p.getByTestId('free-action-status').innerText(), /Not opened/);
    await p.getByRole('button', { name: /Show the suggested position/ }).click();
    assert.match(await p.getByTestId('free-action-status').innerText(), /Suggested — not done yet/);
    await p.getByRole('button', { name: /I have moved the chair/ }).click();
    assert.match(await p.getByTestId('free-action-status').innerText(), /Done by you/);
    await noOverflow(p, 'free action');
    await p.getByRole('button', { name: /See what the full plan adds/ }).click();
    await p.getByRole('button', { name: /Unlock plan/ }).click();
    await waitState(p, 'purchase_pending');
    let d = await debug(p);
    assert.equal(d.content_unlocked, false, 'pending must not unlock');
    await p.getByRole('button', { name: /store confirms payment/ }).click();
    await waitState(p, 'purchase_verified');
    await p.getByRole('button', { name: /delivery succeeds/ }).click();
    await waitState(p, 'delivered');
    d = await debug(p);
    assert.equal(d.content_unlocked, true);
    assert.equal(d.purchases, 1);
    await p.getByText('Stays in place: Bed.').waitFor();
    await noOverflow(p, 'delivered');
  }, p);

  await check('2 unsupported device: explained before the scan, path blocked', async () => {
    await scenario(p, '① happy');
    await p.getByRole('button', { name: /Simulate: unsupported device/ }).click();
    await waitState(p, 'unsupported');
    await p.getByText(/needs a LiDAR sensor/).waitFor();
    assert.equal(await p.getByRole('button', { name: /Start scan|Submit scan|Retry/ }).count(), 0);
    await noOverflow(p, 'unsupported');
  }, p);

  await check('3 incomplete scan: missing area listed, captured areas kept, no analysis', async () => {
    await scenario(p, '① happy');
    await p.getByRole('button', { name: /Start scan/ }).click();
    await p.check('input[name=entry]');
    await p.getByRole('button', { name: /Submit scan \(2 areas missing\)/ }).click();
    await waitState(p, 'scan_incomplete');
    await p.getByText(/missing — the walk from the entry/).waitFor();
    assert.equal((await store(p)).analysisJob, null, 'no analysis on partial input');
    await p.getByRole('button', { name: /Re-scan missing areas/ }).click();
    assert.equal(await p.isChecked('input[name=entry]'), true, 'captured area kept');
    await p.check('input[name=bedside_path]'); await p.check('input[name=bed_outline]');
    await p.getByRole('button', { name: 'Submit scan' }).click();
    await waitState(p, 'analyzing');
  }, p);

  await check('4 analysis: refresh restores the same job and constraints; failure recovers', async () => {
    await scenario(p, '① happy');
    await p.getByRole('button', { name: /Start scan/ }).click();
    await p.check('input[name="constraint-dresser_fixed"]');
    for (const n of ['entry', 'bedside_path', 'bed_outline']) await p.check(`input[name=${n}]`);
    await p.getByRole('button', { name: 'Submit scan' }).click();
    await p.waitForSelector('[data-task=map_furniture][data-status=running]');
    const before = (await store(p)).analysisJob;
    await p.reload();
    const after = (await store(p)).analysisJob;
    assert.equal(after.jobId, before.jobId);
    assert.deepEqual(after.constraints, ['bed_fixed', 'no_new_furniture', 'dresser_fixed']);
    assert.ok(after.currentTaskIndex >= before.currentTaskIndex, 'progress not reset');
    await waitState(p, 'free_action');
    assert.deepEqual((await store(p)).selectedConstraints, ['bed_fixed', 'no_new_furniture', 'dresser_fixed']);

    await scenario(p, '④ analysis_failed_recoverable');
    await waitState(p, 'analysis_failed');
    const failed = (await store(p)).analysisJob;
    assert.deepEqual(failed.tasks.map((t) => t.status), ['completed', 'completed', 'failed', 'pending', 'pending']);
    await p.reload();                                             // failure screen survives a refresh too
    await waitState(p, 'analysis_failed');
    await p.getByRole('button', { name: 'Retry analysis' }).click();
    await waitState(p, 'free_action');
    const done = (await store(p)).analysisJob;
    assert.equal(done.jobId, failed.jobId, 'same job after retry');
    assert.equal(done.attempt, 2);
  }, p);

  await check('5 payment pending: content locked, survives refresh', async () => {
    await scenario(p, '⑤ purchase_pending');
    const tx = (await store(p)).transaction.transactionId;
    await p.getByText(/plan stays locked/).waitFor();
    await p.reload();
    await waitState(p, 'purchase_pending');
    const d = await debug(p);
    assert.equal(d.transaction_id, tx);
    assert.equal(d.content_unlocked, false);
    await noOverflow(p, 'pending');
  }, p);

  await check('6 same transaction verified repeatedly: one purchase, one entitlement', async () => {
    await scenario(p, '⑤ purchase_pending');
    const tx = (await store(p)).transaction.transactionId;
    await p.getByRole('button', { name: /store confirms payment/ }).click();
    await waitState(p, 'purchase_verified');
    await p.getByTestId('panel-toggle').click();
    for (let i = 0; i < 3; i++) await p.getByRole('button', { name: 'Send duplicate verification' }).click();
    await p.getByRole('button', { name: /Test panel/ }).click();
    const d = await debug(p);
    assert.equal(d.transaction_id, tx);
    assert.equal(d.verification_events, 4);
    assert.equal(d.purchases, 1);
    assert.equal(d.payment_status, 'verified');
    assert.equal(await state(p), 'purchase_verified');
  }, p);

  await check('7 verified payment, delivery failed: retry delivers on the same transaction', async () => {
    await scenario(p, '⑥ verified_payment_delivery_failed');
    const tx = (await store(p)).transaction.transactionId;
    await p.getByText(/cannot charge you again/).waitFor();
    let d = await debug(p);
    assert.equal(d.content_unlocked, false);
    await p.getByRole('button', { name: /Retry delivery/ }).click();
    await waitState(p, 'delivered');
    d = await debug(p);
    assert.equal(d.transaction_id, tx);
    assert.equal(d.delivery_attempts, 2);
    assert.equal(d.purchases, 1);
    assert.equal(d.content_unlocked, true);
  }, p);

  await check('8 中文: switch, every screen translated, kept after refresh, no overflow', async () => {
    await scenario(p, '① happy');
    await p.getByTestId('lang-zh').click();
    await p.getByText('你的卧室').waitFor();
    await p.getByText('床保持原位').first().waitFor();
    await noOverflow(p, 'zh start');
    await p.reload();
    await p.getByText('你的卧室').waitFor();                     // choice survives a refresh
    await p.getByRole('button', { name: /开始扫描/ }).click();
    await p.check('input[name=entry]');
    await p.getByRole('button', { name: /提交扫描（缺 2 个区域）/ }).click();
    await p.getByText('扫描不完整 — 未开始分析').waitFor();
    await noOverflow(p, 'zh incomplete');
    const visited = [];
    for (const [label, text] of [['④ analysis_failed_recoverable', '正在分析你的房间'], ['⑤ purchase_pending', '付款处理中'],
      ['⑥ verified_payment_delivery_failed', '已收到付款 — 报告尚未交付']]) {
      await p.getByTestId('panel-toggle').click(); await p.getByRole('button', { name: label }).click(); await p.getByTestId('panel-toggle').click();
      await p.getByText(text).first().waitFor();
      await noOverflow(p, `zh ${label}`);
      visited.push(label);
    }
    await p.getByRole('button', { name: /重试交付/ }).click();
    await p.getByText('你的完整方案').waitFor();
    await p.getByText('保持原位：床。').waitFor();
    // no untranslated key ever leaks into the page
    const leaked = await p.evaluate(() => document.body.innerText.match(/\b(?:section|task|item|status|free|scan|panel|upsell|purchase)\.[a-z_.]+/g));
    assert.equal(leaked, null, `untranslated keys: ${leaked}`);
    await p.getByTestId('lang-en').click();
    await p.getByText('Your full plan').waitFor();
  }, p);

  await check('9 no camera / payment API used, no page errors', async () => {
    assert.deepEqual(await p.evaluate(() => window.__forbidden), []);
    assert.deepEqual(errors, []);
  }, p);

  await browser.close();
  server.kill();
  for (const [n, r, ms, err] of results) console.log(`${r === 'PASS' ? '✓' : '✗'} ${n} (${ms} ms)${err ? `\n    ${err}` : ''}`);
  const failed = results.filter((r) => r[1] !== 'PASS').length;
  console.log(`\n${results.length - failed}/${results.length} browser checks passed`);
  process.exit(failed ? 1 : 0);
})();
