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
SHA_TREE=ef69aa24f298fe994f8a632edcce7734930ce4964e46508eb3c9df8de419d458
SHA_CONF=e54c1b06b7103e35d988739e758b81b66176b69fb3ff2d59c744178f0f3356a3

die() { echo "❌ $*" >&2; exit 1; }
say() { echo "── $*"; }

[[ $EUID -eq 0 ]] || die "يحتاج جذرًا: sudo bash $0"

# البصماتُ أدناه لا تحرس شيئًا إن كان هذا الملفُّ نفسُه قابلًا للتبديل. فيُرفض
# التشغيلُ من مجلّدٍ عامّ الكتابة (‏`/tmp` و`/var/tmp` وأمثالهما).
_self_dir="$(cd "$(dirname "$0")" && pwd)"
if [[ -k "$_self_dir" || "$(stat -c '%A' "$_self_dir")" == *w*w* ]]; then
  die "لا يُشغَّل من مجلّدٍ يكتب فيه الجميع ($_self_dir) — البصمتان بلا معنًى هناك.
   انقله أوّلًا:  sudo install -D -o root -g root -m 755 $0 /usr/local/lib/mihrab-deploy/$(basename "$0")"
fi
[[ -f $STAGE/tree.tgz ]] || die "لا شجرةَ في $STAGE/tree.tgz"
[[ -f $STAGE/mihrab.dev.static.conf ]] || die "لا كتلةَ nginx في $STAGE"

_sha() { sha256sum "$1" | cut -d' ' -f1; }
[[ "$(_sha "$STAGE/tree.tgz")" == "$SHA_TREE" ]] \
  || die "بصمةُ tree.tgz لا تطابق المثبَّتة — لا يُنشَر ما لم يُعرَف."
[[ "$(_sha "$STAGE/mihrab.dev.static.conf")" == "$SHA_CONF" ]] \
  || die "بصمةُ كتلة nginx لا تطابق المثبَّتة — لا تُركَّب."
say "البصمتان مطابقتان"

# ‏`--nginx-only`: تصحيحُ كتلةٍ فوق شجرةٍ منشورةٍ سليمة. بدونه تُفكّ 204 م.ب وتُبدَّل
# بلا داعٍ، **وتُدفَع الشجرةُ السليمةُ إلى `static.old`** فيضيع ما نتراجع إليه.
NGINX_ONLY=no
[[ "${1:-}" == "--nginx-only" ]] && NGINX_ONLY=yes

if [[ $NGINX_ONLY == yes ]]; then
  [[ -s $LIVE/index.html ]] || die "‏--nginx-only فوق لا شيء: $LIVE بلا صفحة"
  say "الكتلةُ وحدَها — الشجرةُ المنشورةُ تُترك كما هي"
fi

# ── (1) الفكّ إلى مجلّدٍ جانبيّ ────────────────────────────────────────────────
if [[ $NGINX_ONLY == no ]]; then
say "فكُّ الشجرة إلى $NEW"
rm -rf "$NEW"
mkdir -p "$NEW"
tar xzf "$STAGE/tree.tgz" -C "$NEW" || die "فشل الفكّ"

# بوّابةٌ **قبل** التبديل: شجرةٌ ناقصةٌ تُبدَّل هي انقطاعُ خدمة.
for f in index.html boot.js product.web.js manifest.json favicon.ico \
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
grep -qi 'vscodium' "$NEW/manifest.json" "$NEW/index.html" "$NEW/boot.js" \
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

# ── التراجعُ يعيد **الاثنين**: الكتلةَ والشجرة ──
# كان يعيد الكتلةَ وحدَها، فيبقى nginx يخدم الشجرةَ الجديدةَ (‏`root` نفسُه في
# الكتلتين) — أي أنّ التراجعَ كان يتراجع عن نصفِ ما فعله. التبديلُ ذرّيٌّ في الأمام
# ويجب أن يكون له نظيرٌ في الخلف.
rollback() {
  local why="$1"
  echo "⚠️ $why — تراجعٌ تلقائيّ" >&2
  if [[ -s $BACKUP ]]; then cp -a "$BACKUP" "$AVAIL"; else rm -f "$LINK"; fi
  if [[ $NGINX_ONLY == no && -d $OLD ]]; then
    rm -rf "$LIVE.bad" && mv "$LIVE" "$LIVE.bad" && mv "$OLD" "$LIVE" \
      && echo "↩️ عادت الشجرةُ السابقة (والمرفوضةُ في $LIVE.bad)" >&2
  fi
  if nginx -t >/dev/null 2>&1; then
    systemctl reload nginx 2>/dev/null
    echo "↩️ عاد الإعدادُ سليمًا وحُمِّل — لم يسقط شيء" >&2
  else
    echo "⛔ الإعدادُ ما زال ساقطًا بعد التراجع — تدخّلٌ يدويٌّ لازم." >&2
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
# **والنوعُ يُقاس لا الرمزُ وحدَه.** كتلةُ `types` على مستوى `server` تستبدل الجدولَ
# الموروثَ ولا توسّعه، فخُدِمت الصفحةُ و`boot.js` والورقةُ `application/octet-stream`
# — ومع `nosniff` يرفض المتصفّحُ تنفيذَ الوحدات: موقعٌ أبيضُ بلا رسالةِ خطأ، وكلُّ
# رمزٍ فيه 200. فحصُ الرمز وحدَه كان أخضرَ على موقعٍ مكسور.
_ct() { curl -sk -I -H 'Host: mihrab.dev' "https://127.0.0.1$1" \
        | tr -d '\r' | awk 'tolower($1)=="content-type:"{print $2}'; }
_want() {
  local got; got="$(_ct "$1")"
  local code; code="$(curl -sk -o /dev/null -w '%{http_code}' -H 'Host: mihrab.dev' "https://127.0.0.1$1")"
  printf '   %-34s %s  %s' "$1" "$code" "${got:-—}"
  if [[ -n "$2" && "$got" != "$2"* ]]; then printf '   ⚠️ المنتظَر %s' "$2"; RC=1; fi
  echo
}
RC=0
_want /                    text/html
_want /boot.js             application/javascript
_want /product.web.js      application/javascript
_want /manifest.json       application/json
_want /favicon.ico         image/
_want /out/nls.messages.js application/javascript
_want /out/vs/workbench/workbench.web.main.internal.css text/css

# **الفحصُ بوّابةٌ لا تقرير.** كان `RC` يُطبَع ولا يُستعمل، وآخرُ أمرٍ `echo` ⇒ خروجٌ
# بصفرٍ على موقعٍ أبيض. أي أنّ الدرسَ الذي كسر النشرَ الحيَّ (‏`types` تستبدل الجدولَ
# فيصير كلُّ شيءٍ `octet-stream` مع `nosniff`) لم يكن قد صار بوّابةً بعد.
if [[ $RC -ne 0 ]]; then
  echo "   ⛔ نوعُ محتوًى خاطئ — المتصفّحُ لن ينفّذ الوحدات: موقعٌ أبيضُ وكلُّ رمزٍ 200." >&2
  rollback "نوعُ المحتوى خاطئ"
fi

echo
echo "   الشجرةُ السابقة في $OLD — احذفها بعد التأكّد:  sudo rm -rf $OLD"
