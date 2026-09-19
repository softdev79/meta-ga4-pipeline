#!/usr/bin/env node
/**
 * Browser smoke test for the built site.
 * Loads dist/index.html in Chromium and exercises the paths a real visitor uses.
 * Run with:  node test/smoke.js
 */
'use strict';

const path = require('path');
const { chromium } = require('playwright');

const URL = 'file://' + path.join(__dirname, '..', 'dist', 'index.html');
const results = [];
let failed = 0;

function assert(name, cond, detail) {
  results.push({ name, ok: !!cond, detail });
  if (!cond) failed++;
}

(async () => {
  // Use the Chromium already on the box rather than downloading one.
  const fs = require('fs');
  const candidates = [
    process.env.CHROMIUM_PATH,
    '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    '/opt/pw-browsers/chromium/chrome-linux/chrome',
    '/usr/bin/chromium',
    '/usr/bin/google-chrome',
  ].filter(Boolean);
  const executablePath = candidates.find((c) => { try { return fs.existsSync(c); } catch (e) { return false; } });

  // --ignore-certificate-errors lets the Google Fonts stylesheet through this
  // sandbox's TLS-intercepting egress proxy, so screenshots show real type.
  const args = ['--no-sandbox', '--ignore-certificate-errors'];
  const browser = await chromium.launch(executablePath ? { executablePath, args } : { args });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();

  // We assert on the page's OWN errors. Network failures fetching the font
  // stylesheet are an artefact of the sandbox's egress proxy, not a page bug.
  const NETWORK_NOISE = /Failed to load resource|ERR_CERT|ERR_NAME_NOT_RESOLVED|net::/i;
  const consoleErrors = [];
  page.on('console', (m) => {
    if (m.type() === 'error' && !NETWORK_NOISE.test(m.text())) consoleErrors.push(m.text());
  });
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + e.message));

  await page.goto(URL, { waitUntil: 'networkidle' });

  // --- render -----------------------------------------------------------
  const rowCount = await page.locator('#rows .row').count();
  assert('all 34 medicines render', rowCount === 34, `got ${rowCount}`);
  assert('no console / page errors on load', consoleErrors.length === 0,
    consoleErrors.join(' | '));

  const title = await page.locator('h1').innerText();
  assert('hero headline present', /chemists/i.test(title), title);

  const licence = await page.locator('#val-licence').innerText();
  assert('business data wired in', licence.includes('UP/KNP'), licence);

  // --- search -----------------------------------------------------------
  await page.fill('#q', 'montair');
  await page.waitForTimeout(220);
  let n = await page.locator('#rows .row').count();
  assert('brand search narrows the list', n === 2, `"montair" -> ${n} rows`);

  await page.fill('#q', 'paracetamol');
  await page.waitForTimeout(220);
  n = await page.locator('#rows .row').count();
  assert('salt search finds combination products', n === 3, `"paracetamol" -> ${n} rows`);

  await page.fill('#q', 'zzzznotreal');
  await page.waitForTimeout(220);
  assert('empty state shows', await page.locator('#rows .empty').count() === 1);

  await page.click('#q-clear');
  await page.waitForTimeout(220);
  n = await page.locator('#rows .row').count();
  assert('clearing search restores full list', n === 34, `got ${n}`);

  // --- filters ----------------------------------------------------------
  await page.click('#co-chips .chip[data-co="Cipla"]');
  await page.waitForTimeout(80);
  n = await page.locator('#rows .row').count();
  assert('company filter works (Cipla = 19)', n === 19, `got ${n}`);

  await page.click('#cat-chips .chip[data-cat="respiratory"]');
  await page.waitForTimeout(80);
  n = await page.locator('#rows .row').count();
  assert('company + category filters combine', n === 7, `Cipla+respiratory -> ${n}`);

  await page.click('#co-chips .chip[data-co="Cipla"]');   // toggle off
  await page.click('#cat-chips .chip[data-cat="respiratory"]');
  await page.waitForTimeout(80);
  n = await page.locator('#rows .row').count();
  assert('filters toggle off again', n === 34, `got ${n}`);

  // --- enquiry flow -----------------------------------------------------
  assert('enquiry bar hidden when empty',
    await page.locator('#enqbar').isHidden());

  await page.locator('#rows .row').first().locator('.add').click();
  await page.waitForTimeout(80);
  assert('enquiry bar appears after adding',
    await page.locator('#enqbar').isVisible());

  await page.locator('#rows .row').first().locator('.step button').last().click();
  await page.waitForTimeout(80);
  const qty = await page.locator('#rows .row').first().locator('.step span').innerText();
  assert('stepper increments quantity', qty.trim() === '2', `got "${qty}"`);

  await page.click('#enqbar-open');
  await page.waitForTimeout(150);
  assert('enquiry sheet opens', await page.locator('#sheet').isVisible());

  await page.fill('#buyer-shop', 'Sharma Medical Store');
  await page.fill('#buyer-phone', '9000000000');
  await page.waitForTimeout(80);

  const waHref = await page.locator('#sheet-send').getAttribute('href');
  const decoded = decodeURIComponent(waHref.split('?text=')[1] || '');
  assert('WhatsApp link points at wa.me', waHref.startsWith('https://wa.me/'), waHref.slice(0, 40));
  assert('order message carries the shop name', decoded.includes('Sharma Medical Store'));
  assert('order message carries the item and quantity',
    /Asthalin.*× 2|Asthalin.*x 2/.test(decoded.replace(/×/g, '×')), decoded.slice(0, 200));
  assert('order message carries the total', /Total items: 2/.test(decoded));

  await page.click('#sheet-close');
  await page.waitForTimeout(120);

  // --- persistence ------------------------------------------------------
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(200);
  assert('enquiry list survives a reload',
    await page.locator('#enqbar').isVisible());

  await page.click('#enqbar-clear');
  await page.waitForTimeout(100);
  assert('clear empties the enquiry list',
    await page.locator('#enqbar').isHidden());

  // --- Hindi ------------------------------------------------------------
  await page.click('#lang-hi');
  await page.waitForTimeout(200);
  const h1hi = await page.locator('h1').innerText();
  assert('Hindi toggle translates the headline', /[ऀ-ॿ]/.test(h1hi), h1hi);
  const firstName = await page.locator('#rows .row').first().locator('.med__name').innerText();
  assert('medicine names switch to Devanagari', /[ऀ-ॿ]/.test(firstName), firstName);
  assert('Latin name kept as a sub-line for recognisability',
    await page.locator('#rows .row').first().locator('.med__hi').count() === 1);
  const htmlLang = await page.getAttribute('html', 'lang');
  assert('document language attribute updates', htmlLang === 'hi', htmlLang);
  assert('still no console errors after interaction', consoleErrors.length === 0,
    consoleErrors.join(' | '));

  // --- screenshots (desktop EN, mobile HI) ------------------------------
  await page.click('#lang-en');
  await page.waitForTimeout(150);
  await page.screenshot({ path: path.join(__dirname, '..', 'dist', '_preview-desktop.png'), fullPage: false });

  const m = await ctx.newPage();
  await m.setViewportSize({ width: 390, height: 844 });
  await m.goto(URL, { waitUntil: 'networkidle' });
  await m.waitForTimeout(250);
  const scrollW = await m.evaluate(() => document.documentElement.scrollWidth);
  assert('no horizontal scroll at 390px', scrollW <= 391, `scrollWidth ${scrollW}`);
  await m.screenshot({ path: path.join(__dirname, '..', 'dist', '_preview-mobile.png'), fullPage: false });

  await browser.close();

  // --- report -----------------------------------------------------------
  console.log('');
  for (const r of results) {
    console.log(`  ${r.ok ? 'PASS' : 'FAIL'}  ${r.name}${r.ok || !r.detail ? '' : `  -> ${r.detail}`}`);
  }
  console.log(`\n  ${results.length - failed}/${results.length} browser checks passed\n`);
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
