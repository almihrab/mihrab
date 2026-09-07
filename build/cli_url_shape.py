#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""شكلُ العناوين التي يطلبها `mihrab-tunnel` — **مُشتقٌّ من الشجرة المُرقَّعة**.

    python build/cli_url_shape.py <‏.upstream/vscode/cli/src/update_service.rs>

يطبع سطرَي `KEY=value` يقرؤهما `build/build.sh` و`build/publish_server.sh`:

    MANIFEST_SUFFIX=user/latest.json
    ARTIFACT_TEMPLATE={app}-reh-web-{os}-{arch}-{name}.tar.gz

## لماذا يُشتقّ ولا يُكتَب

كُتِب المسارُ بيدٍ في موضعَين، مأخوذًا من رقعة `40-cli-use-reh-archive.patch`:

    "{}/{}/{}/{}/latest.json"

**ثمّ تعدّله رقعةٌ ثانية.** `patches/windows/41-cli-fix-update-url.patch` تحوّله إلى
`"{}/{}/{}/{}/user/latest.json"`، و`prepare_vscode.sh` يطبّق `patches/$OS_NAME/`
فعلًا — فبناءُ ويندوز (منصّتُنا الأولى) يطلب `…/stable/win32/x64/user/latest.json`،
ولا `user` في مِجَسّنا ولا في ناشرنا.

وأثرُه أنّ الحلقةَ الموصوفةَ بأنّها «تُغلِق نفسَها» **لا تُغلَق أبدًا**: يُرفَع الأثرُ،
ويقيس البناءُ التالي عنوانًا لا يطلبه أحد، فيخبز وجهةً يردّ عليها الخادمُ 404 عند
المستخدم وحدَه. وهو **بعينه** الصنفُ الذي كُتِبت السلسلةُ كلُّها لمنعه: عنوانٌ صحيحُ
الشكل يبدو مُصلَحًا في القراءة ويكسر في التشغيل.

والخطأُ منهجيٌّ لا سهو: **قُرِئت الرقعةُ ولم تُقرأ الشجرةُ المُجهَّزة**. فالعلاجُ ألّا
يُقرأ الشكلُ من رقعةٍ ولا من ذاكرة، بل من الملفّ الذي يُصرَّف منه الثنائيُّ نفسُه.
ولينكس/ماك بلا `user` — والاشتقاقُ يعطي كلَّ منصّةٍ شكلَها بلا فرعٍ مكتوبٍ عندنا.
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

# ‏`get_latest_commit` تبني عنوانَ المانيفست، و`get_download_url` عنوانَ الأثر.
# ويُلتقَط القالبان بنصَّيهما الحرفيَّين لا بموضعهما: إعادةُ ترتيبٍ في المنبع
# تُبقي الفحصَ عاملًا، وتغيُّرُ الشكل نفسِه هو ما يجب أن يُرى.
MANIFEST = re.compile(r'"\{\}((?:/\{\})*)((?:/[A-Za-z0-9_.-]+)*)/latest\.json"')
ARTIFACT = re.compile(r'"\{\}/download/\{\}/\{\}-reh-web-\{\}-\{\}-\{\}\.tar\.gz"')


def fail(msg):
    print("❌ " + msg, file=sys.stderr)
    return 1


def main(path):
    if not os.path.isfile(path):
        return fail("لا ملفَّ update_service.rs: " + path)
    src = io.open(path, encoding="utf-8", newline="").read()

    m = MANIFEST.search(src)
    if not m:
        return fail("لا قالبَ مانيفستٍ في " + os.path.basename(path) + " — بنيةُ "
                    "`get_latest_commit` ليست ما قِيس. لا تُخمَّن الوجهة: اقرأ "
                    "الدالّةَ وحدِّث هذا المرقِّع، فالعنوانُ الخاطئ يردّ 404 عند "
                    "المستخدم وحدَه.")
    # المقاطعُ الحرفيّةُ بين آخرِ نائبٍ و`latest.json` (‏`/user` على ويندوز، ولا شيءَ سواه).
    lit = m.group(2).strip("/")
    suffix = (lit + "/latest.json") if lit else "latest.json"

    if not ARTIFACT.search(src):
        return fail("لا قالبَ أثرٍ في " + os.path.basename(path) + " — واسمُ الأثر "
                    "الذي يحزمه البناءُ يجب أن يطابق ما يطلبه الـCLI حرفيًّا.")

    print("MANIFEST_SUFFIX=" + suffix)
    print("ARTIFACT_TEMPLATE={app}-reh-web-{os}-{arch}-{name}.tar.gz")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
