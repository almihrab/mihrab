// @ts-check
"use strict";
// امتداد ترحيب محراب (الطبقة 1): جولاتُ الترحيب العربيّة، وحرّاسُ الاتّجاه والحافظة وأسماء الملفّات،
// والمساعدةُ داخل المحرّر، واستيرادُ إعدادات VS Code، وخبرُ الإصدار الأحدث.

const vscode = require("vscode");
const unicodeGuard = require("./unicode-guard.js");
const bidiGuard = require("./bidi-guard.js");
const bidiDecorate = require("./bidi-decorate.js");
const clipboard = require("./clipboard-safety.js");
const { activateNameGuard } = require("./name-guard.js");
const { HelpPanel, OPEN_CMD: OPEN_HELP_CMD } = require("./help-panel.js");
// [WEB-06] قارئُ القرص خارجَ `help-panel.js` كي تبقى تلك الوحدةُ صالحةً لحزمة المتصفّح.
const { nodeReader } = require("./help-data-node.js");
const releaseNotice = require("./release-notice.js");
const terminalNotice = require("./terminal-notice.js");
const { activateTerminalNotice } = terminalNotice;
const diffNotice = require("./diff-notice.js");
const { activateDiffNotice } = diffNotice;
const importSettings = require("./import-settings.js");

// معرّف الجولة التي تُفتَح أوّلَ مرّة (id في contributes.walkthroughs)؛ المعرّف الكامل يُشتَقّ وقت
// التشغيل من context.extension.id (publisher.name) كي لا ينكسر لو تغيّرت الهوية. [M4]
const WALKTHROUGH_LOCAL_ID = "mihrab.arabicFirst";
const WALKTHROUGH_ID_SEP = "#";
// مفتاح حالة عامّة: هل عُرِضت جولة الترحيب مرّة على هذا الملفّ الشخصيّ؟ (تُفتح مرّة واحدة).
const WELCOME_SHOWN_KEY = "mihrab.welcome.shown";
// مخرجُ التعافي من إعدادٍ عامٍّ يُبطِل افتراضاتِ إبراز يونيكود. [AR-04]
const RESET_UNICODE_CMD = "mihrab.resetUnicodeHighlight";
// إزالةُ محارف قلب الاتّجاه غير المتوازنة من المستند الحاليّ (إصلاحُ تشخيص BS-01). المعرّف
// مصدرُه وحدةُ الحارس كي لا يفترق عن الإجراء الذي يستدعيه (نمطُ المصدر الواحد في المستودع).
const REMOVE_BIDI_CMD = bidiGuard.REMOVE_CMD;
const printCmd = require("./print-command.js");
const EXPORT_PRINT_CMD = printCmd.EXPORT_CMD;
// إعادةُ إظهار شارة الطرفيّة بعد إخفائها — المقبضُ الذي يجعل الإخفاءَ قرارًا لا بابًا مغلَقًا.
const SHOW_TERMINAL_NOTICE_CMD = terminalNotice.SHOW_AGAIN_CMD;
const SHOW_DIFF_NOTICE_CMD = diffNotice.SHOW_AGAIN_CMD;
// [BS-02] تبديلُ عرضِ أسماء محارف الاتّجاه — «سمِّ الشيءَ لتُمكِّن من الفعل».
const TOGGLE_BIDI_MARKERS_CMD = bidiDecorate.TOGGLE_CMD;
// [ON-04] فحصُ إصدارٍ أحدث يدويًّا — المحدِّثُ التلقائيُّ معطَّلٌ عمدًا، والخبرُ ليس كذلك.
const CHECK_UPDATE_CMD = "mihrab.checkForUpdate";
// [BS-04] «انسخ للنشر»: يلفّ كلَّ سطرٍ بعزلٍ اتّجاهيّ كي يُعرَض خارج محرابٍ
// بالترتيب نفسِه. المعرّفُ مصدرُه الوحدةُ لا نصٌّ مكرَّر.
const COPY_SAFE_CMD = clipboard.COPY_SAFE_CMD;
// [BS-04] بابُ العودة: يزيل عزلَ النشر من ملفٍّ لُصِق فيه. ميزةٌ تُدخِل شيئًا ولا تملك
// إخراجَه ميزةٌ نصفُها فخّ — والمحارفُ متوازنةٌ فلا يمسّها زرُّ إصلاح BS-01.
const STRIP_ISO_CMD = clipboard.STRIP_ISO_CMD;
// أمرُ المنبع لفتح لوحة المشاكل — يُمرَّر إلى بلاغ اللصق زرًّا «أرِني الموضع».
const SHOW_PROBLEMS_CMD = "workbench.actions.view.problems";
// [ON-04] مصدرُ مانيفست الإصدارات وصفحةُ التنزيل — من هويّة المنتج لا مكتوبَين حرفيًّا هنا.
const RELEASES_URL = "https://mihrab.dev/dl/releases.json";
const DOWNLOAD_URL = "https://mihrab.dev/download/";
// مهلةُ جلبِ المانيفست: خبرٌ تحسينيٌّ لا يُبطئ الإقلاعَ ولا ينتظر شبكةً متعثّرة.
const RELEASES_TIMEOUT_MS = 8000;
// عدّادُ الجلسات، وأقلُّ جلسةٍ يُطلَب فيها إذنُ فحص الإصدارات (لا في أوّل إقلاع).
const SESSIONS_KEY = "mihrab.sessions";
const MIN_SESSIONS_BEFORE_ASK = 2;
// معرّف الامتداد الاحتياطيّ إن غابت هوية التشغيل (publisher.name — يطابق package.json).
const DEFAULT_EXTENSION_ID = "mihrab.mihrab-welcome";

// أمر النواة لفتح جولة، ووسيط «لا عمود جانبيّ» (تُملأ منطقة المحرّر الرئيسة).
const OPEN_WALKTHROUGH_CMD = "workbench.action.openWalkthrough";

/** يفتح جولة الترحيب مرّة واحدة على هذا الملفّ الشخصيّ (أوّل إقلاع بعد التثبيت). */
async function maybeShowWelcome(context) {
  if (context.globalState.get(WELCOME_SHOWN_KEY)) return;
  // المعرّف الكامل يُشتَقّ من هوية الامتداد وقت التشغيل (لا يُثبَّت publisher حرفيًّا). [M4]
  const ext = context.extension;
  const fullId = (ext && ext.id ? ext.id : DEFAULT_EXTENSION_ID) +
    WALKTHROUGH_ID_SEP + WALKTHROUGH_LOCAL_ID;
  try {
    await vscode.commands.executeCommand(OPEN_WALKTHROUGH_CMD, fullId, false);
    // نسِم «عُرِضت» فقط بعد نجاح الفتح: فشلٌ عابر (الجولة لم تُسجَّل بعدُ) يُعيد المحاولة
    // في الإقلاع التالي بدل إخماد الجولة أبدًا — وهو ذات العطل الأصليّ المُبلَّغ. [M2]
    await context.globalState.update(WELCOME_SHOWN_KEY, true);
  } catch {
    // الجولة تحسينيّة — فشلها لا يُفشِل التنشيط ولا يُسجَّل كمعروض (تُعاد المحاولة لاحقًا).
  }
}

/** حالةُ الامتداد العامّة — تُضبَط عند التنشيط ويقرؤها ما يُستدعى من أوامرَ لاحقًا. */
let extensionState = null;
/** إصدارُ محراب المشحون (من مانيفست هذا الامتداد) — مرجعُ مقارنةِ الإصدارات [ON-04]. */
let mihrabVersion = "";

function activate(context) {
  extensionState = context.globalState;
  mihrabVersion = (context.extension && context.extension.packageJSON
    && String(context.extension.packageJSON.version)) || "";

  context.subscriptions.push(
    // [AR-04] مخرجُ تعافٍ: قيمةٌ بنطاقِ لغةٍ في إعدادات المستخدم/المشروع تُظلِّل افتراضَنا،
    // ولا شيءَ في الواجهة يقول للمستخدم لماذا عادت الإطارات. الأمرُ يمسحها بنطاقها.
    vscode.commands.registerCommand(RESET_UNICODE_CMD,
      () => unicodeGuard.resetCommand(vscode, context.globalState)),
    // [BS-01] إزالةُ الفواتح غير المتوازنة — إجراءُ إصلاحٍ للتشخيص وأمرٌ في لوحة الأوامر معًا.
    vscode.commands.registerCommand(REMOVE_BIDI_CMD,
      (uri, range) => bidiGuard.removeCommand(vscode, uri, range)),
    // [PR-01] الورقةُ لا تحمل زخرفةً ولا تحويمًا ولا لونًا، فمراجعةٌ تُجرى على ورقٍ تفقد
    // كلَّ ما بناه محرابٌ ضدّ قلبِ الاتّجاه. هذا الأمرُ يجعل الخفيَّ حبرًا — ويُبقي الأصلَ
    // حرفًا بحرف في `data-src` كي لا يصير التصديرُ غسّالةَ هجوم.
    vscode.commands.registerCommand(EXPORT_PRINT_CMD,
      () => printCmd.exportForPrint(vscode, context)),
    // المُحدِّدُ **مشتقٌّ من المخطّطات التي يمسحها الحارسُ فعلًا** لا مكتوبٌ بيده: كان
    // ‏`{scheme:"file"}` وحدَه يترك ملفًّا غيرَ محفوظ (وهو أوّلُ ما يلصق فيه المستخدمُ من
    // الشابكة، أي أعلى لحظاتِ الخطر) مُشخَّصًا **بلا مصباحِ إصلاح** — لومٌ بلا مخرَج.
    vscode.languages.registerCodeActionsProvider(
      [...bidiGuard.SCANNED_SCHEMES].map((scheme) => ({ scheme })),
      new bidiGuard.BidiCodeActionProvider(vscode),
      { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] }
    )
  );

  // عند اكتمال الإقلاع (onStartupFinished) اعرض الجولة أوّل مرّة فقط (رفض الوعد مُبتلَع). [L5]
  void maybeShowWelcome(context).catch(() => {});

  // [AR-04] إنذارٌ عن إعدادٍ يُظلِّل افتراضَنا **بنطاق لغة** (الحالةُ الوحيدة التي تُنتِج
  // الإطارات)، مرّةً لكلّ حالةٍ لا في كلّ إقلاع.
  void unicodeGuard.maybeWarn(vscode, context.globalState).catch(() => {});

  // [BS-01] كاشفُ قلب الاتّجاه: يُنشأ بعد تسجيل الأمر كي يجد الإصلاحُ أمرَه مسجَّلًا، ويُسجِّل
  // نفسَه في subscriptions من مُنشِئه.
  new bidiGuard.BidiGuard(vscode, context);

  // [BS-03] حارسُ أسماء الملفّات: يعمّم ما كان محصورًا في اسم المشروع على الإنشاء وإعادة
  // التسمية. لا حقَّ نقضٍ لدينا (المنبع لا يمنحه)، فالصدقُ كشفٌ فوريٌّ بإصلاحٍ بنقرة.
  activateNameGuard(vscode, context);

  // [DR-03] شارةُ الطرفيّة ورسالتُها: الحدُّ المنبعيُّ مرئيٌّ ومعالَجٌ لا صامت — ومعه أمرُ
  // إعادةِ إظهارٍ كي لا يصير الإخفاءُ بابًا بلا مقبض (درسُ «أزِل الإطارات الصفراء»).
  const termNotice = activateTerminalNotice(vscode, context.globalState);
  context.subscriptions.push(
    termNotice,
    vscode.commands.registerCommand(SHOW_TERMINAL_NOTICE_CMD, () => termNotice.showAgain())
  );

  // [DR-04] رسالةُ محرّر الفرق: الاستثناءُ الاتّجاهيُّ الوحيدُ الباقي يُسمّى بدل أن يُخمَّن.
  // كان مسجَّلًا «لم يُنفَّذ» لأنّ ترويسةَ الفرق سطحٌ منبعيّ — والحكمُ كان على الموضع لا على
  // الرسالة، والطبقةُ الأولى تبلغ اللحظةَ نفسَها بلا رقعة (سابقةُ رسالة الطرفيّة).
  const dfNotice = activateDiffNotice(vscode, context.globalState);
  context.subscriptions.push(
    dfNotice,
    vscode.commands.registerCommand(SHOW_DIFF_NOTICE_CMD, () => dfNotice.showAgain())
  );

  // [BS-02] تسميةُ محارف الاتّجاه — **مطفأةٌ افتراضيًّا**: نصُّ العربيّة السويُّ مليءٌ
  // بعلاماتٍ مشروعة، فإظهارُها دائمًا يعيد الضجيجَ الذي بُني BS-01 كلُّه لتفاديه. تُفتَح
  // بأمرٍ حين يسأل المستخدمُ «ما هذا؟».
  const bidiMarkers = new bidiDecorate.BidiMarkerDecorator(vscode);
  const helpPanel = new HelpPanel(vscode, context, nodeReader(context.extensionPath));
  context.subscriptions.push(
    bidiMarkers,
    helpPanel,
    vscode.commands.registerCommand(TOGGLE_BIDI_MARKERS_CMD, () => bidiMarkers.toggle()),
    // [ON-03] المساعدةُ داخل المحرّر: المحتوى مكتوبٌ عندنا سلفًا، والناقصُ كان المنفذ.
    vscode.commands.registerCommand(OPEN_HELP_CMD, () => helpPanel.open()),
    // [ON-04] الفحصُ اليدويّ يتجاوز الفاصلَ الزمنيّ ويقول نتيجتَه دائمًا (صمتُ الطلب إهمال).
    vscode.commands.registerCommand(CHECK_UPDATE_CMD, () => checkRelease(true)),
    // [BS-04] بابا الحافظة. **الخروجُ أمرٌ صريح** فكلفتُه صفرٌ لمن لا يطلبه.
    vscode.commands.registerCommand(COPY_SAFE_CMD, () => clipboard.copyForSharing(vscode)),
    vscode.commands.registerCommand(STRIP_ISO_CMD, () => clipboard.stripIsolatesCommand(vscode))
  );

  // [MG-01] بابُ القادم من VS Code. **محلّيٌّ بلا شبكةٍ ولا حساب** — وهو القيدُ الذي يجعل
  // الاستيرادَ متّسقًا مع موقف محرابٍ من الخصوصيّة لا ناقضًا له. والوحدةُ تُسجّل أمرَيها معًا:
  // ميزةٌ تُدخِل شيئًا ولا تملك إخراجَه ميزةٌ نصفُها فخّ (سابقةُ «أزِل عزل النشر»).
  context.subscriptions.push(...importSettings.activateImport(vscode, context));

  // [BS-04] **والدخولُ بلاغٌ لا اعتراض**: اللصقُ أكثرُ عمليّةٍ تكرارًا في المحرّر، فتدخُّلٌ
  // يعترضه ضريبةٌ على كلّ عمل. مرّةً في الجلسة، وحين يكون في الملصوق قالبٌ غيرُ متوازن
  // وحدَه، وله «لا تُنبّهني» دائم. وأمرُ الإصلاح **يُمرَّر** لا يُكتَب هناك حرفيًّا.
  clipboard.activatePasteNotice(vscode, context, {
    removeCommand: REMOVE_BIDI_CMD,
    showProblemsCommand: SHOW_PROBLEMS_CMD,
  });

  // [ON-04] فحصٌ خفيفٌ عند الإقلاع — **بإذنٍ صريحٍ**، وبفاصلٍ يوميّ، وبلا إرسالِ شيءٍ عن
  // المستخدم. غيابُ المحدِّث قرارٌ سليم؛ غيابُ الخبر ليس كذلك.
  //
  // **ولا يُطلَب الإذنُ في أوّل إقلاع.** أوّلُ ثانيةٍ في محرابٍ تحمل الجولةَ وإنذارَ الإطارات
  // الصفراء؛ وطلبُ إذنِ شبكةٍ يزاحمها يُرفَض **بالعادة لا بالقرار** — ورفضٌ مخزَّنٌ لا يُسأل
  // عنه ثانيةً. فنؤجّله إلى الجلسة الثانية، حيث صار للسؤال معنًى عند من عرف المنتج.
  const sessions = (context.globalState.get(SESSIONS_KEY) || 0) + 1;
  void context.globalState.update(SESSIONS_KEY, sessions);
  if (sessions >= MIN_SESSIONS_BEFORE_ASK) void checkRelease(false).catch(() => {});
}

/**
 * [ON-04] يجلب مانيفست الإصدارات ويعرض الخبر. الجلبُ هنا (يمسّ الشبكة)، والقرارُ في وحدةٍ
 * نقيّةٍ تُختبَر. مهلةٌ صريحةٌ: خبرٌ تحسينيٌّ لا يعلّق شيئًا على شبكةٍ متعثّرة.
 */
async function checkRelease(force) {
  // **إصدارُ محرابٍ لا إصدارُ VS Code.** `vscode.version` رقمُ نواةِ المنبع التي بُني عليها،
  // و`releases.json` يحمل إصدارَ محراب — فمقارنتُهما تقارن نظامَي ترقيمٍ مختلفَين، ونتيجتُها
  // إمّا «محدَّث» أبديّةٌ وإمّا خبرٌ زائفٌ متكرّر. أي أنّ الميزةَ كلَّها كانت معطَّلةً صامتة.
  const version = String(mihrabVersion || "");
  if (!version) return { checked: false, newer: false, version: null };
  return releaseNotice.checkForUpdate(vscode, extensionState, {
    currentVersion: version,
    downloadUrl: DOWNLOAD_URL,
    now: Date.now(),
    force,
    fetchManifest: async () => {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), RELEASES_TIMEOUT_MS);
      try {
        const res = await fetch(RELEASES_URL, { signal: ctrl.signal });
        return res && res.ok ? await res.json() : null;
      } finally {
        clearTimeout(t);
      }
    },
  });
}

function deactivate() {}

module.exports = {
  activate,
  deactivate,
};
