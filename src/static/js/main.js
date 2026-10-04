/* ==========================================================================
   Relais Populaire Média — scripts du site (aucune dépendance, aucun traceur)
   ========================================================================== */
(function () {
  'use strict';

  var doc = document.documentElement;
  doc.classList.add('js');

  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $$(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }

  var store = {
    get: function (k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { window.localStorage.setItem(k, v); } catch (e) { /* stockage indisponible */ } }
  };

  var reduceMotion = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };
  var isLocalFile = window.location.protocol === 'file:';
  var isPreview = doc.hasAttribute('data-preview');

  /* ------------------------------------------------------------------
     1. Animations : bouton pause / lecture (WCAG 2.2.2)
     ------------------------------------------------------------------ */
  var motionButtons = $$('[data-motion-toggle]');
  function applyMotion(on) {
    doc.setAttribute('data-motion', on ? 'on' : 'off');
    motionButtons.forEach(function (btn) {
      var label = on ? 'Mettre les animations en pause' : 'Relancer les animations';
      btn.setAttribute('aria-label', label);
      btn.setAttribute('title', label);
    });
  }
  var savedMotion = store.get('rpm-motion');
  applyMotion(savedMotion ? savedMotion === 'on' : !reduceMotion.matches);
  motionButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var on = doc.getAttribute('data-motion') !== 'on';
      applyMotion(on);
      store.set('rpm-motion', on ? 'on' : 'off');
    });
  });
  function motionOn() { return doc.getAttribute('data-motion') === 'on'; }

  /* ------------------------------------------------------------------
     2. En-tête : fond au défilement
     ------------------------------------------------------------------ */
  var header = $('.site-header');
  function onScrollHeader() {
    if (header) header.classList.toggle('is-scrolled', window.scrollY > 24);
  }
  onScrollHeader();
  window.addEventListener('scroll', onScrollHeader, { passive: true });

  /* ------------------------------------------------------------------
     3. Menu mobile
     ------------------------------------------------------------------ */
  var menuBtn = $('[data-menu-toggle]');
  var menu = $('#mobile-menu');
  if (menuBtn && menu) {
    var setMenu = function (open) {
      menuBtn.setAttribute('aria-expanded', String(open));
      menuBtn.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
      menu.classList.toggle('is-open', open);
      doc.classList.toggle('menu-open', open);
      document.body.classList.toggle('no-scroll', open);
      if ('inert' in menu) menu.inert = !open;
      menu.setAttribute('aria-hidden', String(!open));
    };
    setMenu(false);
    menuBtn.addEventListener('click', function () {
      setMenu(menuBtn.getAttribute('aria-expanded') !== 'true');
    });
    menu.addEventListener('click', function (e) {
      if (e.target.closest('a')) setMenu(false);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menu.classList.contains('is-open')) {
        setMenu(false);
        menuBtn.focus();
      }
    });
    if (window.matchMedia) {
      var desktop = window.matchMedia('(min-width: 921px)');
      var onDesktop = function (e) { if (e.matches) setMenu(false); };
      if (desktop.addEventListener) desktop.addEventListener('change', onDesktop);
    }
  }

  /* ------------------------------------------------------------------
     4. Miniatures YouTube : repli élégant si l'image est absente
     ------------------------------------------------------------------ */
  function markFallback(img) {
    var host = img.closest('[data-thumb]');
    if (host) host.classList.add('is-fallback');
  }
  // Miniature absente : on retente avec la version standard (hqdefault),
  // puis on affiche une carte-titre aux couleurs du média.
  function retryOrFallback(img) {
    var alt = img.getAttribute('data-fallback');
    if (alt && img.getAttribute('src') !== alt) {
      img.removeAttribute('srcset');
      img.removeAttribute('sizes');
      img.src = alt;
      return;
    }
    markFallback(img);
  }
  $$('img[data-yt-thumb]').forEach(function (img) {
    var check = function () {
      // YouTube renvoie une image grise de 120×90 quand la miniature n'existe pas
      if (img.naturalWidth && img.naturalWidth <= 120) retryOrFallback(img);
    };
    if (img.complete) {
      if (img.naturalWidth === 0 && img.getAttribute('loading') !== 'lazy') retryOrFallback(img);
      else check();
    }
    img.addEventListener('load', check);
    img.addEventListener('error', function () { retryOrFallback(img); });
  });

  /* Dates relatives : « il y a 2 h », « hier »… (la date reste lisible sans JS) */
  var rtf = window.Intl && Intl.RelativeTimeFormat ? new Intl.RelativeTimeFormat('fr', { numeric: 'auto' }) : null;
  $$('time[data-rel]').forEach(function (el) {
    var t = Date.parse(el.getAttribute('datetime'));
    if (!t) return;
    var mins = Math.round((Date.now() - t) / 60000);
    if (mins < 0) return;
    var label = null;
    if (mins < 60) label = mins < 2 ? 'À l’instant' : 'Il y a ' + mins + ' min';
    else if (mins < 24 * 60) label = 'Il y a ' + Math.round(mins / 60) + ' h';
    else if (rtf && mins < 7 * 24 * 60) {
      label = rtf.format(-Math.round(mins / 1440), 'day');
      label = label.charAt(0).toUpperCase() + label.slice(1);
    }
    if (label) el.textContent = label;
    if (mins < 48 * 60) el.classList.add('is-new');
  });

  /* ------------------------------------------------------------------
     5. Partage (WhatsApp en priorité, partage natif sur mobile)
     ------------------------------------------------------------------ */
  function whatsappUrl(text, url) {
    return 'https://wa.me/?text=' + encodeURIComponent(text + '\n' + url);
  }
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-share]');
    if (!btn || isPreview) return;
    var url = btn.getAttribute('data-share-url') || window.location.href;
    var title = btn.getAttribute('data-share-title') || document.title;
    var text = title + ' — Relais Populaire';
    var mode = btn.getAttribute('data-share');
    if (mode !== 'whatsapp' && navigator.share) {
      e.preventDefault();
      navigator.share({ title: title, text: text, url: url }).catch(function () { /* annulé */ });
      return;
    }
    e.preventDefault();
    window.open(whatsappUrl(text, url), '_blank', 'noopener');
  });

  /* ------------------------------------------------------------------
     6. Lecteur vidéo (YouTube sans cookies, chargé uniquement au clic)
     ------------------------------------------------------------------ */
  var dialog = $('#player');
  var frame = dialog ? $('.player__frame', dialog) : null;
  var lastTrigger = null;

  function youtubeUrl(id, isShort) {
    return (isShort ? 'https://www.youtube.com/shorts/' : 'https://www.youtube.com/watch?v=') + id;
  }

  function openPlayer(id, title, isShort, trigger) {
    if (!dialog || !frame || typeof dialog.showModal !== 'function' || isLocalFile) {
      window.open(youtubeUrl(id, isShort), '_blank', 'noopener');
      return;
    }
    lastTrigger = trigger || null;
    frame.textContent = '';
    var iframe = document.createElement('iframe');
    iframe.src = 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(id) +
      '?autoplay=1&rel=0&playsinline=1';
    iframe.title = title ? 'Vidéo : ' + title : 'Vidéo Relais Populaire';
    iframe.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share');
    iframe.setAttribute('allowfullscreen', '');
    iframe.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    frame.appendChild(iframe);

    dialog.classList.toggle('is-short', !!isShort);
    var t = $('[data-player-title]', dialog);
    if (t) t.textContent = title || '';
    var link = $('[data-player-link]', dialog);
    if (link) link.href = youtubeUrl(id, isShort);
    var share = $('[data-player-share]', dialog);
    if (share) {
      share.setAttribute('data-share-url', youtubeUrl(id, isShort));
      share.setAttribute('data-share-title', title || 'Relais Populaire');
      share.href = whatsappUrl((title || 'Relais Populaire') + ' — Relais Populaire', youtubeUrl(id, isShort));
    }
    dialog.showModal();
  }

  if (dialog) {
    dialog.addEventListener('close', function () {
      if (frame) frame.textContent = '';
      if (lastTrigger && typeof lastTrigger.focus === 'function') lastTrigger.focus();
    });
    dialog.addEventListener('click', function (e) {
      if (e.target === dialog) dialog.close();
    });
    $$('[data-player-close]', dialog).forEach(function (b) {
      b.addEventListener('click', function () { dialog.close(); });
    });
  }

  document.addEventListener('click', function (e) {
    var a = e.target.closest('[data-yt]');
    if (!a || isPreview) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
    e.preventDefault();
    openPlayer(a.getAttribute('data-yt'), a.getAttribute('data-title'), a.getAttribute('data-short') === '1', a);
  });

  /* Lecteur intégré « dernières publications » (playlist automatique) */
  $$('[data-embed-playlist]').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      if (isLocalFile || isPreview) return; // ouvre YouTube directement
      e.preventDefault();
      var box = btn.closest('.embed');
      var iframe = document.createElement('iframe');
      iframe.src = 'https://www.youtube-nocookie.com/embed/videoseries?list=' +
        encodeURIComponent(btn.getAttribute('data-embed-playlist')) + '&autoplay=1&rel=0&playsinline=1';
      iframe.title = 'Dernières vidéos de Relais Populaire';
      iframe.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share');
      iframe.setAttribute('allowfullscreen', '');
      iframe.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
      box.textContent = '';
      box.appendChild(iframe);
    });
  });

  /* ------------------------------------------------------------------
     7. Manifeste : les mots s'allument au fil du défilement
     ------------------------------------------------------------------ */
  var manifesto = $('[data-words]');
  if (manifesto) {
    var wrapWords = function (node) {
      Array.prototype.slice.call(node.childNodes).forEach(function (child) {
        if (child.nodeType === 3) {
          var frag = document.createDocumentFragment();
          child.textContent.split(/(\s+)/).forEach(function (part) {
            if (!part) return;
            if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(part)); return; }
            var s = document.createElement('span');
            s.className = 'w';
            s.textContent = part;
            frag.appendChild(s);
          });
          child.parentNode.replaceChild(frag, child);
        } else if (child.nodeType === 1) {
          wrapWords(child);
        }
      });
    };
    wrapWords(manifesto);
    var words = $$('.w', manifesto);
    var ticking = false;
    var updateWords = function () {
      ticking = false;
      if (!motionOn()) { words.forEach(function (w) { w.classList.add('is-on'); }); return; }
      var r = manifesto.getBoundingClientRect();
      var vh = window.innerHeight || 800;
      var start = vh * 0.88;
      var end = vh * 0.5;
      var p = (start - r.top) / (start - end + r.height * 0.55);
      p = Math.max(0, Math.min(1, p));
      var n = Math.round(p * words.length);
      for (var i = 0; i < words.length; i++) words[i].classList.toggle('is-on', i < n);
    };
    var requestWords = function () {
      if (!ticking) { ticking = true; window.requestAnimationFrame(updateWords); }
    };
    updateWords();
    window.addEventListener('scroll', requestWords, { passive: true });
    window.addEventListener('resize', requestWords);
    motionButtons.forEach(function (b) { b.addEventListener('click', requestWords); });
  }

  /* ------------------------------------------------------------------
     8. Apparitions et compteurs
     ------------------------------------------------------------------ */
  function formatter(decimals) {
    if (!window.Intl) return { format: function (n) { return n.toFixed(decimals).replace('.', ','); } };
    return new Intl.NumberFormat('fr-FR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }
  function runCount(el) {
    var target = parseFloat(el.getAttribute('data-count')) || 0;
    var decimals = parseInt(el.getAttribute('data-decimals'), 10) || 0;
    var nf = formatter(decimals);
    var factor = Math.pow(10, decimals);
    var prefix = el.getAttribute('data-prefix') || '';
    var suffix = el.getAttribute('data-suffix') || '';
    if (!motionOn()) { el.textContent = prefix + nf.format(target) + suffix; return; }
    var t0 = null;
    var dur = 1800;
    var step = function (t) {
      if (t0 === null) t0 = t;
      var k = Math.min(1, (t - t0) / dur);
      var eased = 1 - Math.pow(1 - k, 4);
      el.textContent = prefix + nf.format(Math.round(target * eased * factor) / factor) + suffix;
      if (k < 1) window.requestAnimationFrame(step);
    };
    window.requestAnimationFrame(step);
  }

  var revealables = $$('[data-reveal], [data-count]');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        el.classList.add('is-in');
        if (el.hasAttribute('data-count')) runCount(el);
        io.unobserve(el);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
    revealables.forEach(function (el) {
      if (el.hasAttribute('data-count') && motionOn()) {
        el.textContent = (el.getAttribute('data-prefix') || '') + '0' + (el.getAttribute('data-suffix') || '');
      }
      io.observe(el);
    });
  } else {
    revealables.forEach(function (el) { el.classList.add('is-in'); });
  }

  /* ------------------------------------------------------------------
     9. Orbite 3D : parallaxe à la souris, pause hors écran
     ------------------------------------------------------------------ */
  var orbit = $('.orbit');
  if (orbit) {
    var hero = orbit.closest('.hero') || orbit;
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        orbit.classList.toggle('is-offscreen', !entries[0].isIntersecting);
      }).observe(hero);
    }
    if (window.matchMedia && window.matchMedia('(pointer: fine)').matches) {
      var raf = 0;
      hero.addEventListener('pointermove', function (e) {
        if (!motionOn()) return;
        window.cancelAnimationFrame(raf);
        raf = window.requestAnimationFrame(function () {
          var r = hero.getBoundingClientRect();
          var x = (e.clientX - r.left) / r.width - 0.5;
          var y = (e.clientY - r.top) / r.height - 0.5;
          orbit.style.setProperty('--px', (x * 10).toFixed(2) + 'deg');
          orbit.style.setProperty('--py', (y * -7).toFixed(2) + 'deg');
        });
      });
      hero.addEventListener('pointerleave', function () {
        orbit.style.setProperty('--px', '0deg');
        orbit.style.setProperty('--py', '0deg');
      });
    }
  }

  /* ------------------------------------------------------------------
     10. Filtres de la page vidéos
     ------------------------------------------------------------------ */
  var chips = $$('[data-filter]');
  if (chips.length) {
    var items = $$('[data-cat]');
    var status = $('[data-filter-status]');
    var applyFilter = function (f) {
      var shown = 0;
      chips.forEach(function (c) { c.setAttribute('aria-pressed', String(c.getAttribute('data-filter') === f)); });
      items.forEach(function (it) {
        var ok = f === 'all' || it.getAttribute('data-cat') === f;
        it.hidden = !ok;
        if (ok) shown++;
      });
      if (status) status.textContent = shown + (shown > 1 ? ' vidéos' : ' vidéo');
    };
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () { applyFilter(chip.getAttribute('data-filter')); });
    });
    var params = new URLSearchParams(window.location.search);
    var initial = params.get('theme');
    if (initial && chips.some(function (c) { return c.getAttribute('data-filter') === initial; })) applyFilter(initial);
  }

  /* ------------------------------------------------------------------
     11. Formulaire de contact → ouvre la messagerie, rien n'est stocké
     ------------------------------------------------------------------ */
  var form = $('[data-mailto-form]');
  if (form) {
    var subjectSelect = form.querySelector('[name="objet"]');
    var q = new URLSearchParams(window.location.search).get('objet');
    if (q && subjectSelect) {
      Array.prototype.forEach.call(subjectSelect.options, function (o) { if (o.value === q) subjectSelect.value = q; });
    }
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (typeof form.reportValidity === 'function' && !form.reportValidity()) return;
      var d = new FormData(form);
      var objetLabel = subjectSelect ? subjectSelect.options[subjectSelect.selectedIndex].text : 'Message';
      var nom = (d.get('nom') || '').toString().trim();
      var email = (d.get('email') || '').toString().trim();
      var tel = (d.get('tel') || '').toString().trim();
      var message = (d.get('message') || '').toString().trim();
      var subject = objetLabel + (nom ? ' — ' + nom : '');
      var body = message + '\n\n— ' + nom + (email ? '\n' + email : '') + (tel ? '\n' + tel : '');
      var to = form.getAttribute('data-mailto-form');
      window.location.href = 'mailto:' + to + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
      var note = form.querySelector('[data-form-note]');
      if (note) note.hidden = false;
    });
  }
})();
