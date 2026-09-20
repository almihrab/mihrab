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

# مفسّرُ بايثون يُحلّ ولا يُفترَض: `python` المجرَّد غائبٌ عن أوبونتو 24.04.
. "$HERE/build/lib/pybin.sh"
resolve_py_bin || exit 1

# **القاعدةُ تُقرأ من الهويّة ولا تُكتب هنا ثانيةً.** هي العنوانُ الذي يطلبه التطبيقُ فعلًا،
# ونسخةٌ ثانيةٌ منه في سكربتٍ تنحرف بصمتٍ يومَ يتغيّر النطاق — فيتحقّق الناشرُ من عنوانٍ لم
# يعد أحدٌ يطلبه، ويُعلِن نجاحًا لا يصف شيئًا.
BASE=$("$PY_BIN" - "$HERE/product-overrides/product.json" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8")).get("releaseNotesBaseUrl", ""))
PY
)
[[ -n "$BASE" ]] || { echo "❌ لا releaseNotesBaseUrl في product-overrides/product.json — لا عنوانَ يُتحقَّق منه" >&2; exit 1; }

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
  head -c 2 "$path" | grep -q '^#[[:space:]]' || { echo "❌ $name لا يبدأ بـ«#» ثمّ فراغ — سيرفضه المحرِّرُ بـInvalid release notes" >&2; exit 1; }
  # **تاريخُ الإصدار يُقاس هنا لأنّه لا يُقاس في أيّ مكانٍ آخر.**
  # يُكتَب سطرُ التاريخ يومَ تُكتَب الملاحظاتُ — وهو غالبًا **قبل** يوم النشر بأسابيع،
  # فيُنشَر مستندٌ يُعلِن تاريخًا لم يحدث فيه شيء. ولا يمسكه شيء: الملفُّ نصٌّ سليم،
  # ويبدأ بـ«# »، ويُصيَّر عند القارئ صحيحًا — بتاريخٍ كاذب. أُوقِع فعلًا: كُتِب
  # «14 سبتمبر» وكان النشرُ المزمَع بعده.
  #
  # واللحظةُ الوحيدةُ التي يُعرَف فيها تاريخُ الإصدار هي **لحظةُ النشر نفسِها** — وهي
  # هذه. فالبوّابةُ ترفض ولا تُصحّح: كتابةُ التاريخ في الملفّ تُبقي المصدرَ والمنشورَ
  # نسخةً واحدة، وتصحيحٌ صامتٌ عند الرفع يجعلهما نسختين تفترقان بلا أثر.
  "$PY_BIN" - "$path" "$name" <<'PYDATE' || exit 1
import io, re, sys, datetime
path, name = sys.argv[1], sys.argv[2]
AR = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
      "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
text = io.open(path, encoding="utf-8").read()
m = re.search(r"تاريخ الإصدار:\s*(\d{1,2})\s+(\S+)\s+(\d{4})", text)
if not m:
    sys.stderr.write("\u274c %s بلا سطر «تاريخ الإصدار: <يوم> <شهر> <سنة>» — لا تاريخَ يُقاس\n" % name)
    sys.exit(1)
day, month, year = int(m.group(1)), m.group(2), int(m.group(3))
if month not in AR:
    sys.stderr.write("\u274c %s: شهرٌ غيرُ معروف «%s»\n" % (name, month))
    sys.exit(1)
stamped = datetime.date(year, AR.index(month) + 1, day)
today = datetime.date.today()
if stamped != today:
    sys.stderr.write(
        "\u274c %s يُعلِن تاريخَ إصدارٍ غيرَ اليوم: %s (اليوم %s)\n"
        "   الملاحظاتُ تُنشَر اليومَ، فهذا التاريخُ يصل القارئَ كاذبًا.\n"
        "   صحّحِ السطرَ في release-notes/%s ثمّ أعِد النشر.\n" % (name, stamped, today, name))
    sys.exit(1)
PYDATE

  FILES+=("$name:$path")
done

"${SSH[@]}" "$HOST" "mkdir -p '$DEST'"

# **يُرفَع الجميعُ أوّلًا ثمّ يُسمَّى الجميعُ معًا.** الرفعُ الذرّيُّ لملفٍّ واحدٍ لا يجعل
# النشرةَ ذرّيّة: انقطاعُ شبكةٍ بعد الأوّلِ من ثلاثةٍ يخرج بـ`set -e` تاركًا بالضبط الحالةَ
# التي تتجنّبها البوّابةُ أعلاه — إصدارٌ منشورٌ وآخرُ لا. وscp لا rsync: أجهزةُ البناء هنا
# ويندوز، وrsync ليس في Git Bash. والاسمُ المؤقّتُ يحمي القارئَ من نصٍّ نصفِ مكتمل.
RENAMES=""
for entry in "${FILES[@]}"; do
  name="${entry%%:*}"; path="${entry#*:}"
  echo "▶ رفع $name …"
  scp -P "$PORT" -o BatchMode=yes "$path" "$HOST:$DEST/.$name.part"
  RENAMES="$RENAMES chmod 644 '$DEST/.$name.part' && mv '$DEST/.$name.part' '$DEST/$name' &&"
done
"${SSH[@]}" "$HOST" "${RENAMES% &&}"

for entry in "${FILES[@]}"; do
  name="${entry%%:*}"
  size=$("${SSH[@]}" "$HOST" "stat -c%s '$DEST/$name'")
  sha=$("${SSH[@]}" "$HOST" "sha256sum '$DEST/$name' | cut -d' ' -f1")
  echo "   $name · $size بايت · $sha"
done

# **ويُتحقَّق كما يطلبها التطبيقُ لا كما تبدو في المتصفّح — تحقّقًا يفشل، لا سطرًا يُطبَع.**
# وجودُ الملفّ على القرص لا يعني أنّه يُخدَم: كتلةُ `location /notes/` قد تكون غيرَ منشورةٍ
# فيلتقط الطلبَ موضعٌ آخرُ ويردّ ‎404‎ — قِيس حيًّا على mihrab.dev يومَ كُتب هذا. والنوعُ يهمّ
# بقدر الرمز: مع `nosniff` يصير النصُّ تنزيلًا لا صفحةً تُقرأ في نسخة المتصفّح.
# **ويُطلَب بأصلِ التطبيق لا بـcurl عارٍ.** الجلبُ يجري في عارضِ محراب وأصلُه
# `vscode-file://vscode-app`، أي طلبٌ عابرُ أصلٍ تحكمه CORS. و`curl` بلا أصلٍ لا يخضع لها
# فيخضرّ على خادمٍ يسقط عنده التطبيق — قِيس حيًّا: `mihrab.dev` ردّ ‎200‎ لـcurl وسقط داخل
# محراب بـ`Failed to fetch`. فيُطلَب هنا كما يُطلَب هناك، وتُشترَط الترويسةُ في الردّ.
ORIGIN_HDR='vscode-file://vscode-app'
echo "▶ التحقّق من $BASE (بأصل $ORIGIN_HDR) …"
bad=0
for entry in "${FILES[@]}"; do
  name="${entry%%:*}"
  hdrs=$(curl -sS -D- -o /dev/null --max-time 20 -H "Origin: $ORIGIN_HDR" "$BASE/$name" 2>/dev/null | tr -d "\r" || true)
  code=$(printf '%s' "$hdrs" | awk 'NR==1{print $2}')
  ctype=$(printf '%s' "$hdrs" | awk -F': ' 'tolower($1)=="content-type"{print tolower($2)}' | tail -1)
  acao=$(printf '%s' "$hdrs" | awk -F': ' 'tolower($1)=="access-control-allow-origin"{print $2}' | tail -1)
  if [[ "$code" == 200 && "$ctype" == text/markdown* && ( "$acao" == '*' || "$acao" == "$ORIGIN_HDR" ) ]]; then
    echo "   ✅ $name — $code · $ctype · ACAO=$acao"
  else
    echo "   ❌ $name — ${code:-بلا ردّ} · ${ctype:-بلا نوع} · ACAO=${acao:-غائبة}" >&2
    bad=1
  fi
done

(( bad == 0 )) || { echo "❌ مرفوعٌ ولا يُخدَم: انشرْ كتلةَ location /notes/ من deploy/nginx (ثمّ nginx -t وإعادةُ التحميل)" >&2; exit 1; }

echo "✅ منشورةٌ ومخدومةٌ من $BASE"
