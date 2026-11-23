#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فحصٌ بنيويّ لمخرَج موقع محراب.

يمسك الأعطالَ التي **لا تظهر في المتصفّح**: زرًّا يقود إلى صفحةٍ لم تُبنَ، ووسمًا
يبحث عنه جافاسكربت ولا يجده فيموت السلوكُ كلُّه صامتًا، ومسارًا مطلقًا يربط المخرَج
بمضيفٍ بعينه فيكسر المرآة. وكلُّها أعطالٌ تمرّ من مراجعةِ العين لأنّ الصفحة تبدو سليمة.

    python tests/docs/check_site.py          # يبني ثمّ يفحص
    python tests/docs/check_site.py --no-build
"""
import html as _html
import json
import os
import re
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

fails = []


def bad(msg):
    fails.append(msg)


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
                raise AssertionError(
                    "‏`/*` داخل تعليقٍ مفتوحٍ في %s:%d — تعليقٌ متداخلٌ يُغلَق مبكّرًا "
                    "ويترك بقيّتَه نصًّا طليقًا [CSS-01]"
                    % (name, raw.count("\n", 0, pos) + 1))
            if ch2 == "*/":
                depth, pos = 0, pos + 2
                continue
            pos += 1
            continue
        if ch2 == "/*":
            depth, pos = 1, pos + 2
            continue
        if ch2 == "*/":
            raise AssertionError(
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
    assert depth == 0, "تعليقٌ لم يُغلَق في %s [CSS-01]" % name
    return "".join(out)


def main():
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
        r = subprocess.run([sys.executable, os.path.join(SITE, "build.py")],
                           cwd=ROOT)
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
            print("❌ فشل بناءُ الموقع.")
            return 1
        assert not _survived, (
            "بوائتُ في `site/public/` نجت البناءَ الحقيقيّ: %s — وهذا المجلّدُ بعينه "
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
    # فيُقاس على كلّ ورقةٍ في `site/assets/`: (١) كلُّ `*/` يُغلق `/*` مفتوحًا،
    # ولا `/*` داخل تعليق؛ (٢) بعد نزع التعليقات، كلُّ جملةٍ داخل `:root` إعلانٌ
    # (`اسم: قيمة`) أو فراغ؛ (٣) وأوّلُ `--font-ar` **بعد النزع** هو الخطُّ
    # المورَّد — فتعليقٌ يبتلع الإعلانَ يُسقِط هذا الشرطَ لا محالة.
    _css_dir = os.path.join(SITE, "assets")
    _css_decl, _css_refs = set(), set()
    for _cn in sorted(os.listdir(_css_dir)):
        if not _cn.endswith(".css"):
            continue
        with open(os.path.join(_css_dir, _cn), encoding="utf-8") as _cf3:
            _raw3 = _cf3.read()
        # الماسحُ (تعليق/سلسلة/‏`url(` بلا اقتباس) هو نفسُه النازع: ما تُقاس عليه
        # الجملُ أدناه هو ما مرّ من الماسح حرفًا بحرف — لا نصٌّ ثانٍ من `re.sub`
        # ساذجٍ يبتلع من `"/*"` إلى أوّل `*/` (انظر `css_strip_comments`).
        _bare = css_strip_comments(_raw3, _cn)
        for _rm in re.finditer(r":root(?:[^{]*)\{([^}]*)\}", _bare):
            for _stmt in _rm.group(1).split(";"):
                _st = _stmt.strip()
                assert not _st or re.match(r"^[\w-]+\s*:", _st), (
                    "جملةٌ ليست إعلانًا داخل `:root` في %s: %r — نصٌّ طليقٌ يبتلع "
                    "الإعلانَ الذي يليه بلا خطأ [CSS-01]" % (_cn, _st[:60]))
                # ── ولا إعلانَ داخل إعلان ──
                # نصٌّ طليقٌ يبدأ بـ`كلمة:` (‏`todo: …` بلا علامتَي تعليق) يمرّ من
                # الشرط أعلاه ويبتلع `--font-ar: …` التي تليه حتّى الفاصلة المنقوطة،
                # والشرطُ الأخيرُ يجد `--font-ar:` داخل الجملة المبتلَعة فيمرّ —
                # قِيس بالطفرة: خضراءُ والموقعُ بخطّ المتصفّح. فجملةٌ تحمل `--اسم:`
                # بعد نقطتَيها الأولى هي ابتلاع.
                _tail = _st[_st.index(":") + 1:] if ":" in _st else ""
                assert not re.search(r"(?<![\w-])--[\w-]+\s*:", _tail), (
                    "إعلانٌ مبتلَعٌ داخل جملةٍ أخرى في `:root` في %s: %r — ما قبله "
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
            assert _n_all == _n_root and (_cn == "mihrab-docs.css" or _n_all == 0), (
                "‏`%s` مُعلَنةٌ خارج `:root` أو خارج `mihrab-docs.css` (في %s) — إعلانُ "
                "عنصرٍ أو ورقةٍ لاحقةٍ يغلب سلسلةَ الخطّ المورَّد صامتًا [CSS-01]"
                % (_prop, _cn))
        for _ff in re.findall(r"(?<![\w-])font-family\s*:\s*([^;}]+)", _bare):
            assert re.fullmatch(r"var\(--font-(ar|mono)\)|inherit", _ff.strip()), (
                "‏`font-family: %s` في %s لا تشير إلى `--font-ar`/`--font-mono` — خطٌّ "
                "خارج السلسلة المورَّدة [CSS-01]" % (_ff.strip()[:50], _cn))
        assert not re.search(r"(?<![\w-])font\s*:", _bare), (
            "مختصَرُ `font:` في %s يُعيد `font-family` إلى قيمةٍ بلا `var()` فيُسقِط "
            "الخطَّ المورَّد صامتًا — يُكتَب `font-family`/`font-size` مفصَّلةً [CSS-01]" % _cn)
        if _cn == "mihrab-docs.css":
            _fa = re.findall(r"--font-ar\s*:\s*([^;}]+)[;}]", _bare)
            assert _fa, "لا `--font-ar` صالحٌ في `mihrab-docs.css` بعد نزع التعليقات [CSS-01]"
            _fa0 = _fa[-1].strip().split(",")[0].strip().strip("\"'")
            assert _fa0 == "IBM Plex Sans Arabic", (
                "أوّلُ `--font-ar` الفعليُّ هو %r — الخطُّ المورَّد لا يصل أحدًا "
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
                assert _vals, "لا `%s` في `mihrab-docs.css` [CSS-01]" % _prop
                for _item in _vals[-1].split(","):
                    _it = _item.strip()
                    _ok_item = bool(_it) and _it.lower() not in _css_wide and bool(
                        re.fullmatch(r'"[^"]+"|\'[^\']+\'', _it)
                        or re.fullmatch(r"-?[A-Za-z_][\w-]*(\s+-?[A-Za-z_][\w-]*)*", _it))
                    assert _ok_item, (
                        "عنصرٌ ليس اسمَ خطٍّ صالحًا في `%s`: %r — يُبطِل `font-family` "
                        "كلَّها وقتَ الحساب فيسقط الموقعُ إلى خطّ المتصفّح الافتراضيّ "
                        "بلا خطأ [CSS-01]" % (_prop, _it[:60]))
    _undef = sorted(_css_refs - _css_decl)
    assert not _undef, (
        "‏`var()` تشير إلى خاصّيّةٍ لا تُعلِنها أيُّ ورقة: %s — الإعلانُ المستعمِلُ "
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
    assert os.path.isfile(css_path), "لا `assets/fonts.css` في المخرَج [FNT-01]"
    with open(css_path, encoding="utf-8") as _f:
        fcss = _f.read()

    declared = re.findall(r'url\("fonts/([^"]+)"\)', fcss)
    # ── والمرجعُ `FONT_FACES` في المولِّد، لا مجلّدُ المصدر ──
    # أوّلُ صياغةٍ قابلت المُعلَنَ في `fonts.css` بما في `site/assets/fonts/` —
    # وهما يتقلّصان معًا: `write_fonts_css` لا يُعلِن إلّا الموجود، فحذفُ ملفٍّ
    # يُنقِص الطرفين ويبقى الحارسُ أخضر. قِيس بالطفرة: حذفُ وجهٍ لاتينيٍّ مرّ.
    # والمرجعُ الصحيحُ هو **ما يَعِد به المولِّد**: قائمةُ `FONT_FACES`.
    with open(os.path.join(SITE, "build.py"), encoding="utf-8") as _bf:
        _blk = _bf.read()
    _i = _blk.index("FONT_FACES = [")
    wanted = re.findall(r'\("([^"]+\.woff2)"', _blk[_i:_blk.index("]", _i)])
    assert len(wanted) >= 2, (
        "تعذّر قراءةُ `FONT_FACES` من `site/build.py` — تغيّرت صيغتُها؛ "
        "يُحدَّث الحارس [FNT-01]")
    # والوعدُ يُقابَل بالجرد المستقلّ: تقليصُ `FONT_FACES` عطبٌ لا إعفاء.
    _shrunk = [n for n, _f, _w, _h in EXPECT_FACES if n not in wanted]
    assert not _shrunk, (
        "وجهٌ يشترطه الجردُ ولا تَعِد به `FONT_FACES` في `site/build.py`: %s — "
        "وتقليصُ الوعد يُنقِص المُقاسَ والقياسَ معًا فيمرّ أخضر. من أسقط وجهًا "
        "عمدًا يُسقِطه من `EXPECT_FACES` هنا بتعليلٍ مكتوب [FNT-01]"
        % "، ".join(_shrunk))

    missing = [n for n in wanted if n not in declared]
    assert not missing, (
        "وجهٌ تَعِد به `FONT_FACES` ولا يُعلِنه `fonts.css`: %s. والنقصُ الجزئيُّ "
        "**أسوأُ من التامّ**: وجهٌ عربيٌّ بلا نظيرِه اللاتينيِّ يجعل السطرَ المختلَطَ "
        "بخطَّين، بينما النقصُ التامُّ يُبقيه متّسقًا بخطٍّ واحد. ضَع الملفَّ في "
        "`site/assets/fonts/` [FNT-01]" % "، ".join(missing))

    for name in declared:
        out_f = os.path.join(OUT, "assets", "fonts", name)
        assert os.path.isfile(out_f), (
            "‏`fonts.css` يُعلِن %s ولا وجودَ له في المخرَج — ‎404‎ في كلّ فتحةِ "
            "صفحة ثمّ سقوطٌ صامتٌ إلى خطّ النظام [FNT-01]" % name)
        with open(out_f, "rb") as _ff:
            raw = _ff.read()
        assert raw[:4] == b"wOF2", "%s ليس woff2 [FNT-01]" % name
        (dlen,) = _struct.unpack(">I", raw[8:12])
        assert dlen == len(raw), (
            "%s مبتور: يُعلِن %d بايتًا وعلى القرص %d — يرفضه المتصفّحُ ويسقط "
            "صامتًا إلى خطّ النظام [FNT-01]" % (name, dlen, len(raw)))

    # ── والبصمةُ والعائلةُ والوزن، لا الوجودُ وحدَه ──
    for _fn, _fam, _wt, _sha in EXPECT_FACES:
        _p = os.path.join(OUT, "assets", "fonts", _fn)
        assert os.path.isfile(_p), "وجهُ الجرد %s غائبٌ عن المخرَج [FNT-01]" % _fn
        _got = _hashlib.sha256(open(_p, "rb").read()).hexdigest()
        assert _got == _sha, (
            "بصمةُ %s لا تطابق الجرد (%s… بدل %s…) — وفحصُ الطول يمرّ على ملفٍّ "
            "فاسدِ المحتوى وعلى وجهٍ وُضِع مكانَ آخر. إن كان التغييرُ مقصودًا "
            "فحدِّث `EXPECT_FACES` [FNT-01]" % (_fn, _got[:12], _sha[:12]))
        # الزوجُ (عائلة، ملفّ) لا الملفُّ وحدَه: الملفُّ العربيُّ يُعلَن مرّتين
        # باسمين، وقياسُ «أوّلِ وجهٍ يحمل الملفّ» كان يرى الأوّلَ ويعمى عن الثاني.
        _fm = re.search(r'@font-face\{font-family:"' + re.escape(_fam)
                        + r'";src:url\("fonts/' + re.escape(_fn)
                        + r'"\)[^}]*?font-weight:(\d+)', fcss)
        assert _fm, (
            "لا `@font-face` باسم «%s» لـ%s في `fonts.css` — عائلةٌ غائبةٌ أو "
            "مغايرةٌ لا تصل السلسلةَ أصلًا [FNT-01]" % (_fam, _fn))
        assert int(_fm.group(1)) == _wt, (
            "‏%s باسم «%s» مُعلَنٌ بوزن %s والجردُ يقول %d — وزنٌ مكرّرٌ يترك "
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
                assert os.path.isfile(_st), (
                    "ورقةُ أنماطٍ مربوطةٌ لا تصل: %s ← %s [FNT-01]" % (_relp0, _sh))
            if not _relp0.startswith("preview/"):
                assert "mihrab-docs.css" in _t0, (
                    "صفحةُ قالبٍ بلا `mihrab-docs.css`: %s — تُعرَض عاريةً [FNT-01]" % _relp0)
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
    assert not _unlinked, (
        "صفحاتٌ في المخرَج بلا `fonts.css` صالحٍ — تُعرَض بخطّ النظام وحدَها بين "
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
        assert _why.strip(), (
            "بندٌ في `FONT_ALLOW` بلا تعليل (U+%04X) — القائمةُ البيضاءُ إعلانُ "
            "حدٍّ لا إعفاءٌ صامت [FNT-01]" % ord(_ch))

    def _ranges(var_name):
        m = re.search(var_name + r" = \(([^)]+)\)", bpy, re.S)
        assert m, "تعذّرت قراءةُ %s من `site/build.py` [FNT-01]" % var_name
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

    with open(os.path.join(SITE, "build.py"), encoding="utf-8") as _bf2:
        bpy = _bf2.read()
    ar_r, la_r = _ranges("_UR_AR"), _ranges("_UR_LA")
    overlap = ar_r & la_r
    assert not overlap, (
        "تداخُلٌ بين `_UR_AR` و`_UR_LA` في %d نقطةً (أوّلُها U+%04X) — مقطعٌ "
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
    assert not missing, (
        "محرفٌ ظاهرٌ خارجَ `_UR_AR`/`_UR_LA` وخارجَ القائمة البيضاء — يسقط إلى "
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
        assert os.path.isfile(_lic), (
            "لا `OFL.txt` في %s (%s) — وأوجهُ الخطّ مورَّدةٌ وتُنشَر. إرفاقُ "
            "الإشعار والرخصةِ شرطٌ في OFL‑1.1 لكلّ إعادةِ توزيع، والنشرُ إعادةُ "
            "توزيع [FNT-01]" % (_where, os.path.relpath(_d, ROOT)))
        with open(_lic, encoding="utf-8") as _lf:
            _lt = _lf.read()
        # النصُّ الكاملُ بإشعاره، لا ترويسةً مقتضبة: «Copyright» وحدَه يمرّ على
        # ملفٍّ فارغٍ إلّا من سطر.
        assert "SIL Open Font License" in _lt and "Copyright" in _lt, (
            "‏`OFL.txt` في %s لا يحمل نصَّ الرخصة وإشعارَ حقوق النشر [FNT-01]" % _where)
        assert len(_lt) > 3000, (
            "‏`OFL.txt` في %s أقصرُ من نصّ OFL‑1.1 (%d محرفًا) — رخصةٌ مبتورةٌ "
            "لا تُجزئ [FNT-01]" % (_where, len(_lt)))
        # والهُويّةُ لا الطولُ وحدَه: نصٌّ من ‎3001‎ محرفِ حشوٍ فيه الكلمتان كان
        # يمرّ أخضر. فتُشترَط علاماتُ **رخصةِ خطِّنا بعينه**: مالكُ الحقّ، ورقمُ
        # النسخة، والاسمُ المحجوز — وهي ما يجعل الملفَّ إشعارًا لا نصًّا طويلًا.
        for _mark in ("IBM Corp", "Version 1.1", "Reserved Font Name"):
            assert _mark in _lt, (
                "‏`OFL.txt` في %s لا يحمل «%s» — ليس إشعارَ رخصةِ الخطّ "
                "المورَّد [FNT-01]" % (_where, _mark))

    faces = re.findall(r"@font-face\{([^}]+)\}", fcss)
    assert len(faces) == len(declared), "عددُ `@font-face` لا يطابق المُعلَن [FNT-01]"
    for face in faces:
        _ur = re.search(r"unicode-range:([^;}]*)", face)
        assert _ur and _ur.group(1).strip(), (
            "وجهٌ بـ`unicode-range` **فارغ** في `fonts.css` — وإعلانٌ بلا قيمةٍ "
            "يُسقِطه المتصفّحُ كلَّه فيعود الوجهان متنازعَين: وهو العطبُ عينُه "
            "الذي أُضيف المدى ليمنعه [FNT-01]")
        for _tok in _ur.group(1).split(","):
            assert re.fullmatch(r"\s*U\+[0-9A-Fa-f]{1,6}(-[0-9A-Fa-f]{1,6})?\s*",
                                _tok), (
                "مدًى مشوَّهٌ في `fonts.css`: %r — والمتصفّحُ يُسقِط الإعلانَ "
                "كلَّه، فيعود التنازعُ [FNT-01]" % _tok)
        assert "unicode-range:" in face, (
            "وجهٌ بلا `unicode-range` في `fonts.css` — والأوجهُ مقلَّمة، فوجهان "
            "بالاسم والوزن نفسِهما بلا مدًى يتنازعان: يأخذ المتصفّحُ الأخيرَ "
            "ويهمل الأوّل، فنصفُ الموقع بخطٍّ ونصفُه بخطّ النظام [FNT-01]")
        assert "font-display:swap" in face, (
            "وجهٌ بلا `font-display:swap` — الافتراضيُّ يُخفي النصَّ حتّى يصل "
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
    assert len(_mono) == 2, (
        "المنتظَر وجهان باسم «%s» في `fonts.css` (‏400 و600) ووُجد %d — بلا "
        "الاسم الثاني يسقط العربيُّ في كتل الشيفرة إلى `Courier New` [FNT-01]"
        % (MONO_AR_FAMILY, len(_mono)))
    _ascii = set(range(0x20, 0x7F))
    _gen_punct = set(range(0x2000, 0x2070)) | set(range(0x2E00, 0x2E80))
    for f in _mono:
        rng = _ur_set(re.search(r"unicode-range:([^;}]*)", f).group(1))
        assert rng and rng <= ar_r, (
            "مدى «%s» يتجاوز `_UR_AR` (أوّلُ الزائد U+%04X) — اسمٌ ثانٍ للملفّ "
            "العربيّ لا يحمل غيرَ ما يحمله [FNT-01]"
            % (MONO_AR_FAMILY, min(rng - ar_r) if rng - ar_r else 0))
        # و«يغطّي» لا «لا يتجاوز» وحدَه: مدًى من محرفٍ واحدٍ كان يمرّ، والعربيُّ
        # في كتل الشيفرة يعود إلى `Courier New` — العطبُ الذي أُضيف الاسمُ لمنعه.
        _core = set(range(0x0600, 0x0700)) | set(range(0xFB50, 0xFE00)) | set(range(0xFE70, 0xFEFF))
        _gap = _core - rng
        assert not _gap, (
            "مدى «%s» لا يغطّي كتلةَ العربيّة الأساسيّة (ينقص U+%04X وما بعده، "
            "%d نقطة) — فالعربيُّ في كتل الشيفرة يسقط إلى `Courier New` [FNT-01]"
            % (MONO_AR_FAMILY, min(_gap), len(_gap)))
        for _bad, _why in ((_ascii, "محرفٌ لاتينيٌّ/رقمٌ/مسافة"),
                           (la_r, "مقطعٌ من الوجه اللاتينيّ"),
                           (_gen_punct, "ترقيمٌ عامٌّ له عرضٌ يُحاذى (واصلاتٌ ونحوُها)")):
            _hit = rng & _bad
            assert not _hit, (
                "مدى «%s» يلتقط %s (U+%04X) — فيصير متناسبَ العرض داخل كتلة "
                "شيفرةٍ وتنكسر المحاذاة [FNT-01]" % (MONO_AR_FAMILY, _why, min(_hit)))

    # والسلسلةُ تبدأ به فعلًا — وإلّا فالوجهُ مُعلَنٌ ولا يصل أحدًا.
    with open(os.path.join(SITE, "assets", "mihrab-docs.css"), encoding="utf-8") as _dc:
        _dcss = css_strip_comments(_dc.read(), "mihrab-docs.css")
    # **آخرُ** إعلانٍ لا أوّلُه: المتصفّحُ يطبّق الأخيرَ في التسلسل، فإعلانٌ
    # مُلحَقٌ بآخر الورقة كان يُبطِل الأوّلَ والحارسُ يقرأ الأوّلَ فيمرّ. والاقتباسُ
    # المفرد CSS صالح، فيُجرَّد كالمزدوج.
    # والقيمةُ قد تنتهي بـ`}` لا `;` (آخرُ إعلانٍ في كتلة) — فكلاهما فاصل.
    _fm_all = re.findall(r"--font-mono\s*:\s*([^;}]+)[;}]", _dcss)
    assert _fm_all, "لا `--font-mono` في `mihrab-docs.css` [FNT-01]"
    _first = _fm_all[-1].strip().split(",")[0].strip().strip("\"'")
    assert _first == MONO_AR_FAMILY, (
        "أوّلُ `--font-mono` هو %r لا «%s» — الاسمُ الثاني يعمل بمداه وحدَه، فلا "
        "يضرّ أوّلًا ولا ينفع إن سبقه خطٌّ يحمل العربيّةَ بعرضٍ آخر [FNT-01]"
        % (_first, MONO_AR_FAMILY))

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
    assert not rel, (
        "‏404.html تحمل عنوانًا غيرَ مطلق: %s — وهي تُقدَّم من أصلين (`alias`)، "
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
    assert nf_hosts, "لا أصولَ مطلقةً في 404.html — تغيّرت بنيتُها [W404]"
    extra = sorted(nf_hosts - ALLOW)
    assert not extra, (
        "‏404.html تحمّل من مضيفٍ غيرِ أصل الموقع: %s — وهي تُقدَّم من أصلين، "
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
        assert _r1.returncode == 0, (
            "البناءُ في مخرَجٍ سابقٍ (بشاهد) فشل [OUT-01]:\n"
            + _r1.stderr.decode("utf-8", "replace")[-800:])
        _left = [os.path.relpath(_s, _o1) for _s in _stales if os.path.exists(_s)]
        assert not _left, (
            "ملفٌّ بائتٌ من بناءٍ سابقٍ نجا البناءَ الجديد (%s) — سيُحزَم ويُنشَر "
            "إلى الأبد [OUT-01]" % "، ".join(_left))
        assert os.path.isfile(os.path.join(_o1, "index.html")), "لم يُبنَ شيءٌ [OUT-01]"
        assert os.path.isfile(os.path.join(_o1, _mark)), (
            "الشاهدُ لا يُعاد كتابتُه بعد المحو — فالبناءُ التالي سيرفض مخرَجَه "
            "هو [OUT-01]")

        _o2 = os.path.join(_td, "foreign")
        os.makedirs(_o2)
        _keep = os.path.join(_o2, "precious.txt")
        with open(_keep, "w") as _kf:
            _kf.write("not an output dir")
        _r2 = subprocess.run([sys.executable, _bpy], cwd=SITE, capture_output=True,
                             timeout=120, env=dict(_env0, MIHRAB_SITE_OUT=_o2))
        assert _r2.returncode != 0, (
            "بنى فوق مجلّدٍ غيرِ فارغٍ بلا شاهد — `MIHRAB_SITE_OUT` قد يشير إلى "
            "أيّ مكان، والمحوُ بلا شاهدٍ محوُ ما لا نعرفه [OUT-01]")
        assert os.path.isfile(_keep), "مُحي ملفٌّ ليس من مخرَجٍ سابق [OUT-01]"
        assert not os.path.exists(os.path.join(_o2, "index.html")), (
            "رفض بصوتٍ ثمّ بنى فوقه — الرفضُ يجب أن يسبق أيَّ كتابة [OUT-01]")

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
            assert _mkl.returncode == 0 and os.path.isdir(_lnk), (
                "تعذّر إنشاءُ وصلةٍ (لا symlink ولا junction) — الضلعُ الثالثُ من "
                "[OUT-01] لا يُقاس هنا، ولا يُتخطّى صامتًا")
        _r3 = subprocess.run([sys.executable, _bpy], cwd=SITE, capture_output=True,
                             timeout=120, env=dict(_env0, MIHRAB_SITE_OUT=_o3))
        assert os.path.isfile(_precious), (
            "**مُحي ملفٌّ وراء وصلةٍ في المخرَج** — المحوُ تبع الوصلةَ إلى مجلّدٍ "
            "ليس من البناء [OUT-01]")
        assert _r3.returncode == 0, (
            "البناءُ في مخرَجٍ سابقٍ فيه وصلةٌ فشل [OUT-01]:\n"
            + _r3.stderr.decode("utf-8", "replace")[-800:])
        assert not os.path.lexists(_lnk), (
            "الوصلةُ باقيةٌ في المخرَج بعد البناء — ستُحزَم وجهتُها وتُنشَر [OUT-01]")
        assert os.path.isfile(os.path.join(_o3, _mark)), (
            "الشاهدُ لا يُعاد كتابتُه بعد فكّ الوصلة [OUT-01]")

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
                assert _holder.stdout.read(2) == b"ok", "لم يُفتح المقبضُ الحابس [OUT-01]"
            else:
                os.makedirs(_stuck)
                with open(os.path.join(_stuck, "f"), "w") as _sf4:
                    _sf4.write("x")
                os.chmod(_stuck, 0o500)
            try:
                _r4 = subprocess.run([sys.executable, _bpy], cwd=SITE,
                                     capture_output=True, timeout=120,
                                     env=dict(_env0, MIHRAB_SITE_OUT=_o4))
            finally:
                if _holder is not None:
                    _holder.kill()
                    _holder.wait()
                else:
                    os.chmod(_stuck, 0o700)
            assert _r4.returncode != 0, (
                "مدخلٌ لا يُمحى مرّ صامتًا — البناءُ أخضرُ فوق مخرَجٍ لم يُمحَ كلُّه، "
                "والبائتُ يُحزَم [OUT-01]")
            assert os.path.isfile(os.path.join(_o4, _mark)), (
                "فشلٌ في منتصف المحو ترك المخرَجَ **بلا شاهد** — الشاهدُ يُمحى أوّلًا "
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

    report()
    return 1 if fails else 0


def report():
    if fails:
        print("❌ %d عطبٌ بنيويّ:" % len(fails))
        for f in fails:
            print("   · %s" % f)
    else:
        print("✅ الموقعُ سليمٌ بنيويًّا: الصفحات، والمراسي، والمانيفست، وروابطُ الهويّة.")


if __name__ == "__main__":
    sys.exit(main())
