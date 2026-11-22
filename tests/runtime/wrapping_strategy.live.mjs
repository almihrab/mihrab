// L3 حيّ ‏[IN-02/أ]: مِسطرةُ الالتفاف — هل تنكسر الأسطرُ العربيّةُ في مكانها، وبكم؟
//
// ## المسألة — وكيف قلبها القياسُ عن صياغتها الأولى
// ‏`editor.wrappingStrategy` افتراضُه `simple` ⇒ `MonospaceLineBreaksComputer`، وهو **يفترض
// أنّ كلَّ محرفٍ بعرضِ واحد** (‏`monospaceLineBreaksComputer.ts:81-97`). وعلّةُ البند كما
// كُتبت: «العربيّةُ متّصلةٌ متغيّرةُ العرض فالفرضُ باطل».
//
// **والعلّةُ بهذه الصياغة مُكذَّبة.** المستودعُ نفسُه قرأ `hmtx` من الخطّ المشحون
// (‏`patches/fonts/README.md`): كلُّ محرفٍ أساسيٍّ في Kawkab Mono عرضُه ‎700‎ — «ا» و«م»
// و«ص» و`M` و`0` سواءً — و`PANOSE byte3 = 9`. أي أنّ الفرضَ **صحيحٌ بالخطّ الذي نشحنه**،
// وأنّ الوصفَ «متغيّرةُ العرض» يصف مكدَّسَ السقوط لا خطَّنا. وأثبت القياسُ ذلك: على عربيّةٍ
// خالصة (`--case pure`) تكسر المِسطرتان في **الموضع نفسِه بالضبط**، وملؤُهما ‎95%‎ كلتاهما.
//
// **والعطبُ الحقيقيُّ في مكانٍ آخر: التشكيل.** محارفُ التشكيل عرضُها ‎0‎ عند الرسم
// (‏`README` نفسُه يقولها)، و`simple` يعدّ كلًّا منها ‎1‎. فكلَّما كثُر التشكيلُ بولغ في
// تقدير عرض السطر فكُسر مبكّرًا:
//     عربيّةٌ خالصة        simple ‎95%‎ ملءً · advanced ‎95%‎  ⇒ لا فرق
//     + لاتينيٌّ وأرقام     simple ‎94%‎ · advanced ‎95%‎        ⇒ لا فرق
//     تشكيلٌ خفيف          simple ‎85%‎ · advanced ‎95%‎        ⇒ ‎10%‎ مهدرة
//     تشكيلٌ كامل          simple ‎50%‎ · advanced ‎95%‎        ⇒ **نصفُ السطر بياضٌ ضائع**
// والمنبعُ يصف `advanced` بأنّه «بطيءٌ قد يُجمِّد الملفّاتِ الكبيرة» (‏`editorOptions.ts:3087`)
// — وقِيس فصدق: ‎≈0.17‎ مللي لكلِّ سطرِ نموذج، حجبًا متزامنًا للخيط الرئيسيّ.
//
// ## لماذا لم يكفِ مِجَسُّ الإقلاع [PF-01]
// `advanced` يبدّل **حاسبَ كسرِ السطر**، وكلفتُه في تخطيط المحرّر لا في بناء القشرة.
// فميزانيّةُ الإقلاع تبقى خضراءَ والمحرّرُ صار أبطأَ أضعافًا على عيّنةٍ طويلةِ الأسطر.
// هذا الملفُّ يقيس **ما يتغيّر فعلًا**.
//
// ## «لم تختلفا» — نتيجةٌ أم قياسٌ لم يقع؟ (‏`--case canary`‏)
// أخطرُ التباسٍ هنا أنّ **حالتين متناقضتين تُنتجان الخرجَ نفسَه**: «المِسطرتان اتّفقتا»
// (نتيجةٌ ثمينة — وهي ما حدث فعلًا في `pure` و`mixed`) و«الإعدادُ لم يبلغ المحرّرَ أصلًا»
// (قياسٌ لم يقع). ولذلك حالةٌ مستقلّة `--case canary`: نصٌّ مُشكَّلٌ كاملًا **يجب** أن تختلف
// عليه المِسطرتان (‏التشكيلُ صفرُ العرض و`simple` يعدّه واحدًا). فإن اختلفتا عليه فالآليّةُ
// عاملةٌ والإعدادُ واصل، وكلُّ تطابقٍ في حالةٍ أخرى **نتيجةٌ لا عطبٌ في الأداة**.
//
// ## ولماذا لا يُقاس الصوابُ بمعيارٍ ثنائيّ
// أوّلُ صياغةٍ حكمت «هل كانت الكلمةُ التاليةُ تسع؟» بعنصرٍ مُصطنَعٍ يُقاس عرضُه — فأعطت
// **صفرَ عطبٍ** في حالةٍ نسبةُ ملئها ‎51%‎: تأكيدٌ لا يفشل. فحلّت محلَّها **نسبةُ الملء**
// المتّصلة (حبرُ السطر ÷ عرضِ منطقة المحتوى): تُري الرقمَ بدل أن تحكم به.
// وارتفاعُ `.lines-content` **لا يصلح** شاهدًا كذلك: ثابتٌ ‎2^24‎ دائمًا (حاويةٌ لأسطرٍ
// مُطلَقةِ الموضع) — شاهدٌ ينجح صامتًا مهما تبدّلت المِسطرة. قِيس فسقط.
//
// ## التداخلُ لا التكتيل
// التشغيلُ ABAB لا AAAA/BBBB: الانجرافُ الحراريّ وحملُ الخلفيّة ومسحُ مضادِّ الفيروسات
// كلُّها تتراكم مع الزمن، وفي التكتيل تُسنَد **كلُّها** إلى الذراع الثانية فتبدو أبطأَ
// بذنبِ ترتيبها لا بذنبِ خوارزميّتها. والذراعان في **العمليّة نفسِها** ⇒ لا فرقَ في حالة
// JIT ولا في ذاكرة الشيفرة.
//
// ## ما يُقاس بالضبط
// حسابُ الكسر **متزامنٌ ويشمل كلَّ الأسطر** عند تغيُّر إعدادات الالتفاف
// (‏`viewModelImpl.ts:278` ⇒ `setWrappingSettings` ⇒ إعادةُ بناء الأسطر كلِّها). فتبديلُ
// الإعداد نفسُه هو المُستحِثّ — لا مُستحِثَّ صناعيّ — ويُقاس **أطولُ حجبٍ للخيط الرئيسيّ**
// خلاله: أكبرُ فجوةٍ بين إطارَي رسمٍ متتاليين. هذا ما يشعر به المستخدم تجمُّدًا.
//
// ## الفرقُ المطلقُ هو الرقمُ الذي يصمد
// تُطبَع النِّسَبُ (وسيطُ النِّسَب لا نسبةُ الوسيطين) لكنّ **القرارَ يُبنى على الفرق المطلق
// والميل** ‎≈0.17‎ مللي/سطر: مقامُ النسبة (‏`simple` ‎≈25‎ مللي) داخلٌ في تشتّتِ القياس نفسِه،
// فنسبةٌ ×12 وأخرى ×6 قد لا تعنيان اختلافًا في المقياس. وإن كان الفرقُ دون التشتّت
// ⇒ يُعلَن «لا يُبنى عليه قرار».
//
// العزل: ملفُّ تعريفٍ ومساحةٌ زائلان في tmp — لا يُمسّ شيءٌ للمستخدم.
// الاستعمال: node tests/runtime/wrapping_strategy.live.mjs [--case pure|marks|mixed|canary]
//                                                    [--pairs 5] [--lines 3000] [--keep]
// خرج 0 = القياسُ تمّ (نجاحًا أو بفجوةٍ **معلَنة**) · 1 = تأكيدٌ فشل · 2 = **لم يقع القياس**.
//
// و«لم يقع القياس» حالةٌ متوقّعةٌ لا عطب: في `--case pure` تتّفق المِسطرتان على مواضع
// الكسر، فلا يُلتقَط تبديلٌ فلا يُقاس زمن — والحكمُ على الصواب (نسبةُ الملء) يكتمل قبلها
// ويُطبَع. كانت هذه الحالةُ تخرج بصفرٍ و«✅ القياسُ تمّ» وهي لم تقس ملّي ثانيةٍ واحدة.
// أمّا زمنُ التبديل فيُقاس في `--case marks` حيث تختلف المِسطرتان فعلًا.

import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { CDP, sleep, activateFixtureTab } from "./harness.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const EXE = join(ROOT, ".upstream", "VSCode-win32-x64", "Mihrab.exe");
const argv = process.argv.slice(2);
const has = f => argv.includes(f);
const val = (f, d) => { const i = argv.indexOf(f); return i >= 0 && argv[i + 1] ? argv[i + 1] : d; };
// منفذُ التنقيح **قابلٌ للتمرير**: شاهدُ الكناري عمليّةٌ ابنةٌ تعمل ونسخةُ الأب ما تزال
// قائمة. وبمنفذٍ ثابتٍ كان الابنُ يعثر على منضدة **الأب** في `/json/list` فيقيس مستندَ
// الحالة الأصليّة لا الكناري — ويكتب إعداداتِه في مجلّدِ مستخدمٍ آخرَ لا أثرَ له فيما
// يقيس. فكان الشاهدُ يسقط دائمًا ويُبطِل قياسًا صحيحًا: **أحمرُ كاذبٌ في حارسِ حارس**.
const PORT = Number(val("--port", "9341"));
const PAIRS = parseInt(val("--pairs", "5"), 10);
const LINES = parseInt(val("--lines", "3000"), 10);
const KEEP = has("--keep");

const log = m => console.log(`▶ ${m}`);
let failed = 0;
const ok = (c, n, d = "") => { if (c) console.log(`  ✅ ${n}${d ? " — " + d : ""}`); else { failed++; console.log(`  ❌ ${n}${d ? "\n       " + d : ""}`); } };
const gap = m => console.log(`  ⚠️ فجوة: ${m}`);
const median = a => { const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

if (!existsSync(EXE)) { console.error(`❌ لا نسخةَ مشحونة: ${EXE}\n   شغّل build/build.sh`); process.exit(2); }

// ── العيّنة ───────────────────────────────────────────────────────────────────────
// نصٌّ عربيٌّ **طويلُ الأسطر بلا فواصل سطر**: هو الحالةُ التي تُظهِر الفرقَ أصلًا
// (سطرٌ قصيرٌ لا يلتفّ فلا يُستدعى الحاسبُ له). ومزيجٌ من طول الكلمات كي لا يكون
// النصُّ دوريًّا فيُخفي أثرَ تفاوت العرض.
// أربعُ حالاتٍ **تعزل المتغيّرات** بدل أن تخلطها. أوّلُ صياغةٍ لهذا المِجَسّ خلطتها كلَّها
// في سطرٍ واحد (`// 1 — …` بشرطةٍ طويلةٍ وأرقامٍ لاتينيّةٍ وشدّاتٍ متفرّقة) فأظهرت فرقًا
// بين المِسطرتين **ولم تقل من أينَ جاء** — وهو أسوأُ من ألّا تُظهِر شيئًا، لأنّه يُغري
// بتعليلٍ خاطئ («العربيّةُ متغيّرةُ العرض») والقياسُ لا يحتمله:
//   pure   : عربيّةٌ خالصةٌ ومسافات — لا تشكيل، لا لاتينيّ.  ⇐ يختبر فرضَ أحاديّةِ العرض
//   mixed  : + بادئةُ تعليقٍ لاتينيّةٌ وأرقامٌ وشرطةٌ طويلة.  ⇐ يختبر السقوطَ إلى وجهٍ آخر
//   marks  : + تشكيلٌ خفيفٌ (ثلثُ الكلمات).                  ⇐ يختبر أثرَ صفريِّ العرض
//   canary : تشكيلٌ كاملٌ لكلِّ كلمة.                         ⇐ الحدُّ الأقصى، وشاهدُ الوصول
const WORDS = ["الكتابة", "بسم", "محراب", "استقلال", "لغة", "برمجة", "المعالجة", "اتجاهية",
  "الحوسبة", "من", "في", "على", "المصطلحات", "توثيق", "قياس", "شاهد", "تفعيل", "خوارزمية"];
const MARKED = ["نصّ", "اتّجاهيّة", "مُشكَّلٌ", "الحوسبةُ", "قياسٌ", "لغةٌ", "بسمِ", "شدّة"];
/**
 * كلماتُ الكناري: مُشكَّلةٌ تشكيلًا كاملًا، فتشكيلُها صفرُ العرض عند الرسم و`simple`
 * يعدّ كلَّ علامةٍ واحدًا ⇒ المِسطرتان **يجب** أن تختلفا عليها. وهي بذلك شاهدُ وصولِ
 * الإعداد: تطابقُهما هنا يعني أنّ الإعدادَ لم يبلغ المحرّرَ، لا أنّهما متّفقتان.
 */
const CANARY_WORDS = ["مُشَكَّلٌ", "بِسْمِ", "الْحَوْسَبَةُ", "لُغَةٌ", "اتِّجَاهِيَّةٌ", "نَصٌّ"];

function fixtureText(n, kind) {
  const out = [];
  for (let i = 0; i < n; i++) {
    const parts = [];
    // طولٌ متفاوتٌ **حتميّ** (لا عشوائيّة: القياسُ يجب أن يُعاد إنتاجُه بالضبط)
    const count = 22 + (i * 7) % 14;
    for (let j = 0; j < count; j++) {
      const pool = kind === "canary" ? CANARY_WORDS : (kind === "marks" && j % 3 === 0 ? MARKED : WORDS);
      parts.push(pool[(i * 13 + j * 5) % pool.length]);
    }
    out.push(kind === "mixed" ? `// ${i + 1} — ${parts.join(" ")}` : parts.join(" "));
  }
  return out.join("\n") + "\n";
}

const work = mkdtempSync(join(tmpdir(), "mihrab-wrap-"));
const userData = join(work, "user-data");
const ws = join(work, "ws");
mkdirSync(join(userData, "User"), { recursive: true });
mkdirSync(ws, { recursive: true });
const CASE = val("--case", "mixed");
if (!["pure", "marks", "mixed", "canary"].includes(CASE)) { console.error(`❌ --case غير معروف: ${CASE} (pure|marks|mixed|canary)`); process.exit(2); }
const file = join(ws, "طويل.txt");
writeFileSync(file, fixtureText(LINES, CASE), "utf8");
const settingsPath = join(userData, "User", "settings.json");

/** يكتب إعدادات الذراع. الالتفافُ **مُشغَّلٌ صراحةً**: بلا `wordWrap` عمودُ الالتفاف صفرٌ فلا يُستدعى الحاسبُ أصلًا وتتطابق الذراعان. */
function writeSettings(strategy) {
  writeFileSync(settingsPath, JSON.stringify({
    "editor.wordWrap": "on",
    "editor.wrappingStrategy": strategy,
    "editor.minimap.enabled": false,
    "workbench.startupEditor": "none",
    "workbench.welcomePage.walkthroughs.openOnInstall": false,
    "window.restoreWindows": "none",
    "update.mode": "none",
  }, null, 2), "utf8");
}
writeSettings("simple");

function cleanEnv() {
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  for (const k of Object.keys(env)) if (k.startsWith("VSCODE_")) delete env[k];
  return env;
}

let proc = null;
const cleanup = () => {
  if (proc && !KEEP) { try { proc.kill(); } catch { /* */ } }
  if (!KEEP) { try { rmSync(work, { recursive: true, force: true }); } catch { /* */ } }
};
process.on("exit", cleanup);

// ── الإطلاق ───────────────────────────────────────────────────────────────────────
log(`إطلاقُ محراب على عيّنةٍ من ${LINES} سطرًا عربيًّا طويلًا…`);
proc = spawn(EXE, [
  `--remote-debugging-port=${PORT}`, "--remote-allow-origins=*",
  `--user-data-dir=${userData}`, "--skip-release-notes", "--disable-updates",
  "--disable-workspace-trust", "--new-window", ws, file,
], { detached: false, stdio: "ignore", env: cleanEnv() });

async function pickWorkbench(timeoutMs = 90_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const t = (await r.json()).find(t => t.type === "page" && /workbench(-dev)?\.html/.test(t.url));
      if (t) return t;
    } catch { /* */ }
    await sleep(500);
  }
  return null;
}

const target = await pickWorkbench();
if (!target) { console.error("❌ لم تظهر صفحةُ المنضدة — خطأٌ تشغيليّ لا فشلُ تأكيد."); process.exit(2); }
// نرتبط **بهدفٍ بعينه** لا بـ`CDP.attach` العامّ: نحتاج `target.id` لاحقًا لتغيير حدود
// النافذة، و`pickPage` لا يُرجعه.
const cdp = new CDP(target.webSocketDebuggerUrl);
await new Promise((res, rej) => { cdp.ws.onopen = res; cdp.ws.onerror = () => rej(new Error("WS فشل")); });
cdp.ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && cdp._pend[m.id]) { cdp._pend[m.id](m); delete cdp._pend[m.id]; } };
await cdp.cmd("Runtime.enable");
await cdp.cmd("Page.enable");
await cdp.cmd("Page.bringToFront").catch(() => { });
await sleep(4000);

const evalJs = expr => cdp.evaluate(expr).catch(() => null);

/**
 * شاهدُ السلوك = **الحبر**: أينَ ينكسر السطرُ الأوّل فعلًا.
 *
 * ولا يُقاس بارتفاع `.lines-content`: قيمتُه ثابتةٌ 16777216 (‏2^24) — حِيلةُ المنبع
 * لتثبيت حاويةٍ تُوضَع فيها الأسطرُ مُطلَقةَ الموضع. فالرقمُ يبدو «ارتفاعَ محتوى» وهو
 * ثابتٌ لا يتحرّك أبدًا ⇒ شاهدٌ ينجح صامتًا مهما تبدّلت المِسطرة. قِيس فسقط.
 *
 * والنصُّ المصيَّرُ للسطر الأوّل هو **بعينه** العطبُ الذي يشكو منه المستخدم: موضعُ الكسر.
 * ويُضاف ارتفاعُ مِزلاجِ الشريط عكسَ عددِ الأسطر بعد الالتفاف — أصغرُ مِزلاجٍ = محتوًى أطول.
 */
const CONTENT_H = `(() => {
  const lines = [...document.querySelectorAll('.monaco-editor .view-lines .view-line')];
  if (!lines.length) return null;
  const sorted = lines.map(e => ({ top: parseFloat(e.style.top) || 0, el: e, t: e.textContent })).sort((a,b) => a.top - b.top);
  const slider = document.querySelector('.monaco-editor .scrollbar.vertical .slider');

  // عرضُ منطقة المحتوى وعرضُ **الحبر** لكلِّ سطرِ عرض. الحبرُ يُقاس بمدًى (Range) على
  // محتويات العقدة لا بمستطيلِ العقدة: العقدةُ كتلةٌ عرضُها عرضُ الحاوية دائمًا، فقياسُها
  // يُعطي الرقمَ نفسَه لكلِّ سطرٍ ⇒ تأكيدٌ ينجح دومًا بلا أن يقيس شيئًا.
  const viewport = document.querySelector('.monaco-editor .lines-content')?.parentElement
                || document.querySelector('.monaco-editor .view-lines');
  const contentW = viewport ? viewport.getBoundingClientRect().width : 0;
  const inkW = el => { const r = document.createRange(); r.selectNodeContents(el); const w = r.getBoundingClientRect().width; r.detach?.(); return w; };

  // أيُّ أسطرِ العرض **استمرارٌ** لسطرِ نموذجٍ سابق؟ أسطرُ الاستمرار بلا رقمٍ في الهامش.
  // بلا هذا التمييز يُقارَن آخرُ مقطعٍ من سطرٍ بأوّلِ مقطعٍ من السطر التالي فيُبلَّغ
  // «كسرٌ مبكّر» وهو ليس كسرًا أصلًا.
  const nums = new Map();
  for (const n of document.querySelectorAll('.monaco-editor .margin-view-overlays > div')) {
    const t = Math.round(parseFloat(n.style.top) || 0);
    nums.set(t, (n.textContent || '').trim().length > 0);
  }

  // المقياس: **نسبةُ الملء** = حبرُ السطر ÷ عرضِ منطقة المحتوى، لأسطرِ العرض التي يليها
  // استمرارٌ (أي التي وقع فيها كسرٌ فعلًا — السطرُ الأخيرُ من فقرةٍ قصيرٌ بحقٍّ لا بعطب).
  //   نسبةٌ > 1        ⇒ فيضٌ: النصُّ تجاوز العرضَ فقُطع.
  //   نسبةٌ منخفضةٌ    ⇒ بياضٌ ضائع: كُسر السطرُ وفي العرض متّسع.
  // (‏جُرِّب أوّلًا معيارٌ ثنائيّ «هل كانت الكلمةُ التاليةُ تسع؟» بقياس عرضِ كلمةٍ في عنصرٍ
  //  مُصطنَع — فأعطى صفرًا في حالةٍ نسبةُ ملئها 0.51، أي **تأكيدٌ لا يفشل**. النسبةُ المتّصلةُ
  //  تُري الرقمَ بدل أن تحكم به، فلا يختبئ العطبُ خلف عتبةٍ سيّئةِ التنفيذ.)
  let overflow = 0, judged = 0;
  const fills = [];
  for (let i = 0; i + 1 < sorted.length; i++) {
    const nxtHasNumber = nums.get(Math.round(sorted[i + 1].top));
    if (nxtHasNumber !== false) continue;              // ليس استمرارًا ⇒ لا كسرَ بينهما
    judged++;
    const w = inkW(sorted[i].el);
    fills.push(w / contentW);
    if (w > contentW + 0.5) overflow++;
  }
  const sortedFills = [...fills].sort((a, b) => a - b);
  const medFill = sortedFills.length ? sortedFills[sortedFills.length >> 1] : null;

  return {
    first: sorted[0].t,
    firstThree: sorted.slice(0, 3).map(x => x.t).join('\\u241E'),
    sliderH: slider ? slider.getBoundingClientRect().height : 0,
    lineH: lines[0].getBoundingClientRect().height,
    shown: lines.length,
    contentW, judged, overflow, medFill, minFill: sortedFills[0] ?? null,
    dbg: sorted.slice(0,8).map(x => ({ top: Math.round(x.top), num: nums.get(Math.round(x.top)), ink: Math.round(inkW(x.el)), len: (x.t||'').length })),
  };
})()`;

// ── تنشيطُ تبويبنا ────────────────────────────────────────────────────────────────
// صفحةُ الترحيب تُفتَح رغم `startupEditor: "none"` وتبقى **هي النشطة**، فيُصيَّر محرّرُنا
// بصفرِ أسطرٍ ويُقرأ ذلك «الملفُّ لم يُفتَح». وهو الفخُّ نفسُه الموثَّقُ في
// `word_boundaries.live.mjs`: «لم يُفتَح» ≠ «فُتح بلا نصّ». فالتنشيطُ صريحٌ ومتحقَّقٌ منه.
log("تنشيطُ تبويب العيّنة (صفحةُ الترحيب تسبقنا إلى النشاط)");
let rendered = 0;
for (let attempt = 1; attempt <= 6 && rendered === 0; attempt++) {
  await activateFixtureTab(cdp).catch(() => { });
  await sleep(900);
  rendered = (await evalJs(`document.querySelectorAll('.monaco-editor .view-line').length`)) || 0;
}

// ── شاهدُ التفعيل: هل فُتح الملفُّ أصلًا وهل هو ملفُّنا؟ ─────────────────────────
log("شاهدُ التفعيل: الملفُّ مفتوحٌ والالتفافُ عامل");
const opened = await evalJs(`(() => {
  const t = [...document.querySelectorAll('.tabs-container .tab')].map(e => e.getAttribute('aria-label') || e.textContent);
  const c = document.querySelectorAll('.monaco-editor .view-line').length;
  return { tabs: t, viewLines: c };
})()`);
ok(opened && opened.viewLines > 0, "المحرّرُ صيَّر أسطرًا", opened ? `${opened.viewLines} سطرَ عرضٍ ظاهرًا · تبويبات: ${(opened.tabs || []).join(" | ")}` : "لا نتيجة");
if (!opened || !opened.viewLines) { console.error("\n❌ لا محرّرَ مصيَّر — لا يُقرأ أيُّ قياسٍ بعد هذا."); process.exit(1); }

// ── تبديلُ الذراع + التحقّق من وصولها ────────────────────────────────────────────
/**
 * يكتب الإعداد وينتظر أن **يتغيّر** ارتفاعُ المحتوى — أي أن يصل الإعدادُ فعلًا.
 * الانتظارُ على مهلةٍ ثابتةٍ بدلَ ذلك يُنتج «وصل» كاذبًا كلَّما تأخّر مراقبُ الملفّات.
 */
async function armTo(strategy, prevKey) {
  writeSettings(strategy);
  const deadline = Date.now() + 12_000;
  while (Date.now() < deadline) {
    await sleep(250);
    const m = await evalJs(CONTENT_H);
    if (!m) continue;
    if (prevKey == null) return m;
    if (m.firstThree !== prevKey) return m;
  }
  return null;
}

const m0 = await evalJs(CONTENT_H);
log(`كسرُ السطر الأوّل عند simple:\n     «${(m0?.first || "").slice(0, 90)}…»`);
const mAdv = await armTo("advanced", m0?.firstThree);

// «لم تختلفا» **نتيجةٌ لا عطب** — بشرط أن يكون قد ثبت أنّ الإعداد يصل أصلًا.
//
// ## وهذا الشرطُ كان مكتوبًا لا مُنفَّذًا
// كانت الصياغةُ الأولى تقول للقارئ «شغّل ‎--case canary‎ للتأكّد» ثمّ تمضي. وأثرُ ذلك أنّ
// الحالةَ التي يقول القرارُ نفسُه إنّها **الغالبة** (عربيّةٌ خالصة: المِسطرتان تتّفقان)
// كانت تُنتج: `armTo` ⇒ `null` ⇒ صفرَ أزواجٍ مقيسة ⇒ صفرَ ملّي ثانيةٍ مُبلَّغة ⇒ **خرجٌ
// أخضرُ وعبارةُ «القياسُ تمّ»** — ولا يمكن تمييزُه عن «الإعدادُ لم يبلغ المحرّرَ إطلاقًا».
// وأسوأُ منه: `mAdvB` كان يسقط إلى `m0`، فعمودُ «advanced» في الجدول هو عمودُ «simple»
// **مقروءًا مرّتين**، وصفَّا «عربيّةٌ خالصة» و«مختلطة» في القرار ١١ بُنيا عليه.
//
// فالكناري صار يُشغَّل **تلقائيًّا** هنا: شاهدٌ لا وصيّة. والحكمُ هو الحكم — لا يُقرأ
// تأكيدٌ سالبٌ («اتّفقتا») قبل شاهدٍ يُثبِت أنّ المِسطرةَ قادرةٌ على التمييز.
const sameBreaks = mAdv == null;
if (has("--witness-only")) {
  console.log(sameBreaks ? "WITNESS=FAIL — الكناري نفسُه لم يختلف ⇒ الإعدادُ لا يبلغ المحرّر"
                         : "WITNESS=OK — الإعدادُ يبلغ المحرّرَ ويُعيد بناءَ الأسطر");
  process.exit(sameBreaks ? 1 : 0);
}
const m0b = m0;
if (sameBreaks) {
  ok(true, "المِسطرتان اتّفقتا على مواضع الكسر في هذه الحالة", "نتيجةٌ لا فشل");
  if (CASE === "canary") {
    console.log("       والكناري **يجب** أن تختلف عليه المِسطرتان (تشكيلٌ كاملٌ: صفرُ العرض عند");
    console.log("       الرسم، و`simple` يعدّه واحدًا). فاتّفاقُه يعني أنّ الإعدادَ لم يصل.");
    console.log("\n╚══ ❌ الإعدادُ لا يبلغ المحرّر — القياسُ لم يقع ══╝");
    process.exit(1);
  }
  console.log("       شاهدُ المِسطرة: يُشغَّل الكناري الآن (نصٌّ مُشكَّلٌ يجب أن تختلف عليه) …");
  const witness = await new Promise(res => {
    const c = spawn(process.execPath, [fileURLToPath(import.meta.url), "--case", "canary",
      "--witness-only", "--port", String(PORT + 1)],
      { stdio: ["ignore", "pipe", "pipe"] });
    let out = ""; c.stdout.on("data", d => { out += d; }); c.stderr.on("data", d => { out += d; });
    c.on("close", code => res({ code, out }));
  });
  if (witness.code !== 0) {
    console.log(`  ❌ شاهدُ المِسطرة سقط (خرج ${witness.code}) — فـ«اتّفقتا» غيرُ مقروء.`);
    console.log("       " + (witness.out.split("\n").filter(l => l.includes("WITNESS") || l.includes("❌")).slice(-2).join("\n       ") || "(بلا مخرَج)"));
    console.log("\n╚══ ⚠️ لم يقع القياس (لا نجاحَ ولا فشلَ تأكيد) ══╝");
    process.exit(2);
  }
  ok(true, "شاهدُ المِسطرة: الكناري اختلف ⇒ الإعدادُ يصل والتمييزُ ممكن", "فـ«اتّفقتا» نتيجةٌ لا عجز");
  // **بعد** الشاهد وحدَه تُقرأ الذراعُ الثانية من الـDOM: `armTo` كتب الإعدادَ واستوفى
  // اثنتَي عشرةَ ثانيةً، فالمحرّرُ في وضع `advanced` — والكسورُ لم تتغيّر لا أكثر.
  // قبلَ الشاهدِ كانت هذه القراءةُ نفسُها هي عمودَ «simple» مقروءًا مرّتين.
} else {
  ok(true, "شاهدُ الاختلاف الموجب", "المِسطرتان تكسران في موضعين مختلفين");
  log(`كسرُ السطر الأوّل عند advanced:\n     «${(mAdv.first || "").slice(0, 90)}…»`);
  log(`طولُ الجزء الأوّل: ${(m0.first || "").length} محرفًا بـsimple  مقابل  ${(mAdv.first || "").length} بـadvanced`
    + `${(m0.first || "").length === (mAdv.first || "").length ? "  (تطابقا هنا — الاختلافُ في سطرٍ تالٍ)" : ""}`);
}

// ── الصواب: «مختلف» ليس «أصوب» ───────────────────────────────────────────────────
const mAdvB = mAdv || await evalJs(CONTENT_H);
if (!mAdvB) { console.error("❌ تعذّرت قراءةُ ذراع advanced بعد التبديل — لا يُقرأ جدولٌ بعمودٍ واحد."); process.exit(2); }
const pctf = x => x == null ? "—" : (x * 100).toFixed(0) + "%";
const verdict = (m, name) =>
  log(`  ${name.padEnd(9)}: كسورٌ حُوكمت ${String(m.judged).padStart(3)} · فيضٌ ${m.overflow} · **نسبةُ الملء** وسيطًا ${pctf(m.medFill).padStart(4)} · أدناها ${pctf(m.minFill)}`);
log(`\nالصواب (عرضُ منطقة المحتوى ${m0b.contentW.toFixed(0)} بكسل · الحالة «${CASE}»):`);
verdict(m0b, "simple"); verdict(mAdvB, "advanced");
log(`  وهل اختلف كسرُ **هذه الحالة** نفسِها؟ ${m0b.firstThree === mAdvB.firstThree ? "لا — المِسطرتان اتّفقتا (والكناري أثبت أنّ الإعداد يصل)" : "نعم"}`);
if (has("--debug")) {
  console.log("  [dbg simple]   " + JSON.stringify(m0b.dbg));
  console.log("  [dbg advanced] " + JSON.stringify(mAdvB.dbg));
}
if (m0b.judged === 0 || mAdvB.judged === 0)
  console.log("  ⚠️ لم يُحاكَم كسرٌ واحد — لا يُقرأ حكمُ صوابٍ من عيّنةٍ خالية (وهو نظيرُ فخِّ «النطاقُ الخالي يُبلِّغ نظيفًا»).");
else {
  const d = (mAdvB.medFill ?? 0) - (m0b.medFill ?? 0);
  if (m0b.overflow === 0 && mAdvB.overflow === 0 && Math.abs(d) < 0.05)
    console.log("  ⇒ المِسطرتان **متكافئتان** هنا: لا فيضَ ولا فرقَ يُعتدّ به في الملء ⇒ لا صوابَ يُشترى بزمن.");
  else
    console.log(`  ⇒ ${d > 0 ? "advanced" : "simple"} أفضلُ ملءً بفارق ${pctf(Math.abs(d))} من عرضِ السطر`
      + `${d > 0 ? ` — أي أنّ simple يُهدر نحوَ ${pctf(Math.abs(d))} من كلِّ سطرٍ مكسور` : ""}`);
}

// ── القياس: أطولُ حجبٍ للخيط الرئيسيّ أثناء إعادة حسابِ الكسر ────────────────────
/**
 * **لا مُستحِثَّ صناعيّ.** تبديلُ الإعداد نفسُه هو الاستحثاث: `viewModelImpl.ts:278` يستدعي
 * `setWrappingSettings` فيُرجع true عند تغيُّر المِسطرة ⇒ إعادةُ بناءِ كسورِ **كلِّ** الأسطر
 * بالحاسب الجديد. فما يُقاس هو الكميّةُ المطلوبةُ بعينها.
 * (‏جُرِّب أوّلًا تغييرُ حدود النافذة عبر `Browser.setWindowBounds` — والنطاقُ غيرُ مكشوفٍ
 *  على جلسةِ صفحةٍ في إلكترون. وكان سيقيس كلفةَ تغييرِ الحجم مضافةً إلى الحساب على أيّ حال.)
 *
 * والمقياس: **أكبرُ فجوةٍ بين إطارَي رسمٍ متتاليين** خلال النافذة — الحسابُ متزامنٌ فيحجب
 * الخيطَ الرئيسيّ فيظهر إطارًا واحدًا طويلًا. وهو ما يشعر به المستخدم تجمُّدًا.
 * وكلفةُ قراءةِ الإعداد وتحليلِه داخلةٌ في النافذة — **وهي نفسُها للذراعين** فتسقط بالقسمة.
 */
async function startRecorder() {
  await evalJs(`(() => {
    window.__wrapProbe = { gaps: [], last: performance.now(), t0: performance.now() };
    const tick = () => {
      const n = performance.now();
      window.__wrapProbe.gaps.push(n - window.__wrapProbe.last);
      window.__wrapProbe.last = n;
      if (n - window.__wrapProbe.t0 < 4000) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
    return true;
  })()`);
}
async function readBlock() {
  const gaps = await evalJs(`window.__wrapProbe ? window.__wrapProbe.gaps.slice(1) : null`);
  if (!gaps || gaps.length < 5) return null;
  return Math.max(...gaps);
}

/** يقيس تبديلًا واحدًا: يبدأ التسجيل، يبدّل، يتأكّد من وصول التبديل، ثمّ يقرأ. */
async function measureSwitch(strategy, prevKey) {
  await startRecorder();
  await sleep(100);
  const r = await armTo(strategy, prevKey);
  if (r == null) return { ms: null, key: prevKey };
  await sleep(1200);                       // اتركِ الحجبَ يظهر في نافذة التسجيل كاملًا
  return { ms: await readBlock(), key: r.firstThree };
}

log(`\nالقياس: ${PAIRS} أزواجٍ **متداخلةٍ** ABAB (لا مكتَّلة — الانجرافُ الحراريُّ في التكتيل يُسنَد كلُّه للذراع الثانية)`);
const simple = [], advanced = [], ratios = [];
let curKey = mAdvB.firstThree;

for (let i = 1; i <= PAIRS; i++) {
  process.stdout.write(`  زوج ${i}/${PAIRS} … `);
  const rs = await measureSwitch("simple", curKey); curKey = rs.key;
  const ra = await measureSwitch("advanced", curKey); curKey = ra.key;
  if (rs.ms == null || ra.ms == null) { console.log("قياسٌ ناقص (لم يصل تبديلٌ أو لم يُسجَّل إطارٌ كافٍ)"); continue; }
  simple.push(rs.ms); advanced.push(ra.ms); ratios.push(ra.ms / rs.ms);
  console.log(`simple ${rs.ms.toFixed(1)} مللي · advanced ${ra.ms.toFixed(1)} مللي · ×${(ra.ms / rs.ms).toFixed(2)}`);
}

// ── الحكم ─────────────────────────────────────────────────────────────────────────
console.log();
if (ratios.length === 0) {
  // **صفرُ أزواجٍ ليس «نسبةً غيرَ محسومة» — هو لا قياس.** وكان يمرّ عبر `gap` (تنبيهٌ لا
  // يُحسَب فشلًا) فيصل السطرُ الأخيرُ إلى «✅ القياسُ تمّ» وخروجٍ بصفر: صفرُ ملّي ثانيةٍ
  // مقيسة، وخرجٌ أخضر. يُفصَل الآن: «لم يقع القياس» خروجُه ‎2‎ لا ‎0‎ ولا ‎1‎.
  console.error("❌ لم يكتمل زوجٌ واحد — لم يُقَس شيء. (خرج ‎2‎: لا نجاحَ ولا فشلُ تأكيد.)");
  console.error("   الأرجح: التبديلُ لا يُغيّر كسورًا في هذه الحالة فلا يُلتقط، أو لم يُسجَّل إطارٌ كافٍ.");
  process.exit(2);
} else if (ratios.length < 2) {
  gap(`لم يكتمل إلّا ${ratios.length} زوجًا — لا يُحكَم على نسبةٍ من عيّنةٍ بهذا الحجم.`);
} else {
  const ms = median(simple), ma = median(advanced), mr = median(ratios);
  const noise = Math.max(Math.max(...simple) - Math.min(...simple), Math.max(...advanced) - Math.min(...advanced));
  console.log(`  simple  : وسيط ${ms.toFixed(1)} مللي  (${simple.map(x => x.toFixed(0)).join(", ")})`);
  console.log(`  advanced: وسيط ${ma.toFixed(1)} مللي  (${advanced.map(x => x.toFixed(0)).join(", ")})`);
  console.log(`  **وسيطُ النِّسَب**: ×${mr.toFixed(2)}   (لا نسبةُ الوسيطين — تلك تخلط زوجًا هادئًا بصاخبٍ في كسرٍ واحد)`);
  console.log(`  تشتّتُ القياس: ${noise.toFixed(1)} مللي · الفرقُ في الوسيط: ${Math.abs(ma - ms).toFixed(1)} مللي`);
  if (Math.abs(ma - ms) < noise)
    console.log(`\n  ⚠️ الفرقُ **دون** تشتّتِ القياس ⇒ لا يُبنى عليه قرار: أرضيّةُ الضجيج هنا أكبرُ من الأثر.`);
  else
    console.log(`\n  الأثرُ يتجاوز الضجيجَ ⇒ الرقمُ صالحٌ للقرار على ${LINES} سطرًا بهذا الطول.`);
}

console.log("\n  (‏قياسٌ لا حارس: لا عتبةَ زمنٍ مطلقة — تُخفق دائمًا على عتادٍ بطيءٍ ولا تُخفق أبدًا على سريع.)");
cdp.close();
if (!KEEP) { try { proc.kill(); } catch { /* */ } }
console.log(failed === 0 ? "\n╚══ ✅ القياسُ تمّ ══╝" : "\n╚══ ❌ تأكيدٌ فشل ══╝");
process.exit(failed === 0 ? 0 : 1);
