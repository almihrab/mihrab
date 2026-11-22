"use strict";
/**
 * أمرُ «صدِّر للطباعة» [PR-01] — الطبقةُ الرقيقةُ التي تلمس `vscode`.
 *
 * كلُّ المنطق في `print-export.js` (دالّةٌ نقيّة: نصٌّ ⇒ نصّ) — وهذا الملفُّ لا يفعل غيرَ
 * القراءةِ والحفظِ والإبلاغ. الفصلُ مقصود: تأكيداتُ البند كلُّها تصير اختباراتِ عقدةٍ بلا
 * محرّرٍ ولا حوارٍ، و**حوارُ طباعةٍ لا يُختبَر**.
 *
 * ## ولماذا ملفٌّ لا حوارُ طباعة
 * ثلاثةُ أسباب: (أ) VS Code **لا واجهةَ طباعةٍ فيها**، و`window.print()` داخل webview
 * يتّكئ على سلوكِ إلكترون غيرِ الموثَّق — وميزةٌ أمنيّةٌ مبنيّةٌ على ذلك تنكسر بترقيةِ
 * منبعٍ صامتة؛ (ب) المطلوبُ **أثرٌ يُرفَق ويُؤرشَف** بمراجعة، لا نافذةٌ تختفي؛
 * (ج) الملفُّ يجعل الميزةَ دالّةً نقيّةً فتُختبَر. والزرُّ «اطبع» **داخل الصفحة المصدَّرة**،
 * حيث المتصفّحُ حقيقيّ.
 */
const path = require("node:path");
const { buildPrintHtml } = require("./print-export");
const { loadFontDataUri } = require("./bundled-font");
const { arCount } = require("./clipboard-safety");

const EXPORT_CMD = "mihrab.exportForPrint";

const COPY = {
  noEditor: "لا ملفَّ مفتوحًا لتصديره.",
  saveLabel: "احفظ نسخةَ الطباعة",
  done: (name, n) => n > 0
    ? `صُدِّر «${name}» — وعُلِّم ${arCount(n, "محرفُ اتّجاهٍ خفيٌّ واحدٌ", "محرفا اتّجاهٍ خفيّان",
        "محارفِ اتّجاهٍ خفيّةٍ", "محرفَ اتّجاهٍ خفيًّا")} بحاشيةٍ تشرحها.`
    : `صُدِّر «${name}» — ولا محرفَ اتّجاهٍ خفيًّا فيه.`,
  open: "افتح",
  // `COPY.missing` و`COPY.corrupt` جملتان تامّتان تقولان «لا يمكن التصدير» بأنفسهما،
  // فتغليفُهما بـ«تعذّر التصدير:» كان نفيًا مكرّرًا. البادئةُ للأخطاء غيرِ المصوغة وحدَها.
  failed: (m) => (/لا يمكن التصدير/.test(m) ? m : `تعذّر التصدير: ${m}`),
};

/**
 * @param {typeof import("vscode")} vscode
 * @param {{ extensionPath: string }} context
 */
async function exportForPrint(vscode, context) {
  const editor = vscode.window.activeTextEditor;
  if (!editor) { vscode.window.showWarningMessage(COPY.noEditor); return; }

  const doc = editor.document;
  const source = doc.getText();
  const base = path.basename(doc.fileName || "بلا-اسم");

  let html, count;
  try {
    // **يُقرأ الخطُّ قبل البناء**: غيابُه يُفشِل الأمرَ ولا يُنتج ملفًّا.
    // ملفٌّ يبدو سليمًا عند مُصدِّره ويُطبَع بخطٍّ لاتينيٍّ عند غيره أسوأُ من فشلٍ صريح،
    // لأنّ الفشلَ يُصلَح والانحرافَ الصامتَ يُوقَّع عليه. (التعليل في `bundled-font.js`.)
    const fontDataUri = loadFontDataUri(context && context.extensionPath);
    html = buildPrintHtml(source, {
      fileName: base,
      fontDataUri,
      exportedAt: new Date().toISOString().slice(0, 10),
    });
    count = (html.match(/<mark class="bidi"/g) || []).length;
  } catch (e) {
    vscode.window.showErrorMessage(COPY.failed(e && e.message ? e.message : String(e)));
    return;
  }

  // تجريدُ الامتداد **لا يمسّ الملفَّ النقطيّ**: `/\.[^.\\/]+$/` على `.gitignore` يبتلع
  // الاسمَ كلَّه فيقترح `.print.html` — ملفًّا مخفيًّا بلا أساس، و`.env` و`.gitignore`
  // يتصادمان على المسار نفسِه فيكتب أحدُهما فوق الآخر بلا تحذير. فالنقطةُ الأولى تُستثنى.
  const suggested = (doc.fileName ? doc.fileName.replace(/(?<=[^.\\/])\.[^.\\/]+$/, "") : base) + ".print.html";
  const target = await vscode.window.showSaveDialog({
    defaultUri: vscode.Uri.file(suggested),
    saveLabel: COPY.saveLabel,
    filters: { HTML: ["html"] },
  });
  if (!target) return;   // إلغاءٌ صامت — لا رسالةَ «تمّ» بلا أثر

  try {
    await vscode.workspace.fs.writeFile(target, Buffer.from(html, "utf8"));
  } catch (e) {
    vscode.window.showErrorMessage(COPY.failed(e && e.message ? e.message : String(e)));
    return;
  }

  const pick = await vscode.window.showInformationMessage(COPY.done(base, count), COPY.open);
  if (pick === COPY.open) await vscode.env.openExternal(target);
}

module.exports = { exportForPrint, EXPORT_CMD, COPY };
