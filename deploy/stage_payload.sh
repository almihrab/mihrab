#!/usr/bin/env bash
# تجهيزُ حمولةِ النشر الثابت — **يُشغَّل من جذر المستودع، على جهاز البناء لا الخادم**.
#
#     deploy/stage_payload.sh [--nginx-only] [<مستخدم>@<خادم>]
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

# ‏`--nginx-only` **متناظرةٌ مع نظيرتها في `static_deploy.sh`**، ولهذا التناظرِ سبب:
# رايةٌ يقبلها طرفٌ ويرفضها الآخرُ ليست رايةً بل فخّ. وكانت هذه الأداةُ تشترط شجرةً
# مبنيّةً لتنقل **كتلةَ nginx وحدَها** — فتعذّرَ نقلُ سطرٍ واحدٍ يومَ زالت الشجرةُ
# من جهاز البناء، وهو بعينه اليومُ الذي وُضِعت الرايةُ من أجله.
NGINX_ONLY=no
case "${1:-}" in
  --nginx-only) NGINX_ONLY=yes; shift ;;
esac
DEST="${1:-}"

die() { echo "❌ $*" >&2; exit 1; }
say() { echo "── $*"; }

[[ -f $CONF && -f $SCRIPT ]] || die "ملفّاتُ النشر ناقصة."

if [[ $NGINX_ONLY == no ]]; then
  [[ -d $TREE ]] || die "لا شجرةَ ثابتة في $TREE — شغّل build/build.sh أوّلًا.
   (وإن كان المقصودُ كتلةَ nginx وحدَها فوق شجرةٍ منشورة: --nginx-only)"
  [[ -f $TREE/.mihrab-built-at ]] \
    || die "الشجرةُ بلا طابعِ بناء — بقيّةُ بناءٍ سابق. احذفها وأعِد البناء."
  say "طابعُ البناء: $(cat "$TREE/.mihrab-built-at")"
else
  say "الكتلةُ وحدَها — لا شجرةَ تُحزَم ولا تُرفَع"
fi

# بوّابةٌ قبل الحزم: ما لا يُقاس هنا يُقاس على الخادم بعد فوات الأوان.
# ‏`boot-early.js` في القائمة [WEB-09]: خرج من `index.html` كي تستغني سياسةُ الأمان
# عن `'unsafe-inline'`. وغيابُه لا يُنتج صفحةَ خطأ — يُنتج شاشةَ إقلاعٍ لا تنتهي،
# لأنّ `_VSCODE_FILE_ROOT` لا يُضبَط فلا تُحلّ مساراتُ الحزمة أصلًا.
_sha() { sha256sum "$1" | cut -d' ' -f1; }

if [[ $NGINX_ONLY == no ]]; then
  for f in index.html boot.js boot-early.js product.web.js manifest.json favicon.ico \
           out/nls.messages.js out/vs/workbench/workbench.web.main.internal.js \
           out/vs/workbench/kawkab-mono.woff2; do
    [[ -s "$TREE/$f" ]] || die "ملفٌّ لازمٌ مفقودٌ أو فارغ: $f"
  done
  grep -q 'VSCodium/vscodium' "$TREE/out/vs/workbench/workbench.web.main.internal.js" \
    && die "[BR-05] وجهةُ مستودعِ المنبع في الحزمة — شجرةٌ بُنيت قبل إصلاح GH_REPO_PATH"

  say "الحزم ⇐ $OUT"
  tar czf "$OUT" -C "$TREE" . || die "فشل الحزم"

  SHA_T="$(_sha "$OUT")"
  sed -i -E "s/^SHA_TREE=[0-9a-f]{64}$/SHA_TREE=$SHA_T/" "$SCRIPT"
  grep -q "SHA_TREE=$SHA_T" "$SCRIPT" || die "تعذّرت كتابةُ SHA_TREE في $SCRIPT"
  echo "   tree: $SHA_T"
fi

# ‏**بصمةُ الكتلة تُكتَب دائمًا وتُقرأ بعد الكتابة.** والترتيبُ ليس تجميلًا: البصمةُ
# تُحسَب على `$CONF`، وتُكتَب في `$SCRIPT` — وهما ملفّان مختلفان، فلا يُبطِل أحدُهما
# الآخر. ولو حُسِبت على `$SCRIPT` لَما استقرّت أبدًا (تُغيّرها كتابتُها).
SHA_C="$(_sha "$CONF")"
sed -i -E "s/^SHA_CONF=[0-9a-f]{64}$/SHA_CONF=$SHA_C/" "$SCRIPT"
grep -q "SHA_CONF=$SHA_C" "$SCRIPT" || die "تعذّرت كتابةُ SHA_CONF في $SCRIPT"
say "البصمةُ مكتوبةٌ في static_deploy.sh"
echo "   conf: $SHA_C"

if [[ -z $DEST ]]; then
  echo
  echo "   لم يُعطَ خادم — للرفع:"
  # الوجهةُ اسمُ مجلّدٍ لا اسمُ ملفّ، والحزمةُ تُرفَع باسمها ثمّ تُسمّى هناك: كتابةُ
  # ‏`$OUT:tree.tgz` كانت تُنتج سطرًا **لا يعمل إن نُسِخ** — و`scp` يقرأ ما قبل النقطتين
  # مُضيفًا بعيدًا، فيحاول الاتّصال بمضيفٍ اسمُه مسارُ الملفّ. تلميحٌ خاطئٌ أسوأُ من
  # لا تلميح: القارئُ ينسخه ويثق به.
  if [[ $NGINX_ONLY == yes ]]; then
    echo "     scp -P $PORT '$CONF' '$SCRIPT' <مستخدم>@<خادم>:/tmp/mihrab-static/"
  else
    echo "     scp -P $PORT '$OUT' '$CONF' '$SCRIPT' <مستخدم>@<خادم>:/tmp/mihrab-static/"
    echo "     ثمّ على الخادم: mv /tmp/mihrab-static/$(basename "$OUT") /tmp/mihrab-static/tree.tgz"
  fi
  exit 0
fi

say "الرفع ⇐ $DEST"
ssh -p "$PORT" "$DEST" 'mkdir -p /tmp/mihrab-static' || die "تعذّر تجهيزُ المرحلة"
[[ $NGINX_ONLY == no ]] && { scp -P "$PORT" "$OUT" "$DEST:/tmp/mihrab-static/tree.tgz" \
  || die "فشل رفعُ الشجرة"; }
scp -P "$PORT" "$CONF" "$SCRIPT" "$DEST:/tmp/mihrab-static/" || die "فشل رفعُ الإعداد"

# تحقّقٌ من الطرف الآخر: بصمةٌ تُحسَب هنا لا تُثبِت ما وصل هناك. **والكتلةُ تُفحَص
# كذلك** — كانت الشجرةُ وحدَها تُفحَص، والكتلةُ (وهي ما يُركَّب في nginx ويُقلِعه أو
# يُسقِطه) تصل بلا سؤال. وهي أصغرُ فأسرعُ فأولى بالفحص لا أحقرُ منه.
if [[ $NGINX_ONLY == no ]]; then
  REMOTE="$(ssh -p "$PORT" "$DEST" 'sha256sum /tmp/mihrab-static/tree.tgz | cut -d" " -f1')"
  [[ "$REMOTE" == "$SHA_T" ]] || die "ما وصل يخالف ما غادر ($REMOTE) — أعِد الرفع."
fi
REMOTE_C="$(ssh -p "$PORT" "$DEST" 'sha256sum /tmp/mihrab-static/mihrab.dev.static.conf | cut -d" " -f1')"
[[ "$REMOTE_C" == "$SHA_C" ]] || die "الكتلةُ وصلت مخالفةً ($REMOTE_C) — أعِد الرفع."
say "وصلت الحمولةُ سليمةً"

cat <<'EOF'

   ثمّ على الخادم:
     sudo install -D -o root -g root -m 755 \
          /tmp/mihrab-static/static_deploy.sh \
          /usr/local/lib/mihrab-deploy/static_deploy.sh
EOF
# ‏**السطرُ الأخيرُ يحمل الرايةَ التي شُغِّلت بها هذه الأداة.** الحمولةُ المرفوعةُ الآن
# كتلةٌ بلا شجرة؛ وسطرُ تشغيلٍ بلا `--nginx-only` يُنتج نشرًا كاملًا يموت عند
# `tree.tgz` المفقود. رسالةٌ واضحةٌ نعم، لكنّ التلميحَ الذي **لا يعمل إن نُسِخ**
# سبق أن كُتِب هنا مرّةً (‏`$OUT:tree.tgz`) وأُصلِح — فلا يُعاد.
_flag=""
[[ $NGINX_ONLY == yes ]] && _flag=" --nginx-only"
echo "     sudo bash /usr/local/lib/mihrab-deploy/static_deploy.sh$_flag"
