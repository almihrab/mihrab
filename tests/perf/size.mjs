// [PF-01] ميزانيّةُ حجمِ التوزيعة — **حارسٌ** يُفشِل، لا قياسٌ يُبلِّغ.
//
// لماذا وُجد: البناءُ يحقن امتداداتٍ مضمَّنة، وخطًّا،
// وحزمةَ تعريبٍ كاملة — ولا شيءَ في المستودع كلِّه يزن ما شُحن. فانتفاخُ مئةِ ميغابايتٍ
// وسقوطُ تنفيذيٍّ كامل **يمرّان بالصمت نفسِه**.
//
// ── ثلاثةُ فخاخِ نجاحٍ كاذبٍ صُمِّم هذا الملفُّ ضدَّها بالاسم ────────────────────────
//
// (١) **الصفرُ صغيرٌ فهو تحت السقف.** الخطُّ المحزوم سقوطُه رشيقٌ **بالتصميم**:
//     build.sh ينسخه داخل شرطٍ ويمضي. فبسقفٍ أحاديٍّ يكون
//     **البناءُ الذي لم يشحن شيئًا هو الأخضرَ الأنصع**. ولذلك لكلِّ مكوّنٍ **أرضيّةٌ كما له
//     سقف**، ولكلِّ اختياريٍّ **شاهدُ ملفٍّ** يجب أن يوجد ويتجاوز حدًّا أدنى. والبناءُ
//     الهزيلُ (بلا المكوّنات الاختياريّة) مسموحٌ به **إعلانًا صريحًا** — `MIHRAB_PERF_PROFILE=lean` —
//     لا سقوطًا صامتًا: أن تختار الهزالَ شيء، وأن يقع بك فلا تدري شيءٌ آخر.
//
// (٢) **التخطّي يُحسَب نجاحًا.** `tests/bundle/check_injected.py` يُرجع 0 حين لا بناء،
//     وCI لا يبني إطلاقًا. حارسُ حجمٍ يرث هذا الشكلَ يبقى أخضرَ إلى الأبد وهو لم يزِن
//     بايتًا. فهذا الملفُّ **يُعلِن وضعَه** في سطر الخرج الأوّل (‏`mode=measured|skipped`)
//     وفي JSON، ويشترط `--require-measured` لبوّابة الإصدار.
//
// (٣) **المجلّدُ الناقصُ يعطي رقمًا جميلًا.** بناءٌ نصفُ منسوخٍ مجموعُه أصغرُ ⇒ أخضر.
//     فقبل أن يُوثَق بأيّ رقم تُتحقَّق **مراسٍ** ستٌّ صريحة؛ غيابُ واحدةٍ = «بناءٌ ناقص»
//     برمزِ خروجٍ مميَّز (2) لا «تجاوزُ ميزانيّة» ولا نجاح.
//
// ── العتبةُ ليست مخترَعةً ولا محسوبةً في التشغيلة ──────────────────────────────────
// حارسٌ يحسب أساسَه في كلِّ تشغيلةٍ لا يمكن أن يفشل أبدًا. فالعتباتُ **مثبَّتةٌ في
// `budget.json` المتتبَّع في git**، ومقرونةٌ بوسم المنبع الذي أُسِّست عنده. ترقيةُ المنبع
// تُبطِل الأساسَ عمدًا: يُعاد تأسيسُه بـ`--establish` في **التزامٍ مرئيّ**، لا برفعِ سقفٍ صامت.
//
// ── قياسُ الحجم على Windows: ما يخدع ─────────────────────────────────────────────
// `find -type l` **لا يرى** junctions على Windows. ونحن نستعمل `lstat` من Node التي تُبلِّغ
// عن الوصلة والـjunction معًا بـ`isSymbolicLink()`؛ وأيُّ نقطةِ إعادةِ تحليلٍ تُرفَض ولا
// تُتبَع — وإلّا حُسبت شجرةٌ مرّتين أو حُسبت شجرةٌ ليست لنا. و`readdir` من Node يقرأ
// المخفيَّ افتراضًا (بخلاف `Get-ChildItem` بلا `-Force`).
// وقد قُوبل مجموعُ هذا الملفّ بمصدرين مستقلَّين وقتَ التأسيس: `du -sb` وPowerShell
// `Measure-Object Length -Sum`، فاتّفقت الثلاثةُ بالبايت.
//
// الاستعمال:
//   node tests/perf/size.mjs                  # قِس واحكم على budget.json
//   node tests/perf/size.mjs --json           # أخرِج القياسَ خامًا (لا حكم)
//   node tests/perf/size.mjs --establish      # أعِد تأسيسَ الميزانيّة (يكتب budget.json)
//   node tests/perf/size.mjs --require-measured   # اعتبر «لا بناء» فشلًا (بوّابةُ إصدار)
//   MIHRAB_PERF_PROFILE=lean node tests/perf/size.mjs   # بناءٌ بلا المكوّنات الاختياريّة (إعلانٌ صريح)
//
// الخروج: 0 نجاح/تخطٍّ معلَن · 1 تجاوزُ ميزانيّة أو مكوّنٌ دون أرضيّته · 2 بناءٌ ناقص/غائب.

import { existsSync, lstatSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const DIST = join(ROOT, ".upstream", "VSCode-win32-x64");
const APP = join(DIST, "resources", "app");
const BUDGET = join(HERE, "budget.json");

const argv = process.argv.slice(2);
const has = f => argv.includes(f);
const LEAN = (process.env.MIHRAB_PERF_PROFILE || "").toLowerCase() === "lean";

const MB = n => (n / 1048576).toFixed(2) + " م.ب";
let rc = 0;
const problems = [];
const bad = m => { problems.push(m); rc = Math.max(rc, 1); };

// ── مراسي البناء: غيابُ واحدةٍ يعني «ناقص» لا «صغير» ────────────────────────────
const ANCHORS = [
  "Mihrab.exe",
  "bin/mihrab.cmd",
  "resources/app/product.json",
  "resources/app/out/nls.messages.json",
  "resources/app/extensions/mihrab-welcome/package.json",
];

/**
 * مكوّناتٌ **متقاطعةُ الحدود صفرًا**: كلُّ بايتٍ في دلوٍ واحدٍ على الأكثر، فمجموعُ الدِّلاء
 * قابلٌ للمقارنة بالمجموع الكلّيّ — وهو بذاته فحصُ اتّساقٍ (`_uncategorised` يُطبع دائمًا).
 * `exclude` مساراتٌ نسبيّةٌ تُقتطع من الدلو وتُحسَب في دلوها هي.
 */
const COMPONENTS = {
  "ext_mihrab_welcome": { path: "resources/app/extensions/mihrab-welcome" },
  "ext_mihrab_shell":   { path: "resources/app/extensions/mihrab-shell" },
  "ext_mihrab_icons":   { path: "resources/app/extensions/mihrab-icons" },
  "ext_mihrab_themes":  { path: "resources/app/extensions/mihrab-themes" },
  // **حزمةُ التعريب**: كانت خارجَ كلِّ دلوٍ وكلِّ شاهد — و`build.sh` ينسخها كما ينسخ
  // البقيّة. فسقوطُها يعني شحنَ نسخةٍ بلا تعريب، أي **بلا سببِ وجودِ المنتج**؛ وحجمُها
  // ‎0.2%‎ من المجموع فيمرّ داخلَ هامش الأرضيّة الكلّيّة بلا أن يهتزّ رقم.
  "ext_language_pack_ar": { path: "resources/app/extensions/language-pack-ar" },
};

/**
 * شواهدُ ملفّاتٍ مفردة. هذه هي التي تُبطِل فخَّ «الصفرُ تحت السقف»: دلوٌ كاملٌ قد يبقى
 * فوق أرضيّته وقد سقط منه تنفيذيٌّ واحد، فيُسمّى كلُّ واحدٍ باسمه.
 * `min` بالبايت — حدٌّ أدنى فضفاضٌ عمدًا (يمسك «صفرٌ/كعبٌ/فشلُ نسخ»، لا يمسك انجرافَ إصدار).
 */
const WITNESSES = [
  // الخطُّ **إلزاميّ**: `build.sh` ينسخه داخل `if [[ -f … ]]` **بلا فرعِ else وبلا تحذير**
  // — وحدَه بين الأصول الاختياريّة — فغيابُه صامتٌ في البناء؛ وغيابُه يُعطِّل أمرَ التصدير
  // للطباعة [PR-01] كلّيًّا لأنّ `bundled-font.js` يرمي عليه بـ`required`.
  { path: "resources/app/extensions/mihrab-welcome/media/kawkab-mono.woff2", min: 10_000 },
  { path: "resources/app/out/nls.messages.json",                        min: 100_000 },
  // شاهدُ التعريب **داخل** الامتداد: `nls.messages.json` أعلاه مخبوزٌ من نواة المنبع،
  // فهو يبقى سليمًا وحزمةُ اللغة ساقطة. الملفُّ الأكبرُ فيها هو مقياسُ حياتها.
  { path: "resources/app/extensions/language-pack-ar/translations/main.i18n.json", min: 50_000 },
];

/**
 * ما لا يجوز أن يُشحَن أصلًا. `cp -r` في `build.sh:264` لا يحترم `.vscodeignore`، والتجريدُ
 * التالي له يحذف `*.py` و`__pycache__` **ولا يحذف الاختبارات** — فكانت اثنان وعشرون
 * `*.test.js` تُشحَن داخل التوزيعة. قِيس، فأُضيف التجريدُ وأُضيف هذا الحارسُ معه:
 * تجريدٌ بلا حارسٍ يعود بأوّل امتدادٍ جديد.
 */
const FORBIDDEN = [
  { label: "ملفّاتُ اختبارٍ (‏*.test.js‏)", test: p => /\.test\.(js|mjs|cjs)$/i.test(p) },
  { label: "سكربتاتُ توليدٍ (‏*.py‏)",       test: p => /\.py$/i.test(p) },
  { label: "‏__pycache__",                    test: p => p.split(/[\\/]/).includes("__pycache__") },
];
// نطاقُ المنع: امتداداتُنا وحدَها. امتداداتُ المنبع المضمَّنة ليست لنا ولا نُحاسَب عليها.
const FORBIDDEN_SCOPE = ["mihrab-welcome", "mihrab-shell", "mihrab-themes", "mihrab-icons"]
  .map(n => join("resources", "app", "extensions", n));

// ── العبور ────────────────────────────────────────────────────────────────────────
/** يعبر شجرةً مرّةً واحدة. يرفض نقاطَ إعادة التحليل ولا يتبعها (junction = وصلة عند lstat). */
function walk(absRoot) {
  const out = { bytes: 0, files: 0, reparse: [], list: [] };
  if (!existsSync(absRoot)) return out;
  const st = lstatSync(absRoot);
  if (st.isSymbolicLink()) { out.reparse.push(absRoot); return out; }
  if (st.isFile()) { out.bytes = st.size; out.files = 1; out.list.push([absRoot, st.size]); return out; }
  const stack = [absRoot];
  while (stack.length) {
    const dir = stack.pop();
    let entries;
    try { entries = readdirSync(dir, { withFileTypes: true }); } catch { continue; }
    for (const e of entries) {
      const p = join(dir, e.name);
      if (e.isSymbolicLink()) { out.reparse.push(p); continue; }
      if (e.isDirectory()) { stack.push(p); continue; }
      if (!e.isFile()) continue;
      let size; try { size = lstatSync(p).size; } catch { continue; }
      out.bytes += size; out.files++; out.list.push([p, size]);
    }
  }
  return out;
}

// ── القياس ────────────────────────────────────────────────────────────────────────
console.log("╔══ [PF-01] ميزانيّةُ حجمِ التوزيعة ══╗");

if (!existsSync(DIST)) {
  // تخطٍّ **معلَن**، لا نجاحٌ صامت.
  console.log("mode=skipped — لا مخرَجَ بناءٍ في .upstream/VSCode-win32-x64");
  console.log("   (‏شغّل build/build.sh. هذا ليس نجاحًا: لم يُوزَن بايتٌ واحد.)");
  if (has("--require-measured")) { console.error("❌ --require-measured: البوّابةُ تشترط قياسًا فعليًّا"); process.exit(2); }
  process.exit(0);
}
console.log("mode=measured");

for (const a of ANCHORS) {
  if (!existsSync(join(DIST, a))) {
    console.error(`❌ بناءٌ ناقص: المرساة غائبة — ${a}`);
    console.error("   (‏رقمُ حجمٍ من بناءٍ نصفِ منسوخٍ «جميلٌ» وكاذب. لا حكمَ على الحجم.)");
    process.exit(2);
  }
}

const all = walk(DIST);
if (all.reparse.length) {
  console.error(`❌ نقاطُ إعادةِ تحليلٍ في المخرَج (${all.reparse.length}) — القياسُ غيرُ موثوق:`);
  for (const p of all.reparse.slice(0, 5)) console.error("   " + relative(DIST, p));
  process.exit(2);
}

// إسنادُ كلِّ ملفٍّ إلى دلوٍ واحدٍ على الأكثر (الأطولُ مسارًا يفوز ⇒ `bin` يسبق حاويَه).
const buckets = Object.fromEntries(Object.keys(COMPONENTS).map(k => [k, { bytes: 0, files: 0 }]));
const owners = Object.entries(COMPONENTS)
  .map(([k, c]) => [k, join(DIST, c.path.split("/").join(sep))])
  .sort((a, b) => b[1].length - a[1].length);
let maps = { bytes: 0, files: 0 }, uncategorised = 0;
const forbiddenHits = [];

/**
 * ما **نملكه** من الامتدادات — يُكتشَف من مخرَج البناء لا من قائمةٍ مكتوبة.
 *
 * حزمةُ التعريب أُضيف لها دلوٌ بعد أن قِيس أنّ سقوطَها يمرّ (‏0.4%‎ من المجموع، داخلَ هامش
 * الأرضيّة الكلّيّة). لكنّ ذلك سدَّ **حالةً** لا قاعدة: امتدادٌ جديدٌ لنا يُشحَن بلا دلوٍ
 * يمرّ صامتًا كما مرّت هي. فالقاعدةُ هنا: كلُّ ما تحت `extensions/` باسمٍ نملكه **يجب أن
 * يقع في دلو**. والاسمُ يُكتشَف من الشجرة المشحونة، فلا قائمةَ تنجرف.
 */
const OWNED_EXT = /^(mihrab-|language-pack-ar$)/;
const EXT_PREFIX = join("resources", "app", "extensions") + sep;
/** @type {Map<string, {bytes:number, files:number}>} */
const orphanOwned = new Map();

for (const [p, size] of all.list) {
  const rel = relative(DIST, p);
  if (/\.map$/i.test(p)) { maps.bytes += size; maps.files++; }
  const hit = owners.find(([, base]) => p === base || p.startsWith(base + sep));
  if (hit) { buckets[hit[0]].bytes += size; buckets[hit[0]].files++; }
  else {
    uncategorised += size;
    if (rel.startsWith(EXT_PREFIX)) {
      const name = rel.slice(EXT_PREFIX.length).split(sep)[0];
      if (OWNED_EXT.test(name)) {
        const e = orphanOwned.get(name) || { bytes: 0, files: 0 };
        e.bytes += size; e.files++; orphanOwned.set(name, e);
      }
    }
  }
  if (FORBIDDEN_SCOPE.some(s => rel.startsWith(s + sep))) {
    const f = FORBIDDEN.find(f => f.test(rel));
    if (f) forbiddenHits.push([f.label, rel]);
  }
}

const measured = {
  _mode: "measured",
  _profile: LEAN ? "lean" : "full",
  product_version: JSON.parse(readFileSync(join(APP, "product.json"), "utf8")).version,
  total_bytes: all.bytes,
  file_count: all.files,
  sourcemaps_bytes: maps.bytes,
  sourcemaps_files: maps.files,
  components: Object.fromEntries(Object.entries(buckets).map(([k, v]) => [k, v.bytes])),
  component_files: Object.fromEntries(Object.entries(buckets).map(([k, v]) => [k, v.files])),
  witnesses: Object.fromEntries(WITNESSES.map(w => {
    const p = join(DIST, w.path.split("/").join(sep));
    return [w.path, existsSync(p) ? lstatSync(p).size : null];
  })),
};

if (has("--json")) { console.log(JSON.stringify(measured, null, 2)); process.exit(0); }

// ── التأسيس ───────────────────────────────────────────────────────────────────────
if (has("--establish")) {
  const up = JSON.parse(readFileSync(join(ROOT, "upstream.json"), "utf8"));
  const prev = existsSync(BUDGET) ? JSON.parse(readFileSync(BUDGET, "utf8")) : {};
  const ceil = n => Math.round(n * 1.15);
  const floor = n => Math.round(n * 0.60);
  const budget = {
    _description: "[PF-01] ميزانيّةُ حجمِ محراب. **لا تُحرَّر يدويًّا برفعِ سقف**: أعِد التأسيس "
      + "بـ`node tests/perf/size.mjs --establish` والتزِم الفرقَ مرئيًّا. الأساسُ مقرونٌ بوسم "
      + "المنبع أدناه — ترقيةُ المنبع تُبطِله عمدًا.",
    _bounds: "لكلِّ مكوّنٍ سقفٌ (+15%) **وأرضيّةٌ** (−40%). الأرضيّةُ ليست تجميلًا: "
      + "بسقفٍ وحدَه يكون البناءُ الفارغ أخضرَ.",
    established_at: new Date().toISOString().slice(0, 10),
    upstream_vscodium_tag: up.vscodium.tag,
    product_version: measured.product_version,
    profile: measured._profile,
    // تُصان عبر إعادة التأسيس: إعادةُ التأسيس لا يجوز أن تمحوَ غيابًا مُعلَنًا فتحوّله صامتًا،
    // ولا أن تمحوَ نسبَ القياس فيصير الرقمُ بلا مصدر.
    ...(prev._provenance ? { _provenance: prev._provenance } : {}),
    ...(prev._version_note ? { _version_note: prev._version_note } : {}),
    known_absent: prev.known_absent || [],
    // هامشُ المجموع ضيّقٌ (±10%) لأنّ المنبعَ مثبَّتُ الوسم فحجمُه شبهُ ثابت؛ وهامشُ
    // المكوّنات أوسعُ (‏+15%/−40%) لأنّها تنمو وتنكمش مع المنبع.
    max_total_bytes: Math.round(all.bytes * 1.10),
    min_total_bytes: Math.round(all.bytes * 0.90),
    components: Object.fromEntries(Object.entries(buckets).map(([k, v]) => [k, { min: floor(v.bytes), max: ceil(v.bytes) }])),
  };
  // ── بوّابةُ التأسيس: لا يُثبَّت خرابٌ صامتًا ────────────────────────────────────
  // `--establish` كان يكتب الأساسَ بلا أن يقارنه بالأساس السابق. فنسخةٌ ناقصةٌ (‏`cp -r`
  // مقطوع، دلوٌ نصفُ محتواه) تصير **هي التعريف**، ويحمرّ بعدها البناءُ السليم: ينقلب
  // الحارسُ مرجعًا. فيُطبَع الفرقُ دائمًا، ويُرفَض الانحرافُ الكبيرُ إلّا بـ`--force`.
  if (prev.components) {
    const DRIFT = 0.25;
    const drift = [];
    const mid = b => (b.min / 0.60 + b.max / 1.15) / 2;   // تقديرُ القياس الذي وُلِّد منه الحدّان
    for (const [k, v] of Object.entries(buckets)) {
      const b = prev.components[k];
      if (!b) { drift.push(`  + ${k}: مكوّنٌ جديد (${MB(v.bytes)})`); continue; }
      const was = mid(b), now = v.bytes;
      const d = was ? (now - was) / was : (now ? 1 : 0);
      if (Math.abs(d) >= DRIFT) drift.push(`  ${d < 0 ? "↓" : "↑"} ${k}: ${MB(was)} ⇐ ${MB(now)}  (${(d * 100).toFixed(0)}%)`);
    }
    for (const k of Object.keys(prev.components)) if (!(k in buckets)) drift.push(`  − ${k}: مكوّنٌ اختفى من التعريف`);
    const dTotal = prev.max_total_bytes ? (all.bytes - prev.max_total_bytes / 1.10) / (prev.max_total_bytes / 1.10) : 0;
    if (Math.abs(dTotal) >= 0.05) drift.push(`  ⇄ المجموع: ${(dTotal * 100).toFixed(1)}%`);
    if (drift.length) {
      console.log("انحرافٌ عن الأساس السابق:\n" + drift.join("\n"));
      if (!has("--force")) {
        console.error("\n❌ لم يُؤسَّس. تأسيسٌ فوق انحرافٍ كهذا يُثبِّت بناءً ناقصًا مرجعًا.\n"
          + "   إن كان الانحرافُ مقصودًا فأعِد بـ`--force` واذكر السببَ في التزامك.");
        process.exit(1);
      }
      console.log("‏--force: يُثبَّت الانحرافُ أعلاه أساسًا جديدًا.");
    } else console.log("لا انحرافَ يُذكَر عن الأساس السابق.");
  }
  writeFileSync(BUDGET, JSON.stringify(budget, null, 2) + "\n", "utf8");
  console.log(`✅ أُسِّست الميزانيّة في ${relative(ROOT, BUDGET)} (وسم المنبع ${up.vscodium.tag})`);
  process.exit(0);
}

// ── الحكم ─────────────────────────────────────────────────────────────────────────
if (!existsSync(BUDGET)) {
  console.error("❌ لا budget.json — شغّل: node tests/perf/size.mjs --establish");
  process.exit(2);
}
const budget = JSON.parse(readFileSync(BUDGET, "utf8"));

// انجرافُ المنبع يُبطِل الأساس. تنبيهٌ لا فشل: الأساسُ يُعاد تأسيسُه في التزامٍ مرئيّ.
const up = JSON.parse(readFileSync(join(ROOT, "upstream.json"), "utf8"));
if (budget.upstream_vscodium_tag !== up.vscodium.tag)
  console.log(`⚠️ وسمُ المنبع تغيّر (${budget.upstream_vscodium_tag} ⇐ ${up.vscodium.tag}) — الأساسُ عتيقٌ، أعِد التأسيس.`);

console.log(`\nالمجموع: ${MB(all.bytes)} في ${all.files} ملفًّا  ·  منها خرائطُ مصدر: ${MB(maps.bytes)} (${maps.files})`);
console.log(`الطراز: ${measured._profile}${LEAN ? "  (‏MIHRAB_PERF_PROFILE=lean — المكوّناتُ الاختياريّة غيرُ مطلوبة)" : ""}`);

// (أ) المجموع
if (all.bytes > budget.max_total_bytes) bad(`المجموعُ ${MB(all.bytes)} > السقف ${MB(budget.max_total_bytes)}`);
if (all.bytes < budget.min_total_bytes) bad(`المجموعُ ${MB(all.bytes)} < الأرضيّة ${MB(budget.min_total_bytes)} — بناءٌ ناقصُ المحتوى`);

// (ب) المكوّنات — بحدَّيها
console.log("\nالمكوّنات:");
for (const [k, c] of Object.entries(COMPONENTS)) {
  const got = buckets[k], b = budget.components[k];
  const skip = c.optional && LEAN;
  const mark = got.files === 0 ? "∅" : "•";
  console.log(`  ${mark} ${k.padEnd(20)} ${MB(got.bytes).padStart(12)}  (${got.files} ملفًّا)`);
  // **مكوّنٌ بلا سطرِ ميزانيّةٍ يُفشِل** — كان تنبيهًا يُطبَع ويُمضى. وأثرُه أنّ إضافةَ
  // مكوّنٍ بلا `--establish` تتركه **بلا حدَّين** والحارسُ أخضر: كلُّ ما وُضع الدلوُ لأجله
  // ساقطٌ، والخرجُ يقول «✅ الحجمُ داخل الميزانيّة». أمسكه حارسُ الحرّاس بعطبٍ مزروع.
  if (!b) { bad(`${k}: لا سطرَ ميزانيّةٍ لهذا المكوّن — أعِد التأسيس (‏--establish)`); continue; }
  if (skip) continue;
  // شاهدُ تفعيلٍ موجب: دلوٌ بلا ملفٍّ واحدٍ لم يُقَس، فلا يُحكَم عليه بـ«تحت السقف».
  if (got.files === 0) { bad(`${k}: لا ملفَّ واحدًا — المكوّنُ غائبٌ لا «صغير»`); continue; }
  if (got.bytes > b.max) bad(`${k}: ${MB(got.bytes)} > السقف ${MB(b.max)}`);
  if (got.bytes < b.min) bad(`${k}: ${MB(got.bytes)} < الأرضيّة ${MB(b.min)}`);
}

// فحصُ الاتّساق الذي كان **مُعلَنًا في التعليق وغيرَ موجودٍ في الشيفرة**: `uncategorised`
// كان يُراكَم ولا يُقرأ. وهو المقياسُ الوحيدُ الذي يقول «شُحن شيءٌ لا يعرفه أيُّ دلو» —
// أي أنّ امتدادًا جديدًا (أو ساقطًا) خارجَ التعريف يمرّ بلا أن يُذكَر. يُطبَع دائمًا،
// ولا يُفشِل: نواةُ المنبع نفسُها غيرُ مصنَّفةٍ عمدًا، فالرقمُ للقراءة لا للحكم.
const bucketed = Object.values(buckets).reduce((s, v) => s + v.bytes, 0);
console.log(`\nغيرُ مصنَّف: ${MB(uncategorised)} (منها نواةُ المنبع) · في الدِّلاء: ${MB(bucketed)}`);
if (bucketed + uncategorised !== all.bytes)
  bad(`اتّساق: مجموعُ الدِّلاء وغيرِ المصنَّف (${bucketed + uncategorised}) ≠ المجموع (${all.bytes}) ⇒ دلوان متقاطعان`);

// **وكلُّ ما نملكه يُوزَن.** فحصُ الاتّساق أعلاه يُثبت أنّ الدِّلاءَ لا تتقاطع؛ وهذا يُثبت
// أنّها **تُغطّي**. بلا الشقّ الثاني يبقى الحدُّ الإجماليُّ يُخفي فقدانَ أيّ مكوّنٍ صغيرٍ
// مهما عظُم شأنُه — وهو ما وقع فعلًا لحزمة التعريب قبل أن يُضاف دلوُها.
for (const [name, got] of [...orphanOwned].sort()) {
  bad(`شُحن ما لا دلوَ له: extensions/${name} (${got.files} ملفًّا · ${MB(got.bytes)}) — كلُّ ما نملكه يُوزَن`);
  console.log(`      ⇐ أضِف مكوّنًا في COMPONENTS ثمّ أعِد التأسيس؛ أو احذفه من البناء إن لم يُقصَد شحنُه.`);
}

// (ج) الشواهد المفردة
// `known_absent`: غيابٌ **مُعلَنٌ** بسببٍ مكتوب. الفرقُ عن الغياب الصامت هو كلُّ الفرق —
// وحارسٌ أحمرُ دائمًا يُتجاهَل فيصير كالغائب. فالمُعلَنُ يُطبَع تنبيهًا، و**أيُّ غيابٍ زائدٍ
// على القائمة يُفشِل**: القائمةُ تُقصَر ولا تطول إلّا بالتزامٍ مرئيّ.
console.log("\nالشواهد:");
const declaredAbsent = new Set(budget.known_absent?.map(e => e.path) || []);
for (const w of WITNESSES) {
  const got = measured.witnesses[w.path];
  const name = w.path.replace("resources/app/extensions/", "");
  if (got === null) {
    if (w.optional && LEAN) { console.log(`  – ${name} — غائبٌ بإعلان (lean)`); continue; }
    if (declaredAbsent.has(w.path)) {
      // **الإعلانُ لا يُسكِت شاهدًا إلزاميًّا.** كان `known_absent` مجموعةَ مساراتٍ تُطابَق
      // بلا شرط، فسطرٌ واحدٌ فيه يُطفئ شاهدَ الخطّ — وهو الذي بدونه يُعطَّل أمرُ الطباعة —
      // والميزانيّةُ خضراء. الإعلانُ يصف ما **يسقط رشيقًا في البناء**، لا ما يُبطِل ميزةً.
      if (!w.optional) {
        bad(`${name}: مُدرَجٌ في known_absent وهو شاهدٌ **إلزاميّ** — الإعلانُ لا يُسقِط الإلزام`);
        continue;
      }
      const why = budget.known_absent.find(e => e.path === w.path).why;
      console.log(`  ⚠ ${name} — غيابٌ مُعلَن: ${why}`);
      continue;
    }
    bad(`الشاهدُ غائب: ${name}` + (w.optional ? "  (‏سقوطٌ رشيقٌ في build.sh — أو أعلِن lean)" : ""));
    continue;
  }
  if (declaredAbsent.has(w.path))
    bad(`${name}: مُدرَجٌ في known_absent وهو **موجود** — احذف السطرَ من budget.json`);
  if (got < w.min) { bad(`الشاهدُ أصغرُ من حدِّه: ${name} = ${got} بايت < ${w.min}`); continue; }
  console.log(`  ✓ ${name.padEnd(46)} ${MB(got).padStart(10)}`);
}

// (د) الممنوع
if (forbiddenHits.length) {
  const byLabel = new Map();
  for (const [label, rel] of forbiddenHits) {
    if (!byLabel.has(label)) byLabel.set(label, []);
    byLabel.get(label).push(rel);
  }
  for (const [label, list] of byLabel)
    bad(`شُحن ما لا يُشحَن — ${label}: ${list.length} ملفًّا (مثالًا: ${list[0]})`);
} else console.log("\n✓ لا اختباراتٍ ولا سكربتاتِ توليدٍ داخل الامتدادات المشحونة");

// ── الخلاصة ───────────────────────────────────────────────────────────────────────
console.log();
if (rc === 0) console.log("╚══ ✅ الحجمُ داخل الميزانيّة (سقفًا وأرضيّة) ══╝");
else { for (const p of problems) console.error(`❌ ${p}`); console.error("╚══ ❌ الميزانيّةُ خُرقت ══╝"); }
process.exit(rc);
