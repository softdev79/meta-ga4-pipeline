#!/usr/bin/env node
/**
 * Build the Ajay Pharma site.
 *
 * The catalogue lives in data/*.json (one source of truth). This inlines it
 * into the page so the site loads with zero network round-trips and works on
 * any static host — GitHub Pages, Netlify, Cloudflare Pages, or a plain folder.
 *
 * Outputs:
 *   dist/index.html     standalone document — deploy this folder anywhere
 *   dist/artifact.html  body-only fragment for claude.ai Artifact hosting
 *
 * Usage: node build.js
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const readJson = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));

const business = readJson('data/business.json');
const categories = readJson('data/categories.json');
const medicines = readJson('data/medicines.json');

// Strip the editor-only note so it never ships to the browser.
delete business._NOTE_REPLACE_THESE;

const template = fs.readFileSync(path.join(ROOT, 'src/page.html'), 'utf8');

// The proprietor photo is inlined as a data URI so dist/index.html stays a
// single portable file you can drag onto any host.
const photoPath = business.proprietor && business.proprietor.photo;
let photoDataUri = '';
if (photoPath) {
  const abs = path.join(ROOT, photoPath);
  if (!fs.existsSync(abs)) {
    console.error(`build failed: proprietor photo not found at ${photoPath}`);
    process.exit(1);
  }
  const ext = path.extname(abs).toLowerCase();
  const mime = ext === '.png' ? 'image/png' : ext === '.webp' ? 'image/webp' : 'image/jpeg';
  photoDataUri = `data:${mime};base64,${fs.readFileSync(abs).toString('base64')}`;
}

// JSON inlined into a <script> must not be able to close it early.
const LS = String.fromCharCode(0x2028);
const PS = String.fromCharCode(0x2029);
const SEPARATORS = new RegExp('[' + LS + PS + ']', 'g');
const safeJson = (value) =>
  JSON.stringify(value)
    .replace(/</g, '\\u003C')
    .replace(SEPARATORS, (c) => (c === LS ? '\\u2028' : '\\u2029'));

const fragment = template
  .replace('__PROPRIETOR_PHOTO__', photoDataUri)
  .replace('__BUSINESS__', safeJson(business))
  .replace('__CATEGORIES__', safeJson(categories))
  .replace('__CATALOG__', safeJson(medicines));

for (const token of ['__BUSINESS__', '__CATEGORIES__', '__CATALOG__', '__PROPRIETOR_PHOTO__']) {
  if (fragment.includes(token)) {
    console.error(`build failed: placeholder ${token} was not substituted`);
    process.exit(1);
  }
}

const description =
  'Ajay Pharma — wholesale medicine distributor, 59/105 Canal Road, Birhana Road, ' +
  'Kanpur 208001, Uttar Pradesh. Cipla and Intas range supplied to chemists, ' +
  'clinics and hospitals across Kanpur.';

const standalone = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="${description}">
<meta name="theme-color" content="#046A4E">
<meta property="og:type" content="business.business">
<meta property="og:title" content="Ajay Pharma — Wholesale Medicine Distributor, Kanpur">
<meta property="og:description" content="${description}">
<meta property="og:locale" content="en_IN">
<meta property="og:locale:alternate" content="hi_IN">
<link rel="icon" href="data:image/svg+xml,${encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">' +
  '<rect width="40" height="40" rx="10" fill="#046A4E"/>' +
  '<g fill="#fff"><rect x="8.5" y="9" width="7.5" height="9" rx="3.75"/>' +
  '<rect x="18.5" y="9" width="7.5" height="9" rx="3.75"/>' +
  '<rect x="8.5" y="22" width="7.5" height="9" rx="3.75"/>' +
  '<rect x="18.5" y="22" width="7.5" height="9" rx="3.75" opacity=".6"/></g></svg>'
)}">
<script type="application/ld+json">
${JSON.stringify({
  '@context': 'https://schema.org',
  '@type': 'Pharmacy',
  name: 'Ajay Pharma',
  description: 'Wholesale pharmaceutical distributor stocking the Cipla and Intas range.',
  address: {
    '@type': 'PostalAddress',
    streetAddress: '59/105, Canal Road, Birhana Road',
    addressLocality: 'Kanpur',
    postalCode: '208001',
    addressRegion: 'Uttar Pradesh',
    addressCountry: 'IN',
  },
  telephone: business.phoneDial,
  openingHours: ['Mo-Sa 09:30-20:00'],
  areaServed: business.deliveryAreas.en,
}, null, 2)}
</script>
<style>
  :root{
    color-scheme:light dark;
    padding-top:env(safe-area-inset-top,0px);
    padding-bottom:env(safe-area-inset-bottom,0px);
  }
  body{margin:0}
  img{max-width:100%}
  [hidden]{display:none!important}
</style>
${fragment}
</head>
</html>
`;

// The fragment carries its own <title>/<link>/<style> then markup; browsers move
// the body content out of <head> automatically, but emit it properly instead.
const tidy = standalone.replace('</head>\n</html>', '</html>');

fs.mkdirSync(path.join(ROOT, 'dist'), { recursive: true });
fs.writeFileSync(path.join(ROOT, 'dist/artifact.html'), fragment);
fs.writeFileSync(path.join(ROOT, 'dist/index.html'), tidy);
fs.writeFileSync(path.join(ROOT, 'dist/.nojekyll'), '');

const kb = (f) => (fs.statSync(path.join(ROOT, f)).size / 1024).toFixed(1) + ' KB';
const photoKb = photoDataUri ? Math.round((photoDataUri.length * 3) / 4 / 1024) : 0;
console.log(`\n  built ${medicines.length} medicines, ${categories.length} categories` +
  (photoKb ? `, proprietor photo inlined (${photoKb} KB)` : ', no proprietor photo'));
console.log(`  dist/index.html     ${kb('dist/index.html')}   (standalone — any static host)`);
console.log(`  dist/artifact.html  ${kb('dist/artifact.html')}   (fragment — claude.ai artifact)\n`);
