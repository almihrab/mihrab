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
    # كما يشغّله build.sh: سكربتًا، وخرجُه بترميز ويندوز (cp1252) لا يحمل العربيّة — أسقط
    # بناءَي ويندوز والبياناتُ مكتوبة.
    import subprocess
    with tempfile.TemporaryDirectory() as t:
        env = dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONUTF8="0")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "build", "lib", "help_data.py"), t],
                           capture_output=True, env=env)
        wrote = all(os.path.isfile(os.path.join(t, help_data.DATA_DIR, f)) for f in help_data.FILES)
        case("يعمل سكربتًا وخرجُه بترميز cp1252", r.returncode == 0 and wrote,
             "خرج %d، والملفّان %s — %s" % (r.returncode, "كُتبا" if wrote else "لم يُكتبا",
                                           r.stderr.decode("utf-8", "replace")[-200:]))

    # ‏`mismatch`: ما يقرؤه فحصُ الحزمة (L2). البناءُ يصغّر JSON الامتدادات، فالمقارنةُ بالمحتوى.
    import json

    def pack(write):
        t = tempfile.mkdtemp()
        os.makedirs(os.path.join(t, help_data.DATA_DIR))
        for f in help_data.FILES:
            with open(os.path.join(ROOT, "site", "data", f), encoding="utf-8") as fh:
                write(os.path.join(t, help_data.DATA_DIR, f), f, json.load(fh))
        return t

    def dump(path, obj, **kw):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, **kw)

    def items(obj):  # أوّلُ قائمةٍ غيرِ فارغة: ما تعرضه اللوحةُ صفوفًا (‏`terms` في المسرد)
        lst = next((v for k, v in obj.items() if isinstance(v, list) and len(v) >= 2), None)
        assert lst is not None, "لا قائمةَ في البيانات — الجدولُ يقيس الهواء"
        return lst

    def change_value(obj):  # نصٌّ في أوّل صفّ: الشكلُ والأطوالُ كما هي، والمعنى لا
        row = items(obj)[0]
        k = next(k for k, v in row.items() if isinstance(v, str))
        row[k] = row[k] + "!"
        return obj

    def drop_item(obj):
        items(obj).pop()
        return obj

    def swap_items(obj):  # ترتيبُ العرض في اللوحة من ترتيب القائمة
        lst = items(obj)
        lst[0], lst[1] = lst[1], lst[0]
        return obj

    def corrupt(path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{")

    first = help_data.FILES[0]
    MM = [
        ("مصغَّرٌ كما يكتبه البناء يمرّ", lambda p, f, o: dump(p, o, ensure_ascii=False, separators=(",", ":")), True),
        ("العربيّةُ مرمَّزةً بـ\\uXXXX تمرّ", lambda p, f, o: dump(p, o, ensure_ascii=True), True),
        ("ترتيبُ مفاتيح الكائن مختلفًا يمرّ",
         lambda p, f, o: dump(p, dict(reversed(list(o.items()))), ensure_ascii=False), True),
        ("مفتاحٌ محذوفٌ يُمسَك",
         lambda p, f, o: dump(p, {k: v for k, v in o.items() if k != list(o)[-1]} if f == first else o), False),
        ("قيمةٌ مختلفةٌ تُمسَك", lambda p, f, o: dump(p, change_value(o) if f == first else o), False),
        ("عنصرٌ محذوفٌ من قائمةٍ يُمسَك", lambda p, f, o: dump(p, drop_item(o) if f == first else o), False),
        ("تبديلُ عنصرَين في قائمةٍ يُمسَك", lambda p, f, o: dump(p, swap_items(o) if f == first else o), False),
        ("ملفٌّ غائبٌ يُمسَك", lambda p, f, o: None if f == first else dump(p, o), False),
        ("JSON تالفٌ يُمسَك بسببه", lambda p, f, o: corrupt(p) if f == first else dump(p, o), False),
    ]
    for name, write, ok in MM:
        t = pack(write)
        try:
            why = help_data.mismatch(t)
        except Exception as e:  # noqa: BLE001 — انهيارٌ بدل سببٍ مكتوب عطبٌ بذاته
            why = None
            case(name, False, "انهار: %r" % e)
            continue
        finally:
            shutil.rmtree(t, ignore_errors=True)
        case(name, (why == "") == ok, "السبب: %r" % why)
    if fails:
        print("❌ %d عطبًا:" % len(fails))
        for f in fails:
            print("   · %s" % f)
        return 1
    print("╚══ ✅ المولِّدُ يكتب ما في site/data/ ══╝")
    return 0


if __name__ == "__main__":
    sys.exit(main())
