/* hb-draw.js: Health Booker's small JavaScript engine (window.HBD), reached from Python through client_code/hb.py.
   Only what Python is slow or clumsy at: local-time formatting (the browser's clock and locale), the room drawing
   (pick-a-mat, and blocking mats in Settings), the charts (12-week heatmap, mood line, bars, fill-by-hour grid) with
   hover tips, and files (calendar .ics, CSV downloads, copy to clipboard). Everything else is Python Forms. */
(function () {
  'use strict';
  var HBD = window.HBD = {};

  /* ------------------------------------------------------------------ local time */
  function D(x) { return x instanceof Date ? x : new Date(x); }
  function pad(n) { return ('0' + n).slice(-2); }
  var F = HBD.fmt = {
    time: function (iso) { return D(iso).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }); },
    /* ['10:00', 'AM'] (the clock part big, AM/PM small, any locale) */
    timeParts: function (iso) { var t = F.time(iso), m = t.match(/^([\d:.]+)\s*(.*)$/); return m && m[2] ? [m[1], m[2]] : [t, '']; },
    dayKey: function (x) { var d = D(x); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); },
    startOfDay: function (offset) { var d = new Date(); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() + (offset || 0)); return d.toISOString(); },
    addDays: function (iso, n) { var d = D(iso); d.setDate(d.getDate() + n); return d.toISOString(); },
    relDay: function (iso) {
      var k = F.dayKey(iso), now = new Date(), tom = new Date(); tom.setDate(tom.getDate() + 1);
      if (k === F.dayKey(now)) return 'Today';
      if (k === F.dayKey(tom)) return 'Tomorrow';
      return D(iso).toLocaleDateString(undefined, { weekday: 'long' });
    },
    date: function (iso) { return D(iso).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' }); },
    dayMonth: function (iso) { return D(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }); },
    dayLong: function (iso) { return D(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'long' }); },
    when: function (iso) { return F.relDay(iso) + ', ' + F.dayMonth(iso) + ' · ' + F.time(iso); },
    fullDate: function (iso) { return D(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }); },
    monthYear: function (iso) { return D(iso).toLocaleDateString(undefined, { month: 'long', year: 'numeric' }); },
    weekdayShort: function (iso) { return D(iso).toLocaleDateString(undefined, { weekday: 'short' }); },
    weekdayDay: function (iso) { return D(iso).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' }); },
    monthShort: function (iso) { return D(iso).toLocaleDateString(undefined, { month: 'short' }); },
    dayNum: function (iso) { return D(iso).getDate(); },
    hour: function (iso) { return D(iso).getHours(); },
    ms: function (iso) { return D(iso).getTime(); },
    now: function () { return Date.now(); },
    nowIso: function () { return new Date().toISOString(); },
    /* date + time inputs -> ISO (local time); and back */
    toIso: function (date, time) { return new Date(date + 'T' + time).toISOString(); },
    hhmm: function (iso) { var d = D(iso); return pad(d.getHours()) + ':' + pad(d.getMinutes()); },
    monthStart: function (offset) { var d = new Date(); d.setDate(1); d.setHours(0, 0, 0, 0); d.setMonth(d.getMonth() + offset); return d.toISOString(); },
    ago: function (iso) {
      if (!iso) return '';
      var s = (Date.now() - D(iso).getTime()) / 1000;
      if (s < 60) return 'just now';
      var n = s / 60, units = [[60, 'minute'], [24, 'hour'], [7, 'day'], [4.35, 'week'], [12, 'month'], [1e9, 'year']];
      for (var i = 0; i < units.length; i++) {
        if (n < units[i][0]) { var k = Math.floor(n); return k + ' ' + units[i][1] + (k === 1 ? '' : 's') + ' ago'; }
        n = n / units[i][0];
      }
      return '';
    }
  };
  /* Practice stats in local time: classes this month, weekly streak, hours, average mood. history = [{start, minutes, mood}] */
  HBD.stats = function (historyJson) {
    var h = JSON.parse(historyJson), now = new Date(), month = 0, mins = 0, weeks = {}, moods = [];
    function weekStart(d) { d = new Date(d); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() - (d.getDay() + 6) % 7); return F.dayKey(d); }
    h.forEach(function (b) {
      var d = new Date(b.start);
      if (d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()) month++;
      mins += b.minutes || 0;
      weeks[weekStart(d)] = 1;
      if (b.mood) moods.push(b.mood);
    });
    var streak = 0, w = new Date(now);
    w.setHours(0, 0, 0, 0); w.setDate(w.getDate() - (w.getDay() + 6) % 7);
    if (!weeks[F.dayKey(w)]) w.setDate(w.getDate() - 7);
    while (weeks[F.dayKey(w)]) { streak++; w.setDate(w.getDate() - 7); }
    var avg = moods.length ? moods.reduce(function (a, b) { return a + b; }, 0) / moods.length : 0;
    return JSON.stringify({ month: month, hours: Math.round(mins / 6) / 10, streak: streak, mood: avg });
  };

  /* ------------------------------------------------------------------ hover tips (charts) */
  var tip = null;
  function hideTip() { if (tip) { tip.remove(); tip = null; } }
  function tips(root) {
    if (root.__tips) return;
    root.__tips = true;
    root.addEventListener('pointerover', function (e) {
      var t = e.target.closest && e.target.closest('[data-tip]');
      hideTip();
      if (!t) return;
      tip = document.createElement('div');
      tip.className = 'ui hb-tip'; tip.textContent = t.getAttribute('data-tip');
      document.body.appendChild(tip);
      var r = t.getBoundingClientRect(), w = tip.offsetWidth;
      tip.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left + r.width / 2 - w / 2)) + 'px';
      tip.style.top = Math.max(8, r.top - tip.offsetHeight - 8) + 'px';
    });
    root.addEventListener('pointerout', function (e) { if (!e.relatedTarget || !e.relatedTarget.closest || !e.relatedTarget.closest('[data-tip]')) hideTip(); });
  }
  window.addEventListener('scroll', hideTip, { passive: true });
  window.addEventListener('hashchange', hideTip);

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  /* ------------------------------------------------------------------ the room and its mats
     room = {rows, cols, blocked: ["A1"]}; o = {taken: [], mine: "B2", selected: "C1", edit: bool, front: "Teacher"}
     onPick(spot) runs when a free mat (or, in edit mode, any mat) is pressed. */
  HBD.spotName = function (r, c) { return String.fromCharCode(65 + r) + (c + 1); };
  HBD.matGrid = function (host, roomJson, optsJson, onPick) {
    var room = JSON.parse(roomJson), o = JSON.parse(optsJson || '{}');
    var taken = o.taken || [], blocked = room.blocked || [];
    host.textContent = '';
    var wrap = el('div', 'hb-room'), front = el('div', 'hb-front', o.front || 'Teacher');
    var mats = el('div', 'hb-mats'), w = Math.min(46, Math.floor(300 / Math.max(1, room.cols)));
    mats.style.gridTemplateColumns = 'repeat(' + room.cols + ',' + w + 'px)';
    mats.setAttribute('role', 'group');
    mats.setAttribute('aria-label', o.edit ? 'Mats in this room: press one to block or unblock it' : 'Mats in the room: press one to pick your spot');
    for (var r = 0; r < room.rows; r++) for (var c = 0; c < room.cols; c++) {
      var id = HBD.spotName(r, c), isBlocked = blocked.indexOf(id) >= 0;
      if (isBlocked && !o.edit) { mats.appendChild(el('span', 'hb-mat gap')); continue; }
      var cls = o.edit ? (isBlocked ? 'taken' : '') : id === o.mine ? 'mine' : taken.indexOf(id) >= 0 ? 'taken' : id === o.selected ? 'sel' : '';
      var b = el('button', 'hb-mat ' + cls, id);
      b.type = 'button';
      b.setAttribute('data-spot', id);
      var label = 'Mat ' + id + (cls === 'taken' ? (o.edit ? ', blocked' : ', taken') : cls === 'mine' ? ', yours' : cls === 'sel' ? ', your pick' : '');
      b.setAttribute('aria-label', label);
      if (o.edit) b.setAttribute('aria-pressed', isBlocked ? 'true' : 'false');
      else if (cls === 'sel') b.setAttribute('aria-pressed', 'true');
      if ((cls === 'taken' || cls === 'mine') && !o.edit) b.disabled = true;
      mats.appendChild(b);
    }
    mats.addEventListener('click', function (e) {
      var b = e.target.closest('[data-spot]');
      if (b && !b.disabled && onPick) onPick(b.getAttribute('data-spot'));
    });
    wrap.appendChild(front); wrap.appendChild(mats); host.appendChild(wrap);
    if (!o.edit && !o.nokey) {
      var key = el('div', 'hb-room-key');
      [['', 'Free'], ['t', 'Taken'], ['s', 'Your pick']].forEach(function (k) {
        var s = el('span'), i = el('i', k[0]); s.appendChild(i); s.appendChild(document.createTextNode(k[1])); key.appendChild(s);
      });
      host.appendChild(key);
    }
  };

  /* ------------------------------------------------------------------ charts
     HBD.chart(host, kind, json): kind = heat | mood | hbars | cols | fillgrid. One hue, thin marks, recessive axes. */
  var MOODS = ['Heavy', 'Tired', 'Okay', 'Light', 'Glowing'];
  var SVGNS = 'http://www.w3.org/2000/svg';
  function svg(tag, attrs) { var e = document.createElementNS(SVGNS, tag); for (var k in attrs) e.setAttribute(k, attrs[k]); return e; }
  var CHARTS = {
    /* data = {counts: {"2026-11-03": 2}} -> the last 12 weeks, Monday rows first */
    heat: function (host, d) {
      var box = el('div', 'pr-heat'), lbl = el('div', 'lbl');
      ['Mon', '', 'Wed', '', 'Fri', '', 'Sun'].forEach(function (t) { lbl.appendChild(el('span', '', t)); });
      var grid = el('div', 'hb-heat');
      grid.setAttribute('role', 'img');
      var start = new Date(); start.setHours(0, 0, 0, 0); start.setDate(start.getDate() - (start.getDay() + 6) % 7 - 77);
      var today = F.dayKey(new Date()), total = 0;
      for (var i = 0; i < 84; i++) {
        var day = new Date(start); day.setDate(start.getDate() + i);
        var k = F.dayKey(day), n = d.counts[k] || 0;
        total += n;
        var c = el('i', (n >= 2 ? 'l3' : n === 1 ? 'l2' : '') + (k === today ? ' today' : ''));
        c.setAttribute('data-tip', day.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' }) + ': ' + (n ? n + (n === 1 ? ' class' : ' classes') : 'rest day'));
        grid.appendChild(c);
      }
      grid.setAttribute('aria-label', total + (total === 1 ? ' class' : ' classes') + ' in the last 12 weeks');
      box.appendChild(lbl); box.appendChild(grid); host.appendChild(box);
      var legend = el('div', 'pr-legend');
      legend.appendChild(document.createTextNode('Rest'));
      ['var(--c-surface-2)', 'color-mix(in srgb,var(--c-brand) 60%,var(--c-surface-2))', 'var(--c-brand)'].forEach(function (bg) { var i = el('i'); i.style.background = bg; legend.appendChild(i); });
      legend.appendChild(document.createTextNode('2+ classes'));
      host.appendChild(legend);
    },
    /* data = {points: [{mood, label}]} oldest -> newest */
    mood: function (host, d) {
      var moods = d.points, W = 300, H = 120, step = W / Math.max(1, moods.length - 1);
      var s = svg('svg', { viewBox: '-48 -12 356 146', role: 'img', 'aria-label': 'How you felt after your last ' + moods.length + ' classes' });
      [1, 3, 5].forEach(function (v) {
        var y = H - (v - 1) / 4 * H;
        s.appendChild(svg('line', { x1: 0, x2: 300, y1: y, y2: y, stroke: 'var(--c-line)', 'stroke-width': 1 }));
        var t = svg('text', { x: -6, y: y + 4, 'text-anchor': 'end', 'font-size': 11, fill: 'var(--c-muted)' });
        t.textContent = MOODS[v - 1]; s.appendChild(t);
      });
      var pts = moods.map(function (b, i) { return [i * step, H - (b.mood - 1) / 4 * H]; });
      s.appendChild(svg('polyline', { fill: 'none', stroke: 'var(--c-brand)', 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round',
        points: pts.map(function (p) { return p.join(','); }).join(' ') }));
      pts.forEach(function (p, i) {
        s.appendChild(svg('circle', { cx: p[0], cy: p[1], r: 4.5, fill: 'var(--c-brand)', stroke: 'var(--c-surface)', 'stroke-width': 2 }));
        s.appendChild(svg('circle', { cx: p[0], cy: p[1], r: 12, fill: 'transparent', 'data-tip': moods[i].label + '\n' + MOODS[moods[i].mood - 1] }));
      });
      host.appendChild(s);
    },
    /* data = {rows: [{label, value, text, pct?}]} -> horizontal bars, longest = 100% unless pct given */
    hbars: function (host, d) {
      var box = el('div', 'hb-hbars'), max = 1;
      d.rows.forEach(function (r) { max = Math.max(max, r.value); });
      d.rows.forEach(function (r) {
        var row = el('div', 'hb-hbar'), bar = el('div', 'hb-bar'), fill = el('i');
        fill.style.width = Math.round((r.pct != null ? r.pct : r.value / max * 100)) + '%';
        bar.appendChild(fill);
        row.appendChild(el('span', '', r.label)); row.appendChild(bar);
        var b = el('b', '', r.text != null ? r.text : String(r.value));
        if (r.extra) { b.appendChild(document.createTextNode(' ')); b.appendChild(el('span', 'muted small', r.extra)); }
        row.appendChild(b);
        box.appendChild(row);
      });
      host.appendChild(box);
    },
    /* data = {days: [{iso, value, label}], first, total} -> one column per day */
    cols: function (host, d) {
      var box = el('div', 'hb-cols'), max = 0;
      box.setAttribute('role', 'img');
      box.setAttribute('aria-label', 'Passes sold per day, ' + d.total + ' in all');
      d.days.forEach(function (x) { max = Math.max(max, x.value); });
      d.days.forEach(function (x) {
        var c = el('i');
        c.style.height = (max ? Math.max(1.5, x.value / max * 100) : 1.5) + '%';
        c.setAttribute('data-tip', new Date(x.iso).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' }) + ': ' + x.label);
        box.appendChild(c);
      });
      host.appendChild(box);
      var axis = el('div', 'hb-axis');
      axis.appendChild(el('span', '', d.days.length ? F.dayMonth(d.days[0].iso) : ''));
      axis.appendChild(el('span', '', 'Today'));
      host.appendChild(axis);
    },
    /* data = {heat: [[iso, fill 0..1]]} -> average fill by weekday x hour (6..21) */
    fillgrid: function (host, d) {
      var cells = {}, hours = [];
      for (var h = 6; h < 22; h++) hours.push(h);
      d.heat.forEach(function (x) {
        var dt = new Date(x[0]), key = ((dt.getDay() + 6) % 7) + '-' + dt.getHours();
        (cells[key] = cells[key] || []).push(x[1]);
      });
      var grid = el('div', 'mg-grid');
      grid.setAttribute('role', 'img');
      grid.setAttribute('aria-label', 'Average fill by day and hour');
      ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].forEach(function (name, w) {
        var row = el('div', 'r');
        row.appendChild(el('span', '', name));
        hours.forEach(function (hh) {
          var arr = cells[w + '-' + hh], i = el('i');
          if (arr) {
            var f = arr.reduce(function (a, b) { return a + b; }, 0) / arr.length;
            i.style.background = 'color-mix(in srgb, var(--c-brand) ' + Math.round(20 + f * 80) + '%, var(--c-surface-2))';
            i.setAttribute('data-tip', name + ' ' + hh + ':00 · ' + Math.round(f * 100) + '% full on average (' + arr.length + (arr.length === 1 ? ' class)' : ' classes)'));
          }
          row.appendChild(i);
        });
        grid.appendChild(row);
      });
      var axis = el('div', 'r');
      axis.appendChild(el('span'));
      hours.forEach(function (hh) { var s = el('span', '', hh % 3 === 0 ? String(hh) : ''); s.style.textAlign = 'center'; axis.appendChild(s); });
      grid.appendChild(axis);
      host.appendChild(grid);
    }
  };
  HBD.chart = function (host, kind, json) {
    host.textContent = '';
    if (!CHARTS[kind]) return;
    CHARTS[kind](host, JSON.parse(json || '{}'));
    tips(host);
  };

  /* A face for a mood 1..5 (Heavy .. Glowing), drawn into host. */
  HBD.face = function (host, n) {
    var mouth = { 1: 'M9 16.5q3-2.5 6 0', 2: 'M9 16q3-1 6 0', 3: 'M9 15.5h6', 4: 'M9 15q3 2 6 0', 5: 'M8.5 14.5q3.5 3.5 7 0' }[n] || 'M9 15.5h6';
    var s = svg('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'aria-hidden': 'true' });
    s.appendChild(svg('circle', { cx: 12, cy: 12, r: 9 }));
    if (n === 5) s.appendChild(svg('path', { d: 'M8.5 10.5q1-1 2 0M13.5 10.5q1-1 2 0' }));
    else if (n === 1) s.appendChild(svg('path', { d: 'M8.5 10.5h2M13.5 10.5h2' }));
    else { s.appendChild(svg('circle', { cx: 9.5, cy: 10.3, r: 0.9, fill: 'currentColor' })); s.appendChild(svg('circle', { cx: 14.5, cy: 10.3, r: 0.9, fill: 'currentColor' })); }
    s.appendChild(svg('path', { d: mouth }));
    host.textContent = '';
    host.appendChild(s);
  };

  /* ------------------------------------------------------------------ files */
  HBD.download = function (name, text, type) {
    var blob = new Blob([text], { type: type || 'text/plain' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  };
  /* c = a class dict (start, minutes, title, id, studio, teacher) -> a calendar file with a reminder an hour before */
  HBD.ics = function (json) {
    var c = JSON.parse(json);
    function stamp(d) { return new Date(d).toISOString().replace(/[-:]/g, '').replace(/\.\d+/, ''); }
    var end = new Date(new Date(c.start).getTime() + c.minutes * 60000), s = c.studio || {};
    var lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Health Booker//EN', 'BEGIN:VEVENT', 'UID:' + String(c.id).replace(/[^a-z0-9]/gi, '') + '@healthbooker',
      'DTSTAMP:' + stamp(Date.now()), 'DTSTART:' + stamp(c.start), 'DTEND:' + stamp(end),
      'SUMMARY:' + (c.title + ' at ' + (s.name || '')).replace(/[,;]/g, ' '), 'LOCATION:' + ((s.address || s.name || '') + '').replace(/[,;]/g, ' '),
      'DESCRIPTION:' + ('With ' + (c.teacher ? c.teacher.name : '') + '. Booked on Health Booker.').replace(/[,;]/g, ' '),
      'BEGIN:VALARM', 'TRIGGER:-PT1H', 'ACTION:DISPLAY', 'DESCRIPTION:Yoga in an hour', 'END:VALARM', 'END:VEVENT', 'END:VCALENDAR'];
    HBD.download((c.title || 'class').replace(/[^a-z0-9]+/gi, '-').toLowerCase() + '.ics', lines.join('\r\n'), 'text/calendar');
  };
  /* Resolves true when copied; otherwise shows the text to copy by hand and resolves false. */
  HBD.copy = function (text) {
    return new Promise(function (resolve) {
      function manual() { window.prompt('Copy this link:', text); resolve(false); }
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(function () { resolve(true); }, manual);
      else manual();
    });
  };
  HBD.link = function (hash) { return location.href.split('#')[0].split('?')[0] + hash; };
})();
