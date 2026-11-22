"use strict";
const test = require("node:test");
const assert = require("node:assert");
const { activateDiffNotice, isArabicDiff, STATE_KEY, COPY } = require("./diff-notice.js");

/** ذاكرةُ حالةٍ مبسّطة (نظيرُ `context.globalState`). */
function memento(init = {}) {
  const store = { ...init };
  return {
    get: k => store[k],
    update: async (k, v) => { if (v === undefined) delete store[k]; else store[k] = v; },
    _store: store,
  };
}

/** عنوانٌ بشكل `vscode.Uri`: المقارنةُ بـ`toString()` كما في المحرّر. */
const uri = (p) => ({ path: p, toString: () => "file://" + p });
/** مستندٌ مفتوح بنصٍّ معلوم. */
const doc = (p, text) => ({ uri: uri(p), getText: () => text });

const ARABIC = 'اطبع("مرحبا يا عالم")';
const LATIN = '{ "name": "demo", "version": "1.0.0" }';

/** بديلُ `vscode` يسجّل ما عُرِض ويردّ اختيارًا مُعدًّا. */
function fakeVscode({ tabs = [], docs = [], pick } = {}) {
  const shown = [];
  const executed = [];
  return {
    shown,
    executed,
    workspace: { textDocuments: docs },
    window: {
      activeTextEditor: null,
      tabGroups: { all: [{ tabs }], onDidChangeTabs: () => ({ dispose() {} }) },
      showInformationMessage: async (msg, ...btns) => { shown.push({ msg, btns }); return pick; },
    },
    commands: { executeCommand: async (id, arg) => { executed.push([id, arg]); } },
  };
}

const arDocs = [doc("/م/قديم.txt", ARABIC), doc("/م/جديد.txt", ARABIC)];
const arDiff = { input: { original: uri("/م/قديم.txt"), modified: uri("/م/جديد.txt") } };
const jsonDocs = [doc("/م/a.json", LATIN), doc("/م/b.json", LATIN)];
const jsonDiff = { input: { original: uri("/م/a.json"), modified: uri("/م/b.json") } };
const plainTab = { input: { uri: uri("/م/قديم.txt") } };

test("[DR-04] فرقٌ فيه عربيّةٌ يُتعرَّف عليه، وغيرُه لا", () => {
  assert.ok(isArabicDiff(arDiff.input, arDocs));
  assert.ok(!isArabicDiff(jsonDiff.input, jsonDocs), "فرقٌ لاتينيٌّ كلُّه لا يُحسَب");
  assert.ok(!isArabicDiff(plainTab.input, arDocs), "تبويبٌ عاديٌّ ليس فرقًا وإن كان نصُّه عربيًّا");
  assert.ok(!isArabicDiff(null, arDocs));
});

test("[DR-04] لوحٌ واحدٌ فيه عربيّةٌ يكفي", () => {
  const docs = [doc("/م/قديم.txt", LATIN), doc("/م/جديد.txt", ARABIC)];
  assert.ok(isArabicDiff(arDiff.input, docs));
});

test("[DR-04] مستندٌ لم يُحمَّل بعدُ لا يُحسَب — والتبويبُ التالي يعيد السؤال", () => {
  assert.ok(!isArabicDiff(arDiff.input, []));
});

test("[DR-04] الرسالةُ تقع على أوّل فرقٍ عربيّ", async () => {
  const v = fakeVscode({ tabs: [arDiff], docs: arDocs });
  const n = activateDiffNotice(v, memento());
  await n.initial;
  assert.strictEqual(v.shown.length, 1);
  assert.ok(v.shown[0].msg.includes("لوحا المقارنة"));
  // الرسالةُ تسمّي الحدَّ منبعيًّا — كسابقةِ رسالة الطرفيّة.
  assert.ok(v.shown[0].msg.includes("المنبع"));
  assert.deepStrictEqual(v.shown[0].btns, [COPY.openNormally, COPY.dontRemind]);
});

test("[DR-04] لا رسالةَ على فرقٍ لاتينيّ — الفرصةُ واحدةٌ فلا تُحرَق في غير سياقها", async () => {
  const v = fakeVscode({ tabs: [jsonDiff], docs: jsonDocs });
  const m = memento();
  const n = activateDiffNotice(v, m);
  await n.initial;
  assert.strictEqual(v.shown.length, 0);
  assert.strictEqual(m.get(STATE_KEY), undefined, "لا يجوز أن يُحرَق الوسمُ بلا رسالة");
});

test("[DR-04] مرّةً واحدةً للأبد — والوسمُ يُكتَب قبل الانتظار", async () => {
  const v = fakeVscode({ tabs: [arDiff], docs: arDocs });
  const m = memento();
  const a = activateDiffNotice(v, m);
  await a.initial;
  const b = activateDiffNotice(v, m);
  await b.initial;
  assert.strictEqual(v.shown.length, 1);
  assert.strictEqual(m.get(STATE_KEY), true);
});

test("[DR-04] «افتح في محرّرٍ عاديّ» يفتح الملفَّ النشط", async () => {
  const v = fakeVscode({ tabs: [arDiff], docs: arDocs, pick: COPY.openNormally });
  v.window.activeTextEditor = { document: { uri: uri("/م/جديد.txt") } };
  const n = activateDiffNotice(v, memento());
  await n.initial;
  assert.deepStrictEqual(v.executed[0][0], "vscode.open");
});

test("[DR-04] الإخفاءُ قرارٌ لا بابٌ مغلَق — والإعادةُ تمسح الوسم", async () => {
  const v = fakeVscode({ tabs: [arDiff], docs: arDocs, pick: COPY.dontRemind });
  const m = memento();
  const n = activateDiffNotice(v, m);
  await n.initial;
  assert.ok(v.shown[1].msg.includes("لوحةُ الأوامر"), "الإخفاءُ يقول كيف يُعاد");
  await n.showAgain();
  assert.strictEqual(m.get(STATE_KEY), undefined);
});
