"use strict";
/**
 * اختباراتُ الموجة الثالثة — الوحداتُ النقيّة: تسميةُ محارف الاتّجاه [BS-02]، وحارسُ
 * الأسماء [BS-03]، والترتيبُ العربيّ [DX-06]، والمساعدةُ داخل المحرّر [ON-03]،
 * وإخبارُ الإصدارات [ON-04].
 */
const test = require("node:test");
const assert = require("node:assert");

const D = require("./bidi-decorate.js");
const V = require("./validate-name.js");
const NG = require("./name-guard.js");
const S = require("./arabic-sort.js");
const H = require("./help-panel.js");
// [WEB-06] القارئُ صار مُحقَنًا — والقرصُ يسكن وحدةً خاصّةً بالمكتب.
const { nodeReader } = require("./help-data-node.js");
const READ = nodeReader(__dirname);
const R = require("./release-notice.js");

const ch = (cp) => String.fromCharCode(cp);
const RLO = ch(0x202e), RLM = ch(0x200f), PDF = ch(0x202c);

// ───────────────────── [BS-02] تسميةُ محارف الاتّجاه ─────────────────────

test("يُسمّي كلَّ محرفٍ في المدى المرئيّ، الشرعيَّ والمشبوهَ معًا", () => {
  const items = D.decorationsFor("a" + RLM + "b\nc" + RLO + "d" + PDF, 0, 1);
  assert.deepStrictEqual(items.map((i) => i.code), ["RLM", "RLO", "PDF"]);
  // الرقاقةُ **معزولةٌ اتّجاهيًّا**: القوسان ⟪⟫ محايدان ومرآتيّان فينقلبان في سطرٍ عربيّ.
  assert.deepStrictEqual(items.map((i) => i.label),
    ["⁦⟪RLM⟫⁩", "⁦⟪RLO⟫⁩", "⁦⟪PDF⟫⁩"]);
});

test("الأسطرُ خارج المدى المرئيّ لا تُزخرَف (ملفٌّ بألوفِ العلامات لا يبني ألوفَ زخارف)", () => {
  const text = ["a" + RLM, "b" + RLM, "c" + RLM, "d" + RLM].join("\n");
  assert.strictEqual(D.decorationsFor(text, 1, 2).length, 2);
  assert.strictEqual(D.decorationsFor(text, 0, 3).length, 4);
});

test("التلميحُ يميّز العلامةَ الشرعيّةَ من القالب — والقرارُ بلا معلومةٍ قرارٌ عشوائيّ", () => {
  const [mark] = D.decorationsFor(RLM, 0, 0);
  const [ctrl] = D.decorationsFor(RLO, 0, 0);
  assert.ok(mark.hover.includes("مشروعة"), mark.hover);
  assert.ok(ctrl.hover.includes("يقلب"), ctrl.hover);
});

test("سقفُ الزخارف يُحترَم", () => {
  const many = RLM.repeat(D.MAX_DECORATIONS + 50);
  assert.strictEqual(D.decorationsFor(many, 0, 0).length, D.MAX_DECORATIONS);
});

// ───────────────────── [BS-03] حارسُ الأسماء ─────────────────────

test("اسمٌ عربيٌّ سليمٌ يمرّ", () => {
  assert.strictEqual(V.checkName("مرحبا.ص"), null);
  assert.strictEqual(V.checkName("مشروع-ص_2"), null);
});

test("الانتحالُ يُكشَف **ويُسمّى** (كي يعرف المستخدمُ ما الذي يُزال)", () => {
  const bad = V.checkName("ملف" + RLO + "gpj.exe");
  assert.strictEqual(bad.reason, V.REASON.BIDI_SPOOF);
  assert.deepStrictEqual(bad.chars, ["U+202E"]);
});

test("الانتحالُ يُفحَص **قبل** المحارف الممنوعة (وإلّا ضاع السببُ الأدقّ)", () => {
  const bad = V.checkName("ملف" + RLO + "/x");
  assert.strictEqual(bad.reason, V.REASON.BIDI_SPOOF, "السببُ المُسمّى أنفعُ من «محارف غير صالحة»");
});

test("بقيّةُ الأسباب تبقى كما كانت (لا انحدارَ بالاستخراج)", () => {
  assert.strictEqual(V.checkName("  ").reason, V.REASON.EMPTY);
  assert.strictEqual(V.checkName("..").reason, V.REASON.DOT_NAMES);
  assert.strictEqual(V.checkName("a/b").reason, V.REASON.INVALID_CHARS);
  assert.strictEqual(V.checkName("اسم.").reason, V.REASON.TRAILING_DOT_SPACE);
  assert.strictEqual(V.checkName("CON.txt").reason, V.REASON.RESERVED);
  assert.strictEqual(V.checkName("x".repeat(256)).reason, V.REASON.TOO_LONG);
});

test("الإزالةُ تمسّ محارفَ الانتحال وحدَها", () => {
  assert.strictEqual(V.stripSpoofChars("ملف" + RLO + "x"), "ملفx");
  assert.strictEqual(V.stripSpoofChars("ملف-عاديّ.ص"), "ملف-عاديّ.ص");
  assert.strictEqual(V.stripSpoofChars(null), "");
});

test("‏basenameOf يستخرج الاسمَ من مسار URI، وspoofCharsIn يحكم عليه", () => {
  assert.strictEqual(NG.basenameOf({ path: "/a/b/مرحبا.ص" }), "مرحبا.ص");
  assert.strictEqual(NG.basenameOf({ path: "بلا-فاصل" }), "بلا-فاصل");
  assert.strictEqual(NG.basenameOf(null), "");
  assert.deepStrictEqual(NG.spoofCharsIn("x" + RLO + "y"), ["U+202E"]);
  assert.strictEqual(NG.spoofCharsIn("مرحبا.ص"), null);
  // اسمٌ ممنوعٌ لسببٍ آخرَ ليس شأنَ هذا الحارس: نظامُ الملفّات يرفضه ويعرض خطأه.
  assert.strictEqual(NG.spoofCharsIn("CON.txt"), null);
});

// ───────────────────── [DX-06] الترتيبُ العربيّ ─────────────────────

test("الهمزاتُ تتجاور بدل أن تتباعد بنقطة الكود", () => {
  const names = ["احمد", "بشير", "أحمد", "إبراهيم", "ابراهيم"];
  const sorted = S.sortArabic(names);
  // «أحمد» و«احمد» متجاورتان، و«إبراهيم» و«ابراهيم» كذلك — والبشير بعدهما.
  assert.strictEqual(Math.abs(sorted.indexOf("أحمد") - sorted.indexOf("احمد")), 1);
  assert.strictEqual(Math.abs(sorted.indexOf("إبراهيم") - sorted.indexOf("ابراهيم")), 1);
  assert.strictEqual(sorted[sorted.length - 1], "بشير");
});

test("الترتيبُ الطبيعيُّ للأرقام داخل الأسماء", () => {
  assert.deepStrictEqual(S.sortArabic(["ملف10", "ملف2", "ملف1"]), ["ملف1", "ملف2", "ملف10"]);
});

test("الفرزُ لا يعدّل الأصل (دالّةٌ نقيّة)", () => {
  const src = ["ب", "أ"];
  const out = S.sortArabic(src);
  assert.deepStrictEqual(src, ["ب", "أ"]);
  assert.notStrictEqual(out, src);
});

test("يفرز بمفتاحٍ مستخرَجٍ حين تكون العناصرُ كائنات", () => {
  const rows = [{ ar: "ب" }, { ar: "أ" }];
  assert.deepStrictEqual(S.sortArabic(rows, (r) => r.ar).map((r) => r.ar), ["أ", "ب"]);
});

// ───────────────────── [ON-03] المساعدةُ داخل المحرّر ─────────────────────

test("المسردُ يُقرأ ويُفرَز عربيًّا", () => {
  const rows = H.glossaryRows(H.readData(READ, H.GLOSSARY_FILE));
  assert.ok(rows.length >= 20, "قُرِئ المسردُ المحزوم: " + rows.length);
  assert.deepStrictEqual(rows.map((r) => r.ar), S.sortArabic(rows.map((r) => r.ar)));
});

test("الاختصاراتُ تُسطَّح بحفظ ترتيب المجموعات (ترتيبٌ تعليميٌّ مقصود)", () => {
  const rows = H.keybindingRows(H.readData(READ, H.KEYBINDINGS_FILE));
  assert.ok(rows.length >= 50, String(rows.length));
  // [DX-03] مجموعةُ «لغة ص» أوّلًا عمدًا: هي ما يخصّ محرابًا، ويجب أن تُرى قبل عموميّات
  // المنبع — وقد كانت غائبةً كلَّها، فكانت اللوحةُ تناقض الجولةَ حول F5.
  assert.strictEqual(rows[0].group, "لغة ص", "المجموعةُ الأولى كما كُتِبت لا مفروزةً");
  assert.ok(rows.some((r) => r.win === "F5" && r.ar.includes("شغّل ملفّ ص")),
    "لوحةُ المساعدة تعرف اختصاراتِ ص التي تعلّمها الجولة");
  assert.ok(rows.every((r) => r.ar && r.win));
});

test("‏[DX-01 حيًّا] البحثُ يجد رغم اختلاف الهمزة والتاء المربوطة والتشكيل", () => {
  const rows = H.glossaryRows(H.readData(READ, H.GLOSSARY_FILE));
  const f = (q) => H.filterRows(rows, q, ["ar", "en"]).map((r) => r.ar);
  assert.deepStrictEqual(f("لوحه الاوامر"), ["لوحة الأوامر"], "بلا همزةٍ ولا تاءٍ مربوطة");
  assert.deepStrictEqual(f("لوحة الأوامر"), ["لوحة الأوامر"], "بالرسم الكامل");
  assert.ok(f("Command").includes("لوحة الأوامر"), "بالإنجليزيّة أيضًا");
  assert.strictEqual(f("").length, rows.length, "استعلامٌ فارغٌ يعرض الكلّ");
});

test("بياناتٌ مفقودةٌ تُقرأ `null` ولا ترمي (سقوطٌ لطيف)", () => {
  assert.strictEqual(H.readData(READ, "لا-وجود-له.json"), null);
  assert.deepStrictEqual(H.glossaryRows(null), []);
  assert.deepStrictEqual(H.keybindingRows(null), []);
});

test("‏HTML اللوحة: بلا مورد خارجيّ، وبـCSP صارم، ونصٌّ مهروب", () => {
  // عيّنةٌ فيها **المحارفُ الخمسةُ الخطِرةُ كلُّها** لا `<` وحدَه: بيانُ اللوحة يُحقَن
  // JSON لا HTML، وهذا هو ما يُختبَر — أن يبقى الحقنُ مُغلَقًا مهما كان النصّ [PF-02].
  const nasty = `<script>alert(1)</script>&"'>`;
  const html = H.buildHtml([{ ar: nasty, en: "x" }], []);
  assert.ok(html.includes("default-src 'none'"), "CSP صارم");
  assert.ok(!/https?:\/\//.test(html), "لا مورد خارجيّ إطلاقًا");
  assert.ok(html.includes('dir="rtl"') && html.includes('lang="ar"'));
  assert.ok(!/<script>alert/.test(html), "النصُّ مهروبٌ لا مُدرَجٌ HTML");
});

// ───────────────────── [ON-04] إخبارُ الإصدارات ─────────────────────

test("مقارنةُ الإصدارات **رقميّةٌ لا نصّيّة**", () => {
  assert.strictEqual(R.compareVersions("1.121.5141", "1.121.999"), 1, "٥١٤١ > ٩٩٩ رقميًّا");
  assert.strictEqual(R.compareVersions("1.2", "1.2.0"), 0);
  assert.strictEqual(R.compareVersions("1.2.0", "1.10.0"), -1);
});

test("‏evaluateManifest يميّز الأحدثَ ويحتمل مانيفستًا فاسدًا", () => {
  assert.deepStrictEqual(R.evaluateManifest({ version: "2.0.0" }, "1.0.0"),
    { newer: true, version: "2.0.0" });
  assert.deepStrictEqual(R.evaluateManifest({ version: "1.0.0" }, "1.0.0"),
    { newer: false, version: "1.0.0" });
  assert.deepStrictEqual(R.evaluateManifest(null, "1.0.0"), { newer: false, version: null });
  assert.deepStrictEqual(R.evaluateManifest({}, "1.0.0"), { newer: false, version: null });
});

test("الفاصلُ الزمنيُّ يمنع فحصًا في كلّ إقلاع", () => {
  assert.ok(R.isDue(undefined, 1000), "أوّلُ مرّةٍ مستحقّة");
  assert.ok(!R.isDue(1000, 1000 + R.MIN_INTERVAL_MS - 1));
  assert.ok(R.isDue(1000, 1000 + R.MIN_INTERVAL_MS));
});

function fakeVs(opts = {}) {
  const st = { info: [], warn: [], opened: [] };
  let asked = 0;
  return {
    st,
    vscode: {
      Uri: { parse: (u) => u },
      env: { openExternal: async (u) => { st.opened.push(u); } },
      window: {
        showInformationMessage: async (m, ...items) => {
          st.info.push(m);
          const a = asked++ === 0 ? opts.answer : opts.answer2;
          return a === undefined ? undefined : items[a];
        },
        showWarningMessage: (m) => { st.warn.push(m); },
      },
    },
  };
}
const mem = (init = {}) => {
  const s = { ...init };
  return { get: (k) => s[k], update: async (k, v) => { s[k] = v; }, _s: s };
};
const deps = (o) => ({
  fetchManifest: async () => ({ version: "2.0.0" }),
  currentVersion: "1.0.0",
  downloadUrl: "https://example.invalid/dl",
  now: 1_000_000,
  ...o,
});

test("**لا شبكةَ بلا إذنٍ صريح** — ورفضُ الإذن يُحترَم في كلّ إقلاع", async () => {
  let fetched = 0;
  const m = mem();
  const a = fakeVs({ answer: 1 }); // «لا، شكرًا»
  await R.checkForUpdate(a.vscode, m, deps({ fetchManifest: async () => { fetched++; return {}; } }));
  assert.strictEqual(fetched, 0, "لم تُمَسّ الشبكةُ إطلاقًا");
  assert.strictEqual(m.get(R.CONSENT_KEY), false);

  const b = fakeVs();
  await R.checkForUpdate(b.vscode, m, deps({ fetchManifest: async () => { fetched++; return {}; } }));
  assert.strictEqual(fetched, 0);
  assert.strictEqual(b.st.info.length, 0, "ولا يُسأل ثانيةً");
});

test("إغلاقُ سؤال الإذن يؤجّله ولا يُسجَّل رفضًا", async () => {
  const m = mem();
  const a = fakeVs(); // answer undefined ⇒ أُغلِق
  await R.checkForUpdate(a.vscode, m, deps());
  assert.strictEqual(m.get(R.CONSENT_KEY), undefined, "لم يُحسَم — يُسأل لاحقًا");
});

test("بالإذن: يُخبَر بالأحدث مرّةً، ويفتح صفحةَ التنزيل عند الطلب", async () => {
  const m = mem({ [R.CONSENT_KEY]: true });
  const a = fakeVs({ answer: 0 }); // «افتح صفحة التنزيل»
  const r = await R.checkForUpdate(a.vscode, m, deps());
  assert.deepStrictEqual(r, { checked: true, newer: true, version: "2.0.0" });
  assert.deepStrictEqual(a.st.opened, ["https://example.invalid/dl"]);

  // الفاصلُ الزمنيُّ يمنع التكرارَ في الإقلاع التالي.
  const b = fakeVs({ answer: 0 });
  const r2 = await R.checkForUpdate(b.vscode, m, deps({ now: 1_000_001 }));
  assert.strictEqual(r2.checked, false);
  assert.strictEqual(b.st.info.length, 0);
});

test("لا يُكرَّر الخبرُ عن الإصدار نفسِه ولو حان الفاصل", async () => {
  const m = mem({ [R.CONSENT_KEY]: true });
  const a = fakeVs({ answer: 1 });
  await R.checkForUpdate(a.vscode, m, deps());
  assert.strictEqual(a.st.info.length, 1);
  const b = fakeVs({ answer: 1 });
  await R.checkForUpdate(b.vscode, m, deps({ now: 1_000_000 + R.MIN_INTERVAL_MS * 2 }));
  assert.strictEqual(b.st.info.length, 0, "الإصدارُ نفسُه — لا خبرَ مكرّر");
});

test("الفشلُ صامتٌ في الفحص الدوريّ، مُعلَنٌ في الطلب اليدويّ", async () => {
  const m = mem({ [R.CONSENT_KEY]: true });
  const a = fakeVs();
  await R.checkForUpdate(a.vscode, m, deps({ fetchManifest: async () => { throw new Error("لا شبكة"); } }));
  assert.strictEqual(a.st.warn.length, 0, "صمتُ الفحص الدوريّ أدب");

  const b = fakeVs();
  await R.checkForUpdate(b.vscode, m, deps({
    force: true, now: 2_000_000,
    fetchManifest: async () => { throw new Error("لا شبكة"); },
  }));
  assert.strictEqual(b.st.warn[0], R.COPY.failed, "وصمتُ الطلب إهمال");
});

test("الطلبُ اليدويُّ يقول «محدَّث» حين لا جديد (لا يُترَك المستخدمُ بلا جواب)", async () => {
  const m = mem({ [R.CONSENT_KEY]: true });
  const a = fakeVs();
  await R.checkForUpdate(a.vscode, m, deps({ force: true, fetchManifest: async () => ({ version: "1.0.0" }) }));
  assert.strictEqual(a.st.info[0], R.COPY.upToDate("1.0.0"));
});
