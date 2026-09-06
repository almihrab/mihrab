"use strict";
/**
 * مدخلُ المتصفّح لامتداد لغة ص [WEB-06].
 *
 * ## العطبُ الذي يُغلقه هذا الملفّ ليس نقصَ ميزة
 * قبله كان امتدادُ لغة ص **يسقط من بناء المتصفّح كلَّه**. والقاعدةُ في المنبع صريحة:
 * امتدادٌ فيه `main` وليس فيه `browser` لا يُحمَّل في مضيفِ الويب — فلا تُقرأ
 * مساهماتُه التصريحيّةُ أصلًا. أي أنّ محرابَ المتصفّح كان يخلو من **قواعد لغة ص**
 * ومن مقتطفاتها ومن إعداداتها: ملفُّ `.ص` يُفتَح نصًّا رماديًّا بلا لونٍ ولا طيّ.
 * وأثرُ ذلك يتجاوز اللغة: جولاتُ الترحيب والقياساتُ الطباعيّةُ كلُّها معلّقةٌ بـ
 * `editorLangId == sad`، فسقوطُ اللغة يُسقِطها معها صامتةً.
 *
 * ## وما الذي يبقى مفقودًا هنا — **يُقال ولا يُخفى**
 * خادمُ ص اللغويّ (‏SAD-01) عمليّةٌ ثنائيّة: تشخيصٌ وإكمالٌ وتحويمٌ وتعريف. ولا عمليّةَ
 * خلف صفحةٍ في المتصفّح، فلا خادمَ ولا شيءَ منها. والتلوينُ والمقتطفاتُ والطيُّ
 * وأزواجُ الأقواس **كلُّها تصريحيّة** — تعمل هنا كما تعمل على المكتب.
 *
 * والأمرُ الوحيدُ المُسهَم (`sad.lsp.restart`) يُسجَّل ليقول ذلك، لا ليُترَك بلا مُسجِّلٍ
 * فيردّ «الأمرُ غيرُ معروف» — رسالةُ عطبٍ يقرؤها المستخدمُ خللًا في جهازه.
 */

const vscode = require("vscode");

const RESTART_CMD = "sad.lsp.restart";
const DOWNLOAD_URL = "https://sad-lang.org/mihrab/download/";

const COPY = {
  noServer:
    "خادمُ ص اللغويُّ برنامجٌ يعمل على جهازك، ومحرابٌ هنا يعمل في متصفّحك بلا خادم — " +
    "فلا تشخيصَ ولا إكمالَ ولا «اذهب إلى التعريف». والتلوينُ والمقتطفاتُ تعمل كما هي. " +
    "نسخةُ المكتب تحمل الخادمَ مدمجًا بلا تثبيت.",
  download: "افتح صفحةَ التنزيل",
  ok: "فهمت",
};

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand(RESTART_CMD, async () => {
      const pick = await vscode.window.showInformationMessage(
        COPY.noServer, COPY.download, COPY.ok);
      if (pick === COPY.download) {
        await vscode.env.openExternal(vscode.Uri.parse(DOWNLOAD_URL));
      }
    })
  );
}

function deactivate() {}

module.exports = { activate, deactivate, COPY, RESTART_CMD };
