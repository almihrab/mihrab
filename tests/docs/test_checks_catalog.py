#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[GRD-03] جداولُ الوسوم في `site/guide/checks.md` هي ما يُولَّد من الحارس — بلا تشغيله.

    python tests/docs/test_checks_catalog.py

لكلّ وحدةٍ في `site_guard/`: كلُّ وسمٍ في اسم قسمٍ موصوفٌ في `TAGS`، ولا وصفَ لوسمٍ بلا قسم، وكلُّ
قسمٍ بلا وسمٍ له وصف؛ وجدولُها في `checks.md` بين علامتيه مطابقٌ لما يكتبه
`python tests/docs/check_site.py --list --write`. وكلُّ وحدةٍ لها أقسامٌ في `SECTIONS` لها جدول.
"""
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

_argv, sys.argv = sys.argv, ["check_site.py"]
import check_site  # noqa: E402
from site_guard import catalog  # noqa: E402
sys.argv = _argv

MD = os.path.join(os.path.dirname(os.path.dirname(HERE)), "site", "guide", "checks.md")


def main():
    print("╔══ [GRD-03] جداولُ الوسوم في checks.md ══╗")
    with open(MD, encoding="utf-8") as f:
        md = f.read()
    fails = []
    mods_with_sections = {s.__module__ for s in check_site.SECTIONS}
    listed = {m.__name__ for m in check_site.CATALOG}
    for name in sorted(mods_with_sections - listed):
        fails.append("%s له أقسامٌ وليس في `CATALOG` — لا جدولَ له" % name)
    known = {t for m in check_site.CATALOG for t in getattr(m, "TAGS", {})}
    for m in check_site.CATALOG:
        key = m.__name__.rsplit(".", 1)[1]
        fails += catalog.problems(m, check_site.SECTIONS, known)
        got = catalog.block(md, key)
        if catalog.marks(md, key) > 1:
            fails.append("علامتا «%s» مكرّرتان في checks.md — الثانيةُ تتقادم" % key)
        if got is None:
            fails.append("لا علامتَي «%s» في checks.md" % key)
        elif got.strip() != catalog.render(m, check_site.SECTIONS).strip():
            fails.append("جدولُ «%s» في checks.md يخالف ما يُولَّد" % key)
    if fails:
        print("❌ %d عطبًا:" % len(fails))
        for x in fails:
            print("   · [GRD-03] %s" % x)
        print("   شغّل: python tests/docs/check_site.py --list --write")
        return 1
    print("╚══ ✅ %d جدولًا كما يُولَّد ══╝" % len(check_site.CATALOG))
    return 0


if __name__ == "__main__":
    sys.exit(main())
