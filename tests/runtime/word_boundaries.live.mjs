// L3 حيّ ‏[IN-01]: حدُّ الكلمة العربيّة — هل بلغت قائمةُ الفواصل المشحونةُ المحرّرَ فعلًا؟
//
// ## لماذا هذا الملفّ موجود
// ‏`editor.wordSeparators` المنبعيّة (‏`wordHelper.ts:10`) لا تحوي محرفًا عربيًّا واحدًا،
// فالنقرُ المزدوجُ على كلمةٍ في تعليقٍ عربيٍّ يلتقط معها الفاصلةَ «،»، و‏Ctrl+Shift+→ يقفز
// فوق الجملة. وشحنّا قائمةً بديلةً في `mihrab-shell` — و**القيمةُ تستبدل الافتراضَ ولا
// تضيف إليه**، فخطأٌ في نسخ البادئة عطبٌ فادحٌ لا يرمي خطأً. الحارسُ الساكن يمسك النصَّ،
// وهذا الملفُّ يمسك ما لا يمسكه نصّ: **هل وصلت القيمةُ إلى المحرّر أصلًا؟**
//
// ## الفخُّ الذي بُني هذا المِجَسُّ لتفاديه
// كلُّ تأكيداتِ هذا الباب **سالبة** بطبعها («لم يُشقّ المُعرِّف»، «لم تُلتقَط الفاصلة») —
// وهي تنجح نجاحًا باهرًا **والقيمةُ لم تُشحَن إطلاقًا**، لأنّ الحزمةَ قد تسبق المصدر
// أو لأنّ المفتاحَ رُفض في التحقّق. فالترتيبُ هنا مُلزِم: **لا يُقرأ تأكيدٌ سالبٌ قبل أن
// ينجح شاهدُ التفعيل** — حالةٌ موجبةٌ تُثبِت أنّ المِسطرة تبدّلت فعلًا. وإن سقط الشاهدُ
// فالنتيجةُ `gap()`: «لم تصل القيمة»، لا «لم ينكسر شيء». وهو شكلُ DG-01 بعينه: النطاقُ
// الخالي من المحتوى يُبلِّغ نظيفًا.
//
// ## ولماذا يُقرأ التحديدُ من لوح البحث لا من البكسل
// في محرّرٍ بـ`textDirection: rtl` مستطيلُ التحديد **بصريّ**، و«يسارُ» الشاشة ليس «يسارَ»
// النموذج — فقارئٌ يقيس المستطيلاتِ يقيس الرسمَ لا القرار. ولوحُ البحث يُبذَر من التحديد
// (‏`editor.find.seedSearchStringFromSelection`)، وقيمةُ حقلِه **نصٌّ من النموذج**: محايدةٌ
// للاتّجاه، وقابلةٌ للمقارنة حرفًا بحرف. ولا حافظةَ في الطريق (‏`navigator.clipboard`
// تشترط تركيزًا وإذنًا وترتدّ إلى تخطٍّ صامت — الدرسُ مدفوعٌ في `m6.live.mjs`).
//
// ## العزل
// مساحةٌ زائلةٌ في `tmp` وملفُّ تعريفٍ معزول — لا يُمسّ شيءٌ للمستخدم.
//
// الاستعمال: node tests/runtime/word_boundaries.live.mjs [--keep]
// خرج 0 = القياسُ تمّ (نجاحًا أو بفجوةٍ **معلَنة**) · 1 = تأكيدٌ فشل · 2 = خطأ تشغيليّ.
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { CDP, sleep, MOD, bringToFront } from "./harness.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const EXE = join(ROOT, ".upstream", "VSCode-win32-x64", "Mihrab.exe");
const PORT = 9337;
const KEEP = process.argv.includes("--keep");

const log = m => console.log(`▶ ${m}`);
let failed = 0;
const ok = (cond, name, detail = "") => {
  if (cond) console.log(`  ✅ ${name}${detail ? " — " + detail : ""}`);
  else { failed++; console.log(`  ❌ ${name}${detail ? "\n       " + detail : ""}`); }
};
/** فجوةٌ **معلَنة**: لم يُقَس، ويُقال إنّه لم يُقَس. */
const gap = (name, why) => console.log(`  ⏭️  ${name} — غير مقيس (فجوة معلَنة): ${why}`);

if (!existsSync(EXE)) { console.error(`❌ لا حزمة مشحونة: ${EXE}`); process.exit(2); }

// ───────────────────── القيمةُ المصدريّة (للمقارنة لا للاشتقاق) ─────────────────────
// تُقرأ من المصدر كي تُقال في التقرير حين تسقط، فيُميَّز «الحزمةُ أقدمُ من المصدر» من
// «القيمةُ خطأ». وهما عطبان مختلفان وعلاجُهما مختلف.
let SOURCE_SEPS = null;
try {
  SOURCE_SEPS = JSON.parse(readFileSync(join(ROOT, "extensions", "mihrab-shell", "package.json"), "utf8"))
    ?.contributes?.configurationDefaults?.["editor.wordSeparators"] ?? null;
} catch { /* يبقى null ويُقال */ }

// ───────────────────────── الحالاتُ المقيسة ─────────────────────────
// كلُّ حالةٍ سطرٌ مستقلّ. المؤشّرُ يوضَع بـ«اذهب إلى سطر» (‏سطر:عمود) — لا نقرةَ بالبكسل —
// ثمّ `Ctrl+Shift+→` يمدّ التحديدَ إلى **نهاية الكلمة التالية** (‏`cursorWordEndRightSelect`،
// وهو أحدُ المسارَين اللذين يبنيان مِسطرتَهما من `wordSeparators`، والآخرُ النقرُ المزدوج).
const CASES = [
  { line: 1, col: 1, text: "السلام، عليكم", want: "السلام", role: "شاهدُ التفعيل",
    note: "بالمِسطرة اللاتينيّة تُلتقَط «السلام،» ومعها الفاصلة" },
  { line: 2, col: 1, text: "نصاب_الفضة", want: "نصاب_الفضة", role: "ضابطُ المُعرِّف",
    note: "الشرطةُ السفليّةُ ليست فاصلًا في أيٍّ من القائمتين — المُعرِّفُ لا يُشقّ" },
  { line: 3, col: 1, text: "اطبع(نص)", want: "اطبع", role: "ضابطُ البادئة",
    note: "‏«(» من الواحدِ والثلاثين المنبعيّة — سقوطُه يعني أنّ البادئةَ لم تُنسَخ" },
  { line: 4, col: 1, text: "كيف؟ حالك", want: "كيف", role: "مكسب" },
  { line: 5, col: 1, text: "جملة۔ ثانية", want: "جملة", role: "مكسب" },
  { line: 6, col: 1, text: "٣٫١٤ عدد", want: "٣٫١٤", role: "ضابطُ الاستثناء",
    note: "‏«٫» فاصلُ عددٍ لا ترقيم — استُثنيت عمدًا، فالعددُ يبقى كلمةً واحدة" },
];

// ───────────────────────── المساحةُ الزائلة ─────────────────────────
const tmp = mkdtempSync(join(tmpdir(), "mihrab-in01-"));
const userData = join(tmp, "user-data");
const ws = join(tmp, "مساحة");
mkdirSync(join(userData, "User"), { recursive: true });
mkdirSync(join(ws, ".vscode"), { recursive: true });

const file = join(ws, "حدود.txt");
writeFileSync(file, CASES.map(c => c.text).join("\n") + "\n", "utf8");

// البذرُ من التحديد مُصرَّحٌ به لا متروكٌ للافتراض: قارئُنا كلُّه مبنيٌّ عليه، فلو تغيّر
// افتراضُ المنبع صار المِجَسُّ يقرأ حقلًا فارغًا ويُبلِّغ إخفاقًا كاذبًا في المنتج.
writeFileSync(join(userData, "User", "settings.json"), JSON.stringify({
  "editor.find.seedSearchStringFromSelection": "always",
  "editor.minimap.enabled": false,
  "workbench.startupEditor": "none",
  // ‏**جولةُ الترحيب تُغلَق بالإعداد لا بالنقر.** إبقاؤها مفتوحةً يجعل زرًّا فيها
  // (‏`BUTTON.getting-started-step`) يستردّ التركيزَ بعد تنشيط تبويبنا بمئات المللي،
  // فتذهب ضغطاتُ المفاتيح إليها ويُقرأ «لم يقع تحديد» عطبًا في المنتج.
  "workbench.welcomePage.walkthroughs.openOnInstall": false,
  "window.restoreWindows": "none",
  "update.mode": "none",
}, null, 2), "utf8");

/** ⚠️ فخُّ `ELECTRON_RUN_AS_NODE` الموروث — موثَّقٌ في `launch.mjs` و`scm_input.live.mjs`. */
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
    "--disable-workspace-trust", "--new-window", ws, file,
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

/** ينتظر ظهورَ سطرٍ مُصيَّرٍ فيه نصُّ الحالة الأولى — «فُتح» لا «أُطلِق». */
async function waitEditor(cdp, timeoutMs = 90000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    const seen = await cdp.evaluate(
      `[...document.querySelectorAll('.editor-group-container.active .view-line')].some(l => (l.textContent||'').includes('السلام'))`);
    if (seen === true) return true;
    await sleep(1000);
  }
  return false;
}

/**
 * يُنشِّط تبويبَ ملفِّ الحالات — **شرطٌ يسبق كلَّ شيء، وقد كلّف تشغيلةً كاملة**.
 *
 * محرابٌ يفتح جولةَ الترحيب عند أوّل إقلاع، وهي تبويبٌ **نشط** يسبق ملفَّنا. ‏فتحُ الملفّ
 * إذن لا يعني أنّه المعروض: `.view-line` موجودةٌ في الصفحة (فيمرّ انتظارُ التصيير)،
 * والنقرةُ عليها تقع، ثمّ يعود التركيزُ إلى زرٍّ في الجولة — `BUTTON.getting-started-step`.
 * فتذهب كلُّ ضغطةِ مفتاحٍ إلى الجولة ويُقرأ «لم يقع تحديد» عطبًا في المنتج. وهو الشكلُ
 * الرابعُ لفخّ «النطاقُ الخالي من المحتوى يُبلِّغ نظيفًا»: السطحُ حاضرٌ وليس هو المخاطَب.
 */
/** يُغلق كلَّ تبويبٍ سوى تبويب الحالات — الإعدادُ يمنع الجولةَ، وهذا يمسك ما نجا منه. */
async function closeOtherTabs(cdp) {
  for (let i = 0; i < 8; i++) {
    const p = await cdp.evaluate(`(() => {
      const t = [...document.querySelectorAll('.tabs-container .tab')]
        .find(e => !(e.textContent || '').includes('حدود'));
      if (!t) return null;
      const x = t.querySelector('.tab-actions .action-label, .tab-actions a, .codicon-close');
      const b = (x || t).getBoundingClientRect();
      if (b.width < 4 || b.height < 4) return null;
      return { x: Math.round(b.left + b.width / 2), y: Math.round(b.top + b.height / 2), had: !!x };
    })()`);
    if (!p) return true;
    if (!p.had) return false;
    await cdp.cmd("Input.dispatchMouseEvent", { type: "mousePressed", x: p.x, y: p.y, button: "left", clickCount: 1 });
    await cdp.cmd("Input.dispatchMouseEvent", { type: "mouseReleased", x: p.x, y: p.y, button: "left", clickCount: 1 });
    await sleep(700);
  }
  return false;
}

async function activateOurTab(cdp) {
  for (let i = 0; i < 6; i++) {
    const active = await cdp.evaluate(
      `(() => { const t = document.querySelector('.tabs-container .tab.active');
        return t ? (t.textContent || '') : null; })()`);
    if (typeof active === "string" && active.includes("حدود")) return true;
    const p = await cdp.evaluate(`(() => {
      const t = [...document.querySelectorAll('.tabs-container .tab')]
        .find(e => (e.textContent || '').includes('حدود'));
      if (!t) return null;
      const b = t.getBoundingClientRect();
      if (b.width < 4 || b.height < 4) return null;
      return { x: Math.round(b.left + b.width / 2), y: Math.round(b.top + b.height / 2) };
    })()`);
    if (!p) { await sleep(800); continue; }
    await cdp.cmd("Input.dispatchMouseEvent", { type: "mousePressed", x: p.x, y: p.y, button: "left", clickCount: 1 });
    await cdp.cmd("Input.dispatchMouseEvent", { type: "mouseReleased", x: p.x, y: p.y, button: "left", clickCount: 1 });
    await sleep(900);
  }
  return false;
}

/**
 * يُركِّز المحرّرَ بنقرةٍ واحدةٍ على سطرٍ مُصيَّر — **والتحقّقُ بعدها لا قبلها**.
 * فتحُ الملفّ لا يعني تركيزَه: قد يبقى التركيزُ في المستكشف أو في لوح الترحيب، وحينها
 * تذهب `Ctrl+G` إلى غيرِ المحرّر ويقيس المِجَسُّ لوحًا لم يُفتَح. والنقرةُ هنا **للتركيز
 * وحدَه** — كلُّ القياس بعدها بالمفاتيح، فلا تدخل إحداثيّةٌ بصريّةٌ في أيّ حكم.
 */
async function focusEditor(cdp) {
  for (let i = 0; i < 5; i++) {
    if (await cdp.evaluate(`!!document.querySelector('.editor-group-container.active .monaco-editor.focused')`) === true) return true;
    const p = await cdp.evaluate(`(() => {
      const l = document.querySelector('.editor-group-container.active .view-line');
      if (!l) return null;
      const b = l.getBoundingClientRect();
      if (b.width < 4 || b.height < 4) return null;
      return { x: Math.round(b.left + b.width / 2), y: Math.round(b.top + b.height / 2) };
    })()`);
    if (!p) { await sleep(800); continue; }
    await cdp.cmd("Input.dispatchMouseEvent", { type: "mousePressed", x: p.x, y: p.y, button: "left", clickCount: 1 });
    await cdp.cmd("Input.dispatchMouseEvent", { type: "mouseReleased", x: p.x, y: p.y, button: "left", clickCount: 1 });
    await sleep(800);
  }
  return await cdp.evaluate(`!!document.querySelector('.editor-group-container.active .monaco-editor.focused')`) === true;
}

const VK = { ESC: 27, RIGHT: 39, DOWN: 40, HOME: 36, KEY_F: 70 };

/**
 * ضغطةُ مفتاحٍ **غير مطبوع** (‏Enter · Escape · الأسهم) — بحقل `key` صراحةً.
 *
 * ‏`key()` في الحزام يمرّر `code` و`windowsVirtualKeyCode` وحدَهما، وهو كافٍ للحروف
 * لأنّ كروميوم يشتقّ `key` من الرمز فيها. **ولا يشتقّها للمفاتيح غير المطبوعة**:
 * يصل الحدثُ بـ`key` فارغةٍ فلا يطابق ارتباطًا ولا يعالجه المحرّر. ودُفع ثمنُ هذا
 * مرّتين في بناء هذا الملفّ: تحديدٌ لم يقع بـ`Ctrl+Shift+→`، ثمّ لوحُ انتقالٍ بقي
 * مفتوحًا وفيه «‏1:1» لأنّ `Enter` لم تُقبَل — وكلاهما **يُقرأ عطبًا في المنتج**
 * (‏«المِسطرة لم تتبدّل») وهو عطبٌ في أداة القياس. مثالٌ رابعٌ لفخّ النجاح الكاذب:
 * لو كان التأكيدُ موجبَ الصياغة لَمرّ.
 */
async function press(cdp, keyName, code, vk, mods = 0) {
  for (const type of ["rawKeyDown", "keyUp"]) {
    await cdp.cmd("Input.dispatchKeyEvent", {
      type, key: keyName, code, windowsVirtualKeyCode: vk, nativeVirtualKeyCode: vk, modifiers: mods,
    });
  }
}

/**
 * يقيس حالةً واحدة ويعيد النصَّ المُحدَّد كما يراه **النموذج**.
 * (١) `Ctrl+G` ثمّ «سطر:عمود» ⇒ موضعٌ دقيقٌ بلا بكسل ولا نقرة.
 * (٢) `Ctrl+Shift+→` ⇒ يمدّ التحديدَ إلى نهاية الكلمة التالية.
 * (٣) `Ctrl+F` ⇒ يُبذَر حقلُ البحث من التحديد، فتُقرأ قيمتُه نصًّا.
 * (٤) `Esc` ⇒ يُغلَق اللوحُ كي لا تبذر الحالةُ التاليةُ فوق بقيّةٍ من سابقتها.
 */
async function measureCase(cdp, c) {
  // ‏**التركيزُ يُستردّ منّا، فيُعاد التحقّقُ منه قبل الضغطة المقيسة لا مرّةً في أوّل
  // الحالة.** جولةُ الترحيب تستردّ التركيزَ بعد مئات المللي من تنشيط تبويبنا، فمحاولةٌ
  // واحدةٌ تقيس لوحًا آخر وتُبلِّغ «لم يقع تحديد». والحلقةُ **تسأل قبل كلّ محاولة** —
  // النمطُ نفسُه الموثَّقُ في `openScm`: الوترُ داخل الحلقة لا قبلها.
  let sel = null, pre = null;
  for (let attempt = 0; attempt < 4; attempt++) {
    // إغلاقُ لوح البحث **بالتحقّق لا بضغطةٍ واحدة**: ما دام مفتوحًا فهو يمسك التركيزَ،
    // فتذهب أسهمُ التنقّل إلى حقله ويُقاس سطرٌ غيرُ المقصود.
    for (let e = 0; e < 5; e++) {
      const open = await cdp.evaluate(
        `(() => { const w = document.querySelector('.editor-group-container.active .find-widget');
          return !!(w && w.getBoundingClientRect().height > 4); })()`);
      if (open !== true) break;
      await press(cdp, "Escape", "Escape", VK.ESC);
      await sleep(350);
    }
    // وتنشيطُ التبويب **داخل الحلقة أيضًا**: جولةُ الترحيب تستردّ الواجهةَ بعد حين،
    // فتنشيطٌ مرّةً في الأوّل لا يصمد لستّ حالاتٍ متتالية.
    await activateOurTab(cdp);
    if (!await focusEditor(cdp)) { await sleep(600); continue; }

    // كلُّ الحالات تبدأ من العمود الأوّل، فالتنقّلُ بالأسهم وحدَها — لا لوحَ انتقالٍ ولا
    // حقلَ نصّ. (وهذا **قيدٌ على المصفوفة يُقال**: حالةٌ بعمودٍ غيرِ الأوّل تحتاج طريقًا
    // آخر ولا تُضاف هنا بصمت.) وأوّلُ صيغةٍ استعملت `Ctrl+G` فبقي اللوحُ مفتوحًا وفيه
    // «‏1:1» ولم تُقبَل `Enter` — فقُرِئ ذلك عطبًا في المنتج وهو عطبٌ في أداة القياس.
    await press(cdp, "Home", "Home", VK.HOME, MOD.CTRL); await sleep(250);
    for (let i = 1; i < c.line; i++) { await press(cdp, "ArrowDown", "ArrowDown", VK.DOWN); await sleep(110); }
    await press(cdp, "Home", "Home", VK.HOME); await sleep(250);

    pre = await cdp.evaluate(`(() => {
      const a = document.activeElement;
      return { focused: !!document.querySelector('.editor-group-container.active .monaco-editor.focused'),
               active: a ? (a.tagName + '.' + String(a.className || '').slice(0, 50)) : null };
    })()`);
    if (!pre || pre.focused !== true) { await sleep(700); continue; }

    await press(cdp, "ArrowRight", "ArrowRight", VK.RIGHT, MOD.CTRL | MOD.SHIFT);
    await sleep(700);

    // «وقع تحديدٌ» شرطٌ يسبق قراءةَ الحقل: لو لم يُحدَّد شيء لبقي حقلُ البحث على آخر بذرةٍ
    // من الحالة السابقة، فتُقرأ نتيجةُ حالةٍ أخرى ويُبلَّغ حكمٌ لا يخصّ هذه.
    sel = await cdp.evaluate(`(() => {
      const e = document.querySelector('.editor-group-container.active');
      if (!e) return { has: false };
      const n = e.querySelectorAll('.selected-text').length;
      return { has: n > 0, n };
    })()`);
    if (sel && sel.has === true) break;
  }
  if (!sel || sel.has !== true) {
    return { why: `لم يقع تحديدٌ بعد Ctrl+Shift+→ ${JSON.stringify(sel)} · التركيزُ قبلَها ${JSON.stringify(pre)}` };
  }

  // ‏`Ctrl+F` يُبذَر حقلُه من التحديد — وهو قارئُنا.
  //
  // ⚠️ **والبذرُ لا يقع إن كان اللوحُ مفتوحًا سلفًا.** أوّلُ صيغةٍ سألت «هل اللوحُ ظاهر؟»
  // فإن كان ظاهرًا لم تضغط شيئًا — فبقي الحقلُ على بذرة الحالة السابقة، وردّت الحالاتُ
  // الخمسُ التاليةُ «السلام» كلُّها. وهو أخبثُ من الفشل: **الشاهدُ الموجبُ نجح**، ثمّ
  // قرأت خمسُ حالاتٍ نتيجةَ حالةٍ أولى. وأسوأُ منه أنّ اللوحَ المفتوحَ يخطف التركيزَ،
  // فضغطاتُ التنقّل كانت تذهب إلى حقل البحث لا إلى المحرّر. فالترتيبُ الآن مُلزِم:
  // **يُغلَق اللوحُ قبل التنقّل، ويُفتَح بعد التحديد** — لا يُسأل عن حضوره بل يُصنَع.
  let widget = false;
  for (let i = 0; i < 4; i++) {
    await press(cdp, "f", "KeyF", VK.KEY_F, MOD.CTRL);
    await sleep(800);
    widget = await cdp.evaluate(
      `(() => { const w = document.querySelector('.editor-group-container.active .find-widget');
        return !!(w && w.getBoundingClientRect().height > 4); })()`) === true;
    if (widget) break;
  }
  if (!widget) return { why: "لم يُفتَح لوحُ البحث بـCtrl+F — لا قارئَ للتحديد" };

  const got = await cdp.evaluate(`(() => {
    const w = document.querySelector('.editor-group-container.active .find-widget');
    if (!w) return { why: 'لا لوحَ بحثٍ في الصفحة' };
    const i = w.querySelector('.find-part input, .monaco-findInput input, textarea');
    if (!i) return { why: 'لوحُ البحثِ حاضرٌ بلا حقلِ إدخال' };
    return { value: i.value };
  })()`);
  await press(cdp, "Escape", "Escape", VK.ESC); await sleep(250);
  return got;
}

// ───────────────────────────── التشغيل ─────────────────────────────
(async () => {
  log(`مساحةٌ زائلة: ${tmp}`);
  log(`القيمةُ في المصدر: ${SOURCE_SEPS === null ? "تعذّرت قراءتُها" : JSON.stringify(SOURCE_SEPS)}`);
  launch();
  const cdp = await attach();
  try {
    // ‏`Page.bringToFront` **شرطٌ لا تحسين**: النافذةُ الخلفيّة قد تُصيَّر بلا تخطيط،
    // وضغطاتُ المفاتيح لا تبلغ نظامَ الاختصارات فيبدو أنّ الوترَ غيرُ مسجَّل. مكتوبٌ في
    // رأس الحزام، ودُفع ثمنُه هنا مرّةً: `Ctrl+G` لم تفتح شيئًا حتّى أُضيف هذا السطر.
    try { await cdp.cmd("Page.enable"); } catch { /* */ }
    await bringToFront(cdp);
    if (!await waitEditor(cdp)) {
      gap("حدُّ الكلمة", "لم يُصيَّر سطرُ الحالة الأولى — المحرّرُ لم يفتح الملفّ");
      return;
    }
    await closeOtherTabs(cdp);
    if (!await activateOurTab(cdp)) {
      gap("حدُّ الكلمة", "تعذّر تنشيطُ تبويب «حدود.txt» — جولةُ الترحيب تسبقه، وضغطاتُ المفاتيح تذهب إليها");
      return;
    }
    log("المحرّرُ مفتوحٌ وتبويبُ الحالات نشط");

    // ── الشاهدُ الموجب أوّلًا. لا يُقرأ تأكيدٌ سالبٌ قبله. ──
    const witness = CASES[0];
    const w = await measureCase(cdp, witness);
    if (w.why) {
      gap("شاهدُ التفعيل", `${w.why} — ولا يُقرأ ما بعده`);
      return;
    }
    if (w.value !== witness.want) {
      // الفرقُ بين العطبَين يُقال: «لم تصل القيمةُ» شيءٌ و«القيمةُ خطأ» شيءٌ آخر، وأشيعُ
      // أسبابِ الأوّل في هذا المستودع أنّ الحزمةَ المشحونةَ أقدمُ من المصدر.
      gap("شاهدُ التفعيل",
        `التحديدُ «${w.value}» والمتوقَّع «${witness.want}» — أي أنّ المِسطرة **لم تتبدّل**. ` +
        `القيمةُ في المصدر موجودةٌ (${SOURCE_SEPS ? "نعم" : "لا"})، فالأرجحُ أنّ الحزمةَ ` +
        `المشحونةَ أقدمُ من المصدر: أعِد البناءَ ثمّ أعِد القياس. ولا يُقرأ ما بعده — ` +
        `التأكيداتُ السالبةُ كلُّها كانت ستنجح والميزةُ مطفأة.`);
      return;
    }
    ok(true, `شاهدُ التفعيل: «${witness.text}» ⇒ «${w.value}»`, witness.note);

    // ── وبعده تُقرأ البقيّة ──
    for (const c of CASES.slice(1)) {
      const r = await measureCase(cdp, c);
      if (r.why) { gap(`${c.role}: «${c.text}»`, r.why); continue; }
      ok(r.value === c.want,
        `${c.role}: «${c.text}» ⇒ «${r.value}»`,
        r.value === c.want ? (c.note || "") : `المتوقَّع «${c.want}»${c.note ? " — " + c.note : ""}`);
    }
  } finally {
    try { await cdp.close?.(); } catch { /* */ }
    kill();
    if (!KEEP) {
      // الحذفُ لا يُسقِط القياس: قد يمسك إلكترون ملفًّا لحظةَ الخروج (‏EBUSY)، ولا يجوز
      // أن يمحوَ فشلُ تنظيفٍ نتيجةً تمّت.
      try { rmSync(tmp, { recursive: true, force: true }); }
      catch (e) { console.log(`  ⚠️ تعذّر حذفُ ${tmp}: ${e.code || e.message}`); }
    } else log(`أُبقيت المساحة: ${tmp}`);
    process.exit(failed ? 1 : 0);
  }
})().catch(e => { console.error(`❌ خطأٌ تشغيليّ: ${e.stack || e.message}`); kill(); process.exit(2); });
