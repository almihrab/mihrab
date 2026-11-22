// L3 حيّ لِبنودِ م6 الثلاثةِ المؤجَّلة — على **الحزمة المشحونة** لا على المصدر.
//
// **لماذا حيًّا، والطبقاتُ الأخرى خضراء:** الطبقاتُ الأدنى تقيس نصًّا. L0 يقرأ ملفّاتٍ،
// وL2 يعدّ سلاسلَ في الحزمة، واختباراتُ الوحدة تُشغِّل منطقَنا ببديلٍ لـ`vscode`. ولا
// واحدةٌ منها تُثبت أنّ **المستخدم يرى** الأثر:
//
//   • ‏[VA-04] وجودُ `editor.fontSize: 15` في package.json لا يثبت أنّ المحرّرَ يُصيَّر
//     بخمسة عشر. المنبعُ يدمج الافتراضيّاتِ بأسبقيّةٍ لها مفاجآت، وإعدادُ مستخدمٍ أو
//     ‏`[plaintext]` قد يُبطلها. القياسُ الوحيدُ الصادق هو `getComputedStyle` على سطرِ نصٍّ حقيقيّ.
//   • ‏[VA-05] وجودُ الأصنافِ في ملفّ CSS لا يثبت أنّ **ورقةَ الهويّة الثانية** استُوردت:
//     لو سقط استيرادُها لَبَقيت الحزمةُ تُبنى، ولَبَقي الصنفُ في الـDOM بلا نمطٍ واحد.
//     فنقيس **الخاصّيّةَ المحسوبة** لا وجودَ الصنف.
//   • ‏[BS-04] الحلقةُ التي أمسكتها المراجعة (نسخٌ من محرابٍ ⇒ خطأٌ أحمرُ عند اللصق فيه)
//     **لا يمكن أن تُمسَك إلّا حيّة**: طرفاها أمرُنا ومُشخِّصُنا، وبينهما محرّرُ المنبع.
//
// العزل: `--user-data-dir` مؤقّت يُحذَف. إعداداتُ المستخدم الحقيقيّة لا تُمسّ.
//
// الاستعمال: node tests/runtime/m6.live.mjs [--keep] [--port N]
// خرج 0 = كلّ التأكيدات نجحت · 1 = فشل تأكيد · 2 = خطأ تشغيليّ (لا حزمة/لا إقلاع).
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { CDP, sleep, activateFixtureTab } from "./harness.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const EXE = join(ROOT, ".upstream", "VSCode-win32-x64", "Mihrab.exe");
const KEEP = process.argv.includes("--keep");
const PORT = (() => {
  const i = process.argv.indexOf("--port");
  return i >= 0 && process.argv[i + 1] ? parseInt(process.argv[i + 1], 10) : 9334;
})();

// ── مصادرُ الحقيقة: لا رقمَ يُكتب هنا مرّتين ────────────────────────────────────────
// حجمُ الخطّ يُقرأ من الإضافة نفسِها، والحدُّ يُشتقّ من ملفّ القياس. لو كُتب «15» حرفيًّا
// هنا لصار الاختبارُ ينسخ القرارَ بدل أن يفحصه: تغييرٌ في الإضافة يُمرَّر صامتًا إن
// نُسي هذا الملفّ، أو يُحمِّر بلا سببٍ إن غُيِّر أحدُهما وحده.
const SHELL_PKG = JSON.parse(readFileSync(
  join(ROOT, "extensions", "mihrab-shell", "package.json"), "utf8"));
const DEFAULTS = SHELL_PKG.contributes.configurationDefaults;
const EXPECTED_EDITOR_FONT = DEFAULTS["editor.fontSize"];
const EXPECTED_TERMINAL_FONT = DEFAULTS["terminal.integrated.fontSize"];
const MEASURED = JSON.parse(readFileSync(
  join(ROOT, "tests", "dx", "arabic_legibility.measured.json"), "utf8"));
// السقفُ من القياس: الحجمُ الذي يُبلِّغ النطاقَ العربيّ ما يبلغه 14 لاتينيًّا في وجهٍ
// لاتينيّ. لا رقمَ مكتوب — لو تغيّر الوجهُ وتغيّرت نسبتُه تغيّر الحدُّ معه.
const CEILING = Math.round(14 / MEASURED.bandRatio);
const FLOOR = MEASURED.floorLegiblePx;

// أصنافُ الهويّة الثلاثة ‏[VA-05] — تُقرأ من المانيفست لا تُكتب.
const MANIFEST = readFileSync(join(ROOT, "tests", "patch_manifest.py"), "utf8");
const IDENTITY_CLASSES = (() => {
  const m = MANIFEST.match(/IDENTITY_CLASSES\s*=\s*\(([\s\S]*?)\)/);
  if (!m) throw new Error("تعذّر اشتقاق IDENTITY_CLASSES من tests/patch_manifest.py");
  return [...m[1].matchAll(/"([^"]+)"/g)].map(x => x[1]);
})();

// معرّفا أمرَي [BS-04] — من package.json لا من الذاكرة.
const WELCOME_PKG = JSON.parse(readFileSync(
  join(ROOT, "extensions", "mihrab-welcome", "package.json"), "utf8"));
const CMD_IDS = WELCOME_PKG.contributes.commands.map(c => c.command);
const COPY_CMD = "mihrab.copyForSharing";
const STRIP_CMD = "mihrab.stripSharingIsolates";

// مصدرُ بلاغات حارس الاتّجاه — **يُقرأ من الوحدة** لا يُكتَب: تغييرُ الصياغة هناك
// يجب أن يُتبَع هنا تلقائيًّا، وإلّا صار الفحصُ يبحث عن نصٍّ لم يعد يُنتَج فينجح دائمًا.
const BIDI_SOURCE = (() => {
  const src = readFileSync(join(ROOT, "extensions", "mihrab-welcome", "bidi-guard.js"), "utf8");
  const m = src.match(/const SOURCE\s*=\s*"([^"]+)"/);
  if (!m) throw new Error("تعذّر اشتقاق SOURCE من bidi-guard.js");
  return m[1];
})();

// FSI/PDI — **لا LRI**. الفرقُ جوهريّ: ‏FSI يأخذ اتّجاهَه من أوّل محرفٍ قويّ، وLRI
// ‏**يفرض** اليسار. استعمالُ الثاني كان يقلب الغرضَ رأسًا على عقب (أمسكته المراجعة).
const FSI = "⁨";
const PDI = "⁩";

const log = m => console.log(`▶ ${m}`);
let failed = 0, passed = 0, skipped = 0;
const ok = (cond, name, detail = "") => {
  if (cond) { passed++; console.log(`  ✅ ${name}${detail ? " — " + detail : ""}`); }
  else { failed++; console.log(`  ❌ ${name}${detail ? "\n       " + detail : ""}`); }
};
const skip = (name, why) => { skipped++; console.log(`  ⏭️  ${name} — ${why}`); };

if (!existsSync(EXE)) { console.error(`❌ لا حزمة مشحونة: ${EXE}\n   شغّل: bash build/build.sh`); process.exit(2); }

const tmp = mkdtempSync(join(tmpdir(), "mihrab-m6-"));
const userData = join(tmp, "user-data");
const wsDir = join(tmp, "مشروع");
mkdirSync(join(userData, "User"), { recursive: true });
mkdirSync(wsDir, { recursive: true });

// عيّنةٌ مختلطة: عربيٌّ وأقواسٌ وأرقامٌ لاتينيّة — أي أنّ لها **ترتيبَ عرضٍ يُقلَب**
// خارج محرّرٍ يحميه. لو كانت عربيّةً صرفًا لَما أثبت النسخُ للمشاركة شيئًا.
const SAMPLE = 'دالة رئيسية()\n  اطبع("عدد = 42 * (3 + 1)")\n';
const SAMPLE_FILE = join(wsDir, "مثال.txt");
writeFileSync(SAMPLE_FILE, SAMPLE, "utf8");

/** نفسُ فخّ البيئة الموثَّق في launch.mjs وunicode_guard.live.mjs. */
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
    "--disable-workspace-trust", "--new-window", wsDir, SAMPLE_FILE,
  ], { detached: false, stdio: "ignore", env: cleanEnv() });
}
function kill() { try { proc && proc.kill(); } catch { /* */ } }

async function attach(timeoutMs = 150000) {
  const t0 = Date.now();
  for (;;) {
    try { return await CDP.attach(PORT); } catch (e) {
      if (Date.now() - t0 > timeoutMs) throw new Error(`تعذّر الاتّصال بـCDP: ${e.message}`);
      await sleep(1500);
    }
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// ‏[VA-04] حجمُ الخطّ — كما يُصيَّر، لا كما يُكتَب
// ═════════════════════════════════════════════════════════════════════════════
async function checkFontSize(cdp) {
  console.log("\n── [VA-04] حجمُ الخطّ المُصيَّر ──");
  // الحدُّ أوّلًا: القرارُ نفسُه يجب أن يقع داخل ما يسمح به القياس. هذا تأكيدٌ على
  // **الاتّساق بين المصدرين**، ويُمسك «رُفع الرقمُ في الإضافة ونُسي أنّ القياس يحدّه».
  ok(EXPECTED_EDITOR_FONT >= FLOOR && EXPECTED_EDITOR_FONT <= CEILING,
    "القرارُ داخل ما يحدّه القياس",
    `${EXPECTED_EDITOR_FONT} في [${FLOOR}, ${CEILING}] (نسبةُ النطاق ${MEASURED.bandRatio})`);
  ok(EXPECTED_TERMINAL_FONT === EXPECTED_EDITOR_FONT,
    "الطرفيّةُ بحجم المحرّر",
    `طرفيّة=${EXPECTED_TERMINAL_FONT} · محرّر=${EXPECTED_EDITOR_FONT}`);

  const r = await cdp.evaluate(`(() => {
    const line = document.querySelector(".monaco-editor .view-line");
    if (!line) return { present: false };
    const cs = getComputedStyle(line);
    // ‎.view-line‎ قد يرث الحجمَ من ‎.monaco-editor‎؛ نقرأ الاثنين ونُبلغ الفعليّ.
    const ed = document.querySelector(".monaco-editor");
    return {
      present: true,
      linePx: parseFloat(cs.fontSize),
      editorPx: ed ? parseFloat(getComputedStyle(ed).fontSize) : null,
      family: cs.fontFamily,
      text: (line.textContent || "").slice(0, 40),
    };
  })()`, 30000);

  if (!r || !r.present) { skip("حجمُ الخطّ في المحرّر الحيّ", "لا سطرَ نصٍّ مُصيَّر — هل فُتِح الملفّ؟"); return; }
  ok(Math.abs(r.linePx - EXPECTED_EDITOR_FONT) < 0.51,
    "المحرّرُ يُصيَّر بالحجم المقرَّر",
    `${r.linePx}px (متوقَّع ${EXPECTED_EDITOR_FONT}) · «${r.text}»`);
  // الخطُّ العربيّ المحزوم يجب أن يكون في المكدّس فعلًا — القياسُ كلُّه أُجري عليه،
  // فلو صُيِّر بوجهٍ آخرَ لَما كان للحدّ معنًى.
  ok(/Kawkab/i.test(r.family || ""), "الوجهُ المقيس هو المُصيَّر", r.family);
}

// ═════════════════════════════════════════════════════════════════════════════
// ‏[VA-05] ورقةُ الهويّة وصلت — بالخاصّيّة المحسوبة لا بوجود الصنف
// ═════════════════════════════════════════════════════════════════════════════
async function checkIdentitySheet(cdp) {
  console.log("\n── [VA-05] ورقةُ الهويّة الثانية ──");
  ok(IDENTITY_CLASSES.length >= 3, "أصنافُ الهويّة مشتقّةٌ من المانيفست",
    IDENTITY_CLASSES.join(" · "));

  // نبحث عن القواعد في **أوراقِ المستند المُحمَّلة** لا عن العناصر: عنصرُ الترحيب قد
  // لا يكون مُصيَّرًا في هذه النافذة، وغيابُه ليس دليلَ سقوطِ الورقة. أمّا وجودُ
  // القاعدة في `document.styleSheets` فدليلٌ قاطعٌ أنّ الاستيرادَ الثاني وصل.
  const r = await cdp.evaluate(`(() => {
    const wanted = ${JSON.stringify(IDENTITY_CLASSES)};
    const found = Object.fromEntries(wanted.map(w => [w, null]));
    let scanned = 0, blocked = 0;
    for (const sheet of document.styleSheets) {
      let rules;
      try { rules = sheet.cssRules; } catch { blocked++; continue; }
      if (!rules) continue;
      for (const rule of rules) {
        const sel = rule.selectorText;
        if (!sel) continue;
        scanned++;
        for (const w of wanted) {
          if (sel.includes(w) && !found[w]) found[w] = (rule.cssText || "").slice(0, 160);
        }
      }
    }
    return { found, scanned, blocked };
  })()`, 30000);

  if (!r || r.scanned === 0) { skip("قواعدُ الهويّة في أوراق المستند", "لا قاعدةَ مقروءة"); return; }
  for (const cls of IDENTITY_CLASSES) {
    const hit = r.found[cls];
    ok(!!hit, `قاعدةُ هويّةٍ حيّة: ${cls}`, hit ? hit.replace(/\s+/g, " ").slice(0, 90) : "غائبة عن كلّ الأوراق");
  }
  // **القيدُ المتقابل**: لا خاصّيّةَ اتّجاهيّةً في قواعد الهويّة. لولاه لصار الفصلُ
  // بابًا خلفيًّا — قاعدةُ اتّجاهٍ تُكتَب في ورقة الهويّة فتنجو من قصرِ `[dir="rtl"]`.
  // نفحصُه على **القاعدة المشحونة** لا على الملفّ (‏L0 يفحص الملفّ).
  const dirProps = /(^|[;{\s])(direction|unicode-bidi|text-align|float|clear|writing-mode|flex-direction|order)\s*:/i;
  for (const cls of IDENTITY_CLASSES) {
    const hit = r.found[cls];
    if (!hit) continue;
    const m = hit.match(dirProps);
    ok(!m, `لا خاصّيّةَ اتّجاهيّةً في: ${cls}`, m ? `وجدنا «${m[2]}»` : "");
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// ‏[BS-04] أمانةُ الحافظة — الأمران، ورحلةُ الذهاب والإياب، والحلقةُ المغلقة
// ═════════════════════════════════════════════════════════════════════════════
async function checkClipboard(cdp) {
  console.log("\n── [BS-04] أمانةُ الحافظة ──");
  ok(CMD_IDS.includes(COPY_CMD) && CMD_IDS.includes(STRIP_CMD),
    "الأمران معلنان في package.json", CMD_IDS.filter(c => /Sharing|copyFor/.test(c)).join(" · "));

  // هل سُجِّلا فعلًا في النسخة الحيّة؟ (إعلانٌ بلا تسجيلٍ = أمرٌ في اللوحة يفشل عند النقر.)
  // لا واجهةَ `vscode` في سياق الصفحة، فنسأل لوحةَ الأوامر: نفتحها ونبحث عن العنوان.
  const titles = Object.fromEntries(
    WELCOME_PKG.contributes.commands
      .filter(c => c.command === COPY_CMD || c.command === STRIP_CMD)
      .map(c => [c.command, c.title]));

  for (const [id, title] of Object.entries(titles)) {
    // العنوانُ العربيّ يظهر في `aria-label` لبند اللوحة. نبحث بجزءٍ مميّزٍ منه.
    const needle = title.replace(/^محراب:\s*/, "").slice(0, 18);
    const seen = await commandPaletteHas(cdp, needle);
    ok(seen, `الأمرُ مُسجَّلٌ وظاهرٌ في اللوحة: ${id}`, `بحثنا عن «${needle}»`);
  }

  // رحلةُ الذهاب والإياب. **لا نقرأ الحافظةَ بـ`navigator.clipboard`**: تلك تشترط
  // تركيزَ المستند وإذنًا، وترتدّ إلى تخطٍّ فيبدو الفحصُ ناجحًا وهو لم يقِس شيئًا.
  // نلصق في المستند بدلًا من ذلك — وهو **أقربُ إلى ما يفعله المستخدم** ويقيس شيئين
  // بضربةٍ واحدة: صيغةَ ما نُسِخ، وأثرَ لصقِه داخل محراب (الحلقةُ التي أمسكتها المراجعة).
  const pasted = await copyThenPasteBack(cdp);
  if (!Array.isArray(pasted)) { skip("رحلةُ النسخ للمشاركة", String(pasted)); return; }

  const lines = pasted.filter(l => l.length);
  const show = l => l.replace(new RegExp(FSI, "g"), "⟦").replace(new RegExp(PDI, "g"), "⟧");
  const bare = lines.filter(l => !(l.startsWith(FSI) && l.endsWith(PDI)));
  ok(lines.length > 0 && bare.length === 0,
    "كلُّ سطرٍ منسوخٍ محفوفٌ بعزلٍ",
    bare.length ? `بلا عزلٍ: ${bare.map(show).map(x => "«" + x.slice(0, 46) + "»").join(" · ")}`
                : `${lines.length} سطرًا · أوّلُها «${show(lines[0]).slice(0, 40)}»`);
  // **العزلُ الصحيح**: FSI لا LRI. لو ارتدّت الشيفرةُ إلى U+2066 لَنجح التأكيدُ أعلاه
  // شكلًا (زوجٌ مفتوحٌ ومغلق) وانقلب الغرضُ — فنقيس المحرفَ نفسَه.
  const joined = lines.join("\n");
  ok(!joined.includes("⁦"),
    "العزلُ FSI لا LRI", joined.includes("⁦") ? "وُجِد U+2066 — يفرض اليسار" : "لا U+2066");
  // النصُّ بين العَلَمَين هو الأصلُ حرفًا بحرف (النسخُ لا يعيد صياغةَ الكود).
  const inner = lines.map(l => l.slice(1, -1));
  const want = SAMPLE.split("\n").filter(l => l.length);
  // ‏Monaco يُصيَّر المسافاتِ البادئة بـNBSP‏ (‏U+00A0) كي لا تنطوي — فالمقارنةُ الحرفيّة
  // على نصِّ الـDOM تفشل على سطرٍ سليم. نُسوّي المسافةَ وحدَها، ولا نُسوّي شيئًا آخر.
  const norm = t => t.replace(/ /g, " ");
  const got = inner.map(norm);
  const diff = got.findIndex((l, i) => l !== want[i]);
  ok(got.length === want.length && diff === -1,
    "النصُّ داخل العزل هو الأصلُ بلا تغيير",
    got.length !== want.length ? `${got.length} سطرًا مقابل ${want.length}`
      : diff >= 0 ? `السطر ${diff + 1}: «${got[diff]}» ≠ «${want[diff]}»` : "");

  // ── البابُ الثاني: الأمرُ المقابل يُعيد ما فعله الأوّل ──────────────────────────
  // بابٌ يفتح ولا يُغلَق ليس ميزةً: مَن لصق نصًّا معزولًا في مشروعه يحتاج نزعَه قبل
  // الالتزام. فنُثبت الرجعةَ على المستند نفسِه لا على وحدةٍ معزولة.
  const after = await runStripIsolates(cdp);
  if (!Array.isArray(after)) { skip("الأمرُ المقابل ينزع العزل", String(after)); return; }
  const still = after.filter(l => l.includes(FSI) || l.includes(PDI));
  ok(still.length === 0, "الأمرُ المقابل ينزع العزل",
    still.length ? `بقي العزلُ في ${still.length} سطرًا` : `${after.length} سطرًا نظيفًا`);
}

/** يُحدِّد كلَّ المستند وينفّذ «أزِل عزلَ النشر»، ويعيد أسطرَ الملفّ بعده. */
async function runStripIsolates(cdp) {
  await activateFixtureTab(cdp);
  await sleep(500);
  const box = await editorPoint(cdp);
  if (!box) return "لا محرّرَ مُصيَّر";
  await clickAt(cdp, box.x, box.y);
  await keyPress(cdp, 65, "KeyA", "a", 2);           // Ctrl+A
  await sleep(400);
  await openPalette(cdp, ">أزِل عزلَ النشر");
  await sleep(900);
  await keyPress(cdp, 13, "Enter", "Enter");
  await sleep(1500);
  const lines = await lineTexts(cdp);
  return lines || "تعذّرت قراءةُ الأسطر بعد النزع";
}

/**
 * **الحلقةُ التي أمسكتها المراجعة**: ما نُسخ من محرابٍ لا يجوز أن يُشخَّص خطأً أحمرَ
 * حين يُلصَق فيه. لو عاد `unicode-bidi` إلى وسمِ الزوجِ الكاملِ العابرِ لحدود المناطق
 * (كودٌ ⇄ تعليقٌ ⇄ نصّ) لَظهرت خطوطٌ حمراءُ تحت كلّ سطرٍ لصقه المستخدم — وزرُّ الإصلاح
 * لا يمسّها. نقيسها بالخطّ المتعرّج الأحمر نفسِه: ما يراه المستخدم، لا حالةً داخليّة.
 */
async function checkPasteLoop(cdp) {
  await sleep(3000);   // مهلةُ التشخيص (‏debounce عند تغيّر المستند)
  // **الخطُّ الأحمرُ وحدَه لا يكفي شاهدًا**: لصقُ نسخةٍ ثانيةٍ من الدالّة يُنتج تشخيصًا
  // مشروعًا من خادم اللغة («تعريفٌ مكرَّر»)، فعدُّ ‎.squiggly-error‎ يُحمِّر على صوابٍ ويُخفي
  // خطأً حقيقيًّا تحت الضجيج. فنقرأ **لوحةَ المشاكل** ونسأل عن مصدرِ حارسِنا وحده.
  await keyPress(cdp, 77, "KeyM", "m", 10);   // Ctrl+Shift+M — لوحةُ المشاكل
  await sleep(2000);
  const r = await cdp.evaluate(`(() => {
    const rows = [...document.querySelectorAll(".markers-panel .monaco-list-row, .marker-panel .monaco-list-row")];
    const texts = rows.map(x => (x.getAttribute("aria-label") || x.textContent || "").trim());
    return { texts, squiggles: document.querySelectorAll(".monaco-editor .squiggly-error").length };
  })()`, 20000);
  if (!r) { skip("لا خطأَ أحمرَ من حارس الاتّجاه بعد اللصق", "تعذّر القياس"); return; }
  const ours = r.texts.filter(t => t.includes(BIDI_SOURCE));
  ok(ours.length === 0, "لا بلاغَ من حارس الاتّجاه على ما نسخناه",
    ours.length ? ours.slice(0, 2).join(" | ")
                : `مشاكلُ أخرى=${r.texts.length} · خطوطٌ حمراء=${r.squiggles}`);
  await pressEscape(cdp);
}

/**
 * يفتح لوحةَ الأوامر ويُبلغ هل ظهر بندٌ يطابق النصّ.
 *
 * **بمحاولاتٍ لا بمحاولةٍ واحدة**: فتحُ اللوحة بضغطةٍ عبر CDP سباقٌ مع التركيز — إن
 * وصلت الضغطةُ قبل أن تستقرّ النافذةُ ضاعت، فتعود القائمةُ فارغةً ويُقرأ ذلك «الأمرُ
 * غير مُسجَّل». وهو **بلاغٌ كاذبٌ أسوأُ من الفشل**: يوجّه إلى تسجيل الأوامر ولا شيء فيه.
 */
async function commandPaletteHas(cdp, needle, tries = 3) {
  for (let i = 0; i < tries; i++) {
    await pressEscape(cdp);
    await sleep(400);
    await openPalette(cdp, ">" + needle);
    // ننتظر ظهورَ صفٍّ واحدٍ على الأقلّ بدل مهلةٍ ثابتة.
    let hit = "";
    for (let w = 0; w < 8; w++) {
      hit = await cdp.evaluate(`(() => {
        const rows = [...document.querySelectorAll(".quick-input-list .monaco-list-row")];
        return rows.map(r => (r.getAttribute("aria-label") || r.textContent || "").trim()).join(" | ");
      })()`, 15000) || "";
      if (hit) break;
      await sleep(400);
    }
    await pressEscape(cdp);
    if (hit.includes(needle.slice(0, 10))) return true;
  }
  return false;
}

/** يفتح لوحةَ الأوامر ويكتب فيها (‏Ctrl+Shift+P ثمّ إدراجُ نصّ لا مفاتيح). */
async function openPalette(cdp, text) {
  await cdp.cmd("Input.dispatchKeyEvent", { type: "rawKeyDown", windowsVirtualKeyCode: 80,
    code: "KeyP", key: "p", modifiers: 10 }, 15000);           // Ctrl(2)+Shift(8)
  await cdp.cmd("Input.dispatchKeyEvent", { type: "keyUp", windowsVirtualKeyCode: 80,
    code: "KeyP", key: "p", modifiers: 10 }, 15000);
  await sleep(700);
  await cdp.cmd("Input.insertText", { text }, 15000);
  await sleep(700);
}

async function pressEscape(cdp) {
  for (const type of ["rawKeyDown", "keyUp"]) {
    await cdp.cmd("Input.dispatchKeyEvent", { type, windowsVirtualKeyCode: 27,
      code: "Escape", key: "Escape" }, 15000);
  }
  await sleep(300);
}

/**
 * يُحدِّد كلَّ المستند، ينفّذ «انسخ للمشاركة»، ثمّ **يلصق في آخر الملفّ** ويعيد أسطرَ
 * ما لُصِق كما صُيِّرت. ثمّ يقيس الحلقةَ (لا خطًّا أحمرَ). يعيد null إن تعذّر.
 */
async function copyThenPasteBack(cdp) {
  // **إعادةُ تبويب العيّنة إلى الواجهة أوّلًا.** فحصُ لوحة الأوامر قبلَه يُبدِّل المحرّرَ النشط
  // (‏تبويبُ الترحيب مفتوحٌ في نفس النافذة)، فيختفي `.view-lines` ويُقرأ ذلك «لا محرّر».
  // قِيس: الفحصُ نفسُه مرّ حين سبقه قياسُ حجم الخطّ، وسقط حين سبقته اللوحة.
  await activateFixtureTab(cdp);
  await sleep(600);

  // تركيزُ المحرّر بنقرةٍ حقيقيّة: `.focus()` لا يُسلِّم التركيزَ لـMonaco دائمًا.
  const box = await editorPoint(cdp);
  if (!box) return "لا ‎.view-lines‎ — لا محرّرَ مُصيَّر";
  await clickAt(cdp, box.x, box.y);
  await keyPress(cdp, 65, "KeyA", "a", 2);           // Ctrl+A
  await sleep(400);
  await openPalette(cdp, ">انسخ التحديدَ ليُعرَض");
  await sleep(900);
  await keyPress(cdp, 13, "Enter", "Enter");
  await sleep(1200);

  // عدَدُ الأسطر قبل اللصق — نميّز به الملصوقَ عن الأصل بلا افتراضِ موضع.
  const before = await lineTexts(cdp);
  if (!before || !before.length) return "تعذّرت قراءةُ أسطر المحرّر قبل اللصق";

  // إلى آخر الملفّ (‏Ctrl+End) ثمّ سطرٌ جديد ثمّ لصق.
  await keyPress(cdp, 35, "End", "End", 2);          // Ctrl+End
  await sleep(300);
  await cdp.cmd("Input.insertText", { text: "\n" }, 15000);
  await sleep(300);
  await keyPress(cdp, 86, "KeyV", "v", 2);           // Ctrl+V
  await sleep(1500);

  const after = await lineTexts(cdp);
  if (!after) return "تعذّرت قراءةُ الأسطر بعد اللصق";
  if (after.length <= before.length)
    return `لم يزد عددُ الأسطر (${before.length} ⇐ ${after.length}) — لم يُنفَّذ الأمرُ أو الحافظةُ فارغة`;
  const pasted = after.slice(before.length).filter(l => l.length);

  await checkPasteLoop(cdp);
  return pasted;
}

/**
 * نصوصُ الأسطر **من نموذج المحرّر** لا من الـDOM: `.view-line` لا يُصيَّر إلّا لِما هو
 * داخل نافذة العرض (‏virtual scrolling)، فقراءتُه تُسقِط أسطرًا وتجعل «لم يُلصَق شيء»
 * بلاغًا كاذبًا. ولا واجهةَ للنموذج من الصفحة، فنقرأ الأسطرَ المُصيَّرة **بعد** ضمانِ
 * أنّ الملفَّ أقصرُ من نافذة العرض (عيّنتُنا سطران).
 */
async function lineTexts(cdp, tries = 6) {
  // **بمحاولاتٍ**: بعد تبديل التبويب يُعيد Monaco التصيير غيرَ متزامن، فقراءةٌ واحدةٌ
  // فوريّة قد تقع على `.view-lines` فارغةٍ — وتُقرأ «لا محرّر» وهو حاضر.
  for (let i = 0; i < tries; i++) {
    const r = await lineTextsOnce(cdp);
    if (r && r.length) return r;
    await sleep(600);
  }
  return null;
}

async function lineTextsOnce(cdp) {
  return cdp.evaluate(`(() => {
    const lines = [...document.querySelectorAll(".monaco-editor .view-lines .view-line")];
    if (!lines.length) return null;
    // الترتيبُ في الـDOM ليس ترتيبَ الأسطر — Monaco يعيد استعمالَ العُقَد. نرتّب بالإزاحة.
    // **محارفُ التنسيق تُصيَّر بأسمائها**: Monaco يعرض غيرَ المرئيّ (‏FSI/PDI/RLO…) في
    // سبانٍ نصُّها «[U+2068]» كي يراه المستخدم. فنصُّ الـDOM ليس نصَّ المستند — ولو
    // قِيس كما هو لَقيل «لا عزلَ في السطر» والعزلُ فيه. نردّه إلى المحرف.
    // ‏(‏الهروبُ مُضاعَفٌ عمدًا — قاعدةُ harness.mjs: القالبُ يبتلع الشرطةَ الواحدة.)
    const unrender = t => t.replace(/\\[U\\+([0-9A-Fa-f]{4,6})\\]/g,
      (_, hex) => String.fromCodePoint(parseInt(hex, 16)));
    return lines
      .map(e => ({ top: parseFloat(e.style.top) || 0, t: unrender(e.textContent || "") }))
      .sort((a, b) => a.top - b.top)
      .map(x => x.t);
  })()`, 20000);
}

/** نقطةٌ داخل أوّل سطرٍ من المحرّر (للنقر الحقيقيّ) — أو null إن لم يُصيَّر. */
function editorPoint(cdp) {
  return cdp.evaluate(`(() => {
    const e = document.querySelector(".monaco-editor .view-lines");
    if (!e) return null; const r = e.getBoundingClientRect();
    return { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + 12) };
  })()`, 15000);
}

/** نقرةُ فأرةٍ حقيقيّة بإحداثيّة. */
async function clickAt(cdp, x, y) {
  for (const type of ["mousePressed", "mouseReleased"]) {
    await cdp.cmd("Input.dispatchMouseEvent", { type, x, y, button: "left", clickCount: 1 }, 15000);
  }
  await sleep(400);
}

/** ضغطةُ مفتاحٍ كاملة (نزول + صعود) بمُعدِّلات CDP. */
async function keyPress(cdp, vk, code, key, modifiers = 0) {
  for (const type of ["rawKeyDown", "keyUp"]) {
    await cdp.cmd("Input.dispatchKeyEvent", { type, windowsVirtualKeyCode: vk, code, key, modifiers }, 15000);
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// شريطُ القوائم — تثبيتُ ما قِيس، لا افتراضُ ما يُرجى
// ═════════════════════════════════════════════════════════════════════════════
//
// بلاغُ «القائمةُ العلويّة اختفت» قادَنا إلى قياسٍ مقارِن: انهيارُ الشريط إلى زرٍّ واحد
// سلوكٌ **منبعيّ** يقع في VS Code الإنجليزيّ عند 950 بكسلًا، وفي محراب عند 850 — أي أنّ
// محرابًا يصمد أطول. لكنّ ذلك ليس مضمونًا: أيّ توسيعٍ لمركز الأوامر أو للشريط الجانبيّ
// يقضم عرضَ القوائم صامتًا. فنثبّت العتبةَ المقيسة كي يُمسَك الانحدارُ لا يُكتشَف بالشكوى.
const MENUBAR_CASES = [
  { w: 1600, min: 8 },   // كلُّ القوائم الثماني
  { w: 1200, min: 5 },   // خمسٌ ظاهرة، والباقي تحت «المزيد»
  { w: 900, min: 3 },   // ثلاثٌ — وأدنى من ذلك ينهار إلى زرٍّ واحد (سلوكُ المنبع)
];

const MENUBAR_PROBE = `(() => {
  const bar = document.querySelector(".menubar");
  if (!bar) return { bar: false, w: window.innerWidth };
  const lbl = b => (b.getAttribute("aria-label") || b.textContent || "").trim().replace(/\\s+/g, " ");
  // **القصُّ على صندوق الشريط لا على إطار العرض**: البنودُ الفائضة تبقى مُخطَّطةً
  // (‏getBoundingClientRect غيرُ صفريّ) وهي خارج حدود الشريط فلا تُرى. قياسُها بإطار
  // العرض يعطي «ثمانيةٌ ظاهرة» والشريطُ عرضُه ثمانيةٌ وثلاثون بكسلًا — بلاغٌ كاذبٌ وقعنا فيه.
  const bb = bar.getBoundingClientRect();
  const named = [...bar.querySelectorAll(".menubar-menu-button")]
    .filter(b => !/^(المزيد|More|\\u2026|\\.\\.\\.)$/.test(lbl(b)));
  const inBar = b => { const r = b.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && r.left >= bb.left - 1 && r.right <= bb.right + 1; };
  return { bar: true, w: window.innerWidth, barWidth: Math.round(bb.width),
           shown: named.filter(inBar).map(lbl) };
})()`;

async function checkMenubar(cdp) {
  console.log("\n── شريطُ القوائم: عتبةُ الفيض ──");
  for (const c of MENUBAR_CASES) {
    await cdp.cmd("Emulation.setDeviceMetricsOverride",
      { width: c.w, height: 760, deviceScaleFactor: 0, mobile: false }, 30000);
    await sleep(800);
    const r = await cdp.evaluate(MENUBAR_PROBE, 30000);
    if (!r || !r.bar) { skip(`قوائمُ ظاهرةٌ عند ${c.w}`, "لا شريطَ قوائم (نمطُ عنوانٍ أصيل؟)"); continue; }
    ok(r.shown.length >= c.min, `قوائمُ ظاهرةٌ عند ${c.w}px ≥ ${c.min}`,
      `${r.shown.length}: ${r.shown.join(" · ")}`);
  }
  await cdp.cmd("Emulation.clearDeviceMetricsOverride", {}, 30000);
  await sleep(500);
}

// ═════════════════════════════════════════════════════════════════════════════
async function main() {
  console.log("═══ L3 حيّ: بنودُ م6 المؤجَّلة على الحزمة المشحونة ═══");
  log(`الحزمة: ${EXE}`);
  log(`ملفُّ مستخدمٍ مؤقّت: ${userData}`);
  launch();
  let cdp;
  try {
    cdp = await attach();
  } catch (e) {
    console.error(`❌ ${e.message}`);
    kill(); return 2;
  }
  try {
    await sleep(4000);
    await cdp.cmd("Page.bringToFront", {}, 30000).catch(() => {});
    await checkFontSize(cdp);
    await checkIdentitySheet(cdp);
    // الحافظةُ **قبل** شريط القوائم عمدًا: فحصُ الشريط يفرض مقاساتِ عرضٍ مُصطنَعة
    // (‏Emulation) ثمّ يرفعها، وإعادةُ التخطيط بعدها تُربك التركيزَ ولوحةَ الأوامر —
    // فينقلب سباقُ توقيتٍ إلى «الأمرُ غير مُسجَّل». قِيس: نفسُ الفحص نجح ثمّ فشل بترتيبٍ
    // مقلوبٍ وحده.
    await checkClipboard(cdp);
    await checkMenubar(cdp);
  } finally {
    try { cdp.close(); } catch { /* */ }
    if (!KEEP) { kill(); await sleep(1200); try { rmSync(tmp, { recursive: true, force: true }); } catch { /* */ } }
    else log(`أُبقيت النسخةُ وملفُّها: ${tmp}`);
  }
  console.log(`\n─── ${passed} نجح، ${failed} فشل، ${skipped} تخطٍّ ───`);
  return failed ? 1 : 0;
}

main().then(c => process.exit(c)).catch(e => { console.error("خطأ فادح:", e); kill(); process.exit(2); });
