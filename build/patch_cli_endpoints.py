#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""‏وجهتا الـCLI مخبوزتان في Rust — و[BR-05] يسكن هناك حيث لا يبلغه ترقيعُ JS.

    python build/patch_cli_endpoints.py <‏.upstream/build_cli.sh>

## العطب

`bin/mihrab-tunnel.exe` ثنائيٌّ رُسْتيٌّ يحمل قالبَين مخبوزَين وقتَ الترجمة. قِيسا في
بايتاته (بحثٌ بايتيّ، لا `strings` — وهي غيرُ مثبَّتةٍ على جهاز البناء وتعود بصفرِ
نتائجَ صامتةً، أي بشهادةِ نظافةٍ كاذبة):

```
vscodium https://github.com/VSCodium/vscodium/releases
         /download/{}/{}-reh-web-{}-{}-{}.tar.gz
VSCODE_CLI_UPDATE_URL
         https://raw.githubusercontent.com/VSCodium/versions/refs/heads/master
```

ومنشؤهما `build_cli.sh` قبل `cargo build`، ورقعةُ VSCodium
`40-cli-use-reh-archive.patch` تقرؤهما بـ`option_env!` — **أي وقتَ الترجمة**. فليسا
مفتاحًا في `product.json` يُعاد كتابتُه، ولا سلسلةً في حزمةِ JS تُرقَّع بعد البناء.
ولهذا أعلنت بوّابةُ [BR-05] الشجرةَ نظيفةً وهي ليست كذلك: كانت تمسح `.js` وحدَها.

والأثرُ ليس اسمًا في نصّ:
  • من شغّل `tunnel` أو `serve-web` يُرسِل عنوانَه ونسختَه ومنصّتَه إلى GitHub
    الخاصّ بالمنبع — طرفٌ ثالثٌ لم يخترْه.
  • وينزّل — لو وُجد — **خادمَ VSCodium**: بلا عربيّة، بلا RTL، بلا لغة ص. ونسخةُ
    محرابٍ ليست في إصداراتهم أصلًا ⇒ 404.

## ولماذا التوجيهُ لا الحذف

الحجّةُ التي سُجِّل بها هذا دَينًا كانت «لا ننشر خوادمَ REH فالبديلُ ألّا نَعِد بما
لا نشحن». **وهي قامت على فرضٍ خاطئ**: `build.sh:807` يقول إنّ `vscode-reh-web-*`
يُنتَج في **كلّ** بناء (‏428 م.ب على القرص)، وفيه هويّةُ محرابٍ كاملةٌ و130 قاعدةَ
`[dir=rtl]`، وعُرِّب عمدًا في [WEB-01] بعد أن كان صفرَ سلاسلَ عربيّةٍ من 21922.
الذي تقاعد **استضافتُنا** له على mihrab.dev لا إنتاجُه.

وقرارُ «لا خادم» كان عن أن نستضيفَ نحن — أي أن يُفتَح نظامُ ملفّاتِنا وطرفيّتُنا
خلف عنوانٍ عامّ. و`tunnel`/`serve-web` يشغّلهما **المستخدمُ على جهازه**: ملفّاتُه هو،
وطرفيّتُه هو، وباختياره. فلا تعارض.

## العلاج

`${VAR:-افتراضيّنا}` كأدبِ `utils.sh`: من ضبط شيئًا يُحترَم ضبطُه.

ووجهةُ **التحديث** لا تُوجَّه بل **تُرفَع شرطيّةً**: لا مستودعَ نُسَخٍ عندنا، وقيمةٌ
فارغةٌ ليست حلًّا — `option_env!` يعطي `Some("")` فيُطلَب عنوانٌ فارغٌ بدل أن
يُقال «لا تحديث». والصوابُ ألّا يُصدَّر المتغيّرُ إطلاقًا ما لم يصدّره المُنادي،
فيعطي `option_env!` ‏`None` ويردّ الـCLI «no update url» صراحةً.

⚠️ و`if … fi` لا `[[ … ]] && export`: السكربتُ تحت `set -e`، وشرطٌ كاذبٌ في آخر
   صيغةٍ **يُنهي السكربتَ كلَّه**. فئةُ خطأٍ تُلدَغ بها الصدَفةُ في كلّ مرّة.
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

FILES = ("build_cli.sh",)

OUR_RELEASES = "https://github.com/mihrab-org/mihrab/releases"

# ‏المِرساتان تقبلان أيَّ قيمةٍ افتراضيّة: ترقيةُ المنبع تغيّرها (‏`vscodium-insiders`
# مثلًا)، والمقصودُ **الشكلُ** — `export VAR="قيمةٌ حرفيّةٌ بلا شرط"` — لا القيمةُ
# بعينها. ونهايةُ السطر تقبل محرفَ الإرجاع: الملفُّ يُقرأ بلا ترجمةٍ ليعود كما وُجِد،
# وشجرةُ ويندوز تُستنسَخ بـ`core.autocrlf` مفعَّلًا [CRLF-01].
# ⚠️ **نظرةٌ أماميّةٌ لا استهلاك** (`(?=\r?$)`): أوّلُ صياغةٍ كتبت `\r?$`، فابتلع
#    التعبيرُ محرفَ الإرجاع ولم يُعِده البديلُ — فخرج الملفُّ **مختلطَ النهايات**:
#    ثلاثةُ أسطرٍ بـLF في ملفٍّ كلُّه CRLF. أمسكه تشغيلُ المرقِّع على نسختَي الطرفَين
#    قبل أن يبلغ شجرةً حقيقيّة. وهو [CRLF-01] بعينه، في المرقِّع المكتوب بعد فئته.
DL = re.compile(r'^([ \t]*)export VSCODE_CLI_DOWNLOAD_ENDPOINT="([^"$]+)"(?=\r?$)', re.M)
UP = re.compile(r'^export VSCODE_CLI_UPDATE_ENDPOINT="([^"$]+)"(?=\r?$)', re.M)

DL_DONE = re.compile(r'export VSCODE_CLI_DOWNLOAD_ENDPOINT="\$\{VSCODE_CLI_DOWNLOAD_ENDPOINT:-')
UP_DONE = re.compile(r'if \[\[ -n "\$\{VSCODE_CLI_UPDATE_ENDPOINT:-\}" \]\]')

UP_REPLACEMENT = (
    '# محراب [BR-05]: لا مستودعَ نُسَخٍ عندنا ⇒ لا وجهةَ تحديثٍ أصلًا. والفراغُ ليس\n'
    '# حلًّا: `option_env!` يعطي `Some("")` فيُطلَب عنوانٌ فارغٌ بدل أن يُقال «لا\n'
    '# تحديث». فلا يُصدَّر ما لم يصدّره المُنادي، فيعطي `None` ويردّ الـCLI صراحةً.\n'
    '# و`if … fi` لا `[[ … ]] && …`: السكربتُ تحت `set -e`، وشرطٌ كاذبٌ في الصيغة\n'
    '# الأخيرة يُنهي السكربتَ كلَّه.\n'
    'if [[ -n "${VSCODE_CLI_UPDATE_ENDPOINT:-}" ]]; then\n'
    '  export VSCODE_CLI_UPDATE_ENDPOINT\n'
    'fi'
)


def fail(msg):
    print("❌ " + msg, file=sys.stderr)
    return 1


def main(path):
    if not os.path.isfile(path):
        return fail("لا ملفَّ build_cli.sh: " + path)
    src = io.open(path, encoding="utf-8", newline="").read()

    if DL_DONE.search(src) and UP_DONE.search(src):
        print("  ⏭️ وجهتا الـCLI مُرقَّعتان سلفًا")
        return 0

    eol = "\r\n" if "\r\n" in src else "\n"

    dl_hits = DL.findall(src)
    if len(dl_hits) < 1:
        return fail("مِرساةُ VSCODE_CLI_DOWNLOAD_ENDPOINT لم تقع — بنيةُ build_cli.sh "
                    "ليست ما قِيس. لا يُرقَّع موضعٌ لم يُقرأ [BR-05].")
    up_hits = UP.findall(src)
    if len(up_hits) != 1:
        return fail("مِرساةُ VSCODE_CLI_UPDATE_ENDPOINT وقعت " + str(len(up_hits)) +
                    " مرّةً لا مرّةً واحدة — بنيةُ build_cli.sh ليست ما قِيس [BR-05].")

    def _dl(m):
        return (m.group(1) + 'export VSCODE_CLI_DOWNLOAD_ENDPOINT='
                + '"${VSCODE_CLI_DOWNLOAD_ENDPOINT:-' + OUR_RELEASES + '}"')

    out = DL.sub(_dl, src)
    out = UP.sub(lambda _m: UP_REPLACEMENT.replace("\n", eol), out, count=1)

    tmp = path + ".mihrab-tmp"
    io.open(tmp, "w", encoding="utf-8", newline="").write(out)
    os.replace(tmp, path)
    print("  ✅ وجهةُ التنزيل ⇐ " + OUR_RELEASES
          + " (" + str(len(dl_hits)) + " موضعًا)")
    print("  ✅ وجهةُ التحديث صارت شرطيّةً — بلا ضبطٍ خارجيٍّ لا عنوانَ إطلاقًا")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
