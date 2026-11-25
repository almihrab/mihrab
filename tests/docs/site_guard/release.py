# -*- coding: utf-8 -*-
"""صفحةُ 404 من كلّ أصل [W404]، والمانيفست [MAN-01]، وروابطُ الهويّة، ومعاينةُ ألف.

أقسامُ `main()` القديمة بنصّها، بترتيبها في `check_site.py` (‏`SECTIONS`)."""
from .core import *  # noqa: F401,F403

def s39_w404_every_origin(c):
    _c = vars(c)
    if "DL_BASE" in _c:
        DL_BASE = _c['DL_BASE']
    if "DL_FILES" in _c:
        DL_FILES = _c['DL_FILES']
    # ── صفحةُ ‎404‎: أصولُها تصل من **كلّ** أصلٍ تُقدَّم منه [W404] ──
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


def s40_manifest_platforms(c):
    _c = vars(c)
    if "data" in _c:
        data = _c['data']
    # ── كلُّ منصّةٍ في المانيفست معروفةٌ في site.json ──
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


def s41_identity_links(c):
    _c = vars(c)
    if "data" in _c:
        data = _c['data']
    # ── روابطُ الهويّة تطابق ما يُبنى فعلًا ──
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


def s43_alif_pin(c):
    # ── تثبيتُ إضافةِ ألف: الجالبُ وصفحةُ المعاينة يقولان الشيءَ نفسَه ──
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


def s44_man01_manifest(c):
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
