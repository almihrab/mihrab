"use strict";
/**
 * اختباراتُ استيراد إعدادات VS Code ‏[MG-01].
 *
 * الدوالُّ المختبَرةُ هنا نقيّةٌ عمدًا (‏`candidateUserDirs` تأخذ `env`/`platform`/`exists`،
 * و`classify` تأخذ خريطةَ الملكيّة، و`planUndo` تأخذ قارئًا) — فما دون ذلك (اللوحةُ
 * والكتابةُ في نطاق المستخدم) يبقى غلافًا رفيعًا فوق منطقٍ محكومٍ هنا.
 */

const test = require("node:test");
const assert = require("node:assert");
const path = require("node:path");

const imp = require("./import-settings.js");

// ────────────────────────── قائمةُ التعارض: مشتقّةٌ لا مكتوبة ──────────────────────────

test("mihrabOwnedKeys يلتقط المفاتيحَ داخلَ كتلِ نطاقات اللغات — لا الكتلةَ وحدَها", () => {
  const owned = imp.mihrabOwnedKeys({
    "editor.fontSize": 15,
    "[python]": { "editor.wordWrap": "on", "editor.fontLigatures": true },
  });
  assert.strictEqual(owned.get("editor.fontSize"), 15);
  // الكتلةُ نفسُها مملوكة…
  assert.ok(owned.has("[python]"));
  // …ومعها كلُّ مفتاحٍ فيها: قيمةُ المستخدم **العالميّة** تغلب نطاقَنا اللغويّ.
  assert.strictEqual(owned.get("editor.wordWrap"), "on");
  assert.strictEqual(owned.get("editor.fontLigatures"), true);
});

test("mihrabOwnedKeys يستبعد مفاتيحَ التعليق — توثيقٌ لا إعداد", () => {
  const owned = imp.mihrabOwnedKeys({
    _comment_fontSize: "لماذا ‎15‎",
    "editor.fontSize": 15,
    "[python]": { _comment_wrap: "لماذا", "editor.wordWrap": "on" },
  });
  assert.deepStrictEqual([...owned.keys()].sort(),
    ["[python]", "editor.fontSize", "editor.wordWrap"]);
});

test("mihrabOwnedKeys يحتمل الغياب — لا يرمي على غير كائن", () => {
  assert.strictEqual(imp.mihrabOwnedKeys(null).size, 0);
  assert.strictEqual(imp.mihrabOwnedKeys({ "[x]": null }).size, 1);
});

// ────────────────────────── التصنيف: التساوي لا يُسقِط التحذير ──────────────────────────

test("classify يفرز المملوكَ متعارضًا وغيرَه متوافقًا", () => {
  const owned = imp.mihrabOwnedKeys({ "editor.fontSize": 15 });
  const r = imp.classify({ "editor.fontSize": 14, "files.autoSave": "off" }, owned);
  assert.deepStrictEqual(r.compatible, [{ key: "files.autoSave", value: "off" }]);
  assert.strictEqual(r.conflicting.length, 1);
  assert.strictEqual(r.conflicting[0].key, "editor.fontSize");
  assert.strictEqual(r.conflicting[0].mihrab, 15);
});

test("قيمةٌ **تساوي** قيمتَنا تبقى متعارضة — الاستيرادُ يرقّي الصدفةَ إلى قرار", () => {
  // مَن كتب `15` في نطاقه صدفةً يُجمِّد المفتاحَ عليها، فلا يبلغه أيُّ تحسينٍ لاحقٍ في
  // افتراضاتنا. الاختلافُ ليس شرطَ الخطر — الملكيّةُ هي الشرط.
  const owned = imp.mihrabOwnedKeys({ "editor.fontSize": 15 });
  const r = imp.classify({ "editor.fontSize": 15 }, owned);
  assert.strictEqual(r.compatible.length, 0);
  assert.strictEqual(r.conflicting.length, 1);
});

test("classify يرتّب المخرجَ بالمفتاح — لوحةٌ تتبدّل صفوفُها بين فتحتين لا تُقرَأ", () => {
  const owned = imp.mihrabOwnedKeys({});
  const r = imp.classify({ z: 1, a: 2, m: 3 }, owned);
  assert.deepStrictEqual(r.compatible.map((c) => c.key), ["a", "m", "z"]);
});

test("لكلّ متعارضٍ سطرُ أثرٍ غيرُ فارغ — ولو لم يُكتَب له سطرٌ خاصّ", () => {
  const owned = imp.mihrabOwnedKeys({ "editor.fontLigatures": true, "some.new.key": 1 });
  const r = imp.classify({ "editor.fontLigatures": false, "some.new.key": 2 }, owned);
  for (const c of r.conflicting) assert.ok(c.impact && c.impact.length > 10, c.key);
  // المفتاحُ الموصوفُ يأخذ سطرَه المقيس، والجديدُ يأخذ الصيغةَ العامّة الصادقة.
  assert.strictEqual(r.conflicting.find((c) => c.key === "editor.fontLigatures").impact,
    imp.IMPACT["editor.fontLigatures"]);
  assert.notStrictEqual(imp.impactFor("some.new.key"), imp.IMPACT["editor.fontLigatures"]);
});

test("impactFor يعرف عائلةَ إبراز يونيكود وكتلَ نطاقات اللغات", () => {
  assert.match(imp.impactFor("editor.unicodeHighlight.nonBasicASCII"), /الإطارات/);
  assert.match(imp.impactFor("[python]"), /نطاق لغة/);
});

// ────────────────────────── JSONC: ملفُّ المستخدم مُعلَّقٌ غالبًا ──────────────────────────

test("parseJsonc يقبل التعليقاتِ والفاصلةَ الزائدة", () => {
  const txt = `{
    // تعليقُ سطر
    "a": 1, /* تعليقٌ ممتدّ */
    "b": [1, 2,],
  }`;
  assert.deepStrictEqual(imp.parseJsonc(txt), { a: 1, b: [1, 2] });
});

test("parseJsonc لا يقصّ «//» داخلَ سلسلة — وإلّا بُتِرت القيمةُ من منتصفها", () => {
  const r = imp.parseJsonc('{ "url": "https://example.org/x", "s": "/* ليس تعليقًا */" }');
  assert.strictEqual(r.url, "https://example.org/x");
  assert.strictEqual(r.s, "/* ليس تعليقًا */");
});

test("parseJsonc يحترم الهروبَ داخلَ السلسلة", () => {
  assert.deepStrictEqual(imp.parseJsonc('{ "a": "x\\"//y" }'), { a: 'x"//y' });
});

// ────────────────────────── مواضعُ المصدر: ثلاثُ توزيعاتٍ لا واحدة ──────────────────────────

test("candidateUserDirs يعدّد التوزيعاتِ الموجودةَ وحدَها على ويندوز", () => {
  const appdata = path.join("C:", "Users", "x", "AppData", "Roaming");
  const present = new Set([
    path.join(appdata, "Code", "User"),
    path.join(appdata, "VSCodium", "User"),
  ]);
  const out = imp.candidateUserDirs({ APPDATA: appdata }, "win32", (p) => present.has(p));
  assert.deepStrictEqual(out.map((c) => c.label), ["Visual Studio Code", "VSCodium"]);
});

test("candidateUserDirs يستعمل XDG_CONFIG_HOME على لينكس ثمّ ‎~/.config‎", () => {
  const a = imp.candidateUserDirs({ XDG_CONFIG_HOME: "/cfg", HOME: "/h" }, "linux",
    (p) => p === path.join("/cfg", "Code", "User"));
  assert.deepStrictEqual(a.map((c) => c.dir), [path.join("/cfg", "Code", "User")]);
  const b = imp.candidateUserDirs({ HOME: "/h" }, "linux",
    (p) => p === path.join("/h", ".config", "Code", "User"));
  assert.strictEqual(b.length, 1);
});

test("candidateUserDirs يقرأ Library/Application Support على ماك", () => {
  const dir = path.join("/h", "Library", "Application Support", "Code", "User");
  const out = imp.candidateUserDirs({ HOME: "/h" }, "darwin", (p) => p === dir);
  assert.deepStrictEqual(out, [{ label: "Visual Studio Code", dir }]);
});

test("candidateUserDirs يعود فارغًا بلا بيتٍ ولا APPDATA — لا يرمي", () => {
  assert.deepStrictEqual(imp.candidateUserDirs({}, "win32", () => true), []);
});

// ────────────────────────── اللقطةُ والتراجع ──────────────────────────

test("buildSnapshot يسجّل ما كان وما كُتِب — للمكتوبِ وحدَه", () => {
  const before = { "a.b": "قديم" };
  const snap = imp.buildSnapshot(
    [{ key: "a.b", value: "جديد" }], (k) => before[k], "٢٠٢٦");
  assert.strictEqual(snap.at, "٢٠٢٦");
  assert.deepStrictEqual(snap.entries, [{ key: "a.b", before: "قديم", wrote: "جديد" }]);
});

test("planUndo يعيد ما زال على ما كتبناه، ويترك ما غيّره المستخدمُ بيده", () => {
  const snap = {
    entries: [
      { key: "a", before: 1, wrote: 2 },   // ما زال ‎2‎ ⇒ يُعاد إلى ‎1‎
      { key: "b", before: 3, wrote: 4 },   // صار ‎9‎ بيد المستخدم ⇒ يُترَك
    ],
  };
  const now = { a: 2, b: 9 };
  const { restore, kept } = imp.planUndo(snap, (k) => now[k]);
  assert.deepStrictEqual(restore, [{ key: "a", before: 1 }]);
  assert.deepStrictEqual(kept, ["b"]);
});

test("planUndo يقارن بالقيمة لا بالمرجع — كائنٌ متساوٍ يُعَدّ على حاله", () => {
  const snap = { entries: [{ key: "a", before: null, wrote: { x: [1, 2] } }] };
  const { restore, kept } = imp.planUndo(snap, () => ({ x: [1, 2] }));
  assert.strictEqual(restore.length, 1);
  assert.strictEqual(kept.length, 0);
});

test("planUndo على لقطةٍ غائبةٍ لا يرمي", () => {
  assert.deepStrictEqual(imp.planUndo(null, () => 1), { restore: [], kept: [] });
  assert.deepStrictEqual(imp.planUndo({}, () => 1), { restore: [], kept: [] });
});

test("مفتاحٌ كانت قيمتُه السابقةُ غيرَ معرَّفةٍ يُعاد إلى غير المعرَّف — أي يُمحى", () => {
  // الاستيرادُ كتبه في نطاق المستخدم ولم يكن فيه شيء؛ التراجعُ يعيده إلى **الغياب**
  // لا إلى قيمةٍ مخترَعة — وإلّا بقي المفتاحُ مُجمَّدًا بعد التراجع.
  const snap = { entries: [{ key: "a", before: undefined, wrote: 5 }] };
  const { restore } = imp.planUndo(snap, () => 5);
  assert.strictEqual(restore.length, 1);
  assert.strictEqual(restore[0].before, undefined);
});

// ────────────────────────── مصدرُ الحقيقة: افتراضاتُ القشرة ──────────────────────────

test("readShellDefaults يعود null حين يغيب امتدادُ القشرة — فيُعطَّل الاستيراد", () => {
  const fake = { extensions: { getExtension: () => undefined } };
  assert.strictEqual(imp.readShellDefaults(fake), null);
});

test("readShellDefaults يقرأ configurationDefaults من مانيفست القشرة", () => {
  const fake = {
    extensions: {
      getExtension: (id) => (id === imp.SHELL_EXT_ID
        ? { packageJSON: { contributes: { configurationDefaults: { "editor.fontSize": 15 } } } }
        : undefined),
    },
  };
  assert.deepStrictEqual(imp.readShellDefaults(fake), { "editor.fontSize": 15 });
});

// ────────────────────────── اللوحة: بياناتُ مستخدمٍ لا بياناتُنا ──────────────────────────

test("buildHtml يهرب وسمَ HTML الآتيَ من ملفّ المستخدم", () => {
  const html = imp.buildHtml({
    sourceDir: "C:\\x", compatible: [{ key: "<img src=x onerror=alert(1)>", value: 1 }],
    conflicting: [], keybindings: [], snippets: [],
  });
  assert.ok(!html.includes("<img src=x"), "وسمٌ خامٌ تسرّب إلى اللوحة");
});

test("buildHtml يحمل CSP بلا مصدرٍ خارجيّ، وnonce لكلّ نمطٍ وبرنامج", () => {
  const html = imp.buildHtml({
    sourceDir: "/x", compatible: [], conflicting: [], keybindings: [], snippets: [],
  });
  assert.match(html, /default-src 'none'/);
  const m = html.match(/script-src 'nonce-([^']+)'/);
  assert.ok(m, "لا nonce في CSP");
  assert.ok(html.includes(`<script nonce="${m[1]}">`));
  assert.ok(html.includes(`<style nonce="${m[1]}">`));
});

test("buildHtml يقفل حقنَ الوسم عبر بيانات النموذج المُسلسَلة", () => {
  const html = imp.buildHtml({
    sourceDir: "/x", compatible: [{ key: "a", value: "</script><script>y()" }],
    conflicting: [], keybindings: [], snippets: [],
  });
  assert.ok(!html.includes("</script><script>y()"), "‏</script> تسرّب داخل كتلة البرنامج");
});
