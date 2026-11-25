#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""هل يبني الموقعُ الآن ما كان يبنيه المرجع؟ — أداةُ إثباتٍ لتغييرٍ «لا يغيّر السلوك».

    python tests/docs/same_output.py [المرجع]           المرجع (HEAD افتراضًا) ⇐ شجرة العمل
    python tests/docs/same_output.py <مرجع١> <مرجع٢>     إيداعان، بلا شجرة العمل
    python tests/docs/same_output.py --dirs <أ> <ب>      مجلّدا `site` (لاختبار الأداة نفسِها)

١) **كلُّ طرفٍ يُبنى في مجلّدٍ مؤقّتٍ ليس فيه غيرُ `site/`**: المرجعُ بـ`git archive`، وشجرةُ
   العمل بنسخ ما يراه git فيها (متتبَّعًا أو جديدًا غيرَ مُهمَل). فمولِّدٌ يقرأ يومًا من خارج
   ‏`site/` ينكسر بصوتٍ في الطرفين، لا يقارن مدخلاتٍ مختلفةً والأداةُ لا تدري.
٢) **كلُّ طرفٍ يُبنى مرّاتٍ في بيئاتٍ متباينة** ويُشترط تطابقُها: بذورُ تجزئةٍ مختلفة (ترتيبُ
   المجموعات)، ومنطقتان زمنيّتان بينهما ‎26‎ ساعة (التاريخُ نفسُه يتغيّر)، و`PYTHONUTF8`
   مُطفأٌ ومُشعَل (‏`open()` بلا ترميزٍ يقرأ بمحلّيّة الجهاز). ستُّ بذورٍ للمرجع: عدمُ حتميّةٍ
   ثنائيٌّ (ترتيبٌ من اثنين) يفلت من بذرتين ثابتتين في نصف الحالات **ودائمًا**، ومن ستٍّ
   باحتمال ‎1/32‎. وما لا تبلغه البيئة (‏`time.time()`، ‏`random`) يمنعه [DET-01] في check_site.
٣) يقارن المخرَجين ملفًّا ملفًّا بالبايت، والمجلّداتِ الفارغةَ معها، ويطبع بصمةَ sha256.

الخروج: 0 متطابق · 1 مختلف (أو غيرُ حتميّ) · 2 خطأٌ تشغيليّ — **وكلُّ استثناءٍ غيرِ متوقَّعٍ 2**،
فلا يُقرأ عطبُ الأداة «مختلفًا». ولا يُمَسّ `site/public` ولا شجرةُ العمل.
"""
import hashlib
import io
import os
import shutil
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
REF_BUILDS = 6
WORK_BUILDS = 2


class OpError(Exception):
    """خطأٌ تشغيليٌّ (لا فرق): خروج 2."""


def env_for(i, seed):
    """بيئةُ البناء رقم i: البذرةُ تتغيّر دائمًا، والمنطقةُ والترميزُ يتناوبان."""
    return {
        "PYTHONHASHSEED": str(seed),
        "TZ": ("AAA-14" if i % 2 == 0 else "BBB+12"),
        "PYTHONUTF8": ("0" if i % 2 == 0 else "1"),
    }


def build(site_dir, out, env_extra):
    env = dict(os.environ, MIHRAB_SITE_OUT=out, PYTHONIOENCODING="utf-8", **env_extra)
    r = subprocess.run([sys.executable, os.path.join(site_dir, "build.py")], cwd=site_dir, env=env,
                       capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise OpError("فشل البناءُ من %s:\n%s" % (site_dir, (r.stdout + r.stderr)[-1500:]))


def tree(out):
    """{المسار النسبيّ: sha256} لكلّ ملفّ، و`<مجلّد>/`: «dir» لكلّ مجلّدٍ فارغ."""
    res = {}
    for dp, dn, fn in os.walk(out):
        rel = os.path.relpath(dp, out).replace(os.sep, "/")
        if not dn and not fn and rel != ".":
            res[rel + "/"] = "dir"
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


def stable_tree(site_dir, tmp, label, n, seed0):
    """يبني n مرّةً في بيئاتٍ متباينة ⇒ (الشجرة، سطورُ عدم الحتميّة أو [])."""
    first = None
    for i in range(n):
        out = os.path.join(tmp, "out-%s-%d" % (label, i))
        build(site_dir, out, env_for(i, seed0 + i))
        t = tree(out)
        if first is None:
            first = t
            continue
        nd = diff(first, t, "البناء 1", "البناء %d %s" % (i + 1, env_for(i, seed0 + i)))
        if nd:
            return first, nd
    return first, []


def compare(site_a, site_b, tmp, label_a, label_b, n_a=REF_BUILDS, n_b=WORK_BUILDS):
    """⇒ (رمز الخروج، السطور). يُستورَد في `test_same_output.py`."""
    lines = []
    ta, nd = stable_tree(site_a, tmp, "a", n_a, 1)
    if nd:
        return 1, ["❌ البناءُ غيرُ حتميّ في %s — لا يُوثَق بمقارنةٍ بعده:" % label_a] + nd[:40]
    tb, nd = stable_tree(site_b, tmp, "b", n_b, 101)
    if nd:
        return 1, ["❌ البناءُ غيرُ حتميّ في %s — لا يُوثَق بمقارنةٍ بعده:" % label_b] + nd[:40]
    d = diff(ta, tb, label_a, label_b)
    lines.append("%s — %d ملفًّا، البصمة %s" % (label_a, len(ta), digest(ta)))
    lines.append("%s — %d ملفًّا، البصمة %s" % (label_b, len(tb), digest(tb)))
    if d:
        lines.append("❌ المخرَجُ يختلف في %d موضعًا:" % len(d))
        lines.extend(d[:60])
        return 1, lines
    lines.append("✅ متطابق بالبايت — والبناءُ حتميّ (%d بناءً و%d، في بيئاتٍ متباينة)" % (n_a, n_b))
    return 0, lines


def git(*args, binary=False):
    r = subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True,
                       **({} if binary else {"encoding": "utf-8"}))
    if r.returncode != 0:
        err = r.stderr.decode("utf-8", "replace") if binary else r.stderr
        raise OpError("git %s: %s" % (" ".join(args), err.strip()))
    return r.stdout


def export_ref(ref, dest):
    """‏`site/` من المرجع إلى dest/site ⇒ (المسار، sha)."""
    try:
        sha = git("rev-parse", "--verify", "-q", ref + "^{commit}").strip()
    except OpError:
        raise OpError("مرجعٌ غيرُ معروف: %s" % ref)
    data = git("archive", "--format=tar", sha, "site", binary=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        try:
            tf.extractall(dest, filter="data")
        except TypeError:
            raise OpError("‏`tarfile` بلا `filter=` — يلزم بايثون ≥ 3.12 (أو تصحيحٌ خلفيّ)")
    return os.path.join(dest, "site"), sha


def export_work(dest):
    """ما يراه git في `site/` من شجرة العمل (متتبَّعًا أو جديدًا غيرَ مُهمَل) إلى dest/site."""
    names = [n for n in git("ls-files", "-co", "--exclude-standard", "-z", "--", "site").split("\0") if n]
    for rel in names:
        src = os.path.join(ROOT, rel)
        if not os.path.isfile(src):      # محذوفٌ لم يُودَع بعد
            continue
        dst = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    return os.path.join(dest, "site")


def main(argv):
    with tempfile.TemporaryDirectory(prefix="mihrab-same-") as tmp:
        if argv[:1] == ["--dirs"]:
            if len(argv) != 3:
                raise OpError("‏--dirs <أ> <ب>")
            a = shutil.copytree(argv[1], os.path.join(tmp, "a", "site"))
            b = shutil.copytree(argv[2], os.path.join(tmp, "b", "site"))
            rc, lines = compare(a, b, tmp, "أ", "ب")
        elif len(argv) <= 2:
            ref = argv[0] if argv else "HEAD"
            a, sa = export_ref(ref, os.path.join(tmp, "a"))
            if len(argv) == 2:
                b, sb = export_ref(argv[1], os.path.join(tmp, "b"))
                lb = "%s (%s)" % (argv[1], sb[:7])
            else:
                b = export_work(os.path.join(tmp, "b"))
                lb = "شجرة العمل"
                if git("status", "--porcelain", "--", "site").strip():
                    print("⚠️ في `site/` ما لم يُودَع — البصمةُ بصمةُ شجرة العمل لا إيداعٍ بعينه")
            rc, lines = compare(a, b, tmp, "%s (%s)" % (ref, sa[:7]), lb)
        else:
            raise OpError("وسائطُ زائدة: %s" % " ".join(argv))
    print("\n".join(lines))
    return rc


def _run(argv):
    try:
        return main(argv)
    except OpError as e:
        print("❌ %s" % e)
    except Exception as e:  # noqa: BLE001 — عطبُ الأداة ليس «مختلفًا»
        print("❌ خطأٌ تشغيليّ: %s: %s" % (type(e).__name__, e))
    return 2


if __name__ == "__main__":
    sys.exit(_run(sys.argv[1:]))
