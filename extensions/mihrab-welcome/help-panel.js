"use strict";
/**
 * مساعدةٌ داخل المحرّر [ON-03] — الأصولُ كانت موجودةً والمنفذُ ناقصًا.
 *
 * ## الفجوة
 * كلُّ مسارات المساعدة في `product.json` تخرج إلى المتصفّح، وثلاثةُ أعطابِ تجربةٍ في قرارٍ واحد:
 *   ‏(أ) **انقطاعُ السياق** — يترك المستخدمُ محرابًا ليتعلّمه.
 *   ‏(ب) **الشبكةُ شرطٌ للمساعدة**، ومحرابٌ يُقدَّم كبيئةٍ بتهيئةٍ صفريّةٍ تعمل محلّيًّا.
 *   ‏(ج) **المتصفّحُ يفتح صفحةً خارجَ عربيّةِ محرابٍ ونبرتِه**، فتتشتّت الهويّةُ في أهمّ لحظةٍ
 *       تعليميّة.
 * والمفارقةُ الحادّة: `site/data/glossary.json` و`keybindings.json` **موجودان في المستودع** —
 * أي أنّ محتوى المساعدة مكتوبٌ ومنظَّمٌ ولا يصل إلى المحرّر.
 *
 * ## وهنا يعمل تطبيعُ البحث العربيّ فعلًا [DX-01]
 * هذا هو سطحُ البحث الذي **نملكه كاملًا**: نملك الاستعلامَ والفهرسَ والمُرشِّح. فمن كتب
 * «لوحه الاوامر» يجد «لوحة الأوامر»، ومن كتب «التنقيح» يجدها مشكولةً كانت أو مجرّدة —
 * وهو ما يعجز عنه `filterText` وحدَه في مُرشِّح المنبع.
 *
 * ## الأمن
 * ‏CSP نفسُه المتّبَع في نبراس ولوحة المخرجات: `default-src 'none'` + `nonce`، وكلُّ نصٍّ
 * يُدرَج `textContent` لا HTML — والبياناتُ من ملفّاتنا لا من الشبكة.
 */


const N = require("./arabic-normalize.js");
const { normalizeArabic } = N;
const { sortArabic } = require("./arabic-sort.js");
const { toArabicIndic, SETTING: DIGITS_SETTING } = require("./digits.js");

/**
 * خريطةُ التوحيد ككائنٍ صالحٍ للحقن في العرض.
 * **يرمي عند تغيّر التمثيل** ولا يسقط إلى `{}` صامتًا: سقوطٌ صامتٌ هنا يعني أنّ «لوحه
 * الاوامر» تكفّ عن إيجاد «لوحة الأوامر» بلا خطأٍ ولا رسالة — وهو أسوأُ من انهيارٍ صريح.
 * وخطأُ البناءِ خيرٌ من عطبِ التشغيل.
 */
const FOLD_OBJECT = (() => {
  if (!(N.FOLD instanceof Map)) {
    throw new TypeError("arabic-normalize.FOLD ليست Map — تغيّر تمثيلُها فانكسر حقنُ التطبيع [DX-01]");
  }
  return Object.fromEntries(N.FOLD);
})();

const PANEL_TYPE = "mihrab.help";
const PANEL_TITLE = "مساعدة محراب";
const OPEN_CMD = "mihrab.openHelp";
/** مجلّدُ البيانات المحزوم — نسخٌ **مطابقةٌ بايتًا ببايت** لـ`site/data/` يحرسها فحصُ L0. */
const DATA_DIR = "data";
const GLOSSARY_FILE = "glossary.json";
const KEYBINDINGS_FILE = "keybindings.json";

const COPY = {
  title: PANEL_TITLE,
  // النائبُ يقول **بماذا أبحث** لا كيف تعمل الآليّة.
  searchPlaceholder: "ابحث عن مصطلحٍ أو اختصار… (اكتب بلا همزٍ ولا تشكيلٍ إن شئت)",
  tabGlossary: "المصطلحات",
  tabKeys: "الاختصارات",
  empty: "لا نتيجةَ لهذا البحث. جرّب كلمةً أقصر.",
  // قوالبُ نصٍّ لا دوالّ: هذه تُحقَن JSON في العرض، والدوالُّ لا تُسلسَل.
  emptyHere: "لا نتيجةَ في هذا التبويب — و{n} في «{other}».",
  count: "{n} نتيجة",
  loadFailed: "تعذّر فتحُ المساعدة — يبدو أنّ ملفّاتِ محرابٍ ناقصة. أعِد التثبيت.",
  colTerm: "المصطلح",
  // «الأصل» توحي بـ«النصّ الأصليّ»؛ وفائدةُ العمود للمبتدئ أن يبحث به في الشابكة.
  colEnglish: "بالإنجليزيّة",
  colAction: "الإجراء",
  colKey: "المفتاح",
};

/**
 * ‏`nonce` بلا `require("crypto")`.
 *
 * الوحدةُ تعمل في مضيفَي امتدادٍ اثنين: عقدةٌ على المكتب، وعاملُ ويبٍ في المتصفّح —
 * والثاني ليس فيه `require` لوحدات العقدة إطلاقًا، فاستيرادٌ في رأس الملفّ **يُسقِط
 * الوحدةَ كلَّها** قبل أن يُنفَّذ منها سطر. و`globalThis.crypto` واجهةٌ واحدةٌ في
 * الاثنين (‏WebCrypto مُعرَّضةٌ عالميًّا في Node منذ ‎19‎)، فالمشترَكُ يغني عن الفرع.
 *
 * والارتدادُ ليس ترفًا ولا هو `Math.random`: قيمةٌ ضعيفةٌ في `nonce` تُبطِل سياسةَ الأمان
 * صامتةً. فإن غابت الواجهةُ رُمي الخطأ — لوحةٌ لا تُفتَح خيرٌ من لوحةٍ تُفتَح بلا حماية.
 */
function randomNonce() {
  const c = globalThis.crypto;
  if (!c || typeof c.getRandomValues !== "function") {
    throw new Error("لا WebCrypto في هذا المضيف — لا يُبنى nonce بلا عشوائيّةٍ معمّاة [ON-03]");
  }
  const b = c.getRandomValues(new Uint8Array(16));
  let bin = "";
  for (const x of b) bin += String.fromCharCode(x);
  // ‏`btoa` عالميّةٌ في المتصفّح وفي Node منذ ‎16‎ — وهي المشترَكُ نفسُه.
  return btoa(bin);
}

/**
 * يقرأ ملفَّ بياناتٍ محزومًا. يعيد `null` عند أيّ عطب (سقوطٌ لطيف لا رمي).
 *
 * والقراءةُ **مُمرَّرةٌ لا مفروضة**: `read(name)` يعيد نصَّ الملفّ أو `null`. على المكتب
 * تُبنى من `fs` (‏`nodeReader` أدناه)، وفي المتصفّح من `workspace.fs` — والوحدةُ نفسُها
 * لا تعرف أيَّهما، فلا تحمل استيرادًا يُسقِطها في أحد المضيفَين.
 */
function readData(read, file) {
  try {
    const text = read(file);
    return text == null ? null : JSON.parse(text);
  } catch {
    return null;
  }
}



/**
 * يحوّل المسردَ إلى صفوفٍ مفروزةً عربيًّا. **دالّةٌ نقيّةٌ** تُختبَر بلا محرّر.
 * @param {{terms?:{en:string, ar:string}[]}} glossary
 */
function glossaryRows(glossary) {
  const terms = (glossary && glossary.terms) || [];
  return sortArabic(
    terms.filter((t) => t && t.ar).map((t) => ({ ar: String(t.ar), en: String(t.en || "") })),
    (t) => t.ar
  );
}

/**
 * يسطّح مجموعاتِ الاختصارات إلى صفوف. يحفظ ترتيبَ المجموعات كما كُتِبت (ترتيبٌ تعليميٌّ
 * مقصود: أساسيّاتٌ ثمّ تحريرٌ ثمّ تنقّل)، ولا يفرزه عربيًّا — فالفرزُ هنا يُفقِد المعنى.
 */
function keybindingRows(kb) {
  const out = [];
  for (const g of (kb && kb.groups) || []) {
    for (const it of g.items || []) {
      if (!it || !it.ar) continue;
      out.push({ group: String(g.title || g.id || ""), ar: String(it.ar),
                 win: String(it.win || ""), mac: String(it.mac || it.win || "") });
    }
  }
  return out;
}

/**
 * يُرشِّح صفوفًا بالاستعلام **بعد تطبيع الطرفين** [DX-01].
 * @param {object[]} rows @param {string} query @param {string[]} fields الحقولُ المبحوثة.
 */
function filterRows(rows, query, fields) {
  const q = normalizeArabic(query || "");
  if (!q) return rows;
  return rows.filter((r) => fields.some((f) => normalizeArabic(String(r[f] || "")).includes(q)));
}

/** يهرب النصَّ لإدراجه في HTML (البياناتُ ملفّاتُنا، والهروبُ دفاعٌ في العمق لا شكّ فيها). */
function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

/** يبني HTML اللوحة. البياناتُ تُحقَن JSON ويُرشَّح في العرض (بحثٌ فوريٌّ بلا ذهابٍ وإياب). */
function buildHtml(glossary, keys, arabicDigits) {
  const nonce = randomNonce();
  const csp = [
    "default-src 'none'",
    `style-src 'nonce-${nonce}'`,
    `script-src 'nonce-${nonce}'`,
  ].join("; ");
  // [TY-06] أرقامُ **العرض** وحدَها تُحوَّل — وأرقامُ الاختصارات (`F5`، `Ctrl+Shift+B`)
  // أرقامُ **تعامل**: تُطابَق بما هو مطبوعٌ على لوحة المفاتيح، فتحويلُها يكسر التطابق.
  const shown = arabicDigits
    ? {
        glossary: glossary.map((g) => ({ ...g, ar: toArabicIndic(g.ar) })),
        keys: keys.map((k) => ({ ...k, ar: toArabicIndic(k.ar), group: toArabicIndic(k.group) })),
      }
    : { glossary, keys };
  const data = JSON.stringify(shown).replace(/</g, "\\u003c");
  return `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<style nonce="${nonce}">
  body { margin: 0; font-family: var(--vscode-font-family); color: var(--vscode-foreground);
         background: var(--vscode-editor-background); }
  header { position: sticky; top: 0; padding: 12px 16px 8px; background: var(--vscode-editor-background);
           border-bottom: 1px solid var(--vscode-editorWidget-border, transparent); }
  h1 { font-size: 1.15em; margin: 0 0 8px; }
  input { width: 100%; box-sizing: border-box; padding: 6px 10px; font: inherit; direction: rtl;
          color: var(--vscode-input-foreground); background: var(--vscode-input-background);
          border: 1px solid var(--vscode-input-border, transparent); border-radius: 3px; }
  nav { display: flex; gap: 6px; margin-top: 8px; }
  nav button { font: inherit; padding: 4px 12px; cursor: pointer; border-radius: 3px;
               color: var(--vscode-button-secondaryForeground); border: 1px solid transparent;
               background: var(--vscode-button-secondaryBackground); }
  nav button[aria-selected="true"] { color: var(--vscode-button-foreground);
                                     background: var(--vscode-button-background); }
  main { padding: 8px 16px 24px; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: start; padding: 5px 8px; border-bottom: 1px solid var(--vscode-editorWidget-border, #8884); }
  th { font-weight: 600; opacity: .8; }
  /* المفاتيح والأصلُ اللاتينيّ: اتّجاهٌ صريحٌ لا موروث — وإلّا قفزت المحايداتُ (‏Ctrl+Shift+P). */
  .key, .en { direction: ltr; unicode-bidi: isolate; text-align: start; font-family: var(--vscode-editor-font-family); }
  .group { margin: 14px 0 4px; font-weight: 600; opacity: .75; }
  .empty { padding: 24px 0; opacity: .7; }
  .count { margin: 6px 0 0; font-size: .88em; opacity: .7; min-height: 1.2em; }
</style>
</head>
<body>
<header>
  <h1>${esc(COPY.title)}</h1>
  <input id="q" type="search" placeholder="${esc(COPY.searchPlaceholder)}" aria-label="${esc(COPY.searchPlaceholder)}">
  <nav role="tablist" aria-label="${esc(COPY.title)}">
    <button id="t-glossary" role="tab" aria-selected="true" aria-controls="out" tabindex="0">${esc(COPY.tabGlossary)}</button>
    <button id="t-keys" role="tab" aria-selected="false" aria-controls="out" tabindex="-1">${esc(COPY.tabKeys)}</button>
  </nav>
  <!-- عدّادٌ ناطق: الكتابةُ تغيّر الجدولَ بلا إعلان، فمستخدمُ قارئ الشاشة يكتب ويسمع صمتًا. -->
  <p id="count" class="count" aria-live="polite"></p>
</header>
<main id="out" role="tabpanel" tabindex="0" aria-labelledby="t-glossary"></main>
<script nonce="${nonce}">
  const DATA = ${data};
  const COPY = ${JSON.stringify(COPY)};
  const IS_MAC = ${JSON.stringify(process.platform === 'darwin')};
  let tab = 'glossary';
  const out = document.getElementById('out');
  const q = document.getElementById('q');

  // [DX-01] تطبيعٌ **مشتقٌّ بالكامل** من arabic-normalize.js — لا منسوخٌ بيد.
  // الخريطةُ والأنماطُ الثلاثةُ تُحقَن من الوحدة نفسِها، فتوسيعُ نطاقٍ هناك يسري هنا.
  // (كانت الأنماطُ منسوخةً حرفيًّا، فكان توسيعُ التشكيل غدًا يجعل بحثَ اللوحة يفترق صامتًا
  //  عن بحثِ الإكمال — انجرافٌ لا يمسكه اختبارٌ ولا حارس.)
  const FOLD = ${JSON.stringify(FOLD_OBJECT)};
  const RE_TASHKEEL = new RegExp(${JSON.stringify(N.TASHKEEL_RE.source)}, 'g');
  const RE_TATWEEL = new RegExp(${JSON.stringify(N.TATWEEL_RE.source)}, 'g');
  const RE_BIDI = new RegExp(${JSON.stringify(N.BIDI_MARKS_RE.source)}, 'g');
  function norm(s) {
    if (!s) return '';
    let t = s.normalize('NFKC')
      .replace(RE_TASHKEEL, '')
      .replace(RE_TATWEEL, '')
      .replace(RE_BIDI, '');
    let o = '';
    for (const ch of t) {
      if (FOLD[ch] !== undefined) { o += FOLD[ch]; continue; }
      const cp = ch.codePointAt(0);
      if (cp >= 0x0660 && cp <= 0x0669) o += String.fromCharCode(0x30 + cp - 0x0660);
      else if (cp >= 0x06F0 && cp <= 0x06F9) o += String.fromCharCode(0x30 + cp - 0x06F0);
      else o += ch;
    }
    return o.toLowerCase();
  }

  const el = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  };

  const FIELDS = { glossary: ['ar', 'en'], keys: ['ar', 'win', 'mac', 'group'] };
  const match = (rows, fields, needle) =>
    needle ? rows.filter(r => fields.some(f => norm(r[f] || '').indexOf(needle) >= 0)) : rows;
  // [TY-06] أرقامُ العرض (العدّاد) تتبع الإعداد؛ وأرقامُ المفاتيح لا تُمَسّ.
  const AR_DIGITS = ${JSON.stringify(!!arabicDigits)};
  const showNum = (n) => AR_DIGITS
    ? String(n).replace(/\d/g, d => String.fromCharCode(0x0660 + (+d))) : String(n);

  function render() {
    const needle = norm(q.value);
    out.textContent = '';
    const rows = tab === 'glossary' ? DATA.glossary : DATA.keys;
    const hits = match(rows, FIELDS[tab], needle);
    document.getElementById('count').textContent =
      needle ? COPY.count.replace('{n}', showNum(hits.length)) : '';
    if (!hits.length) {
      // **لا تنصح نصيحةً خاطئة.** الكلمةُ قد تكون في التبويب الآخر على بُعد نقرة، وتقصيرُها
      // لن ينفع. فنقول أين الجواب بدل أن نلوم البحث.
      const otherTab = tab === 'glossary' ? 'keys' : 'glossary';
      const n = match(otherTab === 'glossary' ? DATA.glossary : DATA.keys,
                      FIELDS[otherTab], needle).length;
      const label = otherTab === 'glossary' ? COPY.tabGlossary : COPY.tabKeys;
      out.appendChild(el('div', 'empty', n
        ? COPY.emptyHere.replace('{n}', showNum(n)).replace('{other}', label)
        : COPY.empty));
      return;
    }
    const table = el('table');
    const head = el('tr');
    head.appendChild(el('th', null, tab === 'glossary' ? COPY.colTerm : COPY.colAction));
    head.appendChild(el('th', null, tab === 'glossary' ? COPY.colEnglish : COPY.colKey));
    table.appendChild(head);
    let lastGroup = null;
    for (const r of hits) {
      if (tab === 'keys' && r.group !== lastGroup) {
        lastGroup = r.group;
        const tr = el('tr');
        const td = el('td', 'group', r.group);
        td.colSpan = 2;
        tr.appendChild(td);
        table.appendChild(tr);
      }
      const tr = el('tr');
      tr.appendChild(el('td', null, r.ar));
      tr.appendChild(el('td', tab === 'glossary' ? 'en' : 'key',
        tab === 'glossary' ? r.en : (IS_MAC ? r.mac : r.win)));
      table.appendChild(tr);
    }
    out.appendChild(table);
  }

  const tabs = { glossary: document.getElementById('t-glossary'), keys: document.getElementById('t-keys') };
  function selectTab(next) {
    tab = next;
    for (const [k, btn] of Object.entries(tabs)) {
      const on = k === next;
      btn.setAttribute('aria-selected', String(on));
      // تبويبٌ واحدٌ في ترتيب Tab (نمطُ ARIA): الأسهمُ تتنقّل بينها لا Tab.
      btn.tabIndex = on ? 0 : -1;
    }
    out.setAttribute('aria-labelledby', tabs[next].id);
    render();
  }
  for (const [k, btn] of Object.entries(tabs)) {
    btn.addEventListener('click', () => selectTab(k));
    btn.addEventListener('keydown', (e) => {
      // في تخطيطٍ من اليمين: «التالي» بصريًّا هو السهمُ الأيسر. نقبل الاثنين للتنقّل الدوريّ.
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
      e.preventDefault();
      const next = k === 'glossary' ? 'keys' : 'glossary';
      selectTab(next);
      tabs[next].focus();
    });
  }
  // Escape يغلق اللوحة: بلا ذلك تبقى تأكل نصفَ العرض حتّى يُغلِقها المستخدم بالفأرة.
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') vscode.postMessage({ type: 'close' });
  });
  q.addEventListener('input', render);
  render();
  q.focus();
</script>
</body>
</html>`;
}

/** لوحةُ المساعدة: مفردةٌ تُعاد استعمالها، وتُدار بـ`dispose`. */
class HelpPanel {
  /**
   * @param {*} vscode
   * @param {*} context
   * @param {(file:string)=>string|null} [read] قارئُ بياناتٍ بديل. غيابُه ⇒ قارئُ العقدة.
   *   يُمرَّر في المتصفّح، حيث لا `fs` ولا مسارات — و`workspace.fs` لا يقرأ متزامنًا،
   *   فالنصُّ يُجلَب مرّةً عند التنشيط ويُقدَّم هنا من ذاكرةٍ (‏`open` يبقى متزامنًا).
   */
  constructor(vscode, context, read) {
    this.vscode = vscode;
    this.context = context;
    this.read = read || null;
    this._panel = null;
  }

  /** يفتح اللوحةَ (أو يرفعها إن كانت مفتوحة). يعيد `false` إن تعذّرت قراءةُ البيانات. */
  open() {
    const vscode = this.vscode;
    if (this._panel) {
      this._panel.reveal();
      return true;
    }
    // قارئٌ غائبٌ ⇒ صفوفٌ خاوية ⇒ الرسالةُ الصريحةُ أدناه. ولا ارتدادَ إلى `fs` هنا:
    // مجرّدُ ذكرِ الاسم في هذا الملفّ يُسقِط حزمةَ المتصفّح عند البناء (‏esbuild يحلّ
    // الاستيرادَ نصًّا، ولا يعبأ بأنّه داخل دالّة). فالقارئُ يُحقَن من المدخل.
    const read = this.read || (() => null);
    const glossary = glossaryRows(readData(read, GLOSSARY_FILE));
    const keys = keybindingRows(readData(read, KEYBINDINGS_FILE));
    // [TY-06] الإعدادُ يُقرأ عند الفتح لا يُخزَّن: تبديلُه ثمّ إعادةُ الفتح يُظهِر أثرَه.
    const arabicDigits = !!vscode.workspace.getConfiguration().get(DIGITS_SETTING);
    // **لا لوحةَ فارغةً بلا تفسير.** بياناتٌ غائبةٌ تُقال، لا تُعرَض جدولًا خاويًا.
    if (!glossary.length && !keys.length) {
      vscode.window.showWarningMessage(COPY.loadFailed);
      return false;
    }
    const panel = vscode.window.createWebviewPanel(
      PANEL_TYPE, PANEL_TITLE,
      { viewColumn: vscode.ViewColumn.Beside, preserveFocus: false },
      { enableScripts: true, retainContextWhenHidden: true, localResourceRoots: [] }
    );
    panel.webview.html = buildHtml(glossary, keys, arabicDigits);
    panel.webview.onDidReceiveMessage((m) => {
      if (m && m.type === "close") panel.dispose();
    });
    panel.onDidDispose(() => { this._panel = null; });
    this._panel = panel;
    return true;
  }

  dispose() {
    if (this._panel) {
      try {
        this._panel.dispose();
      } catch {
        /* تجاهُلٌ مقصود عند الإغلاق */
      }
      this._panel = null;
    }
  }
}

module.exports = {
  HelpPanel, buildHtml, glossaryRows, keybindingRows, filterRows, readData, randomNonce,
  OPEN_CMD, PANEL_TYPE, PANEL_TITLE, DATA_DIR, GLOSSARY_FILE, KEYBINDINGS_FILE,
  DIGITS_SETTING, COPY,
};
