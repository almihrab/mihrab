# -*- coding: utf-8 -*-
"""أوراقُ الأنماط [CSS-01] وأوجهُ الخطّ [FNT-01].

أقسامُ `main()` القديمة بنصّها، بترتيبها في `check_site.py` (‏`SECTIONS`)."""
from .core import *  # noqa: F401,F403

def s14_css01_stylesheets(c):
    # ── أوراقُ الأنماط: لا تعليقَ مبتورًا ولا نصًّا طليقًا في `:root` [CSS-01] ──
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


def s15_fnt01_faces(c):
    # ── أوجهُ الخطّ مورَّدةٌ وكاملةٌ ومتوازنة [FNT-01] ──
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
    _l = locals()
    for _n in ('_hashlib', '_struct'):
        if _n in _l:
            setattr(c, _n, _l[_n])


def s16_fnt01_inventory(c):
    # ── [FNT-01] جردٌ **مستقلّ** لا مرآةٌ للمولِّد ──
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
    _l = locals()
    for _n in ('EXPECT_FACES', 'MONO_AR_FAMILY', 'declared', 'fcss'):
        if _n in _l:
            setattr(c, _n, _l[_n])


def s17_fnt01_font_faces_promise(c):
    _c = vars(c)
    if "EXPECT_FACES" in _c:
        EXPECT_FACES = _c['EXPECT_FACES']
    if "_struct" in _c:
        _struct = _c['_struct']
    if "declared" in _c:
        declared = _c['declared']
    # ── [FNT-01] والمرجعُ `FONT_FACES` في المولِّد، لا مجلّدُ المصدر ──
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


def s18_fnt01_hash_family_weight(c):
    _c = vars(c)
    if "EXPECT_FACES" in _c:
        EXPECT_FACES = _c['EXPECT_FACES']
    if "_hashlib" in _c:
        _hashlib = _c['_hashlib']
    if "fcss" in _c:
        fcss = _c['fcss']
    # ── [FNT-01] والبصمةُ والعائلةُ والوزن، لا الوجودُ وحدَه ──
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


def s19_fnt01_pages_load_sheet(c):
    # ── [FNT-01] وكلُّ صفحةٍ في المخرَج **تحمل** الورقةَ ──
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


def s20_fnt01_glyph_coverage(c):
    # ── [FNT-01] وكلُّ محرفٍ **يراه الزائر** داخلَ المدَيَين، أو مسمًّى في قائمةٍ بيضاء ──
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
    _l = locals()
    for _n in ('ar_r', 'la_r'):
        if _n in _l:
            setattr(c, _n, _l[_n])


def s21_fnt01_license(c):
    _c = vars(c)
    if "declared" in _c:
        declared = _c['declared']
    if "fcss" in _c:
        fcss = _c['fcss']
    # ── [FNT-01] ورخصةُ الخطّ تصل الزائرَ معه ──
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
    _l = locals()
    for _n in ('faces',):
        if _n in _l:
            setattr(c, _n, _l[_n])


def s22_fnt01_mono_alias(c):
    _c = vars(c)
    if "MONO_AR_FAMILY" in _c:
        MONO_AR_FAMILY = _c['MONO_AR_FAMILY']
    if "ar_r" in _c:
        ar_r = _c['ar_r']
    if "faces" in _c:
        faces = _c['faces']
    if "la_r" in _c:
        la_r = _c['la_r']
    # ── [FNT-01] والاسمُ الثاني لأحاديّ المسافة لا يلتقط ما يُحاذى ──
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
