#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوّابةُ النشر [OUT-02] مع `--no-build`: مخرَجٌ ليس من هذا المصدر يُرفَض.

الحارسُ في وضعه العاديّ يبني `site/public/` ثمّ يقارنه ببناءٍ نظيف — فكلُّ مُصابٍ في
`mutants.json` يصل [OUT-02] **بعد بناء**، ولا يصل أبدًا الفرعَ الذي وُضع له: `deploy_site.sh`
يشغّله بـ`--no-build` على مخرَجٍ قائم. هنا يُنسخ المستودعُ إلى مجلّدٍ مؤقّت، ويُبنى، ثمّ يُعطَب
المخرَجُ (بايتٌ مختلف، ملفٌّ ناقص، ملفٌّ زائد، مجلّدٌ موصول) ومرّةً بمصدرٍ تغيّر بعد البناء،
ويُشترط أن يحمرّ `check_site.py --no-build` على السطر الصحيح — وأن يخضرّ على المخرَج السليم.
"""
import os
import shutil
import subprocess
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
ENV.pop("MIHRAB_SITE_OUT", None)


# ما يقرؤه `check_site.py` (كما في `same_guard.py`) — لا المستودعُ كلُّه.
PATHS = ("site", "tests", "build", "docs", "product-overrides", "README.md", ".gitattributes")


def tracked_files():
    r = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z", "--", *PATHS], cwd=ROOT,
                       capture_output=True, check=True)
    return [p for p in r.stdout.decode("utf-8").split("\0") if p]


def run(root, *args):
    r = subprocess.run([sys.executable, os.path.join(root, "tests", "docs", "check_site.py"), *args],
                       cwd=root, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def main():
    fails = []
    with tempfile.TemporaryDirectory(prefix="mihrab-nobuild-") as tmp:
        root = os.path.join(tmp, "repo")
        for rel in tracked_files():
            if rel.replace(os.sep, "/").startswith("site/public/"):
                continue
            src = os.path.join(ROOT, rel)
            if not os.path.isfile(src):
                continue
            dst = os.path.join(root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        pub = os.path.join(root, "site", "public")
        rc, out = run(root)  # يبني المخرَجَ ويتحقّق أنّ الحارسَ أخضرُ أصلًا
        if rc:
            print("❌ الحارسُ أحمرُ على النسخة السليمة — لا يُقاس شيء:\n" + out[-800:])
            return 1
        snap = os.path.join(tmp, "public0")
        shutil.copytree(pub, snap)

        def restore():
            shutil.rmtree(pub)
            shutil.copytree(snap, pub)

        def case(name, tamper, expect):
            undo = tamper()
            rc, out = run(root, "--no-build")
            ok = rc != 0 and expect in out
            print(("  ✅ [OUT-02] " if ok else "  ❌ [OUT-02] ") + name)
            if not ok:
                fails.append("%s: خرج %d، و«%s» %s" % (name, rc, expect,
                             "حاضر" if expect in out else "غائبٌ عن الخرج"))
            if undo:
                undo()
            restore()

        def _append(p, data):
            with open(p, "ab") as f:
                f.write(data)

        # الضابط: المخرَجُ السليمُ أخضرُ مع --no-build (وإلّا فكلُّ حالةٍ أدناه «تنجح» زورًا)
        rc, out = run(root, "--no-build")
        if rc:
            fails.append("المخرَجُ السليمُ أحمرُ مع --no-build: " + out[-400:])

        case("بايتٌ مختلف في public/assets/docs.js",
             lambda: _append(os.path.join(pub, "assets", "docs.js"), b" "),
             "`public/assets/docs.js` يخالف البناءَ النظيفَ بالبايت")
        case("ملفٌّ ناقص (404.html)",
             lambda: os.remove(os.path.join(pub, "404.html")),
             "`public/404.html` غائب")
        case("ملفٌّ زائد (stray.txt)",
             lambda: _append(os.path.join(pub, "stray.txt"), b"x"),
             "`public/stray.txt` زائد")

        # أوّلُ صفحةِ محتوى لا اسمٌ بعينه: صفحةٌ تُحذف أو تُسمّى من جديد لا تكسر الاختبار.
        _content = os.path.join(root, "site", "content")
        _stem = sorted(f for f in os.listdir(_content) if f.endswith(".md"))[0][:-3]
        md = os.path.join(_content, _stem + ".md")
        with open(md, "rb") as f:
            md0 = f.read()

        def stale_src():
            _append(md, "\nفقرةٌ أُضيفت بعد البناء.\n".encode("utf-8"))
            def undo():
                with open(md, "wb") as f:
                    f.write(md0)
            return undo
        case("مصدرٌ تغيّر بعد البناء (مخرَجٌ بائت)", stale_src,
             "`public/%s/index.html` يخالف البناءَ النظيفَ بالبايت" % _stem)

        # وصلةُ مجلّدٍ إلى خارج المستودع: ‏`tar` يحزمها كما هي فيُنشَر ما وراءها.
        ext = os.path.join(tmp, "outside")
        os.makedirs(ext)
        with open(os.path.join(ext, "k.txt"), "w", encoding="utf-8") as f:
            f.write("x")
        try:  # ويندوز بلا وضع المطوّر لا ينشئ وصلة؛ CI (ubuntu) ينشئها
            os.symlink(ext, os.path.join(tmp, "probe"), target_is_directory=True)
            can_link = True
        except OSError:
            can_link = False
        if can_link:
            case("مجلّدٌ موصول (public/linked ← خارج المستودع)",
                 lambda: os.symlink(ext, os.path.join(pub, "linked"), target_is_directory=True),
                 "`linked` وصلةٌ في المخرَج")
        else:
            print("  ⚠️ [OUT-02] الوصلة: لا تُنشأ هنا — تُقاس في CI")

    if fails:
        print("❌ بوّابةُ النشر [OUT-02] لا ترفض مخرَجًا ليس من هذا المصدر:")
        for f in fails:
            print("   · " + f)
        return 1
    print("✅ بوّابةُ النشر [OUT-02] مع --no-build ترفض البايتَ المختلفَ والناقصَ والزائدَ والبائت.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
