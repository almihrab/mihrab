"use strict";
/**
 * تحقّقُ أسماء المدخلات — وحدةٌ نقيّةٌ مشتركة [BS-03].
 *
 * ## لماذا اسْتُخرِجت
 * كان المنطقُ حبيسَ أمرِ «مشروعٍ جديد» (أُزيل في 2026-11-22): **حارسٌ ممتازٌ في نقطةٍ واحدة**.
 * وإنشاءُ ملفٍّ أو إعادةُ تسميةٍ لا يمرّان به. والانتحالُ في اسم **الملفّ** أخطرُ منه في اسم المشروع، لأنّ
 * الملفَّ يُستورَد: ملفّان يبدوان في المستكشف بالاسم نفسِه ويُحلَّان إلى مسارَين مختلفَين.
 *
 * والقاعدةُ ٢١ في ورقتنا تعالج **عرضَ** اسم الملفّ بـ`plaintext` — وذاك عزلُ عرضٍ لا منعُ
 * إنشاء. فالمدخلُ كان **محروسًا في بابٍ ومفتوحًا في بابٍ أوسع**.
 *
 * ## ولماذا لا يُطبَّع الاسمُ هنا
 * `arabic-normalize.js` يوحّد «أ» و«ا» قصدًا — وهذا **نقيضُ** المطلوب في الهويّة: هناك
 * المطلوبُ **كشفُ** التشابه لا توحيدُه. فالوحدتان متعاكستان عمدًا، ولا تُستعمَل إحداهما
 * مكانَ الأخرى.
 */

// محارفٌ ممنوعة: رموزُ نظام الملفّات + محارفُ تحكّم C0/DEL/C1 + محارفُ التحكّم ثنائيّةِ
// الاتّجاه (علامتان، تضمينٌ/تجاوزٌ، عزل) — الأخيرةُ تُنتج اسمًا مخادعًا بصريًّا في سياق RTL.
// (نقاطُ الرموز بترميز \u صريح — لا محرفَ غيرَ مرئيٍّ في الكود نفسِه.)
const INVALID_NAME_RE = /[\\\/:*?"<>|\x00-\x1f\x7f-\x9f\u200B-\u200F\u061C\u202A-\u202E\u2066-\u2069]/;
/** المحارفُ الخفيّةُ وحدَها — تُفصَل كي تُسمّى في الرسالة (رسالةٌ تُسمّي أنفعُ من رسالةٍ تلوم). */
const BIDI_SPOOF_RE = /[\u200B-\u200F\u061C\u202A-\u202E\u2066-\u2069]/;
/** أقصى طولٍ لاسم مدخلٍ في معظم أنظمة الملفّات. */
const MAX_NAME_LEN = 255;
/** أسماءٌ محجوزةٌ على ويندوز (بلا/مع امتداد) — تُقارَن دون حساسيّة حالة. */
const RESERVED_NAMES = new Set([
  "con", "prn", "aux", "nul",
  "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
  "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
]);

/** أسبابُ الرفض — رموزٌ لا نصوص: النصُّ شأنُ من يعرض، والسببُ شأنُ من يفحص. */
const REASON = {
  EMPTY: "empty",
  TOO_LONG: "tooLong",
  DOT_NAMES: "dotNames",
  INVALID_CHARS: "invalidChars",
  BIDI_SPOOF: "bidiSpoof",
  TRAILING_DOT_SPACE: "trailingDotSpace",
  RESERVED: "reserved",
};

/**
 * يفحص اسمَ مدخلٍ (ملفٍّ أو مجلّد). يعيد `null` إن صحّ، أو `{reason, chars?}`.
 *
 * ‏`chars` تُملأ لسبب الانتحال وحدَه: أسماءُ المحارف الخفيّة تُعرَض للمستخدم كي يعرف **ما
 * الذي يُزال**، فلا يكون قرارُه عشوائيًّا (المبدأ نفسه في `BS-02`).
 * @param {string} v @returns {{reason:string, chars?:string[]}|null}
 */
function checkName(v) {
  const t = (v || "").trim();
  if (!t) return { reason: REASON.EMPTY };
  if (t.length > MAX_NAME_LEN) return { reason: REASON.TOO_LONG };
  if (t === "." || t === "..") return { reason: REASON.DOT_NAMES };
  if (BIDI_SPOOF_RE.test(t)) {
    const chars = [];
    for (const ch of t) {
      if (BIDI_SPOOF_RE.test(ch)) {
        const hex = ch.codePointAt(0).toString(16).toUpperCase().padStart(4, "0");
        if (!chars.includes("U+" + hex)) chars.push("U+" + hex);
      }
    }
    return { reason: REASON.BIDI_SPOOF, chars };
  }
  if (INVALID_NAME_RE.test(t)) return { reason: REASON.INVALID_CHARS };
  if (/[. ]$/.test(t)) return { reason: REASON.TRAILING_DOT_SPACE };
  if (RESERVED_NAMES.has(t.split(".")[0].toLowerCase())) return { reason: REASON.RESERVED };
  return null;
}

/** يزيل محارفَ الانتحال من اسمٍ (إصلاحٌ بنقرةٍ واحدة). لا يمسّ ما عداها. */
function stripSpoofChars(v) {
  return String(v == null ? "" : v).replace(new RegExp(BIDI_SPOOF_RE.source, "g"), "");
}

module.exports = {
  checkName,
  stripSpoofChars,
  REASON,
  INVALID_NAME_RE,
  BIDI_SPOOF_RE,
  MAX_NAME_LEN,
  RESERVED_NAMES,
};
