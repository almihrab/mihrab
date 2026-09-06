"use strict";
/**
 * قارئُ بيانات المساعدة على المكتب — **ملفٌّ مستقلٌّ لسببٍ واحد** [ON-03 · WEB-06].
 *
 * ‏`help-panel.js` تُحمَّل في مضيفَي امتدادٍ اثنين: عقدةٌ على المكتب، وعاملُ ويبٍ في
 * المتصفّح. وحزمةُ المتصفّح تُبنى بـesbuild، وهو **يحلّ `require` نصًّا لا وقتَ تشغيل**:
 * فمجرّدُ ذكرِ `require("fs")` في الوحدة — ولو داخل دالّةٍ لا تُستدعى هناك أبدًا —
 * يُفشِل البناءَ بـ«‏Could not resolve "fs"». فالسطران اللذان يقرآن القرصَ يسكنان هنا،
 * ولا يستوردهما إلّا `extension.js` (مدخلُ العقدة). والمتصفّحُ يحقن قارئَه من
 * `workspace.fs` بدلَه.
 */

const fs = require("fs");
const path = require("path");

const { DATA_DIR } = require("./help-panel.js");

/**
 * يبني قارئًا متزامنًا من مجلّد الامتداد على القرص.
 * @param {string} extensionPath
 * @returns {(file:string) => string} يرمي عند العطب — و`readData` يبتلع الرميَ ويعيد `null`.
 */
function nodeReader(extensionPath) {
  return (file) => fs.readFileSync(path.join(extensionPath, DATA_DIR, file), "utf8");
}

module.exports = { nodeReader };
