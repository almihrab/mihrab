#!/usr/bin/env node
// ثراءُ العيّنة — المُجمِّعُ والحَكَم [PF-02].
//
// يشغّل اختباراتِ الوحدة تحت أداة القياس (`regex-richness.cjs`)، يجمع شظايا العمليّات،
// ويُفشِل على كلّ نمطٍ **طُبِّق ولم يُطابِق قطّ** — أي فئةَ مُدخَلاتٍ يعالجها الكودُ صراحةً
// ولا تحويها العيّنات. التعليلُ الكاملُ في رأس `regex-richness.cjs`.
//
// الاستعمال:  node tests/meta/richness.mjs [--list] [--json]
// خرج 0 = كلُّ نمطٍ مُطبَّقٍ رأى فئتَه · 1 = نمطٌ باردٌ غيرُ مُعلَن · 2 = خطأٌ تشغيليّ.

import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const WAIVERS = join(HERE, "richness-waivers.json");
const SHARDS = join(ROOT, "tests", "perf", ".runs", "richness");

const argv = process.argv.slice(2);
const has = f => argv.includes(f);

/** المجموعاتُ التي تُقاس. كلُّ مجموعةٍ مجلَّدُ امتدادٍ فيه `*.test.js`. */
const SUITES = [
  "extensions/mihrab-welcome",
];

console.log("╔══ [PF-02] ثراءُ العيّنة ══╗");

// ── جمعُ القياس ──────────────────────────────────────────────────────────────────
rmSync(SHARDS, { recursive: true, force: true });
mkdirSync(SHARDS, { recursive: true });

let ranAny = false;
for (const suite of SUITES) {
  const dir = join(ROOT, suite);
  if (!existsSync(dir)) { console.log(`  ⏭️  ${suite} — غيرُ موجود`); continue; }
  const files = readdirSync(dir).filter(f => /\.test\.(js|mjs|cjs)$/.test(f)).map(f => join(dir, f));
  if (!files.length) { console.log(`  ⏭️  ${suite} — بلا اختبارات`); continue; }
  const r = spawnSync(process.execPath,
    ["--require", join(HERE, "regex-richness.cjs"), "--test", ...files],
    { cwd: ROOT, encoding: "utf8", env: { ...process.env, MIHRAB_RICHNESS_DIR: SHARDS } });
  const pass = /# fail 0/.test(r.stdout || "");
  console.log(`  ${pass ? "•" : "⚠"} ${suite}: ${files.length} ملفًّا${pass ? "" : "  (‏فشلت اختبارات — القياسُ يبقى صالحًا لكنّ التغطيةَ ناقصة)"}`);
  ranAny = true;
}
if (!ranAny) { console.error("❌ لم تُشغَّل مجموعةٌ واحدة — لا قياس."); process.exit(2); }

// ── الدمج ────────────────────────────────────────────────────────────────────────
/** @type {Map<string, {source:string, flags:string, applied:number, matched:number, at:string}>} */
const merged = new Map();
const shardFiles = existsSync(SHARDS) ? readdirSync(SHARDS).filter(f => f.endsWith(".json")) : [];
for (const f of shardFiles) {
  for (const e of JSON.parse(readFileSync(join(SHARDS, f), "utf8"))) {
    const key = e.source + " " + e.flags;
    const prev = merged.get(key);
    // الموضعُ يُحفَظ من أوّل شظيّةٍ تراه: العمليّاتُ متوازيةٌ فترتيبُها غيرُ حتميّ،
    // لكنّ الموضعَ نفسَه واحدٌ — والاختلافُ يعني نمطين متطابقَي النصّ في ملفّين.
    if (!prev) merged.set(key, { ...e });
    else { prev.applied += e.applied; prev.matched += e.matched; }
  }
}

const waivers = existsSync(WAIVERS) ? JSON.parse(readFileSync(WAIVERS, "utf8")) : { min_patterns: 0, cold: [] };
const declared = new Map((waivers.cold || []).map(w => [w.pattern + " " + (w.flags ?? ""), w]));

// **شاهدُ حضورٍ موجب**: سقوطُ التحميل المسبق بصمتٍ يُنتج صفرَ شظايا — وصفرُ أنماطٍ باردةٍ
// حينئذٍ «نجاحٌ» لا يعني شيئًا. فيُشترَط عددٌ أدنى مرصودٌ ومثبَّتٌ، كـ`known_absent` في
// حارس الحجم: يُقصَر ولا يطول إلّا بالتزامٍ مرئيّ.
console.log(`\n  شظايا: ${shardFiles.length} عمليّة · أنماطٌ مرصودة: ${merged.size} (الحدُّ الأدنى ${waivers.min_patterns ?? 0})`);
if (merged.size < (waivers.min_patterns ?? 0)) {
  console.error(`❌ رُصد ${merged.size} نمطًا والمنتظَرُ ${waivers.min_patterns} — أداةُ القياس لم تُحمَّل، أو سقطت مجموعة.`);
  console.error("   (‏صفرُ باردٍ بعد قياسٍ ساقطٍ ليس نجاحًا — وهذا الشرطُ هو ما يمنع قراءتَه نجاحًا.)");
  process.exit(1);
}

// **أنماطُ ملفّات الاختبار لا تُحاسَب.** القاعدةُ «مُطبَّقٌ ولم يُطابِق ⇒ عيّنةٌ فقيرة»
// تصحّ على شيفرة المنتج: النمطُ هناك إقرارٌ بمعالجة فئة. أمّا في ملفّ اختبارٍ فأكثرُ
// الأنماط **تأكيداتٌ سالبةٌ يُقصَد ألّا تُطابِق** (`assert.ok(!/kind-risk/.test(h))`)،
// فمحاسبتُها تُحمِّر الشيفرةَ الصحيحةَ — وأحمرُ كاذبٌ يُعلَّم تجاهُلُه فيموت الحارس.
//
// و**الموضعُ المجهولُ لا يُحاسَب**: أنماطُ العقدة نفسِها (مُطابِقُ ملفّات `--test` مثلًا)
// لا إطارَ لها داخل شجرتنا، ولا عيّنةَ لنا نُثريها لأجلها.
const isProduct = at =>
  at !== "(مجهول)" && !/\.test\.(js|mjs|cjs):/.test(at) && !at.startsWith("tests/");
const all = [...merged.values()].sort((a, b) => a.at.localeCompare(b.at));
const judged = all.filter(e => isProduct(e.at));
const cold = judged.filter(e => e.applied > 0 && e.matched === 0);
const hot = judged.filter(e => e.matched > 0);

if (has("--json")) { console.log(JSON.stringify({ hot, cold }, null, 2)); process.exit(0); }
if (has("--list")) for (const e of all) console.log(`  ${e.matched ? "🔥" : "❄️"} /${e.source}/${e.flags}  @${e.at}  (${e.applied}/${e.matched})`);

let rc = 0;
const undeclaredCold = cold.filter(e => !declared.has(e.source + " " + e.flags));
if (undeclaredCold.length) {
  rc = 1;
  console.log(`\n  ❌ أنماطٌ **طُبِّقت ولم تُطابِق قطّ** (${undeclaredCold.length}) — العيّنةُ خاليةٌ من فئتها:`);
  for (const e of undeclaredCold)
    console.log(`     /${e.source}/${e.flags}\n        @${e.at} · طُبِّق ${e.applied} مرّةً · طابق 0`);
  console.log("\n     العلاجُ **إثراءُ العيّنة** لا إسكاتُ النمط: أضِف إلى مُدخَلات الاختبار محرفًا");
  console.log("     من الفئة. وإن كان النمطُ دفاعًا لا يُتوقَّع تشغيلُه، أعلِنه في");
  console.log("     tests/meta/richness-waivers.json بسببٍ مكتوب.");
}

// وسطرٌ مُعلَنٌ صار ساخنًا يُفشِل: القائمةُ تُقصَر ولا تطول — عقدُ `known_absent` نفسُه.
const staleWaivers = [...declared.values()].filter(w =>
  hot.some(e => e.source === w.pattern && (w.flags === undefined || e.flags === w.flags)));
if (staleWaivers.length) {
  rc = 1;
  console.log(`\n  ❌ إعلاناتٌ صارت باطلة (${staleWaivers.length}) — النمطُ يُطابِق الآن، فيُحذَف سطرُه:`);
  for (const w of staleWaivers) console.log(`     /${w.pattern}/  — «${w.why}»`);
}

console.log(`\n  ساخن: ${hot.length} · بارد: ${cold.length} (منها ${cold.length - undeclaredCold.length} مُعلَنة)`);
if (!has("--keep")) rmSync(SHARDS, { recursive: true, force: true });
console.log(rc === 0 ? "\n╚══ ✅ كلُّ نمطٍ مُطبَّقٍ رأى فئتَه ══╝" : "\n╚══ ❌ عيّنةٌ فقيرة ══╝");
process.exit(rc);
