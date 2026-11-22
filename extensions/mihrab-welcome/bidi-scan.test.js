"use strict";
/**
 * اختباراتُ كاشف قلب الاتّجاه [BS-01] — وحدةٌ نقيّة.
 *
 * ‏**الاختبارُ الأهمُّ هنا ليس «هل يمسك الهجوم؟» بل «هل يسكت عن الشرعيّ؟»** — لأنّ الحارسَ
 * الثرثارَ يُدرِّب المستخدمَ على تجاهُله، فيصير غطاءً للهجوم لا حاجزًا دونه. ولذلك تبدأ
 * الحالاتُ بالسكوت المطلوب قبل الكشف المطلوب.
 */
const test = require("node:test");
const assert = require("node:assert");
const S = require("./bidi-scan.js");

const C = S.CODE_POINTS;
const ch = (cp) => String.fromCharCode(cp);
const RLO = ch(C.RLO), LRO = ch(C.LRO), RLE = ch(C.RLE), LRE = ch(C.LRE), PDF = ch(C.PDF);
const RLI = ch(C.RLI), LRI = ch(C.LRI), FSI = ch(C.FSI), PDI = ch(C.PDI);
const RLM = ch(C.RLM), LRM = ch(C.LRM), ALM = ch(C.ALM);

// ───────────────────── السكوتُ المطلوب (لا إنذارَ كاذب) ─────────────────────

test("العلاماتُ المفردةُ شرعيّةٌ — لا تشخيصَ عليها أبدًا", () => {
  // ٣١٢ علامةً خفيّةً في نواة نهلة كانت كلُّها من هذا الصنف.
  for (const mark of [RLM, LRM, ALM]) {
    assert.deepStrictEqual(S.scanBidi('اطبع("مرحبا' + mark + ' world")', "python"), []);
  }
});

test("القوالبُ المتوازنةُ لا تُشخَّص", () => {
  assert.deepStrictEqual(S.scanBidi("x = " + FSI + "abc" + PDI, "python"), []);
  assert.deepStrictEqual(S.scanBidi(RLO + "abc" + PDF, "python"), []);
  assert.deepStrictEqual(S.scanBidi(RLE + "a" + LRI + "b" + PDI + "c" + PDF, "python"), []);
});

test("خاتمٌ زائدٌ بلا فاتحٍ لا يُشخَّص (لا يقلب شيئًا)", () => {
  assert.deepStrictEqual(S.scanBidi("x" + PDF + "y" + PDI, "python"), []);
});

test("نصٌّ عربيٌّ عاديٌّ بلا محارفِ تحكّمٍ لا يُمسَح أصلًا", () => {
  assert.deepStrictEqual(S.scanBidi("دالة رئيسية() { اطبع(\"مرحبا\") }", "python"), []);
  assert.deepStrictEqual(S.scanBidi("", "python"), []);
  assert.deepStrictEqual(S.scanBidi(null, "python"), []);
});

// ───────────────────── الكشفُ المطلوب ─────────────────────

test("تجاوزٌ بلا خاتمٍ قبل نهاية السطر ⇒ حرِج", () => {
  const hits = S.scanBidi("return 1; " + RLO + " tail", "javascript");
  assert.strictEqual(hits.length, 1);
  assert.strictEqual(hits[0].code, "RLO");
  assert.strictEqual(hits[0].severity, S.SEVERITY.CRITICAL);
  assert.strictEqual(hits[0].expected, "PDF");
});

test("تضمينٌ بلا خاتمٍ خارجَ نصٍّ ⇒ مشبوهٌ لا حرِج (تدرُّجُ الشدّة حقيقيّ)", () => {
  const hits = S.scanBidi("x = " + RLE + "y", "python");
  assert.strictEqual(hits.length, 1);
  assert.strictEqual(hits[0].code, "RLE");
  assert.strictEqual(hits[0].severity, S.SEVERITY.SUSPECT);
  assert.strictEqual(hits[0].inQuoted, false);
});

test("فاتحٌ داخل تعليقٍ يرتفع إلى الحرِج (مخبأُ الهجوم الأثير)", () => {
  const hits = S.scanBidi("# شرح " + RLI + " مخفيّ", "python");
  assert.strictEqual(hits.length, 1);
  assert.strictEqual(hits[0].severity, S.SEVERITY.CRITICAL);
  assert.strictEqual(hits[0].inQuoted, true);
  assert.strictEqual(hits[0].expected, "PDI");
});

test("فاتحٌ داخل سلسلةٍ نصّيّةٍ يرتفع إلى الحرِج", () => {
  const hits = S.scanBidi('اطبع("نصّ ' + LRE + ' مقلوب', "python");
  assert.strictEqual(hits.length, 1);
  assert.strictEqual(hits[0].severity, S.SEVERITY.CRITICAL);
  assert.ok(hits[0].inQuoted);
});

test("العزلُ لا يُغلَق بخاتم التضمين ولا العكس (نظامان مستقلّان — UAX #9)", () => {
  // `RLI` يحتاج `PDI`؛ وجودُ `PDF` لا يُغلِقه.
  const a = S.scanBidi(RLI + "x" + PDF, "python");
  assert.strictEqual(a.length, 1);
  assert.strictEqual(a[0].code, "RLI");
  // `RLE` يحتاج `PDF`؛ وجودُ `PDI` لا يُغلِقه.
  const b = S.scanBidi(RLE + "x" + PDI, "python");
  assert.strictEqual(b.length, 1);
  assert.strictEqual(b[0].code, "RLE");
});

test("النطاقُ سطرٌ سطر: فاتحٌ في سطرٍ لا يُغلَق بخاتمٍ في التالي", () => {
  const hits = S.scanBidi(RLO + "a\n" + PDF + "b", "python");
  assert.strictEqual(hits.length, 1);
  assert.strictEqual(hits[0].line, 0);
});

test("الموضعُ دقيقٌ سطرًا وعمودًا (وإلّا أشار التشخيصُ إلى محرفٍ بريء)", () => {
  const hits = S.scanBidi("سطر أوّل\nab" + LRO + "cd", "python");
  assert.strictEqual(hits.length, 1);
  assert.strictEqual(hits[0].line, 1);
  assert.strictEqual(hits[0].column, 2);
  assert.strictEqual(hits[0].endColumn, 3);
});

test("يتعامل مع نهايات الأسطر الثلاث (CRLF/LF/CR)", () => {
  for (const eol of ["\r\n", "\n", "\r"]) {
    const hits = S.scanBidi("أوّل" + eol + RLO + "ثانٍ", "python");
    assert.strictEqual(hits.length, 1, eol);
    assert.strictEqual(hits[0].line, 1, eol);
  }
});

// ───────────────────── الإزالة ─────────────────────

test("stripUnbalanced يزيل الفواتحَ غيرَ المتوازنة وحدَها", () => {
  const src = "# " + RLO + "هجوم\nسطر " + FSI + "x" + PDI + " سليم\n" + RLM + " علامة";
  const out = S.stripUnbalanced(src, "python");
  assert.deepStrictEqual(S.scanBidi(out, "python"), [], "لم يبقَ غيرُ متوازن");
  assert.ok(out.includes(FSI) && out.includes(PDI), "القالبُ المتوازنُ لم يُمَسّ");
  assert.ok(out.includes(RLM), "العلامةُ المفردةُ لم تُمَسّ");
  assert.ok(!out.includes(RLO));
});

test("stripUnbalanced يزيل عدّةَ فواتحَ في السطر نفسِه دون انزياحِ مواضع", () => {
  const src = "a" + RLO + "b" + LRE + "c";
  assert.strictEqual(S.stripUnbalanced(src, "python"), "abc");
});

test("stripUnbalanced يحافظ على نهايات الأسطر", () => {
  const src = "أ\r\n" + RLO + "ب\r\nج";
  assert.strictEqual(S.stripUnbalanced(src, "python"), "أ\r\nب\r\nج");
});

test("stripUnbalanced على نصٍّ سليمٍ يعيده كما هو (بلا نسخٍ ولا تغيير)", () => {
  const src = "دالة رئيسية()";
  assert.strictEqual(S.stripUnbalanced(src, "python"), src);
});

// ───────────────────── التسمية (BS-02) ─────────────────────

test("listBidiChars يُسمّي الشرعيَّ والمشبوهَ معًا ويميّزهما", () => {
  const all = S.listBidiChars("a" + RLM + "b" + RLO + "c" + PDF);
  assert.deepStrictEqual(all.map((x) => x.code), ["RLM", "RLO", "PDF"]);
  assert.deepStrictEqual(all.map((x) => x.isMark), [true, false, false]);
  assert.ok(all[0].nameAr, "لكلّ محرفٍ اسمٌ عربيٌّ يُعرَض");
});

test("inCommentOrString يفهم الهروبَ داخل السلسلة", () => {
  const syn = S.SYNTAX.python;
  assert.strictEqual(S.inCommentOrString('x = "a\\"b', 8, syn), true, "ما زلنا داخل السلسلة");
  assert.strictEqual(S.inCommentOrString('x = "ab" y', 9, syn), false, "أُغلِقت السلسلة");
});

// ─────────── العبورُ للحدّ: متوازنٌ حسابيًّا، يقلب شيفرةً حقيقيّة ───────────

test("قالبٌ يُفتَح في تعليقٍ ويُغلَق في شيفرة ⇒ تسرُّبٌ حرِج", () => {
  // صيغةُ Trojan Source الأصليّة: التوازنُ وحدَه لا يمسكها.
  const src = "/* " + RLO + " */ ;)(nwodtuhs" + PDF + " doSomething();";
  const hits = S.scanBidi(src, "javascript");
  assert.strictEqual(hits.length, 1);
  assert.strictEqual(hits[0].kind, S.KIND.LEAK);
  assert.strictEqual(hits[0].severity, S.SEVERITY.CRITICAL);
  assert.strictEqual(hits[0].region, S.REGION.COMMENT, "فُتِح في التعليق");
});

test("قالبٌ يُفتَح في سلسلةٍ ويُغلَق في شيفرة ⇒ تسرُّبٌ حرِج", () => {
  const hits = S.scanBidi('var s = "abc ' + RLO + ' def" + x + ' + PDF + ";", "javascript");
  assert.strictEqual(hits.length, 1);
  assert.strictEqual(hits[0].kind, S.KIND.LEAK);
  assert.strictEqual(hits[0].region, S.REGION.STRING);
});

test("قالبٌ متوازنٌ **داخل المنطقة نفسِها** لا يُشخَّص (لا ضجيج)", () => {
  assert.deepStrictEqual(S.scanBidi("/* " + RLO + " نصّ " + PDF + " */ x();", "javascript"), []);
  assert.deepStrictEqual(S.scanBidi('s = "' + FSI + "abc" + PDI + '";', "python"), []);
});

test("التسرُّبُ لا يُزال آليًّا (حذفُ طرفٍ يترك يتيمًا، وحذفُ الطرفين قرارُ إنسان)", () => {
  const src = "/* " + RLO + " */ x" + PDF + ";";
  assert.strictEqual(S.stripUnbalanced(src, "javascript"), src);
});

// ─────────── التعليقاتُ الكتليّة ───────────

test("تعليقٌ كتليٌّ على سطرٍ واحد يُفهَم منطقةً", () => {
  const hits = S.scanBidi("/* شرح " + RLI + " */ x();", "javascript");
  assert.strictEqual(hits.length, 1);
  assert.strictEqual(hits[0].inQuoted, true, "داخل تعليقٍ كتليّ");
  assert.strictEqual(hits[0].severity, S.SEVERITY.CRITICAL);
});

test("تعليقٌ كتليٌّ ممتدٌّ سطورًا تُحمَل حالتُه (وإلّا انقلبت مناطقُ ما بعده)", () => {
  const src = "/* أوّل\nثانٍ " + RLE + " ما زال داخل التعليق\n*/ code();";
  const hits = S.scanBidi(src, "javascript");
  assert.strictEqual(hits.length, 1);
  assert.strictEqual(hits[0].line, 1);
  assert.strictEqual(hits[0].inQuoted, true, "الحالةُ عبرت السطر");
});

test("لغةٌ بلا تعليقٍ كتليٍّ لا تتأثّر بـ/* في نصّها", () => {
  const hits = S.scanBidi("x = 1 /* ليس تعليقًا في بايثون */ " + RLE + "y", "python");
  assert.strictEqual(hits.length, 1);
  assert.strictEqual(hits[0].inQuoted, false);
});

// ─────────── حالاتٌ حديّة ───────────

test("فواتحُ متداخلةٌ متعدّدةٌ: كلٌّ يُبلَّغ بموضعه الصحيح", () => {
  const hits = S.scanBidi(RLE + "a" + RLO + "b" + PDF + "c", "python");
  assert.strictEqual(hits.length, 1, "الأحدثُ (RLO) أُغلِق بـPDF، وبقي RLE");
  assert.strictEqual(hits[0].code, "RLE");
  assert.strictEqual(hits[0].column, 0);
});

test("فاتحٌ في آخرِ محرفٍ من الملفّ بلا فاصلِ سطرٍ نهائيّ", () => {
  const src = "x = 1" + RLO;
  const hits = S.scanBidi(src, "python");
  assert.strictEqual(hits.length, 1);
  assert.strictEqual(hits[0].column, 5);
  assert.strictEqual(S.stripUnbalanced(src, "python"), "x = 1");
});

test("المكتشَفاتُ مرتَّبةٌ بالموضع (ترتيبُ لوحة المشاكل = ترتيبُ الأسطر)", () => {
  const src = "a" + RLO + "b\n/* " + RLI + " */ " + PDI + " c\nd" + LRE + "e";
  const hits = S.scanBidi(src, "javascript");
  const order = hits.map((h) => h.line);
  assert.deepStrictEqual(order, [...order].sort((a, b) => a - b), JSON.stringify(order));
});

test("لغةٌ غيرُ معروفةٍ تسقط إلى نحو بايثون بلا رمي", () => {
  const hits = S.scanBidi("# " + RLO + "x", "لغة-لا-وجود-لها");
  assert.strictEqual(hits.length, 1);
  assert.strictEqual(hits[0].inQuoted, true, "‏`#` تعليقٌ في النحو الافتراضيّ");
});
