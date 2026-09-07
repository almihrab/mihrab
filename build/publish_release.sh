#!/usr/bin/env bash
# رفعُ بناءٍ إلى صفحة التنزيل — https://sad-lang.org/mihrab/download/
#
#   build/publish_release.sh 1.121.05071 win-x64-zip:/c/out/Mihrab-1.121-win-x64.zip \
#                                        win-x64-setup:/c/out/MihrabSetup-1.121.exe
#
# كلُّ وسيطٍ `معرّف_المنصّة:مسار`. المعرّفاتُ المسموحة هي `id` في
# site/data/site.json (win-x64-setup ‏· win-x64-zip ‏· linux-x64-deb …) — ومعرّفٌ
# خارجَها يوقف السكربت: أصلٌ بمعرّفٍ مجهول يظهر في الجدول بلا اسمِ منصّةٍ ولا نوع،
# فيرى الزائر صفًّا مبهمًا ويُنزّل شيئًا لا يعرف ما هو.
#
# ما يفعله: يرفع الملفّات إلى `dl/`، يحسب SHA-256 **على الخادم بعد الرفع** (لا
# محلّيًّا: البصمةُ يجب أن تصف ما وصل لا ما غادر — وهذا كلُّ معنى نشرِها)، ثمّ يكتب
# `dl/releases.json` ذرّيًّا. الصفحةُ تلتقط الجديدَ في أوّل تحميلٍ بلا إعادةِ بناء.
set -euo pipefail

# ⚠️ لا مضيفَ افتراضيًّا في مستودعٍ عامّ — انظر التعليل في deploy_site.sh.
HOST="${MIHRAB_SITE_HOST:?عيّن MIHRAB_SITE_HOST (مثال: user@host)}"
PORT="${MIHRAB_SITE_PORT:-22}"
# قناةٌ فرعيّةٌ داخل dl/ لبناءٍ ليس إصدارًا (معاينةٌ للتجريب مثلًا): تُعزَل
# ملفّاتُها ومانيفستُها عن الإصدار المنشور، فلا يلتقط جدولُ التنزيلِ الرئيس
# بناءً تجريبيًّا، ولا يمسح رفعُ معاينةٍ مانيفستَ الإصدار.
DL="${MIHRAB_SITE_ROOT:-/opt/sad-website}/${MIHRAB_SITE_SUBDIR:-mihrab}/dl${MIHRAB_DL_CHANNEL:+/$MIHRAB_DL_CHANNEL}"
# قاعدةُ الروابط في المانيفست مربوطةٌ بالقناة، لا متغيّرٌ مستقلٌّ يُنسى: من رفع
# بقناةٍ ونسي القاعدةَ كتب في مانيفست المعاينة `"base":"dl/"` — فتُعرَض الصفحةُ
# كاملةً وكلُّ زرِّ تنزيلٍ فيها 404. وفشلٌ صريحٌ هنا أرخصُ من جدولٍ يبدو سليمًا.
if [[ -n "${MIHRAB_DL_CHANNEL:-}" ]]; then
  BASE="${MIHRAB_DL_BASE:?قناةٌ بلا قاعدةِ روابط: عيّن MIHRAB_DL_BASE (مثال: ../../dl/$MIHRAB_DL_CHANNEL/)}"
else
  BASE="${MIHRAB_DL_BASE:-dl/}"
fi
ORIGIN="${MIHRAB_SITE_ORIGIN:-https://sad-lang.org/mihrab/}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# مفسّرُ بايثون يُحلّ ولا يُفترَض: `python` المجرَّد غائبٌ عن أوبونتو 24.04.
. "$HERE/build/lib/pybin.sh"
resolve_py_bin || exit 1
SSH=(ssh -p "$PORT" -o BatchMode=yes)

(( $# >= 2 )) || { echo "الاستعمال: $0 <الإصدار> <معرّف:مسار> [معرّف:مسار …]" >&2; exit 2; }
VERSION="$1"; shift

VALID=$("$PY_BIN" - "$HERE/site/data/site.json" <<'PY'
import json, sys
print(" ".join(p["id"] for p in json.load(open(sys.argv[1], encoding="utf-8"))["platforms"]))
PY
)

"${SSH[@]}" "$HOST" "mkdir -p '$DL'"

ENTRIES=()
for arg in "$@"; do
  id="${arg%%:*}"; path="${arg#*:}"
  [[ " $VALID " == *" $id "* ]] || { echo "❌ معرّفُ منصّةٍ مجهول: $id" >&2
                                     echo "   المسموح: $VALID" >&2; exit 1; }
  [[ -f "$path" ]] || { echo "❌ ملفٌّ غير موجود: $path" >&2; exit 1; }

  file="$(basename "$path")"
  # scp لا rsync: rsync ليس في Git Bash على ويندوز، وهذه أجهزةُ البناء عندنا.
  # الرفعُ إلى اسمٍ مؤقّت ثمّ تسميةٌ ذرّيّة: رفعٌ ينقطع في المنتصف يجب ألّا يترك
  # ملفًّا نصفَ مكتملٍ يحمل الاسمَ النهائيّ ويُقدَّم للزوّار.
  echo "▶ رفع $file …"
  scp -P "$PORT" -o BatchMode=yes "$path" "$HOST:$DL/.$file.part"
  "${SSH[@]}" "$HOST" "mv '$DL/.$file.part' '$DL/$file'"

  size=$("${SSH[@]}" "$HOST" "stat -c%s '$DL/$file'")
  sha=$("${SSH[@]}" "$HOST" "sha256sum '$DL/$file' | cut -d' ' -f1")
  echo "   $size بايت · $sha"
  ENTRIES+=("{\"id\":\"$id\",\"file\":\"$file\",\"size\":$size,\"sha256\":\"$sha\"}")
done

TODAY=$(date +%F)
JOINED=$(IFS=,; echo "${ENTRIES[*]}")
MANIFEST="{\"version\":\"$VERSION\",\"date\":\"$TODAY\",\"origin\":\"$ORIGIN\",\"base\":\"$BASE\",\"notes_url\":\"https://github.com/sadlang/mihrab/releases\",\"assets\":[$JOINED]}"

echo "▶ كتابةُ المانيفست…"
printf '%s' "$MANIFEST" | "${SSH[@]}" "$HOST" "cat > '$DL/.releases.json.new' && mv '$DL/.releases.json.new' '$DL/releases.json'"

echo "✅ الإصدار $VERSION منشور في $DL"
echo
echo "   لتُثبِت الحالةَ في المستودع (كي تصدق المرآةُ وحالةُ انقطاع الشبكة):"
echo "   انسخ المانيفست أعلاه إلى site/data/releases.json ثمّ ادفعه."
