// [DX-02] قياسُ رتبةِ الإكمال بالعربيّة — **قبل** بناء عميل LSP لا بعده.
//
// ## السؤال الذي لم يُطرَح
// ‏`language-configuration.json` يوسّع `wordPattern` ليشمل العربيّة، وهذا صحيح. لكنّ **فرزَ**
// الاقتراحات في Monaco خوارزميّةُ مطابقةٍ ضبابيّةٌ مبنيّةٌ على أعرافٍ لاتينيّة: حدودُ
// ‏`camelCase`، والحروفُ الكبيرة، وبدايةُ الكلمة. والمعرّفاتُ العربيّة تُكتَب `نصاب_الفضة` — بلا
// حروفٍ كبيرة، وحدُّها الوحيدُ شرطةٌ سفليّةٌ لاتينيّة.
//
// فالسؤال: **هل كتابةُ «فضة» ترفع `نصاب_الفضة` إلى صدارة القائمة؟** إن لم تفعل، فسيصف
// المستخدمُ الإكمالَ بأنّه «لا يفهم العربيّة» — **وسيُلقى اللومُ على خادم LSP الذي لم يُبنَ
// بعد**، بينما العطبُ في طبقةِ فرزٍ سابقةٍ عليه تمامًا.
//
// ## لماذا قياسٌ بخطِّ أساسٍ لا حارسٌ بعتبة
// **الرتبةُ** تُقاس وتُقال ولا عتبةَ لها: لا نعرف بعدُ ما «الرتبةُ المقبولة»، وعتبةٌ مخترَعةٌ
// أسوأُ من قياسٍ صادق.
//
// أمّا **«لا تظهر إطلاقًا»** فعطبٌ لا رأيَ فيه — وقد قِسناه فوجدناه **قائمًا اليوم في أربعٍ
// من ثمانٍ**، وسببُه منبعيٌّ لا نملكه (انظر أدناه). فلو أفشلنا البناءَ عليه لصار أحمرَ دائمًا
// **لا يُصلَحه أحد** — ويُعلَّم تجاهُلُه، وهو أسوأُ ما يصيب حارسًا. ولو ابتلعناه لصار أخضرَ
// يخفي أحمر.
//
// فالحلُّ **خطُّ أساسٍ مكتوب**: نُعلِن الفجوةَ القائمةَ بالاسم، ونُفشِل حين **تتّسع** أو حين
// تنكسر حالةٌ كانت تعمل. فالحارسُ يمسك انحدارَنا، ولا يلومنا على عطبِ غيرِنا.
//
// ## ويقيس **ما يجري في المحرّر بالضبط** — لا تقريبًا له
// أوّلُ صياغةٍ لهذا الملفّ استدعت `fuzzyScore` بخيار `firstMatchCanBeWeak: true`، فأعطت
// «‏٠ لا تظهر» وسُجِّلت خلاصةً في خارطة م6. **وكانت خاطئةً في موضعين**، وأمسكتهما مراجعة:
//   ‏(١) المحرّرُ يستعمل `fuzzyScoreGracefulAggressive` لا `fuzzyScore`
//       (‏`completionModel.ts:140`، ما دام `filterGraceful` مضبوطًا — وهو الافتراض).
//   ‏(٢) `firstMatchCanBeWeak = !matchOnWordStartOnly` (‏`suggestModel.ts:611`)، و
//       `editor.suggest.matchOnWordStartOnly` **افتراضُه `true`** (‏`editorOptions.ts:5112`)
//       ⇒ القيمةُ الفعليّة `false` — **عكسُ** ما مُرِّر.
// فالخيارُ يُقرأ الآن من `FuzzyScoreOptions.default` في المصدر نفسِه لا يُكتَب يدويًّا:
// المكتوبُ يدويًّا هو ما انجرف.
//
// الاستعمال:  node tests/dx/completion_rank.mjs

import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync, existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..');
const UP = join(ROOT, '.upstream', 'vscode');
const FILTERS = join(UP, 'src', 'vs', 'base', 'common', 'filters.ts');
const TSC = join(UP, 'node_modules', 'typescript', 'lib', 'tsc.js');
// الرقعةُ المشحونة نفسُها — لا نسخةٌ منها ولا وصفٌ لها.
const PATCH = join(ROOT, 'patches', 'core', '020-nonlatin-word-start.patch');
const MARKER = 'isAfterDefiniteArticleAtPos';

// عشرون معرّفًا عربيًّا من طرازِ ما يُكتَب فعلًا (شرطةٌ سفليّةٌ حدًّا، بلا حروفٍ كبيرة).
const IDENTIFIERS = [
  'نصاب_الفضة', 'نصاب_الذهب', 'حساب_الزكاة', 'مقدار_الزكاة', 'سعر_الغرام',
  'تاريخ_الحول', 'رصيد_الحساب', 'إجمالي_المال', 'عدد_الأيام', 'نسبة_الربح',
  'اسم_المستخدم', 'كلمة_المرور', 'قائمة_الطلاب', 'درجة_الطالب', 'متوسط_الدرجات',
  'طباعة_التقرير', 'قراءة_الملف', 'كتابة_الملف', 'حذف_السجل', 'تحديث_البيانات',
];

// كتاباتٌ جزئيّةٌ **يكتبها المستخدمُ فعلًا**، والنتيجةُ المتوقَّعةُ منها.
const QUERIES = [
  { typed: 'فضة', want: 'نصاب_الفضة', note: 'كلمةٌ في **آخر** المعرّف — لا في بدايته' },
  { typed: 'نصاب', want: 'نصاب_الفضة', note: 'بدايةُ المعرّف (أسهلُ حالة)' },
  { typed: 'زكاة', want: 'حساب_الزكاة', note: 'كلمةٌ بعد الشرطة السفليّة' },
  { typed: 'حسابالزكاة', want: 'حساب_الزكاة', note: 'بلا الشرطة — كما يُكتَب على عجل' },
  { typed: 'كلمة', want: 'كلمة_المرور', note: 'بدايةٌ عربيّةٌ صرفة' },
  { typed: 'مرور', want: 'كلمة_المرور', note: 'ذيلٌ عربيٌّ صرف' },
  { typed: 'طباعة', want: 'طباعة_التقرير', note: 'فعلٌ في البداية' },
  { typed: 'تقرير', want: 'طباعة_التقرير', note: 'مفعولٌ في النهاية' },
];

/**
 * **الفجوةُ المقيسة** (2026-08-05، على العقدة المثبَّتة قبل الرقعة): كتاباتٌ لا تُظهِر
 * مقصودَها لأنّ `matchOnWordStartOnly` (افتراضُه `true`) يوجب بدءَ المطابقة عند **حدّ
 * كلمة**، وحدُّ الكلمة عند المنبع لاتينيٌّ — حرفٌ كبيرٌ وفواصلُ ASCII.
 *
 * **والقياسُ صحّح تشخيصَنا الأوّل**: الفاصلةُ نفسُها ليست لاتينيّةَ الأثر — «الفضة» تُظهِر
 * `نصاب_الفضة` سلفًا. الذي يسقط هو ما بعد **أداة التعريف**: يكتب العربيُّ «فضة» ولا يكتب
 * «الـ»، تمامًا كما يكتب اللاتينيُّ `Btn` لا `SubmitButton`. فأداةُ التعريف هي نظيرُ الحرف
 * الكبير في كتابةٍ بلا حالةِ أحرف — وهذا ما تعلّمه الرقعةُ للمطابِق.
 *
 * ⇒ [م-١٥/ب]، ورقعةٌ منبعيّةُ الصياغة: `patches/core/020-nonlatin-word-start.patch`.
 */
const GAP_BEFORE_PATCH = ['فضة', 'زكاة', 'مرور', 'تقرير'];

const log = (s) => console.log(s);

log('═══ [DX-02] قياسُ رتبةِ الإكمال بالعربيّة ═══');

if (!existsSync(FILTERS) || !existsSync(TSC)) {
  log('  ⚠️ شجرةُ المنبع أو tsc المحلّيّ غيرُ متوفّرة — تخطٍّ (القياسُ يحتاج مُطابِقَ المنبع نفسَه).');
  log(`     المتوقَّع: ${FILTERS}`);
  process.exit(0);
}
if (!existsSync(PATCH)) {
  log('  ❌ الرقعةُ المشحونة مفقودة: ' + PATCH);
  process.exit(1);
}

const PROBE = join(dirname(FILTERS), 'filters.mihrab-probe.ts');
const dir = mkdtempSync(join(tmpdir(), 'mihrab-rank-'));

/**
 * يُصرّف نصَّ مُطابِقٍ ويُعيده وحدةً قابلةً للاستدعاء.
 *
 * ‏`filters.ts` يستورد إخوةً في الحزمة نفسِها (`charCode`، `strings`، `map`…). فنكتب النصَّ
 * ملفًّا **جارًا له في الشجرة** ونصرّفه بـ`rootDir = src`، فتُحَلّ استيراداتُه كما تُحَلّ في
 * البناء الحقيقيّ — لا نسخةً معزولةً تكسر نصفَ ما تقيس، **ولا تعديلًا على ملفّ المنبع نفسِه**
 * (فحصٌ يترك الشجرةَ مغايرةً لِما وجدها عليه يُفسِد ما بعده).
 *
 * **ولا يُقرأ رمزُ خروج tsc حكمًا**: الشجرةُ تُصرَّف عندهم بإعداداتٍ خاصّة فتظهر أخطاءُ
 * أنواعٍ في ملفّاتٍ لا تعنينا، و`tsc` **يُخرِج JS رغمها**. فالحكمُ على **وجود المخرَج**.
 */
async function compileMatcher(source, tag) {
  const out = join(dir, tag);
  writeFileSync(PROBE, source, 'utf8');
  try {
    try {
      execFileSync(process.execPath, [
        TSC, '--target', 'ES2022', '--module', 'ES2022', '--moduleResolution', 'bundler',
        '--skipLibCheck', '--outDir', out, '--rootDir', join(UP, 'src'), PROBE,
      ], { stdio: 'pipe' });
    } catch {
      /* أخطاءُ أنواعٍ في ملفّاتٍ مجاورة — المخرَجُ يُفحَص أدناه */
    }
    const emitted = join(out, 'vs', 'base', 'common', 'filters.mihrab-probe.js');
    if (!existsSync(emitted)) throw new Error('لم يُخرِج tsc مُطابِقًا (' + tag + ')');
    return await import(pathToFileURL(emitted).href);
  } finally {
    rmSync(PROBE, { force: true });
  }
}

/**
 * نصُّ المُطابِق **بعد الرقعة المشحونة** — لا بحسب مزاج الشجرة.
 *
 * الشجرةُ بعد بناءٍ كاملٍ تحمل الرقعةَ، وقبله لا تحملها. فقياسٌ يقرأ الشجرةَ كما هي يُخبِر
 * عن آخر بناءٍ لا عمّا نشحن. فنُطبِّق الرقعةَ بـ`git apply` ونقرأ الناتجَ **ونردّ الملفَّ
 * فورًا**؛ والتصريفُ بعدها على ملفٍّ جارٍ لا على المنبع.
 */
function patchedSource(original) {
  if (original.includes(MARKER)) return original;   // الشجرةُ مرقَّعةٌ سلفًا (بعد بناء)
  try {
    execFileSync('git', ['-C', UP, 'apply', '--include=src/vs/base/common/filters.ts', PATCH], { stdio: 'pipe' });
  } catch (e) {
    throw new Error('الرقعةُ المشحونة لا تنطبق على شجرة المنبع — انجرافُ مرساة: ' +
      String(e.stderr || e.message || e).slice(0, 200));
  }
  try {
    return readFileSync(FILTERS, 'utf8');
  } finally {
    writeFileSync(FILTERS, original, 'utf8');       // تُردّ فورًا مهما حدث
  }
}

const treeSource = readFileSync(FILTERS, 'utf8');
const treeIsPatched = treeSource.includes(MARKER);

let mod, base;
try {
  mod = await compileMatcher(patchedSource(treeSource), 'patched');
  // خطُّ الأساس المنبعيُّ للمقارنة — يتعذّر حين تكون الشجرةُ مرقَّعةً سلفًا (بعد بناء)، فيُقال.
  base = treeIsPatched ? null : await compileMatcher(treeSource, 'upstream');
  log('  ✅ صُرِّف مُطابِقُ المنبع + رقعتُنا — القياسُ على الخوارزميّة والخيارات المشحونة');
} catch (e) {
  const msg = String(e.message || e).slice(0, 220);
  rmSync(dir, { recursive: true, force: true });
  // انجرافُ المرساة عطبُنا فيُفشِل؛ وغيابُ عُدّةِ التصريف بيئةٌ فتُتخطّى.
  if (msg.includes('لا تنطبق')) { log('  ❌ ' + msg); process.exit(1); }
  log('  ⚠️ تعذّر تصريفُ مُطابِق المنبع — تخطٍّ: ' + msg);
  process.exit(0);
}

const { fuzzyScoreGracefulAggressive, FuzzyScoreOptions } = mod;
if (typeof fuzzyScoreGracefulAggressive !== 'function' || !FuzzyScoreOptions) {
  log('  ⚠️ مُطابِقُ الاقتراحات غيرُ مُصدَّرٍ من هذه العقدة — تخطٍّ.');
  rmSync(dir, { recursive: true, force: true });
  process.exit(0);
}
// **الخيارُ من المصدر لا من الذاكرة.** `FuzzyScoreOptions.default` هو ما يُمرَّر فعلًا حين
// لا يُمرَّر شيء، وهو ما يُحاكي `matchOnWordStartOnly: true` المشحون.
const OPTS = FuzzyScoreOptions.default;

/** يرتّب المعرّفات كما يفعل Monaco: نتيجةٌ أعلى ⇒ رتبةٌ أعلى؛ وغيرُ المطابِق يسقط. */
function rank(typed, candidates) {
  const low = typed.toLowerCase();
  const scored = [];
  for (const word of candidates) {
    const r = fuzzyScoreGracefulAggressive(typed, low, 0, word, word.toLowerCase(), 0, OPTS);
    if (r) scored.push({ word, score: r[0] });
  }
  scored.sort((a, b) => b.score - a.score || a.word.localeCompare(b.word));
  return scored;
}

let missing = 0;
const rows = [];
for (const q of QUERIES) {
  const scored = rank(q.typed, IDENTIFIERS);
  const idx = scored.findIndex((s) => s.word === q.want);
  rows.push({ ...q, rank: idx < 0 ? null : idx + 1, of: scored.length, score: idx < 0 ? null : scored[idx].score });
  if (idx < 0) missing++;
}

log('');
log(`  (المرشَّحات: ${IDENTIFIERS.length} معرّفًا. «الرتبة/المطابِقات» — ومطابِقاتٌ قليلةٌ تجعل`);
log('   الصدارةَ بِركةً لا إنجازًا، فيُقرأ العمودان معًا.)');
log('');
log('  المكتوب      → المطلوب            الرتبة/المطابِقات  النتيجة   الملاحظة');
for (const r of rows) {
  const rk = r.rank === null ? '— لا يظهر' : `${r.rank}/${r.of}`;
  log(`  ${r.typed.padEnd(12)} → ${r.want.padEnd(16)} ${String(rk).padEnd(16)} ${String(r.score ?? '—').padEnd(8)} ${r.note}`);
}

const firstRank = rows.filter((r) => r.rank === 1).length;
const topThree = rows.filter((r) => r.rank !== null && r.rank <= 3).length;
log('');
log(`  الخلاصة: ${firstRank}/${rows.length} في الصدارة · ${topThree}/${rows.length} ضمن الثلاثة الأُوَل · ${missing} لا تظهر إطلاقًا`);

// **الحكم:** ألّا تظهر النتيجةُ إطلاقًا عطبٌ لا رأي فيه — وقد صار في يدنا، فيُفشِل. أمّا
// الرتبةُ فتُقاس وتُقال ولا عتبةَ لها بعد؛ وعتبةٌ مخترَعةٌ أسوأُ من قياسٍ صادق.
const gone = rows.filter((r) => r.rank === null).map((r) => r.typed);

// **والرقعةُ تُقاس أثرًا لا وجودًا.** ملفٌّ يُشحَن ولا يُغيّر شيئًا أسوأُ من غيابه: يُقرأ
// كأنّه يعمل. فيُقاس المنبعُ العاري إلى جانبها، وتُقال الفجوةُ التي سدّتها بالاسم.
let closed = null;
if (base) {
  const bOpts = base.FuzzyScoreOptions.default;
  closed = QUERIES.filter((q) =>
    !base.fuzzyScoreGracefulAggressive(q.typed, q.typed.toLowerCase(), 0, q.want, q.want.toLowerCase(), 0, bOpts)
  ).map((q) => q.typed);
}

log('');
if (gone.length) {
  log(`  ❌ ${gone.length} كتاباتٍ لا تُظهِر مقصودَها — ${gone.join('، ')}`);
  log('     ألّا تظهر النتيجةُ إطلاقًا ليس ضعفَ ترتيبٍ بل عطبٌ يُعلَّم منه المستخدمُ ألّا يبحث.');
} else {
  log('  ✅ كلُّ كتابةٍ جزئيّةٍ تُظهِر مقصودَها.');
}

log('');
if (closed === null) {
  log('  ℹ️ الشجرةُ مرقَّعةٌ سلفًا (بعد بناء) — فلا خطَّ أساسٍ منبعيًّا عاريًا يُقارَن به هنا.');
} else if (closed.length) {
  log(`  ✅ أثرُ الرقعة مقيسٌ: ${closed.length} كتاباتٍ كانت تسقط عند المنبع العاري — ${closed.join('، ')}`);
  const expected = GAP_BEFORE_PATCH.filter((t) => !closed.includes(t));
  if (expected.length) {
    log(`     (وكانت الفجوةُ المسجَّلةُ تضمّ أيضًا: ${expected.join('، ')} — سُدَّت عند المنبع نفسِه؟ راجعها.)`);
  }
} else {
  log('  ⚠️ المنبعُ العاري يُظهِر كلَّ الكتابات — رقعتُنا لم تعد تشتري شيئًا.');
  log('     ⇒ لعلّ المقترحَ [م-١٥/ب] دُمِج: احذف patches/core/020-nonlatin-word-start.patch');
  log('     ووصلَه في build.sh وpatch_bundle_extensions.py، ولا تُبقِ دَينًا بلا ثمن.');
}
log('');
log('  ملاحظةُ صدق: الرتبةُ تُقاس وتُقال بلا عتبة؛ والحكمُ على «لا تظهر إطلاقًا» وحدَه.');

rmSync(dir, { recursive: true, force: true });
process.exit(gone.length ? 1 : 0);
