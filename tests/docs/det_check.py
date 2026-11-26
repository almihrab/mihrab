# -*- coding: utf-8 -*-
"""[DET-01] بناءُ الموقع لا يقرأ اللحظةَ ولا الجهازَ ولا ترتيبَ القرص — فحصٌ ساكنٌ بشجرة `ast`.

‏`same_output.py` يبني بمناطقَ زمنيّةٍ وبذورٍ متباينة فيكشف ما يتبعها، ولا يبلغ ما لا تحرّكه
البيئة: ‏`time.time()`، و`random`، و`getpid`، وmtime، واسمَ الجهاز، وترتيبَ `listdir` (أبجديٌّ
على NTFS، وعلى ext4 يتبع الاسمَ المجزَّأ فلا يتغيّر بالنسخ إلى مجلّدٍ جديد)، و`open()` بلا
ترميز على لينكس (محلّيّتُه UTF-8 أصلًا فتبديلُ `PYTHONUTF8` هناك لا يكشف شيئًا).

كان فحصًا بالتعابير النمطيّة سطرًا سطرًا، فأفلت منه 20 من 21 حالةً قِيست: ‏`from os import
listdir`، و`pathlib`، و`sorted(os.walk(…))` (لا يرتّب ما داخل الخطوة)، و`sorted(a) + listdir(b)`
على سطرٍ واحد، ووسمُ إعفاءٍ يشهد به كاتبُه لنفسه. فالقواعدُ هنا على الشجرة:

- **وحداتٌ ممنوعة** الاستيرادَ كلُّه: الوقتُ والعشوائيّةُ والجهاز، و`pathlib` و`glob` (سردٌ بلا
  ترتيب — البديلُ `sorted(os.listdir(…))`)، و`importlib` و`__import__` (بابٌ خلفيٌّ لما سبق).
- **أسماءٌ ممنوعة** استدعاءً أو استيرادًا من `os`: ‏`getpid` و`stat` و`getmtime` و`urandom`…
  و`os.walk` و`os.scandir` كلُّها.
- **‏`os.listdir(…)`** مقبولٌ في ثلاثة مواضعَ فقط: وسيطًا أوّلَ لـ`sorted`، أو اختبارَ صدقٍ
  (‏`if os.listdir(d)`، ‏`not`، ‏`and`/`or`)، أو داخل `len(…)`.
- **‏`os.environ`/`os.getenv`** بمفتاحٍ نصّيٍّ حرفيٍّ يبدأ بـ`MIHRAB_` فقط.
- **‏`open()`** إمّا ثنائيٌّ وإمّا بـ`encoding=`.
- **‏`hash()` و`id()`**: تتبعان البذرةَ والذاكرة.
"""
import ast
import os

BANNED_MODULES = {"time", "datetime", "random", "uuid", "secrets", "zoneinfo", "calendar", "socket",
                  "platform", "getpass", "tempfile", "pathlib", "glob", "fnmatch", "importlib",
                  "locale", "email", "subprocess", "multiprocessing", "threading"}
BANNED_NAMES = {"getpid", "getppid", "getuid", "getlogin", "gethostname", "uname", "urandom",
                "stat", "lstat", "fstat", "getmtime", "getctime", "getatime", "times", "cpu_count",
                "scandir", "walk", "iterdir", "glob", "iglob", "rglob", "getcwd"}
BANNED_BUILTINS = {"hash", "id", "__import__"}
ENV_PREFIX = "MIHRAB_"
ENTRY = "build.py"
# ما يستورده بايثون من مجلّدٍ على `sys.path` بالاسم: مصدرًا (‏`.pyw` على ويندوز)، أو بايتكودًا بلا
# مصدر، أو امتدادًا مُصرَّفًا (‏`importlib.machinery.all_suffixes()`؛ والوسومُ كـ`.cp312-win_amd64.pyd`
# تنتهي بـ`.pyd`).
_IMPORTABLE = (".py", ".pyw", ".pyc", ".pyd", ".so")
# الحزمُ المسموحة في الجذر: مولِّدُ الموقع نفسُه، ولا يظلّل اسمُه وحدةً قياسيّة.
ROOT_PACKAGES = {"sitegen"}


def root_strays(names, packages=()):
    """ما في جذر `site/` ممّا يستورده بايثون بالاسم، سوى نقطة الدخول والحزم المسموحة.

    مجلّدُ `build.py` أوّلُ `sys.path`، فـ`site/json.py` — أو `json.pyc` أو `json.pyd`، أو الحزمةُ
    `site/json/` بـ`__init__.py` — يظلّل المكتبةَ القياسيّة لـ`build.py` ولكلّ وحدةٍ في `sitegen/`،
    فيتغيّر البناءُ بملفٍّ لا يستورده أحدٌ صراحةً. ومجلّدٌ بلا `__init__.py` حزمةُ namespace لا
    تظلّل وحدةً عاديّة، فلا تُعَدّ. يأخذ أسماءً لا مسارًا (‏`packages`: المجلّداتُ التي فيها
    `__init__.py`)، فيُحرَس بجدول حالات. والمطابقةُ حرفيّة: ‏`FileFinder` بلا `PYTHONCASEOK` كذلك."""
    files = [n for n in names if n.endswith(_IMPORTABLE) and n != ENTRY]
    return sorted(files + [p + "/" for p in packages if p not in ROOT_PACKAGES])


def pycache_dirs(walk, site, out):
    """بايتكودٌ في شجرة المصدر — مجلّداتُ `__pycache__` و`.pyc` الطليقة — خارجَ المخرَج.

    ‏`build.py` يضبط `sys.dont_write_bytecode`، فكاتبُه غيرُه: وحدةٌ شُغِّلت مباشرةً، أو
    `compileall`. و`.pyc` يُتحقَّق منه بالحجم وبزمن التعديل بالثواني، فمُصابٌ بالطول نفسه في
    الثانية نفسها قد يُشغَّل قديمُه. ‏`walk` نتيجةُ `os.walk(site)` (أو جدولُ حالاتٍ بشكلها)."""
    out_p = os.path.normpath(out) + os.sep
    found = []
    for d, subs, files in walk:
        if (os.path.normpath(d) + os.sep).startswith(out_p):
            continue
        found += [os.path.join(d, x) for x in subs if x == "__pycache__"]
        if os.path.basename(os.path.normpath(d)) != "__pycache__":
            found += [os.path.join(d, x) for x in files if x.endswith(".pyc")]
    return sorted(os.path.relpath(p, site).replace(os.sep, "/") for p in found)


def _parents(tree):
    par = {}
    for node in ast.walk(tree):
        for ch in ast.iter_child_nodes(node):
            par[ch] = node
    return par


def _is_os(node):
    return isinstance(node, ast.Name) and node.id == "os"


def _call_name(node):
    """اسمُ المستدعى: ‏`f` لـ`f(…)` و`x.f(…)`."""
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _str_const(node, prefix):
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith(prefix)


def _listdir_ok(call, par):
    p = par.get(call)
    if isinstance(p, ast.Call) and isinstance(p.func, ast.Name) and p.args and p.args[0] is call:
        return p.func.id in ("sorted", "len")
    if isinstance(p, (ast.If, ast.While, ast.IfExp)) and p.test is call:
        return True
    if isinstance(p, ast.UnaryOp) and isinstance(p.op, ast.Not):
        return True
    if isinstance(p, ast.BoolOp):
        # ‏`a and os.listdir(d)` قيمتُه القائمةُ نفسُها إن كانت آخرَ الطرفين — صدقٌ فقط إن
        # كانت العبارةُ كلُّها اختبارًا.
        q = par.get(p)
        return isinstance(q, (ast.If, ast.While, ast.IfExp, ast.Assert)) and q.test is p \
            or isinstance(q, ast.UnaryOp) and isinstance(q.op, ast.Not)
    return False


def violations(src, name="<src>"):
    """⇒ [(السطر، السبب)] مرتَّبةً. خطأُ صياغةٍ نفسُه مخالفة (لا يُفحَص ما لا يُحلَّل)."""
    try:
        tree = ast.parse(src, name)
    except SyntaxError as e:
        return [(e.lineno or 0, "لا يُحلَّل: %s" % e.msg)]
    par = _parents(tree)
    out = []

    def add(node, why):
        out.append((getattr(node, "lineno", 0), why))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in BANNED_MODULES:
                    add(node, "استيرادُ %s" % a.name)
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            if mod in BANNED_MODULES:
                add(node, "استيرادٌ من %s" % node.module)
            elif mod == "os":
                for a in node.names:
                    if a.name in BANNED_NAMES or a.name in ("listdir", "environ", "getenv", "*"):
                        add(node, "‏from %s import %s" % (node.module, a.name))
        elif isinstance(node, ast.Call):
            n = _call_name(node)
            if isinstance(node.func, ast.Name) and n in BANNED_BUILTINS:
                add(node, "‏%s()" % n)
            elif n in BANNED_NAMES:
                add(node, "‏%s()" % n)
            elif n == "listdir" and not _listdir_ok(node, par):
                add(node, "‏listdir() بلا sorted — ترتيبُه ترتيبُ القرص")
            elif n == "getenv" and not (node.args and _str_const(node.args[0], ENV_PREFIX)):
                add(node, "‏getenv() بغير مفتاحٍ ‎%s*‎ حرفيّ" % ENV_PREFIX)
            elif isinstance(node.func, ast.Name) and n == "open":
                mode = node.args[1] if len(node.args) > 1 else next(
                    (k.value for k in node.keywords if k.arg == "mode"), None)
                binary = isinstance(mode, ast.Constant) and isinstance(mode.value, str) and "b" in mode.value
                if not binary and not any(k.arg == "encoding" for k in node.keywords):
                    add(node, "‏open() نصّيٌّ بلا encoding= — يقرأ بمحلّيّة الجهاز")
        elif isinstance(node, ast.Attribute) and node.attr == "environ" and _is_os(node.value):
            p = par.get(node)
            ok = False
            if isinstance(p, ast.Attribute) and p.attr == "get":
                c = par.get(p)
                ok = isinstance(c, ast.Call) and c.func is p and c.args and _str_const(c.args[0], ENV_PREFIX)
            elif isinstance(p, ast.Subscript) and p.value is node:
                ok = _str_const(p.slice, ENV_PREFIX)
            if not ok:
                add(node, "‏os.environ بغير مفتاحٍ ‎%s*‎ حرفيّ" % ENV_PREFIX)
    return sorted(set(out))
