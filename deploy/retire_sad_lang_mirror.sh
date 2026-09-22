#!/usr/bin/env bash
# فصلُ محرابٍ عن موقع لغة ص — إزاحةُ البقايا من `sad-lang.org/mihrab/`.
#
# ما الذي بقي؟ نشرُ الموقع القديمُ كان يضع محرابَ في `/opt/sad-website/mihrab/`
# فيُخدَم من `sad-lang.org/mihrab/` (كتلةُ `location /` هناك فيها `try_files`، فأيُّ
# مجلّدٍ فرعيٍّ يُخدَم فورًا). ثمّ انتقل الموقعُ إلى `mihrab.dev` — **ولم يُزَح**
# المجلّدُ القديم: قِيس ‎2026-09-22‎ أنّ `sad-lang.org/mihrab/` و`/mihrab/download/`
# يردّان ‎200‎ بنسخةٍ كاملةٍ قديمة (تحمل ‎1.121‎ أربعَ مرّات). أصلان يقدّمان الموقعَ
# نفسَه، وأحدُهما ميّتٌ يُحدَّث، ولا حارسَ يقيسه — حتّى [LIVE-01].
#
# وهذا السكربتُ **لا يحذف**: ينقل المجلّدَ إلى `/opt/mihrab/.retired-sad-lang-<وقت>`
# (القرصُ نفسُه، فالنقلُ لحظيّ) ويقيس بعدها أنّ المسارَ لم يعد ‎200‎. الحذفُ النهائيُّ
# قرارُ المالك بعد أسبوع. ولا sudo هنا: `/opt/sad-website` مملوكٌ لمستخدم النشر
# (هكذا كان يُكتَب أصلًا).
#
# ⚠️ ما لا يفعله: التحويلَ ‎301‎ من `sad-lang.org/mihrab/…` إلى `mihrab.dev/…` —
#    فذلك سطرٌ في كتلة `sad-lang.org` في nginx ويحتاج sudo. القصاصةُ جاهزة في
#    `deploy/nginx/sad-lang.org-mihrab-301.conf.example`؛ وبدونها يردّ المسارُ ‎404‎
#    وهو الفصلُ الصريح. الروابطُ القديمةُ في البرّيّة (إصداراتٌ، README قديمة) هي ما
#    يُرجِّح التحويلَ على ‎404‎ — والقرارُ للمالك.
#
# الترتيبُ الملزِم (قياسُ سالي): ① نشرُ الموقع بالأصل الجديد ② تركيبُ القصاصة (sudo)
# ③ هذا السكربت. ويرفض السكربتُ التشغيلَ ما لم يتحقّق ①و②.
#   MIHRAB_SITE_HOST=user@host bash deploy/retire_sad_lang_mirror.sh
set -euo pipefail

HOST="${MIHRAB_SITE_HOST:?عيّن MIHRAB_SITE_HOST (مثال: user@host)}"
PORT="${MIHRAB_SITE_PORT:-22}"
OLD="${MIHRAB_OLD_SAD_PATH:-/opt/sad-website/mihrab}"
KEEP="${MIHRAB_SITE_ROOT:-/opt/mihrab}/.retired-sad-lang-$(date -u +%Y%m%d-%H%M%S)"
SSH=(ssh -p "$PORT" -o BatchMode=yes)

# رمزُ الحالة بـ`-w` لا `curl -I | head -1`: مع `pipefail` كان قطعُ `head` للأنبوب
# (‏SIGPIPE ⇒ ‎141‎) يُلحِق «(لا جواب)» بسطرٍ صحيحٍ طُبع للتوّ (قِيس بالمحاكاة) —
# ولا أنبوبَ هنا. وcurl يطبع ‎000‎ بنفسه حين لا جواب، فلا `|| echo 000` (كان
# يُلصِق ‎000‎ بـ‎000‎ فيطبع ‎000000‎).
_code() { curl -s -o /dev/null -w '%{http_code}' -m 15 "https://sad-lang.org$1" || true; }
PATHS=(/mihrab/ /mihrab/download/ /mihrab/docs/)
echo "▶ القياسُ قبل الإزاحة:"
for p in "${PATHS[@]}"; do
  printf '   sad-lang.org%s ⇒ %s\n' "$p" "$(_code "$p")"
done

# ── شرطان قبل الإزاحة (قياسُ سالي، ‎2026-09-22‎) ──
# ① `releases.json` **الحيُّ** على mihrab.dev كان أصلُه `sad-lang.org/mihrab/`، وأزرارُ
#    التنزيل تركّب `origin + base + file` — فإزاحةُ المجلّد تعطّل تنزيلَ محرابٍ من موقع
#    محرابٍ نفسِه. لا إزاحةَ قبل نشرِ الموقع بالأصل الجديد (‏`build/deploy_site.sh`).
# ② كتلةُ `location /` في sad-lang.org تردّ صفحةَ اللغة بـ‎200‎ لأيّ مسارٍ مفقود (قِيس:
#    `/mihrab-zzz/` ⇒ ‎200‎ «لغة ص»). فبعد الإزاحة بلا تحويلٍ لا ‎404‎ بل **ابتلاعٌ صامت**:
#    من ضغط رابطَ التنزيل القديم يرى موقعَ لغةٍ بلا تفسير. فالقصاصةُ تُركَّب **قبل**
#    الإزاحة (‏`location ^~ /mihrab/` تسبق `try_files`)، ويُقاس تركيبُها بمسارٍ عشوائيٍّ
#    تحت `/mihrab/`: ‎301‎ إلى mihrab.dev = مركَّبة؛ ‎404‎ = المجلّدُ يخدم ولا قصاصة.
#    ومن أراد الابتلاعَ عن قصدٍ (فصلٌ بلا أثر) يصرّح: MIHRAB_ALLOW_SWALLOW=yes
echo "▶ الشروط قبل الإزاحة:"
_origin="$(curl -s -m 15 https://mihrab.dev/dl/releases.json | grep -o '"origin": *"[^"]*"' | head -1 || true)"
printf '   أصلُ المانيفست الحيّ: %s\n' "${_origin:-(تعذّرت القراءة)}"
if [[ -z "$_origin" ]]; then
  echo "❌ تعذّرت قراءةُ https://mihrab.dev/dl/releases.json — لا إزاحةَ بلا قياس" >&2; exit 3
fi
if [[ "$_origin" == *sad-lang.org* ]]; then
  echo "❌ المانيفستُ الحيُّ ما زال يشير إلى sad-lang.org/mihrab/ — انشر الموقعَ أوّلًا (MIHRAB_SITE_HOST=… bash build/deploy_site.sh) ثمّ عُد" >&2; exit 3
fi
_probe_path="/mihrab/retire-probe-$(date +%s)/"
_probe="$(curl -s -o /dev/null -w '%{http_code}' -m 15 "https://sad-lang.org$_probe_path" || true)"
_probe_loc="$(curl -s -o /dev/null -w '%{redirect_url}' -m 15 "https://sad-lang.org$_probe_path" || true)"
printf '   مسارٌ عشوائيٌّ تحت /mihrab/: %s %s\n' "$_probe" "$_probe_loc"
if [[ "$_probe" == 301 && "$_probe_loc" == https://mihrab.dev/* ]]; then
  echo "   ✅ قصاصةُ التحويل مركَّبة"
elif [[ "${MIHRAB_ALLOW_SWALLOW:-}" == yes ]]; then
  echo "   ⚠️ لا تحويلَ — والإزاحةُ مصرَّحٌ بها عن قصد: الروابطُ القديمة ستبتلعها صفحةُ اللغة"
else
  echo "❌ لا قصاصةَ تحويلٍ مركَّبة (المنتظَر ‎301‎ إلى mihrab.dev، والمقيس ${_probe}) — ركِّب deploy/nginx/sad-lang.org-mihrab-301.conf.example بـsudo أوّلًا، أو صرِّح MIHRAB_ALLOW_SWALLOW=yes" >&2; exit 4
fi

echo "▶ الإزاحةُ على $HOST: $OLD → $KEEP"
"${SSH[@]}" "$HOST" "set -e
  if [ ! -d '$OLD' ]; then echo '   لا مجلّدَ في $OLD — لا شيءَ يُزاح'; exit 0; fi
  if [ -L '$OLD' ]; then echo '   ⚠️ وصلةٌ رمزيّة: يُنقَل الرابطُ لا هدفُه، والهدفُ يبقى حيث هو:'; readlink '$OLD' | sed 's|^|      → |'; fi
  du -sh '$OLD' | sed 's|^|   الحجم: |'
  mkdir -p '$(dirname "$KEEP")'
  mv '$OLD' '$KEEP'
  echo '   نُقل. للتراجع: mv $KEEP $OLD'
"

echo "▶ القياسُ بعد الإزاحة (المنتظَر: لا ‎200‎):"
# ‎000‎ (لا جواب) ليس «لا ‎200‎»: قياسٌ لم يُحسَم لا يُعلِن فصلًا. و‎200‎ بعد النقل
# ليس ذاكرةً مؤقّتة (‏sad-lang.org يُخدَم من nginx مباشرةً بلا CDN — قِيس: لا
# `age` ولا `cf-cache-status`) بل مسارٌ آخر يخدمه (‏`alias`/`root` ثانٍ)، والتراجعُ
# لا يصلحه؛ فلا يُتراجَع آليًّا بل يُفحَص `nginx -T`.
fail=0
for p in "${PATHS[@]}"; do
  code="$(_code "$p")"
  printf '   sad-lang.org%s ⇒ %s\n' "$p" "$code"
  case "$code" in
    200)    fail=1 ;;
    000|'') [[ "$fail" == 1 ]] || fail=2 ;;
  esac
done
if [[ "$fail" == 1 ]]; then
  echo "❌ ما زال يُخدَم بـ‎200‎ بعد النقل — مسارٌ آخر يخدمه؛ افحص nginx -T على الخادم (المجلّدُ المنقول باقٍ في $KEEP)" >&2
  exit 1
fi
if [[ "$fail" == 2 ]]; then
  echo "❌ نُقل المجلّدُ لكنّ القياسَ البعديَّ لم يُحسَم (لا جواب من sad-lang.org) — أعد القياسَ بيدك؛ وللتراجع: mv '$KEEP' '$OLD'" >&2
  exit 2
fi
echo "✅ انفصل: sad-lang.org لا يخدم محرابَ — وما بقي منه تحويلٌ دائمٌ إلى mihrab.dev بالمسار نفسِه."
