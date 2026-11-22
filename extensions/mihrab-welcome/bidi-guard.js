"use strict";
/**
 * وصلُ كاشفِ قلبِ الاتّجاه بالمحرّر [BS-01] — الطبقةُ الأولى بالكامل: مجموعةُ تشخيصاتٍ على
 * نصّ المستند، ومزوّدُ إجراءاتٍ يعرض إصلاحًا. **لا رقعةَ نواةٍ ولا مسَّ بالمنبع.**
 *
 * والمنطقُ كلُّه في `bidi-scan.js` (وحدةٌ نقيّةٌ مُختبَرة)؛ هنا التوصيلُ وحدَه — النمطُ الذي
 * يتّبعه المستودعُ في `unicode-guard.js` و`validate-name.js`: منطقٌ نقيٌّ يُختبَر، وغلافٌ رفيع.
 *
 * ## قرارُ الصياغة
 * التشخيصُ **لا يفترض معرفةً أمنيّة**. مَن يراه قد لا يعرف «Trojan Source» ولا `RLO`؛ يعرف
 * أنّ سطرًا أمامه. فالجملةُ الأولى تصف **الأثرَ** لا الآليّة: «هذا السطرُ يُعرَض بغيرِ ترتيبِ
 * تنفيذه». والاسمُ التقنيُّ يأتي بعدها لمن أراد أن يستزيد.
 */

const scan = require("./bidi-scan.js");

/** معرّفُ مصدر التشخيص — يظهر في لوحة المشاكل بجانب الرسالة. */
const SOURCE = "محراب — اتّجاه";
/** رمزُ التشخيص (يربط الإصلاحَ بالمشكلة، ويسمح للمستخدم بتصفيته). */
const CODE = "mihrab.bidi.unbalanced";
/** رمزٌ منفصلٌ لتشخيص «لم يُفحَص»: لا إصلاحَ له، ولا يجوز أن يُعرَض له مصباح. */
const CODE_TOO_LARGE = "mihrab.bidi.notScanned";
/** أمرُ الإصلاح — يزيل الفواتحَ غيرَ المتوازنة من المستند الحاليّ. */
const REMOVE_CMD = "mihrab.removeBidiControls";
/** حدُّ الحجم: ملفٌّ أكبرُ من هذا لا يُمسَح حيًّا (المسحُ خطّيّ، لكنّ الحدَّ يمنع مفاجأةً). */
const MAX_SCAN_CHARS = 2 * 1024 * 1024;
/** مخطّطاتُ المستندات التي تُمسَح: ملفّاتٌ حقيقيّةٌ وغيرُ محفوظة. لا `output` ولا `git` (قراءةٌ فقط). */
const SCANNED_SCHEMES = new Set(["file", "untitled", "vscode-vfs"]);

/**
 * يعزل مقطعًا لاتينيًّا داخل جملةٍ عربيّة (`FSI…PDI`) فلا تقفز المحايداتُ حولَه.
 *
 * **ليس تجميلًا:** رسائلُنا تصل إلى `aria-label` وإلى لوحة المشاكل وإلى النسخ واللصق —
 * وثلاثتُها لا تبلغها CSS. وهو الدرسُ نفسُه الذي دفعنا ثمنَه في `mihrabSettingsLexicon.ts`
 * فوضعنا العزلَ **في السلسلة** لا في الورقة. ولا يليق بملفٍّ يشخّص خللَ الاتّجاه أن يهمل
 * اتّجاهَ رسائله هو. (نقطتا الكود صريحتان: لا محرفَ خفيًّا مكتوبًا حرفيًّا في المصدر.)
 */
const iso = (s) => "⁨" + s + "⁩";

const COPY = {
  // **الأثرُ أوّلًا بلغةٍ يفهمها من لا يعرف يونيكود، ثمّ الاسمُ التقنيُّ مذيَّلًا بين قوسين.**
  // ولا يُقحَم رمزٌ لاتينيٌّ في متن الجملة: «PDF» في الدنيا كلِّها صيغةُ ملفّ، فقارئُها
  // يفهم أنّ سطرَه «لم يُغلَق بملفّ PDF» ويتوقّف عن القراءة — ويؤكّده قارئُ الشاشة نطقًا.
  message: (f) =>
    "هذا السطرُ يُعرَض على الشاشة بترتيبٍ غيرِ الترتيب الذي يُنفَّذ به. فيه محرفٌ غيرُ مرئيّ " +
    "يقلب اتّجاهَ ما بعده، فُتِح هنا ولم يُغلَق قبل نهاية السطر — فسرى قلبُه إلى بقيّة السطر. " +
    `(المحرف: ${f.nameAr} — ${iso(f.code)}؛ يُغلَق بـ${iso(f.expected)}.)`,
  // العابرُ للحدّ: متوازنٌ حسابيًّا، ويقلب شيفرةً حقيقيّة. رسالتُه مختلفةٌ لأنّ علاجَه مختلف.
  messageLeak: (f) =>
    "قلبُ الاتّجاه هنا يبدأ داخل تعليقٍ أو نصّ وينتهي خارجَه، فيسري على شيفرةٍ حقيقيّة: " +
    "ما تراه العينُ في هذا السطر غيرُ ما يُنفَّذ. " +
    `(المحرف: ${f.nameAr} — ${iso(f.code)}؛ خاتمُه ${iso(f.expected)} خارج المنطقة.)`,
  // **وصفٌ لا اتّهام.** الاحتمالُ الأغلبُ لهذا التشخيص في محرابٍ ليس هجومًا بل لصقًا من
  // متصفّحٍ أو محرّرِ نصوص. ومصطلحٌ أمنيٌّ يُرعب بلا داعٍ يُدرِّب على تجاهُل التحذير كلِّه.
  inQuoted:
    " وموضعُه داخل تعليقٍ أو نصّ: ما بينهما لا يقرؤه المصرِّفُ وتقرؤه عينُك — فيختلف ما ترى" +
    " عمّا يُنفَّذ. (يحدث كثيرًا عند اللصق من متصفّحٍ أو محرّرِ نصوص.)",
  fixTitle: "أصلِح هذا الموضعَ وحدَه",
  fixTitleAll: "أصلِح ترتيبَ العرض: أزِل محارفَ القلب غيرَ المغلَقة من الملفّ كلّه",
  removed: (n) =>
    `أُصلِح ترتيبُ العرض: أُزيل ${n} محرفَ قلبٍ غيرَ مغلَق. العلاماتُ المفردةُ والقوالبُ` +
    " المتوازنةُ لم تُمَسّ. (للتراجع: Ctrl+Z)",
  // **فشلٌ يُقال كما هو.** رسالةُ «أُزيل ٠» تُنهي بحثَ المستخدم وهي تعني «لم يحدث شيء».
  removeFailed:
    "لم يتغيّر شيء — قد يكون الملفُّ للقراءة فقط أو معدَّلًا في مكانٍ آخر. احفظه ثمّ أعِد المحاولة.",
  removePartial: (done, left) =>
    `أُزيل ${done} وبقي ${left}. افتح لوحةَ المشاكل لترى ما بقي وموضعَه.`,
  nothing: "لا محارفَ قلبٍ غيرَ مغلَقةٍ في هذا الملفّ.",
  noEditor: "لا محرّر نشط.",
  tooLarge: "هذا الملفُّ أكبرُ من حدّ الفحص الحيّ — لم يُفحَص اتّجاهُه. (ليس إقرارًا بسلامته.)",
};

/** يحوّل شدّةَ الماسح إلى شدّةِ VS Code. الحرِجُ خطأٌ، والمشبوهُ تحذير. */
function toSeverity(vscode, severity) {
  return severity === scan.SEVERITY.CRITICAL
    ? vscode.DiagnosticSeverity.Error
    : vscode.DiagnosticSeverity.Warning;
}

/** هل يُمسَح هذا المستند؟ (نقيّةٌ بما يكفي للاختبار ببديل خفيف). */
function shouldScan(doc) {
  if (!doc || !doc.uri) return false;
  if (!SCANNED_SCHEMES.has(doc.uri.scheme)) return false;
  // `getText` على مستندٍ ضخمٍ مكلف؛ الحدُّ يُقرأ من الطول المعلَن لا من النصّ.
  return true;
}

/** طولُ سطرٍ احتياطيٌّ حين لا يوفّر المستندُ `lineAt` (بديلُ اختبارٍ خفيف). */
function lineEndOf(doc, line, fallback) {
  try {
    return doc.lineAt(line).range.end.character;
  } catch {
    return fallback;
  }
}

/** يبني تشخيصات مستندٍ واحد. مفصولةٌ عن الصنف كي تُختبَر بلا دورةِ حياة. */
function diagnosticsFor(vscode, doc) {
  const text = doc.getText();
  if (text.length > MAX_SCAN_CHARS) {
    // **الغيابُ هنا أخطرُ من الضجيج:** بلا هذا السطر يبدو الملفُّ الضخمُ سليمًا، والصوابُ
    // أنّه **لم يُفحَص**. تشخيصٌ إعلاميٌّ واحدٌ يقول الفرق.
    const d = new vscode.Diagnostic(
      new vscode.Range(0, 0, 0, 0),
      COPY.tooLarge,
      vscode.DiagnosticSeverity.Information
    );
    d.source = SOURCE;
    d.code = CODE_TOO_LARGE;
    return [d];
  }
  const hits = scan.scanBidi(text, doc.languageId);
  return hits.map((f) => {
    // **المدى = المنطقةُ المتضرّرةُ فعلًا** (من الفاتح إلى نهاية السطر) لا المحرفُ الصفريُّ
    // العرضِ وحدَه: خطٌّ تحت محرفٍ بلا حبرٍ خطٌّ لا يراه أحد — يرى المستخدمُ علامةً في
    // المسطرة ولا يجد تحتها شيئًا. وما «يُعرَض مقلوبًا» هو المدى لا المحرف.
    const end = f.kind === scan.KIND.LEAK && f.closeColumn !== null
      ? f.closeColumn + 1
      : Math.max(f.endColumn, lineEndOf(doc, f.line, f.endColumn));
    const d = new vscode.Diagnostic(
      new vscode.Range(f.line, f.column, f.line, end),
      (f.kind === scan.KIND.LEAK ? COPY.messageLeak(f) : COPY.message(f)) +
        (f.inQuoted && f.kind !== scan.KIND.LEAK ? COPY.inQuoted : ""),
      toSeverity(vscode, f.severity)
    );
    d.source = SOURCE;
    d.code = CODE;
    return d;
  });
}

/**
 * حارسُ الاتّجاه: يمسح المستنداتِ المفتوحةَ وعند كلّ تغيير (مهدّأً)، ويعرض إصلاحًا.
 * يُدار كـ`Disposable` واحد.
 */
class BidiGuard {
  /**
   * @param {*} vscode واجهةُ المحرّر (تُحقَن كي تُختبَر الوحدةُ ببديل).
   * @param {*} context سياقُ الامتداد.
   * @param {number} [debounceMs] تهدئةُ إعادة المسح أثناء الكتابة.
   */
  constructor(vscode, context, debounceMs = 300) {
    this.vscode = vscode;
    this.debounceMs = debounceMs;
    this.collection = vscode.languages.createDiagnosticCollection("mihrab-bidi");
    /** @type {Map<string, any>} */
    this.timers = new Map();
    this.disposables = [
      this.collection,
      vscode.workspace.onDidOpenTextDocument((d) => this.refresh(d)),
      vscode.workspace.onDidChangeTextDocument((e) => this.schedule(e.document)),
      vscode.workspace.onDidCloseTextDocument((d) => {
        this.collection.delete(d.uri);
        const t = this.timers.get(d.uri.toString());
        if (t) {
          clearTimeout(t);
          this.timers.delete(d.uri.toString());
        }
      }),
    ];
    // المستنداتُ المفتوحةُ سلفًا عند التنشيط — وإلّا لم يُشخَّص شيءٌ حتّى أوّل تغيير.
    for (const d of vscode.workspace.textDocuments) this.refresh(d);
    if (context && context.subscriptions) context.subscriptions.push(this);
  }

  /** يعيد المسحَ بعد تهدئة (الكتابةُ السريعةُ لا تُشغّل مسحًا لكلّ ضغطة). */
  schedule(doc) {
    if (!shouldScan(doc)) return;
    const key = doc.uri.toString();
    const prev = this.timers.get(key);
    if (prev) clearTimeout(prev);
    this.timers.set(
      key,
      setTimeout(() => {
        this.timers.delete(key);
        this.refresh(doc);
      }, this.debounceMs)
    );
  }

  /** يمسح مستندًا ويحدّث تشخيصاته فورًا. */
  refresh(doc) {
    if (!shouldScan(doc)) return;
    try {
      this.collection.set(doc.uri, diagnosticsFor(this.vscode, doc));
    } catch {
      // المسحُ تحسينيّ — فشلُه لا يُفشِل المحرّر ولا يُخفي تشخيصاتٍ أخرى.
    }
  }

  dispose() {
    for (const t of this.timers.values()) clearTimeout(t);
    this.timers.clear();
    for (const d of this.disposables) {
      try {
        d.dispose();
      } catch {
        /* تجاهُلٌ مقصود عند الإغلاق */
      }
    }
  }
}

/**
 * مزوّدُ إجراءاتِ الشيفرة على تشخيصاتنا وحدَها — **إجراءان لا واحد**.
 *
 * ‏«الملفّ كلّه» وحدَه كان يعني أنّ نقرةً على السطر ٣ تغيّر السطرَ ٩٠ الذي لم يفتحه أحد.
 * فالمفضَّلُ هو **الموضعُ وحدَه** (أضيقُ ما يحلّ ما يراه المستخدم)، والكلّيُّ خيارٌ ثانٍ صريح.
 * وتشخيصُ «لم يُفحَص» لا إجراءَ له عمدًا: مصباحٌ بلا إصلاحٍ وعدٌ مكسور.
 */
class BidiCodeActionProvider {
  constructor(vscode) {
    this.vscode = vscode;
  }
  provideCodeActions(doc, range, ctx) {
    const vscode = this.vscode;
    const ours = (ctx.diagnostics || []).filter((d) => d.code === CODE);
    if (!ours.length) return [];
    const here = new vscode.CodeAction(COPY.fixTitle, vscode.CodeActionKind.QuickFix);
    here.command = {
      command: REMOVE_CMD,
      title: COPY.fixTitle,
      arguments: [doc.uri, ours[0].range],
    };
    here.diagnostics = ours;
    here.isPreferred = true;
    const all = new vscode.CodeAction(COPY.fixTitleAll, vscode.CodeActionKind.QuickFix);
    all.command = { command: REMOVE_CMD, title: COPY.fixTitleAll, arguments: [doc.uri] };
    all.diagnostics = ours;
    return [here, all];
  }
}

/**
 * أمرُ الإزالة: يستبدل نصَّ المستند بنسخةٍ بلا الفواتح غير المتوازنة.
 * **يُعيد القراءةَ بعد التحرير ويقول ما بقي** — كما تعلّمنا في `unicode-guard.js`:
 * رسالةُ نجاحٍ بلا أثرٍ أسوأُ من رسالةِ فشل، لأنّها تُنهي بحثَ المستخدم.
 */
async function removeCommand(vscode, uriArg, rangeArg) {
  const editor = vscode.window.activeTextEditor;
  let doc = null;
  if (uriArg && uriArg.scheme) doc = await vscode.workspace.openTextDocument(uriArg);
  else if (editor) doc = editor.document;
  if (!doc) {
    vscode.window.showWarningMessage(COPY.noEditor);
    return 0;
  }
  const before = doc.getText();
  const unbalanced = (t) =>
    scan.scanBidi(t, doc.languageId).filter((h) => h.kind === scan.KIND.UNBALANCED);
  const hits = unbalanced(before);
  if (!hits.length) {
    vscode.window.showInformationMessage(COPY.nothing);
    return 0;
  }
  const edit = new vscode.WorkspaceEdit();
  if (rangeArg) {
    // إصلاحُ موضعٍ واحد: نحذف محرفًا واحدًا في مبدأ المدى — أضيقُ تحريرٍ يحلّ ما يراه.
    const start = rangeArg.start || rangeArg;
    edit.replace(doc.uri, new vscode.Range(start.line, start.character, start.line, start.character + 1), "");
  } else {
    const full = new vscode.Range(doc.positionAt(0), doc.positionAt(before.length));
    edit.replace(doc.uri, full, scan.stripUnbalanced(before, doc.languageId));
  }
  const applied = await vscode.workspace.applyEdit(edit);
  // **إقرارٌ بالأثر لا بعدم الرمي.** الكتابةُ قد تُرفَض (ملفٌّ للقراءة، تعارضُ إصدار) فتعود
  // `applyEdit` بـ`false` ولا ترمي — فرسالةُ «أُزيل ٠» تُنهي بحثَ المستخدم وهي تعني «لم
  // يحدث شيء». نعيد القراءةَ من المستند نفسِه ونقول ما بقي، كما تعلّمنا في `unicode-guard`.
  const left = unbalanced(doc.getText());
  const removed = hits.length - left.length;
  if (!applied || removed <= 0) {
    vscode.window.showWarningMessage(COPY.removeFailed);
    return 0;
  }
  if (left.length) {
    vscode.window.showWarningMessage(COPY.removePartial(removed, left.length));
    return removed;
  }
  vscode.window.showInformationMessage(COPY.removed(removed));
  return removed;
}

module.exports = {
  BidiGuard,
  BidiCodeActionProvider,
  removeCommand,
  diagnosticsFor,
  shouldScan,
  toSeverity,
  iso,
  SOURCE,
  CODE,
  CODE_TOO_LARGE,
  REMOVE_CMD,
  MAX_SCAN_CHARS,
  SCANNED_SCHEMES,
  COPY,
};
