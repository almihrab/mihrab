#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""هل يبني الموقعُ الآن ما كان يبنيه المرجع؟ — أداةُ إثباتٍ لتغييرٍ «لا يغيّر السلوك».

    python tests/docs/same_output.py [المرجع]        (الافتراضيّ: HEAD)

١) يستخرج `site/` من المرجع بـ`git archive` إلى مجلّدٍ مؤقّتٍ **ليس فيه غيرُه** — بلا
   worktree ولا checkout، فلا تُمَسّ شجرةُ العمل. ومولِّدٌ يقرأ يومًا من خارج `site/` ينكسر
   هناك بصوت، فلا تُقارَن مدخلاتٌ مختلفةٌ والأداةُ لا تدري.
٢) يبنيه **مرّتين** ببذرتَي تجزئةٍ مختلفتين ويقارنهما: البناءُ حتميّ أو لا يُوثَق بمقارنةٍ بعده.
٣) يبني `site/` من شجرة العمل ويقارن مخرَجَه بمخرَج المرجع ملفًّا ملفًّا بالبايت.
٤) يطبع بصمةَ sha256 للمخرَج كلِّه تُلصَق في وصف طلب الدمج.

الخروج: 0 متطابق · 1 مختلف (أو غيرُ حتميّ) · 2 خطأٌ تشغيليّ. وكلُّ بناءٍ عبر `MIHRAB_SITE_OUT`
إلى مجلّدٍ مؤقّتٍ جديد، فلا يُمَسّ `site/public` ولا مخرَجٌ سابق.
"""
import hashlib
import io
import os
import subprocess
import sys
import tarfile
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def die(msg):
    print("❌ %s" % msg)
    sys.exit(2)


def build(site_dir, out, seed):
    # بذرةُ تجزئةٍ **مختلفة** لكلّ بناء: تثبيتُها يُخفي ما يتبع ترتيبَ المجموعات (`"|".join({…})`
    # كان يقلب ترتيبَ ضغطتين بين بناءين) بدل أن يكشفه.
    env = dict(os.environ, MIHRAB_SITE_OUT=out, PYTHONIOENCODING="utf-8", PYTHONHASHSEED=str(seed))
    r = subprocess.run([sys.executable, os.path.join(site_dir, "build.py")], cwd=site_dir, env=env,
                       capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        die("فشل البناءُ من %s:\n%s" % (site_dir, (r.stdout + r.stderr)[-1500:]))


def tree(out):
    """{المسار النسبيّ: sha256} لكلّ ملفّ."""
    res = {}
    for dp, _dn, fn in os.walk(out):
        for f in fn:
            p = os.path.join(dp, f)
            with open(p, "rb") as fh:
                res[os.path.relpath(p, out).replace(os.sep, "/")] = hashlib.sha256(fh.read()).hexdigest()
    return res


def digest(t):
    h = hashlib.sha256()
    for k in sorted(t):
        h.update(k.encode("utf-8") + b"\0" + t[k].encode("ascii") + b"\n")
    return h.hexdigest()


def diff(a, b, la, lb):
    """سطورُ الفرق بين شجرتين — فارغةٌ إن تطابقتا."""
    out = []
    for k in sorted(set(a) - set(b)):
        out.append("  − %s: في %s وحدَه" % (k, la))
    for k in sorted(set(b) - set(a)):
        out.append("  + %s: في %s وحدَه" % (k, lb))
    for k in sorted(set(a) & set(b)):
        if a[k] != b[k]:
            out.append("  ≠ %s" % k)
    return out


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    r = subprocess.run(["git", "-C", ROOT, "rev-parse", "--verify", "-q", ref + "^{commit}"],
                       capture_output=True, encoding="utf-8")
    if r.returncode != 0:
        die("مرجعٌ غيرُ معروف: %s" % ref)
    sha = r.stdout.strip()
    with tempfile.TemporaryDirectory(prefix="mihrab-same-") as tmp:
        arc = subprocess.run(["git", "-C", ROOT, "archive", "--format=tar", sha, "site"], capture_output=True)
        if arc.returncode != 0:
            die("تعذّر `git archive %s site`: %s" % (ref, arc.stderr.decode("utf-8", "replace")))
        src = os.path.join(tmp, "ref")
        with tarfile.open(fileobj=io.BytesIO(arc.stdout)) as tf:
            tf.extractall(src, filter="data")
        ref_site = os.path.join(src, "site")

        o1, o2, ow = (os.path.join(tmp, n) for n in ("out-ref-1", "out-ref-2", "out-work"))
        build(ref_site, o1, 1)
        build(ref_site, o2, 2)
        t1, t2 = tree(o1), tree(o2)
        nd = diff(t1, t2, "البناء الأوّل", "البناء الثاني")
        if nd:
            print("❌ البناءُ غيرُ حتميّ: بناءان للمرجع %s نفسِه يختلفان — لا يُوثَق بمقارنةٍ بعدهما" % ref)
            print("\n".join(nd[:40]))
            return 1
        build(os.path.join(ROOT, "site"), ow, 3)
        tw = tree(ow)
        d = diff(t1, tw, "المرجع", "شجرة العمل")
        print("المرجع      %s (%s) — %d ملفًّا، البصمة %s" % (ref, sha[:7], len(t1), digest(t1)))
        print("شجرة العمل  %d ملفًّا، البصمة %s" % (len(tw), digest(tw)))
        if d:
            print("❌ المخرَجُ يختلف عن المرجع في %d ملفًّا:" % len(d))
            print("\n".join(d[:60]))
            return 1
        print("✅ متطابق بالبايت — والبناءُ حتميّ (بناءان للمرجع متطابقان)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
