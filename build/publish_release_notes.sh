#!/usr/bin/env bash
# نشرُ ملاحظات الإصدار على mihrab.dev — يقرؤها محرِّرُ الملاحظات داخل التطبيق.
#
#   build/publish_release_notes.sh 1.126          # ينشر release-notes/v1_126.md
#   build/publish_release_notes.sh 1.126 1.125    # عدّةُ إصداراتٍ في نداءٍ واحد
#
# الوجهة: `<جذر الملاحظات>/v<كبير>_<صغير>.md` — وهو ما يطلبه `releaseNotesEditor.ts`
# بعد رقعة النواة ‎036‎: `<releaseNotesBaseUrl>/v<كبير>_<صغير>.md`، والقاعدةُ في
# `product-overrides/product.json`. من غيّر إحداهما فليغيّر الأخرى وكتلةَ
# `location /notes/` في `deploy/nginx/mihrab.dev.static.conf` — وإلّا جلب المحرِّرُ ‎404‎
# وارتدّ بالقارئ إلى صفحة الإصدارات في المتصفّح.
#
# **المجلّدُ خارج جذر الحمولة عمدًا** (`/opt/mihrab/notes` لا `/opt/mihrab/static/notes`):
# النشرُ الثابت يبدّل جذرَ الحمولة كتلةً واحدةً ذرّيًّا، فملاحظاتٌ داخله تختفي مع أوّل
# نشرِ بناءٍ لا يحملها. وعمرُ الملاحظات أطولُ من عمر الحمولة: تُنشَر مرّةً وتبقى لكلّ
# بناءٍ من الإصدار نفسِه، ويقرؤها من لم يحدّث بعد.
set -euo pipefail

# ⚠️ لا مضيفَ افتراضيًّا في مستودعٍ عامّ — انظر التعليل في deploy_site.sh.
HOST="${MIHRAB_NOTES_HOST:-${MIHRAB_SITE_HOST:?عيّن MIHRAB_NOTES_HOST أو MIHRAB_SITE_HOST (مثال: user@host)}}"
PORT="${MIHRAB_SITE_PORT:-22}"
DEST="${MIHRAB_NOTES_ROOT:-/opt/mihrab/notes}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$HERE/release-notes"
SSH=(ssh -p "$PORT" -o BatchMode=yes)

(( $# >= 1 )) || { echo "الاستعمال: $0 <الإصدار> [<الإصدار> …]   (مثال: 1.126)" >&2; exit 2; }

# التحقّقُ من الجميع **قبل** رفعِ أيٍّ منهم: نشرٌ نصفيٌّ يترك إصدارًا منشورًا وآخرَ لا،
# وهو أسوأُ من رفضٍ مبكّرٍ لا يغيّر شيئًا على الخادم.
FILES=()
for v in "$@"; do
  [[ "$v" =~ ^[0-9]+\.[0-9]+$ ]] || { echo "❌ صيغةُ إصدارٍ غيرُ مقبولة: $v (المتوقَّع: كبير.صغير مثل 1.126)" >&2; exit 1; }
  name="v${v//./_}.md"
  path="$SRC/$name"
  [[ -f "$path" ]] || { echo "❌ لا ملفَّ ملاحظاتٍ: release-notes/$name" >&2; exit 1; }
  # المحرِّرُ يرفض النصَّ الذي لا يبدأ بـ`#` ثمّ فراغ (`Invalid release notes`) ويرتدّ
  # إلى المتصفّح. فيُرفَض هنا لا هناك: خطأُ نشرٍ أوضحُ من صفحةٍ لا تفتح عند القارئ.
  head -c 2 "$path" | grep -q '^# ' || { echo "❌ $name لا يبدأ بـ«# » — سيرفضه المحرِّرُ بـInvalid release notes" >&2; exit 1; }
  FILES+=("$name:$path")
done

"${SSH[@]}" "$HOST" "mkdir -p '$DEST'"

for entry in "${FILES[@]}"; do
  name="${entry%%:*}"; path="${entry#*:}"
  echo "▶ رفع $name …"
  # الرفعُ إلى اسمٍ مؤقّت ثمّ تسميةٌ ذرّيّة: رفعٌ ينقطع في المنتصف يجب ألّا يترك نصًّا
  # نصفَ مكتملٍ يحمل الاسمَ النهائيّ ويُقدَّم للقرّاء. وscp لا rsync: أجهزةُ البناء هنا
  # ويندوز، وrsync ليس في Git Bash.
  scp -P "$PORT" -o BatchMode=yes "$path" "$HOST:$DEST/.$name.part"
  "${SSH[@]}" "$HOST" "chmod 644 '$DEST/.$name.part' && mv '$DEST/.$name.part' '$DEST/$name'"
  size=$("${SSH[@]}" "$HOST" "stat -c%s '$DEST/$name'")
  sha=$("${SSH[@]}" "$HOST" "sha256sum '$DEST/$name' | cut -d' ' -f1")
  echo "   $size بايت · $sha"
done

echo "✅ منشورةٌ في $DEST"
echo
echo "   تحقَّقْ كما يطلبها التطبيقُ نفسُه (لا كما تبدو في المتصفّح):"
for entry in "${FILES[@]}"; do
  echo "   curl -sS -D- -o/dev/null https://mihrab.dev/notes/${entry%%:*}"
done
echo "   المتوقَّع: 200 و‏Content-Type: text/markdown; charset=utf-8"
