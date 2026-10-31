/* core.js: the shared front-end engine (window.UI). Same in every app made from APP_MAKER/template;
   app-specific things live in web/app.js (brand, nav, footer) and web/pages/*.html (the pages).

   Pages:   UI.page(name, {title, nav, icon, auth, order, chrome}, mount)
              auth: null (anyone) | 'guest' (signed-out only) | 'user' | 'admin'
              nav: label for the header / phone tab bar (omit to keep it out of the menus)
              mount(view, ctx) draws into `view`; ctx = {args, me, go, api}. Return a Promise (the page
              is "ready" when it resolves) or {ready, destroy}. URLs are #name/arg1/arg2.
   Server:  UI.api(fn, ...args) -> Promise of the server function's return value. A reply of
              {ok: false, error} rejects with that message (shown as a toast unless you .catch it).
            UI.apiQuiet(fn, ...args) is the same without Anvil's loading spinner.
   Auth:    UI.auth('login'|'signup'|'reset'|'logout', {...}) -> Promise of {ok, me, message}
   Helpers: UI.esc, UI.icon, UI.toast, UI.modal, UI.confirm, UI.busy, UI.formData, UI.fmtDate, UI.ago,
            UI.store, UI.setTheme, UI.feedback, UI.go, UI.refresh
   Tests:   window.UI_READY is true when the current page has finished loading. */
(function () {
  'use strict';
  if (window.UI && window.UI.__v) return;
  var UI = window.UI = { __v: 1, pages: {}, me: null, config: { name: 'App', key: 'app', home: 'home', landing: 'landing' } };
  window.UI_READY = false;

  UI.configure = function (cfg) { Object.keys(cfg).forEach(function (k) { UI.config[k] = cfg[k]; }); };

  /* ------------------------------------------------------------------ small helpers */
  UI.esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };
  UI.plural = function (n, one, many) { return n + ' ' + (n === 1 ? one : (many || one + 's')); };
  UI.initials = function (name) {
    var p = String(name || '?').trim().split(/\s+/);
    return ((p[0] || '?')[0] + (p.length > 1 ? p[p.length - 1][0] : '')).toUpperCase();
  };
  UI.fmtDate = function (iso, opts) {
    if (!iso) return '';
    var d = iso.length <= 10 ? new Date(iso + 'T12:00:00') : new Date(iso);
    return d.toLocaleDateString(undefined, opts || { day: 'numeric', month: 'short', year: 'numeric' });
  };
  UI.fmtDateTime = function (iso) {
    return iso ? new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';
  };
  UI.ago = function (iso) {
    if (!iso) return '';
    var s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 60) return 'just now';
    var steps = [[60, 'minute'], [24, 'hour'], [7, 'day'], [4.35, 'week'], [12, 'month'], [Infinity, 'year']], n = s / 60;
    for (var i = 0; i < steps.length; i++) {
      if (n < steps[i][0]) { n = Math.floor(n); return UI.plural(n, steps[i][1]) + ' ago'; }
      n = n / steps[i][0];
    }
    return '';
  };
  UI.store = {
    get: function (k, dflt) { try { var v = localStorage.getItem(UI.config.key + '.' + k); return v == null ? dflt : JSON.parse(v); } catch (e) { return dflt; } },
    set: function (k, v) { try { localStorage.setItem(UI.config.key + '.' + k, JSON.stringify(v)); } catch (e) {} }
  };
  UI.formData = function (form) {
    var out = {};
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name || el.disabled) return;
      if (el.type === 'checkbox') out[el.name] = el.checked;
      else if (el.type === 'radio') { if (el.checked) out[el.name] = el.value; }
      else out[el.name] = el.value;
    });
    return out;
  };
  /* Disable a button while a Promise runs; returns the Promise. */
  UI.busy = function (btn, promise) {
    if (!btn) return promise;
    btn.disabled = true; btn.classList.add('is-busy');
    var done = function () { btn.disabled = false; btn.classList.remove('is-busy'); };
    promise.then(done, done);
    return promise;
  };

  var ICONS = {
    home: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/>',
    users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.5 3-5.5 6.5-5.5s6.5 2 6.5 5.5"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7"/><path d="M18 14.7c2.2.6 3.5 2.4 3.5 5.3"/>',
    sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    shield: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/>',
    logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    trash: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M6 6l1 14h10l1-14"/>',
    edit: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7"/>',
    x: '<path d="M6 6l12 12M18 6 6 18"/>',
    chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-4.9A8 8 0 1 1 21 12z"/>',
    bell: '<path d="M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    back: '<path d="M19 12H5M11 18l-6-6 6-6"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    bug: '<rect x="7" y="8" width="10" height="12" rx="5"/><path d="M12 8V5M9 5.5 7.5 4M15 5.5 16.5 4M7 13H3M21 13h-4M7.5 18l-3 2M16.5 18l3 2M7.5 9.5l-3-2M16.5 9.5l3-2"/>',
    bulb: '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
    star: '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
    heart: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    chevron: '<path d="m6 9 6 6 6-6"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    inbox: '<path d="M3 13h5l1.5 3h5L16 13h5"/><path d="M5 5h14l2 8v6H3v-6z"/>',
    grid: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
    sparkle: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
    database: '<ellipse cx="12" cy="5.5" rx="7.5" ry="2.5"/><path d="M4.5 5.5v13c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5v-13"/><path d="M4.5 12c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5"/>',
    refresh: '<path d="M20 11a8 8 0 0 0-14.3-4.9L4 8"/><path d="M4 4v4h4"/><path d="M4 13a8 8 0 0 0 14.3 4.9L20 16"/><path d="M20 20v-4h-4"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    map: '<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/>',
    pin: '<path d="M12 21s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/>',
    camera: '<path d="M4 8h3l2-3h6l2 3h3v12H4z"/><circle cx="12" cy="13.5" r="3.5"/>',
    image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3z"/>',
    copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
    filter: '<path d="M4 5h16l-6 7.5V19l-4 1.5v-8z"/>',
    more: '<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>'
  };
  UI.ICONS = ICONS;
  UI.icon = function (name, cls) {
    return '<svg class="ui-ic ' + (cls || '') + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICONS[name] || ICONS.sparkle) + '</svg>';
  };

  /* ------------------------------------------------------------------ toasts, modals */
  UI.toast = function (msg, kind) {
    var box = document.querySelector('.ui-toasts');
    if (!box) { box = document.createElement('div'); box.className = 'ui ui-toasts'; box.setAttribute('aria-live', 'polite'); document.body.appendChild(box); }
    var t = document.createElement('div');
    t.className = 'ui-toast' + (kind ? ' ' + kind : '');
    t.innerHTML = (kind === 'error' ? UI.icon('info') : kind === 'ok' ? UI.icon('check') : '') + '<span>' + UI.esc(msg) + '</span>';
    box.appendChild(t);
    setTimeout(function () { t.classList.add('out'); setTimeout(function () { t.remove(); }, 300); }, kind === 'error' ? 6500 : 3200);
  };
  UI.modal = function (html, opts) {
    opts = opts || {};
    var prev = document.activeElement;
    var wrap = document.createElement('div');
    wrap.className = 'ui ui-modal-wrap';
    wrap.innerHTML = '<div class="ui-modal' + (opts.wide ? ' wide' : '') + '" role="dialog" aria-modal="true">' +
      '<button class="ui-btn ghost icon ui-modal-x" data-close aria-label="Close">' + UI.icon('x') + '</button>' + html + '</div>';
    document.body.appendChild(wrap);
    document.documentElement.classList.add('ui-modal-open');
    function key(e) { if (e.key === 'Escape') close(); }
    function close() {
      if (!wrap.parentNode) return;
      wrap.remove(); document.removeEventListener('keydown', key);
      if (!document.querySelector('.ui-modal-wrap')) document.documentElement.classList.remove('ui-modal-open');
      if (opts.onclose) opts.onclose();
      if (prev && prev.focus) prev.focus();
    }
    document.addEventListener('keydown', key);
    wrap.addEventListener('mousedown', function (e) { if (e.target === wrap) close(); });
    wrap.addEventListener('click', function (e) { if (e.target.closest('[data-close]')) close(); });
    var first = wrap.querySelector('input, textarea, select');
    setTimeout(function () { (first || wrap.querySelector('.ui-modal')).focus && (first || wrap.querySelector('.ui-modal')).focus(); }, 30);
    return { el: wrap.querySelector('.ui-modal'), close: close };
  };
  UI.confirm = function (o) {
    o = typeof o === 'string' ? { title: o } : (o || {});
    return new Promise(function (resolve) {
      var answered = false;
      var m = UI.modal('<h2>' + UI.esc(o.title || 'Are you sure?') + '</h2>' + (o.text ? '<p class="muted">' + UI.esc(o.text) + '</p>' : '') +
        '<div class="ui-row end" style="margin-top:20px"><button class="ui-btn ghost" data-close>' + UI.esc(o.cancel || 'Cancel') + '</button>' +
        '<button class="ui-btn ' + (o.danger ? 'danger solid' : 'primary') + '" data-ok>' + UI.esc(o.ok || 'OK') + '</button></div>',
      { onclose: function () { if (!answered) resolve(false); } });
      m.el.querySelector('[data-ok]').onclick = function () { answered = true; m.close(); resolve(true); };
    });
  };

  /* ------------------------------------------------------------------ theme */
  UI.theme = function () { return UI.store.get('theme', 'auto'); };
  UI.applyTheme = function (t) {
    if (t === 'light' || t === 'dark') document.documentElement.setAttribute('data-theme', t);
    else document.documentElement.removeAttribute('data-theme');
    var dark = t === 'dark' || (t !== 'light' && window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.classList.toggle('ui-dark', !!dark);
  };
  UI.setTheme = function (t) { UI.store.set('theme', t); UI.applyTheme(t); };
  UI.applyTheme(UI.theme());
  if (window.matchMedia) {
    try { matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () { UI.applyTheme(UI.theme()); }); } catch (e) {}
  }

  /* ------------------------------------------------------------------ server bridge */
  var bridge = null;
  function send(kind, payload) {
    if (!bridge) return Promise.reject(new Error('The app is still starting.'));
    var out;
    try { out = bridge(kind, JSON.stringify(payload || {})); } catch (e) { return Promise.reject(e); }
    return Promise.resolve(out).then(function (r) {
      r = typeof r === 'string' ? JSON.parse(r) : (r || {});
      if (r.error) {
        var err = new Error(r.error); err.uiApi = true; err.denied = !!r.denied;
        if (r.detail) console.error(kind, payload && payload.fn, r.detail);
        if (r.reload) setTimeout(function () { location.reload(); }, 2500);
        throw err;
      }
      return r.result;
    });
  }
  function apiCall(quiet, fn, args) {
    return send('call', { fn: fn, args: args, quiet: quiet }).then(function (res) {
      if (res && typeof res === 'object' && res.ok === false) {
        var err = new Error(res.error || 'That didn\'t work.'); err.uiApi = true; err.expected = true; err.result = res;
        throw err;
      }
      return res;
    });
  }
  UI.api = function (fn) { return apiCall(false, fn, Array.prototype.slice.call(arguments, 1)); };
  UI.apiQuiet = function (fn) { return apiCall(true, fn, Array.prototype.slice.call(arguments, 1)); };
  /* Errors nobody caught become a toast, so a failed action is never silent. */
  window.addEventListener('unhandledrejection', function (e) {
    if (e.reason && e.reason.uiApi) { e.preventDefault(); UI.toast(e.reason.message, 'error'); }
  });

  /* Sign in / up / out. On success it navigates: to where the visitor was heading (UI.after) or home
     after signing in, to the landing page after signing out. */
  UI.auth = function (kind, payload) {
    return send(kind, payload || {}).then(function (r) {
      if (r && r.ok === false) { var err = new Error(r.error); err.uiApi = true; err.expected = true; throw err; }
      if (r && 'me' in r && (r.me || kind === 'logout')) {
        UI.me = r.me || null;
        var target = r.me ? (UI.after || '#' + UI.config.home) : '#' + UI.config.landing;
        UI.after = null;
        if (location.hash === target) route(); else location.hash = target;
      }
      return r;
    });
  };
  /* Update the signed-in user's details (e.g. a new name) and redraw the header, without reloading the page. */
  UI.setMe = function (me) {
    UI.me = me || null;
    if (shellRoot) renderChrome(current.name);
  };

  /* ------------------------------------------------------------------ pages and routing */
  UI.page = function (name, opts, mount) {
    if (typeof opts === 'function') { mount = opts; opts = {}; }
    opts.name = name; opts.mount = mount;
    UI.pages[name] = opts;
  };
  UI.allowed = function (p) {
    if (!p) return false;
    if (p.auth === 'user') return !!UI.me;
    if (p.auth === 'admin') return !!(UI.me && UI.me.is_admin);
    if (p.auth === 'guest') return !UI.me;
    return true;
  };
  UI.navPages = function () {
    return Object.keys(UI.pages).map(function (k) { return UI.pages[k]; })
      .filter(function (p) { return p.nav && UI.allowed(p) && (!p.when || p.when()); })
      .sort(function (a, b) { return (a.order || 50) - (b.order || 50); });
  };
  UI.parseHash = function () {
    var h = (location.hash || '').replace(/^#!?\/?/, '');
    var parts = h.split('?')[0].split('/').filter(function (x) { return x !== ''; }).map(decodeURIComponent);
    return { name: parts[0] || '', args: parts.slice(1) };
  };
  UI.hashFor = function (name) {
    var args = Array.prototype.slice.call(arguments, 1).filter(function (a) { return a != null && a !== ''; });
    return '#' + [name].concat(args.map(encodeURIComponent)).join('/');
  };
  UI.go = function (name) {
    var h = UI.hashFor.apply(null, arguments);
    if (location.hash === h) route(); else location.hash = h;
  };
  UI.refresh = function () { route(); };
  UI.after = null;  // where to go after signing in

  var shellRoot = null, view = null, current = { name: null, destroy: null }, routeSeq = 0;

  function defaultPage() { return UI.me ? UI.config.home : UI.config.landing; }

  function route() {
    var r = UI.parseHash(), name = r.name || defaultPage(), p = UI.pages[name];
    if (!p) { name = defaultPage(); p = UI.pages[name]; r.args = []; }
    if (p.auth === 'guest' && UI.me) { p = UI.pages[UI.config.home]; name = UI.config.home; r.args = []; }
    if ((p.auth === 'user' || p.auth === 'admin') && !UI.me) {
      UI.after = location.hash && location.hash !== '#' ? location.hash : null;
      p = UI.pages.auth; name = 'auth'; r.args = [];
    }
    if (p.auth === 'admin' && !(UI.me && UI.me.is_admin)) {
      UI.toast('That page is for admins only.', 'error');
      p = UI.pages[UI.config.home]; name = UI.config.home; r.args = [];
    }
    var seq = ++routeSeq;
    window.UI_READY = false;
    if (current.destroy) { try { current.destroy(); } catch (e) { console.error(e); } }
    current = { name: name, args: r.args, destroy: null };
    if (shellRoot) {
      shellRoot.className = 'ui ui-shell page-' + name + (UI.me ? ' signed-in' : ' signed-out') + (p.chrome === false ? ' no-chrome' : '');
      renderChrome(name);
    }
    // A fresh element for every page, so listeners a page adds to `view` never pile up.
    var fresh = view.cloneNode(false);
    view.parentNode.replaceChild(fresh, view);
    view = fresh;
    window.scrollTo(0, 0);
    document.title = (p.title ? (typeof p.title === 'function' ? p.title(r.args) : p.title) + ' · ' : '') + UI.config.name;
    var ctx = { name: name, args: r.args, me: UI.me, go: UI.go, api: UI.api, page: p };
    var out;
    try { out = p.mount(view, ctx); } catch (e) { console.error(e); out = Promise.reject(e); }
    var ready = out && typeof out.then === 'function' ? out : (out && out.ready) || Promise.resolve();
    if (out && out.destroy) current.destroy = out.destroy;
    Promise.resolve(ready).then(function () { if (seq === routeSeq) window.UI_READY = true; },
      function (e) {
        if (seq !== routeSeq) return;
        console.error(e);
        if (!view.innerHTML) view.innerHTML = '<div class="ui-wrap"><div class="ui-empty">' + UI.icon('info') +
          '<h3>This page didn\'t load</h3><p class="muted">' + UI.esc(e && e.message || 'Something went wrong.') + '</p>' +
          '<button class="ui-btn" onclick="UI.refresh()">Try again</button></div></div>';
        window.UI_READY = true;
      });
  }
  UI.current = function () { return current; };

  /* The shell's parts come from web/app.js: UI.shell = {header(me, active), footer(me), tabbar(me, active)} */
  function renderChrome(active) {
    var S = UI.shell || {};
    var hd = shellRoot.querySelector('[data-ui-header]'), ft = shellRoot.querySelector('[data-ui-footer]'), tb = shellRoot.querySelector('[data-ui-tabbar]');
    if (hd) hd.innerHTML = S.header ? S.header(UI.me, active) : '';
    if (ft) ft.innerHTML = S.footer ? S.footer(UI.me, active) : '';
    if (tb) tb.innerHTML = S.tabbar ? S.tabbar(UI.me, active) : '';
  }
  UI.renderChrome = function () { if (shellRoot) renderChrome(current.name); };

  /* Called by client_code/Main.py (and by the local harness) once the page is up. */
  UI.start = function (node, bridgeFn, bootJson) {
    bridge = bridgeFn;
    var boot = typeof bootJson === 'string' ? JSON.parse(bootJson || '{}') : (bootJson || {});
    UI.me = boot.me || null;
    var host = node && node.matches && node.matches('[data-ui-app]') ? node : (node && node.querySelector('[data-ui-app]')) || node || document.body;
    host.innerHTML = '<div class="ui ui-shell">' +
      '<header class="ui-header" data-ui-header></header>' +
      '<main class="ui-main" data-ui-view></main>' +
      '<footer class="ui-footer" data-ui-footer></footer>' +
      '<nav class="ui-tabbar" data-ui-tabbar aria-label="Main"></nav></div>';
    shellRoot = host.firstChild;
    view = host.querySelector('[data-ui-view]');
    if (UI.shell && UI.shell.wire) UI.shell.wire(shellRoot);
    window.addEventListener('hashchange', route);
    route();
  };

  /* ------------------------------------------------------------------ feedback form (footer + menu) */
  UI.feedback = function (kind) {
    var kinds = [['bug', 'Something\'s broken', 'bug'], ['idea', 'An idea', 'bulb'], ['question', 'A question', 'info'], ['other', 'Something else', 'chat']];
    var m = UI.modal('<h2>Send feedback</h2><p class="muted">Found a bug or have an idea? It goes straight to the people who make ' + UI.esc(UI.config.name) + '.</p>' +
      '<form class="ui-stack" data-fb>' +
      '<div class="ui-choices">' + kinds.map(function (k) {
        return '<label class="ui-choice"><input type="radio" name="kind" value="' + k[0] + '"' + ((kind || 'bug') === k[0] ? ' checked' : '') + '>' +
          '<span>' + UI.icon(k[2]) + UI.esc(k[1]) + '</span></label>';
      }).join('') + '</div>' +
      '<label class="ui-field"><span>What happened, or what would you like?</span><textarea name="message" rows="5" required minlength="5" placeholder="The more detail, the better."></textarea></label>' +
      (UI.me ? '' : '<label class="ui-field"><span>Your email <em>(optional, if you\'d like a reply)</em></span><input type="email" name="email" autocomplete="email"></label>') +
      '<p class="ui-hint">We also send the page you were on, your screen size and browser, to help us fix bugs.</p>' +
      '<div class="ui-row end"><button type="button" class="ui-btn ghost" data-close>Cancel</button><button class="ui-btn primary" type="submit">' + UI.icon('arrow') + 'Send</button></div></form>');
    var form = m.el.querySelector('[data-fb]');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var v = UI.formData(form);
      var ctx = { page: location.hash || '#', screen: innerWidth + 'x' + innerHeight, browser: navigator.userAgent.slice(0, 280), theme: UI.theme() };
      UI.busy(form.querySelector('[type=submit]'), UI.api('submit_feedback', v.kind, v.message, v.email || null, ctx)).then(function () {
        m.close(); UI.toast('Thank you! Your message was sent.', 'ok');
      });
    });
    return m;
  };

  /* Shared clicks: [data-go="page/arg"], [data-feedback], [data-theme-set] anywhere in the app. */
  document.addEventListener('click', function (e) {
    var el = e.target.closest && e.target.closest('[data-go],[data-feedback],[data-theme-set]');
    if (!el) return;
    if (el.hasAttribute('data-go')) { e.preventDefault(); UI.go.apply(null, el.getAttribute('data-go').split('/')); }
    else if (el.hasAttribute('data-feedback')) { e.preventDefault(); UI.feedback(el.getAttribute('data-feedback') || null); }
    else if (el.hasAttribute('data-theme-set')) { e.preventDefault(); UI.setTheme(el.getAttribute('data-theme-set')); if (UI.shell && UI.shell.onTheme) UI.shell.onTheme(); }
  });
})();


/* app.js: Health Booker's identity and frame: name, header (with the inbox bell), footer, phone tab bar.
   Pages live in web/pages/*.html; shared Health Booker helpers (window.HB) in web/pages/_hb.html.
   The engine (window.UI) is web/core.js. */
(function () {
  'use strict';
  UI.configure({
    name: 'Health Booker',
    key: 'healthbooker',          // prefix for this app's browser storage
    tagline: 'One account for every yoga studio in town.',
    home: 'discover',            // first page after signing in
    landing: 'landing'           // first page for visitors who aren't signed in
  });

  var esc = UI.esc;

  function brand() {
    return '<a class="ui-brand" href="#" data-go="' + (UI.me ? UI.config.home : UI.config.landing) + '" aria-label="' + esc(UI.config.name) + ' home">' +
      '<img src="_/theme/icon.svg" alt="" width="32" height="32"><span>' + esc(UI.config.name) + '</span></a>';
  }

  function themeSwitch() {
    var t = UI.theme();
    return '<div class="ui-seg" role="group" aria-label="Appearance">' + [['auto', 'Auto'], ['light', 'Light'], ['dark', 'Dark']].map(function (o) {
      return '<button type="button" data-theme-set="' + o[0] + '" class="' + (t === o[0] ? 'on' : '') + '">' + o[1] + '</button>';
    }).join('') + '</div>';
  }

  function userMenu(me) {
    return '<div class="ui-menu" data-menu hidden>' +
      '<div class="ui-menu-head"><strong>' + esc(me.name) + '</strong><span class="muted small">' + esc(me.email) + '</span></div>' +
      '<a href="#practice" data-go="practice">' + UI.icon('leaf') + 'My practice</a>' +
      '<a href="#practice/wallet" data-go="practice/wallet">' + UI.icon('wallet') + 'Wallet</a>' +
      '<a href="#inbox" data-go="inbox">' + UI.icon('bell') + 'Inbox</a>' +
      (me.teaches ? '<a href="#teach" data-go="teach">' + UI.icon('mat') + 'Teach</a>' : '') +
      (me.manages ? '<a href="#manage" data-go="manage">' + UI.icon('door') + 'Run my studio</a>' : '<a href="#open" data-go="open">' + UI.icon('door') + 'Open a studio</a>') +
      '<a href="#profile" data-go="profile">' + UI.icon('user') + 'Your profile</a>' +
      (me.is_admin ? '<a href="#admin" data-go="admin">' + UI.icon('shield') + 'Admin</a>' : '') +
      '<div class="ui-menu-block"><span class="small muted">Appearance</span>' + themeSwitch() + '</div>' +
      '<button type="button" data-feedback>' + UI.icon('chat') + 'Send feedback</button>' +
      '<button type="button" data-lk-open="overview">' + UI.icon('lock') + 'Privacy &amp; Terms</button>' +
      '<button type="button" data-signout>' + UI.icon('logout') + 'Sign out</button></div>';
  }

  function bell(me) {
    var n = me.unread || 0;
    return '<a class="ui-btn ghost icon ui-bell" href="#inbox" data-go="inbox" aria-label="Inbox' + (n ? ', ' + n + ' new' : '') + '">' + UI.icon('bell') +
      (n ? '<span class="dot">' + (n > 9 ? '9+' : n) + '</span>' : '') + '</a>';
  }

  UI.shell = {
    header: function (me, active) {
      var nav = UI.navPages();
      return '<div class="ui-header-in">' + brand() +
        '<nav class="ui-nav" aria-label="Main">' + nav.map(function (p) {
          return '<a href="#' + p.name + '" class="' + (p.name === active ? 'on' : '') + '">' + UI.icon(p.icon) + '<span>' + esc(p.nav) + '</span></a>';
        }).join('') + '</nav>' +
        '<div class="ui-header-right">' +
        (me ? bell(me) + '<button type="button" class="ui-avatar-btn" data-menu-toggle aria-label="Your account" aria-haspopup="true">' + esc(UI.initials(me.name)) + '</button>' + userMenu(me)
          : (active === 'auth' ? '' : '<a class="ui-btn ghost" href="#auth" data-go="auth">Sign in</a><a class="ui-btn primary" href="#auth/signup" data-go="auth/signup">Join free</a>')) +
        '</div></div>';
    },
    footer: function (me) {
      return '<div class="ui-footer-in"><div class="ui-footer-brand">' + brand() + '<p class="muted small">' + esc(UI.config.tagline) + '</p></div>' +
        '<div class="ui-footer-links">' +
        '<a href="#discover" data-go="discover">Find a class</a>' +
        '<a href="#landing" data-go="landing">About</a>' +
        '<a href="#open" data-go="open">For studios</a>' +
        '<button type="button" data-feedback>Send feedback</button>' +
        '<button type="button" data-lk-open="overview">Privacy &amp; Terms</button>' +
        '</div><p class="ui-footer-legal small muted">© ' + new Date().getFullYear() + ' ' + esc(UI.config.name) + ' · The demo studios, teachers and students are fictional.</p></div>';
    },
    tabbar: function (me, active) {
      var nav = UI.navPages();
      if (!me || nav.length < 2) return '';
      return nav.slice(0, 4).map(function (p) {
        return '<a href="#' + p.name + '" class="' + (p.name === active ? 'on' : '') + '">' + UI.icon(p.icon) + '<span>' + esc(p.tab || p.nav) + '</span></a>';
      }).join('') + '<a href="#profile" class="' + (active === 'profile' ? 'on' : '') + '">' + UI.icon('user') + '<span>You</span></a>';
    },
    wire: function (root) {
      root.addEventListener('click', function (e) {
        var t = e.target.closest('[data-menu-toggle]');
        var menu = root.querySelector('[data-menu]');
        if (t && menu) { menu.hidden = !menu.hidden; t.setAttribute('aria-expanded', String(!menu.hidden)); return; }
        if (e.target.closest('[data-signout]')) { UI.auth('logout').then(function () { UI.toast('Signed out. Namaste!'); }); }
        if (menu && !menu.hidden && !e.target.closest('[data-menu] .ui-seg')) menu.hidden = true;
      });
      document.addEventListener('keydown', function (e) {
        var menu = root.querySelector('[data-menu]');
        if (e.key === 'Escape' && menu) menu.hidden = true;
      });
    },
    onTheme: function () {  // redraw the menu's Auto/Light/Dark buttons and keep the menu open
      var menu = document.querySelector('[data-menu]'), open = menu && !menu.hidden;
      UI.renderChrome();
      if (open) document.querySelector('[data-menu]').hidden = false;
    }
  };

  /* The bell's count: refreshed quietly when the page changes (at most every 20 seconds). */
  var lastCount = 0;
  UI.refreshUnread = function (force) {
    if (!UI.me || (!force && Date.now() - lastCount < 20000)) return;
    lastCount = Date.now();
    UI.apiQuiet('inbox_count').then(function (n) {
      if (UI.me && UI.me.unread !== n) { UI.me.unread = n; UI.renderChrome(); }
    }, function () {});
  };
  window.addEventListener('hashchange', function () { UI.refreshUnread(); });
})();


/* ===== _hb.html ===== */
(function () {
  'use strict';
  var esc = UI.esc;
  var HB = window.HB = {};

  /* extra icons (24px line art like core.js) */
  Object.assign(UI.ICONS, {
    leaf: '<path d="M5 19c0-8 5.5-14 15-14 0 9-6 14-14 14z"/><path d="M5 19 14 10"/>',
    flame: '<path d="M12 21c-4 0-6.5-2.6-6.5-6.2 0-3.8 3.2-5.6 3.9-9.3 2.5 1.6 3.5 3.7 3.4 5.6 1-.6 1.6-1.6 1.8-2.8 2 1.6 3.9 3.9 3.9 6.6C18.5 18.5 16 21 12 21z"/>',
    wallet: '<rect x="3" y="6" width="18" height="14" rx="2.5"/><path d="M3 10h18"/><path d="M16 15h2"/><path d="M6 6l9-3 1.5 3"/>',
    ticket: '<path d="M4 7h16v3a2 2 0 0 0 0 4v3H4v-3a2 2 0 0 0 0-4z"/><path d="M14 7v10" stroke-dasharray="2 2"/>',
    mat: '<rect x="7" y="3" width="10" height="18" rx="2"/><path d="M7 7h10"/>',
    door: '<path d="M5 21V4a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v17"/><path d="M3 21h18"/><circle cx="15" cy="12" r=".8"/>',
    chart: '<path d="M4 20V4"/><path d="M4 20h16"/><path d="M8 16v-4M12 16V8M16 16v-6"/>',
    gift: '<rect x="4" y="9" width="16" height="11" rx="1.5"/><path d="M3 9h18v3H3zM12 9v11"/><path d="M12 9c-2-4-6-4-6-1.5S9 9 12 9zM12 9c2-4 6-4 6-1.5S15 9 12 9z"/>',
    share: '<circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="m8.2 10.8 7.6-3.6M8.2 13.2l7.6 3.6"/>',
    download: '<path d="M12 4v11M7 10l5 5 5-5"/><path d="M4 19h16"/>',
    swap: '<path d="M7 7h12l-3-3M17 17H5l3 3"/>',
    tablet: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M11 18h2"/>',
    tag: '<path d="M3 12V4h8l9 9-8 8z"/><circle cx="7.5" cy="8.5" r="1.3"/>',
    heartfill: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" fill="currentColor"/>'
  });

  HB.ACCENTS = { sage: '#5e8263', clay: '#b8613c', lake: '#3d7690', plum: '#87577b', sun: '#a87b1f', moss: '#66763a' };
  HB.acc = function (key) { return 'acc-' + (HB.ACCENTS[key] ? key : 'sage'); };
  HB.LEVEL = { all: 'All levels', beginner: 'Beginner', intermediate: 'Intermediate', advanced: 'Advanced' };
  HB.MOODS = [[1, 'Heavy'], [2, 'Tired'], [3, 'Okay'], [4, 'Light'], [5, 'Glowing']];

  /* ------------------------------------------------------------------ time, money */
  HB.time = function (iso) { return new Date(iso).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }); };
  /* 10:00<small>AM</small>: the clock part big, AM/PM small (any locale). */
  HB.timeHtml = function (iso) {
    var t = HB.time(iso), m = t.match(/^([\d:.]+)\s*(.*)$/);
    return m && m[2] ? esc(m[1]) + '<small>' + esc(m[2]) + '</small>' : esc(t);
  };
  HB.dayKey = function (d) { d = d instanceof Date ? d : new Date(d); return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2); };
  HB.startOfDay = function (d) { d = new Date(d || Date.now()); d.setHours(0, 0, 0, 0); return d; };
  HB.addDays = function (d, n) { d = new Date(d); d.setDate(d.getDate() + n); return d; };
  HB.relDay = function (iso) {
    var k = HB.dayKey(iso), t = HB.dayKey(new Date());
    if (k === t) return 'Today';
    if (k === HB.dayKey(HB.addDays(new Date(), 1))) return 'Tomorrow';
    return new Date(iso).toLocaleDateString(undefined, { weekday: 'long' });
  };
  HB.date = function (iso) { return new Date(iso).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' }); };
  HB.when = function (iso) { return HB.relDay(iso) + ', ' + new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) + ' · ' + HB.time(iso); };
  HB.money = function (n) {
    n = Number(n || 0);
    if (!n) return 'Free';
    return '$' + (n % 1 ? n.toFixed(2) : n.toLocaleString());
  };
  HB.mins = function (m) { return m >= 60 ? (Math.floor(m / 60) + 'h' + (m % 60 ? ' ' + (m % 60) : '')) : m + ' min'; };

  HB.leaves = function (n) {
    var out = '<span class="hb-leaves" title="Intensity ' + n + ' of 5" aria-label="Intensity ' + n + ' of 5">';
    for (var i = 1; i <= 5; i++) out += '<i class="' + (i <= n ? 'on' : '') + '"></i>';
    return out + '</span>';
  };
  HB.stars = function (n) {
    var out = '<span class="hb-stars" aria-label="' + n + ' out of 5 stars">';
    for (var i = 1; i <= 5; i++) out += UI.icon('star', i <= Math.round(n) ? 'on' : '');
    return out + '</span>';
  };
  HB.rating = function (r, n) { return n ? '<span class="hb-meta" style="display:inline-flex">' + HB.stars(r) + ' <b style="color:var(--c-ink)">' + Number(r).toFixed(1) + '</b> (' + n + ')</span>' : '<span class="muted small">New on Health Booker</span>'; };

  HB.spots = function (c) {
    if (c.status === 'cancelled') return '<span class="hb-left">Cancelled</span>';
    if (c.left <= 0) return '<span class="hb-left low">Full' + (c.waiting ? ' · ' + c.waiting + ' waiting' : '') + '</span>';
    return '<span class="hb-left' + (c.left <= 3 ? ' low' : '') + '">' + (c.left <= 3 ? 'Only ' : '') + UI.plural(c.left, 'mat') + ' left</span>';
  };

  /* One class on a schedule. o: {mine: status, date: true to show the day, studio: false to hide the studio} */
  HB.classRow = function (c, o) {
    o = o || {};
    var mine = o.mine, s = c.studio || {};
    var btn = mine === 'booked' || mine === 'checked_in' ? '<span class="hb-state">' + UI.icon('check') + 'Booked</span>'
      : mine === 'waitlist' ? '<span class="hb-state wait">' + UI.icon('clock') + 'On waitlist</span>'
      : c.status === 'cancelled' ? '' : '<button class="ui-btn sm ' + (c.left > 0 ? 'primary' : '') + '" data-book="' + esc(c.id) + '">' + (c.left > 0 ? 'Book' : 'Join waitlist') + '</button>';
    var tags = [];
    tags.push('<span class="hb-tag">' + esc(c.style) + '</span>');
    if (c.level !== 'all') tags.push('<span class="hb-tag">' + esc(HB.LEVEL[c.level] || c.level) + '</span>');
    if (c.heated) tags.push('<span class="hb-tag heat">' + UI.icon('flame') + ' Heated</span>');
    if (c.kind === 'workshop') tags.push('<span class="hb-tag heat">Workshop · ' + HB.money(c.price) + '</span>');
    if (c.sub) tags.push('<span class="hb-tag sub">Sub: ' + esc(c.teacher ? c.teacher.name.split(' ')[0] : '') + ' for ' + esc((c.orig_teacher || '').split(' ')[0]) + '</span>');
    (c.tags || []).filter(function (t) { return t !== 'Heated'; }).slice(0, o.allTags ? 9 : 2).forEach(function (t) { tags.push('<span class="hb-tag">' + esc(t) + '</span>'); });
    return '<article class="hb-class ' + HB.acc(s.accent) + (c.status === 'cancelled' ? ' cancelled' : '') + '" data-class="' + esc(c.id) + '">' +
      '<div class="hb-time"><b>' + HB.timeHtml(c.start) + '</b><span>' + (o.date ? esc(HB.date(c.start)) + '<br>' : '') + esc(HB.mins(c.minutes)) + '</span></div>' +
      '<div style="min-width:0"><h3>' + esc(c.title) + '</h3><div class="hb-meta">' +
        (o.studio === false ? '' : '<a href="#studio/' + esc(s.slug) + '" data-go="studio/' + esc(s.slug) + '"><span class="hb-dot"></span> ' + esc(s.name) + '</a>') +
        (c.teacher ? '<span>' + esc(c.teacher.name) + '</span>' : '') +
        (o.studio === false ? '' : '<span>' + esc(s.neighbourhood) + '</span>') + HB.leaves(c.intensity) + '</div>' +
        '<div class="hb-tags">' + tags.join('') + '</div></div>' +
      '<div class="hb-side">' + HB.spots(c) + btn + '</div></article>';
  };

  /* Classes grouped by day with headings. */
  HB.byDay = function (classes, rowFn) {
    var out = '', last = null;
    classes.forEach(function (c) {
      var k = HB.dayKey(c.start);
      if (k !== last) {
        if (last !== null) out += '</div>';
        out += '<h3 class="hb-day">' + esc(HB.relDay(c.start)) + ' <span>' + esc(new Date(c.start).toLocaleDateString(undefined, { day: 'numeric', month: 'long' })) + '</span></h3><div class="hb-list">';
        last = k;
      }
      out += rowFn(c);
    });
    return out + (last !== null ? '</div>' : '');
  };

  /* ------------------------------------------------------------------ the room */
  HB.spotName = function (r, c) { return String.fromCharCode(65 + r) + (c + 1); };
  HB.matGrid = function (room, taken, mine, selected, opts) {
    opts = opts || {};
    taken = taken || []; var blocked = room.blocked || [];
    var cells = '';
    for (var r = 0; r < room.rows; r++) for (var c = 0; c < room.cols; c++) {
      var id = HB.spotName(r, c);
      if (blocked.indexOf(id) >= 0 && !opts.edit) { cells += '<span class="hb-mat gap"></span>'; continue; }
      var cls = opts.edit ? (blocked.indexOf(id) >= 0 ? 'taken' : '') : id === mine ? 'mine' : taken.indexOf(id) >= 0 ? 'taken' : id === selected ? 'sel' : '';
      cells += '<button type="button" class="hb-mat ' + cls + '" data-spot="' + id + '"' + (cls === 'taken' && !opts.edit ? ' disabled aria-label="Mat ' + id + ', taken"' : ' aria-label="Mat ' + id + '"') + '>' + id + '</button>';
    }
    var w = Math.min(46, Math.floor(300 / room.cols));
    return '<div class="hb-room"><div class="hb-front">' + esc(opts.front || 'Teacher') + '</div>' +
      '<div class="hb-mats" style="grid-template-columns:repeat(' + room.cols + ',' + w + 'px)">' + cells + '</div></div>' +
      (opts.edit ? '' : '<div class="hb-room-key"><span><i></i>Free</span><span><i class="t"></i>Taken</span><span><i class="s"></i>Your pick</span></div>');
  };

  /* ------------------------------------------------------------------ booking flow */
  HB.book = function (c, o) {
    o = o || {};
    if (!UI.me) {
      UI.after = '#class/' + c.id;
      UI.toast('Create your free account to book. One account works at every studio.');
      UI.go('auth', 'signup');
      return Promise.resolve(null);
    }
    return UI.api('book_class', c.id, o.passId || null, o.spot || null).then(function (r) {
      HB.booked(r.booking);
      UI.refreshUnread && UI.refreshUnread(true);
      return r.booking;
    }, function (err) {
      var res = err.result || {};
      if (res.need === 'waiver') {
        return HB.waiver(c.studio, res.waiver_text).then(function (ok) { return ok ? HB.book(c, o) : null; });
      }
      if (res.need === 'pass') {
        return HB.shop(c.studio, res.products, c).then(function (p) { return p ? HB.book(c, Object.assign({}, o, { passId: p.id })) : null; });
      }
      UI.toast(err.message, 'error');
      return null;
    });
  };

  HB.waiver = function (studio, text) {
    return new Promise(function (resolve) {
      var done = false;
      var m = UI.modal('<h2>A quick waiver</h2><p class="muted">' + esc(studio.name) + ' asks every new student to sign this once. It takes 20 seconds.</p>' +
        '<div class="ui-note" style="white-space:pre-wrap;max-height:180px;overflow:auto">' + esc(text) + '</div>' +
        '<form class="ui-stack" data-waiver style="margin-top:14px">' +
        '<label class="ui-field"><span>Health notes for your teachers <em>(optional)</em></span><textarea name="health" rows="2" maxlength="600" placeholder="Injuries, pregnancy, anything they should know"></textarea></label>' +
        '<label class="ui-check"><input type="checkbox" name="share" checked> Show my health notes to my teachers on the class list</label>' +
        '<label class="ui-field"><span>Emergency contact <em>(optional)</em></span><input type="text" name="emergency" maxlength="120" placeholder="Name and phone"></label>' +
        '<label class="ui-field"><span>Type your full name to sign</span><input type="text" name="signature" required minlength="3" maxlength="80" value="' + esc(UI.me.name) + '"></label>' +
        '<div class="ui-row end"><button type="button" class="ui-btn ghost" data-close>Not now</button><button class="ui-btn primary" type="submit">' + UI.icon('check') + 'Sign and continue</button></div></form>',
      { onclose: function () { if (!done) resolve(false); } });
      var f = m.el.querySelector('[data-waiver]');
      f.addEventListener('submit', function (e) {
        e.preventDefault();
        var v = UI.formData(f);
        UI.busy(f.querySelector('[type=submit]'), UI.api('sign_waiver', studio.slug, v.signature, v.emergency, v.health, v.share)).then(function () {
          done = true; m.close(); resolve(true);
        });
      });
    });
  };

  /* Choose and get a pass (paid at the studio). products: from the server, with .eligible. */
  HB.shop = function (studio, products, klass) {
    return new Promise(function (resolve) {
      var done = false, pick = null;
      var ok = products.filter(function (p) { return p.eligible; });
      var intro = ok.filter(function (p) { return p.intro_only; })[0];
      pick = intro || ok[0] || null;
      function card(p) {
        var what = p.kind === 'unlimited' || p.credits == null ? 'Unlimited classes' : UI.plural(p.credits, 'class', 'classes');
        return '<button type="button" class="hb-buy' + (pick && pick.id === p.id ? ' on' : '') + '" data-p="' + esc(p.id) + '"' + (p.eligible ? '' : ' disabled') + '>' +
          '<b>' + esc(p.name) + (p.intro_only ? ' <span class="ui-badge clay">First visit</span>' : '') + '</b><span class="price">' + HB.money(p.price) + '</span>' +
          '<small>' + esc(what) + ' · valid ' + UI.plural(p.days, 'day') + (p.about ? ' · ' + esc(p.about) : '') + (p.eligible ? '' : ' · for new students') + '</small></button>';
      }
      var m = UI.modal('<h2>Choose a pass</h2><p class="muted">' + (klass ? 'To book <b>' + esc(klass.title) + '</b>, you need a pass for ' : 'Passes for ') + esc(studio.name) + '.</p>' +
        '<div class="hb-shop" data-shop>' + products.map(card).join('') + '</div>' +
        '<p class="ui-hint" style="margin-top:12px">' + UI.icon('info') + ' Health Booker doesn\'t take card payments yet: you pay the studio at your first visit (card, cash or e-Transfer). No fees on top.</p>' +
        '<div class="ui-row end" style="margin-top:16px"><button class="ui-btn ghost" data-close>Cancel</button><button class="ui-btn primary" data-get' + (pick ? '' : ' disabled') + '>' + UI.icon('ticket') + '<span>Get this pass</span></button></div>',
      { onclose: function () { if (!done) resolve(null); } });
      m.el.addEventListener('click', function (e) {
        var b = e.target.closest('[data-p]');
        if (b && !b.disabled) {
          pick = products.filter(function (p) { return p.id === b.getAttribute('data-p'); })[0];
          m.el.querySelectorAll('[data-p]').forEach(function (x) { x.classList.toggle('on', x === b); });
          m.el.querySelector('[data-get]').disabled = false;
        }
        var g = e.target.closest('[data-get]');
        if (g && pick) {
          UI.busy(g, UI.api('buy_product', pick.id)).then(function (r) {
            done = true; m.close();
            UI.toast(pick.price ? 'Pass added to your wallet. Pay at the desk on your first visit.' : 'Pass added to your wallet.', 'ok');
            resolve(r.pass_);
          });
        }
      });
    });
  };

  HB.booked = function (b) {
    var c = b['class'], wait = b.status === 'waitlist';
    var m = UI.modal('<div class="hb-done ' + HB.acc(c.studio.accent) + '">' +
      (wait ? '<div style="font-size:42px;margin:4px 0 6px">' + UI.icon('clock', 'big') + '</div><h2>You\'re #' + (b.waitlist_pos || 1) + ' on the waitlist</h2>' +
        '<p class="muted">If a mat opens up, we move you in automatically and let you know. Nothing is charged until then.</p>'
        : '<div class="hb-breath" aria-hidden="true"><span data-breath>Breathe in</span></div><h2>You\'re booked</h2><p class="muted">See you on the mat. Take a slow breath while you\'re here.</p>') +
      '<div class="hb-facts"><div>' + UI.icon('calendar') + '<span><b>' + esc(c.title) + '</b> · ' + esc(HB.when(c.start)) + '</span></div>' +
      '<div>' + UI.icon('pin') + '<span>' + esc(c.studio.name) + (c.studio.address ? ', ' + esc(c.studio.address) : '') + '</span></div>' +
      (b.spot ? '<div>' + UI.icon('mat') + '<span>Mat ' + esc(b.spot) + '</span></div>' : '') +
      (b.pass_name ? '<div>' + UI.icon('ticket') + '<span>' + esc(b.pass_name) + '</span></div>' : '') +
      (!wait && b.cancel_by ? '<div>' + UI.icon('info') + '<span>Free to cancel until ' + esc(HB.when(b.cancel_by)) + '</span></div>' : '') + '</div>' +
      '<div class="ui-row" style="justify-content:center"><button class="ui-btn" data-ics>' + UI.icon('download') + 'Add to calendar</button><a class="ui-btn primary" href="#practice" data-go="practice" data-close>My practice</a></div></div>');
    m.el.querySelector('[data-ics]').onclick = function () { HB.ics(c); };
    var lbl = m.el.querySelector('[data-breath]'), i = 0;
    if (lbl) {
      var t = setInterval(function () {
        if (!document.body.contains(lbl)) return clearInterval(t);
        i++; lbl.textContent = i % 2 ? 'Breathe out' : 'Breathe in';
      }, 4000);
    }
  };

  HB.cancel = function (b) {
    var c = b['class'];
    var wait = b.status === 'waitlist';
    var hrs = c.studio ? c.studio.cancel_hours : 12;
    return UI.confirm(wait ? { title: 'Leave the waitlist?', text: 'You won\'t be moved into ' + c.title + ' if a mat opens up.', ok: 'Leave waitlist' }
      : b.late_if_cancel ? { title: 'Late cancel?', text: 'It\'s less than ' + hrs + ' hours before class, so this class still counts against your pass. The studio may forgive it.', ok: 'Cancel anyway', danger: true }
      : { title: 'Cancel this class?', text: 'Your credit goes straight back to your wallet' + (b.grace ? ' (you were moved off the waitlist late, so it\'s free).' : '.'), ok: 'Cancel class', cancel: 'Keep it' })
      .then(function (yes) {
        if (!yes) return false;
        return UI.api('cancel_booking', b.id).then(function (r) {
          UI.toast(r.result === 'late' ? 'Cancelled (late). Your mat goes to the next person waiting.' : r.result === 'left_waitlist' ? 'You left the waitlist.' : 'Cancelled. Your credit is back.', 'ok');
          return true;
        });
      });
  };

  /* ------------------------------------------------------------------ reflections + reviews */
  HB.face = function (n) {
    var mouth = { 1: 'M9 16.5q3-2.5 6 0', 2: 'M9 16q3-1 6 0', 3: 'M9 15.5h6', 4: 'M9 15q3 2 6 0', 5: 'M8.5 14.5q3.5 3.5 7 0' }[n];
    var eyes = n === 5 ? '<path d="M8.5 10.5q1-1 2 0M13.5 10.5q1-1 2 0"/>' : n === 1 ? '<path d="M8.5 10.5h2M13.5 10.5h2"/>' : '<circle cx="9.5" cy="10.3" r=".9" fill="currentColor"/><circle cx="14.5" cy="10.3" r=".9" fill="currentColor"/>';
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="9"/>' + eyes + '<path d="' + mouth + '"/></svg>';
  };
  HB.reflect = function (b) {
    return new Promise(function (resolve) {
      var mood = b.mood || 0, stars = 0, saved = false;
      var m = UI.modal('<h2>How do you feel?</h2><p class="muted">' + esc(b['class'].title) + ' · ' + esc(HB.date(b['class'].start)) + '. Only you see your journal.</p>' +
        '<div class="hb-moods" data-moods>' + HB.MOODS.map(function (x) { return '<button type="button" class="hb-mood' + (mood === x[0] ? ' on' : '') + '" data-mood="' + x[0] + '">' + HB.face(x[0]) + esc(x[1]) + '</button>'; }).join('') + '</div>' +
        '<label class="ui-field" style="margin-top:14px"><span>A note for future you <em>(optional)</em></span><textarea data-note rows="2" maxlength="600" placeholder="What felt good? What was hard?">' + esc(b.note || '') + '</textarea></label>' +
        (b.reviewed ? '' : '<div style="margin-top:16px"><b>Review the class</b> <span class="muted small">(optional, public, first name only)</span><div class="hb-starpick" data-stars>' +
          [1, 2, 3, 4, 5].map(function (i) { return '<button type="button" data-star="' + i + '" aria-label="' + i + ' stars">' + UI.icon('star') + '</button>'; }).join('') + '</div>' +
          '<textarea data-review rows="2" maxlength="800" placeholder="What would you tell a friend about this class?" hidden></textarea></div>') +
        '<div class="ui-row end" style="margin-top:16px"><button class="ui-btn ghost" data-close>Close</button><button class="ui-btn primary" data-save>Save</button></div>',
      { onclose: function () { resolve(saved); } });
      m.el.addEventListener('click', function (e) {
        var md = e.target.closest('[data-mood]');
        if (md) { mood = +md.getAttribute('data-mood'); m.el.querySelectorAll('[data-mood]').forEach(function (x) { x.classList.toggle('on', x === md); }); }
        var st = e.target.closest('[data-star]');
        if (st) {
          stars = +st.getAttribute('data-star');
          m.el.querySelectorAll('[data-star]').forEach(function (x) { x.classList.toggle('on', +x.getAttribute('data-star') <= stars); });
          m.el.querySelector('[data-review]').hidden = false;
        }
        var sv = e.target.closest('[data-save]');
        if (sv) {
          var jobs = [];
          if (mood) jobs.push(UI.api('reflect', b.id, mood, m.el.querySelector('[data-note]').value));
          if (stars) jobs.push(UI.api('review_class', b.id, stars, m.el.querySelector('[data-review]').value));
          if (!jobs.length) { UI.toast('Choose how you feel (or some stars) first.'); return; }
          UI.busy(sv, Promise.all(jobs)).then(function () { saved = true; m.close(); UI.toast(stars ? 'Saved. Thank you for the review!' : 'Saved to your journal.', 'ok'); });
        }
      });
    });
  };

  /* ------------------------------------------------------------------ roster (Teach + Manage) */
  HB.roster = function (classId, onChange) {
    var m = UI.modal('<div data-roster><div class="ui-skel"></div></div>', { wide: true, onclose: function () { if (changed && onChange) onChange(); } });
    var box = m.el.querySelector('[data-roster]'), changed = false;
    function draw(d) {
      var c = d['class'], mgr = d.can_manage;
      var people = d.people.filter(function (p) { return p.status !== 'waitlist'; });
      var waiting = d.people.filter(function (p) { return p.status === 'waitlist'; });
      var inCount = people.filter(function (p) { return p.status === 'checked_in'; }).length;
      var started = new Date(c.start).getTime() < Date.now();
      box.innerHTML = '<h2>' + esc(c.title) + '</h2><p class="muted">' + esc(HB.when(c.start)) + ' · ' + esc(c.teacher ? c.teacher.name : '') + ' · ' +
        '<b>' + inCount + '</b> checked in of ' + c.booked + ' booked · ' + c.capacity + ' mats</p>' +
        (people.length ? '<div class="hb-roster">' + people.map(function (p) {
          var acts = '';
          if (p.status === 'booked' || p.status === 'checked_in' || p.status === 'no_show') {
            acts += '<button class="ui-btn sm ' + (p.status === 'checked_in' ? 'primary' : '') + '" data-att="' + (p.status === 'checked_in' ? 'booked' : 'checked_in') + '">' + UI.icon('check') + (p.status === 'checked_in' ? 'Here' : 'Check in') + '</button>';
            if (started && p.status === 'booked') acts += '<button class="ui-btn sm ghost" data-att="no_show">No-show</button>';
          }
          if (mgr && (p.status === 'late' || p.status === 'no_show')) acts += '<button class="ui-btn sm" data-forgive>' + UI.icon('heart') + 'Forgive</button>';
          if (mgr && p.unpaid && p.pass_id) acts += '<button class="ui-btn sm clay" data-paid="' + esc(p.pass_id) + '">Mark paid</button>';
          var badges = (p.first_visit ? '<span class="hb-leaf" title="First visit">' + UI.icon('leaf') + '</span><span class="ui-badge good">First visit</span>' : '') +
            (p.milestone ? '<span class="ui-badge clay">' + p.visits + 'th class!</span>' : '') +
            (p.status === 'late' ? '<span class="ui-badge warn">Late cancel</span>' : '') + (p.status === 'no_show' ? '<span class="ui-badge bad">No-show</span>' : '') +
            (p.unpaid ? '<span class="ui-badge warn">Unpaid</span>' : '') + (!p.waiver ? '<span class="ui-badge bad">No waiver</span>' : '');
          return '<div class="hb-person' + (p.status === 'checked_in' ? ' in' : '') + '" data-b="' + esc(p.id) + '"><span class="ui-avatar">' + esc(UI.initials(p.name)) + '</span>' +
            '<div style="min-width:0"><div class="name">' + esc(p.name) + ' ' + badges + '</div>' +
            '<div class="sub">' + (p.spot ? 'Mat ' + esc(p.spot) + ' · ' : '') + esc(p.pass || 'Walk-in') + ' · ' + UI.plural(p.visits, 'visit') + '</div>' +
            (p.health ? '<div class="health">' + UI.icon('heart') + '<span>' + esc(p.health) + '</span></div>' : '') + '</div>' +
            '<div class="acts">' + acts + '</div></div>';
        }).join('') + '</div>' : '<div class="ui-empty">' + UI.icon('mat') + '<h3>No one booked yet</h3><p>Bookings show up here as they come in.</p></div>') +
        (waiting.length ? '<h3 style="margin-top:20px">Waitlist</h3><div class="hb-roster">' + waiting.map(function (p, i) {
          return '<div class="hb-person"><span class="ui-avatar">' + (i + 1) + '</span><div><div class="name">' + esc(p.name) + '</div><div class="sub">Joined ' + esc(UI.ago(p.wl_at)) + '</div></div><div></div></div>';
        }).join('') + '</div>' : '') +
        (mgr ? '<form class="ui-row" data-walkin style="margin-top:18px"><input type="text" name="name" placeholder="Walk-in name" maxlength="60" style="flex:1;min-width:140px">' +
          '<input type="email" name="email" placeholder="or their account email" maxlength="120" style="flex:1;min-width:160px"><button class="ui-btn" type="submit">' + UI.icon('plus') + 'Add walk-in</button></form>' : '');
    }
    function load() { return UI.api('roster', classId).then(draw); }
    box.addEventListener('click', function (e) {
      var row = e.target.closest('[data-b]');
      var att = e.target.closest('[data-att]');
      if (att && row) { changed = true; UI.busy(att, UI.api('set_attendance', row.getAttribute('data-b'), att.getAttribute('data-att'))).then(load); return; }
      var fg = e.target.closest('[data-forgive]');
      if (fg && row) { changed = true; UI.busy(fg, UI.api('forgive', row.getAttribute('data-b'))).then(function () { UI.toast('Forgiven: their credit is back.', 'ok'); load(); }); return; }
      var pd = e.target.closest('[data-paid]');
      if (pd) { changed = true; HB.markPaid(pd.getAttribute('data-paid')).then(function (ok) { if (ok) load(); }); }
    });
    box.addEventListener('submit', function (e) {
      if (!e.target.matches('[data-walkin]')) return;
      e.preventDefault();
      var v = UI.formData(e.target);
      changed = true;
      UI.busy(e.target.querySelector('[type=submit]'), UI.api('add_walkin', classId, v.name, v.email)).then(function () { UI.toast('Added and checked in.', 'ok'); load(); });
    });
    load();
    return m;
  };

  HB.markPaid = function (passId) {
    return new Promise(function (resolve) {
      var done = false;
      var m = UI.modal('<h2>Mark as paid</h2><p class="muted">How did they pay?</p><div class="ui-row">' +
        [['card', 'Card'], ['cash', 'Cash'], ['e-transfer', 'e-Transfer'], ['comp', 'On the house']].map(function (x) { return '<button class="ui-btn" data-m="' + x[0] + '">' + x[1] + '</button>'; }).join('') + '</div>',
      { onclose: function () { if (!done) resolve(false); } });
      m.el.addEventListener('click', function (e) {
        var b = e.target.closest('[data-m]');
        if (b) UI.busy(b, UI.api('mark_paid', passId, b.getAttribute('data-m'))).then(function () { done = true; m.close(); UI.toast('Marked paid.', 'ok'); resolve(true); });
      });
    });
  };

  /* ------------------------------------------------------------------ files */
  HB.download = function (name, text, type) {
    var blob = new Blob([text], { type: type || 'text/plain' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  };
  HB.ics = function (c) {
    function stamp(d) { return new Date(d).toISOString().replace(/[-:]/g, '').replace(/\.\d+/, ''); }
    var end = new Date(new Date(c.start).getTime() + c.minutes * 60000);
    var s = c.studio || {};
    var lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Health Booker//EN', 'BEGIN:VEVENT', 'UID:' + c.id.replace(/[^a-z0-9]/gi, '') + '@healthbooker',
      'DTSTAMP:' + stamp(Date.now()), 'DTSTART:' + stamp(c.start), 'DTEND:' + stamp(end),
      'SUMMARY:' + (c.title + ' at ' + (s.name || '')).replace(/[,;]/g, ' '), 'LOCATION:' + ((s.address || s.name || '') + '').replace(/[,;]/g, ' '),
      'DESCRIPTION:' + ('With ' + (c.teacher ? c.teacher.name : '') + '. Booked on Health Booker.').replace(/[,;]/g, ' '),
      'BEGIN:VALARM', 'TRIGGER:-PT1H', 'ACTION:DISPLAY', 'DESCRIPTION:Yoga in an hour', 'END:VALARM', 'END:VEVENT', 'END:VCALENDAR'];
    HB.download((c.title || 'class').replace(/[^a-z0-9]+/gi, '-').toLowerCase() + '.ics', lines.join('\r\n'), 'text/calendar');
  };
  HB.copy = function (text, msg) {
    var done = function () { UI.toast(msg || 'Link copied.', 'ok'); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () { prompt('Copy this link:', text); });
    else prompt('Copy this link:', text);
  };
  HB.link = function (hash) { return location.href.split('#')[0].split('?')[0] + hash; };

  /* Hover tooltips for charts: any element with data-tip="text" inside `root`. */
  HB.tips = function (root) {
    var tip = null;
    function hide() { if (tip) { tip.remove(); tip = null; } }
    root.addEventListener('pointerover', function (e) {
      var t = e.target.closest && e.target.closest('[data-tip]');
      hide();
      if (!t) return;
      tip = document.createElement('div');
      tip.className = 'ui hb-tip'; tip.textContent = t.getAttribute('data-tip');
      document.body.appendChild(tip);
      var r = t.getBoundingClientRect(), w = tip.offsetWidth;
      tip.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left + r.width / 2 - w / 2)) + 'px';
      tip.style.top = Math.max(8, r.top - tip.offsetHeight - 8) + 'px';
    });
    root.addEventListener('pointerout', function (e) { if (!e.relatedTarget || !e.relatedTarget.closest || !e.relatedTarget.closest('[data-tip]')) hide(); });
    window.addEventListener('scroll', hide, { passive: true });
    return hide;
  };

  /* A little line drawing of someone in tree pose, for empty states and the landing page. */
  HB.tree = function (cls) {
    return '<svg class="' + (cls || 'hb-empty-art') + '" viewBox="0 0 120 120" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<circle cx="60" cy="60" r="54" fill="var(--c-brand-soft)" stroke="none"/><circle cx="60" cy="30" r="7"/>' +
      '<path d="M60 38v34M60 72l-1 30M60 72q14 6 6 16q-4 4-6-2"/><path d="M60 46q-10-8-6-22M60 46q10-8 6-22"/><path d="M40 104h40" stroke="var(--c-accent)"/></svg>';
  };
})();

/* ===== _mg.html ===== */
(function () {
  'use strict';
  var esc = UI.esc;
  HB.mg = HB.mg || {};
  var KIND = { intro: 'Intro offer', dropin: 'Drop-in', pack: 'Class pack', unlimited: 'Membership', friend: 'Friend pass', workshop: 'Workshop' };
  function money0(n) { return HB.money(n).replace('Free', '$0'); }

  /* ---------------------------------------------------------------- pricing */
  HB.mg.pricing = function (ctl) {
    var body = ctl.body(), slug = ctl.slug();
    return UI.api('manage_products', slug).then(function (d) {
      body.innerHTML = '<div class="ui-row" style="margin-bottom:14px"><p class="muted" style="margin:0;flex:1">What students can buy. Intro offers only show to people who\'ve never been. Students pay you at the desk; Health Booker takes nothing.</p>' +
        '<button class="ui-btn primary" data-pnew>' + UI.icon('plus') + 'New pass</button></div>' +
        '<div class="mg-prods">' + d.products.map(function (p) {
          return '<div class="ui-card mg-prod' + (p.active ? '' : ' off') + '"><div class="ui-row between"><span class="ui-badge ' + (p.intro_only ? 'clay' : '') + '">' + esc(KIND[p.kind]) + '</span>' + (p.active ? '' : '<span class="ui-badge">Hidden</span>') + '</div>' +
            '<b>' + esc(p.name) + '</b><span class="p">' + HB.money(p.price) + '</span><span class="small muted">' + (p.credits == null ? 'Unlimited' : UI.plural(p.credits, 'class', 'classes')) + ' · ' + UI.plural(p.days, 'day') + '</span>' +
            '<span class="small">' + UI.plural(p.sold, 'sold') .replace('solds', 'sold') + '</span><button class="ui-btn sm" data-pedit="' + esc(p.id) + '" style="justify-self:start">' + UI.icon('edit') + 'Edit</button></div>';
        }).join('') + '</div>';
      function form(p) {
        p = p || { name: '', kind: 'pack', credits: 10, days: 180, price: 0, intro_only: false, about: '', active: true };
        var m = UI.modal('<h2>' + (p.id ? 'Edit pass' : 'New pass') + '</h2><form class="mg-form" data-pform>' +
          '<label class="ui-field full"><span>Name</span><input type="text" name="name" required minlength="3" maxlength="60" value="' + esc(p.name) + '"></label>' +
          '<label class="ui-field"><span>Kind</span><select name="kind">' + d.kinds.map(function (k) { return '<option value="' + k + '"' + (k === p.kind ? ' selected' : '') + '>' + KIND[k] + '</option>'; }).join('') + '</select></label>' +
          '<label class="ui-field"><span>Classes <em>(empty = unlimited)</em></span><input type="number" name="credits" min="1" max="200" value="' + (p.credits == null ? '' : p.credits) + '"></label>' +
          '<label class="ui-field"><span>Valid for (days)</span><input type="number" name="days" min="1" max="730" value="' + p.days + '"></label>' +
          '<label class="ui-field"><span>Price ($)</span><input type="number" name="price" min="0" step="0.5" value="' + p.price + '"></label>' +
          '<label class="ui-field full"><span>One line for students</span><input type="text" name="about" maxlength="200" value="' + esc(p.about) + '"></label>' +
          '<label class="ui-check full"><input type="checkbox" name="intro_only"' + (p.intro_only ? ' checked' : '') + '> First visit only (intro offer)</label>' +
          '<label class="ui-check full"><input type="checkbox" name="active"' + (p.active ? ' checked' : '') + '> On sale</label>' +
          '<div class="full ui-row end"><button type="button" class="ui-btn ghost" data-close>Cancel</button><button class="ui-btn primary" type="submit">Save</button></div></form>');
        var f = m.el.querySelector('[data-pform]');
        f.addEventListener('submit', function (e) {
          e.preventDefault();
          var v = UI.formData(f); v.id = p.id || null; v.credits = v.credits ? +v.credits : null;
          UI.busy(f.querySelector('[type=submit]'), UI.api('save_product', slug, v)).then(function () { m.close(); UI.toast('Saved.', 'ok'); ctl.reload(); });
        });
      }
      body.onclick = function (e) {
        if (e.target.closest('[data-pnew]')) form(null);
        var ed = e.target.closest('[data-pedit]');
        if (ed) form(d.products.filter(function (p) { return p.id === ed.getAttribute('data-pedit'); })[0]);
      };
    });
  };

  /* ---------------------------------------------------------------- team */
  HB.mg.team = function (ctl) {
    var body = ctl.body(), slug = ctl.slug();
    var start = new Date(); start.setDate(1); start.setHours(0, 0, 0, 0);
    return UI.api('team', slug, start.toISOString(), new Date().toISOString()).then(function (d) {
      body.innerHTML = '<div class="ui-row" style="margin-bottom:14px"><p class="muted" style="margin:0;flex:1">Numbers are for this month. Teachers see their own classes, class lists, subs and pay in Teach.</p>' +
        '<button class="ui-btn primary" data-invite>' + UI.icon('plus') + 'Add someone</button></div>' +
        '<div class="mg-staff">' + d.team.map(function (t) {
          return '<div class="ui-card mg-person"><div class="head"><span class="ui-avatar">' + esc(UI.initials(t.name)) + '</span><div style="flex:1;min-width:0"><b>' + esc(t.name) + '</b>' +
            '<div class="small muted" style="overflow-wrap:anywhere">' + esc(t.email) + '</div></div><span class="ui-badge ' + (t.role === 'owner' ? 'brand' : '') + '">' + esc(t.role === 'desk' ? 'Front desk' : t.role[0].toUpperCase() + t.role.slice(1)) + '</span></div>' +
            (t.invited ? '<div class="ui-badge warn" style="justify-self:start">Invited: gets access when they sign in with this email</div>' : '') +
            (t.teaches ? '<div class="nums"><div><b>' + t.classes + '</b><span>classes</span></div><div><b>' + t.avg + '</b><span>avg students</span></div><div><b>' + money0(t.pay) + '</b><span>pay</span></div><div><b>' + (t.rating_n ? t.rating.toFixed(1) : '–') + '</b><span>rating</span></div></div>' +
              '<div class="small muted">Pay: ' + money0(t.pay_base) + ' per class' + (t.pay_per_head ? ' + ' + money0(t.pay_per_head) + ' per student after ' + t.pay_after : '') + (t.subs_covered ? ' · covered ' + UI.plural(t.subs_covered, 'sub') : '') + '</div>' : '<div class="small muted">Doesn\'t teach.</div>') +
            '<div class="ui-row"><button class="ui-btn sm" data-sedit="' + esc(t.id) + '">' + UI.icon('edit') + 'Edit</button>' + (t.role === 'owner' ? '' : '<button class="ui-btn sm ghost danger" data-sremove="' + esc(t.id) + '">Remove</button>') + '</div></div>';
        }).join('') + '</div>' +
        '<div class="hb-section"><h2>Sub requests</h2>' + (d.subs.length ? '<div class="ui-list">' + d.subs.map(function (x) {
          var c = x['class'];
          return '<div class="ui-item"><div class="grow"><b>' + esc(c ? c.title : '') + '</b> · ' + esc(c ? HB.when(c.start) : '') + '<p class="small muted">' + esc(x.from) + (x.reason ? ': "' + esc(x.reason) + '"' : '') + '</p></div>' +
            '<span class="ui-badge ' + (x.status === 'filled' ? 'good' : x.status === 'open' ? 'warn' : '') + '" style="align-self:center">' + (x.status === 'filled' ? 'Covered by ' + esc(x.filled_by) : x.status === 'open' ? 'Open' : 'Withdrawn') + '</span></div>';
        }).join('') + '</div>' : '<p class="muted">No sub requests yet.</p>') + '</div>';
      function form(t) {
        var isNew = !t;
        t = t || { name: '', email: '', role: 'teacher', teaches: true, styles: [], bio: '', pay_base: 40, pay_per_head: 3, pay_after: 8 };
        var styles = ['Vinyasa', 'Hatha', 'Yin', 'Restorative', 'Hot', 'Ashtanga', 'Prenatal', 'Pilates', 'Breathwork', 'Meditation', 'Mobility', 'Kids & family', 'Chair', 'Sound'];
        var m = UI.modal('<h2>' + (isNew ? 'Add to the team' : 'Edit ' + esc(t.name)) + '</h2><form class="mg-form" data-sform>' +
          '<label class="ui-field"><span>Name</span><input type="text" name="name" required minlength="2" maxlength="60" value="' + esc(t.name) + '"></label>' +
          (isNew ? '<label class="ui-field"><span>Email they sign in with</span><input type="email" name="email" required maxlength="120"></label>' : '<div></div>') +
          '<label class="ui-field"><span>Role</span><select name="role"><option value="teacher">Teacher</option><option value="desk"' + (t.role === 'desk' ? ' selected' : '') + '>Front desk</option><option value="owner"' + (t.role === 'owner' ? ' selected' : '') + '>Owner</option></select></label>' +
          '<label class="ui-check" style="align-self:end;padding-bottom:10px"><input type="checkbox" name="teaches"' + (t.teaches ? ' checked' : '') + '> Teaches classes</label>' +
          '<div class="ui-field full"><span>Styles</span><div class="mg-tags">' + styles.map(function (s, i) { return '<label><input type="checkbox" name="sty_' + i + '"' + (t.styles.indexOf(s) >= 0 ? ' checked' : '') + '><span>' + esc(s) + '</span></label>'; }).join('') + '</div></div>' +
          '<label class="ui-field full"><span>Bio <em>(on the studio page)</em></span><textarea name="bio" rows="3" maxlength="600">' + esc(t.bio) + '</textarea></label>' +
          '<label class="ui-field"><span>Pay per class ($)</span><input type="number" name="pay_base" min="0" step="1" value="' + t.pay_base + '"></label>' +
          '<label class="ui-field"><span>Plus per student ($)</span><input type="number" name="pay_per_head" min="0" step="0.5" value="' + t.pay_per_head + '"></label>' +
          '<label class="ui-field"><span>...after this many students</span><input type="number" name="pay_after" min="0" max="100" value="' + t.pay_after + '"></label>' +
          '<p class="ui-hint" style="align-self:end" data-payex></p>' +
          '<div class="full ui-row end"><button type="button" class="ui-btn ghost" data-close>Cancel</button><button class="ui-btn primary" type="submit">' + (isNew ? 'Add' : 'Save') + '</button></div></form>', { wide: true });
        var f = m.el.querySelector('[data-sform]');
        function ex() {
          var b = +f.pay_base.value || 0, h = +f.pay_per_head.value || 0, a = +f.pay_after.value || 0;
          f.querySelector('[data-payex]').textContent = 'A class of 12 pays ' + money0(b + h * Math.max(0, 12 - a)) + '; an empty one pays ' + money0(b) + '.';
        }
        f.addEventListener('input', ex); ex();
        f.addEventListener('submit', function (e) {
          e.preventDefault();
          var v = UI.formData(f); v.id = t.id || null; v.styles = styles.filter(function (s, i) { return v['sty_' + i]; });
          UI.busy(f.querySelector('[type=submit]'), UI.api('save_staff', slug, v)).then(function (r) {
            m.close(); UI.toast(r.invited ? 'Invited. They get access when they sign in with that email.' : 'Saved.', 'ok'); ctl.reload();
          });
        });
      }
      body.onclick = function (e) {
        if (e.target.closest('[data-invite]')) form(null);
        var ed = e.target.closest('[data-sedit]');
        if (ed) form(d.team.filter(function (t) { return t.id === ed.getAttribute('data-sedit'); })[0]);
        var rm = e.target.closest('[data-sremove]');
        if (rm) UI.confirm({ title: 'Remove from the team?', text: 'They lose access to this studio. Their past classes stay in your records.', ok: 'Remove', danger: true }).then(function (y) {
          if (y) UI.api('remove_staff', rm.getAttribute('data-sremove')).then(function () { UI.toast('Removed.'); ctl.reload(); });
        });
      };
    });
  };

  /* ---------------------------------------------------------------- insights */
  var insDays = 28;
  HB.mg.insights = function (ctl) {
    var body = ctl.body(), slug = ctl.slug();
    return UI.api('insights', slug, insDays).then(function (d) {
      // revenue per day (local days)
      var days = [], maxRev = 0;
      for (var i = d.days - 1; i >= 0; i--) {
        var day = HB.addDays(HB.startOfDay(), -i), k = HB.dayKey(day), v = 0;
        Object.keys(d.daily).forEach(function (x) { if (x === k) v += d.daily[x]; });
        days.push([day, v]); maxRev = Math.max(maxRev, v);
      }
      // fill by weekday x hour (6..21)
      var cells = {}, hours = [];
      for (var h = 6; h < 22; h++) hours.push(h);
      d.heat.forEach(function (x) {
        var dt = new Date(x[0]), key = ((dt.getDay() + 6) % 7) + '-' + dt.getHours();
        (cells[key] = cells[key] || []).push(x[1]);
      });
      var wd = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      var grid = wd.map(function (name, w) {
        return '<div class="r"><span>' + name + '</span>' + hours.map(function (hh) {
          var arr = cells[w + '-' + hh];
          if (!arr) return '<i></i>';
          var f = arr.reduce(function (a, b) { return a + b; }, 0) / arr.length;
          return '<i style="background:color-mix(in srgb, var(--c-brand) ' + Math.round(20 + f * 80) + '%, var(--c-surface-2))" data-tip="' + esc(name + ' ' + hh + ':00 · ' + Math.round(f * 100) + '% full on average (' + UI.plural(arr.length, 'class', 'classes') + ')') + '"></i>';
        }).join('') + '</div>';
      }).join('') + '<div class="r"><span></span>' + hours.map(function (hh) { return '<span style="text-align:center">' + (hh % 3 === 0 ? hh : '') + '</span>'; }).join('') + '</div>';
      var rk = Object.keys(d.revenue).sort(function (a, b) { return d.revenue[b] - d.revenue[a]; });
      var rmax = d.revenue[rk[0]] || 1;
      var f = d.funnel, fmax = f.started || 1;
      var moodWord = d.mood ? HB.MOODS[Math.round(d.mood) - 1][1] : '';
      body.innerHTML = '<div class="ui-row" style="margin-bottom:14px"><div class="ui-seg">' + [[7, '7 days'], [28, '4 weeks'], [90, '3 months']].map(function (x) {
          return '<button data-range="' + x[0] + '" class="' + (insDays === x[0] ? 'on' : '') + '">' + x[1] + '</button>'; }).join('') + '</div></div>' +
        '<div class="hb-kpis">' +
          '<div class="hb-kpi"><b>' + d.visits + '</b><span>visits</span><small>' + UI.plural(d.classes, 'class', 'classes') + '</small></div>' +
          '<div class="hb-kpi"><b>' + d.fill + '%</b><span>average fill</span></div>' +
          '<div class="hb-kpi"><b>' + money0(d.revenue_total) + '</b><span>passes sold</span><small>Paid to you directly, no commission</small></div>' +
          '<div class="hb-kpi"><b>' + d.no_show_rate + '%</b><span>no-shows</span><small>' + d.late + ' late cancels</small></div>' +
          '<div class="hb-kpi"><b>' + d.clients.new + '</b><span>new students</span><small>' + d.clients.members + ' members · ' + d.clients.drifting + ' drifting</small></div>' +
          '<div class="hb-kpi"><b>' + (d.mood ? esc(moodWord) : '–') + '</b><span>how students leave</span><small>' + (d.mood_n ? 'From ' + UI.plural(d.mood_n, 'reflection') : 'No reflections yet') + '</small></div></div>' +
        '<div class="mg-ins">' +
          '<div class="ui-card"><h3>Passes sold per day</h3><p class="sub">Total ' + money0(d.revenue_total) + '. Hover a bar for the day.</p><div class="hb-cols">' + days.map(function (x) {
            return '<i style="height:' + (maxRev ? Math.max(1.5, x[1] / maxRev * 100) : 1.5) + '%" data-tip="' + esc(x[0].toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' }) + ': ' + money0(x[1])) + '"></i>';
          }).join('') + '</div><div class="hb-axis"><span>' + esc(days[0][0].toLocaleDateString(undefined, { day: 'numeric', month: 'short' })) + '</span><span>Today</span></div></div>' +
          '<div class="ui-card"><h3>By kind of pass</h3><p class="sub">Where the money comes from.</p><div class="hb-hbars">' + (rk.length ? rk.map(function (k) {
            return '<div class="hb-hbar"><span>' + esc(KIND[k] || k) + '</span><div class="hb-bar"><i style="width:' + Math.round(d.revenue[k] / rmax * 100) + '%"></i></div><b>' + money0(d.revenue[k]) + '</b></div>';
          }).join('') : '<p class="muted">No sales in this period.</p>') + '</div></div>' +
          '<div class="ui-card"><h3>When classes fill up</h3><p class="sub">Average fill by day and hour. Darker = fuller.</p><div class="mg-grid">' + grid + '</div></div>' +
          '<div class="ui-card"><h3>Intro offers that stick</h3><p class="sub">Students who started with an intro or friend pass (last ' + Math.max(d.days, 60) + ' days).</p><div class="hb-hbars">' +
            [['Started', f.started], ['Came back', f.second], ['Bought a pack or membership', f.converted]].map(function (x) {
              return '<div class="hb-hbar"><span>' + esc(x[0]) + '</span><div class="hb-bar"><i style="width:' + Math.round(x[1] / fmax * 100) + '%"></i></div><b>' + x[1] + (x[0] !== 'Started' && f.started ? ' <span class="muted small">' + Math.round(x[1] / f.started * 100) + '%</span>' : '') + '</b></div>';
            }).join('') + '</div><p class="small muted" style="margin:14px 0 0">' + UI.icon('gift') + ' Friend passes: ' + d.friend.sent + ' shared, ' + d.friend.claimed + ' claimed.</p></div>' +
          '<div class="ui-card"><h3>Classes people love</h3><p class="sub">Ranked by average fill.</p><table class="mg-table"><thead><tr><th>Class</th><th class="n">Avg</th><th class="n">Fill</th></tr></thead><tbody>' + d.top.map(function (t) {
            return '<tr><td>' + esc(t.title) + ' <span class="muted small">×' + t.classes + '</span></td><td class="n">' + t.avg + '</td><td class="n">' + t.fill + '%<span class="hb-bar"><i style="width:' + Math.min(100, t.fill) + '%"></i></span></td></tr>';
          }).join('') + '</tbody></table></div>' +
          '<div class="ui-card"><h3>Teachers</h3><p class="sub">Classes taught and average students in this period.</p><table class="mg-table"><thead><tr><th>Teacher</th><th class="n">Classes</th><th class="n">Avg</th><th class="n">Rating</th></tr></thead><tbody>' + d.teachers.map(function (t) {
            return '<tr><td>' + esc(t.name) + '</td><td class="n">' + t.classes + '</td><td class="n">' + t.avg + '</td><td class="n">' + (t.rating ? t.rating.toFixed(1) : '–') + '</td></tr>';
          }).join('') + '</tbody></table></div>' +
        '</div>';
      body.onclick = function (e) {
        var r = e.target.closest('[data-range]');
        if (r) { insDays = +r.getAttribute('data-range'); ctl.reload(); }
      };
    });
  };

  /* ---------------------------------------------------------------- reviews */
  HB.mg.reviews = function (ctl) {
    var body = ctl.body(), slug = ctl.slug();
    return UI.api('manage_reviews', slug).then(function (d) {
      body.innerHTML = '<p class="muted">' + (d.rating_n ? HB.rating(d.rating, d.rating_n) + ' · ' : '') + 'Only people who came to a class can review it. Reply publicly, or hide a review that breaks the rules (abuse, personal details); hidden reviews don\'t count.</p>' +
        (d.reviews.length ? '<div class="mg-rev">' + d.reviews.map(function (r) {
          return '<div class="ui-card' + (r.hidden ? '" style="opacity:.6' : '') + '" data-rid="' + esc(r.id) + '"><div class="ui-row between">' + HB.stars(r.stars) + '<span class="small muted">' + esc(r.who) + ' · ' + esc(r['class']) + ' · ' + esc(UI.ago(r.created)) + '</span></div>' +
            '<p style="margin:8px 0 10px">' + esc(r.text || '(no text)') + '</p><textarea data-reply placeholder="Write a public reply" maxlength="600">' + esc(r.reply) + '</textarea>' +
            '<div class="ui-row" style="margin-top:8px"><button class="ui-btn sm primary" data-savereply>Save reply</button><span class="ui-spacer"></span><button class="ui-btn sm ghost" data-hide="' + (r.hidden ? '0' : '1') + '">' + (r.hidden ? 'Show again' : 'Hide') + '</button></div></div>';
        }).join('') + '</div>' : '<div class="ui-empty">' + UI.icon('star') + '<h3>No reviews yet</h3></div>');
      body.onclick = function (e) {
        var card = e.target.closest('[data-rid]');
        if (!card) return;
        var sv = e.target.closest('[data-savereply]');
        if (sv) UI.busy(sv, UI.api('reply_review', card.getAttribute('data-rid'), card.querySelector('[data-reply]').value)).then(function () { UI.toast('Reply saved.', 'ok'); });
        var hd = e.target.closest('[data-hide]');
        if (hd) UI.api('hide_review', card.getAttribute('data-rid'), hd.getAttribute('data-hide') === '1').then(function () { ctl.reload(); });
      };
    });
  };

  /* ---------------------------------------------------------------- settings */
  HB.mg.settings = function (ctl) {
    var body = ctl.body(), slug = ctl.slug();
    return UI.api('manage_settings', slug).then(function (d) {
      var s = d.studio, rooms = d.rooms.map(function (r) { return Object.assign({}, r, { blocked: r.blocked.slice() }); });
      function roomCard(r, i) {
        return '<div class="ui-card mg-room" data-room="' + i + '"><div class="mg-form" style="grid-template-columns:2fr 1fr 1fr"><label class="ui-field"><span>Room</span><input type="text" data-rn value="' + esc(r.name) + '" maxlength="40"></label>' +
          '<label class="ui-field"><span>Rows</span><input type="number" data-rr min="1" max="10" value="' + r.rows + '"></label><label class="ui-field"><span>Per row</span><input type="number" data-rc min="1" max="10" value="' + r.cols + '"></label></div>' +
          '<p class="small muted" style="margin:0">Tap a mat to block it (a pillar, the door). ' + (r.rows * r.cols - r.blocked.length) + ' mats.</p>' +
          HB.matGrid(r, [], null, null, { edit: true }) + '<div class="ui-row end"><button class="ui-btn sm primary" data-saveroom>Save room</button></div></div>';
      }
      body.innerHTML = '<div class="mg-set"><form class="ui-card mg-form" data-studio>' +
          '<h3 class="full" style="margin:0">Studio profile</h3>' +
          '<label class="ui-field"><span>Name</span><input type="text" name="name" required minlength="3" maxlength="60" value="' + esc(s.name) + '"></label>' +
          '<label class="ui-field"><span>Tagline</span><input type="text" name="tagline" maxlength="90" value="' + esc(s.tagline) + '"></label>' +
          '<label class="ui-field"><span>Neighbourhood</span><input type="text" name="neighbourhood" maxlength="60" value="' + esc(s.neighbourhood) + '"></label>' +
          '<label class="ui-field"><span>City</span><input type="text" name="city" maxlength="60" value="' + esc(s.city) + '"></label>' +
          '<label class="ui-field full"><span>Address</span><input type="text" name="address" maxlength="120" value="' + esc(s.address) + '"></label>' +
          '<label class="ui-field full"><span>About</span><textarea name="about" rows="4" maxlength="1500">' + esc(s.about) + '</textarea></label>' +
          '<div class="ui-field full"><span>Styles</span><div class="mg-tags">' + d.styles.map(function (x, i) { return '<label><input type="checkbox" name="sty_' + i + '"' + (s.styles.indexOf(x) >= 0 ? ' checked' : '') + '><span>' + esc(x) + '</span></label>'; }).join('') + '</div></div>' +
          '<label class="ui-field full"><span>Amenities <em>(comma separated)</em></span><input type="text" name="amenities" value="' + esc(s.amenities.join(', ')) + '"></label>' +
          '<label class="ui-field"><span>Languages <em>(comma separated)</em></span><input type="text" name="languages" value="' + esc(s.languages.join(', ')) + '"></label>' +
          '<label class="ui-field"><span>Free cancellation until (hours before class)</span><input type="number" name="cancel_hours" min="0" max="72" value="' + s.cancel_hours + '"></label>' +
          '<div class="ui-field full"><span>Colour</span><div class="op-acc">' + d.accents.map(function (k) { return '<label class="' + HB.acc(k) + '" title="' + k + '"><input type="radio" name="accent" value="' + k + '"' + (k === s.accent ? ' checked' : '') + '><span></span></label>'; }).join('') + '</div></div>' +
          '<label class="ui-field full"><span>Waiver new students sign</span><textarea name="waiver_text" rows="4" maxlength="2000">' + esc(s.waiver_text) + '</textarea></label>' +
          '<div class="full ui-row end"><button class="ui-btn primary" type="submit">' + UI.icon('check') + 'Save profile</button></div></form>' +
        '<div class="ui-stack"><div class="ui-card mg-links-card"><h3>Share and run</h3>' +
          '<div class="ui-row"><button class="ui-btn sm block" data-cp="' + esc(HB.link('#studio/' + slug + '/solo')) + '">' + UI.icon('copy') + 'Copy your direct booking link</button></div>' +
          '<p class="small muted">Shows only your studio: put it on Instagram and your website.</p>' +
          '<div class="ui-row"><button class="ui-btn sm block" data-cp="' + esc(HB.link('#studio/' + slug)) + '">' + UI.icon('copy') + 'Copy your marketplace page link</button></div>' +
          '<div class="ui-row"><a class="ui-btn sm block" href="#kiosk/' + esc(slug) + '" data-go="kiosk/' + esc(slug) + '">' + UI.icon('tablet') + 'Open the check-in kiosk</a></div></div>' +
          '<div class="ui-card"><h3>Your data</h3><p class="small muted">Download everything, any day, free. No lock-in.</p><div class="ui-stack">' +
            [['clients', 'Clients'], ['bookings', 'Bookings'], ['passes', 'Passes and payments']].map(function (x) { return '<button class="ui-btn sm block" data-export="' + x[0] + '">' + UI.icon('download') + esc(x[1]) + ' (CSV)</button>'; }).join('') + '</div></div></div></div>' +
        '<div class="hb-section"><div class="ui-row between"><h2 style="margin:0">Rooms</h2><button class="ui-btn sm" data-addroom>' + UI.icon('plus') + 'Add a room</button></div><div class="mg-rooms" data-rooms>' + rooms.map(roomCard).join('') + '</div></div>';
      var form = body.querySelector('[data-studio]');
      form.onsubmit = function (e) {
        e.preventDefault();
        var v = UI.formData(form);
        v.styles = d.styles.filter(function (x, i) { return v['sty_' + i]; });
        v.amenities = v.amenities.split(',').map(function (x) { return x.trim(); }).filter(Boolean);
        v.languages = v.languages.split(',').map(function (x) { return x.trim(); }).filter(Boolean);
        v.cancel_hours = +v.cancel_hours;
        UI.busy(form.querySelector('[type=submit]'), UI.api('save_studio', slug, v)).then(function () { UI.toast('Saved.', 'ok'); });
      };
      function redrawRoom(i) {
        var card = body.querySelector('[data-room="' + i + '"]');
        card.outerHTML = roomCard(rooms[i], i);
      }
      body.onclick = function (e) {
        var cp = e.target.closest('[data-cp]');
        if (cp) { HB.copy(cp.getAttribute('data-cp')); return; }
        if (e.target.closest('[data-addroom]')) {
          rooms.push({ id: null, name: 'Room ' + (rooms.length + 1), rows: 3, cols: 4, blocked: [] });
          body.querySelector('[data-rooms]').insertAdjacentHTML('beforeend', roomCard(rooms[rooms.length - 1], rooms.length - 1));
          return;
        }
        var card = e.target.closest('[data-room]');
        if (!card) return;
        var i = +card.getAttribute('data-room'), r = rooms[i];
        var mat = e.target.closest('[data-spot]');
        if (mat) {
          var id = mat.getAttribute('data-spot'), k = r.blocked.indexOf(id);
          if (k >= 0) r.blocked.splice(k, 1); else r.blocked.push(id);
          r.name = card.querySelector('[data-rn]').value;
          redrawRoom(i); return;
        }
        var sv = e.target.closest('[data-saveroom]');
        if (sv) {
          r.name = card.querySelector('[data-rn]').value; r.rows = +card.querySelector('[data-rr]').value; r.cols = +card.querySelector('[data-rc]').value;
          UI.busy(sv, UI.api('save_room', slug, r)).then(function () { UI.toast('Room saved.', 'ok'); ctl.reload(); });
        }
      };
      body.oninput = function (e) {
        var card = e.target.closest('[data-room]');
        if (card && (e.target.matches('[data-rr]') || e.target.matches('[data-rc]'))) {
          var i = +card.getAttribute('data-room');
          rooms[i].rows = Math.max(1, Math.min(10, +card.querySelector('[data-rr]').value || 1));
          rooms[i].cols = Math.max(1, Math.min(10, +card.querySelector('[data-rc]').value || 1));
          rooms[i].name = card.querySelector('[data-rn]').value;
          var focus = e.target.matches('[data-rr]') ? '[data-rr]' : '[data-rc]';
          redrawRoom(i);
          var el = body.querySelector('[data-room="' + i + '"] ' + focus); el.focus();
        }
      };
    });
  };
})();

/* ===== admin.html ===== */
(function () {
  var esc = UI.esc;
  var TABS = [['overview', 'Overview', 'grid'], ['studios', 'Studios', 'door'], ['feedback', 'Feedback', 'inbox'], ['users', 'Users', 'users'], ['demo', 'Demo data', 'database']];

  UI.page('admin', { title: 'Admin', auth: 'admin' }, function (view, ctx) {
    var tab = TABS.some(function (t) { return t[0] === ctx.args[0]; }) ? ctx.args[0] : 'overview';
    var fbFilter = 'new';
    view.innerHTML = '<div class="ui-wrap"><div class="ui-page-head"><div><h1>Admin</h1><p class="muted">Only admins see this page.</p></div></div>' +
      '<nav class="ui-tabs">' + TABS.map(function (t) {
        return '<a href="#admin/' + t[0] + '" class="' + (t[0] === tab ? 'on' : '') + '">' + UI.icon(t[2]) + t[1] + '</a>';
      }).join('') + '</nav><div data-body><div class="ui-skel"></div></div></div>';
    var body = view.querySelector('[data-body]');

    function overview() {
      return UI.api('admin_overview').then(function (d) {
        var stat = function (n, label, go) { return '<a class="ui-card ui-stat" href="#admin/' + go + '" style="text-decoration:none;color:inherit"><b>' + n + '</b><span>' + label + '</span></a>'; };
        body.innerHTML = '<div class="ad-stats">' + stat(d.users, 'people signed up', 'users') + stat(d.admins, UI.plural(d.admins, 'admin').replace(/^\d+ /, ''), 'users') +
          stat(d.feedback_new, 'new feedback', 'feedback') + stat(d.studios, 'live studios', 'studios') + stat(d.studios_review, 'waiting for review', 'studios') +
          stat(d.classes_week, 'classes in the next 7 days', 'studios') + stat(d.bookings_week, 'bookings this week', 'overview') + '</div>' +
          '<p class="muted small" style="margin-top:18px">Demo data is <b>' + esc(d.demo.state) + '</b> (' + d.demo.counts.users + ' demo people). Manage it in the Demo data tab.</p>';
      });
    }

    function feedback() {
      return UI.api('list_feedback', null).then(function (d) {
        var items = d.items.filter(function (i) { return fbFilter === 'all' || i.status === fbFilter; });
        body.innerHTML = '<div class="ui-row" style="margin-bottom:16px"><div class="ui-seg">' + [['new', 'New'], ['read', 'Read'], ['done', 'Done'], ['all', 'All']].map(function (f) {
          var n = f[0] === 'all' ? d.items.length : d.counts[f[0]];
          return '<button data-filter="' + f[0] + '" class="' + (fbFilter === f[0] ? 'on' : '') + '">' + f[1] + ' (' + n + ')</button>';
        }).join('') + '</div></div>' +
          (items.length ? '<div class="ad-fb">' + items.map(function (i) {
            var c = i.context || {};
            return '<div class="ui-item" data-id="' + esc(i.id) + '"><div class="meta"><span class="ui-badge ' + (i.kind === 'bug' ? 'bad' : i.kind === 'idea' ? 'brand' : '') + '">' + esc(i.kind_label) + '</span>' +
              '<b>' + esc(i.name) + '</b>' + (i.email ? '<a href="mailto:' + esc(i.email) + '">' + esc(i.email) + '</a>' : '') + '<span>' + esc(UI.fmtDateTime(i.created)) + '</span></div>' +
              '<p class="msg">' + esc(i.message) + '</p>' +
              '<div class="ctx">' + esc([c.page, c.screen, c.theme, c.browser].filter(Boolean).join(' · ')) + '</div>' +
              '<textarea data-note placeholder="Private note (only admins see it)">' + esc(i.note) + '</textarea>' +
              '<div class="ui-row" style="margin-top:10px">' + ['new', 'read', 'done'].map(function (s) {
                return '<button class="ui-btn sm' + (i.status === s ? ' primary' : '') + '" data-status="' + s + '">' + s[0].toUpperCase() + s.slice(1) + '</button>';
              }).join('') + '<span class="ui-spacer"></span><button class="ui-btn sm danger" data-del-fb>' + UI.icon('trash') + 'Delete</button></div></div>';
          }).join('') + '</div>'
            : '<div class="ui-empty">' + UI.icon('inbox') + '<h3>No ' + (fbFilter === 'all' ? '' : fbFilter + ' ') + 'messages</h3><p>Messages from the "Send feedback" form show up here.</p></div>');
      });
    }

    function users(query) {
      return UI.api('list_users', query || null).then(function (d) {
        body.innerHTML = '<form class="ui-row" data-search style="margin-bottom:14px"><input type="search" name="q" placeholder="Search by name or email" value="' + esc(query || '') + '" style="max-width:360px">' +
          '<button class="ui-btn" type="submit">' + UI.icon('search') + 'Search</button><span class="muted small">' + UI.plural(d.total, 'person', 'people') + '</span></form>' +
          '<table class="ad-users"><thead><tr><th>Name</th><th>Email</th><th>Joined</th><th>Admin</th><th>Active</th></tr></thead><tbody>' +
          d.users.map(function (u) {
            return '<tr data-id="' + esc(u.id) + '"><td><b>' + esc(u.name) + '</b></td><td class="email">' + esc(u.email) + '</td><td class="joined muted">' + esc(UI.fmtDate(u.joined)) + '</td>' +
              '<td><label class="ui-check"><input type="checkbox" data-admin' + (u.is_admin ? ' checked' : '') + '> Admin</label></td>' +
              '<td><label class="ui-check"><input type="checkbox" data-enabled' + (u.enabled ? ' checked' : '') + '> Active</label></td></tr>';
          }).join('') + '</tbody></table>';
      });
    }

    function demo() {
      return UI.api('admin_overview').then(function (d) {
        var c = d.demo.counts;
        body.innerHTML = '<div class="ui-card ui-narrow" style="margin:0"><h3>Demo data</h3>' +
          '<p class="muted">Example people and content, so the app never looks empty for the first visitors. Demo rows are flagged, so removing them never touches real data. Once removed, it stays removed until you load it again.</p>' +
          '<p>Status: <b>' + esc(d.demo.state) + '</b> · ' + Object.keys(c).map(function (k) { return c[k] + ' ' + esc(k); }).join(', ') + '</p>' +
          '<div class="ui-row"><button class="ui-btn primary" data-demo="load">' + UI.icon('refresh') + (d.demo.state === 'loaded' ? 'Reload demo data' : 'Load demo data') + '</button>' +
          '<button class="ui-btn danger" data-demo="remove">' + UI.icon('trash') + 'Remove demo data</button></div></div>';
      });
    }

    function studios() {
      return UI.api('admin_studios').then(function (d) {
        body.innerHTML = '<p class="muted">New studios start in review: check they look like a real studio, then publish. Featured studios come first on Discover.</p>' +
          '<div class="ui-list">' + d.studios.map(function (s) {
            return '<div class="ui-item ' + HB.acc(s.accent) + '" data-slug="' + esc(s.slug) + '" style="flex-wrap:wrap"><span class="hb-dot" style="width:14px;height:14px;margin-top:6px"></span><div class="grow" style="min-width:200px">' +
              '<h3><a href="#studio/' + esc(s.slug) + '" data-go="studio/' + esc(s.slug) + '">' + esc(s.name) + '</a>' + (s.demo ? ' <span class="ui-badge">Demo</span>' : '') + '</h3>' +
              '<p class="small muted">' + esc(s.neighbourhood) + ' · ' + esc(s.tagline) + '</p><p class="small muted">Owner: ' + esc(s.owner) + (s.owner_email ? ' (' + esc(s.owner_email) + ')' : '') + ' · ' + s.classes + ' upcoming classes · added ' + esc(UI.fmtDate(s.created)) + '</p></div>' +
              '<div class="ui-row"><select data-status style="width:auto">' + [['live', 'Live'], ['review', 'In review'], ['paused', 'Paused']].map(function (o) {
                return '<option value="' + o[0] + '"' + (s.status === o[0] ? ' selected' : '') + '>' + o[1] + '</option>'; }).join('') + '</select>' +
              '<label class="ui-check"><input type="checkbox" data-featured' + (s.featured ? ' checked' : '') + '> Featured</label>' +
              '<a class="ui-btn sm" href="#manage/' + esc(s.slug) + '" data-go="manage/' + esc(s.slug) + '">Manage</a></div></div>';
          }).join('') + '</div>';
      });
    }

    var DRAW = { overview: overview, studios: studios, feedback: feedback, users: users, demo: demo };

    view.addEventListener('click', function (e) {
      var f = e.target.closest('[data-filter]');
      if (f) { fbFilter = f.getAttribute('data-filter'); feedback(); return; }
      var st = e.target.closest('[data-status]');
      if (st) {
        var card = st.closest('[data-id]');
        UI.api('set_feedback_status', card.getAttribute('data-id'), st.getAttribute('data-status'), card.querySelector('[data-note]').value).then(function () { UI.toast('Saved', 'ok'); feedback(); });
        return;
      }
      var del = e.target.closest('[data-del-fb]');
      if (del) {
        UI.confirm({ title: 'Delete this message?', ok: 'Delete', danger: true }).then(function (yes) {
          if (yes) UI.api('delete_feedback', del.closest('[data-id]').getAttribute('data-id')).then(feedback);
        });
        return;
      }
      var dm = e.target.closest('[data-demo]');
      if (dm) {
        var load = dm.getAttribute('data-demo') === 'load';
        UI.confirm({ title: load ? 'Load the demo data?' : 'Remove the demo data?', text: load ? 'Demo people and content are added (any old demo rows are replaced).' : 'Every demo row is deleted. Real data stays.', ok: load ? 'Load' : 'Remove', danger: !load })
          .then(function (yes) { if (yes) UI.busy(dm, UI.api(load ? 'demo_load' : 'demo_remove')).then(function () { UI.toast('Done', 'ok'); demo(); }); });
      }
    });
    view.addEventListener('change', function (e) {
      var st = e.target.closest('[data-slug]');
      if (st && (e.target.matches('[data-status]') || e.target.matches('[data-featured]'))) {
        var slug = st.getAttribute('data-slug');
        var call = e.target.matches('[data-status]') ? UI.api('admin_set_studio', slug, e.target.value, null) : UI.api('admin_set_studio', slug, null, e.target.checked);
        call.then(function () { UI.toast('Saved', 'ok'); });
        return;
      }
      var row = e.target.closest('tr[data-id]');
      if (!row) return;
      var id = row.getAttribute('data-id'), box = e.target;
      var fn = box.hasAttribute('data-admin') ? 'set_admin' : box.hasAttribute('data-enabled') ? 'set_enabled' : null;
      if (fn) UI.api(fn, id, box.checked).then(function () { UI.toast('Saved', 'ok'); }, function (err) { box.checked = !box.checked; UI.toast(err.message, 'error'); });
    });
    view.addEventListener('submit', function (e) {
      if (e.target.matches('[data-search]')) { e.preventDefault(); users(UI.formData(e.target).q); }
    });
    return DRAW[tab]();
  });
})();

/* ===== auth.html ===== */
(function () {
  var esc = UI.esc;
  function pw(name, auto) {
    return '<div class="au-pw"><input type="password" name="' + name + '" autocomplete="' + auto + '" required minlength="8">' +
      '<button type="button" data-show>Show</button></div>';
  }
  UI.page('auth', { title: 'Sign in', auth: 'guest' }, function (view, ctx) {
    var mode = ['signup', 'reset'].indexOf(ctx.args[0]) >= 0 ? ctx.args[0] : 'login';
    function draw(msg, isErr) {
      var heading = { login: 'Welcome back', signup: 'Create your account', reset: 'Reset your password' }[mode];
      var sub = { login: 'Sign in to continue to ' + esc(UI.config.name) + '.', signup: 'It\'s free and takes a few seconds.',
        reset: 'We\'ll email you a link to choose a new password.' }[mode];
      view.innerHTML = '<div class="au-wrap"><div class="ui-card au-card">' +
        '<h1>' + heading + '</h1><p class="muted">' + sub + '</p>' +
        (mode !== 'reset' ? '<div class="ui-seg" role="tablist"><button type="button" data-mode="login" class="' + (mode === 'login' ? 'on' : '') + '">Sign in</button>' +
          '<button type="button" data-mode="signup" class="' + (mode === 'signup' ? 'on' : '') + '">Create account</button></div>' : '<div style="height:14px"></div>') +
        '<form class="ui-stack" data-form="' + mode + '" novalidate>' +
        (mode === 'signup' ? '<label class="ui-field"><span>Your name</span><input type="text" name="name" autocomplete="name" required maxlength="60"></label>' : '') +
        '<label class="ui-field"><span>Email</span><input type="email" name="email" autocomplete="email" required></label>' +
        (mode === 'login' ? '<label class="ui-field"><span>Password</span>' + pw('password', 'current-password') + '</label>' : '') +
        (mode === 'signup' ? '<label class="ui-field"><span>Password <em>(at least 8 characters)</em></span>' + pw('password', 'new-password') + '</label>' +
          (window.LegalKit ? '<div>' + LegalKit.consentField() + '</div>' : '') : '') +
        '<div data-msg role="alert"' + (msg ? ' class="' + (isErr ? 'ui-error' : 'ui-note') + '">' + esc(msg) : ' hidden>') + '</div>' +
        '<button class="ui-btn primary block" type="submit">' + { login: 'Sign in', signup: 'Create account', reset: 'Send the link' }[mode] + '</button></form>' +
        '<div class="au-links">' + (mode === 'login' ? '<a data-mode="reset">Forgot your password?</a>' : '<a data-mode="login">' + UI.icon('back') + ' Back to sign in</a>') +
        '<a href="#landing" data-go="landing">About ' + esc(UI.config.name) + '</a></div></div></div>';
      var first = view.querySelector('input');
      if (first && !msg) first.focus();
    }
    view.addEventListener('click', function (e) {
      var m = e.target.closest('[data-mode]');
      if (m) { e.preventDefault(); mode = m.getAttribute('data-mode'); history.replaceState(null, '', '#auth' + (mode === 'login' ? '' : '/' + mode)); draw(); return; }
      var s = e.target.closest('[data-show]');
      if (s) { var i = s.parentNode.querySelector('input'); i.type = i.type === 'password' ? 'text' : 'password'; s.textContent = i.type === 'password' ? 'Show' : 'Hide'; }
    });
    view.addEventListener('submit', function (e) {
      e.preventDefault();
      var form = e.target, v = UI.formData(form);
      var problem = !/^\S+@\S+\.\S+$/.test(v.email || '') ? 'Please enter a valid email address.'
        : mode !== 'reset' && (v.password || '').length < (mode === 'signup' ? 8 : 1) ? (mode === 'signup' ? 'Please choose a password of at least 8 characters.' : 'Please enter your password.')
        : mode === 'signup' && (v.name || '').trim().length < 2 ? 'Please tell us your name.' : null;
      if (problem) { say(problem, true); return; }
      if (mode === 'signup' && window.LegalKit && !LegalKit.consentChecked(form)) return;  // the kit shows its own message
      UI.busy(form.querySelector('[type=submit]'), UI.auth(mode, v)).then(function (r) {
        if (mode === 'reset' || (r && !r.me)) { mode = 'login'; draw(r && r.message, false); restore({ email: v.email }); }
        else UI.toast(mode === 'signup' ? 'Welcome to ' + UI.config.name + '!' : 'Welcome back!', 'ok');
      }, function (err) { say(err.message, true); });
    });
    function say(msg, isErr) {
      var box = view.querySelector('[data-msg]');
      box.className = isErr ? 'ui-error' : 'ui-note'; box.textContent = msg; box.hidden = false;
    }
    function restore(v) {
      ['name', 'email'].forEach(function (k) { var i = view.querySelector('[name=' + k + ']'); if (i && v[k]) i.value = v[k]; });
    }
    draw();
  });
})();

/* ===== class.html ===== */
(function () {
  'use strict';
  var esc = UI.esc;

  UI.page('class', { title: 'Class' }, function (view, ctx) {
    var id = ctx.args[0], solo = ctx.args[1] === 'solo';
    var d = null, spot = null;
    if (solo) document.documentElement.classList.add('hb-solo');
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:420px"></div></div>';

    function bookBox() {
      var c = d['class'], b = d.booking;
      if (c.status === 'cancelled') return '<div class="cl-cancelled">' + UI.icon('x') + ' This class was cancelled. ' + esc(c.cancel_note) + '</div>';
      if (b && (b.status === 'booked' || b.status === 'checked_in')) {
        return '<div class="cl-status"><h3>' + UI.icon('check') + (d.past ? 'You came to this class' : 'You\'re booked') + '</h3>' +
          '<p class="small" style="margin:6px 0">' + (b.spot ? 'Mat <b>' + esc(b.spot) + '</b> · ' : 'Any mat · ') + esc(b.pass_name) + '</p>' +
          (d.past ? '' : '<p class="small muted" style="margin:0">' + (b.late_if_cancel ? 'It\'s inside the ' + c.studio.cancel_hours + '-hour window: cancelling now counts against your pass.' : 'Free to cancel until ' + esc(HB.when(b.cancel_by)) + '.') + '</p>') + '</div>' +
          (d.past ? '<button class="ui-btn primary block" data-reflect>' + UI.icon('heart') + (b.mood ? 'Edit your reflection' : 'How do you feel?') + '</button>'
            : '<div class="ui-row"><button class="ui-btn" data-ics>' + UI.icon('download') + 'Calendar</button><button class="ui-btn danger" data-cancel>' + UI.icon('x') + 'Cancel</button></div>') +
          (d.room && !d.past ? HB.matGrid(d.room, d.taken, b.spot, null, {}) : '');
      }
      if (b && b.status === 'waitlist') {
        return '<div class="cl-status wait"><h3>' + UI.icon('clock') + 'You\'re #' + b.waitlist_pos + ' on the waitlist</h3><p class="small" style="margin:6px 0 0">We\'ll move you in automatically if a mat opens up, and message you. If that happens inside the cancel window, you can still cancel for free.</p></div>' +
          '<button class="ui-btn danger" data-cancel>' + UI.icon('x') + 'Leave the waitlist</button>';
      }
      if (b && b.status === 'late') return '<div class="cl-status late"><h3>Late cancel</h3><p class="small" style="margin:0">You cancelled inside the window. Talk to the studio if something came up: they can forgive it.</p></div>';
      if (d.past) return '<div class="ui-note">This class has finished.</div>';
      var full = c.left <= 0;
      var passes = d.passes;
      var out = '<div class="ui-row between"><h3>' + (c.kind === 'workshop' ? 'Workshop · ' + HB.money(c.price) : full ? 'Class is full' : 'Book your mat') + '</h3>' + HB.spots(c) + '</div>';
      if (!full && d.room && c.kind !== 'workshop') {
        out += '<p class="small muted" style="margin:0">Tap a mat to pick your spot, or leave it and take any free mat.</p>' + HB.matGrid(d.room, d.taken, null, spot, {});
      }
      if (UI.me && passes.length && c.kind !== 'workshop') {
        out += '<div class="cl-pass" data-passes>' + passes.map(function (p, i) {
          return '<label><input type="radio" name="pass" value="' + esc(p.id) + '"' + (i === 0 ? ' checked' : '') + '><span style="flex:1">' + esc(p.name) + '</span><b>' + (p.unlimited ? 'Unlimited' : p.credits_left + ' left') + '</b></label>';
        }).join('') + '</div>';
      } else if (UI.me && c.kind !== 'workshop') {
        var intro = d.products.filter(function (p) { return p.intro_only && p.eligible; })[0];
        out += '<div class="ui-note">' + (intro ? 'New to ' + esc(c.studio.name) + '? <b>' + esc(intro.name) + '</b> for ' + HB.money(intro.price) + '. You\'ll choose a pass in the next step.' : 'You\'ll choose a pass in the next step.') + '</div>';
      } else if (c.kind === 'workshop') {
        out += '<p class="small muted" style="margin:0">Pay ' + esc(c.studio.name) + ' at the door. Free to cancel until ' + c.studio.cancel_hours + ' hours before.</p>';
      }
      out += '<button class="ui-btn ' + (full ? '' : 'primary') + ' lg block" data-dobook>' + UI.icon(full ? 'clock' : 'check') + (full ? 'Join the waitlist' + (c.waiting ? ' (' + c.waiting + ' waiting)' : '') : spot ? 'Book mat ' + spot : 'Book') + '</button>' +
        '<p class="small muted" style="margin:0;text-align:center">Free cancellation until ' + c.studio.cancel_hours + ' hours before class.</p>';
      return out;
    }

    function draw() {
      var c = d['class'], t = d.teacher;
      document.title = c.title + ' · Health Booker';
      var tf = t && d.follows.teachers.indexOf(t.id) >= 0;
      view.innerHTML = '<div class="ui-wrap ' + HB.acc(c.studio.accent) + '">' +
        '<a class="ui-btn ghost sm" href="#studio/' + esc(c.studio.slug) + (solo ? '/solo' : '') + '" data-go="studio/' + esc(c.studio.slug) + (solo ? '/solo' : '') + '" style="margin-left:-10px">' + UI.icon('back') + esc(c.studio.name) + '</a>' +
        '<div class="cl-grid" style="margin-top:12px"><div>' +
          '<div class="cl-top"><div class="eyebrow" style="color:var(--acc)">' + esc(c.style) + (c.kind === 'workshop' ? ' workshop' : '') + '</div><h1>' + esc(c.title) + '</h1>' +
          '<div class="cl-when">' + esc(HB.when(c.start)) + ' · ' + esc(HB.mins(c.minutes)) + '</div></div>' +
          '<div class="hb-tags">' + (c.heated ? '<span class="hb-tag heat">' + UI.icon('flame') + ' Heated</span>' : '') + (c.tags || []).filter(function (x) { return x !== 'Heated'; }).map(function (x) { return '<span class="hb-tag">' + esc(x) + '</span>'; }).join('') +
          (c.sub ? '<span class="hb-tag sub">' + esc(c.teacher.name) + ' is subbing for ' + esc(c.orig_teacher) + '</span>' : '') + '</div>' +
          '<div class="cl-facts"><div class="cl-fact"><small>Level</small><b>' + esc(HB.LEVEL[c.level] || c.level) + '</b></div>' +
            '<div class="cl-fact"><small>Intensity</small>' + HB.leaves(c.intensity) + ' <b>' + ['', 'Very gentle', 'Gentle', 'Moderate', 'Strong', 'Very strong'][c.intensity] + '</b></div>' +
            '<div class="cl-fact"><small>Where</small><b>' + esc(c.room ? c.room.name : c.studio.name) + '</b><div class="small muted">' + esc(c.studio.neighbourhood) + '</div></div>' +
            '<div class="cl-fact"><small>Mats</small><b>' + c.booked + ' / ' + c.capacity + '</b>' + (c.waiting ? '<div class="small muted">' + c.waiting + ' waiting</div>' : '') + '</div></div>' +
          '<p style="font-size:1.05rem">' + esc(c.about) + '</p>' +
          (c.studio.address ? '<p class="small muted">' + UI.icon('pin') + ' ' + esc(c.studio.name) + ', ' + esc(c.studio.address) + '</p>' : '') +
          (t ? '<div class="ui-card" style="margin-top:22px"><div class="cl-teacher"><span class="ui-avatar">' + esc(UI.initials(t.name)) + '</span><div><div class="ui-row between"><h3 style="margin:0">' + esc(t.name) + '</h3>' +
            (UI.me ? '<button class="ui-btn sm" data-tfollow>' + UI.icon(tf ? 'heartfill' : 'heart') + (tf ? 'Following' : 'Follow') + '</button>' : '') + '</div>' +
            '<p class="muted" style="margin:6px 0 0">' + esc(t.bio) + '</p></div></div>' +
            (d.reviews.length ? '<div class="ui-list" style="margin-top:16px">' + d.reviews.map(function (r) {
              return '<div style="border-top:1px solid var(--c-line);padding-top:12px">' + HB.stars(r.stars) + '<p style="margin:6px 0 2px">' + esc(r.text) + '</p><div class="small muted">' + esc(r.who) + ' · ' + esc(r['class']) + '</div></div>';
            }).join('') + '</div>' : '') + '</div>' : '') +
          (d.is_staff ? '<button class="ui-btn" style="margin-top:16px" data-roster>' + UI.icon('users') + 'Class list and check-in</button>' : '') +
        '</div><aside class="ui-card cl-book">' + bookBox() + '</aside></div></div>';
    }

    view.addEventListener('click', function (e) {
      var m = e.target.closest('[data-spot]');
      if (m && !m.disabled && !d.booking) { var s = m.getAttribute('data-spot'); spot = spot === s ? null : s; draw(); return; }
      var bk = e.target.closest('[data-dobook]');
      if (bk) {
        var sel = view.querySelector('[data-passes] input:checked');
        UI.busy(bk, HB.book(d['class'], { passId: sel ? sel.value : null, spot: spot })).then(function (b) { if (b) { spot = null; load(); } });
        return;
      }
      if (e.target.closest('[data-cancel]')) { HB.cancel(Object.assign({}, d.booking, { 'class': d['class'] })).then(function (ok) { if (ok) load(); }); return; }
      if (e.target.closest('[data-ics]')) { HB.ics(d['class']); return; }
      if (e.target.closest('[data-reflect]')) { HB.reflect(Object.assign({}, d.booking, { 'class': d['class'] })).then(function (ok) { if (ok) load(); }); return; }
      if (e.target.closest('[data-roster]')) { HB.roster(id, load); return; }
      if (e.target.closest('[data-tfollow]')) {
        UI.api('toggle_follow', 'teacher', d.teacher.id).then(function (r) {
          var i = d.follows.teachers.indexOf(d.teacher.id);
          if (r.following && i < 0) d.follows.teachers.push(d.teacher.id); else if (!r.following && i >= 0) d.follows.teachers.splice(i, 1);
          UI.toast(r.following ? 'You\'ll see ' + d.teacher.name.split(' ')[0] + '\'s classes under "Following".' : 'Unfollowed.'); draw();
        });
      }
    });
    function load() { return UI.api('get_class', id).then(function (r) { d = r; draw(); }); }
    return { ready: load(), destroy: function () { document.documentElement.classList.remove('hb-solo'); } };
  });
})();

/* ===== discover.html ===== */
(function () {
  'use strict';
  var esc = UI.esc;
  var TIMES = [['morning', 'Morning', 0, 12], ['midday', 'Midday', 12, 17], ['evening', 'Evening', 17, 24]];
  var TOGGLES = [['beginner', 'Beginner-friendly'], ['heated', 'Heated'], ['unheated', 'Not heated'], ['french', 'En français'], ['open', 'Mats left'], ['following', 'Following'], ['workshop', 'Workshops']];
  var MATCH = {
    feel: [['energy', 'Energised', ['Vinyasa', 'Hot', 'Ashtanga', 'Pilates']], ['calm', 'Calm and rested', ['Yin', 'Restorative', 'Sound', 'Breathwork', 'Meditation']],
           ['strong', 'Strong and mobile', ['Hatha', 'Mobility', 'Pilates', 'Ashtanga']], ['gentle', 'Gently cared for', ['Prenatal', 'Chair', 'Restorative', 'Kids & family']]],
    exp: [['new', 'Brand new'], ['some', 'I know the basics'], ['lots', 'Bring it on']],
    when: [['morning', 'Morning'], ['midday', 'Midday'], ['evening', 'Evening'], ['any', 'Whenever']],
    heat: [['yes', 'Love the heat'], ['no', 'No heat please'], ['any', 'Don\'t mind']]
  };

  function hour(c) { return new Date(c.start).getHours(); }

  UI.page('discover', { title: 'Find a class', nav: 'Discover', icon: 'search', order: 10 }, function (view, ctx) {
    var tab = ctx.args[0] === 'studios' ? 'studios' : 'classes';
    var data = null;
    var saved = UI.store.get('discover', {}) || {};
    var st = { day: null, q: '', time: saved.time || '', style: saved.style || '', hood: saved.hood || '', on: saved.on || {} };
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:420px"></div></div>';

    function save() { UI.store.set('discover', { time: st.time, style: st.style, hood: st.hood, on: st.on }); }

    function matches(c) {
      var t = (c.title + ' ' + c.studio.name + ' ' + (c.teacher ? c.teacher.name : '') + ' ' + c.studio.neighbourhood + ' ' + c.style).toLowerCase();
      if (st.q && t.indexOf(st.q.toLowerCase()) < 0) return false;
      if (st.time) { var tm = TIMES.filter(function (x) { return x[0] === st.time; })[0], h = hour(c); if (h < tm[2] || h >= tm[3]) return false; }
      if (st.style && c.style !== st.style) return false;
      if (st.hood && c.studio.neighbourhood !== st.hood) return false;
      var on = st.on, tags = c.tags || [];
      if (on.beginner && !(c.level === 'beginner' || tags.indexOf('Beginner-friendly') >= 0)) return false;
      if (on.heated && !c.heated) return false;
      if (on.unheated && c.heated) return false;
      if (on.french && !(tags.indexOf('En français') >= 0 || tags.indexOf('Bilingual') >= 0)) return false;
      if (on.open && c.left <= 0) return false;
      if (on.workshop && c.kind !== 'workshop') return false;
      if (on.following && !(data.follows.studios.indexOf(c.studio.slug) >= 0 || (c.teacher && data.follows.teachers.indexOf(c.teacher.id) >= 0))) return false;
      return true;
    }

    function days() {
      var out = [], start = HB.startOfDay();
      for (var i = 0; i < 7; i++) out.push(HB.addDays(start, i));
      return out;
    }

    function draw() {
      var tabs = '<nav class="ui-tabs" style="margin-bottom:14px"><a href="#discover" class="' + (tab === 'classes' ? 'on' : '') + '">' + UI.icon('calendar') + 'Classes</a>' +
        '<a href="#discover/studios" class="' + (tab === 'studios' ? 'on' : '') + '">' + UI.icon('door') + 'Studios <span class="count">' + data.studios.length + '</span></a></nav>';
      var head = '<div class="ds-head"><div><div class="eyebrow">' + (UI.me ? 'Hello, ' + esc(UI.me.name.split(' ')[0]) : 'Montréal · ' + data.studios.length + ' studios') + '</div>' +
        '<h1>' + (tab === 'classes' ? 'Find your class' : 'Studios near you') + '</h1></div>' +
        (UI.me ? '' : '<a class="ui-btn ghost sm" href="#open" data-go="open">' + UI.icon('door') + 'List your studio</a>') + '</div>';
      view.innerHTML = '<div class="ui-wrap">' + head + tabs + '<div data-body></div></div>';
      var body = view.querySelector('[data-body]');
      if (tab === 'studios') { body.innerHTML = studiosHtml(); return; }
      var byDay = {};
      data.classes.forEach(function (c) { var k = HB.dayKey(c.start); byDay[k] = (byDay[k] || 0) + (matches(c) ? 1 : 0); });
      if (!st.day) {
        var today = HB.dayKey(new Date());
        st.day = byDay[today] ? today : (Object.keys(byDay).sort()[0] || today);
      }
      var list = data.classes.filter(function (c) { return HB.dayKey(c.start) === st.day && matches(c); });
      var styles = data.styles.filter(function (s) { return data.classes.some(function (c) { return c.style === s; }); });
      var nOn = Object.keys(st.on).filter(function (k) { return st.on[k]; }).length + (st.time ? 1 : 0) + (st.style ? 1 : 0) + (st.hood ? 1 : 0);
      body.innerHTML =
        '<div class="ds-days" role="tablist">' + days().map(function (d) {
          var k = HB.dayKey(d), i = Math.round((d - HB.startOfDay()) / 86400000);
          return '<button class="ds-day' + (k === st.day ? ' on' : '') + '" data-day="' + k + '" role="tab"><small>' + (i === 0 ? 'Today' : d.toLocaleDateString(undefined, { weekday: 'short' })) + '</small>' +
            '<b>' + d.getDate() + '</b><span>' + (byDay[k] || 0) + ' classes</span></button>';
        }).join('') + '</div>' +
        '<div class="ds-bar"><label class="ds-search">' + UI.icon('search') + '<input type="search" data-q placeholder="Class, studio, teacher or area" value="' + esc(st.q) + '" aria-label="Search"></label>' +
        '<select data-style aria-label="Style"><option value="">All styles</option>' + styles.map(function (s) { return '<option' + (s === st.style ? ' selected' : '') + '>' + esc(s) + '</option>'; }).join('') + '</select>' +
        '<select data-hood aria-label="Neighbourhood"><option value="">All areas</option>' + data.neighbourhoods.map(function (s) { return '<option' + (s === st.hood ? ' selected' : '') + '>' + esc(s) + '</option>'; }).join('') + '</select></div>' +
        '<div class="hb-chips scroll">' + TIMES.map(function (t) { return '<button class="hb-chip' + (st.time === t[0] ? ' on' : '') + '" data-time="' + t[0] + '">' + t[1] + '</button>'; }).join('') +
          TOGGLES.filter(function (t) { return t[0] !== 'following' || UI.me; }).map(function (t) { return '<button class="hb-chip' + (st.on[t[0]] ? ' on' : '') + '" data-tog="' + t[0] + '">' + (t[0] === 'heated' ? UI.icon('flame') : t[0] === 'following' ? UI.icon('heart') : '') + esc(t[1]) + '</button>'; }).join('') + '</div>' +
        '<button class="ds-match" data-matcher>' + UI.icon('sparkle') + '<span><b>Not sure what to try?</b><span class="muted small">Four quick questions and we\'ll suggest three classes.</span></span></button>' +
        '<div class="ds-count"><span>' + UI.plural(list.length, 'class', 'classes') + ' on ' + esc(HB.relDay(st.day + 'T12:00:00')) + '</span>' +
          (nOn ? '<button class="ui-btn ghost sm" data-clear>' + UI.icon('x') + 'Clear ' + UI.plural(nOn, 'filter') + '</button>' : '') + '</div>' +
        (list.length ? '<div class="hb-list" style="margin-top:12px">' + list.map(function (c) { return HB.classRow(c, { mine: data.mine[c.id] }); }).join('') + '</div>'
          : '<div class="ui-empty" style="margin-top:12px">' + HB.tree() + '<h3>No classes match</h3><p>Try another day, or clear a filter or two.</p></div>');
    }

    function studiosHtml() {
      return '<div class="ds-studios">' + data.studios.map(function (s) {
        var fav = data.follows.studios.indexOf(s.slug) >= 0;
        return '<a class="ds-studio ' + HB.acc(s.accent) + '" href="#studio/' + esc(s.slug) + '" data-go="studio/' + esc(s.slug) + '">' +
          '<div class="ds-cover"><span class="ft">' + (s.featured ? '<span class="ui-badge clay">Featured</span>' : '') + '</span>' +
          (UI.me ? '<button class="ui-btn icon sm fav" data-fav="' + esc(s.slug) + '" aria-label="' + (fav ? 'Unfollow' : 'Follow') + '">' + UI.icon(fav ? 'heartfill' : 'heart') + '</button>' : '') + '</div>' +
          '<div class="in"><h3>' + esc(s.name) + '</h3><div class="hb-meta">' + UI.icon('pin') + esc(s.neighbourhood) + ' · ' + HB.rating(s.rating, s.rating_n) + '</div>' +
          '<p class="muted small" style="margin:0">' + esc(s.tagline) + '</p>' +
          '<div class="hb-tags">' + s.styles.slice(0, 4).map(function (x) { return '<span class="hb-tag">' + esc(x) + '</span>'; }).join('') + '</div>' +
          (s.intro ? '<div class="intro"><span>New here? ' + esc(s.intro.name) + '</span><b>' + HB.money(s.intro.price) + '</b></div>' : '') + '</div></a>';
      }).join('') + '</div>';
    }

    function matcher() {
      var ans = {};
      function q(key, title) {
        return '<div class="ds-q"><b>' + title + '</b><div class="hb-chips">' + MATCH[key].map(function (o) { return '<button type="button" class="hb-chip" data-k="' + key + '" data-v="' + o[0] + '">' + esc(o[1]) + '</button>'; }).join('') + '</div></div>';
      }
      var m = UI.modal('<h2>Find my class</h2><p class="muted">From every studio, over the next week.</p>' +
        q('feel', 'How do you want to feel after?') + q('exp', 'How much yoga have you done?') + q('when', 'When suits you?') + q('heat', 'Heat?') +
        '<div data-res></div>', { wide: true });
      m.el.addEventListener('click', function (e) {
        var b = e.target.closest('[data-k]');
        if (b) {
          ans[b.getAttribute('data-k')] = b.getAttribute('data-v');
          m.el.querySelectorAll('[data-k="' + b.getAttribute('data-k') + '"]').forEach(function (x) { x.classList.toggle('on', x === b); });
          if (Object.keys(ans).length === 4) results();
        }
        var r = e.target.closest('[data-res-id]');
        if (r) { m.close(); UI.go('class', r.getAttribute('data-res-id')); }
      });
      function results() {
        var feel = MATCH.feel.filter(function (f) { return f[0] === ans.feel; })[0];
        var scored = data.classes.filter(function (c) { return c.left > 0 || c.kind !== 'class'; }).map(function (c) {
          var s = 0, why = [];
          var si = feel[2].indexOf(c.style);
          if (si >= 0) { s += 6 - si; why.push(c.style.toLowerCase() + ' leaves you ' + feel[1].toLowerCase()); }
          var beg = c.level === 'beginner' || (c.tags || []).indexOf('Beginner-friendly') >= 0;
          if (ans.exp === 'new') { if (beg) { s += 4; why.push('beginner-friendly'); } if (c.intensity >= 4 || c.level === 'intermediate') s -= 5; }
          if (ans.exp === 'lots' && c.intensity >= 4) { s += 2; why.push('a real challenge'); }
          if (ans.exp === 'some' && c.level === 'all') s += 1;
          var h = hour(c);
          if (ans.when !== 'any') { var tm = TIMES.filter(function (x) { return x[0] === ans.when; })[0]; if (h >= tm[2] && h < tm[3]) { s += 3; why.push(tm[1].toLowerCase()); } else s -= 3; }
          if (ans.heat === 'yes' && c.heated) { s += 2; why.push('heated'); }
          if (ans.heat === 'no' && c.heated) s -= 8;
          if (data.follows.studios.indexOf(c.studio.slug) >= 0) s += 1;
          s -= (new Date(c.start) - Date.now()) / 864e5 * 0.15;
          return { c: c, s: s, why: why };
        }).sort(function (a, b) { return b.s - a.s; });
        var seen = {}, top = [];
        scored.forEach(function (x) { if (top.length < 3 && !seen[x.c.title]) { seen[x.c.title] = 1; top.push(x); } });
        m.el.querySelector('[data-res]').innerHTML = '<h3 style="margin-top:8px">Try one of these</h3><div class="ui-list">' + top.map(function (x) {
          return '<div class="ds-result ' + HB.acc(x.c.studio.accent) + '" data-res-id="' + esc(x.c.id) + '"><span class="hb-dot" style="width:12px;height:12px"></span><div style="flex:1;min-width:0"><b>' + esc(x.c.title) + '</b> · ' + esc(x.c.studio.name) +
            '<div class="small muted">' + esc(HB.when(x.c.start)) + '</div><div class="why">' + esc(x.why.slice(0, 3).join(' · ')) + '</div></div>' + UI.icon('arrow') + '</div>';
        }).join('') + '</div>';
      }
    }

    view.addEventListener('click', function (e) {
      var d = e.target.closest('[data-day]');
      if (d) { st.day = d.getAttribute('data-day'); draw(); return; }
      var t = e.target.closest('[data-time]');
      if (t) { st.time = st.time === t.getAttribute('data-time') ? '' : t.getAttribute('data-time'); save(); draw(); return; }
      var g = e.target.closest('[data-tog]');
      if (g) { var k = g.getAttribute('data-tog'); st.on[k] = !st.on[k]; if (k === 'heated' && st.on[k]) st.on.unheated = false; if (k === 'unheated' && st.on[k]) st.on.heated = false; save(); draw(); return; }
      if (e.target.closest('[data-clear]')) { st.time = st.style = st.hood = ''; st.on = {}; save(); draw(); return; }
      if (e.target.closest('[data-matcher]')) { matcher(); return; }
      var fav = e.target.closest('[data-fav]');
      if (fav) {
        e.preventDefault(); e.stopPropagation();
        var slug = fav.getAttribute('data-fav');
        UI.api('toggle_follow', 'studio', slug).then(function (r) {
          var i = data.follows.studios.indexOf(slug);
          if (r.following && i < 0) data.follows.studios.push(slug); else if (!r.following && i >= 0) data.follows.studios.splice(i, 1);
          UI.toast(r.following ? 'Following. Their classes show under "Following".' : 'Unfollowed.'); draw();
        });
        return;
      }
      var bk = e.target.closest('[data-book]');
      if (bk) {
        var c = data.classes.filter(function (x) { return x.id === bk.getAttribute('data-book'); })[0];
        UI.busy(bk, HB.book(c)).then(function (b) { if (b) load(); });
        return;
      }
      var row = e.target.closest('[data-class]');
      if (row && !e.target.closest('a,button')) UI.go('class', row.getAttribute('data-class'));
    }, true);
    view.addEventListener('input', function (e) {
      if (e.target.matches('[data-q]')) {
        st.q = e.target.value;
        clearTimeout(view._t);
        view._t = setTimeout(function () { var pos = e.target.selectionStart; draw(); var i = view.querySelector('[data-q]'); i.focus(); try { i.setSelectionRange(pos, pos); } catch (x) {} }, 220);
      }
    });
    view.addEventListener('change', function (e) {
      if (e.target.matches('[data-style]')) { st.style = e.target.value; save(); draw(); }
      if (e.target.matches('[data-hood]')) { st.hood = e.target.value; save(); draw(); }
    });
    function load() {
      return UI.api('discover', HB.startOfDay().toISOString(), 7).then(function (d) { data = d; draw(); });
    }
    return load();
  });
})();

/* ===== gift.html ===== */
(function () {
  'use strict';
  var esc = UI.esc;
  UI.page('gift', { title: 'A friend pass for you' }, function (view, ctx) {
    var code = ctx.args[0] || '';
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:300px;max-width:520px;margin:30px auto"></div></div>';
    function draw(d) {
      var s = d.studio;
      var action = d.mine ? '<a class="ui-btn primary lg" href="#studio/' + esc(s.slug) + '" data-go="studio/' + esc(s.slug) + '">Book your free class</a>'
        : d.claimed ? '<p class="muted">This friend pass has already been used.</p>'
        : d.sender_is_me ? '<p class="muted">This is your friend pass. Send this page\'s link to a friend!</p><button class="ui-btn" data-copy>' + UI.icon('copy') + 'Copy link</button>'
        : UI.me ? '<button class="ui-btn primary lg" data-claim>' + UI.icon('gift') + 'Claim my free class</button>'
        : '<a class="ui-btn primary lg" href="#auth/signup" data-signup>Join free to claim it</a>';
      view.innerHTML = '<div class="ui-wrap"><div class="gf-card ' + HB.acc(s.accent) + '"><div class="ic">' + UI.icon('gift') + '</div>' +
        '<div class="eyebrow" style="color:var(--acc)">A gift from ' + esc(d.from) + '</div><h1>Your first class at ' + esc(s.name) + ' is free</h1>' +
        '<p class="muted" style="position:relative">' + esc(s.tagline) + ' · ' + esc(s.neighbourhood) + '</p><div style="margin-top:20px;position:relative">' + action + '</div>' +
        '<p class="small muted" style="margin-top:18px;position:relative">For people who haven\'t been to ' + esc(s.name) + ' before. Valid 3 weeks after claiming.</p></div></div>';
    }
    view.addEventListener('click', function (e) {
      if (e.target.closest('[data-signup]')) { e.preventDefault(); UI.after = '#gift/' + code; UI.go('auth', 'signup'); return; }
      if (e.target.closest('[data-copy]')) { HB.copy(location.href); return; }
      var c = e.target.closest('[data-claim]');
      if (c) UI.busy(c, UI.api('friend_pass_claim', code)).then(function (r) { UI.toast('It\'s in your wallet. Pick a class!', 'ok'); UI.go('studio', r.slug); });
    });
    return UI.api('friend_pass_get', code).then(draw);
  });
})();

/* ===== inbox.html ===== */
(function () {
  'use strict';
  var esc = UI.esc;
  var ICON = { waitlist: 'clock', cancelled: 'x', sub: 'swap', nudge: 'chat', reply: 'star', forgiven: 'heart', friend: 'gift', team: 'users', studio: 'door', pause: 'calendar' };
  UI.page('inbox', { title: 'Inbox', auth: 'user' }, function (view) {
    view.innerHTML = '<div class="ui-wrap ui-narrow"><div class="ui-skel" style="height:300px"></div></div>';
    function draw(d) {
      view.innerHTML = '<div class="ui-wrap ui-narrow"><div class="ui-page-head"><div><h1>Inbox</h1><p class="muted">Notes from your studios, waitlist moves and changes to your classes.</p></div></div>' +
        (d.items.length ? '<div class="ui-list">' + d.items.map(function (n) {
          var s = n.studio;
          return '<article class="ib-item' + (n.read ? '' : ' new') + (s ? ' ' + HB.acc(s.accent) : '') + '"><span class="ib-ic">' + UI.icon(ICON[n.kind] || 'bell') + '</span>' +
            '<div><h3>' + esc(n.title) + '</h3>' + (n.body ? '<p>' + esc(n.body) + '</p>' : '') +
            '<div class="ui-row" style="margin-top:8px">' + (s ? '<span class="small muted"><span class="hb-dot"></span> ' + esc(s.name) + '</span>' : '') +
            (n.link ? '<a class="ui-btn sm ghost" href="' + esc(n.link) + '">Open ' + UI.icon('arrow') + '</a>' : '') + '</div></div>' +
            '<span class="when">' + esc(UI.ago(n.created)) + '</span></article>';
        }).join('') + '</div>' : '<div class="ui-empty">' + UI.icon('inbox') + '<h3>All quiet</h3><p>When a mat opens up or a studio sends you a note, it shows up here.</p></div>') + '</div>';
      if (d.unread) UI.apiQuiet('inbox_read', null).then(function () { if (UI.me) { UI.me.unread = 0; UI.renderChrome(); } });
    }
    return UI.api('inbox').then(draw);
  });
})();

/* ===== kiosk.html ===== */
(function () {
  'use strict';
  var esc = UI.esc;
  UI.page('kiosk', { title: 'Check-in', auth: 'user', chrome: false }, function (view, ctx) {
    var slug = ctx.args[0], d = null, q = '', timer = null, clock = null;
    view.innerHTML = '<div class="ks"><div class="ui-skel" style="height:400px"></div></div>';
    function draw() {
      var s = d.studio;
      view.innerHTML = '<div class="ks ' + HB.acc(s.accent) + '"><div class="ks-top"><div><div class="eyebrow" style="color:var(--acc)">Welcome to</div><h1>' + esc(s.name) + '</h1></div>' +
        '<div class="ks-clock" data-clock>' + esc(HB.time(new Date().toISOString())) + '</div></div>' +
        '<div class="ui-row"><input type="search" class="ks-search" data-q placeholder="Find your name" value="' + esc(q) + '" aria-label="Find your name"><span class="ui-spacer"></span>' +
        '<a class="ui-btn ghost sm" href="#manage/' + esc(slug) + '" data-go="manage/' + esc(slug) + '">' + UI.icon('back') + 'Exit kiosk</a></div>' + list() + '</div>';
    }
    function list() {
      if (!d.classes.length) return '<div class="ui-empty" style="margin-top:30px">' + HB.tree() + '<h3>No more classes today</h3><p>See you tomorrow!</p></div>';
      return d.classes.map(function (c) {
        var ppl = c.people.filter(function (p) { return !q || p.name.toLowerCase().indexOf(q.toLowerCase()) >= 0; });
        return '<section class="ks-class"><h2>' + esc(HB.time(c.start)) + ' · ' + esc(c.title) + ' <span>' + esc(c.teacher ? c.teacher.name : '') + ' · ' + c.people.filter(function (p) { return p['in']; }).length + ' of ' + c.people.length + ' here</span></h2>' +
          (ppl.length ? '<div class="ks-people">' + ppl.map(function (p) {
            return '<button class="ks-p' + (p['in'] ? ' in' : '') + '" data-b="' + esc(p.id) + '" data-in="' + (p['in'] ? 1 : 0) + '" data-name="' + esc(p.name) + '"><span>' + esc(p.name) + '</span><small>' +
              (p['in'] ? 'Checked in' : p.spot ? 'Mat ' + esc(p.spot) : 'Tap to check in') + (p.first ? ' · first visit' : '') + '</small></button>';
          }).join('') + '</div>' : '<p class="muted">' + (q ? 'No one by that name in this class.' : 'No one booked yet.') + '</p>');
      }).join('');
    }
    function welcome(name, first) {
      var w = document.createElement('div');
      w.className = 'ui ks-welcome';
      w.innerHTML = '<div><div class="hb-breath"><span>Breathe in</span></div><h2>Welcome' + (first ? '' : ' back') + ', ' + esc(name.split(' ')[0]) + '</h2><p class="muted">' + (first ? 'So glad you\'re here. Grab a mat and make yourself at home.' : 'Your mat is waiting.') + '</p></div>';
      document.body.appendChild(w);
      setTimeout(function () { w.remove(); }, 2600);
      w.addEventListener('click', function () { w.remove(); });
    }
    view.addEventListener('click', function (e) {
      var b = e.target.closest('[data-b]');
      if (!b) return;
      var wasIn = b.getAttribute('data-in') === '1';
      UI.apiQuiet('set_attendance', b.getAttribute('data-b'), wasIn ? 'booked' : 'checked_in').then(function () {
        if (!wasIn) welcome(b.getAttribute('data-name'), / first visit/.test(b.textContent));
        q = ''; return load(true);
      });
    });
    view.addEventListener('input', function (e) {
      if (e.target.matches('[data-q]')) { q = e.target.value; var pos = e.target.selectionStart; draw(); var i = view.querySelector('[data-q]'); i.focus(); try { i.setSelectionRange(pos, pos); } catch (x) {} }
    });
    function load(quiet) {
      var s = HB.startOfDay();
      return (quiet ? UI.apiQuiet : UI.api)('kiosk_day', slug, s.toISOString(), HB.addDays(s, 1).toISOString()).then(function (r) { d = r; draw(); });
    }
    timer = setInterval(function () { if (!view.querySelector('[data-q]:focus')) load(true); }, 60000);
    clock = setInterval(function () { var c = view.querySelector('[data-clock]'); if (c) c.textContent = HB.time(new Date().toISOString()); }, 15000);
    return { ready: load(), destroy: function () { clearInterval(timer); clearInterval(clock); } };
  });
})();

/* ===== landing.html ===== */
(function () {
  var COPY = {
    eyebrow: 'Yoga across Montréal, in one place',
    title: 'Every studio. <em>One&nbsp;mat.</em>',
    lead: 'Find a class at the city\'s independent studios, pick your mat and book in two taps, with one account instead of one per studio. Studios get a calm back office with no commission, no contract, and their data always theirs.',
    proof: ['No booking fees', 'Pick your own mat', 'Cancel online, see the rules first'],
    students: [
      ['leaf', 'One account, every studio', 'Book hot yoga in Griffintown and yin in Verdun without a new login each time. Your passes live in one wallet.'],
      ['mat', 'Pick your mat', 'See the room and choose your spot by the window or at the back. Free, at every studio.'],
      ['clock', 'A waitlist that\'s fair', 'If a mat opens up you\'re moved in automatically. Moved in late? You can still cancel for free.'],
      ['filter', 'Filters that matter', 'Beginner-friendly, heated or not, prenatal-safe, trauma-informed, en français. Or let the class matcher choose.'],
      ['heart', 'A practice journal', 'Note how you feel after each class and watch the trend. Gentle weekly streaks, never guilt.'],
      ['gift', 'Bring a friend', 'Members get friend passes to share. Your friend\'s first class is on the studio.']
    ],
    pains: [
      ['Fees that stack up: subscription, add-ons, processing markups and a cut of every new client from the marketplace.', 'No commission on bookings, ever. Every feature for every studio, no tiers.'],
      ['12 to 24-month contracts that are hard to leave.', 'No contract. Leave any day.'],
      ['Paying to export your own client list.', 'One-click CSV export of clients, bookings and passes. Free, always.'],
      ['The marketplace shows your students the studio down the street.', 'Your own booking page with no other studios on it. Put it on Instagram and your website.'],
      ['Pick-a-spot and automation only on the expensive plan.', 'Mat picking, waitlists, reminders and insights for everyone.'],
      ['Texting five teachers at 6 am to find a sub.', 'Teachers post a sub request; a colleague covers it in one tap; students are told who\'s teaching.'],
      ['Teacher pay worked out in a spreadsheet.', 'Pay rules per teacher (base + per head) and a statement each month. Nobody teaches an empty room for $0.'],
      ['A dashboard that needs a training course.', 'A Today board, a front-desk check-in kiosk, and insights in plain words.']
    ],
    steps: [['Find a class', 'Browse every studio by day, style, level or neighbourhood. No account needed to look.'],
            ['Pick a pass and your mat', 'Intro offers are front and centre. Pay the studio at your first visit.'],
            ['Breathe', 'Check in, practise, jot down how you feel. Cancel online if life happens.']],
    faq: [['Is it free for students?', 'Yes. Health Booker never adds a booking fee. You only pay the studio for your pass.'],
          ['How do payments work?', 'For now, you pay the studio directly at your first visit (card, cash or e-Transfer) and the front desk marks your pass as paid. Online card payments are coming.'],
          ['What if I cancel late, or the studio cancels?', 'Each studio sets its own cancel window, and you see it before you book. If the studio cancels a class, your credit comes back automatically and you get a message.'],
          ['Who sees my health notes?', 'Only the teachers of the studio you signed the waiver with, and only if you tick the box. Other studios see nothing.'],
          ['What does it cost a studio?', 'Nothing while Health Booker is in early access. We will never take a commission on your bookings, and there is no contract.'],
          ['Can my studio leave with its data?', 'Yes. Export clients, bookings and passes as CSV files any day, from Settings.'],
          ['Is the app in French?', 'Classes are tagged by language (en français, bilingual) and the demo studios teach in both. The app itself is in English for now.']]
  };

  function heroArt() {
    return '<div class="lp-pic" aria-hidden="true"><div class="lp-blob"></div><div class="lp-blob2"></div>' +
      '<svg class="lp-figure" viewBox="0 0 200 260" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">' +
        '<circle cx="100" cy="46" r="15"/><path d="M100 62v78"/><path d="M100 140l-2 82"/><path d="M100 140q32 10 18 34q-8 12-17 2"/>' +
        '<path d="M100 82q-26-18-14-60"/><path d="M100 82q26-18 14-60"/><path d="M60 228h80" stroke="var(--c-accent)"/></svg>' +
      '<div class="lp-card lp-cls"><div class="t">9:30<small style="font:600 .7rem var(--font-body);color:var(--c-muted);margin-left:3px">AM</small></div><h4>Saturday Slow Flow</h4><div class="m">Sage &amp; Stone Yoga · Maya Chen · Plateau</div>' +
        '<div class="row"><span class="m" style="color:var(--c-accent);font-weight:600">Only 2 mats left</span><span class="ui-btn primary">Book</span></div></div>' +
      '<div class="lp-card lp-room"><div class="f">Teacher</div><div class="g">' +
        'tt..t .t.s. ..t..'.split('').filter(function (c) { return c !== ' '; }).map(function (c) { return '<i class="' + (c === 't' ? 't' : c === 's' ? 's' : '') + '"></i>'; }).join('') +
      '</div></div>' +
      '<div class="lp-card lp-breath"><i></i>Breathe in</div></div>';
  }

  UI.page('landing', { title: 'Yoga classes across Montréal' }, function (view, ctx) {
    var me = ctx.me, C = COPY, esc = UI.esc;
    view.innerHTML =
      '<section class="lp-hero"><div class="ui-wrap"><div>' +
        '<div class="eyebrow">' + esc(C.eyebrow) + '</div><h1>' + C.title + '</h1><p class="lp-lead">' + esc(C.lead) + '</p>' +
        '<div class="lp-cta"><a class="ui-btn primary lg" href="#discover" data-go="discover">' + UI.icon('search') + 'Find a class</a>' +
        (me ? '<a class="ui-btn lg" href="#practice" data-go="practice">My practice</a>' : '<a class="ui-btn lg" href="#auth/signup" data-go="auth/signup">Join free</a>') + '</div>' +
        '<div class="lp-proof">' + C.proof.map(function (p) { return '<span>' + UI.icon('check') + esc(p) + '</span>'; }).join('') + '</div>' +
      '</div>' + heroArt() + '</div></section>' +

      '<section class="lp-section" id="students"><div class="ui-wrap"><div class="lp-head"><div class="eyebrow">For students</div><h2>Booking yoga should feel like yoga</h2>' +
        '<p>Not like fighting an app. Everything you need to find the right class and actually go.</p></div>' +
        '<div class="lp-feats">' + C.students.map(function (f) { return '<div class="ui-card lp-feat"><div class="ic">' + UI.icon(f[0]) + '</div><h3>' + esc(f[1]) + '</h3><p>' + esc(f[2]) + '</p></div>'; }).join('') + '</div></div></section>' +

      '<section class="lp-section lp-studios" id="studios"><div class="ui-wrap"><div class="lp-head"><div class="eyebrow">For studio owners</div><h2>We listened to studios who left the big platforms</h2>' +
        '<p>Owners and teachers kept telling the same stories. So we built the opposite.</p></div>' +
        '<div class="lp-vs-head"><span>What studios told us</span><span>What Health Booker does</span></div>' +
        '<div class="lp-vs">' + C.pains.map(function (p) {
          return '<div class="lp-vs-row"><div class="pain">' + UI.icon('x') + '<span>' + esc(p[0]) + '</span></div><div class="fix">' + UI.icon('check') + '<span>' + esc(p[1]) + '</span></div></div>';
        }).join('') + '</div>' +
        '<div class="ui-row" style="margin-top:26px"><a class="ui-btn clay lg" href="#open" data-go="open">' + UI.icon('door') + 'List your studio</a>' +
        '<a class="ui-btn lg" href="#studio/sage-and-stone" data-go="studio/sage-and-stone">See a studio page</a></div></div></section>' +

      '<section class="lp-section"><div class="ui-wrap"><div class="lp-head center"><h2>How it works</h2><p>Three steps from curious to on the mat.</p></div>' +
        '<div class="lp-steps">' + C.steps.map(function (s) { return '<div class="ui-card lp-step"><h3>' + esc(s[0]) + '</h3><p class="muted">' + esc(s[1]) + '</p></div>'; }).join('') + '</div></div></section>' +

      '<section class="lp-section"><div class="ui-wrap"><div class="lp-head center"><h2>Questions</h2></div><div class="lp-faq">' +
        C.faq.map(function (q) { return '<details><summary>' + esc(q[0]) + '</summary><p>' + esc(q[1]) + '</p></details>'; }).join('') + '</div></div></section>' +

      '<section class="lp-section"><div class="ui-wrap"><div class="lp-band"><div><h2>Roll out your mat</h2><p>Classes are on now across Montréal.</p></div>' +
        '<a class="ui-btn lg" href="#discover" data-go="discover">' + UI.icon('search') + 'Find a class</a></div></div></section>';
  });
})();

/* ===== manage.html ===== */
(function () {
  'use strict';
  var esc = UI.esc;
  HB.mg = HB.mg || {};
  var TABS = [['today', 'Today', 'sun'], ['schedule', 'Schedule', 'calendar'], ['clients', 'Clients', 'users'], ['pricing', 'Pricing', 'ticket'],
              ['team', 'Team', 'mat'], ['insights', 'Insights', 'chart'], ['reviews', 'Reviews', 'star'], ['settings', 'Settings', 'sliders']];
  var TAGNAME = { 'new': ['New', 'good'], member: ['Member', 'brand'], intro: ['Intro', 'clay'], drifting: ['Drifting', 'warn'], unpaid: ['Unpaid', 'bad'], expiring: ['Pass ending', ''] };

  UI.page('manage', { title: 'Run my studio', nav: 'Studio', icon: 'door', auth: 'user', order: 40, when: function () { return UI.me && UI.me.manages; } }, function (view, ctx) {
    var list = null, slug = ctx.args[0], tab = TABS.some(function (t) { return t[0] === ctx.args[1]; }) ? ctx.args[1] : 'today';
    var state = { day: HB.startOfDay(), week: HB.startOfDay(), clientTag: 'all', clientQ: '' };
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:420px"></div></div>';
    HB.tips(view);
    var body = null;

    function shell() {
      var me = list.filter(function (s) { return s.slug === slug; })[0];
      view.innerHTML = '<div class="ui-wrap ' + HB.acc(me.accent) + '"><div class="mg-top"><div><div class="eyebrow">' + (me.role === 'admin' ? 'Admin view' : esc(me.role === 'desk' ? 'Front desk' : 'Your studio')) +
        (me.status !== 'live' ? ' · <span class="ui-badge warn">' + esc(me.status === 'review' ? 'In review' : 'Paused') + '</span>' : '') + '</div><h1>' + esc(me.name) + '</h1></div>' +
        '<div class="mg-links">' + (list.length > 1 ? '<select data-pick aria-label="Studio">' + list.map(function (s) { return '<option value="' + esc(s.slug) + '"' + (s.slug === slug ? ' selected' : '') + '>' + esc(s.name) + (s.demo ? ' (demo)' : '') + '</option>'; }).join('') + '</select>' : '') +
        '<a class="ui-btn sm" href="#studio/' + esc(slug) + '" data-go="studio/' + esc(slug) + '">' + UI.icon('external') + 'Studio page</a>' +
        '<a class="ui-btn sm" href="#kiosk/' + esc(slug) + '" data-go="kiosk/' + esc(slug) + '">' + UI.icon('tablet') + 'Check-in kiosk</a></div></div>' +
        '<nav class="ui-tabs">' + TABS.map(function (t) { return '<a href="#manage/' + esc(slug) + '/' + t[0] + '" class="' + (tab === t[0] ? 'on' : '') + '">' + UI.icon(t[2]) + t[1] + '</a>'; }).join('') + '</nav>' +
        '<div data-body><div class="ui-skel" style="height:300px"></div></div></div>';
      body = view.querySelector('[data-body]');
    }

    var ctl = { slug: function () { return slug; }, body: function () { return body; }, reload: function () { return draw(); }, state: state, esc: esc };

    /* ---------------------------------------------------------------- today */
    function today() {
      var start = state.day, end = HB.addDays(start, 1);
      return UI.api('manage_day', slug, start.toISOString(), end.toISOString()).then(function (d) {
        var isToday = HB.dayKey(start) === HB.dayKey(new Date());
        var fill = d.capacity ? Math.round(d.visits / d.capacity * 100) : 0;
        var now = Date.now();
        body.innerHTML = '<div class="mg-daynav"><button class="ui-btn icon" data-dshift="-1" aria-label="Previous day">' + UI.icon('back') + '</button><b>' + esc(isToday ? 'Today' : HB.date(start.toISOString())) + '</b>' +
          '<button class="ui-btn icon" data-dshift="1" aria-label="Next day">' + UI.icon('arrow') + '</button>' + (isToday ? '' : '<button class="ui-btn sm ghost" data-dshift="0">Back to today</button>') + '</div>' +
          '<div class="hb-kpis"><div class="hb-kpi"><b>' + d.visits + '<span class="small muted" style="font-family:var(--font-body)"> / ' + d.capacity + '</span></b><span>mats booked (' + fill + '% full)</span></div>' +
          '<div class="hb-kpi"><b>' + d.first_timers + '</b><span>first-timers</span><small>A leaf marks them on the class list. Say hi!</small></div>' +
          '<div class="hb-kpi"><b>' + HB.money(d.sold.total).replace('Free', '$0') + '</b><span>' + UI.plural(d.sold.count, 'pass', 'passes') + ' sold</span></div>' +
          '<div class="hb-kpi"><b>' + d.unpaid.length + '</b><span>passes to collect at the desk</span></div></div>' +
          (d.open_subs.length ? '<div class="mg-hint" style="margin-top:16px">' + UI.icon('swap') + '<div><b>' + UI.plural(d.open_subs.length, 'class needs', 'classes need') + ' a sub.</b> <span class="muted">' + d.open_subs.map(function (x) { return esc(x['class'].title + ' (' + HB.date(x['class'].start) + ', ' + x.from + ')'); }).join(' · ') + '. Your teachers see it in Teach; or change the teacher in Schedule.</span></div></div>' : '') +
          '<div class="hb-section"><h2>Classes</h2>' + (d.classes.length ? '<div class="mg-tl">' + d.classes.map(function (c) {
            var st = new Date(c.start).getTime(), live = st <= now && now < st + c.minutes * 60000;
            var pct = c.capacity ? Math.round(c.booked / c.capacity * 100) : 0;
            return '<div class="mg-cls' + (c.status === 'cancelled' ? ' cancelled' : '') + (live ? ' now' : '') + '"><div class="hb-time"><b>' + HB.timeHtml(c.start) + '</b><span>' + esc(HB.mins(c.minutes)) + '</span></div>' +
              '<div style="min-width:0"><b>' + esc(c.title) + '</b>' + (live ? ' <span class="ui-badge good">On now</span>' : '') + (c.status === 'cancelled' ? ' <span class="ui-badge bad">Cancelled</span>' : '') +
              '<div class="hb-meta">' + esc(c.teacher ? c.teacher.name : '') + (c.sub ? ' (sub)' : '') + ' · ' + esc(c.room ? c.room.name : '') + '</div></div>' +
              '<div class="mg-fill"><small>' + c.booked + ' / ' + c.capacity + ' booked' + (c.waiting ? ' · ' + c.waiting + ' waiting' : '') + '</small><div class="hb-bar' + (pct >= 100 ? ' full' : '') + '"><i style="width:' + Math.min(100, pct) + '%"></i></div>' +
              '<small>' + c.checked_in + ' checked in' + (c.first_timers ? ' · ' + UI.plural(c.first_timers, 'first-timer') : '') + '</small></div>' +
              '<div class="acts ui-row">' + (c.status === 'cancelled' ? (st > now ? '<button class="ui-btn sm" data-restore="' + esc(c.id) + '">Restore</button>' : '') : '<button class="ui-btn sm primary" data-roster="' + esc(c.id) + '">' + UI.icon('users') + 'Class list</button>') + '</div></div>';
          }).join('') + '</div>' : '<div class="ui-empty">' + UI.icon('calendar') + '<h3>No classes this day</h3><p>Add some in the Schedule tab.</p></div>') + '</div>' +
          '<div class="hb-section"><h2>To collect at the desk</h2>' + (d.unpaid.length ? '<div class="ui-list">' + d.unpaid.map(function (p) {
            return '<div class="ui-item"><span class="ui-avatar">' + esc(UI.initials(p.who)) + '</span><div class="grow"><b>' + esc(p.who) + '</b><p class="small muted">' + esc(p.name) + ' · got it ' + esc(UI.ago(p.created)) + '</p></div>' +
              '<b style="align-self:center">' + HB.money(p.price) + '</b><button class="ui-btn sm clay" data-paid="' + esc(p.id) + '" style="align-self:center">Mark paid</button></div>';
          }).join('') + '</div>' : '<p class="muted">Nothing to collect. Every pass is paid.</p>') + '</div>';
      });
    }

    /* ---------------------------------------------------------------- schedule */
    var sched = null;
    function schedule() {
      var start = state.week;
      return UI.api('manage_schedule', slug, start.toISOString(), 7).then(function (d) {
        sched = d;
        var days = [];
        for (var i = 0; i < 7; i++) days.push(HB.addDays(start, i));
        var todayK = HB.dayKey(new Date());
        body.innerHTML = '<div class="mg-daynav"><button class="ui-btn icon" data-wshift="-7" aria-label="Previous week">' + UI.icon('back') + '</button><b>' + esc(days[0].toLocaleDateString(undefined, { day: 'numeric', month: 'short' })) + ' – ' + esc(days[6].toLocaleDateString(undefined, { day: 'numeric', month: 'short' })) + '</b>' +
          '<button class="ui-btn icon" data-wshift="7" aria-label="Next week">' + UI.icon('arrow') + '</button><span class="ui-spacer"></span><button class="ui-btn primary" data-newclass>' + UI.icon('plus') + 'New class</button></div>' +
          (d.teachers.length && d.rooms.length ? '' : '<div class="ui-note" style="margin-bottom:12px">Add a teacher (Team) and a room (Settings) first.</div>') +
          '<div class="mg-week">' + days.map(function (day) {
            var k = HB.dayKey(day), cs = d.classes.filter(function (c) { return HB.dayKey(c.start) === k; });
            return '<div class="mg-col"><h4 class="' + (k === todayK ? 'today' : '') + '">' + esc(day.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' })) + '</h4>' + cs.map(function (c) {
              var pct = c.capacity ? Math.round(c.booked / c.capacity * 100) : 0;
              return '<button class="mg-blk' + (c.status === 'cancelled' ? ' cancelled' : '') + (c.kind === 'workshop' ? ' ws' : '') + '" data-edit="' + esc(c.id) + '"><b>' + esc(HB.time(c.start)) + ' ' + esc(c.title) + '</b>' +
                '<span>' + esc(c.teacher ? c.teacher.name.split(' ')[0] : '') + (c.sub ? ' (sub)' : '') + ' · ' + c.booked + '/' + c.capacity + '</span><div class="hb-bar' + (pct >= 100 ? ' full' : '') + '"><i style="width:' + Math.min(100, pct) + '%"></i></div></button>';
            }).join('') + '</div>';
          }).join('') + '</div>';
      });
    }

    function classForm(c) {
      var d = sched, isNew = !c;
      c = c || { title: '', style: 'Vinyasa', level: 'all', intensity: 2, heated: false, tags: [], about: '', minutes: 60, kind: 'class', price: 0 };
      var st = c.start ? new Date(c.start) : (function () { var x = HB.addDays(state.week, 1); x.setHours(18, 0, 0, 0); return x; })();
      var room0 = c.room ? c.room.id : (d.rooms[0] || {}).id;
      var cap = c.capacity || (d.rooms[0] || {}).capacity || 12;
      var m = UI.modal('<h2>' + (isNew ? 'New class' : 'Edit class') + '</h2><form class="mg-form" data-cform>' +
        '<label class="ui-field full"><span>Name</span><input type="text" name="title" required minlength="3" maxlength="70" value="' + esc(c.title) + '" placeholder="e.g. Sunset Flow"></label>' +
        '<label class="ui-field"><span>Style</span><select name="style">' + d.styles.map(function (s) { return '<option' + (s === c.style ? ' selected' : '') + '>' + esc(s) + '</option>'; }).join('') + '</select></label>' +
        '<label class="ui-field"><span>Level</span><select name="level">' + d.levels.map(function (s) { return '<option value="' + s + '"' + (s === c.level ? ' selected' : '') + '>' + esc(HB.LEVEL[s]) + '</option>'; }).join('') + '</select></label>' +
        '<label class="ui-field"><span>Teacher</span><select name="teacher_id">' + d.teachers.map(function (t) { return '<option value="' + esc(t.id) + '"' + (c.teacher && c.teacher.id === t.id ? ' selected' : '') + '>' + esc(t.name) + '</option>'; }).join('') + '</select></label>' +
        '<label class="ui-field"><span>Room</span><select name="room_id">' + d.rooms.map(function (r) { return '<option value="' + esc(r.id) + '" data-cap="' + r.capacity + '"' + (r.id === room0 ? ' selected' : '') + '>' + esc(r.name) + ' (' + r.capacity + ' mats)</option>'; }).join('') + '</select></label>' +
        '<label class="ui-field"><span>Date</span><input type="date" name="date" required value="' + HB.dayKey(st) + '"></label>' +
        '<label class="ui-field"><span>Time</span><input type="time" name="time" required value="' + ('0' + st.getHours()).slice(-2) + ':' + ('0' + st.getMinutes()).slice(-2) + '"></label>' +
        '<label class="ui-field"><span>Minutes</span><input type="number" name="minutes" min="15" max="300" step="5" value="' + c.minutes + '"></label>' +
        '<label class="ui-field"><span>Mats available</span><input type="number" name="capacity" min="1" max="100" value="' + cap + '"></label>' +
        '<label class="ui-field"><span>Kind</span><select name="kind"><option value="class">Class (uses passes)</option><option value="workshop"' + (c.kind === 'workshop' ? ' selected' : '') + '>Workshop (own price)</option></select></label>' +
        '<label class="ui-field"><span>Workshop price ($)</span><input type="number" name="price" min="0" step="1" value="' + (c.price || 0) + '"></label>' +
        '<label class="ui-field"><span>Intensity: <b data-intv>' + c.intensity + '</b> of 5</span><input type="range" name="intensity" min="1" max="5" value="' + c.intensity + '"></label>' +
        '<label class="ui-check" style="align-self:end;padding-bottom:10px"><input type="checkbox" name="heated"' + (c.heated ? ' checked' : '') + '> Heated room</label>' +
        '<div class="ui-field full"><span>Tags</span><div class="mg-tags">' + d.tags.map(function (t, i) { return '<label><input type="checkbox" name="tag_' + i + '"' + ((c.tags || []).indexOf(t) >= 0 ? ' checked' : '') + '><span>' + esc(t) + '</span></label>'; }).join('') + '</div></div>' +
        '<label class="ui-field full"><span>Description</span><textarea name="about" rows="3" maxlength="800">' + esc(c.about) + '</textarea></label>' +
        (isNew ? '<label class="ui-field full"><span>Repeat every week for</span><select name="repeat_weeks">' + [1, 2, 4, 6, 8, 12].map(function (n) { return '<option value="' + n + '"' + (n === 8 ? ' selected' : '') + '>' + (n === 1 ? 'Just once' : n + ' weeks') + '</option>'; }).join('') + '</select></label>'
          : (c.series ? '<div class="ui-field full"><span>Apply changes to</span><div class="ui-row"><label class="ui-check"><input type="radio" name="scope" value="one" checked> This class only</label><label class="ui-check"><input type="radio" name="scope" value="future"> This and the following ones</label></div></div>' : '')) +
        '<div class="full ui-row" style="margin-top:6px">' + (isNew ? '' : (c.status === 'cancelled' ? '' : '<button type="button" class="ui-btn danger" data-cancelclass>' + UI.icon('x') + 'Cancel class</button>') + '<button type="button" class="ui-btn" data-croster>' + UI.icon('users') + 'Class list</button>') +
        '<span class="ui-spacer"></span><button type="button" class="ui-btn ghost" data-close>Close</button><button class="ui-btn primary" type="submit">' + UI.icon('check') + (isNew ? 'Add to schedule' : 'Save') + '</button></div></form>', { wide: true });
      var f = m.el.querySelector('[data-cform]');
      f.addEventListener('input', function (e) {
        if (e.target.name === 'intensity') f.querySelector('[data-intv]').textContent = e.target.value;
      });
      f.addEventListener('change', function (e) {
        if (e.target.name === 'room_id') { var o = e.target.selectedOptions[0]; f.capacity.value = o.getAttribute('data-cap'); }
      });
      f.addEventListener('submit', function (e) {
        e.preventDefault();
        var v = UI.formData(f);
        var payload = { id: c.id || null, title: v.title, style: v.style, level: v.level, teacher_id: v.teacher_id, room_id: v.room_id,
          start: new Date(v.date + 'T' + v.time).toISOString(), minutes: +v.minutes, capacity: +v.capacity, kind: v.kind, price: +v.price,
          intensity: +v.intensity, heated: v.heated, about: v.about, repeat_weeks: +(v.repeat_weeks || 1), scope: v.scope || 'one',
          tags: d.tags.filter(function (t, i) { return v['tag_' + i]; }) };
        UI.busy(f.querySelector('[type=submit]'), UI.api('save_class', slug, payload)).then(function (r) {
          m.close(); UI.toast(isNew ? (r.count > 1 ? UI.plural(r.count, 'class', 'classes') + ' added.' : 'Class added.') : (r.count > 1 ? UI.plural(r.count, 'class', 'classes') + ' updated.' : 'Saved.'), 'ok'); draw();
        });
      });
      if (!isNew) {
        var cc = m.el.querySelector('[data-cancelclass]');
        if (cc) cc.onclick = function () {
          var m2 = UI.modal('<h2>Cancel ' + esc(c.title) + '?</h2><p class="muted">Everyone booked (' + c.booked + ') and waiting (' + c.waiting + ') gets their credit back and this message:</p>' +
            '<textarea data-note rows="3" maxlength="300">Sorry, we have to cancel this class. Your credit is back in your wallet.</textarea>' +
            '<div class="ui-row end" style="margin-top:14px"><button class="ui-btn ghost" data-close>Keep it</button><button class="ui-btn danger solid" data-yes>Cancel class</button></div>');
          m2.el.querySelector('[data-yes]').onclick = function (ev) {
            UI.busy(ev.currentTarget, UI.api('cancel_class', c.id, m2.el.querySelector('[data-note]').value)).then(function (r) {
              m2.close(); m.close(); UI.toast('Cancelled. ' + UI.plural(r.notified, 'person', 'people') + ' told.', 'ok'); draw();
            });
          };
        };
        m.el.querySelector('[data-croster]').onclick = function () { HB.roster(c.id, draw); };
      }
    }

    /* ---------------------------------------------------------------- clients */
    var cdata = null;
    function clients() {
      return UI.api('clients', slug).then(function (d) { cdata = d; drawClients(); });
    }
    function drawClients() {
      var d = cdata, tag = state.clientTag, q = state.clientQ.toLowerCase();
      var rows = d.clients.filter(function (c) { return (tag === 'all' || c.tags.indexOf(tag) >= 0) && (!q || (c.name + ' ' + c.email).toLowerCase().indexOf(q) >= 0); });
      body.innerHTML = (d.counts.drifting ? '<div class="mg-hint">' + UI.icon('heart') + '<div style="flex:1"><b>' + UI.plural(d.counts.drifting, 'student has', 'students have') + ' a pass but hasn\'t come in 2 weeks.</b><div class="small muted">A short personal note brings many of them back.</div></div>' +
          '<button class="ui-btn sm" data-ctag="drifting">See who</button></div>' : '') +
        '<div class="ui-row" style="margin-bottom:12px"><div class="hb-chips">' + [['all', 'All']].concat(Object.keys(TAGNAME).map(function (k) { return [k, TAGNAME[k][0]]; })).map(function (t) {
          return '<button class="hb-chip' + (tag === t[0] ? ' on' : '') + '" data-ctag="' + t[0] + '">' + esc(t[1]) + ' <span class="faint">' + (d.counts[t[0]] || 0) + '</span></button>';
        }).join('') + '</div></div>' +
        '<div class="ui-row" style="margin-bottom:14px"><input type="search" data-cq placeholder="Search name or email" value="' + esc(state.clientQ) + '" style="max-width:320px">' +
        (tag !== 'all' && rows.length ? '<button class="ui-btn" data-nudgeall>' + UI.icon('chat') + 'Message these ' + rows.length + '</button>' : '') +
        '<span class="ui-spacer"></span><button class="ui-btn sm ghost" data-export="clients">' + UI.icon('download') + 'Export CSV</button></div>' +
        (rows.length ? '<div class="ui-list">' + rows.slice(0, state.clientAll ? 9999 : 40).map(function (c) {
          return '<div class="mg-client" data-uid="' + esc(c.id) + '"><span class="ui-avatar">' + esc(UI.initials(c.name)) + '</span>' +
            '<div style="min-width:0"><b>' + esc(c.name) + '</b><div class="small muted" style="overflow-wrap:anywhere">' + esc(c.email) + '</div><div class="tags">' + c.tags.map(function (t) { return '<span class="ui-badge ' + TAGNAME[t][1] + '">' + TAGNAME[t][0] + '</span>'; }).join('') + '</div></div>' +
            '<div class="stats small"><b>' + UI.plural(c.visits, 'visit') + '</b>' + (c.last ? ' · last ' + esc(UI.ago(c.last)) : '') + '<div class="muted">' + esc(c.passes.join(', ') || 'No active pass') + (c.upcoming ? ' · ' + c.upcoming + ' booked' : '') + '</div>' +
            (c.nudged ? '<div class="faint">Messaged ' + esc(UI.ago(c.nudged)) + '</div>' : '') + '</div>' +
            '<div class="acts ui-row"><button class="ui-btn sm" data-nudge="' + esc(c.id) + '">' + UI.icon('chat') + 'Message</button><button class="ui-btn sm ghost" data-detail="' + esc(c.id) + '">Details</button></div></div>';
        }).join('') + '</div>' + (rows.length > 40 && !state.clientAll ? '<div class="ui-row" style="justify-content:center;margin-top:16px"><button class="ui-btn" data-callall>Show all ' + rows.length + '</button></div>' : '') : '<div class="ui-empty">' + UI.icon('users') + '<h3>No clients here</h3><p>' + (d.counts.all ? 'Try another filter.' : 'People who book or buy a pass show up here.') + '</p></div>');
    }
    function template(c, tag) {
      var first = c.name.split(' ')[0], studio = list.filter(function (s) { return s.slug === slug; })[0].name;
      if (tag === 'drifting' || c.tags.indexOf('drifting') >= 0) return 'Hi ' + first + ', we miss you on the mat! Your pass is still waiting. Is there a time that would suit you better? - ' + studio;
      if (tag === 'intro' || c.tags.indexOf('intro') >= 0) return 'Hi ' + first + ', so glad you came in! How are you finding the classes? If you have questions about which pass fits you, just reply at the desk. - ' + studio;
      if (tag === 'expiring' || c.tags.indexOf('expiring') >= 0) return 'Hi ' + first + ', a heads-up that your pass ends soon. We\'d love to keep practising with you! - ' + studio;
      return 'Hi ' + first + ', thanks for practising with us. - ' + studio;
    }
    function nudge(people, tag) {
      var m = UI.modal('<h2>' + (people.length === 1 ? 'Message ' + esc(people[0].name) : 'Message ' + people.length + ' people') + '</h2><p class="muted">It appears in their Health Booker inbox, from your studio. "{name}" becomes each first name.</p>' +
        '<textarea data-msg rows="5" maxlength="600">' + esc(template(people.length === 1 ? people[0] : { name: '{name}', tags: [tag] }, tag)) + '</textarea>' +
        '<div class="ui-row end" style="margin-top:14px"><button class="ui-btn ghost" data-close>Cancel</button><button class="ui-btn primary" data-send>' + UI.icon('chat') + 'Send</button></div>');
      m.el.querySelector('[data-send]').onclick = function (ev) {
        var txt = m.el.querySelector('[data-msg]').value;
        var jobs = people.reduce(function (p, c) { return p.then(function () { return UI.api('nudge', slug, c.id, txt.replace(/\{name\}/g, c.name.split(' ')[0])); }); }, Promise.resolve());
        UI.busy(ev.currentTarget, jobs).then(function () { m.close(); UI.toast('Sent to ' + UI.plural(people.length, 'person', 'people') + '.', 'ok'); clients(); });
      };
    }
    function detail(uid) {
      UI.api('client_detail', slug, uid).then(function (d) {
        var m = UI.modal('<h2>' + esc(d.name) + '</h2><p class="muted">' + esc(d.email) + '</p>' +
          (d.waiver ? '<div class="ui-note">' + UI.icon('check') + ' Waiver signed ' + esc(UI.fmtDate(d.waiver.signed)) + (d.waiver.health ? '<br><b>Health notes:</b> ' + esc(d.waiver.health) : d.waiver.shared ? '' : '<br><span class="muted">Health notes not shared.</span>') + (d.waiver.emergency ? '<br><b>Emergency:</b> ' + esc(d.waiver.emergency) : '') + '</div>' : '<div class="ui-note">No waiver yet.</div>') +
          '<h3 style="margin-top:16px">Passes</h3><div class="ui-list">' + d.passes.map(function (p) {
            return '<div class="ui-item"><div class="grow"><b>' + esc(p.name) + '</b><p class="small muted">' + esc(p.state) + ' · ' + (p.unlimited ? 'unlimited' : p.credits_left + ' left') + ' · until ' + esc(UI.fmtDate(p.expires)) + '</p></div>' +
              (p.paid ? '<span class="ui-badge good">Paid</span>' : '<button class="ui-btn sm clay" data-paid="' + esc(p.id) + '">Mark paid · ' + HB.money(p.price) + '</button>') + '</div>';
          }).join('') + '</div>' +
          '<h3 style="margin-top:16px">Visits</h3><div class="small">' + d.bookings.slice(0, 25).map(function (b) {
            return '<div class="ui-row between" style="padding:6px 0;border-bottom:1px solid var(--c-line)"><span>' + esc(HB.date(b.start)) + ' · ' + esc(b.title) + '</span><span class="ui-badge">' + esc(b.status.replace('_', ' ')) + '</span></div>';
          }).join('') + '</div>', { wide: true });
        m.el.addEventListener('click', function (e) {
          var p = e.target.closest('[data-paid]');
          if (p) HB.markPaid(p.getAttribute('data-paid')).then(function (ok) { if (ok) { m.close(); detail(uid); } });
        });
      });
    }

    var DRAW = { today: today, schedule: schedule, clients: clients };
    function draw() {
      var f = DRAW[tab] || (HB.mg[tab] && function () { return HB.mg[tab](ctl); });
      return f ? f() : Promise.resolve();
    }

    view.addEventListener('change', function (e) {
      if (e.target.matches('[data-pick]')) { UI.store.set('mg-slug', e.target.value); UI.go('manage', e.target.value, tab); }
    });
    view.addEventListener('input', function (e) {
      if (e.target.matches('[data-cq]')) {
        state.clientQ = e.target.value;
        clearTimeout(view._t);
        view._t = setTimeout(function () { drawClients(); var i = view.querySelector('[data-cq]'); i.focus(); i.setSelectionRange(i.value.length, i.value.length); }, 200);
      }
    });
    view.addEventListener('click', function (e) {
      var ds = e.target.closest('[data-dshift]');
      if (ds) { var n = +ds.getAttribute('data-dshift'); state.day = n ? HB.addDays(state.day, n) : HB.startOfDay(); today(); return; }
      var ws = e.target.closest('[data-wshift]');
      if (ws) { state.week = HB.addDays(state.week, +ws.getAttribute('data-wshift')); schedule(); return; }
      var r = e.target.closest('[data-roster]');
      if (r) { HB.roster(r.getAttribute('data-roster'), draw); return; }
      var rs = e.target.closest('[data-restore]');
      if (rs) { UI.api('restore_class', rs.getAttribute('data-restore')).then(function () { UI.toast('Back on the schedule.', 'ok'); draw(); }); return; }
      var pd = e.target.closest('[data-paid]');
      if (pd && body.contains(pd)) { HB.markPaid(pd.getAttribute('data-paid')).then(function (ok) { if (ok) draw(); }); return; }
      if (e.target.closest('[data-newclass]')) { classForm(null); return; }
      var ed = e.target.closest('[data-edit]');
      if (ed) { classForm(sched.classes.filter(function (c) { return c.id === ed.getAttribute('data-edit'); })[0]); return; }
      var ct = e.target.closest('[data-ctag]');
      if (ct) { state.clientTag = ct.getAttribute('data-ctag'); drawClients(); return; }
      if (e.target.closest('[data-callall]')) { state.clientAll = true; drawClients(); return; }
      var ng = e.target.closest('[data-nudge]');
      if (ng) { nudge(cdata.clients.filter(function (c) { return c.id === ng.getAttribute('data-nudge'); }), null); return; }
      if (e.target.closest('[data-nudgeall]')) {
        var tag = state.clientTag, q = state.clientQ.toLowerCase();
        nudge(cdata.clients.filter(function (c) { return c.tags.indexOf(tag) >= 0 && (!q || (c.name + ' ' + c.email).toLowerCase().indexOf(q) >= 0); }), tag); return;
      }
      var dt = e.target.closest('[data-detail]');
      if (dt) { detail(dt.getAttribute('data-detail')); return; }
      var ex = e.target.closest('[data-export]');
      if (ex) { UI.busy(ex, UI.api('export_csv', slug, ex.getAttribute('data-export'))).then(function (r) { HB.download(r.filename, r.csv, 'text/csv'); UI.toast('Downloaded ' + r.filename, 'ok'); }); }
    });

    return UI.api('manage_list').then(function (l) {
      list = l;
      if (!list.length) {
        view.innerHTML = '<div class="ui-wrap ui-narrow"><div class="ui-empty">' + UI.icon('door') + '<h3>You don\'t run a studio yet</h3><p>Open one in two minutes.</p><a class="ui-btn primary" href="#open" data-go="open">Open a studio</a></div></div>';
        return;
      }
      if (!slug || !list.some(function (s) { return s.slug === slug; })) {
        var last = UI.store.get('mg-slug');
        var own = list.filter(function (s) { return s.role !== 'admin'; });
        slug = (list.some(function (s) { return s.slug === last; }) ? last : (own[0] || list[0]).slug);
      }
      UI.store.set('mg-slug', slug);
      shell();
      return draw();
    });
  });
})();

/* ===== open.html ===== */
(function () {
  'use strict';
  var esc = UI.esc;
  var STYLES = ['Vinyasa', 'Hatha', 'Yin', 'Restorative', 'Hot', 'Ashtanga', 'Prenatal', 'Pilates', 'Breathwork', 'Meditation', 'Mobility', 'Kids & family', 'Chair', 'Sound'];
  var PERKS = ['No commission on bookings, no contract', 'Pick-a-mat, waitlists and intro offers included', 'Teacher subs and pay statements', 'Your own booking page with no other studios', 'Export your data any day'];

  UI.page('open', { title: 'List your studio' }, function (view, ctx) {
    var perks = '<div class="ui-card"><h3>Every studio gets</h3><ul class="op-perks" style="padding-left:18px;margin:0">' + PERKS.map(function (p) { return '<li>' + esc(p) + '</li>'; }).join('') + '</ul></div>';
    if (!ctx.me) {
      view.innerHTML = '<div class="ui-wrap ui-narrow" style="text-align:center"><div class="eyebrow">For studio owners</div><h1>Bring your studio to Health Booker</h1>' +
        '<p class="muted" style="font-size:1.1rem">Set up your schedule, passes and team in an afternoon. Free while we\'re in early access.</p>' +
        '<a class="ui-btn primary lg" href="#auth/signup" data-start>' + UI.icon('door') + 'Create an account to start</a><div style="text-align:left;margin-top:28px">' + perks + '</div></div>';
      view.querySelector('[data-start]').addEventListener('click', function (e) { e.preventDefault(); UI.after = '#open'; UI.go('auth', 'signup'); });
      return Promise.resolve();
    }
    var mine = (ctx.me.roles || []).filter(function (r) { return r.role === 'owner'; });
    view.innerHTML = '<div class="ui-wrap"><div class="ui-page-head"><div><div class="eyebrow">For studio owners</div><h1>Open your studio</h1>' +
      '<p class="muted">Two minutes now; you can change everything later in Manage.' + (mine.length ? ' You already run ' + esc(mine.map(function (r) { return r.name; }).join(', ')) + '.' : '') + '</p></div></div>' +
      '<div class="op-grid"><form class="ui-card ui-stack" data-open>' +
        '<label class="ui-field"><span>Studio name</span><input type="text" name="name" required minlength="3" maxlength="60" placeholder="e.g. Maple Leaf Yoga"></label>' +
        '<label class="ui-field"><span>Tagline <em>(one line)</em></span><input type="text" name="tagline" maxlength="90" placeholder="What makes your studio yours?"></label>' +
        '<div class="op-row"><label class="ui-field"><span>Neighbourhood</span><input type="text" name="neighbourhood" required maxlength="60" placeholder="e.g. Villeray"></label>' +
        '<label class="ui-field"><span>City</span><input type="text" name="city" maxlength="60" value="Montréal"></label></div>' +
        '<label class="ui-field"><span>Address</span><input type="text" name="address" maxlength="120" placeholder="Street and number"></label>' +
        '<div class="ui-field"><span>Styles you teach</span><div class="op-styles">' + STYLES.map(function (s, i) { return '<label><input type="checkbox" name="st_' + i + '" value="' + esc(s) + '"' + (i < 2 ? ' checked' : '') + '><span>' + esc(s) + '</span></label>'; }).join('') + '</div></div>' +
        '<label class="ui-field"><span>About the studio</span><textarea name="about" rows="4" maxlength="1500" placeholder="The space, the vibe, who it\'s for"></textarea></label>' +
        '<div class="ui-field"><span>Colour</span><div class="op-acc">' + Object.keys(HB.ACCENTS).map(function (k, i) { return '<label class="' + HB.acc(k) + '" title="' + k + '"><input type="radio" name="accent" value="' + k + '"' + (i === 0 ? ' checked' : '') + '><span></span></label>'; }).join('') + '</div></div>' +
        '<div class="op-row"><label class="ui-field"><span>Main room: rows of mats</span><input type="number" name="rows" min="1" max="10" value="4"></label>' +
        '<label class="ui-field"><span>Mats per row</span><input type="number" name="cols" min="1" max="10" value="5"></label></div>' +
        '<label class="ui-field"><span>Languages you teach in</span><select name="languages"><option>English</option><option>Français</option><option value="both">English and Français</option></select></label>' +
        '<div class="ui-row end"><button class="ui-btn primary lg" type="submit">' + UI.icon('check') + 'Open my studio</button></div>' +
        '<p class="ui-hint">' + (ctx.me.is_admin ? 'You\'re an admin, so it goes live straight away.' : 'An admin reviews new studios (usually within a day). Meanwhile you can set up everything and preview your page.') + '</p></form>' +
      '<aside class="op-side"><div data-preview></div>' + perks + '</aside></div></div>';
    var form = view.querySelector('[data-open]');
    function values() {
      var v = UI.formData(form);
      v.styles = STYLES.filter(function (s, i) { return v['st_' + i]; });
      v.languages = v.languages === 'both' ? ['English', 'Français'] : [v.languages];
      return v;
    }
    function preview() {
      var v = values();
      view.querySelector('[data-preview]').innerHTML = '<div class="ds-studio ' + HB.acc(v.accent) + '" style="cursor:default"><div class="ds-cover"></div><div class="in"><h3>' + esc(v.name || 'Your studio') + '</h3>' +
        '<div class="hb-meta">' + UI.icon('pin') + esc(v.neighbourhood || 'Neighbourhood') + '</div><p class="muted small" style="margin:0">' + esc(v.tagline || 'Your tagline') + '</p>' +
        '<div class="hb-tags">' + v.styles.slice(0, 4).map(function (s) { return '<span class="hb-tag">' + esc(s) + '</span>'; }).join('') + '</div>' +
        '<div class="intro"><span>Room: ' + ((+v.rows || 0) * (+v.cols || 0)) + ' mats</span><b>Preview</b></div></div></div>';
    }
    form.addEventListener('input', preview);
    form.addEventListener('change', preview);
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      UI.busy(form.querySelector('[type=submit]'), UI.api('create_studio', values())).then(function (r) {
        return UI.api('get_me').then(function (me) { UI.setMe(me); UI.toast(r.status === 'live' ? 'Your studio is live!' : 'Studio created. It\'s in review; set it up meanwhile.', 'ok'); UI.go('manage', r.slug); });
      });
    });
    preview();
    return Promise.resolve();
  });
})();

/* ===== practice.html ===== */
(function () {
  'use strict';
  var esc = UI.esc;
  var TABS = [['upcoming', 'Upcoming', 'calendar'], ['journal', 'Journal', 'leaf'], ['wallet', 'Wallet', 'wallet'], ['following', 'Following', 'heart']];

  function weekStart(d) { d = HB.startOfDay(d); var wd = (d.getDay() + 6) % 7; return HB.addDays(d, -wd); }

  function stats(h) {
    var now = new Date(), month = 0, mins = 0, weeks = {}, moods = [];
    h.forEach(function (b) {
      var d = new Date(b['class'].start);
      if (d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()) month++;
      mins += b['class'].minutes;
      weeks[HB.dayKey(weekStart(d))] = 1;
      if (b.mood) moods.push(b.mood);
    });
    var streak = 0, w = weekStart(now);
    if (!weeks[HB.dayKey(w)]) w = HB.addDays(w, -7);
    while (weeks[HB.dayKey(w)]) { streak++; w = HB.addDays(w, -7); }
    var avg = moods.length ? moods.reduce(function (a, b) { return a + b; }, 0) / moods.length : 0;
    return { month: month, hours: Math.round(mins / 6) / 10, streak: streak, mood: avg, total: h.length };
  }

  UI.page('practice', { title: 'My practice', nav: 'Practice', icon: 'leaf', auth: 'user', order: 20 }, function (view, ctx) {
    var tab = TABS.some(function (t) { return t[0] === ctx.args[0]; }) ? ctx.args[0] : 'upcoming';
    var d = null;
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:420px"></div></div>';
    HB.tips(view);

    function draw() {
      var s = stats(d.history);
      var moodWord = s.mood ? HB.MOODS[Math.round(s.mood) - 1][1] : '';
      view.innerHTML = '<div class="ui-wrap"><div class="ui-page-head"><div><div class="eyebrow">Namaste, ' + esc(ctx.me.name.split(' ')[0]) + '</div><h1>My practice</h1></div>' +
        '<a class="ui-btn primary" href="#discover" data-go="discover">' + UI.icon('search') + 'Find a class</a></div>' +
        '<div class="hb-kpis pr-kpis">' +
          '<div class="hb-kpi"><b>' + s.month + '</b><span>classes this month</span></div>' +
          '<div class="hb-kpi"><b>' + s.streak + '</b><span>' + (s.streak === 1 ? 'week' : 'weeks') + ' in a row</span><small>Any week with a class counts.</small></div>' +
          '<div class="hb-kpi"><b>' + s.hours + '</b><span>hours on the mat</span></div>' +
          '<div class="hb-kpi"><b>' + (s.mood ? esc(moodWord) : '–') + '</b><span>how you usually leave</span>' + (s.mood ? '<small>Average of your reflections</small>' : '<small>Add a reflection after class</small>') + '</div>' +
        '</div>' +
        '<nav class="ui-tabs" style="margin-top:22px">' + TABS.map(function (t) {
          var n = t[0] === 'upcoming' ? d.upcoming.length : t[0] === 'wallet' ? d.passes.filter(function (p) { return p.state === 'active' || p.state === 'paused'; }).length : 0;
          return '<a href="#practice/' + t[0] + '" class="' + (tab === t[0] ? 'on' : '') + '">' + UI.icon(t[2]) + t[1] + (n ? ' <span class="count">' + n + '</span>' : '') + '</a>';
        }).join('') + '</nav><div data-body>' + ({ upcoming: upcoming, journal: journal, wallet: wallet, following: following })[tab]() + '</div></div>';
    }

    function upcoming() {
      if (!d.upcoming.length) return '<div class="ui-empty">' + HB.tree() + '<h3>Nothing booked yet</h3><p>Your next class is a tap away.</p><a class="ui-btn primary" href="#discover" data-go="discover">Find a class</a></div>';
      return HB.byDay(d.upcoming.map(function (b) { var c = Object.assign({}, b['class']); c._b = b; return c; }), function (c) {
        var b = c._b;
        var html = HB.classRow(c, { mine: b.status });
        var extra = '<div class="ui-row" style="margin:-4px 0 6px 6px;font-size:.85rem">' +
          (b.status === 'waitlist' ? '<span class="ui-badge warn">#' + b.waitlist_pos + ' on the waitlist</span>' : (b.spot ? '<span class="ui-badge">Mat ' + esc(b.spot) + '</span>' : '<span class="ui-badge">Any mat</span>')) +
          '<span class="muted">' + esc(b.pass_name) + '</span><span class="ui-spacer"></span>' +
          (b.status === 'booked' ? '<button class="ui-btn ghost sm" data-ics="' + esc(b.id) + '">' + UI.icon('download') + 'Calendar</button>' : '') +
          '<button class="ui-btn ghost sm danger" data-cancel="' + esc(b.id) + '">' + UI.icon('x') + (b.status === 'waitlist' ? 'Leave waitlist' : 'Cancel') + '</button></div>';
        return html + extra;
      });
    }

    function journal() {
      var h = d.history;
      if (!h.length) return '<div class="ui-empty">' + HB.tree() + '<h3>Your journal starts after your first class</h3><p>Every class you come to lands here, with how you felt.</p></div>';
      // 12-week heatmap (Monday rows first)
      var counts = {};
      h.forEach(function (b) { var k = HB.dayKey(b['class'].start); counts[k] = (counts[k] || 0) + 1; });
      var start = HB.addDays(weekStart(new Date()), -77), cells = '', today = HB.dayKey(new Date());
      for (var i = 0; i < 84; i++) {
        var day = HB.addDays(start, i), k = HB.dayKey(day), n = counts[k] || 0;
        cells += '<i class="' + (n >= 2 ? 'l3' : n === 1 ? 'l2' : '') + (k === today ? ' today' : '') + '" data-tip="' + esc(day.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' }) + ': ' + (n ? UI.plural(n, 'class', 'classes') : 'rest day')) + '"></i>';
      }
      // styles
      var styles = {};
      h.forEach(function (b) { styles[b['class'].style] = (styles[b['class'].style] || 0) + 1; });
      var sorted = Object.keys(styles).sort(function (a, b) { return styles[b] - styles[a]; });
      var max = styles[sorted[0]] || 1;
      // mood line, oldest -> newest, last 15 reflections
      var moods = h.filter(function (b) { return b.mood; }).slice(0, 15).reverse();
      var line = '';
      if (moods.length >= 2) {
        var W = 300, Hh = 120, step = W / (moods.length - 1);
        var pts = moods.map(function (b, i) { return [i * step, Hh - (b.mood - 1) / 4 * Hh]; });
        line = '<svg viewBox="-48 -12 356 146" role="img" aria-label="How you felt after your last ' + moods.length + ' classes">' +
          [1, 3, 5].map(function (v) { var y = Hh - (v - 1) / 4 * Hh; return '<line x1="0" x2="300" y1="' + y + '" y2="' + y + '" stroke="var(--c-line)" stroke-width="1"/><text x="-6" y="' + (y + 4) + '" text-anchor="end" font-size="9" fill="var(--c-muted)">' + HB.MOODS[v - 1][1] + '</text>'; }).join('') +
          '<polyline fill="none" stroke="var(--c-brand)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" points="' + pts.map(function (p) { return p.join(','); }).join(' ') + '"/>' +
          pts.map(function (p, i) { var b = moods[i]; return '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="4.5" fill="var(--c-brand)" stroke="var(--c-surface)" stroke-width="2"/><circle cx="' + p[0] + '" cy="' + p[1] + '" r="12" fill="transparent" data-tip="' + esc(b['class'].title + ', ' + HB.date(b['class'].start) + '\n' + HB.MOODS[b.mood - 1][1]) + '"/>'; }).join('') + '</svg>';
      }
      return '<div class="pr-two"><div class="ui-card"><h3>Last 12 weeks</h3><div class="pr-heat"><div class="lbl"><span>Mon</span><span></span><span>Wed</span><span></span><span>Fri</span><span></span><span>Sun</span></div>' +
        '<div class="hb-heat">' + cells + '</div></div><div class="pr-legend">Rest<i style="background:var(--c-surface-2)"></i><i style="background:color-mix(in srgb,var(--c-brand) 60%,var(--c-surface-2))"></i><i style="background:var(--c-brand)"></i>2+ classes</div></div>' +
        '<div class="ui-stack"><div class="ui-card"><h3>Your styles</h3><div class="hb-hbars">' + sorted.slice(0, 6).map(function (k) {
          return '<div class="hb-hbar"><span>' + esc(k) + '</span><div class="hb-bar"><i style="width:' + Math.round(styles[k] / max * 100) + '%"></i></div><b>' + styles[k] + '</b></div>';
        }).join('') + '</div></div>' +
        (line ? '<div class="ui-card pr-mood"><h3>How you leave class</h3><p class="small muted" style="margin-top:-4px">Your last ' + moods.length + ' reflections. Hover a dot for the class.</p>' + line + '</div>' : '') + '</div></div>' +
        '<div class="hb-section"><h2>Every class</h2><div class="ui-list">' + h.map(function (b) {
          var c = b['class'], dt = new Date(c.start);
          return '<div class="pr-entry ' + HB.acc(c.studio.accent) + '"><div class="d"><small>' + esc(dt.toLocaleDateString(undefined, { month: 'short' })) + '</small><b>' + dt.getDate() + '</b></div>' +
            '<div style="min-width:0"><b>' + esc(c.title) + '</b><div class="hb-meta"><span class="hb-dot"></span>' + esc(c.studio.name) + ' · ' + esc(c.teacher ? c.teacher.name : '') + '</div>' +
            (b.note ? '<div class="note">"' + esc(b.note) + '"</div>' : '') + '</div>' +
            '<button class="face" data-reflect="' + esc(b.id) + '" aria-label="Reflection">' + (b.mood ? HB.face(b.mood) + esc(HB.MOODS[b.mood - 1][1]) : UI.icon('plus') + 'How was it?') + '</button></div>';
        }).join('') + '</div></div>';
    }

    function wallet() {
      var html = d.passes.length ? '<div class="pr-passes">' + d.passes.map(function (p) {
        var live = p.state === 'active' || p.state === 'paused';
        return '<div class="pr-pass ' + HB.acc(p.studio.accent) + (live ? '' : ' dim') + '"><div class="ui-row between"><b>' + esc(p.studio.name) + '</b>' +
          '<span class="ui-badge ' + (p.state === 'active' ? 'good' : p.state === 'paused' ? 'warn' : '') + '">' + esc(p.state[0].toUpperCase() + p.state.slice(1)) + '</span></div>' +
          '<div>' + esc(p.name) + '</div><div class="big">' + (p.unlimited ? 'Unlimited' : p.credits_left + '<span class="small muted" style="font-family:var(--font-body)"> of ' + p.credits_total + ' left</span>') + '</div>' +
          '<div class="small muted">' + (p.state === 'paused' ? 'Paused until ' + esc(UI.fmtDate(p.paused_until)) + ' · ' : '') + (live ? 'Valid until ' : 'Ended ') + esc(UI.fmtDate(p.expires)) + '</div>' +
          (!p.paid && live ? '<div class="ui-badge warn" style="justify-self:start">Pay at the desk: ' + HB.money(p.price) + '</div>' : '') +
          '<div class="ui-row">' + (p.can_pause ? '<button class="ui-btn sm" data-pause="' + esc(p.id) + '">Pause membership</button>' : '') +
          '<a class="ui-btn sm ghost" href="#studio/' + esc(p.studio.slug) + '" data-go="studio/' + esc(p.studio.slug) + '">Book here ' + UI.icon('arrow') + '</a></div></div>';
      }).join('') + '</div>' : '<div class="ui-empty">' + UI.icon('wallet') + '<h3>Your wallet is empty</h3><p>Passes you get at any studio land here. Intro offers are the best place to start.</p><a class="ui-btn primary" href="#discover/studios" data-go="discover/studios">Browse studios</a></div>';
      if (d.late.length) {
        html += '<div class="hb-section"><h2>Late cancels and no-shows</h2><p class="muted small">These used a credit. Something came up? Ask the studio: they can forgive it.</p><div class="ui-list">' + d.late.map(function (b) {
          return '<div class="ui-item"><div class="grow"><b>' + esc(b['class'].title) + '</b><p class="small muted">' + esc(b['class'].studio.name) + ' · ' + esc(HB.date(b['class'].start)) + '</p></div><span class="ui-badge ' + (b.status === 'late' ? 'warn' : 'bad') + '">' + (b.status === 'late' ? 'Late cancel' : 'No-show') + '</span></div>';
        }).join('') + '</div></div>';
      }
      html += '<div class="hb-section"><h2>' + UI.icon('gift') + ' Friend passes</h2><p class="muted">With a pack or membership you can give friends a free first class: open the studio\'s About tab and create a link.</p>' +
        (d.friend_passes.length ? '<div class="ui-list">' + d.friend_passes.map(function (f) {
          return '<div class="ui-item"><div class="grow"><b>' + esc(f.studio) + '</b><p class="small muted">Created ' + esc(UI.ago(f.created)) + '</p></div>' +
            (f.claimed ? '<span class="ui-badge good">Claimed</span>' : '<button class="ui-btn sm" data-copygift="' + esc(f.code) + '">' + UI.icon('copy') + 'Copy link</button>') + '</div>';
        }).join('') + '</div>' : '') + '</div>';
      return html;
    }

    function following() {
      if (!d.follows.length) return '<div class="ui-empty">' + UI.icon('heart') + '<h3>You don\'t follow anyone yet</h3><p>Follow studios and teachers, then filter Discover to just their classes.</p></div>';
      return '<div class="pr-follow">' + d.follows.map(function (f) {
        return f.kind === 'studio' ? '<a class="' + HB.acc(f.accent) + '" href="#studio/' + esc(f.slug) + '" data-go="studio/' + esc(f.slug) + '"><span class="ui-avatar">' + UI.icon('door') + '</span><span><b>' + esc(f.name) + '</b><div class="small muted">Studio</div></span></a>'
          : '<a href="#studio/' + esc(f.slug) + '" data-go="studio/' + esc(f.slug) + '"><span class="ui-avatar">' + esc(UI.initials(f.name)) + '</span><span><b>' + esc(f.name) + '</b><div class="small muted">Teaches at ' + esc(f.studio) + '</div></span></a>';
      }).join('') + '</div>';
    }

    function find(id) { return d.upcoming.concat(d.history).filter(function (b) { return b.id === id; })[0]; }

    view.addEventListener('click', function (e) {
      var c = e.target.closest('[data-cancel]');
      if (c) { HB.cancel(find(c.getAttribute('data-cancel'))).then(function (ok) { if (ok) load(); }); return; }
      var i = e.target.closest('[data-ics]');
      if (i) { HB.ics(find(i.getAttribute('data-ics'))['class']); return; }
      var r = e.target.closest('[data-reflect]');
      if (r) { HB.reflect(find(r.getAttribute('data-reflect'))).then(function (ok) { if (ok) load(); }); return; }
      var g = e.target.closest('[data-copygift]');
      if (g) { HB.copy(HB.link('#gift/' + g.getAttribute('data-copygift')), 'Friend pass link copied.'); return; }
      var p = e.target.closest('[data-pause]');
      if (p) {
        var m = UI.modal('<h2>Pause your membership</h2><p class="muted">Going away or injured? Pause for up to 4 weeks. Your end date moves by the same time, so you lose nothing.</p>' +
          '<div class="ui-row">' + [1, 2, 3, 4].map(function (w) { return '<button class="ui-btn" data-w="' + w + '">' + UI.plural(w, 'week') + '</button>'; }).join('') + '</div>');
        m.el.addEventListener('click', function (ev) {
          var w = ev.target.closest('[data-w]');
          if (w) UI.busy(w, UI.api('pause_pass', p.getAttribute('data-pause'), +w.getAttribute('data-w'))).then(function () { m.close(); UI.toast('Paused. Enjoy the break.', 'ok'); load(); });
        });
        return;
      }
      var bk = e.target.closest('[data-book]');
      if (bk) return;
      var row = e.target.closest('[data-class]');
      if (row && !e.target.closest('a,button')) UI.go('class', row.getAttribute('data-class'));
    });
    function load() { return UI.api('my_practice').then(function (r) { d = r; draw(); }); }
    return load();
  });
})();

/* ===== profile.html ===== */
(function () {
  var esc = UI.esc;
  UI.page('profile', { title: 'Your profile', auth: 'user' }, function (view, ctx) {
    var me = ctx.me;
    view.innerHTML = '<div class="ui-wrap ui-narrow"><div class="pf-head"><span class="ui-avatar">' + esc(UI.initials(me.name)) + '</span>' +
      '<div><h1>' + esc(me.name) + '</h1><div class="muted">' + esc(me.email) + (me.joined ? ' · member since ' + esc(UI.fmtDate(me.joined, { month: 'long', year: 'numeric' })) : '') + '</div></div></div>' +
      '<div class="pf-grid"><form class="ui-card ui-stack" data-name><h3>Your name</h3><label class="ui-field"><span>Shown to other people</span>' +
      '<input type="text" name="name" value="' + esc(me.name) + '" maxlength="60" required></label><button class="ui-btn primary" type="submit">Save</button></form>' +
      '<div class="ui-card ui-stack"><h3>Appearance</h3><p class="muted small">Follow your device, or pick one.</p><div data-theme-box></div>' +
      '<h3 style="margin-top:22px">Password</h3><p class="muted small">We\'ll email you a link to choose a new one.</p>' +
      '<button class="ui-btn" data-reset>' + UI.icon('mail') + 'Email me a reset link</button></div></div>' +
      '<div class="ui-card" style="margin-top:16px"><div class="pf-links">' +
      (me.is_admin ? '<a href="#admin" data-go="admin">' + UI.icon('shield') + 'Admin</a>' : '') +
      '<button data-feedback>' + UI.icon('chat') + 'Send feedback</button>' +
      '<button data-lk-open="overview">' + UI.icon('lock') + 'Privacy &amp; Terms, and your data</button>' +
      '<button data-signout-here>' + UI.icon('logout') + 'Sign out</button></div></div></div>';
    function themeBox() {
      var t = UI.theme();
      view.querySelector('[data-theme-box]').innerHTML = '<div class="ui-seg">' + [['auto', 'Auto'], ['light', 'Light'], ['dark', 'Dark']].map(function (o) {
        return '<button type="button" data-theme-pick="' + o[0] + '" class="' + (t === o[0] ? 'on' : '') + '">' + o[1] + '</button>';
      }).join('') + '</div>';
    }
    themeBox();
    view.addEventListener('click', function (e) {
      var t = e.target.closest('[data-theme-pick]');
      if (t) { UI.setTheme(t.getAttribute('data-theme-pick')); themeBox(); UI.renderChrome(); return; }
      if (e.target.closest('[data-reset]')) {
        UI.busy(e.target.closest('[data-reset]'), UI.auth('reset', { email: me.email })).then(function (r) { UI.toast(r.message, 'ok'); });
      }
      if (e.target.closest('[data-signout-here]')) UI.auth('logout');
    });
    view.querySelector('[data-name]').addEventListener('submit', function (e) {
      e.preventDefault();
      var v = UI.formData(e.target);
      UI.busy(e.target.querySelector('[type=submit]'), UI.api('update_profile', v.name)).then(function (r) {
        UI.setMe(r.me); ctx.me = r.me; UI.toast('Saved', 'ok');
        view.querySelector('.pf-head h1').textContent = r.me.name;
      });
    });
  });
})();

/* ===== studio.html ===== */
(function () {
  'use strict';
  var esc = UI.esc;
  var TABS = [['schedule', 'Schedule', 'calendar'], ['pricing', 'Pricing', 'ticket'], ['teachers', 'Teachers', 'users'], ['reviews', 'Reviews', 'star'], ['about', 'About', 'info']];

  UI.page('studio', { title: 'Studio' }, function (view, ctx) {
    var slug = ctx.args[0], solo = ctx.args[1] === 'solo';
    var tab = UI.store.get('studio-tab', 'schedule'), d = null, weeks = 1;
    if (solo) document.documentElement.classList.add('hb-solo');
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:360px"></div></div>';

    function following() { return d.follows.studios.indexOf(slug) >= 0; }

    function draw() {
      var s = d.studio;
      document.title = s.name + ' · Health Booker';
      var intro = d.products.filter(function (p) { return p.intro_only && p.eligible; })[0];
      var mine = d.passes.filter(function (p) { return p.state === 'active' || p.state === 'paused'; });
      view.innerHTML = (s.status !== 'live' ? '<div class="st-preview">' + UI.icon('lock') + ' Preview: this studio is ' + (s.status === 'review' ? 'waiting for review' : 'paused') + '. Only its team and admins can see it.</div>' : '') +
        '<section class="st-hero ' + HB.acc(s.accent) + '"><div class="ui-wrap">' +
        (solo ? '' : '<a class="ui-btn ghost sm" href="#discover/studios" data-go="discover/studios" style="margin-left:-10px">' + UI.icon('back') + 'All studios</a>') +
        '<h1>' + esc(s.name) + '</h1><p class="tag">' + esc(s.tagline) + '</p>' +
        '<div class="hb-meta"><span>' + UI.icon('pin') + ' ' + esc(s.neighbourhood) + (s.address ? ' · ' + esc(s.address) : '') + '</span><span>' + HB.rating(s.rating, s.rating_n) + '</span>' +
        (s.languages.length ? '<span>' + UI.icon('globe') + ' ' + esc(s.languages.join(' · ')) + '</span>' : '') + '</div>' +
        '<div class="st-actions">' +
          (UI.me ? '<button class="ui-btn" data-follow>' + UI.icon(following() ? 'heartfill' : 'heart') + (following() ? 'Following' : 'Follow') + '</button>' : '') +
          '<button class="ui-btn" data-share>' + UI.icon('share') + 'Share</button>' +
          (d.can_manage ? '<a class="ui-btn primary" href="#manage/' + esc(slug) + '" data-go="manage/' + esc(slug) + '">' + UI.icon('door') + 'Manage studio</a>' : '') +
        '</div></div></section>' +
        '<div class="ui-wrap ' + HB.acc(s.accent) + '"><div class="st-grid"><div>' +
          '<nav class="ui-tabs">' + TABS.map(function (t) {
            var n = t[0] === 'reviews' ? s.rating_n : t[0] === 'teachers' ? d.teachers.length : 0;
            return '<button data-tab="' + t[0] + '" class="' + (tab === t[0] ? 'on' : '') + '">' + UI.icon(t[2]) + t[1] + (n ? ' <span class="count">' + n + '</span>' : '') + '</button>';
          }).join('') + '</nav><div data-body>' + body() + '</div></div>' +
          '<aside class="st-side">' +
            (intro ? '<div class="st-intro"><span>New here?</span><b>' + HB.money(intro.price) + '</b><div>' + esc(intro.name) + '</div><button class="ui-btn sm" data-buy="' + esc(intro.id) + '">' + UI.icon('ticket') + 'Get the intro offer</button></div>' : '') +
            (mine.length ? '<div class="ui-card tight"><h4 style="margin:0 0 4px">Your passes here</h4>' + mine.map(function (p) {
              return '<div class="st-pass"><span>' + esc(p.name) + (p.paid ? '' : ' <span class="ui-badge warn">Pay at desk</span>') + '</span><b>' + (p.unlimited ? 'Unlimited' : (p.credits_left + ' left')) + '</b></div>';
            }).join('') + '</div>' : '') +
            '<div class="ui-card tight"><h4 style="margin:0 0 6px">Good to know</h4><p class="small muted" style="margin:0">' +
              'Cancel for free up to <b>' + s.cancel_hours + ' hours</b> before class. ' + (d.waiver ? 'Your waiver is signed.' : 'You\'ll sign a short waiver the first time you book.') + ' Pay the studio at your first visit.</p></div>' +
          '</aside></div>' +
          (solo ? '<p class="st-powered">Booking by <a href="#landing" data-go="landing">Health Booker</a>: no fees, one account for every studio.</p>' : '') + '</div>';
    }

    function body() {
      var s = d.studio;
      if (tab === 'pricing') {
        return '<div class="st-products">' + d.products.map(function (p) {
          var what = p.credits == null ? 'Unlimited classes' : UI.plural(p.credits, 'class', 'classes');
          return '<div class="ui-card st-prod">' + (p.intro_only ? '<span class="ui-badge clay" style="justify-self:start">First visit</span>' : '') + '<b>' + esc(p.name) + '</b><span class="p">' + HB.money(p.price) + '</span>' +
            '<span class="small muted">' + esc(what) + ' · valid ' + UI.plural(p.days, 'day') + '</span>' + (p.about ? '<span class="small">' + esc(p.about) + '</span>' : '') +
            (p.eligible ? '<button class="ui-btn sm" data-buy="' + esc(p.id) + '">' + UI.icon('ticket') + 'Get it</button>' : '<span class="small faint">For first-time students</span>') + '</div>';
        }).join('') + '</div><p class="ui-hint" style="margin-top:14px">' + UI.icon('info') + ' You pay ' + esc(s.name) + ' directly at your first visit. Health Booker adds no fees.</p>';
      }
      if (tab === 'teachers') {
        return d.teachers.length ? '<div class="st-teachers">' + d.teachers.map(function (t) {
          var f = d.follows.teachers.indexOf(t.id) >= 0;
          return '<div class="ui-card st-teacher"><span class="ui-avatar">' + esc(UI.initials(t.name)) + '</span><div><h3 style="margin:2px 0 4px">' + esc(t.name) + '</h3>' +
            '<div class="hb-tags" style="margin:0 0 6px">' + t.styles.map(function (x) { return '<span class="hb-tag">' + esc(x) + '</span>'; }).join('') + '</div>' +
            '<p class="small muted" style="margin:0 0 8px">' + esc(t.bio) + '</p>' +
            (UI.me ? '<button class="ui-btn sm" data-tfollow="' + esc(t.id) + '">' + UI.icon(f ? 'heartfill' : 'heart') + (f ? 'Following' : 'Follow') + '</button>' : '') + '</div></div>';
        }).join('') + '</div>' : '<div class="ui-empty">' + UI.icon('users') + '<h3>No teachers listed yet</h3></div>';
      }
      if (tab === 'reviews') {
        return d.reviews.length ? '<div class="ui-list">' + d.reviews.map(function (r) {
          return '<div class="ui-card st-review"><div class="ui-row between">' + HB.stars(r.stars) + '<span class="small muted">' + esc(UI.ago(r.created)) + '</span></div>' +
            '<p style="margin:8px 0 6px">' + esc(r.text) + '</p><div class="small muted">' + esc(r.who) + ' · ' + esc(r['class']) + (r.teacher ? ' with ' + esc(r.teacher) : '') + '</div>' +
            (r.reply ? '<div class="reply"><b>' + esc(s.name) + ':</b> ' + esc(r.reply) + '</div>' : '') + '</div>';
        }).join('') + '</div><p class="ui-hint" style="margin-top:12px">Only people who came to a class can review it.</p>'
          : '<div class="ui-empty">' + UI.icon('star') + '<h3>No reviews yet</h3><p>Reviews come from people who came to a class.</p></div>';
      }
      if (tab === 'about') {
        var canGift = d.passes.some(function (p) { return (p.kind === 'pack' || p.kind === 'unlimited') && p.state === 'active'; });
        return '<div class="ui-card"><p style="white-space:pre-wrap">' + esc(s.about || s.tagline) + '</p>' +
          (s.amenities.length ? '<h4>Amenities</h4><div class="st-amen">' + s.amenities.map(function (a) { return '<span>' + UI.icon('check') + esc(a) + '</span>'; }).join('') + '</div>' : '') +
          '<h4 style="margin-top:18px">Styles</h4><div class="hb-tags">' + s.styles.map(function (x) { return '<span class="hb-tag">' + esc(x) + '</span>'; }).join('') + '</div>' +
          '<h4 style="margin-top:18px">Policies</h4><p class="small muted">Free cancellation until ' + s.cancel_hours + ' hours before class. Later cancels and no-shows count against your pass. If the studio cancels, your credit comes back automatically.</p>' +
          '<details><summary class="small" style="cursor:pointer">Read the waiver</summary><p class="small muted" style="white-space:pre-wrap;margin-top:8px">' + esc(s.waiver_text) + '</p></details></div>' +
          (canGift ? '<div class="ui-card" style="margin-top:14px"><h3>' + UI.icon('gift') + ' Bring a friend</h3><p class="muted">Your pass comes with friend passes: their first class at ' + esc(s.name) + ' is free.</p><button class="ui-btn primary" data-gift>' + UI.icon('share') + 'Create a friend pass link</button></div>' : '');
      }
      var until = HB.addDays(HB.startOfDay(), 7 * weeks).getTime();
      var cls = d.classes.filter(function (c) { return new Date(c.start).getTime() < until; });
      var more = d.classes.length > cls.length;
      return cls.length ? HB.byDay(cls, function (c) { return HB.classRow(c, { mine: d.mine[c.id], studio: false }); }) +
          (more ? '<div class="ui-row" style="justify-content:center;margin-top:18px"><button class="ui-btn" data-more>' + UI.icon('calendar') + 'Show the following week</button></div>' : '')
        : '<div class="ui-empty">' + HB.tree() + '<h3>No classes on the schedule yet</h3><p>' + (d.can_manage ? 'Add your first class in Manage studio.' : 'Follow the studio to hear when classes open.') + '</p></div>';
    }

    view.addEventListener('click', function (e) {
      var t = e.target.closest('[data-tab]');
      if (t) { tab = t.getAttribute('data-tab'); UI.store.set('studio-tab', tab); draw(); return; }
      if (e.target.closest('[data-more]')) { weeks++; draw(); return; }
      if (e.target.closest('[data-follow]')) {
        UI.api('toggle_follow', 'studio', slug).then(function (r) {
          var i = d.follows.studios.indexOf(slug);
          if (r.following && i < 0) d.follows.studios.push(slug); else if (!r.following && i >= 0) d.follows.studios.splice(i, 1);
          UI.toast(r.following ? 'Following ' + d.studio.name + '.' : 'Unfollowed.'); draw();
        });
        return;
      }
      var tf = e.target.closest('[data-tfollow]');
      if (tf) {
        var id = tf.getAttribute('data-tfollow');
        UI.api('toggle_follow', 'teacher', id).then(function (r) {
          var i = d.follows.teachers.indexOf(id);
          if (r.following && i < 0) d.follows.teachers.push(id); else if (!r.following && i >= 0) d.follows.teachers.splice(i, 1);
          draw();
        });
        return;
      }
      if (e.target.closest('[data-share]')) {
        var m = UI.modal('<h2>Share ' + esc(d.studio.name) + '</h2>' +
          '<p class="muted">The marketplace page shows this studio among others. The direct booking link shows only this studio: perfect for Instagram or the studio\'s website.</p>' +
          '<div class="ui-stack"><button class="ui-btn block" data-cp="' + esc(HB.link('#studio/' + slug)) + '">' + UI.icon('copy') + 'Copy the studio page link</button>' +
          '<button class="ui-btn primary block" data-cp="' + esc(HB.link('#studio/' + slug + '/solo')) + '">' + UI.icon('copy') + 'Copy the direct booking link</button></div>');
        m.el.addEventListener('click', function (ev) { var b = ev.target.closest('[data-cp]'); if (b) HB.copy(b.getAttribute('data-cp')); });
        return;
      }
      var buy = e.target.closest('[data-buy]');
      if (buy) {
        if (!UI.me) { UI.after = location.hash; UI.toast('Create your free account first. It works at every studio.'); UI.go('auth', 'signup'); return; }
        var p = d.products.filter(function (x) { return x.id === buy.getAttribute('data-buy'); });
        HB.shop(d.studio, p.concat(d.products.filter(function (x) { return x.id !== p[0].id; }))).then(function (r) { if (r) load(); });
        return;
      }
      if (e.target.closest('[data-gift]')) {
        UI.api('friend_pass_send', slug).then(function (r) {
          var link = HB.link('#gift/' + r.code);
          var m2 = UI.modal('<h2>' + UI.icon('gift') + ' Your friend pass</h2><p class="muted">Send this link to a friend who\'s never been to ' + esc(d.studio.name) + '. Their first class is free.</p>' +
            '<input type="text" readonly value="' + esc(link) + '"><div class="ui-row end" style="margin-top:14px"><button class="ui-btn primary" data-cp>' + UI.icon('copy') + 'Copy link</button></div>');
          m2.el.querySelector('[data-cp]').onclick = function () { HB.copy(link, 'Copied. Send it to your friend!'); };
        });
        return;
      }
      var bk = e.target.closest('[data-book]');
      if (bk) {
        var c = d.classes.filter(function (x) { return x.id === bk.getAttribute('data-book'); })[0];
        UI.busy(bk, HB.book(c)).then(function (b) { if (b) load(); });
        return;
      }
      var row = e.target.closest('[data-class]');
      if (row && !e.target.closest('a,button')) UI.go('class', row.getAttribute('data-class'), solo ? 'solo' : '');
    });
    function load() { return UI.api('get_studio', slug).then(function (r) { d = r; draw(); }); }
    return { ready: load(), destroy: function () { document.documentElement.classList.remove('hb-solo'); } };
  });
})();

/* ===== teach.html ===== */
(function () {
  'use strict';
  var esc = UI.esc;
  var TABS = [['classes', 'My classes', 'calendar'], ['subs', 'Subs', 'swap'], ['pay', 'Pay', 'wallet'], ['reviews', 'Reviews', 'star']];

  function monthRange(offset) {
    var d = new Date(); d.setDate(1); d.setHours(0, 0, 0, 0); d.setMonth(d.getMonth() + offset);
    var e = new Date(d); e.setMonth(e.getMonth() + 1);
    return [d, e];
  }

  UI.page('teach', { title: 'Teach', nav: 'Teach', icon: 'mat', auth: 'user', order: 30, when: function () { return UI.me && UI.me.teaches; } }, function (view, ctx) {
    var tab = TABS.some(function (t) { return t[0] === ctx.args[0]; }) ? ctx.args[0] : 'classes';
    var month = 0, d = null;
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:400px"></div></div>';

    function draw() {
      if (!d.teaching) {
        view.innerHTML = '<div class="ui-wrap ui-narrow"><div class="ui-empty">' + HB.tree() + '<h3>You\'re not on a studio team yet</h3>' +
          '<p>When a studio owner adds you (with the email you sign in with), your classes, class lists, subs and pay show up here.</p>' +
          '<a class="ui-btn" href="#open" data-go="open">Or open your own studio</a></div></div>';
        return;
      }
      var openN = d.open_subs.length;
      view.innerHTML = '<div class="ui-wrap"><div class="ui-page-head"><div><div class="eyebrow">' + esc(d.studios.map(function (s) { return s.name; }).join(' · ')) + '</div><h1>Teach</h1></div></div>' +
        '<div class="hb-kpis"><div class="hb-kpi"><b>' + d.upcoming.length + '</b><span>classes in the next 2 weeks</span></div>' +
        '<div class="hb-kpi"><b>' + HB.money(d.pay.total).replace('Free', '$0') + '</b><span>earned this month so far</span><small>' + UI.plural(d.pay.lines.length, 'class', 'classes') + ', ' + UI.plural(d.pay.heads, 'student') + '</small></div>' +
        '<div class="hb-kpi"><b>' + openN + '</b><span>' + (openN === 1 ? 'colleague needs' : 'colleagues need') + ' a sub</span></div>' +
        '<div class="hb-kpi"><b>' + (d.rating_n ? d.rating.toFixed(1) : '–') + '</b><span>your rating</span><small>' + UI.plural(d.rating_n, 'review') + '</small></div></div>' +
        '<nav class="ui-tabs" style="margin-top:22px">' + TABS.map(function (t) {
          var n = t[0] === 'subs' ? openN : 0;
          return '<a href="#teach/' + t[0] + '" class="' + (tab === t[0] ? 'on' : '') + '">' + UI.icon(t[2]) + t[1] + (n ? ' <span class="count">' + n + '</span>' : '') + '</a>';
        }).join('') + '</nav><div data-body>' + ({ classes: classes, subs: subs, pay: pay, reviews: reviews })[tab]() + '</div></div>';
    }

    function classes() {
      if (!d.upcoming.length) return '<div class="ui-empty">' + UI.icon('calendar') + '<h3>No classes in the next two weeks</h3></div>';
      var asked = {};
      d.my_subs.forEach(function (x) { if (x.status === 'open' && x['class']) asked[x['class'].id] = x.id; });
      return HB.byDay(d.upcoming, function (c) {
        var started = new Date(c.start) < new Date();
        return '<div class="hb-class tc-class ' + HB.acc(c.studio.accent) + '" style="grid-template-columns:78px minmax(0,1fr) auto" data-cid="' + esc(c.id) + '">' +
          '<div class="hb-time"><b>' + HB.timeHtml(c.start) + '</b><span>' + esc(HB.mins(c.minutes)) + '</span></div>' +
          '<div style="min-width:0"><h3>' + esc(c.title) + '</h3><div class="hb-meta"><span class="hb-dot"></span>' + esc(c.studio.name) + ' · ' + esc(c.room ? c.room.name : '') + '</div>' +
          '<div class="hb-tags"><span class="hb-tag">' + c.booked + ' / ' + c.capacity + ' booked</span>' + (c.waiting ? '<span class="hb-tag">' + c.waiting + ' waiting</span>' : '') +
          (c.first_timers ? '<span class="hb-tag" style="background:var(--c-good-soft);color:var(--c-good)">' + UI.plural(c.first_timers, 'first-timer') + '</span>' : '') +
          (asked[c.id] ? '<span class="hb-tag sub">Sub requested</span>' : '') + '</div></div>' +
          '<div class="tc-acts"><button class="ui-btn sm primary" data-roster="' + esc(c.id) + '">' + UI.icon('users') + 'Class list</button>' +
          (started ? '' : asked[c.id] ? '<button class="ui-btn sm ghost" data-withdraw="' + esc(asked[c.id]) + '">Withdraw request</button>' : '<button class="ui-btn sm" data-ask="' + esc(c.id) + '">' + UI.icon('swap') + 'Ask for a sub</button>') + '</div></div>';
      });
    }

    function subRow(x, mine) {
      var c = x['class'];
      return '<div class="tc-sub' + (x.status === 'open' && !mine ? ' open' : '') + '"><div><b>' + esc(c.title) + '</b> · ' + esc(HB.when(c.start)) +
        '<div class="small muted">' + esc(c.studio.name) + (mine ? '' : ' · for ' + esc(x.from)) + (x.reason ? ' · "' + esc(x.reason) + '"' : '') + ' · ' + c.booked + ' booked</div></div>' +
        (mine ? '<span class="ui-badge ' + (x.status === 'filled' ? 'good' : x.status === 'open' ? 'warn' : '') + '">' + (x.status === 'filled' ? 'Covered by ' + esc(x.filled_by) : x.status === 'open' ? 'Waiting for a sub' : 'Withdrawn') + '</span>'
          : '<button class="ui-btn primary" data-cover="' + esc(x.id) + '">' + UI.icon('check') + 'I\'ll cover it</button>') + '</div>';
    }

    function subs() {
      return '<p class="muted">Covering is one tap: the class moves to you straight away, the owner and your colleague are told, and so are the students.</p>' +
        '<h3 style="margin-top:18px">Colleagues who need a sub</h3>' + (d.open_subs.length ? '<div class="ui-list">' + d.open_subs.map(function (x) { return subRow(x, false); }).join('') + '</div>' : '<div class="ui-empty" style="padding:24px">' + UI.icon('check') + '<p>No open requests. Everyone\'s covered.</p></div>') +
        '<h3 style="margin-top:26px">Your requests</h3>' + (d.my_subs.length ? '<div class="ui-list">' + d.my_subs.map(function (x) { return subRow(x, true); }).join('') + '</div>' : '<p class="muted small">Need a class covered? Use "Ask for a sub" on it in My classes.</p>');
    }

    function pay() {
      var p = d.pay, r = monthRange(month);
      var label = r[0].toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
      return '<div class="ui-row between" style="margin-bottom:12px"><div class="ui-row"><button class="ui-btn icon" data-month="-1" aria-label="Previous month">' + UI.icon('back') + '</button><b style="font-size:1.1rem">' + esc(label) + '</b>' +
        '<button class="ui-btn icon" data-month="1" aria-label="Next month"' + (month >= 0 ? ' disabled' : '') + '>' + UI.icon('arrow') + '</button></div>' +
        '<button class="ui-btn sm" data-paycsv>' + UI.icon('download') + 'Download CSV</button></div>' +
        d.studios.map(function (s) {
          return '<div class="tc-rule"><b>' + esc(s.name) + ':</b> ' + HB.money(s.pay_base).replace('Free', '$0') + ' per class' + (s.pay_per_head ? ' + ' + HB.money(s.pay_per_head) + ' for each student after the ' + s.pay_after + (s.pay_after === 1 ? 'st' : s.pay_after === 2 ? 'nd' : s.pay_after === 3 ? 'rd' : 'th') : '') + '. Classes with nobody still pay the base.</div>';
        }).join('') +
        (p.lines.length ? '<table class="tc-pay"><thead><tr><th>Date</th><th>Class</th><th class="studio">Studio</th><th class="n">Students</th><th class="n">Pay</th></tr></thead><tbody>' + p.lines.map(function (l) {
          return '<tr><td>' + esc(HB.date(l.start)) + '</td><td>' + esc(l.title) + '</td><td class="studio muted">' + esc(l.studio) + '</td><td class="n">' + l.heads + '</td><td class="n">' + HB.money(l.pay).replace('Free', '$0') + '</td></tr>';
        }).join('') + '</tbody><tfoot><tr><td colspan="3">Total</td><td class="n">' + p.heads + '</td><td class="n">' + HB.money(p.total).replace('Free', '$0') + '</td></tr></tfoot></table>'
          : '<div class="ui-empty" style="padding:24px">' + UI.icon('wallet') + '<p>No classes taught in ' + esc(label) + ' yet.</p></div>') +
        '<p class="ui-hint" style="margin-top:12px">Students = checked in or booked (no-shows and late cancels don\'t count). Your studio pays you directly; this statement is what you\'re owed.</p>';
    }

    function reviews() {
      return d.reviews.length ? '<div class="ui-list">' + d.reviews.map(function (r) {
        return '<div class="ui-card tight">' + HB.stars(r.stars) + '<p style="margin:6px 0 4px">' + esc(r.text) + '</p><div class="small muted">' + esc(r['class']) + ' · ' + esc(UI.ago(r.created)) + '</div></div>';
      }).join('') + '</div>' : '<div class="ui-empty">' + UI.icon('star') + '<h3>No reviews yet</h3><p>Students who come to your classes can leave one.</p></div>';
    }

    view.addEventListener('click', function (e) {
      var r = e.target.closest('[data-roster]');
      if (r) { HB.roster(r.getAttribute('data-roster'), load); return; }
      var a = e.target.closest('[data-ask]');
      if (a) {
        var m = UI.modal('<h2>Ask for a sub</h2><p class="muted">Your colleagues at this studio get a message. The first one to cover it takes the class.</p>' +
          '<label class="ui-field"><span>Reason <em>(optional)</em></span><input type="text" data-reason maxlength="200" placeholder="e.g. Family wedding"></label>' +
          '<div class="ui-row end" style="margin-top:14px"><button class="ui-btn ghost" data-close>Cancel</button><button class="ui-btn primary" data-send>' + UI.icon('swap') + 'Send request</button></div>');
        m.el.querySelector('[data-send]').onclick = function (ev) {
          UI.busy(ev.currentTarget, UI.api('request_sub', a.getAttribute('data-ask'), m.el.querySelector('[data-reason]').value)).then(function () { m.close(); UI.toast('Sent to your colleagues.', 'ok'); load(); });
        };
        return;
      }
      var w = e.target.closest('[data-withdraw]');
      if (w) { UI.busy(w, UI.api('withdraw_sub', w.getAttribute('data-withdraw'))).then(function () { UI.toast('Request withdrawn.'); load(); }); return; }
      var cv = e.target.closest('[data-cover]');
      if (cv) {
        UI.confirm({ title: 'Cover this class?', text: 'It moves to you right away and everyone is told.', ok: 'Yes, I\'ll teach it' }).then(function (yes) {
          if (yes) UI.api('cover_sub', cv.getAttribute('data-cover')).then(function () { UI.toast('Thank you! It\'s in your classes now.', 'ok'); load(); });
        });
        return;
      }
      var mo = e.target.closest('[data-month]');
      if (mo) { month += +mo.getAttribute('data-month'); load(); return; }
      if (e.target.closest('[data-paycsv]')) {
        var rows = [['date', 'class', 'studio', 'students', 'pay']].concat(d.pay.lines.map(function (l) { return [l.start, l.title, l.studio, l.heads, l.pay]; }));
        HB.download('pay-' + HB.dayKey(monthRange(month)[0]).slice(0, 7) + '.csv', rows.map(function (r) { return r.map(function (v) { return '"' + String(v).replace(/"/g, '""') + '"'; }).join(','); }).join('\n'), 'text/csv');
      }
    });
    function load() {
      var r = monthRange(month);
      return UI.api('teach_home', r[0].toISOString(), r[1].toISOString()).then(function (x) { d = x; draw(); });
    }
    return load();
  });
})();
