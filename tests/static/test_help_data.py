#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""‏[ON-03] ‏`build/lib/help_data.sync` يكتب بياناتِ المساعدة كما هي في `site/data/` — بالسلوك لا بالنصّ.

    python tests/static/test_help_data.py

‏L0 في `lint_patchers.py` يقيس أنّ كلَّ خطوةِ حزمٍ **تستدعي** المولِّد، و`check_injected.py` (L2)
يقيس الحزمةَ المبنيّة. وهذا يقيس **أنّ المولِّد يفعل الصواب** — بلا بناء، فتحرسه المُصابات.
"""
import filecmp
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "build", "lib"))
import help_data  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

fails = []


def case(name, ok, why=""):
    print(("  ✅ " if ok else "  ❌ ") + name)
    if not ok:
        fails.append("[ON-03/sync] %s%s" % (name, (": " + why) if why else ""))


def main():
    print("╔══ [ON-03] مولِّدُ بيانات المساعدة ══╗")
    case("يكتب ملفَّي اللوحة كلَّيهما", set(help_data.FILES) == {"glossary.json", "keybindings.json"},
         "FILES = %r" % (help_data.FILES,))
    with tempfile.TemporaryDirectory() as t:
        out = help_data.sync(t)
        case("في `data/` داخل الامتداد",
             all(os.path.dirname(p) == os.path.join(t, help_data.DATA_DIR) for p in out) and len(out) == len(help_data.FILES))
        for f in help_data.FILES:
            got = os.path.join(t, help_data.DATA_DIR, f)
            case("‏%s مطابقٌ لـsite/data/ بالبايت" % f,
                 os.path.isfile(got) and filecmp.cmp(got, os.path.join(ROOT, "site", "data", f), shallow=False))
        # نسخةٌ قديمةٌ في الوجهة تُستبدَل، لا تبقى.
        stale = os.path.join(t, help_data.DATA_DIR, help_data.FILES[0])
        with open(stale, "w", encoding="utf-8") as fh:
            fh.write("{}")
        help_data.sync(t)
        case("يستبدل نسخةً قديمةً في الوجهة",
             filecmp.cmp(stale, os.path.join(ROOT, "site", "data", help_data.FILES[0]), shallow=False))
    # مصدرٌ غائبٌ يُفشِل بصوت، لا يكتب لوحةً فارغة.
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as t:
        saved = help_data.SOURCE
        help_data.SOURCE = src
        try:
            help_data.sync(t)
            case("مصدرٌ غائبٌ يُفشِل بصوت", False, "لم يرمِ SystemExit")
        except SystemExit as e:
            case("مصدرٌ غائبٌ يُفشِل بصوت", "[ON-03]" in str(e), str(e))
        finally:
            help_data.SOURCE = saved
    if fails:
        print("❌ %d عطبًا:" % len(fails))
        for f in fails:
            print("   · %s" % f)
        return 1
    print("╚══ ✅ المولِّدُ يكتب ما في site/data/ ══╝")
    return 0


if __name__ == "__main__":
    sys.exit(main())
