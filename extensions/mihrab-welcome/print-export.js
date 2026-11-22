"use strict";
/**
 * تصديرٌ إلى HTML للطباعة [PR-01] — وحدةٌ **نقيّة** بلا `vscode` (تُختبَر وحدويًّا).
 *
 * ## لماذا وُجد
 * محارفُ الاتّجاه الخفيّة تجعل الشيفرةَ **تُقرَأ بترتيبٍ غيرِ الذي تُنفَّذ به**، ومحرابٌ
 * يمسكها على الشاشة بثلاث طبقات (‏`bidi-scan` · `bidi-decorate` · `bidi-guard`). لكنّ
 * **الورقةَ لا تحمل شيئًا من ذلك**: لا زخرفةً ولا تحويمًا ولا لونًا. فمراجعةٌ تُجرى على
 * ورقٍ — وهي أكثرُ ما تُجرى عليه المراجعاتُ الرسميّة — تفقد كلَّ ما بناه محراب.
 * وهذا الأمرُ يُعيده: يجعل الخفيَّ **حبرًا**.
 *
 * ## طبقتان، وكسرُ الأمانة **مقصودٌ في واحدةٍ منهما وحدَها**
 *   • **المرئيّ**: يُستبدَل بكلّ محرفِ اتّجاهٍ رقاقةٌ `⟪RLO⟫` في موضعه بالضبط. فالطبقةُ
 *     المرئيّةُ **ليست أمينةً للنصّ عمدًا** — وهذا هو البند.
 *   • **`data-src` لكلّ سطر**: النصُّ الأصليُّ حرفًا بحرف، **بالمحارف مهرَّبةً `\\u202E`
 *     نصًّا** لا خامًا. فيبقى الاستخراجُ حتميًّا، **ويبقى الملفُّ كلُّه خاليًا من أيِّ
 *     محرفِ اتّجاهٍ خام** — بما فيه السمات.
 *
 * ولماذا تُصان الأمانة أصلًا: الورقةُ المطبوعةُ **دليلُ مراجعة**. تصديرٌ يُنقّي بصمتٍ
 * يحوّل هذا الأمرَ إلى **غسّالةِ هجوم**: يراجع الفريقُ ورقةً نظيفةً ويوقّع على ملفٍّ ملغوم.
 * فالتعليمُ يُظهِر، ولا يحذف.
 *
 * ## `unicode-bidi: plaintext` لا `isolate`
 *   • `isolate` يعزل **ويرث اتّجاهَ الحاوية** (‏RTL هنا) ⇒ سطرٌ يبدأ بلاتينيّةٍ يُصفّ يمينًا.
 *   • `<bdi>` عنصرٌ **سطريّ** — خطأُ بنيةٍ لسطرِ شيفرة.
 *   • `plaintext` = عزلٌ + اتّجاهٌ من أوّلِ حرفٍ قويّ = دلالةُ `FSI` بالضبط.
 * وهو ما استقرّ عليه المستودعُ مرّتين قبل هذا الملفّ (`clipboard-safety.js:49` تعليلًا،
 * ولوحةُ مخرجاتٍ أُزيلت لاحقًا تنفيذًا). ولا يُستعمَل `isolateForSharing` هنا: يُدخِل `FSI…PDI`
 * **خامًّا** فينقض تعهُّدَ «لا محرفَ اتّجاهٍ خامٍّ في الخرج». العزلُ في HTML مهمّةُ CSS.
 *
 * ## أرقامٌ غربيّة [TY-06]
 * أرقامُ الأسطر هنا **سطحُ تعامل** لا عرض: تُقارَن في المراجعة برقمِ سطرٍ في المحرّر
 * وبمخرَج المصرِّف. فلا تُحوَّل بـ`formatDigits` — وهو الحدُّ نفسُه المرسومُ في `digits.js`.
 *
 * ## والخطُّ مُضمَّنٌ دائمًا، بلا إعداد
 * خيارُ «بلا خطّ» يبيع الوعدَ كلَّه: من يُطفئه يصدّر ملفًّا يبدو سليمًا عنده ويُطبَع
 * بخطٍّ لاتينيٍّ عند غيره. وغيابُ الخطّ **يُفشِل الأمر** (`bundled-font.js`، سياسةُ
 * `required` ومُعلَّلةٌ هناك).
 */

const { listBidiChars, CHAR_NAMES } = require("./bidi-scan");
const { FONT_FAMILY } = require("./bundled-font");
// تمييزُ العدد: مصدرٌ واحدٌ في المستودع (`clipboard-safety.js:80`) لا نسخةٌ ثانيةٌ تنجرف.
const { arCount } = require("./clipboard-safety");

/** الرقاقةُ نفسُها التي تُعرَض على الشاشة (`bidi-decorate.js:63`) — كي تتطابق الورقةُ والشاشة. */
const CHIP = (code) => `⟪${code}⟫`;

const COPY = {
  title: (name) => `${name} — نسخةٌ للطباعة`,
  legendHead: "محارفُ الاتّجاه الخفيّة في هذا الملفّ",
  legendNote:
    "هذه المحارفُ لا تُرسَم على الشاشة، وهي تغيّر ترتيبَ قراءةِ النصّ دون أن تغيّر ما يُنفَّذ. "
    + "عُلِّم كلٌّ منها هنا في موضعه بالضبط. والنصُّ الأصليُّ محفوظٌ حرفًا بحرف في سمة "
    + "«data-src» لكلّ سطر.",
  none: "لا محرفَ اتّجاهٍ خفيًّا في هذا الملفّ.",
  noneNote: "فُحص الملفُّ كلُّه ولم يُعثَر على شيء — وهذا خبرٌ، لا غيابُ فحص.",
  printBtn: "اطبع",
  colChar: "المحرف", colName: "معناه", colCount: "مرّاته",
  colKind: "صنفُه", colWhere: "أسطرُه",
  kindMark: "ضبطٌ مشروع", kindOverride: "تجاوزٌ — يُراجَع",
  kindsNote:
    "العلاماتُ المفردةُ ضبطٌ شائعٌ ومستحسَنٌ في النصّ العربيّ، ولا تُقلب بها قراءةُ سطر. "
    + "أمّا التجاوزاتُ والعوازلُ فهي التي يُبنى بها إخفاءُ الشيفرة — فهذه تُراجَع بعينها. "
    + "و«أسطرُه» تُحيل إلى أرقام الأسطر أعلاه؛ ما لا رقمَ له فهو في اسم الملفّ.",
  // «‎3‎ سطرًا» عددٌ غيرُ مصروف: ‎٣–١٠‎ جمعُ قلّةٍ مجرور. والحالةُ الغالبةُ هنا صغيرة.
  footer: (n, when) => `صُدِّر من محراب · ${arCount(n, "سطرٌ واحدٌ", "سطران", "أسطرٍ", "سطرًا")} · ${when}`,
};

/** محارفُ الاتّجاه كلُّها — مشتقّةٌ من `CHAR_NAMES` كي لا تكون قائمةً ثانيةً تنجرف. */
const BIDI_RE = new RegExp("[" + [...CHAR_NAMES.keys()].map(cp => "\\u" + cp.toString(16).padStart(4, "0")).join("") + "]", "g");

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/**
 * يُهرِّب **كلَّ** محرفِ اتّجاهٍ إلى `\uXXXX` نصًّا. هذا ما يجعل تعهُّدَ «لا محرفَ اتّجاهٍ
 * خامٍّ في الملفّ» صحيحًا على السمات أيضًا، ويُبقي الاستخراجَ حتميًّا (‏`unescapeSrc` عكسُها).
 *
 * ## ولماذا تُهرَّب الشرطةُ المائلةُ أوّلًا
 * كانت لا تُهرَّب، فلم تكن الدالّةُ **متباينة**: مصدرٌ فيه `U+202E` خامٌّ ومصدرٌ فيه النصُّ
 * الحرفيُّ `‮` (ستّةُ محارفِ ASCII — وهو في كلّ ملفٍّ يشرح Trojan Source) يُنتجان
 * `data-src` **متطابقًا**. فكان الملفُّ الثاني يُصدَّر بـ«‏٠ رقاقة · لا محرفَ اتّجاه»
 * — وهو صادقٌ — ثمّ **يُنتج الاستخراجُ منه محرفَ RLO خامًّا لم يوجد في الأصل**.
 * أي أنّ الورقةَ تُبرّئ ملفًّا نظيفًا وتُسلّم مراجعَها أصلًا ملغومًا.
 *
 * والترتيبُ ملزِم: `\` ⇒ `\\` **قبل** كتابة `\uXXXX`، وإلّا هُرِّبت الشرطةُ التي كتبناها نحن.
 */
function escapeSrc(line) {
  return escapeHtml(
    String(line)
      .replace(/\\/g, "\\\\")
      .replace(BIDI_RE, c => "\\u" + c.charCodeAt(0).toString(16).toUpperCase().padStart(4, "0")));
}

/**
 * عكسُ `escapeSrc` على النصّ الخام (بعد فكّ HTML). مُصدَّرةٌ لأنّ الأمانةَ تُختبَر بها.
 *
 * **مُبدِّلٌ واحدٌ بتبادُل**، لا مرّتان: فكُّ `\\` ثمّ فكُّ `\uXXXX` يحوّل `\\u202E`
 * (شرطةٌ حرفيّةٌ متبوعةٌ بالنصّ) إلى `‮` ثمّ إلى المحرف — وهو العطبُ نفسُه بخطوةٍ أبعد.
 * المرورُ الواحدُ يستهلك كلَّ تسلسلٍ مرّةً فلا يُعاد قراءةُ ما فُكّ.
 */
function unescapeSrc(s) {
  return String(s).replace(/\\\\|\\u([0-9A-Fa-f]{4})/g,
    (m, h) => (h === undefined ? "\\" : String.fromCharCode(parseInt(h, 16))));
}

/**
 * يبني سطرًا مرئيًّا: نصٌّ مُهرَّبٌ للـHTML، وكلُّ محرفِ اتّجاهٍ يصير رقاقةً في موضعه.
 * البناءُ **بالموضع** لا بالاستبدال العامّ: `String.replace` يفقد ترتيبَ المحارف المتماثلة
 * ويصعب ربطُه بـ`listBidiChars`، والتأكيدُ «رمزُ الرقاقة = رمزُ المحرف في موضعه» يشترط الربط.
 */
function renderLine(line) {
  let out = "", buf = "";
  for (const ch of line) {
    const info = CHAR_NAMES.get(ch.codePointAt(0));
    if (info) {
      if (buf) { out += escapeHtml(buf); buf = ""; }
      out += `<mark class="bidi" data-code="${info.code}" title="${escapeHtml(info.ar)}">${escapeHtml(CHIP(info.code))}</mark>`;
    } else buf += ch;
  }
  if (buf) out += escapeHtml(buf);
  return out;
}

/**
 * نصٌّ مسطَّحٌ بلا وسوم: كلُّ محرفِ اتّجاهٍ يصير `⟪RLO⟫` حروفًا.
 * لـ`<title>`، فهو **لا يقبل وسمًا** — لا `<mark>` فيه — ومع ذلك يُعرَض في شريط
 * النافذة وفي اسم علامة التبويب وفي رأس الصفحة المطبوعة، فتركُ المحرفِ فيه خامًّا
 * يُبقي القلبَ في السطح الوحيد الذي يقرؤه المستخدمُ قبل أن يفتح الملفّ.
 */
function chipText(s) {
  return String(s).replace(BIDI_RE, c => CHIP(CHAR_NAMES.get(c.codePointAt(0)).code));
}

/**
 * @param {string} source نصُّ الملفّ
 * @param {{ fileName?: string, fontDataUri: string, exportedAt?: string }} opts
 *        `fontDataUri` **إلزاميّ**: بلا خطٍّ لا تصدير (انظر رأسَ الملفّ).
 * @returns {string} مستندُ HTML كاملٌ ومستقلٌّ بذاته
 */
function buildPrintHtml(source, opts = {}) {
  if (typeof source !== "string") throw new TypeError("buildPrintHtml: المصدرُ نصٌّ");
  // **الشكلُ كلُّه لا البادئةُ وحدَها.** القيمةُ تُسقَط خامّةً في `url("…")`، ففحصُ البادئة
  // يقبل `data:font/woff2;base64,AA") } mark.bidi { display: none } @font-face { src: url("`
  // — فتخرج ورقةٌ **بلا رقاقةٍ واحدة** وحاشيتُها تعدّد المحارف. وهي «غسّالةُ الهجوم» بعينها
  // التي وُجد هذا الملفّ ليمنعها. والدالّةُ نقيّةٌ ومُصدَّرة، فمُنتِجُ القيمة ليس واحدًا للأبد.
  if (typeof opts.fontDataUri !== "string" || !/^data:font\/woff2;base64,[A-Za-z0-9+/]+={0,2}$/.test(opts.fontDataUri))
    throw new Error("buildPrintHtml: لا خطَّ مُضمَّنًا — التصديرُ بلا خطٍّ يُخفي العطبَ ولا يمنعه");

  const name = opts.fileName || "بلا اسم";
  // السطرُ الأخيرُ الفارغُ من `\n` الختاميّة **يُبقى عمدًا**. رُوجع هذا وقيل إنّه يزيد
  // واحدًا على المحرّر — وهو عكسُ الحقيقة: `TextDocument.lineCount` في VS Code لنصٍّ
  // ينتهي بسطرٍ جديدٍ يعدّ السطرَ الفارغَ الأخير (يستقرّ المؤشّرُ عليه)، فحذفُه هو الذي
  // كان **يُنقِص** واحدًا. وأرقامُ الأسطر هنا وُضعت لتُطابق المحرّرَ [TY-06]، فتُطابقه.
  const lines = source.split(/\r\n|\r|\n/);
  const found = listBidiChars(source);
  // **واسمُ الملفّ يُفحَص كما يُفحَص متنُه.** كان يمرّ بـ`escapeHtml` وحدَها — وهي لا تمسّ
  // محارفَ الاتّجاه — فملفٌّ اسمُه `report‹RLO›cod.txt` كان يُعرَض مقلوبًا في الترويسة
  // **وتحته حاشيةٌ تقول «لا محرفَ اتّجاهٍ خفيًّا في هذا الملفّ»**. أي أنّ الورقةَ تشهد
  // بالبراءة لِما تعرضه هي مقلوبًا. وإخفاءُ الاسم هو الهجومُ الأوّلُ في Trojan Source.
  const foundInName = listBidiChars(name);

  // الحاشيةُ تصف **هذا المستندَ** لا كلَّ يونيكود: قائمةٌ ثابتةٌ تشرح اثني عشرَ محرفًا في
  // ملفٍّ فيه واحدٌ تمرّ «الحاشيةُ موجودة» وتكذب على القارئ فتُعلِّمه أنّ في ورقته ما ليس فيها.
  // و`isMark` **لا يُرمى**: `bidi-scan.js` يُرجعه لأنّ العلاماتِ المفردةَ (‏RLM/LRM/ALM)
  // ضبطٌ **مشروعٌ ومستحسَنٌ** في نصٍّ عربيّ، والتجاوزاتِ (‏RLO/LRO/PDF…) هي أداةُ الهجوم.
  // فحاشيةٌ تسوّي بينهما تُنذِر حيث لا شيء وتُهدِّئ حيث الخطر — وتُخرِج الورقتين بنبرةٍ
  // واحدة. عمودٌ ثالثٌ يفرزهما بلا كلفة، والمراجعُ يقرأ الفرقَ لا يخمّنه.
  const tally = new Map();
  // محارفُ الاسم بلا رقم سطر: «سطر ١» لها يوهم أنّها في المتن. تُعدّ ولا تُنسَب.
  for (const f of [...foundInName.map(f => ({ ...f, line: null })), ...found]) {
    const e = tally.get(f.code) || { code: f.code, nameAr: f.nameAr, isMark: f.isMark, count: 0, where: [] };
    e.count++;
    // ‏`listBidiChars` يعدّ الأسطر **من صفر**، والمِسطرةُ تعرضها من واحد. فيُزاد واحدٌ
    // هنا وإلّا أحال العمودُ إلى السطر السابق لموضع المحرف. و`!= null` لا `truthy`:
    // السطرُ الأوّلُ رقمُه `0` فيسقط بالشرط الكاذب — وهو أكثرُ الأسطر إصابةً.
    if (e.where.length < 6 && f.line != null) e.where.push(f.line + 1);
    tally.set(f.code, e);
  }
  const legend = [...tally.values()].sort((a, b) => a.code.localeCompare(b.code));

  const body = lines.map((ln, i) =>
    `<div class="row"><span class="num">${i + 1}</span>`
    + `<code class="line" data-src="${escapeSrc(ln)}">${renderLine(ln)}</code></div>`
  ).join("\n");

  const legendHtml = legend.length
    ? `<section class="legend">
  <h2>${escapeHtml(COPY.legendHead)}</h2>
  <p>${escapeHtml(COPY.legendNote)}</p>
  <table><thead><tr><th>${COPY.colChar}</th><th>${COPY.colName}</th><th>${COPY.colKind}</th><th>${COPY.colCount}</th><th>${COPY.colWhere}</th></tr></thead><tbody>
${legend.map(e => `    <tr><td><code>${escapeHtml(CHIP(e.code))}</code></td><td>${escapeHtml(e.nameAr)}</td>`
      + `<td class="${e.isMark ? "kind-ok" : "kind-risk"}">${escapeHtml(e.isMark ? COPY.kindMark : COPY.kindOverride)}</td>`
      + `<td>${e.count}</td><td class="lines">${e.where.length ? e.where.join("، ") + (e.count > e.where.length ? " …" : "") : "—"}</td></tr>`).join("\n")}
  </tbody></table>
  <p class="kinds">${escapeHtml(COPY.kindsNote)}</p>
</section>`
    : `<section class="legend none"><h2>${escapeHtml(COPY.none)}</h2><p>${escapeHtml(COPY.noneNote)}</p></section>`;

  // **لا محرفَ اتّجاهٍ في هذا القالب نفسِه.** تعليقاتُ CSS هنا عربيّةٌ، وكتابةُ العربيّةِ
  // بجانبِ اللاتينيّةِ تُغري بإدراج RLM لضبطِ الرسم — وقد وقع ذلك فعلًا وأمسكه التأكيدُ
  // الأوّل: تسرّب U+200F من تعليقٍ في هذا الملفّ إلى الخرج. فالتعهُّدُ يشمل القالبَ لا
  // مدخلاتِ المستخدم وحدَها، والحارسُ هو ما جعله صحيحًا لا الانتباه.
  return `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>${escapeHtml(chipText(COPY.title(name)))}</title>
<style>
  /* الخطُّ مُضمَّنٌ data: — الملفُّ يُطبَع كما هو حيثما ذهب، بلا خطٍّ مثبَّتٍ عند القارئ.
     قِيس بطباعةٍ فعليّة إلى PDF: يُدرَج مجزّأً مع ToUnicode ⇒ النصُّ يبقى مستخرَجًا وقابلًا للبحث. */
  @font-face { font-family: "${FONT_FAMILY}"; font-style: normal; font-weight: 400;
               src: url("${opts.fontDataUri}") format("woff2"); }
  :root { color-scheme: light; }
  /* **الخطُّ يُفرَض على العناصر لا يُترَك للوراثة.** «code» و«mark» تحملان من ورقةِ الوكيل
     «font-family: monospace» — وهي قاعدةُ عنصرٍ تغلب الوراثةَ من «body». فأوّلُ صياغةٍ
     ضبطت الخطَّ على «body» وحدَه، وكان الخطُّ يُضمَّن ولا يُستعمَل: قِيست طباعةٌ فعليّةٌ
     إلى PDF فجاءت بـConsolas وTimes، و١٤٥ ك.ب محمولةٌ بلا أثر. ولا يمسك هذا تأكيدٌ على
     «الخطُّ مُضمَّن» — الحمولةُ كانت حاضرةً كاملةً. */
  body, code, mark, .line, .num { font-family: "${FONT_FAMILY}", "Noto Sans Arabic", monospace; }
  body { margin: 2rem; background: #fff; color: #111;
         /* المدى العربيّ الفعليّ 1.798em (patches/fonts/README.md) — وأقلُّ منه يقتطع التشكيل. */
         line-height: 1.8; }
  h1 { font-size: 1.1rem; border-bottom: 1px solid #ccc; padding-bottom: .5rem; }
  .row { display: flex; align-items: baseline; gap: .75rem; }
  /* أرقامُ الأسطر **غربيّةٌ عمدًا** [TY-06]: سطحُ تعاملٍ يُقارَن برقم سطرٍ في المحرّر
     وبمخرَج المصرِّف، لا سطحُ عرضٍ يُزيَّن. و«direction: ltr» كي لا تنقلب. */
  .num { direction: ltr; unicode-bidi: isolate; min-width: 3.5ch; text-align: end;
         color: #888; font-size: .85em; user-select: none; }
  /* جوهرُ العزل: **لكلِّ سطرٍ اتّجاهُه من أوّل حرفٍ قويٍّ فيه**، ولا يتسرّب إلى ما بعده.
     «plaintext» لا «isolate»: الثاني يرث اتّجاهَ الحاوية فيَصُفّ سطرًا لاتينيَّ البدء يمينًا. */
  .line { unicode-bidi: plaintext; text-align: start; white-space: pre-wrap;
          word-break: break-word; flex: 1; }
  /* الرقاقةُ حبرٌ لا لون: الطباعةُ قد تكون بالأسود وحدَه، فالإطارُ والوزنُ هما ما يبقى. */
  /* «direction: ltr» ليست زينة: قوسا الرقاقة (U+27EA/27EB) «Bidi_Mirrored» — والعزلُ
     وحدَه يرث اتّجاهَ الفقرة، وفقراتُ الأسطر تختلف اتّجاهًا بـ«plaintext». فبلا هذا
     السطر ينقلب القوسان بين سطرٍ وسطرٍ من الورقة نفسِها فتُقرأ الرقاقةُ شيئين.
     (ولا يُكتَب هنا مثالٌ حرفيٌّ للرقاقة: تأكيدُ «الحاشيةُ = ما في المستند» يقرأ
      الخرجَ كلَّه، فرمزٌ في تعليقٍ يُقرأ ذِكرًا لمحرفٍ غيرِ موجود — وقد أمسكه فعلًا.) */
  mark.bidi { direction: ltr; background: #ffe9a8; border: 1px solid #b07d00; border-radius: .25em;
              padding: 0 .15em; font-weight: 700; font-size: .85em;
              unicode-bidi: isolate; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .legend { margin-top: 2rem; border-top: 2px solid #333; padding-top: 1rem; break-inside: avoid; }
  .legend h2 { font-size: 1rem; }
  .legend table { border-collapse: collapse; }
  .legend td, .legend th { border: 1px solid #bbb; padding: .3rem .6rem; text-align: start; }
  /* الفرزُ **حبرٌ لا لون**: الورقةُ قد تُطبَع بالأسود وحدَه، فالوزنُ هو ما يبقى. */
  .legend .kind-risk { font-weight: 700; }
  .legend .kind-ok { color: #555; }
  .legend .kinds { font-size: .85em; color: #444; max-width: 46em; }
  /* أرقامُ الأسطر في الحاشية غربيّةٌ ومعزولةٌ كنظيراتها في المِسطرة [TY-06] — و«num»
     لا تصلح هنا: فيها «user-select: none» وعرضٌ أدنى، وهما لعمودِ المِسطرة لا لخليّة. */
  .legend .lines { direction: ltr; unicode-bidi: isolate; text-align: start; }
  .foot { margin-top: 1.5rem; color: #666; font-size: .8em; }
  button.print { margin-bottom: 1rem; padding: .4rem 1rem; font: inherit; cursor: pointer; }
  /* الطباعةُ عملُ المتصفّح: VS Code لا واجهةَ طباعةٍ فيها، و«window.print()» في webview
     يتّكئ على سلوكِ إلكترون غيرِ الموثَّق. فالزرُّ **داخل الصفحة** حيث المتصفّحُ حقيقيّ. */
  @media print { button.print { display: none; } body { margin: 0; } .row { break-inside: avoid; } }
</style>
</head>
<body>
<button class="print" onclick="window.print()">${escapeHtml(COPY.printBtn)}</button>
<h1 class="line">${renderLine(name)}</h1>
<main>
${body}
</main>
${legendHtml}
<p class="foot">${escapeHtml(COPY.footer(lines.length, opts.exportedAt || ""))}</p>
</body>
</html>
`;
}

module.exports = { buildPrintHtml, escapeSrc, unescapeSrc, renderLine, CHIP, COPY, BIDI_RE };
