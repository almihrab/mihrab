#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""أساسُ حارس الموقع (‏`tests/docs/check_site.py`): ‏`check`/`need`/`bad` وتجميعُ الفشل، والعدّادُ
وبصمتُه، و`read`، وشجرةُ الصفحة المبنيّة، وماسحُ CSS المستقلّ، و`report`. كلُّ وحدةٍ في
`site_guard/` تستورده بـ`from .core import *`.
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

# ‏`tests/docs/` مستوًى فوق هذه الوحدة، والجذرُ مستويان فوقه.
DOCS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(DOCS_DIR))
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


# ── تتبّعُ الأقسام لـ`mutation.mjs` ──
# بـ`MIHRAB_GUARD_TRACE=<ملفّ>` يُكتب لكلّ فشلٍ قسمُه ونوعُه (‏bad: عطبٌ مجموع، stop: إيقافٌ
# بـ`need`، return: قسمٌ أنهى الحارسَ بلا عطبٍ مسجَّل، crash: انهيار) وموضعُه ونصُّه — فيُقاس أنّ
# المُصابَ يُحمِّر القسمَ الذي يُعلنه `sec` **بنصّ `expect`**، في كلّ تشغيل لا مرّةً وقتَ كتابته.
# ولا يتغيّر من الخرج ولا من العدد والبصمة شيء. ويُنزَع المتغيّرُ من البيئة: البناءُ الذي
# يشغّله الحارسُ لا يرثه (‏DET-01 يسمح بمفاتيح `MIHRAB_*` الحرفيّة).
_TRACE = os.environ.pop("MIHRAB_GUARD_TRACE", None)
current = None  # القسمُ الجاري؛ يضبطه `check_site.main`
_trace = []


def _mark(kind, msg=None, at=None):
    if not _TRACE or (current is None and kind != "crash"):
        return
    if at is None:
        f = sys._getframe(1)
        while f is not None and os.path.abspath(f.f_code.co_filename) == os.path.abspath(__file__):
            f = f.f_back
        at = "%s:%d" % (os.path.basename(f.f_code.co_filename), f.f_lineno) if f is not None else "؟"
    _trace.append({"sec": current or "<main>", "kind": kind, "at": at, "msg": "" if msg is None else str(msg)})


def write_trace():
    if not _TRACE:
        return
    try:
        with open(_TRACE, "w", encoding="utf-8") as fh:
            json.dump(_trace, fh, ensure_ascii=False)
    except OSError as e:  # لا يُخفي رمزَ خروج الحارس؛ و`mutation.mjs` يقرأ غيابَ الملفّ عطبًا
        print("⚠️ تعذّرت كتابةُ التتبّع %s: %s" % (_TRACE, e), file=sys.stderr)


def bad(msg):
    _mark("bad", msg)
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
        text = msg() if callable(msg) else msg
        _mark("stop", text)
        raise _Stop(text)
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


# ما تستورده الوحداتُ بـ`from .core import *` — والمسبوقُ بشرطةٍ سفليّةٍ معه.
__all__ = [
    'collections',
    'glob',
    'hashlib',
    '_html',
    'json',
    'os',
    're',
    'shutil',
    'subprocess',
    'sys',
    'uuid',
    'DOCS_DIR',
    'ROOT',
    'SITE',
    'OUT',
    'fails',
    'evaluated',
    '_TAG',
    '_strings',
    '_key',
    '_count',
    'fingerprint',
    'bad',
    '_Stop',
    'check',
    'need',
    '_page_tree',
    'read',
    'css_strip_comments',
    'report',
]
