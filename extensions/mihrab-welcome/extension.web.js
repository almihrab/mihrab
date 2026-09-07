"use strict";
/**
 * مدخلُ المتصفّح لامتداد الترحيب [WEB-06].
 *
 * ## لماذا مِلفٌّ ثانٍ لا رايةٌ في الأوّل
 * مُضيفُ الامتدادات في المتصفّح عاملُ ويبٍ لا عقدة: `require` فيه يحلّ `vscode` وحدَها
 * (‏`extHostExtensionService.ts` في `api/worker` — `_fakeModules.getModule` وإلّا رمى
 * «‏Cannot load module»). فأيُّ `require("fs")` في **رأس** ملفٍّ يُسقِط الوحدةَ كلَّها قبل
 * أن يُنفَّذ منها سطر، وشرطٌ داخل `activate` لا ينفع لأنّ السقوطَ يقع عند التحميل.
 * ومن هنا مدخلٌ مستقلٌّ يستورد **الوحدات الخاليةَ من العقدة وحدَها**، ويُحزَم esbuildًا
 * ملفًّا واحدًا وقتَ البناء (`dist/web/extension.js`) لأنّ ذلك المُضيفَ لا يحلّ
 * `require("./x.js")` أيضًا.
 *
 * ## وما الذي يُشحَن هنا فعلًا
 * كلُّ ما لا يحتاج عمليّةً ولا قرصًا: حرّاسُ الاتّجاه (‏BS-01/02) وبابا الحافظة (‏BS-04)
 * وحارسُ الأسماء (‏BS-03) ومخرجُ الإطارات الصفراء (‏AR-04) ورسالةُ محرّر الفرق (‏DR-04)
 * ولوحةُ المساعدة (‏ON-03، بقارئٍ من `workspace.fs`).
 *
 * ## وما لا يُشحَن — **يُقال ولا يُخفى**
 * التشغيلُ والبناءُ والفحص تحتاج عمليّةً، والاستيرادُ من VS Code يحتاج قرصَ المستخدم،
 * والتصديرُ للطباعة يقرأ خطًّا محزومًا من القرص. وكلُّها **مُسهَمةٌ في المانيفست الواحد**
 * الذي تقرؤه المنصّتان، فبنودُها تظهر في لوحة الأوامر هنا أيضًا. والخياران: أن نتركها
 * بلا مُسجِّلٍ فتقول «الأمرُ غيرُ معروف» — وهي رسالةُ عطبٍ يقرؤها المستخدمُ على أنّها
 * خللٌ في جهازه؛ أو أن نُسجِّلها برسالةٍ تقول **ما الحدُّ وأين البديل**. والثانيةُ
 * هي الصدقُ نفسُه الذي أزلنا لأجله لوحَ الطرفيّة الميّت (‏م-٢٩): الغيابُ يُفهَم،
 * والصمتُ لا يُفهَم.
 */

const vscode = require("vscode");

const unicodeGuard = require("./unicode-guard.js");
const bidiGuard = require("./bidi-guard.js");
const bidiDecorate = require("./bidi-decorate.js");
const clipboard = require("./clipboard-safety.js");
const { activateNameGuard } = require("./name-guard.js");
const diffNotice = require("./diff-notice.js");
const { activateDiffNotice } = diffNotice;
const {
  HelpPanel,
  OPEN_CMD: OPEN_HELP_CMD,
  DATA_DIR,
  GLOSSARY_FILE,
  KEYBINDINGS_FILE,
} = require("./help-panel.js");

const RESET_UNICODE_CMD = "mihrab.resetUnicodeHighlight";
const REMOVE_BIDI_CMD = bidiGuard.REMOVE_CMD;
const TOGGLE_BIDI_MARKERS_CMD = bidiDecorate.TOGGLE_CMD;
const COPY_SAFE_CMD = clipboard.COPY_SAFE_CMD;
const STRIP_ISO_CMD = clipboard.STRIP_ISO_CMD;
const SHOW_DIFF_NOTICE_CMD = diffNotice.SHOW_AGAIN_CMD;
const SHOW_PROBLEMS_CMD = "workbench.actions.view.problems";
const OPEN_WALKTHROUGH_CMD = "workbench.action.openWalkthrough";

/** جولةُ المتصفّح — نظيرةُ `mihrab.gettingStarted` حيث لا تشغيلَ ولا قرص. */
const WEB_WALKTHROUGH_LOCAL_ID = "mihrab.web";
const WALKTHROUGH_ID_SEP = "#";
const DEFAULT_EXTENSION_ID = "sadlang.mihrab-welcome";
const WELCOME_SHOWN_KEY = "mihrab.web.welcome.shown";

const DOWNLOAD_URL = "https://sad-lang.org/mihrab/download/";

/**
 * نصُّ الحدّ — **موضعٌ واحد**. كان أوّلَ ما كُتِب مكرَّرًا في خمسة مُسجِّلات، ونسخةٌ
 * سادسةٌ تُضاف يومًا بصياغةٍ أخرى تجعل المنتَجَ يقول الشيءَ نفسَه بلسانَين.
 */
const COPY = {
  needsProcess: (what) =>
    `${what} يحتاج مُشغِّلًا على جهازك، ومحرابٌ هنا يعمل في متصفّحك بلا خادم — ` +
    "لا عمليّةَ خلف هذه الصفحة تُنفّذ شيئًا. نسخةُ المكتب تفعل ذلك.",
  needsDisk:
    "الاستيرادُ يقرأ ملفَّ إعداداتك على جهازك، ولا سبيلَ لصفحةٍ في المتصفّح إلى " +
    "مجلّدات نظامك. افعلها في نسخة المكتب — ثمّ انقل النتيجةَ إن شئت.",
  // ‏**«تراجَع» سؤالُه غيرُ سؤال «استورِد».** كانت الرسالتان واحدةً، فيُقال لمن
  // يطلب الإلغاءَ كيف يستورد — وهو لم يستورد هنا شيئًا أصلًا. وسؤالُه الحقيقيُّ
  // «أتراجعتُ أم لا؟»، فيُجاب عنه صراحةً.
  // ‏**ولا إحالةَ هنا ولا زرّ.** من ضغط «تراجَع» يريد جوابًا لا وجهة: سؤالُه
  // «أتراجعتُ أم لا؟»، وقد أُجيب. وذيلٌ يحيله إلى نسخة المكتب يعيده إلى السؤال
  // الذي أُجيب عنه للتوّ. والقاعدةُ في هذا الملفّ: من يذكر نسخةَ المكتب يدلّ
  // عليها بزرّ — فلا يُذكَر هنا أصلًا.
  noImportHere:
    "لا استيرادَ في نسخة المتصفّح، فلا شيءَ يُتراجَع عنه هنا — إعداداتُك في هذه " +
    "الصفحة تخصُّ متصفّحك وحدَه.",
  // ‏**والقالبُ لا يحتاج مُشغِّلًا** — قِيس: `newSadProject` في `extension.js` يستعمل
  // `workspace.fs` وحدَها، بلا `spawn` ولا `fs` عُقديّة. فسببُ «يحتاج مُشغِّلًا» كان
  // غيرَ صحيح، وسببٌ خاطئٌ أسوأُ من الصمت: من يعرف أنّ إنشاءَ مجلّدٍ لا يحتاج
  // مُشغِّلًا يستنتج أنّ المنتَجَ لا يعرف نفسَه. والمانعُ الحقيقيُّ ما **بداخل**
  // القالب: مَهمّةُ تشغيلٍ تنادي `sad-run`، وREADME يَعِد بـF5.
  templateNeedsRunner:
    "قالبُ مشروع ص يكتب مجلّدًا وملفًّا ومَهمّةَ تشغيل — والمَهمّةُ تحتاج مُشغِّلًا " +
    "على جهازك. فلا يُنشئه محرابٌ هنا: كان سيسلّمك مشروعًا لا يعمل. أنشئ ملفَّ " +
    "«.ص» جديدًا وابدأ الكتابة، أو خذ القالبَ كاملًا من نسخة المكتب.",
  // ‏**ولا طرفيّةَ**: كان نصًّا حرفيًّا عند موضع الاستدعاء، والملفُّ نفسُه يقول إنّ
  // نصَّ الحدّ «موضعٌ واحد». استثناءٌ بلا تعليلٍ يُغري بالثاني.
  noTerminal:
    "لا طرفيّةَ في نسخة المتصفّح — لا عمليّةَ خلف هذه الصفحة تستضيف صدَفة، " +
    "فلا رسالةَ اتّجاهٍ لها. ونسخةُ المكتب فيها الطرفيّةُ ورسالتُها.",
  // ‏**والحدُّ يُقال ومعه المخرج** — وبسببه الصحيح. قيل أوّلًا «الخطُّ غيرُ متاحٍ في
  // المتصفّح»، والخطُّ يعمل أمام الزائر في اللحظة نفسِها (الورقةُ تجلبه بـ@font-face
  // من `out/vs/workbench/kawkab-mono.woff2`). والمانعُ مقيسٌ في مكانٍ آخر:
  // `print-command.js:16` يستورد `node:path` في **رأس** الملفّ، و`bundled-font.js`
  // يقرأ بـ`node:fs` — أي أنّ مسارَ التصدير مكتوبٌ بواجهات العقدة، لا أنّ الخطَّ
  // بعيد. وسببٌ خاطئٌ في منتَجٍ يقول «الغيابُ يُفهَم» أسوأُ من الصمت: من يرى الخطَّ
  // أمامه يستنتج أنّ المنتَجَ لا يعرف نفسَه.
  needsBundledFont:
    "تصديرُ الطباعة مكتوبٌ ليقرأ الخطَّ والقالبَ بواجهات نظام الملفّات على جهازك، " +
    "وهي غيرُ موجودةٍ في متصفّح. والخطُّ نفسُه يعمل هنا أمامك — الناقصُ مسارُ " +
    "التصدير لا الخطّ. ونسخةُ المكتب تصدّر الصفحةَ كاملةً.",
  noUpdater:
    "لا مُحدِّثَ في نسخة المتصفّح: الصفحةُ تحمل دائمًا آخرَ ما نُشِر — أعِد التحميل وحسب.",
  download: "افتح صفحةَ التنزيل",
  ok: "فهمت",
};

/**
 * يُسجِّل أمرًا **غيرَ متاحٍ هنا** برسالةٍ تقول الحدَّ والبديل.
 *
 * ولماذا `showInformationMessage` لا `showWarningMessage`: هذا ليس عطبًا ولا خطأً من
 * المستخدم — هو حدٌّ معلومٌ في منصّةٍ اختارها. والتحذيرُ يُلقي عليه لومًا لا يستحقّه.
 */
function unavailable(id, message, withDownload) {
  return vscode.commands.registerCommand(id, async () => {
    const buttons = withDownload ? [COPY.download, COPY.ok] : [COPY.ok];
    const pick = await vscode.window.showInformationMessage(message, ...buttons);
    if (pick === COPY.download) {
      await vscode.env.openExternal(vscode.Uri.parse(DOWNLOAD_URL));
    }
  });
}

/**
 * يقرأ ملفَّي بيانات المساعدة مرّةً واحدةً إلى الذاكرة.
 *
 * ‏`workspace.fs` غيرُ متزامنٍ و`HelpPanel.open()` متزامن — والقراءةُ عند **التنشيط**
 * تحلّ الاثنين بلا تغيير واجهةِ اللوحة على المكتب. وحجمُ الملفَّين معًا دون ‎40‎ ك.ب،
 * فالثمنُ لا يُقاس مقابل لوحةٍ تُفتَح فورَ طلبها.
 */
async function loadHelpData(context) {
  const cache = new Map();
  const dec = new TextDecoder("utf-8");
  for (const file of [GLOSSARY_FILE, KEYBINDINGS_FILE]) {
    try {
      const uri = vscode.Uri.joinPath(context.extensionUri, DATA_DIR, file);
      cache.set(file, dec.decode(await vscode.workspace.fs.readFile(uri)));
    } catch {
      // سقوطٌ لطيف: اللوحةُ نفسُها تقول «ملفّاتُ محرابٍ ناقصة» إن خلا الاثنان.
    }
  }
  return (file) => (cache.has(file) ? cache.get(file) : null);
}

/** يفتح جولةَ المتصفّح مرّةً واحدةً في العمر (وتُعاد المحاولةُ إن فشل الفتحُ عابرًا). */
async function maybeShowWelcome(context) {
  if (context.globalState.get(WELCOME_SHOWN_KEY)) return;
  const ext = context.extension;
  const fullId = (ext && ext.id ? ext.id : DEFAULT_EXTENSION_ID) +
    WALKTHROUGH_ID_SEP + WEB_WALKTHROUGH_LOCAL_ID;
  try {
    await vscode.commands.executeCommand(OPEN_WALKTHROUGH_CMD, fullId, false);
    await context.globalState.update(WELCOME_SHOWN_KEY, true);
  } catch {
    /* الجولةُ تحسينيّةٌ: فشلُها لا يُفشِل التنشيط ولا يُسجَّل معروضًا */
  }
}

function activate(context) {
  // ── ما يعمل هنا كما يعمل على المكتب، بالوحدات نفسِها ──────────────────────
  const bidiMarkers = new bidiDecorate.BidiMarkerDecorator(vscode);
  const helpPanel = new HelpPanel(vscode, context);
  const dfNotice = activateDiffNotice(vscode, context.globalState);

  context.subscriptions.push(
    bidiMarkers,
    helpPanel,
    dfNotice,
    vscode.commands.registerCommand(RESET_UNICODE_CMD,
      () => unicodeGuard.resetCommand(vscode, context.globalState)),
    vscode.commands.registerCommand(REMOVE_BIDI_CMD,
      (uri, range) => bidiGuard.removeCommand(vscode, uri, range)),
    vscode.commands.registerCommand(TOGGLE_BIDI_MARKERS_CMD, () => bidiMarkers.toggle()),
    vscode.commands.registerCommand(OPEN_HELP_CMD, () => helpPanel.open()),
    vscode.commands.registerCommand(COPY_SAFE_CMD, () => clipboard.copyForSharing(vscode)),
    vscode.commands.registerCommand(STRIP_ISO_CMD, () => clipboard.stripIsolatesCommand(vscode)),
    vscode.commands.registerCommand(SHOW_DIFF_NOTICE_CMD, () => dfNotice.showAgain()),
    // المُحدِّدُ مشتقٌّ من المخطّطات التي يمسحها الحارسُ فعلًا — و`untitled` من بينها،
    // وهو أوّلُ ما يُلصَق فيه من الشابكة، أي أعلى لحظاتِ الخطر في المتصفّح خاصّةً.
    vscode.languages.registerCodeActionsProvider(
      [...bidiGuard.SCANNED_SCHEMES].map((scheme) => ({ scheme })),
      new bidiGuard.BidiCodeActionProvider(vscode),
      { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] }
    )
  );

  new bidiGuard.BidiGuard(vscode, context);
  activateNameGuard(vscode, context);
  clipboard.activatePasteNotice(vscode, context, {
    removeCommand: REMOVE_BIDI_CMD,
    showProblemsCommand: SHOW_PROBLEMS_CMD,
  });

  // ── وما لا يعمل: يُسجَّل ليقول لماذا، لا ليُترَك يقول «أمرٌ غيرُ معروف» ──────
  context.subscriptions.push(
    unavailable("mihrab.runSadFile", COPY.needsProcess("تشغيلُ ملفّ ص"), true),
    unavailable("mihrab.buildSadFile", COPY.needsProcess("بناءُ ملفّ ص"), true),
    unavailable("mihrab.checkSadFile", COPY.needsProcess("فحصُ ملفّ ص"), true),
    unavailable("mihrab.newSadProject", COPY.templateNeedsRunner, true),
    unavailable("mihrab.importVSCodeSettings", COPY.needsDisk, true),
    unavailable("mihrab.undoVSCodeImport", COPY.noImportHere, false),
    unavailable("mihrab.exportForPrint", COPY.needsBundledFont, true),
    unavailable("mihrab.checkForUpdate", COPY.noUpdater, false),
    // شارةُ الطرفيّة: لا طرفيّةَ في هذا البناء أصلًا (‏م-٢٩)، فرسالةُ اتّجاهها بلا موضوع.
    // ومن يطلب رسالةَ اتّجاه الطرفيّة يريد الطرفيّة — فالزرُّ في محلّه.
    unavailable("mihrab.showTerminalDirectionNotice", COPY.noTerminal, true)
  );

  // بياناتُ المساعدة تُجلَب بعد التسجيل: اللوحةُ تعمل متى فُتِحت، والجلبُ لا يؤخّر التنشيط.
  void loadHelpData(context).then((read) => { helpPanel.read = read; }).catch(() => {});

  void unicodeGuard.maybeWarn(vscode, context.globalState).catch(() => {});
  void maybeShowWelcome(context).catch(() => {});
}

function deactivate() {}

module.exports = { activate, deactivate, COPY };
