#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""من يحرس `same_output.py`؟ — هذا. [SO-01..12]

أداةُ إثباتٍ خضراءُ دائمًا أسوأُ من غيابها: يُلصَق «متطابق» في طلب الدمج والمخرَجُ تغيّر.
فيُبنى **مستودعُ git مؤقّت** فيه نسخةٌ من `site/` ومن الأداة نفسِها (جذرُها يُستنتَج من موضعها)،
وتُشغَّل الأداةُ **من سطر الأوامر** — المسارَ الذي يُستعمل فعلًا: المرجعُ مقابلَ شجرة العمل،
ومرجعان. ويُزرَع فيه كلُّ نوعٍ من الفرق: بايتٌ مغيَّر، وملفٌّ جديدٌ غيرُ متتبَّع، وملفٌّ محذوف —
ويُشترط **رمزُ الخروج** لا نصُّ الرسالة وحده (CI يقرأ الرمز). ثمّ عدمُ الحتميّة بأنواعه الثلاثة
(ترتيبُ التجزئة، والمنطقةُ الزمنيّة، ووضعُ الترميز) على الدالّة مباشرةً، والثوابتُ نفسُها.

لا يُمَسّ المستودعُ الحقيقيّ: كلُّ شيءٍ في مؤقّت.
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
CSS = "assets/mihrab-docs.css"


def expect(tag, cond, msg):
    if cond:
        print("  ✅ [%s] %s" % (tag, msg))
    else:
        fails.append("[%s] %s" % (tag, msg))


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("git %s: %s" % (" ".join(args), r.stderr))
    return r.stdout


def make_repo(tmp, base):
    """مستودعٌ مؤقّت: ‏`site/` و`tests/docs/same_output.py` و`.gitattributes`، في إيداعٍ واحد."""
    repo = os.path.join(tmp, "repo")
    shutil.copytree(base, os.path.join(repo, "site"))
    os.makedirs(os.path.join(repo, "tests", "docs"))
    shutil.copyfile(os.path.join(HERE, "same_output.py"), os.path.join(repo, "tests", "docs", "same_output.py"))
    shutil.copyfile(os.path.join(so.ROOT, ".gitattributes"), os.path.join(repo, ".gitattributes"))
    git(repo, "init", "-q")
    # إعداداتُ هذا المستودع المؤقّت وحدَه: هويّةٌ للإيداع، وبلا تحويلِ نهايات أسطر.
    for k, v in (("user.name", "test"), ("user.email", "test@example.invalid"),
                 ("core.autocrlf", "false"), ("commit.gpgsign", "false")):
        git(repo, "config", k, v)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    return repo


def cli(repo, *args):
    """الأداةُ من سطر الأوامر في المستودع المؤقّت ⇒ (رمز الخروج، الخرج)."""
    r = subprocess.run([sys.executable, os.path.join(repo, "tests", "docs", "same_output.py"), "--builds", "2"]
                       + list(args), capture_output=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return r.returncode, r.stdout + r.stderr


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


def main():
    print("╔══ [SO] حارسُ أداة الإثبات same_output.py ══╗")
    expect("SO-11", so.BUILDS >= 8 and so.MIN_BUILDS >= 2,
           "ثماني بناءاتٍ لكلّ طرفٍ افتراضًا (BUILDS=%d)، وبناءان أدنى (MIN_BUILDS=%d)" % (so.BUILDS, so.MIN_BUILDS))

    with tempfile.TemporaryDirectory(prefix="mihrab-so-test-") as tmp:
        base = so.export_work(os.path.join(tmp, "base"))
        repo = make_repo(tmp, base)
        site = os.path.join(repo, "site")

        rc, out = cli(repo, "HEAD")
        expect("SO-07", rc == 0 and "✅ متطابق" in out, "المرجعُ وشجرةُ عملٍ نظيفة ⇒ 0 (خرج %s)" % rc)

        with open(os.path.join(site, CSS), "ab") as f:
            f.write(b"\n")
        rc, out = cli(repo, "HEAD")
        expect("SO-01", rc == 1 and "≠ " + CSS in out, "بايتٌ مغيَّرٌ في شجرة العمل ⇒ «≠ %s» وخروج 1 (خرج %s)" % (CSS, rc))
        rc2, out2 = cli(repo, "HEAD", "HEAD")
        git(repo, "commit", "-q", "-am", "byte")
        rc3, out3 = cli(repo, "HEAD~1", "HEAD")
        expect("SO-04", rc2 == 0 and rc3 == 1 and "≠ " + CSS in out3,
               "مرجعان: ‏HEAD HEAD ⇒ 0 وشجرةُ العمل متّسخة (خرج %s)، وHEAD~1 HEAD ⇒ 1 (خرج %s)" % (rc2, rc3))

        with open(os.path.join(site, "assets", "so-extra.txt"), "wb") as f:
            f.write(b"x")
        rc, out = cli(repo, "HEAD")
        expect("SO-02", rc == 1 and "+ assets/so-extra.txt" in out,
               "ملفٌّ جديدٌ غيرُ متتبَّعٍ في site/ يُنسخ ويُرى «+» وخروج 1 (خرج %s)" % rc)
        # يُودَع ثمّ يُحذف من شجرة العمل: محذوفٌ لم يُودَع حذفُه (أصلٌ يُنسخ كما هو، فالبناءُ لا ينكسر).
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "extra")
        os.remove(os.path.join(site, "assets", "so-extra.txt"))
        rc, out = cli(repo, "HEAD")
        expect("SO-08", rc == 1 and "− assets/so-extra.txt" in out,
               "ملفٌّ محذوفٌ من شجرة العمل ⇒ «− assets/so-extra.txt» وخروج 1 (خرج %s)" % rc)
        git(repo, "checkout", "-q", "--", "site")

        bad = [cli(repo, "nosuchref")[0], cli(repo, "--dirs", os.path.join(tmp, "nope"), site)[0],
               cli(repo, "HEAD", "--builds", "1")[0], cli(repo, "a", "b", "c")[0]]
        expect("SO-10", bad == [2, 2, 2, 2],
               "مرجعٌ مجهول، و--dirs على غير site، و--builds 1، ووسائطُ زائدة ⇒ 2 لا «مختلف» (%s)" % bad)

        # عدمُ الحتميّة على الدالّة: بناءان لكلّ طرفٍ للسرعة.
        def variant(name, edit):
            d = os.path.join(tmp, name, "site")
            shutil.copytree(base, d)
            edit(d)
            return d

        def cmp(a, b):
            return so.compare(a, b, os.path.join(tmp, "w-%d" % len(os.listdir(tmp))), "أ", "ب", 2)

        for tag, code, what, sides in (
            ("SO-03", "text += '<!--%d-->' % hash('محراب')", "ترتيبُ التجزئة", "ab"),
            ("SO-05", "import time; text += time.strftime('%Y-%m-%d')", "المنطقةُ الزمنيّة", "a"),
            ("SO-06", "text += str(sys.flags.utf8_mode)", "وضعُ الترميز", "a"),
        ):
            nd = variant(tag, plant_build(code))
            ok = True
            for side in sides:
                rc, ln = cmp(nd, base) if side == "a" else cmp(base, nd)
                ok = ok and rc == 1 and "غيرُ حتميّ" in ln[0]
            expect(tag, ok, "بناءٌ يتبع %s يُكشف غيرَ حتميٍّ (%s)" % (what, "في الطرفين" if sides == "ab" else "في الأوّل"))

        e = os.path.join(tmp, "empty-out")
        os.makedirs(os.path.join(e, "x"))
        expect("SO-12", so.tree(e) == {"x/": "dir"}, "مجلّدٌ فارغٌ في المخرَج يُحصى (%r)" % so.tree(e))

    if fails:
        print("❌ %d عطبٌ في أداة الإثبات:" % len(fails))
        for f in fails:
            print("   · %s" % f)
        return 1
    print("╚══ ✅ same_output يرى البايتَ والجديدَ والمحذوفَ وعدمَ الحتميّة، ويخرج بالرمز الصحيح ══╝")
    return 0


if __name__ == "__main__":
    sys.exit(main())
