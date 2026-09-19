#!/usr/bin/env node
/**
 * Data integrity tests for the Ajay Pharma catalogue.
 * Run with:  node test/validate.js
 * Exits non-zero on the first failing suite so CI / pre-deploy can gate on it.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const read = (f) => JSON.parse(fs.readFileSync(path.join(ROOT, 'data', f), 'utf8'));

const medicines = read('medicines.json');
const categories = read('categories.json');
const business = read('business.json');

let passed = 0;
const failures = [];

function check(name, fn) {
  try {
    const problem = fn();
    if (problem) throw new Error(problem);
    passed++;
  } catch (err) {
    failures.push(`${name}: ${err.message}`);
  }
}

const REQUIRED_FIELDS = [
  'id', 'company', 'name', 'nameHi', 'composition', 'compositionHi',
  'form', 'pack', 'mrp', 'schedule', 'category', 'stock',
];
const SCHEDULES = new Set(['H', 'H1', 'X', 'OTC']);
const STOCK = new Set(['in', 'order', 'out']);
const categoryIds = new Set(categories.map((c) => c.id));

check('catalogue is a non-empty array', () =>
  Array.isArray(medicines) && medicines.length > 0 ? null : 'expected a non-empty array');

check('every medicine has all required fields', () => {
  for (const m of medicines) {
    for (const f of REQUIRED_FIELDS) {
      if (m[f] === undefined || m[f] === null || m[f] === '') {
        return `"${m.id || '(no id)'}" is missing "${f}"`;
      }
    }
  }
  return null;
});

check('medicine ids are unique', () => {
  const seen = new Set();
  for (const m of medicines) {
    if (seen.has(m.id)) return `duplicate id "${m.id}"`;
    seen.add(m.id);
  }
  return null;
});

check('medicine ids are url-safe slugs', () => {
  const bad = medicines.filter((m) => !/^[a-z0-9-]+$/.test(m.id));
  return bad.length ? `bad id(s): ${bad.map((m) => m.id).join(', ')}` : null;
});

check('every category referenced by a medicine exists', () => {
  const orphans = medicines.filter((m) => !categoryIds.has(m.category));
  return orphans.length
    ? `unknown category on: ${orphans.map((m) => `${m.id} -> ${m.category}`).join(', ')}`
    : null;
});

check('every category is used by at least one medicine', () => {
  const used = new Set(medicines.map((m) => m.category));
  const unused = categories.filter((c) => !used.has(c.id));
  return unused.length ? `unused categories: ${unused.map((c) => c.id).join(', ')}` : null;
});

check('MRP is a positive number with at most 2 decimals', () => {
  for (const m of medicines) {
    if (typeof m.mrp !== 'number' || !isFinite(m.mrp) || m.mrp <= 0) {
      return `"${m.id}" has a non-positive MRP (${m.mrp})`;
    }
    if (Math.round(m.mrp * 100) !== m.mrp * 100) {
      return `"${m.id}" MRP has more than 2 decimals (${m.mrp})`;
    }
  }
  return null;
});

check('schedule values are recognised', () => {
  const bad = medicines.filter((m) => !SCHEDULES.has(m.schedule));
  return bad.length ? `bad schedule on: ${bad.map((m) => m.id).join(', ')}` : null;
});

check('stock values are recognised', () => {
  const bad = medicines.filter((m) => !STOCK.has(m.stock));
  return bad.length ? `bad stock on: ${bad.map((m) => m.id).join(', ')}` : null;
});

check('Hindi fields actually contain Devanagari', () => {
  const devanagari = /[ऀ-ॿ]/;
  for (const m of medicines) {
    if (!devanagari.test(m.nameHi)) return `"${m.id}" nameHi is not in Devanagari`;
    if (!devanagari.test(m.compositionHi)) return `"${m.id}" compositionHi is not in Devanagari`;
  }
  for (const c of categories) {
    if (!devanagari.test(c.hi)) return `category "${c.id}" hi is not in Devanagari`;
  }
  return null;
});

check('categories have unique ids', () => {
  const ids = categories.map((c) => c.id);
  return new Set(ids).size === ids.length ? null : 'duplicate category id';
});

check('the two principal companies are stocked', () => {
  const companies = new Set(medicines.map((m) => m.company));
  const missing = ['Cipla', 'Intas'].filter((c) => !companies.has(c));
  return missing.length ? `no products listed for: ${missing.join(', ')}` : null;
});

check('business profile has the fields the page renders', () => {
  const required = [
    'name', 'tagline', 'address', 'mapsQuery', 'phoneDisplay',
    'phoneDial', 'whatsapp', 'hours', 'deliveryAreas',
  ];
  for (const f of required) {
    if (business[f] === undefined) return `business.json is missing "${f}"`;
  }
  if (!business.name.en || !business.name.hi) return 'business name needs en + hi';
  if (!business.address.en || !business.address.hi) return 'business address needs en + hi';
  return null;
});

check('WhatsApp number is digits only (wa.me format)', () =>
  /^[0-9]{10,15}$/.test(business.whatsapp) ? null : `"${business.whatsapp}" is not a wa.me number`);

check('dial number is E.164', () =>
  /^\+[0-9]{10,15}$/.test(business.phoneDial) ? null : `"${business.phoneDial}" is not E.164`);

// ---- report -------------------------------------------------------------
const total = passed + failures.length;
if (failures.length) {
  console.error(`\n  ${failures.length} of ${total} checks FAILED\n`);
  for (const f of failures) console.error(`  x ${f}`);
  console.error('');
  process.exit(1);
}

const byCompany = medicines.reduce((acc, m) => {
  acc[m.company] = (acc[m.company] || 0) + 1;
  return acc;
}, {});

console.log(`\n  ${passed}/${total} checks passed`);
console.log(`  ${medicines.length} medicines across ${categories.length} categories`);
console.log('  ' + Object.entries(byCompany)
  .sort((a, b) => b[1] - a[1])
  .map(([c, n]) => `${c}: ${n}`)
  .join('  |  ') + '\n');
