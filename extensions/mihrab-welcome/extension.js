// @ts-check
"use strict";
// امتداد ترحيب محراب (الطبقة 1) — أمرا الإعداد الأوّل:
//   • mihrab.newSadProject — ينشئ مجلّد مشروع ص بقالب حيّ مشروح بالعربية (الفكرة أ-٢).
//   • mihrab.runSadFile     — يشغّل ملفّ ص الحاليّ عبر أدوات ص (sad-run) في لوحة مخرجات عربيّة (bidi صحيح، spawn بلا صدفة). [AR-01]
// كلّ نصّ ظاهر للمستخدم ثابت مسمّى في COPY (نسخة عربيّة-أوّلًا = بيانات واجهة، استثناء
// مقبول لقاعدة منع السلاسل الحرفيّة، متّسق مع قرار جملة الترحيب في patch_welcome_rtl.py).

const vscode = require("vscode");
const path = require("path");
const { SadDiagnostics } = require("./diagnostics.js");
const { SadOutputPanel, ACTION_RUN, ACTION_BUILD } = require("./output-panel.js");
const { resolveBundledTool, probeTool } = require("./tool-resolve.js");
const unicodeGuard = require("./unicode-guard.js");
const bidiGuard = require("./bidi-guard.js");
const fontProbe = require("./font-probe.js");
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

// اسم أداتَي تشغيل/بناء ص (مصدر حقيقة واحد داخل هذا الامتداد). sad-run يفسّر ويشغّل مباشرةً؛
// sad-build يترجم إلى تنفيذيّ فقط (لا يشغّل) — «ابنِ» [SAD-04].
const SAD_RUN = "sad-run";
const SAD_BUILD = "sad-build";
// وسيط مخرَج الترجمة في sad-build: «sad-build <ملفّ> -o <مخرَج>» (راجع tools/build).
const BUILD_OUT_FLAG = "-o";
// معرّف الجولة المحلّيّ (id في contributes.walkthroughs)؛ المعرّف الكامل يُشتَقّ وقت
// التشغيل من context.extension.id (publisher.name) كي لا ينكسر لو تغيّرت الهوية. [M4]
const WALKTHROUGH_LOCAL_ID = "mihrab.gettingStarted";
const WALKTHROUGH_ID_SEP = "#";
// مفتاح حالة عامّة: هل عُرِضت جولة الترحيب مرّة على هذا الملفّ الشخصيّ؟ (تُفتح مرّة واحدة).
const WELCOME_SHOWN_KEY = "mihrab.welcome.shown";
// معرّف لغة ص (يطابق contributes.languages في sad-lang) وامتدادها (حرف الصاد).
const SAD_LANG_ID = "sad";
const SAD_EXT = ".ص";
// كلمتا «دالة رئيسية» المفتاحيّتان (تعكسان KEYWORD_FUNCTION/KEYWORD_MAIN في language-truth؛ النحو
// والمقتطفات مرآتها المولَّدة). تُستعملان لكشف نقطة الدخول وعرض عدسات الكود فوقها. [SAD-04]
const SAD_KW_FUNCTION = "دالة";
const SAD_KW_MAIN = "رئيسية";
// نمط سطر تصريح الدالّة الرئيسيّة «دالة [نوع] رئيسية(» — نوع الإرجاع اختياريّ قبل الاسم (grammar).
const MAIN_FN_RE = new RegExp("(?:^|\\s)" + SAD_KW_FUNCTION + "\\s+(?:\\S+\\s+)?" + SAD_KW_MAIN + "\\s*\\(");
// اسم المشروع الافتراضيّ واسم الملفّ الرئيس والمجلّدات.
const DEFAULT_PROJECT_NAME = "مشروع-ص";
const MAIN_FILE = "مرحبا" + SAD_EXT;
const README_FILE = "اقرأني.md";
const VSCODE_DIR = ".vscode";
const TASKS_FILE = "tasks.json";
const RUN_TASK_LABEL = "تشغيل برنامج ص";
const DOCS_URL = "https://github.com/sadlang/s-programming-language";
// معرّفا أمرَي هذا الامتداد (مصدر حقيقة واحد؛ يطابقان contributes.commands في package.json).
const NEW_PROJECT_CMD = "mihrab.newSadProject";
const RUN_FILE_CMD = "mihrab.runSadFile";
// أمر فحص ملفّ ص الحاليّ يدويًّا (يكمّل الفحص التلقائيّ عند الحفظ). [SAD-02]
const CHECK_FILE_CMD = "mihrab.checkSadFile";
// أمر بناء (ترجمة) ملفّ ص الحاليّ عبر sad-build. [SAD-04]
const BUILD_FILE_CMD = "mihrab.buildSadFile";
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
const RELEASES_URL = "https://sad-lang.org/mihrab/dl/releases.json";
const DOWNLOAD_URL = "https://sad-lang.org/mihrab/download/";
// مهلةُ جلبِ المانيفست: خبرٌ تحسينيٌّ لا يُبطئ الإقلاعَ ولا ينتظر شبكةً متعثّرة.
const RELEASES_TIMEOUT_MS = 8000;
// عدّادُ الجلسات، وأقلُّ جلسةٍ يُطلَب فيها إذنُ فحص الإصدارات (لا في أوّل إقلاع).
const SESSIONS_KEY = "mihrab.sessions";
const MIN_SESSIONS_BEFORE_ASK = 2;
// أوامر النواة المدمجة المُستدعاة (لا سلاسل حرفيّة موضعيّة — أسوة بـOPEN_WALKTHROUGH_CMD).
const OPEN_FOLDER_CMD = "vscode.openFolder";
const OPEN_CMD = "vscode.open";
// معرّف الامتداد الاحتياطيّ إن غابت هوية التشغيل (publisher.name — يطابق package.json).
const DEFAULT_EXTENSION_ID = "sadlang.mihrab-welcome";
// حدّ نتائج البحث عن ملفّات ص في مساحة العمل (أداء على مساحة كبيرة) + استبعاد التبعيّات.
const SAD_SEARCH_MAX = 50;
const NODE_MODULES_GLOB = "**/node_modules/**";
// [TY-03] مهلةُ إعادة قياس الخطّ بعد ضبطه. إن مضت بلا قياسٍ **لا يُدَّعى نجاح** — تُعرَض
// رسالةُ «كُتِب ولم يُتحقَّق». صمتُ اللوحة ليس برهانَ أثر.
const REMEASURE_TIMEOUT_MS = 3000;

// نصوص الواجهة (عربيّة-أوّلًا).
const COPY = {
  pickParentTitle: "اختر المجلّد الذي سيُنشأ فيه مشروع ص",
  pickParentButton: "أنشئ هنا",
  namePrompt: "اسم مشروع ص الجديد",
  namePlaceholder: DEFAULT_PROJECT_NAME,
  nameEmpty: "الرجاء إدخال اسم للمشروع.",
  nameInvalidChars: "الاسم يحتوي محارف غير صالحة لاسم مجلّد (مثل \\ / : * ? \" < > | أو محارف تحكّم).",
  nameDotNames: "الاسم «.» أو «..» غير صالح لمجلّد مشروع.",
  nameTrailingDotSpace: "لا يصحّ أن ينتهي الاسم بنقطة أو مسافة (يُسبِّب مشكلات على ويندوز).",
  nameReserved: "هذا اسم محجوز في ويندوز (مثل CON أو PRN أو COM1) — اختر اسمًا آخر.",
  nameTooLong: "الاسم طويل جدًّا (أقصى 255 محرفًا).",
  existsDirPrompt: (n) => `يوجد مجلّد باسم «${n}» في هذا الموضع — ماذا تريد؟`,
  existsFilePrompt: (n) => `يوجد ملفّ (لا مجلّد) باسم «${n}» في هذا الموضع — ماذا تريد؟`,
  existsOverwrite: "الكتابة فوق الملفّات الأساسيّة",
  existsNewCopy: "إنشاء نسخة باسم آخر",
  createdInfo: (n) => `أُنشئ مشروع «${n}». بالتوفيق في أوّل برنامج!`,
  openFolder: "افتح المجلّد",
  createFailed: (e) => `تعذّر إنشاء المشروع: ${e}`,
  noEditor: "لا يوجد محرّر نشط — افتح ملفّ ص أوّلًا كي تشغّله.",
  sadFileAmbiguous: `وُجدت عدّة ملفّات ص — افتح الملفّ الذي تريد تشغيله أوّلًا (لا يوجد ‹${MAIN_FILE}› لأختاره تلقائيًّا).`,
  notSadFile: `الملفّ الحاليّ ليس ملفّ ص (‹${SAD_EXT}›).`,
  notOnDisk: "احفظ الملفّ على القرص أوّلًا كي يمكن تشغيله.",
  saveCancelled: "أُلغي الحفظ — لم يُشغَّل الملفّ.",
  toolMissingTitle: `لم يُعثَر على أداة تشغيل ص (‹${SAD_RUN}›) في مسار النظام.`,
  buildToolMissingTitle: `لم يُعثَر على أداة بناء ص (‹${SAD_BUILD}›) في مسار النظام.`,
  toolMissingHint: "ثبّت أدوات ص وأضِفها إلى PATH ثمّ أعِد المحاولة.",
  toolMissingLearn: "كيف أثبّت أدوات ص؟",
  // عناوين عدسات الكود (CodeLens) فوق دالّة رئيسية [SAD-04].
  lensRun: "▶ شغّل",
  lensBuild: "🔨 ابنِ",
};

// قالب البرنامج الحيّ: برنامج ص صغير يعمل فورًا، مشروح بالعربية سطرًا سطرًا.
const TEMPLATE_MAIN =
  "# 👋 أهلًا بك في محراب! هذا أوّل برنامج لك بلغة ص.\n" +
  "# كلّ سطر يبدأ بعلامة # هو تعليق (شرح) لا يُنفِّذه الحاسوب.\n" +
  "\n" +
  "اطبع(\"مرحبا يا عالم\")\n" +
  "\n" +
  "# جرّب الآن: غيّر النصّ بين علامتَي الاقتباس ثمّ شغّل البرنامج من جديد\n" +
  "# (من الجولة، أو بأمر «محراب: شغّل ملفّ ص الحاليّ»).\n";

/**
 * يبني نصّ اقرأني بعنوان يطابق اسم المشروع الفعليّ (لا الاسم الافتراضيّ). ملاحظة المهمّة تتبع
 * حالة المُشغّل: محلول لمسار مطلق (runnerReady=صحيح، مدمجًا أو من PATH) ⇒ تعمل مباشرةً؛
 * وإلا اسم مجرّد ⇒ تتطلّب توفّره على PATH.
 */
function buildReadme(projectName, runnerReady) {
  // ملاحظة المهمّة تُشغَّل في الطرفيّة (xterm لا يدعم bidi فقد لا تُعرَض العربيّة باتّجاهها الصحيح)؛
  // لذا نقدّم أمر التشغيل (لوحة ص العربيّة) أوّلًا كالمسار الموصى به، والمهمّة بديلٌ طرفيّ صريح. [تدقيق #1]
  const taskNote = runnerReady
    ? "- أو المهمّة **«" + RUN_TASK_LABEL + "»** — تُشغَّل في الطرفيّة (قد لا تُعرَض العربيّة باتّجاهها الصحيح).\n"
    : "- أو المهمّة **«" + RUN_TASK_LABEL + "»** — تُشغَّل في الطرفيّة، وتتطلّب تثبيت أدوات ص ‹" + SAD_RUN + "› على PATH.\n";
  return (
    "# " + projectName + "\n\n" +
    "أوّل مشروع لك بلغة ص داخل محراب.\n\n" +
    "## التشغيل\n\n" +
    "- افتح ‹" + MAIN_FILE + "› ثمّ نفّذ أمر **«محراب: شغّل ملفّ ص الحاليّ»** — تظهر المخرجات في لوحة مخرجات محراب (باتّجاهها الصحيح).\n" +
    taskNote
  );
}

// مهمّة تشغيل قياسيّة (آليّة VSCode). الأمر = المُشغّل المحلول (runCommand): الثنائيّ المدمج
// بمساره المطلق حين يُشحَن (تعمل المهمّة فورًا كزرّ التشغيل، بلا تثبيت)، وإلا اسم PATH المجرّد
// (منقول بين الأجهزة). يُبنى وقت الإنشاء بالقيمة نفسها التي يستعملها الأمر كي لا يتباعد
// مسارا التشغيل (الأمر مقابل المهمّة) — كان التباعد يُفشِل المهمّة رغم توفّر المدمج.
// مقايضة مقبولة لهدف P0: المسار المطلق المخبوز يبيت إن نُقل المشروع لجهاز آخر أو تغيّر مسار
// تثبيت محراب؛ لكنّ جولة المبتدئ على جهازه تعمل فورًا — وهو الأهمّ هنا.
function buildTasksJson(runCommand) {
  return {
    version: "2.0.0",
    tasks: [
      {
        label: RUN_TASK_LABEL,
        type: "process",
        command: runCommand,
        args: ["${file}"],
        // ليست مهمّة البناء الافتراضيّة (لا group): كي لا يشغّلها Ctrl+Shift+B تلقائيًّا في الطرفيّة
        // (تشوّه العربيّة). المسار الموصى به للعربيّة الصحيحة = أمر «شغّل ملفّ ص» ⇒ لوحة ص. [تدقيق #1]
        problemMatcher: [],
      },
    ],
  };
}

const enc = new TextEncoder();

// محارف ممنوعة في أسماء المجلّدات: رموز نظام الملفّات + محارف تحكّم C0/DEL/C1 +
// محارف التحكّم ثنائيّة الاتّجاه (LRM/RLM، تضمين/تجاوز/عزل الاتّجاه) — الأخيرة تُنتج
// اسمًا مخادعًا بصريًّا (spoofing) في سياق RTL فتُرفَض صراحةً.
// (نقاط الرموز بترميز \u صريح — لا محرف غير مرئيّ في الكود نفسه.)
const INVALID_NAME_RE = /[\\/:*?"<>|\x00-\x1f\x7f-\x9f\u200e\u200f\u202a-\u202e\u2066-\u2069]/;
// أقصى طول لاسم مدخل في معظم أنظمة الملفّات (بايت/محرف).
const MAX_NAME_LEN = 255;
// أسماء محجوزة على ويندوز (بلا/مع امتداد) — تُقارَن دون حساسية حالة.
const RESERVED_NAMES = new Set([
  "con", "prn", "aux", "nul",
  "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
  "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
]);

/** يتحقّق من صلاحيّة اسم المجلّد؛ يُرجع رسالة خطأ أو null. */
function validateProjectName(v) {
  const t = (v || "").trim();
  if (!t) return COPY.nameEmpty;
  if (t.length > MAX_NAME_LEN) return COPY.nameTooLong;
  if (t === "." || t === "..") return COPY.nameDotNames;
  if (INVALID_NAME_RE.test(t)) return COPY.nameInvalidChars;
  if (/[. ]$/.test(t)) return COPY.nameTrailingDotSpace;
  const stem = t.split(".")[0].toLowerCase();
  if (RESERVED_NAMES.has(stem)) return COPY.nameReserved;
  return null;
}

/** يكتب ملفًّا نصّيًّا عبر workspace.fs (يدعم البعيد أيضًا). */
async function writeText(uri, text) {
  await vscode.workspace.fs.writeFile(uri, enc.encode(text));
}

/** يُرجع نوع الملفّ عند المسار (vscode.FileType) أو null إن لم يوجد. */
async function statType(uri) {
  try {
    const s = await vscode.workspace.fs.stat(uri);
    return s.type;
  } catch {
    return null;
  }
}

/** يختار مجلّدًا فريدًا: name، ثمّ name-2، name-3… لتفادي الدوس. */
async function uniqueChild(parentUri, name) {
  let candidate = vscode.Uri.joinPath(parentUri, name);
  let i = 2;
  while ((await statType(candidate)) !== null) {
    candidate = vscode.Uri.joinPath(parentUri, `${name}-${i}`);
    i += 1;
  }
  return candidate;
}

/** أمر: مشروع ص جديد بقالب حيّ. */
async function newSadProject() {
  // (١) موضع الإنشاء: نطلبه دائمًا من المستخدم (الافتراضيّ = أوّل مجلّد عمل إن وُجد).
  const folders = vscode.workspace.workspaceFolders;
  const picked = await vscode.window.showOpenDialog({
    canSelectFolders: true,
    canSelectFiles: false,
    canSelectMany: false,
    openLabel: COPY.pickParentButton,
    title: COPY.pickParentTitle,
    defaultUri: folders && folders.length ? folders[0].uri : undefined,
  });
  if (!picked || !picked.length) return; // ألغى المستخدم
  const parentUri = picked[0];

  // (٢) اسم المشروع، مع تحقّق صارم من المحارف والأسماء المحجوزة.
  const name = await vscode.window.showInputBox({
    prompt: COPY.namePrompt,
    placeHolder: COPY.namePlaceholder,
    value: DEFAULT_PROJECT_NAME,
    validateInput: validateProjectName,
  });
  if (name === undefined) return; // ألغى المستخدم
  const projectName = name.trim();

  // (٣) الحالة الحديّة (أ-٢): مسار بالاسم نفسه موجود ⇒ لا تَدُس؛ اسأل بلطف (مع تمييز
  //     المجلّد من الملفّ كي لا نَعِد باستبدال يفشل على مسار ملفّ).
  let targetUri = vscode.Uri.joinPath(parentUri, projectName);
  const existing = await statType(targetUri);
  if (existing !== null) {
    const isDir = (existing & vscode.FileType.Directory) !== 0;
    const prompt = isDir ? COPY.existsDirPrompt(projectName) : COPY.existsFilePrompt(projectName);
    // على ملفّ قائم: الاستبدال داخله متعذّر ⇒ نعرض «نسخة باسم آخر» فقط.
    const options = isDir ? [COPY.existsOverwrite, COPY.existsNewCopy] : [COPY.existsNewCopy];
    const choice = await vscode.window.showWarningMessage(prompt, { modal: true }, ...options);
    if (choice === COPY.existsNewCopy) {
      targetUri = await uniqueChild(parentUri, projectName);
    } else if (choice !== COPY.existsOverwrite) {
      return; // إلغاء أو إغلاق الحوار
    }
    // الكتابة فوق: نكتب الملفّات الأساسيّة داخل المجلّد نفسه (لا نحذف ما عداها).
  }

  try {
    // (٤) أنشئ المجلّد والملفّات.
    await vscode.workspace.fs.createDirectory(targetUri);
    await vscode.workspace.fs.createDirectory(vscode.Uri.joinPath(targetUri, VSCODE_DIR));
    const mainUri = vscode.Uri.joinPath(targetUri, MAIN_FILE);
    await writeText(mainUri, TEMPLATE_MAIN);
    // مسار مطلق للمُشغّل ⇒ محلول (مدمج أو من PATH؛ تعمل المهمّة فورًا)؛ اسم مجرّد ⇒ يتطلّب PATH.
    const runnerReady = path.isAbsolute(sadRunCmd);
    await writeText(vscode.Uri.joinPath(targetUri, README_FILE), buildReadme(projectName, runnerReady));
    await writeText(
      vscode.Uri.joinPath(targetUri, VSCODE_DIR, TASKS_FILE),
      JSON.stringify(buildTasksJson(sadRunCmd), null, 2) + "\n"
    );

    // (٥) افتح الملفّ الرئيس، واعرض دعوة لفتح المجلّد كمساحة عمل.
    const doc = await vscode.workspace.openTextDocument(mainUri);
    await vscode.window.showTextDocument(doc, { preview: false });
    const action = await vscode.window.showInformationMessage(COPY.createdInfo(projectName), COPY.openFolder);
    if (action === COPY.openFolder) {
      await vscode.commands.executeCommand(OPEN_FOLDER_CMD, targetUri, { forceNewWindow: false });
    }
  } catch (err) {
    vscode.window.showErrorMessage(COPY.createFailed(String(err && err.message ? err.message : err)));
  }
}

// أمرا التشغيل/البناء المحلولان: يُضبَطان عند التنشيط إلى الثنائيّ المدمج (إن وُجِد) وإلا اسم PATH.
let sadRunCmd = SAD_RUN;
let sadBuildCmd = SAD_BUILD;

// لوحة المخرجات العربيّة [AR-01]: تُنشأ عند التنشيط وتُبثّ إليها مخرجات sad-run بـbidi صحيح.
/** @type {import("./output-panel.js").SadOutputPanel} */
let sadOutput;

// اسم ثنائيّ ص المدمج حسب المنصّة (البناء ويندوزيّ ويحزم .exe؛ نطابقه هنا). [L1]
const SAD_RUN_EXE = process.platform === "win32" ? SAD_RUN + ".exe" : SAD_RUN;
const SAD_BUILD_EXE = process.platform === "win32" ? SAD_BUILD + ".exe" : SAD_BUILD;

// حلّ المسار (المدمج ثمّ PATH) وفحص التوفّر مشتركان في tool-resolve.js مع جسر التشخيص (sad-check)
// كي لا يتباعد سلوك أدوات ص المتطابقة الدور. هنا أغلفة رفيعة تحقن اسم الأداة وترقّي المتغيّر. [تدقيق #2]
/** يحلّ sad-run/sad-build المدمج ثمّ PATH (ثوابت مسمّاة، يحرسها L0). */
function resolveSadRun(context) {
  return resolveBundledTool(context, SAD_RUN_EXE, SAD_RUN);
}
function resolveSadBuild(context) {
  return resolveBundledTool(context, SAD_BUILD_EXE, SAD_BUILD);
}

/** يتحقّق توفّر sad-run ويرقّي sadRunCmd إلى المسار المحلول عند النجاح. */
async function isSadRunAvailable() {
  const resolved = await probeTool(sadRunCmd);
  if (resolved) sadRunCmd = resolved;
  return !!resolved;
}
/** يتحقّق توفّر sad-build ويرقّي sadBuildCmd إلى المسار المحلول عند النجاح. */
async function isSadBuildAvailable() {
  const resolved = await probeTool(sadBuildCmd);
  if (resolved) sadBuildCmd = resolved;
  return !!resolved;
}

/** يتحقّق أنّ المستند ملفّ ص حقيقيّ على القرص؛ يُرجع رسالة خطأ مناسبة أو null (صالح). */
function sadDocError(doc) {
  // كشف اللغة بالمعرّف (أدقّ من الامتداد)، مع الامتداد احتياطًا.
  if (doc.languageId !== SAD_LANG_ID && !doc.fileName.endsWith(SAD_EXT)) return COPY.notSadFile;
  // يجب أن يكون ملفًّا حقيقيًّا على القرص (لا untitled ولا مخطّط بعيد/افتراضيّ).
  if (doc.isUntitled || doc.uri.scheme !== "file") return COPY.notOnDisk;
  return null;
}

/**
 * يبحث في مساحة العمل عن ملفّ ص لتشغيله حين لا محرّر ص نشط (مثلًا لوحة الجولة/الترحيب مركَّزة).
 * مرحلتان: (١) بحث مستهدف عن الملفّ الرئيس (مرحبا.ص) — لا يفوته حدّ النتائج في مساحة كبيرة؛
 * (٢) وإلا كلّ ملفّات ص: الوحيد ⇒ شغّله، التعدّد ⇒ التباس (لا نخمّن). يُرجع {uri} أو
 * {ambiguous:true} (تعدّد بلا رئيس) أو null (لا ملفّ ص). يتجاهل node_modules ويحدّ العدد.
 */
async function findWorkspaceSadFile() {
  const mains = await vscode.workspace.findFiles("**/" + MAIN_FILE, NODE_MODULES_GLOB, 1);
  if (mains.length) return { uri: mains[0] };
  const uris = await vscode.workspace.findFiles("**/*" + SAD_EXT, NODE_MODULES_GLOB, SAD_SEARCH_MAX);
  if (uris.length === 1) return { uri: uris[0] };
  if (uris.length > 1) return { ambiguous: true };
  return null;
}

/**
 * يحلّ مستند ص للتشغيل. المحرّر النشط إن كان ملفّ ص (السلوك الصارم يبقى لمحرّر غير-ص نشط).
 * وإلا — لا محرّر نصّ نشط، وهو حال زرّ التشغيل داخل لوحة الجولة (تحتلّ المحرّر فلا نصّ نشط):
 * يجرّب محرّرًا ظاهرًا بجانبها ثمّ ملفّ مساحة العمل الرئيس ويفتحه بجانب الجولة. {doc} أو {error}.
 */
async function resolveSadDoc() {
  const active = vscode.window.activeTextEditor;
  if (active) {
    const err = sadDocError(active.document);
    return err ? { error: err } : { doc: active.document };
  }
  // ملفّ ص ظاهر في مجموعة أخرى (مفتوح بجانب الجولة) ⇒ شغّله دون فتح جديد.
  const visibleSad = vscode.window.visibleTextEditors.find((e) => sadDocError(e.document) === null);
  if (visibleSad) return { doc: visibleSad.document };
  // وإلا: ملفّ ص في مساحة العمل (مرحبا.ص أو الوحيد) — افتحه بجانب الجولة ثمّ شغّله.
  const found = await findWorkspaceSadFile();
  if (!found) return { error: COPY.noEditor }; // لا ملفّ ص إطلاقًا
  if (found.ambiguous) return { error: COPY.sadFileAmbiguous }; // تعدّد بلا رئيس ⇒ رسالة صادقة
  const doc = await vscode.workspace.openTextDocument(found.uri);
  await vscode.window.showTextDocument(doc, { viewColumn: vscode.ViewColumn.Beside, preview: false });
  return { doc };
}

/**
 * يحلّ مستند ص من وسيط الأمر (Uri تمرّره عدسة الكود لوثيقتها) إن وُجِد — فيعمل الأمر على تلك
 * الوثيقة تحديدًا لا المحرّر النشط [تدقيق #5] — وإلا المسار المعتاد (النشط/الجولة). {doc} أو {error}.
 */
async function resolveSadDocArg(arg) {
  if (arg && arg.scheme === "file") {
    const doc = await vscode.workspace.openTextDocument(arg);
    const err = sadDocError(doc);
    return err ? { error: err } : { doc };
  }
  return resolveSadDoc();
}

/** أمر: شغّل ملفّ ص (وثيقة العدسة إن مُرِّرت، أو النشط/الرئيس) عبر sad-run في لوحة المخرجات العربيّة (bidi صحيح، spawn بلا صدفة فلا حقن). [AR-01] */
async function runSadFile(arg) {
  const resolved = await resolveSadDocArg(arg);
  if (resolved.error) {
    vscode.window.showWarningMessage(resolved.error);
    return;
  }
  const doc = resolved.doc;
  if (!(await doc.save())) {
    vscode.window.showWarningMessage(COPY.saveCancelled);
    return;
  }

  if (!(await isSadRunAvailable())) {
    const pick = await vscode.window.showErrorMessage(
      COPY.toolMissingTitle + " " + COPY.toolMissingHint,
      COPY.toolMissingLearn
    );
    if (pick === COPY.toolMissingLearn) {
      vscode.commands.executeCommand(OPEN_CMD, vscode.Uri.parse(DOCS_URL));
    }
    return;
  }

  // AR-01: بدل مهمّة الطرفيّة (xterm بلا bidi ⇒ يشوّه مخرجات ص العربيّة)، نبثّ المخرجات إلى
  // لوحة مخرجات عربيّة واعية بالاتّجاه (كلّ سطر يأخذ اتّجاهه من محتواه). العربيّة تُقرأ صحيحةً.
  // المسار المحلول (المدمج ثمّ PATH) والوسيط مفصولان (spawn بلا صدفة، فلا حقن)، ومجلّد العمل =
  // مجلّد الملفّ كي تُحلّ المسارات النسبيّة داخل برنامج ص صوابًا. [M5]
  // نصُّ الوثيقة يُمرَّر لمسحٍ ساكنٍ عن «اقرأ» [م٧]: اللوحةُ لا تستقبل دخلًا، فإن طلبه
  // البرنامجُ رافَقَ سطرَ الخروجِ سطرُ نظامٍ يقول ذلك — لئلّا يُقرأ «انتهى بنجاح» حكمًا عليه.
  sadOutput.run(
    sadRunCmd,
    [doc.fileName],
    path.dirname(doc.fileName),
    path.basename(doc.fileName),
    ACTION_RUN,
    doc.getText()
  );
}

/** يشتقّ مسار المخرَج التنفيذيّ من ملفّ المصدر: بجواره باسمه دون لاحقة ص (sad-build يضيف لاحقة المنصّة). */
function outputPath(file) {
  return path.join(path.dirname(file), path.basename(file, path.extname(file)));
}

/** أمر: ابنِ (ترجِم) ملفّ ص (وثيقة العدسة إن مُرِّرت، أو النشط/الرئيس) عبر sad-build إلى تنفيذيّ (لا يشغّل)، وتُبثّ نتيجة الترجمة للّوحة. [SAD-04] */
async function buildSadFile(arg) {
  const resolved = await resolveSadDocArg(arg);
  if (resolved.error) {
    vscode.window.showWarningMessage(resolved.error);
    return;
  }
  const doc = resolved.doc;
  if (!(await doc.save())) {
    vscode.window.showWarningMessage(COPY.saveCancelled);
    return;
  }

  if (!(await isSadBuildAvailable())) {
    const pick = await vscode.window.showErrorMessage(
      COPY.buildToolMissingTitle + " " + COPY.toolMissingHint,
      COPY.toolMissingLearn
    );
    if (pick === COPY.toolMissingLearn) {
      vscode.commands.executeCommand(OPEN_CMD, vscode.Uri.parse(DOCS_URL));
    }
    return;
  }

  // sad-build يترجم فقط (لا يشغّل): «sad-build <ملفّ> -o <مخرَج>». المسار المحلول والوسائط مفصولة
  // (spawn بلا صدفة، فلا حقن)، ومجلّد العمل = مجلّد الملفّ. نتيجة الترجمة (نجاح/أخطاء) تظهر باللوحة.
  sadOutput.run(
    sadBuildCmd,
    [doc.fileName, BUILD_OUT_FLAG, outputPath(doc.fileName)],
    path.dirname(doc.fileName),
    path.basename(doc.fileName),
    ACTION_BUILD
  );
}

/**
 * موفّر عدسات كود [SAD-04]: يعرض فوق «دالة رئيسية» عدستَي «شغّل» و«ابنِ» (زرّا تشغيل/بناء في
 * السياق). منطق كشف نقيّ (MAIN_FN_RE)؛ الأمران المرتبطان يعملان على المحرّر النشط (نفس مسار
 * الأوامر). يكتفي بأوّل نقطة دخول (دالّة رئيسية واحدة للبرنامج).
 */
class SadMainCodeLensProvider {
  /** @param {vscode.TextDocument} document @returns {vscode.CodeLens[]} */
  provideCodeLenses(document) {
    const lenses = [];
    // نمرّر uri وثيقة العدسة كوسيط: الأمر يشغّل/يبني هذه الوثيقة تحديدًا لا المحرّر النشط
    // (يصمد في مجموعات المحرّر المنقسمة حيث قد يختلفان). [تدقيق #5]
    const arg = [document.uri];
    for (let i = 0; i < document.lineCount; i++) {
      if (MAIN_FN_RE.test(document.lineAt(i).text)) {
        const range = new vscode.Range(i, 0, i, 0);
        lenses.push(new vscode.CodeLens(range, { title: COPY.lensRun, command: RUN_FILE_CMD, arguments: arg }));
        lenses.push(new vscode.CodeLens(range, { title: COPY.lensBuild, command: BUILD_FILE_CMD, arguments: arg }));
        break; // نقطة دخول واحدة تكفي
      }
    }
    return lenses;
  }
}

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
  // حلّ مساري sad-run/sad-build مرّة واحدة عند التنشيط (المدمج أوّلًا ثمّ PATH).
  sadRunCmd = resolveSadRun(context);
  sadBuildCmd = resolveSadBuild(context);

  // جسر التشخيص [SAD-02]: يفحص ملفّ ص عند الحفظ (مهدّأ) وبأمر يدويّ عبر sad-check --json.
  // مُعامل ملفّ ص = مستند ص صالح على القرص (sadDocError == null): يمنع فحص ملفّات غير-ص/غير محفوظة.
  const sadDiag = new SadDiagnostics(context, {
    isSadFile: (doc) => !!doc && sadDocError(doc) === null,
  });

  // لوحة المخرجات العربيّة [AR-01]: وجهة تشغيل ملفّ ص (بديل الطرفيّة، bidi صحيح). نمرّر context
  // كي تقرأ الخطّ العربيّ المحزوم [AR-02] من media/ وتعرض المخرجات به عينه (webview معزول).
  sadOutput = new SadOutputPanel(context);
  // [TY-03] القياسُ يقع في اللوحة (حيث DOM وخطٌّ مُحلَّل)، والحكمُ في وحدةٍ نقيّةٍ تُختبَر.
  //
  // **والإنذارُ لا يقع لحظةَ القياس.** أوّلُ «شغّل» ناجحٍ هو أثمنُ ثانيةٍ في عمر المبتدئ
  // معنا — أوّلُ مرّةٍ يأمر فيها الحاسوبَ فيطيع — وإطارٌ أصفرُ فيها يُقرأ «برنامجي فيه خطأ»
  // لا «خطُّ الشاشة غير مثاليّ». وانكسارُ الأعمدة مشكلةُ **كتابةٍ** لا مشكلةُ تشغيل. فنقيس
  // صامتين، ونتكلّم عند أوّل تعديلٍ في ملفّ ص بعدها — حيث تصير الجملةُ قابلةً للتصديق لأنّه
  // أمام أعمدته. (الفرصةُ واحدةٌ للأبد، فلا تُحرَق في غير سياقها.)
  /** @type {{fontFamily:string, widths:Record<string,number>}|null} */
  let pendingFontMeasurement = null;
  /** @type {((m:*) => void)|null} مستقبِلُ قياسٍ لمرّةٍ واحدة (لإعادة القياس بعد الضبط). */
  let awaitingRemeasure = null;
  sadOutput.onFontProbe((m) => {
    if (awaitingRemeasure) {
      const fn = awaitingRemeasure;
      awaitingRemeasure = null;
      fn(m);
      return;
    }
    pendingFontMeasurement = m;
  });

  /** يعرض إنذارَ الخطّ مرّةً، في سياق الكتابة لا في لحظة أوّل تشغيل. */
  const flushFontWarning = () => {
    const m = pendingFontMeasurement;
    if (!m) return;
    pendingFontMeasurement = null;
    // مكدَّسُ الإصلاح يُقرَأ من افتراضنا لا يُكتَب حرفيًّا — مصدرُ حقيقةٍ واحدٌ في
    // `mihrab-shell`، فلا يقترح الإصلاحُ مكدَّسًا يخالف ما نشحنه.
    const info = vscode.workspace.getConfiguration().inspect(fontProbe.FONT_SETTING);
    void fontProbe
      .maybeWarnProportional(vscode, context.globalState, m, {
        bundledStack: info && info.defaultValue,
        inspect: info,
        // إعادةُ القياس **من السطح نفسِه**: نطلبها ونصبر لها بمهلة، فإن لم تأتِ لم نَدَّعِ.
        remeasure: () =>
          new Promise((resolve) => {
            const timer = setTimeout(() => {
              awaitingRemeasure = null;
              resolve(null);
            }, REMEASURE_TIMEOUT_MS);
            awaitingRemeasure = (mm) => {
              clearTimeout(timer);
              resolve(mm);
            };
            sadOutput.requestRemeasure();
          }),
      })
      .catch(() => {});
  };

  context.subscriptions.push(
    sadDiag,
    sadOutput,
    vscode.commands.registerCommand(NEW_PROJECT_CMD, newSadProject),
    vscode.commands.registerCommand(RUN_FILE_CMD, runSadFile),
    vscode.commands.registerCommand(BUILD_FILE_CMD, buildSadFile),
    vscode.commands.registerCommand(CHECK_FILE_CMD, () => {
      const ed = vscode.window.activeTextEditor;
      return sadDiag.checkNow(ed && ed.document);
    }),
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
    ),
    // عدسات كود «شغّل/ابنِ» فوق دالّة رئيسية في ملفّات ص [SAD-04].
    vscode.languages.registerCodeLensProvider(
      { language: SAD_LANG_ID, scheme: "file" },
      new SadMainCodeLensProvider()
    ),
    vscode.workspace.onDidSaveTextDocument((doc) => sadDiag.scheduleCheck(doc)),
    // [TY-03] لحظةُ الإنذار: أوّلُ تعديلٍ في ملفّ ص **بعد** أن قِسنا صامتين.
    vscode.workspace.onDidChangeTextDocument((e) => {
      if (e.document && e.document.languageId === SAD_LANG_ID) flushFontWarning();
    })
  );

  // افحص الملفّ النشط عند التنشيط (إن كان ملفّ ص محفوظًا) كي تظهر التشخيصات فورًا لا بعد أوّل حفظ.
  const activeEditor = vscode.window.activeTextEditor;
  if (activeEditor) sadDiag.scheduleCheck(activeEditor.document);

  // عند اكتمال الإقلاع (onStartupFinished) اعرض الجولة أوّل مرّة فقط (رفض الوعد مُبتلَع). [L5]
  void maybeShowWelcome(context).catch(() => {});

  // [AR-04] إنذارٌ عن إعدادٍ يُظلِّل افتراضَنا **بنطاق لغة** (الحالةُ الوحيدة التي تُنتِج
  // الإطارات)، مرّةً لكلّ حالةٍ لا في كلّ إقلاع.
  void unicodeGuard.maybeWarn(vscode, context.globalState).catch(() => {});

  // [BS-01] كاشفُ قلب الاتّجاه: يُنشأ بعد تسجيل الأمر كي يجد الإصلاحُ أمرَه مسجَّلًا، ويُسجِّل
  // نفسَه في subscriptions من مُنشِئه (كـSadDiagnostics).
  new bidiGuard.BidiGuard(vscode, context);

  // [BS-03] حارسُ أسماء الملفّات: يعمّم ما كان محصورًا في اسم المشروع على الإنشاء وإعادة
  // التسمية. لا حقَّ نقضٍ لدينا (المنبع لا يمنحه)، فالصدقُ كشفٌ فوريٌّ بإصلاحٍ بنقرة.
  activateNameGuard(vscode, context);

  // [DR-03] شارةُ الطرفيّة ورسالتُها: الحدُّ المنبعيُّ مرئيٌّ ومعالَجٌ لا صامت — ومعه أمرُ
  // إعادةِ إظهارٍ كي لا يصير الإخفاءُ بابًا بلا مقبض (درسُ «أزِل الإطارات الصفراء»).
  const termNotice = activateTerminalNotice(vscode, context.globalState, RUN_FILE_CMD);
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

// دوالّ مُصدَّرة للاختبار الوحدويّ: validateProjectName وsadDocError نقيّتان (بلا vscode)،
// وfindWorkspaceSadFile/resolveSadDoc تُختبَران ببديل vscode متحكَّم (Module._load). COPY مُصدَّر
// كي تقابل الاختبارات رسائل الخطأ العائدة بمصدرها لا بحرفيّة مكرَّرة.
module.exports = {
  activate,
  deactivate,
  validateProjectName,
  sadDocError,
  findWorkspaceSadFile,
  resolveSadDoc,
  outputPath,
  SadMainCodeLensProvider,
  MAIN_FN_RE,
  COPY,
};
