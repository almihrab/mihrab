#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""‏`file://` تُقتطَع بـ`replace` فيبقى الشرطةُ قبل حرف القرص — بناءُ الويب يسقط على ويندوز.

    python build/patch_esbuild_fileurl.py <‏.upstream/vscode>

## العطب

`extensions/html-language-features/esbuild.browser.mts` يحلّ مكتبةَ TypeScript هكذا:

```ts
const TYPESCRIPT_LIB_SOURCE = path.dirname(import.meta.resolve('typescript').replace('file://', ''));
```

وعلى بوسكس يصحّ بالمصادفة: `file:///a/b` ناقصَ `file://` يساوي `/a/b`. وعلى ويندوز
`import.meta.resolve` يعطي **‏`file:///C:/…`** (قِيس)، فيبقى بعد الاقتطاع `/C:/…` —
مسارٌ يبدأ بشرطةٍ قبل حرف القرص. فيراه `path.join` مطلقًا ويحتفظ بالشرطة، ثمّ يحلّه
`fs` على قرص العمل الحاليّ:

```
ENOENT: no such file or directory, open 'C:\\C:\\…\\typescript\\lib\\lib.es2020.full.d.ts'
```

فيسقط `vscode-web-min` بعد ‎6.7‎ دقيقة — **وهو هدفُ البناء الذي يُنشَر على mihrab.dev**.
والرسالةُ تقول «الملفُّ مفقود» والملفُّ موجودٌ في مكانه بالضبط (قِيس)، فيُبحَث عن
تثبيتٍ ناقصٍ لا عن مسارٍ مضاعَف.

وليس عارضًا: `import.meta.resolve` يعطي الشكلَ نفسَه في كلّ تشغيلٍ على ويندوز، فالهدفُ
يسقط في **كلّ** بناء. ولا يظهر في CI المنبع لأنّه لينكس.

## العلاج

`url.fileURLToPath` — وهي الدالّةُ الموضوعةُ لهذا بالذات: تفكّ الترميزَ وتعالج حرفَ
القرص وتُخرِج مسارًا أصليًّا. و`replace('file://','')` تخمينٌ يصحّ على منصّةٍ واحدة.
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

REL = os.path.join("extensions", "html-language-features", "esbuild.browser.mts")
FILES = (REL.replace(os.sep, "/"),)

# المِرساةُ تقبل أيَّ وحدةٍ تُحَلّ، لا `typescript` وحدَها: المقصودُ **الشكلُ**
# (‏`import.meta.resolve(...).replace('file://', '')`) لا الوسيط.
ANCHOR = re.compile(
    r"import\.meta\.resolve\((?P<arg>[^)]*)\)\.replace\('file://',\s*''\)")
DONE = re.compile(r"fileURLToPath\(import\.meta\.resolve\(")
IMPORT_AFTER = "import * as path from 'node:path';"
IMPORT_LINE = "import { fileURLToPath } from 'node:url';"


def fail(msg):
    print("❌ " + msg, file=sys.stderr)
    return 1


def main(vscode_dir):
    path = os.path.join(vscode_dir, REL)
    if not os.path.isfile(path):
        return fail("لا ملفَّ esbuild.browser.mts: " + path)
    src = io.open(path, encoding="utf-8", newline="").read()

    if DONE.search(src):
        print("  ⏭️ حلُّ مسار file:// مُرقَّعٌ سلفًا")
        return 0

    hits = ANCHOR.findall(src)
    if len(hits) != 1:
        return fail("مِرساةُ `import.meta.resolve(...).replace('file://','')` وقعت "
                    + str(len(hits)) + " مرّةً لا مرّةً واحدة — بنيةُ الملفّ ليست ما قِيس.")

    out = ANCHOR.sub(lambda m: "fileURLToPath(import.meta.resolve(" + m.group("arg") + "))", src)

    if IMPORT_LINE not in out:
        if IMPORT_AFTER not in out:
            return fail("لا سطرَ استيرادِ node:path يُلحَق به الاستيرادُ الجديد.")
        eol = "\r\n" if "\r\n" in out else "\n"
        out = out.replace(IMPORT_AFTER, IMPORT_AFTER + eol + IMPORT_LINE, 1)

    tmp = path + ".mihrab-tmp"
    io.open(tmp, "w", encoding="utf-8", newline="").write(out)
    os.replace(tmp, path)
    print("  ✅ حلُّ مسار file:// صار بـfileURLToPath (بناءُ الويب على ويندوز)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
