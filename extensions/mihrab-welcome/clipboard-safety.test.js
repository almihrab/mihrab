"use strict";
/** اختبارات أمانة الحافظة [BS-04] — الخارجُ والداخل. */

const test = require("node:test");
const assert = require("node:assert");

const cb = require("./clipboard-safety.js");

const FSI = cb.ISO_OPEN;   // U+2068 — عزلٌ يتبع أوّلَ حرفٍ قويّ
const PDI = cb.ISO_CLOSE;
const RLO = "‮";
const PDF = "‬";

// ── الخارج: `isolateForSharing` ──────────────────────────────────────────────

test("يلفّ كلّ سطرٍ بعزلٍ اتّجاهيّ مستقلّ", () => {
  const r = cb.isolateForSharing("اطبع(\"مرحبا\")\nإذا س > ٣:");
  assert.strictEqual(r.lines, 2);
  for (const line of r.text.split("\n")) {
    assert.ok(line.startsWith(FSI) && line.endsWith(PDI), line);
  }
});

test("السطرُ الفارغُ يُترَك بلا عزل — زوجٌ حول لا شيءٍ حشوٌ بلا أثر", () => {
  const r = cb.isolateForSharing("أ\n\n  \nب");
  const lines = r.text.split("\n");
  assert.strictEqual(r.lines, 2);
  assert.strictEqual(lines[1], "");
  assert.strictEqual(lines[2], "  ");
});

test("لا يُضاعِف العزلَ على نصٍّ ملفوفٍ سلفًا", () => {
  const once = cb.isolateForSharing("اطبع(س)");
  const twice = cb.isolateForSharing(once.text);
  assert.strictEqual(twice.text, once.text);
  assert.strictEqual(twice.lines, 0);
});

test("محرفُ CR يبقى خارجَ العزل — وإلّا وقع محرفٌ بعد نهاية السطر في CRLF", () => {
  const r = cb.isolateForSharing("اطبع(س)\r\nب\r\n");
  const lines = r.text.split("\n");
  assert.ok(lines[0].endsWith(PDI + "\r"), JSON.stringify(lines[0]));
  assert.ok(!lines[0].includes("\r" + PDI));
});

test("النصُّ الفارغُ لا يرمي ولا يلفّ", () => {
  assert.deepStrictEqual(cb.isolateForSharing(""), { text: "", lines: 0 });
  assert.deepStrictEqual(cb.isolateForSharing(null), { text: "", lines: 0 });
});

test("المحتوى محفوظٌ حرفيًّا — العزلُ إضافةٌ لا تحويل", () => {
  const src = "اطبع(\"مرحبا يا عالم\") // تعليقٌ فيه ; و( و)";
  const r = cb.isolateForSharing(src);
  assert.strictEqual(r.text.slice(FSI.length, -PDI.length), src);
});

// ── الخارج: أمرُ النسخ ───────────────────────────────────────────────────────

/** محاكٍ صغيرٌ لواجهة `vscode` — القدرُ الذي يستعمله الأمرُ لا أكثر. */
function fakeVscode(opts) {
  const o = opts || {};
  const msgs = { info: [], warn: [], error: [] };
  let written = null;
  return {
    msgs,
    written: () => written,
    window: {
      activeTextEditor: o.editor === undefined ? null : o.editor,
      showInformationMessage: (m) => {
        msgs.info.push(m);
        return Promise.resolve(undefined);
      },
      showWarningMessage: (m) => {
        msgs.warn.push(m);
        return Promise.resolve(undefined);
      },
      showErrorMessage: (m) => {
        msgs.error.push(m);
        return Promise.resolve(undefined);
      },
    },
    env: {
      clipboard: {
        writeText: (t) => {
          if (o.clipboardFails) return Promise.reject(new Error("الحافظة مشغولة"));
          written = t;
          return Promise.resolve();
        },
      },
    },
  };
}

/** تحديدٌ مبسَّط: `start` رقمٌ يقارَن، والنصُّ ثابت. */
function sel(order, text) {
  return {
    isEmpty: !text,
    start: { _o: order, compareTo: (b) => order - b._o },
    _text: text,
  };
}

function editorWith(sels) {
  return {
    selections: sels,
    document: { getText: (s) => s._text },
  };
}

test("ينسخ التحديداتِ بترتيب المستند لا بترتيب الإنشاء", async () => {
  const v = fakeVscode({ editor: editorWith([sel(2, "ثانٍ"), sel(1, "أوّل")]) });
  const n = await cb.copyForSharing(v);
  assert.strictEqual(n, 2);
  assert.strictEqual(v.written(), FSI + "أوّل" + PDI + "\n" + FSI + "ثانٍ" + PDI);
});

test("بلا محرّرٍ نشط: تحذيرٌ ولا نسخ", async () => {
  const v = fakeVscode({ editor: null });
  assert.strictEqual(await cb.copyForSharing(v), 0);
  assert.strictEqual(v.written(), null);
  assert.deepStrictEqual(v.msgs.warn, [cb.COPY.noEditor]);
});

test("بلا تحديد: يقول ما ينقص ولا يدّعي نسخًا", async () => {
  const v = fakeVscode({ editor: editorWith([sel(1, "")]) });
  assert.strictEqual(await cb.copyForSharing(v), 0);
  assert.deepStrictEqual(v.msgs.warn, [cb.COPY.noSelection]);
  assert.strictEqual(v.msgs.info.length, 0);
});

test("فشلُ الحافظة يُبلَّغ خطأً — لا رسالةَ نجاحٍ بلا أثر", async () => {
  const v = fakeVscode({ editor: editorWith([sel(1, "س")]), clipboardFails: true });
  assert.strictEqual(await cb.copyForSharing(v), 0);
  assert.strictEqual(v.msgs.info.length, 0);
  assert.strictEqual(v.msgs.error.length, 1);
});

// ── الداخل: بلاغُ اللصق ──────────────────────────────────────────────────────

function pasteHarness(opts) {
  const o = opts || {};
  const settings = new Map();
  if (o.disabled) settings.set(cb.CONFIG_KEY, false);
  const shown = [];
  const executed = [];
  const doc = { languageId: "plaintext", uri: { toString: () => o.uri || "file:///a.txt" } };
  const vscode = {
    window: {
      activeTextEditor: { document: doc },
      showWarningMessage: (m, ...btns) => {
        shown.push(m);
        return Promise.resolve(o.pick ? o.pick(btns) : undefined);
      },
    },
    workspace: {
      onDidChangeTextDocument: () => ({ dispose() {} }),
      getConfiguration: () => ({
        get: (k) => settings.get(k),
        update: (k, v) => {
          settings.set(k, v);
          return Promise.resolve();
        },
      }),
    },
    commands: {
      executeCommand: (c) => {
        executed.push(c);
        return Promise.resolve();
      },
    },
  };
  const context = { subscriptions: [] };
  const h = cb.activatePasteNotice(vscode, context, {
    removeCommand: "mihrab.fix",
    showProblemsCommand: "mihrab.problems",
  });
  return { h, doc, shown, executed, settings, vscode };
}

const change = (doc, text, reason) => ({ document: doc, reason, contentChanges: [{ text }] });

test("يبلّغ عن قالبٍ غيرِ متوازنٍ في لصقةٍ كبيرة", async () => {
  const t = pasteHarness();
  await t.h._onChange(change(t.doc, "اطبع(\"ما شاء الله\") # " + RLO + " تعليقٌ طويلٌ كافٍ"));
  assert.strictEqual(t.shown.length, 1);
});

test("لا يبلّغ عن قالبٍ متوازن — العلامةُ المشروعةُ ليست هجومًا", async () => {
  const t = pasteHarness();
  await t.h._onChange(change(t.doc, "اطبع(\"نصٌّ\") # " + RLO + "متوازنٌ هنا" + PDF + " وبقيّةُ سطرٍ طويل"));
  assert.strictEqual(t.shown.length, 0);
});

test("لا يبلّغ عن إدراجٍ قصير — الكتابةُ باليد ليست لصقًا", async () => {
  const t = pasteHarness();
  await t.h._onChange(change(t.doc, RLO + "قصير"));
  assert.strictEqual(t.shown.length, 0);
});

test("لا يبلّغ عن تراجعٍ أو إعادة — لم يجلبه المستخدمُ الآن", async () => {
  const t = pasteHarness();
  await t.h._onChange(change(t.doc, "اطبع(\"نصّ\") # " + RLO + " تعليقٌ طويلٌ كافٍ", 1));
  assert.strictEqual(t.shown.length, 0);
});

test("مرّةً واحدةً لكلّ مستندٍ في الجلسة", async () => {
  const t = pasteHarness();
  const c = change(t.doc, "اطبع(\"نصّ\") # " + RLO + " تعليقٌ طويلٌ كافٍ");
  await t.h._onChange(c);
  await t.h._onChange(c);
  assert.strictEqual(t.shown.length, 1);
});

test("مستندٌ آخرُ يُبلَّغ عنه — لصقةُ الصباح لا تحرق بلاغَ المساء", async () => {
  const t = pasteHarness();
  const body = "اطبع(\"نصّ\") # " + RLO + " تعليقٌ طويلٌ كافٍ";
  await t.h._onChange(change(t.doc, body));
  const other = { languageId: "plaintext", uri: { toString: () => "file:///b.txt" } };
  t.vscode.window.activeTextEditor = { document: other };
  await t.h._onChange({ document: other, reason: undefined, contentChanges: [{ text: body }] });
  assert.strictEqual(t.shown.length, 2);
});

test("بعد إصلاحٍ ناجحٍ يُعاد التسليح — الملفُّ عاد نظيفًا فالخطرُ التالي جديد", async () => {
  const t = pasteHarness({ pick: (b) => b[0] });
  const c = change(t.doc, "اطبع(\"نصّ\") # " + RLO + " تعليقٌ طويلٌ كافٍ");
  await t.h._onChange(c);
  await t.h._onChange(c);
  assert.strictEqual(t.shown.length, 2);
});

test("لصقٌ متعدّدُ المؤشّرات يُفحَص مجموعًا لا مُهمَلًا", async () => {
  const t = pasteHarness();
  await t.h._onChange({
    document: t.doc,
    reason: undefined,
    contentChanges: [{ text: "اطبع(\"أ\") # " + RLO }, { text: " تعليقٌ ثانٍ طويلٌ كافٍ" }],
  });
  assert.strictEqual(t.shown.length, 1);
});

test("«أصلِحه الآن» يستدعي أمرَ الإصلاح المُمرَّر — لا معرّفًا مكتوبًا هنا", async () => {
  const t = pasteHarness({ pick: (b) => b[0] });
  await t.h._onChange(change(t.doc, "اطبع(\"نصّ\") # " + RLO + " تعليقٌ طويلٌ كافٍ"));
  assert.deepStrictEqual(t.executed, ["mihrab.fix"]);
});

test("«أوقِف التنبيه» يكتب **الإعداد** لا حالةً خفيّة — فله بابُ عودة", async () => {
  const t = pasteHarness({ pick: (b) => b[b.length - 1] });
  await t.h._onChange(change(t.doc, "اطبع(" + '"نصّ"' + ") # " + RLO + " تعليقٌ طويلٌ كافٍ"));
  assert.strictEqual(t.settings.get(cb.CONFIG_KEY), false);
});

test("الإعدادُ مُطفأٌ ⇒ لا بلاغ", async () => {
  const t = pasteHarness({ disabled: true });
  await t.h._onChange(change(t.doc, "اطبع(" + '"نصّ"' + ") # " + RLO + " تعليقٌ طويلٌ كافٍ"));
  assert.strictEqual(t.shown.length, 0);
});

test("«أرِني الموضع» يفتح لوحةَ المشاكل بأمرٍ مُمرَّر", async () => {
  const t = pasteHarness({ pick: (b) => b[1] });
  await t.h._onChange(change(t.doc, "اطبع(" + '"نصّ"' + ") # " + RLO + " تعليقٌ طويلٌ كافٍ"));
  assert.deepStrictEqual(t.executed, ["mihrab.problems"]);
});

test("رسالةُ اللصق لا تُعيد حقنَ النصّ الملصوق — ولا تعرض المحرفَ الخفيّ", async () => {
  const t = pasteHarness();
  await t.h._onChange(change(t.doc, "اطبع(\"نصّ\") # " + RLO + " تعليقٌ طويلٌ كافٍ"));
  assert.ok(!t.shown[0].includes(RLO), "الرسالةُ تحمل محرفَ القلب نفسَه");
});

// ── بابُ العودة: نزعُ العزل ──────────────────────────────────────────────────

test("نزعُ العزل معكوسُ اللفّ تمامًا — ذهابٌ وإياب", () => {
  const src = "اطبع(\"مرحبا\")\n\nإذا س > ٣:\r\n";
  const w = cb.isolateForSharing(src);
  assert.strictEqual(cb.stripSharingIsolates(w.text).text, src);
});

test("سطرٌ فيه عزلان متجاوران يُلَفّ — الطرفان لا يعنيان التفافًا", () => {
  const line = FSI + "أ" + PDI + " = " + FSI + "ب" + PDI;
  assert.strictEqual(cb.isWrapped(line), false);
  assert.strictEqual(cb.isolateForSharing(line).lines, 1);
});

test("نزعُ العزل لا يمسّ عزلًا جزئيًّا داخل السطر", () => {
  const line = "س = " + FSI + "١" + PDI + " # شرح";
  assert.strictEqual(cb.stripSharingIsolates(line).lines, 0);
});

test("تمييزُ العدد العربيّ مصروفٌ في كلّ الحالات", () => {
  assert.strictEqual(cb.arCount(1, "واحد", "اثنان", "قلّة", "كثرة"), "واحد");
  assert.strictEqual(cb.arCount(2, "واحد", "اثنان", "قلّة", "كثرة"), "اثنان");
  assert.strictEqual(cb.arCount(3, "واحد", "اثنان", "قلّة", "كثرة"), "3 قلّة");
  assert.strictEqual(cb.arCount(11, "واحد", "اثنان", "قلّة", "كثرة"), "11 كثرة");
  assert.ok(!cb.COPY.copied(1).includes("1 سطرًا"));
});

test("رسالةُ النجاح لا تَعِد عن طرفٍ ثالثٍ وعدًا مطلقًا", () => {
  const m = cb.COPY.copied(3);
  assert.ok(m.includes("الوجهات التي تحترم"), m);
});

test("رسالةُ فشلِ النسخ تعزل التفصيلَ اللاتينيّ", () => {
  const m = cb.COPY.copyFailed("DOMException: not focused");
  assert.ok(m.includes("\u2066DOMException: not focused\u2069"), m);
});

// ── الحلقةُ المغلقة: ما نُسِخ من محرابٍ لا يُتَّهم في محراب ────────────────────

test("النصُّ المنسوخُ للنشر لا يُشخَّص حين يعود إلى محراب", () => {
  const scan = require("./bidi-scan.js");
  const src = "س = ١  # شرحٌ عربيّ\nاطبع(س)  # تعليقٌ آخر";
  const shared = cb.isolateForSharing(src).text;
  assert.deepStrictEqual(scan.scanBidi(shared, "python"), []);
});

test("والاستثناءُ ضيّقٌ: عزلٌ جزئيٌّ عابرٌ للحدّ ما يزال يُشخَّص", () => {
  const scan = require("./bidi-scan.js");
  const line = "س = " + FSI + "١  # نصّ" + PDI + " وبقيّة";
  assert.deepStrictEqual(scan.scanBidi(line, "python").map((f) => f.kind), ["leak"]);
});

test("و`RLO` غيرُ المغلَق ما يزال يُشخَّص", () => {
  const scan = require("./bidi-scan.js");
  assert.deepStrictEqual(
    scan.scanBidi("س = ١ # " + RLO + "مقلوب", "python").map((f) => f.kind), ["unbalanced"]);
});
