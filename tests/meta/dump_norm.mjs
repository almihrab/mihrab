// اختيارُ سطور الفشل وتطبيعُها — دوالُّ نقيّةٌ يستعملها حارسُ الحرّاس [PF-03] (`mutation.mjs`).
//
// منفصلةٌ عنه لتُختبَر وحدَها (`dump_norm.test.mjs`): حارسُ الحرّاس لا يحرس نفسَه — تشغيلُه
// من داخله يصطدم بقفله. و`--dump-failures` أداةُ إثبات: تطبيعٌ يبتلع فرقًا حقيقيًّا يجعل
// تفريغين مختلفين «متطابقين»، وتطبيعٌ يترك ضجيجًا يجعل كلَّ مقارنةٍ حمراء فتُهمَل.

// **سطورُ الفشل تُختار ولا يُسقَط ما سواها.** إسقاطُ سطور النجاح (✅/✔/ok) كان يُبقي
// كلَّ ما لم يُتوقَّع: ‏`node --test` يطبع `# Subtest: <الاسم>` لكلّ اختبارٍ **ناجح**، ولافتةُ
// ‏`╚══ ✅ … (سقفًا وأرضيّة) ══╝` لا تبدأ بـ✅، وسطورُ ⏭️ و⚠️ — فيطابقها `expect` والفحصُ لم يحمرّ.
// فالمختارُ: سطرٌ يحمل علامةَ فشل، وما تحته من سطورٍ أعمقَ إزاحةً (تفصيلُه، وكتلةُ YAML
// تحت `not ok` في TAP، وجسمُ `Traceback`).
export const PASS_LINE = /^\s*(✅|✔|ok\b|# Subtest:)/;
export const FAIL_MARK = /❌|✗|✖|^\s*not ok\b|^\s*FAIL\b|Traceback \(most recent call last\)|\b\w*(Error|Exception)\b/;
const indent = l => l.match(/^\s*/)[0].length;

// **والسطرُ الفارغ لا يقطع التفصيل** ما دام ما بعده أعمق: كتلةُ YAML في TAP تفصل
// `+ actual - expected` عن القيمتين بسطرٍ من مسافات، فكان القطعُ عنده يُسقط القيمتين ونصَّ
// الرسالة كلَّه — ورسالتان مختلفتان تمامًا تعطيان تفريغًا واحدًا (قِيس).
// و**‏`stack:` يُسقَط** بما تحته: سطورُ `node:internal/…:1047:25` تتبع نسخةَ node لا الحارس.
const STACK = /^\s*stack:\s*\|?-?\s*$/;
export const failureText = (out) => {
  const lines = out.split("\n").map(l => l.replace(/\r$/, ""));
  const keep = [];
  const nextDeep = (j, base) => {             // أوّلُ سطرٍ غيرِ فارغٍ من j أعمقُ من base؟
    while (j < lines.length && !lines[j].trim()) j++;
    return j < lines.length && indent(lines[j]) > base;
  };
  for (let i = 0; i < lines.length; i++) {
    if (PASS_LINE.test(lines[i]) || !FAIL_MARK.test(lines[i])) continue;
    const base = indent(lines[i]);
    keep.push(lines[i]);
    while (i + 1 < lines.length && nextDeep(i + 1, base)) {
      const l = lines[++i];
      if (STACK.test(l)) {                    // تخطَّ الكتلةَ كلَّها
        const sb = indent(l);
        while (i + 1 < lines.length && (!lines[i + 1].trim() || indent(lines[i + 1]) > sb) && nextDeep(i + 1, sb)) i++;
        continue;
      }
      keep.push(l.trim() ? l : "");
    }
  }
  return keep.join("\n");
};

// ذيلُ الخرج بديلًا حين لا علامةَ فشل (‏`sys.exit("…")` مثلًا): بلاه يُكتب للمُصاب ملفٌّ
// فارغٌ قبل التغيير وبعده فيتطابقان مهما تغيّرت رسالتُه.
export const tail = (out, n = 3) => out.split("\n").filter(l => l.trim()).slice(-n);

// مسارٌ نصًّا مُهرَّبًا لتعبيرٍ نمطيّ، وكلُّ فاصلٍ فيه يطابق **أيَّ عددٍ** من `\` و`/`:
// ‏`%r` في بايثون وحقلُ `location` في TAP يطبعان `C:\\Users\\…` بشرطتين.
export const escRe = p => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\\\\|\//g, "[\\\\/]+");

// ⇒ دالّةُ تطبيعٍ لجذرٍ ومؤقّتٍ بعينهما. الترتيبُ مقصود: الجذرُ أوّلًا (قد يقع داخل المؤقّت).
// ‏`gi`: حرفُ القرص يُطبع `c:` و`C:` بحسب من حسبه. و**المسارُ مرسًى**: لا يُطبَّع إن سبقه
// حرفُ اسم — ‏`tmpdir()` على لينكس `/tmp`، فبلا مرساةٍ يصير `/home/x/tmp/y` ‏`/home/x<TMP>`.
// (والفاصلُ قبله مقبول: ‏`file:///C:/…` في مكدّس node.)
const ANCHOR = "(?<![\\w.-])";
export const makeNorm = (root, tmp) => {
  const ROOT_RE = new RegExp(ANCHOR + escRe(root), "gi");
  // **مكوّنٌ واحدٌ بعد المؤقّت** (اسمُ المجلّد العشوائيّ) لا بقيّةُ المسار: ابتلاعُ البقيّة كان
  // يُطابق `…\tmpab\docs\index.html` بـ`…\tmpzz\start\index.html` — أيُّ صفحةٍ فشلت يضيع.
  const TMP_RE = new RegExp(ANCHOR + escRe(tmp) + "[\\\\/]+[^\\\\/\\s\"'»)]+", "gi");
  // وما بعد العلامة يُوحَّد فاصلُه: الحارسُ نفسُه يطبع `\` على ويندوز و`/` على غيره.
  const seps = (_, mark, rest) => mark + rest.replace(/\\+/g, "/");
  return t => t
    .replace(/\r\n/g, "\n")
    .replace(ROOT_RE, "<ROOT>")
    .replace(TMP_RE, "<TMP>")
    .replace(/(<ROOT>|<TMP>)([^\s"'»)]*)/g, seps)
    // [OUT-01] يزرع بوائتَ بأسماءٍ عشوائيّةٍ عمدًا (‏`stale-2f548b84`) كي لا يمرّ محوٌ بالاسم.
    .replace(/(stale(?:-dir|-page)?)-[0-9a-f]{8}\b/g, "$1-<RAND>")
    // ‏`node --test` يطبع زمنَ كلّ اختبارٍ تحت `not ok` — يختلف بين كلّ تشغيلين.
    .replace(/^(\s*duration_ms:).*$/gm, "$1 <T>");
};

// ⇒ ما يُكتب لمُصابٍ في `--dump-failures`: **رمزُ الخروج** ثمّ سطورُ الفشل (أو الذيل).
// انهيارٌ جديدٌ بخروج 2 بدل 1 يظهر، وحارسٌ أحمرُ بلا علامةِ فشلٍ لا يُكتب له فراغ.
export const dumpText = (res) => {
  if (res.code === null) return `‹لم ينتهِ: ${res.why}›`;
  if (res.code === 0) return "‹أخضر›";
  const fl = failureText(res.out);
  return `‹خرج ${res.code}›\n` + (fl || "‹بلا علامةِ فشل — الذيل:›\n" + tail(res.out).join("\n"));
};
