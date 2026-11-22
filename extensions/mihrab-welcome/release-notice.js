"use strict";
/**
 * إخبارٌ بالإصدارات بعد تعطيل التحديث التلقائيّ [ON-04] — وحدةٌ نقيّةُ المنطق.
 *
 * ## لماذا
 * `updateUrl: null` تعطيلٌ **مقصودٌ ومبرَّر**: المحدِّثُ المورَّثُ كان يستبدل محرابًا بـVSCodium
 * صامتًا (عطبٌ حقيقيٌّ أبلغه مستخدم). لكنّ التعطيلَ ترك المستخدمَ **بلا أيّ إشعارٍ بإصدارٍ
 * جديد**: لا يعرف أنّ إصلاحًا لعطبٍ يواجهه صدر أمس. وأثرُ ذلك أقسى في مرحلةٍ يتغيّر فيها
 * دعمُ العربيّةِ سريعًا — فمن ثبّت بناءً قديمًا **يحكم على محرابٍ بحالةٍ تجاوزها بشهور**.
 *
 * ‏**غيابُ التحديث قرارٌ سليم؛ غيابُ الخبر ليس كذلك.**
 *
 * ## حدودٌ مقصودة
 *   ‏(١) **بإذنٍ صريحٍ أوّلَ مرّة** — انسجامًا مع موقف محرابٍ من التتبّع. الفحصُ اتّصالُ شبكةٍ،
 *       ولا يقع بلا سؤال.
 *   ‏(٢) **لا محدِّثَ ولا تنزيلَ تلقائيّ**: خبرٌ وزرُّ «افتح صفحة التنزيل» — لا أكثر.
 *   ‏(٣) **لا يُرسَل شيءٌ عنك**: طلبُ `GET` لملفٍّ ثابتٍ بلا معرّفٍ ولا بصمة.
 */

/** مفاتيحُ الحالة: الإذنُ (‏`true`/`false`/غير مسؤول) وآخرُ إصدارٍ أُخبِر عنه. */
const CONSENT_KEY = "mihrab.release.checkConsent";
const LAST_NOTIFIED_KEY = "mihrab.release.lastNotified";
/** أقلُّ فاصلٍ بين فحصَين — الأخبارُ لا تتغيّر كلَّ ساعة، والشبكةُ ليست مجّانيّةً للمستخدم. */
const MIN_INTERVAL_MS = 24 * 60 * 60 * 1000;
const LAST_CHECK_KEY = "mihrab.release.lastCheck";

const COPY = {
  ask:
    "أتأذن لمحراب بفحصِ وجود إصدارٍ أحدث؟ يقرأ ملفَّ إصداراتٍ واحدًا على موقع محراب، **ولا يُرسِل" +
    " عنك شيئًا** ولا يُنزِّل شيئًا تلقائيًّا. (المحدِّثُ التلقائيُّ معطَّلٌ عمدًا في محراب.)",
  askYes: "نعم، افحص",
  askNo: "لا، شكرًا",
  available: (v, cur) => `صدر محرابٌ ${v} (عندك ${cur}).`,
  open: "افتح صفحة التنزيل",
  later: "لاحقًا",
  upToDate: (v) => `محرابُك محدَّث (${v}).`,
  failed: "تعذّر فحصُ الإصدارات — لا شبكةَ أو الملفُّ غيرُ متاح.",
};

/**
 * يقارن رقمَي إصدارٍ رقميًّا لا نصّيًّا. `"1.121.5141"` أحدثُ من `"1.121.999"`.
 * يعيد `1` إن كان `a` أحدث، `-1` إن كان أقدم، `0` إن تساويا.
 */
function compareVersions(a, b) {
  const pa = String(a || "").split(".").map((n) => parseInt(n, 10) || 0);
  const pb = String(b || "").split(".").map((n) => parseInt(n, 10) || 0);
  const len = Math.max(pa.length, pb.length);
  for (let i = 0; i < len; i++) {
    const x = pa[i] || 0, y = pb[i] || 0;
    if (x !== y) return x > y ? 1 : -1;
  }
  return 0;
}

/**
 * هل ثمّة إصدارٌ أحدث؟ **دالّةٌ نقيّة** — تُختبَر بمانيفستٍ مصنوع.
 * @param {{version?:string}} manifest ما قُرئ من `releases.json`.
 * @param {string} current إصدارُ محرابٍ الجاري.
 * @returns {{newer:boolean, version:string|null}}
 */
function evaluateManifest(manifest, current) {
  const v = manifest && typeof manifest.version === "string" ? manifest.version : null;
  if (!v) return { newer: false, version: null };
  return { newer: compareVersions(v, current) > 0, version: v };
}

/** هل حان وقتُ فحصٍ جديد؟ (فاصلٌ أدنى — لا فحصَ في كلّ إقلاع). */
function isDue(lastCheckMs, nowMs) {
  return !lastCheckMs || nowMs - lastCheckMs >= MIN_INTERVAL_MS;
}

/**
 * المسارُ الكامل: إذنٌ ⇐ فحصٌ ⇐ خبر. مُحقَّنُ التبعيّات بالكامل (لا `fetch` ولا `Date` هنا).
 *
 * @param {*} vscode
 * @param {*} memento
 * @param {object} deps
 * @param {() => Promise<object|null>} deps.fetchManifest يجلب `releases.json` (أو `null`).
 * @param {string} deps.currentVersion
 * @param {string} deps.downloadUrl
 * @param {number} deps.now طابعُ الوقت (يُمرَّر ولا يُقرأ هنا — فتُختبَر الدالّةُ حتميًّا).
 * @param {boolean} [deps.force] تجاوزُ الفاصل الزمنيّ (استدعاءٌ يدويّ من لوحة الأوامر).
 * @returns {Promise<{checked:boolean, newer:boolean, version:string|null}>}
 */
async function checkForUpdate(vscode, memento, deps) {
  const { fetchManifest, currentVersion, downloadUrl, now, force } = deps;
  let consent = memento ? memento.get(CONSENT_KEY) : undefined;
  if (consent === undefined) {
    // **الإذنُ يُطلَب مرّةً، ويُحترَم رفضُه.** ولا يُسأل ثانيةً في كلّ إقلاع.
    const pick = await vscode.window.showInformationMessage(COPY.ask, COPY.askYes, COPY.askNo);
    if (pick === undefined) return { checked: false, newer: false, version: null }; // أُغلِق ⇒ نسأل لاحقًا
    consent = pick === COPY.askYes;
    if (memento) await memento.update(CONSENT_KEY, consent);
  }
  if (!consent) return { checked: false, newer: false, version: null };
  if (!force && memento && !isDue(memento.get(LAST_CHECK_KEY), now)) {
    return { checked: false, newer: false, version: null };
  }
  if (memento) await memento.update(LAST_CHECK_KEY, now);

  let manifest = null;
  try {
    manifest = await fetchManifest();
  } catch {
    manifest = null;
  }
  if (!manifest) {
    // الفشلُ يُقال **عند الطلب اليدويّ وحدَه**: صمتُ الفحص الدوريّ أدبٌ، وصمتُ الطلب إهمال.
    if (force) vscode.window.showWarningMessage(COPY.failed);
    return { checked: true, newer: false, version: null };
  }
  const { newer, version } = evaluateManifest(manifest, currentVersion);
  if (!newer) {
    if (force) vscode.window.showInformationMessage(COPY.upToDate(currentVersion));
    return { checked: true, newer: false, version };
  }
  // لا نُكرّر الخبرَ عن الإصدار نفسِه (إلّا بطلبٍ يدويّ).
  if (!force && memento && memento.get(LAST_NOTIFIED_KEY) === version) {
    return { checked: true, newer: true, version };
  }
  if (memento) await memento.update(LAST_NOTIFIED_KEY, version);
  const pick = await vscode.window.showInformationMessage(
    COPY.available(version, currentVersion), COPY.open, COPY.later);
  if (pick === COPY.open) {
    await vscode.env.openExternal(vscode.Uri.parse(downloadUrl));
  }
  return { checked: true, newer: true, version };
}

module.exports = {
  checkForUpdate,
  evaluateManifest,
  compareVersions,
  isDue,
  CONSENT_KEY,
  LAST_NOTIFIED_KEY,
  LAST_CHECK_KEY,
  MIN_INTERVAL_MS,
  COPY,
};
