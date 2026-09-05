#!/usr/bin/env bash
# جلبُ أدوات لغة ص من **الإصدار الرسميّ المنشور** لمستودع اللغة، كي يحمل كلُّ نشرٍ لمحراب
# أحدثَ ص رسميّة — بدل الاعتماد على `../sad-engines-dev/` الموجود على جهاز المطوّر وحده.
#
# **العطبُ الذي يعالجه:** لا خطوةَ جلبٍ لأدوات ص في أيّ سير عمل (`grep -rl MIHRAB_SAD .github/`
# ⇒ لا شيء)، و`build.sh` يسقط سقوطًا رشيقًا عند غيابها. فالنسخةُ المبنيّةُ على جهاز مطوّرٍ
# تعمل، والمنشورةُ من CI **بلا لغةٍ أصلًا** — والموقعُ يَعِد بأنّها «جاهزةٌ في الصندوق».
# وهو فرقٌ لا يراه المطوّر لأنّ جهازه مملوء.
#
# الاستعمال:
#   bash build/fetch_sad_tools.sh                  # أحدثُ إصدارٍ رسميّ لهذه المنصّة
#   SAD_TOOLS_TAG=v1.0.0 bash build/fetch_sad_tools.sh
#   source .upstream/.sad-tools/env.sh && bash build/build.sh
#
# الخرج: `.upstream/.sad-tools/` فيه الأدواتُ بأسماء محراب، و`env.sh` للتصدير،
#        و`manifest.json` يسجّل الوسمَ والأصلَ وبصماتِ الملفّات.
# الخروج: 0 حين تُجلَب أداةٌ واحدةٌ على الأقلّ · 3 حين لا أصلَ لهذه المنصّة (ليس فشلًا:
#        المستودعُ لا ينشر لكلّ منصّة بعدُ) · 1 خطأٌ حقيقيّ.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# مفسّرُ بايثون يُحلّ ولا يُفترَض: `python` المجرَّد غائبٌ عن أوبونتو 24.04.
. "$ROOT/build/lib/pybin.sh"
resolve_py_bin || exit 1
REPO="${SAD_TOOLS_REPO:-sadlang/s-programming-language}"
TAG="${SAD_TOOLS_TAG:-}"
OUT="$ROOT/.upstream/.sad-tools"
log() { echo "▶ $*"; }

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT) PLATFORM=windows; EXE=.exe ;;
  Darwin) PLATFORM=mac; EXE= ;;
  *) PLATFORM=linux; EXE= ;;
esac
ARCH="$(uname -m)"; [[ "$ARCH" == "aarch64" ]] && ARCH=arm64
[[ "$ARCH" == "x86_64" ]] && ARCH=x64

# **رموزُ المنصّة متعدّدة عمدًا**: `v1.0.0` سمّى أصلَه `…-windows-x64.zip`، وسيرُ عمل
# الإصدار على الفرع الرئيسيّ اليومَ يسمّي `…-windows-x86_64.zip` و`…-linux-aarch64.tar.gz`.
# فرمزٌ واحدٌ يجعل الجالبَ يخرج بـ3 «لا أصلَ لهذه المنصّة» على إصدارٍ فيه أصلُها — قِسناه
# على أسماء سير العمل المحدَّث. نطابق كلَّ الصيغ المعروفة بدل تخمين واحدة.
TOKENS=()
case "$PLATFORM/$ARCH" in
  windows/x64) TOKENS=(windows-x86_64 windows-x64 win32-x64) ;;
  windows/arm64) TOKENS=(windows-aarch64 windows-arm64) ;;
  linux/x64) TOKENS=(linux-x86_64 linux-x64) ;;
  linux/arm64) TOKENS=(linux-aarch64 linux-arm64) ;;
  mac/x64) TOKENS=(macos-x86_64 macos-x64 mac-x64 darwin-x64) ;;
  mac/arm64) TOKENS=(macos-aarch64 macos-arm64 mac-arm64 darwin-arm64) ;;
esac

command -v gh >/dev/null || { echo "❌ لا gh CLI — لازمٌ لجلب الإصدار الرسميّ." >&2; exit 1; }

if [[ -z "$TAG" ]]; then
  TAG="$(gh release view --repo "$REPO" --json tagName --jq .tagName)"
fi
log "إصدارُ لغة ص الرسميّ: $TAG (من $REPO) · المنصّة: $PLATFORM/$ARCH"

# اختيارُ الأصول: نمطُ المنصّة، و**استبعادُ المثبِّتات** (`sad-setup-*`) — نريد نسخةً محمولةً
# نستخرج منها، لا مثبِّتًا يحتاج تفاعلًا.
#
# و**كلُّ أصولِ المنصّة لا أوّلُها**: سيرُ عمل الإصدار يُخرج ثلاثَ عائلات — `sad-full-*`
# (مفسّرٌ + مترجمٌ + أدوات)، و`sad-v*` (مفسّرٌ وأدواتٌ بلا مترجم)، و`sadc-*` (مترجمٌ وحدَه).
# فأخذُ أوّلِ مطابقٍ قد يقع على `sadc` فيخرج محرابٌ ببناءٍ بلا تشغيل. نستخرجها كلَّها
# بترتيبِ أفضليّةٍ صريح، والخريطةُ أدناه تأخذ أوّلَ موجودٍ لكلّ أداة.
mapfile -t ASSETS < <(gh release view "$TAG" --repo "$REPO" --json assets --jq '.assets[].name')
PICKS=()
for family in "sad-full" "sad" "sadc" ""; do
  for a in "${ASSETS[@]}"; do
    [[ "$a" == sad-setup-* ]] && continue
    [[ -n "$family" && "$a" != "$family"-* ]] && continue
    case "$a" in *.zip|*.tar.gz|*.tar.xz) ;; *) continue ;; esac
    hit=""
    for tok in "${TOKENS[@]}"; do [[ "$a" == *"$tok"* ]] && hit=1 && break; done
    [[ -z "$hit" ]] && continue
    [[ " ${PICKS[*]-} " == *" $a "* ]] && continue
    PICKS+=("$a")
  done
done
if ((${#PICKS[@]} == 0)); then
  echo "⚠️ لا أصلَ لهذه المنصّة في $TAG (المتاح: ${ASSETS[*]:-لا شيء})." >&2
  echo "   محرابُ هذه المنصّة سيُبنى **بلا أدوات ص**. انشر أصلًا باسمٍ يحوي أحدَ: ${TOKENS[*]}." >&2
  exit 3
fi
log "الأصول المختارة (${#PICKS[@]}): ${PICKS[*]}"

rm -rf "$OUT"; mkdir -p "$OUT/raw" "$OUT/bin"
EX="$OUT/raw/ex"; mkdir -p "$EX"
i=0
for PICK in "${PICKS[@]}"; do
  i=$((i + 1)); DEST="$EX/$i"; mkdir -p "$DEST"
  gh release download "$TAG" --repo "$REPO" --pattern "$PICK" --dir "$OUT/raw" --clobber
  case "$PICK" in
    # ‏`unzip` يعيد 1 على **تحذير** لا على فشل — وأرشيفُ الإصدار الرسميّ يُطلق تحذيرَ
    # «backslashes as path separators» (أُنشئ على ويندوز). تحت `set -e` كان ذلك يُسقِط
    # الجلبَ صامتًا بعد تنزيلٍ ناجح. فنقبل 0 و1 ونرفض ما فوقهما.
    *.zip) ( cd "$OUT/raw" && unzip -o -q "$PICK" -d "ex/$i" ) || [[ $? -le 1 ]] ;;
    *.tar.gz|*.tar.xz) tar -xf "$OUT/raw/$PICK" -C "$DEST" ;;
  esac
done

# ── الخريطة: اسمُ محرابٍ ⇐ أوّلُ موجودٍ من مرشّحي الإصدار ──
# الاسمُ المطابقُ أوّلًا، ثمّ أسماءُ `v1.0.0`: `sad` مُشغِّلٌ و`sadc` مترجم. والفرعُ الرئيسيّ
# اليومَ يبني الأربعةَ بأسمائها المطابقة (‏`OUTPUT_NAME` في apps/ وtools/check وtools/lsp)،
# فأوّلُ إصدارٍ يُوسَم منه يُلتقط بلا تعديلٍ هنا.
declare -A CANDIDATES=(
  [sad-run]="sad-run sad"
  [sad-build]="sad-build sadc"
  [sad-check]="sad-check"
  [sad-lsp]="sad-lsp"
)
declare -A ENVVAR=(
  [sad-run]=MIHRAB_SAD_RUN [sad-build]=MIHRAB_SAD_BUILD
  [sad-check]=MIHRAB_SAD_CHECK [sad-lsp]=MIHRAB_SAD_LSP
)

: > "$OUT/env.sh"
FOUND=0; MISSING=()
for tool in sad-run sad-build sad-check sad-lsp; do
  src=""
  # الأصلُ الأعلى أفضليّةً أوّلًا (‏`$EX/1` = `sad-full` حين يُنشَر)، ثمّ الاسمُ الأدقّ.
  for cand in ${CANDIDATES[$tool]}; do
    for d in $(seq 1 ${#PICKS[@]}); do
      hit="$(find "$EX/$d" -maxdepth 4 -type f -name "$cand$EXE" -print -quit 2>/dev/null || true)"
      [[ -n "$hit" ]] && { src="$hit"; break 2; }
    done
  done
  if [[ -z "$src" ]]; then MISSING+=("$tool"); continue; fi
  cp -f "$src" "$OUT/bin/$tool$EXE"
  chmod +x "$OUT/bin/$tool$EXE" 2>/dev/null || true
  echo "export ${ENVVAR[$tool]}='$OUT/bin/$tool$EXE'" >> "$OUT/env.sh"
  log "‏$tool$EXE ⇐ $(basename "$src") ($(du -h "$OUT/bin/$tool$EXE" | cut -f1))"
  FOUND=$((FOUND + 1))
done

# حمولةٌ مجاورة: المكتبةُ القياسيّة ومكتباتُ التشغيل. `sad.exe` يعمل بلا SDL2 لبرنامجٍ
# نصّيّ (قِسناه)، لكنّ استيرادَ المكتبة القياسيّة وتوليدَ الواجهات يحتاجانهما.
for extra in stdlib SDL2.dll; do
  # تُبحث لا تُفترض: `v1.0.0` وضعها في جذر الأرشيف، وحزمُ الفرع الرئيسيّ تضعها تحت
  # مجلّدٍ باسم الحزمة (`sad-full-v…/stdlib`). مسارٌ ثابتٌ كان يفقدها صامتًا.
  hit="$(find "$EX" -maxdepth 4 -name "$extra" -print -quit 2>/dev/null || true)"
  [[ -n "$hit" ]] && cp -rf "$hit" "$OUT/bin/" && log "حمولةٌ مجاورة: $extra"
done
[[ -d "$OUT/bin/stdlib" || -f "$OUT/bin/SDL2.dll" ]] && \
  echo "export MIHRAB_SAD_PAYLOAD='$OUT/bin'" >> "$OUT/env.sh"

if ((FOUND == 0)); then
  echo "❌ لم تُطابَق أيُّ أداةٍ داخل ${PICKS[*]} — تغيّرت أسماءُ ملفّات الإصدار؟" >&2
  exit 1
fi

"$PY_BIN" - "$OUT" "$REPO" "$TAG" "$(IFS=,; echo "${PICKS[*]}")" <<'PY'
import hashlib, json, os, sys
out, repo, tag, asset = sys.argv[1:5]
bins = {}
for f in sorted(os.listdir(os.path.join(out, "bin"))):
    p = os.path.join(out, "bin", f)
    if os.path.isfile(p):
        bins[f] = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
json.dump({"repo": repo, "tag": tag, "asset": asset, "tools": bins},
          open(os.path.join(out, "manifest.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
PY

echo "✅ أدواتُ ص $TAG جاهزة: $FOUND/4 (${MISSING[*]:-لا نقص})"
# الأثرُ يُذكر بأداته: نقصُ `sad-build` على macOS/Intel مثلًا يعني «بلا ترجمة» لا
# «بلا إكمال» — ورسالةٌ واحدةٌ لكلّ الحالات كانت تقول الخطأ في أكثرها.
declare -A LOSS=(
  [sad-run]="تشغيلِ البرامج" [sad-build]="الترجمةِ إلى تنفيذيّ"
  [sad-check]="التشخيصِ" [sad-lsp]="الإكمالِ وذكاءِ المحرّر"
)
if [[ ${#MISSING[@]} -gt 0 ]]; then
  loss=""; for m in "${MISSING[@]}"; do loss+="${loss:+ و}${LOSS[$m]}"; done
  echo "   ⚠️ غيرُ منشورٍ في الإصدار الرسميّ: ${MISSING[*]} — محرابُ هذه المنصّة بلا $loss حتّى يُنشَر."
fi
echo "   للاستعمال: source ${OUT#$ROOT/}/env.sh"
exit 0
