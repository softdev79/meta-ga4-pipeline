# Dr. Om Prakash Gupta — Senior Advocate (chamber website)

A static, single-page website for **Dr. Om Prakash Gupta, Senior Advocate**
(Genius Senior Advocate & Associates), practising before the Hon'ble High Court
of Judicature at Allahabad.

No build step, no framework, no server. Three files plus one photograph.

```
website/
├── index.html                  all page content
├── assets/css/styles.css       all styling (colour tokens at the top)
├── assets/js/main.js           menu, disclaimer gate, appointment form
└── assets/img/advocate.jpg     portrait, cropped from the visiting card
```

## Sections

| Section | What it does |
|---|---|
| Hero | Name, designation, years of practice, portrait, two calls to action |
| About | Short biography and an "at a glance" credentials card |
| Practice Areas | Twelve areas of law the chamber handles |
| How It Works | Four steps from first call to representation |
| **Appointment** | Booking form — validated, sent to the chamber on WhatsApp or email |
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

These are marked in the page and should be checked by Dr. Gupta himself:

1. **Chamber address.** The visiting card shows the chamber in the District &
   Sessions Court campus, but the chamber number and city are not legible in
   the photograph. In `index.html`, the contact card contains a placeholder:
   `[Chamber number, road and city — please confirm]`.
2. **Enrolment details.** The site says "over 47 years" and "Senior Advocate",
   both taken from the card. Nothing about enrolment year, bar council
   registration number or university degrees has been invented — add them if
   you want them shown.
3. **Practice areas.** Twelve common areas are listed. Remove any the chamber
   does not take, and add any that are missing.
4. **Bar Council compliance.** Advocates in India may not solicit work or
   advertise (Bar Council of India Rules, Chapter II, Part VI, Rule 36). The
   site is written as information only, carries the standard disclaimer gate on
   first visit, and makes no claim about results, success rates or client
   numbers. Please keep it that way when editing, and do not add testimonials,
   case victories or comparative claims.
5. **UPI / payment details.** The UPI ID and QR code printed on the visiting
   card have deliberately **not** been put on the website. Publishing payment
   handles on a public page invites misuse. Add them only if you are sure.

## Publishing it

Any static host works. The simplest free options:

**GitHub Pages** — push this folder to a repository, then Settings → Pages →
Deploy from branch, and choose the branch with `/website` as the folder. The
site appears at `https://<username>.github.io/<repo>/`.

**Netlify or Cloudflare Pages** — drag the `website` folder onto the dashboard.
No build command is needed.

**A custom domain** (e.g. `opguptaadvocate.in`) can be pointed at any of these
from the host's domain settings.

To preview it locally:

```sh
cd website
python3 -m http.server 8000
# then open http://localhost:8000
```

## Notes on the photograph

`assets/img/advocate.jpg` was cropped from the photograph of the visiting card
and cleaned up (deskewed, denoised, contrast corrected). It is a scan of a
small printed photo, so it is grainy at large sizes. If Dr. Gupta has the
original photograph or a recent one, replacing this file — same name, portrait
orientation — will improve the page considerably.

## Browser support

Tested at 390px (mobile), 1024px (tablet) and 1280px (desktop): no horizontal
overflow, mobile menu, floating call and WhatsApp buttons, keyboard-focusable
form with inline error messages, and `prefers-reduced-motion` respected.
