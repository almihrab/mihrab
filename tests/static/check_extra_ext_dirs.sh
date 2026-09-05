#!/usr/bin/env bash
# L0 — حارسا ميزةِ بناءِ المعاينة، بلا بناء (ثوانٍ).
#
# سقط بناءُ المعاينةِ الأوّلُ في منصّتين، بعد ساعةٍ من العمل في كلٍّ منهما، لعطبين
# لا يحتاجان بناءً أصلًا: `sha256sum` غائبةٌ عن macOS، وفاصلُ النقطتين يقطع مسارَ
# ويندوز `D:\…` نصفين. كلاهما تفكيكُ نصٍّ وتوفّرُ أداة — يُمسَكان هنا في ثانية.
#
# ويقرأ هذا الحارسُ الكتلَ **من ملفّاتها** بين سياجين، لا نسخةً منها: نسخةُ منطقٍ
# في اختبارٍ تنجرف عن الأصل صامتةً فيمرّ الاختبارُ على شيءٍ لم يعد يُشحن.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fails=0
ok()  { echo "  ✅ $1"; }
no()  { echo "  ❌ $1"; fails=$((fails + 1)); }

echo "─── إضافاتُ بناءِ المعاينة (L0) ───"

# ═══ ١) تفكيكُ MIHRAB_EXTRA_EXT_DIRS ═══
BLOCK=$(sed -n '/# <<EXTRA_EXT_DIRS_BLOCK/,/# EXTRA_EXT_DIRS_BLOCK>>/p' "$ROOT/build/build.sh")
if [[ -z "$BLOCK" ]]; then
  no "لم أجد كتلةَ MIHRAB_EXTRA_EXT_DIRS في build/build.sh (سياجٌ مفقود؟)"
else
  # الكتلةُ تُشغَّل معزولةً: STAGE_EXT مجلّدٌ مؤقّت، وcp/log مُستبدلان كي يبقى
  # المقيسُ هو التفكيكَ والحراسةَ لا النسخ.
  { echo 'set -uo pipefail'
    echo 'STAGE_EXT="$1"'
    echo 'log(){ echo "STAGED:$*"; }'
    echo 'cp(){ :; }'
    echo 'strip_ext_artifacts(){ :; }'
    echo "$BLOCK"; } > "$TMP/block.sh"

  mkdir -p "$TMP/stage" "$TMP/ext one/alif-lang" "$TMP/ext one/ثانية" "$TMP/بلا"
  echo '{}' > "$TMP/ext one/alif-lang/package.json"
  echo '{}' > "$TMP/ext one/ثانية/package.json"

  run() { MIHRAB_EXTRA_EXT_DIRS="$1" bash "$TMP/block.sh" "$TMP/stage" 2>&1; }

  out=$(run "$TMP/ext one/alif-lang"); rc=$?
  if (( rc == 0 )) && [[ "$out" == *"STAGED:"*"alif-lang"* ]]; then
    ok "مسارٌ فيه فراغاتٌ وحروفٌ عربيّةٌ لا ينقسم"
  else
    no "مسارٌ فيه فراغات: rc=$rc · $out"
  fi

  out=$(run "$TMP/ext one/alif-lang
$TMP/ext one/ثانية"); rc=$?
  if (( rc == 0 )) && [[ "$out" == *alif-lang* && "$out" == *ثانية* ]]; then
    ok "سطران ⇒ إضافتان (والسطرُ الأخيرُ بلا newline يُقرأ)"
  else
    no "سطران: rc=$rc · $out"
  fi

  # الحارسُ الأصليّ: مسارُ ويندوز يبدأ بحرفِ سواقةٍ ونقطتين. لا يوجد على لينكس،
  # فالمقيسُ أنّ الرسالةَ تحمل المسارَ **كاملًا** لا الحرفَ «D» وحدَه.
  out=$(run 'D:\a\mihrab-ide\mihrab-ide/.preview-extensions/alif-lang'); rc=$?
  if (( rc != 0 )) && [[ "$out" == *".preview-extensions/alif-lang"* ]]; then
    ok "مسارُ ويندوز لا يُقطَع عند نقطتَي السواقة"
  else
    no "مسارُ ويندوز انقطع أو مرّ: rc=$rc · $out"
  fi

  out=$(run ""); rc=$?
  if (( rc == 0 )) && [[ "$out" != *STAGED:* ]]; then
    ok "قيمةٌ فارغة ⇒ لا شيءَ يُجهَّز (البناءُ العاديّ)"
  else
    no "قيمةٌ فارغة: rc=$rc · $out"
  fi

  out=$(run "$TMP/بلا"); rc=$?
  if (( rc != 0 )) && [[ "$out" == *"package.json"* ]]; then
    ok "مجلّدٌ بلا package.json ⇒ فشلٌ صريحٌ لا تخطٍّ صامت"
  else
    no "مجلّدٌ بلا package.json مرّ صامتًا: rc=$rc · $out"
  fi

  mkdir -p "$TMP/stage/alif-lang"
  out=$(run "$TMP/ext one/alif-lang"); rc=$?
  if (( rc != 0 )) && [[ "$out" == *"يصادم"* ]]; then
    ok "تصادمٌ مع إضافةٍ مدمجة ⇒ فشلٌ صريح"
  else
    no "التصادمُ لم يُمسَك: rc=$rc · $out"
  fi
  rmdir "$TMP/stage/alif-lang"
fi

# ═══ ٢) سلسلةُ البصمة ═══
# shellcheck source=/dev/null
. "$ROOT/build/lib/sha256.sh"

# مفسّرُ بايثون: كانت الأولويّةُ هنا معكوسة (`python` قبل `python3`) — وهو بايثون 2
# على توزيعاتٍ أقدم. الدالّةُ المشتركة تختبر النسخةَ لا الوجودَ وحدَه.
. "$ROOT/build/lib/pybin.sh"
printf 'mihrab' > "$TMP/probe"
WANT="b058209cf203796183d7ec228d0dc4f7b5a08c56338c6b506ce56c1594c83dba"  # sha256("mihrab")
got=$(sha256_of "$TMP/probe" 2>&1) && [[ "$got" == "$WANT" ]] \
  && ok "بصمةُ ملفٍّ معلومٍ صحيحةٌ على أداةِ هذه المنصّة" \
  || no "بصمةٌ خاطئة: $got ≠ $WANT"

# غيابُ الأدوات الثلاث: خطأٌ صريحٌ غيرُ صفريّ، لا بصمةٌ فارغةٌ تُقارَن بنجاحٍ زائف.
out=$(PATH="$TMP/empty" sha256_of "$TMP/probe" 2>&1); rc=$?
if (( rc != 0 )) && [[ -z "${out//[[:space:]]/}" || "$out" == *"أداةَ بصمة"* ]]; then
  ok "غيابُ أدواتِ البصمة ⇒ فشلٌ لا صمت"
else
  no "غيابُ أدواتِ البصمة: rc=$rc · $out"
fi

# ═══ ٣) فكُّ vsix لا يكتب خارجَ وجهته (zip slip) ═══
EXTRACT=$(sed -n '/# <<VSIX_EXTRACT/,/# VSIX_EXTRACT>>/p' "$ROOT/build/fetch_alif_extension.sh")
if [[ -z "$EXTRACT" ]]; then
  no "لم أجد كتلةَ فكّ vsix (سياجٌ مفقود؟)"
elif ! resolve_py_bin 2>/dev/null; then
  echo "  ⏭️  لا بايثون — تخطّي حارس zip slip"
else
  PY="$PY_BIN"
  "$PY" - "$TMP/evil.vsix" <<'MAKE'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1], "w") as z:
    z.writestr("extension/package.json", "{}")
    z.writestr("extension/../../pwned.txt", "x")
MAKE
  mkdir -p "$TMP/out/dest"
  { echo 'TMP="$1"; DEST="$2"'; echo "$EXTRACT"; } > "$TMP/extract.sh"
  out=$(cd "$TMP/out" && bash "$TMP/extract.sh" "$TMP/evil.vsix" "$TMP/out/dest" 2>&1); rc=$?
  if (( rc != 0 )) && [[ ! -e "$TMP/out/pwned.txt" && ! -e "$TMP/pwned.txt" ]]; then
    ok "مدخلٌ يخرج من الوجهة (zip slip) يُرفَض"
  else
    no "zip slip نجح — كُتب ملفٌّ خارجَ الوجهة: rc=$rc · $out"
  fi
fi


# ═══ ٤) فكُّ حزمةِ المفسّر: لا خروجَ من الوجهة، ولا وصلات، وبتُّ التنفيذ يصل ═══
RT=$(sed -n '/# <<RUNTIME_EXTRACT/,/# RUNTIME_EXTRACT>>/p' "$ROOT/build/fetch_alif_extension.sh")
if [[ -z "$RT" ]]; then
  no "لم أجد كتلةَ فكّ المفسّر (سياجٌ مفقود؟)"
elif ! resolve_py_bin 2>/dev/null; then
  echo "  ⏭️  لا بايثون — تخطّي حراس فكّ المفسّر"
else
  PY="$PY_BIN"
  { echo 'RT_TMP="$1"; DEST="$2"'; echo "$RT"; } > "$TMP/rt.sh"

  # يبني الحزمَ الخبيثةَ والسليمة. الحزمُ الحقيقيّةُ تلفّ محتواها في مجلّدٍ أعلى
  # واحدٍ يُسقَط عند الفكّ، فكلُّ اسمٍ ههنا يبدأ به كي يُقاس الفكُّ كما يجري فعلًا.
  "$PY" - "$TMP" <<'MAKERT'
import os, sys, tarfile, zipfile, io
d = sys.argv[1]

with zipfile.ZipFile(os.path.join(d, "evil.zip"), "w") as z:
    z.writestr("pkg/../../pwned-zip.txt", "x")

with zipfile.ZipFile(os.path.join(d, "good.zip"), "w") as z:
    info = zipfile.ZipInfo("pkg/alif")
    info.external_attr = 0o755 << 16
    z.writestr(info, "#!/bin/sh\n")

with tarfile.open(os.path.join(d, "evil.tar.gz"), "w:gz") as t:
    data = b"x"
    m = tarfile.TarInfo("pkg/../../pwned-tar.txt"); m.size = len(data)
    t.addfile(m, io.BytesIO(data))

with tarfile.open(os.path.join(d, "link.tar.gz"), "w:gz") as t:
    m = tarfile.TarInfo("pkg/alif"); m.type = tarfile.SYMTYPE; m.linkname = "/etc/passwd"
    t.addfile(m)

with tarfile.open(os.path.join(d, "good.tar.gz"), "w:gz") as t:
    data = b"#!/bin/sh\n"
    m = tarfile.TarInfo("pkg/alif"); m.size = len(data); m.mode = 0o755
    t.addfile(m, io.BytesIO(data))
MAKERT

  rt_rejects () { # اسمُ الحالة، الأرشيف، الملفُّ الذي كان سيُكتب
    rm -rf "$TMP/rt"; mkdir -p "$TMP/rt/bin"
    out=$(cd "$TMP/rt" && bash "$TMP/rt.sh" "$2" "$TMP/rt" 2>&1); rc=$?
    if (( rc != 0 )) && [[ ! -e "$TMP/$3" && ! -e "$TMP/rt/$3" ]]; then
      ok "$1"
    else
      no "$1 — rc=$rc · $out"
    fi
  }

  rt_rejects "zip يخرج من الوجهة يُرفَض"  "$TMP/evil.zip"     "pwned-zip.txt"
  rt_rejects "tar يخرج من الوجهة يُرفَض"  "$TMP/evil.tar.gz"  "pwned-tar.txt"
  rt_rejects "وصلةٌ رمزيّةٌ في tar تُرفَض" "$TMP/link.tar.gz"  "rt/bin/alif"

  # والسليمُ يمرّ: المجلّدُ الأعلى يُسقَط، وبتُّ التنفيذ ينجو.
  for arch in good.zip good.tar.gz; do
    rm -rf "$TMP/rt"; mkdir -p "$TMP/rt/bin"
    out=$(bash "$TMP/rt.sh" "$TMP/$arch" "$TMP/rt" 2>&1); rc=$?
    if (( rc == 0 )) && [[ -f "$TMP/rt/bin/alif" ]]; then
      ok "$arch: المجلّدُ الأعلى يُسقَط والملفُّ يصل"
    else
      no "$arch: rc=$rc · $out"
      continue
    fi
    if [[ "$OSTYPE" == msys* || "$OSTYPE" == cygwin* || "$OSTYPE" == win32 ]]; then
      echo "  ⏭️  ويندوز لا يحمل بتَّ تنفيذٍ — تخطّي فحصَه لـ$arch"
    elif [[ -x "$TMP/rt/bin/alif" ]]; then
      ok "$arch: بتُّ التنفيذ نجا الفكّ"
    else
      no "$arch: بتُّ التنفيذ سقط في الفكّ — مفسّرٌ موجودٌ لا يعمل"
    fi
  done
fi

if (( fails )); then
  echo "❌ $fails فحصًا ساقطًا في حراس بناءِ المعاينة."
  exit 1
fi
echo "✅ حراسُ بناءِ المعاينة سليمة."
