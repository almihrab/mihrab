// L3 حيّ ‏[SC-01 · SC-02]: صندوقُ رسالة الالتزام ومحرّرُ الدمج — **قياسٌ قبل الإصلاح**.
//
// ## لماذا هذا الملفّ موجود
// صندوقُ رسالة الالتزام هو **أطولُ نصٍّ عربيٍّ متّصلٍ يكتبه مستخدمُ محرابٍ في يومه**، وهو
// السطحُ الوحيدُ الذي وجدنا أنّ بنودَ الطباعة السبعة وبندَ الاتّجاه لا تبلغه. والسببُ
// بنيويّ: الصندوقُ محرّرُ Monaco بـ`isSimpleWidget: true` (‏`scmInput.ts:613`)، و«الودجةُ
// البسيطة» **لا تقرأ خدمةَ الإعدادات إطلاقًا** (‏`editorConfiguration.ts:73-88`)، فيُعيد
// ‏`SCMInputWidget` قراءةَ ما يريده بيده في **قائمةِ سماحٍ مغلقة** (‏`scmInput.ts:310`).
//
// وكلُّ حرّاسنا يسألون «هل الإعدادُ مضبوط؟» و«هل يُصيَّر في `.view-line` في جزء المحرّر؟» —
// والصندوقُ ليس منهما. **فلا حارسٌ ساكنٌ يبلغه ولا مِجَسٌّ حيٌّ يفتحه**، حتى اليوم.
//
// ## وما نُقِض من هذا الوصف بعد رقعة النواة ‎030‎ — يُصحَّح ولا يُترَك
// الفقرتان أعلاه تصفان حالًا **سبقت الرقعة**، وتُبقيان لأنّهما سببُ وجود هذا الملفّ. وما
// صار خطأً فيهما يُقال هنا صراحةً: ‏`scmInput.ts:280` يُفرِد `...getSimpleEditorOptions(this.configurationService)`
// **قبل** قائمةِ السماح، وقائمةُ السماح تُطبَّق فوقها ولا تنقضها؛ ورقعةُ ‎030‎ أضافت
// ‏`textDirection` و`fontLigatures` إلى تلك الدالّة (‏`simpleEditorOptions.ts:67`). فالصندوقُ
// **يقرأ خدمةَ الإعدادات اليوم**.
//
// ## وما نُقِض مرّةً ثانية — بعد قلب الافتراض [DR-02]
// كان مكتوبًا هنا أنّ القراءةَ **بلا `overrideIdentifier`** فيسري جذرُ
// ‏`configurationDefaults` وتُهمَل تجاوزاتُ اللغة، «ولذلك بالضبط وصلَه الاتّجاه، ولذلك كتلةُ
// ‏`[scminput]` كانت ستكون ميّتةً لو كُتبت». وكان صحيحًا يومَه، **وصار هو نفسُه العطب**:
// يومَ قُلِب الجذرُ إلى `ltr` (لأنّ فرضَ `rtl` عالميًّا كان يُصيَّر ‎٥٣‎ لغةً مشحونةً يمينًا
// بلا حرفٍ عربيٍّ واحد) كان الصندوقُ سيفقد اتّجاهَه في اللحظة نفسِها — انحدارٌ يسلب
// **أطولَ نصٍّ عربيٍّ متّصلٍ يكتبه المستخدم** اتّجاهَه ثمنًا لإصلاحِ ملفّات `.cpp`.
// فمُرِّر المعرِّفُ في الرقعة نفسِها: ‏`getSimpleEditorOptions(this.configurationService,
// 'scminput')`، وأُحييت كتلةُ `[scminput]` في قشرة محراب. والقلبُ والتمريرُ **صفقةٌ واحدة**:
// أيُّهما بلا الآخر انحدار — ولذلك يحرسهما توكيدٌ واحدٌ في
// ‏`lint_patchers.py::_editor_direction_defaults_to_ltr`.
//
// **والدَّينُ الباقي غيرُ الاتّجاه**: مرشِّحُ تغيُّر الإعدادات (‏`scmInput.ts:258-270`) وحمولةُ
// ‏`updateOptions` (‏`:298-311`) لا تذكران أيًّا من الثلاثة — فالقيمُ تُلتقَط **عند الإنشاء
// ولا تتجدّد حيًّا**. من غيّر اتّجاهَه وهو يعمل لا يرى الصندوقَ يتبعه حتى إعادة التحميل ⇐ م-١٧.
//
// ## وما لا يفعله هذا الملفّ
// **لا يُصلِح شيئًا.** هو مِجَسُّ قياسٍ صرف: يفتح، ويقيس، ويقول ما وجده رقمًا. والإصلاحُ
// يُقرَّر بعده لا قبله — وهو المبدأُ الذي علّمنا إيّاه هذا المستودعُ حين أعاد «الكشفُ
// بالسبب» اثنتي عشرة ورقةً كلُّها سليمة.
//
// ## العزلُ وسلامةُ العمل
// ما يُكتَب في هذا الصندوق **رسالةُ التزامٍ في مستودعٍ حقيقيّ**. فلا يُشغَّل على مستودع
// المستخدم أبدًا: يُصنَع مستودعٌ زائلٌ في `tmp`، ويُمحى بعد القياس. وملفُّ التعريف معزولٌ
// كذلك (‏`--user-data-dir` مؤقّت) — القاعدةُ نفسُها المكتوبةُ في `unicode_guard.live.mjs`.
//
// الاستعمال: node tests/runtime/scm_input.live.mjs [--keep]
// خرج 0 = القياسُ تمّ (نجاحًا أو بفجوةٍ **معلَنة**) · 1 = تأكيدٌ فشل · 2 = خطأ تشغيليّ.
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { CDP, sleep, key, MOD } from "./harness.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const EXE = join(ROOT, ".upstream", "VSCode-win32-x64", "Mihrab.exe");
const PORT = 9335;
const KEEP = process.argv.includes("--keep");

/** المقيسُ في VA-04 و TY-02 — يُقرآن هنا **للمقارنة** لا لإعادة اشتقاقهما. */
const EDITOR_FONT_SIZE = 15;
// ‏[TY-02] الأرضيّةُ من المصدر الواحد المقيس، لا رقمًا منسوخًا (كان ‎1.88‎ مشتقًّا من
// ‏كونتوراتٍ منفردةٍ لا تركّب علامةً على قاعدة — أنقصَ الحقيقةَ بـ‎0.885em‎).
const INK_FLOOR_EM = JSON.parse(readFileSync(
  new URL("../dx/arabic_ink.measured.json", import.meta.url), "utf8")).composedInkEm;

const log = m => console.log(`▶ ${m}`);
let failed = 0;
const ok = (cond, name, detail = "") => {
  if (cond) console.log(`  ✅ ${name}${detail ? " — " + detail : ""}`);
  else { failed++; console.log(`  ❌ ${name}${detail ? "\n       " + detail : ""}`); }
};
/** فجوةٌ **معلَنة**: لم يُقَس، ويُقال إنّه لم يُقَس. لا `pass` ولا دفنٌ في «لم ينفتح». */
const gap = (name, why) => console.log(`  ⏭️  ${name} — غير مقيس (فجوة معلَنة): ${why}`);

if (!existsSync(EXE)) { console.error(`❌ لا حزمة مشحونة: ${EXE}`); process.exit(2); }

// ───────────────────────── المستودعُ الزائل ─────────────────────────
const tmp = mkdtempSync(join(tmpdir(), "mihrab-sc01-"));
const userData = join(tmp, "user-data");
const ws = join(tmp, "مستودع");
mkdirSync(join(userData, "User"), { recursive: true });
mkdirSync(ws, { recursive: true });

const git = (...args) => spawnSync("git", args, { cwd: ws, encoding: "utf8" });
function buildRepo() {
  git("init", "-b", "main");
  git("config", "user.email", "probe@mihrab.test");
  git("config", "user.name", "مِجَسّ");
  git("config", "commit.gpgsign", "false");
  writeFileSync(join(ws, "مثال.txt"), "دالة رئيسية()\n  اطبع(\"الأساس\")\n", "utf8");
  git("add", "-A"); git("commit", "-m", "أساس");
  // فرعٌ يعدّل السطرَ نفسَه ⇒ تعارضٌ حتميٌّ عند الدمج (‏SC-02).
  git("checkout", "-b", "فرع");
  writeFileSync(join(ws, "مثال.txt"), "دالة رئيسية()\n  اطبع(\"لهم — نصاب_الفضة\")\n", "utf8");
  git("add", "-A"); git("commit", "-m", "تعديل الفرع");
  git("checkout", "main");
  writeFileSync(join(ws, "مثال.txt"), "دالة رئيسية()\n  اطبع(\"لك — نصاب_الذهب\")\n", "utf8");
  git("add", "-A"); git("commit", "-m", "تعديل الأصل");
  const merged = git("merge", "فرع");
  // ملفٌّ متغيّرٌ **غيرُ متعارض** كي يبقى في القائمة موردٌ عاديٌّ أيضًا.
  writeFileSync(join(ws, "ثانٍ.txt"), "دالة ثانية()\n  اطبع(\"نصّ عربيّ للقياس\")\n", "utf8");
  return (merged.stdout || "") + (merged.stderr || "");
}

// ‏[SC-02] محرّرُ الدمج ثلاثيُّ اللوحات **مطفأٌ افتراضيًّا في المنبع** (‏`git.mergeEditor`
// افتراضُه false في `extensions/git/package.json`). فبلا هذا السطر يُفتَح التعارضُ في
// محرّرٍ عاديٍّ ولا يُقاس السطحُ المقصود إطلاقًا — وكنّا سنُبلِّغ «سليم» عن سطحٍ لم يُفتَح.
//
// **ومصدرٌ واحدٌ للأساس.** قسمُ التجدُّد الحيّ (‏SC-01/د) يعيد كتابةَ هذا الملفّ بمفتاحٍ
// واحدٍ زائد، ثمّ يستعيده. فلو كُتب الأساسُ مرّتين لانزلق أحدُهما عن الآخر، فيصير
// «الاستعادةُ» تغييرًا ثانيًا يُقرأ انتقالًا.
const BASE_SETTINGS = {
  "window.restoreWindows": "none",
  "git.mergeEditor": true,
  "git.openRepositoryInParentFolders": "always",
};
const SETTINGS_PATH = join(userData, "User", "settings.json");
writeFileSync(SETTINGS_PATH, JSON.stringify(BASE_SETTINGS, null, 2), "utf8");

/** ⚠️ فخُّ `ELECTRON_RUN_AS_NODE` الموروث — موثَّقٌ في `launch.mjs` و`unicode_guard.live.mjs`. */
function cleanEnv() {
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  for (const k of Object.keys(env)) if (k.startsWith("VSCODE_")) delete env[k];
  return env;
}

let proc = null;
const launch = () => {
  proc = spawn(EXE, [
    `--remote-debugging-port=${PORT}`, "--remote-allow-origins=*",
    `--user-data-dir=${userData}`, "--skip-release-notes", "--disable-updates",
    // الملفُّ **ضابطٌ لا زينة**: قياسُ الأشكال السياقيّة في الصندوق بلا مقارنةٍ بالمحرّر
    // الرئيس حكمٌ بلا ضابط. وبلا ملفٍّ مفتوحٍ لا سطرَ محرّرٍ يُقاس، فتُبلَّغ الفجوةُ معلَنةً
    // بلا سبب. فنفتح الملفَّ مع المجلّد.
    "--disable-workspace-trust", "--new-window", ws, join(ws, "ثانٍ.txt"),
  ], { detached: false, stdio: "ignore", env: cleanEnv() });
};
const kill = () => { try { proc && proc.kill(); } catch { /* */ } };

async function attach(timeoutMs = 120000) {
  const t0 = Date.now();
  for (;;) {
    try { return await CDP.attach(PORT); } catch (e) {
      if (Date.now() - t0 > timeoutMs) throw new Error(`تعذّر الاتّصال بـCDP: ${e.message}`);
      await sleep(1500);
    }
  }
}

/**
 * يفتح جزءَ التحكّم بالمصادر — **بالأيقونة داخل حلقة تحقّقٍ ثمّ الوتر**، لا بالوتر وحده.
 * الوترُ `Ctrl+Shift+G G` **مبدِّلٌ لا فاتح**: يفتح الجزءَ حين يكون مغلقًا ويُبدّله حين
 * يكون مفتوحًا. والدرسُ مدفوعٌ في `openDiffFromScm` — ننقله ولا نعيد اكتشافه.
 * والأيقونةُ نفسُها مبدِّلة، فالنقرةُ **داخل الحلقة** لا قبلها: كلُّ دورةٍ تسأل أوّلًا.
 */
async function openScm(cdp) {
  for (let i = 0; i < 6; i++) {
    const has = await cdp.evaluate(
      `!!document.querySelector('.scm-view .scm-editor-container .monaco-editor')`);
    if (has) return true;
    await cdp.evaluate(`(document.querySelector('.part.activitybar .codicon-source-control-view-icon')
      ?.closest('.action-item')?.querySelector('a, .action-label')?.click(), 1)`);
    await sleep(700);
    await key(cdp, 71, "KeyG", MOD.CTRL | MOD.SHIFT); await sleep(300);
    await key(cdp, 71, "KeyG", 0); await sleep(1500);
  }
  return false;
}

/** ينقر مركزَ عنصرٍ بإحداثيّةٍ محسوبةٍ **بعد التحقّق من إصابته** (لا إحداثيّةَ ثابتة). */
async function clickSelector(cdp, sel) {
  const p = await cdp.evaluate(`(() => {
    const e = document.querySelector(${JSON.stringify(sel)});
    if (!e) return null;
    const b = e.getBoundingClientRect();
    if (b.width < 4 || b.height < 4) return null;
    const x = Math.round(b.left + b.width / 2), y = Math.round(b.top + b.height / 2);
    const at = document.elementFromPoint(x, y);
    return (at && (e.contains(at) || at.contains(e))) ? { x, y } : null;
  })()`);
  if (!p) return false;
  await cdp.cmd("Input.dispatchMouseEvent", { type: "mousePressed", x: p.x, y: p.y, button: "left", clickCount: 1 });
  await cdp.cmd("Input.dispatchMouseEvent", { type: "mouseReleased", x: p.x, y: p.y, button: "left", clickCount: 1 });
  await sleep(600);
  return true;
}

/**
 * القياساتُ الخمسة في تقييمٍ واحد — والحكمُ فيها كلِّها **بالحبر وبمواضع المحارف**
 * لا بالإعلان:
 *   ‏(١) الاتّجاه: ترتيبُ المحارف المرئيُّ لا `getComputedStyle` — وهي تكذب في هذا الباب
 *       بعينه على `.view-line` (موثَّقٌ في الماسح).
 *   ‏(٢) ارتفاعُ السطر: نسبةُ الحبر الحدّيّ إلى ارتفاع السطر، بمنهج TY-02 نفسِه.
 *   ‏(٣) الوجه: **بالتفاوت لا بالاسم** — درسُ VA-02ب: «المكدّسُ مكتوبٌ ولم يُطبَّق».
 *   ‏(٤) الأشكالُ السياقيّة: المُعلَنُ (‏`font-feature-settings`) **ومعه أثرٌ مقيس**،
 *       وضابطٌ من المحرّر الرئيس — وإلّا فالنتيجة «غير مقيس» لا «سليم».
 *   ‏(٥) حجمُ الخطّ: رقمٌ مقيسٌ من العنصر لا مقروءٌ من إعداد.
 */
const MEASURE = `(() => {
  const box = document.querySelector('.scm-view .scm-editor-container .monaco-editor');
  if (!box) return { present: false, why: 'لا صندوقَ رسالةٍ في الصفحة' };
  const line = box.querySelector('.view-line');
  if (!line) return { present: false, why: 'الصندوقُ حاضرٌ بلا سطرٍ مُصيَّر' };
  const node = line.firstChild && line.firstChild.nodeType === 3 ? line.firstChild
             : (line.querySelector('span') || {}).firstChild;
  const text = (line.textContent || '').replace(/\\u200b/g, '');
  if (text.trim().length < 4) return { present: false, why: 'الصندوقُ مفتوحٌ وفارغ — لا مقامَ يُقاس' };

  // (١) الاتّجاه: خريطةُ محرفٍ ⇒ x، ثمّ مقارنةُ الترتيب المنطقيّ بالمرئيّ.
  // ⚠️ **لا عقدةَ نصٍّ واحدة.** يلفّ Monaco السطرَ في عناصر span بحسب التلوين، فقراءةُ
  // firstChild وحدَها تُعيد null فيُبلَّغ «تعذّر القياس» ويُقرأ فشلًا — وقد وقع ذلك في أوّل
  // تشغيلةٍ لهذا المِجَسّ. نمشي على **كلّ** عُقَد النصّ تحت السطر.
  // **والمِسطرةُ الفاصلة ليست ترتيبَ المحارف.** نصٌّ عربيٌّ خالصٌ يُقلَب بصريًّا في الفقرة
  // ‏LTR كذلك (خوارزميّةُ bidi تعكس المقطعَ القويّ أيًّا كان مستوى الفقرة)، فـ«يبدأ من
  // اليمين» **يصدُق على الحالتين** ⇒ توكيدٌ صحيحُ الحكم لا يُميّز. والمُميِّزُ حقنُ المنبع
  // نفسِه: ‏viewLine.ts:181-195 يكتب dir="rtl" **حصرًا** عند textDirection === RTL،
  // ويكتب dir="ltr" عند نصٍّ فيه عربيّةٌ بلا اتّجاهٍ مضبوط — فالسمةُ تفرز الحالتين بعينهما.
  const dirAttr = line.getAttribute('dir');
  let visual = null, startsRight = null;
  try {
    const r = document.createRange(); const xs = [];
    const walk = document.createTreeWalker(line, NodeFilter.SHOW_TEXT);
    for (let n = walk.nextNode(); n; n = walk.nextNode()) {
      for (let i = 0; i < n.data.length; i++) {
        r.setStart(n, i); r.setEnd(n, i + 1);
        const b = r.getBoundingClientRect();
        if (b.width > 0) xs.push({ c: n.data[i], x: b.left });
      }
    }
    if (xs.length) {
      // **الحكمُ بمرساة الفقرة لا بانعكاسٍ كامل.** نصٌّ مختلطٌ في فقرةٍ RTL لا يُقلَب حرفًا
      // حرفًا (المقاطعُ اللاتينيّةُ تبقى بترتيبها داخلها)، فشرطُ «المرئيُّ = معكوسُ المنطقيّ»
      // يفشل على نصٍّ مختلطٍ **سليمِ الاتّجاه** ⇒ بلاغٌ كاذب. والسؤالُ الصحيح: من أيّ
      // حافّةٍ يبدأ السطر؟ في RTL يقع **أوّلُ** محرفٍ منطقيٍّ إلى يمين آخرِه.
      startsRight = xs[0].x > xs[xs.length - 1].x;
      const sorted = xs.slice().sort((p, q) => p.x - q.x);
      visual = sorted.map(o => o.c).join('');
    }
  } catch (e) { visual = null; }

  const cs = getComputedStyle(line);
  const size = parseFloat(cs.fontSize);
  const lh = cs.lineHeight === 'normal' ? size * 1.35 : parseFloat(cs.lineHeight);
  const ctx = document.createElement('canvas').getContext('2d');
  ctx.font = size + 'px ' + cs.fontFamily;
  const ink = (s) => { const m = ctx.measureText(s);
    return +(((m.actualBoundingBoxAscent || 0) + (m.actualBoundingBoxDescent || 0))).toFixed(2); };
  const w = (s) => +ctx.measureText(s).width.toFixed(3);

  // (٣) الوجه: تفاوتُ عرضِ أربعة رسومٍ يجب أن يكون شبهَ صفرٍ في وجهٍ أحاديّ.
  const widths = { M: w('M'), ا: w('ا'), م: w('م'), ص: w('ص') };
  const vals = Object.values(widths);
  const spread = +((Math.max(...vals) - Math.min(...vals)) / Math.max(...vals)).toFixed(4);

  // (٤) الأشكالُ السياقيّة: المُعلَنُ ثمّ الأثر. الضابطُ سطرُ المحرّر الرئيس.
  const editorLine = [...document.querySelectorAll('.monaco-editor .view-line')]
    .find(l => !l.closest('.scm-view'));
  const featOf = (el) => { const c = getComputedStyle(el);
    return (c.fontFeatureSettings || 'normal') + ' | ' + (c.fontVariantLigatures || 'normal'); };
  const ligaEffect = (font) => {
    const c2 = document.createElement('canvas').getContext('2d');
    c2.font = font;
    return +(c2.measureText('ببب').width - c2.measureText('ب\\u200Cب\\u200Cب').width).toFixed(3);
  };
  const boxFont = size + 'px ' + cs.fontFamily;
  const edCs = editorLine ? getComputedStyle(editorLine) : null;
  const edFont = edCs ? parseFloat(edCs.fontSize) + 'px ' + edCs.fontFamily : null;

  return {
    present: true,
    text, visual, startsRight, dirAttr,
    fontFamily: cs.fontFamily, fontSizePx: size,
    lineHeightPx: +lh.toFixed(2), lineHeightEm: +(lh / size).toFixed(3),
    extremes: ink('أٌإٍآً'), extremesRatio: +(ink('أٌإٍآً') / lh).toFixed(3),
    widths, monoSpread: spread,
    features: featOf(line),
    editorFeatures: editorLine ? featOf(editorLine) : null,
    ligaEffectBox: ligaEffect(boxFont),
    ligaEffectEditor: edFont ? ligaEffect(edFont) : null,
    editorFontSizePx: edCs ? parseFloat(edCs.fontSize) : null,
    editorFontFamily: edCs ? edCs.fontFamily : null,
    // **ضوابطُ الوصول.** الرقعةُ ‎032‎ تُقاس بالانتقال، والانتقالُ لا يُقاس بلا برهانٍ على
    // أنّ الكتابةَ بلغت التطبيقَ أصلًا. فالمحرّرُ الرئيسُ يقرأ المفاتيحَ الثلاثةَ اليوم بلا
    // رقعة؛ فإن لم يتحرّك هو فالعطبُ في مراقب الإعدادات لا في الصندوق، وذلك **أحمرُ كاذب**.
    editorDirAttr: editorLine ? editorLine.getAttribute('dir') : null,
    editorLineHeightPx: edCs ? +parseFloat(edCs.lineHeight).toFixed(2) : null,
  };
})()`;

/**
 * ‏[SC-02] مواضعُ ترويسات اللوحات الثلاث.
 *
 * ‏**و`top` و`width` يُعادان لا يُحسَبان ويُرمَيان**: كان المِقياسُ يحسب `width` ولا يطبعه
 * ولا يقرأ `top` أصلًا، فكان وصفُ «صفٌّ علويٌّ ولوحةٌ أسفلَه» **استنتاجًا من ثلاثة أرقامِ
 * ‏`left`** لا قياسَ تخطيط. سطران يحوّلان الاستنتاجَ إلى قياس.
 */
const MERGE_MEASURE = `(() => {
  const root = document.querySelector('.merge-editor');
  if (!root) return { present: false };
  const heads = [...root.querySelectorAll('.code-view > .header')].map(h => {
    const b = h.getBoundingClientRect();
    return { text: (h.textContent || '').trim().slice(0, 40), left: Math.round(b.left),
             top: Math.round(b.top), width: Math.round(b.width) };
  });
  const cs = getComputedStyle(root);
  heads.sort((a, b) => a.left - b.left);
  return { present: true, panes: heads.length, direction: cs.direction, heads,
           order: heads.map(h => h.text + '@' + h.left) };
})()`;

/**
 * ‏[SC-02] **تأكيدُ القرار التاسع — لا سطرُ سجلٍّ يُطبَع ويُقرأ.**
 *
 * القرارُ في `docs/rtl/typography-decisions.md` **قبِل** انعكاسَ الصفّ العلويّ: ‏`Current`
 * في مبتدأ القراءة العربيّة (يمينًا) و`Incoming` في منتهاها (يسارًا) — لأنّ القلبَ حفِظ
 * رتبةَ git (‏`Current` يسبق `Incoming`‏) وغيّر إخراجَها وحدَه.
 *
 * وقرارُ القبول قرارُ **إبقاءٍ**، وأخطرُ ما يصيبه أن يُنقَض ضمنًا بتحديثِ منبعٍ أو رقعة.
 * فيصير مُعطًى القياسِ **حكمًا يسقط عند البوّابة** لا رقمًا في تقرير.
 *
 * والحكمُ يُبنى على الترويستين بأسمائهما لا بترتيبهما في DOM: الأخيرُ لا يُقلَب بـ`dir`
 * أصلًا، فالحكمُ عليه كان سيُصادق على أيّ شيء.
 */
function judgeMergeOrder(m) {
  if (!m || !m.present) return { measured: false, why: "محرّرُ الدمج لم يُفتَح" };
  if (m.direction !== "rtl") return { measured: false, why: `جذرُ محرّر الدمج ${m.direction} لا rtl` };
  const find = (needle) => (m.heads || []).find((h) => h.text.includes(needle));
  const cur = find("Current");
  const inc = find("Incoming");
  if (!cur || !inc) {
    // ‏**فجوةٌ تُقال ولا تُهرَّب**: تعريبُ الترويستين مطلوبٌ ودَينٌ في صلب القرار، فحين
    // يقع يسقط هذا الكشفُ بالسلسلة الإنجليزيّة — ولا يجوز أن يُقرأ سقوطُه «مرّ الفحص».
    return { measured: false, why: "لم تُميَّز ترويستا Current/Incoming بأسمائهما (تعريبٌ أو تغييرُ منبع)" };
  }
  return {
    measured: true,
    ok: cur.left > inc.left,
    detail: `Current@${cur.left} · Incoming@${inc.left}`,
  };
}

try {
  log("بناءُ مستودعٍ زائلٍ بتعارضٍ حقيقيّ…");
  const mergeOut = buildRepo();
  log(`git merge: ${mergeOut.trim().split("\n").slice(-1)[0]}`);

  log("إطلاق النسخة المشحونة بملفّ تعريفٍ معزول…");
  launch();
  const cdp = await attach();
  await sleep(9000);

  // **الضابطُ أوّلًا:** يُفتَح ملفٌّ في جزء المحرّر بـ`Ctrl+P` واسمِ الملفّ — لا باسم أمرٍ
  // مترجَم. بلا سطرِ محرّرٍ مُصيَّرٍ لا ضابطَ لقياس الأشكال السياقيّة، فيُبلَّغ «غير مقيس»
  // بلا سببٍ حقيقيّ — وهو تخطٍّ يُخفي نتيجةً كانت ستُقاس.
  await key(cdp, 80, "KeyP", MOD.CTRL); await sleep(1200);
  await cdp.cmd("Input.insertText", { text: "ثانٍ" }); await sleep(1500);
  await key(cdp, 13, "Enter"); await sleep(2500);

  // ═══ (أ) SC-01 — قياسُ صندوق رسالة الالتزام ═══
  const opened = await openScm(cdp);
  if (!opened) {
    gap("SC-01: صندوق رسالة الالتزام", "لم يُفتَح جزءُ المصادر (لا `.scm-editor-container`)");
  } else {
    // الصندوقُ الفارغُ لا مقامَ فيه يُقاس: نحقن جملةً **مشكولةً** (حبرٌ حدّيٌّ فعلًا)
    // ونقرؤها استرجاعًا بنزع `​`. ولا نعتمد على قيمةٍ يعيدها الإدخال: الصندوقُ
    // محرّرُ Monaco فلا حقلَ يُقَرّ.
    await clickSelector(cdp, ".scm-view .scm-editor-container .monaco-editor");
    await sleep(400);
    // ‏**git يملأ الصندوقَ برسالة الدمج** («‏Merge branch…») في مستودعٍ متعارض. فلولا
    // التفريغُ لَقِسنا سلسلةً إنجليزيّةً ظنًّا أنّها جملتُنا العربيّة — قياسٌ صحيحُ الرقم
    // خاطئُ الموضوع. ‏(Ctrl+A داخل صندوقٍ **نملكه** لا في محرّر المستخدم.)
    await key(cdp, 65, "KeyA", MOD.CTRL); await sleep(200);
    await key(cdp, 46, "Delete"); await sleep(300);
    await cdp.cmd("Input.insertText", { text: "أصلِحُ اتّجاهَ العدسةِ في مِحرابٍ" });
    await sleep(1200);
    const m = await cdp.evaluate(MEASURE);
    if (!m || !m.present) {
      gap("SC-01: صندوق رسالة الالتزام", m ? m.why : "تعذّر التقييم");
    } else {
      console.log(`  · المقيس: خطّ «${m.fontFamily}» ${m.fontSizePx}px · سطر ${m.lineHeightPx}px ` +
                  `(${m.lineHeightEm}em) · تفاوت ${(m.monoSpread * 100).toFixed(1)}٪`);
      console.log(`  · المنطقيّ: ${JSON.stringify(m.text)}`);
      console.log(`  · المرئيّ  : ${JSON.stringify(m.visual)}`);
      console.log(`  · السمات: صندوق «${m.features}» · محرّر «${m.editorFeatures}»`);
      console.log(`  · أثرُ الوصل: صندوق ${m.ligaEffectBox} · محرّر (ضابط) ${m.ligaEffectEditor}`);

      // (١) الاتّجاه — **بسمة `dir` التي يكتبها المنبعُ، لا بترتيب المحارف**. الترتيبُ
      // يُبقى مطبوعًا للقارئ (خطُّ «المرئيّ» أعلاه) لأنّه يشرح، لكنّه لا يحكم: يصدُق في
      // ‏LTR أيضًا على نصٍّ عربيٍّ خالص. والحكمُ على ما لا يكتبه المنبعُ إلّا في RTL.
      // ⚠️ التفصيلُ يُطبَع في الحالتين (‏`ok` يُلحِقه بالنجاح كما بالفشل)، فيُصاغ **وصفًا
      // للمقيس** لا شرحًا للفشل. وصياغةٌ تقول «كذا لا كذا» تُقرأ فشلًا تحت علامة نجاح.
      ok(m.dirAttr === "rtl", "SC-01/الاتّجاه: الصندوقُ يُصيَّر من اليمين",
        `سمةُ dir على السطر = ${m.dirAttr === null ? "غائبة" : `«${m.dirAttr}»`}؛ والمطلوب «rtl». ` +
        `‏viewLine.ts:181-195 لا يكتبها إلّا عند textDirection === RTL، ويكتب «ltr» عند ` +
        `عربيّةٍ بلا اتّجاهٍ مضبوط — فهي تفرز الحالتين. المسارُ بعد [DR-02]: ` +
        `getSimpleEditorOptions يقرأ editor.textDirection بمعرِّف 'scminput' (رقعةُ النواة 030)، ` +
        `فتسري كتلةُ [scminput] من configurationDefaults = rtl. والجذرُ اليوم ltr، ` +
        `فهذا التوكيدُ يفشل إن سقط المعرِّفُ أو سقطت الكتلة — وهو ضابطُ صفقةِ القلب.`);

      // (٢) ارتفاعُ السطر — **هامشٌ لا انعدامُ قصّ**، بأرضيّة الحبر المقيسة.
      ok(m.lineHeightEm >= INK_FLOOR_EM,
        `SC-01/ارتفاعُ السطر ≥ ${INK_FLOOR_EM}em`,
        `${m.lineHeightEm}em (${m.lineHeightPx}px على ${m.fontSizePx}px) — ` +
        `رقعةُ النواة ‎030‎ جعلت الصندوقَ يحترم editor.lineHeight بدل نسبةٍ لاتينيّةٍ ثابتة (1.5). ` +
        `قبلها: 15×1.5 ⇒ 23px (دون الأرضيّة 1.88em). بعدها: المقيسُ أعلاه.`);

      // (٣) الوجه — بالتفاوت لا بالاسم (درسُ VA-02ب).
      ok(m.monoSpread <= 0.02, "SC-01/الوجه: أحاديُّ العرض مطبَّقٌ فعلًا",
        `تفاوت ${(m.monoSpread * 100).toFixed(1)}٪ · «${m.fontFamily}»`);

      // (٤) الأشكالُ السياقيّة — الضابطُ أوّلًا: بلا أثرٍ في المحرّر لا حكمَ على الصندوق.
      if (m.ligaEffectEditor === null) {
        gap("SC-01/الأشكالُ السياقيّة", "لا سطرَ محرّرٍ مُصيَّرٍ ضابطًا");
      } else if (Math.abs(m.ligaEffectEditor) < 0.01) {
        // **الضابطُ عجز، والمُعلَنُ لا يعجز.** قياسُ الأثر بالقماش لا يُظهِر فرقًا (الوصلُ
        // العربيُّ الإلزاميّ init/medi/fina لا يُطفئه `calt off`، فالعرضُ لا يتغيّر). فلا
        // نُبلِّغ «سليم» ولا نُبلِّغ «مجهول»: نحكم على ما **قِيس فعلًا** — قيمةُ
        // `font-feature-settings` المحسوبةُ على العنصر — ونقول صراحةً أنّ أثرَ التصيير
        // لم يُقَس. فرقُ الإعلان حقيقةٌ قابلةٌ للقياس، وحدُّه يُقال ولا يُهرَّب.
        ok(m.features === m.editorFeatures,
          "SC-01/الأشكالُ السياقيّة (المُعلَن): الصندوقُ كالمحرّر",
          `صندوق «${m.features}» ${m.features === m.editorFeatures ? "=" : "≠"} محرّر ` +
          `«${m.editorFeatures}» — والمطلوبُ التطابق: fontLigatures تبلغ المحرّرَ البسيطَ ` +
          `برقعة النواة ‎030‎، فتباعدُهما يعني سقوطَها. ` +
          `‏(أثرُ التصيير لم يُقَس: الضابطُ لم يُظهِر فرقًا بالقماش.)`);
      } else {
        ok(Math.abs(m.ligaEffectBox - m.ligaEffectEditor) < 0.01,
          "SC-01/الأشكالُ السياقيّة: الصندوقُ كالمحرّر",
          `أثرُ الصندوق ${m.ligaEffectBox} ≠ أثرُ المحرّر ${m.ligaEffectEditor} — ` +
          `fontLigatures تبلغ الصندوقَ الآن برقعة النواة ‎030‎`);
      }

      // ═══ هل تُنقِذ الطبقةُ الثانيةُ شيئًا؟ **يُقاس ولا يُفترَض** ═══
      // التقريرُ رجّح أنّ ثلاثةً من الخمسة تُعالَج بورقة أنماط. وهذه فرضيّةٌ تُختبَر لا
      // تُنفَّذ: نحقن القاعدةَ المرشَّحة **حيًّا** ونقيس ما تغيّر فعلًا، فما لم يتغيّر لا
      // يُكتَب في الورقة — وإلّا شحنّا قواعدَ ميّتةً تجتاز الحرّاسَ وهي لا تفعل شيئًا
      // (وقد وقع ذلك في هذا المستودع: القاعدةُ 20 اجتازت L0 وL2 وهي شيفرةٌ ميّتة).
      const css = await cdp.evaluate(`(() => {
        const box = document.querySelector('.scm-view .scm-editor-container .monaco-editor');
        const line = box && box.querySelector('.view-line');
        if (!line) return null;
        const boxOf = (el) => { const b = el.getBoundingClientRect(); return Math.round(b.height); };
        const before = { feat: getComputedStyle(line).fontFeatureSettings,
                         lh: getComputedStyle(line).lineHeight, h: boxOf(line),
                         inline: line.getAttribute('style') };
        const s = document.createElement('style');
        s.textContent = '.scm-view .scm-editor-container .monaco-editor .view-line,'
          + ' .scm-view .scm-editor-container .monaco-editor .view-line span'
          + ' { font-feature-settings: "calt" 1, "liga" 1 !important; }'
          + ' .scm-view .scm-editor-container .monaco-editor .view-line'
          + ' { line-height: 1.95em !important; }';
        document.head.appendChild(s);
        const after = { feat: getComputedStyle(line).fontFeatureSettings,
                        lh: getComputedStyle(line).lineHeight, h: boxOf(line) };
        s.remove();
        return { before, after };
      })()`);
      if (css) {
        const featFixed = css.before.feat !== css.after.feat;
        const boxGrew = css.after.h > css.before.h;
        console.log(`  · جدوى الطبقة الثانية: السمات «${css.before.feat}» ⇒ «${css.after.feat}» · ` +
                    `صندوقُ السطر ${css.before.h}px ⇒ ${css.after.h}px · inline=${JSON.stringify(css.before.inline)}`);
        // **انقلب اتّجاهُ هذا التأكيد** مع رقعة النواة ‎030‎: كان يشهد بأنّ حقنَ الورقة
        // **يُغيِّر** القيمة (فتلزم القاعدة ‎37‎)، وصار يشهد بأنّ الأشكالَ عاملةٌ **قبل أيّ
        // حقن** — لأنّ المفتاحَ يبلغ المحرّرَ البسيطَ من المصدر. فحُذفت القاعدةُ ‎37‎، وبقي
        // الشاهدُ ليمسك سقوطَ الرقعة. و`featFixed` صار المتوقَّعُ فيه **الثبات** لا التغيّر.
        const shaped = /calt/.test(css.before.feat) && !/calt"?\s*0/.test(css.before.feat);
        ok(shaped, "SC-01/ب: الأشكالُ السياقيّةُ عاملةٌ في الصندوق **بلا ورقة** (رقعة ‎030‎)",
          `المحسوب قبل أيّ حقن: «${css.before.feat}» — والمطلوبُ calt مفعَّلة؛ ` +
          `إطفاؤها هنا يعني سقوطَ الرقعة ‎030‎.`);
        if (featFixed) console.log("  ℹ️  حقنُ الورقة ما يزال يُغيِّر القيمة — القاعدةُ ‎37‎ قد تلزم ثانيةً (سقطت الرقعة؟).");
        if (!boxGrew) {
          console.log("  ℹ️  و**ارتفاعُ السطر لا تصلحه الورقة**: صندوقُ السطر لم يكبر بحقن " +
            "line-height، لأنّ Monaco يحسب ارتفاعَ السطر في JS ويكتبه سمةً مضمَّنة. " +
            "فيبقى هذا الشقُّ لِـم-١٧ وحدَه — ولا تُكتَب له قاعدةٌ ميّتة.");
        }
      }

      // (٥) حجمُ الخطّ — مقيسٌ لا مقروء.
      ok(m.fontSizePx === EDITOR_FONT_SIZE,
        `SC-01/حجمُ الخطّ = ${EDITOR_FONT_SIZE} المقيس في VA-04`,
        `المقيس ${m.fontSizePx}px · المحرّر ${m.editorFontSizePx}px`);

      // ═══ (٦) التجدُّدُ الحيّ — رقعةُ النواة ‎032‎ [SC-01/د · م-١٧] ═══
      //
      // **وكلُّ ما فوقَ هذا السطر لا يحرس الرقعةَ ‎032‎ إطلاقًا.** توكيداتُ الحال —
      // ‏`dirAttr === "rtl"` و`lineHeightEm >= 1.88` و`features === editorFeatures` —
      // تمرّ برقعة ‎030‎ وحدَها، فهي **خضراءُ قبل ‎032‎ وبعدها سواء**. وحارسٌ لا يفرّق بين
      // وجود الرقعة وعدمِها حارسٌ صوريّ. فالمقياسُ هنا **انتقالٌ داخل الجلسة الواحدة**:
      // يُقاس الحال، ثمّ يُكتب مفتاحٌ **واحد**، ثمّ يُنتظَر انقلابُ المقيس.
      //
      // وثلاثةُ شروطٍ تجعل الانتقالَ فارزًا، سقوطُ أيٍّ منها يُعيده إلى «أخضرَ في الحالتين»:
      //   (أ) **إعدادٌ واحدٌ في كلّ كتابة.** المرشِّحُ القائمُ في المنبع يذكر `editor.fontFamily`
      //       و`scm.inputFontSize` وغيرَهما؛ فتغييرُ إعدادَين معًا يُنعِش الصندوقَ بالإعداد
      //       **القديم** فيُقرأ تجدُّدًا وليس به.
      //       ⚠️ وبعد [DR-02] صارت كتابةُ الاتّجاه **مفتاحَين نصًّا وإعدادًا واحدًا معنًى**:
      //       ‏`[plaintext]` و`[scminput]`، وكلاهما `editor.textDirection`. والشرطُ يحرس
      //       ‏`affectsConfiguration(<إعداد>)` لا عددَ المفاتيح المكتوبة، وهو لا يُخرَق هنا:
      //       المُرشِّحُ يرى الإعدادَ نفسَه من الكتابتين. وسببُ لزومِهما أنّ الجذرَ لم يعد
      //       يبلغ أيًّا من السطحين: الصندوقُ يقرأ بمعرِّف `scminput`، والضابطُ ملفُّ
      //       ‏`ثانٍ.txt` يقرأ بمعرِّف `plaintext` — وكلٌّ منهما له كتلةُ `rtl` في القشرة تغلب
      //       جذرَ إعدادات المستخدم (تجاوزُ اللغة يُطبَّق فوق المدمَج، لا تحته).
      //   (ب) **ضابطُ وصول.** بعد كلّ كتابةٍ يُقاس المحرّرُ الرئيس: هو يقرأ المفاتيحَ الثلاثةَ
      //       اليوم بلا رقعة. فإن لم يتحرّك، فالكتابةُ لم تبلغ التطبيقَ ⇒ فجوةٌ معلَنةٌ لا فشل.
      //   (ج) **لا إعادةَ تحميل، ولا نومٌ ثابت**: استطلاعٌ بمهلة، ونفادُها يُقال فجوةً.
      //
      // ولا تُجرَّب `rtl ⇄ auto`: تحت واجهةٍ عربيّةٍ تُحسَب `auto` إلى `rtl`
      // (‏`EffectiveTextDirection.compute` ⇒ `isRtlLanguage(platform.language)`)، فالتجربةُ
      // **تنجح فارغة**. المُميِّزُ هو `ltr` صراحةً.
      const settingsPath = SETTINGS_PATH;
      const writeOne = (patch) => writeFileSync(settingsPath,
        JSON.stringify({ ...BASE_SETTINGS, ...patch }, null, 2), "utf8");
      /** يستطلع القياسَ حتّى يتحقّق الشرطُ أو تنفد المهلة. يُعيد آخرَ قراءةٍ دائمًا. */
      const settle = async (pred, ms = 12000) => {
        const t0 = Date.now();
        let last = null;
        while (Date.now() - t0 < ms) {
          last = await cdp.evaluate(MEASURE);
          if (last && last.present && pred(last)) return last;
          await sleep(400);
        }
        return last;
      };

      for (const t of [
        {
          name: "الاتّجاه",
          patch: {
            "[scminput]": { "editor.textDirection": "ltr" },
            "[plaintext]": { "editor.textDirection": "ltr" },
          },
          read: (x) => x.dirAttr, control: (x) => x.editorDirAttr,
          // الأساسُ `rtl` من كتلتَي `[scminput]` و`[plaintext]` في `configurationDefaults`،
          // وكتلتا المستخدمِ تغلبانهما (تجاوزُ لغةٍ فوق تجاوزِ لغة، أعلى نطاقًا يفوز).
          // و`viewLine.ts` يكتب `dir="ltr"` صراحةً على عربيّةٍ في فقرةٍ LTR — فالقيمةُ
          // ثلاثيّةٌ (rtl · ltr · غائبة) ولا تُختصَر إلى «موجودة».
          want: "ltr",
        },
        {
          name: "ارتفاعُ السطر", patch: { "editor.lineHeight": 40 },
          read: (x) => x.lineHeightPx, control: (x) => x.editorLineHeightPx,
          want: 40,
        },
        {
          name: "الأشكالُ السياقيّة", patch: { "editor.fontLigatures": false },
          read: (x) => x.features, control: (x) => x.editorFeatures,
          want: null, // لا قيمةَ متوقَّعةٌ بعينها — المطلوبُ **تغيُّرٌ** عن الأساس
        },
      ]) {
        const before = await cdp.evaluate(MEASURE);
        if (!before || !before.present) { gap(`SC-01/د: ${t.name}`, "تعذّر قياسُ الأساس"); continue; }
        const b = t.read(before), bc = t.control(before);
        if (t.want !== null && b === t.want) {
          // الأساسُ يساوي الهدفَ سلفًا ⇒ الانتقالُ غيرُ قابلٍ للقياس، ولو خضّرناه لكان
          // أخضرَ في الحالتين. يُقال فجوةً لا نجاحًا.
          gap(`SC-01/د: ${t.name}`, `الأساسُ يساوي الهدفَ سلفًا (${b}) — لا انتقالَ يُقاس`);
          continue;
        }
        writeOne(t.patch);
        const after = await settle((x) => t.read(x) !== b && t.control(x) !== bc);
        const a = t.read(after), ac = t.control(after);
        if (ac === bc) {
          gap(`SC-01/د: ${t.name}`,
            `الضابطُ لم يتحرّك (المحرّرُ الرئيس ${bc} ⇒ ${ac}) — الكتابةُ لم تبلغ التطبيق، ` +
            `فلا يُحكَم على الصندوق`);
        } else {
          ok(a !== b && (t.want === null || a === t.want),
            `SC-01/د: ${t.name} يتجدّد حيًّا بلا إعادة تحميل [رقعة ‎032‎]`,
            `الصندوق ${b} ⇒ ${a} · الضابط ${bc} ⇒ ${ac}. ` +
            `تساويهما قبلًا وبعدًا يعني أنّ المفتاحَ التُقِط عند الإنشاء ولم يتبع تغيُّرَه.`);
        }
        writeFileSync(settingsPath, JSON.stringify(BASE_SETTINGS, null, 2), "utf8");
        await settle((x) => t.read(x) === b, 8000);
      }
    }
  }

  // ═══ (ب) SC-02 — محرّرُ الدمج ثلاثيُّ اللوحات ═══
  log("فتحُ محرّر الدمج على تعارضٍ حقيقيّ…");
  let mergeOpened = false;
  const rows = await cdp.evaluate(`(() => {
    const pts = [];
    for (const r of document.querySelectorAll('.scm-view .monaco-list-row')) {
      if (!r.querySelector('.resource .monaco-icon-label')) continue;
      const b = r.getBoundingClientRect();
      if (b.height < 8) continue;
      const x = Math.round(b.left + b.width / 2), y = Math.round(b.top + b.height / 2);
      const at = document.elementFromPoint(x, y);
      if (at && r.contains(at)) pts.push({ x, y, t: (r.textContent || '').trim().slice(0, 30) });
      if (pts.length >= 8) break;
    }
    return pts; })()`);
  for (const p of rows) {
    await cdp.cmd("Input.dispatchMouseEvent", { type: "mousePressed", x: p.x, y: p.y, button: "left", clickCount: 1 });
    await cdp.cmd("Input.dispatchMouseEvent", { type: "mouseReleased", x: p.x, y: p.y, button: "left", clickCount: 1 });
    await sleep(2500);
    if (await cdp.evaluate(`document.querySelectorAll('.merge-editor').length`)) { mergeOpened = true; break; }
  }
  if (!mergeOpened) {
    gap("SC-02: محرّرُ الدمج ثلاثيّ اللوحات",
      `لم يُفتَح على أيٍّ من ${rows.length} مورِدًا — راجِع git.mergeEditor وحالةَ التعارض`);
  } else {
    const g = await cdp.evaluate(MERGE_MEASURE);
    console.log(`  · اللوحات: ${g.panes} · اتّجاه الجذر ${g.direction}`);
    console.log(`  · ترتيبُ الترويسات من اليسار: ${JSON.stringify(g.order)}`);
    console.log(`  · مواضعُ الترويسات (top·left·width): ${JSON.stringify(g.heads)}`);
    ok(g.panes >= 3, "SC-02: المحرّرُ الثلاثيُّ مفتوحٌ بثلاث لوحات", `${g.panes} لوحة`);
    // **القرارُ التاسعُ صار تأكيدًا** — قبولُ الانعكاس قرارُ إبقاءٍ، وأخطرُ ما يصيبه أن
    // يُنقَض ضمنًا بتحديثِ منبعٍ أو رقعة. فيسقط هنا عند البوّابة لا عند المستخدم.
    const j = judgeMergeOrder(g);
    if (!j.measured) {
      gap("SC-02/ترتيبُ اللوحات", j.why);
    } else {
      ok(j.ok, "SC-02: Current في مبتدأ القراءة العربيّة و Incoming في منتهاها [القرار ٩]", j.detail);
    }
  }

  if (!KEEP) { cdp.close(); kill(); }
} catch (e) {
  console.error(`❌ خطأ تشغيليّ: ${e.message}`);
  kill();
  if (!KEEP) rmSync(tmp, { recursive: true, force: true });
  process.exit(2);
}

await sleep(1000);
if (!KEEP) rmSync(tmp, { recursive: true, force: true });
console.log(failed ? `─── ${failed} تأكيدًا فشل ───` : "─── قياسُ SC-01/SC-02 تمّ ───");
process.exit(failed ? 1 : 0);
