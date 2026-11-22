// L3 حيّ ‏[DG-01]: لوحاتُ التنقيح — **سطحٌ لم تبلغه أيُّ قاعدةٍ من قواعدنا الخمسِ والثلاثين**.
//
// ## لماذا هذا الملفّ موجود
// ‏`grep debug patches/mihrab-rtl.css` يعيد **صفرَ قواعد**. أي أنّ فجوةَ التنقيح ليست فجوةَ
// قياسٍ فحسب — هي فجوةُ **تغطيةٍ كاملة**. وأربعُ لوحاتٍ (المتغيّرات · كومةُ الاستدعاء ·
// وحدةُ التصحيح · المراقبةُ ونقاطُ التوقّف) لم يُفتَح منها شيءٌ قطُّ في مِجَسّاتنا.
//
// ## وثلاثةُ دروسٍ اشتُريت قبل أن يُكتَب سطرٌ واحد
// ‏(١) **`stopOnEntry` كان سيُعطي لوحةً فارغةً من موضوعها**: الوقفةُ عند الدخول تقع قبل
//     تنفيذ أيّ سطر، فالمتغيّراتُ لم تُسنَد، و`debugExpressionRenderer.ts:99` لا يضيف
//     «‎=‎» أصلًا إلّا إذا كانت للمتغيّر قيمة ⇒ **لا صفَّ يُقاس**، وتُبلَّغ الفجوةُ
//     «لا صفوف» والسببُ تصميمُ الوقفة لا العطب. فالوقفةُ بعبارة debugger بعد الإسنادات.
// ‏(٢) **حضورُ شريط التنقيح ليس بصمةَ توقّف**: ‏`debugToolBar.ts:121` يخفيه في حالة
//     Inactive وحدَها — أي يظهر في Running أيضًا. والبصمةُ **شاهدٌ فريدٌ في قيمة متغيّر**:
//     سلسلةٌ لا ينتجها شيءٌ آخرُ في الدنيا. ظهورُها يعني أنّ محوّلًا حقيقيًّا قوّم إطارًا
//     حقيقيًّا في نطاقٍ مُوسَّع — ولا يزوّرها سطحٌ فارغٌ ولا حالةٌ بائتة.
// ‏(٣) **`proc.kill()` لا يكفي على ويندوز**: المُنقَّحُ **حفيدُ** محراب (يُطلقه مضيفُ
//     الامتدادات)، فيبقى node معلَّقًا ماسكًا cwd داخل tmp فيفشل الحذفُ بـEBUSY. تُقتَل
//     الشجرةُ، **ويُقَرّ عددُ اليتامى بالقياس** لا بالافتراض.
//
// الاستعمال: node tests/runtime/debug_panes.live.mjs [--keep]
// خرج 0 = القياسُ تمّ (نجاحًا أو بفجوةٍ **معلَنة**) · 1 = تأكيدٌ فشل · 2 = خطأ تشغيليّ.
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { CDP, sleep, key, MOD } from "./harness.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const EXE = join(ROOT, ".upstream", "VSCode-win32-x64", "Mihrab.exe");
const PORT = 9337;
const KEEP = process.argv.includes("--keep");

/** المقيسُ في VA-04 — يُقرأ هنا **للمقارنة** لا لإعادة اشتقاقه. */
const EDITOR_FONT_SIZE = 15;
/** أرضيّةُ ارتفاع السطر المشتقّةُ من مقاييس Kawkab Mono ‏[TY-02]. */
// ‏[TY-02] الأرضيّةُ من المصدر الواحد المقيس، لا رقمًا منسوخًا (كان ‎1.88‎ مشتقًّا من
// ‏كونتوراتٍ منفردةٍ لا تركّب علامةً على قاعدة — أنقصَ الحقيقةَ بـ‎0.885em‎).
const INK_FLOOR_EM = JSON.parse(readFileSync(
  new URL("../dx/arabic_ink.measured.json", import.meta.url), "utf8")).composedInkEm;
/** الشاهدُ الفريد: سلسلةٌ لا ينتجها سطحٌ فارغٌ ولا حالةٌ بائتة. */
const SENTINEL = "مِجَسّ-٧٣١";

const log = m => console.log(`▶ ${m}`);
let failed = 0;
const ok = (cond, name, detail = "") => {
  if (cond) console.log(`  ✅ ${name}${detail ? " — " + detail : ""}`);
  else { failed++; console.log(`  ❌ ${name}${detail ? "\n       " + detail : ""}`); }
};
/** فجوةٌ **معلَنة**: لم يُقَس، ويُقال إنّه لم يُقَس. لا pass ولا دفنٌ في «لم ينفتح». */
const gap = (name, why) => console.log(`  ⏭️  ${name} — غير مقيس (فجوة معلَنة): ${why}`);

if (!existsSync(EXE)) { console.error(`❌ لا حزمة مشحونة: ${EXE}`); process.exit(2); }

// ⚠️ **حارسٌ يسبق كلَّ شيء.** ‏`runtimeExecutable` يأخذ مُفسِّرَ هذا المِجَسّ نفسِه — نودٌ
// محمولٌ بلا تثبيت. فإن شُغِّل المِجَسُّ بثنائيّ Electron (وهو حالُ مضيفِ امتدادٍ أو CI
// مضبوطٍ خطأً) فـ`execPath` ليس نودًا، ويُطلق js-debug ثنائيًّا لا يفهم ‏`--inspect`
// فيفشل فشلًا غامضًا. الفشلُ الغامضُ يُقرأ «السطحُ معطوب» وهو ليس كذلك.
if (!/[\\/]node(\.exe)?$/i.test(process.execPath)) {
  gap("DG-01", `المِجَسُّ لا يعمل على node (${process.execPath}) — لا نودَ محمولًا لـrunimeExecutable`);
  process.exit(0);
}

const tmp = mkdtempSync(join(tmpdir(), "mihrab-dg01-"));
const userData = join(tmp, "user-data");
const extDir = join(tmp, "extensions");
const ws = join(tmp, "مساحة");
mkdirSync(join(userData, "User"), { recursive: true });
mkdirSync(extDir, { recursive: true });
mkdirSync(join(ws, ".vscode"), { recursive: true });

const PROGRAM = "برنامج.js";

/**
 * البرنامجُ المُنقَّح. **معرّفان متقابلان في الملفّ نفسِه** — عربيٌّ ولاتينيّ — لأنّ عطبَ
 * المحايد التابع للفقرة عطبُ **تذبذب**: يقع على صفٍّ ولا يقع على شقيقه. فقياسُ صفٍّ
 * واحدٍ يقيس حالةً، وقياسُ الصفّين يقيس **قاعدة**.
 */
function buildWorkspace() {
  writeFileSync(join(ws, PROGRAM),
    "// برنامجُ قياسٍ زائلٌ — يُنشأ ويُمحى في الجلسة نفسِها.\n" +
    "function احسب_الزكاة(نصاب_الذهب) {\n" +
    "  const المجموع = نصاب_الذهب * 2;\n" +
    "  const total = 42;\n" +
    "  const الشاهد = \"" + SENTINEL + "\";\n" +
    "  // الوقفةُ هنا لا عند الدخول: بعد الإسناد يكون للمتغيّرات قيمٌ تُصيَّر.\n" +
    "  debugger;\n" +
    "  return المجموع + total + الشاهد.length;\n" +
    "}\n" +
    "احسب_الزكاة(85);\n", "utf8");

  // تهيئةٌ **واحدة** تُكتَب **قبل** الإطلاق: بأكثرَ من واحدةٍ يُستجوَب المستخدمُ بقائمة
  // اختيار، وبكتابتها بعد الفتح قد لا يلتقطها `debugConfigurationManager`.
  writeFileSync(join(ws, ".vscode", "launch.json"), JSON.stringify({
    version: "0.2.0",
    configurations: [{
      type: "node", request: "launch", name: "مِجَسّ",
      program: "${workspaceFolder}/" + PROGRAM,
      runtimeExecutable: process.execPath,
      cwd: "${workspaceFolder}",
      stopOnEntry: false,
      // صريحًا: بدونه قد يذهب الخرجُ إلى طرفيّةٍ فتُقاس وحدةُ تصحيحٍ فارغة.
      console: "internalConsole",
      skipFiles: [], smartStep: false,
    }],
  }, null, 2), "utf8");
}

// كلُّ مفتاحٍ هنا يمنع نجاحًا كاذبًا أو فجوةً بلا سبب — لا واحدَ منها تحسينٌ للراحة.
writeFileSync(join(userData, "User", "settings.json"), JSON.stringify({
  "window.restoreWindows": "none",
  // بلا هذا يكون غيابُ الشريط **ليس نفيًا**: قد يكون مستضافًا في ودجة الأوامر.
  "debug.toolBarLocation": "floating",
  // تُفتَح لوحةُ التنقيح بلا أمرٍ مترجَمٍ في الطريق (درسُ أسماء الأوامر المخبوزة).
  "debug.openDebug": "openOnDebugBreak",
  "debug.internalConsoleOptions": "openOnSessionStart",
  // بدونه تختفي وحدةُ التصحيح عند انتهاء الجلسة قبل أن تُقاس.
  "debug.console.closeOnEnd": false,
  // **يثبّت الفرعَ المقيس** في debugExpressionRenderer:99-104 (‏« =» لا «: »). بلا
  // تثبيته نقيس فرعًا لا نعرف أيَّهما.
  "debug.showVariableTypes": false,
  // القيمُ المضمَّنة: أوّلُ موضعٍ يمتزج فيه نصٌّ عربيٌّ بسطر كودٍ **داخل** المحرّر.
  "debug.inlineValues": "on",
}, null, 2), "utf8");

/** ⚠️ فخُّ `ELECTRON_RUN_AS_NODE` الموروث — موثَّقٌ في `launch.mjs` و`scm_input.live.mjs`. */
function cleanEnv() {
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  for (const k of Object.keys(env)) if (k.startsWith("VSCODE_")) delete env[k];
  return env;
}

let proc = null;
const launch = () => {
  proc = spawn(EXE, [
    `--remote-debugging-port=${PORT}`, "--remote-allow-origins=*",
    `--user-data-dir=${userData}`,
    // يعزل امتداداتِ المستخدم ولا يمسّ المضمَّنات — و`ms-vscode.js-debug` مضمَّنٌ في
    // الحزمة، فلولا ذلك لكان البندُ كلُّه فجوةً بلا محوّل.
    `--extensions-dir=${extDir}`,
    "--skip-release-notes", "--disable-updates",
    // في الوضع المقيَّد **يُرفَض بدءُ التنقيح صراحةً** ⇒ فجوةٌ بلا سبب.
    "--disable-workspace-trust", "--new-window", ws, join(ws, PROGRAM),
  ], { detached: false, stdio: "ignore", env: cleanEnv() });
};

/**
 * قتلُ **الشجرة** لا العمليّة. والمُنقَّحُ حفيدٌ لا ابن، فـ`proc.kill()` يتركه معلَّقًا
 * ماسكًا `cwd` داخل `tmp` فيفشل الحذف. ثمّ **يُقَرّ عددُ اليتامى بالقياس**: مسارُ `tmp`
 * فريدٌ بحكم `mkdtemp`، فأيُّ نودٍ سطرُ أمره يحويه يتيمُنا نحن لا عمليّةُ المستخدم.
 */
function killTree() {
  try { spawnSync("taskkill", ["/F", "/T", "/PID", String(proc && proc.pid)], { stdio: "ignore" }); }
  catch { /* */ }
}
function countOrphans() {
  try {
    const r = spawnSync("powershell", ["-NoProfile", "-Command",
      "(Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | " +
      "Where-Object { $_.CommandLine -like '*" + tmp.replace(/\\/g, "\\\\") + "*' }).Count"],
      { encoding: "utf8" });
    return parseInt((r.stdout || "").trim(), 10);
  } catch { return NaN; }
}

async function attach(timeoutMs = 120000) {
  const t0 = Date.now();
  for (;;) {
    try { return await CDP.attach(PORT); } catch (e) {
      if (Date.now() - t0 > timeoutMs) throw new Error(`تعذّر الاتّصال بـCDP: ${e.message}`);
      await sleep(1500);
    }
  }
}

// ═════════════════ تعبيراتُ القياس ═════════════════

/**
 * **البصمةُ المقترنة.** ثلاثةٌ معًا، وأقواها الشاهدُ الفريد.
 *
 * ‏`toolbarVisible` هندسيٌّ لا وجوديّ: ‏`show/hide` في المنبع `display` فقط، والعنصرُ
 * يبقى في DOM بعد أوّل ظهور — فـ`querySelector` يصدق **بعد انتهاء الجلسة**.
 */
const LIVE_STOPPED = `(() => {
  const tb = document.querySelector('.debug-toolbar');
  const box = tb ? tb.getBoundingClientRect() : null;
  const frames = [...document.querySelectorAll('.debug-pane .debug-call-stack .stack-frame')]
    .map(f => ((f.querySelector('.file-name') || {}).textContent || '').trim()).filter(Boolean);
  const vals = [...document.querySelectorAll('.debug-variables .expression .value')]
    .map(v => (v.textContent || '').trim());
  return {
    toolbarVisible: !!box && box.height > 4 && !!tb.offsetParent,
    toolbarInDom: !!tb,
    frames: frames.slice(0, 6), frameCount: frames.length,
    sentinel: vals.some(v => v.indexOf(${JSON.stringify(SENTINEL)}) >= 0),
    rowsRendered: document.querySelectorAll('.debug-variables .monaco-list-row').length,
  };
})()`;

/**
 * يُقرأ حين تنفد المهلة: **سببٌ حقيقيّ** بدل «لم ينفتح».
 *
 * ويُقرأ عريضًا عمدًا. «لم يتوقّف» له خمسةُ أسبابٍ مختلفةٍ تمامًا — لا محوّل · تهيئةٌ لم
 * تُلتقَط · البرنامجُ ركض إلى نهايته · اللوحةُ مطويّةٌ فلم تُصيَّر · خطأٌ في البرنامج —
 * وتشخيصٌ واحدٌ لخمسةٍ يجعل الفجوةَ بلا مخرَج.
 */
const WHY_NOT = `(() => ({
  toasts: [...document.querySelectorAll('.notification-list-item-message')]
    .map(n => (n.textContent || '').trim()).slice(0, 6),
  debugPane: !!document.querySelector('.debug-pane'),
  toolbar: !!document.querySelector('.debug-toolbar'),
  panes: [...document.querySelectorAll('.debug-pane .pane, .debug-view-content .pane')].map(p => {
    const h = p.querySelector('.pane-header .title'), b = p.querySelector('.pane-body');
    return { title: h ? h.textContent.trim() : null, expanded: p.classList.contains('expanded'),
             h: b ? Math.round(b.getBoundingClientRect().height) : null,
             rows: p.querySelectorAll('.monaco-list-row').length };
  }),
  repl: [...document.querySelectorAll('.repl-tree .monaco-list-row')]
    .map(r => (r.textContent || '').trim().slice(0, 120)).slice(0, 10),
  toolbarBtns: [...document.querySelectorAll('.debug-toolbar .action-label')]
    .map(a => a.getAttribute('aria-label') || a.className).slice(0, 8),
  status: (() => { const e = document.querySelector('.statusbar .debug'); return e ? e.textContent.trim() : null; })(),
}))()`;

/**
 * خريطةُ محارفَ + قياسُ لوحةٍ من عائلة «‎اسم = قيمة‎» (المتغيّرات والمراقبة معًا).
 *
 * **والمعيارُ «البَينيّة» لا الانعكاس ولا مرساةُ الفقرة**: «‎=‎» يجب أن تقع فيزيائيًّا
 * **بين** رسوم الاسم وصندوقِ القيمة. معيارٌ محايدُ الاتّجاه يصدق في LTR وRTL معًا،
 * ويلتقط بالضبط العطبَ الموصوف — قفزَها إلى الطرف البعيد عن القيمة.
 *
 * **وهو معيارٌ قابلٌ للنقض عمدًا.** ‏`span.name` بندُ flex فيُكتَّل، فيصير فقرةً bidi
 * مستقلّةً قد تستقرّ فيها «‎=‎» على الحافّة المواجهة للقيمة أصلًا. فقد **لا يقع** العطبُ
 * الهندسيّ. ومِجَسٌّ لا يستطيع أن يقول «لم يقع» تنفيذٌ للمقترح لا اختبارٌ له.
 */
const PAIR_MEASURE = (root) => `(() => {
  const pane = document.querySelector(${JSON.stringify(root)});
  if (!pane) return { present: false, why: 'لا لوحةَ في الصفحة' };
  const rows = [...pane.querySelectorAll('.monaco-list-row .expression')];
  if (!rows.length) return { present: false, why: 'اللوحةُ حاضرةٌ بلا صفوفٍ مُصيَّرة (تفريغٌ أو نطاقٌ مطويّ)' };
  const xmap = (el) => {
    const r = document.createRange(), xs = [];
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode())
      for (let i = 0; i < n.data.length; i++) {
        r.setStart(n, i); r.setEnd(n, i + 1);
        const b = r.getBoundingClientRect();
        if (b.width > 0) xs.push({ c: n.data[i], l: b.left, r: b.right });
      }
    return xs;
  };
  const out = [];
  for (const ex of rows) {
    const nameEl = ex.querySelector('.name'), valEl = ex.querySelector('.value');
    if (!nameEl || !valEl) continue;
    const xs = xmap(nameEl);
    const eq = xs.filter(o => o.c === '=');
    const body = xs.filter(o => o.c !== '=' && o.c.trim());
    if (!xs.length || !eq.length || !body.length) continue;
    const nameL = Math.min(...body.map(o => o.l)), nameR = Math.max(...body.map(o => o.r));
    const eqX = (eq[0].l + eq[0].r) / 2;
    const v = valEl.getBoundingClientRect();
    const csn = getComputedStyle(nameEl), cse = getComputedStyle(ex);
    const row = ex.closest('.monaco-list-row');
    out.push({
      nameText: nameEl.textContent || '',
      valueText: (valEl.textContent || '').slice(0, 60),
      aria: row ? (row.getAttribute('aria-label') || '') : '',
      arabic: /[\\u0600-\\u06ff]/.test(nameEl.textContent || ''),
      startsRight: xs[0].l > xs[xs.length - 1].l,
      nameL: Math.round(nameL), nameR: Math.round(nameR), eqX: Math.round(eqX),
      valL: Math.round(v.left), valR: Math.round(v.right),
      between: (eqX > nameR && eqX < v.left) || (eqX < nameL && eqX > v.right),
      gapInner: Math.round(Math.min(Math.abs(v.left - nameR), Math.abs(nameL - v.right))),
      dirName: csn.direction, bidiName: csn.unicodeBidi, dirRow: cse.direction,
      fontSizePx: parseFloat(cse.fontSize), fontFamily: cse.fontFamily,
      // ‏[DG-01 · رقعة النواة 031] **اقتران** الحبر بالصفّ لا حجمُ الحبر وحدَه.
      // ارتفاعُ الصفّ يُحسَب في JS من FONT.sidebarSize22 المشتقّ من مفتاح حجمِ خطّ
      // الشريط الجانبيّ؛ فالمقياسُ الصحيح أن يُشتقَّ الحبرُ من المصدر نفسِه. ونقرأ
      // المتغيّرَ **من الحاوية المُصيَّرة** لا من الإعداد: قاعدةٌ حاضرةٌ في الورقة
      // ومتغيّرٌ خارجَ نطاقها يُعطيان القيمةَ الاحتياطيّةَ بصمت.
      sidebarVar: (getComputedStyle(document.documentElement)
        .getPropertyValue('--vscode-workbench-sidebar-font-size') || '').trim()
        || (() => { const sb = ex.closest('.part.sidebar, .part.auxiliarybar, .part.panel');
                    return sb ? getComputedStyle(sb)
                      .getPropertyValue('--vscode-workbench-sidebar-font-size').trim() : ''; })(),
      rowHeightPx: row ? Math.round(row.getBoundingClientRect().height) : null,
      inPanel: !!ex.closest('.part.panel'),
    });
  }
  return { present: true, count: out.length, list: out };
})()`;

/** كومةُ الاستدعاء — **رقمان يفصلان**، لا حكمٌ واحد. */
const STACK_MEASURE = `(() => {
  const frames = [...document.querySelectorAll('.debug-pane .debug-call-stack .stack-frame')];
  if (!frames.length) return { present: false, why: 'لا إطاراتٍ مُصيَّرة' };
  const xmap = (el) => {
    if (!el) return [];
    const r = document.createRange(), xs = [];
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode())
      for (let i = 0; i < n.data.length; i++) {
        r.setStart(n, i); r.setEnd(n, i + 1);
        const b = r.getBoundingClientRect();
        if (b.width > 0) xs.push({ c: n.data[i], l: b.left });
      }
    return xs;
  };
  const dirOf = (el) => { const xs = xmap(el); return xs.length ? xs[0].l > xs[xs.length - 1].l : null; };
  const out = [];
  for (const f of frames.slice(0, 5)) {
    const label = f.querySelector('.label.expression') || f.querySelector('.label');
    const file = f.querySelector('.file');
    const fname = f.querySelector('.file-name');
    const lnum = f.querySelector('.line-number');
    if (!label || !file || !fname) continue;
    const lb = label.getBoundingClientRect(), fb = file.getBoundingClientRect();
    const nb = fname.getBoundingClientRect();
    const qb = lnum ? lnum.getBoundingClientRect() : null;
    const cs = getComputedStyle(f);
    out.push({
      label: (label.textContent || '').trim(), file: (fname.textContent || '').trim(),
      line: lnum ? (lnum.textContent || '').trim() : null,
      labelArabic: /[\\u0600-\\u06ff]/.test(label.textContent || ''),
      labelStartsRight: dirOf(label), fileStartsRight: dirOf(fname),
      lineStartsRight: lnum ? dirOf(lnum) : null,
      fileBidi: getComputedStyle(fname).unicodeBidi,
      labelBox: { l: Math.round(lb.left), r: Math.round(lb.right) },
      fileBox: { l: Math.round(fb.left), r: Math.round(fb.right) },
      innerGap: qb ? Math.round(Math.abs(nb.left - qb.right)) : null,
      outerGap: Math.round(Math.abs(lb.left - fb.right)),
      padStart: parseFloat(cs.paddingRight), padEnd: parseFloat(cs.paddingLeft),
      dir: cs.direction,
    });
  }
  return { present: true, count: out.length, list: out };
})()`;

/**
 * وحدةُ التصحيح — **نسخةٌ ثانيةٌ من ‏SC-01 حرفيًّا**: ‏`repl.ts:750` ينشئ حقلَ الإدخال
 * بـ`getSimpleCodeEditorWidgetOptions()` و`simpleEditorOptions.ts:61` يمرّر
 * ‏`isSimpleWidget: true` — العلّةُ البنيويّةُ نفسُها. وأسوأُ منها: لا تقرأ `editor.*`
 * إطلاقًا بل ثلاثةَ مفاتيحَ خاصّةٍ افتراضاتُها ‎14‎ و`'default'` و‎1.4em‎.
 */
const REPL_MEASURE = `(() => {
  const box = document.querySelector('.repl .repl-input-wrapper .monaco-editor');
  const ctrl = (() => {
    let best = null, area = -1;
    for (const ed of document.querySelectorAll('.monaco-editor')) {
      if (ed.closest('.repl') || ed.closest('.scm-view')) continue;
      const r = ed.getBoundingClientRect(); const a = r.width * r.height;
      if (a <= area) continue;
      const l = ed.querySelector('.view-line'); if (!l) continue;
      area = a; best = l;
    }
    return best;
  })();
  const of = (line) => {
    if (!line) return null;
    const cs = getComputedStyle(line);
    const size = parseFloat(cs.fontSize) || 1;
    return {
      fontFamily: cs.fontFamily, fontSizePx: parseFloat(cs.fontSize),
      lineHeightEm: +((parseFloat(cs.lineHeight) || 0) / size).toFixed(3),
      features: cs.fontFeatureSettings, direction: cs.direction,
    };
  };
  const inputLine = box ? box.querySelector('.view-line') : null;
  const results = [...document.querySelectorAll('.repl-tree .evaluation-result.expression .value, .repl-tree .value')]
    .map(v => (v.textContent || '').trim()).filter(Boolean);
  const src = document.querySelector('.repl-tree .source');
  let source = null;
  if (src) {
    const cs = getComputedStyle(src), b = src.getBoundingClientRect();
    const row = src.closest('.monaco-list-row');
    const rb = row ? row.getBoundingClientRect() : null;
    source = { marginStart: cs.marginRight, marginEnd: cs.marginLeft, textAlign: cs.textAlign,
               direction: cs.direction,
               fromRowStart: rb ? Math.round(rb.right - b.right) : null,
               fromRowEnd: rb ? Math.round(b.left - rb.left) : null };
  }
  return {
    present: !!box, input: of(inputLine), control: of(ctrl),
    results: results.slice(0, 6),
    sentinel: results.some(v => v.indexOf(${JSON.stringify(SENTINEL)}) >= 0),
    source,
  };
})()`;

/**
 * ‏**يقيس أثرَ قاعدةٍ مرشّحةٍ حيًّا: قبل ⇒ حقن ⇒ بعد ⇒ نزع.** لا تُكتَب قاعدةٌ إلّا وقد
 * غيّرت شيئًا فعلًا — درسُ ‏SC-01 حين تبيّن أنّ حقنَ `line-height` لا يكبّر صندوقَ السطر
 * لأنّ Monaco يبصمه سمةً مضمَّنة، فتُجُنِّبت قاعدةٌ ميّتة.
 *
 * والنظافةُ **مُتحقَّقٌ منها لا مفترَضة**: ورقةٌ عالقةٌ من قياسٍ سابقٍ تجعل «قبل» مُصلَحًا
 * أصلًا فيُقرأ `changed:false` «لا جدوى» وهو «مُطبَّقٌ سلفًا».
 */
const RULE_TRY = (sel, css, reader) => `(() => {
  for (const s of document.querySelectorAll('style[data-mihrab-probe]')) s.remove();
  const stale = document.querySelectorAll('style[data-mihrab-probe]').length;
  const read = () => {
    const el = document.querySelector(${JSON.stringify(sel)});
    if (!el) return null;
    const cs = getComputedStyle(el), b = el.getBoundingClientRect();
    return Object.assign({
      inline: el.getAttribute('style'),
      w: Math.round(b.width), h: Math.round(b.height),
      l: Math.round(b.left), r: Math.round(b.right),
    }, (${reader})(el, cs));
  };
  const before = read();
  if (!before) return { applicable: false, why: 'لا عنصرَ يطابق المُحدِّد' };
  const s = document.createElement('style');
  s.setAttribute('data-mihrab-probe', '1');
  s.textContent = ${JSON.stringify(css)};
  document.head.appendChild(s);
  const after = read();
  s.remove();
  const left = document.querySelectorAll('style[data-mihrab-probe]').length;
  // **الخاصّيّةُ تغيّرت ≠ الحبرُ تحرّك.** قاعدةٌ تقلب قيمةً محسوبةً ولا تُزحزح صندوقًا
  // قاعدةٌ ميّتةٌ بصريًّا — تجتاز حارسَ الجدوى السطحيَّ وتُشحَن بلا أثر. فيُفصَل الحكمان.
  const geom = (o) => o && [o.l, o.r, o.w, o.h].join(',');
  return { applicable: true, stale, left, before, after,
           changed: JSON.stringify(before) !== JSON.stringify(after),
           moved: geom(before) !== geom(after) };
})()`;

// ═════════════════ التشغيل ═════════════════

let cdp = null;

/**
 * يفتح **جزءَ التنقيح** — والدرسُ اشتُري بقياس.
 *
 * كان المِجَسُّ يعتمد على `debug.openDebug: "openOnDebugBreak"` (وهو افتراضُ المنبع
 * أصلًا)، فقاس فبلغَ حالًا لم تخطر: الجلسةُ **متوقّفةٌ فعلًا** — شريطُ التنقيح ظاهرٌ
 * وزرُّ «متابعة» فيه، ووحدةُ التصحيح تعرض سطرَ الإطلاق — و`.debug-pane` **غيرُ موجودةٍ
 * في DOM إطلاقًا**. أي أنّ لوحاتِ المتغيّرات وكومةِ الاستدعاء **لم تُصيَّر**، فتُقرأ
 * «صفرُ صفوف» ويُظنّ أنّ الوقفةَ لم تقع.
 *
 * وهو **الفخُّ الموثَّقُ ثلاثَ مرّاتٍ في هذا المستودع** بصيغةٍ رابعة: نطاقٌ بلا محتوًى
 * يُبلِّغ «نظيف» بلا أن يمسح شيئًا — وهنا يُبلِّغ «لم يتوقّف» بلا أن ينظر.
 *
 * فيُفتَح بالوتر **داخل حلقة تحقّق** (‏Ctrl+Shift+D مبدِّلٌ لا فاتحٌ صرف — درسُ
 * ‏`openScm`)، ثمّ بأيقونة شريط النشاط إن لم يكفِ. ومعرِّفُ الأيقونة ثابتٌ لا يتغيّر
 * بتغيّر لغة الواجهة (‏درسُ أسماء الأوامر المخبوزة عربيّةً في الحزمة).
 */
async function openDebugView() {
  const has = `!!document.querySelector('.debug-pane')`;
  for (let i = 0; i < 6; i++) {
    if (await cdp.evaluate(has)) return true;
    if (i < 3) {
      await key(cdp, 68, "KeyD", MOD.CTRL | MOD.SHIFT);
    } else {
      const pt = await cdp.evaluate(`(() => {
        const a = document.querySelector('.activitybar [aria-label*="Debug" i], .activitybar .codicon-debug-alt, .activitybar li[id*="debug" i] a');
        if (!a) return null;
        const b = a.getBoundingClientRect();
        if (b.width < 4 || b.height < 4) return null;
        return { x: Math.round(b.left + b.width / 2), y: Math.round(b.top + b.height / 2) };
      })()`);
      if (!pt) return false;
      await cdp.cmd("Input.dispatchMouseEvent", { type: "mousePressed", x: pt.x, y: pt.y, button: "left", clickCount: 1 });
      await cdp.cmd("Input.dispatchMouseEvent", { type: "mouseReleased", x: pt.x, y: pt.y, button: "left", clickCount: 1 });
    }
    await sleep(1200);
  }
  return !!(await cdp.evaluate(has));
}

/**
 * فتحُ نطاقاتِ لوحة المتغيّرات المطويّة.
 *
 * الوقفةُ تُصيِّر صفَّ نطاقٍ لكلِّ نطاق (‏Local · Global)، وطيُّها أو فتحُها **حالةُ عرضٍ
 * محفوظةٌ في ملفّ التعريف** لا نتيجةُ الجلسة. فمساحةٌ زائلةٌ بملفِّ تعريفٍ جديدٍ قد
 * تُصيِّرها مطويّةً، فلا تظهر قيمةُ متغيّرٍ واحدةٍ — ويُقرأ ذلك «الوقفةُ لم تقع».
 * يُنقَر مثلثُ الطيّ على كلِّ صفٍّ `aria-expanded="false"`؛ ولا يُنقَر شيءٌ إن كانت
 * مفتوحةً سلفًا، فالدالّةُ محايدةٌ حين لا عملَ لها.
 */
async function expandScopes() {
  const pts = await cdp.evaluate(`(() => {
    const out = [];
    for (const r of document.querySelectorAll('.debug-variables .monaco-list-row[aria-expanded="false"]')) {
      const t = r.querySelector('.monaco-tl-twistie') || r;
      const b = t.getBoundingClientRect();
      if (b.width < 2 || b.height < 2) continue;
      out.push({ x: Math.round(b.left + b.width / 2), y: Math.round(b.top + b.height / 2) });
    }
    return out.slice(0, 4);
  })()`);
  for (const pt of (pts || [])) {
    await cdp.cmd("Input.dispatchMouseEvent", { type: "mousePressed", x: pt.x, y: pt.y, button: "left", clickCount: 1 });
    await cdp.cmd("Input.dispatchMouseEvent", { type: "mouseReleased", x: pt.x, y: pt.y, button: "left", clickCount: 1 });
    await sleep(400);
  }
  return (pts || []).length;
}

/** إيقافُ الجلسة **بإقرارٍ بالقياس** لا بادّعاء: يُنتظَر اختفاءُ الشريط فعلًا. */
async function stopSession() {
  try {
    await key(cdp, 116, "F5", MOD.SHIFT);
    for (let i = 0; i < 20; i++) {
      await sleep(500);
      const alive = await cdp.evaluate(
        `(() => { const t = document.querySelector('.debug-toolbar'); return !!t && !!t.offsetParent; })()`);
      if (!alive) return true;
    }
  } catch { /* */ }
  return false;
}

try {
  log("بناءُ مساحةِ تنقيحٍ زائلةٍ ببرنامجٍ عربيٍّ ولاتينيٍّ متجاورَين…");
  buildWorkspace();

  log("إطلاق النسخة المشحونة بملفّ تعريفٍ ومجلّدِ امتداداتٍ معزولَين…");
  launch();
  cdp = await attach();
  await sleep(9000);

  // ═══ بدءُ الجلسة: F5 محايدٌ للتخطيط ولا يمرّ باسم أمرٍ مترجَم ═══
  log("F5 — وانتظارُ وقفةٍ حقيقيّةٍ بشاهدٍ فريد…");
  await key(cdp, 116, "F5", 0);

  // **المرحلةُ الأولى: جلسةٌ حيّة.** أوّلُ تنشيطٍ لـjs-debug بطيء، فالمهلةُ سخيّة.
  let live = null;
  const t0 = Date.now();
  while (Date.now() - t0 < 45000) {
    await sleep(500);
    live = await cdp.evaluate(LIVE_STOPPED);
    if (live && live.toolbarVisible) break;
  }

  // **المرحلةُ الثانية: السطحُ مفتوح.** الوقفةُ لا تفتح جزءَ التنقيح عندنا، ولوحاتُه
  // غيرُ مُصيَّرةٍ حتّى يُفتَح — فطلبُ الصفوف قبل الفتح قياسُ فراغٍ يُقرأ «لم يتوقّف».
  if (live && live.toolbarVisible && !(await openDebugView())) {
    gap("DG-01: فتحُ جزء التنقيح", "لم تُصيَّر .debug-pane بالوتر ولا بأيقونة شريط النشاط");
  }

  // **المرحلةُ الثالثة: وقفةٌ حقيقيّةٌ بشاهدٍ فريد.**
  const t1 = Date.now();
  while (Date.now() - t1 < 30000) {
    live = await cdp.evaluate(LIVE_STOPPED);
    if (live && live.toolbarVisible && live.frameCount >= 1 && live.sentinel) break;
    // النطاقاتُ قد تُصيَّر **مطويّةً**، فتُقرأ صفّان اثنان بلا شاهدٍ فيهما ويُحكَم «لم
    // يتوقّف» على جلسةٍ متوقّفةٍ فعلًا — تشخيصٌ واحدٌ لسببٍ آخرَ تمامًا. والطيُّ حالةُ
    // عرضٍ لا حالةُ جلسة، فيُفتَح كما يُفتَح جزءُ التنقيح: خطوةُ تهيئةٍ لا قياس.
    await expandScopes();
    await sleep(500);
  }

  const stopped = !!(live && live.toolbarVisible && live.frameCount >= 1 && live.sentinel);
  if (!stopped) {
    const why = await cdp.evaluate(WHY_NOT);
    const bits = live
      ? `شريط=${live.toolbarVisible} · إطارات=${live.frameCount} · شاهد=${live.sentinel} · صفوف=${live.rowsRendered}`
      : "لا قراءة";
    const toast = (why && why.toasts && why.toasts.length) ? " · إشعار: " + why.toasts.join(" | ") : "";
    gap("DG-01: جلسةُ تنقيحٍ متوقّفة", `${bits}${toast}`);
    console.log(`       تشخيص: ${JSON.stringify(why)}`);
  } else {
    console.log(`  · إطارات: ${JSON.stringify(live.frames)} · صفوفُ متغيّرات: ${live.rowsRendered}`);
    ok(true, "DG-01: جلسةٌ حيّةٌ متوقّفةٌ بشاهدٍ فريدٍ في قيمة متغيّر", SENTINEL);

    // ═══ (أ) لوحةُ المتغيّرات — وم-١٨ قابلٌ للنقض ═══
    const v = await cdp.evaluate(PAIR_MEASURE(".debug-variables"));
    if (!v.present) {
      gap("DG-01/أ: لوحةُ المتغيّرات", v.why);
    } else {
      console.log(`  · صفوفٌ مقيسة: ${v.count}`);
      for (const r of v.list) {
        console.log(`    ${r.arabic ? "ع" : "ل"} «${r.nameText}» = ${r.valueText} · ` +
          `بَينيّة=${r.between} · فجوة=${r.gapInner}px · ${r.fontSizePx}px · ${r.bidiName}`);
      }
      const ar = v.list.find(r => r.arabic);
      const lat = v.list.find(r => !r.arabic);

      // (١) **الثباتُ عبر الخطّ — الأقوى**: عطبُ المحايد التابعِ للفقرة عطبُ تذبذب،
      //     يقع على صفٍّ ولا يقع على شقيقه. فالحكمُ على القاعدة لا على الحالة.
      if (!ar || !lat) {
        gap("DG-01/أ١: ثباتُ موضع «=» بين صفٍّ عربيٍّ وآخرَ لاتينيّ",
          `لم يُصيَّر الصفّان معًا (عربيّ=${!!ar} · لاتينيّ=${!!lat}) — تفريغُ الشجرة أو نطاقٌ مطويّ`);
      } else {
        ok(ar.between === lat.between && ar.between === true,
          "DG-01/أ١: «=» بين الاسم والقيمة في الصفّين معًا [م-١٨]",
          `عربيّ=${ar.between} · لاتينيّ=${lat.between}`);
      }

      // (٢) **لبُّ م-١٨ في السلسلة لا في البكسل**: المنبعُ يبني `name + ' ='` عقدةَ نصٍّ
      //     واحدة. ولا مُحدِّدَ CSS يصل إلى **جزءٍ** من عقدة نصّ — `unicode-bidi` تعزل
      //     صندوقًا لا محرفًا. فالعلاجُ منبعيٌّ قطعًا.
      //
      // **وهذا يُقاس ويُعلَن، ولا يُؤكَّد.** كان تأكيدًا أحمرَ يسقط في كلّ تشغيلة — وهو
      // ‏`DG-02`: بندٌ **مفتوحٌ عن قرارٍ مكتوب** لا انحدارٌ يقع. وأحمرُ دائمٌ على قرارٍ
      // مقصودٍ يُعلِّم تجاهُلَ الأحمر، فيمرّ الانحدارُ الحقيقيُّ يومَ يقع. وقد قُرئ المسارُ
      // بعدَها فسقط تعليلُ الضرر نفسُه: التسميةُ الوصوليّةُ تُبنى من `name`/`value`
      // مباشرةً (‏`variablesView.ts:664`) فلا تمرّ بالسلسلة، و`user-select: none` على
      // ‏`.monaco-list` يمنع النسخَ منها. فلا مستهلِكَ متضرِّرًا مُثبَتًا — ويُقال رقمًا.
      if (ar) {
        const glued = /[؀-ۿ]\s*=\s*$/u.test(ar.nameText);
        const isolated = ar.nameText.indexOf("⁨") >= 0;
        if (glued && !isolated) {
          gap("DG-01/أ٢: «=» ملصَقةٌ بالاسم في عقدة النصّ [DG-02 · م-١٨]",
            `النصّ=${JSON.stringify(ar.nameText)} — علاجُه منبعيٌّ (فصلُ العنصر أو FSI/PDI)، ` +
            `ولا ضررَ مقيسًا: الموضعُ البصريُّ صحيحٌ (أ١)، والتسميةُ الوصوليّةُ لا تمرّ بالسلسلة`);
        } else {
          ok(true, "DG-01/أ٢: «=» مفصولةٌ أو معزولةٌ في عقدة النصّ [م-١٨]",
            `النصّ=${JSON.stringify(ar.nameText)} · عزلٌ صريح=${isolated} — ` +
            `تغيَّر المنبعُ أو قُبِل المقترح`);
        }
      }

      // (٣) حجمُ الخطّ — **والمقياسُ تبدّل، فيُقال لماذا**.
      //
      // كان التوكيدُ هنا `fontSizePx >= 14` مسنودًا بـVA-04، وكان **يطلب المستحيلَ
      // بغير وجهه**: ارتفاعُ الصفّ في هذه الشجرة يُحسَب في JS من `FONT.sidebarSize22`
      // (‏`variablesView.ts:371` ⇐ `font.ts:166`)، وهو مشتقٌّ من
      // ‏`workbench.sideBar.experimental.fontSize`. فإجبارُ الحبر على ‎15px‎ من الورقة
      // كان **يفصله عن صندوقه** — حبرٌ أكبرُ في صفٍّ ما زال محسوبًا على ‎13‎.
      //
      // والمقياسُ الصحيحُ **اقترانٌ لا عتبة**: أن يُشتقَّ الحبرُ من المصدر الذي يُشتقّ
      // منه الصفُّ. وذلك ما تفعله رقعةُ النواة ‎031‎. والتوكيدُ يقيس الاقترانَ نفسَه، فلو
      // شُحنت القاعدةُ ولم يبلغها المتغيّرُ (نطاقٌ خاطئ، أو اللوحةُ سُحبت إلى الأسفل)
      // سقط — وهو بالضبط الأخضرُ الكاذبُ الذي يتربّص بهذا الإصلاح.
      const row0 = (ar || lat || {});
      const fs = row0.fontSizePx;
      const svar = parseFloat(row0.sidebarVar || "");
      if (fs) {
        if (row0.inPanel) {
          gap("DG-01/أ٣: اقترانُ حبر الشجرة بمصدر ارتفاع صفّها",
            "اللوحةُ في الجزء السفليّ — خارجَ نطاق متغيّر الشريط الجانبيّ، وذلك حدٌّ مكتوبٌ في م-٢١ لا انحدار");
        } else if (!Number.isFinite(svar)) {
          gap("DG-01/أ٣: اقترانُ حبر الشجرة بمصدر ارتفاع صفّها",
            "لم يُقرأ ‎--vscode-workbench-sidebar-font-size‎ من أيّ حاوية");
        } else {
          ok(Math.abs(fs - svar) <= 0.6,
            "DG-01/أ٣: حبرُ شجرة التنقيح مقترنٌ بمفتاح حجم خطّ الشريط [رقعة ‎031‎]",
            `الحبرُ ${fs}px والمتغيّرُ ${svar}px — فرقٌ ${(fs - svar).toFixed(2)}px. ` +
            `القاعدةُ ‎031‎ تربط الطرفين؛ وتباعدُهما يعني إمّا أنّ الرقعةَ لم تُشحَن ` +
            `وإمّا أنّ محدِّدًا أخصَّ منها يسبقها.`);
          // وارتفاعُ الصفّ من المصدر نفسِه: ‎22/13‎ من قيمة المفتاح.
          if (row0.rowHeightPx) {
            const expected = svar * 22 / 13;
            ok(Math.abs(row0.rowHeightPx - expected) <= 2,
              "DG-01/أ٣ب: ارتفاعُ الصفّ مشتقٌّ من المفتاح نفسِه (‎×22/13‎)",
              `المقيس ${row0.rowHeightPx}px والمتوقَّع ${expected.toFixed(1)}px — ` +
              `تباعدُهما يعني أنّ الطرفين عادا إلى مصدرين، فيعود الحبرُ ينفصل عن صندوقه.`);
          }
        }
      }

      // (٤) فجوةُ القيمة: `.value { margin-left: 6px }` فيزيائيّة ⇒ في RTL تقع على
      //     الجانب البعيد فتلتصق القيمةُ بالاسم وتفغر فجوةً حيث لا تُرى.
      const g = (ar || lat || {}).gapInner;
      if (g !== undefined) {
        ok(g >= 4, "DG-01/أ٤: فجوةٌ بين الاسم والقيمة (margin منطقيٌّ لا فيزيائيّ)",
          `${g}px`);
      }
    }

    // ═══ (ب) كومةُ الاستدعاء — عائلةُ القاعدة 30 ═══
    const st = await cdp.evaluate(STACK_MEASURE);
    if (!st.present) {
      gap("DG-01/ب: كومةُ الاستدعاء", st.why);
    } else {
      const f = st.list.find(x => x.labelArabic) || st.list[0];
      console.log(`  · إطار: «${f.label}» · ${f.file}:${f.line} · ` +
        `داخليّة=${f.innerGap}px خارجيّة=${f.outerGap}px · حشوة ${f.padStart}/${f.padEnd}`);
      // الضابطُ: اسمُ الدالّة في مبتدأ القراءة (يقيس dir على الحاوية).
      ok(f.labelBox.r >= f.fileBox.r,
        "DG-01/ب١: اسمُ الدالّة في مبتدأ القراءة العربيّة",
        `label.r=${f.labelBox.r} · file.r=${f.fileBox.r}`);
      // لكلِّ نصٍّ اتّجاهُه: الاسمُ العربيُّ يبدأ يمينًا، واسمُ الملفّ اللاتينيُّ يسارًا.
      if (f.labelArabic) {
        ok(f.labelStartsRight === true, "DG-01/ب٢: اسمُ الدالّة العربيُّ يُصيَّر RTL", `${f.label}`);
      }
      // **الحكمُ من محتوى الاسم لا من افتراضِ لاتينيّته.** كان التأكيدُ يشترط LTR دائمًا،
      // فأحمرّ على `برنامج.js` — واسمُ الملفّ العربيُّ هو **حالُ مستخدمِ محرابٍ الغالبة**
      // لا الحالةُ الشاذّة. حارسٌ يحمرّ على السويّ يُعلَّم تجاهُلُه كما يُعلَّم الأخضرُ الكاذب.
      const fileArabic = /[؀-ۿ]/.test(f.file || "");
      ok(f.fileStartsRight === fileArabic,
        `DG-01/ب٣: اسمُ الملفّ يتّجه بمحتواه (${fileArabic ? "عربيٌّ ⇒ RTL" : "لاتينيٌّ ⇒ LTR"})`,
        `${f.file} · unicode-bidi=${f.fileBidi}`);
      // الفجوتان: رقمان يفصلان، لا استنتاج.
      if (f.innerGap !== null) {
        ok(f.innerGap >= 6 && Math.abs(f.innerGap - f.outerGap) < 6,
          "DG-01/ب٤: فجوتا اسمِ الملفّ ورقمِ السطر متوازنتان (margin منطقيّ)",
          `داخليّة=${f.innerGap}px · خارجيّة=${f.outerGap}px`);
      } else {
        gap("DG-01/ب٤: فجوتا الإطار", "لا رقمَ سطرٍ مُصيَّرًا في الإطار");
      }
      // الحشوةُ الطرفيّة: `padding-right: 12px` فيزيائيّة على `.stack-frame`.
      //
      // **فجوةٌ معلَنةٌ لا تأكيد.** القاعدةُ المرشَّحةُ جُرِّبت بالحقن الحيّ فلم تُسقِط
      // الحشوةَ الفيزيائيّة، فلم تُشحَن — والسببُ مكتوبٌ في `mihrab-rtl.css` عند القاعدة
      // ‎38/ج‎: «ولا تُشحَن قاعدةٌ لم تثبت جدواها ولو بدت صحيحة». وتأكيدٌ أحمرُ على قرارٍ
      // مكتوبٍ ليس حراسةً بل تدريبٌ على تجاهُل الأحمر. فيُقاس الرقمُ ويُعلَن.
      if (f.padEnd >= f.padStart) {
        ok(true, "DG-01/ب٥: حشوةُ الإطار على طرف نهاية القراءة (padding-inline-end)",
          `بداية=${f.padStart}px · نهاية=${f.padEnd}px`);
      } else {
        gap("DG-01/ب٥: حشوةُ إطار كومة الاستدعاء فيزيائيّة",
          `بداية=${f.padStart}px · نهاية=${f.padEnd}px — القاعدةُ ‎38/ج‎ جُرِّبت فلم تُثبِت ` +
          `جدواها فلم تُشحَن؛ قرارٌ مكتوبٌ لا انحدار`);
      }
      // رقمُ السطر «12:5»: نقطتان بين رقمين ⇒ يبقى بترتيبه.
      if (f.lineStartsRight !== null) {
        ok(f.lineStartsRight === false, "DG-01/ب٦: رقمُ السطر يبقى بترتيبه", `${f.line}`);
      }
    }

    // ═══ (ج) وحدةُ التصحيح — نسخةٌ ثانيةٌ من SC-01 ═══
    log("قياسُ وحدة التصحيح (‏isSimpleWidget — العلّةُ البنيويّةُ نفسُها)…");
    const r0 = await cdp.evaluate(REPL_MEASURE);
    if (!r0.present) {
      gap("DG-01/ج: وحدةُ التصحيح", "لم يُصيَّر حقلُ الإدخال — راجِع debug.internalConsoleOptions");
    } else if (!r0.input) {
      gap("DG-01/ج: وحدةُ التصحيح", "الحقلُ حاضرٌ بلا سطرٍ مُصيَّر (اللوحةُ مخفيّةٌ فلم تُطبَّق أنماطُها)");
    } else {
      const i = r0.input, c = r0.control;
      console.log(`  · الوحدة: ${i.fontSizePx}px · ${i.lineHeightEm}em · ${i.fontFamily}`);
      if (c) console.log(`  · الضابط (المحرّر): ${c.fontSizePx}px · ${c.lineHeightEm}em · ${c.fontFamily}`);
      ok(i.fontSizePx >= EDITOR_FONT_SIZE - 1,
        `DG-01/ج١: حجمُ خطّ وحدة التصحيح ≥ ${EDITOR_FONT_SIZE - 1}`,
        `المقيس ${i.fontSizePx}px (‏debug.console.fontSize افتراضُه 14)`);
      ok(i.lineHeightEm >= INK_FLOOR_EM,
        `DG-01/ج٢: ارتفاعُ سطر الوحدة ≥ أرضيّة الحبر ${INK_FLOOR_EM}em [TY-02]`,
        `المقيس ${i.lineHeightEm}em (‏lineHeightEm في المنبع 1.4)`);
      if (c) {
        ok(i.fontFamily === c.fontFamily,
          "DG-01/ج٣: وجهُ الوحدة هو وجهُ المحرّر (‏debug.console.fontFamily لا يبلغه خطُّنا)",
          `الوحدة=${i.fontFamily}`);
      } else {
        gap("DG-01/ج٣: وجهُ وحدة التصحيح", "لا سطرَ محرّرٍ ضابطًا للمقارنة");
      }
      if (r0.source) {
        const s = r0.source;
        console.log(`  · رابطُ المصدر: هوامش ${s.marginStart}/${s.marginEnd} · ` +
          `من المبتدأ ${s.fromRowStart}px · من المنتهى ${s.fromRowEnd}px`);
        // `margin-left:auto` في صفٍّ RTL يمتصّ الفراغَ من الجانب الخطأ فيدفع الرابطَ
        // إلى مبتدأ القراءة بدل منتهاها.
        if (s.fromRowEnd !== null) {
          ok(s.fromRowEnd <= 12, "DG-01/ج٤: رابطُ المصدر على طرف نهاية القراءة",
            `من المنتهى ${s.fromRowEnd}px · من المبتدأ ${s.fromRowStart}px`);
        }
      } else {
        gap("DG-01/ج٤: رابطُ المصدر في الوحدة", "لا سطرَ مخرَجٍ يحمل مصدرًا");
      }
    }

    // ═══ (د) المراقبة — صياغةُ م-١٨ نفسُها بجذرٍ آخر ═══
    const w = await cdp.evaluate(PAIR_MEASURE(".debug-watch"));
    if (!w.present) {
      gap("DG-01/د: لوحةُ المراقبة", w.why + " (لا تعبيرَ مراقبةٍ مضاف — سطحٌ يحتاج محفِّزًا)");
    } else {
      ok(w.list.every(r => r.between),
        "DG-01/د: «=» بين الاسم والقيمة في لوحة المراقبة", `${w.count} صفًّا`);
    }

    // ═══ (هـ) نقاطُ التوقّف ═══
    const bp = await cdp.evaluate(`(() => {
      const rows = [...document.querySelectorAll('.debug-breakpoints .monaco-list-row')];
      if (!rows.length) return { present: false };
      const r = rows[0], b = r.getBoundingClientRect();
      const icon = r.querySelector('.icon, .codicon'), name = r.querySelector('.file-path, .name');
      const ln = r.querySelector('.line-number');
      const bx = (e) => { if (!e) return null; const q = e.getBoundingClientRect();
        return { l: Math.round(q.left), r: Math.round(q.right) }; };
      return { present: true, count: rows.length, dir: getComputedStyle(r).direction,
               row: { l: Math.round(b.left), r: Math.round(b.right) },
               icon: bx(icon), name: bx(name), line: bx(ln),
               text: (r.textContent || '').trim().slice(0, 60) };
    })()`);
    if (!bp.present) {
      gap("DG-01/هـ: نقاطُ التوقّف", "لا صفوفَ — لم تُنشَأ نقطةٌ (وقفةُ debugger لا تُنشئ صفًّا)");
    } else {
      console.log(`  · نقاطُ التوقّف: ${bp.count} · «${bp.text}»`);
      // ‏**صندوقٌ بلا مساحةٍ ليس موضعًا**: أوّلُ صفٍّ هنا «‏Caught Exceptions» — نقطةُ
      // استثناءٍ لا نقطةَ مصدر، وأيقونتُها مربّعُ تأشيرٍ بصندوقٍ صفريّ. والحكمُ على
      // صندوقٍ صفريٍّ حكمٌ على لا شيء، فيُعلَن فجوةً لا يُقرأ فشلًا.
      if (bp.icon && (bp.icon.r - bp.icon.l) > 2) {
        ok(bp.icon.r >= bp.row.r - 40, "DG-01/هـ: أيقونةُ نقطة التوقّف في مبتدأ القراءة",
          `icon.r=${bp.icon.r} · row.r=${bp.row.r}`);
      } else {
        gap("DG-01/هـ: موضعُ أيقونة نقطة التوقّف",
          `صندوقٌ صفريٌّ أو لا أيقونة — الصفُّ «${bp.text}» نقطةُ استثناءٍ لا نقطةَ مصدر`);
      }
    }

    // ═══ (و) جدوى الطبقة الثانية — تُقاس قبل أن تُكتَب قاعدة ═══
    log("قياسُ **جدوى** القواعد المرشّحة (حقنٌ ⇒ قراءةٌ ⇒ نزع) — لا تُكتَب ميّتةٌ ولا ضارّة…");
    // **قارئُ الحبر لا قارئُ الصندوق.** ‏`.expression` بندُ flex يملأ الصفَّ، فصندوقُه
    // لا يتحرّك بتغيّر حجم الخطّ ولو تضاعف. والحكمُ على صندوقٍ لا يتحرّك حكمٌ بأنّ
    // القاعدةَ ميّتةٌ وهي حيّة — نجاحٌ كاذبٌ مقلوب. فيُقاس **ارتفاعُ رسمِ نصٍّ حقيقيّ**.
    const READ_FS = `(el, cs) => {
      const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      let n = w.nextNode();
      while (n && !n.data.trim()) n = w.nextNode();
      let ink = null;
      if (n) { const r = document.createRange(); r.setStart(n, 0); r.setEnd(n, Math.min(n.data.length, 4));
               const b = r.getBoundingClientRect(); ink = Math.round(b.height * 10) / 10; }
      return { fontSize: cs.fontSize, inkH: ink };
    }`;
    const READ_BIDI = "(el, cs) => ({ bidi: cs.unicodeBidi, dir: cs.direction })";
    const READ_PAD = "(el, cs) => ({ padS: cs.paddingRight, padE: cs.paddingLeft })";
    const READ_MARGIN = "(el, cs) => ({ mS: cs.marginRight, mE: cs.marginLeft })";
    const W = `.monaco-workbench[dir="rtl"]`;
    const CANDIDATES = [
      // المحدِّداتُ **مطابقةٌ لسلاسل المنبع** لا مخترَعة: كلُّ مرشَّحٍ أقصرَ من سلسلة
      // المنبع يُقرأ «لا جدوى» وهو في الحقيقة «خسِر في الأسبقيّة» — وقد وقع ذلك فعلًا
      // في أوّل تشغيلٍ لهذا المِجَسّ، فأُصلِح بقراءة أوراقِ المنبع لا بالتخمين.
      // ‏(‏debug.contribution.css:90-97 · debugViewlet.css:117-119 · repl.css:79-88)
      ["حجمُ خطّ لوحات التنقيح",
       ".debug-variables .monaco-list-row .expression",
       `${W} .debug-pane .monaco-list-row .expression { font-size: ${EDITOR_FONT_SIZE}px; }`, READ_FS],
      ["حشوةُ إطار كومة الاستدعاء (‏padding-inline-end)",
       ".debug-pane .debug-call-stack .stack-frame",
       `${W} .debug-pane .debug-call-stack .thread,
        ${W} .debug-pane .debug-call-stack .session,
        ${W} .debug-pane .debug-call-stack .stack-frame
        { padding-right: 0; padding-inline-end: 12px; }`, READ_PAD],
      ["فجوةُ اسم الملفّ عن رقم السطر (‏margin-inline-end)",
       ".debug-pane .stack-frame .file-name",
       `${W} .debug-pane .stack-frame .file-name
        { margin-right: 0; margin-inline-end: .8em; }`, READ_MARGIN],
      ["فجوةُ كتلة الملفّ عن اسم الدالّة (‏margin-inline-start)",
       ".debug-pane .stack-frame .file",
       `${W} .debug-pane .stack-frame .file:not(:first-child)
        { margin-left: 0; margin-inline-start: .8em; }`, READ_MARGIN],
      ["فجوةُ القيمة عن الاسم (‏margin-inline-start)",
       ".debug-variables .monaco-list-row .expression .value",
       `${W} .monaco-list-row .expression .value
        { margin-left: 0; margin-inline-start: 6px; }`, READ_MARGIN],
      ["رابطُ المصدر في وحدة التصحيح (‏margin-inline-start: auto)",
       ".repl .repl-tree .source",
       `${W} .repl .repl-tree .output.expression.value-and-source .source,
        ${W} .repl .repl-tree .group .source
        { margin-left: 0; margin-right: 0; margin-inline-start: auto; margin-inline-end: 8px; }`,
       READ_MARGIN],
      ["اتّجاهُ اسم الملفّ في كومة الاستدعاء",
       ".debug-pane .stack-frame .file-name",
       `${W} .debug-pane .stack-frame .file-name { unicode-bidi: plaintext; }`, READ_BIDI],
      ["خطُّ حقل وحدة التصحيح",
       ".repl .repl-input-wrapper .monaco-editor .view-line",
       `.repl .repl-input-wrapper .monaco-editor .view-line { font-size: ${EDITOR_FONT_SIZE}px; }`,
       READ_FS],
      // ⚠️ **مرشَّحٌ يُتوقَّع أن يكون ضارًّا لا نافعًا** — وهو أنفعُ ما يخرج به هذا المِجَسّ:
      //    مع اسمٍ **لاتينيّ** تصير فقرةُ الاسم LTR فتنتقل «=» إلى حافّة النهاية
      //    اللاتينيّة = الطرفُ **البعيدُ** عن القيمة في صفّ RTL. فرضيّةٌ تُختبَر لا تُنفَّذ.
      ["عزلُ اسم المتغيّر (‏مرشَّحٌ يُشتبَه بضرره)",
       ".debug-variables .monaco-list-row .expression .name",
       `${W} .debug-variables .expression .name { unicode-bidi: plaintext; }`, READ_BIDI],
    ];
    for (const [name, sel, css, reader] of CANDIDATES) {
      const t = await cdp.evaluate(RULE_TRY(sel, css, reader));
      if (!t.applicable) { gap(`جدوى: ${name}`, t.why); continue; }
      if (t.stale || t.left) {
        gap(`جدوى: ${name}`, `ورقةُ مِجَسٍّ عالقة (قبل=${t.stale} · بعد=${t.left}) — القراءةُ ملوَّثة`);
        continue;
      }
      const mark = t.moved ? "🟢 يُزحزح الحبر" : (t.changed ? "🟡 يقلب القيمةَ ولا يُزحزح" : "⚪ لا يُغيّر");
      console.log(`  ${mark} — ${name}\n       قبل ${JSON.stringify(t.before)}\n       بعد ${JSON.stringify(t.after)}`);
      if (!t.changed && t.after && t.after.inline) {
        console.log("       ℹ️  المنبعُ يبصمها سمةً مضمَّنة — الطبقةُ الثانيةُ لا تبلغها (درسُ SC-01).");
      }
    }

    // ═══ (ز) **القاعدةُ المشحونةُ نفسُها، بنصّها من الملفّ** ═══
    //
    // آخرُ حلقةٍ في السلسلة، وأكثرُها انكسارًا في تاريخ هذا المستودع: مرشَّحٌ تُثبَت جدواه
    // ثمّ يُكتَب في الورقة **بمحدِّدٍ أضيقَ قليلًا** (‏`>` بدل نزول) فيُشحَن ولا يطابق شيئًا.
    // فيُقرَأ نصُّ القاعدة ‎38‎ **من الملفّ** ويُحقَن كما هو — لا نسخةٌ ثانيةٌ في المِجَسّ
    // تنجرف عن المشحون.
    {
      const css = readFileSync(join(ROOT, "patches", "mihrab-rtl.css"), "utf8");
      const at = css.indexOf("38. لوحاتُ التنقيح");
      const block = at >= 0 ? css.slice(css.indexOf("*/", at) + 2) : "";
      if (!block.trim()) {
        gap("DG-01/ز: القاعدة 38 المشحونة", "لم يُعثَر على كتلتها في mihrab-rtl.css");
      } else {
        // ⚠️ **والمقياسُ تبدّل بعد أن شُحنت القاعدة، فيُقال لماذا.**
        //
        // كان هنا حقنُ نصِّ القاعدة ‎38‎ ثمّ الحكمُ بأنّ شيئًا **تغيَّر**. وذلك صحيحٌ يومَ
        // كُتب — كانت القاعدةُ مرشَّحةً لم تُشحَن بعد، فحقنُها يُحدِث فرقًا. ولمّا شُحنت
        // صار حقنُها **إعادةَ ما هو نافذٌ سلفًا**: صفرُ فرقٍ حتمًا، فاحمرَّت الأربعُ في كلّ
        // تشغيلةٍ على قاعدةٍ **عاملةٍ تمامًا**. تجربةُ ما قبل الشحن تُركت حارسًا بعده،
        // فانقلبت إلى **أحمرَ كاذبٍ دائم** — وهو العطبُ نفسُه الذي أُصلح في
        // ‏`_squeeze_combinators`، بصيغةٍ أخرى.
        //
        // والسؤالُ المقصودُ أصلًا لا يحتاج حقنًا: **هل المحدِّدُ المشحونُ يطابق شيئًا،
        // وهل أثرُه قائمٌ على العنصر؟** (‏والعطبُ التاريخيُّ الذي وُجدت له هذه الحلقةُ هو
        // محدِّدٌ أضيقُ بقليلٍ لا يطابق شيئًا فيُشحَن ولا يفعل.) فيُقاس الطرفان مباشرةً:
        // عددُ المطابقات من الورقة المشحونة، وقيمةُ الهامش المنطقيّ على أوّل مطابقة.
        // **ومحدِّدٌ لا يطابق ليس دائمًا عطبًا**: قد يكون السطحُ غيرَ مُصيَّرٍ في هذه
        // الجلسة (وحدةُ التصحيح لا تُخرِج مجموعاتٍ إلّا إن سُجِّلت). فيُقاس **حضورُ
        // الصنف** أوّلًا بمحدِّدٍ أوسع: صفرٌ هناك ⇒ فجوةٌ معلَنة، أمّا حضورُه مع صفرِ
        // مطابقةٍ لمحدِّدنا فهو العطبُ التاريخيُّ بعينه — محدِّدٌ أضيقُ يُشحَن ولا يفعل.
        for (const [name, sel, present] of [
          ["اسمُ الملفّ", ".debug-pane .debug-call-stack .stack-frame .file-name",
           ".debug-pane .debug-call-stack .stack-frame"],
          ["كتلةُ الملفّ", ".debug-pane .debug-call-stack .stack-frame > .file:not(:first-child)",
           ".debug-pane .debug-call-stack .stack-frame .file"],
          ["قيمةُ المتغيّر", ".debug-pane .monaco-list-row .expression > .value",
           ".debug-pane .monaco-list-row .expression"],
          // شقّان في القاعدة نفسِها، ويُقاسان **منفصلَين**: الأوّلُ يبلغ سطورَ المخرَج
          // العاديّة (وهي ما يُصيَّر في كلّ جلسةٍ تقريبًا)، والثاني لا يبلغ إلّا صفوفَ
          // ‏`console.group`. فقياسُهما بمشهودٍ واحدٍ يجعل غيابَ المجموعات يُقرأ «الشقُّ
          // ميّت»، أو حضورَ السطور يُخضِّر شقًّا لم يُختبَر — والوجهان كذبٌ متقابل.
          ["رابطُ المصدر", ".repl .repl-tree .output.expression.value-and-source > .source",
           ".repl .repl-tree .source"],
          ["رابطُ مصدرِ المجموعة", ".repl .repl-tree .group .source",
           ".repl .repl-tree .group"],
        ]) {
          const t = await cdp.evaluate(`(() => {
            const els = document.querySelectorAll(${JSON.stringify(sel)});
            const p = document.querySelectorAll(${JSON.stringify(present)}).length;
            if (!els.length) return { n: 0, p };
            const cs = getComputedStyle(els[0]);
            return { n: els.length, p,
                     mS: cs.marginInlineStart, mE: cs.marginInlineEnd,
                     mL: cs.marginLeft, mR: cs.marginRight };
          })()`);
          if (!t || !t.n) {
            if (!t || !t.p) {
              gap(`DG-01/ز: القاعدة 38 — ${name}`,
                `السطحُ غيرُ مُصيَّرٍ في هذه الجلسة (صفرُ مطابقاتٍ لـ«${present}») — لا مشهودَ عليه`);
            } else {
              ok(false, `DG-01/ز: مُحدِّدُ القاعدة 38 المشحون يطابق — ${name}`,
                `السطحُ حاضرٌ (${t.p} عنصرًا) ومحدِّدُنا «${sel}» يطابق صفرًا — ` +
                `قاعدةٌ تُشحَن ولا تفعل شيئًا`);
            }
            continue;
          }
          // الأثرُ: هامشٌ منطقيٌّ غيرُ صفريّ على أحد الطرفين. القاعدةُ تُصفّر الفيزيائيَّ
          // وتضع المنطقيَّ، فصفرُ الاثنين معًا يعني أنّ القاعدةَ لم تُطبَّق.
          const nz = (v) => parseFloat(v || "0") > 0.5;
          ok(nz(t.mS) || nz(t.mE),
            `DG-01/ز: القاعدة 38 المشحونة مطابِقةٌ ونافذة — ${name}`,
            `${t.n} مطابقة · بداية=${t.mS} نهاية=${t.mE} (فيزيائيّ: يسار=${t.mL} يمين=${t.mR})`);
        }
      }
    }

    // (٤) لوحةُ المراقبة: حقلُ الإضافة **تبلغه قاعدتُنا ٤** — أوّلُ برهانٍ على أنّ قاعدةً
    //     من قواعدنا تصل سطحَ تنقيحٍ أصلًا.
    const wi = await cdp.evaluate(`(() => {
      const i = document.querySelector('.debug-watch .inputBoxContainer input, .debug-pane .monaco-inputbox input.input');
      if (!i) return null;
      const cs = getComputedStyle(i);
      return { bidi: cs.unicodeBidi, dir: cs.direction };
    })()`);
    if (!wi) {
      gap("DG-01/د٢: حقلُ إضافة تعبير مراقبة", "لم يُفتَح الحقلُ (يحتاج نقرَ زرّ + في ترويسة اللوحة)");
    } else {
      ok(wi.bidi === "plaintext",
        "DG-01/د٢: قاعدتُنا ٤ تبلغ حقلَ المراقبة (‏unicode-bidi: plaintext)",
        `${wi.bidi} · ${wi.dir}`);
    }
  }

  // ═══ الفجواتُ المعلَنةُ صراحةً — تُقال ولا تُهرَّب ═══
  gap("DG-01: بالونُ التمرير (‏.debug-hover-widget)", "يحتاج تحويمَ فأرةٍ فوق معرِّفٍ في محرّرٍ متوقّف، وتوقيتُه هشّ");
  gap("DG-01: الحافظةُ («نسخ القيمة»)", "تمرّ بخدمة الحافظة ولا تُقرأ من الصفحة بلا إذن — aria-label مقيسٌ وحدَه");
  gap("DG-01: سحبُ الشريط العائم", "موضعُه محسوبٌ في JS بـtranslate على 100vw وثوابتَ أزرارِ نافذةٍ فيزيائيّة");
  gap("DG-01: التفكيك · السكربتات · الذاكرة · ودجةُ الاستثناء", "لم تُفتَح — أسطحٌ خارج المسار الأدنى");
  gap("DG-01: تعدُّدُ الجلسات والخيوط", "جلسةٌ واحدةٌ وخيطٌ واحد — تخطيطُ الشجرة المتداخلة غيرُ مقيس");

} catch (e) {
  console.error(`❌ خطأ تشغيليّ: ${e.message}`);
  failed = failed || 0;
  process.exitCode = 2;
} finally {
  if (cdp) {
    const clean = await stopSession();
    if (!clean) console.log("  ⚠️  لم يُقَر اختفاءُ شريط التنقيح بعد Shift+F5 — تُقتَل الشجرةُ قسرًا.");
    if (!KEEP) { try { cdp.close(); } catch { /* */ } }
  }
  if (!KEEP) {
    killTree();
    await sleep(1200);
    const n = countOrphans();
    if (Number.isFinite(n) && n > 0) {
      console.log(`  ⚠️  ${n} عمليّةَ node يتيمةً ما زالت تمسك المساحةَ الزائلة — تُقتَل ثانيةً.`);
      killTree();
      await sleep(1200);
    } else if (Number.isFinite(n)) {
      console.log("  ✅ التنظيف: صفرُ عمليّاتٍ يتيمة (مقيسٌ لا مفترَض).");
    } else {
      gap("التنظيف: عدُّ اليتامى", "تعذّر استعلامُ العمليّات — لا يُدَّعى أنّ الشجرةَ نظيفة");
    }
    // **الحذفُ لا يُسقِط القياس.** ملفّاتُ سجلٍّ يمسكها المحرّرُ لحظةَ خروجه تُفشِل
    // ‏`rmSync` بـEBUSY، وسقوطُ المِجَسّ حينها يمحو نتيجةً **تمّت** ويستبدلها بأثرِ
    // مكدّسٍ لا علاقةَ له بالمقيس. فالفشلُ هنا يُقال ولا يُرمى.
    try {
      rmSync(tmp, { recursive: true, force: true, maxRetries: 8, retryDelay: 400 });
    } catch (e) {
      console.log(`  ⚠️  تعذّر حذفُ المساحة الزائلة (${e.code}): ${tmp} — تُحذَف يدويًّا.`);
    }
  }
}

console.log(failed ? `─── ${failed} تأكيدًا فشل ───` : "─── قياسُ DG-01 تمّ ───");
process.exit(process.exitCode === 2 ? 2 : (failed ? 1 : 0));
