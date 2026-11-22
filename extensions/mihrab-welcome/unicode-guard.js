"use strict";
/**
 * حارسُ إبراز يونيكود [AR-04]: مخرجُ تعافٍ من إعدادٍ يُظلِّل افتراضاتِ محراب.
 *
 * **أيُّ إعدادٍ يغلب افتراضَنا فعلًا — مُثبَتٌ بقراءة المنبع لا بالحدس.** افتراضاتُنا
 * تُسهَم عبر `configurationDefaults` بنطاقٍ لغويّ (`"[markdown]": {...}`). و
 * `getConsolidatedConfigurationModel` (‏configurationModels.ts:990) يدمج المصادرَ كلَّها
 * أوّلًا ثمّ يستدعي `.override(id)` — فمحتوى النطاق اللغويّ يُطبَّق **فوق** المتن أيًّا كان
 * مصدرُه. والنتيجة:
 *   • قيمةُ مستخدمٍ **عامّة** (`nonBasicASCII: true` بلا نطاق) ⇒ **لا تغلبنا**. افتراضُنا
 *     اللغويُّ يبقى ساريًا في اللغات التي نضبطها. فالإنذارُ عليها إنذارٌ كاذب.
 *   • قيمةٌ **بنطاقٍ لغويّ** (`"[markdown]": {"editor.unicodeHighlight.nonBasicASCII": true}`)
 *     في إعدادات المستخدم أو مساحة العمل أو المجلّد ⇒ **تغلبنا**، وهي الحالةُ الوحيدة.
 *
 * وهذه القيمُ اللغويّةُ **لا تظهر** في `inspect().globalValue`: لا يملأ المنبعُ
 * `globalLanguageValue` إلّا حين يُطلَب الإعدادُ بنطاقِ لغة. فقراءةٌ بلا `languageId`
 * تعمى عن الحالة الوحيدة التي تُنتِج العَرَض — وهذا ما كانت عليه الصيغةُ الأولى:
 * تُنذر على ما لا يضرّ، وتصمت عمّا يضرّ، وتقول للمستخدم «لا إعداد» والإطاراتُ أمامه.
 */

const SECTION = "editor.unicodeHighlight";
// المفاتيحُ التي تطالها نقرةٌ واحدةٌ من قائمة الاستبعاد أو شريطِ مساحة العمل المقيَّدة.
// ‏`allowedLocales` منها: `excludeLocaleFromBeingHighlighted` يكتبها بنقرة.
const KEYS = [
  "allowedCharacters",
  "allowedLocales",
  "nonBasicASCII",
  "ambiguousCharacters",
  "invisibleCharacters",
  "includeComments",
  "includeStrings",
];
// النطاقاتُ التي يضبطها محرابٌ في mihrab-shell/package.json. فحصُ L0 يوجب تطابقَ
// القائمتين: نطاقٌ يُضاف هناك ولا يُضاف هنا يبقى بلا تشخيصٍ ولا إصلاح.
const LANGS = ["markdown", "plaintext", "git-commit", "git-rebase"];

const STATE_KEY = "mihrab.unicodeHighlight.dismissed";
const OPEN_SETTINGS_CMD = "workbench.action.openSettings";

// النصوصُ من عَرَضِ المستخدم لا من مصطلح المنبع: من يراها لا يعرف «إبراز يونيكود» ولا
// «إعدادًا عامًّا» — يعرف إطارًا أصفرَ حول حروفه. (صياغةُ مراجعةِ تجربة المستخدم.)
const COPY = {
  warn: "يوجد إعدادٌ يرسم إطارًا أصفرَ حول الحروف العربيّة في محراب. أتريد إزالته؟",
  reset: "أزِل الإطارات",
  dismiss: "اتركها",
  // **لا وعدَ مطلقٌ عن سببٍ واحدٍ نملكه.** «لن تُحاط الحروفُ بإطارٍ بعد الآن» صحيحةٌ عن
  // الإعدادات وكاذبةٌ عن الشاشة: للإطار أسبابٌ أخرى لا يملكها الأمرُ (مساحةٌ غيرُ موثوقة،
  // كلمةٌ تخلط كتابتَين). ومن يرى الإطارَ باقيًا بعد «تمّ» يظنّ الأداةَ عطبةً فيكفّ.
  done: (names) => `تمّ. أُزيل من إعداداتك: ${names}. إن بقي إطارٌ أمامك فسببُه ليس إعدادًا لك — شغّل الأمرَ ثانيةً لأقول من أين.`,
  partial: (n, total, e) =>
    `أُزيل ${n} من ${total} إعدادًا ثمّ تعذّر الباقي: ${e}. أعِد المحاولة أو احذف يدويًّا ما يبدأ بـ editor.unicodeHighlight.`,
  /**
   * **الرسالةُ التي كانت تكذب.** كانت جملةً واحدة: «لم أجد إعدادًا يسبّب الإطاراتِ
   * الصفراء… فقد تكون فراغاتِ خطٍّ لا يعرض العربيّة». وهي في ملفّ `.yaml` كذبتان:
   * السببُ **موجودٌ ومعروفٌ وموثَّقٌ عندنا** (افتراضُ المنبع، وإعفاؤنا لا يشمل هذه
   * اللغة)، ونقصُ الرسم يُعرَض مربّعًا **فارغًا** لا إطارًا حول حرفٍ مرسوم — فالجملةُ
   * توجّه صاحبَ البلاغ إلى تغيير خطٍّ لا يغيّر شيئًا وتُنهي بحثَه.
   *
   * والصدقُ هنا يحتاج متغيّرَين مقروءَين مجّانًا: لغةُ الملفّ المفتوح، وثقةُ المساحة —
   * لأنّ السببَ يختلف بهما اختلافًا كاملًا:
   *   • مساحةٌ **غيرُ موثوقة** ولغةٌ خارجَ إعفائنا ⇒ `nonBasicASCII` (افتراضُه
   *     `inUntrustedWorkspace`) يُبرِز كلَّ حرفٍ غيرِ لاتينيّ. والعلاجُ الأرخصُ الثقةُ
   *     بالمجلّد، لا تعديلُ إعداد.
   *   • مساحةٌ **موثوقة** ⇒ الباقي هو `ambiguousCharacters`، أي تنبيهُ خلطِ الكتابتَين
   *     بعد رقعة النواة ‎033‎ — **مقصودٌ ولا يُوعَد بإزالته**، فهو ما يميّز `مثال` من
   *     `مثاl`.
   */
  clean: (langId, isTrusted) => {
    const covered = LANGS.includes(langId);
    const what = langId ? `ملفّاتِ ${langId}` : "هذا النوعِ من الملفّات";
    const out = ["لا شيءَ في إعداداتك يرسم هذه الإطارات."];
    if (!isTrusted && !covered) {
      out.push(`ومساحةُ العمل هذه غيرُ موثوقة: يُبرَز فيها كلُّ حرفٍ غيرِ لاتينيٍّ افتراضًا،`
        + ` ومحرابٌ يُطفئ ذلك في النصوص العربيّة (markdown والنصّ العاديّ ورسائل الالتزام) وحدَها — لا في ${what}.`
        + " الثقةُ بالمجلّد تُزيل أكثرَها.");
    } else {
      out.push("والباقي تنبيهُ «كلمةٌ تخلط كتابتَين»: حرفٌ عربيٌّ في كلمةٍ لاتينيّةٍ أو"
        + " العكس. وهو مقصودٌ لأنّه يميّز «مثال» من «مثاl».");
    }
    out.push("أمّا المربّعُ **الفارغ** فليس إطارًا: حرفٌ لا يملك الخطُّ رسمَه، وعلاجُه"
      + " تغييرُ الخطّ لا الإعدادات.");
    return out.join(" ");
  },
  openSettings: "افتح الإعدادات",
  failed: (e) =>
    `تعذّرت إزالةُ الإعداد: ${e} — افتح ملفّ الإعدادات واحذف السطورَ التي تبدأ بـ editor.unicodeHighlight.`,
  stubborn: (names) =>
    `لم تُزَل هذه الإعدادات رغم المحاولة: ${names}. افتح ملفّ الإعدادات واحذفها يدويًّا.`,
};

/** وصفٌ مقروءٌ لموضع القيمة، يُذكر للمستخدم كي يتعلّم لا كي يُسحَر. */
function describe(entry) {
  const where = { global: "إعداداتك", workspace: "إعدادات المشروع",
                  folder: "إعدادات المجلّد" }[entry.scope];
  return entry.langId ? `${entry.key} في ${where} للغة ${entry.langId}`
                      : `${entry.key} في ${where}`;
}

/**
 * يمسح كلَّ موضعٍ فيه قيمة. يعيد `{key, langId, scope, target, overrideInLanguage}`.
 * يقرأ بنطاقِ اللغة **وبلا نطاق**: الأوّلُ ضروريٌّ لكشف ما يغلبنا، والثاني ليمسحه الأمرُ
 * أيضًا حين يطلب المستخدمُ العودةَ إلى حالٍ نظيفة.
 */
function findOverrides(vscode) {
  const found = [];
  const targets = vscode.ConfigurationTarget;
  const scopes = [
    ["global", "globalValue", "globalLanguageValue", targets.Global],
    ["workspace", "workspaceValue", "workspaceLanguageValue", targets.Workspace],
    ["folder", "workspaceFolderValue", "workspaceFolderLanguageValue",
     targets.WorkspaceFolder],
  ];
  for (const langId of [null, ...LANGS]) {
    const config = vscode.workspace.getConfiguration(
      undefined, langId ? { languageId: langId } : undefined);
    for (const key of KEYS) {
      const info = config.inspect(`${SECTION}.${key}`);
      if (!info) continue;
      for (const [scope, plainProp, langProp, target] of scopes) {
        const value = info[langId ? langProp : plainProp];
        if (value === undefined) continue;
        found.push({ key, langId, scope, target, value,
                     overrideInLanguage: Boolean(langId) });
      }
    }
  }
  return found;
}

/**
 * ما يغلب افتراضَنا فعلًا: قيمةٌ بنطاقِ لغةٍ من لغاتنا تُعيد الإبراز. القيمةُ ثلاثيّة
 * (`true|false|"inUntrustedWorkspace"`)، فالشرطُ «ليست false» لا «تساوي true».
 */
function shadowing(overrides) {
  return overrides.filter(
    (o) => o.langId && o.key === "nonBasicASCII" && o.value !== false);
}

/** أمرُ «أزِل الإطارات الصفراء». يعيد عددَ ما أُزيل. */
async function resetCommand(vscode, memento) {
  const found = findOverrides(vscode);
  // تنفيذُ الأمر يدويًّا إلغاءٌ ضمنيٌّ لأيّ «اتركها» سابقة.
  if (memento) await memento.update(STATE_KEY, undefined);
  if (!found.length) {
    // يُقرآن دفاعيًّا: لا محرّرَ مفتوحٍ حالةٌ واقعة، و`isTrusted` قد تغيب في مضيفٍ قديم.
    // و«ليست false» لا «تساوي true» — الغيابُ يُقرأ موثوقًا لأنّه الحالُ الغالبة، ولأنّ
    // الفرعَ الآخرَ يَعِد بأنّ الثقةَ تُزيل الإطارات فلا يُقال إلّا عن يقين.
    const doc = vscode.window.activeTextEditor && vscode.window.activeTextEditor.document;
    const choice = await vscode.window.showInformationMessage(
      COPY.clean((doc && doc.languageId) || null, vscode.workspace.isTrusted !== false),
      COPY.openSettings);
    if (choice === COPY.openSettings) {
      await vscode.commands.executeCommand(OPEN_SETTINGS_CMD, SECTION);
    }
    return 0;
  }
  let cleared = 0;
  for (const o of found) {
    try {
      // ‏**الضبطُ يُكتب من نفس الكائن الذي قُرئ منه.** `overrideInLanguage` يعمل على
      // `overrideIdentifier` المحمولِ في نطاق كائن الإعداد؛ فكائنٌ أُخذ بلا `languageId`
      // لا يعرف أيَّ كتلةٍ يمسّ، فتمرّ الكتابةُ **بلا خطأٍ وبلا أثر**. أمسكه تشغيلٌ حيّ:
      // الرسالةُ تقول «تمّ… أُزيل» و`settings.json` كما هو. مثالُ نجاحٍ كاذبٍ لا يراه
      // اختبارُ وحدةٍ ببديلٍ لا يُنمذِج النطاق.
      const scoped = vscode.workspace.getConfiguration(
        undefined, o.langId ? { languageId: o.langId } : undefined);
      await scoped.update(`${SECTION}.${o.key}`, undefined, o.target,
                          o.overrideInLanguage);
      cleared++;
    } catch (e) {
      const msg = (e && e.message) || String(e);
      // فشلٌ جزئيٌّ يُقال كما هو: ادّعاءُ النجاح يترك المستخدمَ يظنّ حالَه سليمةً وهي نصفُ ممسوحة.
      vscode.window.showErrorMessage(
        cleared ? COPY.partial(cleared, found.length, msg) : COPY.failed(msg));
      return cleared;
    }
  }
  // **إقرارٌ بالأثر لا بعدم الرمي.** الكتابةُ قد تُقبَل ولا تُغيّر شيئًا (أعلاه)، فنُعيد
  // القراءةَ ونقول ما بقي. رسالةُ نجاحٍ بلا أثرٍ أسوأُ من رسالة فشل: تُنهي بحثَ المستخدم.
  const left = findOverrides(vscode);
  if (left.length) {
    vscode.window.showErrorMessage(COPY.stubborn(left.map(describe).join("، ")));
    return cleared;
  }
  vscode.window.showInformationMessage(COPY.done(found.map(describe).join("، ")));
  return cleared;
}

/** إنذارٌ عند الإقلاع، مرّةً لكلّ حالةٍ جديدة. يعيد true إن أُزيلت الإطاراتُ فعلًا. */
async function maybeWarn(vscode, memento) {
  const hits = shadowing(findOverrides(vscode));
  if (!hits.length) return false;
  const signature = hits.map((o) => `${o.scope}:${o.langId}:${o.key}`).sort().join(",");
  if (memento.get(STATE_KEY) === signature) return false;
  const choice = await vscode.window.showWarningMessage(
    COPY.warn, COPY.reset, COPY.dismiss);
  if (choice === COPY.reset) return (await resetCommand(vscode, memento)) > 0;
  if (choice === COPY.dismiss) await memento.update(STATE_KEY, signature);
  return false;
}

module.exports = {
  SECTION, KEYS, LANGS, STATE_KEY, OPEN_SETTINGS_CMD, COPY,
  describe, findOverrides, shadowing, resetCommand, maybeWarn,
};
