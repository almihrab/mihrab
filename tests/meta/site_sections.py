#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""أيُّ أقسام حارس الموقع يُحمِّرها كلُّ مُصاب — قياسُ ما يعلنه حقلُ `sec` في mutants.json.

    python tests/meta/site_sections.py              # كلُّ مُصابٍ يحمل `sec`: أيُحمِّر قسمَه؟
    python tests/meta/site_sections.py <id>…        # مُصاباتٌ بعينها (ولو بلا `sec`)، لكتابة `sec` جديد

لماذا: ‏`mutation.mjs` يشترط ساكنًا أن يكون لكلّ قسمٍ في SECTIONS مُصابٌ يحمل `sec` أو إعلان،
ولا يستطيع أن يرى **أيَّ قسمٍ** احمرّ — فالربطُ يُقاس هنا: يُلفّ كلُّ قسمٍ فيُسجَّل من أضاف عطبًا
(‏`sNN`)، ومن أوقف الحارسَ بـ`need` (‏`sNN*`)، ومن انهار (‏`sNN!` — لا يُحسَب تغطية).
يزرع المُصابَ في الشجرة ويعيدها كما كانت، فلا يُشغَّل مع `mutation.mjs` (القفلُ نفسه)."""
import contextlib
import io
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LOCK = os.path.join(HERE, ".mutation.lock")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def trace():
    """يُشغَّل في عمليّةٍ وليدة: الحارسُ كاملًا، ثمّ سطرُ JSON بالأقسام التي احمرّت."""
    sys.argv = ["check_site.py"]
    sys.path.insert(0, os.path.join(ROOT, "tests", "docs"))
    os.chdir(ROOT)
    import check_site
    from site_guard import core
    hit = []

    def wrap(fn):
        def w(c):
            n = len(core.fails)
            try:
                return fn(c)
            except core._Stop:
                hit.append(fn.__name__ + "*")
                raise
            except Exception:
                hit.append(fn.__name__ + "!")
                raise
            finally:
                if len(core.fails) > n and fn.__name__ not in hit:
                    hit.append(fn.__name__)
        w.__name__, w.__module__ = fn.__name__, fn.__module__
        return w

    check_site.SECTIONS[:] = [wrap(f) for f in check_site.SECTIONS]
    check_site._layout = lambda: []  # الأقسامُ ملفوفة؛ وبنيتُها يحرسها [GRD-01] في التشغيل العاديّ
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        try:
            rc = check_site._run()
        except SystemExit as e:
            rc = e.code
    print(json.dumps({"rc": rc, "hit": hit}, ensure_ascii=False))


def run():
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, os.path.abspath(__file__), "--trace"],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        raise SystemExit("❌ تعذّر تتبّعُ الحارس:\n" + (p.stdout + p.stderr)[-600:])


def main(ids):
    if os.path.exists(LOCK):
        raise SystemExit("❌ ‏mutation.mjs يعمل (%s) — هذا يزرع في الشجرة نفسها" % LOCK)
    spec = json.load(open(os.path.join(HERE, "mutants.json"), encoding="utf-8"))["mutants"]
    muts = [m for m in spec if m["id"] in ids] if ids else [m for m in spec if m.get("sec")]
    unknown = set(ids) - {m["id"] for m in muts}
    if unknown:
        raise SystemExit("❌ لا مُصابَ بهذا المعرّف: %s" % "، ".join(sorted(unknown)))
    base = run()
    if base["rc"] != 0 or base["hit"]:
        raise SystemExit("❌ الحارسُ ليس أخضرَ قبل الزرع: %s" % base)
    bad = 0
    for m in muts:
        p = os.path.join(ROOT, m["file"])
        orig = open(p, encoding="utf-8", newline="").read()
        if orig.count(m["old"]) != 1:
            print("❌ %s: `old` ليس فريدًا في %s" % (m["id"], m["file"]))
            bad += 1
            continue
        try:
            open(p, "w", encoding="utf-8", newline="").write(orig.replace(m["old"], m["new"]))
            d = run()
        finally:
            open(p, "w", encoding="utf-8", newline="").write(orig)
        crashed = [h for h in d["hit"] if h.endswith("!")]
        sec = m.get("sec")
        ok = not crashed and (not sec or sec in d["hit"] or sec + "*" in d["hit"])
        bad += not ok
        print("%s %-36s sec=%s ← %s" % ("✅" if ok else "❌", m["id"], sec or "—", "، ".join(d["hit"]) or "لا قسم"),
              flush=True)
    print("%s %d مُصابًا، %d عطبًا" % ("✅" if not bad else "❌", len(muts), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--trace"]:
        trace()
    else:
        sys.exit(main(sys.argv[1:]))
