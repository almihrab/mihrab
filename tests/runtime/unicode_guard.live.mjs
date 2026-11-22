// L3 حيّ [AR-04]: أمرُ «أزِل الإطارات الصفراء» وإنذارُه — على الحزمة المشحونة لا على المصدر.
//
// **لماذا حيًّا:** اختباراتُ الوحدة تقيس المنطقَ ببديلِ vscode؛ وهي لا تُثبت أنّ
// `getConfiguration(undefined, {languageId})` يملأ `globalLanguageValue` فعلًا، ولا أنّ
// `update(..., overrideInLanguage)` يمسح كتلةَ `"[plaintext]"`، ولا أنّ الأمرَ مُسجَّلٌ ويظهر في
// لوحة الأوامر بعنوانه العربيّ. هذه أربعةُ ادّعاءاتٍ عن **المنبع** لا عن شيفرتنا.
//
// **العزل:** يُطلَق بـ`--user-data-dir` مؤقّت. إعداداتُ المستخدم الحقيقيّة لا تُمسّ —
// والاختبارُ يكتب في `settings.json` ويمسحه، فلا يجوز أن يقع ذلك على ملفٍّ يملكه أحد.
//
// الاستعمال: node tests/runtime/unicode_guard.live.mjs [--keep]
// خرج 0 = كلّ التأكيدات نجحت · 1 = فشل تأكيد · 2 = خطأ تشغيليّ (لا حزمة/لا إقلاع).
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { CDP, sleep, key, MOD, insertText } from "./harness.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const EXE = join(ROOT, ".upstream", "VSCode-win32-x64", "Mihrab.exe");
const PORT = 9333;
const KEEP = process.argv.includes("--keep");
const CMD_TITLE = "أزِل الإطارات الصفراء";
const SETTING = "editor.unicodeHighlight.nonBasicASCII";

const log = m => console.log(`▶ ${m}`);
let failed = 0;
const ok = (cond, name, detail = "") => {
  if (cond) console.log(`  ✅ ${name}`);
  else { failed++; console.log(`  ❌ ${name}${detail ? "\n       " + detail : ""}`); }
};

if (!existsSync(EXE)) { console.error(`❌ لا حزمة مشحونة: ${EXE}`); process.exit(2); }

const tmp = mkdtempSync(join(tmpdir(), "mihrab-ar04-"));
const userData = join(tmp, "user-data");
const wsDir = join(tmp, "مشروع");
const userSettings = join(userData, "User", "settings.json");
mkdirSync(join(userData, "User"), { recursive: true });
mkdirSync(wsDir, { recursive: true });
writeFileSync(join(wsDir, "مثال.txt"), "دالة رئيسية()\n  اطبع(\"نصاب_الفضة\")\n", "utf8");

/**
 * ⚠️ نفسُ الفخّ الموثَّق في `launch.mjs`: حين يعمل هذا السكربت داخل طرفيّةٍ مدمجةٍ في
 * VS Code تكون البيئةُ موروثةً من Electron مضيفٍ آخر، وفيها `ELECTRON_RUN_AS_NODE=1`
 * وسائرُ `VSCODE_*`. فيرثها الطفلُ ويعمل **بوضع Node** لا بوضع تطبيق ⇒ لا نافذةَ ولا
 * منفذَ تنقيح، والعَرَضُ الظاهر «تعذّر الاتّصال بـCDP: fetch failed» يبدو عطبَ حزمةٍ لا
 * تلوّثَ بيئة. وقعنا فيه فعلًا في أوّل تشغيلةٍ لهذا الملفّ.
 */
function cleanEnv() {
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  for (const k of Object.keys(env)) if (k.startsWith("VSCODE_")) delete env[k];
  return env;
}

let proc = null;
function launch() {
  proc = spawn(EXE, [
    `--remote-debugging-port=${PORT}`, "--remote-allow-origins=*",
    `--user-data-dir=${userData}`, "--skip-release-notes", "--disable-updates",
    // بلا هذا يعترض حوارُ الثقة أوّلَ نافذةٍ في ملفّ تعريفٍ جديد، فيسرق التركيز ولا
    // تُفتَح لوحةُ الأوامر — والعَرَضُ الظاهر «الأمرُ غير موجود» وهو موجود. (قِيس حيًّا:
    // `document.activeElement` كان زرَّ الحوار لا حقلَ اللوحة.)
    "--disable-workspace-trust",
    "--new-window", wsDir,
  ], { detached: false, stdio: "ignore", env: cleanEnv() });
}
function kill() { try { proc && proc.kill(); } catch { /* */ } }

async function attach(timeoutMs = 120000) {
  const t0 = Date.now();
  for (;;) {
    try { return await CDP.attach(PORT); } catch (e) {
      if (Date.now() - t0 > timeoutMs) throw new Error(`تعذّر الاتّصال بـCDP: ${e.message}`);
      await sleep(1500);
    }
  }
}

/** نصوصُ فقاعات الإشعار الظاهرة الآن. */
const toasts = cdp => cdp.evaluate(`
  Array.from(document.querySelectorAll(".notification-toast .notification-list-item-message"))
       .map(e => (e.textContent || "").trim())`);

/** ينقر زرًّا في فقاعة الإشعار بنصِّه (نقرةُ فأرةٍ حقيقيّة بإحداثيّة، لا .click()). */
async function clickToastButton(cdp, label) {
  const box = await cdp.evaluate(`(() => {
    const b = Array.from(document.querySelectorAll(".notification-toast .monaco-button"))
      .find(e => (e.textContent || "").includes(${JSON.stringify(label)}));
    if (!b) return null;
    const r = b.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`);
  if (!box) return false;
  await cdp.cmd("Input.dispatchMouseEvent", { type: "mousePressed", x: box.x, y: box.y, button: "left", clickCount: 1 });
  await cdp.cmd("Input.dispatchMouseEvent", { type: "mouseReleased", x: box.x, y: box.y, button: "left", clickCount: 1 });
  await sleep(1200);
  return true;
}

/** يفتح لوحة الأوامر وينفّذ الأمر بعنوانه العربيّ. يعيد نصَّ أوّل نتيجةٍ معروضة. */
async function runCommand(cdp) {
  await key(cdp, 80, "KeyP", MOD.CTRL | MOD.SHIFT);
  await sleep(1500);
  // حقنٌ مباشر لا عبر `insertText` المُقِرّ: حقلُ اللوحة يُفتَح بالبادئة «>» وحدها،
  // فالإقرارُ بـ`before + text` يعيد الكتابةَ عند أوّل عدمِ تطابقٍ فيتضاعف النصّ
  // ⇒ «لا توجد نتائج مطابقة». قِسناه: القيمةُ كانت مضاعفةً لا مفقودة.
  await cdp.cmd("Input.insertText", { text: CMD_TITLE });
  await sleep(1500);
  const typed = await cdp.evaluate(
    `(document.querySelector(".quick-input-widget input") || {}).value`);
  const first = await cdp.evaluate(`(() => {
    const e = document.querySelector(".quick-input-list .monaco-list-row .label-name");
    return e ? (e.textContent || "").trim() : null;
  })()`);
  await key(cdp, 13, "Enter");
  await sleep(2500);
  return { first, typed };
}

function writeUserSettings(obj) {
  writeFileSync(userSettings, JSON.stringify(obj, null, 2), "utf8");
}
function readUserSettings() {
  try { return JSON.parse(readFileSync(userSettings, "utf8")); } catch { return null; }
}

try {
  // ═══ (١) حالةٌ نظيفة: لا إعدادَ يُظلِّل ⇒ الأمرُ يُبلِّغ بالسلامة ولا يخترع عطبًا ═══
  writeUserSettings({ "window.restoreWindows": "none" });
  log("إطلاق النسخة المشحونة بملفّ تعريفٍ معزول…");
  launch();
  let cdp = await attach();
  await sleep(6000);   // مهلةُ تنشيط الامتدادات (onStartupFinished)
  log("حالةٌ نظيفة: تنفيذ الأمر من لوحة الأوامر");
  const { first: shownTitle, typed } = await runCommand(cdp);
  ok(shownTitle && shownTitle.includes(CMD_TITLE),
    "الأمرُ يظهر في لوحة الأوامر بعنوانه العربيّ",
    `الظاهر: ${shownTitle} · المكتوب في الحقل: ${JSON.stringify(typed)}`);
  let msgs = await toasts(cdp);
  // **النصُّ المشترَط كان محذوفًا عمدًا.** كان هذا التأكيدُ يبحث عن «لم أجد إعدادًا
  // يسبّب الإطارات» — وهي الجملةُ التي وُصِفت في `unicode-guard.js` بأنّها «الرسالةُ
  // التي كانت تكذب»: تنفي وجودَ سببٍ وقد يكون الإطارُ من قاعدةٍ منبعيّةٍ لا من إعداد.
  // والاختبارُ الوحدويُّ يمنعها صراحةً (`doesNotMatch(/لم أجد إعدادًا يسبّب/)`)، فكان
  // الحيُّ يشترط ما يمنعه الوحدويّ — أحمرَ منذ أُصلحت الرسالة ولا علاقةَ له بانحدار.
  //
  // والمرساةُ اليومَ أوّلُ جملةٍ في الرسالة الجديدة، وهي التي تحمل الحكم.
  ok(msgs.some(m => m.includes("لا شيءَ في إعداداتك يرسم هذه الإطارات")),
    "رسالةُ «لا شيءَ في إعداداتك يرسم هذه الإطارات» على حالةٍ نظيفة", JSON.stringify(msgs));
  ok(!msgs.some(m => m.includes("إطارًا أصفرَ حول الحروف")),
    "لا إنذارَ كاذبٌ على حالةٍ نظيفة", JSON.stringify(msgs));
  cdp.close(); kill(); await sleep(3000);

  // ═══ (٢) إعدادٌ **بنطاق لغة** يُظلِّل افتراضَنا ⇒ إنذارٌ ثمّ إزالةٌ فعليّة ═══
  writeUserSettings({
    "window.restoreWindows": "none",
    "[plaintext]": { [SETTING]: true },
  });
  log("إعدادٌ بنطاق [plaintext] يُظلِّل الافتراض: إعادة الإطلاق");
  launch();
  cdp = await attach();
  await sleep(9000);   // الإنذارُ يقع بعد onStartupFinished
  msgs = await toasts(cdp);
  ok(msgs.some(m => m.includes("إطارًا أصفرَ حول الحروف")),
    "الإنذارُ يقع على إعدادٍ بنطاق لغة (الحالةُ الوحيدة التي تُظلِّلنا)", JSON.stringify(msgs));

  const clicked = await clickToastButton(cdp, "أزِل الإطارات");
  ok(clicked, "زرُّ «أزِل الإطارات» موجودٌ في الإنذار");
  await sleep(2500);
  const after = readUserSettings();
  ok(after && (!after["[plaintext]"] || after["[plaintext]"][SETTING] === undefined),
    "الإزالةُ تمسح المفتاحَ **داخل** كتلة [plaintext] (overrideInLanguage يعمل)",
    JSON.stringify(after));
  ok(after && after["window.restoreWindows"] === "none",
    "لا تمسّ الإزالةُ إعداداتٍ أخرى", JSON.stringify(after));
  msgs = await toasts(cdp);
  // ‏«تمّ —» صارت «تمّ.» حين أُعيدت صياغةُ الرسالة. والشرطُ المهمُّ هو الثاني: أن
  // **تُسمّى** المفاتيحُ المُزالة — رسالةُ نجاحٍ لا تقول ماذا مسّت من إعداداتك أسوأُ
  // من صمت. فالمرساةُ تُشدّ إلى ذلك لا إلى علامة الترقيم.
  ok(msgs.some(m => m.includes("تمّ") && m.includes("أُزيل من إعداداتك") && m.includes("nonBasicASCII")),
    "رسالةُ النجاح تسمّي ما أُزيل", JSON.stringify(msgs));
  if (!KEEP) { cdp.close(); kill(); }
} catch (e) {
  console.error(`❌ خطأ تشغيليّ: ${e.message}`);
  kill();
  if (!KEEP) rmSync(tmp, { recursive: true, force: true });
  process.exit(2);
}

await sleep(1000);
if (!KEEP) rmSync(tmp, { recursive: true, force: true });
console.log(failed ? `─── ${failed} تأكيدًا فشل ───` : "─── كلّ تأكيدات AR-04 الحيّة نجحت ───");
process.exit(failed ? 1 : 0);
