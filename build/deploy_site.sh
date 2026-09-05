#!/usr/bin/env bash
# نشرُ موقع محراب على خادمنا → https://sad-lang.org/mihrab/
#
# لماذا خادمنا لا GitHub Pages وحده؟ الثنائيّات. مثبِّتُ محراب يقارب ٣٠٠ ميغابايت،
# وGitHub Pages لا يستضيف مخرجاتِ بناءٍ أصلًا (والمستودعُ ليس مخزنَ ملفّات). والخادمُ
# يملك ٥٤٦ غيغابايت حرّة وعرضَ نطاقٍ لنا، والنطاقُ `sad-lang.org` نطاقُ العائلة نفسِها
# — فمحرابٌ يسكن مع لغة ص لا في جزيرةٍ اسمُها `github.io`.
#
# وGitHub Pages يبقى **مرآةً** ينشرها CI من المولِّد نفسِه، فلا انجرافَ بين النسختين.
#
# ⚠️ ثلاثةُ قيودٍ يفرضها الخادم، وكلُّها مقصودةٌ في هذا السكربت:
#   ١) لا sudo بلا كلمةِ مرور ⇒ لا vhost جديد ولا شهادةَ نطاقٍ فرعيّ. ولا حاجة:
#      كتلةُ `location /` في vhost القائم فيها `try_files $uri $uri/`، فأيّ مجلّدٍ
#      فرعيّ تحت /opt/sad-website يُخدَم فورًا بشهادةِ sad-lang.org نفسِها.
#   ٢) `dl/` **مستثنى من --delete**: الثنائيّات تُرفَع مرّةً وتبقى، وبناءُ الموقع لا
#      يعرف بها. بلا هذا الاستثناء يمسح أوّلُ نشرٍ كلَّ ملفّاتِ التنزيل.
#   ٣) النقلُ إلى مجلّدٍ مؤقّت ثمّ تبديلٌ ذرّيّ: rsync مباشرةً على المجلّد الحيّ يترك
#      الزائرَ في منتصف النقل أمام صفحةٍ بأصولٍ ناقصة.
set -euo pipefail

# ⚠️ لا قيمةَ افتراضيّة للمضيف: المستودعُ عامّ، واسمُ مستخدمٍ ومنفذٌ غيرُ قياسيٍّ
# مكتوبان في الشيفرة استطلاعٌ مجّانيٌّ لمن يقرأ. ليسا سرًّا، لكنّ نشرَهما لا يفيد
# أحدًا إلّا من يبحث عن بابٍ يطرقه. الناشرُ يعرف مضيفَه فليمرّره:
#   MIHRAB_SITE_HOST=user@host bash build/deploy_site.sh
HOST="${MIHRAB_SITE_HOST:?عيّن MIHRAB_SITE_HOST (مثال: user@host)}"
PORT="${MIHRAB_SITE_PORT:-22}"
ROOT="${MIHRAB_SITE_ROOT:-/opt/sad-website}"
SUB="${MIHRAB_SITE_SUBDIR:-mihrab}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# مفسّرُ بايثون يُحلّ ولا يُفترَض: `python` المجرَّد غائبٌ عن أوبونتو 24.04.
. "$HERE/build/lib/pybin.sh"
resolve_py_bin || exit 1
PUB="$HERE/site/public"

SSH=(ssh -p "$PORT" -o BatchMode=yes)

echo "▶ بناءُ الموقع…"
"$PY_BIN" "$HERE/site/build.py"

[[ -f "$PUB/index.html" ]] || { echo "❌ لا مخرَجَ في $PUB" >&2; exit 1; }

DEST="$ROOT/$SUB"
STAGE="$ROOT/.$SUB.new"

echo "▶ النقلُ إلى $HOST:$STAGE …"
"${SSH[@]}" "$HOST" "rm -rf '$STAGE' && mkdir -p '$STAGE' '$DEST/dl'"

# نبذر المرحلةَ بـ dl/ الحاليّ (روابطٌ صلبة، بلا نقلِ غيغابايتات) كي يصير التبديل
# ذرّيًّا فعلًا: مجلّدٌ جديدٌ كاملٌ يحلّ محلَّ القديم دفعةً واحدة.
"${SSH[@]}" "$HOST" "cp -al '$DEST/dl' '$STAGE/dl' 2>/dev/null || cp -a '$DEST/dl' '$STAGE/dl'"

# tar عبر الأنبوب لا rsync: أجهزةُ التطوير هنا ويندوز، وrsync ليس في Git Bash.
# ولا حاجةَ إلى `--delete` أصلًا — المرحلةُ تبدأ فارغةً إلّا من `dl/`، فالفكُّ فيها
# يعطي دلالةَ الحذف مجّانًا: ما لم يُبنَ هذه المرّة ليس موجودًا هناك.
tar -C "$PUB" -czf - . | "${SSH[@]}" "$HOST" "tar -C '$STAGE' -xzf -"

echo "▶ التبديلُ الذرّيّ…"
"${SSH[@]}" "$HOST" "rm -rf '$ROOT/.$SUB.old' && mv '$DEST' '$ROOT/.$SUB.old' 2>/dev/null || true; mv '$STAGE' '$DEST' && rm -rf '$ROOT/.$SUB.old'"

echo "✅ نُشر: https://sad-lang.org/$SUB/"
echo "   الثنائيّات:  $DEST/dl/   (لم تُمَسّ)"
