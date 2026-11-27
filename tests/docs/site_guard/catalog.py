# -*- coding: utf-8 -*-
"""جداولُ الوسوم في `site/guide/checks.md` تُولَّد من الحارس نفسِه [GRD-03]

كانت مكتوبةً باليد، فقسمٌ جديدٌ أو وسمٌ نُقل لا يغيّر الجدولَ معه — أوّلُ ما يتقادم في الدليل.
فالمصدرُ هنا: ‏`TAGS` في كلّ وحدة (الوسمُ وما يمسكه)، ووصفُ كلّ قسمٍ بلا وسم (سطرُه الأوّل؛ وما
يبدأ بـ«تهيئة:» قسمٌ يحسب لما بعده فلا يدخل الجدول).

    python tests/docs/check_site.py --list          # الجداولُ كلُّها
    python tests/docs/check_site.py --list fonts    # جدولُ وحدةٍ واحدة

وفي `checks.md` يقع كلُّ جدولٍ بين علامتين: ‏`<!-- مولَّد: <الوحدة> -->` و`<!-- /مولَّد -->`.
"""
import ast
import inspect
import re
import textwrap

PREP = "تهيئة:"
_TAG_IN_NAME = re.compile(r"^s\d\d_([a-z]+)(\d+)(?:_|$)")
# وسمٌ في نصّ قسم: ‏`[OUT-02]` و`[W404]` و`[AND-02..05]` — لا اختصارٌ مثل `[OUT-0x]`.
_TAG_IN_TEXT = re.compile(r"\[([A-Z]{1,5}(?:-\d\d|\d{3}))(?![\dA-Za-z])")
BEGIN = "<!-- مولَّد: %s — من `python tests/docs/check_site.py --list %s`، لا يُحرَّر يدويًّا -->"
END = "<!-- /مولَّد -->"


def tag_of(name):
    """وسمُ القسم من اسمه: ‏`s25_and06_…` ⇒ `AND-06`، و`s39_w404_…` ⇒ `W404`، وبلا وسمٍ ⇒ None."""
    m = _TAG_IN_NAME.match(name)
    if not m:
        return None
    letters, digits = m.groups()
    return "%s-%s" % (letters.upper(), digits) if len(digits) == 2 else letters.upper() + digits


def doc_of(fn):
    return (fn.__doc__ or "").strip().splitlines()[0].strip() if (fn.__doc__ or "").strip() else ""


def sections_of(mod, sections):
    return [s for s in sections if s.__module__ == mod.__name__]


def render(mod, sections):
    """جدولُ الوحدة وسطرُ «ومعها بلا وسم» بنصّ Markdown."""
    out = ["| الوسم | يمسك |", "| --- | --- |"]
    out += ["| %s | %s |" % (t, d) for t, d in mod.TAGS.items()]
    plain = [doc_of(s) for s in sections_of(mod, sections) if tag_of(s.__name__) is None]
    plain = [p for p in plain if p and not p.startswith(PREP)]
    if plain:
        out += ["", "ومعها بلا وسم: %s." % "، و".join(plain)]
    return "\n".join(out)


def _printed(fn):
    """⇒ (نصوصُ القسم الحرفيّة — ما يُطبَع لا التعليقات، هل فيه مسارُ فشلٍ: check/bad/need؟).
    والوصفُ (docstring) لا يُعَدّ نصًّا مطبوعًا."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    node = tree.body[0]
    doc = ast.get_docstring(node, clean=False)
    texts = [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)
             and n.value != doc]
    fails = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("check", "bad", "need")
                for n in ast.walk(node))
    return "\n".join(texts), fails


def problems(mod, sections, known=None):
    """⇒ قائمةُ ما يجعل الجدولَ كاذبًا: وسمُ قسمٍ بلا وصف، أو وصفٌ لوسمٍ لا قسمَ له، أو قسمٌ بلا وسمٍ ولا وصف،
    أو قسمٌ لا يطبع وسمَ اسمه، أو وسمٌ في نصّ قسمٍ لا يصفه جدول. والأخيران لأنّ القارئ يبحث في الدليل
    بالوسم المطبوع في رسالة الفشل، لا باسم الدالّة. ‏`known`: وسومُ الجداول كلِّها."""
    out = []
    for s in sections_of(mod, sections):
        text, fails = _printed(s)
        t = tag_of(s.__name__)
        if t and fails and not re.search(r"\[%s(?![\dA-Za-z])" % re.escape(t), text):
            out.append("%s.%s: لا رسالةَ فيه تحمل [%s] — وسمُ الاسم لا يُطبَع" % (mod.__name__, s.__name__, t))
        for x in sorted(set(_TAG_IN_TEXT.findall(text)) - set(known or ())):
            out.append("%s.%s: يطبع [%s] ولا جدولَ يصفه" % (mod.__name__, s.__name__, x))
    named = {tag_of(s.__name__) for s in sections_of(mod, sections)} - {None}
    described = set(getattr(mod, "TAGS", {}))
    for t in sorted(named - described):
        out.append("%s: الوسمُ %s في اسم قسمٍ ولا وصفَ له في `TAGS`" % (mod.__name__, t))
    for t in sorted(described - named):
        out.append("%s: ‏`TAGS` يصف %s ولا قسمَ يحمله" % (mod.__name__, t))
    for t, d in getattr(mod, "TAGS", {}).items():
        if not d.strip():
            out.append("%s: وصفُ %s فارغ" % (mod.__name__, t))
    for s in sections_of(mod, sections):
        if tag_of(s.__name__) is None and not doc_of(s):
            out.append("%s.%s: قسمٌ بلا وسمٍ ولا وصف — لا يظهر في الجدول" % (mod.__name__, s.__name__))
    return out


def marks(md, key):
    """⇒ كم مرّةً وردت علامةُ بدء الوحدة: واحدةٌ وحدَها صحيحة — المكرَّرةُ تتقادم ولا يكتبها `--write`."""
    return md.count(BEGIN % (key, key))


def block(md, key):
    """⇒ النصُّ بين علامتَي الوحدة في Markdown، أو None إن غابت إحداهما."""
    b = BEGIN % (key, key)
    i = md.find(b)
    if i < 0:
        return None
    j = md.find(END, i)
    return None if j < 0 else md[i + len(b):j].strip("\n")


def replace_block(md, key, body):
    """⇒ (النصُّ وقد صار جدولُ الوحدة `body`، أوُجدت العلامتان؟)."""
    b = BEGIN % (key, key)
    i = md.find(b)
    j = md.find(END, i) if i >= 0 else -1
    if j < 0:
        return md, False
    return md[:i + len(b)] + "\n\n" + body + "\n\n" + md[j:], True
