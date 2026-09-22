#!/usr/bin/env bash
# تغليفُ مخرَج البناء إلى **أصولِ تنزيلٍ** بأسماءِ مانيفست الموقع.
#
#   build/package_assets.sh win-x64-zip win-x64-setup
#   build/package_assets.sh linux-x64-tar linux-x64-deb linux-x64-rpm
#   build/package_assets.sh mac-arm64
#
# يُشغَّل **بعد** `build/build.sh` وفي المنصّة نفسِها (لا تغليفَ عابرَ منصّة: حزمةُ
# دبيان تُبنى بأدوات دبيان، والمثبِّتُ بـInno على ويندوز).
#
# ── لماذا ملفٌّ مستقلّ ──
# كان التغليفُ سطرَي `case` داخل `build-matrix.yml`: أرشيفٌ واحدٌ لكلّ منصّة. فكانت
# صفحةُ التنزيل تُعلِن **ثمانيَ** منصّاتٍ ولا يُبنى منها إلّا **ثلاث**، وخمسةُ صفوفٍ
# رماديّةٍ تقول «لم يُبنَ بعد» — أي أنّ أغلبَ الجدول «لا». والصياغةُ في سير عملٍ
# ‏YAML لا تُختبَر محلّيًّا ولا يحرسها حارس.
#
# فصار المُغلِّفُ سكربتًا واحدًا: يُقرأ، ويُشغَّل على جهاز مطوّر، **ويحرسه [PKG-01]**
# الذي يشترط أن يكون لكلّ `id` في `site/data/site.json` فرعُ تغليفٍ هنا. فمن أضاف
# منصّةً إلى الصفحة ولم يبنِها يحمرّ في L0 لا عند الزائر.
#
# ── وصفةُ التغليف مأخوذةٌ من VSCodium لا مخترَعة ──
# `.upstream/build/{linux,windows}/prepare_assets.sh` هي المرجع: مهامُّ gulp نفسُها
# وبالترتيب نفسِه. وما لا نشحنه (‏AppImage ‏· snap ‏· MSI) متروكٌ عمدًا لا سهوًا.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UP="$HERE/.upstream"
DIST="${MIHRAB_DIST:-$HERE/dist}"

. "$HERE/build/lib/pybin.sh"
resolve_py_bin || exit 1

# المنصّةُ تُكشَف كما يكشفها `build.sh` حرفًا بحرف — ومصدرُ ذلك `build.sh --platform`
# لا نسخةٌ ثانيةٌ من المنطق هنا: نسختان تنحرفان بصمتٍ يومَ يتغيّر الكشف، فيُغلَّف
# مخرَجٌ لمنصّةٍ ويُسمّى باسم أخرى.
read -r _PLAT _OUTKV <<<"$(bash "$HERE/build/build.sh" --platform)"
OS_NAME="${_PLAT%%/*}"
VSCODE_ARCH="${_PLAT##*/}"
OUT_NAME="${_OUTKV#out=}"
OUT="$UP/$OUT_NAME"
export VSCODE_ARCH

[[ -d "$OUT" ]] || { echo "❌ لا مخرَجَ بناءٍ في $OUT — شغّل build/build.sh أوّلًا" >&2; exit 1; }
(( $# >= 1 )) || { echo "الاستعمال: $0 <معرّف-أصل> [معرّف-أصل …]" >&2; exit 2; }

# ── الإصدارُ يُقرأ من الهويّة المشحونة لا يُمرَّر ──
# هو ما يراه المستخدمُ في «حول»، وأيُّ مصدرٍ آخرَ يمكن أن ينحرف عنه — فيحمل اسمُ
# الملفّ إصدارًا غيرَ الذي بداخله، وتصير البصمةُ المنشورةُ تصف شيئًا آخر.
APP_PJ="$(find "$OUT" -path '*/[Rr]esources/app/product.json' -print -quit)"
[[ -n "$APP_PJ" ]] || { echo "❌ لم يُعثر على product.json المشحون في $OUT" >&2; exit 1; }
VERSION="$("$PY_BIN" -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8'))['version'])" "$APP_PJ")"
SUFFIX="${MIHRAB_ASSET_SUFFIX:-}"      # «‎-alif» لبناء المعاينة
STEM="Mihrab-$VERSION$SUFFIX"

mkdir -p "$DIST"

# المعرّفاتُ المسموحة تُقرأ من الصفحة لا تُكتَب هنا: معرّفٌ لا تعرفه الصفحةُ يُنتِج
# أصلًا لا يظهر في الجدول، ومعرّفٌ تعرفه الصفحةُ ولا نعرفه يُنتِج صفًّا رماديًّا.
VALID="$("$PY_BIN" - "$HERE/site/data/site.json" <<'PY'
import json, sys
print(" ".join(p["id"] for p in json.load(open(sys.argv[1], encoding="utf-8"))["platforms"]))
PY
)"

# ‏gulp داخل شجرة المنبع: المهامُّ تقرأ `product.json` المرقَّعَ هناك و`../VSCode-*`.
gulp_task() {
  echo "▶ gulp $1 …"
  ( cd "$UP/vscode" && npm run gulp "$1" )
}

# نقلُ ناتجٍ واحدٍ إلى `dist/` باسمِ المانيفست. الصرامةُ مقصودة: صفرُ ملفّاتٍ أو
# أكثرُ من واحدٍ يعني أنّ المهمّةَ غيّرت مخرَجَها — وتخمينُ «الأوّلِ أبجديًّا» هنا
# يشحن حزمةَ بناءٍ سابقٍ بهدوء.
take_one() {
  local glob="$1" dest="$2" n
  # shellcheck disable=SC2086
  n=$(ls -1 $glob 2>/dev/null | wc -l)
  (( n == 1 )) || { echo "❌ تُوقِّع ناتجٌ واحدٌ من «$glob» فوُجد $n" >&2
                    # shellcheck disable=SC2086
                    ls -la $glob 2>/dev/null || true; exit 1; }
  # shellcheck disable=SC2086
  mv $glob "$DIST/$dest"
  echo "   ✅ $dest  ($(du -h "$DIST/$dest" | cut -f1))"
}

want() { [[ " $ASSETS " == *" $1 "* ]]; }

ASSETS=""
for a in "$@"; do
  [[ " $VALID " == *" $a "* ]] || { echo "❌ معرّفُ أصلٍ لا تعرفه صفحةُ التنزيل: $a" >&2
                                    echo "   المسموح: $VALID" >&2; exit 1; }
  ASSETS="$ASSETS $a"
done

# ── وتُنظَّف أصولُ **هذه الدورة** قبل البدء ──
# الفحصُ في نهاية السكربت يقرأ **المجلّد** لا ما وُلِد في هذه الدورة. وفي CI
# المجلّدُ نظيفٌ دائمًا فلا أثر؛ أمّا على جهاز مطوّرٍ يُعيد التغليفَ بالإصدار
# نفسِه، فملفٌّ من دورةٍ سابقةٍ يُرضي الفحصَ بينما الفرعُ الحاليُّ لم يُنتج شيئًا —
# وهو بالضبط ما بُني الفحصُ ليمنعه.
#
# ⚠️ **والحذفُ بالمعرّف لا بـ`"$DIST/$STEM-"*`.** كانت تلك الصيغةُ تمسح أصولَ
#    **المعاينة** كلَّها: `MIHRAB_ASSET_SUFFIX=-alif` يجعل الجذعَ
#    `Mihrab-1.126-alif`، وملفّاتُه `Mihrab-1.126-alif-win-x64-zip.zip` —
#    وهي تطابق `Mihrab-1.126-*` حرفًا بحرف. فتغليفُ الإصدار المستقرّ بعد
#    المعاينة كان يمسح المعاينةَ بصمت. والحذفُ بالاسم الكامل لا يمسّ إلّا ما
#    هذه الدورةُ مسؤولةٌ عن توليده.
for a in $ASSETS; do
  rm -f "$DIST/$STEM-$a."* 2>/dev/null || true
done

# ══════════════════════════ ويندوز ══════════════════════════
if [[ "$OS_NAME" == "windows" ]]; then
  # ‏`inno_updater` يسبق **كلَّ** تغليفِ ويندوز لا المثبِّتَ وحدَه: هو ما يحدّث
  # الأيقونةَ في `tools/`، وغيابُه يترك أداةً بأيقونة VSCodium داخل الحزمة.
  if want win-x64-setup || want win-arm64-setup; then
    gulp_task "vscode-win32-$VSCODE_ARCH-inno-updater"
  fi

  if want "win-$VSCODE_ARCH-zip"; then
    echo "▶ أرشيفٌ محمول …"
    # ‏`-x!tools` كما يفعل المنبع: أدواتُ المثبِّت ليست جزءًا من النسخة المحمولة.
    ( cd "$OUT" && 7z a -tzip -mx=5 "$DIST/$STEM-win-$VSCODE_ARCH-zip.zip" \
        -x'!'CodeSignSummary'*'.md -x'!'tools './*' -r >/dev/null )
    echo "   ✅ $STEM-win-$VSCODE_ARCH-zip.zip"
  fi

  if want "win-$VSCODE_ARCH-setup"; then
    # **مثبِّتُ المستخدِم لا مثبِّتُ النظام.** الأوّلُ يعمل بلا صلاحيّاتِ مدير،
    # والثاني يرفع نافذةَ UAC على أوّلِ نقرة. وجمهورُ محرابٍ أكثرُه على أجهزةٍ
    # لا يملك عليها الصلاحيّة، ومثبِّتٌ يُرفَض في الثانية الأولى تنزيلٌ ضائع.
    # (‏`win32UserAppId` ومعرّفاه المعماريّان مضبوطةٌ في `product-overrides`.)
    gulp_task "vscode-win32-$VSCODE_ARCH-user-setup"
    take_one "$UP/vscode/.build/win32-$VSCODE_ARCH/user-setup/*.exe" \
             "$STEM-win-$VSCODE_ARCH-setup.exe"
  fi
fi

# ══════════════════════════ لينكس ══════════════════════════
if [[ "$OS_NAME" == "linux" ]]; then
  if want "linux-$VSCODE_ARCH-tar"; then
    echo "▶ أرشيفٌ محمول …"
    tar -C "$OUT" -czf "$DIST/$STEM-linux-$VSCODE_ARCH-tar.tar.gz" .
    echo "   ✅ $STEM-linux-$VSCODE_ARCH-tar.tar.gz"
  fi

  if want "linux-$VSCODE_ARCH-deb"; then
    gulp_task "vscode-linux-$VSCODE_ARCH-prepare-deb"
    gulp_task "vscode-linux-$VSCODE_ARCH-build-deb"
    take_one "$UP/vscode/.build/linux/deb/*/deb/*.deb" \
             "$STEM-linux-$VSCODE_ARCH-deb.deb"
  fi

  if want "linux-$VSCODE_ARCH-rpm"; then
    gulp_task "vscode-linux-$VSCODE_ARCH-prepare-rpm"
    gulp_task "vscode-linux-$VSCODE_ARCH-build-rpm"
    take_one "$UP/vscode/.build/linux/rpm/*/*.rpm" \
             "$STEM-linux-$VSCODE_ARCH-rpm.rpm"
  fi
fi

# ══════════════════════════ macOS ══════════════════════════
if [[ "$OS_NAME" == "osx" ]]; then
  if want "mac-$VSCODE_ARCH"; then
    # ── توقيعٌ مؤقّتٌ (ad-hoc) قبل الأرشفة ──
    # لا شهادةَ مطوّرٍ من آبل بعد، ولا نَعِد بواحدة. لكنّ الفرقَ بين ثنائيٍّ
    # **موقَّعٍ مؤقّتًا** وثنائيٍّ **بلا توقيعٍ البتّة** هو الفرقُ بين رسالتين:
    #
    #   بلا توقيع  ⇒ «محراب تالف ولا يمكن فتحه. انقله إلى سلّة المهملات»
    #   مؤقّتًا     ⇒ «لا يمكن فتحه لأنّ المطوّرَ غير موثَّق»  + زرٌّ في لوحة الأمان
    #
    # الأولى رسالةُ **عطب**: تقول إنّ الملفَّ خرب، وهو سليم، وآخرُ ما يراه
    # المستخدمُ من محراب. والثانية رسالةُ **سياسة**: تقول إنّنا لسنا في سجلّ
    # آبل، وهذا صحيحٌ ومكتوبٌ على صفحة التنزيل. ولا زرَّ للأولى أصلًا.
    #
    # وعلى Apple Silicon ليست تجميلًا: النواةُ **ترفض تنفيذ** ثنائيٍّ arm64 بلا
    # أيّ توقيع. فبلا هذه الخطوة لا يُقلِع بناءُ ماك عند أحدٍ إطلاقًا.
    #
    # ⚠️ **و`--deep` يمسح استحقاقاتِ إلكترون**، وفيها `allow-jit`. وهي لا تلزم
    # ما دام `--options runtime` غائبًا (بلا وقتِ تشغيلٍ مُقسَّى الـJIT مسموحٌ
    # افتراضًا). **فمن أضاف `--options runtime` لاحقًا دون `--entitlements`
    # قتل مصيِّرَ الصفحات كلَّه** — وذلك عطبٌ يظهر عند المستخدم لا في البناء.
    #
    # ⏳ وتُستبدَل بتوقيعٍ حقيقيٍّ وتوثيقٍ (notarization) يومَ تتوفّر الشهادة —
    # ويُحذَف عندها قسمُ «أوّلُ تشغيل» من صفحة التنزيل.
    _APP="$(find "$OUT" -maxdepth 1 -name '*.app' -print -quit)"
    [[ -n "$_APP" ]] || { echo "❌ لا حزمةَ .app في $OUT" >&2; exit 1; }
    echo "▶ توقيعٌ مؤقّت …"
    # ‏`--force` لازمٌ: إلكترون يصل موقَّعًا سلفًا بتوقيعٍ لا يخصّنا.
    codesign --force --deep --sign - "$_APP"       || { echo "❌ فشل التوقيعُ المؤقّت — البناءُ لن يُقلِع على Apple Silicon" >&2; exit 1; }
    codesign --verify --deep --strict "$_APP"       || { echo "❌ التوقيعُ لا يجتاز التحقّق" >&2; exit 1; }
    echo "   ✅ موقَّعٌ مؤقّتًا: $(basename "$_APP")"

    echo "▶ أرشيفٌ …"
    # ‏`zip -y` يحفظ الوصلاتِ الرمزيّة كما هي: حزمةُ `.app` مليئةٌ بها (الأُطُر
    # ونسخُها)، واتّباعُها يضاعف الحجمَ **ويكسر توقيعَ الحزمة**.
    ( cd "$OUT" && zip -qry "$DIST/$STEM-mac-$VSCODE_ARCH.zip" . )
    echo "   ✅ $STEM-mac-$VSCODE_ARCH.zip"
  fi
fi

# ── وكلُّ أصلٍ طُلِب قد وُلِد فعلًا ──
# بلا هذا يخرج السكربتُ بـ0 و`dist/` فارغة، فيرفع `upload-artifact` لا شيء
# **والسيرُ أخضر**، وتَعِد صفحةُ التنزيل بملفٍّ لا وجودَ له. ويقع ذلك بأسبابٍ
# ثلاثة: معماريّةٌ مخالفة (المُغلِّفُ كُشِف على x64 والبناءُ arm64) · فرعٌ عُطِّل
# بغير `want` · معرّفٌ بلا فرع. و[PKG-01] يقيس النصَّ لا التشغيل، فهذه هي
# الطبقةُ الوحيدةُ التي تمسكها — ولذلك يشترط ذلك الحارسُ بقاءَ هذا الفحص.
_missing=""
for a in $ASSETS; do
  compgen -G "$DIST/$STEM-$a."* >/dev/null || _missing="$_missing $a"
done
if [[ -n "$_missing" ]]; then
  echo "❌ طُلِبَ تغليفُها ولم يُولَد لها ملفّ:$_missing" >&2
  echo "   المنصّةُ المكشوفة: $OS_NAME/$VSCODE_ARCH · المخرَج: $OUT_NAME" >&2
  echo "   إن كان الهدفُ معماريّةً أخرى فصرِّح بـMIHRAB_ARCH قبل التغليف." >&2
  exit 1
fi

echo
echo "📦 في $DIST:"
ls -lh "$DIST"
