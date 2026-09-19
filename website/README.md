# Ajay Pharma — website

Bilingual (English / हिंदी) website for **Ajay Pharma**, a wholesale medicine
distributor at 59/105, Canal Road, Birhana Road, Kanpur – 208001, Uttar Pradesh.

The site is a static page with a searchable medicine rate list. A visitor picks
items, and the "Send on WhatsApp" button opens WhatsApp with the whole order
already written out — no backend, no login, no app to install.

---

## Before you share this site publicly

`data/business.json` ships with **placeholder** contact and licence details.
Replace these five values with Ajay Pharma's real ones, then rebuild:

| Field | Currently | What it is |
|---|---|---|
| `phoneDisplay` | `+91 00000 00000` | number shown on the page |
| `phoneDial` | `+910000000000` | number the Call button dials |
| `whatsapp` | `910000000000` | WhatsApp number, digits only, country code first, no `+` |
| `email` | `orders@ajaypharma.example` | shop email |
| `drugLicence` / `gstin` | `UP/KNP/20B-00000…` | real licence and GST numbers |

Opening hours, delivery districts and the year established are in the same file.

---

## Editing the medicine list

Everything the page shows comes from `data/`. There is no database server and no
CMS — edit the JSON, rebuild, redeploy.

```
data/medicines.json    the catalogue — one object per medicine
data/categories.json   the filter chips
data/business.json     shop name, address, phone, hours, delivery areas
```

A medicine looks like this:

```json
{
  "id": "cip-montair-10",
  "company": "Cipla",
  "name": "Montair 10 Tablet",
  "nameHi": "मॉन्टेयर 10 टैबलेट",
  "composition": "Montelukast 10mg",
  "compositionHi": "मोंटेलुकास्ट 10mg",
  "form": "Tablet",
  "pack": "10 Tablets",
  "mrp": 212.00,
  "schedule": "H",
  "category": "allergy",
  "stock": "in"
}
```

- `id` — lowercase letters, digits and hyphens; must be unique.
- `schedule` — `H`, `H1`, `X` (all shown as a red **Rx** badge) or `OTC` (green badge).
- `category` — must match an `id` in `categories.json`.
- `stock` — `in`, `order` (shows an "On order" badge) or `out`.
- `mrp` — a number, not a string; at most two decimals.

Search matches the brand name, the Hindi name, the composition in both scripts,
the company and the form — so a customer can type either "Montair" or
"मॉन्टेयर" or "Montelukast" and find the same row.

**The MRPs in this repo are indicative.** The page says so, and deliberately
does not publish trade rates — those are quoted on enquiry. Replace the figures
with your own current list when you have one.

---

## Build and test

Needs Node.js 18+. No dependencies to install for building.

```bash
node build.js          # data/ + src/page.html  ->  dist/
node test/validate.js  # 15 checks on the catalogue data
node test/smoke.js     # 27 checks in a real browser (needs: npm i playwright)
```

`build.js` inlines the JSON into the page, so the site loads with no extra
network requests and works even from a plain folder on a pen drive.

It writes two files:

- `dist/index.html` — a complete standalone page. **This is what you deploy.**
- `dist/artifact.html` — the same page as a fragment, for claude.ai hosting.

`test/validate.js` is what catches a typo in the catalogue: it checks required
fields, unique ids, valid categories, sane MRPs, recognised schedule and stock
values, and that every Hindi field really contains Devanagari. Run it before
every deploy — the GitHub Actions workflow runs it for you and refuses to
deploy a broken catalogue.

---

## Deploying (free options)

### Netlify Drop — fastest, no account needed to try

Run `node build.js`, then drag the `dist` folder onto
[app.netlify.com/drop](https://app.netlify.com/drop). You get a live HTTPS URL
in a few seconds. Sign in afterwards if you want to keep it permanently or
rename the subdomain. Cloudflare Pages and tiiny.host work the same way.

Because `build.js` inlines everything, `dist/index.html` is the entire site —
a single file you can upload anywhere, email to yourself, or open from a pen
drive with no server at all.

### GitHub Pages — workflow is wired up, needs one switch

`.github/workflows/deploy-website.yml` validates, builds and deploys on every
push. Two things the automation cannot do for itself:

1. **Enable Pages:** Settings → Pages → Build and deployment → Source:
   **“GitHub Actions”**. The workflow token can deploy to a Pages site but is
   not allowed to create one (`Resource not accessible by integration`), so
   this click is unavoidable.
2. **Deploy from the default branch:** Pages only deploys from `main` unless
   you add another branch under Settings → Environments → `github-pages`. So
   merge the website branch into `main`.

The site then lives at `https://softdev79.github.io/meta-ga4-pipeline/`.

### A custom domain

Once you buy something like `ajaypharma.in`, point it at whichever host you
picked; both GitHub Pages and Netlify handle custom domains and the HTTPS
certificate for free.

---

## How the page is put together

- **One file, no framework.** `src/page.html` holds the markup, the CSS and the
  JavaScript. Nothing is fetched at runtime except the two Google fonts.
- **Both languages are first-class.** Every string exists in `STR.en` and
  `STR.hi` in `src/page.html`; the toggle re-renders the page and remembers the
  choice. In Hindi the Latin brand name stays visible under the Devanagari one,
  because that is how a chemist reads a strip.
- **Light and dark.** Colours are CSS custom properties defined three times —
  for light, for `prefers-color-scheme: dark`, and for an explicit theme stamp —
  so the page follows the visitor's phone.
- **The enquiry list survives a reload** via `localStorage`, wrapped in
  try/catch so a private window or blocked storage cannot break the page.
- **Type:** Bricolage Grotesque for headings, Mukta for body text in both Latin
  and Devanagari, IBM Plex Mono for rates and pack sizes.

---

## Regulatory note

The page states that Ajay Pharma is a wholesale distributor, that Schedule H and
H1 medicines go only to buyers holding a valid drug licence, and that the listing
is not medical advice. Keep that notice in place — it is at the bottom of
`src/page.html` under `class="disclaim"`.
