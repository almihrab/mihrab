#!/usr/bin/env bash
# بناء محراب م0 — VSCodium نظيف من المنبع المثبَّت، قابل للتكرار.
# ويندوز (Git Bash) · لينكس · macOS.
#
# يجسّد «وصفة م0»: يجهّز سلسلة أدوات معزولة في build/.toolchain (مُتجاهَلة)، ويطبّق
# خمسة إصلاحات بيئة لازمة لبناء VSCodium 1.121 على هذا الجهاز (راجع build/README.md
# §«وصفة م0 وإصلاحاتها»). idempotent: يُعاد تشغيله بأمان.
#
# الاستعمال:  bash build/build.sh           # بناء كامل
#             SKIP_SOURCE=yes bash build/build.sh   # أعد الاستعمال من شجرة منبع موجودة
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UP="$ROOT/.upstream"
TC="$ROOT/build/.toolchain"
mkdir -p "$TC"

# ══════════════════════════════════════════════════════════════════════════
#  (٠) المنصّة — يُشتَقّ كلُّ ما بعده منها
#
#  كان هذا السكربت ويندوزيًّا وحده، وكانت الويندوزيّةُ **مبثوثةً** فيه لا معلَنة:
#  ‏.exe في أسماء الأدوات، وcygpath في التصدير، ومسارُ مخرَجٍ حرفيّ. فبناءُ لينكس
#  لم يكن «غيرَ مدعوم» — كان يفشل متأخّرًا بعد أربعين دقيقة برسالةٍ عن ملفٍّ مفقود.
#  التصريحُ هنا يجعل الفشلَ (إن وقع) في السطر الأوّل لا في الساعة الأولى.
#
#  الاصطلاحاتُ تطابق dev/build.sh في المنبع (OS_NAME · VSCODE_ARCH) كي لا يكون
#  للمشروع تسميتان للشيء نفسه.
# ══════════════════════════════════════════════════════════════════════════
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) OS_NAME="windows" ;;
  Darwin)               OS_NAME="osx" ;;
  Linux)                OS_NAME="linux" ;;
  *) echo "❌ منصّةٌ غيرُ مدعومة: $(uname -s)" >&2; exit 1 ;;
esac
case "$(uname -m)" in
  aarch64|arm64) VSCODE_ARCH="arm64" ;;
  *)             VSCODE_ARCH="x64" ;;
esac
VSCODE_ARCH="${MIHRAB_ARCH:-$VSCODE_ARCH}"
export OS_NAME VSCODE_ARCH

IS_WIN=no; [[ "$OS_NAME" == "windows" ]] && IS_WIN=yes
EXE_SUFFIX=""; [[ "$IS_WIN" == "yes" ]] && EXE_SUFFIX=".exe"

# مجلّدُ المخرَج ومسارُ التطبيق داخله. الفرقُ الجوهريّ في macOS: المخرَجُ حزمة
# ‏`.app` وليس شجرةً مسطّحة، فمسارُ `resources/app` يغوص في Contents.
case "$OS_NAME" in
  windows) OUT_NAME="VSCode-win32-$VSCODE_ARCH"
           APP_REL="resources/app"
           LAUNCH_REL="Mihrab.exe" ;;
  linux)   OUT_NAME="VSCode-linux-$VSCODE_ARCH"
           APP_REL="resources/app"
           LAUNCH_REL="bin/mihrab" ;;
  # macOS: اسمُ الحزمة يُشتَقّ من nameLong وهو **عربيّ** («محراب.app»)، فلا يُكتب
  # حرفيًّا هنا — يُحلّ بالبحث بعد البناء. وكتابةُ «Mihrab.app» تجعل الفحصَ يفشل
  # على بناءٍ سليم، وهو أسوأُ من ألّا يكون هناك فحص.
  osx)     OUT_NAME="VSCode-darwin-$VSCODE_ARCH"
           APP_REL=""            # يُحلّ بعد البناء
           LAUNCH_REL="" ;;
esac

# ── مفسّرُ بايثون: يُحلّ مرّةً ولا يُفترَض ────────────────────────────────────
# الدالّةُ مشتركةٌ لأنّ خمسةَ سكربتاتٍ أخرى كانت تنادي `python` مجرَّدًا فتموت على
# أوبونتو 24.04. التعليلُ الكامل في الملفّ، والقاعدةُ يحرسها [PY-01] في L0.
# ‏`export` لازمٌ: شيفرةُ الحقن داخل `build.sh` المنبع ترثه (رُقَعُ النواة كلُّها بايثون).
. "$ROOT/build/lib/pybin.sh"
resolve_py_bin || exit 1

# تحويلُ مسارٍ إلى صيغة النظام لمستهلكٍ غير POSIX (node-gyp على ويندوز وحده).
winpath() { if [[ "$IS_WIN" == "yes" ]]; then cygpath -w "$1"; else printf '%s' "$1"; fi; }

# مَخرَجٌ للفحص: يطبع ما استنتجه ثمّ يخرج. سببُ وجوده أنّ CI يجب أن يتحقّق من
# صحّة الكشف في ثوانٍ لا أن ينتظر أربعين دقيقةً ليكتشف أنّه بنى للمنصّة الخطأ.
if [[ "${1:-}" == "--platform" ]]; then
  echo "$OS_NAME/$VSCODE_ARCH out=$OUT_NAME"
  exit 0
fi

# ── إصدارات سلسلة الأدوات ──
#
# ‏NODE_VERSION **يُقرأ من `upstream.json`** لا يُكتب هنا. كان مكتوبًا حرفيًّا بتعليقٍ
# يقول «طابِقه مع vscode/.nvmrc» — أي تثبيتان للشيء نفسِه، أحدهما في `upstream.json`
# والآخرُ هنا، وسطرُ تعليقٍ يرجو من القارئ أن يزامنهما. وترقيةُ المنبع تلمس الأوّل
# دائمًا وتنسى الثاني، فيُنزَّل Node إصدارِ المنبعِ السابق ويفشل البناءُ متأخّرًا
# برسالةٍ لا تذكر Node (‏1.121 ⇐ 22.22.1 · 1.126 ⇐ 24.15.0 — قفزةُ إصدارٍ رئيسيّ).
#
# ويُقرَأ بـgrep لا بـjq: jq يُجهَّز في الخطوة (ب)، بعد هذه بعشرات الأسطر. والحقلُ
# مسطّحٌ معروفُ الشكل، فالتحليلُ البسيط يكفيه — وإن أخفق فالسقوطُ صريحٌ لا صامت.
NODE_VERSION="${MIHRAB_NODE_VERSION:-$(grep -oE '"node"[[:space:]]*:[[:space:]]*"[^"]*"' "$ROOT/upstream.json" | head -1 | grep -oE '[0-9]+[.][0-9]+[.][0-9]+')}"
[[ "$NODE_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
  echo "❌ تعذّر قراءة toolchain.node من upstream.json (قُرئ: '$NODE_VERSION')." >&2
  echo "   مرّر MIHRAB_NODE_VERSION=x.y.z لتجاوزه، أو أصلح الملفّ." >&2
  exit 1; }
JQ_VERSION="1.7.1"
NODEGYP_VERSION="13.0.0"   # 11.x لا يعرف VS 2026 (v18)؛ 13 يدعم [2019,2022,2026]
PYTHON_HINT="${MIHRAB_NODE_GYP_PYTHON:-${MIHRAB_PYTHON:-}}"   # مسار python3.12 لـnode-gyp (‏لا علاقةَ له بـPY_BIN)؛ يُكتشف تلقائيًّا إن تُرك فارغًا

log() { echo "▶ $*"; }

# ── (أ) Node محمول مطابق لـ.nvmrc (Node النظام قد يكون أقدم من أن يشغّل ملفّات .ts) ──
# اسمُ التوزيعة وصيغةُ الأرشيف وموضعُ الثنائيّ داخله تختلف الثلاثةُ بين المنصّات،
# ولا اشتقاقَ يجمعها — فتُذكَر صراحةً.
case "$OS_NAME" in
  windows) NODE_SLUG="node-v${NODE_VERSION}-win-x64";                NODE_PKG="zip";    NODE_BIN_SUB="" ;;
  linux)   NODE_SLUG="node-v${NODE_VERSION}-linux-${VSCODE_ARCH}";   NODE_PKG="tar.xz"; NODE_BIN_SUB="/bin" ;;
  osx)     NODE_SLUG="node-v${NODE_VERSION}-darwin-${VSCODE_ARCH}";  NODE_PKG="tar.gz"; NODE_BIN_SUB="/bin" ;;
esac
NODE_DIR="$TC/$NODE_SLUG"
NODE_BIN="$NODE_DIR$NODE_BIN_SUB"

if [[ ! -x "$NODE_BIN/node$EXE_SUFFIX" ]]; then
  log "تنزيل Node ${NODE_VERSION} المحمول ($NODE_SLUG)"
  # -f يُفشِل عند 4xx/5xx؛ نُنزِّل لملفّ مؤقّت ثمّ نُعيد التسمية حتى لا يبقى أرشيفٌ ناقص
  # يُربك إعادة التشغيل لو انقطع التنزيل في المنتصف.
  curl -fsSL --retry 3 -o "$TC/node.$NODE_PKG.part" \
       "https://nodejs.org/dist/v${NODE_VERSION}/${NODE_SLUG}.${NODE_PKG}"
  mv -f "$TC/node.$NODE_PKG.part" "$TC/node.$NODE_PKG"
  if [[ "$IS_WIN" == "yes" ]]; then
    powershell -NoProfile -Command "Expand-Archive -Force -Path '$(cygpath -w "$TC/node.zip")' -DestinationPath '$(cygpath -w "$TC")'"
  else
    tar -C "$TC" -xf "$TC/node.$NODE_PKG"
  fi
  rm -f "$TC/node.$NODE_PKG"
  # تحقّق أنّ الاستخراج أنتج ثنائيًّا فعلًا (Expand-Archive قد يفشل بصمت في powershell).
  [[ -x "$NODE_BIN/node$EXE_SUFFIX" ]] || { echo "❌ فشل استخراج Node إلى $NODE_DIR" >&2; exit 1; }
fi
export PATH="$NODE_BIN:$TC:$PATH"
log "المنصّة=$OS_NAME/$VSCODE_ARCH · Node=$(node -v) npm=$(npm -v)"

# ── (ب) jq (يحتاجه get_repo.sh/utils.sh في المنبع) ──
case "$OS_NAME" in
  windows) JQ_ASSET="jq-windows-amd64.exe" ;;
  linux)   JQ_ASSET="jq-linux-$([[ "$VSCODE_ARCH" == "arm64" ]] && echo arm64 || echo amd64)" ;;
  osx)     JQ_ASSET="jq-macos-$([[ "$VSCODE_ARCH" == "arm64" ]] && echo arm64 || echo amd64)" ;;
esac
JQ_BIN="$TC/jq$EXE_SUFFIX"
# ── [TC-01] ثنائيُّ منصّةٍ أخرى في سلسلة الأدوات ──────────────────────────────
# ‏`build/.toolchain` مجلّدٌ **في المستودع**، والمستودعُ يُبنى من ويندوز ومن WSL
# على القرص نفسِه. فبناءُ لينكسٍ يُشير إلى `/mnt/c/...` يُنزِّل `jq` بلا لاحقة
# جنبَ `jq.exe` الويندوزيّ — واسمُ الملفّ وحدَه يفرّقهما.
#
# والأثرُ ليس نظريًّا: `$TC` يتصدّر `PATH` هنا، و`prepare.sh` ينادي `jq` مجرَّدًا،
# فيلتقط ELF على ويندوز ويموت بـ«‏Exec format error» **في السطر الرابعَ عشرَ من
# ملفٍّ آخر** — رسالةٌ لا تذكر سلسلةَ الأدوات ولا المنصّة، وتُقرأ عطبًا في المنبع.
# وقد كلّفت بناءً كاملًا مرّةً حتّى شُخِّصت.
#
# والعلاجُ إقصاءٌ لا حذفٌ أعمى: يُختبَر الملفُّ بتشغيله، فإن لم يعمل على هذه
# المنصّة نُحّي جانبًا باسمٍ يقول لماذا — فيبقى لصاحبه إن كان يعمل عنده.
for _stray in "$TC/jq" "$TC/jq.exe"; do
  [[ "$_stray" == "$JQ_BIN" ]] && continue
  [[ -e "$_stray" ]] || continue
  if ! "$_stray" --version >/dev/null 2>&1; then
    mv -f "$_stray" "$_stray.foreign" 2>/dev/null || rm -f "$_stray"
    log "نُحّي ثنائيُّ jq لمنصّةٍ أخرى: $(basename "$_stray") [TC-01]"
  fi
done
if [[ ! -x "$JQ_BIN" ]]; then
  log "تنزيل jq ${JQ_VERSION} ($JQ_ASSET)"
  # نُنزِّل لملفّ مؤقّت ثمّ نُعيد التسمية: يمنع بقاء jq ناقص (يجتاز فحص -x) عند انقطاع.
  curl -fsSL --retry 3 -o "$JQ_BIN.part" \
       "https://github.com/jqlang/jq/releases/download/jq-${JQ_VERSION}/${JQ_ASSET}"
  chmod +x "$JQ_BIN.part"
  mv -f "$JQ_BIN.part" "$JQ_BIN"
  # تحقّق أنّ الثنائيّ يعمل (تنزيل صفحة خطأ HTML يجتاز فحص الوجود لكن لا يُنفَّذ).
  "$JQ_BIN" --version >/dev/null 2>&1 || { echo "❌ jq المُنزَّل لا يعمل — تحقّق من الرابط/الشبكة." >&2; rm -f "$JQ_BIN"; exit 1; }
fi

# وما يلتقطه `PATH` هو ما جهّزناه — لا ما سبقه إلى الاسم. الفحصُ **تشغيلٌ لا
# وجود**: ملفٌّ لمنصّةٍ أخرى موجودٌ وقابلٌ للتنفيذ في نظر `-x` ولا يعمل.
jq --version >/dev/null 2>&1 || {
  echo "❌ ‏jq الذي يجده PATH لا يعمل على هذه المنصّة: $(command -v jq)" >&2
  echo "   احذفه أو أزِله من PATH — ‏prepare.sh ينادي jq مجرَّدًا [TC-01]" >&2
  exit 1
}

# ── (ج) تحضير شجرة المنبع (استنساخ VSCodium المثبَّت + رُقَع محراب) ──
if [[ "${SKIP_SOURCE:-no}" != "yes" || ! -d "$UP/.git" ]]; then
  log "تحضير المنبع عبر prepare.sh"
  bash "$ROOT/build/prepare.sh"
fi

# ══════════════════════════════════════════════════════════════════════════
#  (د)+(هـ)+(ز) إصلاحاتُ سلسلةِ أدوات ويندوز — **لا تُنفَّذ على غيرها**
#
#  الثلاثةُ تعالج أعطالَ MSVC وحدها: node-gyp لا يعرف VS 2026، ومكتباتُ Spectre
#  غير مثبّتة، وvswhere يكتشف موضعَ VS. ولينكس وmacOS يبنيان بـclang/gcc من
#  النظام، فتشغيلُها هناك ليس زائدًا فحسب — بل يُتلف node-gyp سليمًا ثمّ يفشل
#  البناءُ بعده بسببٍ لا صلةَ له بالسبب المكتوب في الرسالة.
# ══════════════════════════════════════════════════════════════════════════
if [[ "$IS_WIN" == "yes" ]]; then

# ── (د) استبدال node-gyp المدمج بـ13 (يدعم VS 2026). تجاوز npm_config_node_gyp
#        وحده لا يكفي لأنّ وحدات تنادي node-gyp في سكربتها ⇒ نستبدل المدمج فعليًّا. ──
BUNDLED_GYP="$NODE_DIR/node_modules/npm/node_modules/node-gyp"
gyp_version() { node "$BUNDLED_GYP/bin/node-gyp.js" --version 2>/dev/null | tr -d 'v\r'; }
if [[ "$(gyp_version)" != "$NODEGYP_VERSION" ]]; then
  log "ترقية node-gyp المدمج إلى ${NODEGYP_VERSION}"
  STAGE="$TC/nodegyp"; rm -rf "$STAGE"; mkdir -p "$STAGE"
  npm install "node-gyp@${NODEGYP_VERSION}" --prefix "$STAGE" --no-audit --no-fund >/dev/null
  # تحقّق أنّ التثبيت أنتج node-gyp قبل حذف المدمج (وإلا نُتلِف node-gyp بلا بديل).
  [[ -d "$STAGE/node_modules/node-gyp" ]] || { echo "❌ فشل تثبيت node-gyp@${NODEGYP_VERSION} في $STAGE" >&2; exit 1; }
  rm -rf "$BUNDLED_GYP"
  cp -r "$STAGE/node_modules/node-gyp" "$BUNDLED_GYP"
  mkdir -p "$BUNDLED_GYP/node_modules"
  for d in "$STAGE"/node_modules/*; do
    # if لا «A && continue»: الأخيرة تُفشِل الحلقة تحت set -e عند أوّل تبعيّة ليست node-gyp.
    if [[ "$(basename "$d")" == "node-gyp" ]]; then continue; fi
    cp -r "$d" "$BUNDLED_GYP/node_modules/$(basename "$d")"
  done
  log "node-gyp = $(gyp_version)"
fi

# ── (هـ) ترقيع Spectre: مكتبات Spectre غير مثبّتة في VS 2026 وتثبيتها يحتاج رفعًا
#        تفاعليًّا (UAC). نُجبر مولّد msvs على SpectreMitigation=false لتفادي MSB8040.
#        انحراف م0 معروف — لبناء إنتاجيّ تُثبَّت مكتبات Spectre ويُزال هذا الترقيع. ──
MSVS_PY="$BUNDLED_GYP/gyp/pylib/gyp/generator/msvs.py"
[[ -f "$MSVS_PY" ]] || { echo "❌ لم يُعثر على msvs.py في $MSVS_PY — بنية node-gyp غير متوقّعة." >&2; exit 1; }
if ! grep -q 'spectre_mitigation = "false"' "$MSVS_PY"; then
  log "ترقيع msvs.py لتعطيل SpectreMitigation"
  "$PY_BIN" "$ROOT/build/patch_node_gyp_spectre.py" "$MSVS_PY"
  # امسح أيّ bytecode مخبَّأ للمولِّد القديم حتى يُحمَّل المُرقَّع (احتمال غياب الدليل مقبول).
  find "$BUNDLED_GYP" -name "msvs.cpython-*.pyc" -delete 2>/dev/null || true
fi

fi  # ── نهاية إصلاحات ويندوز (د)+(هـ) ──

# ── (و) ترقيع رقصة .npmrc في prepare_vscode.sh (تتوقّف تحت set -e عند حالة متبقّية) ──
PVS="$UP/prepare_vscode.sh"
if [[ -f "$PVS" ]] && ! grep -q 'محراب م0: تسامح مع غياب .npmrc' "$PVS"; then
  log "ترقيع prepare_vscode.sh (تسامح .npmrc)"
  "$PY_BIN" "$ROOT/build/patch_npmrc_tolerance.py" "$PVS"
fi

# ── (و-2) ترقيع build_cli.sh: «mkdir openssl» (بلا -p) يفشل تحت set -e عند إعادة
#         الاستعمال (المجلّد موجود من بناء سابق). نجعله idempotent. ──
BCL="$UP/build_cli.sh"
if [[ -f "$BCL" ]] && grep -qE '^mkdir openssl$' "$BCL"; then
  log "ترقيع build_cli.sh (mkdir -p openssl)"
  # ⚠️ لا `sed -i`: صيغتُه تختلف بين GNU وBSD — الأخيرةُ (macOS) تُلزِم بلاحقةٍ بعد
  # ‏-i، فتبتلع النمطَ التالي وتموت بـ«-I or -i may not be used with stdin».
  # وأمسكها حارسُ المنصّات في أوّل تشغيلٍ له، بعد ثلاث ثوانٍ من بدء بناء macOS.
  sed 's/^mkdir openssl$/mkdir -p openssl/' "$BCL" > "$BCL.tmp" && mv -f "$BCL.tmp" "$BCL"
fi

# ── (و-3) اسمُ حزمة macOS: المنبع يشتقّه من nameShort، ومغلِّفُ vscode من nameLong ──
# متطابقان في VSCodium («VSCodium») فلا يظهر الفرق. وعندنا nameShort لاتينيّ
# (Mihrab — منه اسمُ التنفيذيّ) وnameLong عربيّ (محراب)، فيُبنى «محراب.app»
# ويُبحَث عن «Mihrab.app». يفشل بعد ست عشرة دقيقة، في آخر خطوة، على macOS وحدها.
if [[ -f "$UP/build_cli.sh" ]]; then
  "$PY_BIN" "$ROOT/build/patch_cli_macapp.py" "$UP/build_cli.sh" "$UP/prepare_assets.sh" \
    || { echo "❌ فشل ترقيع مسار حزمة macOS." >&2; exit 1; }
fi

# ── (و-4) وجهتا الـCLI: تنزيلُ الخادم وفحصُ التحديث [BR-05] ──
# مخبوزتان في Rust بـ`option_env!` وقتَ الترجمة، فلا يبلغهما ترقيعُ `product.json`
# ولا ترقيعُ حزمةِ JS — وهو سببُ بقاء التسرّب الرابع حيًّا بعد أن أُغلِقت الثلاثة.
# ولا بديلَ عن ترقيعِ السكربت قبل `cargo build`: بعده يصير العنوانُ بايتاتٍ.
if [[ -f "$UP/build_cli.sh" ]]; then
  "$PY_BIN" "$ROOT/build/patch_cli_endpoints.py" "$UP/build_cli.sh" \
    || { echo "❌ فشل ترقيعُ وجهتَي الـCLI — [BR-05] يبقى مخبوزًا في الثنائيّ، أي أنّ" >&2
         echo "   الـCLI سيظلّ يخاطب خوادمَ المنبع من جهاز المستخدم." >&2
         echo "   الملفّ: $UP/build_cli.sh · المرقِّع: build/patch_cli_endpoints.py" >&2
         echo "   الأرجحُ بعد ترقية منبع: المِرساةُ لم تعد تُطابق. شغّله وحدَه لترى سببَه:" >&2
         echo "     \"$PY_BIN\" \"$ROOT/build/patch_cli_endpoints.py\" \"$UP/build_cli.sh\"" >&2
         exit 1; }
fi


# ── (ز) بيئة البناء + كشف Visual Studio و Python تلقائيًّا ──
VSWHERE="/c/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe"
if [[ "$IS_WIN" == "yes" && -x "$VSWHERE" ]]; then
  VS_PATH="$("$VSWHERE" -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>/dev/null | tr -d '\r')"
  # فحص vscode للمترجم يقبل 2022/2019 ويكتفي بوجود المسار ⇒ نوجّهه إلى أحدث VS.
  # ملاحظة: نستعمل if لا «A && B» لأنّ الأخيرة تُفشِل السكربت تحت set -e عند فراغ المسار.
  if [[ -n "$VS_PATH" ]]; then export vs2022_install="$(cygpath -w "$VS_PATH")"; fi
fi
if [[ -z "$PYTHON_HINT" && "$IS_WIN" == "yes" ]]; then
  PYTHON_HINT="$(py -3.12 -c 'import sys;print(sys.executable)' 2>/dev/null | tr -d '\r' || true)"
fi
# ‏if لا «A && B»: للوضوح لا للسلامة — القائمةُ `A && B` معفاةٌ من set -e حين يفشل
# غيرُ الأخير (اختُبر على bash 5.2). كان التعليلُ يقول إنّها تُوقف البناء، وذلك خطأ.
if [[ -n "$PYTHON_HINT" ]]; then export npm_config_python="$PYTHON_HINT"; fi
# node-gyp المُستبدَل لا وجودَ له خارج ويندوز؛ npm يستعمل المدمج وهو الصواب هناك.
if [[ "$IS_WIN" == "yes" ]]; then
  export npm_config_node_gyp="$(winpath "$BUNDLED_GYP/bin/node-gyp.js")"
fi
# عددُ الأنوية لا ١٢ ثابتًا: عدّاءُ CI يملك ٢–٤، وطلبُ ١٢ وظيفة عليه يُثقل الذاكرة
# فيُقتل البناءُ بـOOM في منتصفه — وهو فشلٌ يصعب ردُّه إلى سببه.
JOBS="${MIHRAB_JOBS:-$( { nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4; } )}"
export npm_config_jobs="$JOBS"
export UV_THREADPOOL_SIZE="$JOBS"
export NODE_OPTIONS="--max-old-space-size=8192"
export VSCODE_SKIP_NODE_VERSION_CHECK=yes

# ── مستودعُنا لا مستودعُ المنبع في الرُقَع المُولَّدة [BR-05] ──
# ‏`.upstream/utils.sh` يستبدل `!!GH_REPO_PATH!!` في رُقَع VSCodium، وافتراضُه
# `VSCodium/vscodium`. ولم نضبطه، فورثنا وجهتَه: رقعةُ `00-community-add-announcements`
# تجعل **لوحَ الترحيب** يجلب
#     https://raw.githubusercontent.com/VSCodium/vscodium/<branch>/announcements-extra.json
# في كلّ فتحةٍ أولى. أي أنّ محرابًا كان يُخبِر مستودعَ المنبع بكلّ زائرٍ جديد، ويعرض
# **إعلاناتِ VSCodium داخل لوح ترحيبِ محراب** لو نُشرت.
#
# قِيس حيًّا على mihrab.dev عبر CDP (لا استُنتج)، وهو في الأشجار الثلاث. ولم تمسكه
# أيُّ طبقة: عنوانٌ مضروبٌ في الحزمة المصغَّرة لا مفتاحٌ في `product.json`، وبوّاباتُنا
# تفحص `product.json` والنصَّ المخبوز.
#
# والارتدادُ آمنٌ بحكم الرقعة: فشلُ الجلب (‏404 على مستودعنا) ⇒ `BUILTIN_ANNOUNCEMENTS`.
export GH_REPO_PATH="sadlang/mihrab"

log "vs2022_install=${vs2022_install:-<افتراضيّ>} · python=${npm_config_python:-<النظام>}"

# ── (ز-2) هوية محراب (م1، الطبقة الثانية): ادمج product-overrides/product.json فوق
#         product.json الخاصّ بـVSCodium. prepare_vscode.sh يدمج «../product.json»
#         فوق إعداداته (jq .[0]*.[1]) ⇒ قيمنا تسود. idempotent (دمج نفس المفاتيح).
#         نحذف ._comment حتى لا يتسرّب حقل غير معروف إلى product.json النهائيّ. ──
OVERRIDES="$ROOT/product-overrides/product.json"
if [[ -f "$OVERRIDES" ]]; then
  log "تطبيق هوية محراب (product.json)"
  # تحقّق أنّ هدف الدمج موجود (prepare.sh يُنتجه)؛ غيابه يعني خللًا في خطوة (ج).
  [[ -f "$UP/product.json" ]] || { echo "❌ $UP/product.json غير موجود — فشلت خطوة (ج) تحضير المنبع؟" >&2; exit 1; }
  # نكتب لملفّ مؤقّت ثمّ نُعيد التسمية ذرّيًّا: فشل jq (JSON تالف/خطأ قرص) يُجهض
  # قبل mv فلا يُداس product.json الصالح بناتج ناقص. ننظّف tmp عند الفشل.
  # نحذف **كلّ** مفتاحٍ يبدأ بـ_comment لا `._comment` وحده: أضفنا تعليقًا ثانيًا
  # (‏_comment_update) فكاد يتسرّب حقلٌ غير معروف إلى المنتج — حذفٌ بالاسم الواحد
  # يصمت عن الثاني ولا يُبلِّغ.
  if ! jq -s '.[0] * .[1] | with_entries(select(.key | startswith("_comment") | not))' "$UP/product.json" "$OVERRIDES" > "$UP/product.json.tmp"; then
    rm -f "$UP/product.json.tmp"
    echo "❌ فشل دمج هوية محراب عبر jq — تحقّق من صحّة $OVERRIDES و$UP/product.json." >&2
    exit 1
  fi
  mv -f "$UP/product.json.tmp" "$UP/product.json"
fi

# ── (ز-2ب) حزم إضافات محراب المدمجة (م2-أ، الطبقة 1) + رُقَع نواة محراب (الطبقة 3):
#         جهّزها في .mihrab-* (تنجو من git reset في وضع -s) ورقّع build.sh المنبع
#         ليحقنها بعد cd vscode (لا قبل dev/build.sh لأنّ «git add . ; git reset
#         --hard» يحذف غير المتعقَّب). يشمل التعريب (إضافة لغة عربيّة + لغة افتراضيّة). ──
# جرّد مصنوعات التوليد غير الوقتيّة من نسخةٍ مشحونةٍ من إضافة (cp -r لا يحترم
# .vscodeignore): سكربتات مولِّدات السمات/الأيقونات (*.py) و__pycache__ ليست جزءًا من
# المنتج. و[PF-01] وكذلك الاختبارات: كان هذا غائبًا فشُحن **اثنان وعشرون** ملفَّ
# `*.test.js` داخل التوزيعة — صغيرةٌ حجمًا (‏0.23 م.ب) لكنّها سطحُ شيفرةٍ لا يخصّ
# المستخدم، ومؤشّرُ خللٍ في التجريد لا في حجمه. أمسكها حارسُ `tests/perf/size.mjs`.
# ودالّةٌ لا سطورٌ مكرّرة: إضافةُ المعاينة تمرّ من هنا أيضًا، وتجريدٌ يُطبَّق على
# إضافاتِ الدار وحدَها يجعل إضافةً من خارجها تُسقط حارسَ الحجم بتشخيصٍ مضلّلٍ لا يخصّها.
strip_ext_artifacts() {
  find "$1" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
  find "$1" -type f -name '*.py' -delete 2>/dev/null || true
  find "$1" -type f \( -name '*.test.js' -o -name '*.test.mjs' -o -name '*.test.cjs' \) -delete 2>/dev/null || true
}

STAGE_EXT="$UP/.mihrab-extensions"
rm -rf "$STAGE_EXT"; mkdir -p "$STAGE_EXT"
shopt -s nullglob
for ext in "$ROOT"/extensions/*/; do
  [[ -f "${ext}package.json" ]] || continue
  _dst="$STAGE_EXT/$(basename "$ext")"
  cp -r "$ext" "$_dst"
  strip_ext_artifacts "$_dst"
  log "إضافة مدمجة مُجهَّزة: $(basename "$ext")"
done

# ── (ز-2ب-1ب) إضافاتٌ إضافيّةٌ لبناءِ المعاينة (خارجَ extensions/): ──
#         بناءُ محرابٍ العاديُّ لا يحمل لغةً من خارجِ الدار — اللغةُ إضافةٌ تُثبَّت من
#         السوق، وشحنُها داخلَ المنتجِ يجعل المنصّةَ تُبارك لغةً بعينها. لكنّ بناءَ
#         معاينةٍ يُعطى لمطوّري لغةٍ ليجرّبوا محرابًا بلا خطوةِ تثبيتٍ حالةٌ أخرى:
#         الغرضُ عرضٌ لا توزيع، والمتغيّرُ يبقى فارغًا في كلّ بناءٍ عاديّ.
#         المسارات مفصولةٌ بأسطر، لا بنقطتين: مسارُ ويندوز يبدأ بحرفِ سواقةٍ ونقطتين
#         (D:\…) فالفصلُ بالنقطتين يقطعه نصفين ويُفشِل البناءَ على ويندوز وحده.
# <<EXTRA_EXT_DIRS_BLOCK — سياجٌ يقرأ منه tests/static/check_extra_ext_dirs.sh هذه
# الكتلةَ **نفسَها** ليختبرها. نسخةٌ ثانيةٌ من المنطق في الاختبار تنجرف صامتةً.
if [[ -n "${MIHRAB_EXTRA_EXT_DIRS:-}" ]]; then
  while IFS= read -r _extra; do
    [[ -n "$_extra" ]] || continue
    _extra="${_extra%/}"
    # فشلٌ صريحٌ لا تخطٍّ صامت: مسارٌ خاطئٌ هنا يُنتج بناءَ معاينةٍ بلا اللغةِ التي
    # صُنع لأجلها — وهو أسوأُ من فشلِ بناءٍ لأنّه يُكتشَف عند المُجرِّب لا عندنا.
    [[ -f "$_extra/package.json" ]] || { echo "❌ MIHRAB_EXTRA_EXT_DIRS: لا package.json في $_extra" >&2; exit 1; }
    _dst="$STAGE_EXT/$(basename "$_extra")"
    [[ ! -e "$_dst" ]] || { echo "❌ MIHRAB_EXTRA_EXT_DIRS: $(basename "$_extra") يصادم إضافةً مدمجة" >&2; exit 1; }
    cp -r "$_extra" "$_dst"
    strip_ext_artifacts "$_dst"
    log "إضافةُ معاينةٍ مُجهَّزة: $(basename "$_extra")"
  done <<< "$MIHRAB_EXTRA_EXT_DIRS"
fi
# EXTRA_EXT_DIRS_BLOCK>>
# استعادةُ nullglob: كتلةُ المعاينة حلّت محلَّ `shopt -u` فبقي مفعَّلًا إلى آخرِ الملفّ،
# وحلقةٌ على مجلّدٍ فارغٍ صارت تمرّ صامتةً بدل أن تُفشِل البناء (حمولةُ ص أدناه).
shopt -u nullglob

# ── (ز-2ب-2) حزم سلسلة أدوات ص المدمجة (الخيار ١): احقن sad-run.exe في bin/ داخل
#         نسخة mihrab-welcome المُجهَّزة كي يعمل «شغّل ملفّ ص» فورًا دون تثبيت. المصدر:
#         MIHRAB_SAD_RUN إن ضُبط، وإلّا الافتراضيّ المجاور (../sad-engines-dev/sad-run.exe).
#         **سقوط رشيق لا قاتل** (بخلاف الهوية/RTL): غياب الثنائيّ يعني بناءً بلا تشغيل مدمج،
#         والامتداد يسقط إلى PATH ويعرض تلميح التثبيت — لا نُفشِل البناء كلّه لأجله.
#         الهدف المستقبليّ (الخيار ٣، موثَّق في docs/toolchain-delivery.md): أمر «ثبّت أدوات ص»
#         يُنزّل أحدث إصدار عند الطلب فوق هذا المدمج. (راجع resolveSadRun في extension.js.)
#
# ── الأسبقيّة: بيئةٌ صريحة ⇐ **المجلوبُ الرسميّ** ⇐ المجاورُ التطويريّ ──
# كان المجاورُ التطويريُّ يسبق المجلوبَ الرسميَّ، فالجالبُ لا يُثمِر إلّا لمن تذكّر أن
# يُصدّر `.upstream/.sad-tools/env.sh`. وأثرُه مقيسٌ لا مفترَض: هذا البناءُ حزم ثنائيّات
# `../sad-engines-dev` بينما المانيفستُ يشهد بجلبِ `v1.0.0` — فأمسكه حارسُ البصمة
# («‏ما جُلب وصل الحزمةَ ببصمته») بحقّ. وضمانٌ رهنُ ذاكرةٍ ليس ضمانًا: الجالبُ إن عمل
# فناتجُه هو المقصود، والمجاورُ التطويريُّ احتياطٌ لمن لا جالبَ عنده — لا العكس.
SAD_FETCHED_BIN="$ROOT/.upstream/.sad-tools/bin"
_sad_src() {  # $1 = اسمُ الأداة بلا لاحقة · $2 = التجاوزُ الصريح (قد يكون فارغًا)
  if [[ -n "${2:-}" ]]; then printf '%s' "$2"; return; fi
  local fetched="$SAD_FETCHED_BIN/$1$EXE_SUFFIX"
  if [[ -f "$fetched" ]]; then printf '%s' "$fetched"; return; fi
  printf '%s' "$ROOT/../sad-engines-dev/$1$EXE_SUFFIX"
}
SAD_RUN_SRC="$(_sad_src sad-run "${MIHRAB_SAD_RUN:-}")"
# [SAD-02] مصدر أداة الفحص المدمجة (تشخيص عند الحفظ عبر sad-check --json). نفس اصطلاح sad-run.
SAD_CHECK_SRC="$(_sad_src sad-check "${MIHRAB_SAD_CHECK:-}")"
# [SAD-04] مصدر أداة البناء المدمجة (أمر «ابنِ» عبر sad-build). نفس اصطلاح sad-run/sad-check.
SAD_BUILD_SRC="$(_sad_src sad-build "${MIHRAB_SAD_BUILD:-}")"
# [SAD-01] مصدر خادم ص اللغويّ المدمج (LSP: تشخيص/إكمال/تحويم/تعريف). نفس اصطلاح الأدوات؛
# يُحزَم في bin/ داخل نسخة sad-lang المُجهَّزة (لا mihrab-welcome — العميل يسكن في sad-lang).
SAD_LSP_SRC="$(_sad_src sad-lsp "${MIHRAB_SAD_LSP:-}")"
# [AR-02] مصدر خطّ ص العربيّ المحزوم (Kawkab Mono، OFL). يُستهلَك مرّتين: (١) media/ لوحة الترحيب
# (AR-01 تُضمّنه data:URI)، (٢) @font-face وثيقة الـworkbench (تجهيز أدناه). MIHRAB_ARABIC_FONT أو الافتراضيّ.
ARABIC_FONT_SRC="${MIHRAB_ARABIC_FONT:-$ROOT/patches/fonts/kawkab-mono.woff2}"
if [[ -d "$STAGE_EXT/mihrab-welcome" ]]; then
  WELCOME_BIN="$STAGE_EXT/mihrab-welcome/bin"
  # نظّف أيّ bin/ منسوخ من الشجرة المصدريّة (قد يوجد على جهاز مطوّر رغم تجاهله في git):
  # لا نشحن إلّا الثنائيّات من المصدر المعتمَد، أو لا شيء — فلا نسخة بائتة تُشحن صامتًا. [H1]
  rm -rf "$WELCOME_BIN"
  mkdir -p "$WELCOME_BIN"
  # (أ) sad-run — «شغّل ملفّ ص» المدمج.
  if [[ -f "$SAD_RUN_SRC" ]]; then
    cp -f "$SAD_RUN_SRC" "$WELCOME_BIN/sad-run$EXE_SUFFIX"
    log "حُزِمت أداة ص المدمجة: sad-run.exe ($(du -h "$WELCOME_BIN/sad-run$EXE_SUFFIX" 2>/dev/null | cut -f1 || echo '؟')) من $SAD_RUN_SRC"
  else
    log "⚠️ لا sad-run.exe في $SAD_RUN_SRC — بناء بلا تشغيل مدمج (يسقط الامتداد إلى PATH). اضبط MIHRAB_SAD_RUN للحزم."
  fi
  # (ب) sad-check — جسر التشخيص عند الحفظ [SAD-02]. سقوط رشيق كذلك: غيابه ⇒ الجسر يسقط إلى PATH.
  if [[ -f "$SAD_CHECK_SRC" ]]; then
    cp -f "$SAD_CHECK_SRC" "$WELCOME_BIN/sad-check$EXE_SUFFIX"
    log "حُزِمت أداة الفحص المدمجة: sad-check.exe ($(du -h "$WELCOME_BIN/sad-check$EXE_SUFFIX" 2>/dev/null | cut -f1 || echo '؟')) من $SAD_CHECK_SRC"
  else
    log "⚠️ لا sad-check.exe في $SAD_CHECK_SRC — تشخيص الحفظ يسقط إلى PATH. اضبط MIHRAB_SAD_CHECK للحزم."
  fi
  # (ج) sad-build — أمر «ابنِ» [SAD-04]. سقوط رشيق كذلك: غيابه ⇒ أمر البناء يسقط إلى PATH.
  if [[ -f "$SAD_BUILD_SRC" ]]; then
    cp -f "$SAD_BUILD_SRC" "$WELCOME_BIN/sad-build$EXE_SUFFIX"
    log "حُزِمت أداة البناء المدمجة: sad-build.exe ($(du -h "$WELCOME_BIN/sad-build$EXE_SUFFIX" 2>/dev/null | cut -f1 || echo '؟')) من $SAD_BUILD_SRC"
  else
    log "⚠️ لا sad-build.exe في $SAD_BUILD_SRC — أمر البناء يسقط إلى PATH. اضبط MIHRAB_SAD_BUILD للحزم."
  fi
  # (ج-2) حمولةٌ مجاورةٌ للأدوات (`MIHRAB_SAD_PAYLOAD`): المكتبةُ القياسيّة ومكتباتُ
  #        التشغيل التي تأتي في الإصدار الرسميّ. برنامجٌ نصّيٌّ يعمل بلا هذه (قِسناه)،
  #        لكنّ استيرادَ المكتبة القياسيّة يحتاجها — فشحنُ الثنائيّ وحدَه يُنتج «يعمل
  #        في مثال الترحيب ويسقط في أوّل استيراد»، وهو أسوأُ من غيابٍ صريح.
  if [[ -n "${MIHRAB_SAD_PAYLOAD:-}" && -d "$MIHRAB_SAD_PAYLOAD" && -d "$WELCOME_BIN" ]]; then
    for item in "$MIHRAB_SAD_PAYLOAD"/*; do
      base="$(basename "$item")"
      case "$base" in sad-run*|sad-build*|sad-check*|sad-lsp*) continue ;; esac
      cp -rf "$item" "$WELCOME_BIN/" && log "حمولةُ ص المجاورة: $base"
    done
  fi
  # لا تشحن دليلًا فارغًا إن غابت كلّ الأدوات (يُبقي السلوك كما لو لم يُنشأ bin/).
  rmdir "$WELCOME_BIN" 2>/dev/null || true
  # (د) [AR-02] الخطّ العربيّ المحزوم في media/ لوحة الترحيب: تُضمّنه لوحة المخرجات (AR-01) كـdata:URI
  # كي تعرض المخرجات بالخطّ المحزوم عينه (الـwebview معزول عن @font-face الـworkbench). سقوط رشيق.
  if [[ -f "$ARABIC_FONT_SRC" ]]; then
    WELCOME_MEDIA="$STAGE_EXT/mihrab-welcome/media"
    mkdir -p "$WELCOME_MEDIA"
    cp -f "$ARABIC_FONT_SRC" "$WELCOME_MEDIA/kawkab-mono.woff2"
    log "حُزِم الخطّ العربيّ في لوحة الترحيب: media/kawkab-mono.woff2 من $ARABIC_FONT_SRC"
  fi
fi

# ── (ز-2ب-3) [SAD-01] حزم خادم ص اللغويّ المدمج: احقن sad-lsp.exe في bin/ داخل نسخة sad-lang
#         المُجهَّزة كي يعمل الذكاء اللغويّ (تشخيص/إكمال/تحويم/تعريف) فورًا دون تثبيت. **سقوط رشيق
#         لا قاتل**: غياب الثنائيّ ⇒ العميل يسقط إلى PATH ويعرض تلميح تثبيت (LSP تحسينيّ لا شرط صحّة).
if [[ -d "$STAGE_EXT/sad-lang" ]]; then
  SADLANG_BIN="$STAGE_EXT/sad-lang/bin"
  # نظّف أيّ bin/ منسوخ من الشجرة المصدريّة (قد يوجد على جهاز مطوّر رغم تجاهله في git):
  # لا نشحن إلّا الثنائيّ من المصدر المعتمَد، أو لا شيء — فلا نسخة بائتة تُشحن صامتًا.
  rm -rf "$SADLANG_BIN"
  mkdir -p "$SADLANG_BIN"
  if [[ -f "$SAD_LSP_SRC" ]]; then
    cp -f "$SAD_LSP_SRC" "$SADLANG_BIN/sad-lsp$EXE_SUFFIX"
    log "حُزِم خادم ص اللغويّ المدمج: sad-lsp.exe ($(du -h "$SADLANG_BIN/sad-lsp$EXE_SUFFIX" 2>/dev/null | cut -f1 || echo '؟')) من $SAD_LSP_SRC"
  else
    log "⚠️ لا sad-lsp.exe في $SAD_LSP_SRC — الذكاء اللغويّ يسقط إلى PATH. اضبط MIHRAB_SAD_LSP للحزم."
  fi
  # لا تشحن دليلًا فارغًا إن غاب الخادم (يُبقي السلوك كما لو لم يُنشأ bin/).
  rmdir "$SADLANG_BIN" 2>/dev/null || true
fi

# جهّز رُقَع النواة + أصولها (تُطبَّق داخل build.sh المنبع بعد cd vscode، فتنجو من reset).
[[ -f "$ROOT/build/patch_main_locale.py" ]] && cp -f "$ROOT/build/patch_main_locale.py" "$UP/.mihrab-patch-main-locale.py"
[[ -f "$ROOT/build/patch_workbench_rtl.py" ]] && cp -f "$ROOT/build/patch_workbench_rtl.py" "$UP/.mihrab-patch-workbench-rtl.py"
[[ -f "$ROOT/build/patch_menubar_rtl.py" ]] && cp -f "$ROOT/build/patch_menubar_rtl.py" "$UP/.mihrab-patch-menubar-rtl.py"
[[ -f "$ROOT/build/patch_menu_rtl.py" ]] && cp -f "$ROOT/build/patch_menu_rtl.py" "$UP/.mihrab-patch-menu-rtl.py"
[[ -f "$ROOT/build/patch_splitview_rtl.py" ]] && cp -f "$ROOT/build/patch_splitview_rtl.py" "$UP/.mihrab-patch-splitview-rtl.py"
[[ -f "$ROOT/build/patch_sash_rtl.py" ]] && cp -f "$ROOT/build/patch_sash_rtl.py" "$UP/.mihrab-patch-sash-rtl.py"
[[ -f "$ROOT/build/patch_tabsdrop_rtl.py" ]] && cp -f "$ROOT/build/patch_tabsdrop_rtl.py" "$UP/.mihrab-patch-tabsdrop-rtl.py"
[[ -f "$ROOT/build/patch_gridview_marker.py" ]] && cp -f "$ROOT/build/patch_gridview_marker.py" "$UP/.mihrab-patch-gridview-marker.py"
# ‏**رُقعةُ مصدرِ vscode تُحقَن بعد الـreset لا قبله.** أوّلُ صياغةٍ نادت المرقِّعَ في
# خطوة (و) المبكّرة، فطبع «مُرقَّعٌ سلفًا» (لأنّي كنتُ رقّعتُ الملفَّ بيدي للقياس)
# **ثمّ محا `dev/build.sh` أثرَه** بـ`git add . ; git reset --hard` — فسقط بناءُ الويب
# بالعطب نفسِه، والسجلُّ يحمل شهادةَ ترقيعٍ لملفٍّ غيرِ مُرقَّع. وهو الفخُّ الذي يصفه
# التعليقُ في خطوة (ز) حرفيًّا، ووقعتُ فيه بعد قراءته.
[[ -f "$ROOT/build/patch_esbuild_fileurl.py" ]] && cp -f "$ROOT/build/patch_esbuild_fileurl.py" "$UP/.mihrab-patch-esbuild-fileurl.py"
# محرّر Monaco RTL: لم تعد رُقعةً خاصّة بمحراب بل **تعديلٌ منبعيٌّ كامل** (خيار
# `editor.textDirection`) مُصاغٌ للرفع إلى microsoft/vscode ومحفوظٌ هنا ملفَّ diff واحدًا.
# يُطبَّق بـ`git apply --3way` داخل شجرة vscode بعد reset (يتسامح مع انجراف المنبع).
# يسقط كلّه يوم يُدمَج المقترح م-٢ — لا تُحدَّث مراسيه يدويًّا: يُعاد توليده من الشوكة.
[[ -f "$ROOT/patches/core/010-editor-text-direction.patch" ]] && cp -f "$ROOT/patches/core/010-editor-text-direction.patch" "$UP/.mihrab-editor-text-direction.patch"
# بدايةُ الكلمة بعد أداة التعريف [م-١٥/ب]: تعديلٌ منبعيٌّ آخرُ لا رُقعةَ هويّة — المطابقةُ
# الضبابيّةُ تعرف حدَّ الكلمة اللاتينيَّ (حرفٌ كبير) ولا تعرف نظيرَه العربيَّ (أداةُ التعريف)،
# فتسقط «فضة» عن `نصاب_الفضة` إسقاطًا لا إضعافَ رتبة. يسقط كلُّه يوم يُدمَج المقترح.
[[ -f "$ROOT/patches/core/020-nonlatin-word-start.patch" ]] && cp -f "$ROOT/patches/core/020-nonlatin-word-start.patch" "$UP/.mihrab-nonlatin-word-start.patch"
# صناديقُ الإدخال البسيطة [SC-01 + م-١٧]: `getSimpleEditorOptions` يقرأ ستّةَ مفاتيحَ من
# الإعدادات ولا يقرأ `textDirection` ولا `fontLigatures`. فرسالةُ الالتزام — وهي **أطولُ
# نصٍّ عربيٍّ متّصلٍ يكتبه المستخدم في المحرِّر** — فقرةٌ LTR بأحرفٍ مفكَّكة، وكذلك حقلُ وحدة
# التصحيح وشرطُ نقطة التوقّف. تعديلٌ منبعيٌّ لا رقعةُ هويّة: يسقط يومَ يُدمَج.
[[ -f "$ROOT/patches/core/030-simple-editor-rtl-input.patch" ]] && cp -f "$ROOT/patches/core/030-simple-editor-rtl-input.patch" "$UP/.mihrab-simple-editor-rtl-input.patch"
# حجمُ خطّ شجرة التنقيح [DG-01 + م-٢١]: ارتفاعُ الصفّ يتبع مفتاحَ حجم خطّ الشريط الجانبيّ
# والحبرُ لا يتبعه — فالتكبيرُ يزيد الفراغَ ولا يزيد المقروء. تعديلٌ منبعيٌّ بحتٌ (سطرا CSS
# مربوطان بمتغيّرٍ منبعيٍّ قائم، بلا مفتاحٍ جديد ولا واجهةٍ عامّة): يسقط يومَ يُدمَج.
[[ -f "$ROOT/patches/core/031-debug-tree-font-size.patch" ]] && cp -f "$ROOT/patches/core/031-debug-tree-font-size.patch" "$UP/.mihrab-debug-tree-font-size.patch"
# تجدُّدُ خيارات صندوق الالتزام حيًّا [SC-01 + م-١٧]: الاتّجاهُ والأشكالُ السياقيّةُ وارتفاعُ
# السطر تُلتقَط عند الإنشاء ولا تتبع تغيُّرَ الإعداد. تعديلٌ منبعيٌّ بحتٌ بلا مفتاحٍ جديد:
# ‏`affectsConfiguration` للثلاثة، ودفعُ مفتاحَين في حمولة `updateOptions`. يسقط يومَ يُدمَج.
[[ -f "$ROOT/patches/core/032-scm-input-live-options.patch" ]] && cp -f "$ROOT/patches/core/032-scm-input-live-options.patch" "$UP/.mihrab-scm-input-live-options.patch"
# خلطُ الكتابتَين في إبراز يونيكود [AR-05 · م-١٣/ب]: المنبع يسأل «أفي الكلمة محرفُ
# ASCII؟» ويقصد «أتخلط كتابتَين؟» — والشَرطةُ السفليّةُ والأرقامُ ليست كتابةً بل غِراءُ
# معرّفاتٍ في كلّ كتابة. فمعرّفُ ص `حقل_اسم` كان يُقرأ خلطًا فتُصنَّد كلُّ ألفٍ فيه:
# ‏622 إبرازًا مرسومًا في ملفٍّ واحد، ولا واحدَ منها انتحال. تعديلٌ منبعيٌّ لا رقعةُ
# هويّة: يسقط يومَ يُدمَج م-١٣/ب. فشلٌ قاتلٌ كسابقاتها.
[[ -f "$ROOT/patches/core/033-unicode-word-script-mixing.patch" ]] && cp -f "$ROOT/patches/core/033-unicode-word-script-mixing.patch" "$UP/.mihrab-unicode-word-script-mixing.patch"
# الطرفيّةُ في المتصفّح بلا خادم [WEB-05]: أربعةُ مداخلَ تفتح لوحًا لا خلفيّةَ له —
# لسانُ اللوحة، وCtrl+Backquote، وبندُ «طرفيّة جديدة» في قائمة الطرفيّة، وCtrl+Shift+C.
# كلُّ أوامر الطرفيّة مُقيَّدةٌ بـ`processSupported` أصلًا، لكنّ **وصفَ العرض** لم يكن
# مُقيَّدًا، وقاعدةَ الاختصار في `terminal.web.contribution.ts` تُسجَّل مباشرةً فتتخطّى
# القيدَ، وبندَ القائمة الأوّلَ نسي المنبعُ شرطَه الذي تحمله إخوتُه الأربعة. تعديلٌ
# منبعيٌّ بحتٌ يسقط يومَ يُدمَج. فشلٌ قاتلٌ كسابقاته.
[[ -f "$ROOT/patches/core/034-terminal-unavailable-in-web.patch" ]] && cp -f "$ROOT/patches/core/034-terminal-unavailable-in-web.patch" "$UP/.mihrab-terminal-unavailable-in-web.patch"
[[ -f "$ROOT/build/patch_welcome_rtl.py" ]] && cp -f "$ROOT/build/patch_welcome_rtl.py" "$UP/.mihrab-patch-welcome-rtl.py"
[[ -f "$ROOT/build/patch_walkthrough_dir.py" ]] && cp -f "$ROOT/build/patch_walkthrough_dir.py" "$UP/.mihrab-patch-walkthrough-dir.py"
[[ -f "$ROOT/build/patch_walkthroughs_drop.py" ]] && cp -f "$ROOT/build/patch_walkthroughs_drop.py" "$UP/.mihrab-patch-walkthroughs-drop.py"
# لوحُ الترحيب لا يَعِد بما لا خلفيّةَ له: بندُ «فتح المستودع» شرطُه `webworker` —
# وهو متحقّقٌ في بنائنا الثابت — وأمرُه من إضافةِ مايكروسوفت المِلكيّة التي لا نشحنها.
[[ -f "$ROOT/build/patch_welcome_web_entries.py" ]] && cp -f "$ROOT/build/patch_welcome_web_entries.py" "$UP/.mihrab-patch-welcome-web-entries.py"
[[ -f "$ROOT/build/patch_html_lang.py" ]] && cp -f "$ROOT/build/patch_html_lang.py" "$UP/.mihrab-patch-html-lang.py"
[[ -f "$ROOT/build/patch_dialog_style.py" ]] && cp -f "$ROOT/build/patch_dialog_style.py" "$UP/.mihrab-patch-dialog-style.py"
# مجلّد إعدادات المشروع `.محراب` (بتوافقٍ خلفيّ مع `.vscode`). ينسخ معه وحدتَي TS
# جديدتَين — فالرقعةُ تُضيف ملفّات لا تعدّل قائمًا وحسب.
[[ -f "$ROOT/build/patch_config_folder.py" ]] && cp -f "$ROOT/build/patch_config_folder.py" "$UP/.mihrab-patch-config-folder.py"
# تعريب عناوين لوحة الإعدادات (تُشتَقّ حسابيًّا فلا تصلها ترجمةُ NLS). ينسخ معه وحدةَ
# TS واحدة عبر .mihrab-core أدناه.
[[ -f "$ROOT/build/patch_settings_labels.py" ]] && cp -f "$ROOT/build/patch_settings_labels.py" "$UP/.mihrab-patch-settings-labels.py"
# بياناتُ نسخةِ ويندوز في الثنائيّات (‏CompanyName/LegalCopyright). قِيس على المشحون:
# ‏Mihrab.exe كان ينسب نفسَه إلى VSCodium، وmihrab-tunnel.exe إلى Microsoft Corporation.
[[ -f "$ROOT/build/patch_win_metadata.py" ]] && cp -f "$ROOT/build/patch_win_metadata.py" "$UP/.mihrab-patch-win-metadata.py"
[[ -d "$ROOT/patches/core" ]] && { rm -rf "$UP/.mihrab-core"; cp -rf "$ROOT/patches/core" "$UP/.mihrab-core"; }
# ورقتا الأنماط [VA-05]: الاتّجاه والهويّة. **كلتاهما إلزاميّةٌ وغيابُها يُفشِل هنا**.
#
# ولماذا `if` صريحةٌ لا `[[ -f X ]] && cp` كالسطور المجاورة: تحت `set -euo pipefail` تكون
# قائمةُ `&&` التي يفشل طرفُها الأوّل **فشلًا للسكربت كلِّه** — أي أنّ النمطَ المجاور
# يُسقِط البناءَ بلا رسالةٍ واحدة (فخٌّ موثَّقٌ في هذا الملفّ نفسِه أدناه). فالصياغةُ هنا
# تقول ما نقص **بالعربيّة وفي ثانيةِ التهيئة الأولى**، قبل جلبِ شجرة المنبع ودقائقِ البناء.
for _sheet in mihrab-rtl mihrab-identity; do
  if [[ -f "$ROOT/patches/${_sheet}.css" ]]; then
    cp -f "$ROOT/patches/${_sheet}.css" "$UP/.${_sheet}.css"
  else
    echo "محراب: ورقة الأنماط patches/${_sheet}.css مفقودة — والاستيرادُ محقونٌ في workbench.ts" >&2
    exit 1
  fi
done
# [AR-02] جهّز خطّ ص العربيّ المحزوم لوثيقة الـworkbench: patch_bundle يشتقّ منه base64 ويحقن
# @font-face بمصدر data: URI في نسخة media من mihrab-rtl.css (لا url() نسبيّ: يكسر بناء esbuild —
# لا loader لـ.woff2). المصدر ARABIC_FONT_SRC معرَّف أعلى الملفّ. سقوط رشيق: غيابه ⇒ لا حقن.
[[ -f "$ARABIC_FONT_SRC" ]] && cp -f "$ARABIC_FONT_SRC" "$UP/.mihrab-kawkab-mono.woff2"
# جهّز أصول هوية محراب البصريّة (أيقونة التطبيق + بلاطتا ويندوز) في مجلّد ينجو من reset،
# ليحقنها build.sh المنبع فوق resources/win32/ بعد cd vscode (تستبدل هوية VSCodium).
BRAND_SRC="$ROOT/assets/branding"
BRAND_STAGE="$UP/.mihrab-branding"
rm -rf "$BRAND_STAGE"; mkdir -p "$BRAND_STAGE"
[[ -f "$BRAND_SRC/mihrab.ico" ]] && cp -f "$BRAND_SRC/mihrab.ico" "$BRAND_STAGE/code.ico"
[[ -f "$BRAND_SRC/mihrab_150x150.png" ]] && cp -f "$BRAND_SRC/mihrab_150x150.png" "$BRAND_STAGE/code_150x150.png"
[[ -f "$BRAND_SRC/mihrab_70x70.png" ]] && cp -f "$BRAND_SRC/mihrab_70x70.png" "$BRAND_STAGE/code_70x70.png"
# أيقونتا لينكس وmacOS. كانتا مفقودتين حين كان البناءُ ويندوزيًّا وحده، وغيابُهما
# لا يُفشل بناءً — يشحن شعارَ VSCodium في شريط مهامّ لينكس وفي Dock. وهو من صنف
# updateUrl الموروث: البناءُ ينجح والمستخدمُ يرى مشروعًا آخر.
if [[ -f "$BRAND_SRC/mihrab-mark-color-256.png" ]]; then
  cp -f "$BRAND_SRC/mihrab-mark-color-256.png" "$BRAND_STAGE/code.png"
  "$PY_BIN" "$ROOT/build/gen_icns.py" "$BRAND_SRC/mihrab-mark-color-256.png" \
         "$BRAND_STAGE/code.icns" >/dev/null \
    || { echo "❌ فشل توليد code.icns" >&2; exit 1; }
fi
# شعار رأس التطبيق (code-icon.svg) + خلفية المحرّر الفارغ (letterpress-*.svg) — أصول SVG
# تُحقَن فوق مصدر vscode في كتلة INJECT، فيظهر شعار القوس في شريط العنوان والخلفية أيضًا.
[[ -f "$BRAND_SRC/mihrab-appicon.svg" ]] && cp -f "$BRAND_SRC/mihrab-appicon.svg" "$BRAND_STAGE/code-icon.svg"
for _lp in dark light hcDark hcLight; do
  [[ -f "$BRAND_SRC/mihrab-letterpress-$_lp.svg" ]] && cp -f "$BRAND_SRC/mihrab-letterpress-$_lp.svg" "$BRAND_STAGE/letterpress-$_lp.svg"
done
# أصول مساحة sessions التجريبيّة (شعار الحوض + أيقونة Open-in + خلفيّتها الفارغة).
[[ -f "$BRAND_SRC/mihrab-sessions-icon.svg" ]] && cp -f "$BRAND_SRC/mihrab-sessions-icon.svg" "$BRAND_STAGE/vscode-icon.svg"
[[ -f "$BRAND_SRC/mihrab-vscodeLogoPath.ts" ]] && cp -f "$BRAND_SRC/mihrab-vscodeLogoPath.ts" "$BRAND_STAGE/vscodeLogoPath.ts"
for _lps in dark light; do
  [[ -f "$BRAND_SRC/mihrab-letterpress-sessions-$_lps.svg" ]] && cp -f "$BRAND_SRC/mihrab-letterpress-sessions-$_lps.svg" "$BRAND_STAGE/letterpress-sessions-$_lps.svg"
done
BSH="$UP/build.sh"
# مصدر حقيقة واحد لإصدار الرُقَع: يُشتَقّ CORE_PATCH_VERSION من patch_bundle_extensions.py
# فيبقى الحارس هنا والوسم في المرقِّع متّسقين تلقائيًّا (رفع الإصدار في موضع واحد يكفي).
# **يُسأل المُرقِّعُ ولا يُقرَأ نصُّه**: كان `sed` يلتقط `CORE_PATCH_VERSION = "v33"`
# حرفيًّا. ثمّ صار الوسمُ مشتقًّا من بصمة المحتوى فاختفى الثابتُ من النصّ، فسقط
# البناءُ بـ«تعذّر الاشتقاق» — والطبقاتُ الأربعُ خضراء، لأنّها تستورد الوحدةَ
# ولا تقرأ نصَّها. لا يمسك هذا إلّا بناءٌ فعليّ، وقد أمسكه.
CORE_PATCH_VERSION="$("$PY_BIN" -c "import importlib.util,sys; s=importlib.util.spec_from_file_location('m', sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.CORE_PATCH_VERSION)" "$ROOT/build/patch_bundle_extensions.py" 2>/dev/null)"
[[ -z "$CORE_PATCH_VERSION" ]] && { echo "❌ تعذّر اشتقاق CORE_PATCH_VERSION من patch_bundle_extensions.py." >&2; exit 1; }
# الوسم يتضمّن إصدار الحقن؛ بدّله (في المرقِّع) عند توسيع الرُقَع كي يُعاد الترقيع على build.sh نظيف.
if [[ -f "$BSH" ]] && ! grep -q "محراب: رُقَع النواة $CORE_PATCH_VERSION" "$BSH"; then
  log "ترقيع build.sh (حقن الإضافات + رُقَع النواة: لغة + اتّجاه RTL)"
  # أعِد ضبط build.sh لو كان مُرقَّعًا بحقن أقدم كي يُطبَّق الحقن الموسَّع على نسخة نظيفة.
  # نتحقّق من نجاح الاستعادة فعلًا (لا || true صامت) لتفادي تراكب حقنين في الحالة الحديّة.
  if grep -q 'محراب: حقن الإضافات المدمجة' "$BSH"; then
    git -C "$UP" checkout -- build.sh 2>/dev/null || true
    if grep -q 'محراب: حقن الإضافات المدمجة' "$BSH"; then
      echo "❌ تعذّر استعادة build.sh نظيفًا (ربّما صار غير متعقَّب) — لتفادي حقن مزدوج، أوقف." >&2
      echo "   أعد توليد المنبع: shift أو احذف $UP وأعد تشغيل البناء." >&2
      exit 1
    fi
  fi
  "$PY_BIN" "$ROOT/build/patch_bundle_extensions.py" "$BSH"
fi

# ── (ز-3) نظّف مجلّد المخرَج السابق مبكّرًا: لو كان مقفولًا (نسخة محراب قيد التشغيل)
#         يفشل تنظيف gulp بـEBUSY بعد ~20 د. نُجهض الآن برسالة واضحة بدل إهدار الوقت. ──
OUTDIR="$UP/$OUT_NAME"

# ‏**المخرَجُ قد يكون وصلةَ مجلّدٍ إلى خارج شجرة العمل** (`mklink /J`)، وذلك علاجُ تصادمٍ
# قِيس لا فُرِض: مراقبُ الملفّات في محرّرٍ يفتح المستودعَ يُمسِك مقبضًا على مخرَج البناء
# فيمنع تنظيفَه، و`files.watcherExclude` يُرشّح الأحداثَ ولا يُفلِت المقبض. فإخراجُ
# المخرَجِ من الشجرة المراقَبة هو الحلُّ الوحيد الذي لا يعتمد على سلوكِ محرّرٍ خارجيّ.
#
# وحين يكون وصلةً **يُمحى محتواها ولا تُزاح هي**: إزاحةُ الوصلةِ تُتلِفها، فيُعيد gulp
# إنشاءَ مجلّدٍ حقيقيٍّ داخل شجرة العمل ويعود التصادمُ **صامتًا** — أي إصلاحٌ يُبطِل نفسَه
# من أوّل بناء، وهذا أسوأُ من عدم إصلاحٍ لأنّه يبدو مُصلَحًا.
_outdir_is_link() {
  [[ -L "$OUTDIR" ]] && return 0
  [[ "$IS_WIN" == "yes" ]] && fsutil reparsepoint query "$(cygpath -w "$OUTDIR")" >/dev/null 2>&1
}
# «نظيف» = غيرُ موجودٍ **أو** موجودٌ فارغ. الوصلةُ تبقى بعد المسح، فشرطُ `-d` وحدَه
# يقرأ نجاحَ التنظيفِ فشلًا ويُجهض البناء.
_outdir_dirty() { [[ -d "$OUTDIR" ]] && [[ -n "$(ls -A "$OUTDIR" 2>/dev/null)" ]]; }

if [[ -d "$OUTDIR" ]]; then
  # محاولاتٌ متباعدة: مقبضُ ماسحِ الفيروسات/المفهرِس عابرٌ ويسقط في ثوانٍ، وإفشالُ
  # بناءٍ من أربعين دقيقةً على قفلٍ عمرُه ثلاثُ ثوانٍ إهدارٌ لا حراسة.
  # **يُزاح قبل أن يُمحى.** كان `rm -rf` يُطبَّق مباشرةً، فإن كان ملفٌّ واحدٌ مقفولًا
  # مسح الشجرةَ كلَّها حولَه وأجهض — فتبقى حزمةٌ مشحونةٌ لا `Mihrab.exe` فيها، وتحمرّ
  # طبقةُ L2 لسببٍ لا علاقةَ له بما يُفحَص. وقع اليوم: مقبضٌ واحدٌ على
  # `node_modules.asar` أتى على البناء السابق كلِّه. والنقلُ على المجلّد يفشل ذرّيًّا
  # حين يكون فيه مقبضٌ مفتوح — فيُكتشَف القفلُ **والشجرةُ سليمة**، ثمّ يُمحى المُزاح.
  for _try in 1 2 3 4 5; do
    if _outdir_is_link; then
      # وصلة: امسح المحتوى واحتفظ بالرابط.
      # ‏**`$OUTDIR/.` لا `$OUTDIR`**: ‏find لا يعبر وصلةً إلّا بلاحقة النقطة، فبدونها
      # يُرجِع صفرَ مدخلاتٍ ويمرّ المسحُ صامتًا بلا أثر — فيُبنى فوق مخرَجٍ قديم. قِيس.
      find "$OUTDIR/." -mindepth 1 -maxdepth 1 -print0 2>/dev/null | xargs -0 -r rm -rf 2>/dev/null || true
      _outdir_dirty || break
    elif mv "$OUTDIR" "$OUTDIR.wipe.$$" 2>/dev/null; then
      rm -rf "$OUTDIR.wipe.$$" 2>/dev/null || true   # بقاياه لا تضرّ: خارج مسار البناء
      break
    fi
    [[ $_try -lt 5 ]] && sleep 3
  done
  if _outdir_dirty; then
    echo "❌ مجلّد المخرَج مقفول: $OUTDIR" >&2
    # ‏**سمِّ المُمسِك ولا تُخمّنه.** كانت الرسالة هنا تقول «أغلق أيّ نسخة محراب قيد
    # التشغيل»، وقِيس يومًا أنّ المُمسِك عمليّةُ خدمةٍ تابعةٌ لـVS Code ولا نسخةَ
    # محرابٍ تعمل أصلًا. فالقارئُ يبحث عمّا لا وجودَ له، ثمّ يستنتج أنّ العطبَ عرضيّ
    # فيعيد المحاولة — ورسالةٌ تسمّي سببًا خاطئًا أسوأُ من رسالةٍ صامتة.
    _named=no
    if [[ "$IS_WIN" == "yes" && -f "$ROOT/build/who_locks.ps1" ]]; then
      while IFS= read -r _f; do
        _who="$(powershell -NoProfile -ExecutionPolicy Bypass -File "$ROOT/build/who_locks.ps1" \
                  -Path "$(cygpath -w "$_f")" 2>/dev/null | tr -d '\r')"
        [[ -n "$_who" ]] || continue
        _named=yes
        echo "   ${_f#$OUTDIR/} يُمسِكه:" >&2
        while IFS=$'\t' read -r _pid _app; do
          echo "     • PID $_pid — ${_app:-?}" >&2
        done <<< "$_who"
      done < <(find "$OUTDIR" -type f 2>/dev/null | head -5)
    fi
    if [[ "$_named" == "no" ]]; then
      echo "   لم يُعرَف المُمسِك. أغلق أيّ نسخة محراب/VSCodium قيد التشغيل، وأيّ محرّرٍ" >&2
      echo "   يفهرس .upstream، ثمّ أعد المحاولة." >&2
    fi
    exit 1
  fi
fi

# ── (ح) البناء عبر نقطة دخول VSCodium الرسميّة (هوية محراب من الطبقة 2؛ لا رُقَع نواة) ──
cd "$UP"
BUILD_ARGS=()
# if لا «A && B»: في المسار الافتراضيّ (SKIP_SOURCE≠yes) تُفشِل «A && B» السكربتَ تحت set -e.
if [[ "${SKIP_SOURCE:-no}" == "yes" ]]; then BUILD_ARGS+=("-s"); fi
# ── [BR-05] `dev/build.sh` يدهس بيئتَنا قبل أن تصل `utils.sh` ──────────────
# سطرُه `export GH_REPO_PATH="VSCodium/vscodium"` بلا شرط، فتصديرُنا أعلاه كان
# **يبدو** إصلاحًا ولا يصل شيئًا. والمرقِّعُ يُعيد للسطر أدبَ نظيره في `utils.sh`
# (`${VAR:-افتراضيّ}`) — أصغرُ تغييرٍ، ومن لم يضبط شيئًا يرى سلوكَ المنبع كما هو.
# فشلٌ قاتل: بلا هذا يعود لوحُ الترحيب يجلب إعلاناتِ المنبع من مستودعه في كلّ
# فتحةٍ أولى، ويُخبِره بكلّ زائرٍ جديد.
"$PY_BIN" "$ROOT/build/patch_dev_build_env.py" "$UP/dev/build.sh" || {
  echo "❌ فشل ترقيعُ بيئة dev/build.sh — [BR-05] يعود صامتًا، أي أنّ لوحَ الترحيب" >&2
  echo "   سيجلب إعلاناتِ المنبع ومُبلِّغُ الأعطاب سيبحث في قضاياه." >&2
  echo "   الملفّ: $UP/dev/build.sh · المرقِّع: build/patch_dev_build_env.py" >&2
  echo "   شغّله وحدَه لترى سببَه:  \"$PY_BIN\" \"$ROOT/build/patch_dev_build_env.py\" \"$UP/dev/build.sh\"" >&2
  exit 1; }

# ── (و-4ب) وجهةُ خادمِ النفق: **تُبكَّر يومَ يُقاس أنّها تخدم، لا يومَ نأمل** [BR-05] ──
# ‏bin/mihrab-tunnel.exe يحتاج وجهتَين مخبوزتَين وقتَ الترجمة (option_env!):
#   • VSCODE_CLI_UPDATE_ENDPOINT   ⇒ {وجهة}/{جودة}/{نظام}/{معماريّة}/latest.json
#     تعيد {"name","version"} — update_service.rs:46
#   • VSCODE_CLI_DOWNLOAD_ENDPOINT ⇒
#     {وجهة}/download/{name}/{app}-reh-web-{نظام}-{معماريّة}-{name}.tar.gz
# و patch_cli_endpoints.py جعل تصديرَهما **شرطيًّا** في build_cli.sh، فما لا
# نُصدِّره هنا يعطي option_env! القيمةَ None ويردّ الـCLI «no download url» صراحةً.
#
# ⚠️ **ولا يُصدَّر عنوانٌ لم يُقَس.** الدَّينُ الذي يُغلَق هنا لم يكن غيابَ الوجهة بل
#    وجهةً **بلا خلفيّة**: عنوانٌ صحيحُ الشكل يردّ 404، يبدو مُصلَحًا في القراءة
#    ويكسر في التشغيل. فالشرطُ ليس «هل ضُبِط متغيّر» بل «هل يخدم العنوانُ الأثرَ
#    فعلًا الآن»: يُجلَب المانيفست، ويُبنى منه اسمُ الأثر، ويُطلَب رأسُه.
#    فإن خدم بُكِّرت الوجهتان، وإلّا فلا شيءَ يُخبَز ويُقال السببُ وطريقُ إصلاحه.
#    وهي حلقةٌ تُغلِق نفسَها: بناءٌ يُخرِج الأثرَ ⇒ يُرفَع بـ build/publish_server.sh
#    ⇒ البناءُ التالي يقيسه فيخبزه. ولا خطوةَ يدويّةً في السلسلة.
#
# ‏${VAR-افتراضيّ} لا ${VAR:-…}: قيمةٌ فارغةٌ **صريحةٌ** تعني «أطفِئ النفق»، وهو
# فرقٌ حقيقيّ عن «لم أضبط شيئًا».
MIHRAB_SERVER_BASE="${MIHRAB_SERVER_BASE-https://sad-lang.org/mihrab/dl/server}"
_CLI_ENDPOINT=""
case "$OS_NAME" in
  windows) _CLI_OS="win32" ;;
  linux)   _CLI_OS="linux" ;;
  osx)     _CLI_OS="darwin" ;;
  *)       _CLI_OS="" ;;
esac
if [[ -z "$MIHRAB_SERVER_BASE" ]]; then
  log "لا وجهةَ خادمٍ للنفق (MIHRAB_SERVER_BASE فارغةٌ صراحةً) — يُشحَن الـCLI بلا تنزيل"
elif [[ -z "$_CLI_OS" ]]; then
  log "نظامٌ لا يعرفه قالبُ أثرِ الخادم ($OS_NAME) — لا تُبكَّر وجهةُ النفق"
else
  _CLI_APP="$(node -p "require(process.argv[1]).applicationName" "$UP/product.json")"
  _LATEST="$MIHRAB_SERVER_BASE/stable/$_CLI_OS/$VSCODE_ARCH/latest.json"
  # ── أرضيّةُ صدقٍ للمِجَسّ: **عجزُه يُميَّز عن غيابِ الأثر** ──
  # ‏أوّلُ صياغةٍ كتبت أنبوبًا واحدًا `curl … | jq -r '.name // empty'` وقرأت
  # الفراغَ «لا مانيفست». وقِيس أنّها تقول ذلك حرفيًّا حين **يغيب `jq`** —
  # فتمرّ رسالةٌ تصف الخادمَ وهي تصف جهازَ البناء، ويُشحَن CLI أعمى بسببٍ
  # مكتوبٍ خاطئ. وهي الفئةُ عينُها التي أُغلِقت في `verify_cache` وفي بوّابة
  # `vscodium`: مِجَسٌّ عاجزٌ يُعلن النتيجةَ السالبة.
  #
  # فالحالاتُ ثلاثٌ ولا تُخلَط: رمزٌ غيرُ 200 ⇒ لا مانيفستَ منشور (وهي الحالةُ
  # الصحيحةُ اليوم). و200 بلا اسمٍ مقروء ⇒ **إسقاطُ بناء**، لا تخطٍّ: خادمٌ
  # يخدم مانيفستًا لا نقرؤه عطبٌ عندنا لا نقصٌ في نشرنا. ولا `|| true` على
  # الإسناد: `curl -f` يخرج بغير صفرٍ على 404 والملفُّ تحت `set -e`.
  _MAN="$(mktemp)"
  _MAN_CODE="$(curl -fsS -o "$_MAN" -w '%{http_code}' --max-time 20 "$_LATEST" 2>/dev/null || true)"
  if [[ "$_MAN_CODE" != "200" ]]; then
    rm -f "$_MAN"
    log "لا مانيفستَ خادمٍ على $_LATEST (رمز ${_MAN_CODE:-—}) — لا تُخبَز وجهةُ النفق"
    echo "   المعنى: tunnel و serve-web سيردّان «no download url» عند المستخدم." >&2
    echo "   وهو **مقصودٌ** ما لم يُنشَر الأثر. لنشره بعد هذا البناء:" >&2
    echo "     build/publish_server.sh \$UP/assets/<الأثر>.tar.gz" >&2
    _REL_NAME=""
  else
    _REL_NAME="$("$JQ_BIN" -r '.name // empty' < "$_MAN" 2>/dev/null || true)"
    rm -f "$_MAN"
    [[ -n "$_REL_NAME" ]] || {
      echo "❌ مانيفستُ الخادم يُخدَم بـ200 ولا يُقرأ منه اسمٌ: $_LATEST" >&2
      echo "   وهذا عطبٌ عندنا لا نقصٌ في النشر — إمّا jq غائبٌ أو معطوب" >&2
      echo "   (\$JQ_BIN = ${JQ_BIN:-—})، وإمّا أنّ المانيفست ليس {\"name\",\"version\"}." >&2
      echo "   ولو قُرِئ فراغًا «لا مانيفست» لَشُحِن CLI أعمى بسببٍ مكتوبٍ خاطئ." >&2
      exit 1; }
  fi
  if [[ -z "$_REL_NAME" ]]; then
    :
  else
    _TGZ_URL="$MIHRAB_SERVER_BASE/download/$_REL_NAME/$_CLI_APP-reh-web-$_CLI_OS-$VSCODE_ARCH-$_REL_NAME.tar.gz"
    _TGZ_CODE="$(curl -fsS -o /dev/null -w '%{http_code}' -I --max-time 20 "$_TGZ_URL" 2>/dev/null || true)"
    if [[ "$_TGZ_CODE" == "200" ]]; then
      export VSCODE_CLI_DOWNLOAD_ENDPOINT="$MIHRAB_SERVER_BASE"
      export VSCODE_CLI_UPDATE_ENDPOINT="$MIHRAB_SERVER_BASE"
      _CLI_ENDPOINT="$MIHRAB_SERVER_BASE"
      log "وجهةُ النفق مقيسةٌ وتخدم ($_REL_NAME) — تُخبَز في الثنائيّ [BR-05]"
    else
      # ‏**مانيفستٌ بلا أثرٍ أسوأُ من لا مانيفست**: يَعِد باسمٍ ثمّ يُخفِق عند
      # التنزيل، فيبدو العطبُ عطبَ شبكةٍ عند المستخدم لا نقصًا في نشرنا.
      log "مانيفستُ الخادم يَعِد بـ$_REL_NAME والأثرُ يردّ ${_TGZ_CODE:-—} — لا تُخبَز الوجهة"
      echo "   المفقود: $_TGZ_URL" >&2
    fi
  fi
fi

log "بدء dev/build.sh ${BUILD_ARGS[*]:-}"
# "${BUILD_ARGS[@]:-}" يمنع خطأ unbound تحت set -u عند مصفوفة فارغة في إصدارات bash الأقدم.
bash dev/build.sh "${BUILD_ARGS[@]:-}"

# ── (ط-0) خبز الواجهة العربيّة في nls.messages.json الافتراضيّ (مساهمة بناء — الطبقة 2) ──
# خطوة بعد-بناء سريعة على الـartifacts (لا إعادة gulp). تجعل العربيّة الافتراضيّ الحرفيّ
# للنواة ⇒ أوّل فتح عربيّ بلا إعادة تحميل ولا اعتماد على مسح حزمة لغة. idempotent.
# macOS: حلُّ حزمة `.app` الآن بعد أن صارت موجودة (اسمُها عربيٌّ مشتقٌّ من nameLong).
if [[ "$OS_NAME" == "osx" ]]; then
  MAC_APP="$(find "$OUTDIR" -maxdepth 1 -name '*.app' -print -quit)"
  [[ -n "$MAC_APP" ]] || { echo "❌ لا حزمةَ .app في $OUTDIR" >&2; exit 1; }
  APP_REL="$(basename "$MAC_APP")/Contents/Resources/app"
  LAUNCH_REL="$(basename "$MAC_APP")/Contents/Info.plist"
  log "حزمةُ macOS: $(basename "$MAC_APP")"
fi
APP_DIR="$OUTDIR/$APP_REL"

# ── (ط-0ز) إعادةُ فرض هويّة محراب على product.json **المشحون** ──
# ⚠️ قِيست: خطوةُ (ز-2) تدمج تجاوزاتنا فوق `$UP/product.json`، لكنّ prepare_vscode.sh
# الخاصّ بـVSCodium يكتب بعضَ المفاتيح **بعد** ذلك الدمج، فيعود بعضُها إلى قيمة المنبع
# في المنتج النهائيّ. أُمسك حيًّا: `updateUrl` نجا `null`، بينما عاد
# `serverDownloadUrlTemplate` يشير إلى تغذية إصدارات VSCodium في الحزمة المشحونة —
# دمجٌ واحدٌ مبكّر لا يكفي، فآخرُ من يكتب هو من يفوز.
# فالحلُّ أن نُعيد الفرض على الملفّ الذي يُشحَن فعلًا (وهو ما تقيسه طبقةُ L2).
#
# **ودالّةٌ لا كتلة**: كانت مربوطةً بـ`$APP_DIR` وحدَه، فنجا العطبُ نفسُه في شجرة
# الويب — قِيس على 1.126.05942: `serverDownloadUrlTemplate` فيها يشير إلى إصدارات
# VSCodium. أي أنّ محرابًا المنشورَ يوزّع المنبعَ باسمه. الشجرتان تُشحَنان، فتُعامَلان
# معاملةً واحدة.
reforce_identity() {
  local _dir="$1" _label="$2"
  [[ -f "$_dir/product.json" && -f "$OVERRIDES" ]] || return 0
  log "إعادة فرض هوية محراب على product.json المشحون ($_label)"
  if ! jq -s '.[0] * .[1] | with_entries(select(.key | startswith("_comment") | not))'       "$_dir/product.json" "$OVERRIDES" > "$_dir/product.json.tmp"; then
    rm -f "$_dir/product.json.tmp"
    echo "❌ فشل إعادة فرض هوية محراب على $_label." >&2; return 1
  fi
  mv -f "$_dir/product.json.tmp" "$_dir/product.json"
}

# بوّابةُ هويّةٍ على أيّ شجرةٍ تُشحَن. تُستدعى للمكتبيّ وللويب، لأنّ «بُني بنجاح»
# ليس دليلَ «يحمل هويّتَنا» — وقد سقطت الهويّةُ في المشحون مرّتين قبل هذا السطر.
assert_identity() {
  local _dir="$1" _label="$2" _n _l _u _s
  [[ -f "$_dir/product.json" ]] || return 0
  _n="$("$JQ_BIN" -r '.nameLong // ""' "$_dir/product.json")"
  _l="$("$JQ_BIN" -r '.defaultLocale // ""' "$_dir/product.json")"
  _u="$("$JQ_BIN" -r '.updateUrl // "null"' "$_dir/product.json")"
  _s="$("$JQ_BIN" -r '.serverDownloadUrlTemplate // "null"' "$_dir/product.json")"
  [[ "$_n" == "محراب" ]] || { echo "❌ [$_label] هويّةٌ مفقودة: nameLong=$_n" >&2; return 1; }
  [[ "$_l" == "ar"     ]] || { echo "❌ [$_label] اللغةُ الافتراضيّة ليست العربيّة: $_l" >&2; return 1; }
  [[ "$_u" == "null"   ]] || { echo "❌ [$_label] updateUrl ليس null: $_u" >&2; return 1; }
  # وهذا هو المفتاحُ الذي نجا في الويب: تغذيةُ تنزيلِ الخادم يجب ألّا تشير إلى المنبع.
  case "$_s" in
    *vscodium*|*VSCodium*|*microsoft*|*Microsoft*)
      echo "❌ [$_label] serverDownloadUrlTemplate يشير إلى المنبع: $_s" >&2; return 1 ;;
  esac
  log "هويّةُ $_label سليمة (nameLong · locale · updateUrl · serverDownloadUrlTemplate)"
}

reforce_identity "$APP_DIR" "المكتبيّ" || exit 1

# ── (ط-0أ) حقن ترجمة بيانات الامتدادات إلى العربيّة — مساهمة بناء (الطبقة 2) ──
# يعيد بناء contents.package في ملفّ i18n لحزمة اللغة لكلّ امتداد مدمج (عناوين أوامر/أوصاف
# إعدادات)؛ المسار الذي تحلّه النواة فعلًا حين تكون حزمة اللغة نشطة (getLocalizedMessages
# ⟵ nlsConfig.translations[id].contents.package). package.nls.ar.json يُتجاوَز مع حزمة لغة
# نشطة، فيُكتب فقط للامتدادات غير المُدرَجة فيها. أُثبِت حيًّا عبر CDP.
# **قبل الخبز**: bake_nls يرفع نسخة حزمة اللغة من بصمة تشمل ملفّات i18n المحقونة هنا ⇒
# إبطال كاش CLP (%APPDATA%/clp) في «التحديث فوق ملفّ تعريف قائم». [[mihrab-stale-clp...]]
if [[ -d "$APP_DIR/extensions" ]]; then
  log "حقن ترجمة بيانات الامتدادات (contents.package في حزمة اللغة)"
  "$PY_BIN" "$ROOT/build/patch_extension_nls.py" "$APP_DIR" || {
    echo "❌ فشل حقن ترجمة بيانات الامتدادات — راجع أعلاه." >&2; exit 1; }
else
  log "تخطّي حقن بيانات الامتدادات: لا مجلّد extensions في $APP_DIR"
fi

# ── (ط-0أ2) رياضيّاتُ أعمدة الطرفيّة تعرف الصفَّ اليمينيّ [DR-08] ──
# ورقةُ الاتّجاه تقلب **التخطيط**، وxterm يحسب العمودَ من يسار الشاشة حسابًا صلبًا.
# فبلا هذه الرقعة يرى المستخدمُ نصًّا عربيًّا صحيحًا **ويحدّد غيرَه** عند النقر — وهو
# أسوأُ من عرضٍ مقلوبٍ يعرف صاحبُه أنّه مقلوب. ولذلك الفشلُ هنا **يُجهض البناء**:
# شحنُ الورقة بلا الرقعة يُنتج العطبَ الأسوأ لا نصفَ الإصلاح.
if [[ -d "$APP_DIR/node_modules/@xterm/xterm" ]]; then
  log "ترقيع اتّجاه أعمدة xterm (فأرة + تحديد)"
  "$PY_BIN" "$ROOT/build/patch_xterm_bidi.py" "$APP_DIR" || {
    echo "❌ فشل ترقيع اتّجاه xterm — راجع أعلاه. ورقةُ الاتّجاه بلا هذه الرقعة تعني" >&2
    echo "   تحديدًا يقع في غير موضع النقر. لا يُشحَن." >&2; exit 1; }
else
  echo "❌ لا حزمةَ xterm في المشحون ($APP_DIR/node_modules/@xterm/xterm)." >&2; exit 1
fi

# ── (ط-0أ3) الخطُّ العربيُّ المحزوم يُحمَّل فعلًا [AR-02] ──
# القاعدةُ تُحقَن قبل التحزيم بمصدر `data:` (لأنّ esbuild بلا مُحمِّل .woff2)، و
# ‏`font-src` في workbench.html لا يذكر `data:` ⇒ المتصفّحُ يحجب الخطَّ **صامتًا**
# (قِيس حيًّا: "Kawkab Mono:error" و securitypolicyviolation "font-src data").
# بعد الحزم لا esbuild، فيُنسَخ الملفُّ ويُوصَل بـurl() نسبيّ يغطّيه 'self'.
# لا يُجهض البناء: بلا هذا يسقط العرضُ لبقيّة المكدّس — نقصُ جودةٍ لا عطبٌ صامتٌ ضارّ.
if [[ -f "$APP_DIR/out/vs/workbench/workbench.desktop.main.css" ]]; then
  log "وصلُ الخطّ العربيّ المحزوم بملفٍّ مجاور (بدل data: المحجوبة)"
  "$PY_BIN" "$ROOT/build/patch_workbench_font.py" "$APP_DIR" || {
    echo "❌ فشل وصلُ الخطّ العربيّ — راجع أعلاه." >&2; exit 1; }
else
  log "تخطّي وصلِ الخطّ: لا workbench.desktop.main.css في $APP_DIR"
fi

# ── (ط-0ب) خبز الواجهة العربيّة + رفع نسخة حزمة اللغة (يشمل بصمة i18n المحقونة أعلاه) ──
if [[ -f "$APP_DIR/out/nls.messages.json" ]]; then
  log "خبز الواجهة العربيّة في nls.messages.json"
  "$PY_BIN" "$ROOT/build/bake_nls_arabic.py" "$APP_DIR" || {
    echo "❌ فشل خبز الترجمة العربيّة — راجع أعلاه." >&2; exit 1; }
else
  log "تخطّي الخبز: لا nls.messages.json في $APP_DIR (بناء غير مكتمل؟)"
fi

# ── (ط-0د) البناءُ نفسُه يُخرج محرابَ المتصفّح — فليُعرَّب هو الآخر [WEB-01] ──
# ‏`vscode-reh-web-*` يُنتَج في **كلّ** بناءٍ (‏424 م.ب) وفيه هويّةُ محرابٍ كاملةٌ من
# `product.json`، وورقةُ الاتّجاه كلُّها (‏130 قاعدةَ `[dir=rtl]` — نفسُ عددِ المكتبيّ
# بالضبط). لكنّ خطواتِ ما بعد البناء أعلاه كلَّها مربوطةٌ بـ`$APP_DIR` وحدَه، فكانت
# واجهةُ المتصفّح **إنجليزيّةً بالكامل**: 1 سلسلة عربيّة من 21922 (‏0%) مقابل 94% في
# المكتبيّ. أي اتّجاهٌ عربيٌّ بلا كلمةٍ عربيّة.
#
# والمِجَسّاتُ الأربعةُ تعمل على شجرة الويب بلا تعديلٍ في منطقها: تخطيطُ
# `out/nls.{keys,messages}.json` و`extensions/` و`node_modules/@xterm/xterm` متطابقٌ مع
# المكتبيّ. اختلافان اثنان فقط، وكلاهما مُعالَجٌ في الأداة لا هنا:
#   • الويبُ يخدم `out/nls.messages.js` للمتصفّح (لا وجودَ له في المكتبيّ) — يخبزه
#     `bake_nls_arabic.py` مع الـjson.
#   • ورقتُه `out/vs/code/browser/workbench/workbench.css` لا `workbench.desktop.main.css`.
# ولا بصماتِ نزاهةٍ في `product.json` الخاصّ به (لا مفتاحَ `checksums`) ⇒ لا خطوةَ (ط-0ج).
#
# وقِيس حيًّا على 1.126.05942 عبر CDP في Edge: `dir=rtl` على الـworkbench، شريطُ النشاط
# يمينًا، 545 محرفًا عربيًّا من 779 مرئيّة، و`Kawkab Mono:loaded` بلا خرقِ CSP —
# وسياسةُ الويب `font-src 'self' blob:` تخلو من `data:` كسياسةِ المكتبيّ، فرقعةُ [AR-02]
# لازمةٌ هنا كذلك.
_REH_DIRS=("$UP"/vscode-reh-web-*)
if [[ -d "${_REH_DIRS[0]:-}" ]]; then
  if (( ${#_REH_DIRS[@]} != 1 )); then
    echo "❌ وُجد ${#_REH_DIRS[@]} مجلّدَ ويبٍ في $UP — لا يُعرَّب ما لم يُقرأ." >&2; exit 1
  fi
  WEB_DIR="${_REH_DIRS[0]}"
  log "تعريبُ بناء الويب: $(basename "$WEB_DIR")"
  reforce_identity "$WEB_DIR" "الويب" || exit 1
  "$PY_BIN" "$ROOT/build/patch_extension_nls.py" "$WEB_DIR" || {
    echo "❌ فشل حقنُ ترجمة الامتدادات في بناء الويب." >&2; exit 1; }
  "$PY_BIN" "$ROOT/build/patch_xterm_bidi.py" "$WEB_DIR" || {
    echo "❌ فشل ضبطُ اتّجاه xterm في بناء الويب." >&2; exit 1; }
  "$PY_BIN" "$ROOT/build/patch_workbench_font.py" "$WEB_DIR" || {
    echo "❌ فشل وصلُ الخطّ العربيّ في بناء الويب." >&2; exit 1; }
  "$PY_BIN" "$ROOT/build/bake_nls_arabic.py" "$WEB_DIR" || {
    echo "❌ فشل خبزُ العربيّة في بناء الويب." >&2; exit 1; }
  assert_identity "$WEB_DIR" "الويب" || exit 1

  # ── (ط-0د1) والأثرُ يُحزَم — وإلّا فالنفقُ وعدٌ بلا خلفيّة [BR-05] ──
  # هذه الشجرةُ نفسُها هي ما ينزّله `mihrab-tunnel` ويشغّله. وكانت تُنتَج في كلّ
  # بناءٍ **وتُترَك في مكانها**: 428 م.ب معرَّبةً بالكامل، لا يراها أحد. فالدَّينُ
  # لم يكن في المصدر ولا في الثنائيّ، بل في **خطوةِ تحزيمٍ غائبة**.
  #
  # والاسمُ ليس اختيارًا: `update_service.rs` يبني العنوانَ حرفيًّا
  # `{app}-reh-web-{نظام}-{معماريّة}-{name}.tar.gz` — فحرفٌ زائدٌ هنا يعني 404
  # هناك، وهو الصنفُ الذي يبدو مُصلَحًا ولا يعمل. ولهذا يُقرأ `applicationName`
  # من `product.json` ولا يُكتب بيدٍ (كان `VSCodium` في بيئة البناء).
  #
  # والمحتوى **من جذر الشجرة لا من مجلّدها**: الـCLI يفكّ الأرشيفَ ثمّ يبحث عن
  # `bin/<serverApplicationName>` مباشرةً — أرشيفٌ يحمل مجلّدًا واحدًا في جذره
  # يفكّ سليمًا ثمّ لا يجد نقطةَ الدخول، فيُخفِق **بعد** تنزيل مئات الميغابايتات.
  case "$OS_NAME" in
    windows) _PKG_OS="win32" ;;
    linux)   _PKG_OS="linux" ;;
    osx)     _PKG_OS="darwin" ;;
    *)       _PKG_OS="" ;;
  esac
  _PKG_APP="$(node -p "require(process.argv[1]).applicationName" "$UP/product.json")"
  _PKG_SRV="$(node -p "require(process.argv[1]).serverApplicationName" "$UP/product.json")"
  _PKG_VER="$(node -p "require(process.argv[1]).version" "$UP/vscode/package.json")"
  if [[ -z "$_PKG_OS" ]]; then
    log "نظامٌ لا يعرفه قالبُ أثرِ الخادم ($OS_NAME) — لا يُحزَم"
  elif [[ -z "$_PKG_APP" || -z "$_PKG_VER" || "$_PKG_APP" == "undefined" || "$_PKG_VER" == "undefined" ]]; then
    echo "❌ اسمُ التطبيق أو نسختُه لا يُقرآن — واسمُ الأثر يُشتقّ منهما لا يُكتب بيد." >&2
    echo "   applicationName=${_PKG_APP:-—} · version=${_PKG_VER:-—}" >&2
    exit 1
  else
    # ونقطةُ الدخول تُقاس قبل التحزيم: أرشيفٌ بلا `bin/<اسم>` يُنزَّل كاملًا ثمّ يُخفِق.
    _PKG_ENTRY=""
    for _c in "$WEB_DIR/bin/$_PKG_SRV" "$WEB_DIR/bin/$_PKG_SRV.cmd" "$WEB_DIR/bin/$_PKG_SRV.sh"; do
      # ‏`if` لا «[[ … ]] && …» — **وليس لـ`set -e`**. جُرّبت الصيغتان:
      # شرطٌ كاذبٌ في آخر دورةٍ **لا يُنهي السكربت**، لأنّ bash يعفي
      # ما يسبق الطرفَ الأخيرَ في قائمة `&&`. فالسببُ قراءةٌ لا أكثر،
      # ويُقال صراحةً: تعليلٌ يدّعي خطرًا لا يقع يُعلّم قارئَه قاعدةً خاطئة.
      if [[ -f "$_c" ]]; then _PKG_ENTRY="$_c"; break; fi
    done
    [[ -n "$_PKG_ENTRY" ]] || {
      echo "❌ لا نقطةَ دخولٍ في $WEB_DIR/bin/ باسم $_PKG_SRV — الـCLI يبحث عنها" >&2
      echo "   بعد فكّ الأرشيف، فيُخفِق بعد تنزيل مئات الميغابايتات لا قبله." >&2
      echo "   الموجود: $(ls "$WEB_DIR/bin" 2>/dev/null | tr '\n' ' ')" >&2
      exit 1; }
    mkdir -p "$UP/assets"
    REH_TGZ="$UP/assets/$_PKG_APP-reh-web-$_PKG_OS-$VSCODE_ARCH-$_PKG_VER.tar.gz"
    log "تحزيمُ أثر الخادم: $(basename "$REH_TGZ")"
    ( cd "$WEB_DIR" && tar czf "$REH_TGZ" . ) || {
      echo "❌ فشل تحزيمُ أثر الخادم." >&2; exit 1; }
    # ‏**والتحزيمُ يُقاس لا يُفترَض**: `tar` يخرج بصفرٍ على أرشيفٍ ناقصٍ في حالاتٍ
    # (قرصٌ امتلأ · ملفٌّ تغيّر أثناءه)، وأرشيفٌ ينقصه ما ينقصه يفشل **عند
    # المستخدم** لا هنا. فتُقرأ نقطةُ الدخول من داخله.
    tar tzf "$REH_TGZ" >/dev/null 2>&1 || {
      echo "❌ أرشيفُ الخادم لا يُقرأ بعد كتابته: $REH_TGZ" >&2; exit 1; }
    tar tzf "$REH_TGZ" 2>/dev/null | grep -q "^\./bin/$_PKG_SRV" || {
      echo "❌ أرشيفُ الخادم بلا ./bin/$_PKG_SRV في جذره — يُفكّ سليمًا ولا يُقلِع." >&2
      exit 1; }
    log "أثرُ الخادم جاهز: $(du -m "$REH_TGZ" | cut -f1) م.ب · $(basename "$REH_TGZ")"
    log "لنشره: build/publish_server.sh \"$REH_TGZ\""
  fi
else
  log "لا بناءَ ويبٍ (vscode-reh-web-*) في $UP — تُخطّى خطوةُ تعريبه"
fi

# ── (ط-0د2) الشجرةُ الثالثة: محرابٌ الثابت بلا خادم (`vscode-web`) [WEB-03] ──
# `gulp vscode-web-min` يُخرج شجرةً ثالثةً هي **ما يُنشَر فعلاً** بعد أن أُوقِف النشرُ
# بخادم. وكانت خارجَ كلّ ما سبق: لا تعريبَ ولا هويّةَ ولا حارس — لأنّ الحلقةَ
# أعلاه مربوطةٌ بـ`vscode-reh-web-*` حرفيّاً. والطبقاتُ الخمسُ تبقى خضراءَ
# على شجرةٍ تُنشَر بواجهةٍ إنجليزيّةٍ كاملةٍ وهويّةِ VSCodium الموروثة.
#
# وثلاثةُ فروقٍ عن أختِها، كلُّها **معالَجةٌ في الأدوات لا هنا**:
#   • لا `product.json` إطلاقاً ⇒ لا (ط-0ز) ولا `assert_identity`. الهويّةُ تسكن
#     صفحةَ المضيف، ويفرضها `patch_web_host.py` مشتقّةً من ملفّ التجاوزات نفسِه.
#   • ورقتُها `out/vs/workbench/workbench.web.main.internal.css` — ثالثةُ مرشّحات
#     `patch_workbench_font.py`.
#   • `out/nls.messages.js` فيها يسبقُه إشعارُ حقوقٍ منبعيّ ⇒ `bake_nls_arabic.py`
#     يبحث عن البادئة ولا يشترط موضِعَها، ويحفظ الرأس.
# ── (ط-0ج2) الشجرةُ الثالثة **تُبنى** لا تُفترَض ──
# كان اسمُ الهدف `vscode-web-min` يرد في تعليقٍ واحدٍ ولا يُستدعى قطّ. فبناءٌ نظيفٌ
# لا يُخرج الشجرةَ الثابتة إطلاقًا، والفرعُ أدناه يطبع «تُخطّى» ويمضي بصفر — و**ثلاثةُ
# حرّاسٍ كُتِبوا لها يبقون أخضرَ على غيابها**:
#   • `${STATIC_DIR:+…}` في بوّابتَي التسرّب و[BR-05] تتمدّد إلى لا شيء.
#   • و[WEB-03] في L2 يرفع `_Skip` فلا يجري على أيّ آلةٍ ولا في CI.
# أي أنّ ما يُنشَر على mihrab.dev كان يُبنى **يدويًّا خارج المستودع**، والحراسةُ كلُّها
# تقيس نصَّ هذا الملفّ لا ناتجَه. حارسٌ يحرس نيّةً غيرَ منفَّذة.
#
# والهدفُ لا يستغرق إلّا ~9 دقائق (قِيس)، لأنّ الشجرةَ مُرقَّعةٌ ومُصرَّفةٌ سلفًا من
# البناء المكتبيّ — فهذه خطوةُ تحزيمٍ فوقها لا بناءٌ من الصفر.
# **رايةٌ تُقرأ لا تُطابَق حرفيًّا.** `== "yes"` وحدَها تجعل `MIHRAB_BUILD_WEB=1`
# أو `=true` أو `=YES` **يتخطّى البناءَ صامتًا** ويطبع «عمدًا» — وهو أسوأُ من رفضٍ.
case "$(printf '%s' "${MIHRAB_BUILD_WEB:-yes}" | tr 'A-Z' 'a-z')" in
  yes|y|1|true|on)  _BUILD_WEB=yes ;;
  no|n|0|false|off) _BUILD_WEB=no  ;;
  *) echo "❌ قيمةٌ غيرُ مفهومةٍ لـMIHRAB_BUILD_WEB: ${MIHRAB_BUILD_WEB}" >&2
     echo "   المقبول: yes|no (‏1|0 · true|false · on|off)" >&2; exit 1 ;;
esac
if [[ "$_BUILD_WEB" == "yes" ]]; then
  log "بناءُ الشجرة الثابتة (gulp vscode-web-min)"
  if ( cd "$UP/vscode" && node --max-old-space-size=8192 \
         node_modules/gulp/bin/gulp.js vscode-web-min ); then
    # **طابعُ طزاجةٍ يربط الشجرةَ بهذا البناء.** بدونه لا شيءَ يميّز شجرةً
    # أُنتجت الآن من شجرةٍ نجت من بناءٍ قديم: كلتاهما مجلّدٌ موجود، فتُعرَّب
    # وتُحزَم وتُنشَر — وهو العطبُ الأصليُّ نفسُه («ما يُنشَر يُبنى خارج المستودع»)
    # بحرفيّته. ويُقرأ الطابعُ في (ط-0د2) فيرفض شجرةً ليست من هذه الجولة.
    date -u +%Y-%m-%dT%H:%M:%SZ > "$UP/vscode-web/.mihrab-built-at"
    log "الشجرةُ الثابتة بُنيت"
  else
    echo "❌ فشل بناءُ الشجرة الثابتة (vscode-web-min) — وهي ما يُنشَر على mihrab.dev." >&2
    echo "   لتخطّيها عمدًا: MIHRAB_BUILD_WEB=no" >&2
    exit 1
  fi
else
  log "MIHRAB_BUILD_WEB=no — تُخطّى الشجرةُ الثابتة عمدًا"
fi

_STATIC_DIR="$UP/vscode-web"
if [[ -d "$_STATIC_DIR" ]]; then
  # شجرةٌ بلا طابعٍ = شجرةٌ لم تُنتَج في هذه الجولة. تُرفَض بدل أن تُنشَر صامتةً.
  if [[ "$_BUILD_WEB" == "yes" && ! -f "$_STATIC_DIR/.mihrab-built-at" ]]; then
    echo "❌ شجرةٌ ثابتةٌ بلا طابعِ بناء ($_STATIC_DIR/.mihrab-built-at) — بقيّةُ" >&2
    echo "   بناءٍ سابق. احذفها ثمّ أعِد البناء، أو MIHRAB_BUILD_WEB=no عن قصد." >&2
    exit 1
  fi
  log "تعريبُ محرابِ المتصفّح الثابت: $(basename "$_STATIC_DIR")"
  "$PY_BIN" "$ROOT/build/patch_web_host.py" "$_STATIC_DIR" || {
    echo "❌ فشل تركيبُ صفحة المضيف وهويّتها." >&2; exit 1; }
  "$PY_BIN" "$ROOT/build/patch_extension_nls.py" "$_STATIC_DIR" || {
    echo "❌ فشل حقنُ ترجمة الامتدادات في البناء الثابت." >&2; exit 1; }
  "$PY_BIN" "$ROOT/build/patch_xterm_bidi.py" "$_STATIC_DIR" || {
    echo "❌ فشل ضبطُ اتّجاه xterm في البناء الثابت." >&2; exit 1; }
  "$PY_BIN" "$ROOT/build/patch_workbench_font.py" "$_STATIC_DIR" || {
    echo "❌ فشل وصلُ الخطّ العربيّ في البناء الثابت." >&2; exit 1; }
  "$PY_BIN" "$ROOT/build/bake_nls_arabic.py" "$_STATIC_DIR" || {
    echo "❌ فشل خبزُ العربيّة في البناء الثابت." >&2; exit 1; }
  "$PY_BIN" "$ROOT/build/patch_web_host.py" --verify "$_STATIC_DIR" || {
    echo "❌ بوّابةُ هويّةِ صفحة المضيف رفضت البناءَ الثابت." >&2; exit 1; }
  STATIC_DIR="$_STATIC_DIR"
else
  log "لا بناءَ ثابتٍ (vscode-web) في $UP — تُخطّى خطوةُ تعريبه"
fi

# ── (ط-0ج) بصماتُ النزاهة تُحدَّث **بعد** آخرِ خطوةٍ تكتب في `out/` [PK-01] ──
# المنبعُ يبصم عشرةَ ملفّاتٍ في `product.json` ويتحقّق منها عند كلّ إقلاع، فإن اختلفت
# واحدةٌ عرض «يبدو أن تثبيت Mihrab تالف. يرجى إعادة التثبيت». و(ط-0أ3) أعلاه يعيد
# كتابةَ `workbench.desktop.main.css` **بعد** حساب البصمة، فكان الإشعارُ يظهر لكلّ
# مستخدمٍ في كلّ إقلاع — قِيس على البناء 1.121.05937: تسعٌ مطابقةٌ وواحدةٌ بائتة.
# ولم يمسكه حارس: L2 يقيس وجودَ الشيفرة لا نزاهتَها.
#
# **موضعُه هنا لا في مكانٍ آخر**: كلُّ ما بعده قراءةٌ وتحقّق (ط · ي · ي-2)، فلو سبق
# خطوةً تكتب لعاد العطبُ صامتًا. أيُّ خطوةِ كتابةٍ تُضاف لاحقًا تسبق هذا السطر.
# ── حزمةُ المتصفّح لا تُشحَن إلى سطح المكتب ──
# ‏`patch_bundle_extensions.py` يبني `extensions/*/dist/web/extension.js` في شجرة
# المصدر المشتركة، فتُنسَخ إلى **كلّ** الشجرات — ومنها المكتبيّة، التي لا تقرأ حقلَ
# `browser` إطلاقًا (مضيفُها عقدةٌ يقرأ `main`). فمئةُ كيلوبايتٍ لكلّ امتدادٍ تُشحَن
# ميّتةً في كلّ تثبيت.
#
# ولم يُكشَف بتفتيش: **ميزانيّةُ الحجم هي التي احمرّت** (`ext_mihrab_welcome`:
# ‏0.59 م.ب > سقف 0.55). ولو رُفِع السقفُ حينها — وهو أسهلُ إصلاحٍ ظاهرًا — لَبقي
# الوزنُ الميّتُ ولَصار الحارسُ يُصادِق عليه. السقفُ يُرفَع لنموٍّ مشروع، لا ليَسَع
# ما لا ينبغي أن يُشحَن.
#
# **وموضعُه قبل `refresh_checksums.py`** بحكم القاعدة المكتوبة تحته: كلُّ ما بعده
# قراءةٌ وتحقّق، فخطوةُ كتابةٍ بعده تُبطِل البصماتِ صامتةً.
# ⚠️⚠️ **الهدفُ `dist/web` لا `dist`، والامتدادُ يُنتقى بمدخله لا بموضعه.** أوّلُ
#    صياغةٍ حذفت `$(dirname "$_wd")` — أي `dist/` كاملًا — ولمَحت كلَّ امتدادٍ فيه
#    مجلَّدٌ بهذا الاسم. و`dist/` في امتدادات المنبع **هي حزمتُها الأساسيّة**
#    (`typescript-language-features` · `git` · `markdown-language-features`:
#    `main=./dist/extension`)، فكانت تُفرِّغ سبعةً وعشرين امتدادًا من مدخلها.
#    والمسارُ `./dist/web/extension.js` مخرَجُ `patch_bundle_extensions.py` وحدَه؛
#    المنبعُ يكتب `./dist/browser/…` دائمًا. فالانتقاءُ بالحقل لا بوجود المجلّد.
log "تجريدُ حزم المتصفّح من الشجرة المكتبيّة"
_pruned=0
for _pj in "$APP_DIR"/extensions/*/package.json; do
  [[ -f "$_pj" ]] || continue
  grep -q '"browser"[[:space:]]*:[[:space:]]*"\./dist/web/extension\.js"' "$_pj" || continue
  _ext="$(dirname "$_pj")"
  [[ -d "$_ext/dist/web" ]] || continue
  rm -rf "$_ext/dist/web" || { echo "❌ تعذّر تجريدُ $_ext/dist/web" >&2; exit 1; }
  # يزول إن لم يبقَ فيه شيء، ويبقى إن بقي — ولا يُجبَر.
  # ⚠️ **`|| true` لازمة.** التعليقُ يعلن التسامحَ وbash لا يمنحه: أمرٌ بسيطٌ يفشل
  #    تحت `set -euo pipefail` يُنهي السكربتَ، و`2>/dev/null` تبتلع السبب. فيوم
  #    يظهر ناتجٌ آخرُ تحت `dist/` لأحد امتدادَينا يسقط البناءُ صامتًا عند آخرِ
  #    سطرٍ مطبوع. قِيس: `rmdir` على مجلَّدٍ غيرِ فارغٍ ⇒ exit=1 بلا طباعة.
  rmdir "$_ext/dist" 2>/dev/null || true
  _pruned=$(( _pruned + 1 ))
done

# **والتجريدُ يُقاس بعده لا يُفترَض** — من طرفيه معًا:
# ‏`rm -rf` ينجح على مسارٍ غيرِ موجودٍ كذلك، فالنجاحُ لا يقول إنّ شيئًا زال؛ ولا يقول
# إنّ ما بقي سليم. والشاهدُ الثاني هو عينُ العطب الذي وقع: امتدادُ منبعٍ مدخلُه في
# `dist/`. فإن سقط فالحلقةُ وسّعت هدفَها.
if compgen -G "$APP_DIR/extensions/*/dist/web/extension.js" >/dev/null; then
  echo "❌ بقيت حزمةُ متصفّحٍ في الشجرة المكتبيّة بعد التجريد." >&2; exit 1
fi
# ‏**ونفيُ البقاء ليس إثباتَ التجريد.** «لم يبقَ» صادقٌ كذلك لو «لم يوجد»: تغيُّرُ
# مخرَج `patch_bundle_extensions.py` (إلى `dist/browser/` مثلًا) أو حقلِ `browser`
# يجعل `_pruned=0` والكتلةَ بلا أثر — فتمرّ خضراءَ وتعود المئتا كيلوبايتٍ صامتةً.
# والعددُ معلومٌ سلفًا: امتدادانا وحدَهما يكتبان `./dist/web/extension.js`.
[[ "$_pruned" -ge 1 ]] || {
  echo "❌ لم تُجرَّد حزمةُ متصفّحٍ واحدة — والمنتظَر امتدادان على الأقلّ." >&2
  echo "   الأرجح: تغيّر مخرَجُ patch_bundle_extensions.py أو حقلُ browser، فصار" >&2
  echo "   الانتقاءُ لا يطابق شيئًا. التجريدُ الصامتُ يعيد الوزنَ الميّتَ بلا كلمة." >&2
  exit 1; }
for _canary in typescript-language-features/dist/extension.js git/dist/main.js \
               markdown-language-features/dist/extension.js; do
  [[ -s "$APP_DIR/extensions/$_canary" ]] || {
    echo "❌ التجريدُ أصاب امتدادَ منبع: $_canary مفقود. «dist/» فيها مدخلُه." >&2
    exit 1; }
done
log "جُرِّدت $_pruned حزمةَ متصفّحٍ من المكتبيّ (وامتداداتُ المنبع سليمة)"

log "تحديثُ بصمات النزاهة في product.json المشحون"
"$PY_BIN" "$ROOT/build/refresh_checksums.py" "$APP_DIR" || {
  echo "❌ فشل تحديثُ بصمات النزاهة — راجع أعلاه." >&2; exit 1; }

# ── (ط) تحقّق المخرَج (اسم المشغِّل = nameShort = Mihrab؛ CLI = applicationName = mihrab) ──
LAUNCHER="$OUTDIR/$LAUNCH_REL"
if [[ ! -f "$LAUNCHER" ]]; then
  echo "❌ لم يُنتَج مشغِّلُ محراب ($LAUNCH_REL) في $OUTDIR — راجع السجلّ أعلاه." >&2
  exit 1
fi
echo "✅ البناء نجح: $LAUNCHER"

# ── (ي) تحقّقٌ بعد البناء: أنّ ما بُني **محرابٌ** لا VSCodium بأيقونةٍ أخرى ──
# البناءُ الناجح ليس دليلَ صحّة: الهويّةُ قد تنجو في `$UP/product.json` وتسقط في
# المشحون (وقد سقطت فعلًا — انظر ط-0ز)، والتعريبُ قد يُخبَز في ملفٍّ لا يُقرأ.
# فحصٌ رخيصٌ على المخرَج هنا يمسك ذلك قبل أن يصل إلى مستخدم.
assert_identity "$APP_DIR" "المكتبيّ" || exit 1
if [[ -f "$APP_DIR/out/nls.messages.json" ]]; then
  # بايتا 0xD8/0xD9 بادئتا العربيّة في UTF-8. لا `grep -P` ولا محرفٌ عربيٌّ حرفيّ:
  # الأوّلُ غائبٌ عن grep في macOS، والثاني رهنُ محارف السكربت ولغةِ البيئة معًا.
  # ‏`-e` مرّتين لا `\|`: الأخير امتدادُ GNU يقرؤه grep البِسْديّ (macOS) حرفيًّا،
  # فيفشل على بناءٍ سليمٍ ويتّهمه — وهو الفخُّ نفسُه الذي تفاداه التعليقُ أعلاه في PCRE.
  LC_ALL=C grep -q -e $'\xd8' -e $'\xd9' "$APP_DIR/out/nls.messages.json" \
    || { echo "❌ nls.messages.json بلا عربيّةٍ إطلاقًا — الخبزُ لم يصل إلى المخرَج." >&2; exit 1; }
  log "التعريبُ مخبوزٌ في nls.messages.json"
fi

# ── (ي-2) بوّابةُ بيانات الامتدادات: تعريبٌ في **الملفّ الذي يُقرأ**، وبلا اسم المنبع ──
# بوّابةٌ واحدةٌ لا `grep` هنا: النسبةُ ولائحةُ التسرّب تُحسَبان في
# `patch_extension_nls.py --verify` قراءةً من المشحون. ولماذا لا grep:
#   • `grep -q $'\xd8\|\xd9'` يشهد لبايتٍ عربيٍّ **واحد** — وتطبيعُ الهويّة وحدَه
#     («within VS Code» ⇐ «within محراب») يُرضيه ولو كانت الواجهةُ إنجليزيّةً كلَّها.
#   • و`\|` امتدادُ GNU: grep البِسْديّ (macOS) يقرؤه حرفيًّا فيفشل على بناءٍ سليم.
#   • ونسبةٌ مجمَّعةٌ تُخفي سقوطَ امتدادٍ كاملٍ ⇒ للبوّابة حدٌّ لكلّ امتدادٍ ذي وزن.
if [[ -d "$APP_DIR/extensions" ]]; then
  "$PY_BIN" "$ROOT/build/patch_extension_nls.py" --verify "$APP_DIR" || {
    echo "❌ بوّابةُ تعريب بيانات الامتدادات رفضت المخرَج — راجع أعلاه." >&2; exit 1; }
fi
# والنصُّ المخبوز (سلاسلُ القشرة): تسرّبُ اسمِ التوزيعة الأمّ فيه عطبٌ كذلك.
# الفحصُ بايتيٌّ مباشرٌ لأنّ الملفَّ مصفوفةُ سلاسل بلا بنية — و«VSCodium» ASCII بحت.
# ويشمل الفحصُ **الشجرتين والملفَّين**: نسخةُ المتصفّح (`nls.messages.js`) كانت تحمل
# رابطَ sourceMappingURL إلى إصدارات VSCodium — اسمُ منبعٍ يُخدَم للزائر، وجلبٌ من
# طرفٍ ثالثٍ عند فتح أدوات المطوّر. وكان خارجَ كلّ بوّابة.
for _nls in "$APP_DIR/out/nls.messages.json" "$APP_DIR/out/nls.messages.js" \
            ${WEB_DIR:+"$WEB_DIR/out/nls.messages.json"} ${WEB_DIR:+"$WEB_DIR/out/nls.messages.js"} \
            ${STATIC_DIR:+"$STATIC_DIR/out/nls.messages.json"} ${STATIC_DIR:+"$STATIC_DIR/out/nls.messages.js"}; do
  [[ -f "$_nls" ]] || continue
  if LC_ALL=C grep -qi "vscodium" "$_nls"; then
    echo "❌ تسرّبُ هويّة: اسمُ التوزيعة الأمّ في $_nls — لا يُشحَن." >&2
    exit 1
  fi
done
log "الهويّةُ نظيفةٌ في النصّ المُصيَّر (المخبوز + بيانات الامتدادات)"

# ── (ي-3) لا وجهةَ مستودعٍ منبعيٍّ في الحزمة المصغَّرة [BR-05] ──
# صنفٌ لم تحرسه بوّابةٌ قبله: عنوانٌ **يُضرَب في الشيفرة** وقتَ الترقيع، لا مفتاحٌ
# في `product.json` ولا سلسلةٌ في النصّ المخبوز — وكلُّ ما سبق يفحص هذين.
# ثلاثةُ مواضعَ قِيست حيّةً على mihrab.dev عبر CDP بعد النشر:
#   • لوحُ الترحيب يجلب `announcements-extra.json` من مستودع المنبع في كلّ فتحةٍ
#     أولى — يُخبِره بكلّ زائرٍ جديد، ويعرض إعلاناتِه في لوحِنا لو نُشرت.
#   • ومُبلِّغُ الأعطاب يبحث في **قضايا المنبع** بنصّ عطبِ مستخدمِنا.
#   • ورابطان إلى ويكي المنبع في واجهة التبليغ.
# ومنشؤها واحد: `!!GH_REPO_PATH!!` في رُقَع VSCodium، وافتراضُه `VSCodium/vscodium`.
# فـ`export GH_REPO_PATH` أعلاه يعالجها جميعًا — وهذه البوّابةُ تقيس **الأثر** لا النيّة.
for _bundle in "$APP_DIR/out/vs/workbench/workbench.desktop.main.js" \
               ${WEB_DIR:+"$WEB_DIR/out/vs/workbench/workbench.web.main.internal.js"} \
               ${STATIC_DIR:+"$STATIC_DIR/out/vs/workbench/workbench.web.main.internal.js"}; do
  [[ -f "$_bundle" ]] || continue
  if LC_ALL=C grep -q "VSCodium/vscodium" "$_bundle"; then
    echo "❌ [BR-05] وجهةُ مستودعِ المنبع مضروبةٌ في $_bundle" >&2
    echo "   الأثر: لوحُ الترحيب يجلب من مستودعه · ومُبلِّغُ الأعطاب يبحث في قضاياه." >&2
    echo "   السبب: GH_REPO_PATH لم يصل خطوةَ الترقيع — لا يكفي ضبطُه بعد البناء." >&2
    exit 1
  fi
done

# ── وثنائيّاتُ الشجرة كذلك: البوّابةُ كانت تقرأ جافاسكربت وحدَها ────────────
# فأعلنت «نظيفةٌ» على شجرةٍ فيها تسرّبٌ رابع: `mihrab-tunnel.exe` يحمل قالبَ
# تنزيلِ الخادم مضروبًا في شيفرة Rust —
#     https://github.com/VSCodium/vscodium/releases/download/…-reh-web-….tar.gz
# فمن شغّل `mihrab tunnel` ينزّل **خادمَ VSCodium** من مستودع المنبع. وهو ليس
# اسمًا في نصٍّ بل سلوكٌ يعمل: طلبُ شبكةٍ إلى المنبع، وحمولةٌ ليست حمولتَنا.
#
# ‏`serverDownloadUrlTemplate: null` عندنا لا يُلغيه — يجعل الـCLI يرتدّ إلى هذا
# الثابتِ المخبوزِ بالضبط.
#
# وكان هنا تسامحٌ مُعلَنٌ باسمه (`_BR05_KNOWN="bin/mihrab-tunnel"`) بحجّة «لا ننشر
# خوادمَ REH فالبديلُ ألّا نَعِد بما لا نشحن». **والحجّةُ قامت على فرضٍ خاطئ**:
# كتلةُ (ط-0د) [WEB-01] أعلاه تقول إنّ `vscode-reh-web-*` يُنتَج في **كلّ** بناء
# (‏424 م.ب هناك · 428 مقيسةً على القرص اليوم)، وفيه
# هويّةُ محرابٍ كاملةٌ و130 قاعدةَ `[dir=rtl]`، وعُرِّب عمدًا في [WEB-01]. الذي تقاعد
# **استضافتُنا** له لا إنتاجُه — وقرارُ «لا خادم» كان عن أن نستضيفَ نحن، بينما
# `tunnel`/`serve-web` يشغّلهما المستخدمُ على جهازه: ملفّاتُه وطرفيّتُه وباختياره.
# فالعلاجُ إعادةُ التوجيه (`patch_cli_endpoints.py` في و-4)، ولا تسامحَ بعده.
_br05_bin_hits=0
while IFS= read -r _bin; do
  # ‏`-e` مرّتين لا `\|`: الأخير امتدادُ GNU يقرؤه grep البِسْديّ (macOS) حرفيًّا،
  # فلا يطابق شيئًا — أي **بوّابةٌ تُعطَّل عند غياب لهجتها** وتُعلن النظافةَ كذبًا.
  LC_ALL=C grep -qa -e "VSCodium/vscodium" -e "VSCodium/versions" "$_bin" || continue
  echo "❌ [BR-05] وجهةُ مستودعِ المنبع في ثنائيٍّ مشحون: ${_bin#$OUTDIR/}" >&2
  _br05_bin_hits=$((_br05_bin_hits + 1))
done < <(find "$OUTDIR" -type f \( -name '*.exe' -o -name '*.dll' -o -name '*.node' \
                                  -o -name '*.so' -o -name '*.dylib' \) 2>/dev/null)
[[ "$_br05_bin_hits" -eq 0 ]] || {
  echo "   الثنائيّاتُ لا يبلغها GH_REPO_PATH: قيمُها مضروبةٌ في مصدرِ Rust/C++." >&2
  echo "   وترقيعُها يقع **قبل** cargo build — بعده تصير بايتاتٍ (و-4)." >&2
  exit 1; }

# ── ونفيُ الخطأ ليس إثباتَ الصواب ──
# غيابُ `VSCodium/vscodium` من الثنائيّ يتحقّق كذلك لو **لم يُبنَ الـCLI أصلًا**، أو
# بُني بوجهةٍ فارغةٍ فصار `Some("")` — وكلاهما يمرّ من البوّابة أعلاه صامتًا ويترك
# `tunnel` يطلب عنوانًا فارغًا. فيُسأل الثنائيُّ عن **وجهتنا** لا عن غياب وجهتهم.
# ⚠️⚠️ **المسارُ وسيطٌ لا نصٌّ داخل التعبير.** كانت الصيغةُ
#     node -p "require('$UP/product.json').tunnelApplicationName"
# و`$UP` مسارٌ MSYS (`/c/s_lang/…`). ووسائطُ البرامج الأصليّة تُحوَّل تلقائيًّا إلى
# صيغة ويندوز، **أمّا النصُّ المُضمَّن داخل تعبير JS فلا** — فيرى node.exe مسارًا لا
# يعرفه ويسقط بـMODULE_NOT_FOUND.
# وثلاثةُ أشياءَ اجتمعت فصار العطبُ صامتًا تمامًا: `set -euo pipefail` يُنهي السكربتَ
# عند فشل إسنادٍ من بديلِ أمر، و`2>/dev/null` تبتلع رسالةَ node، والكتلةُ لا تطبع
# شيئًا قبلها. فانتهى السجلُّ عند الخطوة السابقة **بلا كلمةٍ واحدة**، مرّتين،
# وشجرةُ البناء سليمةٌ في الحالتين. ومِجَسٌّ لا يقول لماذا سقط أسوأُ من غيابه.
_TUNNEL_NAME="$(node -p "require(process.argv[1]).tunnelApplicationName" "$UP/product.json")" \
  || { echo "❌ [BR-05] تعذّرت قراءةُ tunnelApplicationName من $UP/product.json" >&2; exit 1; }
[[ -n "$_TUNNEL_NAME" ]] \
  || { echo "❌ [BR-05] tunnelApplicationName فارغٌ في product.json" >&2; exit 1; }
[[ "$_TUNNEL_NAME" == "undefined" ]] \
  && { echo "❌ [BR-05] tunnelApplicationName غيرُ معرَّفٍ في product.json" >&2; exit 1; }
_TUNNEL="$OUTDIR/bin/$_TUNNEL_NAME"
[[ -f "$_TUNNEL" ]] || _TUNNEL="$_TUNNEL.exe"
# ⚠️ **غيابُ الثنائيّ ليس نجاحًا.** كان الفحصُ كلُّه داخل `if [[ -f … ]]`، والتعليقُ
#    فوقه يَعِد بتغطية «لو لم يُبنَ الـCLI أصلًا» — وهو بالضبط ما كان يمرّ صامتًا.
#    و`node -p` على مفتاحٍ غائبٍ يُخرِج النصَّ `undefined` (غيرَ فارغٍ فيمرّ من `-n`)
#    فيصير المسارُ `bin/undefined` والتخطّي هو هو. حراسةٌ تقيس نيّةً لا أثرًا.
[[ -f "$_TUNNEL" ]] || {
  echo "❌ [BR-05] ثنائيُّ النفق مفقودٌ من المخرَج: bin/$_TUNNEL_NAME" >&2
  echo "   وغيابُه يُخفي الفحصَ لا يُرضيه — إمّا يُبنى الـCLI أو يُسقَط من product.json." >&2
  exit 1; }
if true; then
  # ‏**العقدُ ذو حالتَين، وكلتاهما تُقاس في البايتات لا في نيّة السكربت.**
  # كانت البوّابةُ تطلب وجهتَنا، ثمّ قِيس أنّ الاسمَ الذي وجّهتْ إليه **غيرُ مسجَّلٍ
  # على GitHub** — فصار الثنائيُّ يشير إلى ما يملكه أوّلُ من يسجّله. فأُغلِقت
  # الوجهةُ كلُّها. واليومَ تُفتَح **بقياس**: (و-4ب) لا يصدّر شيئًا ما لم يجلب
  # المانيفستَ ويقبض 200 على الأثر. وهنا يُقاس أثرُ ذلك القرار في المخرَج:
  #
  #   • خُبِزت وجهة  ⇒ **يجب** أن تكون في الثنائيّ حرفيًّا. تصديرٌ لا يصل
  #     `option_env!` يترك الـCLI أعمى ويترك السجلَّ يقول إنّه بُكِّر — أي حارسٌ
  #     يشهد لنيّةٍ لا لأثر، وهو الصنفُ الذي وقعنا فيه مرّتَين.
  #   • لم تُخبَز    ⇒ لا `releases/download` ولا مضيفُنا. عنوانٌ يتسرّب من طريقٍ
  #     آخر (رقعةٌ منبعيّةٌ · قيمةٌ في البيئة) يمرّ صامتًا لولا هذا.
  if [[ -n "${_CLI_ENDPOINT:-}" ]]; then
    LC_ALL=C grep -qa "$_CLI_ENDPOINT" "$_TUNNEL" || {
      echo "❌ [BR-05] وجهةٌ صُدِّرت ولم تُخبَز: $_CLI_ENDPOINT" >&2
      echo "   خرجت (و-4ب) بأنّ العنوانَ يخدم فصدّرت المتغيّرَين، ولم يبلغا" >&2
      echo "   \`option_env!\`. الأرجح: build_cli.sh لم يُرقَّع (راجع و-4)، أو" >&2
      echo "   \`dev/build.sh\` دهس البيئةَ قبل أن تصله. والـCLI أعمى والسجلُّ" >&2
      echo "   يقول إنّه مُبكَّر — وهذا أسوأُ من غيابٍ صريح." >&2
      exit 1; }
    log "وجهةُ النفق مخبوزةٌ ومقيسةٌ في الثنائيّ: $_CLI_ENDPOINT [BR-05]"
  else
    LC_ALL=C grep -qa "releases/download" "$_TUNNEL" && {
      echo "❌ [BR-05] وجهةُ تنزيلٍ مخبوزةٌ في ثنائيّ النفق: ${_TUNNEL#$OUTDIR/}" >&2
      echo "   ولم تُصدَّر وجهةٌ في (و-4ب) — فمصدرُها ليس نحن: رقعةٌ منبعيّةٌ أو" >&2
      echo "   قيمةٌ في البيئة. وعنوانٌ لا نملكه يُنزَّل منه ويُشغَّل خادمًا على" >&2
      echo "   جهاز المستخدم." >&2
      exit 1; }
  fi
  # واسمُ الأثر جزءٌ من العنوان لا زينةٌ حوله: بقيت `vscodium` مفردةً بعد أن صار
  # المضيفُ لنا (قِيست في أوّل بناءٍ مُرقَّع)، فكان الطلبُ على `vscodium-reh-web-…`
  # من مستودعنا — عنوانٌ صحيحُ المضيف خاطئُ الأثر، يبدو مُصلَحًا ويردّ 404.
  # والاسمُ الوحيدُ الذي كان يحملها هو هذا، فالعتبةُ صفر.
  # ‏**`|| true` لازمةٌ لا زينة.** `grep` بلا تطابقٍ يخرج بـ1، والملفُّ تحت
  # `set -euo pipefail` — فإسنادُ نتيجةِ أنبوبٍ فاشلٍ **يُنهي البناءَ صامتًا**.
  # أي أنّ البوّابةَ كانت تقتل البناءَ **لحظةَ نجاحها**: صفرُ تسرّبٍ = صفرُ
  # تطابق = خروجٌ بـ1. وقع فعلًا: انتهى السجلُّ عند الخطوة السابقة بلا كلمة.
  _v="$(LC_ALL=C grep -ca "vscodium" "$_TUNNEL" || true)"
  # ‏**ونفيُ التطابق يُميَّز عن عجزِ الأداة.** `grep` يخرج بـ1 لعدم التطابق وبـ2
  # لخطأٍ (ملفٌّ لا يُقرأ · I/O)، وفي الثانية يكون المخرَجُ فارغًا. و`[[ "" -eq 0 ]]`
  # **صحيحٌ** في bash (قِيس) — أي أنّ البوّابةَ كانت تُعلن النظافةَ حين يعجز مِجَسُّها،
  # وهو عينُ الصنف الذي كُتِبت `-e` مرّتين أعلاه لأجله.
  [[ "$_v" =~ ^[0-9]+$ ]] || {
    echo "❌ [BR-05] تعذّر عدُّ السلاسل في ${_TUNNEL#$OUTDIR/} — مِجَسٌّ عاجزٌ لا شهادةَ له." >&2
    exit 1; }
  [[ "$_v" -eq 0 ]] || {
    echo "❌ [BR-05] اسمُ المنبع ما زال في ثنائيّ النفق ($_v مرّة) — اسمُ الأثر" >&2
    echo "   يُشتقّ من APP_NAME لا من product.applicationName. راجع (و-4)." >&2
    exit 1; }
  log "ثنائيُّ النفق بلا وجهةِ تنزيلٍ ولا اسمِ منبع [BR-05]"
fi

log "لا وجهةَ مستودعٍ منبعيٍّ في الحزم المصغَّرة ولا في الثنائيّات [BR-05]"

# ‏--version لا يعمل بلا شاشة على لينكس (Electron يحتاج X/Wayland)، ولا يُشغَّل من
# داخل حزمة .app بهذه الصورة على macOS. فيُترك لويندوز، والتحقّقُ أعلاه يغني عنه.
if [[ "$IS_WIN" == "yes" ]]; then
  "$OUTDIR/bin/mihrab.cmd" --version 2>/dev/null | head -3 || true
fi
