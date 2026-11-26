# -*- coding: utf-8 -*-
"""بنيةُ المخرَج وبناؤه: الحتميّة، وحدودُ المولِّد، والصفحاتُ الإلزاميّة، والمطابقةُ لبناءٍ نظيف [OUT-0x]، والتجريد [MIN-0x]، والمراسي، والمساراتُ والأصول.

أقسامُ `main()` القديمة بنصّها، بترتيبها في `check_site.py` (‏`SECTIONS`)."""
from .core import *  # noqa: F401,F403

def s01_det01_determinism(c):
    # ── [DET-01] البناءُ لا يقرأ اللحظةَ ولا الجهازَ ولا ترتيبَ القرص ──
    # القواعدُ وعلّتُها في `det_check.py`، وجدولُ حالاتها في `test_det_check.py`. والمسحُ على
    # كلّ `site/**/*.py` (عدا المخرَج): وحدةٌ فرعيّةٌ يستوردها البناءُ يومًا تُفحَص معه.
    sys.path.insert(0, DOCS_DIR)
    from det_check import violations as _det
    _det_files = sorted(p for p in glob.glob(os.path.join(SITE, "**", "*.py"), recursive=True)
                        if not os.path.abspath(p).startswith(os.path.abspath(OUT) + os.sep))
    need(_det_files, lambda: "[DET-01] لا ملفَّ بايثون في site/ — المسحُ لا يرى البناء")
    # وجذرُ `site/` لا يحمل بايثون سوى نقطة الدخول — العلّةُ وجدولُ الحالات مع `root_strays`.
    from det_check import root_strays as _strays
    _root_ls = os.listdir(SITE)
    _root_py = _strays(_root_ls, [d for d in _root_ls if os.path.isfile(os.path.join(SITE, d, "__init__.py"))])
    check(not _root_py, lambda: "[DET-01] بايثون في جذر site/ سوى build.py: %s — يظلّل ما يستورده "
          "البناء؛ مكانُه site/sitegen/" % "، ".join(_root_py))
    _l = locals()
    for _n in ('_det', '_det_files'):
        if _n in _l:
            setattr(c, _n, _l[_n])


def s02_gen01_sitegen_bounds(c):
    _c = vars(c)
    if "_det" in _c:
        _det = _c['_det']
    if "_det_files" in _c:
        _det_files = _c['_det_files']
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
    from det_check import pycache_dirs as _pycache  # العلّةُ وجدولُ الحالات معها
    _pyc = _pycache(os.walk(SITE), SITE, OUT)
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
    _l = locals()
    for _n in ('data',):
        if _n in _l:
            setattr(c, _n, _l[_n])


def s03_required_files(c):
    # ── الصفحاتُ الإلزاميّة ──
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


def s04_out02_clean_build(c):
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
    _l = locals()
    for _n in ('dl', 'home', 'kbd'):
        if _n in _l:
            setattr(c, _n, _l[_n])


def s05_site_js_anchors(c):
    _c = vars(c)
    if "dl" in _c:
        dl = _c['dl']
    if "home" in _c:
        home = _c['home']
    # ── مراسي site.js ──
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


def s08_out03_nothing_foreign(c):
    _c = vars(c)
    if "data" in _c:
        data = _c['data']
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


def s09_min01_strip_equivalence(c):
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


def s10_min02_gzip_cap(c):
    _c = vars(c)
    if "kbd" in _c:
        kbd = _c['kbd']
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


def s11_data_island(c):
    _c = vars(c)
    if "dl" in _c:
        dl = _c['dl']
    if "home" in _c:
        home = _c['home']
    # ── جزيرةُ البيانات تُحلَّل فعلًا ──
    for name, page in (("index.html", home), ("download/index.html", dl)):
        for isle in ("site-platforms", "baked-releases"):
            m = re.search(r'id="%s">(.*?)</script>' % isle, page, re.S)
            if not m:
                continue
            try:
                json.loads(m.group(1).replace("<\\/", "</"))
            except ValueError as e:
                bad("جزيرةُ بياناتٍ غيرُ صالحة (%s في %s): %s" % (isle, name, e))


def s12_no_absolute_paths(c):
    # ── لا مساراتٍ مطلقةً إلى مضيفٍ بعينه ──
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


def s13_local_assets_exist(c):
    # ── كلُّ أصلٍ محلّيٍّ مُشار إليه موجودٌ في المخرَج ──
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
    _l = locals()
    for _n in ('DL_BASE', 'DL_FILES'):
        if _n in _l:
            setattr(c, _n, _l[_n])


def s42_out01_fresh_output(c):
    # ── المخرَجُ يبدأ فارغًا، ولا يُمحى ما ليس مخرَجًا [OUT-01] ──
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
