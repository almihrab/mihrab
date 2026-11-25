// اختبارُ وحدةٍ لتطبيع `--dump-failures` [PF-03] — node --test tests/meta/dump_norm.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { dumpText, failureText, makeNorm } from "./dump_norm.mjs";

// جذرٌ **داخل** المؤقّت كما في شجرة عملٍ تحت scratchpad — فالترتيبُ (الجذرُ أوّلًا) يُقاس.
const TMP = "C:\\Users\\Admin\\AppData\\Local\\Temp";
const ROOT = TMP + "\\claude\\x\\wt-proof";
const norm = makeNorm(ROOT, TMP);

test("الجذر بأيّ فاصلٍ وبالشرطتين المضاعفتين (%r وTAP location)", () => {
  const a = norm("· " + ROOT + "\\site\\b.js");
  const b = norm("· " + ROOT.replace(/\\/g, "/") + "/site/b.js");
  const c = norm("· '" + ROOT.replace(/\\/g, "\\\\") + "\\\\site\\\\b.js'");
  assert.equal(a, "· <ROOT>/site/b.js");
  assert.equal(b, a);
  assert.equal(c, "· '<ROOT>/site/b.js'");
});

test("المؤقّت: يُطبَّع اسمُ المجلّد العشوائيّ وحدَه ويبقى relpath داخله", () => {
  const a = norm(TMP + "\\tmpab12\\docs\\index.html: رابطٌ مكسور");
  const b = norm(TMP + "\\tmpzz99\\start\\index.html: رابطٌ مكسور");
  assert.equal(a, "<TMP>/docs/index.html: رابطٌ مكسور");
  assert.notEqual(a, b, "relpath داخل المؤقّت ابتُلِع: صفحتان مختلفتان تطابقتا");
  assert.equal(norm(TMP + "\\mihrab-a1\\x.css»"), "<TMP>/x.css»");
});

test("زمنُ node --test وأسماءُ OUT-01 العشوائيّة", () => {
  assert.equal(norm("  ---\n  duration_ms: 1.3874\n  ..."), "  ---\n  duration_ms: <T>\n  ...");
  assert.equal(norm("stale-2f548b84.html، stale-dir-866e5da4\\index.html"),
    "stale-<RAND>.html، stale-dir-<RAND>\\index.html");
  assert.equal(norm("stale-page-1a2b3c4d"), "stale-page-<RAND>");
  assert.equal(norm("a\r\nb"), "a\nb");
});

test("سطورُ الفشل تُختار مع تفصيلها، وسطورُ النجاح لا", () => {
  const out = "✅ [A-01] سليم\n❌ 2 عطب:\n   · [B-02] مكسور\n   · [C-03] ناقص\n╚══ ✅ (سقفًا) ══╝\nok 1 - x";
  assert.equal(failureText(out), "❌ 2 عطب:\n   · [B-02] مكسور\n   · [C-03] ناقص");
});

test("سطرُ نجاحٍ يحمل كلمةَ خطأ لا يُختار (PASS_LINE)", () => {
  const out = "✅ [X-01] لا TypeError في الوحدة\n# Subtest: يرفض RangeError\nok 2 - Error مُعالَج";
  assert.equal(failureText(out), "");
});

test("حرفُ القرص بأيّ حالة، والمرساة: ‏/tmp داخل مسارٍ آخر لا يُطبَّع", () => {
  assert.equal(norm(ROOT.replace(/^C:/, "c:") + "\\x"), "<ROOT>/x");
  const nl = makeNorm("/home/u/repo", "/tmp");
  assert.equal(nl("/tmp/abc/d.txt و /home/u/tmp/zz"), "<TMP>/d.txt و /home/u/tmp/zz");
  assert.equal(norm("at file:///" + ROOT.replace(/\\/g, "/") + "/t.js:3"), "at file:///<ROOT>/t.js:3");
});

// خرجُ TAP حقيقيّ من `assert.equal` (‏node 22): سطرٌ من مسافاتٍ يفصل الفرقَ عن القيمتين.
const tap = (actual) => [
  "TAP version 13", "# Subtest: x", "not ok 1 - x", "  ---", "  duration_ms: 1.4745",
  "  failureType: 'testCodeFailure'", "  error: |-", "    Expected values to be strictly equal:",
  "    + actual - expected", "    ", `    + '${actual}'`, "    - 'متوقَّع'", "    ",
  "  code: 'ERR_ASSERTION'", "  name: 'AssertionError'", `  actual: '${actual}'`, "  stack: |-",
  "    TestContext.<anonymous> (file:///x/t.test.mjs:2:38)", "    Test.run (node:internal/test_runner/test:1047:25)",
  "  ...", "1..1", "# fail 1"].join("\n");

test("TAP: القيمتان بعد السطر الفارغ تبقيان، والمكدّسُ يُسقَط", () => {
  const a = failureText(tap("رسالة أ")), b = failureText(tap("رسالة ب مختلفة"));
  assert.notEqual(a, b, "رسالتان مختلفتان أعطتا تفريغًا واحدًا: السطرُ الفارغ قطع التفصيل");
  assert.match(a, /\+ 'رسالة أ'/);
  assert.match(a, /actual: 'رسالة أ'/);
  assert.doesNotMatch(a, /node:internal|TestContext/, "المكدّسُ يتبع نسخةَ node");
});

test("dumpText: رمزُ الخروج، والذيلُ حين لا علامةَ فشل", () => {
  assert.equal(dumpText({ code: 0, out: "" }), "‹أخضر›");
  assert.equal(dumpText({ code: null, why: "ETIMEDOUT", out: "" }), "‹لم ينتهِ: ETIMEDOUT›");
  assert.equal(dumpText({ code: 2, out: "❌ x" }), "‹خرج 2›\n❌ x");
  const t = dumpText({ code: 1, out: "a\nb\n\nc\nd\n" });
  assert.equal(t, "‹خرج 1›\n‹بلا علامةِ فشل — الذيل:›\nb\nc\nd");
});
