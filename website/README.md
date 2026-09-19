# Dr. Om Prakash Gupta — Senior Advocate (chamber website)

A static, single-page website for **Dr. Om Prakash Gupta, Senior Advocate**
(Genius Senior Advocate & Associates, **Chamber No. 1, Kanpur Nagar Court**).

No build step, no framework, no server. Three files plus one photograph.

```
website/
├── index.html                  all page content
├── 404.html                    branded "page not found"
├── robots.txt                  lets search engines index the site
├── assets/css/styles.css       all styling (colour tokens at the top)
├── assets/js/main.js           menu, disclaimer gate, appointment form
└── assets/img/advocate.jpg     portrait, cropped from the visiting card

netlify.toml                    (repository root) hosting configuration
```

## Sections

| Section | What it does |
|---|---|
| Hero | Visiting card across the top of the banner, then name, designation, photograph and two calls to action |
| About | Short biography and an "at a glance" credentials card |
| Practice Areas | Twelve areas of law the chamber handles |
| How It Works | Four steps from first call to representation |
| **Appointment** | Booking form — validated, sent to the chamber on WhatsApp or email |
| **Payment by UPI** | QR code and UPI ID, directly below the booking form |
| Contact | Chamber address, phone, email, chamber hours |
| Footer | Bar Council disclaimer and copyright |

## How the appointment booking works

There is no backend and no database, so nothing can break, expire or leak.
When a visitor fills the form and presses **Send request on WhatsApp**, the
browser opens WhatsApp with the whole request already typed out — name,
mobile, city, mode, nature of matter, preferred date and time, and a brief
description — addressed to the chamber's number. The visitor presses send.
The chamber receives it as an ordinary WhatsApp message and replies to confirm
the slot.

**Send request by email instead** does the same thing through the visitor's
email application, addressed to `opguptaadv.8@gmail.com`.

Validation done in the browser before anything is sent:

- name of at least three characters;
- a valid 10-digit Indian mobile number (optionally with the 91 prefix);
- a valid email address, if one is given at all;
- nature of matter and preferred time must be chosen;
- the date must be **tomorrow or later**, within 90 days, and **not a Sunday**
  (the chamber is closed on Sunday — the form says so);
- the acknowledgement checkbox must be ticked.

A highlighted note under the two buttons asks anyone who sends their details by
**email** to also inform the chamber by **phone call**, so that a message sitting
in the inbox is not missed. The same note is repeated on the email card in the
contact section.

### Changing the phone number or email

Both live in one place — the top of `assets/js/main.js`:

```js
var CHAMBER = {
  whatsapp: '919450132436',          // country code + number, digits only
  email:    'opguptaadv.8@gmail.com',
  name:     'Dr. Om Prakash Gupta'
};
```

They also appear as clickable links in `index.html` (top bar, hero, contact
section, floating buttons) — search for `9450132436` and replace all.

### Changing the chamber sitting times

The time slots are the `<option>` list under `id="f-time"` in `index.html`.

## Please confirm before publishing

1. **Chamber address.** Listed as *Chamber No. 1, Kanpur Nagar Court, District &
   Sessions Court campus*. The visiting card also shows the chamber reached via
   **Court Gate No. 2** — add that line if it helps clients find you, or correct
   the wording if it is wrong.
2. **Enrolment details.** The site says "over 47 years" and "Senior Advocate",
   both taken from the card. Nothing about enrolment year, bar council
   registration number or degrees has been invented — add them if you want them
   shown.
3. **Practice areas.** Twelve common areas are listed. Remove any the chamber
   does not take, and add any that are missing.
4. **Payment QR.** The QR was **regenerated** rather than photographed, so it is
   sharp at any size. It encodes exactly the payload read from the card's own
   QR: `upi://pay?pa=omprakashadv8@okhdfcbank&pn=omprakash%20adv&aid=...` — this
   was verified by decoding both the original and the new one. Please scan it
   once yourself before publishing, and remember that a UPI ID on a public page
   can attract nuisance payments and impersonation; the page therefore tells
   clients to confirm the amount by phone first and warns that the chamber never
   asks for an OTP or PIN.
5. **Bar Council compliance.** Advocates in India may not solicit work or
   advertise (Bar Council of India Rules, Chapter II, Part VI, Rule 36). The
   site is written as information only, carries the standard disclaimer gate on
   first visit, and makes no claim about results, success rates or client
   numbers. Please keep it that way when editing, and do not add testimonials,
   case victories or comparative claims.

## Publishing it on Netlify (free)

Netlify's free tier is enough for this site: it is static, so there is no build,
no server and no running cost. Two routes — pick one.

### Route A — drag and drop (about two minutes, no account setup)

1. Open **https://app.netlify.com/drop**
2. Drag the file **`advocate-website.zip`** onto the page (or drag the `website`
   folder itself, after deleting `README.md` from the copy you drag — that file
   is internal notes and should not be published).
3. Netlify puts the site live immediately on a random address such as
   `https://sparkly-halva-4c1f2e.netlify.app`.
4. Sign in (free, GitHub or email) to keep the site permanently — without an
   account the drop expires.
5. **Site configuration → Change site name** to something sensible, e.g.
   `opgupta-advocate`, giving `https://opgupta-advocate.netlify.app`.

The drawback: every future change means dragging a new zip.

### Route B — connect the GitHub repository (recommended)

Every push updates the live site automatically. `netlify.toml` in the
repository root already carries the whole configuration, so there is nothing to
type into the dashboard.

1. Sign in at **https://app.netlify.com** with the GitHub account.
2. **Add new site → Import an existing project → GitHub**, authorise Netlify,
   and choose the `meta-ga4-pipeline` repository.
3. Netlify reads `netlify.toml` and fills in the settings itself:
   - Branch: `claude/advocate-website-appointments-conjfv` (or `main` once this
     branch is merged — set it under **Site configuration → Build & deploy →
     Branches**)
   - Publish directory: `website`
   - Build command: none
4. **Deploy site.** The first deploy takes well under a minute.
5. Rename it under **Site configuration → Change site name**.

### A custom domain (optional, not free)

A `.in` domain costs roughly ₹500–900 a year from any registrar. Once bought:
**Domain management → Add a domain**, then point the registrar's nameservers at
Netlify. HTTPS is issued automatically by Netlify at no cost.

`www.opguptaadvocate.in` or `opguptaadvocate.in` reads far better on a visiting
card than a `.netlify.app` address, and the card can be reprinted with it.

### What `netlify.toml` sets up

- **Publish directory** `website`, with no build step.
- **Security headers** on every response: `X-Frame-Options: DENY` (the site
  cannot be embedded in someone else's page), `X-Content-Type-Options`,
  `Referrer-Policy`, a `Permissions-Policy` switching off geolocation, camera,
  microphone and payment, and a strict `Content-Security-Policy` allowing only
  this site's own files plus Google Fonts.
- **Caching**: `index.html` is never cached, so edits appear at once; the CSS,
  JavaScript and portrait are cached for a day.
- **Tidy URLs**: `/appointment` and `/contact` jump to those sections.
- **`/README.md` returns 404** — this file is internal notes, not a page.
- **`404.html`** is served for any unknown address, branded and linking back.

### After it is live — worth doing

1. Open the site on a phone and **send yourself a test appointment request**
   through the WhatsApp button, to confirm requests arrive on the chamber's
   number.
2. Add the address to the visiting card, WhatsApp profile and Google Business
   listing.
3. If you want visitor statistics, Netlify Analytics is paid; a free
   alternative such as Plausible or Cloudflare Web Analytics can be added with
   one line in `index.html` — but note that any third-party script must also be
   added to the `Content-Security-Policy` line in `netlify.toml`, or the browser
   will block it.

## Notes on the images

All four images were prepared from the two photographs supplied:

- **`visiting-card.jpg`** — the card was photographed at an angle, so a
  perspective transform was applied to square it up, followed by mild contrast
  and sharpening. It is legible at full size and links to itself, so a visitor
  can tap to enlarge it.
- **`advocate.png`** — the background of the court photograph was removed, and
  the figure now stands on a designed panel that is part of the page rather than
  part of the image. This is why the file is a PNG: it needs transparency.
- **`advocate-portrait.jpg`** — a head-and-shoulders crop of the same photograph
  on a soft neutral backdrop, used in the About section.
- **`upi-qr.png`** — regenerated from the payload decoded out of the card's QR,
  at the highest error-correction level. Verified to decode back to the identical
  payload, including at the 186px size the page displays it at.

If a higher-resolution photograph exists, replacing `advocate.png` will improve
the hero further — the supplied one is 420px wide, which is why the figure is
displayed at a moderate size rather than filling the banner.

## Browser support

Tested at 390px (mobile), 1024px (tablet) and 1280px (desktop): no horizontal
overflow, mobile menu, floating call and WhatsApp buttons, keyboard-focusable
form with inline error messages, and `prefers-reduced-motion` respected.
