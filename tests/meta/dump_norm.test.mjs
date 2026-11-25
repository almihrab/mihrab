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
  assert.equal(norm("a\r\nb"), "a\nb");
});

test("سطورُ الفشل تُختار مع تفصيلها، وسطورُ النجاح لا", () => {
  const out = "✅ [A-01] سليم\n❌ 2 عطب:\n   · [B-02] مكسور\n   · [C-03] ناقص\n╚══ ✅ (سقفًا) ══╝\nok 1 - x";
  assert.equal(failureText(out), "❌ 2 عطب:\n   · [B-02] مكسور\n   · [C-03] ناقص");
});

test("dumpText: رمزُ الخروج، والذيلُ حين لا علامةَ فشل", () => {
  assert.equal(dumpText({ code: 0, out: "" }), "‹أخضر›");
  assert.equal(dumpText({ code: null, why: "ETIMEDOUT", out: "" }), "‹لم ينتهِ: ETIMEDOUT›");
  assert.equal(dumpText({ code: 2, out: "❌ x" }), "‹خرج 2›\n❌ x");
  const t = dumpText({ code: 1, out: "a\nb\n\nc\nd\n" });
  assert.equal(t, "‹خرج 1›\n‹بلا علامةِ فشل — الذيل:›\nb\nc\nd");
});
