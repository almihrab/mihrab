#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""من يحرس `same_output.py`؟ — هذا. [SO-00..06]

أداةُ إثباتٍ خضراءُ دائمًا أسوأُ من غيابها: يُلصَق «متطابق» في طلب الدمج والمخرَجُ تغيّر.
فيُزرَع كلُّ نوعٍ من الفرق في **نسخةٍ** من `site/` داخل مؤقّت (لا يُمَسّ المستودع) ويُشترط
أن تراه الأداة: بايتٌ مغيَّر، وملفٌّ زائد، وثلاثةُ أنواعٍ من عدم الحتميّة (ترتيبُ التجزئة،
والمنطقةُ الزمنيّة، ووضعُ الترميز) — ورمزُ الخروج 1 لا نصُّ الرسالة وحده (CI يقرأ الرمز).
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import same_output as so  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

fails = []


def expect(tag, cond, msg):
    if cond:
        print("  ✅ [%s] %s" % (tag, msg))
    else:
        fails.append("[%s] %s" % (tag, msg))


def variant(base, tmp, name, edit):
    """نسخةٌ من `site/` يُطبَّق عليها edit(المسار)."""
    d = os.path.join(tmp, name, "site")
    shutil.copytree(base, d)
    edit(d)
    return d


def plant_build(code):
    """يزرع سطرًا في `write()` من build.py: كلُّ صفحةٍ تحمل ما يحسبه."""
    def edit(d):
        p = os.path.join(d, "build.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        anchor = "def write(path, text):\n"
        assert src.count(anchor) == 1, "مرساةُ الزرع في build.py تغيّرت: %r" % anchor
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(src.replace(anchor, anchor + "    " + code + "\n"))
    return edit


def append(rel, data):
    def edit(d):
        with open(os.path.join(d, rel), "ab") as f:
            f.write(data)
    return edit


def main():
    print("╔══ [SO] حارسُ أداة الإثبات same_output.py ══╗")
    with tempfile.TemporaryDirectory(prefix="mihrab-so-test-") as tmp:
        base = so.export_work(os.path.join(tmp, "base"))

        # المرجعُ ببناءين (للسرعة)، وشجرةُ العمل **بعددها الافتراضيّ** `WORK_BUILDS`: هو ما
        # يستعمله سطرُ الأوامر، وإنقاصُه إلى بناءٍ واحدٍ يجب أن يحمرّ هنا.
        def cmp(a, b):
            return so.compare(a, b, os.path.join(tmp, "w-%d" % len(os.listdir(tmp))), "أ", "ب", 2)

        rc, lines = cmp(base, variant(base, tmp, "same", lambda d: None))
        expect("SO-00", rc == 0, "نسختان متطابقتان ⇒ 0 (%s)" % lines[-1])

        rc, lines = cmp(base, variant(base, tmp, "byte", append("assets/mihrab-docs.css", b"\n")))
        expect("SO-01", rc == 1 and "  ≠ assets/mihrab-docs.css" in lines,
               "بايتٌ زائدٌ في CSS ⇒ «≠ assets/mihrab-docs.css» وخروج 1")

        rc, lines = cmp(base, variant(base, tmp, "extra", append("assets/so-extra.txt", b"x")))
        expect("SO-02", rc == 1 and any(l.startswith("  + assets/so-extra.txt") for l in lines),
               "ملفٌّ زائدٌ في المخرَج ⇒ «+ assets/so-extra.txt» وخروج 1")

        # ترتيبُ التجزئة في الطرفين (المرجعُ وشجرةُ العمل يُبنيان كلٌّ مرّاتٍ)، والبيئتان في الأوّل.
        for tag, code, what, sides in (
            ("SO-03", "text += '<!--%d-->' % hash('محراب')", "ترتيبُ التجزئة", "ab"),
            ("SO-05", "import time; text += time.strftime('%Y-%m-%d')", "المنطقةُ الزمنيّة", "a"),
            ("SO-06", "text += str(sys.flags.utf8_mode)", "وضعُ الترميز", "a"),
        ):
            nd = variant(base, tmp, tag, plant_build(code))
            ok = True
            for side in sides:
                rc, ln = cmp(nd, base) if side == "a" else cmp(base, nd)
                ok = ok and rc == 1 and "غيرُ حتميّ" in ln[0]
            expect(tag, ok, "بناءٌ يتبع %s يُكشف غيرَ حتميٍّ (%s)" % (what, "في الطرفين" if sides == "ab" else "في المرجع"))

        # رمزُ الخروج من سطر الأوامر نفسِه، لا من الدالّة.
        r = subprocess.run([sys.executable, os.path.join(HERE, "same_output.py"), "--dirs", base,
                            os.path.join(tmp, "byte", "site")],
                           capture_output=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        expect("SO-04", r.returncode == 1 and "≠ assets/mihrab-docs.css" in r.stdout,
               "‏--dirs على نسختين مختلفتين يخرج 1 (خرج %s)" % r.returncode)

    if fails:
        print("❌ %d عطبٌ في أداة الإثبات:" % len(fails))
        for f in fails:
            print("   · %s" % f)
        return 1
    print("╚══ ✅ same_output يرى البايتَ والملفَّ الزائدَ وعدمَ الحتميّة، ويخرج بالرمز الصحيح ══╝")
    return 0


if __name__ == "__main__":
    sys.exit(main())
