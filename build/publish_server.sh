#!/usr/bin/env bash
# نشرُ أثرِ خادمِ النفق — ما ينزّله `mihrab-tunnel` ويشغّله على جهاز المستخدم.
#
#   build/publish_server.sh /مسار/mihrab-reh-web-win32-x64-1.126.06007.tar.gz [مسارٌ آخر …]
#
# ‏**ولماذا سكربتٌ ثانٍ ولا `publish_release.sh`؟** ذاك ينشر ما يُنزِّله **إنسانٌ من
# صفحة**: يتحقّق من معرّفات `site/data/site.json` ويكتب `releases.json` الذي يبني
# جدولَ التنزيل. وهذا ينشر ما يُنزِّله **برنامجٌ من عنوانٍ مخبوزٍ في ثنائيّ**: لا
# معرّفَ منصّةٍ له، ولا يظهر في جدول، وتخطيطُه ليس اختيارًا بل ما يبنيه
# ‏`update_service.rs` حرفيًّا. وخلطُهما يعني أنّ رفعَ خادمٍ يمسح مانيفستَ الإصدار،
# أو أن يظهر أرشيفُ خادمٍ في صفحة التنزيل صفًّا لا يعرف الزائرُ ما هو.
#
# التخطيطُ الذي يقرؤه الـCLI (مقيسٌ في المصدر لا مُخمَّن):
#   المانيفست: {قاعدة}/{جودة}/{نظام}/{معماريّة}/latest.json   ⟵ update_service.rs:88
#              محتواه {"name": …, "version": …}               ⟵ UpdateServerVersion
#   الأثر:     {قاعدة}/download/{name}/{app}-reh-web-{نظام}-{معماريّة}-{name}.tar.gz
#                                                             ⟵ get_download_url()
# و`name` هو ما يظهر في **العنوان مرّتَين**، و`version` هو ما يُخزَّن به الخادمُ في
# ذاكرة المستخدم المؤقّتة (`cache.create(&release.commit, …)`). فاسمٌ يتكرّر مع
# محتوًى مختلفٍ يترك خادمًا قديمًا يعمل إلى الأبد؛ ولهذا يُشتقّان من اسم الملفّ.
set -euo pipefail

HOST="${MIHRAB_SITE_HOST:?عيّن MIHRAB_SITE_HOST (مثال: user@host)}"
PORT="${MIHRAB_SITE_PORT:-22}"
# القاعدةُ نفسُها التي تخبزها (و-4ب) في build/build.sh — ولا تُكتَب مرّتَين بيدٍ:
# فرقُ حرفٍ بين المخبوز والمنشور يعني 404 لا يظهر إلّا عند المستخدم.
BASE_URL="${MIHRAB_SERVER_BASE:-https://sad-lang.org/mihrab/dl/server}"
SRV_DIR="${MIHRAB_SITE_ROOT:-/opt/sad-website}/${MIHRAB_SITE_SUBDIR:-mihrab}/dl/server"

SSH=(ssh -p "$PORT" -o BatchMode=yes)

die() { echo "❌ $*" >&2; exit 1; }
say() { echo "▶ $*"; }

(( $# >= 1 )) || die "الاستعمال: $0 <أثرٌ .tar.gz> [أثرٌ آخر …]"

for arg in "$@"; do
  case "$arg" in
    -*) die "وسيطٌ غيرُ معروف: $arg — هذا السكربتُ يأخذ مساراتِ آثارٍ لا رايات" ;;
  esac
done

for path in "$@"; do
  [[ -f "$path" ]] || die "ملفٌّ غير موجود: $path"
  file="$(basename "$path")"

  # ‏**الاسمُ يُفكَّك ولا يُصدَّق.** أرشيفٌ باسمٍ لا يطابق القالبَ يُرفَع بلا شكوى ثمّ
  # لا يجده الـCLI أبدًا — والعطبُ يظهر عند المستخدم بعد أشهر، لا هنا.
  # القالب: {app}-reh-web-{نظام}-{معماريّة}-{name}.tar.gz
  [[ "$file" =~ ^([A-Za-z0-9_.-]+)-reh-web-(win32|linux|darwin|alpine)-([A-Za-z0-9]+)-(.+)\.tar\.gz$ ]] \
    || die "اسمٌ لا يطابق قالبَ الـCLI: $file
   المنتظَر: <app>-reh-web-<win32|linux|darwin|alpine>-<معماريّة>-<نسخة>.tar.gz
   والقالبُ ليس اصطلاحًا عندنا بل ما يبنيه update_service.rs حرفيًّا."
  app="${BASH_REMATCH[1]}"; os="${BASH_REMATCH[2]}"
  arch="${BASH_REMATCH[3]}"; name="${BASH_REMATCH[4]}"

  # ‏**واسمُ التطبيق يُطابَق بهويّتنا لا يُقبَل كما جاء.** أرشيفٌ باسم المنبع
  # (`vscodium-reh-web-…`) يطابق القالبَ تمامًا، ويُرفَع بلا شكوى، ويُقدَّم من
  # نطاقنا خادمًا **ليس خادمَنا**: بلا عربيّةٍ ولا اتّجاهٍ ولا لغة ص. وهو عطبٌ
  # وقع فعلًا في الثنائيّ قبل هذا (بقيت `vscodium` مفردةً بعد تصحيح المضيف)،
  # فيُقاس هنا كذلك — وهذا ما يجعل النشرَ طرفًا في [BR-05] لا خطوةَ نقلٍ صمّاء.
  # ‏`path.resolve` لازمة: `require` بمسارٍ لا يبدأ بـ`./` يُعامَل **اسمَ حزمةٍ**
  # فيموت بـMODULE_NOT_FOUND — والقيمةُ تصير فارغةً فيمرّ الفحصُ على كلّ شيء.
  want_app="$(node -p "require(require('path').resolve(process.argv[1])).applicationName" "$(dirname "${BASH_SOURCE[0]}")/../product-overrides/product.json")"
  [[ "$app" == "$want_app" ]] || die "اسمُ التطبيق في الأثر «$app» وهويّتُنا «$want_app».
   المعنى: هذا ليس خادمَنا — أو أنّ البناءَ خرج باسم المنبع. وفي الحالتَين
           يُقدَّم من نطاقنا خادمٌ بلا عربيّةٍ ولا اتّجاه [BR-05]."

  # ونقطةُ الدخول تُقاس **قبل الرفع**: أرشيفٌ بلا `bin/…` يُنزَّل كاملًا عند
  # المستخدم (مئاتُ الميغابايتات) ثمّ يُخفِق. والقياسُ هنا يكلّف ثانية.
  tar tzf "$path" 2>/dev/null | grep -qE "^\./bin/[^/]+$" \
    || die "لا bin/ في جذر الأرشيف: $file — يُفكّ سليمًا ولا يُقلِع"

  say "رفع $file ($(du -m "$path" | cut -f1) م.ب) …"
  "${SSH[@]}" "$HOST" "mkdir -p '$SRV_DIR/download/$name' '$SRV_DIR/stable/$os/$arch'"
  # رفعٌ إلى اسمٍ مؤقّتٍ ثمّ تسميةٌ ذرّيّة: انقطاعٌ في المنتصف يجب ألّا يترك أرشيفًا
  # نصفَ مكتملٍ يحمل الاسمَ النهائيّ — وهنا خاصّةً، فالمُنزِّلُ برنامجٌ لا إنسان،
  # ولا يفتح الملفَّ ليرى أنّه ناقص: يفكّه ويُخفِق برسالةٍ لا تدلّ على السبب.
  scp -P "$PORT" -o BatchMode=yes "$path" "$HOST:$SRV_DIR/download/$name/.$file.part"
  "${SSH[@]}" "$HOST" "mv '$SRV_DIR/download/$name/.$file.part' '$SRV_DIR/download/$name/$file'"

  # البصمةُ تُحسَب **على الخادم بعد الرفع**: يجب أن تصف ما وصل لا ما غادر.
  sha="$("${SSH[@]}" "$HOST" "sha256sum '$SRV_DIR/download/$name/$file' | cut -d' ' -f1")"
  local_sha="$(sha256sum "$path" | cut -d' ' -f1)"
  [[ "$sha" == "$local_sha" ]] || die "بصمةُ ما وصل تخالف ما غادر:
   محلّيًّا: $local_sha
   على الخادم: $sha
   المعنى: الرفعُ عطب. والملفُّ في مكانه الآن باسمه النهائيّ — احذفه قبل إعادة المحاولة."
  echo "   ✓ $sha"

  # ── المانيفست يُكتب **بعد** الأثر، ذرّيًّا ──
  # الترتيبُ ليس تجميلًا: مانيفستٌ يَعِد باسمٍ لا أثرَ له يجعل كلَّ عميلٍ يقرؤه
  # يُخفِق حتّى يصل الرفعُ — نافذةٌ يظهر فيها العطبُ عند المستخدمين لا عندنا.
  # و`version` = `name`: لا مُعرّفَ إيداعٍ لدينا يُميّز بناءَين بالاسم نفسِه،
  # والنسخةُ عندنا تحمل رقمَ البناء أصلًا (1.126.06007) فهي فريدةٌ لكلّ أثر.
  printf '{"name":"%s","version":"%s"}\n' "$name" "$name" \
    | "${SSH[@]}" "$HOST" "cat > '$SRV_DIR/stable/$os/$arch/.latest.json.new' \
                           && mv '$SRV_DIR/stable/$os/$arch/.latest.json.new' \
                                 '$SRV_DIR/stable/$os/$arch/latest.json'"
  echo "   ✓ $BASE_URL/stable/$os/$arch/latest.json ⇐ $name"
done

echo
echo "✅ أثرُ الخادم منشور. والبناءُ التالي **يقيسه فيخبز الوجهةَ من نفسه** —"
echo "   لا خطوةَ يدويّةً بعد هذه. وللتحقّق الآن:"
echo "     curl -fsS $BASE_URL/stable/$os/$arch/latest.json"
