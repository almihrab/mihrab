"use strict";
/**
 * كاشفُ قلبِ الاتّجاه — واعٍ بالعربيّة [BS-01]. وحدةٌ **نقيّة** بلا `vscode` (تُختبَر وحدويًّا).
 *
 * ## لماذا في محرابٍ دون سواه
 * هجومُ «Trojan Source» يستعمل محارفَ قلبِ الاتّجاه ليجعل الشيفرةَ **تُقرَأ بترتيبٍ غيرِ
 * الذي تُنفَّذ به**. وفي محرّرٍ إنجليزيٍّ يبدو أيُّ محرفِ اتّجاهٍ شاذًّا فيُشتَبَه فيه. أمّا في
 * محراب — حيث الشيفرةُ عربيّةٌ وحيث أطفأنا عمدًا `nonBasicASCII` في خمس لغات — **فمحرفُ
 * الاتّجاه مواطنٌ طبيعيٌّ لا غريب**. أي أنّ الإعفاءَ الذي أنقذ قراءةَ العربيّة وسّع في الوقت
 * نفسِه سطحَ الهجوم. وهذه حجّةٌ لِما يجب أن يُبنى بجانبه، لا حجّةٌ ضدّه.
 *
 * ## لماذا لا يكفي إبرازُ «المحارف الخفيّة» المنبعيّ
 * لأنّه **يبرز ولا يميّز**. وقياسُنا يثبته بأرقامنا: ٣١٢ علامةً خفيّةً في نواة نهلة، كلُّها
 * `RLM`/`LRM` — أي **مشروعةٌ تمامًا** في نصٍّ عربيّ. فالمستخدمُ يرى تحذيرًا يوميًّا على
 * محارفَ سليمة، فيتعلّم تجاهُلَه، **فيصير التحذيرُ غطاءً للهجوم لا حاجزًا دونه**.
 *
 * ## القاعدةُ الحاسمة
 * الفرقُ ليس بين محرفٍ ومحرف، بل بين **علامةٍ** و**قالبٍ يتسرّب**:
 *   • **علامة** (`RLM`/`LRM`/`ALM`) — محرفٌ مفردٌ بلا نطاق: لا يقلب شيئًا بعده. **لا تشخيص.**
 *   • **قالبٌ متوازنٌ داخل منطقةٍ واحدة** (`FSI…PDI` كلاهما في السلسلة نفسِها) — **لا تشخيص.**
 *   • **قالبٌ غيرُ متوازن** — فاتحٌ بلا خاتمٍ قبل نهاية السطر: قلبٌ يتسرّب إلى بقيّة السطر.
 *   • **قالبٌ متوازنٌ عابرٌ للحدّ** — يُفتَح داخل تعليقٍ أو سلسلةٍ ويُغلَق خارجَها (أو العكس):
 *     متوازنٌ حسابيًّا، **يقلب شيفرةً حقيقيّةً فعلًا**. وهذه صيغةُ Trojan Source الأصليّة.
 *
 * **الصدقُ في حدّ الادّعاء:** «الفاتحُ بلا خاتم» أشيعُ توقيعٍ لا التوقيعُ الوحيد — ولذلك
 * أُضيف فحصُ العبور. وهذان معًا يقاربان ما يفعله `gcc -Wbidi-chars=unpaired` وما يزيد.
 *
 * والشدّةُ تتدرّج: التجاوزُ (`RLO`/`LRO`) أشدُّ من التضمين (`RLE`/`LRE`) لأنّه يفرض الاتّجاه
 * على المحارف القويّة نفسِها؛ ووقوعُ الفاتح **داخل تعليقٍ أو سلسلةٍ نصّيّة** يرفعه إلى الحرِج
 * لأنّ ما بينهما لا يقرؤه المصرِّفُ وتقرؤه العين — فيختلف ما يُرى عمّا يُنفَّذ.
 */

// ── المحارفُ المعنيّة (نقاطُ كودٍ لا محارفَ حرفيّة — لا خفيَّ في مصدرِ كاشفِ الخفيّ) ──
const LRE = 0x202a; // Left-to-Right Embedding
const RLE = 0x202b; // Right-to-Left Embedding
const PDF = 0x202c; // Pop Directional Formatting  (خاتمُ التضمين والتجاوز)
const LRO = 0x202d; // Left-to-Right Override
const RLO = 0x202e; // Right-to-Left Override
const LRI = 0x2066; // Left-to-Right Isolate
const RLI = 0x2067; // Right-to-Left Isolate
const FSI = 0x2068; // First Strong Isolate
const PDI = 0x2069; // Pop Directional Isolate    (خاتمُ العزل)
const LRM = 0x200e; // Left-to-Right Mark
const RLM = 0x200f; // Right-to-Left Mark
const ALM = 0x061c; // Arabic Letter Mark

/**
 * أسماءُ المحارف كما تُعرَض للمستخدم — رمزٌ لاتينيٌّ قصير (مُعرَّفٌ في يونيكود) + وصفٌ عربيّ.
 *
 * **الوصفُ يصف الأثرَ لا الآليّة.** «عزلٌ بأوّلِ قويّ» ترجمةٌ أمينةٌ لمصطلح UAX #9 ولا يفهمها
 * أحدٌ خارج المواصفة — فاستبدالُ مصطلحٍ إنجليزيٍّ غامضٍ بعربيٍّ غامضٍ لا يُفيد قارئًا. والمبتدئُ
 * لا يحتاج اسمَ الآليّة: يحتاج أن يعرف أنّ هذا المحرفَ **يقلب ما بعده**.
 */
const CHAR_NAMES = new Map([
  [LRE, { code: "LRE", ar: "بدءُ مقطعٍ يُقرأ من اليسار" }],
  [RLE, { code: "RLE", ar: "بدءُ مقطعٍ يُقرأ من اليمين" }],
  [PDF, { code: "PDF", ar: "نهايةُ المقطع" }],
  [LRO, { code: "LRO", ar: "فرضُ القراءة من اليسار" }],
  [RLO, { code: "RLO", ar: "فرضُ القراءة من اليمين" }],
  [LRI, { code: "LRI", ar: "بدءُ مقطعٍ معزولٍ من اليسار" }],
  [RLI, { code: "RLI", ar: "بدءُ مقطعٍ معزولٍ من اليمين" }],
  [FSI, { code: "FSI", ar: "بدءُ مقطعٍ يتبع اتّجاهَ أوّلِ حرفٍ فيه" }],
  [PDI, { code: "PDI", ar: "نهايةُ المقطع المعزول" }],
  [LRM, { code: "LRM", ar: "علامةُ ضبطٍ يساريّة" }],
  [RLM, { code: "RLM", ar: "علامةُ ضبطٍ يمينيّة" }],
  [ALM, { code: "ALM", ar: "علامةُ ضبطٍ عربيّة" }],
]);

// فاتحٌ ⇒ خاتمُه. التضمينُ والتجاوزُ يُغلَقان بـ`PDF`، والعزلُ بـ`PDI` — نظامان مستقلّان
// في يونيكود (UAX #9)، فلا يُغلِق أحدُهما الآخر. خلطُهما كان سيُنتج إنذاراتٍ كاذبة.
const OPENERS = new Map([
  [LRE, PDF], [RLE, PDF], [LRO, PDF], [RLO, PDF],
  [LRI, PDI], [RLI, PDI], [FSI, PDI],
]);
const CLOSERS = new Set([PDF, PDI]);
// التجاوزُ أشدُّ من التضمين: يفرض الاتّجاه على المحارف القويّة نفسِها (الحروفِ اللاتينيّة).
const OVERRIDES = new Set([LRO, RLO]);
/** العلاماتُ المفردةُ الشرعيّة — تُذكَر للعرض [BS-02] ولا تُشخَّص أبدًا. */
const MARKS = new Set([LRM, RLM, ALM]);

/** درجاتُ الشدّة، من الأعلى إلى الأدنى. */
const SEVERITY = { CRITICAL: "critical", SUSPECT: "suspect" };

/** أصنافُ المكتشَفات — تُميّز الرسالةَ والإصلاحَ معًا. */
const KIND = { UNBALANCED: "unbalanced", LEAK: "leak" };

/**
 * تعريفُ التعليقات والسلاسل لكلّ لغة. **ليس تزيينًا للشدّة بل ركنٌ في الكشف**: هجومُ
 * Trojan Source الأصليُّ يفتح القالبَ داخل تعليقٍ أو سلسلةٍ ويُغلِقه خارجَها.
 *
 * **حدٌّ معلَن:** هذا مسحٌ معجميٌّ بسيطٌ لا مُحلِّلٌ نحويّ — لا يعرف السلاسلَ الخامّة
 * (`r"…"`، والاقتباسَ المائلَ في Go) فيبتلع فيها الهروبَ خطأً، ولا السلاسلَ الثلاثيّة.
 * وأثرُ خطئه **رفعُ شدّةٍ أو خفضُها لا إسقاطُ كشفٍ للفاتح غير المتوازن** — ذاك يُشخَّص دائمًا.
 */
const SYNTAX = {
  python: { line: ["#"], quotes: ['"', "'"], block: [] },
  javascript: { line: ["//"], quotes: ['"', "'", "`"], block: [["/*", "*/"]] },
  typescript: { line: ["//"], quotes: ['"', "'", "`"], block: [["/*", "*/"]] },
  javascriptreact: { line: ["//"], quotes: ['"', "'", "`"], block: [["/*", "*/"]] },
  typescriptreact: { line: ["//"], quotes: ['"', "'", "`"], block: [["/*", "*/"]] },
  json: { line: ["//"], quotes: ['"'], block: [["/*", "*/"]] },
  jsonc: { line: ["//"], quotes: ['"'], block: [["/*", "*/"]] },
  c: { line: ["//"], quotes: ['"', "'"], block: [["/*", "*/"]] },
  cpp: { line: ["//"], quotes: ['"', "'"], block: [["/*", "*/"]] },
  csharp: { line: ["//"], quotes: ['"', "'"], block: [["/*", "*/"]] },
  rust: { line: ["//"], quotes: ['"', "'"], block: [["/*", "*/"]] },
  go: { line: ["//"], quotes: ['"', "`"], block: [["/*", "*/"]] },
  java: { line: ["//"], quotes: ['"', "'"], block: [["/*", "*/"]] },
  php: { line: ["//", "#"], quotes: ['"', "'"], block: [["/*", "*/"]] },
  css: { line: [], quotes: ['"', "'"], block: [["/*", "*/"]] },
  shellscript: { line: ["#"], quotes: ['"', "'"], block: [] },
  yaml: { line: ["#"], quotes: ['"', "'"], block: [] },
  ruby: { line: ["#"], quotes: ['"', "'"], block: [] },
  html: { line: [], quotes: ['"', "'"], block: [["<!--", "-->"]] },
  xml: { line: [], quotes: ['"', "'"], block: [["<!--", "-->"]] },
};
// الافتراضُ للّغات غيرِ المعرَّفة: تعليقُ `#` وسلسلتا `"` و`'` (قواعدُ بايثون نفسُها).
const DEFAULT_SYNTAX = SYNTAX.python;

/** المناطقُ الثلاث: شيفرةٌ · تعليقٌ · سلسلة. المقارنةُ بينها هي ما يكشف العبور. */
const REGION = { CODE: "code", COMMENT: "comment", STRING: "string" };

/**
 * يحسب **منطقةَ كلّ عمودٍ** في سطرٍ واحد بمسحٍ واحدٍ من اليسار.
 *
 * حالةُ التعليق الكتليّ تُمرَّر بين الأسطر (`state.block`) فتُفهَم التعليقاتُ الممتدّةُ
 * سطورًا — وهو ما كان الحدُّ المعلَن يعتذر عنه. تُعاد المصفوفةُ لا دالّةُ استعلامٍ لأنّ
 * الماسحَ يحتاج المنطقةَ عند كلّ محرفِ تحكّم، فحسابُها مرّةً واحدةً أرخصُ وأدقّ.
 *
 * @param {string} line @param {*} syntax @param {{block:?string}} state حالةٌ تُعدَّل مكانَها.
 * @returns {string[]} منطقةُ كلّ عمود.
 */
function regionsOfLine(line, syntax, state) {
  const out = new Array(line.length);
  let quote = null;
  let i = 0;
  while (i < line.length) {
    // (١) داخل تعليقٍ كتليٍّ ممتدّ: ابحث عن خاتمِه.
    if (state.block) {
      if (line.startsWith(state.block, i)) {
        for (let k = 0; k < state.block.length && i + k < line.length; k++) {
          out[i + k] = REGION.COMMENT;
        }
        i += state.block.length;
        state.block = null;
        continue;
      }
      out[i] = REGION.COMMENT;
      i++;
      continue;
    }
    // (٢) داخل سلسلة: الهروبُ يبتلع التالي، والاقتباسُ المطابقُ يُنهيها.
    if (quote) {
      out[i] = REGION.STRING;
      if (line[i] === "\\") {
        if (i + 1 < line.length) out[i + 1] = REGION.STRING;
        i += 2;
        continue;
      }
      if (line[i] === quote) quote = null;
      i++;
      continue;
    }
    // (٣) شيفرة: هل يبدأ هنا تعليقٌ سطريٌّ أو كتليٌّ أو سلسلة؟
    let opened = false;
    for (const marker of syntax.line) {
      if (line.startsWith(marker, i)) {
        for (let k = i; k < line.length; k++) out[k] = REGION.COMMENT;
        i = line.length;
        opened = true;
        break;
      }
    }
    if (opened) continue;
    for (const pair of syntax.block) {
      if (line.startsWith(pair[0], i)) {
        for (let k = 0; k < pair[0].length && i + k < line.length; k++) {
          out[i + k] = REGION.COMMENT;
        }
        i += pair[0].length;
        state.block = pair[1];
        opened = true;
        break;
      }
    }
    if (opened) continue;
    if (syntax.quotes.includes(line[i])) {
      out[i] = REGION.STRING;
      quote = line[i];
      i++;
      continue;
    }
    out[i] = REGION.CODE;
    i++;
  }
  return out;
}

/**
 * هل الإزاحةُ `col` في هذا السطر واقعةٌ داخل تعليقٍ أو سلسلةٍ نصّيّة؟
 * غلافٌ رفيعٌ حول `regionsOfLine` — يبقى مُصدَّرًا لأنّه سؤالٌ مستقلٌّ يُختبَر وحدَه.
 */
function inCommentOrString(line, col, syntax) {
  if (!line) return false;
  const r = regionsOfLine(line, syntax || DEFAULT_SYNTAX, { block: null });
  // إزاحةٌ عند نهاية السطر (أو بعدها) تُقرأ من **آخر محرفٍ فعليّ**: السؤالُ عمليًّا هو
  // «هل انتهى السطرُ ونحن داخل نصّ؟»، وهو ما تجيب عنه منطقةُ آخر محرف.
  const idx = Math.min(Math.max(col, 0), line.length - 1);
  return r[idx] === REGION.COMMENT || r[idx] === REGION.STRING;
}

/** يبني مكتشَفًا واحدًا (شكلٌ واحدٌ للصنفين، فلا يتباعد حقلٌ بينهما). */
function makeFinding(line, open, kind, closeColumn) {
  const info = CHAR_NAMES.get(open.cp);
  const inQuoted = open.region === REGION.COMMENT || open.region === REGION.STRING;
  // الحرِج: تجاوزٌ صريح · أو فاتحٌ داخل تعليقٍ/سلسلة · أو قالبٌ عابرٌ للحدّ.
  const severity =
    inQuoted || OVERRIDES.has(open.cp) || kind === KIND.LEAK
      ? SEVERITY.CRITICAL
      : SEVERITY.SUSPECT;
  return {
    line,
    column: open.col,
    endColumn: open.col + 1,
    codePoint: open.cp,
    code: info.code,
    nameAr: info.ar,
    severity,
    inQuoted,
    kind,
    closeColumn,
    region: open.region,
    expected: CHAR_NAMES.get(OPENERS.get(open.cp)).code,
  };
}

/**
 * يمسح نصًّا كاملًا ويعيد **القوالبَ التي تتسرّب**: غيرَ المتوازنة، والمتوازنةَ العابرةَ
 * لحدّ التعليق/السلسلة.
 *
 * نطاقُ التوازن سطرٌ سطر لا مستندٌ كامل — عمدًا: قلبٌ يعبر نهايةَ سطرِه تسرّبٌ بذاته، وفاتحٌ
 * منسيٌّ في أوّل الملفّ لا يُغرِق بقيّتَه بتشخيصاتٍ متتالية. أمّا **حالةُ التعليق الكتليّ**
 * فتُمرَّر بين الأسطر، فتُعرَف المنطقةُ صوابًا في ملفٍّ فيه تعليقٌ ممتدّ.
 *
 * @param {string} text نصُّ المستند كاملًا.
 * @param {string} [languageId] معرّفُ اللغة (يحدّد التعليقاتِ والسلاسل؛ الافتراضُ قواعدُ بايثون).
 * @returns {{line:number, column:number, endColumn:number, codePoint:number, code:string,
 *            nameAr:string, severity:string, inQuoted:boolean, expected:string,
 *            kind:string, closeColumn:?number, region:string}[]}
 *          مصفوفةٌ من المكتشَفات (سطرٌ وعمودٌ بادئتهما صفر، بوحدات UTF-16).
 */
function scanBidi(text, languageId) {
  if (typeof text !== "string" || !text) return [];
  const syntax = SYNTAX[languageId] || DEFAULT_SYNTAX;
  const findings = [];
  const lines = text.split(/\r\n|\r|\n/);
  // حالةُ التعليق الكتليّ تعبر الأسطر ⇒ لا يُتخطّى سطرٌ في لغةٍ لها تعليقٌ كتليّ، وإلّا
  // عمِيَت الحالةُ فانقلبت مناطقُ ما بعده (وهذا يُسقِط كشفًا لا يرفع شدّةً فقط).
  const state = { block: null };
  const HAS_CONTROL = /[\u202A-\u202E\u2066-\u2069]/;
  for (let ln = 0; ln < lines.length; ln++) {
    const line = lines[ln];
    // تخطٍّ رخيص: سطرٌ بلا محرفِ تحكّمٍ **وبلا احتمالِ تغييرِ حالةِ التعليق الكتليّ**.
    if (!HAS_CONTROL.test(line) && !syntax.block.length && !state.block) continue;
    const regions = regionsOfLine(line, syntax, state);
    if (!HAS_CONTROL.test(line)) continue;
    /** @type {{cp:number, col:number, region:string}[]} */
    const stack = [];
    for (let col = 0; col < line.length; col++) {
      const cp = line.charCodeAt(col);
      if (OPENERS.has(cp)) {
        stack.push({ cp, col, region: regions[col] });
      } else if (CLOSERS.has(cp)) {
        // أغلِق أحدثَ فاتحٍ **من نظامِه** (التضمين/التجاوز بـPDF، العزل بـPDI). خاتمٌ زائدٌ
        // بلا فاتح لا يقلب شيئًا فلا يُشخَّص — الضجيجُ عدوُّ هذا الحارس.
        for (let i = stack.length - 1; i >= 0; i--) {
          if (OPENERS.get(stack[i].cp) === cp) {
            const open = stack.splice(i, 1)[0];
            // **متوازنٌ لكنّه عابرٌ للحدّ**: فُتِح في منطقةٍ وأُغلِق في أخرى ⇒ القلبُ يسري
            // على شيفرةٍ حقيقيّة. هذه صيغةُ Trojan Source الأصليّة، ولا يمسكها التوازنُ وحدَه.
            //
            // **إلّا عزلَ السطر الكامل — وهو توقيعُنا نحن لا توقيعُ مهاجم.** أمرُ «انسخ
            // للنشر» (‏[BS-04]) يلفّ كلَّ سطرٍ بـ`FSI…PDI` من العمود صفر إلى آخر محرف.
            // وأيُّ سطرٍ فيه تعليقٌ طرفيٌّ يجعل الفاتحَ في `code` والخاتمَ في `comment` ⇒
            // «عابرٌ للحدّ» ⇒ خطأٌ حرجٌ أحمر. فكان النصُّ الذي نُسِخ **من محراب** يُتَّهم
            // فورَ لصقه **في محراب**، وزرُّ الإصلاح لا يمسّه (‏`stripUnbalanced` يزيل
            // الفواتحَ المعلَّقة وحدَها) — بابٌ مسدودٌ صنعناه بأيدينا عند زميل المستخدم.
            //
            // والاستثناءُ **ضيّقٌ لا يفتح ثغرة**: زوجُ عزلٍ (‏لا تجاوزٍ ولا تضمين) يبدأ
            // عند العمود صفر وينتهي عند آخر محرفٍ في السطر. مثلُ هذا الزوج **لا يقلب شيئًا
            // على شيفرةٍ حقيقيّة**: يعطي السطرَ سياقَه بنفسِه ولا يُخفي ترتيبًا داخله.
            // أمّا `RLO` أو زوجٌ جزئيٌّ فيبقى مشخَّصًا كما كان.
            const wrapsWholeLine =
              open.col === 0 && col === line.length - 1 &&
              open.cp === FSI && cp === PDI;
            if (open.region !== regions[col] && !wrapsWholeLine) {
              findings.push(makeFinding(ln, open, KIND.LEAK, col));
            }
            break;
          }
        }
      }
    }
    for (const open of stack) findings.push(makeFinding(ln, open, KIND.UNBALANCED, null));
  }
  // ترتيبٌ حتميٌّ بالموضع: العابرُ يُسجَّل عند خاتمه والمُعلَّقُ في آخر السطر، فبلا فرزٍ
  // يختلف ترتيبُ التشخيصات عن ترتيب الأسطر — وهو ما يراه المستخدمُ في لوحة المشاكل.
  findings.sort((a, b) => a.line - b.line || a.column - b.column);
  return findings;
}

/**
 * يزيل من النصّ **الفواتحَ غيرَ المتوازنة وحدَها** — لا كلَّ محرفِ اتّجاه.
 * العلاماتُ المفردةُ والقوالبُ المتوازنةُ تبقى كما هي: هي أدواتُ ترتيبٍ يستعملها كاتبُ
 * العربيّة كلَّ يوم، ومحوُها إصلاحٌ يكسر ما لم يكن مكسورًا.
 *
 * **والقالبُ العابرُ للحدّ لا يُمسّ أيضًا** وإن شُخِّص: حذفُ فاتحِه وحدَه يترك خاتمًا يتيمًا،
 * وحذفُ الطرفين قد يغيّر معنى نصٍّ مقصود. ذاك قرارُ إنسانٍ لا إصلاحٌ آليّ — والتشخيصُ
 * يدلّه على الموضع.
 * @param {string} text @param {string} [languageId] @returns {string}
 */
function stripUnbalanced(text, languageId) {
  const hits = scanBidi(text, languageId).filter((h) => h.kind === KIND.UNBALANCED);
  if (!hits.length) return text;
  // احذف من الآخِر إلى الأوّل كي لا تنزاح المواضعُ الباقية.
  const lines = text.split(/(\r\n|\r|\n)/);
  // `split` بمجموعةِ التقاط يُعيد [سطر، فاصل، سطر، فاصل…] ⇒ فهرسُ السطر ن = 2ن.
  const byLine = new Map();
  for (const h of hits) {
    if (!byLine.has(h.line)) byLine.set(h.line, []);
    byLine.get(h.line).push(h.column);
  }
  for (const [ln, cols] of byLine) {
    const idx = ln * 2;
    if (idx >= lines.length) continue;
    let s = lines[idx];
    for (const col of cols.slice().sort((a, b) => b - a)) {
      s = s.slice(0, col) + s.slice(col + 1);
    }
    lines[idx] = s;
  }
  return lines.join("");
}

/**
 * كلُّ محارف الاتّجاه في النصّ — **المشروعةُ والمشبوهةُ معًا** — لعرضِ اسمِ المحرف [BS-02].
 * مستقلٌّ عن `scanBidi` قصدًا: ذاك يشخّص، وهذا يُسمّي. خلطُهما كان سيعيد الضجيجَ الذي
 * وُجد هذا الملفُّ كلُّه لتفاديه.
 * @param {string} text
 * @returns {{line:number, column:number, code:string, nameAr:string, isMark:boolean}[]}
 */
function listBidiChars(text) {
  if (typeof text !== "string" || !text) return [];
  const out = [];
  const lines = text.split(/\r\n|\r|\n/);
  for (let ln = 0; ln < lines.length; ln++) {
    const line = lines[ln];
    for (let col = 0; col < line.length; col++) {
      const cp = line.charCodeAt(col);
      const info = CHAR_NAMES.get(cp);
      if (info) out.push({ line: ln, column: col, code: info.code, nameAr: info.ar, isMark: MARKS.has(cp) });
    }
  }
  return out;
}

module.exports = {
  scanBidi,
  stripUnbalanced,
  listBidiChars,
  inCommentOrString,
  regionsOfLine,
  KIND,
  REGION,
  SEVERITY,
  CHAR_NAMES,
  OPENERS,
  CLOSERS,
  OVERRIDES,
  MARKS,
  SYNTAX,
  CODE_POINTS: { LRE, RLE, PDF, LRO, RLO, LRI, RLI, FSI, PDI, LRM, RLM, ALM },
};
