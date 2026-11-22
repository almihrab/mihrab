"use strict";
/**
 * سياقٌ عربيّ: هل في هذا النصّ حرفٌ عربيّ؟
 *
 * رسالتا الطرفيّة [DR-03] والمقارنة [DR-04] لمرّةٍ واحدةٍ للأبد، فلا تُحرَقان في غير سياقهما:
 * طرفيّةٌ تُفتَح لأمرِ `git` في مشروعٍ لاتينيّ، أو فرقُ `package.json`، ليسا اللحظةَ المقصودة.
 * والسياقُ نصٌّ عربيٌّ أمام المستخدم. يُفحَص أوّلُ جزءٍ من النصّ فقط — كلفةٌ ثابتةٌ مهما كبر.
 */

/** الحروفُ العربيّة وملحقاتُها وأشكالُ العرض (أ وب). */
const ARABIC_RE = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/;
/** أقصى ما يُفحَص من النصّ. */
const PROBE_CHARS = 20000;

/** @param {unknown} text @returns {boolean} */
function hasArabic(text) {
  return typeof text === "string" && ARABIC_RE.test(text.slice(0, PROBE_CHARS));
}

module.exports = { ARABIC_RE, PROBE_CHARS, hasArabic };
