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
//   (٣) **وللسببِ الصحيح**: خرجُ الحارس يحوي `expect`. هذا ما يقتل الطقس — لا يُرضيك
//       خطأُ صياغةٍ ولا انهيارٌ ولا رسالةٌ عن شيءٍ آخر.
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
import { existsSync, readFileSync, writeFileSync } from "node:fs";
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
const sha = s => createHash("sha256").update(s).digest("hex").slice(0, 16);

console.log("╔══ [PF-03] حارسُ الحرّاس: عطبٌ مزروعٌ لكلّ حارس ══╗");

// ── قاعدةُ التغطية ───────────────────────────────────────────────────────────────
// تُستخرَج أوامرُ الحرّاس من `tests/run.sh` نفسِه لا من قائمةٍ ثانيةٍ تنجرف.
const runSh = readFileSync(join(ROOT, "tests", "run.sh"), "utf8");
const guardsInRun = new Set();
// المسارُ في `run.sh` مكتوبٌ بمتغيّرَي صدفة، فيُحلَّان هنا. و**تُستثنى الطبقةُ الحيّة**
// (`*.live.mjs` و`launch.mjs` و`run.mjs`): تشترط نسخةً مشحونةً وإطلاقَ تطبيق، فزرعُ عطبٍ
// لها يعني بناءً كاملًا لكلّ مُصاب — والمُصابُ الذي لا يُشغَّل ليس تغطية.
const RESOLVE = { "$HERE": "tests", "$NEBRAS": "extensions/mihrab-nebras" };
for (const m of runSh.matchAll(/"(\$HERE|\$NEBRAS)\/([\w./-]+\.(?:py|mjs|cjs|js))"/g)) {
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
      .replace("$NEBRAS", "extensions/mihrab-nebras")
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
const runGuard = (cmd) => {
  const r = spawnSync(cmd, { cwd: ROOT, shell: true, encoding: "utf8", timeout: 600_000 });
  return { code: r.status ?? 1, out: (r.stdout || "") + (r.stderr || "") };
};

for (const m of spec.mutants) {
  if (ONLY && m.id !== ONLY) continue;
  const file = join(ROOT, m.file);
  if (!existsSync(file)) { console.log(`  ❌ ${m.id}: لا ملفَّ ${m.file}`); rc = 1; continue; }

  const original = readFileSync(file, "utf8");
  const before = sha(original);

  // **الوسمُ يجب أن يكون فريدًا**: وسمٌ متكرّرٌ يُصيب موضعًا لم يُقصَد، فيحمرّ الحارسُ
  // لسببٍ آخرَ ويُقرَأ ذلك نجاحًا للمُصاب — أخضرُ كاذبٌ داخل حارس الحرّاس نفسِه.
  const n = original.split(m.old).length - 1;
  if (n !== 1) { console.log(`  ❌ ${m.id}: الوسمُ ورد ${n} مرّةً لا مرّةً واحدة — مُصابٌ لا يُوثَق به`); rc = 1; continue; }

  const base = runGuard(m.guard);
  if (base.code !== 0) {
    // (١) حارسٌ أحمرُ أصلًا «ينجح» في كلّ مُصاب: القياسُ لا يقع.
    console.log(`  ❌ ${m.id}: الحارسُ أحمرُ على الشجرة السليمة (خرج ${base.code}) — لا يُقرأ مُصابٌ بعده`);
    // **ولماذا احمرّ**: بلا هذا السطر تكون الرسالةُ بلاغًا لا تشخيصًا — والقارئُ يُشغّل
    // الحارسَ يدويًّا فيجده أخضرَ (وقعنا فيه) فيظنّه شبحًا، وهو غالبًا حالةٌ عابرةٌ خلّفها
    // مُصابٌ سابق. سببُ الاحمرار يُقال هنا حيث وقع.
    console.log("       " + base.out.split("\n").filter(l => l.includes("❌")).slice(0, 3).join("\n       "));
    rc = 1; continue;
  }

  let res;
  try {
    // ⚠️ **البديلُ دالّةٌ لا سلسلة.** `String.replace` يفسّر `$&` و`` $` `` و`$'`
    //    و`$1` في سلسلة البديل. ومُصابٌ ينتهي بـ`$'` — وهو شائعٌ في تعابيرَ نمطيّةٍ
    //    مثل `\r?$'` — كان يُحقَن معه **كلُّ ما بعد الموضع من الملفّ** مكرَّرًا.
    //    فلا يحمرّ الحارسُ المقصود بل غيرُه، ويُقرَأ ذلك «حمِر لسببٍ آخر»: تشخيصٌ
    //    يوجّه الاتّهامَ إلى المُصاب وإلى الحارس، والعطبُ في أداة الزرع.
    //    والدالّةُ تُعطِّل هذا التفسير كلَّه.
    writeFileSync(file, original.replace(m.old, () => m.new), "utf8");
    res = runGuard(m.guard);
  } finally {
    writeFileSync(file, original, "utf8");
    const after = sha(readFileSync(file, "utf8"));
    if (after !== before) { console.log(`  ❌ ${m.id}: **لم تُستعَد الشجرة** (${before} ⇐ ${after}) — أصلِح يدويًّا`); rc = 1; }
  }

  if (res.code === 0) {
    console.log(`  ❌ ${m.id}: العطبُ مزروعٌ والحارسُ **أخضر** — لا يحرس ما يدّعي (${m.file})`);
    rc = 1;
  } else if (!res.out.includes(m.expect)) {
    console.log(`  ❌ ${m.id}: حمِر لكن **لسببٍ آخر** — لم يُذكَر «${m.expect}»`);
    console.log("       " + res.out.split("\n").filter(l => l.trim()).slice(-3).join("\n       "));
    rc = 1;
  } else {
    console.log(`  ✅ ${m.id.padEnd(26)} ${m.guardFile} يحمرّ على «${m.expect}»`);
  }
}

console.log(rc === 0 ? "\n╚══ ✅ كلُّ حارسٍ مُغطًّى شوهد وهو يحمرّ ══╝" : "\n╚══ ❌ حارسٌ لا يفشل، أو تغطيةٌ ناقصة ══╝");
process.exit(rc);
