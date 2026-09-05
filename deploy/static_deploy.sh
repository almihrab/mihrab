#!/usr/bin/env bash
# نشرُ محرابٍ الثابت على mihrab.dev — يُشغَّل بجذرٍ **على الخادم**.
#
#     sudo bash /tmp/mihrab-static/static_deploy.sh
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
SHA_TREE=9bf29511716887470b16f3c44e5809537769dceb48b400f64f9e89690f211552
SHA_CONF=db7962916cf0e74cfd2a96e92956a4fe66c72e745888086c81f4c1c27fa6f217

die() { echo "❌ $*" >&2; exit 1; }
say() { echo "── $*"; }

[[ $EUID -eq 0 ]] || die "يحتاج جذرًا: sudo bash $0"
[[ -f $STAGE/tree.tgz ]] || die "لا شجرةَ في $STAGE/tree.tgz"
[[ -f $STAGE/mihrab.dev.static.conf ]] || die "لا كتلةَ nginx في $STAGE"

_sha() { sha256sum "$1" | cut -d' ' -f1; }
[[ "$(_sha "$STAGE/tree.tgz")" == "$SHA_TREE" ]] \
  || die "بصمةُ tree.tgz لا تطابق المثبَّتة — لا يُنشَر ما لم يُعرَف."
[[ "$(_sha "$STAGE/mihrab.dev.static.conf")" == "$SHA_CONF" ]] \
  || die "بصمةُ كتلة nginx لا تطابق المثبَّتة — لا تُركَّب."
say "البصمتان مطابقتان"

# ── (1) الفكّ إلى مجلّدٍ جانبيّ ────────────────────────────────────────────────
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

chown -R root:root "$NEW"
find "$NEW" -type d -exec chmod 755 {} +
find "$NEW" -type f -exec chmod 644 {} +
say "الشجرة: $(du -sh "$NEW" | cut -f1) · $(find "$NEW" -type f | wc -l) ملفًّا"

# ── (2) تبديلٌ ذرّيّ ──────────────────────────────────────────────────────────
say "التبديل"
rm -rf "$OLD"
[[ -d $LIVE ]] && mv "$LIVE" "$OLD"
mv "$NEW" "$LIVE" || die "فشل التبديل — الشجرةُ القديمةُ في $OLD"

# ── (3) nginx ────────────────────────────────────────────────────────────────
say "نسخةٌ احتياطيّةٌ من الكتلة الحاليّة ⇐ $BACKUP"
[[ -f $AVAIL ]] && cp -a "$AVAIL" "$BACKUP"

install -o root -g root -m 644 "$STAGE/mihrab.dev.static.conf" "$AVAIL" \
  || die "فشل تركيبُ الكتلة"
# الملفُّ **قبل** الرابط، والرابطُ إلى مسارٍ مطلق: `ln -sf` لا يتحقّق من هدفه،
# فرابطٌ معلَّقٌ يكسر `nginx -t` لكلّ المواقع لا لموقعنا.
ln -sfn "$AVAIL" "$LINK"

if ! nginx -t; then
  echo "⚠️ سقط الاختبار — تراجعٌ تلقائيّ" >&2
  if [[ -f $BACKUP ]]; then cp -a "$BACKUP" "$AVAIL"; else rm -f "$LINK"; fi
  nginx -t && echo "↩️ عاد الإعدادُ سليمًا — لم يسقط شيء" >&2
  die "لم يُنشَر. الشجرةُ الجديدةُ في $LIVE والقديمةُ في $OLD"
fi

systemctl reload nginx || die "فشل تحميلُ nginx"
say "‏nginx حُمِّل"

# ── (4) الخدمةُ لم تعد لها وظيفة ─────────────────────────────────────────────
say "إيقافُ mihrab-web.service وتعطيلها"
systemctl stop mihrab-web    2>/dev/null
systemctl disable mihrab-web 2>/dev/null

echo
echo "✅ نُشِر. تحقّقٌ سريع:"
for p in / /product.web.js /manifest.json /favicon.ico /out/nls.messages.js; do
  printf '   %-28s %s\n' "$p" \
    "$(curl -sk -o /dev/null -w '%{http_code}' -H 'Host: mihrab.dev' "https://127.0.0.1$p")"
done
echo
echo "   الشجرةُ السابقة في $OLD — احذفها بعد التأكّد:  sudo rm -rf $OLD"
