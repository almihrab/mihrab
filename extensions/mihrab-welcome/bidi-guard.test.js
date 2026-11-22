"use strict";
/** اختباراتُ وصل كاشف الاتّجاه بالمحرّر [BS-01] — ببديلِ vscode متحكَّمٍ فيه. */
const test = require("node:test");
const assert = require("node:assert");
const G = require("./bidi-guard.js");
const S = require("./bidi-scan.js");

const ch = (cp) => String.fromCharCode(cp);
const RLO = ch(S.CODE_POINTS.RLO);
const RLM = ch(S.CODE_POINTS.RLM);

// ── بديلٌ صغيرٌ يُنمذِج ما نستعمله فعلًا (مدياتٍ وتشخيصاتٍ وتحريرًا) ──
/** يُنمذِج `vscode.Range` بما نستعمله: الحقولُ المختصرةُ للتوكيد، و`start`/`end` كالمنبع. */
class Range {
  constructor(sl, sc, el, ec) {
    Object.assign(this, { sl, sc, el, ec });
    this.start = { line: sl, character: sc };
    this.end = { line: el, character: ec };
  }
}
class Diagnostic {
  constructor(range, message, severity) { Object.assign(this, { range, message, severity }); }
}
function fakeVscode(opts = {}) {
  const state = { set: [], deleted: [], info: [], warn: [], edits: [] };
  const listeners = {};
  const on = (name) => (cb) => { listeners[name] = cb; return { dispose() { delete listeners[name]; } }; };
  const vscode = {
    Range,
    Diagnostic,
    DiagnosticSeverity: { Error: 0, Warning: 1 },
    CodeActionKind: { QuickFix: "quickfix" },
    CodeAction: class { constructor(title, kind) { Object.assign(this, { title, kind }); } },
    WorkspaceEdit: class {
      constructor() { this.replacements = []; }
      replace(uri, range, text) { this.replacements.push({ uri, range, text }); }
    },
    languages: {
      createDiagnosticCollection: () => ({
        set: (uri, diags) => state.set.push([uri.toString(), diags]),
        delete: (uri) => state.deleted.push(uri.toString()),
        dispose() {},
      }),
    },
    workspace: {
      textDocuments: opts.docs || [],
      onDidOpenTextDocument: on("open"),
      onDidChangeTextDocument: on("change"),
      onDidCloseTextDocument: on("close"),
      openTextDocument: async (uri) => (opts.docs || []).find((d) => d.uri.toString() === uri.toString()),
      applyEdit: async (edit) => {
        state.edits.push(edit);
        // `applyEdit` **لا ترمي عند الرفض** بل تعيد `false` (ملفٌّ للقراءة، تعارضُ إصدار).
        // فبديلٌ يعيد `true` دائمًا يُخفي أخطرَ فرعٍ في الأمر: رسالةَ نجاحٍ بلا أثر.
        if (opts.applyResult === false) return false;
        if (opts.applyFor) opts.applyFor(edit);
        return true;
      },
    },
    window: {
      activeTextEditor: opts.activeEditor,
      showInformationMessage: (m) => { state.info.push(m); },
      showWarningMessage: (m) => { state.warn.push(m); },
    },
  };
  return { vscode, state, listeners };
}

/** مستندٌ زائفٌ يحاكي `TextDocument` بما نستعمله (نصٌّ متغيّرٌ كي يُقاس أثرُ التحرير فعلًا). */
function fakeDoc(text, { scheme = "file", languageId = "plaintext", path = "/a.txt" } = {}) {
  const doc = {
    languageId,
    uri: { scheme, path, toString: () => scheme + "://" + path },
    getText: () => doc._text,
    positionAt: (o) => ({ offset: o }),
    _text: text,
  };
  return doc;
}

test("يشخّص القالبَ غيرَ المتوازن ويسكت عن العلامة المفردة", () => {
  const { vscode } = fakeVscode();
  const bad = G.diagnosticsFor(vscode, fakeDoc("# " + RLO + "هجوم"));
  assert.strictEqual(bad.length, 1);
  assert.strictEqual(bad[0].severity, vscode.DiagnosticSeverity.Error, "داخل تعليق ⇒ خطأ");
  assert.strictEqual(bad[0].code, G.CODE);
  assert.strictEqual(bad[0].source, G.SOURCE);
  assert.deepStrictEqual(G.diagnosticsFor(vscode, fakeDoc("x" + RLM + "y")), []);
});

test("الرسالةُ تصف الأثرَ قبل الاسم التقنيّ (قرارُ صياغةٍ لا تفصيل)", () => {
  const { vscode } = fakeVscode();
  const [d] = G.diagnosticsFor(vscode, fakeDoc("x = " + RLO + "y"));
  const effectAt = d.message.indexOf("بترتيبٍ غيرِ الترتيب الذي يُنفَّذ به");
  const codeAt = d.message.indexOf("RLO");
  assert.ok(effectAt >= 0 && codeAt >= 0 && effectAt < codeAt, d.message);
});

test("الرموزُ اللاتينيّةُ في الرسالة معزولةٌ بـFSI…PDI (تصل إلى aria-label ولوحة المشاكل)", () => {
  const { vscode } = fakeVscode();
  const [d] = G.diagnosticsFor(vscode, fakeDoc("x = " + RLO + "y"));
  // العزلُ في **النصّ** لا في الورقة: CSS لا تبلغ قارئَ الشاشة ولا النسخَ واللصق.
  assert.ok(d.message.includes(G.iso("RLO")), "رمزُ المحرف معزول");
  assert.ok(d.message.includes(G.iso("PDF")), "رمزُ الخاتم معزول");
});

test("ملفٌّ أكبرُ من الحدّ يُبلَّغ عنه ولا يُبتلَع صمتًا", () => {
  const { vscode } = fakeVscode();
  const huge = fakeDoc("x".repeat(G.MAX_SCAN_CHARS + 1) + RLO);
  const out = G.diagnosticsFor(vscode, huge);
  // الغيابُ هنا أخطرُ من الضجيج: بلا بلاغٍ يبدو الملفُّ سليمًا والصوابُ أنّه لم يُفحَص.
  assert.strictEqual(out.length, 1);
  assert.strictEqual(out[0].code, G.CODE_TOO_LARGE);
  assert.strictEqual(out[0].severity, vscode.DiagnosticSeverity.Information);
});

test("تشخيصُ «لم يُفحَص» بلا مصباحِ إصلاح (مصباحٌ بلا إصلاحٍ وعدٌ مكسور)", () => {
  const { vscode } = fakeVscode();
  const p = new G.BidiCodeActionProvider(vscode);
  assert.deepStrictEqual(
    p.provideCodeActions(fakeDoc("x"), null, { diagnostics: [{ code: G.CODE_TOO_LARGE }] }),
    []
  );
});

test("المدى يغطّي المنطقةَ المتضرّرة لا المحرفَ الصفريَّ العرض", () => {
  const { vscode } = fakeVscode();
  const line = "x = " + RLO + "yyyy";
  const doc = fakeDoc(line);
  doc.lineAt = (n) => ({ range: { end: { character: line.length } } });
  const [d] = G.diagnosticsFor(vscode, doc);
  assert.strictEqual(d.range.sc, 4, "يبدأ عند الفاتح");
  assert.strictEqual(d.range.ec, line.length, "ينتهي بنهاية السطر — خطٌّ يراه المستخدم");
});

test("shouldScan يقبل الملفّاتِ وغيرَ المحفوظة ويرفض ما عداها", () => {
  assert.ok(G.shouldScan(fakeDoc("x", { scheme: "file" })));
  assert.ok(G.shouldScan(fakeDoc("x", { scheme: "untitled" })));
  assert.ok(!G.shouldScan(fakeDoc("x", { scheme: "output" })));
  assert.ok(!G.shouldScan(fakeDoc("x", { scheme: "git" })));
  assert.ok(!G.shouldScan(null));
});

test("الحارسُ يمسح المفتوحَ سلفًا عند الإنشاء (لا ينتظر أوّلَ تغيير)", () => {
  const doc = fakeDoc("# " + RLO + "x");
  const { vscode, state } = fakeVscode({ docs: [doc] });
  const guard = new G.BidiGuard(vscode, { subscriptions: [] }, 0);
  assert.strictEqual(state.set.length, 1);
  assert.strictEqual(state.set[0][1].length, 1);
  guard.dispose();
});

test("إغلاقُ المستند يمسح تشخيصاته ويلغي مؤقّتَه", () => {
  const doc = fakeDoc("سليم");
  const { vscode, state, listeners } = fakeVscode({ docs: [doc] });
  const guard = new G.BidiGuard(vscode, { subscriptions: [] }, 50);
  listeners.change({ document: doc });
  assert.strictEqual(guard.timers.size, 1, "جُدوِل مسحٌ مؤجّل");
  listeners.close(doc);
  assert.deepStrictEqual(state.deleted, [doc.uri.toString()]);
  assert.strictEqual(guard.timers.size, 0, "أُلغي المؤقّتُ فلا تسريب");
  guard.dispose();
});

test("مزوّدُ الإجراءات يعرض إصلاحَين: الموضعُ أوّلًا (مفضَّلًا) ثمّ الملفُّ كلُّه", () => {
  const { vscode } = fakeVscode();
  const p = new G.BidiCodeActionProvider(vscode);
  const doc = fakeDoc("x");
  assert.deepStrictEqual(p.provideCodeActions(doc, null, { diagnostics: [] }), []);
  assert.deepStrictEqual(
    p.provideCodeActions(doc, null, { diagnostics: [{ code: "غيرنا" }] }), [],
    "لا نتطفّل على تشخيصات غيرنا"
  );
  const range = new Range(2, 5, 2, 9);
  const acts = p.provideCodeActions(doc, null, { diagnostics: [{ code: G.CODE, range }] });
  assert.strictEqual(acts.length, 2);
  // **المفضَّلُ أضيقُهما**: نقرةٌ على السطر ٣ يجب ألّا تغيّر السطرَ ٩٠ الذي لم يفتحه أحد.
  assert.ok(acts[0].isPreferred);
  assert.deepStrictEqual(acts[0].command.arguments, [doc.uri, range]);
  assert.strictEqual(acts[1].command.arguments.length, 1, "الكلّيُّ بلا مدًى");
  assert.ok(!acts[1].isPreferred);
});

test("أمرُ الإزالة يحرّر المستندَ ويقول ما أُزيل — بعد إعادة القراءة", async () => {
  const doc = fakeDoc("# " + RLO + "هجوم\n" + RLM + " علامة");
  const { vscode, state } = fakeVscode({
    activeEditor: { document: doc },
    // البديلُ يُنمذِج **الأثرَ الفعليّ**: يطبّق النصَّ الجديد كما يفعل المحرّر. بدون ذلك
    // يمرّ «نجاحٌ كاذب» — وهو الدرسُ المدفوعُ ثمنُه في `unicode-guard`.
    applyFor: (edit) => { doc._text = edit.replacements[0].text; },
  });
  const removed = await G.removeCommand(vscode);
  assert.strictEqual(removed, 1);
  assert.ok(!doc._text.includes(RLO), "أُزيل غيرُ المتوازن");
  assert.ok(doc._text.includes(RLM), "بقيت العلامةُ الشرعيّة");
  assert.strictEqual(state.info.length, 1);
});

test("‏applyEdit مرفوضةٌ ⇒ **تحذيرٌ لا رسالةُ نجاحٍ بصفر أثر**", async () => {
  const doc = fakeDoc("# " + RLO + "هجوم");
  const { vscode, state } = fakeVscode({
    activeEditor: { document: doc },
    applyResult: false, // ملفٌّ للقراءة فقط، أو تعارضُ إصدار — لا ترمي وترجع false.
  });
  assert.strictEqual(await G.removeCommand(vscode), 0);
  assert.strictEqual(state.info.length, 0, "لا رسالةَ نجاحٍ إطلاقًا");
  assert.strictEqual(state.warn[0], G.COPY.removeFailed);
});

test("إصلاحُ موضعٍ واحد يحرّر محرفًا واحدًا لا الملفَّ كلَّه", async () => {
  const src = "a" + RLO + "b\nc" + RLO + "d";
  const doc = fakeDoc(src);
  const { vscode, state } = fakeVscode({
    docs: [doc], // الأمرُ يأتي من المصباح بـURI ⇒ يمرّ بـopenTextDocument لا بالمحرّر النشط.
    activeEditor: { document: doc },
    applyFor: (edit) => {
      const r = edit.replacements[0];
      const lines = doc._text.split("\n");
      lines[r.range.sl] = lines[r.range.sl].slice(0, r.range.sc) + lines[r.range.sl].slice(r.range.ec);
      doc._text = lines.join("\n");
    },
  });
  const removed = await G.removeCommand(vscode, doc.uri, new Range(0, 1, 0, 2));
  assert.strictEqual(removed, 1);
  assert.strictEqual(doc._text, "ab\nc" + RLO + "d", "السطرُ الثاني لم يُمَسّ");
  // بقي واحدٌ ⇒ رسالةٌ جزئيّةٌ صادقةٌ لا «تمّ».
  assert.ok(state.warn[0].includes("بقي"), state.warn[0]);
});

test("المؤقّتُ ينطلق فعلًا بعد التهدئة (الجدولةُ وحدَها ليست تنفيذًا)", async () => {
  const doc = fakeDoc("سليم");
  const { vscode, state, listeners } = fakeVscode({ docs: [doc] });
  const guard = new G.BidiGuard(vscode, { subscriptions: [] }, 1);
  const before = state.set.length;
  doc._text = "# " + RLO + "x";
  listeners.change({ document: doc });
  await new Promise((r) => setTimeout(r, 20));
  assert.strictEqual(state.set.length, before + 1, "أُعيد المسحُ فعلًا");
  assert.strictEqual(state.set[state.set.length - 1][1].length, 1);
  guard.dispose();
});

test("‏dispose يمنع مسحًا مجدوَلًا من الوقوع بعد الإغلاق", async () => {
  const doc = fakeDoc("سليم");
  const { vscode, state, listeners } = fakeVscode({ docs: [doc] });
  const guard = new G.BidiGuard(vscode, { subscriptions: [] }, 5);
  const before = state.set.length;
  listeners.change({ document: doc });
  guard.dispose();
  await new Promise((r) => setTimeout(r, 25));
  assert.strictEqual(state.set.length, before, "لا كتابةَ بعد الإغلاق");
});

test("مستندٌ يرمي من getText لا يُسقِط الحارس", () => {
  const { vscode } = fakeVscode();
  const guard = new G.BidiGuard(vscode, { subscriptions: [] }, 0);
  const bad = fakeDoc("x");
  bad.getText = () => { throw new Error("انهار"); };
  assert.doesNotThrow(() => guard.refresh(bad));
  guard.dispose();
});

test("أمرُ الإزالة على ملفٍّ سليمٍ لا يحرّر ويقول ذلك", async () => {
  const doc = fakeDoc("دالة رئيسية()");
  const { vscode, state } = fakeVscode({ activeEditor: { document: doc } });
  assert.strictEqual(await G.removeCommand(vscode), 0);
  assert.strictEqual(state.edits.length, 0, "لا تحريرَ بلا سبب");
  assert.strictEqual(state.info[0], G.COPY.nothing);
});

test("أمرُ الإزالة بلا محرّرٍ نشطٍ يقول ذلك ولا يرمي", async () => {
  const { vscode, state } = fakeVscode();
  assert.strictEqual(await G.removeCommand(vscode), 0);
  assert.strictEqual(state.warn[0], G.COPY.noEditor);
});
