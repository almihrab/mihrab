#!/usr/bin/env bash
# [PKG-02] غلافُ curl لتغليف لينكس (`build/lib/curl_shim.sh`) — بـcurl وهميٍّ، بلا شبكة.
#   bash tests/static/test_curl_shim.sh
# بلا هذا لا يُرى الغلافُ يعمل إلّا في بناء لينكس الحقيقيّ — بعد ساعة، وفي اليوم الذي يردّ فيه الخادمُ 429.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
cp "$HERE/build/lib/curl_shim.sh" "$T/curl"; chmod +x "$T/curl"

# ‏curl الوهميّ: يسجّل استدعاءاته، وسلوكُه بـFAKE_PRIMARY (المضيف الأوّل) وFAKE_FALLBACK (googlesource).
# ويحاكي الحقيقيَّ في ما يهمّ: بلا `-f` يكتب صفحةَ «429» في الملفّ ويخرج 0.
cat > "$T/fake" <<'FAKE'
#!/usr/bin/env bash
echo "$*" >> "$FAKE_LOG"
out="" url="" f=0
for ((i = 1; i <= $#; i++)); do
  a="${!i}"
  case "$a" in -o) j=$((i + 1)); out="${!j}" ;; http*) url="$a" ;; -f*) f=1 ;; esac
done
emit() { if [[ -n "$out" ]]; then printf '%s' "$1" > "$out"; else printf '%s' "$1"; fi; }
case "$url" in *googlesource*) mode="$FAKE_FALLBACK" ;; *) mode="$FAKE_PRIMARY" ;; esac
case "$mode" in
  ok)       emit $'#!/usr/bin/perl\nprint 1;\n'; exit 0 ;;
  b64ok)    emit "$(printf '#!/usr/bin/perl\nprint 1;\n' | base64 | tr -d '\n')"; exit 0 ;;
  b64html)  emit "$(printf '<html>429 Too Many</html>' | base64 | tr -d '\n')"; exit 0 ;;
  html200)  emit '<!DOCTYPE html><html>sign in</html>'; exit 0 ;;
  b64trunc) emit "$(printf '#!/usr/bin/perl\nprint 1;\nprint 2;\n' | base64 | tr -d '\n' | head -c 16)"; exit 18 ;;
  429)      ((f)) || { emit "429: Too Many Requests"; exit 0; }
            echo "curl: (22) The requested URL returned error: 429" >&2; exit 22 ;;
esac
exit 99
FAKE
chmod +x "$T/fake"
export MIHRAB_REAL_CURL="$T/fake" FAKE_LOG="$T/log"

pass=0 fail=0
URL=https://raw.githubusercontent.com/chromium/chromium/150.0.7871.250/third_party/dpkg-shlibdeps/dpkg-shlibdeps.pl
ok()  { pass=$((pass + 1)); echo "  ✅ [PKG-02] $1"; }
bad() { fail=$((fail + 1)); echo "  ❌ [PKG-02] $1"; }

check() { # الاسم · الرمزُ المتوقَّع · ملفٌّ؟(yes|no) · الأوّل · الاحتياط · [الرابط]
  local name=$1 wrc=$2 wfile=$3 u=${6:-$URL}
  export FAKE_PRIMARY=$4 FAKE_FALLBACK=$5
  : > "$FAKE_LOG"; rm -f "$T/out.pl" "$T/out.pl.part" "$T/out.pl.b64"
  "$T/curl" "$u" -o "$T/out.pl" 2> "$T/err"; local rc=$?
  local got=no; [[ -f "$T/out.pl" ]] && got=yes
  local why=""
  [[ $rc == "$wrc" ]] || why+=" خرج $rc لا $wrc؛"
  [[ $got == "$wfile" ]] || why+=" الملفّ: $got لا $wfile؛"
  [[ -e "$T/out.pl.part" || -e "$T/out.pl.b64" ]] && why+=" بقي .part/.b64؛"
  [[ $got == yes && "$(head -c2 "$T/out.pl")" != "#!" ]] && why+=" الملفُّ لا يبدأ بـ#!؛"
  if [[ -z $why ]]; then ok "$name"; else bad "$name —$why"; fi
}

echo "╔══ [PKG-02] غلافُ curl لتغليف لينكس ══╗"
check "نجاح مباشر"                     0  yes ok  -
check "429 ثم احتياط ناجح"              0  yes 429 b64ok
check "احتياط يرجع HTML مرمّزًا يُرفض"   22 no  429 b64html
check "احتياط يرجع HTML خامًّا يُرفض"    22 no  429 html200
check "احتياط يفشل كلّيًّا"              22 no  429 429
check "احتياط مبتور (curl خرج 18) يُرفض" 22 no  429 b64trunc
check "مضيفٌ آخر: لا احتياط"            22 no  429 b64ok https://raw.githubusercontent.com/electron/electron/v1/script/sysroots.json

FAKE_PRIMARY=429 FAKE_FALLBACK=b64ok; export FAKE_PRIMARY FAKE_FALLBACK; : > "$FAKE_LOG"
"$T/curl" "$URL" -o "$T/out.pl" 2> /dev/null
if grep -q 'chromium/src/+/refs/tags/150.0.7871.250/third_party/dpkg-shlibdeps/dpkg-shlibdeps.pl?format=TEXT' "$FAKE_LOG" \
   && grep -q -- '-fsSL --retry 5' "$FAKE_LOG" && grep -q -- '--retry-max-time' "$FAKE_LOG"; then
  ok "رابطُ الاحتياط بالوسم refs/tags، والخيارات -f وretry بسقف"
else
  bad "رابطُ الاحتياط أو الخيارات: $(tr '\n' '|' < "$FAKE_LOG")"
fi
# ‏`PATH=… gulp_task` على دالّةٍ تفتح subshell يصل إلى العمليّة الابنة (node ⇐ curl في المنبع).
_fn() { ( bash -c 'command -v curl' ); }
if [[ "$(PATH="$T:$PATH" _fn)" == "$T/curl" ]]; then ok "PATH المؤقّت يصل إلى الابن عبر دالّة"; else bad "PATH لا يصل إلى الابن"; fi

if ((fail)); then echo "❌ $fail حالةً من $((pass + fail))"; exit 1; fi
echo "╚══ ✅ $pass حالات ══╝"
