# النشر والإصدارات

> لمن ينشر الموقع، أو يرفع إصدارًا جديدًا من محراب، أو يضيف منصّة.
> ← [فهرس الموقع](../README.md)

## أين ينشر

| | العنوان | مَن ينشر |
| --- | --- | --- |
| **الأصل** | <https://mihrab.dev/> | السكربت `build/deploy_site.sh`، بـtar عبر ssh |
| المرآة | غيرُ مفعَّلة ([ق-01](decisions.md#ق-01--الأصل-على-خادمنا)) | — |

- **النطاق:** الجذرُ هذا الموقع، و`app.mihrab.dev` محرابُ المتصفّح، وهو أصلٌ منفصلٌ عمدًا.
- **الهويّة:** يشير `product-overrides/product.json` و`rel=canonical` في كلّ صفحةٍ إلى الجذر.
- **الخطوط:** كتلةُ الخطوط على الخادم تحمل ترويسةَ `Access-Control-Allow-Origin`. صفحةُ 404 تُقدَّم من الأصلين، فتجلب الخطَّ عبر الأصل، وبلا الترويسة يسقط الخطُّ بصمت.

## انشر الموقع

يلزمك: مفتاحُ ssh إلى الخادم، وعنوانُه في `MIHRAB_SITE_HOST`.

1. انشر:
   ```bash
   MIHRAB_SITE_HOST=user@host build/deploy_site.sh
   ```

يبني `deploy_site.sh` الموقعَ، ثمّ يفحصه بـ`check_site.py --no-build`، ثمّ ينقله ويبدّل المجلّدَ على الخادم ذرّيًّا.

- **مجلّد `dl/`:** لا يحذف منه شيئًا، ويستبدل `dl/releases.json` بالمخبوز إن كان المخبوزُ أحدث ([MAN-01](checks.md#الإصدار-والهوية)).
- **شاهدُ البناء:** لا يشحن `.mihrab-site-build`.

تحقّق: تفتح `https://mihrab.dev/` بالتعديل، و`https://mihrab.dev/download/` تعرض الإصدارَ الحاليّ.

## ارفع إصدارا

يلزمك: مخرَجُ `build/build.sh` على المنصّة نفسِها، و`MIHRAB_SITE_HOST`.

1. غلّف المخرَج:
   ```bash
   build/package_assets.sh win-x64-zip win-x64-setup
   # ← dist/Mihrab-<الإصدار>-<المعرّف>.<الامتداد>
   ```
2. ارفع الثنائيّات وحدّث المانيفستَ الحيّ:
   ```bash
   MIHRAB_SITE_HOST=user@host build/publish_release.sh <الإصدار> \
       win-x64-setup:dist/Mihrab-<الإصدار>-win-x64-setup.exe \
       win-x64-zip:dist/Mihrab-<الإصدار>-win-x64-zip.zip
   ```
3. انسخ `https://mihrab.dev/dl/releases.json` إلى `site/data/releases.json`، وأودعه، ثمّ [انشر الموقع](#انشر-الموقع).

تحقّق: `https://mihrab.dev/download/` تعرض الإصدارَ الجديد، وروابطُه تنزّل.

- **المعرّفات:** يستعمل `package_assets.sh` أسماءَ معرّفات `data/site.json` نفسَها.
- **البصمة:** يحسب `publish_release.sh` بصمةَ SHA-256 على الخادم بعد الرفع، فتصف ما وصل لا ما غادر.

## أضف منصة

متى: نظامٌ أو معماريّةٌ جديدة في صفحة التنزيل.

1. أضف مدخلَها إلى مصفوفة المنصّات في `site/data/site.json` بحقوله الستّة، على نسق جيرانه: `id`، و`os`، و`arch`، و`label`، و`kind`، و`ext`.
2. أضف فرعَ تغليفها في `build/package_assets.sh`.
3. أضف معرّفَها إلى `assets:` في مصفوفة `.github/workflows/build-matrix.yml`.
4. شغّل `python tests/static/lint_patchers.py` و`python tests/docs/check_site.py`.

تحقّق: يمرّ الفحصان. منصّةٌ في الصفحة بلا فرع تغليفٍ تحمرّ بـ[PKG-01](checks.md#حراس-من-خارج-الموقع).

## المانيفست بنسختيه

| | أين | مَن يكتبها |
| --- | --- | --- |
| الحيّة | `dl/releases.json` على الخادم | السكربت `publish_release.sh`، و`deploy_site.sh` إن كان المخبوزُ أحدث |
| المخبوزة | `site/data/releases.json` | أنت، بعد كلّ إصدار |

- **الحيّة:** تجلبها صفحةُ التنزيل عند فتحها.
- **المخبوزة:** احتياطٌ إن حُجب الجلب.
- **حالةُ الفراغ:** تعني `version: null`، فتحيل الصفحةُ إلى البناء من المصدر.

لماذا نسختان؟ ← [ق-03](decisions.md#ق-03--مانيفستان-حي-ومخبوز)
