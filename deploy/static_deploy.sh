#!/usr/bin/env bash
# نشرُ محرابٍ الثابت على mihrab.dev — يُشغَّل بجذرٍ **على الخادم**.
#
#     sudo install -D -o root -g root -m 755 \
#          /tmp/mihrab-static/static_deploy.sh \
#          /usr/local/lib/mihrab-deploy/static_deploy.sh
#     sudo bash /usr/local/lib/mihrab-deploy/static_deploy.sh
#
# ⚠️ **يُنقَل قبل أن يُشغَّل.** تشغيلُه من `/tmp` يُبطِل البصمتين أدناه إبطالًا كاملًا:
#    من يقدر على تبديل الحمولة يقدر على تبديل السطرين اللذين يحرسانها في السكربت
#    نفسِه. والسكربتُ يرفض العملَ من مسارٍ يكتب فيه الجميع.
#
# ما يفعله، بهذا الترتيب:
#   1. يفكّ الشجرةَ إلى `/opt/mihrab/static.new` ويتحقّق من صفحة المضيف قبل التبديل.
#   2. يبدّل `static` ⇐ `static.new` تبديلًا **ذرّيًّا** (‏rename لا cp).
#   3. يركّب كتلةَ nginx الثابتة، ويختبر، ويحمّل — **ويتراجع تلقائيًّا إن سقط الاختبار**.
#   4. يوقف `mihrab-web.service` ويعطّلها: لم تعد لها وظيفة.
#
# ولماذا كلُّ هذا في سكربتٍ واحدٍ بدل أوامرَ متتابعة: التبديلُ والاختبارُ والتراجعُ
# يجب أن تكون **كتلةً واحدةً**. أُوقِع سابقًا أن نجح `ln -sf` وفشل `cp` قبله، فبقي
# رابطٌ معلَّقٌ يكسر `nginx -t` — وستّةُ مواقعَ على حافّة السقوط عند أوّل إعادة تشغيل.
set -uo pipefail

STAGE=/tmp/mihrab-static
ROOT_DIR=/opt/mihrab
LIVE=$ROOT_DIR/static
NEW=$ROOT_DIR/static.new
OLD=$ROOT_DIR/static.old
AVAIL=/etc/nginx/sites-available/mihrab
LINK=/etc/nginx/sites-enabled/mihrab
BACKUP=/root/mihrab-nginx-$(date +%Y%m%d-%H%M%S).bak

# ── بصمتا الحمولة ──
# ‏`/tmp` يكتب فيه **أيُّ مستخدم**. وهذا السكربتُ يعمل بجذر، فبين لحظةِ رفع الحمولة
# ولحظةِ تشغيله نافذةٌ يمكن أن تُبدَّل فيها. البصمتان مثبَّتتان هنا — في ملفٍّ يملكه
# الجذر — فالتبديلُ يُكشَف ولا يُنفَّذ. حدِّثهما مع كلّ حمولةٍ جديدة.
SHA_TREE=7b4d60428d8622a7f95ab66c8569f2d7042bdb72cbe7825de1d710cc7a0c5c8e
SHA_CONF=c8e1f208351ecb593a4bc66bffccfe533cb11d4bd1e2e0568598319ef5533787

die() { echo "❌ $*" >&2; exit 1; }
say() { echo "── $*"; }

[[ $EUID -eq 0 ]] || die "يحتاج جذرًا: sudo bash $0"

# البصماتُ أدناه لا تحرس شيئًا إن كان هذا الملفُّ نفسُه قابلًا للتبديل. فيُرفض
# التشغيلُ من مجلّدٍ عامّ الكتابة (‏`/tmp` و`/var/tmp` وأمثالهما).
_self_dir="$(cd "$(dirname "$0")" && pwd)"
# ‏`%a` لا `%A`، وبِتُّ `o+w` وحدَه لا «حرفا w»: `drwxrwxr-x` (‏root:staff بـumask 002،
# شائعٌ تحت `/usr/local`) كان يُرفَض كذبًا، والرسالةُ تنصح بنقلٍ إلى مجلّدٍ مثلِه.
# و`stat -c` صيغةُ GNU حصرًا: على BSD يفشل الأمرُ فتصير القيمةُ فارغةً والشرطُ كاذبًا
# — أي أنّ **تحقُّقًا أمنيًّا يُعطَّل عند غياب أداته**. فيُجرَّب البديلُ ثمّ يُعلَن العجز.
_mode="$(stat -c '%a' "$_self_dir" 2>/dev/null || stat -f '%Lp' "$_self_dir" 2>/dev/null || true)"
if [[ -z "$_mode" ]]; then
  die "تعذّر قياسُ صلاحيّات $_self_dir (لا stat متوافق) — لا يُشغَّل بجذرٍ بلا قياس."
fi
if [[ -k "$_self_dir" ]] || (( (8#$_mode & 8#002) != 0 )); then
  die "لا يُشغَّل من مجلّدٍ يكتب فيه الجميع ($_self_dir · $_mode) — البصمتان بلا معنًى هناك.
   انقله أوّلًا:  sudo install -D -o root -g root -m 755 $0 /usr/local/lib/mihrab-deploy/$(basename "$0")"
fi
# ‏`--nginx-only`: تصحيحُ كتلةٍ فوق شجرةٍ منشورةٍ سليمة. بدونه تُفكّ ‏≈203 م.ب وتُبدَّل
# بلا داعٍ، **وتُدفَع الشجرةُ السليمةُ إلى `static.old`** فيضيع ما نتراجع إليه.
NGINX_ONLY=no
# **وسيطٌ غيرُ معروفٍ يُرفَض ولا يُهمَل.** `--nginx_only` أو `-n` كان يمرّ صامتًا
# فيقع نشرٌ كامل: تُفكّ ‏≈203 م.ب و**تُدفَع الشجرةُ السليمةُ إلى `static.old`** — وهو
# بعينه ما تقول الوثيقةُ إنّ الرايةَ تمنعه.
case "${1:-}" in
  "")            ;;
  --nginx-only)  NGINX_ONLY=yes ;;
  *)             die "وسيطٌ غيرُ معروف: ${1} — المعروفُ وحدَه: --nginx-only" ;;
esac
(( $# <= 1 )) || die "وسائطُ زائدة: $* — يُقبَل وسيطٌ واحدٌ على الأكثر"

if [[ $NGINX_ONLY == yes ]]; then
  [[ -s $LIVE/index.html ]] || die "‏--nginx-only فوق لا شيء: $LIVE بلا صفحة"
  say "الكتلةُ وحدَها — الشجرةُ المنشورةُ تُترك كما هي"
fi

# ── ما يُستهلَك يُطلَب، وما لا يُمَسّ لا يُشترَط ──
# كان الشرطان فوق قراءةِ الراية، فيلزمان `tree.tgz` **حتّى مع `--nginx-only`** —
# وهي رايةٌ وُضِعت أصلًا لتصحيحِ كتلةٍ فوق شجرةٍ منشورةٍ **لا تُمَسّ**. فصارت تطلب
# ‏≈203 م.ب لتنقل بضعةَ كيلوبايتات، وسقطت تمامًا يومَ زالت الحمولةُ من `/tmp`
# (يُنظَّف بالإقلاع) وزالت الشجرةُ من جهاز البناء: بقيت الرايةُ في الوثيقة ولا
# سبيلَ إلى تشغيلها. حارسٌ يُبطِل الطريقَ الذي يحرسه.
_sha() { sha256sum "$1" | cut -d' ' -f1; }

[[ -f $STAGE/mihrab.dev.static.conf ]] || die "لا كتلةَ nginx في $STAGE"
[[ "$(_sha "$STAGE/mihrab.dev.static.conf")" == "$SHA_CONF" ]] \
  || die "بصمةُ كتلة nginx لا تطابق المثبَّتة — لا تُركَّب."

if [[ $NGINX_ONLY == no ]]; then
  [[ -f $STAGE/tree.tgz ]] || die "لا شجرةَ في $STAGE/tree.tgz"
  [[ "$(_sha "$STAGE/tree.tgz")" == "$SHA_TREE" ]] \
    || die "بصمةُ tree.tgz لا تطابق المثبَّتة — لا يُنشَر ما لم يُعرَف."
  say "البصمتان مطابقتان"
else
  say "بصمةُ الكتلة مطابقة (والشجرةُ خارج هذا التشغيل)"
fi

# ── (1) الفكّ إلى مجلّدٍ جانبيّ ────────────────────────────────────────────────
if [[ $NGINX_ONLY == no ]]; then
say "فكُّ الشجرة إلى $NEW"
rm -rf "$NEW"
mkdir -p "$NEW"
tar xzf "$STAGE/tree.tgz" -C "$NEW" || die "فشل الفكّ"

# بوّابةٌ **قبل** التبديل: شجرةٌ ناقصةٌ تُبدَّل هي انقطاعُ خدمة.
# ‏`boot-early.js` في القائمة [WEB-09]: خرج من `index.html` كي تستغني سياسةُ الأمان
# عن `'unsafe-inline'`. وغيابُه لا يُنتج صفحةَ خطأ — يُنتج شاشةَ إقلاعٍ لا تنتهي،
# لأنّ `_VSCODE_FILE_ROOT` لا يُضبَط فلا تُحلّ مساراتُ الحزمة أصلًا.
for f in index.html boot.js boot-early.js product.web.js manifest.json favicon.ico \
         out/nls.messages.js out/vs/workbench/workbench.web.main.internal.js \
         out/vs/workbench/workbench.web.main.internal.css \
         out/vs/workbench/kawkab-mono.woff2 \
         out/vs/workbench/contrib/webview/browser/pre/index.html; do
  [[ -s "$NEW/$f" ]] || die "ملفٌّ لازمٌ مفقودٌ أو فارغ: $f"
done
grep -q 'globalThis._MIHRAB_PRODUCT=' "$NEW/product.web.js" \
  || die "product.web.js بلا هويّة"
grep -q '"name": "محراب"' "$NEW/manifest.json" \
  || die "المانيفست ليس مانيفستَ محراب — أيقونةُ التبويب واسمُ التثبيت ليسا لنا"
grep -qi 'vscodium' "$NEW/manifest.json" "$NEW/index.html" \
                    "$NEW/boot.js" "$NEW/boot-early.js" \
  && die "تسرّبُ اسمِ المنبع في ملفٍّ يُخدَم للزائر"
# ‏[BR-05]: وجهةُ مستودعِ المنبع مضروبةٌ في الحزمة المصغَّرة — لا مفتاحٌ في إعدادٍ،
# فلا تراها بوّاباتُ `product.json` ولا النصِّ المخبوز. كان لوحُ الترحيب يجلب
# `announcements-extra.json` من مستودع المنبع في كلّ فتحةٍ أولى، ومُبلِّغُ الأعطاب
# يبحث في قضاياه بنصّ عطبِ مستخدمِنا. قِيس حيًّا بعد أوّل نشرٍ لا قبله.
grep -q 'VSCodium/vscodium' "$NEW/out/vs/workbench/workbench.web.main.internal.js" \
  && die "[BR-05] وجهةُ مستودعِ المنبع في الحزمة — شجرةٌ بُنيت قبل إصلاح GH_REPO_PATH"

chown -R root:root "$NEW"
find "$NEW" -type d -exec chmod 755 {} +
find "$NEW" -type f -exec chmod 644 {} +
say "الشجرة: $(du -sh "$NEW" | cut -f1) · $(find "$NEW" -type f | wc -l) ملفًّا"

# ── (2) تبديلٌ ذرّيّ ──────────────────────────────────────────────────────────
say "التبديل"
rm -rf "$OLD"
[[ -d $LIVE ]] && mv "$LIVE" "$OLD"
mv "$NEW" "$LIVE" || die "فشل التبديل — الشجرةُ القديمةُ في $OLD"
fi   # NGINX_ONLY

# ── (3) nginx ────────────────────────────────────────────────────────────────
say "نسخةٌ احتياطيّةٌ من الكتلة الحاليّة ⇐ $BACKUP"
[[ -f $AVAIL ]] && cp -a "$AVAIL" "$BACKUP"

install -o root -g root -m 644 "$STAGE/mihrab.dev.static.conf" "$AVAIL" \
  || die "فشل تركيبُ الكتلة"
# الملفُّ **قبل** الرابط، والرابطُ إلى مسارٍ مطلق: `ln -sf` لا يتحقّق من هدفه،
# فرابطٌ معلَّقٌ يكسر `nginx -t` لكلّ المواقع لا لموقعنا.
ln -sfn "$AVAIL" "$LINK"

# ── قياسُ خدمةٍ لا نحوٍ ──
# ‏`nginx -t` يقول «الإعدادُ سليمٌ نحويًّا» ولا يقول «الموقعُ يخدم»: لا يتحقّق من
# وجود `root` ولا من نوع المحتوى. وكتلةُ `types` التي كسرت النشرَ الحيَّ مرّت من
# `nginx -t` ومن سبعةِ رموزِ 200 معًا — وكان الموقعُ أبيض. فالبوّابةُ تقيس **النوع**،
# وتُستدعى بعد النشر وبعد التراجع كليهما.
# ‏`%{content_type}` من curl مباشرةً — **لا تحليلَ ترويسات**. أوّلُ صياغةٍ كانت
# `curl -I | tr -d '\r' | awk …`، ومحرفُ الإرجاع فيها انقلب سطرًا حقيقيًّا وهي
# تُكتَب، فصار `tr` يمسح **الأسطر**: تنهار الترويساتُ إلى سطرٍ واحدٍ فلا يطابق
# awk شيئًا، ويعود كلُّ نوعٍ فارغًا. فأُنذِر بعطبٍ لا وجودَ له، وتراجع النشرُ عن
# شجرةٍ سليمة. وcurl يعرف النوعَ ولا يحتاج من يقرؤه له.
_ct() { curl -sk -o /dev/null -w '%{content_type}' -H 'Host: mihrab.dev' "https://127.0.0.1$1"; }

# ‏`[:cntrl:]` لا `tr -d '\r'`: محرفُ الإرجاع في نصٍّ يُكتَب برمجيًّا انقلب مرّةً
# سطرًا حقيقيًّا، فصار `tr` يمسح **الأسطر** وتراجع النشرُ عن شجرةٍ سليمة. والصنفُ
# المسمَّى لا يحمل هذا الفخَّ أصلًا.
_cc() {
  curl -sk -o /dev/null -D - -H 'Host: mihrab.dev' "https://127.0.0.1$1" 2>/dev/null \
    | grep -i '^cache-control:' | head -1 | cut -d: -f2- | tr -d '[:cntrl:]' | sed 's/^ *//'
}

verify_serving() {
  local rc=0 got code blank=0
  local -a paths=(
    "/|text/html"
    "/boot.js|application/javascript"
    "/boot-early.js|application/javascript"
    "/product.web.js|application/javascript"
    "/manifest.json|application/json"
    "/favicon.ico|image/"
    "/out/nls.messages.js|application/javascript"
    "/out/vs/workbench/workbench.web.main.internal.css|text/css"
  )
  for entry in "${paths[@]}"; do
    local path="${entry%%|*}" want="${entry##*|}"
    got="$(_ct "$path")"
    code="$(curl -sk -o /dev/null -w '%{http_code}' -H 'Host: mihrab.dev' "https://127.0.0.1$path")"
    printf '   %-34s %s  %s' "$path" "$code" "${got:-—}"
    if [[ "$code" != "200" ]]; then printf '   ⚠️ المنتظَر 200'; rc=1
    elif [[ -z "$got" ]]; then printf '   ⚠️ لا نوع'; blank=$((blank + 1)); rc=1
    elif [[ "$got" != "$want"* ]]; then printf '   ⚠️ المنتظَر %s' "$want"; rc=1; fi
    echo
  done

  # ── مِجَسٌّ صامتٌ ليس عطبًا في الموقع ──
  # **كلُّ** الأنواع فارغةً مع رموزِ 200 سليمةٍ لا تصف موقعًا مكسورًا: nginx الذي
  # يردّ 200 يردّ نوعًا معه. تصف **أداةَ القياس** وقد عطبت. وقد وقع فعلًا: انقلب
  # `\r` في `tr` سطرًا حقيقيًّا فصار يمسح الأسطر، فعاد كلُّ نوعٍ فارغًا وتراجع
  # النشرُ عن شجرةٍ سليمة. ومِجَسٌّ يُنذِر بما لم يقِسه أسوأُ من مِجَسٍّ غائب.
  if (( blank == ${#paths[@]} )); then
    echo "   ⛔ **كلُّ الأنواع فارغة مع رموزِ 200** — العطبُ في المِجَسّ لا في الموقع." >&2
    echo "      افحص \`_ct\` قبل أن تلوم النشر:  curl -sk -o /dev/null -w '%{content_type}' -H 'Host: mihrab.dev' https://127.0.0.1/" >&2
  fi
  return $rc
}


# ── ما يصل الزائرَ، لا ما في المستودع ──
# الحارسُ الساكن [CACHE-02] يقرأ `mihrab.dev.static.conf` عندنا. وما يخدم فعلًا هو
# ما في `sites-enabled` — وقد يفترقان: تركيبٌ فشل، أو كتلةٌ أسبقُ تلتقط المسار،
# أو `add_header` في مستوًى أدنى ألغى وراثةَ ما فوقه. فيُسأل السلكُ نفسُه.
# ومساراتُ `/out/` غيرُ مبصومة ⇒ أيُّ طزاجةٍ موجبةٍ نافذةُ عمًى لا يبلغها نشرٌ.
verify_cache() {
  local cc rc=0
  cc="$(_cc /out/nls.messages.js)"
  printf '   %-34s %s' "/out/ Cache-Control" "${cc:-—}"
  if [[ -z "$cc" ]]; then
    printf '   ⚠️ لا ترويسةَ تخزينٍ أصلًا'; rc=1
  elif [[ "$cc" == *no-store* || "$cc" == *no-cache* || "$cc" =~ max-age=0([^0-9]|$) ]]; then
    printf '   ✅ طزاجةٌ صفريّة'
  else
    printf '   ⚠️ طزاجةٌ موجبةٌ على اسمٍ غيرِ مبصوم'; rc=1
  fi
  echo
  return $rc
}

# ── التراجعُ يعيد **الاثنين**: الكتلةَ والشجرة ──
# كان يعيد الكتلةَ وحدَها، فيبقى nginx يخدم الشجرةَ الجديدةَ (‏`root` نفسُه في
# الكتلتين) — أي أنّ التراجعَ كان يتراجع عن نصفِ ما فعله. التبديلُ ذرّيٌّ في الأمام
# ويجب أن يكون له نظيرٌ في الخلف.
rollback() {
  local why="$1" hurt=0
  echo "⚠️ $why — تراجعٌ تلقائيّ" >&2

  # ‏**كلُّ خطوةٍ تُفحَص.** `set -uo pipefail` بلا `-e`، فسلسلةُ `&&` التي تنكسر
  # في منتصفها تُبتلَع بصمت. وكان فشلُ `mv "$OLD" "$LIVE"` (مساحةٌ · مقبضٌ · ACL)
  # يترك `/opt/mihrab/static` **غيرَ موجود**، ثمّ ينجح `nginx -t` (فهو نحويٌّ لا
  # يتحقّق من وجود `root`)، فيُطبَع «لم يسقط شيء» والموقعُ يردّ 404 على كلّ مسار.
  if [[ -s $BACKUP ]]; then
    cp -a "$BACKUP" "$AVAIL" || { echo "⛔ تعذّرت استعادةُ الكتلة من $BACKUP" >&2; hurt=1; }
  else
    rm -f "$LINK" || { echo "⛔ تعذّرت إزالةُ الرابط $LINK" >&2; hurt=1; }
  fi

  if [[ $NGINX_ONLY == no && -d $OLD ]]; then
    rm -rf "$LIVE.bad"
    if mv "$LIVE" "$LIVE.bad" && mv "$OLD" "$LIVE"; then
      echo "↩️ عادت الشجرةُ السابقة (والمرفوضةُ في $LIVE.bad)" >&2
    else
      echo "⛔ **فشل إرجاعُ الشجرة.** الحالةُ الآن: $LIVE=$( [[ -d $LIVE ]] && echo موجود || echo مفقود )" >&2
      hurt=1
    fi
  fi

  nginx -t >/dev/null 2>&1 || { echo "⛔ الإعدادُ ما زال ساقطًا بعد التراجع." >&2; hurt=1; }
  systemctl reload nginx 2>/dev/null || { echo "⛔ فشل تحميلُ nginx بعد التراجع." >&2; hurt=1; }

  # **ولا يُدَّعى النجاحُ إلّا بقياسِ خدمةٍ.** `nginx -t` يقول «الإعدادُ نحويٌّ سليم»
  # ولا يقول «الموقعُ يخدم». وبوّابةُ النوع موجودةٌ في هذا السكربت — فلتُعَد.
  if (( hurt == 0 )) && verify_serving >/dev/null 2>&1; then
    echo "↩️ عاد الموقعُ يخدم — لم يسقط شيء" >&2
  else
    echo "⛔ الموقعُ لا يخدم بعد التراجع — تدخّلٌ يدويٌّ لازم:" >&2
    echo "   sudo ls -ld $LIVE ; sudo nginx -t ; sudo systemctl status nginx" >&2
  fi
  exit 1
}

nginx -t || rollback "سقط nginx -t"

systemctl reload nginx || rollback "فشل تحميلُ nginx"
say "‏nginx حُمِّل"

# ── (4) الخدمةُ لم تعد لها وظيفة ─────────────────────────────────────────────
say "إيقافُ mihrab-web.service وتعطيلها"
systemctl stop mihrab-web    2>/dev/null
systemctl disable mihrab-web 2>/dev/null

echo
echo "✅ نُشِر. تحقّقٌ سريع:"
if ! verify_serving; then
  echo "   ⛔ الموقعُ لا يخدم كما يجب — المتصفّحُ لن ينفّذ الوحدات." >&2
  rollback "فشلَ قياسُ الخدمة بعد النشر"
fi

if ! verify_cache; then
  echo "   ⛔ ترويسةُ التخزين على /out/ ليست ما في الكتلة — نافذةُ عمًى تعود." >&2
  rollback "فشلَ قياسُ ترويسة التخزين"
fi

echo
echo "   الشجرةُ السابقة في $OLD — احذفها بعد التأكّد:  sudo rm -rf $OLD"
