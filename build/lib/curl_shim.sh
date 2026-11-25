#!/usr/bin/env bash
# غلافُ `curl` لمهامّ تغليف لينكس [PKG-02] — يُنسَخ باسم `curl` إلى مجلّدٍ مؤقّتٍ أوّلَ `PATH`
# (انظر `build/package_assets.sh`)، و`curl` الحقيقيُّ في `MIHRAB_REAL_CURL`.
#
# لماذا: `calculate-deps.ts` و`install-sysroot.ts` في المنبع يجلبان من raw.githubusercontent.com بـ
# ‏`curl URL -o FILE` بلا `-f` ولا إعادة محاولة. فحين ردّ الخادمُ ‎429‎ (حدُّ الطلبات، يتشاركه
# عدّاؤو GitHub) حُفظت صفحةُ الخطأ «429: …» سكربتًا وانهار perl عليها (‏#43، مرّتين).
#
# - ‏`-f` يجعل الخطأَ خطأً لا ملفًّا، و`--retry` يعيد على 408/429/500/502/503/504 — لا على 404
#   (‏`--retry-all-errors` كان يضيّع دقيقةً عليه). ويحترم `Retry-After`، لكنّ قيمةً تتجاوز السقف
#   (‏`--retry-max-time`) تُسقط الإعادةَ فورًا: فيُنتقل إلى الاحتياط حيث وُجد، و`sysroots.json` يفشل.
# - **وإعادةُ المحاولة وحدها لا تكفي**: الحدُّ قد يدوم (قِيس 2026-11-25: ‎429‎ من جهاز المطوّر
#   أيضًا). فلمسارٍ من `chromium/chromium` يُجلَب الملفُّ نفسُه من مستودع Chromium الرسميّ
#   (‏googlesource، ‏`?format=TEXT` = base64) — قِيس متطابقًا بالبصمة لـ`dpkg-shlibdeps.pl` على
#   الوسم نفسه. ويُنزَّل إلى ملفٍّ **ثمّ** يُفكّ: أنبوبٌ `curl | base64 -d` يأخذ رمزَ `base64`،
#   فنقلٌ مبتورٌ يبدأ بـ`#!` كان يُقبَل (قِيس). ولا يحلّ محلَّ الهدف إلّا ما يبدأ بـ`#!`.
# - ‏`sysroots.json` (من `electron/electron`) بلا احتياط: يحميه `-f` وإعادةُ المحاولة وحدهما.
#
# يحرسه `tests/static/test_curl_shim.sh` بـcurl وهميّ (بلا شبكة).
REAL="${MIHRAB_REAL_CURL:?MIHRAB_REAL_CURL غيرُ مضبوط — مسارُ curl الحقيقيّ}"
OPTS=(-fsSL --retry 5 --retry-connrefused --retry-delay 10 --retry-max-time 180)
"$REAL" "${OPTS[@]}" "$@" && exit 0
rc=$?
url="" out=""
for ((i = 1; i <= $#; i++)); do
  case "${!i}" in
    https://raw.githubusercontent.com/chromium/chromium/*) url="${!i}" ;;
    -o) j=$((i + 1)); out="${!j}" ;;
  esac
done
[[ -n "$url" && -n "$out" ]] || exit "$rc"
rest="${url#https://raw.githubusercontent.com/chromium/chromium/}"
ref="${rest%%/*}" path="${rest#*/}"
[[ "$ref" =~ ^[0-9]+(\.[0-9]+)+$ ]] && ref="refs/tags/$ref"
echo "↻ raw.githubusercontent.com رفض (خرج $rc) — يُجلَب من chromium.googlesource.com: $path" >&2
if "$REAL" "${OPTS[@]}" "https://chromium.googlesource.com/chromium/src/+/$ref/$path?format=TEXT" -o "$out.b64" \
    && base64 -d "$out.b64" > "$out.part" 2>/dev/null \
    && [[ "$(head -c2 "$out.part")" == "#!" ]]; then
  mv "$out.part" "$out"
  rm -f "$out.b64"
  exit 0
fi
rm -f "$out.part" "$out.b64"
exit "$rc"
