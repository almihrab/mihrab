#!/usr/bin/env node
// حارسُ الحرّاس — عطبٌ مزروعٌ لكلّ حارس [PF-03].
//
// ## لماذا
// من خمسةَ عشرَ عطبًا كشفتها المراجعةُ العدائيّة، **سبعةٌ كانت في الحرّاس أنفسهم**، وواحدٌ
// في حارسِ حارس. والقاعدةُ المستخلَصة: **نجاحُ الحارس معلومةٌ عديمةُ القيمة ما لم يُعرَف
// أنّه كان قادرًا على الفشل.** فالأخضرُ لا يُقرأ حتّى يُشاهَد الأحمر.
//
// ## ولماذا لا يُعمَّم «فحصُ الفحص» شكلًا
// في `print-export.test.js` تأكيدٌ يبني الخرجَ بتعليمٍ معطَّلٍ ويشترط أن يحمرّ الأساسيّ.
// شكلٌ جميلٌ — وإلزامُه **يُنتج طقسًا**: يكتب المطوّرُ `assert.ok(true)` باسمٍ فيه «فحصُ
// الفحص» ويمضي. فلا يُفرَض الشكل، يُفرَض **الأثر**: عطبٌ يُزرَع في الملفّ الذي يحرسه
// الحارسُ فعلًا، ويجب أن يحمرّ **وللسبب الصحيح**.
//
// ## شرطُ النجاح ثلاثيّ — وكلُّ فرعٍ يمنع نوعًا من الخداع
//   (١) **الأساسُ أخضر**: يُشغَّل الحارسُ على الشجرة السليمة أوّلًا. حارسٌ أحمرُ دائمًا
//       كان «سينجح» في كلّ مُصاب.
//   (٢) **المُصابُ أحمر**: رمزُ خروجٍ غيرُ صفر.
//   (٣) **وللسببِ الصحيح**: **سطورُ فشلِ** الحارس تحوي `expect`. هذا ما يقتل الطقس —
//       لا يُرضيك خطأُ صياغةٍ ولا انهيارٌ ولا رسالةٌ عن شيءٍ آخر.
//       و«سطورُ الفشل» **تُختار** (‏`failureText`): الحارسُ يطبع اسمَ كلِّ فحصٍ ناجحٍ ومعه
//       وسمُه، فـ`expect` بصيغة وسمٍ كان يوجد في الخرج **وإن لم يحمرّ ذلك الفحص**.
//
// ## وقاعدةُ التغطية
// كلُّ حارسٍ في `tests/run.sh` إمّا له مُصابٌ، وإمّا **مُعلَنٌ في `uncovered` بسببٍ مكتوب**.
// وحارسٌ غيرُ مغطًّى وغيرُ مُعلَنٍ يُفشِل. العقدُ نفسُه المستعمَل في `known_absent` و
// `richness-waivers`: القائمةُ تُقصَر ولا تطول إلّا بالتزامٍ مرئيّ.
//
// ## أينَ يُشغَّل
// **لا في المسار السريع**: تشغيلُ كلّ حارسٍ مرّتين يحوّل `run.sh` من ثوانٍ إلى دقائق،
// وحارسٌ بطيءٌ يُعطَّل — والمعطَّلُ أسوأُ من الغائب.
//   node tests/meta/mutation.mjs            # كلّ المُصابات
//   node tests/meta/mutation.mjs --only <id>
// خرج 0 = كلُّ حارسٍ يستطيع أن يحمرّ · 1 = حارسٌ لا يفشل، أو تغطيةٌ ناقصة · 2 = خطأٌ تشغيليّ.

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const SPEC = join(HERE, "mutants.json");

const argv = process.argv.slice(2);
const val = (f, d) => { const i = argv.indexOf(f); return i >= 0 && argv[i + 1] ? argv[i + 1] : d; };
const ONLY = val("--only", null);

if (!existsSync(SPEC)) { console.error(`❌ لا ${SPEC}`); process.exit(2); }
const spec = JSON.parse(readFileSync(SPEC, "utf8"));

// ── القفلُ وسجلُّ الاستعادة ──────────────────────────────────────────────────────────
// تشغيلان متوازيان يُتلفان الشجرةَ بلا إنذار (قِيس 2026-11-24): (أ) يقرأ «الأصلَ» وهو
// مُصابُ (ب)، (ب) يستعيد الأصلَ الحقيقيّ، (أ) «يستعيد» مُصابَ (ب) — وفحصُ الاستعادة في
// (أ) ينجح لأنّه يقارن بقراءته الأولى. فالقفلُ حصريٌّ (`wx`) ويحمل رقمَ العمليّة.
const LOCK = join(HERE, ".mutation.lock");
const JOURNAL = join(HERE, ".mutation-journal.json");
const alive = pid => { try { process.kill(pid, 0); return true; } catch (e) { return e.code === "EPERM"; } };
const sha = b => createHash("sha256").update(b).digest("hex");
const held = pid => {
  console.error(`❌ حارسُ الحرّاس يعمل في عمليّةٍ أخرى (${pid}) — تشغيلان معًا يُتلفان الشجرة`
    + `\n   (إن لم يكن يعمل شيءٌ فعلًا فاحذف ${LOCK})`);
  process.exit(2);
};
// ‏`wx` يُنشئ الملفَّ ثمّ يكتب الرقم: بينهما قفلٌ **فارغ**. وكان الفارغُ يُقرأ «بائتًا»
// فيُكتب فوقه ويعمل التشغيلان معًا — السباقُ نفسُه الذي وُضع القفلُ لمنعه. فالفارغُ الحديثُ
// محجوز. والبائتُ **يُحذف ثمّ يُؤخَذ بـ`wx` من جديد** لا يُكتب فوقه: آخذان معًا يكتبان
// فوقه كلاهما وينجحان كلاهما، وبالحذف لا يفوز بـ`wx` إلّا واحد. (يبقى سباقٌ أضيق: آخذٌ
// يحذف قفلًا أنشأه الآخرُ للتوّ — يشترط موتَ تشغيلٍ ثمّ بدءَ اثنين في اللحظة نفسها.)
const takeLock = () => {
  for (let attempt = 0; attempt < 3; attempt++) {
    try { writeFileSync(LOCK, String(process.pid), { flag: "wx" }); return; }
    catch (e) { if (e.code !== "EEXIST") throw e; }
    let text, age;
    try { text = readFileSync(LOCK, "utf8").trim(); age = Date.now() - statSync(LOCK).mtimeMs; }
    catch { continue; }                                   // حُرِّر بين المحاولة والقراءة
    const pid = Number(text);
    if (!text && age < 10_000) held("؟ قفلٌ يُكتب الآن");
    if (pid > 0 && alive(pid)) held(pid);
    rmSync(LOCK, { force: true });                        // بائتٌ من عمليّةٍ ماتت، أو تالف
  }
  held("؟");
};
takeLock();
process.on("exit", () => {
  try { if (readFileSync(LOCK, "utf8").trim() === String(process.pid)) rmSync(LOCK); } catch {}
});
// سجلٌّ باقٍ = تشغيلٌ سابقٌ قُتل. والقفلُ في يدنا، فلا أحدَ يزرع الآن. **ولا يُكتب فوق
// الملفّ عميانًا**: بين القتل وهذا التشغيل قد يكون المالكُ حرّره (أو أعاده بـgit) — فيُستعاد
// فقط إن كان ما على القرص **هو المُصابَ نفسَه** بالبايت، وإلّا يُرفَض التشغيلُ ويُسمّى الملفّ.
if (existsSync(JOURNAL)) {
  let j = null;
  try { j = JSON.parse(readFileSync(JOURNAL, "utf8")); } catch {}
  if (!j || typeof j.file !== "string" || typeof j.data !== "string") {
    // السجلُّ يُكتب كاملًا **قبل** الزرع: سجلٌّ مبتورٌ = قُتل التشغيلُ قبل أن يزرع شيئًا.
    rmSync(JOURNAL);
    console.log("  ↺ سجلُّ استعادةٍ مبتور (قُتل التشغيلُ قبل الزرع) — حُذف");
  } else {
    const target = join(ROOT, j.file);
    const orig = Buffer.from(j.data, "base64");
    const cur = existsSync(target) ? readFileSync(target) : null;
    if (cur && cur.equals(orig)) {
      rmSync(JOURNAL);
    } else if (cur && j.planted && sha(cur) === j.planted) {
      writeFileSync(target, orig);
      rmSync(JOURNAL);
      console.log(`  ↺ استُعيد ${j.file} من مُصاب «${j.id}» الذي بقي مزروعًا من تشغيلٍ قُتل`);
    } else {
      console.error(`❌ سجلُّ استعادةٍ لمُصاب «${j.id}» في ${j.file}، والملفُّ ${cur ? "تغيّر بعده" : "محذوف"}`
        + ` — لا يُكتب فوقه عميانًا.\n   افحصه يدويًّا (الأصلُ base64 في ${JOURNAL}) ثمّ احذف السجلّ.`);
      process.exit(2);
    }
  }
}

console.log("╔══ [PF-03] حارسُ الحرّاس: عطبٌ مزروعٌ لكلّ حارس ══╗");

// ── قاعدةُ التغطية ───────────────────────────────────────────────────────────────
// تُستخرَج أوامرُ الحرّاس من `tests/run.sh` نفسِه لا من قائمةٍ ثانيةٍ تنجرف.
const runSh = readFileSync(join(ROOT, "tests", "run.sh"), "utf8");
const guardsInRun = new Set();
// المسارُ في `run.sh` مكتوبٌ بمتغيّرَي صدفة، فيُحلَّان هنا. و**تُستثنى الطبقةُ الحيّة**
// (`*.live.mjs` و`launch.mjs` و`run.mjs`): تشترط نسخةً مشحونةً وإطلاقَ تطبيق، فزرعُ عطبٍ
// لها يعني بناءً كاملًا لكلّ مُصاب — والمُصابُ الذي لا يُشغَّل ليس تغطية.
const RESOLVE = { "$HERE": "tests" };
for (const m of runSh.matchAll(/"(\$HERE)\/([\w./-]+\.(?:py|mjs|cjs|js))"/g)) {
  const rel = `${RESOLVE[m[1]]}/${m[2]}`;
  if (/\.live\.mjs$|\/(launch|run)\.mjs$/.test(rel)) continue;
  if (rel.includes("/..")) continue;
  guardsInRun.add(rel);
}
// **وحلقةُ اختبارات الامتدادات ليست في هذا الشكل** (`run.sh`: `cd "$_ext" && node --test`)،
// فكانت تسقط من العدّ كلَّها: أيُّ اختبارِ وحدةٍ يُكتَب في `extensions/*` يقع **خارج** حارس
// الحرّاس ولا يشتكي أحد. والحارسُ هنا **الأمرُ لا الملفّ**: `node --test` واحدٌ لكلّ امتداد،
// فالتغطيةُ أن يحمل الامتدادُ مُصابًا واحدًا على الأقلّ يُثبِت أنّ سويّتَه تُشغَّل وترى —
// لا مُصابًا لكلّ ملفِّ اختبارٍ من الأربعة والعشرين (ذاك عدٌّ لا قياس).
const extDirs = [];
for (const m of runSh.matchAll(/for _ext in (.+); do/g)) {
  for (const tok of m[1].matchAll(/"([^"]+)"/g)) {
    const rel = tok[1]
      .replace("$HERE/../", "")
      .replace("$HERE/", "tests/");
    if (rel.startsWith("extensions/")) extDirs.push(rel);
  }
}
for (const d of extDirs) guardsInRun.add(d);

// مُصابٌ على ملفٍّ داخل امتدادٍ يُغطّي أمرَ `node --test` الخاصَّ به.
const covered = new Set(spec.mutants.map(m => m.guardFile));
for (const d of extDirs) {
  if (spec.mutants.some(m => m.guardFile.startsWith(d + "/"))) covered.add(d);
}
const declaredUncovered = new Map((spec.uncovered || []).map(u => [u.guardFile, u.why]));
let rc = 0;

const missing = [...guardsInRun].filter(g => !covered.has(g) && !declaredUncovered.has(g)).sort();
if (missing.length) {
  rc = 1;
  console.log(`\n  ❌ حرّاسٌ بلا مُصابٍ وبلا إعلان (${missing.length}):`);
  for (const g of missing) console.log(`     ${g}`);
  console.log("     أضِف مُصابًا في tests/meta/mutants.json، أو أعلِنه في `uncovered` بسببٍ مكتوب.");
}
// وإعلانٌ صار باطلًا (الحارسُ غُطِّي، أو زال من run.sh) يُفشِل كذلك.
for (const [g] of declaredUncovered) {
  if (covered.has(g)) { rc = 1; console.log(`  ❌ ${g}: مُعلَنٌ «بلا مُصاب» وله مُصابٌ — احذف سطرَ الإعلان.`); }
  else if (!guardsInRun.has(g)) { rc = 1; console.log(`  ❌ ${g}: مُعلَنٌ وليس في run.sh — إعلانٌ عن حارسٍ زائل.`); }
}
console.log(`\n  تغطية: ${covered.size} مُغطًّى · ${declaredUncovered.size} مُعلَن · من ${guardsInRun.size} حارسًا في run.sh`);

// ── المُصابات ────────────────────────────────────────────────────────────────────
// **سطورُ الفشل تُختار ولا يُسقَط ما سواها.** إسقاطُ سطور النجاح (✅/✔/ok) كان يُبقي
// كلَّ ما لم يُتوقَّع: ‏`node --test` يطبع `# Subtest: <الاسم>` لكلّ اختبارٍ **ناجح**، ولافتةُ
// ‏`╚══ ✅ … (سقفًا وأرضيّة) ══╝` لا تبدأ بـ✅، وسطورُ ⏭️ و⚠️ — فيطابقها `expect` والفحصُ لم يحمرّ.
// فالمختارُ: سطرٌ يحمل علامةَ فشل، وما تحته من سطورٍ أعمقَ إزاحةً (تفصيلُه، وكتلةُ YAML
// تحت `not ok` في TAP، وجسمُ `Traceback`).
const PASS_LINE = /^\s*(✅|✔|ok\b|# Subtest:)/;
const FAIL_MARK = /❌|✗|✖|^\s*not ok\b|^\s*FAIL\b|Traceback \(most recent call last\)|\b\w*(Error|Exception)\b/;
const indent = l => l.match(/^\s*/)[0].length;
const failureText = (out) => {
  const lines = out.split("\n");
  const keep = [];
  for (let i = 0; i < lines.length; i++) {
    if (PASS_LINE.test(lines[i]) || !FAIL_MARK.test(lines[i])) continue;
    const base = indent(lines[i]);
    keep.push(lines[i]);
    while (i + 1 < lines.length && lines[i + 1].trim() && indent(lines[i + 1]) > base) keep.push(lines[++i]);
  }
  return keep.join("\n");
};
// ‏`r.status ?? 1` كان يقرأ انقضاءَ المهلة والقتلَ بإشارةٍ **أحمرَ** — فمُصابٌ علِق حارسُه
// يُحسَب «أمسكه الحارس». فالمهلةُ والإشارةُ خطأٌ تشغيليٌّ صريح.
const runGuard = (cmd) => {
  const r = spawnSync(cmd, { cwd: ROOT, shell: true, encoding: "utf8", timeout: 600_000 });
  const out = (r.stdout || "") + (r.stderr || "");
  if (r.error || r.signal) return { code: null, out, why: r.error ? r.error.code || r.error.message : `إشارة ${r.signal}` };
  return { code: r.status, out };
};

const selected = spec.mutants.filter(m => !ONLY || m.id === ONLY);
if (ONLY && !selected.length) {
  // مرشِّحٌ لا يطابق شيئًا كان يطبع اللافتةَ الخضراء ويخرج بـ0 — أخضرُ لم يقِس شيئًا.
  console.log(`\n  ❌ لا مُصابَ بالمعرِّف «${ONLY}»`);
  process.exit(2);
}

for (const m of selected) {
  const file = join(ROOT, m.file);
  if (!existsSync(file)) { console.log(`  ❌ ${m.id}: لا ملفَّ ${m.file}`); rc = 1; continue; }

  // **المقارنةُ بالبايت لا بالنصّ المفكوك**: ملفٌّ ليس UTF-8 صالحًا يُتلَف بالفكّ ثمّ الكتابة
  // (‏U+FFFD) وتتطابق بصمتا النصّين المفكوكين فيمرّ الإتلافُ صامتًا.
  const origBuf = readFileSync(file);
  const original = origBuf.toString("utf8");
  if (!Buffer.from(original, "utf8").equals(origBuf)) {
    console.log(`  ❌ ${m.id}: ${m.file} ليس UTF-8 صالحًا — لا يُزرَع فيه`); rc = 1; continue;
  }

  // **الوسمُ يجب أن يكون فريدًا**: وسمٌ متكرّرٌ يُصيب موضعًا لم يُقصَد، فيحمرّ الحارسُ
  // لسببٍ آخرَ ويُقرَأ ذلك نجاحًا للمُصاب — أخضرُ كاذبٌ داخل حارس الحرّاس نفسِه.
  const n = original.split(m.old).length - 1;
  if (n !== 1) { console.log(`  ❌ ${m.id}: الوسمُ ورد ${n} مرّةً لا مرّةً واحدة — مُصابٌ لا يُوثَق به`); rc = 1; continue; }

  const base = runGuard(m.guard);
  if (base.code !== 0) {
    // (١) حارسٌ أحمرُ أصلًا «ينجح» في كلّ مُصاب: القياسُ لا يقع.
    console.log(`  ❌ ${m.id}: الحارسُ أحمرُ على الشجرة السليمة (${base.code === null ? base.why : "خرج " + base.code}) — لا يُقرأ مُصابٌ بعده`);
    // **ولماذا احمرّ**: بلا هذا السطر تكون الرسالةُ بلاغًا لا تشخيصًا — والقارئُ يُشغّل
    // الحارسَ يدويًّا فيجده أخضرَ (وقعنا فيه) فيظنّه شبحًا، وهو غالبًا حالةٌ عابرةٌ خلّفها
    // مُصابٌ سابق. سببُ الاحمرار يُقال هنا حيث وقع.
    // وحارسٌ يحمرّ بلا علامةِ فشلٍ (‏`sys.exit("…")` مثلًا) لا يُترك سطرُه فارغًا: الذيلُ بديلًا.
    const bfl = failureText(base.out).split("\n").filter(l => l.trim());
    const btail = base.out.split("\n").filter(l => l.trim()).slice(-3);
    console.log("       " + (bfl.length ? bfl.slice(0, 3) : btail).join("\n       "));
    rc = 1; continue;
  }

  let res;
  // سجلُّ الاستعادة يُكتب **قبل** الزرع: قتلٌ قسريٌّ أو Ctrl-C (الحلقةُ متزامنةٌ فلا يعمل
  // معالجُ إشارة) يترك المُصابَ مزروعًا، والتشغيلُ التالي يستعيده من هنا قبل أيّ شيء.
  // و`planted` بصمةُ المُصاب: الاستعادةُ لا تقع إلّا إن كان ما على القرص هو المُصابَ نفسَه.
  // ⚠️ **البديلُ دالّةٌ لا سلسلة.** `String.replace` يفسّر `$&` و`` $` `` و`$'`
  //    و`$1` في سلسلة البديل. ومُصابٌ ينتهي بـ`$'` — وهو شائعٌ في تعابيرَ نمطيّةٍ
  //    مثل `\r?$'` — كان يُحقَن معه **كلُّ ما بعد الموضع من الملفّ** مكرَّرًا.
  //    فلا يحمرّ الحارسُ المقصود بل غيرُه، ويُقرَأ ذلك «حمِر لسببٍ آخر»: تشخيصٌ
  //    يوجّه الاتّهامَ إلى المُصاب وإلى الحارس، والعطبُ في أداة الزرع.
  //    والدالّةُ تُعطِّل هذا التفسير كلَّه.
  const mutated = original.replace(m.old, () => m.new);
  writeFileSync(JOURNAL, JSON.stringify({ id: m.id, file: m.file, data: origBuf.toString("base64"),
    planted: sha(Buffer.from(mutated, "utf8")) }));
  try {
    writeFileSync(file, mutated, "utf8");
    res = runGuard(m.guard);
  } finally {
    writeFileSync(file, origBuf);
    if (!readFileSync(file).equals(origBuf)) {
      console.log(`  ❌ ${m.id}: **لم تُستعَد الشجرة** (${m.file}) — النسخةُ السليمةُ في ${JOURNAL}`);
      process.exit(2);
    }
    rmSync(JOURNAL, { force: true });
  }

  if (res.code === null) {
    console.log(`  ❌ ${m.id}: الحارسُ لم ينتهِ (${res.why}) — لا يُقرأ أحمرَ`);
    rc = 1;
  } else if (res.code === 0) {
    console.log(`  ❌ ${m.id}: العطبُ مزروعٌ والحارسُ **أخضر** — لا يحرس ما يدّعي (${m.file})`);
    rc = 1;
  } else if (!(m.expect && failureText(res.out).includes(m.expect))) {
    console.log(`  ❌ ${m.id}: حمِر لكن **لسببٍ آخر** — لم يُذكَر «${m.expect}» في سطور الفشل`);
    const fl = failureText(res.out).split("\n").filter(l => l.trim());
    const tail = res.out.split("\n").filter(l => l.trim()).slice(-3);
    console.log("       " + (fl.length ? fl.slice(0, 3) : tail).join("\n       "));
    rc = 1;
  } else {
    console.log(`  ✅ ${m.id.padEnd(26)} ${m.guardFile} يحمرّ على «${m.expect}»`);
  }
}

// ── وتُعاد الشجرةُ المبنيّةُ لا المصدرُ وحدَه ──
// المصدرُ يُستعاد بعد كلّ مُصاب، لكنّ `check_site.py` يبني `site/public/` **من المُصاب**
// فيبقى المخرَجُ في حالة آخرِ عطبٍ مزروع (قِيس: صفحةُ التنزيل تقول ‎194‎ بعد مُصاب
// `site-size-binary-mb`). ومن نشر بعدها بلا بناءٍ — أو قاس بالعين — قاس العطب.
// فيُعاد البناءُ مرّةً في النهاية إن شُغِّل مُصابٌ حارسُه حارسُ الموقع.
const touchedSite = selected.some(m => m.guard.includes("check_site.py"));
if (touchedSite) {
  const py = process.platform === "win32" ? "python" : "python3";
  const b = spawnSync(py, ["site/build.py"], { cwd: ROOT, encoding: "utf8", timeout: 600_000,
    env: { ...process.env, PYTHONIOENCODING: "utf-8" } });
  if (b.status === 0) console.log("\n  ↻ أُعيد بناءُ site/public/ من المصدر السليم");
  else { console.log(`\n  ❌ تعذّرت إعادةُ بناء site/public/ (خرج ${b.status}) — المخرَجُ في حالة آخرِ مُصاب`); rc = rc || 1; }
}

console.log(rc === 0 ? "\n╚══ ✅ كلُّ حارسٍ مُغطًّى شوهد وهو يحمرّ ══╝" : "\n╚══ ❌ حارسٌ لا يفشل، أو تغطيةٌ ناقصة ══╝");
process.exit(rc);
