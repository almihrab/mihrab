# -*- coding: utf-8 -*-
"""ما رآه محاكي أندرويد ويُقاس بالحساب [AND-01..07].

أقسامُ `main()` القديمة بنصّها، بترتيبها في `check_site.py` (‏`SECTIONS`)."""
from .core import *  # noqa: F401,F403

# الوسومُ التي تحرسها أقسامُ هذه الوحدة، بما يمسكه كلٌّ منها — منها يُولَّد جدولُها في
# `site/guide/checks.md` (‏`python tests/docs/check_site.py --list`)، ويحرس التطابقَ [GRD-03].
TAGS = {
    "AND-01": "ما قِيس على محاكي أندرويد ثمّ عاد: سيريفًا في سلسلة خطوط، وحافّةَ الشيفرة تحت زرّ النسخ، وفراغًا متراكمًا فوق اللقطة",
    "AND-02": "التقاطًا يدّعي قراءةَ اختصارٍ لم يصل من لوحة مفاتيحٍ افتراضيّة",
    "AND-03": "بطاقةَ هاتفٍ تَعِد بأكثرَ ممّا قِيس (‏iOS «لم يُقَس»)",
    "AND-04": "هدفَ لمسٍ في الدرج أو الترويسة دون 44px",
    "AND-05": "أرقامَ أوّل إقلاعٍ في الوثائق غيرَ المقيسة",
    "AND-06": "`letter-spacing` غيرَ صفرٍ في أيّ CSS يصل الزائر",
    "AND-07": "حجمًا معروضًا غيرَ عشريّ في المانيفست المخبوز أو `site.js` أو المعاينة",
    "AND-08": "أسهمًا أو Escape لا تعمل في نتائج البحث، أو ترشيحًا لا يُنطَق",
}

def s23_and01_measured(c):
    # ── ما رآه محاكي أندرويد يُقاس بالحساب [AND-01] ──
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
    _l = locals()
    for _n in ('_HP', '_css_get', '_rules', '_tokens'):
        if _n in _l:
            setattr(c, _n, _l[_n])


def s24_and01_no_serif(c):
    # ── [AND-01] لا اسمَ يحلّه أندرويد إلى سيريف في أيّ سلسلةٍ تصل الزائر ──
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
    _l = locals()
    for _n in ('_chains',):
        if _n in _l:
            setattr(c, _n, _l[_n])


def s25_and06_letter_spacing(c):
    _c = vars(c)
    if "_chains" in _c:
        _chains = _c['_chains']
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


def s26_and07_decimal_size(c):
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
    _l = locals()
    for _n in ('_node',):
        if _n in _l:
            setattr(c, _n, _l[_n])


def s27_and01_copy_edge(c):
    _c = vars(c)
    if "_css_get" in _c:
        _css_get = _c['_css_get']
    if "_rules" in _c:
        _rules = _c['_rules']
    if "_tokens" in _c:
        _tokens = _c['_tokens']
    # ── [AND-01] حافّةُ الشيفرة فوق زرّ النسخ على اللمس، وتعود في الطباعة ──
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


def s28_and01_hero_gap(c):
    _c = vars(c)
    if "_HP" in _c:
        _HP = _c['_HP']
    if "_css_get" in _c:
        _css_get = _c['_css_get']
    if "_rules" in _c:
        _rules = _c['_rules']
    if "_tokens" in _c:
        _tokens = _c['_tokens']
    # ── [AND-01] بين البطل واللقطة: حشوٌ + هامشٌ لا يُبتلَع + هامش — من المخرَج ──
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


def s29_and02_capture_ime(c):
    # ── الجولةُ ‎13‎: أربعُ طفراتٍ كانت تعود صامتةً [AND-02..05] ──
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
    _l = locals()
    for _n in ('_docs_js', '_ime'):
        if _n in _l:
            setattr(c, _n, _l[_n])


def s30_and03_ios_card(c):
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


def s31_and04_touch_targets(c):
    _c = vars(c)
    if "_css_get" in _c:
        _css_get = _c['_css_get']
    if "_rules" in _c:
        _rules = _c['_rules']
    if "_tokens" in _c:
        _tokens = _c['_tokens']
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


def s32_and05_boot_numbers(c):
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


def s33_and08_search_arrows_filter(c):
    _c = vars(c)
    if "_docs_js" in _c:
        _docs_js = _c['_docs_js']
    if "_node" in _c:
        _node = _c['_node']
    # ── الجولةُ ‎15‎: الأسهمُ وEscape في نتائج البحث، والترشيحُ يُنطَق [AND-08] ──
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
    _l = locals()
    for _n in ('_kb_html',):
        if _n in _l:
            setattr(c, _n, _l[_n])
