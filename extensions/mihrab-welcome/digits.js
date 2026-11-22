"use strict";
/**
 * الأرقامُ الهنديّة: عرضًا في أسطحنا، **لا** في أرقام الأسطر [TY-06]. وحدةٌ نقيّة.
 *
 * ## الحدُّ التصميميُّ الذي يجعلها آمنة
 * ثمّة فرقٌ جوهريٌّ بين **رقمٍ للعرض** و**رقمٍ للتعامل**:
 *   • **رقمُ التعامل** — رقمُ السطر — ليس زينة: يُنسَخ إلى بلاغِ عطب، ويُطابَق بـ
 *     `problemMatcher`، ويُكتَب في `file.txt:19:1`، ويُقارَن بمخرَج المصرِّف. فتحويلُه إلى
 *     «‏١٩» **يكسر السلسلةَ كلَّها**.
 *   • **رقمُ العرض** — عدّادُ نتائج البحث، شارةُ الأنشطة، ترقيمُ سطرٍ في لوحة المخرجات —
 *     لا يُقارَن بشيءٍ ولا يُنسَخ إلى أداة.
 *
 * ولذلك: هذه الوحدةُ **لا تُستدعى على أرقام الأسطر أبدًا**، والإعدادُ الذي يقودها **مطفأٌ
 * افتراضيًّا**، ونطاقُه أسطحُ إضافاتنا وحدَها.
 *
 * ## وسابقةٌ مدفوعةُ الثمن
 * القاعدةُ ٣٠ في ورقتنا وُلِدت أصلًا من عطبِ أرقامٍ مجاورةٍ للعربيّة: «‏٣ من ١٤٦» صارت
 * «‏٣ ١٤٦ من». فبابُ الأرقام **مزلقةٌ مثبَتة** — ولذلك يعزل التحويلُ كلَّ عددٍ يحوّله.
 */

/** مفتاحُ الإعداد الذي يقود العرض — مطفأٌ افتراضيًّا. */
const SETTING = "mihrab.display.arabicIndicDigits";
const AR_INDIC_ZERO = 0x0660;
const ASCII_ZERO = 0x30;
/** عزلٌ اتّجاهيّ (`FSI…PDI`) حول كلّ عددٍ محوَّل — درسُ القاعدة ٣٠. */
const FSI = "⁨";
const PDI = "⁩";

/**
 * يحوّل الأرقامَ اللاتينيّةَ في نصٍّ إلى عربيّةٍ-هنديّة، **معزولةً اتّجاهيًّا**.
 * @param {string} text @returns {string}
 */
function toArabicIndic(text) {
  if (typeof text !== "string" || !text) return "";
  return text.replace(/\d+/g, (run) => {
    let out = "";
    for (const d of run) out += String.fromCharCode(AR_INDIC_ZERO + (d.charCodeAt(0) - ASCII_ZERO));
    return FSI + out + PDI;
  });
}

/**
 * يطبّق التحويلَ **بشرط الإعداد**. الدالّةُ الوحيدةُ التي تُستدعى من أسطح العرض، كي يبقى
 * الشرطُ في موضعٍ واحدٍ لا مبعثرًا في كلّ نداء.
 * @param {string} text @param {boolean} enabled
 */
function formatDigits(text, enabled) {
  return enabled ? toArabicIndic(text) : String(text == null ? "" : text);
}

module.exports = { toArabicIndic, formatDigits, SETTING, AR_INDIC_ZERO, FSI, PDI };
