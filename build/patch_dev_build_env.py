#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""‏`dev/build.sh` يدهس بيئةَ مُناديه — و[BR-05] عاد من هذا الباب.

    python build/patch_dev_build_env.py <‏.upstream/dev/build.sh>

## العطب

`.upstream/utils.sh` يستبدل `!!GH_REPO_PATH!!` في رُقَع VSCodium، وسطرُه مكتوبٌ
بأدبٍ يحترم المُنادي:

```sh
GH_REPO_PATH="${GH_REPO_PATH:-VSCodium/vscodium}"
```

فضبطُ المتغيّر من الخارج **يكفي في الورق**. لكنّ `dev/build.sh` — وهو نقطةُ الدخول
التي ننادي — يسبقه بسطرٍ لا شرطَ فيه:

```sh
export GH_REPO_PATH="VSCodium/vscodium"
```

فيدهس ما صدّرناه قبل أن يصل `utils.sh`. أي أنّ `export` في `build/build.sh` كان
**يبدو** إصلاحًا وهو لا يصل شيئًا.

## وكيف مرّ ذلك على القياس

لأنّ الشجرةَ التي قِيست خضراءَ لم تكن ناتجَ هذا المسار: أُصلحت بـ`sed` يدويٍّ على
`src/` ثمّ حُزِمت بـ`gulp` وحدَه. فالمقيسُ كان **شجرةً** لا **خطَّ إنتاج**، وأوّلُ
بناءٍ كاملٍ بعده أعاد التسرّبَ كما كان: عنوانان في الحزمة المصغَّرة يجلبان إعلاناتِ
المنبع ويرفعان بلاغاتِ العطب إلى مستودعه.

وبوّابةُ `[BR-05]` في `build.sh` تقيس **الحزمةَ المبنيّة** لا النيّة، وهي التي كانت
ستمسكه — لكنّ البناءَ سقط قبلها لسببٍ آخر. الحارسُ صحيحٌ وترتيبُه أخّره.

## العلاج

أصغرُ تغييرٍ يُعيد للسطر أدبَ نظيره في `utils.sh`: `${VAR:-افتراضيّ}`. لا حذفَ ولا
قيمةً مضروبة — من لم يضبط شيئًا يرى سلوكَ VSCodium كما هو. **ويُقصَر على
`GH_REPO_PATH`**: بقيّةُ المتغيّرات (‏`BINARY_NAME` · `APP_NAME` · `ORG_NAME`) تسمّي
ملفّاتٍ وتُبنى عليها مساراتٌ في مواضعَ لم تُقَس بعد، وتعميمُ الإصلاح عليها يبدّل
أسماءَ المخرَج في خطوةٍ عابرة. هويّةُ محرابٍ تأتيها من `product.json` لا من هنا.

مقترحٌ للمنبع: أن يكتب `dev/build.sh` كلَّ صادراته بصيغة `${VAR:-…}` كما يفعل
`utils.sh` — نقطةُ دخولٍ للمطوّر لا يُفترَض أن تدهس بيئتَه.
"""
import io
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

VAR = "GH_REPO_PATH"
# المِرساةُ تقبل أيَّ قيمةٍ افتراضيّة: ترقيةُ المنبع قد تغيّرها، والمقصودُ **الشكل**
# (‏`export VAR="قيمة"` بلا شرط) لا القيمةُ بعينها.
# ونهايةُ السطر تقبل محرفَ الإرجاع: الملفُّ يُقرأ بـ`newline=""` (بلا ترجمة) كي يعود كما وُجِد، وشجرةُ
# ويندوز تُستنسَخ بـ`core.autocrlf` مفعَّلًا — بل وُجِد هذا الملفُّ بعينه **مختلطَ
# النهايات** على القرص. وقد سقطت أوّلُ صياغةٍ لهذه المِرساة في الفخّ نفسِه الذي
# كُتِبت لأجله فئتُه قبل ساعة [CRLF-01]. يُجرَّب على النهايتَين في L1.
# ⚠️ **نظرةٌ أماميّةٌ لا استهلاك.** كانت `\\r?$` — فيبتلع التعبيرُ محرفَ الإرجاع
# ولا يُعيده البديل، فيخرج `dev/build.sh` **مختلطَ النهايات**: سطرٌ بـLF في ملفٍّ
# كلُّه CRLF. والتعليقُ أدناه كان يقول «يُجرَّب على النهايتَين في L1» — **وهو ادّعاءُ
# تغطيةٍ لا وجودَ لها**: هذا المرقِّعُ في `BUILD_PATCHERS`، وL1 يتخطّاها بحكم تعريفه
# (لا مصدرَ منبعٍ نظيفًا لها). فقِيس بتشغيلٍ فعليٍّ على نسخةٍ CRLF غيرِ مُرقَّعة
# فظهر العطب. والحارسُ الآن ساكنٌ يسري على كلّ مرقِّع [CRLF-02].
ANCHOR = re.compile(r'^export ' + VAR + r'="([^"$]+)"' + '(?=\\r?$)', re.M)
DONE = re.compile(r'^export ' + VAR + r'="\$\{' + VAR + r':-', re.M)


def fail(msg):
    print("❌ " + msg, file=sys.stderr)
    return 1


def main(path):
    if not os.path.isfile(path):
        return fail("لا ملفَّ dev/build.sh: " + path)
    src = io.open(path, encoding="utf-8", newline="").read()

    if DONE.search(src):
        print("  ⏭️ dev/build.sh يحترم البيئةَ سلفًا")
        return 0

    hits = ANCHOR.findall(src)
    if len(hits) != 1:
        return fail("مِرساةُ «export " + VAR + "» وقعت " + str(len(hits)) +
                    " مرّةً لا مرّةً واحدة — بنيةُ dev/build.sh ليست ما قِيس. "
                    "لا يُرقَّع موضعٌ لم يُقرأ [BR-05].")

    out = ANCHOR.sub('export ' + VAR + '="${' + VAR + ':-' + hits[0] + '}"', src, count=1)
    tmp = path + ".mihrab-tmp"
    io.open(tmp, "w", encoding="utf-8", newline="").write(out)
    os.replace(tmp, path)
    print("  ✅ dev/build.sh صار يحترم " + VAR + " من البيئة (افتراضُه " + hits[0] + ")")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
