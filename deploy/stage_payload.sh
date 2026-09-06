#!/usr/bin/env bash
# تجهيزُ حمولةِ النشر الثابت — **يُشغَّل من جذر المستودع، على جهاز البناء لا الخادم**.
#
#     deploy/stage_payload.sh [<مستخدم>@<خادم>]
#
# يحزم الشجرةَ الثابتة، ويحسب البصمتين، **ويكتبهما في `static_deploy.sh`**، ثمّ
# يرفع الثلاثةَ إن أُعطي عنوانُ خادم.
#
# ولماذا هذا السكربتُ أصلًا: تحديثُ `SHA_TREE`/`SHA_CONF` باليد كان خطوةً موصوفةً
# بـ«لا تُنسى» — والوثيقةُ الجيّدةُ لا تكتفي بالاعتراف. ونسيانُها يوقف النشرَ
# برسالةٍ («بصمةُ tree.tgz لا تطابق المثبَّتة») تُربك من لا يعرف سببَها. فئةُ خطأٍ
# تُلغى بسطرٍ من `sed` بدل أن تُوصَف في فقرة.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TREE="$ROOT/.upstream/vscode-web"
CONF="$ROOT/deploy/nginx/mihrab.dev.static.conf"
SCRIPT="$ROOT/deploy/static_deploy.sh"
OUT="${TMPDIR:-/tmp}/mihrab-tree.tgz"
PORT=2000
DEST="${1:-}"

die() { echo "❌ $*" >&2; exit 1; }
say() { echo "── $*"; }

[[ -d $TREE ]] || die "لا شجرةَ ثابتة في $TREE — شغّل build/build.sh أوّلًا."
[[ -f $TREE/.mihrab-built-at ]] \
  || die "الشجرةُ بلا طابعِ بناء — بقيّةُ بناءٍ سابق. احذفها وأعِد البناء."
[[ -f $CONF && -f $SCRIPT ]] || die "ملفّاتُ النشر ناقصة."

say "طابعُ البناء: $(cat "$TREE/.mihrab-built-at")"

# بوّابةٌ قبل الحزم: ما لا يُقاس هنا يُقاس على الخادم بعد فوات الأوان.
# ‏`boot-early.js` في القائمة [WEB-09]: خرج من `index.html` كي تستغني سياسةُ الأمان
# عن `'unsafe-inline'`. وغيابُه لا يُنتج صفحةَ خطأ — يُنتج شاشةَ إقلاعٍ لا تنتهي،
# لأنّ `_VSCODE_FILE_ROOT` لا يُضبَط فلا تُحلّ مساراتُ الحزمة أصلًا.
for f in index.html boot.js boot-early.js product.web.js manifest.json favicon.ico \
         out/nls.messages.js out/vs/workbench/workbench.web.main.internal.js \
         out/vs/workbench/kawkab-mono.woff2; do
  [[ -s "$TREE/$f" ]] || die "ملفٌّ لازمٌ مفقودٌ أو فارغ: $f"
done
grep -q 'VSCodium/vscodium' "$TREE/out/vs/workbench/workbench.web.main.internal.js" \
  && die "[BR-05] وجهةُ مستودعِ المنبع في الحزمة — شجرةٌ بُنيت قبل إصلاح GH_REPO_PATH"

say "الحزم ⇐ $OUT"
tar czf "$OUT" -C "$TREE" . || die "فشل الحزم"

_sha() { sha256sum "$1" | cut -d' ' -f1; }
SHA_T="$(_sha "$OUT")"
SHA_C="$(_sha "$CONF")"

# الكتابةُ في مكانها: بديلٌ عن خطوةٍ يدويّةٍ تُنسى.
sed -i -E "s/^SHA_TREE=[0-9a-f]{64}$/SHA_TREE=$SHA_T/" "$SCRIPT"
sed -i -E "s/^SHA_CONF=[0-9a-f]{64}$/SHA_CONF=$SHA_C/" "$SCRIPT"
grep -q "SHA_TREE=$SHA_T" "$SCRIPT" || die "تعذّرت كتابةُ SHA_TREE في $SCRIPT"
grep -q "SHA_CONF=$SHA_C" "$SCRIPT" || die "تعذّرت كتابةُ SHA_CONF في $SCRIPT"
say "البصمتان مكتوبتان في static_deploy.sh"
echo "   tree: $SHA_T"
echo "   conf: $SHA_C"

if [[ -z $DEST ]]; then
  echo
  echo "   لم يُعطَ خادم — للرفع:"
  echo "     scp -P $PORT $OUT:tree.tgz $CONF $SCRIPT <مستخدم>@<خادم>:/tmp/mihrab-static/"
  exit 0
fi

say "الرفع ⇐ $DEST"
ssh -p "$PORT" "$DEST" 'mkdir -p /tmp/mihrab-static' || die "تعذّر تجهيزُ المرحلة"
scp -P "$PORT" "$OUT" "$DEST:/tmp/mihrab-static/tree.tgz" || die "فشل رفعُ الشجرة"
scp -P "$PORT" "$CONF" "$SCRIPT" "$DEST:/tmp/mihrab-static/" || die "فشل رفعُ الإعداد"

# تحقّقٌ من الطرف الآخر: بصمةٌ تُحسَب هنا لا تُثبِت ما وصل هناك.
REMOTE="$(ssh -p "$PORT" "$DEST" 'sha256sum /tmp/mihrab-static/tree.tgz | cut -d" " -f1')"
[[ "$REMOTE" == "$SHA_T" ]] || die "ما وصل يخالف ما غادر ($REMOTE) — أعِد الرفع."
say "وصلت الحمولةُ سليمةً"

cat <<'EOF'

   ثمّ على الخادم:
     sudo install -D -o root -g root -m 755 \
          /tmp/mihrab-static/static_deploy.sh \
          /usr/local/lib/mihrab-deploy/static_deploy.sh
     sudo bash /usr/local/lib/mihrab-deploy/static_deploy.sh
EOF
