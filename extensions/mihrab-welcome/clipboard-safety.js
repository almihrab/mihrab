"use strict";
/**
 * أمانةُ الحافظة — الخارجُ والداخلُ ‏[BS-04].
 *
 * ## بابان لا باب
 * ‏`BS-01` يشخّص ما **في المستند**. والحافظةُ بابان لا يمرّان به:
 *
 *   ‏(١) **الخارج.** شيفرةٌ عربيّةٌ تُنسَخ إلى متصفّحٍ أو محادثةٍ أو بريد. وهناك لا محرّرَ
 *       يعزل ولا ورقةَ أنماطٍ تُصلِح: نصٌّ عارٍ تحكمه خوارزميّةُ UAX #9 وحدَها، وسياقُ
 *       الفقرة المحيطة (لاتينيّةٌ غالبًا) يقلب ترتيبَ ما حول المقطع العربيّ. فالسطرُ الذي
 *       نُسِخ صحيحًا يُلصَق بترتيبٍ آخَر — **والناسخُ لا يرى ذلك أبدًا**، لأنّه يرى محرّرَه.
 *
 *   ‏(٢) **الداخل.** اللصقُ لحظةُ **نيّةٍ**: المستخدمُ يعرف أنّه جلب نصًّا من مكانٍ لا
 *       يثق به. والتشخيصُ وحدَه يظهر في المسطرة وقد لا يُنظَر إليه — أمّا لحظةُ اللصق
 *       فأنسبُ لحظةٍ يُسأل فيها.
 *
 * ## ولماذا لم نتدخّل في اللصق قبل اليوم — ولا نتدخّل فيه الآن بالمنع
 * اللصقُ **أكثرُ عمليّةٍ تكرارًا في المحرّر كلِّه**. فتدخُّلٌ يعترض كلَّ لصقةٍ يصير ضريبةً
 * على كلّ عمل. ولذلك:
 *   • **الخروجُ أمرٌ صريحٌ لا تلقائيّ** — يُطلَب حين يُراد، فكلفتُه صفرٌ لمن لا يريده.
 *   • **الدخولُ بلاغٌ لا اعتراض** — رسالةٌ واحدةٌ **مرّةً في الجلسة**، ولها «لا تُنبّهني».
 *     ولا تظهر إلّا حين يكون في الملصوق **قالبٌ غيرُ متوازن**، لا لمجرّد وجودِ علامة.
 */

const scan = require("./bidi-scan.js");

/** أوامرُ الحافظة — تُصدَّر كي لا يُكتَب المعرّفُ حرفيًّا في مكانَين. */
const COPY_SAFE_CMD = "mihrab.copyForSharing";
/**
 * الأمرُ المقابل: يزيل عزلَ النشر من الملفّ.
 *
 * **بابُ العودة.** من يلصق شيفرةً ليعمل عليها لا يريد محارفَ خفيّةً في ملفّه، وحذفُها
 * يدويًّا متعذّرٌ (لا تُرى ولا يمسّها زرُّ إصلاحِ `BS-01` لأنّها متوازنةٌ ومشروعة). وميزةٌ
 * تُدخِل شيئًا ولا تملك إخراجَه ميزةٌ نصفُها فخّ.
 */
const STRIP_ISO_CMD = "mihrab.stripSharingIsolates";
/**
 * مفتاحُ بلاغِ اللصق — **إعدادٌ مرئيٌّ لا حالةٌ خفيّة**.
 *
 * كان في `globalState`: يُكتَب بنقرةٍ ولا يُقرأ ولا يُعاد إلّا بمسح تخزين المحرّر. وهذا
 * كتمٌ **لتحذيرٍ أمنيّ** لا لإشعارِ تسويق — فمن ضغط الزرَّ في يومه الأوّل كان يفقد
 * الميزةَ إلى الأبد. والإعدادُ يُبحَث ويُزامَن ويُعاد بنقرة.
 */
const PASTE_NOTICE_SETTING = "mihrab.clipboard.pasteNotice";
const CONFIG_SECTION = "mihrab.clipboard";
const CONFIG_KEY = "pasteNotice";

/**
 * عزلٌ اتّجاهيّ — **`FSI` (‏U+2068) لا `LRI` (‏U+2066)**، خلافًا لـ`iso()` في `bidi-guard.js`.
 *
 * الفرقُ ليس شكليًّا: `LRI` **يفرض** اتّجاهًا من اليسار، و`FSI` يأخذ اتّجاهَه من **أوّل
 * حرفٍ قويٍّ داخله**. و`bidi-guard` يلفّ مقاطعَ لاتينيّةً معلومةَ الاتّجاه (رمزُ خطأ،
 * نقطةُ كود) فـ`LRI` صحيحٌ هناك. أمّا هنا فنلفّ **سطرَ شيفرةٍ لا نعرف بمَ يبدأ** — قد
 * يبدأ بمعرّفٍ عربيّ وقد يبدأ بقوسٍ أو بكلمةٍ لاتينيّة. و`LRI` كان سيقلب اتّجاهَ كلّ سطرٍ
 * عربيٍّ إلى اليسار في الوجهة، أي **يصنع العطبَ الذي جاء الأمرُ ليمنعه**.
 */
const ISO_OPEN = "⁨";
const ISO_CLOSE = "⁩";

/**
 * أدنى طولِ إدراجٍ يُعَدّ «لصقًا».
 *
 * لا سبيلَ في واجهة الامتداد إلى معرفة أنّ التغيير لصقٌ: `TextDocumentChangeEvent` لا
 * يحمل مصدرَ التغيير. والفرقُ المتاحُ هو **الشكل**: الكتابةُ باليد تُدرِج محرفًا محرفًا،
 * واللصقُ يُدرِج كتلةً في تغييرٍ واحد. وحدُّ ‎24‎ محرفًا يعلو فوق أطولِ ما يُدرِجه الإكمالُ
 * التلقائيُّ والمقتطفاتُ، ويقلّ عن أقصرِ مقطعِ شيفرةٍ يُنسَخ عمليًّا.
 *
 * **وهو تقريبٌ نُقِرّ به**: لصقةٌ قصيرةٌ جدًّا لا تُبلَّغ. ولا ضرر: `BS-01` يشخّصها كما
 * يشخّص غيرَها، وهذا البلاغُ **زيادةٌ في التوقيت لا بديلٌ عن التشخيص**.
 */
const PASTE_MIN_CHARS = 24;

/**
 * تمييزُ العدد العربيّ: ‎١‎ مفردٌ · ‎٢‎ مثنّى · ‎٣–١٠‎ جمعُ قلّةٍ مجرور · ‎١١+‎ مفردٌ منصوب.
 *
 * ‏`${n} سطرًا` صحيحةٌ من ‎١١‎ إلى ‎٩٩‎ وحدَها — والحالةُ الغالبةُ في هذا الأمر ‎١‎ («نُسِخ
 * ‏‎1‎ سطرًا») و‎٢–١٠‎ («نُسِخ ‎3‎ سطرًا»). ومستودعٌ يزن الشدّةَ في اسم الشعار لا يليق به
 * عددٌ غيرُ مصروف.
 */
function arCount(n, one, two, few, many) {
  if (n === 1) return one;
  if (n === 2) return two;
  if (n >= 3 && n <= 10) return `${n} ${few}`;
  return `${n} ${many}`;
}
const arLines = (n) => arCount(n, "سطرٌ واحدٌ", "سطران", "أسطرٍ", "سطرًا");
const arChars = (n) =>
  arCount(n, "محرفُ قلبٍ واحدٌ", "محرفا قلبٍ", "محارفِ قلبٍ", "محرفَ قلبٍ");

/** يعزل مقطعًا لاتينيًّا داخل جملةٍ عربيّة — نظيرُ `iso` في `bidi-guard.js`. */
const isoLatin = (s) => "⁦" + s + "⁩";

const COPY = {
  noEditor: "لا محرّر نشط.",
  noSelection: "لا تحديد — حدّد ما تريد نسخَه أوّلًا.",
  // **لا وعدَ عن طرفٍ ثالث.** «سيُعرَض خارج محراب بالترتيب نفسِه» وعدٌ لا نملكه: وجهاتٌ
  // كثيرةٌ تجرّد محارفَ التحكّم قبل العرض. وحين يفشل وعدٌ مطلقٌ يستنتج المستخدمُ أنّ
  // الأمرَ لا يعمل — فيكفّ عنه — بدل أن يعرف أنّ الوجهةَ هي التي جرّدت.
  copied: (n) =>
    `نُسِخ ${arLines(n)} في عزلٍ اتّجاهيّ. في الوجهات التي تحترم عزلَ يونيكود ` +
    "(أكثرُ المحرّرات ومنصّاتِ الشيفرة والمحادثة) سيُعرَض بالترتيب نفسِه الذي تراه هنا؛ " +
    "وما يجرّد المحارفَ الخفيّةَ يعود إلى ترتيبه السابق.",
  // رسالةُ نظامٍ لاتينيّةٌ **معزولةٌ**: بلا عزلٍ تُعاد نقطتُها وأقواسُها ترتيبًا عند الحدّ
  // فتُقرأ مبعثرة. والسببُ المحتمَلُ يُقال بالعربيّة قبلها — «DOMException» ليست رسالةً.
  copyFailed: (e) =>
    "تعذّر النسخُ إلى الحافظة — قد تكون مشغولةً ببرنامجٍ آخر أو ممنوعةً بسياسةِ نظام. " +
    `أعِد المحاولة. (التفصيل: ${isoLatin(String(e))})`,
  stripped: (n) => `أُزيل عزلُ النشر من ${arLines(n)}.`,
  strippedNone: "لا عزلَ نشرٍ في هذا الملفّ.",
  stripFailed: "تعذّر تعديلُ الملفّ — رُفض التحرير.",
  // **الأثرُ لا الآليّة**، وجملٌ قصيرةٌ لأنّ الإشعارَ يقتطع الطويلة. ولا تقل «المسطرة»:
  // مصطلحٌ غيرُ معرَّفٍ في مسردنا، والمستخدمُ الجديدُ لا يعرف أنّ المقصودَ شريطَ الحافّة.
  pasteWarn: (n) =>
    `النصُّ الملصوق فيه ${arChars(n)} غيرُ متوازن. ` +
    "فما تراه في هذا السطر قد لا يكون ترتيبَ تنفيذه — وهي الحيلةُ التي تُخبَّأ بها شيفرةٌ " +
    "في مراجعةٍ تبدو سليمة. المواضعُ معلَّمةٌ في الملفّ وفي لوحة المشاكل.",
  pasteFix: "أصلِحه الآن",
  pasteShow: "أرِني الموضع",
  // «لا تُنبّهني ثانيةً» لا تقول إنّها **دائمة**، والقارئُ العربيُّ يفهمها «كُفَّ عنّي
  // الآن». والجملةُ تحمل بابَ العودة في نصّها كي لا يُبحَث عنه.
  pasteMute: "أوقِف هذا التنبيه (يُعاد من الإعدادات)",
};

/**
 * يلفّ نصًّا للنشر خارج محراب: **كلُّ سطرٍ في عزله**.
 *
 * ## ولماذا سطرًا سطرًا لا الكتلةَ كلَّها
 * عزلُ الكتلة يحميها من سياقها الخارجيّ، ولا يحمي **السطرَ من جاره**: في `<pre>` أو
 * رسالةِ محادثة، كلُّ سطرٍ فقرةٌ مستقلّةٌ في خوارزميّة UAX #9 — فسطرٌ ينتهي بمحايدٍ
 * (‏`;` أو `)`) يستعير اتّجاهَه من محيطه لا من سطرِه. فالعزلُ لكلّ سطرٍ هو الوحيدُ الذي
 * يعطي كلَّ سطرٍ سياقَه بنفسِه.
 *
 * ## والأسطرُ الفارغة تُترَك كما هي
 * ‏`FSI…PDI` حول لا شيءٍ زوجُ محرفَين خفيَّين بلا أثر — وزيادةٌ في حجم النصّ وفي احتمال
 * أن يظنّها قارئٌ لاحقٌ حشوًا مقصودًا.
 *
 * ## ولا يُلَفُّ ما هو ملفوفٌ سلفًا
 * لصقٌ ثمّ نسخٌ آمنٌ ثمّ لصقٌ يُراكِم أزواجَ العزل، فيتضخّم النصُّ بلا مقابل.
 *
 * @param {string} text
 * @returns {{text:string, lines:number}}
 */
function isWrapped(line) {
  // **البدءُ بفاتحٍ والانتهاءُ بخاتمٍ لا يعني الالتفاف.** سطرٌ فيه عزلان متجاوران
  // (‏`⁨أ⁩ = ⁨ب⁩`) يجتاز فحصَ الطرفين ويُترَك بلا عزلٍ للسطر — وهو بالضبط السطرُ الذي
  // يحتاجه. فالفحصُ على **العمق**: هل يبقى الزوجُ الأوّلُ مفتوحًا حتّى آخر محرف؟
  if (!line.startsWith(ISO_OPEN) || !line.endsWith(ISO_CLOSE)) return false;
  let depth = 0;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === ISO_OPEN) depth += 1;
    else if (ch === ISO_CLOSE) depth -= 1;
    if (depth === 0 && i < line.length - 1) return false;
  }
  return depth === 0;
}

/**
 * يزيل عزلَ السطر الكامل — **معكوسُ `isolateForSharing` بالضبط**.
 * @param {string} text
 * @returns {{text:string, lines:number}}
 */
function stripSharingIsolates(text) {
  const src = String(text == null ? "" : text);
  let stripped = 0;
  const out = src.split("\n").map((raw) => {
    const cr = raw.endsWith("\r") ? "\r" : "";
    const line = cr ? raw.slice(0, -1) : raw;
    if (!isWrapped(line)) return raw;
    stripped += 1;
    return line.slice(ISO_OPEN.length, -ISO_CLOSE.length) + cr;
  });
  return { text: out.join("\n"), lines: stripped };
}

function isolateForSharing(text) {
  const src = String(text == null ? "" : text);
  const lines = src.split("\n");
  let wrapped = 0;
  const out = lines.map((raw) => {
    // ‏`\r` يبقى **خارج** العزل: لفُّه يضع محرفًا بعد نهاية السطر في ملفّات CRLF.
    const cr = raw.endsWith("\r") ? "\r" : "";
    const line = cr ? raw.slice(0, -1) : raw;
    if (!line.trim()) return raw;
    if (isWrapped(line)) return raw;
    wrapped += 1;
    return ISO_OPEN + line + ISO_CLOSE + cr;
  });
  return { text: out.join("\n"), lines: wrapped };
}

/**
 * أمرُ «انسخ للنشر». يعيد عددَ الأسطر المعزولة، أو ‎0‎ إن لم يقع نسخٌ.
 *
 * **يُقِرّ بالأثر لا بعدم الرمي**: `writeText` وعدٌ قد يُرفَض (الحافظةُ مشغولةٌ أو ممنوعة)،
 * ورسالةُ نجاحٍ بلا نسخٍ تُنهي بحثَ المستخدم عند نصٍّ لم يصل.
 */
async function copyForSharing(vscode) {
  const ed = vscode.window.activeTextEditor;
  if (!ed) {
    vscode.window.showWarningMessage(COPY.noEditor);
    return 0;
  }
  // التحديداتُ المتعدّدة بترتيب المستند لا بترتيب الإنشاء — وإلّا خرج النصُّ مبعثرًا.
  const sels = ed.selections.filter((s) => !s.isEmpty)
    .slice()
    .sort((a, b) => a.start.compareTo(b.start));
  if (!sels.length) {
    vscode.window.showWarningMessage(COPY.noSelection);
    return 0;
  }
  const raw = sels.map((s) => ed.document.getText(s)).join("\n");
  const { text, lines } = isolateForSharing(raw);
  try {
    await vscode.env.clipboard.writeText(text);
  } catch (e) {
    vscode.window.showErrorMessage(COPY.copyFailed((e && e.message) || String(e)));
    return 0;
  }
  vscode.window.showInformationMessage(COPY.copied(lines));
  return lines;
}

/**
 * أمرُ «أزِل عزلَ النشر» — بابُ العودة من الأمر السابق.
 * يعيد عددَ الأسطر التي نُزِع عزلُها، أو ‎0‎ إن لم يقع تعديل.
 */
async function stripIsolatesCommand(vscode) {
  const ed = vscode.window.activeTextEditor;
  if (!ed) {
    vscode.window.showWarningMessage(COPY.noEditor);
    return 0;
  }
  const doc = ed.document;
  const { text, lines } = stripSharingIsolates(doc.getText());
  if (!lines) {
    vscode.window.showInformationMessage(COPY.strippedNone);
    return 0;
  }
  const edit = new vscode.WorkspaceEdit();
  const whole = new vscode.Range(
    doc.positionAt(0), doc.positionAt(doc.getText().length));
  edit.replace(doc.uri, whole, text);
  // **إقرارٌ بالأثر لا بعدم الرمي** — نمطُ المستودع في `name-guard` و`bidi-guard`.
  const ok = await vscode.workspace.applyEdit(edit);
  if (!ok) {
    vscode.window.showErrorMessage(COPY.stripFailed);
    return 0;
  }
  vscode.window.showInformationMessage(COPY.stripped(lines));
  return lines;
}

/**
 * مراقبُ اللصق: يبلّغ **مرّةً لكلّ مستندٍ في الجلسة** حين يحمل الملصوقُ قالبًا غيرَ متوازن.
 *
 * ## لماذا «لكلّ مستند» لا «لكلّ جلسة»
 * الجلسةُ قد تمتدّ يومًا كاملًا. و«مرّةً في الجلسة» كانت تعني أنّ **لصقةً بريئةً في
 * الصباح تحرق البلاغَ عن لصقةِ ما بعد الظهر** — والتوقيتُ هو كلُّ قيمة هذا البلاغ
 * (التشخيصُ في المسطرة قائمٌ في الحالين). والمستندُ وحدةُ سياقٍ يفهمها المستخدم: ملفٌّ
 * جديدٌ سياقٌ جديد. ويُعاد التسليحُ بعد إصلاحٍ ناجح، لأنّ الملفَّ عاد نظيفًا فالخطرُ
 * التالي خطرٌ جديدٌ فعلًا.
 *
 * @param {*} vscode
 * @param {*} context امتدادُ السياق (‏`subscriptions`).
 * @param {{removeCommand?:string, showProblemsCommand?:string}} [opts]
 *        أوامرُ الأزرار — **تُمرَّر ولا تُكتَب حرفيًّا هنا** (مصدرُ حقيقةٍ واحد).
 */
function activatePasteNotice(vscode, context, opts) {
  const removeCmd = (opts && opts.removeCommand) || null;
  const showCmd = (opts && opts.showProblemsCommand) || null;
  /** مستنداتٌ بُلِّغ عنها في هذه الجلسة (بمعرّف URI). */
  const notified = new Set();
  const enabled = () => {
    try {
      return vscode.workspace.getConfiguration(CONFIG_SECTION).get(CONFIG_KEY) !== false;
    } catch {
      return true; // غيابُ الإعداد لا يُطفئ تحذيرًا أمنيًّا
    }
  };

  /** يفحص نصًّا مُدرَجًا؛ يعيد عددَ القوالب غير المتوازنة فيه. */
  function unbalancedIn(text, languageId) {
    let findings;
    try {
      findings = scan.scanBidi(text, languageId);
    } catch {
      return 0; // بلاغٌ تحسينيّ — فشلُ الفحص لا يمسّ اللصق
    }
    return findings.filter((f) => f.kind === "unbalanced").length;
  }

  async function onChange(e) {
    if (!enabled()) return;
    const ed = vscode.window.activeTextEditor;
    if (!ed || e.document !== ed.document) return;
    const key = String((e.document.uri && e.document.uri.toString()) || "");
    if (notified.has(key)) return;
    // شكلُ اللصق: تغييرٌ واحدٌ يُدرِج كتلةً. أمّا التراجعُ/الإعادة فمصدرُهما معلَنٌ
    // في `reason` — واستثناؤهما يمنع بلاغًا عن نصٍّ لم يجلبه المستخدمُ الآن.
    //
    // **وتقريبٌ ثانٍ نُقِرّ به:** اللصقُ متعدّدُ المؤشّرات يصل في عدّة `contentChanges`،
    // فنجمعها ونفحص المجموع. ولو فُحِص كلٌّ على حدةٍ لتكرّر البلاغُ في اللصقة الواحدة.
    if (e.reason !== undefined || !e.contentChanges.length) return;
    const inserted = e.contentChanges.map((c) => c.text || "").join("\n");
    if (inserted.length < PASTE_MIN_CHARS) return;
    // **يُفحَص المقطعُ المُدرَجُ وحدَه لا الوثيقةُ بعده** — تقريبٌ ثالث: مقطعٌ يكتمل
    // توازنُه بما حوله يُبلَّغ عنه، والعكسُ يمرّ صامتًا. مقبولٌ لبلاغٍ **تحسينيّ**
    // غرضُه التوقيت؛ والحكمُ النهائيُّ لتشخيص `BS-01` على الوثيقة كاملةً.
    const n = unbalancedIn(inserted, e.document.languageId);
    if (!n) return;
    notified.add(key);
    const buttons = [];
    if (removeCmd) buttons.push(COPY.pasteFix);
    if (showCmd) buttons.push(COPY.pasteShow);
    buttons.push(COPY.pasteMute);
    const pick = await vscode.window.showWarningMessage(COPY.pasteWarn(n), ...buttons);
    if (pick === COPY.pasteFix && removeCmd) {
      await vscode.commands.executeCommand(removeCmd);
      notified.delete(key); // عاد الملفُّ نظيفًا ⇒ الخطرُ التالي جديد
    } else if (pick === COPY.pasteShow && showCmd) {
      await vscode.commands.executeCommand(showCmd);
    } else if (pick === COPY.pasteMute) {
      // إلى **الإعداد** لا إلى حالةٍ خفيّة: `Global` كي يتبع المستخدمَ لا المجلّد.
      await vscode.workspace.getConfiguration(CONFIG_SECTION)
        .update(CONFIG_KEY, false, true);
    }
  }

  const sub = vscode.workspace.onDidChangeTextDocument((e) => {
    onChange(e).catch(() => {});
  });
  const handle = {
    dispose() {
      try {
        sub.dispose();
      } catch {
        /* تجاهُلٌ مقصود عند الإغلاق */
      }
    },
    /** للاختبار: يفحص حدثًا مباشرةً بلا انتظارِ المراقب. */
    _onChange: onChange,
  };
  if (context && context.subscriptions) context.subscriptions.push(handle);
  return handle;
}

module.exports = {
  isolateForSharing,
  stripSharingIsolates,
  isWrapped,
  copyForSharing,
  stripIsolatesCommand,
  activatePasteNotice,
  arCount,
  COPY_SAFE_CMD,
  STRIP_ISO_CMD,
  PASTE_NOTICE_SETTING,
  CONFIG_SECTION,
  CONFIG_KEY,
  PASTE_MIN_CHARS,
  ISO_OPEN,
  ISO_CLOSE,
  COPY,
};
