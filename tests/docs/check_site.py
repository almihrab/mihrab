#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فحصٌ بنيويّ لمخرَج موقع محراب.

يمسك الأعطالَ التي **لا تظهر في المتصفّح**: زرًّا يقود إلى صفحةٍ لم تُبنَ، ووسمًا
يبحث عنه جافاسكربت ولا يجده فيموت السلوكُ كلُّه صامتًا، ومسارًا مطلقًا يربط المخرَج
بمضيفٍ بعينه فيكسر المرآة. وكلُّها أعطالٌ تمرّ من مراجعةِ العين لأنّ الصفحة تبدو سليمة.

    python tests/docs/check_site.py          # يبني ثمّ يفحص
    python tests/docs/check_site.py --no-build
"""
import collections
import glob
import hashlib
import html as _html
import json
import os
import re
import shutil
import subprocess
import sys
import uuid

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITE = os.path.join(ROOT, "site")
OUT = os.path.join(SITE, "public")
# **يُقاس ما يُشحَن**: محتوى JS وCSS يُقرأ من `OUT/assets/` لا من `site/assets/` — [OUT-02]
# يشترط أنّ `public/` بناءٌ نظيفٌ من المصدر، والبناءُ قد يحوِّل الأصل (تجريدُ التعليقات)،
# فعطبٌ يُدخله التحويلُ لا يُرى في المصدر. (قوائمُ الملفّات تبقى من المصدر: ما يُفحَص هو
# ما كتبه المطوّر، بمحتواه كما يصل الزائر.)

fails = []
# عددُ الفحوص المُقيَّمة (‏`check` و`need`) وبصمتُها — تُطبعان في اللافتة الخضراء، ويقارنهما
# ‏`same_guard.py` بين مرجعٍ وشجرة عمل. إعادةُ تنظيمٍ «لا تغيّر السلوك» يجب أن تُبقيهما:
# وحدةٌ لا تُستدعى، أو فحصٌ يسقط خلف `need`، يبقى أخضرَ ويبقى تفريغُ المُصابات مطابقًا
# (المُصاباتُ لا تلمس كلَّ فحص) — والعددُ ينقص. و**البصمةُ** تُحصي الفحوصَ بمفتاحها: وسمُها
# ‏`[XXX-NN]` إن كان في رسالتها، وإلّا أوّلُ نصّها. فاستبدالُ فحصٍ بآخرَ بالعدد نفسه يغيّرها،
# ونقلُ فحصٍ إلى وحدةٍ أخرى برسالته لا يغيّرها. (وإضعافُ شرطٍ برسالته نفسِها لا يراه هذا —
# ذاك عملُ المُصابات.)
evaluated = collections.Counter()
_TAG = re.compile(r"\[([A-Z]{2,5}-\d{2})")


def _strings(code):
    for c in code.co_consts:
        if isinstance(c, str):
            yield c
        elif hasattr(c, "co_consts"):
            yield from _strings(c)


def _key(msg):
    strs = list(_strings(msg.__code__)) if callable(msg) and hasattr(msg, "__code__") else [str(msg)]
    for s_ in strs:
        m = _TAG.search(s_)
        if m:
            return m.group(1)
    return next((s_.strip()[:40] for s_ in strs if s_.strip()), "؟")


def _count(msg):
    evaluated[_key(msg)] += 1


def fingerprint():
    """⇒ (العدد، بصمةٌ من 12 خانة)."""
    h = hashlib.sha256("\n".join("%s\t%d" % kv for kv in sorted(evaluated.items())).encode("utf-8"))
    return sum(evaluated.values()), h.hexdigest()[:12]


def bad(msg):
    fails.append(msg)


class _Stop(Exception):
    """فشلٌ لا يُكمَل بعده: ما يليه يستعمل ما لم يتحقّق (مطابقةً، أو عمليّةً، أو ملفًّا)."""


def check(cond, msg):
    """يُسجَّل الفشلُ ويُكمَل — فيُرى كلُّ عطبٍ في تشغيلةٍ واحدة، لا أوّلُها وحدَه.
    والرسالةُ دالّةٌ تُحسَب عند الفشل وحدَه كما كانت مع `assert` (بعضُها يحسب ما لا
    يصحّ إلّا حينها، كـ`min()` على ما يُفترَض ألّا يكون فارغًا).

    كانت `assert`: أوّلُ فشلٍ يُخفي كلَّ ما بعده (قِيس: مُصابُ W404 احمرّ على FNT-01 قبله
    فلم يُرَ W404 قطّ)، و`python -O` ينزعها كلَّها فيصير الحارسُ أخضرَ بلا قياس."""
    _count(msg)
    if not cond:
        bad(msg() if callable(msg) else msg)
    return bool(cond)


def need(cond, msg):
    """كـ`check` لكنّ ما بعده لا يُقاس بلاه: يُسجَّل ويوقف الحارسَ بعد عرض ما جُمع."""
    _count(msg)
    if not cond:
        raise _Stop(msg() if callable(msg) else msg)
    return True



def _page_tree(src):
    """صفحةٌ مبنيّةٌ شجرةً `[وسم، سمات، أبناء]` والنصُّ سلاسل — يبنيها الصندوقُ [CAP-04]
    ‏`El` ويجد فيها ما يجده docs.js في المتصفّح. ومحتوى `script`/`style`/`noscript` لا يُنقَل
    (‏`noscript` نصٌّ خامٌ في متصفّحٍ يشغّل السكربت).

    ⇒ ‏`(الشجرة، العيوب)`. ‏`HTMLParser` لا يُغلق شيئًا ضمنيًّا والمتصفّحُ يُغلق: ‏`<p>` يُغلَق
    عند أوّل `<div>`، و`<li>` عند `<li>` التالي… فصفحةٌ تعتمد ذلك تُبنى هنا شجرةً غيرَ شجرة
    المتصفّح، وقد يجد الصندوقُ `.capture-box .result` والمتصفّحُ لا يجده (قِيس بالزرع: ‏`div`
    الصندوق ‏`p` ⇒ أخضر والالتقاطُ ميّتٌ في الموقع). فكلُّ موضعٍ يفترق فيه الاثنان عيبٌ يُسمّى
    لا تخمينٌ يُصلَح: وسمٌ يُغلَق في غير مكانه، وكتلةٌ داخل `<p>`، و`<div/>` (مفتوحٌ في HTML)،
    و`<template>` (محتواه خارجَ الوثيقة)."""
    from html.parser import HTMLParser
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
            "source", "track", "wbr"}
    RAW = {"script", "style", "noscript"}
    # ما يُغلق `<p>` مفتوحًا (‏HTML §13.2.6.4.7، مختصرًا) وما يحدّ نطاقَه
    P_CLOSERS = {"address", "article", "aside", "blockquote", "details", "dialog", "div", "dl",
                 "dd", "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
                 "h3", "h4", "h5", "h6", "header", "hgroup", "hr", "li", "main", "menu", "nav",
                 "ol", "p", "pre", "section", "table", "ul"}
    P_SCOPE = {"button", "table", "td", "th", "caption", "svg", "math"}

    class _P(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.root = ["html", {}, []]
            self.stack = [self.root]
            self.errs = []

        def _raw(self):
            return any(n[0] in RAW for n in self.stack)

        def _where(self):
            return "السطر %d" % self.getpos()[0]

        def _attrs_ok(self, tag, attrs):
            # سمةٌ مكرّرة: المتصفّحُ يأخذ **الأولى** والقاموسُ هنا الأخيرة — `id="a" id="capture-btn"`
            # يجده الصندوقُ ولا يجده docs.js (قِيس بالزرع وبـEdge).
            names = [k for k, _ in attrs]
            for k in sorted({k for k in names if names.count(k) > 1}):
                self.errs.append("<%s %s=… %s=…> (%s): سمةٌ مكرّرة — المتصفّحُ يأخذ الأولى"
                                 % (tag, k, k, self._where()))

        def handle_starttag(self, tag, attrs):
            self._attrs_ok(tag, attrs)
            if tag == "html":
                self.root[1] = {k: (v or "") for k, v in attrs}
                return
            # ‏`textarea` و`title` نصٌّ خامّ (RCDATA) في المتصفّح: ما فيها من وسومٍ نصٌّ، فتُبتلَع
            # بقيّةُ الصفحة إن لم تُغلَق — و`HTMLParser` يبنيها عناصر.
            for n in self.stack:
                if n[0] in ("textarea", "title"):
                    self.errs.append("<%s> داخل <%s> (%s): المتصفّحُ يقرؤه نصًّا لا عنصرًا"
                                     % (tag, n[0], self._where()))
                    break
            if tag == "template":
                self.errs.append("<template> (%s): محتواه خارجَ الوثيقة في المتصفّح" % self._where())
            if tag in P_CLOSERS:
                for n in reversed(self.stack):
                    if n[0] in P_SCOPE:
                        break
                    if n[0] == "p":
                        self.errs.append("<%s> داخل <p> مفتوح (%s): المتصفّحُ يُغلق <p> قبله"
                                         % (tag, self._where()))
                        break
            node = [tag, {k: (v or "") for k, v in attrs}, []]
            if not self._raw():
                self.stack[-1][2].append(node)
            if tag not in VOID:
                self.stack.append(node)

        def handle_startendtag(self, tag, attrs):
            self._attrs_ok(tag, attrs)
            if tag not in VOID and not any(n[0] in ("svg", "math") for n in self.stack):
                self.errs.append("<%s/> (%s): الشرطةُ لا تُغلق وسمًا في HTML — يبقى مفتوحًا"
                                 % (tag, self._where()))
            if not self._raw():
                self.stack[-1][2].append([tag, {k: (v or "") for k, v in attrs}, []])

        def handle_endtag(self, tag):
            if tag in VOID or tag == "html":
                return
            if self.stack[-1][0] != tag:
                self.errs.append("</%s> (%s) والمفتوحُ <%s>: إغلاقٌ ضمنيٌّ يُبنى في المتصفّح غيرَ ما يُبنى هنا"
                                 % (tag, self._where(), self.stack[-1][0]))
            for i in range(len(self.stack) - 1, 0, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    return

        def handle_data(self, data):
            if data and not self._raw():
                self.stack[-1][2].append(data)

    _p = _P()
    _p.feed(src)
    return _p.root, _p.errs


def read(rel):
    with open(os.path.join(OUT, rel), encoding="utf-8") as f:
        return f.read()


def css_strip_comments(raw, name="?"):
    """نصُّ CSS بلا تعليقات — بماسحٍ بأربع حالات: خارجَ كلّ شيء، داخلَ تعليق،
    داخلَ سلسلة، داخلَ `url(` بلا اقتباس [CSS-01].

    **الماسحُ والنازعُ شيءٌ واحد.** كان الماسحُ ثلاثيَّ الحالات (فـ`content: "*/"`
    سلسلةٌ لا إغلاقُ تعليق) بينما النزعُ الذي تُقاس عليه بقيّةُ [CSS-01] — جُملُ
    `:root` و`font-family` و`var()` — `re.sub(r"/\\*.*?\\*/")` ساذجٌ لا يعرف
    السلسلة: فـ`content: "/*"` يمرّ من الماسح ثمّ يبتلع النازعُ كلَّ ما بينه وبين
    أوّل `*/` حقيقيّ، و`font-family: serif` في المبتلَع يمرّ أخضر. قِيس بالطفرة:
    خضراء. و`url(data:…*/…)` بلا اقتباس رمزٌ واحدٌ في CSS (`url-token`) لا
    إغلاقُ تعليق، فكان يحمرّ كذبًا.

    والسلسلةُ تنتهي باقتباسها أو بسطرٍ جديد (كما في المحلِّل: `bad-string`)،
    والهروبُ `\\` يقفز محرفًا — فـ`"\\""` سلسلةٌ واحدة. و`/*` داخل تعليقٍ ليس
    خطأً في CSS لكنّه ممنوعٌ هنا عمدًا: تعليقٌ يُظَنّ متداخلًا يُغلَق مبكّرًا
    ويترك بقيّتَه نصًّا طليقًا.
    """
    out = []
    pos, depth, n = 0, 0, len(raw)
    while pos < n:
        ch2 = raw[pos:pos + 2]
        if depth == 1:
            if ch2 == "/*":
                raise _Stop(
                    "‏`/*` داخل تعليقٍ مفتوحٍ في %s:%d — تعليقٌ متداخلٌ يُغلَق مبكّرًا "
                    "ويترك بقيّتَه نصًّا طليقًا [CSS-01]"
                    % (name, raw.count("\n", 0, pos) + 1))
            if ch2 == "*/":
                depth, pos = 0, pos + 2
                continue
            pos += 1
            continue
        # الهروبُ خارج السلسلة محرفٌ واحد: ‏`\/*` ليس بدايةَ تعليق.
        if raw[pos] == "\\":
            out.append(raw[pos:pos + 2])
            pos += 2
            continue
        if ch2 == "/*":
            depth, pos = 1, pos + 2
            continue
        if ch2 == "*/":
            raise _Stop(
                "‏`*/` بلا `/*` يسبقه في %s:%d — ما بعده حتّى أوّل `;` نصٌّ طليقٌ "
                "يبتلع الإعلانَ التالي صامتًا (وقع: الموقعُ كلُّه بخطّ المتصفّح "
                "الافتراضيّ) [CSS-01]" % (name, raw.count("\n", 0, pos) + 1))
        if raw[pos] in "\"'":
            q, e = raw[pos], pos + 1
            while e < n and raw[e] != q and raw[e] != "\n":
                e += 2 if raw[e] == "\\" else 1
            out.append(raw[pos:e + 1])
            pos = e + 1
            continue
        if raw[pos:pos + 4].lower() == "url(":
            e = pos + 4
            while e < n and raw[e] in " \t\r\n":
                e += 1
            if e < n and raw[e] not in "\"')":
                k = raw.find(")", e)
                k = n if k < 0 else k
                out.append(raw[pos:k])
                pos = k
                continue
        out.append(raw[pos])
        pos += 1
    check(depth == 0, lambda: "تعليقٌ لم يُغلَق في %s [CSS-01]" % name)
    return "".join(out)


def main():
    # ── [DET-01] البناءُ لا يقرأ اللحظةَ ولا الجهازَ ولا ترتيبَ القرص ──
    # القواعدُ وعلّتُها في `det_check.py`، وجدولُ حالاتها في `test_det_check.py`. والمسحُ على
    # كلّ `site/**/*.py` (عدا المخرَج): وحدةٌ فرعيّةٌ يستوردها البناءُ يومًا تُفحَص معه.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from det_check import violations as _det
    _det_files = sorted(p for p in glob.glob(os.path.join(SITE, "**", "*.py"), recursive=True)
                        if not os.path.abspath(p).startswith(os.path.abspath(OUT) + os.sep))
    need(_det_files, lambda: "[DET-01] لا ملفَّ بايثون في site/ — المسحُ لا يرى البناء")
    # وجذرُ `site/` لا يحمل بايثون سوى نقطة الدخول: مجلّدُ السكربت أوّلُ `sys.path`، فملفٌّ
    # كـ`site/json.py` أو `site/html.py` يظلّل المكتبةَ القياسيّة لـ`build.py` ولكلّ وحدةٍ في
    # `sitegen/` — فيتغيّر البناءُ بملفٍّ لا يستورده أحدٌ صراحةً. والوحداتُ مكانُها `sitegen/`.
    _root_py = sorted(f for f in os.listdir(SITE) if f.endswith(".py") and f != "build.py")
    check(not _root_py, lambda: "[DET-01] بايثون في جذر site/ سوى build.py: %s — يظلّل ما يستورده "
          "البناء؛ مكانُه site/sitegen/" % "، ".join(_root_py))

    # ── [GEN-01] حدودُ المولِّد المقسَّم: كلُّ وحدةٍ في `sitegen/` مستورَدة، ولا حلقات، ولا بايتكود ──
    # وحدةٌ لا يستوردها أحدٌ شيفرةٌ ميّتةٌ تبدو حيّة (تعديلُها لا يغيّر الموقع فيمرّ كلُّ حارسٍ
    # أخضر)؛ والحلقةُ تجعل ترتيبَ الاستيراد يقرّر أيَّ اسمٍ يُرى؛ و`__pycache__` بجانب المصدر
    # يظهر في `git status` وفي أدوات الإثبات (لذا `sys.dont_write_bytecode` في `build.py`).
    import ast as _ast
    _gen = os.path.join(SITE, "sitegen")
    _mods = sorted(f[:-3] for f in os.listdir(_gen) if f.endswith(".py") and f != "__init__.py")
    need(len(_mods) >= 2, lambda: "[GEN-01] لا وحداتٍ في site/sitegen/ — الحارسُ يقيس الهواء")
    _edges = {}

    def _gen_imports(_path):
        """أسماءُ وحدات sitegen التي يستوردها الملفّ — **بكلّ صيغة** وفي أيّ موضع (استيرادٌ
        كسولٌ داخل دالّةٍ يُغلق حلقةً كما يُغلقها رأسُ الملفّ): ‏`from .x import`،
        ‏`from . import x`، ‏`from sitegen.x import`، ‏`from sitegen import x`، ‏`import sitegen.x`.
        وصيغةٌ مفقودةٌ هنا تُسقط حافّةً فتُعلَن وحدةٌ حيّةٌ ميّتةً، وتفوت حلقة."""
        with open(_path, encoding="utf-8") as _gf:
            _tree = _ast.parse(_gf.read(), _path)
        _out = set()
        for _n in _ast.walk(_tree):
            if isinstance(_n, _ast.ImportFrom):
                _mod = _n.module or ""
                if _n.level >= 1:
                    _out.update([_mod.split(".")[0]] if _mod else [a.name for a in _n.names])
                elif _mod == "sitegen":
                    _out.update(a.name for a in _n.names)
                elif _mod.startswith("sitegen."):
                    _out.add(_mod.split(".")[1])
            elif isinstance(_n, _ast.Import):
                _out.update(a.name.split(".")[1] for a in _n.names if a.name.startswith("sitegen."))
        return _out

    for _m in _mods:
        _edges[_m] = _gen_imports(os.path.join(_gen, _m + ".py")) & set(_mods)
    # نقطتا الدخول: `build.py`، و`__init__.py` (يُنفَّذ مع أيّ استيرادٍ من الحزمة).
    _from_entry = _gen_imports(os.path.join(SITE, "build.py"))
    if os.path.isfile(os.path.join(_gen, "__init__.py")):
        _from_entry |= _gen_imports(os.path.join(_gen, "__init__.py"))
    # **الوصولُ من نقطة الدخول** لا «يستوردها أحد»: وحدتان ميّتتان تستورد إحداهما الأخرى
    # كانتا تمرّان بالقاعدة الثانية (قِيس بالزرع).
    _used, _todo = set(), sorted(_from_entry & set(_mods))
    while _todo:
        _m = _todo.pop()
        if _m not in _used:
            _used.add(_m)
            _todo.extend(_edges.get(_m, ()))
    _orphans = [m for m in _mods if m not in _used]
    check(not _orphans, lambda: "[GEN-01] وحداتٌ في sitegen/ لا تصل إليها build.py (مباشرةً أو عبر وحدة): %s"
          % "، ".join(_orphans))
    _cycle = []

    def _gen_dfs(_m, _stack):
        if _cycle:
            return
        if _m in _stack:
            _cycle.extend(_stack[_stack.index(_m):] + [_m])
            return
        for _d in sorted(_edges.get(_m, ())):
            _gen_dfs(_d, _stack + [_m])

    for _m in _mods:
        _gen_dfs(_m, [])
    check(not _cycle, lambda: "[GEN-01] حلقةُ استيرادٍ بين وحدات sitegen/: %s" % " ← ".join(_cycle))
    _pyc = [os.path.relpath(os.path.join(_d, _x), SITE).replace(os.sep, "/")
            for _d, _sub, _fs in os.walk(SITE)
            if not (os.path.abspath(_d) + os.sep).startswith(os.path.abspath(OUT) + os.sep)
            for _x in _sub if _x == "__pycache__"]
    check(not _pyc, lambda: "[GEN-01] بايتكود في شجرة المصدر: %s — `build.py` يضبط "
          "`sys.dont_write_bytecode`؛ وكاتبُه غيرُه: وحدةٌ شُغِّلت مباشرةً، أو `compileall` "
          "بلا `PYTHONPYCACHEPREFIX` — يُحذف" % "، ".join(_pyc))
    for _py in _det_files:
        with open(_py, encoding="utf-8") as _f:
            _dv = _det(_f.read(), _py)
        check(not _dv, lambda: "[DET-01] %s يقرأ اللحظةَ أو الجهازَ أو ترتيبَ القرص — البناءُ لا يعود حتميًّا: %s"
              % (os.path.relpath(_py, SITE).replace(os.sep, "/"), "؛ ".join("سطر %d: %s" % d for d in _dv[:5])))

    if "--no-build" not in sys.argv:
        # ── بائتٌ يُزرَع في المخرَج **الحقيقيّ** قبل البناء [OUT-01] ──
        # الحارسُ في ٨) يبني في مجلّدٍ مؤقّتٍ بـ`MIHRAB_SITE_OUT` — فبناءٌ يمحو
        # **فقط حين يُضبَط المتغيّرُ** كان يمرّ هناك ويترك `site/public/` البائتَ
        # يُحزَم ويُنشَر (قِيس بالطفرة). فيُقاس المسارُ الذي يحزمه النشرُ نفسُه:
        # ثلاثةُ بوائتَ في الجذر وداخل `assets/` ومجلّدٌ كامل، كلُّها تزول.
        #
        # ⚠️ **ولا شرطَ على وجود المخرَج**: `site/public/` مُهمَلٌ في git، فعلى CI
        # لا مخرَجَ قبل البناء — وكان الزرعُ مشروطًا بوجوده فيُتخطّى هناك ويقيس
        # الشرطُ أدناه الهواء: طفرةُ «المحوُ فقط حين يُضبَط `MIHRAB_SITE_OUT`»
        # حمراءُ على جهاز المطوّر وخضراءُ على CI (قِيست في نسخةٍ بلا مخرَج).
        # فمخرَجٌ غائبٌ أو فارغٌ يُنشأ بشاهده ثمّ يُزرَع؛ وغيرُ الفارغ بلا شاهدٍ
        # يُترَك لبناءٍ سيرفضه بصوت.
        # **والأسماءُ عشوائيّة**: محوٌ بالاسم للبوائت الثلاثة المكتوبة كان يمرّ
        # أخضرَ (قِيس بالطفرة) — فما يُزرَع لا يُعرَف قبل التشغيل.
        _pub_planted = []
        _mark0 = os.path.join(OUT, ".mihrab-site-build")
        _tag = uuid.uuid4().hex[:8]
        if not os.path.isdir(OUT) or not os.listdir(OUT):
            os.makedirs(OUT, exist_ok=True)
            with open(_mark0, "w", encoding="utf-8") as _mf0:
                _mf0.write("x")
        if os.path.isfile(_mark0):
            for _rel in ("stale-%s.html" % _tag,
                         os.path.join("assets", "stale-%s.css" % _tag),
                         os.path.join("stale-dir-%s" % _tag, "index.html")):
                _pp = os.path.join(OUT, _rel)
                os.makedirs(os.path.dirname(_pp), exist_ok=True)
                with open(_pp, "w") as _pf:
                    _pf.write("stale")
                _pub_planted.append(_pp)
        # الخرجُ يُلتقَط ثمّ يُطبَع كما هو، كي يُلحَق ذيلُه برسالة الفشل: «فشل البناء» وحدَها
        # لا تقول أين — والسببُ (‏`SystemExit` أو التتبّع) في آخر سطورٍ منه.
        r = subprocess.run([sys.executable, os.path.join(SITE, "build.py")],
                           cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        _bout = r.stdout.decode("utf-8", "replace")
        sys.stdout.write(_bout)
        _survived = [os.path.relpath(_pp, OUT) for _pp in _pub_planted if os.path.exists(_pp)]
        if r.returncode:
            # بناءٌ فشل قبل المحو يترك ما زُرع في `site/public/` مع الشاهد —
            # فيُنظَّف هنا كي لا يُحزَم يومًا. (‏`deploy_site.sh` يسقط قبل الحزم
            # بـ`set -e`، لكنّ النظافةَ لا تعتمد على ذلك.)
            for _pp in _pub_planted:
                try:
                    os.remove(_pp)
                    _pd = os.path.dirname(_pp)
                    if os.path.basename(_pd).startswith("stale-dir-") and not os.listdir(_pd):
                        os.rmdir(_pd)
                except OSError:
                    pass
            _tail = [ln for ln in _bout.splitlines() if ln.strip()][-3:]
            print("❌ فشل بناءُ الموقع (خرج %d):\n     %s" % (r.returncode, "\n     ".join(_tail) or "بلا خرج"))
            return 1
        check(not _survived, lambda: "بوائتُ في `site/public/` نجت البناءَ الحقيقيّ: %s — وهذا المجلّدُ بعينه "
            "ما يحزمه `deploy_site.sh` [OUT-01]" % "، ".join(_survived))

    with open(os.path.join(SITE, "data", "site.json"), encoding="utf-8") as f:
        data = json.load(f)

    # ── ١) الصفحاتُ الإلزاميّة ──
    required = ["index.html", "download/index.html", "docs/index.html",
                "keyboard/index.html", "start/index.html",
                "search-index.json", "dl/releases.json", ".nojekyll",
                "assets/mihrab-docs.css", "assets/mihrab-home.css",
                "assets/docs.js", "assets/site.js", "assets/fonts.css"]
    for rel in required:
        if not os.path.exists(os.path.join(OUT, rel)):
            bad("ملفٌّ إلزاميّ مفقود في المخرَج: %s" % rel)
    if fails:
        report()
        return 1

    # ── [OUT-02] ما يُنشَر هو بناءٌ نظيفٌ من هذا المصدر، بالبايت ──
    # الفحوصُ أدناه تقرأ `site/public/` (ما يحزمه `deploy_site.sh`)، ومع `--no-build`
    # (بوّابةُ النشر) لا شيءَ يضمن أنّه من هذا المصدر: عطبٌ في `public/assets/docs.js` كان يمرّ
    # أخضرَ ويُشحَن (قِيس بالزرع). كان الشرطُ «كلُّ أصلٍ يطابق `site/assets/` بالبايت» — وهو
    # ينكسر عمدًا يومَ يُحوِّل البناءُ أصلًا (تجريدُ التعليقات)، ولا يرى الصفحاتِ ولا المولَّدَين.
    # فالمرجعُ الآن **بناءٌ نظيفٌ في مجلّدٍ مؤقّت**: كلُّ ملفٍّ في `public/` يطابق نظيرَه بالبايت،
    # ولا ناقصَ ولا زائد. وفي وضع البناء يكشف أيضًا ما يكتبه البناءُ في `public/` ولا يكتبه
    # في غيره (فرعٌ على `MIHRAB_SITE_OUT`)، فيُشحَن ما لم يُقَس.
    import tempfile as _tf2
    with _tf2.TemporaryDirectory(prefix="mihrab-clean-") as _cd:
        _clean = os.path.join(_cd, "out")
        try:
            _cr = subprocess.run([sys.executable, os.path.join(SITE, "build.py")], cwd=ROOT,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 env=dict(os.environ, MIHRAB_SITE_OUT=_clean, PYTHONIOENCODING="utf-8"),
                                 timeout=120)
        except subprocess.TimeoutExpired:
            need(False, lambda: "[OUT-02] البناءُ النظيفُ للمقارنة لم ينتهِ في 120 ثانية")
        need(_cr.returncode == 0, lambda: "[OUT-02] البناءُ النظيفُ للمقارنة فشل (خرج %d): %s" % (
            _cr.returncode, " | ".join(_cr.stdout.decode("utf-8", "replace").strip().splitlines()[-3:])))

        def _linked(_p):
            return os.path.islink(_p) or getattr(os.path, "isjunction", lambda _x: False)(_p)

        def _tree(_root):
            _t = {}
            for _dp, _dn, _fs in os.walk(_root):
                # **لا وصلةَ في المخرَج، مجلّدًا ولا ملفًّا**: ‏`os.walk` لا ينزل في وصلة مجلّد فتغيب
                # عن الطرفين ويتطابقان، و`open` يتبع وصلةَ الملفّ فيطابق محتواها — و`tar` في
                # `deploy_site.sh` يحزم الوصلةَ كما هي فيُنشَر ما وراءها. و`islink` لا يرى
                # junction ويندوز (والنشرُ يجري من ويندوز)، فـ`isjunction` معه.
                for _d in list(_dn):
                    if _linked(os.path.join(_dp, _d)):
                        bad("[OUT-02] ‏`%s` وصلةٌ في المخرَج — لا تُقارَن ولا يكتبها البناء"
                            % os.path.relpath(os.path.join(_dp, _d), _root).replace(os.sep, "/"))
                        _dn.remove(_d)
                _dn.sort()
                for _f in sorted(_fs):
                    _fp = os.path.join(_dp, _f)
                    if _linked(_fp):
                        bad("[OUT-02] ‏`%s` وصلةٌ في المخرَج — لا تُقارَن ولا يكتبها البناء"
                            % os.path.relpath(_fp, _root).replace(os.sep, "/"))
                        continue
                    with open(_fp, "rb") as _fb:
                        _t[os.path.relpath(_fp, _root).replace(os.sep, "/")] = _fb.read()
            return _t
        _pub, _cln = _tree(OUT), _tree(_clean)
    # بناءٌ نجح ولم يكتب في المجلّد المؤقّت شيئًا لا يحترم `MIHRAB_SITE_OUT` — فكتب في
    # `site/public/` نفسِه. هذا عطبُ [OUT-01] لا «كلُّ الملفّات زائدة»، فيُسمّى باسمه.
    need(_cln, lambda: "[OUT-02] البناءُ النظيفُ نجح ولم يكتب في `MIHRAB_SITE_OUT` شيئًا — لا يحترم "
         "المتغيّرَ فيكتب في `site/public/`؛ لم يُبنَ شيءٌ [OUT-01]")
    for _rel in sorted(set(_cln) - set(_pub)):
        bad("[OUT-02] ‏`public/%s` غائب — البناءُ النظيفُ يكتبه والمخرَجُ ليس من هذا المصدر؛ أعِد البناء" % _rel)
    for _rel in sorted(set(_pub) - set(_cln)):
        bad("[OUT-02] ‏`public/%s` زائد — لا يكتبه بناءٌ نظيفٌ من هذا المصدر، فيُشحَن ما لم يُقَس" % _rel)
    for _rel in sorted(set(_pub) & set(_cln)):
        if _pub[_rel] != _cln[_rel]:
            bad("[OUT-02] ‏`public/%s` يخالف البناءَ النظيفَ بالبايت — المخرَجُ ليس من هذا المصدر؛ "
                "أعِد البناء" % _rel)
    if fails:
        report()
        return 1

    home = read("index.html")
    dl = read("download/index.html")
    kbd = read("keyboard/index.html")

    # ── ٢) مراسي site.js ──
    # كلُّ واحدٍ منها عقدٌ بين المولِّد والسكربت. كسرُه لا يرمي خطأً: الزرُّ يبقى
    # على نصّه المحافظ والجدولُ يبقى فارغًا، والصفحةُ تبدو «قيد الإعداد».
    for sel, page, name in [("data-dl-primary", home, "index.html"),
                            ("data-dl-meta", home, "index.html"),
                            ("data-dl-pick", dl, "download/index.html"),
                            ("data-dl-table", dl, "download/index.html"),
                            ("data-dl-empty", dl, "download/index.html"),
                            ("data-dl-wrap", dl, "download/index.html"),
                            ("data-dl-version", dl, "download/index.html"),
                            ('id="site-platforms"', home, "index.html"),
                            ('id="baked-releases"', home, "index.html"),
                            ('id="site-platforms"', dl, "download/index.html"),
                            ('id="baked-releases"', dl, "download/index.html")]:
        if sel not in page:
            bad("مِرساةٌ مفقودة في %s: %s" % (name, sel))

    # ── [PRIV-01] ⭐ دعوى الخصوصيّة مضبوطةٌ بقدرِ ما يُبرهَن عليه ───────────
    # جملةُ خصوصيّةٍ تكذب أسوأُ من غيابها: «بلا تتبّع» مجرّدةً أوسعُ ممّا نبرهن
    # عليه — الخادمُ يكتب سجلَّ طلباتٍ فيه عنوانُ من طلب. فالدعوى ضُيِّقت إلى ما
    # يُفحَص في الصفحة نفسِها: لا كعكةَ ولا سكربتَ في هذه الصفحة.
    if "بلا حساب، وبلا تتبّع." in home:
        bad("[PRIV-01] الصفحةُ الأولى تُعلن «بلا تتبّع» مجرّدةً — دعوى أوسعُ ممّا "
            "يُبرهَن عليه: الخادمُ يكتب سجلَّ طلباتٍ فيه عنوانُ من طلب. الصيغةُ "
            "المضبوطةُ تحدّد ما يُفحَص في هذه الصفحة: لا كعكةَ ولا سكربتَ تتبّع")
    if "وبلا كعكةٍ ولا سكربتِ تتبّعٍ في هذه الصفحة" not in home:
        bad("[PRIV-01] الصفحةُ الأولى بلا الدعوى المضبوطة — وهي التي تُفحَص فعلًا "
            "بحارسِ «لا سكربتَ داخليًّا في مخرَج الموقع»")

    # ── [PRIV-02] لا دعوى خصوصيّةٍ إلّا المضبوطة، ولا ما يكذّبها في المخرَج ──
    # ‏[PRIV-01] يطابق جملةً واحدةً حرفيًّا، فكانت تمرّ (قِيس بالزرع): دعوى عامّةٌ **بجانب**
    # المضبوطة («… في هذه الصفحة. ولا نتتبّعك أبدًا.»)، وكعكةٌ تُكتب في site.js تكذّب
    # «بلا كعكة» نفسَها. فيُقاس الطرفان: كلُّ ذكرٍ للتتبّع أو الكعكة في نصّ **أيّ** صفحةٍ
    # خارجَ الجملة المضبوطة عطب، وJS المخرَج لا يكتب كعكةً ولا يبلّغ أصلًا آخر، و
    # `localStorage` لمفتاحَي التفضيل وحدَهما (السمةُ والنظام: اختيارٌ لا هويّة).
    _PRIV_OK = "بلا حساب، وبلا كعكةٍ ولا سكربتِ تتبّعٍ في هذه الصفحة"
    _PRIV_WORD = re.compile(r"[نيت]?تتب[ً-ْ]*ع|كعك|كوكي|cookie", re.I)
    for _pf in sorted(glob.glob(os.path.join(OUT, "**", "*.html"), recursive=True)):
        with open(_pf, encoding="utf-8") as _pff:
            _pt = re.sub(r"<(script|style)\b.*?</\1>", " ", _pff.read(), flags=re.S)
        _pt = _html.unescape(re.sub(r"<[^>]+>", " ", _pt)).replace(_PRIV_OK, " ")
        _pt = " ".join(_pt.split())
        for _pm in _PRIV_WORD.finditer(_pt):
            bad("[PRIV-02] %s يذكر «%s» خارج الدعوى المضبوطة: «…%s…»"
                % (os.path.relpath(_pf, OUT).replace(os.sep, "/"), _pm.group(0),
                   _pt[max(0, _pm.start() - 40):_pm.end() + 40]))
    _PRIV_KEYS = {"mihrab-docs-theme", "mihrab-docs-platform"}
    for _jf in sorted(glob.glob(os.path.join(OUT, "assets", "*.js"))):
        with open(_jf, encoding="utf-8") as _jff:
            _jt = _jff.read()
        _jn = "assets/" + os.path.basename(_jf)
        for _pat, _why in ((r"document\.cookie", "يكتب كعكةً أو يقرؤها"),
                           (r"navigator\.sendBeacon|new\s+Image\s*\(|XMLHttpRequest|WebSocket|EventSource",
                            "يبلّغ بقناةٍ غيرِ `fetch` النسبيّ"),
                           (r"""["'`](?:https?:)?//(?!mihrab\.dev[/"'`])""", "فيه عنوانٌ مطلقٌ إلى أصلٍ آخر")):
            for _jm in re.finditer(_pat, _jt):
                bad("[PRIV-02] %s %s: «%s»" % (_jn, _why, _jt[_jm.start():_jm.start() + 60].split("\n")[0]))
        for _km in re.finditer(r"""localStorage\.setItem\(\s*['"]([^'"]*)['"]""", _jt):
            if _km.group(1) not in _PRIV_KEYS:
                bad("[PRIV-02] %s يحفظ في localStorage مفتاحًا غيرَ التفضيلَين: %r" % (_jn, _km.group(1)))

    # ── [OUT-03] المخرَجُ لا يحمل ما ليس من المصدر، ولا يحمّل من أصلٍ آخر ──
    # ‏[OUT-02] يقابل `public/` ببناءٍ نظيف، فلا يرى ما يكتبه **البناءُ نفسُه** وليس من المصدر:
    # مولِّدٌ يُخرج ملفًّا بلا مصدرٍ في `site/assets` يكتبه في البناءين معًا فيتطابقان. فكلُّ
    # ملفٍّ في `public/assets` إمّا له مصدرٌ أو هو مولَّدٌ معلَن (‏`fonts.css`،
    # ‏`preview-alif.js`)، ولا CSS
    # مخرَجٌ يستورد (`@import`) أو يحمّل `url()` من أصلٍ آخر، ولا صفحةٌ تحمّل موردًا من غير
    # أصلها — فـ`@import url(https://…)` في مولَّدٍ معطوبٍ كان يُشحَن ويكذّب الخصوصيّة.
    _GENERATED = {"fonts.css", "preview-alif.js"}
    _src_root = os.path.join(SITE, "assets")
    for _dp, _dn, _fn in os.walk(os.path.join(OUT, "assets")):
        for _f in _fn:
            _rel = os.path.relpath(os.path.join(_dp, _f), os.path.join(OUT, "assets")).replace(os.sep, "/")
            if _rel not in _GENERATED and not os.path.isfile(os.path.join(_src_root, _rel)):
                bad("[OUT-03] ‏`public/assets/%s` بلا مصدرٍ في `site/assets` وليس مولَّدًا معلَنًا — بائتٌ يُشحَن" % _rel)
    for _cf in sorted(glob.glob(os.path.join(OUT, "**", "*.css"), recursive=True)):
        with open(_cf, encoding="utf-8") as _cff:
            _ct = _cff.read()
        _cn = os.path.relpath(_cf, OUT).replace(os.sep, "/")
        # بلا تعليقات: «لا ‎@import‎ هنا» في تعليقٍ ليس استيرادًا (والماسحُ يحفظ السلاسلَ و`url(`).
        _ct = css_strip_comments(_ct, _cn)
        # ‏`re.I`: قواعدُ `@` وأسماءُ الدوالّ في CSS لا تفرّق بين الأحرف — `@IMPORT` و`URL(`
        # تُحمَّل كما تُحمَّل الصغيرة، وكانت تمرّ (قِيس بالزرع).
        for _cm in re.finditer(r"@import\b|url\(\s*['\"]?(?:https?:)?//", _ct, re.I):
            bad("[OUT-03] %s يحمّل من خارجه: «%s»" % (_cn, _ct[_cm.start():_cm.start() + 70].split("\n")[0]))
    _RES = re.compile(r"""<(script|link|img|iframe|source|video|audio|embed|object)\b[^>]*?\b(src|href|data)\s*=\s*["']((?:https?:)?//[^"'/]+)""", re.I)
    for _pf in sorted(glob.glob(os.path.join(OUT, "**", "*.html"), recursive=True)):
        with open(_pf, encoding="utf-8") as _pff:
            _ph = _pff.read()
        for _rm in _RES.finditer(_ph):
            # الأصلُ من `site.json` لا مكتوبًا هنا — كما في [W404]: يُغيَّر في مكانٍ واحد.
            if _rm.group(3).lower() != data["canonical"].rstrip("/").lower():
                bad("[OUT-03] %s يحمّل موردًا من أصلٍ آخر: <%s %s=\"%s…\">"
                    % (os.path.relpath(_pf, OUT).replace(os.sep, "/"), _rm.group(1), _rm.group(2), _rm.group(3)))

    # ── [MIN-01] تجريدُ التعليقات وقتَ البناء لا يغيّر إلّا التعليقات ──
    # البناءُ يجرّد تعليقاتِ CSS (‏`site/sitegen/strip.py`). وماسحُ الحارس (‏`css_strip_comments`)
    # **مستقلٌّ عنه**: يجرّد المصدرَ بنفسه، ويُشترط أن يطابق الناتجُ المنشورَ بعد توحيد المسافات —
    # فمجرِّدٌ يبتلع سلسلةً فيها `/*` أو `url(data:…*/…)`، أو يحذف ما ليس تعليقًا، يُرى هنا.
    # (ولو كان الماسحُ واحدًا لشهد لنفسه.) ولا تعليقَ يبقى في المنشور.
    for _cn in sorted(os.listdir(os.path.join(SITE, "assets"))):
        if not _cn.endswith(".css"):
            continue
        with open(os.path.join(SITE, "assets", _cn), encoding="utf-8") as _mf:
            _msrc = _mf.read()
        _mpub = read("assets/" + _cn)
        _mnorm = lambda _t: re.sub(r"\s+", " ", _t).strip()
        check(_mnorm(css_strip_comments(_msrc, _cn)) == _mnorm(_mpub), lambda: "[MIN-01] ‏`public/assets/%s` ليس "
              "المصدرَ بلا تعليقاته — المجرِّدُ غيّر ما ليس تعليقًا" % _cn)
        check(_mnorm(css_strip_comments(_mpub, _cn)) == _mnorm(_mpub), lambda: "[MIN-01] ‏`public/assets/%s` ما زال "
              "يحمل تعليقًا — المجرِّدُ لم يجرّد" % _cn)

    # و**JS يُجرَّد سطريًّا** (أسطرُ التعليق الكاملة وحدَها؛ انظر `strip_js`). والشاهدُ هنا مستقلٌّ
    # عنه: (١) المنشورُ أسطرُ المصدر نفسُها بترتيبها — حذفٌ لا تعديل؛ (٢) كلُّ سطرٍ محذوفٍ تعليقٌ
    # بعدّ الحارس (داخلَ `/* … */` يبدأ في أوّل سطره، أو `//` في أوّله)؛ (٣) لا سطرَ تعليقٍ كاملٍ
    # باقٍ؛ (٤) ‏`node --check` يقبل المنشور.
    _node_chk = shutil.which("node")
    for _jn in sorted(os.listdir(os.path.join(SITE, "assets"))):
        if not _jn.endswith(".js"):
            continue
        with open(os.path.join(SITE, "assets", _jn), encoding="utf-8") as _jf:
            _jsrc = _jf.read().split("\n")
        _jpub = read("assets/" + _jn).split("\n")
        _k, _inb, _bad = 0, False, []
        for _no, _ln in enumerate(_jsrc, 1):
            _st = _ln.lstrip()
            _is_c = _inb or _st.startswith("//") or _st.startswith("/*")
            if _st.startswith("/*") and not _inb:
                _inb = "*/" not in _st[2:]
            elif _inb and "*/" in _ln:
                _inb = False
            if _k < len(_jpub) and _jpub[_k] == _ln and not _is_c:
                _k += 1
            elif _is_c:
                continue
            else:
                _bad.append(_no)
        check(_k == len(_jpub) and not _bad, lambda: "[MIN-01] ‏`public/assets/%s` ليس المصدرَ بلا أسطر تعليقه — "
              "أسطرُ شيفرةٍ حُذفت أو تغيّرت (المصدر: %s)" % (_jn, _bad[:5] or "زيادةٌ في المنشور"))
        _left = [_n for _n, _l in enumerate(_jpub, 1) if _l.lstrip().startswith(("//", "/*"))]
        check(not _left, lambda: "[MIN-01] ‏`public/assets/%s` ما زال يحمل سطرَ تعليقٍ كاملًا: %s" % (_jn, _left[:5]))
        if _node_chk:
            _nc = subprocess.run([_node_chk, "--check", os.path.join(OUT, "assets", _jn)],
                                 capture_output=True, encoding="utf-8", errors="replace", timeout=60)
            check(_nc.returncode == 0, lambda: "[MIN-01] ‏`node --check` يرفض `public/assets/%s`: %s"
                  % (_jn, (_nc.stderr.strip().splitlines() or ["?"])[-1]))

    # ── [MIN-02] سقفُ الحجم المضغوط لكلّ أصلٍ نصّيّ ──
    # ما يُنزِّله الزائرُ فعلًا (gzip، المستوى 9): التجريدُ أنزل أوراقَ CSS من ‎16.4‎/‎10.6‎ ك.ب إلى
    # ‎3.9‎/‎2.7‎ (قِيس 2026-11-25). والسقفُ فوق القياس بنحو ‎15%‎: إعادةُ التعليقات (مجرِّدٌ
    # معطَّل) أو ملفٌّ يتضخّم بلا قرار يحمرّ هنا لا عند الزائر. ورفعُ السقف قرارٌ مكتوبٌ هنا.
    # وJS من ‎14.7‎/‎7.2‎ إلى ‎5.6‎/‎3.2‎.
    import gzip as _gz
    _GZ_CAP = {"mihrab-docs.css": 4500, "mihrab-home.css": 3100, "docs.js": 6400, "site.js": 3700}
    for _an, _cap in sorted(_GZ_CAP.items()):
        with open(os.path.join(OUT, "assets", _an), "rb") as _gf:
            _gzn = len(_gz.compress(_gf.read(), 9, mtime=0))
        check(_gzn <= _cap, lambda: "[MIN-02] ‏`public/assets/%s` مضغوطًا %d بايت فوق سقفه %d — تعليقاتٌ عادت "
              "أو تضخّمٌ بلا قرار؛ يُرفَع السقفُ في `_GZ_CAP` بتعليلٍ إن كان مقصودًا" % (_an, _gzn, _cap))

    # docs.js يخرج مبكّرًا بلا هذا الوسم، فيموت مبدّلُ النظام والترشيحُ والالتقاط.
    if "data-kbd-table" not in kbd:
        bad("keyboard/index.html بلا data-kbd-table — سلوكُ صفحة الاختصارات ميّتٌ صامتًا.")

    # ── ٣) جزيرةُ البيانات تُحلَّل فعلًا ──
    for name, page in (("index.html", home), ("download/index.html", dl)):
        for isle in ("site-platforms", "baked-releases"):
            m = re.search(r'id="%s">(.*?)</script>' % isle, page, re.S)
            if not m:
                continue
            try:
                json.loads(m.group(1).replace("<\\/", "</"))
            except ValueError as e:
                bad("جزيرةُ بياناتٍ غيرُ صالحة (%s في %s): %s" % (isle, name, e))

    # ── ٤) لا مساراتٍ مطلقةً إلى مضيفٍ بعينه ──
    # المخرَجُ نفسُه يُخدَم من mihrab.dev/ ومن almihrab.github.io/mihrab/.
    # رابطُ تنقّلٍ مطلقٌ واحدٌ إلى أحدهما يربط المرآةَ بالأصل ويرسل زوّارَها بعيدًا.
    #
    # ‏`<link rel=canonical>` مستثنًى: هو **يجب** أن يكون مطلقًا ويشير إلى الأصل —
    # وهذا بالضبط ما يمنع محرّكات البحث من معاملة المرآة كمحتوًى مكرّر.
    NAV = re.compile(r'<a\b[^>]*\bhref="([^"]+)"|<(?:img|script)\b[^>]*\bsrc="([^"]+)"')
    for rel in ("index.html", "download/index.html", "docs/index.html",
                "keyboard/index.html"):
        page = read(rel)
        for m in NAV.finditer(page):
            url = m.group(1) or m.group(2)
            # و`mihrab.dev` معهما: هو **أصلُ** هذا المخرَج الآن، ورابطٌ مطلقٌ إليه من داخله
            # يربط المرآةَ بالأصل ويرسل زوّارَها بعيدًا — وهي العلّةُ نفسُها.
            # (‏`app.mihrab.dev` مستثنًى: أصلٌ آخرُ فعلًا، والرابطُ إليه مقصود.)
            for host in ("almihrab.github.io", "https://mihrab.dev"):
                if host in url:
                    bad("رابطٌ مطلقٌ إلى مضيفٍ بعينه في %s: %s" % (rel, url))

    # ── ٤ب) كلُّ أصلٍ محلّيٍّ مُشار إليه موجودٌ في المخرَج ──
    # ‏`shots/` مجلّد، وناسخُ الأصول كان يتخطّى المجلّدات — فأشارت الصفحةُ الأولى إلى
    # لقطةٍ لا تُنسَخ: مستطيلٌ مكسورٌ فوق الطيّة والبناءُ أخضر.
    #
    # والثنائيّاتُ مستثناةٌ من شرطِ الوجود لا من الفحص: `dl/` يعيش **على الخادم**
    # بجوار الملفّات المرفوعة ويستثنيه سكربتُ النشر عمدًا، فلا وجودَ له في المخرَج
    # أصلًا. فيُطلَب منها شرطٌ أقوى بدلًا من ذلك: أن يكون الملفُّ المُشارُ إليه
    # **معلَنًا في المانيفست**. رابطُ تنزيلٍ باسمٍ لا يذكره المانيفست هو بالضبط
    # العطبُ الذي أراد هذا الفحصُ منعَه — و`Mihrab-Setup.exe` المتخيَّلُ سابقته.
    with open(os.path.join(SITE, "data", "releases.json"), encoding="utf-8") as f:
        _rel_manifest = json.load(f)
    DL_BASE = (_rel_manifest.get("base") or "dl/").strip("/") + "/"
    DL_FILES = {a["file"] for a in _rel_manifest.get("assets", []) if a.get("file")}

    # ── ٥) أوراقُ الأنماط: لا تعليقَ مبتورًا ولا نصًّا طليقًا في `:root` [CSS-01] ──
    # وقع فعلًا: تعليقٌ في `mihrab-docs.css` أُغلق بـ`*/` ثمّ بدأت فقرةٌ جديدةٌ
    # **بلا `/*`** — فصارت نصًّا طليقًا داخل `:root` يبتلع إعلانَ `--font-ar` كلَّه
    # حتّى فاصلته المنقوطة. المتصفّحُ لا يخطئ بصوت: يُسقِط الإعلانَ المشوَّه ويمضي،
    # فعُرض الموقعُ **كلُّه** بـ`Times New Roman` والوجوهُ الأربعةُ المورَّدةُ لم
    # تُحمَّل، وكلُّ حارسٍ أخضر — لأنّ الحرّاسَ كانوا يقيسون الوجوهَ والمدياتِ
    # والسلسلة، ولا أحدَ يقيس أنّ **السلسلةَ تصل المتصفّحَ إعلانًا صالحًا**.
    # (١) كلُّ `*/` يُغلق `/*` مفتوحًا ولا `/*` داخل تعليق — **في المصدر**: المنشورُ بلا تعليقات
    #     (تُجرَّد وقتَ البناء)، والتعليقُ المبتورُ في المصدر يُمسَك مرّتين: المجرِّدُ يرفضه فيفشل
    #     البناء، و[MIN-01] يمرّر المصدرَ على `css_strip_comments` فيرمي بوسم [CSS-01].
    # ثمّ على كلّ ورقةٍ بمحتواها **المنشور**: (٢) بعد نزع التعليقات، كلُّ جملةٍ داخل `:root` إعلانٌ
    # (`اسم: قيمة`) أو فراغ؛ (٣) وأوّلُ `--font-ar` **بعد النزع** هو الخطُّ
    # المورَّد — فتعليقٌ يبتلع الإعلانَ يُسقِط هذا الشرطَ لا محالة.
    _css_dir = os.path.join(SITE, "assets")
    _css_decl, _css_refs = set(), set()
    for _cn in sorted(os.listdir(_css_dir)):
        if not _cn.endswith(".css"):
            continue
        with open(os.path.join(OUT, "assets", _cn), encoding="utf-8") as _cf3:
            _raw3 = _cf3.read()
        # الماسحُ (تعليق/سلسلة/‏`url(` بلا اقتباس) هو نفسُه النازع: ما تُقاس عليه
        # الجملُ أدناه هو ما مرّ من الماسح حرفًا بحرف — لا نصٌّ ثانٍ من `re.sub`
        # ساذجٍ يبتلع من `"/*"` إلى أوّل `*/` (انظر `css_strip_comments`).
        _bare = css_strip_comments(_raw3, _cn)
        for _rm in re.finditer(r":root(?:[^{]*)\{([^}]*)\}", _bare):
            for _stmt in _rm.group(1).split(";"):
                _st = _stmt.strip()
                check(not _st or re.match(r"^[\w-]+\s*:", _st), lambda: "جملةٌ ليست إعلانًا داخل `:root` في %s: %r — نصٌّ طليقٌ يبتلع "
                    "الإعلانَ الذي يليه بلا خطأ [CSS-01]" % (_cn, _st[:60]))
                # ── ولا إعلانَ داخل إعلان ──
                # نصٌّ طليقٌ يبدأ بـ`كلمة:` (‏`todo: …` بلا علامتَي تعليق) يمرّ من
                # الشرط أعلاه ويبتلع `--font-ar: …` التي تليه حتّى الفاصلة المنقوطة،
                # والشرطُ الأخيرُ يجد `--font-ar:` داخل الجملة المبتلَعة فيمرّ —
                # قِيس بالطفرة: خضراءُ والموقعُ بخطّ المتصفّح. فجملةٌ تحمل `--اسم:`
                # بعد نقطتَيها الأولى هي ابتلاع.
                _tail = _st[_st.index(":") + 1:] if ":" in _st else ""
                check(not re.search(r"(?<![\w-])--[\w-]+\s*:", _tail), lambda: "إعلانٌ مبتلَعٌ داخل جملةٍ أخرى في `:root` في %s: %r — ما قبله "
                    "نصٌّ طليقٌ يُسقِط الإعلانَ كلَّه بلا خطأ [CSS-01]" % (_cn, _st[:60]))
        # ── وكلُّ `var(--x)` تشير إلى `--x` مُعلَنةٍ في ورقةٍ ما ──
        # `font-family: var(--font-arr)` (خطأُ طباعة) يجعل الإعلانَ **باطلًا وقتَ
        # الحساب**: `font-family` تصير `unset` فيرث الجسمُ خطَّ المتصفّح الافتراضيّ
        # — بلا خطأٍ في أيّ طبقة. قِيس بالطفرة: خضراء.
        _css_decl.update(re.findall(r"(?<![\w-])(--[\w-]+)\s*:", _bare))
        _css_refs.update(re.findall(r"var\(\s*(--[\w-]+)", _bare))
        # ── وسلسلتا الخطّ تُعلَنان في `:root` من `mihrab-docs.css` **وحدَها**،
        #    وتُستهلَكان بـ`var()` وحدَه ──
        # الشرطُ «آخرُ إعلانٍ في الورقة» يرى ما جاء **بعد** `:root` في الورقة
        # نفسِها ولا يرى: `body { --font-ar: serif }` **قبلها** (إعلانُ العنصر
        # يغلب الموروثَ أيًّا كان ترتيبُه)، ولا إعلانًا في `mihrab-home.css`
        # (تُحمَّل بعدها فتغلب)، ولا `body { font: 17px serif }` (المختصَرُ يُعيد
        # `font-family` بلا `var()`). قِيست الثلاثُ بالطفرة: خضراء. فتُحصَر
        # السلسلتان في `:root` من ورقةٍ واحدة، وكلُّ `font-family` تشير إليهما.
        _root_txt = "".join(m.group(1) for m in re.finditer(r":root(?:[^{]*)\{([^}]*)\}", _bare))
        for _prop in ("--font-ar", "--font-mono"):
            _n_all = len(re.findall(r"(?<![\w-])%s\s*:" % _prop, _bare))
            _n_root = len(re.findall(r"(?<![\w-])%s\s*:" % _prop, _root_txt))
            check(_n_all == _n_root and (_cn == "mihrab-docs.css" or _n_all == 0), lambda: "‏`%s` مُعلَنةٌ خارج `:root` أو خارج `mihrab-docs.css` (في %s) — إعلانُ "
                "عنصرٍ أو ورقةٍ لاحقةٍ يغلب سلسلةَ الخطّ المورَّد صامتًا [CSS-01]"
                % (_prop, _cn))
        for _ff in re.findall(r"(?<![\w-])font-family\s*:\s*([^;}]+)", _bare):
            check(re.fullmatch(r"var\(--font-(ar|mono)\)|inherit", _ff.strip()), lambda: "‏`font-family: %s` في %s لا تشير إلى `--font-ar`/`--font-mono` — خطٌّ "
                "خارج السلسلة المورَّدة [CSS-01]" % (_ff.strip()[:50], _cn))
        check(not re.search(r"(?<![\w-])font\s*:", _bare), lambda: "مختصَرُ `font:` في %s يُعيد `font-family` إلى قيمةٍ بلا `var()` فيُسقِط "
            "الخطَّ المورَّد صامتًا — يُكتَب `font-family`/`font-size` مفصَّلةً [CSS-01]" % _cn)
        if _cn == "mihrab-docs.css":
            _fa = re.findall(r"--font-ar\s*:\s*([^;}]+)[;}]", _bare)
            need(_fa, lambda: "لا `--font-ar` صالحٌ في `mihrab-docs.css` بعد نزع التعليقات [CSS-01]")
            _fa0 = _fa[-1].strip().split(",")[0].strip().strip("\"'")
            check(_fa0 == "IBM Plex Sans Arabic", lambda: "أوّلُ `--font-ar` الفعليُّ هو %r — الخطُّ المورَّد لا يصل أحدًا "
                "[CSS-01]" % _fa0)
            # ── والقائمةُ كلُّها قائمةُ خطوطٍ صالحة، لا أوّلُها وحدَه ──
            # الخاصّيّةُ المخصَّصة تقبل أيَّ رموز، والبطلانُ لا يظهر إلّا حين تُستبدَل
            # في `font-family`: فاصلةٌ ناقصةٌ بين اسمين، أو فاصلةٌ زائدةٌ في الآخر،
            # أو اسمٌ فيه رقمٌ بلا اقتباس (`Noto Sans Symbols 2`)، أو `inherit` في
            # القائمة — كلُّها تجعل `font-family` باطلةً وقتَ الحساب فتصير `unset`،
            # والموقعُ بخطّ المتصفّح الافتراضيّ والأوّلُ في القائمة سليم. قِيست
            # الأربعُ بالطفرة: خضراء. فكلُّ عنصرٍ إمّا سلسلةٌ مقتبسةٌ وإمّا معرِّفاتٌ
            # متتاليةٌ بلا رقمٍ في أوّلها، وليس كلمةً من كلمات CSS العامّة.
            _css_wide = {"inherit", "initial", "unset", "revert", "revert-layer", "default"}
            for _prop in ("--font-ar", "--font-mono"):
                _vals = re.findall(r"%s\s*:\s*([^;}]+)[;}]" % _prop, _bare)
                need(_vals, lambda: "لا `%s` في `mihrab-docs.css` [CSS-01]" % _prop)
                for _item in _vals[-1].split(","):
                    _it = _item.strip()
                    _ok_item = bool(_it) and _it.lower() not in _css_wide and bool(
                        re.fullmatch(r'"[^"]+"|\'[^\']+\'', _it)
                        or re.fullmatch(r"-?[A-Za-z_][\w-]*(\s+-?[A-Za-z_][\w-]*)*", _it))
                    need(_ok_item, lambda: "عنصرٌ ليس اسمَ خطٍّ صالحًا في `%s`: %r — يُبطِل `font-family` "
                        "كلَّها وقتَ الحساب فيسقط الموقعُ إلى خطّ المتصفّح الافتراضيّ "
                        "بلا خطأ [CSS-01]" % (_prop, _it[:60]))
    _undef = sorted(_css_refs - _css_decl)
    check(not _undef, lambda: "‏`var()` تشير إلى خاصّيّةٍ لا تُعلِنها أيُّ ورقة: %s — الإعلانُ المستعمِلُ "
        "يبطل وقتَ الحساب ويصير `unset` بلا خطأ [CSS-01]" % "، ".join(_undef))

    # ── ٥أ) أوجهُ الخطّ مورَّدةٌ وكاملةٌ ومتوازنة [FNT-01] ──
    # محرابٌ دعواه أنّ العربيّةَ فيه **أصلٌ لا قشرةٌ مضافة**. و`IBM Plex Sans
    # Arabic` غيرُ منصَّبٍ على أيّ نظامٍ من الثلاثة، و`Noto Sans Arabic` غيرُ
    # منصَّبٍ على ويندوز — وأكثرُ الجمهور على ويندوز. فبلا توريدٍ يُعرَض الموقعُ
    # بـ`Segoe UI`: تصميمٌ لم يره أحدٌ منّا على شاشته، وتُنقَض الدعوى في أوّل سطر.
    #
    # ويُقاس ستّةٌ لأنّ كلًّا منها وقع فعلًا أو كاد:
    #   ١) **كلُّ** وجهٍ تُعلِنه `FONT_FACES` مورَّدٌ — لا بعضُها. والنقصُ الجزئيُّ
    #      **أسوأُ من التامّ**: وجهٌ عربيٌّ بلا نظيرِه اللاتينيِّ يجعل السطرَ
    #      المختلَطَ بخطَّين، بينما النقصُ التامُّ يُبقيه متّسقًا بخطٍّ واحد.
    #   ٢) والملفُّ **مكتمِل**: تنزيلٌ ينقطع يترك woff2 مبتورًا يقبله `file` ولا
    #      يقبله المتصفّح — فيسقط صامتًا إلى خطّ النظام بلا خطأٍ في أيّ طبقة.
    #      والطولُ المُعلَن في ترويسة woff2 هو ما يُقابَل بالحجم على القرص.
    #   ٣) و`unicode-range` على كلّ وجه: الأوجهُ مقلَّمة، ووجهان بالاسم والوزن
    #      نفسِهما بلا مدًى **يتنازعان** — يأخذ المتصفّحُ الأخيرَ ويهمل الأوّلَ
    #      (لا سقوطَ بين وجهَي العائلة الواحدة). فنصفُ الموقع بخطٍّ ونصفُه بآخر.
    import hashlib as _hashlib
    import struct as _struct

    # ── جردٌ **مستقلّ** لا مرآةٌ للمولِّد ──
    # المرجعُ كان `FONT_FACES` في `build.py` — وهو **وعدٌ يملكه المُقاس نفسُه**.
    # قِيس بالطفرة: حذفُ وجهَي اللاتينيّة من `FONT_FACES` أنقصَ الوعدَ والقياسَ معًا
    # فمرّ أخضرَ، والموقعُ يُعرَض بلا لاتينيّةٍ مورَّدة. والشاهدُ المستقلُّ وحدَه
    # يمسك ذلك: الجردُ مكتوبٌ **هنا**، وبصمةُ كلّ ملفٍّ معه.
    #
    # والبصمةُ لا الطولُ وحدَه: ملفٌّ سليمُ الترويسةِ فاسدُ المحتوى يمرّ من فحص
    # الطول (قِيس: قَلْبُ ‎200‎ بايتٍ في الوسط مرّ أخضر)، و**استبدالُ الوجه العربيّ
    # بنسخةٍ من اللاتينيّ** يمرّ منه كذلك — وهو أسوأُ ما يمكن أن يقع بهذا الملفّ:
    # الموقعُ يَعِد بخطٍّ عربيٍّ ويسلّم ملفًّا بلا حرفٍ عربيٍّ واحد، بلا ‎404‎ ولا خطأ.
    #
    # ⚠️ ومن غيّر وجهًا عمدًا يُحدِّث بصمتَه هنا: تلك هي البوّابةُ لا عائقُها.
    EXPECT_FACES = [
        ("plex-arabic-400.woff2", "IBM Plex Sans Arabic", 400,
         "6010e7fd0dce5d527583951750728cbe3c895efbd16aa0f809ab8c824878c9d8"),
        ("plex-arabic-600.woff2", "IBM Plex Sans Arabic", 600,
         "16734a5adb27b0f363e566cbbeacec480da0dc0baa19c8f0053251c2e2bc0eac"),
        ("plex-latin-400.woff2", "IBM Plex Sans Arabic", 400,
         "9ed8dcb02e6c7246de4c120295fafa39a7bb73085f4951a4524a07dc911069f2"),
        ("plex-latin-600.woff2", "IBM Plex Sans Arabic", 600,
         "63f4757271e403f7baec0862f284ffaa4560ea6096ba9fe8bc6e585ca656e724"),
        # والاسمُ الثاني للملفَّين العربيَّين — لسلسلة أحاديّ المسافة: الملفُّ
        # عينُه والبصمةُ عينُها، والعائلةُ غيرُها. ويُقاس مداه أسفلَه.
        ("plex-arabic-400.woff2", "Mihrab Code Arabic", 400,
         "6010e7fd0dce5d527583951750728cbe3c895efbd16aa0f809ab8c824878c9d8"),
        ("plex-arabic-600.woff2", "Mihrab Code Arabic", 600,
         "16734a5adb27b0f363e566cbbeacec480da0dc0baa19c8f0053251c2e2bc0eac"),
    ]
    MONO_AR_FAMILY = "Mihrab Code Arabic"

    css_path = os.path.join(OUT, "assets", "fonts.css")
    need(os.path.isfile(css_path), lambda: "لا `assets/fonts.css` في المخرَج [FNT-01]")
    with open(css_path, encoding="utf-8") as _f:
        fcss = _f.read()

    declared = re.findall(r'url\("fonts/([^"]+)"\)', fcss)
    # ── والمرجعُ `FONT_FACES` في المولِّد، لا مجلّدُ المصدر ──
    # أوّلُ صياغةٍ قابلت المُعلَنَ في `fonts.css` بما في `site/assets/fonts/` —
    # وهما يتقلّصان معًا: `write_fonts_css` لا يُعلِن إلّا الموجود، فحذفُ ملفٍّ
    # يُنقِص الطرفين ويبقى الحارسُ أخضر. قِيس بالطفرة: حذفُ وجهٍ لاتينيٍّ مرّ.
    # والمرجعُ الصحيحُ هو **ما يَعِد به المولِّد**: قائمةُ `FONT_FACES`.
    with open(os.path.join(SITE, "sitegen", "fonts.py"), encoding="utf-8") as _bf:
        _blk = _bf.read()
    _i = _blk.index("FONT_FACES = [")
    wanted = re.findall(r'\("([^"]+\.woff2)"', _blk[_i:_blk.index("]", _i)])
    check(len(wanted) >= 2, lambda: "تعذّر قراءةُ `FONT_FACES` من `site/sitegen/fonts.py` — تغيّرت صيغتُها؛ "
        "يُحدَّث الحارس [FNT-01]")
    # والوعدُ يُقابَل بالجرد المستقلّ: تقليصُ `FONT_FACES` عطبٌ لا إعفاء.
    _shrunk = [n for n, _f, _w, _h in EXPECT_FACES if n not in wanted]
    check(not _shrunk, lambda: "وجهٌ يشترطه الجردُ ولا تَعِد به `FONT_FACES` في `site/sitegen/fonts.py`: %s — "
        "وتقليصُ الوعد يُنقِص المُقاسَ والقياسَ معًا فيمرّ أخضر. من أسقط وجهًا "
        "عمدًا يُسقِطه من `EXPECT_FACES` هنا بتعليلٍ مكتوب [FNT-01]"
        % "، ".join(_shrunk))

    missing = [n for n in wanted if n not in declared]
    check(not missing, lambda: "وجهٌ تَعِد به `FONT_FACES` ولا يُعلِنه `fonts.css`: %s. والنقصُ الجزئيُّ "
        "**أسوأُ من التامّ**: وجهٌ عربيٌّ بلا نظيرِه اللاتينيِّ يجعل السطرَ المختلَطَ "
        "بخطَّين، بينما النقصُ التامُّ يُبقيه متّسقًا بخطٍّ واحد. ضَع الملفَّ في "
        "`site/assets/fonts/` [FNT-01]" % "، ".join(missing))

    for name in declared:
        out_f = os.path.join(OUT, "assets", "fonts", name)
        check(os.path.isfile(out_f), lambda: "‏`fonts.css` يُعلِن %s ولا وجودَ له في المخرَج — ‎404‎ في كلّ فتحةِ "
            "صفحة ثمّ سقوطٌ صامتٌ إلى خطّ النظام [FNT-01]" % name)
        with open(out_f, "rb") as _ff:
            raw = _ff.read()
        check(raw[:4] == b"wOF2", lambda: "%s ليس woff2 [FNT-01]" % name)
        (dlen,) = _struct.unpack(">I", raw[8:12])
        check(dlen == len(raw), lambda: "%s مبتور: يُعلِن %d بايتًا وعلى القرص %d — يرفضه المتصفّحُ ويسقط "
            "صامتًا إلى خطّ النظام [FNT-01]" % (name, dlen, len(raw)))

    # ── والبصمةُ والعائلةُ والوزن، لا الوجودُ وحدَه ──
    for _fn, _fam, _wt, _sha in EXPECT_FACES:
        _p = os.path.join(OUT, "assets", "fonts", _fn)
        check(os.path.isfile(_p), lambda: "وجهُ الجرد %s غائبٌ عن المخرَج [FNT-01]" % _fn)
        _got = _hashlib.sha256(open(_p, "rb").read()).hexdigest()
        check(_got == _sha, lambda: "بصمةُ %s لا تطابق الجرد (%s… بدل %s…) — وفحصُ الطول يمرّ على ملفٍّ "
            "فاسدِ المحتوى وعلى وجهٍ وُضِع مكانَ آخر. إن كان التغييرُ مقصودًا "
            "فحدِّث `EXPECT_FACES` [FNT-01]" % (_fn, _got[:12], _sha[:12]))
        # الزوجُ (عائلة، ملفّ) لا الملفُّ وحدَه: الملفُّ العربيُّ يُعلَن مرّتين
        # باسمين، وقياسُ «أوّلِ وجهٍ يحمل الملفّ» كان يرى الأوّلَ ويعمى عن الثاني.
        _fm = re.search(r'@font-face\{font-family:"' + re.escape(_fam)
                        + r'";src:url\("fonts/' + re.escape(_fn)
                        + r'"\)[^}]*?font-weight:(\d+)', fcss)
        need(_fm, lambda: "لا `@font-face` باسم «%s» لـ%s في `fonts.css` — عائلةٌ غائبةٌ أو "
            "مغايرةٌ لا تصل السلسلةَ أصلًا [FNT-01]" % (_fam, _fn))
        check(int(_fm.group(1)) == _wt, lambda: "‏%s باسم «%s» مُعلَنٌ بوزن %s والجردُ يقول %d — وزنٌ مكرّرٌ يترك "
            "الغامقَ اصطناعيًّا [FNT-01]" % (_fn, _fam, _fm.group(1), _wt))

    # ── وكلُّ صفحةٍ في المخرَج **تحمل** الورقةَ ──
    # الأوجهُ المورَّدةُ لا تصل صفحةً لا تربط `fonts.css`. وصفحةُ `preview/alif/`
    # تُبنى خارج `page_shell` بورقةٍ داخليّةٍ خاصّة — فكانت الصفحةَ الوحيدةَ في
    # الموقع التي تُعرَض بخطّ النظام، والحارسُ أعلاه أخضر لأنّه يقيس الورقةَ
    # لا من يستعملها. فيُقاس الاستعمالُ: كلُّ HTML في المخرَج يحمل رابطًا نسبيًّا
    # إلى `assets/fonts.css` **يصل فعلًا** من مكان الصفحة.
    _unlinked = []
    with open(os.path.join(SITE, "data", "site.json"), encoding="utf-8") as _sj0:
        _canon_pref = json.load(_sj0)["canonical"].rstrip("/") + "/"
    for base, _dirs, names in os.walk(OUT):
        for n in names:
            if not n.endswith(".html"):
                continue
            _p = os.path.join(base, n)
            with open(_p, encoding="utf-8") as _hf0:
                _t0 = _hf0.read()
            # تعليقُ HTML يُجرَّد أوّلًا: رابطٌ داخل `<!-- -->` لا يُحمَّل.
            _t0 = re.sub(r"<!--.*?-->", "", _t0, flags=re.S)
            # وليس `fonts.css` وحدَها: تعليقُ HTML حول `mihrab-docs.css` كان يمرّ
            # (الحارسُ قاس ورقةً واحدة). فكلُّ `<link rel=stylesheet>` يجب أن يصل،
            # وكلُّ صفحةٍ من القالب (لا المعاينةُ) تحمل ورقةَ التوثيق.
            _relp0 = os.path.relpath(_p, OUT).replace(os.sep, "/")
            # ترتيبُ السمات لا يهمّ المتصفّحَ فلا يهمّ الحارس: `href` قبل `rel` كان
            # يُخرج الورقةَ من القياس صامتًا (ملاحظةُ أيمليا).
            for _sm in re.finditer(r'<link\b[^>]*>', _t0):
                _tag = _sm.group(0)
                if not re.search(r'\brel="stylesheet"', _tag):
                    continue
                _hm = re.search(r'\bhref="([^"]+)"', _tag)
                if not _hm:
                    continue
                _sh = _hm.group(1)
                if _sh.startswith(("http://", "https://")) and not _sh.startswith(_canon_pref):
                    continue
                _sh2 = _sh[len(_canon_pref) - 1:] if _sh.startswith(_canon_pref) else _sh
                _st = (os.path.normpath(os.path.join(OUT, _sh2.lstrip("/"))) if _sh2.startswith("/")
                       else os.path.normpath(os.path.join(base, _sh2)))
                check(os.path.isfile(_st), lambda: "ورقةُ أنماطٍ مربوطةٌ لا تصل: %s ← %s [FNT-01]" % (_relp0, _sh))
            if not _relp0.startswith("preview/"):
                check("mihrab-docs.css" in _t0, lambda: "صفحةُ قالبٍ بلا `mihrab-docs.css`: %s — تُعرَض عاريةً [FNT-01]" % _relp0)
            _lm = re.search(r'<link[^>]+href="([^"]*assets/fonts\.css)"', _t0)
            if not _lm:
                _unlinked.append(os.path.relpath(_p, OUT).replace(os.sep, "/"))
                continue
            _href = _lm.group(1)
            # صفحةُ ‎404‎ تربط بأصلٍ مطلقٍ عمدًا (تُقدَّم من أصلين) — فيُقصّ الأصلُ
            # المعتمَدُ وحدَه، وما سواه من المضيفين لا يصل.
            with open(os.path.join(SITE, "data", "site.json"), encoding="utf-8") as _sj:
                _canon0 = json.load(_sj)["canonical"].rstrip("/")
            if _href.startswith(_canon0 + "/"):
                _href = _href[len(_canon0):]
            _target = (os.path.normpath(os.path.join(OUT, _href.lstrip("/")))
                       if _href.startswith("/")
                       else os.path.normpath(os.path.join(base, _href)))
            if not os.path.isfile(_target):
                _unlinked.append("%s ← %s لا يصل" % (
                    os.path.relpath(_p, OUT).replace(os.sep, "/"), _href))
    check(not _unlinked, lambda: "صفحاتٌ في المخرَج بلا `fonts.css` صالحٍ — تُعرَض بخطّ النظام وحدَها بين "
        "صفحات الموقع، بلا خطأٍ في أيّ طبقة [FNT-01]:\n       "
        + "\n       ".join(sorted(_unlinked)[:10]))

    # ── وكلُّ محرفٍ **يراه الزائر** داخلَ المدَيَين، أو مسمًّى في قائمةٍ بيضاء ──
    # الحارسُ كان يحرس **الملفَّ**: وجودَه وطولَه ووجودَ `unicode-range` فيه.
    # ولم يكن يسأل السؤالَ الذي يهمّ: **أتغطّي المدَياتُ ما نكتبه فعلًا؟** فمرّت
    # `←` في تسع صفحاتٍ خضراءَ تمامًا — وهي فاصلُ مسار القوائم **داخل جملةٍ
    # عربيّةٍ متّصلة** («انقر عليه باليمين ← فتح»): سهمٌ من خطّ النظام بين كلمتين
    # من الخطّ المورَّد، أرفعُ قلمًا وأعلى موضعًا. والأسوأُ في `folders/`: كتلةُ
    # `<pre>` فيها ثلاثةُ خطوطٍ في سطرٍ واحد.
    #
    # والقائمةُ البيضاءُ ليست تساهلًا بل **إعلانُ حدّ**: ستّةُ رموزٍ تصويريّةٍ لا
    # يحملها IBM Plex ولا بديلَ لها فيه (‏`‹` و`›` موجودتان لكنّهما تنعكسان في
    # السياق اليمينيّ فتشيران إلى الجهة الخطأ). فالسقوطُ واقعٌ لا محالة، وقد
    # أُعلِن في سلسلة `--font-ar` بخطوطِ رموزٍ مسمّاةٍ لثلاثة أنظمة. ومحرفٌ
    # **جديدٌ** خارج المدَيَين يحمرّ هنا فيُقرَّر أمرُه قصدًا لا سهوًا.
    FONT_ALLOW = {
        "\u2190": "← فاصلُ مسار القوائم — لا سهمَ في IBM Plex، والبدائلُ تنعكس",
        "\u2197": "↗ مؤشّرُ رابطٍ خارجيّ في `.app-link::after`",
        "\u2318": "⌘ مفتاحُ ماك — رمزٌ لا مقابلَ له",
        "\u2325": "⌥ مفتاحُ ماك",
        "\u21E7": "⇧ مفتاحُ ماك",
        "\u2726": "✦ زخرفةٌ في `.trust span::before`",
    }

    # وكلُّ بندٍ في القائمة البيضاء **بتعليلٍ مكتوب**: مدخلٌ بنصٍّ فارغٍ كان
    # يمرّ أخضر، فيصير التوسيعُ سطرًا صامتًا بدل قرارٍ مكتوب — وهو نقضُ غرضِ
    # القائمة من أصله.
    for _ch, _why in FONT_ALLOW.items():
        check(_why.strip(), lambda: "بندٌ في `FONT_ALLOW` بلا تعليل (U+%04X) — القائمةُ البيضاءُ إعلانُ "
            "حدٍّ لا إعفاءٌ صامت [FNT-01]" % ord(_ch))

    def _ranges(var_name):
        m = re.search(var_name + r" = \(([^)]+)\)", bpy, re.S)
        need(m, lambda: "تعذّرت قراءةُ %s من `site/sitegen/fonts.py` [FNT-01]" % var_name)
        out = set()
        for part in "".join(re.findall(r'"([^"]*)"', m.group(1))).split(","):
            part = part.strip()
            if not part.startswith("U+"):
                continue
            body = part[2:]
            if "-" in body:
                lo, hi = body.split("-")
                out.update(range(int(lo, 16), int(hi, 16) + 1))
            else:
                out.add(int(body, 16))
        return out

    with open(os.path.join(SITE, "sitegen", "fonts.py"), encoding="utf-8") as _bf2:
        bpy = _bf2.read()
    ar_r, la_r = _ranges("_UR_AR"), _ranges("_UR_LA")
    overlap = ar_r & la_r
    check(not overlap, lambda: "تداخُلٌ بين `_UR_AR` و`_UR_LA` في %d نقطةً (أوّلُها U+%04X) — مقطعٌ "
        "يطالب به وجهان بالعائلة والوزن نفسِهما يفوز فيه الأخيرُ إعلانًا، فتُسنَد "
        "محارفُ عربيّةٌ إلى الملفّ اللاتينيّ بلا أن يقول أحدٌ ذلك [FNT-01]"
        % (len(overlap), min(overlap)))
    covered = ar_r | la_r

    missing = {}
    # وأوراقُ الأنماط معها: `content:` تُرسَم نصًّا (‏`↗` و`✦` منها).
    for _css in sorted(os.listdir(os.path.join(OUT, "assets"))):
        if not _css.endswith(".css"):
            continue
        with open(os.path.join(OUT, "assets", _css), encoding="utf-8") as _cf2:
            # بلا تعليقات: `content: "✦"` **مذكورةٌ في تعليقٍ** لا تُرسَم، وكانت
            # تُقاس فتحمرّ على محرفٍ لا يراه أحد.
            _ccss = css_strip_comments(_cf2.read(), "assets/" + _css)
            for _cm in re.finditer(r'content\s*:\s*"([^"]*)"', _ccss):
                for ch in _cm.group(1).replace("\\", ""):
                    if ch.isspace() or ord(ch) in covered or ch in FONT_ALLOW:
                        continue
                    missing.setdefault(ch, set()).add("assets/" + _css)

    for base, _dirs, names in os.walk(OUT):
        for n in sorted(names):
            if not n.endswith(".html"):
                continue
            rel_p = os.path.relpath(os.path.join(base, n), OUT).replace(os.sep, "/")
            with open(os.path.join(base, n), encoding="utf-8") as _hf:
                txt = _hf.read()
            # النصُّ المرئيُّ وحدَه: السكربتاتُ والأنماطُ لا تُرسَم.
            txt = re.sub(r"<(script|style)\b.*?</\1>", " ", txt, flags=re.S | re.I)
            # ── والسماتُ المعروضةُ تُستخرَج **قبل** تجريد الوسوم ──
            # `<[^>]+>` يبتلع الوسمَ بسماته، فـ`title="☺"` كان يمرّ أخضر رغم
            # أنّ المستخدمَ يراه في تلميحٍ أو يسمعه من قارئ الشاشة. قِيس بالطفرة.
            shown = []
            for _am in re.finditer(
                    r'\b(?:title|alt|placeholder|aria-label|value|label|content)'
                    r'\s*=\s*"([^"]*)"', txt, re.I):
                shown.append(_am.group(1))
            txt = re.sub(r"<[^>]+>", " ", txt)
            # ── والكياناتُ **تُفَكّ** لا تُمحى ──
            # `re.sub(r"&[#\w]+;", " ", …)` كان يحوّل `&#9786;` إلى مسافة، فيمرّ
            # محرفٌ خارج المدَيَين أخضرَ لأنّه كُتب بصورته العدديّة. والفكُّ يقيس
            # ما يُرسَم لا ما يُكتَب.
            txt = _html.unescape(txt + " " + " ".join(shown))
            for ch in txt:
                if ch.isspace() or ord(ch) in covered or ch in FONT_ALLOW:
                    continue
                missing.setdefault(ch, set()).add(rel_p)
    check(not missing, lambda: "محرفٌ ظاهرٌ خارجَ `_UR_AR`/`_UR_LA` وخارجَ القائمة البيضاء — يسقط إلى "
        "خطّ النظام **صامتًا**، فيصير السطرُ بخطَّين:\n       "
        + "\n       ".join(
            "%r (U+%04X) في %s" % (c, ord(c), "، ".join(sorted(f)[:3]))
            for c, f in sorted(missing.items()))
        + "\n       إمّا أن يُوسَّع المدى (إن كان الوجهُ يحمله) أو يُضاف إلى "
          "`FONT_ALLOW` بتعليلٍ مكتوب [FNT-01].")

    # ── ورخصةُ الخطّ تصل الزائرَ معه ──
    # ‏OFL‑1.1 (البندُ ٢) يشترط مصاحبةَ الإشعار والرخصة لكلّ نسخةٍ يُعاد توزيعُها،
    # **والنشرُ على الويب إعادةُ توزيع**. والمشروعُ يكتب هذا بنفسه في `.gitignore`
    # («إلزامٌ قانونيٌّ لا نظافةٌ اختياريّة») ويطبّقه على `patches/fonts/` منذ
    # البداية — وغاب عن `site/assets/fonts/` يومَ وُرِّدت الأوجهُ الأربعة: دخلت
    # المستودعَ وطريقَها إلى النشر بلا إشعارٍ واحد. والضلعان يُقاسان معًا لأنّ
    # المصدرَ وحدَه لا يكفي: حلقةُ النسخ تنقل ملفّاتِ `FONT_FACES` وحدَها.
    for _where, _d in (("المصدر", os.path.join(SITE, "assets", "fonts")),
                       ("المخرَج", os.path.join(OUT, "assets", "fonts"))):
        _lic = os.path.join(_d, "OFL.txt")
        need(os.path.isfile(_lic), lambda: "لا `OFL.txt` في %s (%s) — وأوجهُ الخطّ مورَّدةٌ وتُنشَر. إرفاقُ "
            "الإشعار والرخصةِ شرطٌ في OFL‑1.1 لكلّ إعادةِ توزيع، والنشرُ إعادةُ "
            "توزيع [FNT-01]" % (_where, os.path.relpath(_d, ROOT)))
        with open(_lic, encoding="utf-8") as _lf:
            _lt = _lf.read()
        # النصُّ الكاملُ بإشعاره، لا ترويسةً مقتضبة: «Copyright» وحدَه يمرّ على
        # ملفٍّ فارغٍ إلّا من سطر.
        check("SIL Open Font License" in _lt and "Copyright" in _lt, lambda: "‏`OFL.txt` في %s لا يحمل نصَّ الرخصة وإشعارَ حقوق النشر [FNT-01]" % _where)
        check(len(_lt) > 3000, lambda: "‏`OFL.txt` في %s أقصرُ من نصّ OFL‑1.1 (%d محرفًا) — رخصةٌ مبتورةٌ "
            "لا تُجزئ [FNT-01]" % (_where, len(_lt)))
        # والهُويّةُ لا الطولُ وحدَه: نصٌّ من ‎3001‎ محرفِ حشوٍ فيه الكلمتان كان
        # يمرّ أخضر. فتُشترَط علاماتُ **رخصةِ خطِّنا بعينه**: مالكُ الحقّ، ورقمُ
        # النسخة، والاسمُ المحجوز — وهي ما يجعل الملفَّ إشعارًا لا نصًّا طويلًا.
        for _mark in ("IBM Corp", "Version 1.1", "Reserved Font Name"):
            check(_mark in _lt, lambda: "‏`OFL.txt` في %s لا يحمل «%s» — ليس إشعارَ رخصةِ الخطّ "
                "المورَّد [FNT-01]" % (_where, _mark))

    faces = re.findall(r"@font-face\{([^}]+)\}", fcss)
    check(len(faces) == len(declared), lambda: "عددُ `@font-face` لا يطابق المُعلَن [FNT-01]")
    for face in faces:
        _ur = re.search(r"unicode-range:([^;}]*)", face)
        need(_ur and _ur.group(1).strip(), lambda: "وجهٌ بـ`unicode-range` **فارغ** في `fonts.css` — وإعلانٌ بلا قيمةٍ "
            "يُسقِطه المتصفّحُ كلَّه فيعود الوجهان متنازعَين: وهو العطبُ عينُه "
            "الذي أُضيف المدى ليمنعه [FNT-01]")
        for _tok in _ur.group(1).split(","):
            check(re.fullmatch(r"\s*U\+[0-9A-Fa-f]{1,6}(-[0-9A-Fa-f]{1,6})?\s*",
                                _tok), lambda: "مدًى مشوَّهٌ في `fonts.css`: %r — والمتصفّحُ يُسقِط الإعلانَ "
                "كلَّه، فيعود التنازعُ [FNT-01]" % _tok)
        check("unicode-range:" in face, lambda: "وجهٌ بلا `unicode-range` في `fonts.css` — والأوجهُ مقلَّمة، فوجهان "
            "بالاسم والوزن نفسِهما بلا مدًى يتنازعان: يأخذ المتصفّحُ الأخيرَ "
            "ويهمل الأوّل، فنصفُ الموقع بخطٍّ ونصفُه بخطّ النظام [FNT-01]")
        check("font-display:swap" in face, lambda: "وجهٌ بلا `font-display:swap` — الافتراضيُّ يُخفي النصَّ حتّى يصل "
            "الخطّ: صفحةٌ فارغةٌ على اتّصالٍ بطيء [FNT-01]")

    # ── والاسمُ الثاني لأحاديّ المسافة لا يلتقط ما يُحاذى ──
    # وجهُ `Mihrab Code Arabic` يقف **أوّلَ** `--font-mono`. فلو اتّسع مداه إلى
    # حرفٍ لاتينيٍّ أو رقمٍ أو مسافةٍ أو واصلةٍ صار ذلك المحرفُ متناسبَ العرض داخل
    # كتلة شيفرة — فتنكسر المحاذاةُ الرأسيّة في السطر الذي فيه عربيّةٌ وحدَه،
    # وهو أسوأُ من `Courier New`: هناك كان الأسوأُ اختلافَ أسرة، وهنا يصير
    # اختلافَ عرض. ويُقاس المدى **المكتوبُ في `fonts.css`** لا متغيّرُ المولِّد.
    def _ur_set(text):
        out = set()
        for part in text.split(","):
            part = part.strip()
            if not part.upper().startswith("U+"):
                continue
            body = part[2:]
            if "-" in body:
                lo, hi = body.split("-")
                out.update(range(int(lo, 16), int(hi, 16) + 1))
            else:
                out.add(int(body, 16))
        return out

    _mono = [f for f in faces if 'font-family:"%s"' % MONO_AR_FAMILY in f]
    check(len(_mono) == 2, lambda: "المنتظَر وجهان باسم «%s» في `fonts.css` (‏400 و600) ووُجد %d — بلا "
        "الاسم الثاني يسقط العربيُّ في كتل الشيفرة إلى `monospace` العامّ [FNT-01]"
        % (MONO_AR_FAMILY, len(_mono)))
    _ascii = set(range(0x20, 0x7F))
    _gen_punct = set(range(0x2000, 0x2070)) | set(range(0x2E00, 0x2E80))
    for f in _mono:
        rng = _ur_set(re.search(r"unicode-range:([^;}]*)", f).group(1))
        need(rng and rng <= ar_r, lambda: "مدى «%s» يتجاوز `_UR_AR` (أوّلُ الزائد U+%04X) — اسمٌ ثانٍ للملفّ "
            "العربيّ لا يحمل غيرَ ما يحمله [FNT-01]"
            % (MONO_AR_FAMILY, min(rng - ar_r) if rng - ar_r else 0))
        # و«يغطّي» لا «لا يتجاوز» وحدَه: مدًى من محرفٍ واحدٍ كان يمرّ، والعربيُّ
        # في كتل الشيفرة يعود إلى العامّ — العطبُ الذي أُضيف الاسمُ لمنعه.
        _core = set(range(0x0600, 0x0700)) | set(range(0xFB50, 0xFE00)) | set(range(0xFE70, 0xFEFF))
        _gap = _core - rng
        check(not _gap, lambda: "مدى «%s» لا يغطّي كتلةَ العربيّة الأساسيّة (ينقص U+%04X وما بعده، "
            "%d نقطة) — فالعربيُّ في كتل الشيفرة يسقط إلى `monospace` العامّ [FNT-01]"
            % (MONO_AR_FAMILY, min(_gap), len(_gap)))
        for _bad, _why in ((_ascii, "محرفٌ لاتينيٌّ/رقمٌ/مسافة"),
                           (la_r, "مقطعٌ من الوجه اللاتينيّ"),
                           (_gen_punct, "ترقيمٌ عامٌّ له عرضٌ يُحاذى (واصلاتٌ ونحوُها)")):
            _hit = rng & _bad
            check(not _hit, lambda: "مدى «%s» يلتقط %s (U+%04X) — فيصير متناسبَ العرض داخل كتلة "
                "شيفرةٍ وتنكسر المحاذاة [FNT-01]" % (MONO_AR_FAMILY, _why, min(_hit)))

    # والسلسلةُ تبدأ به فعلًا — وإلّا فالوجهُ مُعلَنٌ ولا يصل أحدًا.
    with open(os.path.join(OUT, "assets", "mihrab-docs.css"), encoding="utf-8") as _dc:
        _dcss = css_strip_comments(_dc.read(), "mihrab-docs.css")
    # **آخرُ** إعلانٍ لا أوّلُه: المتصفّحُ يطبّق الأخيرَ في التسلسل، فإعلانٌ
    # مُلحَقٌ بآخر الورقة كان يُبطِل الأوّلَ والحارسُ يقرأ الأوّلَ فيمرّ. والاقتباسُ
    # المفرد CSS صالح، فيُجرَّد كالمزدوج.
    # والقيمةُ قد تنتهي بـ`}` لا `;` (آخرُ إعلانٍ في كتلة) — فكلاهما فاصل.
    _fm_all = re.findall(r"--font-mono\s*:\s*([^;}]+)[;}]", _dcss)
    need(_fm_all, lambda: "لا `--font-mono` في `mihrab-docs.css` [FNT-01]")
    _first = _fm_all[-1].strip().split(",")[0].strip().strip("\"'")
    check(_first == MONO_AR_FAMILY, lambda: "أوّلُ `--font-mono` هو %r لا «%s» — الاسمُ الثاني يعمل بمداه وحدَه، فلا "
        "يضرّ أوّلًا ولا ينفع إن سبقه خطٌّ يحمل العربيّةَ بعرضٍ آخر [FNT-01]"
        % (_first, MONO_AR_FAMILY))

    # ── ٥ج) ما رآه محاكي أندرويد يُقاس بالحساب [AND-01] ──
    # ثلاثُ ملاحظاتٍ ظهرت على المحاكي وأُصلحت في CSS، وكلُّها كانت تعود صامتةً
    # بطفرةٍ واحدة (قِيست الثلاثُ بالطفرة: خضراء):
    # (١) `Courier New` في سلسلة أحاديّ المسافة — وهو في `fonts.xml` على أندرويد
    #     اسمٌ مستعارٌ لـ`serif-monospace` (‏Cutive Mono) يُلتقَط قبل العامّ،
    #     فالشيفرةُ **سيريفيّةٌ** على كلّ هاتف. وأمثالُه: `courier` و`times`
    #     و`georgia` و`baskerville` و`goudy` و`fantasy` كلُّها إلى `serif` هناك.
    #     تُقاس كلُّ سلسلةٍ تصل الزائر: `--font-*` و`font-family` في الأوراق،
    #     و`<style>` و`style=` في **كلّ** صفحةٍ مبنيّة — فصفحةُ المعاينة خارج
    #     `page_shell` بورقةٍ داخليّة، وكان الاسمُ فيها بعد أن حُذف من الورقة.
    # (٢) زرُّ «انسخ» على اللمس ‎44‎ من أعلى ‎8‎ يطمس السطرَ الأوّل الذي يبدأ عند
    #     ‎16‎ — فحشوُ `pre` العلويُّ تحت `pointer: coarse` يبلغ أسفلَ الزرّ. وفي
    #     الطباعة الزرُّ مخفيٌّ فيعود الحشوُ — وإلّا طُبعت من الهاتف بثقبٍ فوق
    #     كلّ كتلة.
    # (٣) بين البطل واللقطة ‎136‎ (‏‎120‎ جوّالًا): حشوُ البطل + هامشُ آخرِ ابنٍ
    #     (لا يُبتلَع في الحشو) + هامشُ اللقطة.
    # تُقاس بتتالٍ مصغَّر: القواعدُ بترتيبها في الورقتين (‏`docs` ثمّ `home`)،
    # والوسيطُ (عرضٌ/لمس/طباعة) يُقيَّم، والوزنُ يسبق الترتيبَ، والمختصَراتُ تُفكّ،
    # و`var()` و`calc()` تُحسَب من رموز `:root`. والعنصرُ المقيسُ يُؤخَذ من
    # **المخرَج** لا يُفترَض: آخرُ أبناء `.hero` في `index.html` كما بُني.
    from html.parser import HTMLParser as _HP

    def _css_rules(text, name):
        """قواعدُ الورقة بترتيبها: (وسيطُ @media أو ""، محدِّدٌ واحد، إعلانات)."""
        rules = []

        def _parse(seg, media):
            p = 0
            while True:
                j = seg.find("{", p)
                if j < 0:
                    break
                head = seg[p:j].rsplit(";", 1)[-1].strip()  # ما قبل آخر `;` جملةٌ مستقلّة (‏`@charset`)
                d, k = 0, j
                while k < len(seg):
                    if seg[k] == "{":
                        d += 1
                    elif seg[k] == "}":
                        d -= 1
                        if d == 0:
                            break
                    k += 1
                check(d == 0, lambda: "قوسٌ لم يُغلَق في %s [AND-01]" % name)
                inner = seg[j + 1:k]
                p = k + 1
                if head.startswith("@media"):
                    _parse(inner, head[len("@media"):].strip())
                elif head.startswith("@"):
                    continue
                else:
                    decls = []
                    for st in inner.split(";"):
                        if ":" in st:
                            pn, _, pv = st.partition(":")
                            decls.append((pn.strip().lower(), pv.replace("!important", "").strip()))
                    for sel in head.split(","):
                        rules.append((media, sel.strip(), decls))

        _parse(css_strip_comments(text, name), "")
        return rules

    def _media_ok(cond, vw, coarse, prn):
        if not cond:
            return True
        for alt in cond.split(","):
            ok = True
            for term in re.split(r"\band\b", alt):
                t = term.strip().strip("()").strip().replace(" ", "")
                if not t:
                    continue
                if t == "print":
                    ok = ok and prn
                elif t == "screen":
                    ok = ok and not prn
                elif t.startswith("max-width:"):
                    ok = ok and vw <= float(t[len("max-width:"):-2])
                elif t.startswith("min-width:"):
                    ok = ok and vw >= float(t[len("min-width:"):-2])
                elif t == "pointer:coarse":
                    ok = ok and coarse
                elif t == "pointer:fine":
                    ok = ok and not coarse
                else:  # prefers-* ونحوها: لا تمسّ حشوًا ولا هامشًا — تُعدّ غيرَ مطابِقة
                    ok = False
            if ok:
                return True
        return False

    _COMP = re.compile(r"\*|[\w-]+|\.[\w-]+|:[\w-]+")

    def _comp_ok(comp, el):
        """مركّبٌ واحد (`main.page`، `:last-child`) على عنصرٍ (وسم، أصناف، أوّل، آخر).
        ما لا يُفهَم (‏`:hover`، `[attr]`، `:not(`) لا يطابق — العنصرُ المقيسُ ساكن."""
        toks = _COMP.findall(comp)
        if "".join(toks) != comp:
            return False
        tag, cls, first, last = el
        for t in toks:
            if t == "*":
                continue
            if t.startswith("."):
                if t[1:] not in cls:
                    return False
            elif t == ":last-child":
                if not last:
                    return False
            elif t == ":first-child":
                if not first:
                    return False
            elif t.startswith(":"):
                return False
            elif t != tag:
                return False
        return True

    def _sel_match(sel, path):
        """يُعيد (يطابق؟، الوزن) — الوزنُ (أصنافٌ+أشباهٌ، وسوم)؛ لا معرِّفاتٍ في الورقتين."""
        toks = re.findall(r">|[^\s>]+", sel)
        if not toks or not _comp_ok(toks[-1], path[-1]):
            return False, (0, 0)

        def rec(ti, pi, direct):
            if ti < 0:
                return True
            tok = toks[ti]
            if tok == ">":
                return rec(ti - 1, pi, True)
            if direct:
                return pi >= 0 and _comp_ok(tok, path[pi]) and rec(ti - 1, pi - 1, False)
            for q in range(pi, -1, -1):
                if _comp_ok(tok, path[q]) and rec(ti - 1, q - 1, False):
                    return True
            return False

        if not rec(len(toks) - 2, len(path) - 2, False):
            return False, (0, 0)
        flat = _COMP.findall("".join(t for t in toks if t != ">"))
        return True, (sum(1 for t in flat if t[0] in ".:"),
                      sum(1 for t in flat if t[0] not in ".:*"))

    def _split_ws(v):
        out, d, cur = [], 0, ""
        for ch in v:
            if ch == "(":
                d += 1
            elif ch == ")":
                d -= 1
            if ch.isspace() and d == 0:
                if cur:
                    out.append(cur)
                cur = ""
            else:
                cur += ch
        if cur:
            out.append(cur)
        return out

    def _side(shorthand, side):
        p = _split_ws(shorthand)
        need(1 <= len(p) <= 4, lambda: "مختصَرٌ لا يُفكّ: %r [AND-01]" % shorthand)
        p = (p * 4)[:4] if len(p) == 1 else (p + p) if len(p) == 2 else (p + p[1:2]) if len(p) == 3 else p
        t, r, b, l = p
        return {"top": t, "right": r, "bottom": b, "left": l}[side]

    def _px(v, tokens):
        """قيمةٌ بالبكسل بعد `var()` و`calc()`؛ `None` لما ليس بكسلًا (‏`auto`، `em`)."""
        for _ in range(8):
            v2 = re.sub(r"var\(\s*(--[\w-]+)\s*\)", lambda m: tokens.get(m.group(1), "var-missing"), v)
            if v2 == v:
                break
            v = v2
        v = v.strip()
        if v.startswith("calc(") and v.endswith(")"):
            v = v[5:-1]
        expr = v.replace("px", "")
        if re.fullmatch(r"[\d\s.+\-*/()]+", expr) and re.search(r"\d", expr):
            return float(eval(expr, {"__builtins__": {}}, {}))  # أرقامٌ وعوامل فقط (تحقّقٌ فوقه)
        return None

    def _css_get(rules, tokens, path, prop, vw, coarse=False, prn=False, raw=False):
        best = None
        for order, (media, sel, decls) in enumerate(rules):
            if not _media_ok(media, vw, coarse, prn):
                continue
            ok, spec = _sel_match(sel, path)
            if not ok:
                continue
            val = None
            for pn, pv in decls:
                if pn == prop:
                    val = pv
                elif pn in ("margin", "padding") and prop.startswith(pn + "-"):
                    val = _side(pv, prop[len(pn) + 1:])
            if val is not None and (best is None or (spec, order) >= best[:2]):
                best = (spec, order, val)
        if best is None:
            return None
        if raw:
            return best[2]
        px = _px(best[2], tokens)
        check(px is not None, lambda: "‏`%s` لـ%s تُحسَب إلى %r لا إلى بكسل — الحارسُ لا يستطيع قياسَها "
            "[AND-01]" % (prop, path[-1][0], best[2]))
        return px

    _rules, _tokens = [], {}
    for _cn in ("mihrab-docs.css", "mihrab-home.css"):  # بترتيب التحميل في `page_shell`
        with open(os.path.join(OUT, "assets", _cn), encoding="utf-8") as _cf5:
            _rules.extend(_css_rules(_cf5.read(), _cn))
    for _media, _sel, _decls in _rules:
        if _sel == ":root" and not _media:
            _tokens.update((pn, pv) for pn, pv in _decls if pn.startswith("--"))
    check("--s1" in _tokens and "--s8" in _tokens, lambda: "رموزُ المسافات `--s*` غائبةٌ عن `:root` [AND-01]")

    # ── (١) لا اسمَ يحلّه أندرويد إلى سيريف في أيّ سلسلةٍ تصل الزائر ──
    _AND_SERIF = {"courier", "courier new", "times", "times new roman", "georgia",
                  "baskerville", "goudy", "fantasy", "itc stone serif",
                  "serif-monospace", "serif", "cursive"}
    _chains = []
    for _cn in sorted(os.listdir(os.path.join(SITE, "assets"))):
        if _cn.endswith(".css"):
            with open(os.path.join(OUT, "assets", _cn), encoding="utf-8") as _cf6:
                _chains.append((_cn, css_strip_comments(_cf6.read(), _cn)))
    for base, _dirs, names in os.walk(OUT):
        for _nm in names:
            if not _nm.endswith(".html"):
                continue
            _hp = os.path.join(base, _nm)
            with open(_hp, encoding="utf-8") as _hf:
                _ht = _hf.read()
            _rel = os.path.relpath(_hp, OUT).replace(os.sep, "/")
            for _m in re.finditer(r"<style[^>]*>(.*?)</style>", _ht, re.S | re.I):
                _chains.append((_rel + " <style>", css_strip_comments(_m.group(1), _rel)))
            for _m in re.finditer(r'\sstyle="([^"]*)"', _ht):
                _chains.append((_rel + " style=", _html.unescape(_m.group(1))))
    _n_chains = 0
    for _where, _txt in _chains:
        for _m in re.finditer(r"(?<![\w-])(font-family|--font-[\w-]+)\s*:\s*([^;}]+)", _txt):
            _n_chains += 1
            for _item in _m.group(2).split(","):
                _it = _item.strip().strip("\"'").lower()
                check(_it not in _AND_SERIF, lambda: "‏`%s` في %s تحمل %r — على أندرويد اسمٌ مستعارٌ لسيريف في "
                    "`fonts.xml` يُلتقَط قبل العامّ، فالنصُّ سيريفيٌّ على كلّ هاتف "
                    "[AND-01]" % (_m.group(1), _where, _item.strip()))
    check(_n_chains >= 3, lambda: "لم تُقرأ سلاسلُ الخطوط (%d) — الحارسُ يقيس الهواء [AND-01]" % _n_chains)

    # ── [AND-06] لا `letter-spacing` غيرَ صفرٍ في أيّ CSS يصل الزائر ──
    # التباعدُ يُدخَل بين الحروف العربيّة **المتّصلة** فيفكّ اتّصالَها: عناوينُ الدرج
    # على محاكي أندرويد («اضبط ووسّع») ظهرت حروفًا متقطّعة. كان في ستّة مواضع
    # (‏`.site-nav h2`، `.toc-title`، `th`، `.hero h1`، `.footer-in h4`، `.docs-index
    # h2`) ووسمِ صفحة المعاينة داخل `build.py` (اليومَ `sitegen/preview.py`) — والطفرةُ (إعادةُ `.18em` إلى واحدٍ
    # منها) كانت تمرّ خضراء. تُقاس السلاسلُ نفسُها التي يقيسها [AND-01].
    _n_ls = 0
    for _where, _txt in _chains:
        for _m in re.finditer(r"(?<![\w-])letter-spacing\s*:\s*([^;}]+)", _txt):
            _n_ls += 1
            _v = _m.group(1).strip().lower()
            check(_v in ("0", "normal", "0px", "0em", "unset", "initial", "inherit"), lambda: "‏`letter-spacing: %s` في %s — يفكّ اتّصالَ الحروف العربيّة (ظهر على "
                "محاكي أندرويد في عناوين الدرج) [AND-06]" % (_m.group(1).strip(), _where))
    # والصفرُ المنتظَر لا يميّز حارسًا يرى عن حارسٍ أعمى: يُطعَم التعبيرُ نفسُه
    # الأشكالَ التي تُكتَب فعلًا (بلا صفرٍ بادئ، سالبة، بلا مسافة، داخل `style=`)
    # فيلتقطها — ولا يلتقط رمزًا مخصَّصًا يحمل الاسمَ.
    _LS_RE = r"(?<![\w-])letter-spacing\s*:\s*([^;}]+)"
    for _probe, _want in (("h2{letter-spacing:.18em}", ".18em"), ("a{letter-spacing: -.01em;}", "-.01em"),
                          ("th{letter-spacing:normal}", "normal"), ("color:red;letter-spacing:1px", "1px")):
        _pm = re.search(_LS_RE, _probe)
        need(_pm and _pm.group(1).strip() == _want, lambda: "تعبيرُ [AND-06] لا يلتقط %r" % _probe)
    check(not re.search(_LS_RE, "--letter-spacing-x: 1"), lambda: "تعبيرُ [AND-06] يلتقط رمزًا لا خاصّيّة")
    del _n_ls

    # ── [AND-07] الحجمُ المعروضُ عشريٌّ في **الثلاثة**: المخبوز، وsite.js، والمعاينة ──
    # الشاهدُ يملكه الحارس: أرشيفُ ويندوز ‎203,053,894‎ بايت يُعرَض ‎203‎ (‏÷‎1e6‎)،
    # وكان ‎194‎ (‏÷‎1048576‎). صار `fmtSize` عشريًّا وبقي `_fmt_size` (اليومَ في `sitegen/pages.py`)
    # ثنائيًّا — فالصفحةُ المخبوزةُ تقول ‎194‎ ويمحوها السكربتُ بـ‎203‎ بعد التحميل،
    # ومن عطّل السكربتات يقرأ الأوّل. فتُقاس الأوجهُ الثلاثة، والقاعدةُ نفسُها تُطبَّق
    # على كلّ أصلٍ في المانيفست المخبوز. و`fmtSize` **تُنفَّذ** بـnode لا تُقرأ بتعبير.
    _AND07_BYTES, _AND07_WANT = 203053894, "203 ميغابايت"

    def _and07_fmt(_b):
        _mb = _b / 1e6
        return ("%.2f غيغابايت" % (_mb / 1000)) if _mb >= 1000 else ("%d ميغابايت" % round(_mb))

    check(_and07_fmt(_AND07_BYTES) == _AND07_WANT, lambda: "قاعدةُ [AND-07] نفسُها منحرفة")
    with open(os.path.join(SITE, "data", "releases.json"), encoding="utf-8") as _rj:
        _and07_assets = [a for a in json.load(_rj).get("assets", []) if a.get("size")]
    need(_and07_assets, lambda: "لا أصولَ في releases.json — [AND-07] يقيس الهواء")
    _dl_html = read("download/index.html")
    for _a in _and07_assets:
        _dec = _and07_fmt(_a["size"])
        _bin = "%d ميغابايت" % round(_a["size"] / 1048576.0)
        check(">%s<" % _dec in _dl_html, lambda: "صفحةُ التنزيل المخبوزة لا تعرض %s لـ%s (‏%d بايت) — `_fmt_size` في "
            "`site/sitegen/pages.py` ليست عشريّة [AND-07]" % (_dec, _a["file"], _a["size"]))
        if _bin != _dec:
            check(">%s<" % _bin not in _dl_html, lambda: "صفحةُ التنزيل تعرض %s الثنائيّ لـ%s بجانب العشريّ [AND-07]" % (_bin, _a["file"]))
    _sjs = read("assets/site.js")
    _fm = re.search(r"function fmtSize\(bytes\)\s*\{.*?\n\t\}", _sjs, re.S)
    need(_fm, lambda: "لم تُعرَف `fmtSize` في site.js [AND-07]")
    # ⚠️ **node مطلوبٌ لا اختياريّ.** كانت كلُّ فحوصِ السلوك أدناه تتراجع بلا node إلى
    # مطابقةِ نصٍّ هو `old` المُصاب نفسُه — فيُقتَل المُصابُ ولا يُقاس سلوك، و
    # `site-chord-prefix-never-waits` كان يعيش (قِيس بحذف node من PATH). فالغيابُ أحمرُ بصوت.
    _node = shutil.which("node")
    need(_node, lambda: "node غيرُ موجود — فحوصُ السلوك [AND-07][AND-08][CAP-02][CAP-03] تُنفِّذ "
                   "دوالَّ الموقع به، ولا بديلَ نصّيّ")
    _nr = subprocess.run([_node, "-e", _fm.group(0) + "\nprocess.stdout.write(fmtSize(%d))" % _AND07_BYTES],
                         capture_output=True, encoding="utf-8", errors="replace", timeout=60)
    need(_nr.returncode == 0 and _nr.stdout.strip() == _AND07_WANT, lambda: "‏`fmtSize(%d)` في site.js ⇒ %r لا %r [AND-07]" % (_AND07_BYTES, _nr.stdout.strip(), _AND07_WANT))
    # وفرعُ الغيغابايت لم يكن يُنفَّذ قطّ (‏203 م.ب وحدَها): القسمةُ على 1024 فيه كانت تمرّ.
    _AND07_GB = 1500000000
    _nrg = subprocess.run([_node, "-e", _fm.group(0) + "\nprocess.stdout.write(fmtSize(%d))" % _AND07_GB],
                          capture_output=True, encoding="utf-8", errors="replace", timeout=60)
    need(_nrg.returncode == 0 and _nrg.stdout.strip() == _and07_fmt(_AND07_GB), lambda: "‏`fmtSize(%d)` في site.js ⇒ %r لا %r [AND-07]" % (_AND07_GB, _nrg.stdout.strip(), _and07_fmt(_AND07_GB)))
    _pjs = read("assets/preview-alif.js")
    _pm2 = re.search(r"a\.size/([0-9e]+)\)", _pjs)
    need(_pm2 and _pm2.group(1) == "1e6", lambda: "صفحةُ المعاينة تقسم الحجمَ على %r لا 1e6 [AND-07]" % (_pm2.group(1) if _pm2 else None))

    # ── (٢) حافّةُ الشيفرة فوق زرّ النسخ على اللمس، وتعود في الطباعة ──
    _pre = [("main", {"layout"}, False, False), ("div", {"content"}, False, False),
            ("pre", set(), False, False)]
    _btn = _pre + [("button", {"copy-btn"}, False, True)]
    _b_top = _css_get(_rules, _tokens, _btn, "top", 412, coarse=True)
    _b_h = _css_get(_rules, _tokens, _btn, "min-height", 412, coarse=True)
    _pt_touch = _css_get(_rules, _tokens, _pre, "padding-top", 412, coarse=True)
    _pt_fine = _css_get(_rules, _tokens, _pre, "padding-top", 1200)
    _pt_print = _css_get(_rules, _tokens, _pre, "padding-top", 412, coarse=True, prn=True)
    need(None not in (_b_top, _b_h, _pt_touch, _pt_fine, _pt_print), lambda: "تعذّر حسابُ زرّ النسخ/حشو `pre` (top=%r min-height=%r touch=%r fine=%r print=%r) "
        "[AND-01]" % (_b_top, _b_h, _pt_touch, _pt_fine, _pt_print))
    check(_b_h >= 44, lambda: "زرُّ النسخ على اللمس %gpx — تحت حدّ اللمس ‎44‎ [AND-01]" % _b_h)
    check(_pt_touch >= _b_top + _b_h, lambda: "حشوُ `pre` العلويُّ على اللمس %gpx وأسفلُ زرّ النسخ عند %g+%g=%gpx — الزرُّ "
        "يطمس السطرَ الأوّل من كلّ كتلة شيفرةٍ على الهاتف [AND-01]"
        % (_pt_touch, _b_top, _b_h, _b_top + _b_h))
    check(_pt_print <= _pt_fine, lambda: "حشوُ `pre` العلويُّ في الطباعة من جهاز لمسٍ %gpx والأساسُ %gpx — الزرُّ مخفيٌّ "
        "في الطباعة وثقبُه باقٍ فوق كلّ كتلة [AND-01]" % (_pt_print, _pt_fine))

    # ── (٣) بين البطل واللقطة: حشوٌ + هامشٌ لا يُبتلَع + هامش — من المخرَج ──
    class _Kids(_HP):
        VOID = {"img", "br", "hr", "input", "meta", "link", "path", "circle", "rect",
                "use", "source", "wbr", "area", "base", "col", "embed", "param", "track"}

        def __init__(self):
            _HP.__init__(self)
            self.stack, self.hero_kids, self.after_hero = [], [], None
            self._hero_depth = self._sib_depth = None

        def handle_starttag(self, tag, attrs):
            cls = set((dict(attrs).get("class") or "").split())
            depth = len(self.stack)
            if self._hero_depth is not None and depth == self._hero_depth + 1:
                self.hero_kids.append((tag, cls))
            if self._sib_depth is not None and depth == self._sib_depth and self.after_hero is None:
                self.after_hero = (tag, cls)
            if tag == "section" and "hero" in cls:
                self._hero_depth = depth
            if tag not in self.VOID:
                self.stack.append(tag)

        def handle_startendtag(self, tag, attrs):
            self.handle_starttag(tag, attrs)
            if tag not in self.VOID:
                self.stack.pop()

        def handle_endtag(self, tag):
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i] == tag:
                    if self._hero_depth == i and tag == "section":
                        self._hero_depth, self._sib_depth = None, i
                    del self.stack[i:]
                    break

    _kp = _Kids()
    _kp.feed(read("index.html"))
    need(_kp.hero_kids and _kp.after_hero, lambda: "لا `section.hero` يليه عنصرٌ في `index.html` [AND-01]")
    _lk_tag, _lk_cls = _kp.hero_kids[-1]
    check("shot" in _kp.after_hero[1], lambda: "ما يلي البطلَ في `index.html` هو %r لا `.shot` — حسابُ الفجوة يقيس غيرَ ما "
        "على الصفحة [AND-01]" % (_kp.after_hero,))
    _main = ("main", {"page"}, False, False)
    _hero = ("section", {"hero"}, True, False)
    _last = (_lk_tag, _lk_cls, len(_kp.hero_kids) == 1, True)
    _shot = (_kp.after_hero[0], _kp.after_hero[1], False, False)
    # الميزانيّة: ما قِيس على المحاكي وكان عطبًا ‎120‎ (‏‎136‎ مكتبًا)، وما يُقصَد
    # حشوُ البطل + هامشُ اللقطة **وحدَهما**: ‎32+32‎ جوّالًا و‎48+64‎ مكتبًا.
    for _vw, _label, _budget in ((412, "الجوّال", 64), (1200, "المكتب", 112)):
        _pb = _css_get(_rules, _tokens, [_main, _hero], "padding-bottom", _vw)
        _mb = _css_get(_rules, _tokens, [_main, _hero, _last], "margin-bottom", _vw)
        _mt = _css_get(_rules, _tokens, [_main, _shot], "margin-top", _vw)
        need(None not in (_pb, _mb, _mt), lambda: "تعذّر حسابُ فجوة البطل/اللقطة على %s (pb=%r mb=%r mt=%r) [AND-01]"
            % (_label, _pb, _mb, _mt))
        check(_mb == 0, lambda: "هامشُ آخرِ أبناء `.hero` (‏%s.%s) %gpx على %s — يُضاف إلى حشو البطل "
            "لا يُبتلَع فيه، فيتراكم فوق اللقطة [AND-01]"
            % (_lk_tag, ".".join(sorted(_lk_cls)) or "-", _mb, _label))
        check(_pb + _mb + _mt <= _budget, lambda: "بين البطل واللقطة %g+%g+%g=%gpx على %s والميزانيّةُ %g — فراغٌ متراكم "
            "فوق اللقطة [AND-01]" % (_pb, _mb, _mt, _pb + _mb + _mt, _label, _budget))

    # ── ٥د) الجولةُ ‎13‎: أربعُ طفراتٍ كانت تعود صامتةً [AND-02..05] ──
    # ما أُصلح بعد المحاكي ليس مقيسًا في الشجرة: حذفُ فرع IME من الالتقاط، وإعادةُ
    # نصّ iOS إلى «يعمل على جهازك»، وحذفُ ‎44‎ من الدرج، وإعادةُ ‎19/4.6‎ القديمة
    # إلى الوثائق — كلُّها تمرّ بلا خطأٍ في أيّ طبقة. وكلُّ حارسٍ هنا قِيس بطفرته.

    # ── [AND-02] الالتقاطُ لا يدّعي قراءةَ اختصارٍ لم يصل ──
    # لوحةُ الهاتف تُطلق keydown بـ`key="Unidentified"` (أندرويد Chrome، قِيس على
    # المحاكي) أو `"Process"` (‏Chromium وفايرفوكس أثناء تركيب IME — لم يُقَس على
    # فايرفوكس أندرويد ولا iOS) و`keyCode 229` في الحالين، و`isComposing` اسمُ
    # الحالة في المواصفة. بلا الفرع كانت النتيجة «Unidentified — لا أمرَ معروفًا».
    # يُقاس ساكنًا: الفرعُ **قبل** `chordFromEvent` ويعود بعد رسالةٍ لا تحمل
    # «Unidentified». (والسلوكُ قِيس على msedge: الثلاثُ تُعرَض الرسالةَ نفسَها.)
    with open(os.path.join(OUT, "assets", "docs.js"), encoding="utf-8") as _dj:
        _docs_js = _dj.read()
    _kd = re.search(r"captureField\.addEventListener\('keydown',\s*function \(e\) \{(.*?)var chord = chordFromEvent\(e\);",
                    _docs_js, re.S)
    need(_kd, lambda: "معالجُ keydown للالتقاط لا يستدعي `chordFromEvent(e)` كما يعرفه الحارس [AND-02]")
    _pre_chord = re.sub(r"/\*.*?\*/", "", _kd.group(1), flags=re.S)
    for _cond in ("e.isComposing", "e.key === 'Unidentified'", "e.key === 'Process'", "e.keyCode === 229"):
        check(_cond in _pre_chord, lambda: "الالتقاطُ لا يفحص `%s` قبل قراءة الاختصار — لوحةُ الهاتف تُعرَض "
            "«Unidentified — لا أمرَ معروفًا» [AND-02]" % _cond)
    _ime = re.search(r"if \([^)]*e\.keyCode === 229[^)]*\)\s*\{(.*?)\}", _pre_chord, re.S)
    need(_ime, lambda: "فرعُ IME في الالتقاط ليس `if (…) { … }` واحدًا [AND-02]")
    _msg = re.search(r"captureOut\.textContent = '([^']*)'", _ime.group(1))
    need(_msg and _msg.group(1).strip(), lambda: "فرعُ IME لا يكتب رسالةً في `.result` — الحقلُ يصمت [AND-02]")
    check("Unidentified" not in _msg.group(1) and "لا أمرَ معروفًا" not in _msg.group(1), lambda: "رسالةُ فرع IME تدّعي اختصارًا: %r [AND-02]" % _msg.group(1))
    check(re.search(r"\breturn;", _ime.group(1)), lambda: "فرعُ IME لا يعود — يمضي إلى `chordFromEvent` ويكتب فوق الرسالة [AND-02]")

    # ── [AND-03] بطاقةُ الهاتف تقول بقدر ما قِيس: iOS «لم يُقَس» لا «يعمل على جهازك» ──
    # وكشفُ iOS يُكتَب **مرّةً واحدة**: كان تعبيرُ `iPhone|iPad|iPod` + `Macintosh`
    # باللمس مكرَّرًا في كشف الهاتف وفي `IS_IOS` فيصلح أحدُهما ويبقى الآخر —
    # وiPad يُعرَف «هاتفًا» بتعبيرٍ و«ليس iOS» بالآخر.
    with open(os.path.join(OUT, "assets", "site.js"), encoding="utf-8") as _sj2:
        _site_js = _sj2.read()
    _site_code = re.sub(r"/\*.*?\*/", "", _site_js, flags=re.S)
    need(len(re.findall(r"iPhone\|iPad\|iPod", _site_code)) == 1, lambda: "تعبيرُ كشف iOS مكتوبٌ %d مرّة في `site.js` — يُكتَب مرّةً في `IS_IOS` "
        "ويُستعمَل في كشف الهاتف [AND-03]" % len(re.findall(r"iPhone\|iPad\|iPod", _site_code)))
    check(_site_code.count("maxTouchPoints") == 1, lambda: "كشفُ iPadOS باللمس مكرَّرٌ في `site.js` [AND-03]")
    _is_ios_at = _site_code.find("var IS_IOS = ")
    _mobile_at = _site_code.find("guess.os = 'mobile'")
    check(0 <= _is_ios_at < _mobile_at, lambda: "‏`IS_IOS` لا يسبق كشفَ الهاتف في `site.js` [AND-03]")
    _mob_if = re.search(r"if \(([^{]*)\)\s*\{ guess\.os = 'mobile'; \}", _site_code)
    need(_mob_if and "IS_IOS" in _mob_if.group(1) and "Android" in _mob_if.group(1), lambda: "كشفُ الهاتف لا يبني على `IS_IOS` و`Android` معًا: %r [AND-03]" % (_mob_if and _mob_if.group(1)))
    check("meta.textContent = IS_IOS ? MOBILE_META_IOS : MOBILE_META;" in _site_code, lambda: "بطاقةُ الهاتف لا تختار نصَّ iOS بـ`IS_IOS` — كلُّ هاتفٍ يقرأ نصَّ أندرويد [AND-03]")
    _metas = dict(re.findall(r"var (MOBILE_META(?:_IOS)?) = '([^']*)';", _site_code))
    need(set(_metas) == {"MOBILE_META", "MOBILE_META_IOS"}, lambda: "نصّا بطاقة الهاتف غيرُ معرَّفين كما يعرفهما الحارس [AND-03]")
    check("يعمل على جهازك" in _metas["MOBILE_META"], lambda: "نصُّ أندرويد لم يعد يقول ما قِيس: «يعمل على جهازك» [AND-03]")
    check("يعمل على جهازك" not in _metas["MOBILE_META_IOS"] and "iPhone" in _metas["MOBILE_META_IOS"]
            and re.search(r"لم (?:يُقَس|نقس|نجرّب|يُجرَّب|تُجرَّب)", _metas["MOBILE_META_IOS"]), lambda: "نصُّ iOS يعِد بما لم يُقَس: %r — لم يُجرَّب على iPhone/iPad بعد [AND-03]" % _metas["MOBILE_META_IOS"])
    check(_metas["MOBILE_META"] != _metas["MOBILE_META_IOS"], lambda: "نصُّ iOS هو نصُّ أندرويد [AND-03]")

    # ── [AND-04] أهدافُ اللمس في الدرج والترويسة ‎44‎ — وبلا فليكس يُفكّك الرابط ──
    # روابطُ الدرج كانت ‎34‎ (الجولة ‎12‎) و«القائمة» ‎31.6‎. تُقاس بالتتالي المصغَّر
    # أعلاه على ‎412‎ لمسًا. و`display: flex` على `.site-nav a` **مرفوض** ما دام
    # رابطٌ يحمل ابنًا: نصُّ `.nav-app` وسهمُه ↗ يصيران عنصرين والمسافةُ بينهما
    # تسقط (قِيست ‎0‎ بكسل على msedge بلمس). فالارتفاعُ بالحشو: ‎10 + 15×1.6 + 10‎.
    _nav_a = [("nav", {"site-nav"}, False, False), ("ul", set(), False, False),
              ("li", set(), False, False), ("a", set(), False, False)]
    _nav_mh = _css_get(_rules, _tokens, _nav_a, "min-height", 412, coarse=True)
    check(_nav_mh is not None and _nav_mh >= 44, lambda: "روابطُ الدرج على اللمس `min-height` %r — تحت ‎44‎، الإبهامُ يخطئها [AND-04]" % _nav_mh)
    _nav_pt = _css_get(_rules, _tokens, _nav_a, "padding-top", 412, coarse=True)
    _nav_pb = _css_get(_rules, _tokens, _nav_a, "padding-bottom", 412, coarse=True)
    _nav_fs = _css_get(_rules, _tokens, _nav_a, "font-size", 412, coarse=True)
    _nav_lh = _css_get(_rules, _tokens, _nav_a, "line-height", 412, coarse=True, raw=True)
    need(None not in (_nav_pt, _nav_pb, _nav_fs, _nav_lh) and re.fullmatch(r"[\d.]+", _nav_lh), lambda: "تعذّر حسابُ ارتفاع رابط الدرج (pt=%r pb=%r fs=%r lh=%r) [AND-04]" % (_nav_pt, _nav_pb, _nav_fs, _nav_lh))
    _nav_h = _nav_pt + _nav_pb + _nav_fs * float(_nav_lh)
    check(_nav_h >= 44, lambda: "ارتفاعُ رابط الدرج بالحشو %g+%g×%s+%g=%gpx على اللمس — `min-height` وحدَها "
        "تمدّ الصندوقَ وتترك النصَّ في أعلاه [AND-04]" % (_nav_pt, _nav_fs, _nav_lh, _nav_pb, _nav_h))
    _nav_disp = _css_get(_rules, _tokens, _nav_a, "display", 412, coarse=True, raw=True)
    _nav_pages = [os.path.join(b_, n_) for b_, _d, ns_ in os.walk(OUT) for n_ in ns_ if n_ == "index.html"]
    _kids = 0
    for _np in _nav_pages:
        with open(_np, encoding="utf-8") as _nf:
            _nt = _nf.read()
        _nm = re.search(r'<nav class="site-nav"[^>]*>(.*?)</nav>', _nt, re.S)
        if not _nm:
            continue
        for _am in re.finditer(r"<a\b[^>]*>(.*?)</a>", _nm.group(1), re.S):
            if "<" in _am.group(1):
                _kids += 1
    need(_kids, lambda: "لا رابطَ في الدرج يحمل ابنًا (‏`.nav-app` وسهمُه) — تغيّر المخرَج، يُراجَع الحارس [AND-04]")
    check(_nav_disp not in ("flex", "inline-flex", "grid", "inline-grid"), lambda: "‏`.site-nav a` على اللمس `display: %s` و%d رابطًا في الدرج يحمل ابنًا — النصُّ "
        "والسهمُ عنصران متجاوران والمسافةُ بينهما تسقط [AND-04]" % (_nav_disp, _kids))
    _hdr_btn = [("header", {"site-header"}, False, False), ("button", {"icon-btn"}, False, False)]
    _hdr_mh = _css_get(_rules, _tokens, _hdr_btn, "min-height", 412, coarse=True)
    check(_hdr_mh is not None and _hdr_mh >= 44, lambda: "«القائمة» وزرُّ السمة في الترويسة على اللمس `min-height` %r — كانت ‎31.6‎ [AND-04]" % _hdr_mh)

    # ── [AND-05] أرقامُ أوّل الإقلاع في الوثائق هي المقيسة، لا القديمة ──
    # الشاهدُ يملكه الحارس: قياسُ ‎2026-09-22‎ على `app.mihrab.dev` عبر CDP (‏msedge،
    # مخبأٌ فارغ): من الأصل نفسِه ‎20‎ طلبًا و‎5.20‎ م.ب منقولةً؛ والخامُ ‎20.3‎ من
    # DevTools (الحزمةُ الرئيسةُ ‎4.4‎ مضغوطةً لا يعيدها CDP خامًا). والشجرةُ ‎203‎.
    # كانت الوثائقُ تقول ‎19/4.6‎ من قياسٍ أقدم، وإعادتُها لا تُخطئ شيئًا.
    # كلُّ رقمٍ في جملة أوّل الإقلاع يجب أن يكون من المقيس (بعد التقريب)، والعشرون
    # طلبًا تُذكَر لفظًا أو رقمًا.
    _BOOT = {"requests": 20, "transfer_mb": 5.2, "raw_mb": 20.3, "tree_mb": 203}
    _boot_ok = {float(round(_BOOT["transfer_mb"])), float(round(_BOOT["raw_mb"])),
                float(_BOOT["tree_mb"]), float(_BOOT["requests"])}
    _AR_DIG = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}

    def _boot_nums(s):
        s = s.translate(_AR_DIG).replace("\u200e", "").replace("\u200f", "").replace("\u061c", "")
        return {float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)}, s

    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as _rf:
        _readme_row = [ln for ln in _rf.read().splitlines() if ln.startswith("| أوّلُ تحميل |")]
    need(len(_readme_row) == 1, lambda: "صفُّ «أوّلُ تحميل» في README غائبٌ أو مكرَّر [AND-05]")
    with open(os.path.join(ROOT, "docs", "محراب-في-المتصفّح.md"), encoding="utf-8") as _bf:
        _boot_doc = re.search(r"\*\*الثابتة\*\*\s*\(`vscode-web`(.*?)\)\.", _bf.read(), re.S)
    need(_boot_doc, lambda: "جملةُ الشجرة الثابتة في `docs/محراب-في-المتصفّح.md` لم تُعرَف [AND-05]")
    with open(os.path.join(SITE, "data", "site.json"), encoding="utf-8") as _sjb:
        _lim = [x for x in json.load(_sjb)["browser"]["limits"] if x.startswith("أوّلُ تحميل")]
    need(len(_lim) == 1, lambda: "حدُّ «أوّلُ تحميل» في `site.json` غائبٌ أو مكرَّر [AND-05]")
    for _where, _txt, _need in (("README.md", _readme_row[0], {5.0, 20.0, 203.0}),
                                ("docs/محراب-في-المتصفّح.md", _boot_doc.group(1), {5.0, 20.0, 203.0}),
                                ("site.json", _lim[0], {5.0})):
        _got, _norm = _boot_nums(_txt)
        check(_need <= _got, lambda: "جملةُ أوّل الإقلاع في %s بلا الأرقام المقيسة %s (فيها %s) [AND-05]"
            % (_where, sorted(_need - _got), sorted(_got)))
        check(_got <= _boot_ok, lambda: "جملةُ أوّل الإقلاع في %s تحمل رقمًا ليس من القياس: %s — الأرقامُ القديمة "
            "(‏19/4.6) تعود بلا قياس [AND-05]" % (_where, sorted(_got - _boot_ok)))
        if _where != "site.json":
            check(re.search(r"عشرين|العشرون|عشرون|20 طلب", _norm), lambda: "جملةُ أوّل الإقلاع في %s لا تذكر أنّها **عشرون** ملفًّا لا الشجرةُ كلُّها [AND-05]" % _where)

    # ── ٥هـ) الجولةُ ‎15‎: الأسهمُ وEscape في نتائج البحث، والترشيحُ يُنطَق [AND-08] ──
    # ثلاثةُ سلوكاتٍ أُضيفت في docs.js وكلُّها كانت تعود صامتةً بطفرة (قِيست الثلاثُ):
    # Escape يمنع الحركةَ الأصليّة **ما دامت النتائجُ ظاهرة** (‏Chromium يمسح
    # `input[type=search]` بنفسه ويُطلق `input`) ولا يمنعها والقائمةُ مطويّة؛ و↓/↑ تسير
    # في الروابط وتعود من الأولى إلى الحقل ولا تلتفّ؛ وحقلُ الترشيح يكتب عددَ الصفوف في
    # `role="status"` بصيغةٍ صحيحةِ العدد. `moveIn` و`kbdWord` **تُنفَّذان** بـnode على
    # صندوقٍ مصنوع كما [AND-07]، ولا تُقرآن نصًّا إلّا حين لا node.
    _esc = re.search(
        r"document\.addEventListener\('keydown', function \(e\) \{\s*if \(e\.key !== 'Escape'\) \{ return; \}(.*?)\n\t\t\}\);",
        _docs_js, re.S)
    need(_esc, lambda: "معالجُ Escape لصناديق البحث لم يُعرَف في docs.js [AND-08]")
    _esc_body = re.sub(r"/\*.*?\*/", "", _esc.group(1), flags=re.S)
    _esc_if = re.search(r"if \(!b\.results\.hidden\) \{(.*?)\n\t\t\t\t\}", _esc_body, re.S)
    need(_esc_if, lambda: "معالجُ Escape لا يشترط نتائجَ ظاهرةً قبل أن يفعل شيئًا [AND-08]")
    check("e.preventDefault()" in _esc_if.group(1), lambda: "Escape لا يمنع الحركةَ الأصليّة والنتائجُ ظاهرة — Chromium يمسح النصَّ فيطوي "
        "النتائجَ ويُضيع السؤالَ بضغطةٍ واحدة [AND-08]")
    check("e.preventDefault()" not in _esc_body.replace(_esc_if.group(1), ""), lambda: "Escape يمنع الحركةَ الأصليّة **خارج** شرط النتائج الظاهرة — الضغطةُ الثانية لا تمسح "
        "النصَّ كما اعتاد الزائر [AND-08]")
    check("show(b, false)" in _esc_if.group(1) and "announce(b, '')" in _esc_if.group(1), lambda: "Escape لا يطوي النتائجَ أو لا يُصمِت الإعلان [AND-08]")
    check("if (b.results.contains(document.activeElement)) { b.input.focus(); }" in _esc_if.group(1), lambda: "Escape من رابطٍ داخل النتائج لا يعيد البؤرةَ إلى الحقل — تبقى على عنصرٍ صار مخفيًّا [AND-08]")

    _mv = re.search(r"function moveIn\(b, from, dir\) \{.*?\n\t\t\}", _docs_js, re.S)
    need(_mv, lambda: "لم تُعرَف `moveIn` في docs.js [AND-08]")
    _in_kd = re.search(r"b\.input\.addEventListener\('keydown', function \(e\) \{(.*?)\n\t\t\t\}\);", _docs_js, re.S)
    need(_in_kd, lambda: "لا معالجَ keydown على حقل البحث [AND-08]")
    check("if (e.key !== 'ArrowDown' || b.results.hidden) { return; }" in _in_kd.group(1), lambda: "↓ من الحقل لا يُشترَط فيه نتائجُ ظاهرة — يُبتلَع السهمُ والقائمةُ مطويّة [AND-08]")
    check("if (moveIn(b, null, 1)) { e.preventDefault(); }" in _in_kd.group(1), lambda: "↓ من الحقل لا يدخل القائمةَ، أو يمنع الحركةَ الأصليّة حتّى حين لا رابطَ [AND-08]")
    _res_kd = re.search(r"b\.results\.addEventListener\('keydown', function \(e\) \{(.*?)\n\t\t\t\}\);", _docs_js, re.S)
    need(_res_kd and "e.key === 'ArrowDown' ? 1 : -1" in _res_kd.group(1), lambda: "↓/↑ داخل النتائج لا تسير [AND-08]")

    _kw = re.search(r"function kbdWord\(n\) \{.*?\n\t\}", _docs_js, re.S)
    need(_kw, lambda: "لم تُعرَف `kbdWord` في docs.js [AND-08]")
    # قواعدُ العدد: صفرٌ نفيٌ، وواحدٌ مفرد، واثنان مثنًّى، و‎3–10‎ جمعٌ مجرور، و‎11‎ فأكثرَ مفردٌ منصوب.
    _KW_WANT = {0: "لا اختصارَ يطابق", 1: "اختصارٌ واحد", 2: "اختصاران", 3: "3 اختصارات",
                10: "10 اختصارات", 11: "11 اختصارًا", 100: "100 اختصارًا"}
    _AND08_JS = _mv.group(0) + r"""
var log = [];
function mk(n) {
  var links = [];
  for (var i = 0; i < n; i++) { (function (i) { links.push({ focus: function () { log.push('a' + i); } }); }(i)); }
  return { input: { focus: function () { log.push('input'); } },
           results: { querySelectorAll: function () { return links; } }, links: links };
}
var e0 = mk(0), b = mk(3), out = [];
out.push(moveIn(e0, null, 1));
out.push(moveIn(b, null, 1));
out.push(moveIn(b, b.links[1], 1));
out.push(moveIn(b, b.links[2], 1));
out.push(moveIn(b, b.links[0], -1));
out.push(moveIn(b, null, -1));
process.stdout.write(JSON.stringify([out, log]));
"""
    _AND08_WANT = [[False, True, True, True, True, True], ["a0", "a2", "input", "a2"]]
    _nr8 = subprocess.run([_node, "-e", _AND08_JS], capture_output=True, encoding="utf-8",
                          errors="replace", timeout=60)
    need(_nr8.returncode == 0, lambda: "تعذّر تنفيذُ `moveIn` بـnode: %s [AND-08]" % _nr8.stderr.strip()[-300:])
    _got8 = json.loads(_nr8.stdout)
    check(_got8 == _AND08_WANT, lambda: "‏`moveIn` على صندوقٍ مصنوع ⇒ %r لا %r — المنتظَر: بلا روابط false؛ ↓ من الحقل إلى "
        "الأولى؛ ↓ بين الروابط؛ ↓ من الأخيرة تبقى بلا التفاف؛ ↑ من الأولى إلى الحقل؛ "
        "↑ بلا مصدرٍ إلى الأخيرة [AND-08]" % (_got8, _AND08_WANT))
    _nr9 = subprocess.run(
        [_node, "-e", _kw.group(0) + "\nprocess.stdout.write(JSON.stringify(%s.map(kbdWord)))"
         % json.dumps(sorted(_KW_WANT))],
        capture_output=True, encoding="utf-8", errors="replace", timeout=60)
    need(_nr9.returncode == 0, lambda: "تعذّر تنفيذُ `kbdWord` بـnode: %s [AND-08]" % _nr9.stderr.strip()[-300:])
    for _n, _s in zip(sorted(_KW_WANT), json.loads(_nr9.stdout)):
        check(_s == _KW_WANT[_n], lambda: "‏`kbdWord(%d)` ⇒ %r لا %r — قواعدُ العدد العربيّ [AND-08]" % (_n, _s, _KW_WANT[_n]))

    _kb_html = read("keyboard/index.html")
    check(_kb_html.count('class="sr-only kbd-status" role="status" aria-live="polite"') == 1, lambda: "صفحةُ الاختصارات بلا سطرِ حالةٍ واحدٍ `role=\"status\" aria-live=\"polite\"` للترشيح — "
        "قارئُ الشاشة لا يسمع عددَ الصفوف [AND-08]")
    check(re.search(r"var msg = q \? kbdWord\(total\) : '';\n\s*if \(kbdStatus && kbdStatus\.textContent !== msg\) "
                     r"\{ kbdStatus\.textContent = msg; \}", _docs_js), lambda: "‏`filterRows` لا تكتب العددَ في `.kbd-status` مشروطًا بتغيّر النصّ، أو تنطق والحقلُ فارغ [AND-08]")
    with open(os.path.join(OUT, "assets", "mihrab-home.css"), encoding="utf-8") as _hf2:
        check(re.search(r"\.sr-only\s*\{", css_strip_comments(_hf2.read(), "mihrab-home.css")), lambda: "لا قاعدةَ `.sr-only` في الورقة التي تصل صفحةَ الاختصارات — سطرُ الحالة يُرى لا يُنطَق وحدَه [AND-08]")
    check("assets/mihrab-home.css" in _kb_html, lambda: "صفحةُ الاختصارات لا تحمّل `mihrab-home.css` حيث `.sr-only` [AND-08]")

    # ── [PRN-01] الطباعةُ تُخفي مقدّمةَ صفحة الاختصارات لا متنَ كلّ صفحة ──
    # `.content > p` في كتلة الطباعة كانت بلا قيدٍ (الجولة ‎15‎) فتُخفي فقراتِ وعناوينَ
    # وكتلَ **كلّ** صفحةِ توثيقٍ عند الطباعة: `/start/` تُطبَع بلا فقراتها السبع وعناوينها
    # الخمسة وكتلتها. التتالي المصغَّر لا يفهم `:has()` فلا يطابقه — وهذا المقصود: يُقاس
    # أنّ ابنًا مباشرًا لـ`main.content` لا يُخفى في الطباعة **بقاعدةٍ عامّة**، وأنّ القيدَ
    # موجودٌ في الورقة وجدولُه في الصفحة.
    _mc = [("main", {"content"}, False, False)]
    for _tag in ("p", "h2", "pre"):
        _d = _css_get(_rules, _tokens, _mc + [(_tag, set(), False, False)], "display", 1200, prn=True, raw=True)
        check(_d != "none", lambda: "‏`main.content > %s` في الطباعة `display: none` بقاعدةٍ عامّة — متنُ كلّ صفحةِ "
            "توثيقٍ يختفي من الورق [PRN-01]" % _tag)
    _cc = _css_get(_rules, _tokens, _mc, "column-count", 1200, prn=True, raw=True)
    check(_cc in (None, "auto", "1"), lambda: "‏`main.content` في الطباعة أعمدةٌ (%r) بقاعدةٍ عامّة — لصفحة الاختصارات وحدَها [PRN-01]" % _cc)
    with open(os.path.join(OUT, "assets", "mihrab-docs.css"), encoding="utf-8") as _pf:
        _prn_css = css_strip_comments(_pf.read(), "mihrab-docs.css")
    check(re.search(r"\.content:has\(\[data-kbd-table\]\)\s*>\s*p\b", _prn_css), lambda: "قاعدةُ إخفاء مقدّمة صفحة الاختصارات في الطباعة غائبةٌ أو بلا قيد `:has([data-kbd-table])` [PRN-01]")
    check("data-kbd-table" in _kb_html, lambda: "صفحةُ الاختصارات بلا `data-kbd-table` — قيدُ الطباعة لا يجد جدولَه [PRN-01]")
    # ⚠️ **والتتالي المصغَّرُ أعمى عن `:has()`** — فقاعدةٌ بقيدٍ يطابق كلَّ صفحة
    # (‏`.content:has(h1) > p { display: none }`) كانت تمرّ أخضرَ وهي تُخفي متنَ كلّ صفحة
    # من الورق (قِيس بالزرع). فكلُّ `:has(` في كتل الطباعة هو قيدُ الجدول بعينه لا غير.
    for _pm in re.finditer(r"@media\s+print\b[^{]*\{", _prn_css):
        _depth, _k = 1, _pm.end()
        while _depth and _k < len(_prn_css):
            _depth += {"{": 1, "}": -1}.get(_prn_css[_k], 0)
            _k += 1
        for _hm in re.finditer(r":has\(((?:[^()]|\([^()]*\))*)\)", _prn_css[_pm.end():_k]):
            check(_hm.group(1).strip() == "[data-kbd-table]",
                  lambda: "في كتلة الطباعة `:has(%s)` — القيدُ الوحيدُ المقبول `:has([data-kbd-table])`؛ "
                          "غيرُه قد يطابق كلَّ صفحةٍ والتتالي هنا لا يقيسه [PRN-01]" % _hm.group(1))
    _start_html = read("start/index.html")
    check(re.search(r'<main class="content">\s*<h1', _start_html) and "<p>" in _start_html, lambda: "صفحةُ `/start/` ليست `main.content` بفقراتٍ مباشرة — شاهدُ [PRN-01] زال")

    # ── [CAP-01] ما يُقارَن به الالتقاطُ بترتيب `chordFromEvent` نفسِه ──
    # ‏`data-chords` كانت السلسلةَ كما كُتبت في البيانات («Shift+Alt+Cmd+C»)، والحدثُ
    # يبنيها Ctrl ثمّ Cmd ثمّ Shift ثمّ Alt («Cmd+Shift+Alt+C») — فثلاثةُ اختصاراتِ ماك
    # كانت تُلتقَط «لا أمرَ معروفًا» والصفُّ أمام الزائر. الترتيبُ يُقرأ من docs.js لا يُكتَب.
    _ord = re.findall(r"if \(e\.(ctrl|meta|shift|alt)Key\) \{ parts\.push\('(\w+)'\); \}", _docs_js)
    check([m for m, _ in _ord] == ["ctrl", "meta", "shift", "alt"], lambda: "ترتيبُ المعدِّلات في `chordFromEvent` %r — يُراجَع `_canon_chord` في site/sitegen/pages.py [CAP-01]" % (_ord,))
    _mods = [n for _, n in _ord]
    _chords = [c for m in re.finditer(r'data-chords="([^"]*)"', _kb_html)
               for c in _html.unescape(m.group(1)).split("|") if c]
    check(len(_chords) >= 40, lambda: "عددُ الاختصارات في الصفحة %d — الحارسُ يقيس الهواء [CAP-01]" % len(_chords))
    for _c in _chords:
        for _press in _c.split(" "):
            _parts = _press.split("+")
            _pm = _parts[:-1]
            check(all(m in _mods for m in _pm), lambda: "معدِّلٌ لا يعرفه `chordFromEvent` في %r [CAP-01]" % _c)
            check(_pm == [m for m in _mods if m in _pm], lambda: "‏`data-chords` تحمل %r وترتيبُ معدِّلاتها ليس ترتيبَ `chordFromEvent` (%s) — "
                "الالتقاطُ يقارن حرفًا بحرف فيردّ «لا أمرَ معروفًا» والصفُّ أمام الزائر [CAP-01]"
                % (_c, "، ".join(_mods)))
            check(_parts[-1], lambda: "اختصارٌ ينتهي بـ`+` في %r [CAP-01]" % _c)
    # وشاهدُ تفعيل: البياناتُ تحمل ترتيبًا غيرَ قانونيٍّ **عمدًا** (المعروضُ يبقى كما كُتب:
    # «Shift+Alt+Cmd» ترتيبُ ماك المألوف) فيُرى التقنينُ وهو يعمل. من قنّن البياناتِ كلَّها
    # فليُبقِ مثالًا واحدًا أو يُغذِّ الحارسَ به.
    with open(os.path.join(SITE, "data", "keybindings.json"), encoding="utf-8") as _kbf:
        _kb_raw = [e.get(k) for g in json.load(_kbf)["groups"] for e in g["items"]
                   for k in ("win", "mac") if e.get(k)]
    _raw_noncanon = [v for v in _kb_raw for _press in v.split(" ")
                     if _press.split("+")[:-1] != [m for m in _mods if m in _press.split("+")[:-1]]]
    need(_raw_noncanon, lambda: "لا اختصارَ في `keybindings.json` بترتيبٍ غيرِ قانونيّ — شاهدُ تفعيل [CAP-01] زال؛ أبقِ "
        "مثالًا («Shift+Alt+Cmd+C») أو غذِّ الحارسَ بغيره")

    # ── [CAP-02] الالتقاطُ يلتقط تسلسلَ ضغطتين، ويُلغي التعليقَ حين يجب ──
    # `Ctrl+K` وحدَه ليس اختصارًا وهو بادئةُ تسلسلات؛ كان يُلتقَط «لا أمرَ معروفًا» ولا سبيلَ
    # إلى تسلسلٍ (الجولة ‎16‎). `chordStep` نقيّةٌ **فتُنفَّذ** بـnode على جدول الصفحة
    # المبنيّة نفسِه لا على صندوقٍ مصنوع: Ctrl+K ⇒ انتظار؛ ثمّ Ctrl+S ⇒ «اختصارات لوحة
    # المفاتيح»؛ Ctrl+P فوريّ؛ بعد انقضاء المهلة Ctrl+S ⇒ «حفظ الملفّ»؛ Ctrl+K S ⇒ «حفظ
    # الكلّ»؛ Ctrl+K Ctrl+K ⇒ لا أمرَ ولا تعليقَ ثانٍ. وساكنًا: المهلةُ ‎1–8‎ ث بمفتاحٍ لا
    # قيمة، والتعليقُ يُلغى في Escape وIME وblur والمهلة (الجولة ‎17‎: كان Escape يعود
    # قبل التصفير وblur لا يمسّه، فمن غادر الحقلَ وعاد خلال المهلة دُمجت ضغطتُه في تسلسلٍ
    # لم يقصده). كلُّ فرعٍ قِيس بمُصابه في tests/meta/mutants.json.
    _cs = re.search(r"function chordStep\(chord, pending, entries\) \{.*?\n\t\}", _docs_js, re.S)
    need(_cs, lambda: "لم تُعرَف `chordStep(chord, pending, entries)` في docs.js [CAP-02]")
    _cw = re.search(r"var CHORD_WAIT_MS = (\d+);", _docs_js)
    need(_cw, lambda: "لا `var CHORD_WAIT_MS = N;` في docs.js — المهلةُ رقمٌ مدفون [CAP-02]")
    check(1000 <= int(_cw.group(1)) <= 8000, lambda: "مهلةُ التسلسل %s مث — دون ثانيةٍ لا تُدرَك الضغطةُ الثانية، وفوق ثمانٍ يُدمَج ما لم "
        "يُقصَد [CAP-02]" % _cw.group(1))
    _cp = re.search(r"function clearPending\(\) \{(.*?)\n\t\}", _docs_js, re.S)
    need(_cp and "pendingChord = null;" in _cp.group(1) and "clearTimeout(pendingTimer)" in _cp.group(1), lambda: "‏`clearPending` لا تصفّر التعليقَ ومهلتَه معًا [CAP-02]")
    _cap = re.search(r"captureField\.addEventListener\('keydown', function \(e\) \{(.*?)\n\t\t\}\);", _docs_js, re.S)
    need(_cap, lambda: "معالجُ keydown للالتقاط لم يُعرَف بحدوده [CAP-02]")
    _cap_body = re.sub(r"/\*.*?\*/", "", _cap.group(1), flags=re.S)
    _esc2 = re.search(r"if \(e\.key === 'Escape'\) \{([^}]*)\}", _cap_body)
    _ro = re.search(r"function resetOut\(\) \{(.*?)\n\t\t\}", _docs_js, re.S)
    need(_esc2 and _ro and "resetOut();" in _esc2.group(1) and "clearPending();" in _ro.group(1), lambda: "Escape يُغلق الالتقاطَ ولا يُلغي التعليق — Ctrl+K ثمّ Escape ثمّ فتحٌ وS خلال المهلة "
        "⇒ «Ctrl+K S ← حفظ الكلّ» [CAP-02]")
    check("clearPending();" in _ime.group(1), lambda: "ضغطةُ IME أثناء التعليق لا تُلغيه — تُدمَج الضغطةُ المفهومةُ التالية في تسلسلٍ لم يُقصَد [CAP-02]")
    _dp = re.search(r"function dropPending\(\) \{(.*?)\n\t\t\}", _docs_js, re.S)
    need(_dp and "if (!pendingChord) { return; }" in _dp.group(1) and "clearPending();" in _dp.group(1), lambda: "‏`dropPending` لا تُسقِط التعليقَ أو لا تعود حين لا تعليق [CAP-02]")
    check("لم تصل الضغطةُ الثانية" in _dp.group(1), lambda: "سقوطُ التعليق صامتٌ — السطرُ يبقى يطلب الضغطةَ الثانية [CAP-02]")
    check("captureField.addEventListener('blur', dropPending);" in _docs_js, lambda: "فقدانُ البؤرة لا يُسقِط التعليق — المعالجُ على الحقل وحدَه لكنّ التعليقَ يبقى للعائد خلال "
        "المهلة [CAP-02]")
    check(re.search(r"var step = chordStep\(chord, pendingChord, chordTable\);\n\s*clearPending\(\);", _cap_body), lambda: "المعالجُ لا يستدعي `chordStep(chord, pendingChord, chordTable)` ثمّ يصفّر التعليقَ قبل الحسم [CAP-02]")
    check(re.search(r"if \(step\.wait\) \{.*?pendingChord = chord;.*?pendingTimer = setTimeout\(dropPending, CHORD_WAIT_MS\);\s*return;",
                     _cap_body, re.S), lambda: "فرعُ الانتظار لا يعلّق الضغطةَ بمهلة `CHORD_WAIT_MS` تسقط بـ`dropPending` ويعود [CAP-02]")
    _rows2 = [{"row": _html.unescape(m.group(2)), "chords": _html.unescape(m.group(1)).split("|")}
              for m in re.finditer(r'data-chords="([^"]*)"><td><span class="cmd-name">([^<]*)</span>', _kb_html)]
    check(len(_rows2) >= 40, lambda: "صفوفُ الاختصارات بأسمائها %d — الحارسُ يقيس الهواء [CAP-02]" % len(_rows2))
    _CAP02_JS = _cs.group(0) + "\nvar entries = " + json.dumps(_rows2, ensure_ascii=False) + r""";
function step(c, p) { var s = chordStep(c, p, entries); return [s.chord, s.row, s.wait]; }
var out = [];
out.push(step('Ctrl+K', null));
out.push(step('Ctrl+S', 'Ctrl+K'));
out.push(step('Ctrl+P', null));
out.push(step('Ctrl+S', null));
out.push(step('S', 'Ctrl+K'));
out.push(step('Ctrl+K', 'Ctrl+K'));
out.push(step('F24', null));
process.stdout.write(JSON.stringify(out));
"""
    _CAP02_WANT = [["Ctrl+K", None, True],
                   ["Ctrl+K Ctrl+S", "اختصارات لوحة المفاتيح", False],
                   ["Ctrl+P", "الانتقال السريع إلى ملفّ", False],
                   ["Ctrl+S", "حفظ الملفّ", False],
                   ["Ctrl+K S", "حفظ الكلّ", False],
                   ["Ctrl+K Ctrl+K", None, False],
                   ["F24", None, False]]
    _nr10 = subprocess.run([_node, "-e", _CAP02_JS], capture_output=True, encoding="utf-8",
                           errors="replace", timeout=60)
    need(_nr10.returncode == 0, lambda: "تعذّر تنفيذُ `chordStep` بـnode: %s [CAP-02]" % _nr10.stderr.strip()[-300:])
    _got10 = json.loads(_nr10.stdout)
    check(_got10 == _CAP02_WANT, lambda: "‏`chordStep` على جدول الصفحة ⇒ %r لا %r — المنتظَر: Ctrl+K ينتظر؛ Ctrl+K Ctrl+S "
        "«اختصارات لوحة المفاتيح»؛ Ctrl+P فوريّ؛ Ctrl+S بلا تعليقٍ «حفظ الملفّ»؛ Ctrl+K S "
        "«حفظ الكلّ»؛ Ctrl+K Ctrl+K لا أمرَ ولا انتظار؛ F24 لا شيء [CAP-02]" % (_got10, _CAP02_WANT))

    # ── [CAP-03] الالتقاطُ يقرأ المفتاحَ لا المحرفَ المطبوع ──
    # على لوحةٍ عربيّة `Ctrl+S` تصل `key="س"`، و`Shift` يقلب «`» إلى «~»، وOption على ماك
    # يقلب C إلى «ç» — فكان «Ctrl+Shift+`» (طرفيّةٌ جديدة) و«Cmd+Shift+Alt+C» لا يُلتقَطان
    # أبدًا والصفُّ أمام الزائر. `chordFromEvent` **تُنفَّذ** بأحداثٍ مصنوعة.
    _cfe = re.search(r"\tvar CODE_KEY = \{.*?\n\tfunction chordFromEvent\(e\) \{.*?\n\t\}", _docs_js, re.S)
    need(_cfe, lambda: "لم تُعرَف `CODE_KEY` ثمّ `chordFromEvent` في docs.js [CAP-03]")
    _CAP03 = [({"ctrlKey": True, "key": "س", "code": "KeyS"}, "Ctrl+S"),
              ({"ctrlKey": True, "shiftKey": True, "key": "~", "code": "Backquote"}, "Ctrl+Shift+`"),
              ({"metaKey": True, "shiftKey": True, "altKey": True, "key": "ç", "code": "KeyC"}, "Cmd+Shift+Alt+C"),
              ({"ctrlKey": True, "shiftKey": True, "key": "{", "code": "BracketLeft"}, "Ctrl+Shift+["),
              ({"key": "س", "code": "KeyS"}, "S"),
              ({"key": "F1", "code": "F1"}, "F1"),
              ({"ctrlKey": True, "key": "k", "code": "KeyK"}, "Ctrl+K"),
              # الحرفُ الصغيرُ يُكبَّر: بلا ذلك يُبنى «Ctrl+s» فلا يطابق صفًّا واحدًا بحرف
              ({"ctrlKey": True, "key": "s", "code": "KeyS"}, "Ctrl+S"),
              # المعدِّلُ وحدَه ليس ضغطة: بلا ذلك يُكتب «Ctrl+Control» قبل أن يكمل الزائر
              ({"ctrlKey": True, "key": "Control", "code": "ControlLeft"}, None),
              ({"shiftKey": True, "key": "Shift", "code": "ShiftLeft"}, None),
              ({"key": " ", "code": "Space"}, "Space"),
              # المتصفّحُ يرسل `ArrowUp` والجدولُ يكتب `Up`: بلا ترجمةٍ لا يُلتقَط «Alt+Up» أبدًا
              ({"altKey": True, "key": "ArrowUp", "code": "ArrowUp"}, "Alt+Up"),
              # المفتاحُ الميّت (‏Option+E على ماك) يصل `Dead` لا محرفًا
              ({"metaKey": True, "altKey": True, "key": "Dead", "code": "KeyE"}, "Cmd+Alt+E")]
    # ورحلةُ ذهابٍ وإياب: كلُّ ضغطةٍ في جدول الصفحة تُصنَع حدثًا لاتينيًّا كما يرسله
    # المتصفّح، ثمّ تُعاد بـ`chordFromEvent` فيجب أن تعطي نصَّها نفسَه — وإلّا فصفٌّ في
    # الجدول لا يمكن أن يُلتقَط أبدًا.
    _CODE_OF = {"`": "Backquote", "-": "Minus", "=": "Equal", "[": "BracketLeft", "]": "BracketRight",
                "\\": "Backslash", ";": "Semicolon", "'": "Quote", ",": "Comma", ".": "Period", "/": "Slash"}
    # ⚠️ **الحدثُ كما يرسله المتصفّح، لا كما يكتبه الجدول.** كان الفرعُ الأخير يصنع
    # `key=الرمز` لكلّ ما لم يُعرَف، فمرّت الأسهمُ (المتصفّحُ يرسل `ArrowUp`) والرحلةُ تصدّق
    # نفسَها؛ وكانت ضغطاتُ Shift تُصنَع بالمحرف غيرِ المُزاح فبقي `CODE_KEY` وفرعُ `Digit`
    # بلا حارسٍ فعليّ (قِيس بالزرع). فمع Shift يُرسَل المحرفُ المُزاح على تخطيط US، والمفاتيحُ
    # المسمّاةُ من قائمةٍ صريحة، و**ما لا يُعرَف اسمُ حدثه يُفشِل الحارس** لا يمرّ صامتًا.
    _US_SHIFTED = {"`": "~", "-": "_", "=": "+", "[": "{", "]": "}", "\\": "|", ";": ":", "'": '"',
                   ",": "<", ".": ">", "/": "?", "1": "!", "2": "@", "3": "#", "4": "$", "5": "%",
                   "6": "^", "7": "&", "8": "*", "9": "(", "0": ")"}
    _NAMED = {"Up": "ArrowUp", "Down": "ArrowDown", "Left": "ArrowLeft", "Right": "ArrowRight",
              "Enter": "Enter", "Escape": "Escape", "Tab": "Tab", "Backspace": "Backspace",
              "Delete": "Delete", "Insert": "Insert", "Home": "Home", "End": "End",
              "PageUp": "PageUp", "PageDown": "PageDown"}
    _MODS = {"Ctrl": "ctrlKey", "Cmd": "metaKey", "Shift": "shiftKey", "Alt": "altKey"}
    for _press in sorted({p for c in _chords for p in c.split(" ")}):
        _toks = _press.split("+")
        _key = _toks[-1]
        _ev = {_MODS[t]: True for t in _toks[:-1] if t in _MODS}
        _shift = bool(_ev.get("shiftKey"))
        if re.fullmatch(r"[A-Z]", _key):
            _ev.update(key=_key if _shift else _key.lower(), code="Key" + _key)
        elif re.fullmatch(r"[0-9]", _key):
            _ev.update(key=_US_SHIFTED[_key] if _shift else _key, code="Digit" + _key)
        elif _key in _CODE_OF:
            _ev.update(key=_US_SHIFTED[_key] if _shift else _key, code=_CODE_OF[_key])
        elif _key == "Space":
            _ev.update(key=" ", code="Space")
        elif _key in _NAMED:
            _ev.update(key=_NAMED[_key], code=_NAMED[_key])
        elif re.fullmatch(r"F([1-9]|1[0-9]|2[0-4])", _key):
            _ev.update(key=_key, code=_key)
        else:
            bad("ضغطةٌ في جدول الصفحة لا يُعرَف اسمُ حدثها في المتصفّح: %r — أضِفها إلى "
                "`_NAMED` بما يرسله المتصفّح فعلًا، أو صحّح الجدول [CAP-03]" % _press)
            continue
        _CAP03.append((_ev, _press))
    _js3 = _cfe.group(0) + "\nprocess.stdout.write(JSON.stringify(%s.map(function (o) { return chordFromEvent(" \
        "Object.assign({ctrlKey: false, metaKey: false, shiftKey: false, altKey: false}, o)); })))" \
        % json.dumps([e for e, _ in _CAP03], ensure_ascii=False)
    _nr11 = subprocess.run([_node, "-e", _js3], capture_output=True, encoding="utf-8",
                           errors="replace", timeout=60)
    need(_nr11.returncode == 0, lambda: "تعذّر تنفيذُ `chordFromEvent` بـnode: %s [CAP-03]" % _nr11.stderr.strip()[-300:])
    for (_ev, _want), _got in zip(_CAP03, json.loads(_nr11.stdout)):
        check(_got == _want, lambda: "‏`chordFromEvent(%s)` ⇒ %r لا %r — المحرفُ المطبوعُ قُرئ مفتاحًا [CAP-03]"
            % (json.dumps(_ev, ensure_ascii=False), _got, _want))
    _known = set(_chords) | {p for c in _chords for p in c.split(" ")}
    check({"Ctrl+Shift+`", "Cmd+Shift+Alt+C"} <= _known, lambda: "شاهدا [CAP-03] لم يعودا في جدول الصفحة — يُغذّى الحارسُ بغيرهما")

    # ── [CAP-04] صندوقٌ سلوكيّ: `docs.js` المشحونُ يُنفَّذ كاملًا على صفحةٍ مزيّفة ──
    # فحوصُ الالتقاط أعلاه تقرأ نصَّ المعالج، فكانت تُخدَع بإبطالٍ لا يمسّ النصّ: سطرُ
    # `blur` تعليقًا، و`if (false) resetOut();`، ومهلةٌ تُظلَّل بعد تعريفها — كلُّها خضراء
    # والميزةُ معطوبة (قِيس بالزرع). فيُشغَّل `tests/docs/docs_sandbox.js` على صفوف الصفحة
    # المبنيّة وفهرس بحثها، ويرسل أحداثًا كما يرسلها المتصفّح، ويقيس ما يقرؤه الزائر:
    # التعليقُ وحسمُه، وإلغاؤه بـEscape وفقدانِ البؤرة والمهلة وIME، والترشيحُ بلا تشكيلٍ
    # ومن وسط الاسم، والأسهمُ وEscape في نتائج البحث.
    def _plain(t):
        return re.sub(r"[ً-ْٰـ]", "", t).replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    _secs = []
    for _sm in re.finditer(r'<section class="kbd-section">(.*?)</section>', _kb_html, re.S):
        _rows = []
        for _tm in re.finditer(r'<tr data-search="([^"]*)"(?: data-chords="([^"]*)")?><td><span class="cmd-name">([^<]*)</span>',
                               _sm.group(1)):
            _rows.append({"search": _html.unescape(_tm.group(1)),
                          "chords": None if _tm.group(2) is None else _html.unescape(_tm.group(2)),
                          "name": _html.unescape(_tm.group(3))})
        _secs.append({"rows": _rows})
    _all_rows = [r for sec in _secs for r in sec["rows"]]
    _by_chord = {c: r["name"] for r in _all_rows if r["chords"] for c in r["chords"].split("|")}
    _save_all, _save_one = _by_chord.get("Ctrl+K S"), _by_chord.get("Ctrl+S")
    # صفٌّ تُطابَق كلمتُه الثانيةُ بلا تشكيل: مطابقةٌ من وسط الاسم **و**بلا شدّةٍ معًا
    _frow = next((r["name"] for r in _all_rows
                  if len(r["name"].split()) > 1 and _plain(r["name"].split()[1]) != r["name"].split()[1]), None)
    if not (_secs and _save_all and _save_one and _frow):
        bad("صفحةُ الاختصارات بلا ما يقيسه الصندوق (أقسام، Ctrl+K S، Ctrl+S، صفٌّ مشكول) [CAP-04]")
    else:
        with open(os.path.join(OUT, "search-index.json"), encoding="utf-8") as _sif:
            _sindex = json.load(_sif)
        # الصندوقُ يقيس الشجرةَ التي يبنيها `_page_tree`؛ وموضعٌ تفترق فيه عن شجرة المتصفّح
        # يجعل أخضرَه شهادةً على صفحةٍ غيرِ المشحونة — فيُقال قبل نتيجته.
        _tree, _tree_errs = _page_tree(_kb_html)
        for _te in _tree_errs:
            bad("keyboard/index.html: %s — الصندوقُ لا يرى ما يراه المتصفّح [CAP-04]" % _te)
        _fx = {"tree": _tree, "save_all": _save_all, "save_one": _save_one,
               "filter_row": _frow, "filter_query": _plain(_frow.split()[1]),
               "filter_query_raw": _frow.split()[1],
               "count_query": _save_all.split()[0],
               "search_query": "محراب", "index": _sindex}
        # الـfixture في مجلّدٍ مؤقّتٍ لا في `site/public`: `deploy_site.sh` يحزم `public/` كلَّه،
        # وحارسٌ يُقتَل بين الكتابة والحذف كان يترك فيه ملفًّا يُشحَن ولا يراه [OUT-03]
        # (يفحص `public/assets` وحدَه).
        import tempfile
        with tempfile.TemporaryDirectory() as _fxd:
            _fxp = os.path.join(_fxd, "cap04-fixture.json")
            with open(_fxp, "w", encoding="utf-8") as _fxf:
                json.dump(_fx, _fxf, ensure_ascii=False)
            try:
                _nr12 = subprocess.run([_node, os.path.join(ROOT, "tests", "docs", "docs_sandbox.js"),
                                        os.path.join(OUT, "assets", "docs.js"), _fxp],
                                       capture_output=True, encoding="utf-8", errors="replace", timeout=60)
                _sb_out, _sb_err = _nr12.stdout, _nr12.stderr
            except subprocess.TimeoutExpired:
                _sb_out, _sb_err = "", "انقضت ‎60‎ ثانية — مؤقّتٌ أو وعدٌ لا ينتهي في الصندوق"
        try:
            _sb = json.loads(_sb_out)
            # و`{}` أو `{"fails": "…"}` كانا `KeyError` أو حروفًا تُعدّ فشولًا لا خطأً مُسمًّى
            if not (isinstance(_sb, dict) and isinstance(_sb.get("fails"), list)
                    and isinstance(_sb.get("ran"), int)):
                raise ValueError(_sb_out)
        except ValueError:
            _sb = {"ran": 0, "fails": ["خرجُ الصندوق ليس JSON بشكل {ran, fails}: %s %s [CAP-04]"
                                       % (_sb_out[-200:], _sb_err[-300:])]}
        for _f in _sb["fails"]:
            bad(_f)
        # بلا فشلٍ مسارُ الصندوق واحدٌ لا يتفرّع (كلُّ تفرّعٍ فيه يمرّ بفشلٍ مُسمًّى)، فعددُه ثابت:
        # ‎42‎. والأرضيّةُ هي العددُ نفسُه — ‎35‎ كانت تُسقط السيناريو (٣) أو (٤) كلَّه صامتًا.
        if not _sb["fails"] and _sb["ran"] < 42:
            bad("الصندوقُ قاس %d توقّعًا لا أقلَّ من ‎42‎ — سيناريو سقط صامتًا [CAP-04]" % _sb["ran"])

    # ── ٥ب) صفحةُ ‎404‎: أصولُها تصل من **كلّ** أصلٍ تُقدَّم منه [W404] ──
    # هي الصفحةُ الوحيدةُ التي تُقدَّم من أصلين — `mihrab.dev` و`app.mihrab.dev`
    # بـ`alias` — ولذلك **كلُّ** عناوينها مطلقةٌ بأصل الموقع عمدًا، على خلاف كلّ
    # صفحةٍ أخرى. فهي ساقطةٌ من الفحصين أعلاه بطبيعتها، وكانت ساقطةً من كلّ فحص:
    # طفرةٌ حوّلت أصلَها المطلقَ إلى مضيفٍ غريب ⇒ مرّت خضراءَ في كلّ طبقة.
    #
    # ويُقاس ضلعان، لأنّ أحدَهما وحدَه أوقعَنا مرّتين:
    #   ١) المضيفُ هو أصلُ الموقع لا شيءٌ آخر — وإلّا كانت الصفحةُ تُحمّل من مكانٍ
    #      لا نملكه، أو (كما وقع أوّلًا) بشرطةٍ من الجذر فتُحلّ على أصل الورشة
    #      حيث لا `assets/` ⇒ حلقةُ ‎404‎ مغلقة.
    #   ٢) وسياسةُ **كلّ** `location = /404.html` في إعداد nginx تسمح بذلك المضيف.
    nf = read("404.html")
    with open(os.path.join(SITE, "data", "site.json"), encoding="utf-8") as _f:
        _site = json.load(_f)
    origin = _site["canonical"].rstrip("/")
    app = (_site.get("browser") or {}).get("url", "").rstrip("/")

    # ① **لا عنوانَ نسبيًّا البتّة.** وهذا هو الضلعُ الذي كان ناقصًا: الحارسُ كان
    #    يسأل «أكلُّ مضيفٍ مذكورٍ مشروع؟» — سؤالٌ يجيب عنه العدمُ بنعم. فطفرةُ
    #    تحويلِ `https://mihrab.dev/assets/…` إلى `/assets/…` (وهي **العطبُ
    #    الأصليُّ حرفًا بحرف**) مرّت خضراء: لا مضيفَ غريبًا، لأنّه لا مضيفَ. وعلى
    #    `app.mihrab.dev` تُحلّ الشرطةُ على حمولة الورشة حيث لا `assets/` ⇒ صفحةٌ
    #    عاريةٌ وكلُّ رابطٍ فيها ‎404‎: حلقةٌ مغلقة.
    rel = sorted({m.group(1) for m in re.finditer(r'(?:href|src)="([^"]*)"', nf)
                  if not m.group(1).startswith(("https://", "http://", "mailto:",
                                                "data:", "#"))})
    check(not rel, lambda: "‏404.html تحمل عنوانًا غيرَ مطلق: %s — وهي تُقدَّم من أصلين (`alias`)، "
        "فالشرطةُ من الجذر تُحلّ على حمولة الورشة حيث لا `assets/`: الصفحةُ تصل "
        "عاريةً وكلُّ رابطٍ فيها ‎404‎ [W404]" % ", ".join(rel))

    # ② **وكلُّ مضيفٍ في الملفّ لا ما ورد في `href`/`src` وحدَه.** `srcset`
    #    و`url()` في نمطٍ سطريٍّ وسمةٌ بلا اقتباسٍ كلُّها تُحمِّل من الشبكة
    #    ولا يلتقطها تعبيرٌ مقيَّدٌ بسمتين (قِيس: ثلاثُ طفراتٍ مرّت خضراء).
    #    والمقارنةُ **بالمضيف تامًّا لا بالبادئة**: `https://github.com.evil`
    #    يبدأ بـ`https://github.com` ومرّ أخضرَ كذلك.
    ALLOW = {origin, app, "https://github.com", "https://vscodium.com"}
    nf_hosts = {"https://" + m.group(1)
                for m in re.finditer(r"https?://([A-Za-z0-9._-]+)", nf)}
    need(nf_hosts, lambda: "لا أصولَ مطلقةً في 404.html — تغيّرت بنيتُها [W404]")
    extra = sorted(nf_hosts - ALLOW)
    check(not extra, lambda: "‏404.html تحمّل من مضيفٍ غيرِ أصل الموقع: %s — وهي تُقدَّم من أصلين، "
        "فكلُّ عنوانٍ فيها يجب أن يكون مطلقًا بأصل الموقع [W404]" % ", ".join(extra))

    REF = re.compile(r'(?:href|src)="((?!https?:|//|#|mailto:)[^"]+)"')
    for rel in ("index.html", "download/index.html", "docs/index.html",
                "keyboard/index.html"):
        page_dir = os.path.dirname(os.path.join(OUT, rel))
        for m in REF.finditer(read(rel)):
            url = m.group(1).split("#")[0].split("?")[0]
            if not url or url.endswith("/"):
                continue          # صفحةٌ لا أصل — تُغطّى بفحص الصفحات أعلاه
            norm = url.lstrip("./")
            if norm.startswith(DL_BASE):
                name = norm[len(DL_BASE):]
                if name not in DL_FILES:
                    bad("رابطُ تنزيلٍ لا يذكره المانيفست (%s): %s" % (rel, url))
                continue
            target = os.path.normpath(os.path.join(page_dir, url))
            if not os.path.exists(target):
                bad("أصلٌ مُشارٌ إليه ولا وجودَ له في المخرَج (%s): %s" % (rel, url))

    # ── ٥) كلُّ منصّةٍ في المانيفست معروفةٌ في site.json ──
    ids = {p["id"] for p in data["platforms"]}
    with open(os.path.join(SITE, "data", "releases.json"), encoding="utf-8") as f:
        rel_data = json.load(f)
    for a in rel_data.get("assets", []):
        if a.get("id") not in ids:
            bad("أصلٌ بمعرّفِ منصّةٍ مجهول في releases.json: %r" % a.get("id"))
        for k in ("file", "size", "sha256"):
            if not a.get(k):
                bad("أصل %r بلا %s — الصفحةُ ستعرض صفًّا ناقصًا." % (a.get("id"), k))
    if rel_data.get("assets") and not rel_data.get("version"):
        bad("releases.json فيه أصولٌ بلا `version` — الصفحةُ ستُخفيها كلَّها.")

    # ── ٦) روابطُ الهويّة تطابق ما يُبنى فعلًا ──
    # عطبٌ سبق أن أُبلغ عنه من هذا الصنف: مفتاحٌ في product.json يشير إلى صفحةٍ
    # لا وجودَ لها، فيقود «مساعدة ← التوثيق» إلى 404.
    with open(os.path.join(ROOT, "product-overrides", "product.json"),
              encoding="utf-8") as f:
        prod = json.load(f)
    canon = data["canonical"].rstrip("/") + "/"
    for key in ("documentationUrl", "downloadUrl", "keyboardShortcutsUrlWin",
                "keyboardShortcutsUrlLinux", "keyboardShortcutsUrlMac"):
        url = prod.get(key)
        if not url:
            continue
        if not url.startswith(canon):
            bad("product.json:%s لا يشير إلى %s — %s" % (key, canon, url))
            continue
        path = url[len(canon):].strip("/")
        target = os.path.join(OUT, path, "index.html") if path else os.path.join(OUT, "index.html")
        if not os.path.isfile(target):
            bad("product.json:%s يشير إلى صفحةٍ لا تُبنى: %s" % (key, url))

    # ── ٨) المخرَجُ يبدأ فارغًا، ولا يُمحى ما ليس مخرَجًا [OUT-01] ──
    # `deploy_site.sh` يحزم `site/public/` كلَّه ويعد أنّ «ما لم يُبنَ هذه المرّة
    # ليس موجودًا هناك». والوعدُ يصدق فقط إن بدأ `public/` فارغًا — وكان لا
    # يبدأ: صفحةٌ حُذفت من `content/` بقيت تُنشَر بلا خطأ. ويُقاس هنا **بأربعة
    # بناءاتٍ حقيقيّة** في مجلّدٍ مؤقّت لا بقراءة المصدر: (١) مخرَجٌ سابقٌ فيه
    # ملفٌّ بائت ⇒ يُمحى ويُعاد بناؤه والشاهدُ يُعاد كتابتُه؛ (٢) مجلّدٌ غيرُ فارغٍ
    # **بلا شاهد** ⇒ يُرفَض ولا يُمسّ — `MIHRAB_SITE_OUT` قد يشير إلى أيّ مكان؛
    # (٣) وصلةٌ في المخرَج إلى مجلّدٍ خارجيّ ⇒ تُفكّ ولا يُمسّ هدفُها؛ (٤) فشلٌ في
    # منتصف المحو ⇒ الشاهدُ باقٍ، لأنّه يُمحى آخرًا.
    import tempfile
    _bpy = os.path.join(SITE, "build.py")
    _mark = ".mihrab-site-build"
    _env0 = dict(os.environ, PYTHONIOENCODING="utf-8")
    with tempfile.TemporaryDirectory() as _td:
        _o1 = os.path.join(_td, "prev")
        # والأسماءُ عشوائيّةٌ كما في `main()`: محوٌ بالاسم كان يمرّ (قِيس).
        _t8 = uuid.uuid4().hex[:8]
        os.makedirs(os.path.join(_o1, "stale-page-" + _t8))
        os.makedirs(os.path.join(_o1, "assets"))
        with open(os.path.join(_o1, _mark), "w") as _mf:
            _mf.write("x")
        # ثلاثةُ مواضع لا واحد: محوٌ **جزئيٌّ** يستبقي `assets/` («للسرعة») كان
        # يمرّ حين كان البائتُ الوحيدُ في مجلّدٍ خاصّ. قِيس بالطفرة.
        _stales = [os.path.join(_o1, "stale-page-" + _t8, "index.html"),
                   os.path.join(_o1, "assets", "stale-%s.css" % _t8),
                   os.path.join(_o1, "stale-%s.html" % _t8)]
        for _stale in _stales:
            with open(_stale, "w") as _sf:
                _sf.write("stale")
        _r1 = subprocess.run([sys.executable, _bpy], cwd=SITE, capture_output=True,
                             timeout=120, env=dict(_env0, MIHRAB_SITE_OUT=_o1))
        need(_r1.returncode == 0, lambda: "البناءُ في مخرَجٍ سابقٍ (بشاهد) فشل [OUT-01]:\n"
            + _r1.stderr.decode("utf-8", "replace")[-800:])
        _left = [os.path.relpath(_s, _o1) for _s in _stales if os.path.exists(_s)]
        check(not _left, lambda: "ملفٌّ بائتٌ من بناءٍ سابقٍ نجا البناءَ الجديد (%s) — سيُحزَم ويُنشَر "
            "إلى الأبد [OUT-01]" % "، ".join(_left))
        check(os.path.isfile(os.path.join(_o1, "index.html")), lambda: "لم يُبنَ شيءٌ [OUT-01]")
        check(os.path.isfile(os.path.join(_o1, _mark)), lambda: "الشاهدُ لا يُعاد كتابتُه بعد المحو — فالبناءُ التالي سيرفض مخرَجَه "
            "هو [OUT-01]")

        _o2 = os.path.join(_td, "foreign")
        os.makedirs(_o2)
        _keep = os.path.join(_o2, "precious.txt")
        with open(_keep, "w") as _kf:
            _kf.write("not an output dir")
        _r2 = subprocess.run([sys.executable, _bpy], cwd=SITE, capture_output=True,
                             timeout=120, env=dict(_env0, MIHRAB_SITE_OUT=_o2))
        need(_r2.returncode != 0, lambda: "بنى فوق مجلّدٍ غيرِ فارغٍ بلا شاهد — `MIHRAB_SITE_OUT` قد يشير إلى "
            "أيّ مكان، والمحوُ بلا شاهدٍ محوُ ما لا نعرفه [OUT-01]")
        check(os.path.isfile(_keep), lambda: "مُحي ملفٌّ ليس من مخرَجٍ سابق [OUT-01]")
        check(not os.path.exists(os.path.join(_o2, "index.html")), lambda: "رفض بصوتٍ ثمّ بنى فوقه — الرفضُ يجب أن يسبق أيَّ كتابة [OUT-01]")

        # ── (٣) وصلةٌ في المخرَج السابق إلى مجلّدٍ خارجيّ: تُفكّ ولا تُتبَع ──
        # المخرَجُ قد يحمل وصلةً (رمزيّةً أو junction — خادمُ معاينةٍ يربط مجلّدَ
        # لقطات، أو مطوّرٌ يجرّب) إلى مجلّدٍ **ليس من البناء**. و`_wipe` في
        # `build.py` يفكّها بـ`rmdir`/`remove` من غير أن يمسّ هدفَها — وكان ذلك
        # بلا حارس: محوٌ يتبع الوصلةَ (‏`rmtree(realpath)`) يمحو مجلّدًا لا نملكه
        # والبناءُ أخضر. فيُقاس أنّ الملفَّ وراء الوصلة باقٍ، والوصلةُ زائلة،
        # والبناءُ ناجح. والوصلةُ رمزيّةٌ إن أُذِن بها (لينكس دائمًا، وويندوز بوضع
        # المطوّر) وإلّا junction بـ`mklink /J` بلا صلاحيّة — ولا تخطٍّ صامت.
        _o3 = os.path.join(_td, "linked")
        os.makedirs(_o3)
        with open(os.path.join(_o3, _mark), "w") as _mf3:
            _mf3.write("x")
        _ext = os.path.join(_td, "external-" + _t8)
        os.makedirs(_ext)
        _precious = os.path.join(_ext, "precious-%s.txt" % _t8)
        with open(_precious, "w") as _pf3:
            _pf3.write("not an output")
        _lnk = os.path.join(_o3, "linked-dir")
        try:
            os.symlink(_ext, _lnk, target_is_directory=True)
        except (OSError, NotImplementedError):
            _mkl = subprocess.run(["cmd", "/c", "mklink", "/J", _lnk, _ext],
                                  capture_output=True)
            need(_mkl.returncode == 0 and os.path.isdir(_lnk), lambda: "تعذّر إنشاءُ وصلةٍ (لا symlink ولا junction) — الضلعُ الثالثُ من "
                "[OUT-01] لا يُقاس هنا، ولا يُتخطّى صامتًا")
        _r3 = subprocess.run([sys.executable, _bpy], cwd=SITE, capture_output=True,
                             timeout=120, env=dict(_env0, MIHRAB_SITE_OUT=_o3))
        check(os.path.isfile(_precious), lambda: "**مُحي ملفٌّ وراء وصلةٍ في المخرَج** — المحوُ تبع الوصلةَ إلى مجلّدٍ "
            "ليس من البناء [OUT-01]")
        need(_r3.returncode == 0, lambda: "البناءُ في مخرَجٍ سابقٍ فيه وصلةٌ فشل [OUT-01]:\n"
            + _r3.stderr.decode("utf-8", "replace")[-800:])
        check(not os.path.lexists(_lnk), lambda: "الوصلةُ باقيةٌ في المخرَج بعد البناء — ستُحزَم وجهتُها وتُنشَر [OUT-01]")
        check(os.path.isfile(os.path.join(_o3, _mark)), lambda: "الشاهدُ لا يُعاد كتابتُه بعد فكّ الوصلة [OUT-01]")

        # ── (٤) فشلٌ في منتصف المحو يُبقي الشاهد ──
        # الشاهدُ يُمحى **آخرًا**: `listdir` يضعه أوّلًا، فمحوُه في ترتيبه كان يترك
        # `public/` غيرَ فارغٍ **بلا شاهد** عند أوّل مدخلٍ لا يُمحى — والبناءُ التالي
        # يرفض مخرَجَه هو حتّى يتدخّل أحد. والمدخلُ الذي لا يُمحى حقيقيٌّ لا مزعوم:
        # ملفٌّ بمقبضٍ مفتوحٍ من عمليّةٍ ثانية على ويندوز (‏`WinError 32`)، ومجلّدٌ
        # بلا إذنِ كتابةٍ على POSIX (حذفُ ما فيه `EACCES`). فيُقاس أنّ البناءَ يفشل
        # **بصوت** وأنّ الشاهدَ باقٍ. وبصلاحيّة الجذر على POSIX لا مدخلَ لا يُمحى،
        # فيُعلَن التخطّي ولا يُدفَن.
        _o4 = os.path.join(_td, "midfail")
        os.makedirs(_o4)
        with open(os.path.join(_o4, _mark), "w") as _mf4:
            _mf4.write("x")
        _stuck = os.path.join(_o4, "stuck-" + _t8)
        _root_posix = os.name != "nt" and getattr(os, "geteuid", lambda: 1)() == 0
        if _root_posix:
            print("⚠️ [OUT-01] الضلعُ الرابعُ (الشاهدُ يُمحى آخرًا) لا يُقاس بصلاحيّة "
                  "الجذر: لا مدخلَ يمتنع عن المحو.")
        else:
            _holder = None
            if os.name == "nt":
                with open(_stuck, "w") as _sf4:
                    _sf4.write("x")
                _holder = subprocess.Popen(
                    [sys.executable, "-c",
                     "import sys,time; f=open(sys.argv[1],'rb'); sys.stdout.write('ok'); "
                     "sys.stdout.flush(); time.sleep(300)", _stuck],
                    stdout=subprocess.PIPE)
            else:
                os.makedirs(_stuck)
                with open(os.path.join(_stuck, "f"), "w") as _sf4:
                    _sf4.write("x")
                os.chmod(_stuck, 0o500)
            try:
                # داخل `try`: المقبضُ الحابسُ يُقتَل وإن توقّف الحارسُ هنا (كان يبقى ‎300‎ ثانية)،
                # و`need` لا `check`: بلا مقبضٍ ينجح المحوُ فيُقرأ ما بعده عطبًا في البناء لا في الحارس.
                if _holder is not None:
                    need(_holder.stdout.read(2) == b"ok", lambda: "لم يُفتح المقبضُ الحابس [OUT-01]")
                _r4 = subprocess.run([sys.executable, _bpy], cwd=SITE,
                                     capture_output=True, timeout=120,
                                     env=dict(_env0, MIHRAB_SITE_OUT=_o4))
            finally:
                if _holder is not None:
                    _holder.kill()
                    _holder.wait()
                else:
                    os.chmod(_stuck, 0o700)
            need(_r4.returncode != 0, lambda: "مدخلٌ لا يُمحى مرّ صامتًا — البناءُ أخضرُ فوق مخرَجٍ لم يُمحَ كلُّه، "
                "والبائتُ يُحزَم [OUT-01]")
            check(os.path.isfile(os.path.join(_o4, _mark)), lambda: "فشلٌ في منتصف المحو ترك المخرَجَ **بلا شاهد** — الشاهدُ يُمحى أوّلًا "
                "لا آخرًا، والبناءُ التالي سيرفض مخرَجَه هو [OUT-01]")

    # ── ٧) تثبيتُ إضافةِ ألف: الجالبُ وصفحةُ المعاينة يقولان الشيءَ نفسَه ──
    # الإصدارُ والبصمةُ مكتوبان في مكانين: `build/fetch_alif_extension.sh` (ما يُبنى
    # به) و`site/data/releases-alif.json` (ما تُعلنه الصفحة). ترقيةُ أحدِهما وحدَه
    # تجعل الصفحةَ تُملي على الزائر بصمةً يقارن بها شيئًا لم يُبنَ منها.
    fetch = os.path.join(ROOT, "build", "fetch_alif_extension.sh")
    alif_json = os.path.join(SITE, "data", "releases-alif.json")
    if os.path.isfile(fetch) and os.path.isfile(alif_json):
        with open(fetch, encoding="utf-8") as f:
            src = f.read()
        with open(alif_json, encoding="utf-8") as f:
            declared = (json.load(f).get("alif_extension") or {})
        for var, key in (("ALIF_EXT_VERSION", "version"), ("ALIF_EXT_SHA256", "sha256")):
            m = re.search(r"\$\{%s:-([^}]*)\}" % var, src)
            if not m:
                bad("لم أجد تثبيتَ %s في fetch_alif_extension.sh" % var)
            elif m.group(1) != declared.get(key):
                bad("تثبيتُ ألف منجرف: الجالبُ %s=%r وصفحةُ المعاينة %r"
                    % (key, m.group(1), declared.get(key)))

        # والمفسّرُ مثلُها: إصدارٌ واحدٌ وثلاثُ بصماتٍ لثلاث منصّات. وبصمةُ منصّةٍ
        # تُرقّى وحدَها في الجالبِ دون الصفحةِ تجعل مطوّرَ تلك المنصّةِ يقارن بصمةً
        # لا تخصّ ما نزّله — وهو أسوأُ من ألّا نعلن بصمةً أصلًا.
        runtime = (json.load(open(alif_json, encoding="utf-8")).get("alif_runtime") or {})
        m = re.search(r'ALIF_RUNTIME_VERSION:-([^}]*)\}', src)
        if not m:
            bad("لم أجد تثبيتَ ALIF_RUNTIME_VERSION في fetch_alif_extension.sh")
        elif m.group(1) != runtime.get("version"):
            bad("تثبيتُ مفسّر ألف منجرف: الجالبُ version=%r وصفحةُ المعاينة %r"
                % (m.group(1), runtime.get("version")))
        pinned = dict(re.findall(
            r'RT_ASSET="([^"]+)"\s*\n\s*RT_SHA="\$\{ALIF_RUNTIME_SHA256:-([0-9a-f]{64})\}"', src))
        declared_assets = runtime.get("assets") or {}
        if not pinned:
            bad("لم أجد بصماتِ حزمِ المفسّر في fetch_alif_extension.sh")
        for asset, sha in sorted(pinned.items()):
            if declared_assets.get(asset) != sha:
                bad("بصمةُ %s منجرفة: الجالبُ %r وصفحةُ المعاينة %r"
                    % (asset, sha, declared_assets.get(asset)))
        for asset in sorted(set(declared_assets) - set(pinned)):
            bad("صفحةُ المعاينة تُعلن حزمةً لا يجلبها الجالب: %s" % asset)

    # ── [MAN-01] مَن يبقى على الخادم: المانيفستُ المخبوزُ أم الحيّ ──
    # ‏`deploy_site.sh` يسأل `build/lib/manifest_pick.py` ولا يقرّر بنفسه، والقرارُ يُقاس هنا
    # جدوليًّا: كان سطورًا داخل السكربت بلا اختبار، وقِيس فيه أنّ مرشَّحًا يحلّ محلَّ
    # النهائيّ، وأنّ `v` البادئة تُقرأ صفرًا، وأنّ التساوي يمحو أصلًا رُفع بعد آخر مزامنة.
    import importlib.util as _ilu
    _mspec = _ilu.spec_from_file_location("_manifest_pick", os.path.join(ROOT, "build", "lib", "manifest_pick.py"))
    _mp = _ilu.module_from_spec(_mspec)
    _mspec.loader.exec_module(_mp)
    _A = {"id": "win-x64-zip", "file": "a.zip", "sha256": "11"}
    _B = {"id": "linux-x64-tar", "file": "b.tar.gz", "sha256": "22"}
    _MAN01 = [  # (المخبوز، الحيّ، المنتظَر)
        ({"version": "1.121.05803"}, None, "baked"),                          # مرآةٌ جديدة
        ({"version": "1.121.05803"}, {"version": "1.121.5802"}, "baked"),     # أصفارٌ بادئة
        ({"version": "1.121.5803"}, {"version": "1.122.0"}, "live"),          # الحيُّ أحدث
        ({"version": "1.2"}, {"version": "1.2.0.1"}, "live"),                 # الحشوُ بأصفار
        ({"version": "1.2.0-rc1"}, {"version": "1.2.0"}, "live"),             # مرشَّحٌ لا يحلّ محلَّ نهائيّ
        ({"version": "1.2.0"}, {"version": "1.2.1-rc1"}, "live"),             # مرشَّحٌ أحدثُ رقمًا
        ({"version": "1.2.0"}, {"version": "1.2.0-rc1"}, "baked"),            # النهائيُّ يحلّ محلَّ مرشَّحه
        ({"version": "1.2.0-rc2"}, {"version": "1.2.0-rc10"}, "live"),        # ‏rc10 عددٌ لا نصّ
        ({"version": "1.2.0-rc.10"}, {"version": "1.2.0-rc.9"}, "baked"),
        ({"version": "1.121.0"}, {"version": "v1.122.0"}, "live"),            # `v` البادئة
        ({"version": "1.2.0", "assets": [_A]}, {"version": "1.2.0", "assets": [_A, _B]}, "live"),  # أصلٌ رُفع بعدُ
        ({"version": "1.2.0", "assets": [_A, _B]}, {"version": "1.2.0", "assets": [_A]}, "baked"),
        ({"version": "1.2.0", "assets": [_A]}, {"version": "1.2.0", "assets": [_A]}, "baked"),
        ({"version": "1.2.0"}, {"version": ""}, "baked"),                     # حيٌّ بلا إصدار
        ({"version": "1.2"}, {"version": "1.2.0"}, "baked"),                  # التساوي بطولين: ليس الحيُّ أحدث
        ({"version": "1.2.0-beta"}, {"version": "1.2.0-RC1"}, "live"),        # beta < rc بلا حالة أحرف
        ({"version": "1.2.0-alpha.2"}, {"version": "1.2.0-alpha.2.1"}, "live"),  # معرِّفٌ زائدٌ أحدث
        ({"version": "1.2.0-rc.1"}, {"version": "1.2.0-alpha.9"}, "baked"),
    ]
    for _bk, _lv, _want in _MAN01:
        _got = _mp.pick(_bk, _lv)[0]
        if _got != _want:
            bad("‏`manifest_pick` المخبوزُ %s والحيُّ %s ⇒ %s لا %s [MAN-01]"
                % (_bk.get("version"), (_lv or {}).get("version"), _got, _want))
    for _badv in ("latest", "1.x.0", "", 5):
        try:
            _mp.pick({"version": _badv}, {"version": "1.0"})
            bad("‏`manifest_pick` قبل إصدارًا مخبوزًا غيرَ مفهوم %r بلا خطأ [MAN-01]" % _badv)
        except ValueError:
            pass
    for _badl in ("nightly", 5):
        try:
            _mp.pick({"version": "1.0"}, {"version": _badl})
            bad("‏`manifest_pick` قبل إصدارًا حيًّا غيرَ مفهوم %r بلا خطأ — يُقرأ صفرًا فيُمحى [MAN-01]" % (_badl,))
        except ValueError:
            pass
    for _badl in ("١.٣.٠",):
        try:
            _mp.pick({"version": "1.0"}, {"version": _badl})
            bad("‏`manifest_pick` قبل أرقامًا غيرَ لاتينيّة %r إصدارًا [MAN-01]" % (_badl,))
        except ValueError:
            pass
    # أصلٌ واحدٌ ببصمتين عند تساوي الإصدار: لا يُعرَف أيُّهما الأحدث، فلا يُختار صامتًا
    _A2 = dict(_A, sha256="99")
    try:
        _r = _mp.pick({"version": "1.2.0", "assets": [_A2]}, {"version": "1.2.0", "assets": [_A]})
        bad("‏`manifest_pick` اختار %r صامتًا والأصلُ نفسُه ببصمتين في الإصدار نفسِه [MAN-01]" % (_r[0],))
    except ValueError:
        pass
    # ومعرِّفٌ مكرَّرٌ في مانيفستٍ واحد (أو أصلان بلا `id`) لا يُطوى صامتًا إلى آخرهما؛
    # وتصادمٌ بمعرِّفٍ غائبٍ بجانب معرِّفٍ نصّيّ خطأٌ بصوت لا `TypeError` من الفرز.
    for _bk_a, _lv_a in (([_A], [_A, _A2]), ([_A], [{"file": "x"}, {"file": "y"}]),
                         ([{"file": "x"}, dict(_A)], [{"file": "y"}, _A2])):
        try:
            _r = _mp.pick({"version": "1.2.0", "assets": _bk_a}, {"version": "1.2.0", "assets": _lv_a})
            bad("‏`manifest_pick` اختار %r صامتًا ومعرِّفٌ مكرَّرٌ أو متصادمٌ في %r [MAN-01]" % (_r[0], _lv_a))
        except ValueError:
            pass
    # والواجهةُ نفسُها كما يستدعيها `deploy_site.sh`: الحيُّ على stdin، والقرارُ على stdout،
    # وغيرُ المفهوم خروجٌ ‎2‎ — فوحدةٌ صحيحةٌ بواجهةٍ معطوبةٍ لا تمرّ.
    _mpy = os.path.join(ROOT, "build", "lib", "manifest_pick.py")
    _mbk = os.path.join(OUT, "dl", "releases.json")
    for _stdin, _rc, _out in (("", 0, "baked"), ('{"version":"nightly"}', 2, "")):
        _cr = subprocess.run([sys.executable, _mpy, _mbk], input=_stdin, capture_output=True,
                             encoding="utf-8", errors="replace", timeout=60)
        if _cr.returncode != _rc or _cr.stdout.strip() != _out:
            bad("‏`manifest_pick.py` على stdin %r ⇒ خروج %s وخرج %r لا %s و%r [MAN-01]"
                % (_stdin, _cr.returncode, _cr.stdout.strip(), _rc, _out))

    report()
    return 1 if fails else 0


def report():
    # ‏`same_guard.py` يقارن هذه المفاتيحَ بين مرجعٍ وشجرة عمل، فيسمّي ما تغيّر لا البصمةَ وحدها.
    _keys = os.environ.get("MIHRAB_GUARD_KEYS")
    if _keys:
        with open(_keys, "w", encoding="utf-8") as _kf:
            json.dump(dict(sorted(evaluated.items())), _kf, ensure_ascii=False, indent=0)
    if fails:
        print("❌ %d عطبٌ بنيويّ:" % len(fails))
        for f in fails:
            print("   · %s" % f)
    else:
        print("✅ الموقعُ سليمٌ بنيويًّا: الصفحات، والمراسي، والمانيفست، وروابطُ الهويّة."
              " (%d فحصًا مُقيَّمًا · البصمة %s)" % fingerprint())


def _run():
    """‏`need` يوقف بعد عرض ما جُمع، وانهيارٌ غيرُ متوقَّعٍ يُعرَض مع ما جُمع قبله."""
    try:
        return main()
    except _Stop as e:
        bad(str(e))
    except Exception:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        bad("انهار الحارسُ بعد %d عطبٍ مجموع — الانهيارُ أعلاه" % len(fails))
    report()
    return 1


if __name__ == "__main__":
    sys.exit(_run())
