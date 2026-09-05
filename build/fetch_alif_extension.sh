#!/usr/bin/env bash
# جلبُ إضافة «لغة ألف» لبناءِ المعاينة — لا للبناءِ العاديّ.
#
# لماذا جلبٌ لا إيداع؟ الإضافةُ منتَجُ مستودعٍ آخر (SalehKadah/alif-vscode) وله
# إصداراتُه. إيداعُ vsix هنا يخلق نسخةً ثانيةً تنجرف صامتةً عن الأصل، ويجعل
# مستودعَ محرابٍ مخزنَ ثنائيّاتٍ لغيره. الجلبُ يُبقي مصدرَ الحقيقةِ واحدًا.
#
# ولماذا بصمةٌ مثبَّتة؟ لأنّ هذا الملفَّ يُنفَّذ في جهازِ المستخدمِ آخرَ المطاف.
# رابطُ إصدارٍ على GitHub قابلٌ للاستبدالِ بأصلٍ آخرَ بالاسمِ نفسِه بلا أثر،
# فبلا بصمةٍ نبني ما لا نعرفه. البصمةُ تُثبَّت هنا وتُقاس قبل الفكّ لا بعده.
set -euo pipefail

ALIF_VERSION="${ALIF_EXT_VERSION:-0.1.2}"
ALIF_SHA256="${ALIF_EXT_SHA256:-917510b0931b9362097c238f34da7b942c56c626ac9bc994e625aa80f8afa38f}"
ALIF_URL="https://github.com/SalehKadah/alif-vscode/releases/download/v${ALIF_VERSION}/alif-lang-${ALIF_VERSION}.vsix"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# الحسابُ في دالّةٍ مشتركةٍ لأنّه يُختبَر (tests/static/check_extra_ext_dirs.sh).
. "$ROOT/build/lib/sha256.sh"
# مفسّرُ بايثون يُحلّ ولا يُفترَض: `python` المجرَّد غائبٌ عن أوبونتو 24.04.
. "$ROOT/build/lib/pybin.sh"
resolve_py_bin || exit 1
DEST="$ROOT/.preview-extensions/alif-lang"
TMP="$ROOT/.preview-extensions/.alif.vsix"

mkdir -p "$(dirname "$TMP")"
echo "▶ جلبُ إضافة لغة ألف $ALIF_VERSION …"
curl -fsSL -o "$TMP" "$ALIF_URL"

got=$(sha256_of "$TMP")
if [[ "$got" != "$ALIF_SHA256" ]]; then
  echo "❌ بصمةُ الإضافةِ لا تطابق المثبَّتة." >&2
  echo "   المتوقَّع: $ALIF_SHA256" >&2
  echo "   المقيس:   $got" >&2
  rm -f "$TMP"
  exit 1
fi
echo "   ✅ البصمة مطابقة: $got"

rm -rf "$DEST"; mkdir -p "$DEST"
# vsix أرشيفُ zip، ومحتوى الإضافةِ كلُّه تحت extension/ — تُنقل إلى الجذر لأنّ
# ماسحَ الإضافاتِ المدمجةِ يتوقّع package.json في أعلى المجلّد.
# <<VSIX_EXTRACT — سياجٌ يقرأ منه tests/static/check_extra_ext_dirs.sh هذا الفكَّ نفسَه.
"$PY_BIN" - "$TMP" "$DEST" <<'PY'
import sys, zipfile, os
src, dest = sys.argv[1], os.path.realpath(sys.argv[2])
with zipfile.ZipFile(src) as z:
    for name in z.namelist():
        if not name.startswith("extension/") or name.endswith("/"):
            continue
        rel = name[len("extension/"):]
        # zip slip: اسمُ مدخلٍ فيه «‏../» أو مسارٌ مطلقٌ يكتب **خارج** الوجهة —
        # و«‏../..» من ‎.preview-extensions/alif-lang هو جذرُ المستودع، أي كتابةٌ فوق
        # build/build.sh قبل تشغيله بلحظة. والبصمةُ المثبَّتة ليست حارسًا عن هذا:
        # تُبدَّل مع كلّ ترقيةٍ للإضافة، وتُتجاوَز بـALIF_EXT_SHA256.
        out = os.path.realpath(os.path.join(dest, rel))
        if out != dest and not out.startswith(dest + os.sep):
            sys.exit("❌ مدخلٌ يخرج من وجهةِ الفكّ (zip slip): %s" % name)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as fh:
            fh.write(z.read(name))
PY
# VSIX_EXTRACT>>

[[ -f "$DEST/package.json" ]] || { echo "❌ لا package.json في المفكوك: $DEST" >&2; exit 1; }
rm -f "$TMP"

# ═══════════════════ مفسّرُ ألف — يُشحن في bin/ داخل الإضافة ═══════════════════
# لماذا داخل الإضافة لا بجوار التطبيق؟ لأنّ العثورَ عليه شأنُ الإضافة: من 0.1.2
# تبحث في `bin/` نسبةً إلى جذرها. ووضعُه بجوار Mihrab.exe كان يفرض رقعةً في
# محرابٍ تُقحِم مسارًا في PATH لأجل لغةٍ بعينها — ومحرابٌ منصّةٌ لا بائعُ لغة.
#
# والحزمُ ثلاثٌ ببصماتٍ ثلاث: الجالبُ يعمل على آلةِ البناء نفسِها في كلّ منصّة،
# فيأخذ حزمةَ منصّته. وثبَّتنا الثلاثَ لا واحدةً كي تُقاس كلُّ منصّةٍ ببصمتها،
# ولا يُشحن ثنائيُّ نظامٍ آخرَ بحجّة أنّ بصمةً واحدةً طابقت.
RT_VERSION="${ALIF_RUNTIME_VERSION:-v5.2.0-ar.2}"
case "${ALIF_RUNTIME_TARGET:-$(uname -s)}" in
  MINGW*|MSYS*|CYGWIN*|Windows*|windows) RT_ASSET="alif-windows-x64.zip"
    RT_SHA="${ALIF_RUNTIME_SHA256:-0dd3a9257d56f317de94209c26b6e97b7a115a4d1c7f2c7b522f5e2dffbf5b70}" ;;
  Linux|linux) RT_ASSET="alif-linux-x64.tar.gz"
    RT_SHA="${ALIF_RUNTIME_SHA256:-40ceb5e5ab49abe346b8d685197444fd8166a1fc598010435e8bf9faae058ab2}" ;;
  Darwin|darwin|macos) RT_ASSET="alif-macos-universal.tar.gz"
    RT_SHA="${ALIF_RUNTIME_SHA256:-afc25cfa30755cfe2f1254bd2ba04f6c1e66b6af7b8053816ccd6908a425aeae}" ;;
  *) echo "❌ منصّةٌ لا حزمةَ مفسّرٍ لها: ${ALIF_RUNTIME_TARGET:-$(uname -s)}" >&2; exit 1 ;;
esac
RT_URL="https://github.com/SalehKadah/Alif/releases/download/${RT_VERSION}/${RT_ASSET}"
RT_TMP="$ROOT/.preview-extensions/.alif-runtime"

echo "▶ جلبُ مفسّر ألف $RT_VERSION ($RT_ASSET) …"
curl -fsSL -o "$RT_TMP" "$RT_URL"
got=$(sha256_of "$RT_TMP")
if [[ "$got" != "$RT_SHA" ]]; then
  echo "❌ بصمةُ المفسّرِ لا تطابق المثبَّتة." >&2
  echo "   المتوقَّع: $RT_SHA" >&2
  echo "   المقيس:   $got" >&2
  rm -f "$RT_TMP"
  exit 1
fi
echo "   ✅ البصمة مطابقة: $got"

rm -rf "$DEST/bin"; mkdir -p "$DEST/bin"
# <<RUNTIME_EXTRACT — سياجٌ يقرأ منه tests/static/check_extra_ext_dirs.sh هذا الفكَّ نفسَه.
"$PY_BIN" - "$RT_TMP" "$DEST/bin" <<'RUNTIME_PY'
import os, sys, tarfile, zipfile

src, dest = sys.argv[1], os.path.realpath(sys.argv[2])


def target_of(name):
    """مسارُ الوجهة بعد إسقاطِ المجلّد الأعلى الواحد الذي تلفّ به حزمُ ألف محتواها.

    وحارسُ الخروجِ ههنا لا في مكانٍ آخر: «‏../» في اسمِ مدخلٍ يكتب فوق شجرة
    الإضافة، و«‏../../..» منها جذرُ المستودع — أي فوق build/build.sh قبل تشغيله
    بلحظة. والبصمةُ المثبَّتةُ ليست حارسًا عن هذا: تُبدَّل مع كلّ ترقيةٍ للمفسّر،
    وتُتجاوَز بـALIF_RUNTIME_SHA256."""
    parts = [p for p in name.replace("\\", "/").split("/")[1:] if p not in ("", ".")]
    if not parts:
        return None
    out = os.path.realpath(os.path.join(dest, *parts))
    if out != dest and not out.startswith(dest + os.sep):
        sys.exit("❌ مدخلٌ يخرج من وجهةِ الفكّ: %s" % name)
    return out


def put(out, data, mode):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as fh:
        fh.write(data)
    if mode:
        os.chmod(out, mode)


if zipfile.is_zipfile(src):
    with zipfile.ZipFile(src) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            out = target_of(info.filename)
            if out:
                # بتُّ التنفيذ يعيش في البايتات العليا من external_attr، ويضيع إن
                # كُتب الملفُّ بلا استرجاعه — فيصل مفسّرٌ موجودٌ لا يعمل.
                put(out, z.read(info), (info.external_attr >> 16) & 0o777)
else:
    with tarfile.open(src, "r:*") as t:
        for m in t:
            if m.isdir():
                continue
            # الوصلاتُ طريقُ خروجٍ ثانٍ لا يراه فحصُ الاسم: وصلةٌ إلى مجلّدٍ خارجَ
            # الوجهة ثمّ كتابةٌ عبرها. ولا حاجةَ إليها في حزمةِ مفسّر، فتُرفض.
            if not m.isfile():
                sys.exit("❌ مدخلٌ ليس ملفًّا عاديًّا: %s" % m.name)
            out = target_of(m.name)
            if out:
                put(out, t.extractfile(m).read(), m.mode & 0o777)
RUNTIME_PY
# RUNTIME_EXTRACT>>

RT_BIN=alif; [[ "$RT_ASSET" == *windows* ]] && RT_BIN=alif.exe
[[ -f "$DEST/bin/$RT_BIN" ]] || { echo "❌ لا $RT_BIN في المفسّر المفكوك: $DEST/bin" >&2; exit 1; }
[[ -x "$DEST/bin/$RT_BIN" ]] || { echo "❌ $RT_BIN وصل بلا بتِّ تنفيذ" >&2; exit 1; }
rm -f "$RT_TMP"

echo "✅ لغة ألف جاهزة: $DEST"
echo "   والمفسّر:     $DEST/bin/$RT_BIN"
echo "   للبناء بها:  MIHRAB_EXTRA_EXT_DIRS=\"$DEST\" bash build/build.sh"
