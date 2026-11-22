// L3 حيّ ‏[PR-01]: هل يُستعمَل الخطُّ المُضمَّن **عند الطباعة** فعلًا؟
//
// ## لماذا لم تكفِ اختباراتُ الوحدة
// تسعةَ عشرَ تأكيدًا وحدويًّا كانت خضراءَ، ومنها «الخطُّ يُدرَج في @font-face بحمولته
// كاملةً» — و**الخطُّ كان يُضمَّن ولا يُستعمَل**. لأنّ `code` و`mark` تحملان من ورقةِ
// الوكيل `font-family: monospace`، وهي **قاعدةُ عنصرٍ تغلب الوراثةَ** من `body`. فكانت
// أسطرُ الشيفرة — وهي كلُّ المحتوى — تُطبَع بـConsolas، و‎145‎ ك.ب تُحمَل بلا أثر.
//
// ولا يمسك ذلك تأكيدٌ نصّيّ: الحمولةُ حاضرةٌ كاملةً، والـCSS سليمُ الصياغة، والملفُّ
// يُفتَح ويُعرَض. **الفرقُ لا يظهر إلّا في ما رُسِم**. وهذا هو الشكلُ نفسُه الذي تكرّر
// في هذا المستودع: يُحكَم بالحبر لا بالإعلان.
//
// ## المِسطرة: ذراعان — وإحداهما **يجب أن تفشل**
// لا يُقاس «هل Kawkab في الـPDF؟» مباشرةً: كروميوم يُدرِج الخطَّ المُضمَّن **Type3**
// (إجراءاتُ رسمٍ لكلّ محرف) فلا اسمَ له في `/BaseFont` أصلًا — فتأكيدٌ على اسمه يفشل
// دائمًا، وتأكيدٌ على وجود `Type3` ينجح دائمًا (العناوينُ والحاشيةُ ترثه من `body` حتّى
// حين تسقط أسطرُ الشيفرة).
//
// فالفارقُ الحقيقيُّ **سالب**: إن طُبِّق الخطُّ فلا يبقى خطٌّ أحاديٌّ احتياطيٌّ في المستند.
// وتأكيدٌ سالبٌ لا يُقرأ بلا شاهدٍ يُثبِت أنّه قادرٌ على الفشل — فتُطبَع **ذراعٌ ضابطة**
// حُذفت منها قاعدةُ الخطّ: يجب أن يظهر فيها الاحتياطيُّ. فإن لم يظهر في الذراعين معًا،
// فالمِسطرةُ لا تقيس شيئًا والنتيجةُ «لم يقع القياس» لا «الخطُّ يعمل».
//
// الاستعمال: node tests/runtime/print_export.live.mjs
// خرج 0 = القياسُ تمّ · 1 = تأكيدٌ فشل · 2 = خطأ تشغيليّ / لا متصفّح (تخطٍّ **معلَن**).

import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const require_ = createRequire(import.meta.url);
const EXT = join(ROOT, "extensions", "mihrab-welcome");
const SHIPPED = join(ROOT, ".upstream", "VSCode-win32-x64", "resources", "app", "extensions", "mihrab-welcome");

let failed = 0;
const ok = (c, n, d = "") => { if (c) console.log(`  ✅ ${n}${d ? " — " + d : ""}`); else { failed++; console.log(`  ❌ ${n}${d ? "\n       " + d : ""}`); } };

console.log("╔══ [PR-01] الخطُّ المُضمَّن عند الطباعة ══╗");

const BROWSERS = [
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
];
// **الوجودُ ليس قدرة.** كان الاختيارُ `BROWSERS.find(existsSync)` — أوّلُ موجودٍ يفوز.
// وقِيس على هذا الجهاز أنّ Edge موجودٌ ويخرج بالرمز **صفر** ولا يكتب PDF: طباعةٌ صامتةٌ
// فاشلة. فكان المِجَسُّ يسقط بالرمز 2 («خطأٌ تشغيليّ») وكروم بجانبه يعمل — أي أنّ
// تغطيةَ PR-01 كانت مفقودةً على كلّ جهازٍ فيه Edge، وهو كلُّ جهاز ويندوز.
//
// فالاختيارُ بالقياس: تُطبَع صفحةٌ تافهةٌ بكلّ مرشَّحٍ ويفوز أوّلُ من **أنتج ملفًّا**.
// والمرشَّحُ الواحدُ يُستعمَل للذراعين معًا — ذراعان بمحرّكَي طباعةٍ مختلفَين لا تُقارَنان.
function probeBrowser() {
  const probeDir = mkdtempSync(join(tmpdir(), "mihrab-probe-"));
  const h = join(probeDir, "p.html");
  writeFileSync(h, "<html><body><p>p</p></body></html>", "utf8");
  const tried = [];
  for (const b of BROWSERS.filter(existsSync)) {
    const p = join(probeDir, `p-${tried.length}.pdf`);
    spawnSync(b, ["--headless=new", "--disable-gpu", "--no-sandbox", `--print-to-pdf=${p}`, h],
      { encoding: "utf8", timeout: 60_000, windowsHide: true });
    if (existsSync(p)) return { browser: b, tried };
    tried.push(b);
  }
  return { browser: null, tried };
}
const { browser, tried: mute } = probeBrowser();
if (!browser) {
  console.log(mute.length
    ? `mode=skipped — لا متصفّحَ Chromium **يطبع**: ${mute.length} موجودًا وكلُّها صامتة (${mute.join(", ")})`
    : "mode=skipped — لا متصفّحَ Chromium للطباعة (هذا ليس نجاحًا: لم يُطبَع شيء)");
  process.exit(2);
}
if (mute.length) console.log(`  ℹ️  تُخُطِّي ${mute.length} متصفّحًا لا يكتب PDF (خرجَ صفرًا صامتًا): ${mute.join(", ")}`);

const { buildPrintHtml } = require_(join(EXT, "print-export.js"));
const { loadFontDataUri } = require_(join(EXT, "bundled-font.js"));

// الخطُّ من **الحزمة المشحونة**: `media/` مصنوعُ بناءٍ غيرُ متتبَّعٍ في git، فمصدرُ الشجرة لا يحويه.
let fontDataUri;
try { fontDataUri = loadFontDataUri(SHIPPED, { required: true }); }
catch (e) { console.log(`mode=skipped — ${e.message.split("\n")[0]}`); process.exit(2); }

const SAMPLE = [
  "دالة نصاب_الفضة(الوزن) {",
  "  // تحقّقٌ من الحدّ الأدنى\u202E — لاحظ ما بعده",
  "  إذا (الوزن >= 595) { أرجِع صحيح; }",
  "  اطبع(«لم يبلغ النصاب\u200F»);",
  "}",
].join("\n");

const work = mkdtempSync(join(tmpdir(), "mihrab-print-"));
const html = buildPrintHtml(SAMPLE, { fileName: "نصاب.txt", fontDataUri, exportedAt: "—" });

/**
 * الذراعُ الضابطة: القاعدةُ التي تفرض الخطَّ على العناصر تُحذَف — لا الخطُّ نفسُه.
 * (‏حذفُ الخطّ يجعل الفرقَ بديهيًّا ولا يشهد لشيء؛ المطلوب أن تُقاس القاعدةُ بعينها.)
 */
const FORCE_RE = /\n\s*body, code, mark, \.line, \.num \{ font-family:[^\n]*\n/;
ok(FORCE_RE.test(html), "قاعدةُ فرضِ الخطّ حاضرةٌ في المُصدَّر", "وهي التي تُحذَف في الذراع الضابطة");
const control = html.replace(FORCE_RE, "\n");

/** أسماءُ خطوطٍ **حقيقيّةٍ** لا تظهر إلّا إن سقط النصُّ إليها. Type3 لا اسمَ له فلا يُعدّ. */
const FALLBACKS = /Consolas|Courier|Menlo|DejaVuSansMono|LucidaConsole|SegoeUI|TimesNewRoman/i;

function printToPdf(source, name) {
  const h = join(work, name + ".html"), p = join(work, name + ".pdf");
  writeFileSync(h, source, "utf8");
  const r = spawnSync(browser, ["--headless=new", "--disable-gpu", "--no-sandbox", `--print-to-pdf=${p}`, h],
    { encoding: "utf8", timeout: 90_000, windowsHide: true });
  if (!existsSync(p)) { console.error(`❌ لم يُنتَج PDF لـ${name}: ${(r.stderr || "").split("\n").slice(-3).join(" ")}`); process.exit(2); }
  const d = readFileSync(p);
  return {
    bytes: d.length,
    baseFonts: [...new Set([...d.toString("latin1").matchAll(/\/BaseFont\s*\/([A-Za-z0-9+\-]+)/g)].map(m => m[1]))],
    type3: (d.toString("latin1").match(/\/Type3/g) || []).length,
    toUnicode: d.includes(Buffer.from("/ToUnicode")),
  };
}

const armOn = printToPdf(html, "on");
const armOff = printToPdf(control, "off");

const monoOn = armOn.baseFonts.filter(f => FALLBACKS.test(f));
const monoOff = armOff.baseFonts.filter(f => FALLBACKS.test(f));
console.log(`\n  مع القاعدة : ${armOn.baseFonts.join(", ") || "(لا خطَّ مسمًّى)"}`);
console.log(`  بحذفِها    : ${armOff.baseFonts.join(", ") || "(لا خطَّ مسمًّى)"}`);

// **الشاهدُ أوّلًا**: بلا ذراعٍ ضابطةٍ تفشل، التأكيدُ التالي بلا معنى.
ok(monoOff.length > 0, "شاهدُ المِسطرة: الذراعُ الضابطةُ تسقط إلى خطٍّ احتياطيّ",
  monoOff.join(", ") || "لم تسقط — فالمِسطرةُ لا تميّز، ولا يُقرأ التأكيدُ بعدها");
if (monoOff.length === 0) {
  console.log("\n       لا يُقرأ تأكيدٌ سالبٌ بعد شاهدٍ ساقط. القياسُ **لم يقع**.");
  rmSync(work, { recursive: true, force: true });
  process.exit(1);
}

ok(monoOn.length === 0, "بالقاعدة: لا خطَّ احتياطيًّا في المستند ⇒ المُضمَّنُ هو المستعمَل",
  monoOn.length ? `ما يزال يسقط إلى: ${monoOn.join(", ")} — الخطُّ يُحمَل ولا يُستعمَل` : "");
ok(armOn.type3 > 0, "الخطُّ المُضمَّنُ مُدرَجٌ في الـPDF (‏Type3)", `${armOn.type3} كائنًا`);
ok(armOn.toUnicode, "‏ToUnicode حاضرٌ ⇒ النصُّ يبقى مستخرَجًا وقابلًا للبحث في الـPDF",
  "وإلّا صارت الورقةُ صورةً لا دليلَ مراجعة");

console.log(`\n  الحجم: HTML ${(html.length / 1024).toFixed(1)} ك.ب · PDF ${(armOn.bytes / 1024).toFixed(1)} ك.ب`);
rmSync(work, { recursive: true, force: true });
console.log(failed === 0 ? "\n╚══ ✅ الخطُّ يُطبَع فعلًا ══╝" : "\n╚══ ❌ تأكيدٌ فشل ══╝");
process.exit(failed === 0 ? 0 : 1);
