#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[GRD-02] أسماءُ أقسام حارس الموقع محلولةٌ كلُّها — ساكنًا، بلا تشغيل.

    python tests/docs/test_site_guard_names.py

لماذا: الحارسُ قُسِّم من `main()` واحدةٍ إلى أقسامٍ في `site_guard/`، وما يعبر الأقسامَ يمرّ في
سياقٍ صريح. واسمٌ نُسي في السياق لا يظهر في التشغيل الأخضر: يقع في **مسار فشلٍ** فيرمي
`NameError` بدل رسالة العطب — و‎19‎ قسمًا لا يمرّ بمسار فشلها أيُّ مُصاب (قِيس). فيُقاس هنا
لكلّ قسمٍ بجدول الرموز (‏`symtable`، ومعه كلُّ نطاقٍ داخله: لامبدا الرسائل والدوالُّ المحلّيّة):
(١) كلُّ اسمٍ عامٍّ يقرؤه معرَّفٌ في `core.__all__` أو المبنيّات أو وحدتِه؛ (٢) كلُّ اسمٍ يقرؤه من
السياق كتبه قسمٌ قبله؛ (٣) وكتبه **آخرُ** قسمٍ عيّنه قبله — لا قيمةً قديمة.
"""
import ast
import builtins
import os
import re
import symtable
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
from site_guard import core  # noqa: E402
sys.argv = _argv


def section_info(path, name):
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    # أسماءُ الوحدة نفسِها: دوالُّها وأصنافُها وثوابتُها واستيراداتُها (ثابتٌ على مستوى الوحدة ليس «غيرَ معرَّف»).
    modnames = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    modnames |= {x.id for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign))
                 for t in (n.targets if isinstance(n, ast.Assign) else [n.target])
                 for x in ast.walk(t) if isinstance(x, ast.Name)}
    modnames |= {(a.asname or a.name).split(".")[0] for n in tree.body
                 if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names if a.name != "*"}
    reads, writes = set(), set()
    for n in ast.walk(fn):
        if (isinstance(n, ast.Compare) and isinstance(n.left, ast.Constant)
                and isinstance(n.comparators[0], ast.Name) and n.comparators[0].id == "_c"):
            reads.add(n.left.value)
        if (isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == "_n"
                and isinstance(n.iter, ast.Tuple)):
            writes |= {e.value for e in n.iter.elts}
    table = next(t for t in symtable.symtable(src, path, "exec").get_children() if t.get_name() == name)
    glob = set()

    def walk(t):
        for sym in t.get_symbols():
            if sym.is_global() and sym.is_referenced():
                glob.add(sym.get_name())
        for ch in t.get_children():
            walk(ch)
    walk(table)
    # ما يعيّنه القسمُ **بنفسه** — لا سطورُ الاستيراد من السياق (‏`if "x" in _c: x = _c["x"]`):
    # قسمٌ استورد اسمًا ولم يغيّره لا يحتاج أن يكتبه ثانيةً.
    prologue = {id(n) for st in fn.body if isinstance(st, ast.If) and isinstance(st.test, ast.Compare)
                and isinstance(st.test.comparators[0], ast.Name) and st.test.comparators[0].id == "_c"
                for n in ast.walk(st)}
    # ولا ما يُعيَّن داخل نطاقٍ متداخل: متغيّرُ الاستيعاب (يظهر محلّيًّا في جدول الرموز منذ 3.12،
    # PEP 709) ومحلّيّاتُ الدوالّ الداخليّة واللامبدا لا تغيّر قيمةَ الاسم في القسم.
    nested = {id(x) for n in ast.walk(fn)
              if isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.Lambda))
              or (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not fn)
              for x in ast.walk(n) if x is not n}
    locs = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
            and id(n) not in prologue and id(n) not in nested}
    locs |= {n.name for n in ast.walk(fn) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not fn}
    locs |= {(a.asname or a.name).split(".")[0] for n in ast.walk(fn)
             if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    locs &={s.get_name() for s in table.get_symbols() if s.is_local()}
    return dict(reads=reads, writes=writes, glob=glob, locs=locs, modnames=modnames)


def main():
    print("╔══ [GRD-02] أسماءُ أقسام حارس الموقع ══╗")
    known = set(core.__all__) | set(dir(builtins)) | {"__file__", "__name__"}
    order = [(s.__module__, s.__name__, sys.modules[s.__module__].__file__) for s in check_site.SECTIONS]
    info = {n: section_info(p, n) for _m, n, p in order}
    fails, seen = [], set()
    for i, (_m, n, _p) in enumerate(order):
        d = info[n]
        undef = d["glob"] - known - d["modnames"]
        if undef:
            fails.append("[GRD-02] %s يقرأ اسمًا غيرَ معرَّف: %s — ‏NameError في مسار فشله" % (n, sorted(undef)))
        never = d["reads"] - seen
        if never:
            fails.append("[GRD-02] %s يقرأ من السياق ما لم يكتبه قسمٌ قبله: %s" % (n, sorted(never)))
        for x in sorted(d["reads"] & seen):
            last = [q for _mm, q, _pp in order[:i] if x in info[q]["locs"]][-1:]
            if not last or x not in info[last[0]]["writes"]:
                fails.append("[GRD-02] %s يقرأ «%s» وآخرُ من عيّنه (%s) لا يكتبه في السياق — قيمةٌ قديمة"
                             % (n, x, last[0] if last else "؟"))
        seen |= d["writes"]
    if fails:
        print("❌ %d عطبًا في %d قسمًا:" % (len(fails), len(order)))
        for f in fails:
            print("   · %s" % f)
        return 1
    print("╚══ ✅ %d قسمًا، وكلُّ اسمٍ محلول ══╝" % len(order))
    return 0


if __name__ == "__main__":
    sys.exit(main())
