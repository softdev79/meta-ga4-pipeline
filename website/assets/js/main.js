/* =============================================================
   Genius Senior Advocate & Associates — site behaviour
   Appointment requests are delivered to the chamber over WhatsApp
   (or email), so the site stays a plain static page with no server.
   ============================================================= */

/* ---- Edit these three lines if the chamber's contact details change ---- */
var CHAMBER = {
  whatsapp: '919450132436',          // country code + number, digits only
  email:    'opguptaadv.8@gmail.com',
  name:     'Dr. Om Prakash Gupta'
};

(function () {
  'use strict';

  var $  = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };

  /* ---------------- Current year ---------------- */
  var yearEl = $('#year');
  if (yearEl) { yearEl.textContent = new Date().getFullYear(); }

  /* ---------------- Bar Council disclaimer ---------------- */
  var gate = $('#disclaimer');
  if (gate) {
    var seen = false;
    try { seen = sessionStorage.getItem('disclaimerAccepted') === '1'; } catch (e) { seen = false; }
    if (!seen) {
      gate.hidden = false;
      document.body.style.overflow = 'hidden';
      var agree = $('#disc-agree');
      if (agree) { agree.focus(); }
    }
    $('#disc-agree').addEventListener('click', function () {
      gate.hidden = true;
      document.body.style.overflow = '';
      try { sessionStorage.setItem('disclaimerAccepted', '1'); } catch (e) { /* private mode */ }
    });
  }

  /* ---------------- Mobile navigation ---------------- */
  var toggle = $('#nav-toggle');
  var nav = $('#nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    });
    $$('a', nav).forEach(function (link) {
      link.addEventListener('click', function () {
        nav.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* ---------------- Sticky header shadow ---------------- */
  var header = $('#header');
  var onScroll = function () {
    if (header) { header.classList.toggle('is-stuck', window.scrollY > 8); }
    markActiveSection();
  };
  window.addEventListener('scroll', onScroll, { passive: true });

  /* ---------------- Active nav link ---------------- */
  var sections = $$('section[id]');
  var navLinks = $$('.nav a[href^="#"]').filter(function (a) { return !a.classList.contains('btn'); });
  function markActiveSection() {
    var pos = window.scrollY + 140;
    var currentId = '';
    sections.forEach(function (sec) {
      if (sec.offsetTop <= pos) { currentId = sec.id; }
    });
    navLinks.forEach(function (link) {
      link.classList.toggle('is-active', link.getAttribute('href') === '#' + currentId);
    });
  }
  markActiveSection();

  /* ---------------- Appointment form ---------------- */
  var form = $('#appt-form');
  if (!form) { return; }

  var status = $('#form-status');
  var dateInput = $('#f-date');
  var brief = $('#f-brief');
  var count = $('#f-count');

  /* Earliest bookable date is tomorrow; no bookings beyond 90 days. */
  var today = new Date();
  var min = new Date(today.getTime() + 24 * 60 * 60 * 1000);
  var max = new Date(today.getTime() + 90 * 24 * 60 * 60 * 1000);
  var iso = function (d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  };
  dateInput.min = iso(min);
  dateInput.max = iso(max);

  if (brief && count) {
    brief.addEventListener('input', function () { count.textContent = String(brief.value.length); });
  }

  function setError(field, message) {
    var box = document.querySelector('.error[data-for="' + field.id + '"]');
    if (box) { box.textContent = message || ''; }
    field.classList.toggle('is-invalid', Boolean(message));
  }

  function clearErrors() {
    $$('.error', form).forEach(function (e) { e.textContent = ''; });
    $$('.is-invalid', form).forEach(function (e) { e.classList.remove('is-invalid'); });
    if (status) { status.textContent = ''; status.classList.remove('is-ok'); }
  }

  function validate() {
    clearErrors();
    var ok = true;
    var name = $('#f-name'), phone = $('#f-phone'), email = $('#f-email'),
        matter = $('#f-matter'), time = $('#f-time'), consent = $('#f-consent');

    if (name.value.trim().length < 3) {
      setError(name, 'Please enter your full name.'); ok = false;
    }

    var digits = phone.value.replace(/\D/g, '');
    if (!/^(91)?[6-9]\d{9}$/.test(digits)) {
      setError(phone, 'Please enter a valid 10-digit Indian mobile number.'); ok = false;
    }

    if (email.value.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.value.trim())) {
      setError(email, 'Please enter a valid email address, or leave it blank.'); ok = false;
    }

    if (!matter.value) { setError(matter, 'Please select the nature of your matter.'); ok = false; }
    if (!time.value)   { setError(time, 'Please choose a preferred time.'); ok = false; }

    if (!dateInput.value) {
      setError(dateInput, 'Please choose a preferred date.'); ok = false;
    } else {
      var parts = dateInput.value.split('-');
      var chosen = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
      var floorToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
      if (chosen <= floorToday) {
        setError(dateInput, 'Please choose a date from tomorrow onwards.'); ok = false;
      } else if (chosen.getDay() === 0) {
        setError(dateInput, 'The chamber is closed on Sunday. Please choose another day.'); ok = false;
      }
    }

    if (!consent.checked) {
      setError(consent, 'Please acknowledge the note above to continue.'); ok = false;
    }

    if (!ok) {
      var firstBad = $('.is-invalid', form);
      if (firstBad) { firstBad.focus({ preventScroll: false }); }
    }
    return ok;
  }

  function prettyDate(value) {
    var parts = value.split('-');
    var d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return d.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  }

  function buildMessage() {
    var val = function (id) { return ($(id).value || '').trim(); };
    var lines = [
      'Appointment request — ' + CHAMBER.name,
      '',
      'Name: ' + val('#f-name'),
      'Mobile: ' + val('#f-phone'),
      'Email: ' + (val('#f-email') || '—'),
      'City / District: ' + (val('#f-city') || '—'),
      'Mode: ' + val('#f-mode'),
      'Nature of matter: ' + val('#f-matter'),
      'Preferred date: ' + prettyDate(val('#f-date')),
      'Preferred time: ' + val('#f-time'),
      '',
      'Brief: ' + (val('#f-brief') || '—'),
      '',
      'Sent from the chamber website.'
    ];
    return lines.join('\n');
  }

  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    if (!validate()) { return; }
    var url = 'https://wa.me/' + CHAMBER.whatsapp + '?text=' + encodeURIComponent(buildMessage());
    window.open(url, '_blank', 'noopener');
    if (status) {
      status.textContent = 'WhatsApp has been opened with your request. Please press send there to deliver it to the chamber.';
      status.classList.add('is-ok');
    }
  });

  var emailBtn = $('#send-email');
  if (emailBtn) {
    emailBtn.addEventListener('click', function () {
      if (!validate()) { return; }
      var subject = 'Appointment request — ' + ($('#f-name').value || '').trim();
      var href = 'mailto:' + CHAMBER.email +
        '?subject=' + encodeURIComponent(subject) +
        '&body=' + encodeURIComponent(buildMessage());
      window.location.href = href;
      if (status) {
        status.textContent = 'Your email application has been opened with the request filled in. Please press send there.';
        status.classList.add('is-ok');
      }
    });
  }
})();
