#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""هل يقيس حارسُ الموقع الآن ما كان يقيسه المرجع؟ — رفيقُ `same_output.py` لإعادة تنظيم الحارس.

    python tests/docs/same_guard.py [المرجع]        (الافتراضيّ: HEAD) ⇐ شجرة العمل

يستخرج من المرجع ومن شجرة العمل ما يقرؤه `check_site.py` (‏`site/` و`tests/` و`build/` و`docs/`
و`product-overrides/` و`README.md`) إلى مجلّدين مؤقّتين، ويشغّل الحارسَ في كلٍّ منهما، ويشترط:
أن يكون أخضرَ في الطرفين، وأن يتساوى **عددُ الفحوص المُقيَّمة وبصمتُها** — وإلّا سمّى المفاتيحَ
(وسمَ الفحص أو أوّلَ رسالته) التي تغيّر عددُها.

لماذا: تفريغُ المُصابات (`mutation.mjs --dump-failures`) يثبت أنّ **سببَ** احمرار كلّ مُصابٍ لم
يتغيّر، والمُصاباتُ لا تلمس كلَّ فحص. ووحدةٌ لا تُستدعى بعد التقسيم، أو فحصٌ يسقط خلف `need`،
يبقى أخضرَ ويبقى التفريغُ مطابقًا — والعددُ ينقص. وإضعافُ شرطٍ برسالته نفسِها لا يراه هذا ولا
ذاك: ذلك عملُ المُصابات.

الخروج: 0 متساوٍ · 1 مختلف · 2 خطأٌ تشغيليّ (حارسٌ أحمر في أحد الطرفين، أو مرجعٌ بلا بصمة).
"""
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import same_output as so  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

PATHS = ("site", "tests", "build", "docs", "product-overrides", "README.md", ".gitattributes")
BANNER = re.compile(r"\((\d+) فحصًا مُقيَّمًا · البصمة ([0-9a-f]{12})\)")


def run_guard(root, label, tmp):
    keys = os.path.join(tmp, "keys-%s.json" % label)
    r = subprocess.run([sys.executable, os.path.join(root, "tests", "docs", "check_site.py")], cwd=root,
                       capture_output=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8", MIHRAB_GUARD_KEYS=keys))
    out = r.stdout + r.stderr
    if r.returncode != 0:
        raise so.OpError("الحارسُ أحمرُ في %s (خرج %d) — لا يُقارَن أحمر:\n%s" % (label, r.returncode, out[-1500:]))
    m = BANNER.search(out)
    if not m or not os.path.isfile(keys):
        raise so.OpError("‏%s بلا عددٍ وبصمةٍ في لافتة الحارس — أقدمُ من هذه الأداة" % label)
    with open(keys, encoding="utf-8") as f:
        return int(m.group(1)), m.group(2), json.load(f)


def main(argv):
    if len(argv) > 1:
        raise so.OpError("وسائطُ زائدة: %s" % " ".join(argv))
    ref = argv[0] if argv else "HEAD"
    with tempfile.TemporaryDirectory(prefix="mihrab-same-guard-") as tmp:
        _, sha = so.export_ref(ref, os.path.join(tmp, "a"), PATHS)
        so.export_work(os.path.join(tmp, "b"), PATHS)
        la = "%s (%s)" % (ref, sha[:7])
        na, fa, ka = run_guard(os.path.join(tmp, "a"), la, tmp)
        nb, fb, kb = run_guard(os.path.join(tmp, "b"), "شجرة العمل", tmp)
    print("%s — %d فحصًا، البصمة %s" % (la, na, fa))
    print("شجرة العمل — %d فحصًا، البصمة %s" % (nb, fb))
    if (na, fa) == (nb, fb):
        print("✅ الحارسُ يقيس ما كان يقيسه: العددُ والبصمةُ متساويان")
        return 0
    print("❌ تغيّر ما يقيسه الحارس:")
    for k in sorted(set(ka) | set(kb)):
        if ka.get(k, 0) != kb.get(k, 0):
            print("  %s: %d ⇐ %d" % (k, ka.get(k, 0), kb.get(k, 0)))
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except so.OpError as e:
        print("❌ %s" % e)
    except Exception as e:  # noqa: BLE001
        print("❌ خطأٌ تشغيليّ: %s: %s" % (type(e).__name__, e))
    sys.exit(2)
