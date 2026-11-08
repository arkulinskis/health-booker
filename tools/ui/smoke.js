/* Smoke test (tools/ui_test.py runs it at 1280 px and at 390 px): every page address opens without errors, is not
   empty and doesn't scroll sideways. Signed out (landing, Discover, a studio + its direct booking link, a class, a bad
   friend pass, open a studio, sign in / up), then as a new member (Discover + the matcher, a booking end to end:
   waiver -> pass -> booked, Practice tabs, inbox, teach, profile), then as admin (Admin tabs, every back-office tab,
   the class list, the kiosk). Python/JS errors are caught by ui_test.py from the browser log. Resolves to {ok, log}. */
(async function () {
  const log = [], bad = [];
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function until(fn, what, ms) {
    const end = Date.now() + (ms || 20000);
    while (Date.now() < end) { try { const v = fn(); if (v) return v; } catch (e) {} await sleep(150); }
    throw new Error('timed out waiting for: ' + what);
  }
  const q = (s) => document.querySelector(s), qa = (s) => Array.from(document.querySelectorAll(s));
  const errs = [];
  window.addEventListener('error', (e) => errs.push(String(e.message || e)));
  const visible = (el) => !!el && el.getClientRects().length > 0;
  function type(input, value) {
    input.focus(); input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true }));
  }
  function button(re, root) { return qa((root || '') + ' button').find((b) => re.test(b.textContent.trim()) && visible(b)); }
  function check(name, expect) {
    const main = q('.ui-main');
    const text = main ? main.innerText.trim() : '';
    const w = document.documentElement.scrollWidth, vw = screen.width <= 500 ? screen.width : window.innerWidth;
    const problems = [];
    if (text.length < 40) problems.push('empty page');
    if (expect && !new RegExp(expect.source, 'i').test(text)) problems.push('missing ' + expect);
    if (w > vw + 1) {
      const wide = qa('body *').filter((e) => { const r = e.getBoundingClientRect(); return r.width && r.right > vw + 1; })
        .slice(0, 3).map((e) => e.tagName.toLowerCase() + '.' + String(e.className).split(' ').slice(0, 2).join('.'));
      problems.push('scrolls sideways (' + w + ' > ' + vw + ') ' + wide.join(' '));
    }
    if (errs.length) problems.push('errors: ' + errs.splice(0).join(' / '));
    if (problems.length) bad.push(name + ': ' + problems.join('; '));
    log.push((problems.length ? 'BAD  ' : 'ok   ') + name);
  }
  async function open(hash, expect) {
    if (location.hash !== hash) window.UI_READY = false;
    location.hash = hash;
    await until(() => window.UI_READY && location.hash === hash, hash, 40000);
    await sleep(700);
    check(hash, expect);
  }
  const modal = () => qa('.modal, .anvil-modal').find((m) => visible(m) && m.innerText.trim().length > 10);
  async function waitModal(re, what) {
    return until(() => { const m = modal(); return m && re.test(m.innerText) ? m : null; }, what, 30000);
  }
  async function closeModal() {
    const m = modal();
    const close = m && qa('button').filter((b) => m.contains(b)).find((b) => /^(Cancel|Close|Not now)$/.test(b.textContent.trim()) && visible(b));
    if (close) close.click();
    await until(() => !modal(), 'dialog closed', 10000);
    await sleep(300);
  }
  async function dialog(name, opener, expect) {
    if (!opener) { bad.push('dialog ' + name + ': no button to open it'); return; }
    opener.click();
    const dlg = await until(() => modal(), 'dialog ' + name, 20000);
    await sleep(400);
    const problems = [];
    if (expect && !expect.test(dlg.innerText)) problems.push('missing ' + expect);
    if (errs.length) problems.push('errors: ' + errs.splice(0).join(' / '));
    if (problems.length) bad.push('dialog ' + name + ': ' + problems.join('; '));
    log.push((problems.length ? 'BAD  ' : 'ok   ') + 'dialog ' + name);
    await closeModal();
  }
  async function signUp(name, email, password) {
    location.hash = '#auth/signup';
    await until(() => window.UI_READY && qa('.au-card input').length >= 3, 'sign-up form');
    await sleep(400);
    const inputs = qa('.au-card input[type=text], .au-card input[type=email], .au-card input[type=password]');
    type(inputs[0], name); type(inputs[1], email); type(inputs[2], password);
    const tick = q('.au-card input[type=checkbox]'); if (tick && !tick.checked) tick.click();
    button(/Create account/, '.au-card .anvil-role-btn-block').click();
    const end = Date.now() + 40000;
    while (Date.now() < end) {
      if (location.hash === '#discover' && window.UI_READY) return true;
      const msg = q('.au-card .anvil-role-msg-error');
      if (msg && visible(msg) && msg.textContent.trim()) { log.push('sign-up said: ' + msg.textContent.trim()); return false; }
      await sleep(200);
    }
    log.push('sign-up: still on ' + location.hash);
    return false;
  }
  async function signIn(email, password) {
    location.hash = '#auth';
    await until(() => window.UI_READY && qa('.au-card input[type=password]').length, 'sign-in form');
    await sleep(400);
    type(q('.au-card input[type=email]'), email); type(q('.au-card input[type=password]'), password);
    button(/Sign in/, '.au-card .anvil-role-btn-block').click();
    await until(() => location.hash === '#discover' && window.UI_READY, 'signed in as ' + email, 40000);
  }
  async function signOut() {
    q('.anvil-role-avatar button').click();
    await sleep(300);
    button(/Sign out/, '.ui-menu').click();
    await until(() => {
      const a = q('.anvil-role-avatar button');
      return location.hash === '#landing' && window.UI_READY && (!a || !visible(a));
    }, 'signed out');
    await sleep(500);
  }
  try {
    // ---- signed out
    await open('#landing', /Every studio/);
    await open('#discover', /Find your class/);
    await open('#discover/studios', /Studios near you/);
    await open('#studio/sage-and-stone', /Sage/);
    await open('#studio/sage-and-stone/solo', /Booking by/);
    if (visible(q('.ui-nav'))) bad.push('solo link still shows the marketplace menu');
    const classHref = (await until(() => q('.hb-class h3 a[href^="#class/"]'), 'a class link')).getAttribute('href');
    await open(classHref.replace('/solo', ''), /Free cancellation|finished|full|cancelled/);
    await open('#gift/nope', /doesn't exist/);
    await open('#open', /Bring your studio/);
    await open('#auth', /Sign in/);
    await open('#auth/signup', /Create account/);

    // ---- a new member
    const ok = await signUp('Smoke Student', 'smoke' + Date.now() + '@example.com', 'Hb-' + Math.random().toString(36).slice(2) + '-Kq7');
    if (!ok) throw new Error('sign-up failed');
    await sleep(600);
    check('#discover (member)', /Hello, Smoke/);
    await dialog('class matcher', qa('button.ds-match').find(visible), /How do you want to feel/);
    // book a class end to end: waiver -> pass -> booked
    await open('#studio/sage-and-stone', /Schedule/);
    const rows = qa('.hb-class').filter((r) => /left/.test(r.innerText) && !/Full/.test(r.innerText));
    const target = rows[Math.min(3, rows.length - 1)];
    if (!target) throw new Error('no class with mats left');
    await open(target.querySelector('h3 a').getAttribute('href'), /Book/);
    const bookBtn = await until(() => qa('.cl-book .anvil-role-btn-lg button').find(visible), 'the Book button');
    bookBtn.click();
    let m = await waitModal(/quick waiver/, 'the waiver');
    log.push('ok   waiver dialog');
    button(/Sign and continue/, '.anvil-modal').click();
    m = await waitModal(/Choose a pass/, 'the pass shop');
    log.push('ok   pass shop dialog');
    button(/Get this pass/, '.anvil-modal').click();
    m = await waitModal(/You're booked|waitlist/, 'the booked confirmation');
    log.push('ok   booked confirmation');
    await closeModal();
    await until(() => /You're booked|waitlist/.test(q('.cl-book').innerText), 'the class shows the booking', 30000);
    check('class after booking', /booked|waitlist/);
    await open('#practice', /My practice/);
    if (!/Any mat|Mat [A-Z]\d/.test(q('.ui-main').innerText)) bad.push('#practice: the new booking is missing');
    await open('#practice/journal', /journal/);
    await open('#practice/wallet', /Friend passes/);
    await open('#practice/following', /follow/);
    await open('#inbox', /Inbox/);
    await open('#teach', /studio team/);
    await open('#open', /Open your studio/);
    await open('#profile', /Your name/);
    await signOut();

    // ---- admin (ADMIN_EMAILS in Accounts.py): sign up the first time, sign in after that
    const adminPw = 'Hb-smoke-adm-93Kx-7q';
    if (!(await signUp('Admin Tester', 'arkulinskis@gmail.com', adminPw))) await signIn('arkulinskis@gmail.com', adminPw);
    for (const t of ['overview', 'studios', 'feedback', 'users', 'demo']) await open('#admin/' + t, /Admin/);
    for (const t of ['today', 'schedule', 'clients', 'pricing', 'team', 'insights', 'reviews', 'settings'])
      await open('#manage/sage-and-stone/' + t, /Sage/);
    await open('#manage/sage-and-stone/today', /Classes/);
    await dialog('class list', button(/^Class list$/), /checked in/);
    await open('#manage/sage-and-stone/schedule', /New class/);
    await dialog('new class', button(/New class/), /Repeat every week/);
    await open('#kiosk/sage-and-stone', /Welcome to/);
    await open('#discover', /Find your class/);
    await signOut();
    log.push(bad.length ? 'PROBLEMS: ' + bad.join(' | ') : 'PASSED');
    return { ok: !bad.length, log: log };
  } catch (e) {
    log.push(String(e && e.message || e));
    if (bad.length) log.push('PROBLEMS: ' + bad.join(' | '));
    return { ok: false, log: log };
  }
})();
