#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""جدولُ حالاتٍ لـ`det_check.violations` [DET-01] — ما يُمسَك وما لا يُمسَك، ولماذا.

    python tests/docs/test_det_check.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from det_check import pycache_dirs, root_strays, violations  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

# (الشيفرة، هل تُمسَك، الوسم) — الوسمُ في سطر الفشل لتُقرأ المُصاباتُ عليه.
CASES = [
    # الوقتُ والعشوائيّةُ والجهاز
    ("import time", True, "mod"),
    ("import os, time", True, "mod"),
    ("import time as t", True, "mod"),
    ("from datetime import datetime", True, "mod"),
    ("import zoneinfo", True, "mod"),
    ("from email.utils import formatdate", True, "mod"),
    ("import socket", True, "mod"),
    ("import importlib", True, "mod"),
    ("m = __import__('time')", True, "builtin"),
    ("x = hash('a')", True, "builtin"),
    ("x = id(o)", True, "builtin"),
    # من os
    ("from os import listdir", True, "from-os"),
    ("from os import getpid", True, "from-os"),
    ("from os import *", True, "from-os"),
    ("from os.path import getmtime", True, "from-os"),
    ("x = os.getpid()", True, "name"),
    ("x = os.path.getmtime(p)", True, "name"),
    ("x = os.stat(p).st_mtime", True, "name"),
    ("x = os.urandom(4)", True, "name"),
    ("for a, b, c in os.walk(d): pass", True, "name"),
    ("x = sorted(os.walk(d))", True, "name"),
    ("x = list(os.scandir(d))", True, "name"),
    # pathlib وglob
    ("from pathlib import Path", True, "mod"),
    ("import glob", True, "mod"),
    ("from glob import glob", True, "mod"),
    ("x = p.iterdir()", True, "name"),
    ("x = p.stat().st_mtime", True, "name"),
    # ترتيبُ listdir
    ("for f in os.listdir(d): pass", True, "listdir"),
    ("x = sorted(os.listdir(a)) + os.listdir(b)", True, "listdir"),
    ("a, b = sorted(os.listdir(x)), os.listdir(y)", True, "listdir"),
    ("x = sorted(f for f in os.listdir(d))", True, "listdir"),
    ("x = d and os.listdir(d)", True, "listdir"),
    ("x = list(os.listdir(d))", True, "listdir"),
    ("x = set(os.listdir(d))", True, "listdir"),
    ("for f in sorted(os.listdir(d)): pass", False, "listdir"),
    ("for f in sorted(\n        os.listdir(d)):\n    pass", False, "listdir"),
    ("if os.listdir(d): pass", False, "listdir"),
    ("if os.listdir(d) and not ok: pass", False, "listdir"),
    ("if not os.listdir(d): pass", False, "listdir"),
    ("n = len(os.listdir(d))", False, "listdir"),
    # البيئة
    ("x = os.environ.get('MIHRAB_SITE_OUT')", False, "env"),
    ("x = os.environ['MIHRAB_X']", False, "env"),
    ("x = os.environ.get('USER')", True, "env"),
    ("x = os.environ['USER']", True, "env"),
    ("x = os.environ", True, "env"),
    ("x = os.getenv('HOME')", True, "env"),
    ("x = os.getenv('MIHRAB_Y')", False, "env"),
    ("k = 'MIHRAB_X'\nx = os.environ.get(k)", True, "env"),
    # open
    ("open(p).read()", True, "open"),
    ("open(p, 'w').close()", True, "open"),
    ("open(p, mode='r')", True, "open"),
    ("open(p, encoding='utf-8')", False, "open"),
    ("open(p, 'w', encoding='utf-8')", False, "open"),
    ("open(p, 'rb')", False, "open"),
    ("open(p, mode='wb')", False, "open"),
    # ما ليس عطبًا: نصوصٌ وتعليقات
    ("s = 'import time; datetime now'", False, "text"),
    ("# import time\nx = 1", False, "text"),
    ('"""\nimport time\n"""', False, "text"),
    ("import timeit_like_name_os", False, "text"),
    ("import os, re, json, html, shutil, struct, sys, urllib.parse", False, "text"),
    # ما لا يُحلَّل مخالفةٌ لا صمت
    ("def (:", True, "syntax"),
]


# (أسماءُ جذر site/، الحزمُ منها (بـ`__init__.py`)، ما يُمسَك) — ‏`root_strays`: ما يستورده
# بايثون بالاسم سوى نقطة الدخول والحزم المسموحة.
ROOT_CASES = [
    (["build.py"], [], []),
    (["build.py", "README.md", "content", "sitegen", "public"], ["sitegen"], []),
    (["build.py", "json.py"], [], ["json.py"]),           # يظلّل `json` لكلّ وحدة
    (["build.py", "html.pyc"], [], ["html.pyc"]),         # بايتكودٌ بلا مصدر يُستورَد كذلك
    (["build.py", "_speedups.pyd"], [], ["_speedups.pyd"]),
    (["build.py", "re.so"], [], ["re.so"]),
    (["build.py", "csv.pyw"], [], ["csv.pyw"]),           # مصدرٌ على ويندوز
    (["build.py", "json"], ["json"], ["json/"]),          # حزمةٌ تظلّل كالوحدة
    (["build.py", "content"], [], []),                    # مجلّدٌ بلا `__init__.py`: namespace
    (["build.py", "JSON.PY"], [], []),                    # المطابقةُ حرفيّة
    (["build.py.bak", "notes.txt"], [], []),              # ليس اسمَ وحدة
    (["build.py", "a.py", "b.py"], [], ["a.py", "b.py"]),  # الكلُّ يُبلَّغ، مرتّبًا
]

# (نتيجةُ walk لشجرةٍ جذرُها S ومخرَجُها S/public، ما يُمسَك) — ‏`pycache_dirs`.
S = os.path.join(os.sep, "s")
P = os.path.join(S, "public")
PYC_CASES = [
    ([(S, ["sitegen"], ["build.py"]), (os.path.join(S, "sitegen"), [], ["data.py"])], []),
    ([(S, ["sitegen"], []), (os.path.join(S, "sitegen"), ["__pycache__"], []),
      (os.path.join(S, "sitegen", "__pycache__"), [], ["data.cpython-312.pyc"])],
     ["sitegen/__pycache__"]),                                     # المجلّدُ وحدَه، لا ما فيه
    ([(S, ["__pycache__"], [])], ["__pycache__"]),                 # بجانب build.py
    ([(os.path.join(S, "sitegen"), [], ["fonts.pyc"])], ["sitegen/fonts.pyc"]),  # ‏.pyc طليق
    ([(P, ["__pycache__"], ["x.pyc"]), (os.path.join(P, "assets"), [], ["y.pyc"])], []),  # المخرَجُ ليس مصدرًا
    ([(os.path.join(S, "publicity"), ["__pycache__"], [])], ["publicity/__pycache__"]),  # ليس المخرَجَ وإن شابهه
]


def main():
    print("╔══ [DET-01] جدولُ حالات det_check ══╗")
    fails = []
    for src, want, tag in CASES:
        got = bool(violations(src))
        if got != want:
            fails.append("[DET-01/%s] %s: %r" % (tag, "لم يُمسَك" if want else "أُمسِك خطأً", src))
    for names, pkgs, want in ROOT_CASES:
        got = root_strays(names, pkgs)
        if got != want:
            fails.append("[DET-01/root] %r (حزم %r) ⇒ %r والمتوقَّع %r" % (names, pkgs, got, want))
    for walk, want in PYC_CASES:
        got = pycache_dirs(walk, S, P)
        if got != want:
            fails.append("[DET-01/pycache] %r ⇒ %r والمتوقَّع %r" % ([w[0] for w in walk], got, want))
    n = len(CASES) + len(ROOT_CASES) + len(PYC_CASES)
    if fails:
        print("❌ %d حالةً خاطئة من %d:" % (len(fails), n))
        for f in fails:
            print("   · %s" % f)
        return 1
    print("╚══ ✅ %d حالةً كما يُتوقَّع ══╝" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
