#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""‏`undo_telemetry.sh` يفشل بصمتٍ حين لا يعمل `rg` على المضيف [UNDO-01].

    python build/patch_undo_telemetry.py <‏.upstream/undo_telemetry.sh>

## العطب

سكربتُ VSCodium يستبدل `//*.data.microsoft.com` بـ`//0.0.0.0` في شجرة المصدر قبل
الترجمة، ويبحث عن الملفّات بـ`./node_modules/@vscode/ripgrep/bin/rg` موصولًا بـ`xargs`:

```sh
./node_modules/@vscode/ripgrep/bin/rg … -l "${SEARCH}" . | xargs … replace_with_debug …
```

و`set -ex` بلا `pipefail`: إن لم يعمل `rg` خرج بـ126 والأنبوبُ يأخذ رمزَ `xargs` (صفر)،
فتمضي الخطوةُ خضراءَ ولم تستبدل شيئًا. وهذا بالضبط ما يقع في البناء المتقاطع:
`build.sh` يصدّر `npm_config_arch=$VSCODE_ARCH` (لازمٌ كي لا تُشحَن وحداتٌ `.node`
بمعماريّة المضيف)، فيجلب `@vscode/ripgrep` نسخةَ arm64 على عدّاءٍ x64 ⇒
`Exec format error` ⇒ `undo_telemetry: 0s`. قِيس على `ea497f3`: ويندوز x64 استبدل
472 ملفًّا، وويندوز arm64 من الشجرة نفسِها **صفرًا**.

وفرعُ لينكس غيرِ x64 في المنبع يتّقي هذا بـ`grep -rl` — وفرعا ويندوز وmacOS لا.

## العلاج

قبل التفرّع يُسأل `rg` نفسُه أن يعمل (`--version`)، فإن لم يعمل يُسقَط إلى `grep -rl`
— **الأمرُ نفسُه** الذي يستعمله المنبعُ في فرع لينكس — مع سطرٍ في السجلّ يقول ذلك. ومن
يعمل عنده `rg` لا يرى تغييرًا. والحارسُ على **ما شُحن** هو [UNDO-01] في L2.
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

# نظرةٌ أماميّةٌ لا استهلاك لمحرف الإرجاع [CRLF-02]: الملفُّ يُقرأ ويُكتب بـ`newline=""`.
ANCHOR = re.compile(r'^if \[\[ "\$\{OS_NAME\}" == "linux" \]\]; then(?=\r?$)', re.M)
DONE = re.compile(r'^# \[UNDO-01\] محراب', re.M)


def fail(msg):
    print("❌ " + msg, file=sys.stderr)
    return 1


def main(path):
    if not os.path.isfile(path):
        return fail("لا ملفَّ undo_telemetry.sh: " + path)
    src = io.open(path, encoding="utf-8", newline="").read()

    if DONE.search(src):
        print("  ⏭️ undo_telemetry.sh يسقط إلى grep سلفًا [UNDO-01]")
        return 0

    n = len(ANCHOR.findall(src))
    if n != 1:
        return fail("مِرساةُ «if [[ \"${OS_NAME}\" == \"linux\" ]]» وقعت " + str(n) +
                    " مرّةً لا مرّةً واحدة — بنيةُ undo_telemetry.sh ليست ما قِيس [UNDO-01].")

    nl = "\r\n" if "\r\n" in src else "\n"
    lines = [
        "# [UNDO-01] محراب: `rg` لا يعمل على مضيف البناء المتقاطع (npm_config_arch)، والأنبوبُ",
        "# بلا pipefail يبتلع فشلَه فلا يُستبدَل شيء. نسقط إلى grep كفرع لينكس غيرِ x64.",
        'if ! ./node_modules/@vscode/ripgrep/bin/rg --version >/dev/null 2>&1; then',
        '  echo "[UNDO-01] rg لا يعمل على المضيف — السقوطُ إلى grep"',
        '  grep -rl --exclude-dir=.git -E "${SEARCH}" . | xargs -I {} bash -c \'replace_with_debug "${1}" "{}"\' _ "${REPLACEMENT}"',
        'elif [[ "${OS_NAME}" == "linux" ]]; then',
    ]
    out = ANCHOR.sub(lambda m: nl.join(lines), src, count=1)
    tmp = path + ".mihrab-tmp"
    io.open(tmp, "w", encoding="utf-8", newline="").write(out)
    os.replace(tmp, path)
    print("  ✅ undo_telemetry.sh يسقط إلى grep حين لا يعمل rg [UNDO-01]")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
