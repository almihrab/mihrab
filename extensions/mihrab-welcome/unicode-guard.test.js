"use strict";
/** اختباراتُ حارس إبراز يونيكود [AR-04] — ببديلِ vscode متحكَّمٍ فيه (لا محرّرَ حيًّا). */
const test = require("node:test");
const assert = require("node:assert");
const G = require("./unicode-guard.js");

const T = { Global: 1, Workspace: 2, WorkspaceFolder: 3 };

/**
 * values: خريطةُ `"<langId|''>|<key>|<prop>" ⇒ قيمة`. البديلُ يعيد `undefined` لما لم
 * يُذكَر — كي ينكشف أيُّ اعتمادٍ على وجود الخاصّيّة.
 */
function fakeVscode(values, opts = {}) {
  const updates = [];
  const shown = { info: [], warn: [], error: [] };
  const executed = [];
  let answer = opts.answer;
  const vscode = {
    ConfigurationTarget: T,
    commands: { executeCommand: async (...a) => { executed.push(a); } },
    workspace: {
      getConfiguration: (_section, scope) => {
        const lang = (scope && scope.languageId) || "";
        return {
          inspect: (key) => {
            const short = key.replace("editor.unicodeHighlight.", "");
            const out = {};
            let any = false;
            for (const prop of ["globalValue", "workspaceValue", "workspaceFolderValue",
                                "globalLanguageValue", "workspaceLanguageValue",
                                "workspaceFolderLanguageValue"]) {
              const v = values[`${lang}|${short}|${prop}`];
              if (v !== undefined) { out[prop] = v; any = true; }
            }
            return opts.noInspect ? undefined : (any ? out : {});
          },
          // ‏**البديلُ يُنمذِج النطاق** لأنّ المنبعَ كذلك: `overrideInLanguage` يعمل على
          // `overrideIdentifier` المحمول في نطاق كائن الإعداد. الصيغةُ الأولى من هذا
          // البديل تجاهلت ذلك، فمرّ نجاحٌ كاذبٌ حتّى أمسكه تشغيلٌ حيّ.
          update: async (key, value, target, inLang) => {
            if (opts.failAfter !== undefined && updates.length >= opts.failAfter) {
              throw new Error("مقفول");
            }
            if (inLang && !lang) throw new Error("طلبُ overrideInLanguage من كائنٍ بلا لغة");
            const short = key.replace("editor.unicodeHighlight.", "");
            if (opts.keepValues) { updates.push([key, value, target, inLang, lang || null]); return; }
            for (const prop of ["globalValue", "workspaceValue", "workspaceFolderValue",
                                "globalLanguageValue", "workspaceLanguageValue",
                                "workspaceFolderLanguageValue"]) {
              delete values[`${lang}|${short}|${prop}`];
            }
            updates.push([key, value, target, inLang, lang || null]);
          },
        };
      },
    },
    window: {
      showInformationMessage: async (m, ...items) => {
        shown.info.push(m);
        return answer === undefined ? undefined : items[answer];
      },
      showErrorMessage: (m) => shown.error.push(m),
      showWarningMessage: async (m, ...items) => {
        shown.warn.push(m);
        return answer === undefined ? undefined : items[answer];
      },
    },
  };
  return { vscode, updates, shown, executed };
}

function fakeMemento(initial = {}) {
  const store = { ...initial };
  return { get: (k) => store[k], update: async (k, v) => { store[k] = v; }, store };
}

test("قائمةُ المفاتيح تشمل السبعة — نقصانُ واحدٍ يترك بابًا مفتوحًا", () => {
  assert.deepStrictEqual(G.KEYS.slice().sort(), [
    "allowedCharacters", "allowedLocales", "ambiguousCharacters",
    "includeComments", "includeStrings", "invisibleCharacters", "nonBasicASCII",
  ]);
  // ‏`allowedLocales` تحديدًا: يكتبها `excludeLocaleFromBeingHighlighted` بنقرة.
  assert.ok(G.KEYS.includes("allowedLocales"));
});

test("قائمةُ اللغات = ما يضبطه محرابٌ فعلًا في قشرته", () => {
  assert.deepStrictEqual(G.LANGS,
    ["markdown", "plaintext", "git-commit", "git-rebase"]);
});

test("‏inspect يعيد undefined ⇒ لا انهيار ولا اكتشافٌ كاذب", () => {
  const f = fakeVscode({}, { noInspect: true });
  assert.deepStrictEqual(G.findOverrides(f.vscode), []);
});

test("قيمةٌ عامّةٌ بلا نطاقٍ لغويّ لا تُعدّ مُظلِّلة — افتراضُنا اللغويُّ يغلبها", () => {
  // مسارُ المنبع: الدمجُ أوّلًا ثمّ `.override(id)` — فمحتوى النطاق يُطبَّق فوق المتن.
  const f = fakeVscode({ "|nonBasicASCII|globalValue": true });
  const found = G.findOverrides(f.vscode);
  assert.strictEqual(found.length, 1);
  assert.deepStrictEqual(G.shadowing(found), []);
});

test("قيمةٌ بنطاقِ لغةٍ في إعدادات المستخدم تُعدّ مُظلِّلة — وهي الحالةُ الوحيدة", () => {
  const f = fakeVscode({ "plaintext|nonBasicASCII|globalLanguageValue": true });
  const hits = G.shadowing(G.findOverrides(f.vscode));
  assert.strictEqual(hits.length, 1);
  assert.strictEqual(hits[0].langId, "plaintext");
  assert.strictEqual(hits[0].overrideInLanguage, true);
});

test("قيمةُ مساحةِ عملٍ بنطاقِ لغة تُكتشَف أيضًا (تُورَّث مع المستودع)", () => {
  const f = fakeVscode({ "markdown|nonBasicASCII|workspaceLanguageValue": true });
  const hits = G.shadowing(G.findOverrides(f.vscode));
  assert.deepStrictEqual(hits.map((h) => [h.langId, h.scope]), [["markdown", "workspace"]]);
  assert.strictEqual(hits[0].target, T.Workspace);
});

test("‏«inUntrustedWorkspace» تُعدّ مُظلِّلة — القيمةُ ثلاثيّةٌ لا بوليانيّة", () => {
  const f = fakeVscode({ "plaintext|nonBasicASCII|globalLanguageValue": "inUntrustedWorkspace" });
  assert.strictEqual(G.shadowing(G.findOverrides(f.vscode)).length, 1);
});

test("‏false بنطاقِ لغةٍ ليست مُظلِّلة — توافقُ افتراضِنا لا مخالفتُه", () => {
  const f = fakeVscode({ "plaintext|nonBasicASCII|globalLanguageValue": false });
  assert.deepStrictEqual(G.shadowing(G.findOverrides(f.vscode)), []);
});

test("لا شيءَ ⇒ رسالةُ سلامةٍ ومخرجٌ إلى الإعدادات، بلا كتابة", async () => {
  const f = fakeVscode({}, { answer: 0 });
  assert.strictEqual(await G.resetCommand(f.vscode, fakeMemento()), 0);
  assert.deepStrictEqual(f.updates, []);
  assert.deepStrictEqual(f.shown.info, [G.COPY.clean(null, true)]);
  assert.deepStrictEqual(f.executed, [[G.OPEN_SETTINGS_CMD, G.SECTION]]);
});

// رسالةُ «لا إعداد» كانت جملةً ثابتةً تنفي السببَ وتقترح تغييرَ خطّ — وكلاهما كاذبٌ في
// ملفّ `.yaml`، وهو عينُ الملفّ الذي جاء منه بلاغُ المربّعات الصفراء [AR-05]. فصارت
// دالّةً في (لغةِ الملفّ، ثقةِ المساحة)، وهذه الأذرعُ الثلاث هي ما تجعلها صادقة.
test("رسالةُ «لا إعداد»: غيرُ الموثوقة تُسمّي السببَ وتقترح الثقة لا الخطّ", () => {
  const m = G.COPY.clean("yaml", false);
  assert.match(m, /غيرُ موثوقة/);
  assert.match(m, /yaml/);
  assert.doesNotMatch(m, /لم أجد إعدادًا يسبّب/);
});

test("رسالةُ «لا إعداد»: الموثوقةُ تنسب الباقيَ إلى خلط الكتابتَين ولا تَعِد بإزالته", () => {
  const m = G.COPY.clean("yaml", true);
  assert.match(m, /تخلط كتابتَين/);
  assert.doesNotMatch(m, /غيرُ موثوقة/);      // لا يُقال ما ليس واقعًا
});

test("رسالةُ «لا إعداد»: لغةٌ مُعفاةٌ لا تُلام على إعفاءٍ لا ينقصها", () => {
  const m = G.COPY.clean("plaintext", true);
  assert.match(m, /تخلط كتابتَين/);
  // وحتّى في مساحةٍ غيرِ موثوقة: `nonBasicASCII: false` مُسهَمٌ للنصّ العاديّ فلا سببَ يُنسَب إليه.
  assert.doesNotMatch(G.COPY.clean("plaintext", false), /غيرُ موثوقة/);
});

test("رسالةُ «تمّ» لا تَعِد بما لا يملكه الأمر", () => {
  assert.doesNotMatch(G.COPY.done("س"), /لن تُحاط/);
  assert.match(G.COPY.done("س"), /إن بقي إطارٌ/);
});

test("المسحُ يبلغ كلَّ نطاقٍ بهدفه، وبـoverrideInLanguage حين يلزم", async () => {
  const f = fakeVscode({
    "|allowedCharacters|globalValue": { "а": true },
    "plaintext|nonBasicASCII|workspaceLanguageValue": true,
  });
  assert.strictEqual(await G.resetCommand(f.vscode, fakeMemento()), 2);
  // العمودُ الأخير هو **لغةُ كائن الإعداد الذي كُتب منه**: الكتابةُ بنطاقِ لغةٍ من كائنٍ
  // بلا لغةٍ تمرّ بلا أثر (نجاحٌ كاذبٌ أمسكه تشغيلٌ حيّ).
  assert.deepStrictEqual(f.updates, [
    ["editor.unicodeHighlight.allowedCharacters", undefined, T.Global, false, null],
    ["editor.unicodeHighlight.nonBasicASCII", undefined, T.Workspace, true, "plaintext"],
  ]);
});

test("نجاحٌ بلا أثرٍ يُقال فشلًا — إقرارٌ بإعادة القراءة لا بعدم الرمي", async () => {
  const f = fakeVscode({ "plaintext|nonBasicASCII|globalLanguageValue": true },
                       { keepValues: true });
  await G.resetCommand(f.vscode, fakeMemento());
  assert.deepStrictEqual(f.shown.info, []);
  assert.strictEqual(f.shown.error.length, 1);
  assert.ok(f.shown.error[0].startsWith("لم تُزَل"));
});

test("رسالةُ النجاح تسمّي ما أُزيل — لا «تمّ» صامتة", async () => {
  const f = fakeVscode({ "plaintext|invisibleCharacters|globalLanguageValue": false });
  await G.resetCommand(f.vscode, fakeMemento());
  assert.strictEqual(f.shown.info.length, 1);
  assert.ok(f.shown.info[0].includes("invisibleCharacters"));
  assert.ok(f.shown.info[0].includes("plaintext"));
});

test("فشلٌ جزئيّ يُقال جزئيًّا — لا ادّعاءَ نجاحٍ ولا ادّعاءَ فشلٍ تامّ", async () => {
  const f = fakeVscode({
    "|allowedCharacters|globalValue": { "а": true },
    "|nonBasicASCII|globalValue": true,
  }, { failAfter: 1 });
  const n = await G.resetCommand(f.vscode, fakeMemento());
  assert.strictEqual(n, 1);
  assert.deepStrictEqual(f.shown.info, []);
  assert.strictEqual(f.shown.error.length, 1);
  assert.ok(f.shown.error[0].startsWith("أُزيل 1 من 2"));
});

test("فشلٌ من أوّل مفتاح ⇒ رسالةُ فشلٍ تامّ بطريقٍ يدويّ", async () => {
  const f = fakeVscode({ "|nonBasicASCII|globalValue": true }, { failAfter: 0 });
  assert.strictEqual(await G.resetCommand(f.vscode, fakeMemento()), 0);
  assert.ok(f.shown.error[0].includes("editor.unicodeHighlight"));
});

test("الإنذار يقع على المُظلِّل، و«أزِل» تعيد true بعد إزالةٍ فعليّة", async () => {
  const f = fakeVscode({ "plaintext|nonBasicASCII|globalLanguageValue": true }, { answer: 0 });
  assert.strictEqual(await G.maybeWarn(f.vscode, fakeMemento()), true);
  assert.deepStrictEqual(f.shown.warn, [G.COPY.warn]);
});

test("«أزِل» مع فشلِ الكتابة ⇒ لا تُعيد true (لا ادّعاءَ إصلاح)", async () => {
  const f = fakeVscode({ "plaintext|nonBasicASCII|globalLanguageValue": true },
                       { answer: 0, failAfter: 0 });
  assert.strictEqual(await G.maybeWarn(f.vscode, fakeMemento()), false);
});

test("«اتركها» يُحفَظ ببصمةٍ مرتّبة فلا يتكرّر الإنذار", async () => {
  const f = fakeVscode({ "plaintext|nonBasicASCII|globalLanguageValue": true }, { answer: 1 });
  const m = fakeMemento();
  await G.maybeWarn(f.vscode, m);
  assert.strictEqual(m.get(G.STATE_KEY), "global:plaintext:nonBasicASCII");
  const f2 = fakeVscode({ "plaintext|nonBasicASCII|globalLanguageValue": true }, { answer: 1 });
  assert.strictEqual(await G.maybeWarn(f2.vscode, m), false);
  assert.deepStrictEqual(f2.shown.warn, []);
});

test("البصمةُ التي يحفظها الحارسُ **مرتّبة** — لا ترتيبَ اكتشافٍ عارض", async () => {
  // ‏`findOverrides` تمرّ على ‏LANGS بترتيبها (plaintext ثمّ git-commit)، فبلا `sort()` تُحفَظ
  // بصمةٌ بترتيبِ المرور — وتتغيّر بتغيّر ترتيب اللغات فيعود الإنذارُ بلا سبب.
  const f = fakeVscode({
    "plaintext|nonBasicASCII|globalLanguageValue": true,
    "git-commit|nonBasicASCII|globalLanguageValue": true,
  }, { answer: 1 });
  const m = fakeMemento();
  await G.maybeWarn(f.vscode, m);
  assert.strictEqual(m.get(G.STATE_KEY),
    "global:git-commit:nonBasicASCII,global:plaintext:nonBasicASCII");
});

test("حالةٌ جديدةٌ بعد «اتركها» تُعيد الإنذار", async () => {
  const m = fakeMemento({ [G.STATE_KEY]: "global:plaintext:nonBasicASCII" });
  const f = fakeVscode({ "markdown|nonBasicASCII|workspaceLanguageValue": true },
                       { answer: 1 });
  await G.maybeWarn(f.vscode, m);
  assert.deepStrictEqual(f.shown.warn, [G.COPY.warn]);
});

test("تنفيذُ الأمر يدويًّا يمسح «اتركها» — طلبُ الإصلاح إلغاءٌ ضمنيٌّ للتجاهل", async () => {
  const m = fakeMemento({ [G.STATE_KEY]: "global:plaintext:nonBasicASCII" });
  const f = fakeVscode({});
  await G.resetCommand(f.vscode, m);
  assert.strictEqual(m.get(G.STATE_KEY), undefined);
});

test("إغلاقُ الإنذار بلا اختيار لا يُحفَظ — فيعود في الإقلاع التالي", async () => {
  const f = fakeVscode({ "plaintext|nonBasicASCII|globalLanguageValue": true });
  const m = fakeMemento();
  await G.maybeWarn(f.vscode, m);
  assert.strictEqual(m.get(G.STATE_KEY), undefined);
});
