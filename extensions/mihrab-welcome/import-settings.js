"use strict";
/**
 * استيرادُ إعدادات VS Code — البابُ الذي يدخل منه القادمُ من محرّرٍ آخر ‏[MG-01].
 *
 * ## لماذا بابٌ أصلًا
 * ‏`dataFolderName` في محرابٍ هو `.mihrab` — فضاءُ أسماءٍ جديدٌ تمامًا. ومستخدمُ VS Code
 * الذي يفتح محرابًا يبدأ من الصفر: لا إعداداتِه ولا اختصاراتِه ولا مقتطفاتِه. وأوّلُ
 * سؤالٍ يسأله: «هل أفقد ضبطي؟». ووعدُ الجولة نفسُه — «ابدأ في ٩٠ ثانية» — يُقاس **من
 * لحظة التثبيت**، وإعادةُ بناء الإعدادات يدويًّا تُبطله قبل أن يبدأ.
 *
 * وتوافقُ **المشروع** معالَجٌ عندنا بعنايةٍ نادرة (‏`mihrabConfigFolder` يقرأ ثلاثةَ أسماءٍ
 * بأسبقيّةٍ صريحة كي لا يكتسب مشروعٌ قديمٌ مجلّدًا ثانيًا) — وتوافقُ **المستخدم** لم يكن
 * معالَجًا إطلاقًا. هذا الملفّ يسدّ ذلك، **محلّيًّا وبلا شبكة**: لا حسابَ ولا مزامنة، وهو
 * القيدُ الذي يجعل الاستيرادَ متّسقًا مع موقف محرابٍ من الخصوصيّة لا ناقضًا له.
 *
 * ## وأخطرُ ما فيه — وقد بُني الملفُّ كلُّه حوله
 * ‏`settings.json` عند أكثر الناس **ليس بيانَ تفضيلات**؛ هو رسوبُ سنواتٍ من وصفاتٍ
 * منسوخةٍ من الشابكة وإضافاتٍ كتبت فيه بنفسها. واستيرادٌ أمينٌ حرفيًّا ينقل هذا الرسوبَ
 * إلى **نطاق المستخدم** — والنطاقُ يغلب `configurationDefaults` إلى الأبد. فمن ورث
 * `editor.fontSize: 14` من افتراضِ محرّرٍ آخرَ ولم يخترها قطُّ، يخرج من الاستيراد وقد صارت
 * **تفضيلَه الصريح**، ولا يبلغه أيُّ تحسينٍ في افتراضات محرابٍ بعد اليوم.
 * ‏**الاستيرادُ يرقّي الصدفةَ إلى قرار** — وهذا هو ما يحرسه {@link classify}.
 *
 * ## ولماذا تُشتَقّ قائمةُ التعارض ولا تُكتَب
 * قائمةٌ مكتوبةٌ بيدٍ تنجرف، وانجرافُها **صامتٌ لا يُصدِر خطأً**: يضيف المشروعُ مفتاحًا
 * طباعيًّا غدًا فلا يدخل الحمايةَ لأنّ أحدًا لم يتذكّره. فنقرأ `configurationDefaults` من
 * ‏`mihrab-shell` نفسِه — مصدرُ الحقيقة الوحيد — ويكون كلُّ ما ضبطه المشروعُ متعارضًا
 * بالبناء لا بالتذكُّر. (وأخطرُ مفتاحٍ في القائمة ليس الاتّجاهَ بل `editor.fontLigatures`:
 * إطفاؤه **يفكّك الكلمةَ العربيّة** إلى حروفٍ منفصلة، وكلُّ دليلِ إعدادٍ لاتينيٍّ ينصح
 * بإطفائه.)
 *
 * ## والمتعارضةُ تُعرَض ولا تُخفى
 * غيرُ محدَّدةٍ افتراضيًّا، **ومعروضةٌ مع سطرِ أثرٍ لكلٍّ منها**. إخفاؤها يصنع الفخَّ نفسَه
 * الذي عالجناه في `clipboard-safety` حين نقلنا الكتمَ من `globalState` الخفيّ إلى إعدادٍ
 * مرئيّ: **الحالةُ التي لا تُرى لا تُراجَع**. ومن أراد خطَّه فلم يجده في القائمة يستنتج
 * أنّ الاستيراد كسِر فيكتبه بيده **بلا أن يقرأ سطرَ الأثر** — أي يفعل الضررَ ولا يبلغه
 * التحذير.
 */

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const IMPORT_CMD = "mihrab.importVSCodeSettings";
const UNDO_CMD = "mihrab.undoVSCodeImport";

/** مفتاحُ اللقطة في `globalState` — لقطةٌ واحدةٌ (آخرُ استيراد)، لا سجلٌّ يتراكم. */
const SNAPSHOT_KEY = "mihrab.import.lastSnapshot";

/** مُعرِّفُ امتداد القشرة — مصدرُ `configurationDefaults` الوحيد. */
const SHELL_EXT_ID = "mihrab.mihrab-shell";

const COPY = {
  title: "استيراد إعدادات VS Code",
  noSource:
    "لم أجد إعداداتِ VS Code على هذا الجهاز. تُقرَأ عادةً من مجلّد المستخدم الخاصّ به، " +
    "ولم يوجد أيٌّ من المواضع المعروفة.",
  readFrom: "قُرِئت إعداداتُك من",
  nothingWritten: "ولم يُكتَب شيءٌ بعد.",
  conflictHeading: "مفاتيحُ يضبطها محرابٌ عن قياس",
  conflictLead:
    "هذه المفاتيحُ يضبطها محرابٌ عن قياسٍ لا عن ذوق، وقيمتُك فيها ستغلبه. " +
    "وهي غيرُ محدَّدةٍ افتراضيًّا — علِّم ما تريد استيرادَه رغم ذلك.",
  shellMissing:
    "تعذّرت قراءةُ افتراضات محراب، فلا أعرف أيَّ مفاتيحَ يضبطها عن قياس. " +
    "لذلك عُطِّل استيرادُ الإعدادات في هذه الجلسة — استيرادٌ لا يعرف ما يعارضه أسوأُ من لا استيراد.",
  secTitles: { settings: "الإعدادات", keybindings: "الاختصارات", snippets: "المقتطفات" },
  colKey: "المفتاح",
  colMine: "قيمتُك",
  colMihrab: "قيمةُ محرابٍ الآن",
  btnImport: "استورد المحدَّد",
  btnCancel: "ألغِ",
  selAll: "الكلّ",
  selNone: "لا شيء",
  selSafe: "المتوافقُ وحدَه",
  undoHint: "لإعادة ما كان: لوحةُ الأوامر ← «محراب: تراجع عن آخر استيرادٍ من VS Code».",
  noSnapshot: "لا استيرادَ سابقٌ لأتراجع عنه.",
};

/**
 * **سطرُ الأثر لكلّ مفتاحٍ متعارض — ما سيراه بعينه، لا ما يجري في الداخل.**
 *
 * كلُّ سطرٍ منقولٌ من قياسٍ موثَّقٍ في هذا المستودع (‏TY-02 · TY-04 · VA-04 · DR-02 ·
 * DR-05 · AR-04) لا من رأي. والمفاتيحُ التي لا سطرَ لها تأخذ الصيغةَ العامّة في
 * {@link impactFor} — فالقائمةُ **مشتقّة** والسطورُ **شرحٌ لبعضها**، لا العكس: مفتاحٌ
 * جديدٌ بلا سطرٍ يبقى محميًّا، ويظهر بجملةٍ عامّةٍ صادقة.
 */
const IMPACT = {
  "editor.fontLigatures":
    "ستتفكّك الكلمةُ العربيّة إلى حروفٍ منفصلة: «محراب» تصير «م ح ر ا ب».",
  "editor.textDirection":
    "سيعود مزرابُ أرقام الأسطر إلى اليسار، ويعود المحرّرُ اتّجاهَ الإنجليزيّة.",
  "editor.fontFamily":
    "لن تصطفَّ الأعمدةُ تحت بعضها: «ااااا» ستبدو أضيقَ من «ممممم» رغم أنّهما خمسةُ حروفٍ لكلَيهما.",
  "editor.lineHeight":
    "ستُقَصُّ الشدّةُ والهمزةُ والتنوينُ من أعلى السطر — قياسٌ من جداول الخطّ لا تقدير.",
  "editor.fontSize":
    "حرفُك العربيُّ سيصير أقصرَ بنحو ‎17٪‎ ممّا يعطيه الحجمُ نفسُه للّاتينيّة.",
  "workbench.sideBar.location": "سينتقل الشريطُ الجانبيُّ إلى اليسار.",
  "editor.experimentalGpuAcceleration":
    "قد يسقط اتّجاهُ المحرّر كلُّه — طبقةُ الرسم بالمعالج الرسوميّ بلا أيّ معالجةِ اتّجاه.",
  "terminal.integrated.fontFamily": "الأثرُ نفسُه في مخرجات برنامجك.",
  "terminal.integrated.fontSize": "الأثرُ نفسُه في مخرجات برنامجك.",
  "terminal.integrated.lineHeight": "الأثرُ نفسُه في مخرجات برنامجك.",
  "scm.inputFontFamily": "سيعود صندوقُ رسالة الالتزام إلى خطّ الواجهة بدل وجه المحرّر.",
  "scm.inputFontSize": "الأثرُ نفسُه في أطولِ نصٍّ عربيٍّ تكتبه في يومك: رسالةِ الالتزام.",
};

/** الصيغةُ العامّة لمفتاحٍ متعارضٍ لا سطرَ أثرٍ مكتوبٌ له — صادقةٌ ولا تدّعي تفصيلًا. */
function impactFor(key) {
  if (IMPACT[key]) return IMPACT[key];
  if (key.startsWith("editor.unicodeHighlight."))
    return "ستعود الإطاراتُ الصفراءُ حول الحروف العربيّة في محرّرك.";
  if (key.startsWith("[") && key.endsWith("]"))
    return "كتلةُ تجاوزٍ بنطاق لغةٍ تغلب ما ضبطه محرابٌ لتلك اللغة.";
  return "مفتاحٌ يضبطه محرابٌ عن قياس؛ قيمتُك ستغلبه في هذا المحرّر.";
}

/**
 * مواضعُ إعدادات VS Code **المرشّحة** على هذا الجهاز.
 *
 * ثلاثُ توزيعاتٍ لا واحدة (‏Code · Code - Insiders · VSCodium): من كان له أكثرُ من نسخةٍ
 * **يختار**، ولا نخمّن. والدالّةُ نقيّةٌ عمدًا (تأخذ `env` و`platform` و`existsSync`)
 * كي تُختبَر بلا نظامِ ملفّاتٍ ولا نظامِ تشغيل.
 *
 * @param {NodeJS.ProcessEnv} env @param {string} platform @param {(p:string)=>boolean} exists
 * @returns {{label:string, dir:string}[]}
 */
function candidateUserDirs(env, platform, exists) {
  const home = env.HOME || env.USERPROFILE || "";
  const roots = [];
  if (platform === "win32") {
    const appdata = env.APPDATA || (home ? path.join(home, "AppData", "Roaming") : "");
    if (appdata) roots.push(appdata);
  } else if (platform === "darwin") {
    if (home) roots.push(path.join(home, "Library", "Application Support"));
  } else {
    roots.push(env.XDG_CONFIG_HOME || (home ? path.join(home, ".config") : ""));
  }
  const apps = [
    ["Visual Studio Code", "Code"],
    ["Visual Studio Code — Insiders", "Code - Insiders"],
    ["VSCodium", "VSCodium"],
  ];
  const out = [];
  for (const root of roots) {
    if (!root) continue;
    for (const [label, folder] of apps) {
      const dir = path.join(root, folder, "User");
      if (exists(dir)) out.push({ label, dir });
    }
  }
  return out;
}

/**
 * يقرأ JSONC (يسمح بالتعليقات والفواصل الزائدة) — ‏`settings.json` عند المستخدم **مُعلَّقٌ
 * غالبًا**، و`JSON.parse` عليه يفشل فيُبلَّغ «لا إعدادات» زورًا.
 *
 * وطريقةُ التجريد تحترم السلاسل: تعليقٌ داخل سلسلةٍ (`"http://x"`) ليس تعليقًا، وقد كان
 * تجريدٌ ساذجٌ يقصّ القيمةَ من منتصفها.
 */
function parseJsonc(text) {
  let out = "";
  let i = 0;
  let inStr = false;
  while (i < text.length) {
    const c = text[i];
    if (inStr) {
      out += c;
      if (c === "\\") { out += text[i + 1] || ""; i += 2; continue; }
      if (c === '"') inStr = false;
      i++;
      continue;
    }
    if (c === '"') { inStr = true; out += c; i++; continue; }
    if (c === "/" && text[i + 1] === "/") { while (i < text.length && text[i] !== "\n") i++; continue; }
    if (c === "/" && text[i + 1] === "*") {
      i += 2;
      while (i < text.length && !(text[i] === "*" && text[i + 1] === "/")) i++;
      i += 2;
      continue;
    }
    out += c;
    i++;
  }
  out = out.replace(/,(\s*[}\]])/g, "$1");
  return JSON.parse(out);
}

/**
 * **قائمةُ التعارض مشتقّةٌ لا مكتوبة** — كلُّ مفتاحٍ يضبطه محرابٌ في
 * ‏`configurationDefaults`، ومعه كلُّ مفتاحٍ داخلَ كتلِ نطاقات اللغات.
 *
 * ومفاتيحُ التعليق (‏`_comment_*`) تُستبعَد: توثيقٌ لا إعداد.
 * @param {object} defaults @returns {Map<string, any>} مفتاح ⇐ قيمةُ محرابٍ الحاليّة
 */
function mihrabOwnedKeys(defaults) {
  const owned = new Map();
  for (const [k, v] of Object.entries(defaults || {})) {
    if (k.startsWith("_comment")) continue;
    if (k.startsWith("[") && k.endsWith("]")) {
      owned.set(k, v);
      for (const [ik, iv] of Object.entries(v || {})) {
        if (ik.startsWith("_comment")) continue;
        owned.set(ik, iv);   // المفتاحُ عالميًّا أيضًا: قيمةُ المستخدم العالميّة تغلب نطاقَنا
      }
      continue;
    }
    owned.set(k, v);
  }
  return owned;
}

/**
 * يصنّف إعداداتِ المستخدم إلى **متوافقٍ** و**متعارض**.
 *
 * والتصنيفُ لا يسأل «هل القيمتان مختلفتان؟» بل «**هل هذا مفتاحٌ يملكه محراب؟**» — لأنّ
 * المستخدمَ الذي تصادف أنّ قيمتَه تساوي قيمتَنا اليومَ يظلّ، بالكتابة في نطاقه، يُجمِّد
 * المفتاحَ على تلك القيمة ويحرم نفسَه من أيّ تحسينٍ لاحق. التساوي اليومَ لا يُسقِط التحذير.
 *
 * @param {object} userSettings @param {Map<string,any>} owned
 * @returns {{compatible:{key:string,value:any}[], conflicting:{key:string,value:any,mihrab:any,impact:string}[]}}
 */
function classify(userSettings, owned) {
  const compatible = [];
  const conflicting = [];
  for (const [key, value] of Object.entries(userSettings || {})) {
    if (owned.has(key)) {
      conflicting.push({ key, value, mihrab: owned.get(key), impact: impactFor(key) });
    } else {
      compatible.push({ key, value });
    }
  }
  const byKey = (a, b) => (a.key < b.key ? -1 : a.key > b.key ? 1 : 0);
  return { compatible: compatible.sort(byKey), conflicting: conflicting.sort(byKey) };
}

/**
 * يبني اللقطةَ التي يقوم عليها التراجع — **قبل أوّل كتابة لا بعدها**.
 *
 * تُحفَظ القيمةُ السابقةُ **للمفاتيح المكتوبة وحدَها**، ومعها ما كُتِب فعلًا: بهما معًا
 * يُعرَف يومَ التراجع أيُّ مفتاحٍ ما زال على ما كتبناه وأيُّها غيّره المستخدمُ بيده.
 * @param {{key:string,value:any}[]} chosen @param {(k:string)=>any} readCurrent
 */
function buildSnapshot(chosen, readCurrent, stamp) {
  return {
    at: stamp,
    entries: chosen.map((c) => ({ key: c.key, before: readCurrent(c.key), wrote: c.value })),
  };
}

/**
 * يقسّم مفاتيحَ اللقطة يومَ التراجع إلى **ما يُعاد** و**ما يُترَك**.
 *
 * ‏**والحدُّ يُقال ولا يُدَّعى**: من عدّل مفتاحًا بيده بعد الاستيراد لا يُداس عليه صامتًا.
 * وهي القاعدةُ نفسُها التي رفضنا بها الوعدَ المطلق في `clipboard-safety`.
 * @returns {{restore:{key:string,before:any}[], kept:string[]}}
 */
function planUndo(snapshot, readCurrent) {
  const restore = [];
  const kept = [];
  for (const e of (snapshot && snapshot.entries) || []) {
    const now = readCurrent(e.key);
    if (JSON.stringify(now) === JSON.stringify(e.wrote)) restore.push({ key: e.key, before: e.before });
    else kept.push(e.key);
  }
  return { restore, kept };
}

/** يهرب النصَّ لإدراجه في HTML (دفاعٌ في العمق: البياناتُ هنا **ملفُّ مستخدمٍ** لا ملفُّنا). */
function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

/**
 * يبني HTML لوحةِ المعاينة — بوصفة `help-panel.js` نفسِها: `default-src 'none'` و`nonce`
 * لكلّ نمطٍ وبرنامج، ولا موردَ خارجيًّا واحدًا.
 *
 * **ولماذا لوحةٌ لا `showQuickPick`:** الاختيارُ هنا يحتاج **مقارنةَ قيمتَين** وسطرَ أثرٍ
 * تحت كلّ مفتاحٍ متعارض؛ والقائمةُ المنسدلةُ تعرض سطرًا واحدًا لا ثلاثة، فتُخفي بالضبط ما
 * جاءت المعاينةُ لتُظهره.
 */
function buildHtml(model) {
  const nonce = crypto.randomBytes(16).toString("base64");
  const csp = ["default-src 'none'", `style-src 'nonce-${nonce}'`, `script-src 'nonce-${nonce}'`].join("; ");
  const data = JSON.stringify(model).replace(/</g, "\\u003c");
  return `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<style nonce="${nonce}">
  body { margin: 0; font-family: var(--vscode-font-family); color: var(--vscode-foreground);
         background: var(--vscode-editor-background); }
  header { padding: 14px 18px 10px; border-bottom: 1px solid var(--vscode-editorWidget-border, #8884); }
  h1 { font-size: 1.15em; margin: 0 0 6px; }
  /* المسارُ لاتينيٌّ بشرطاتٍ مائلة — محايداتٌ تقفز بلا عزلٍ صريح. */
  .path { direction: ltr; unicode-bidi: isolate; font-family: var(--vscode-editor-font-family); }
  main { padding: 10px 18px 90px; }
  h2 { font-size: 1em; margin: 18px 0 4px; }
  .lead { opacity: .8; margin: 2px 0 10px; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: start; padding: 4px 8px; border-bottom: 1px solid var(--vscode-editorWidget-border, #8884);
           vertical-align: top; }
  th { font-weight: 600; opacity: .8; }
  .k, .v { direction: ltr; unicode-bidi: isolate; font-family: var(--vscode-editor-font-family); font-size: .92em; }
  .impact { padding: 2px 8px 8px; opacity: .85; border-bottom: 1px solid var(--vscode-editorWidget-border, #8884); }
  .warn { border-inline-start: 3px solid var(--vscode-editorWarning-foreground, #cca700); padding-inline-start: 10px; }
  .bar { position: fixed; inset-block-end: 0; inset-inline: 0; padding: 10px 18px; display: flex; gap: 10px;
         background: var(--vscode-editor-background); border-top: 1px solid var(--vscode-editorWidget-border, #8884); }
  button { font: inherit; padding: 5px 14px; cursor: pointer; border-radius: 3px; border: 1px solid transparent;
           color: var(--vscode-button-foreground); background: var(--vscode-button-background); }
  button.sec { color: var(--vscode-button-secondaryForeground); background: var(--vscode-button-secondaryBackground); }
  .seg button { padding: 2px 10px; font-size: .9em; }
</style>
</head>
<body>
<header>
  <h1>${esc(COPY.title)}</h1>
  <p>${esc(COPY.readFrom)} <span class="path">${esc(model.sourceDir)}</span> — ${esc(COPY.nothingWritten)}</p>
</header>
<main id="out"></main>
<div class="bar">
  <button id="go">${esc(COPY.btnImport)}</button>
  <button id="cancel" class="sec">${esc(COPY.btnCancel)}</button>
</div>
<script nonce="${nonce}">
  const M = ${data};
  const COPY = ${JSON.stringify(COPY)};
  const vscode = acquireVsCodeApi();
  const chosen = new Set(M.compatible.map(c => c.key));   // الحالةُ الابتدائيّة: المتوافقُ وحدَه
  const kbChosen = new Set(M.keybindings.map((_, i) => i));
  const snChosen = new Set(M.snippets.map(s => s.name));

  function esc(s) { const d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; }
  function val(v) { try { return JSON.stringify(v); } catch { return String(v); } }

  function rows(list, conflicting) {
    return list.map(r => {
      const id = 'k:' + r.key;
      const row = '<tr><td><input type="checkbox" data-id="' + esc(id) + '"' + (chosen.has(r.key) ? ' checked' : '') +
        '></td><td class="k">' + esc(r.key) + '</td><td class="v">' + esc(val(r.value)) + '</td><td class="v">' +
        (conflicting ? esc(val(r.mihrab)) : '—') + '</td></tr>';
      return conflicting ? row + '<tr><td></td><td colspan="3" class="impact">' + esc(r.impact) + '</td></tr>' : row;
    }).join('');
  }

  function render() {
    let h = '';
    h += '<h2>' + esc(COPY.secTitles.settings) + ' — ' + M.compatible.length + ' متوافقًا · ' +
         M.conflicting.length + ' يعارضها محراب</h2>';
    h += '<div class="seg"><button data-sel="all">' + esc(COPY.selAll) + '</button> ' +
         '<button data-sel="none">' + esc(COPY.selNone) + '</button> ' +
         '<button data-sel="safe">' + esc(COPY.selSafe) + '</button></div>';
    const head = '<tr><th></th><th>' + esc(COPY.colKey) + '</th><th>' + esc(COPY.colMine) + '</th><th>' +
                 esc(COPY.colMihrab) + '</th></tr>';
    h += '<table>' + head + rows(M.compatible, false) + '</table>';
    if (M.conflicting.length) {
      h += '<h2 class="warn">' + esc(COPY.conflictHeading) + '</h2><p class="lead">' + esc(COPY.conflictLead) + '</p>';
      h += '<table>' + head + rows(M.conflicting, true) + '</table>';
    }
    if (M.keybindings.length) {
      h += '<h2>' + esc(COPY.secTitles.keybindings) + ' — ' + M.keybindings.length + '</h2><table>' +
        M.keybindings.map((k, i) => '<tr><td><input type="checkbox" data-kb="' + i + '"' +
          (kbChosen.has(i) ? ' checked' : '') + '></td><td class="k">' + esc(k.key || '') +
          '</td><td class="v" colspan="2">' + esc(k.command || '') + '</td></tr>').join('') + '</table>';
    }
    if (M.snippets.length) {
      h += '<h2>' + esc(COPY.secTitles.snippets) + ' — ' + M.snippets.length + '</h2><table>' +
        M.snippets.map(s => '<tr><td><input type="checkbox" data-sn="' + esc(s.name) + '"' +
          (snChosen.has(s.name) ? ' checked' : '') + '></td><td class="k">' + esc(s.name) +
          '</td><td class="v" colspan="2">' + s.count + ' مقتطفًا</td></tr>').join('') + '</table>';
    }
    document.getElementById('out').innerHTML = h;
    document.getElementById('go').textContent = COPY.btnImport + ' (' +
      (chosen.size + kbChosen.size + snChosen.size) + ')';
  }

  document.addEventListener('change', (e) => {
    const t = e.target;
    if (t.dataset.id) { const k = t.dataset.id.slice(2); t.checked ? chosen.add(k) : chosen.delete(k); }
    else if (t.dataset.kb) { const i = +t.dataset.kb; t.checked ? kbChosen.add(i) : kbChosen.delete(i); }
    else if (t.dataset.sn) { t.checked ? snChosen.add(t.dataset.sn) : snChosen.delete(t.dataset.sn); }
    document.getElementById('go').textContent = COPY.btnImport + ' (' +
      (chosen.size + kbChosen.size + snChosen.size) + ')';
  });
  document.addEventListener('click', (e) => {
    const sel = e.target.dataset && e.target.dataset.sel;
    if (!sel) return;
    chosen.clear();
    if (sel === 'all') { M.compatible.forEach(c => chosen.add(c.key)); M.conflicting.forEach(c => chosen.add(c.key)); }
    if (sel === 'safe') M.compatible.forEach(c => chosen.add(c.key));
    render();
  });
  document.getElementById('go').addEventListener('click', () => {
    vscode.postMessage({ type: 'import', settings: [...chosen], keybindings: [...kbChosen], snippets: [...snChosen] });
  });
  document.getElementById('cancel').addEventListener('click', () => vscode.postMessage({ type: 'cancel' }));
  render();
</script>
</body>
</html>`;
}

/** يقرأ ملفًّا نصّيًّا إن وُجد، وإلّا `null` — لا يرمي: غيابُ ملفٍّ حالٌ لا خطأ. */
function readIfAny(p) {
  try { return fs.readFileSync(p, "utf8"); } catch { return null; }
}

/**
 * يجمع نموذجَ المعاينة من مجلّد مستخدمٍ واحد.
 * @param {string} dir مجلّد `User` @param {Map<string,any>} owned
 */
function collect(dir, owned) {
  const settingsRaw = readIfAny(path.join(dir, "settings.json"));
  let userSettings = {};
  let settingsError = null;
  if (settingsRaw != null) {
    try { userSettings = parseJsonc(settingsRaw) || {}; }
    catch (e) { settingsError = e.message; }
  }
  const kbRaw = readIfAny(path.join(dir, "keybindings.json"));
  let keybindings = [];
  if (kbRaw != null) { try { keybindings = parseJsonc(kbRaw) || []; } catch { keybindings = []; } }

  const snippets = [];
  const snDir = path.join(dir, "snippets");
  let names = [];
  try { names = fs.readdirSync(snDir); } catch { names = []; }
  for (const name of names) {
    // اسمٌ آمنٌ لا غير: لا مسارَ فيه ولا صعود. الملفُّ ملفُّ مستخدمٍ لا ملفُّنا.
    if (name !== path.basename(name) || name.startsWith(".")) continue;
    if (!/\.(json|code-snippets)$/i.test(name)) continue;
    const raw = readIfAny(path.join(snDir, name));
    if (raw == null) continue;
    let count = 0;
    try { count = Object.keys(parseJsonc(raw) || {}).length; } catch { count = 0; }
    snippets.push({ name, count });
  }
  const { compatible, conflicting } = classify(userSettings, owned);
  return { sourceDir: dir, compatible, conflicting, keybindings, snippets, settingsError };
}

/**
 * يقرأ `configurationDefaults` من امتداد القشرة — **مصدرُ الحقيقة الوحيد**.
 * ويعود `null` إن تعذّر: وحينها **يُعطَّل استيرادُ الإعدادات**، لأنّ استيرادًا لا يعرف ما
 * يعارضه أسوأُ من لا استيراد (والصمتُ هنا يهدم الطباعةَ التي بُني عليها المشروع).
 */
function readShellDefaults(vscode) {
  try {
    const ext = vscode.extensions.getExtension(SHELL_EXT_ID);
    const d = ext && ext.packageJSON && ext.packageJSON.contributes
      && ext.packageJSON.contributes.configurationDefaults;
    return d && typeof d === "object" ? d : null;
  } catch { return null; }
}

/** يفتح لوحةَ المعاينة، ويكتب ما اختاره المستخدمُ وحدَه. */
async function openImportPanel(vscode, context) {
  const defaults = readShellDefaults(vscode);
  if (!defaults) { vscode.window.showErrorMessage(COPY.shellMissing); return; }
  const owned = mihrabOwnedKeys(defaults);

  const cands = candidateUserDirs(process.env, process.platform, (p) => {
    try { return fs.statSync(p).isDirectory(); } catch { return false; }
  });
  if (!cands.length) { vscode.window.showInformationMessage(COPY.noSource); return; }
  let picked = cands[0];
  if (cands.length > 1) {
    const sel = await vscode.window.showQuickPick(
      cands.map((c) => ({ label: c.label, description: c.dir, c })),
      { title: COPY.title, placeHolder: "من أيّ نسخةٍ أستورد؟" });
    if (!sel) return;
    picked = sel.c;
  }
  const model = collect(picked.dir, owned);
  if (model.settingsError) {
    vscode.window.showWarningMessage(
      `تعذّرت قراءةُ settings.json من ${picked.dir}: ${model.settingsError} — ` +
      "تُعرَض الاختصاراتُ والمقتطفاتُ وحدَها.");
  }

  const panel = vscode.window.createWebviewPanel(
    "mihrabImportSettings", COPY.title, vscode.ViewColumn.One,
    { enableScripts: true, retainContextWhenHidden: true });
  panel.webview.html = buildHtml(model);

  panel.webview.onDidReceiveMessage(async (msg) => {
    if (!msg || msg.type === "cancel") { panel.dispose(); return; }
    if (msg.type !== "import") return;
    const cfg = vscode.workspace.getConfiguration();
    const byKey = new Map([...model.compatible, ...model.conflicting].map((c) => [c.key, c]));
    const chosen = (msg.settings || []).map((k) => byKey.get(k)).filter(Boolean);

    // **اللقطةُ قبل أوّل كتابةٍ لا بعدها** — وإلّا سجّلنا ما كتبناه نحن أصلًا.
    const snap = buildSnapshot(chosen, (k) => cfg.inspect(k) && cfg.inspect(k).globalValue,
      new Date().toISOString());
    await context.globalState.update(SNAPSHOT_KEY, snap);

    let written = 0;
    for (const c of chosen) {
      try { await cfg.update(c.key, c.value, vscode.ConfigurationTarget.Global); written++; }
      catch { /* مفتاحٌ غيرُ مسجَّلٍ في هذا المحرّر — يُتخطّى ولا يُوقِف الباقي */ }
    }
    let kb = 0;
    const kbSel = (msg.keybindings || []).map((i) => model.keybindings[i]).filter(Boolean);
    if (kbSel.length) kb = await mergeKeybindings(vscode, kbSel);
    let sn = 0;
    for (const name of msg.snippets || []) {
      if (await copySnippet(vscode, path.join(model.sourceDir, "snippets", name), name)) sn++;
    }
    panel.dispose();
    const pick = await vscode.window.showInformationMessage(
      `استُورد ${written} إعدادًا و${kb} اختصارًا و${sn} ملفَّ مقتطفات. ${COPY.undoHint}`,
      "تراجع عن الاستيراد");
    if (pick) await vscode.commands.executeCommand(UNDO_CMD);
  }, undefined, context.subscriptions);
}

/**
 * يدمج اختصاراتِ المستخدم في ملفّ اختصارات محراب — **دمجٌ لا إحلال**: من ضبط اختصارًا في
 * محرابٍ قبل الاستيراد لا يفقده.
 */
async function mergeKeybindings(vscode, entries) {
  try {
    const target = path.join(userDir(vscode), "keybindings.json");
    let existing = [];
    const raw = readIfAny(target);
    if (raw != null) { try { existing = parseJsonc(raw) || []; } catch { existing = []; } }
    const seen = new Set(existing.map((e) => JSON.stringify([e.key, e.command, e.when])));
    let added = 0;
    for (const e of entries) {
      const sig = JSON.stringify([e.key, e.command, e.when]);
      if (seen.has(sig)) continue;
      existing.push(e); seen.add(sig); added++;
    }
    fs.writeFileSync(target, JSON.stringify(existing, null, 2), "utf8");
    return added;
  } catch { return 0; }
}

/** ينسخ ملفَّ مقتطفاتٍ إلى مجلّد مقتطفات محراب. يعود `false` بصمتٍ إن تعذّر. */
async function copySnippet(vscode, src, name) {
  try {
    const dst = path.join(userDir(vscode), "snippets");
    fs.mkdirSync(dst, { recursive: true });
    fs.copyFileSync(src, path.join(dst, name));
    return true;
  } catch { return false; }
}

/**
 * مجلّدُ مستخدمِ محراب — يُشتقّ من مسارٍ يملكه المحرّرُ (‏`globalStorageUri`) لا من
 * `dataFolderName` مكتوبٍ بيد: الاسمُ قد يتغيّر في هويّة المنتج، والسلسلةُ المكرّرةُ تنجرف.
 */
let _userDir = null;
function setUserDir(p) { _userDir = p; }
function userDir(_vscode) {
  if (!_userDir) throw new Error("مجلّدُ المستخدم غيرُ مضبوط");
  return _userDir;
}

/** يُنفّذ التراجعَ عن آخر استيراد — ويقول ما تركه ولمَ. */
async function undoImport(vscode, context) {
  const snap = context.globalState.get(SNAPSHOT_KEY);
  if (!snap || !snap.entries || !snap.entries.length) {
    vscode.window.showInformationMessage(COPY.noSnapshot); return;
  }
  const cfg = vscode.workspace.getConfiguration();
  const { restore, kept } = planUndo(snap, (k) => cfg.inspect(k) && cfg.inspect(k).globalValue);
  for (const r of restore) {
    try { await cfg.update(r.key, r.before, vscode.ConfigurationTarget.Global); } catch { /* */ }
  }
  await context.globalState.update(SNAPSHOT_KEY, undefined);
  let msg = `أُعيد ${restore.length} مفتاحًا إلى قيمته قبل الاستيراد.`;
  if (kept.length) {
    msg += ` و${kept.length} مفاتيحَ غيّرتَها بنفسك بعد الاستيراد — تُركت كما ضبطتَها: ` +
      kept.slice(0, 5).join(" · ") + (kept.length > 5 ? " …" : "");
  }
  vscode.window.showInformationMessage(msg);
}

/** يوصل الأمرين. يُستدعى من `activate` مرّةً واحدة. */
function activateImport(vscode, context) {
  try {
    // `globalStorageUri` = …/User/globalStorage/<ext> ⇒ الصعودُ مرّتين يعطي …/User
    const gs = context.globalStorageUri && context.globalStorageUri.fsPath;
    if (gs) setUserDir(path.dirname(path.dirname(gs)));
  } catch { /* يبقى غيرَ مضبوط، فتفشل النسخُ بصمتٍ وتُبلَّغ صفرًا */ }
  return [
    vscode.commands.registerCommand(IMPORT_CMD, () => openImportPanel(vscode, context)),
    vscode.commands.registerCommand(UNDO_CMD, () => undoImport(vscode, context)),
  ];
}

module.exports = {
  IMPORT_CMD, UNDO_CMD, SNAPSHOT_KEY, SHELL_EXT_ID, COPY, IMPACT,
  candidateUserDirs, parseJsonc, mihrabOwnedKeys, classify, impactFor,
  buildSnapshot, planUndo, buildHtml, collect,
  readShellDefaults, openImportPanel, undoImport, activateImport, setUserDir,
};
