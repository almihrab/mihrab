# -*- coding: utf-8 -*-
"""الصفحاتُ المولَّدة بلا ملفّ محتوى: الأولى، والتنزيل، والاختصارات، و404."""
import html
import json
import os
import struct
import urllib.parse

from .data import ASSETS, DATA, RELEASES, SITE
from .templates import MARK_SVG, data_island, page_shell
from .text import inline


# ═════════════════════════════════════════════════════════════════════════
#  واجهةُ المنتج — الصفحةُ الأولى وصفحةُ التنزيل
# ═════════════════════════════════════════════════════════════════════════

def hero_visual():
    """برهانٌ بصريّ: لقطةٌ حقيقيّة إن وُرِّدت، ورسمٌ مبسّطٌ إن لم تُورَّد.

    ولا `<img>` لملفٍّ غائب — السببُ نفسُه الذي منع `@font-face` لخطٍّ غائب:
    الوسمُ لا يفشل بصوت، بل يترك مستطيلًا مكسورًا في أهمّ موضعٍ في الصفحة.
    الرسمُ البديل **مبسّطٌ صراحةً** ومكتوبٌ تحته أنّه كذلك: صورةٌ تدّعي أنّها لقطةُ
    شاشة وليست كذلك كذبٌ بصريّ، وهو أسوأُ من رسمٍ يعلن عن نفسه.
    """
    shot = os.path.join(ASSETS, "shots", "editor.png")
    if os.path.isfile(shot):
        # الأبعادُ تُقرأ من ترويسة PNG لا تُكتب يدويًّا: قيمةٌ خاطئة تُنتج قفزةَ
        # تخطيط (CLS) عند تحميل الصورة — وهي أوّلُ ما يراه الزائر.
        with open(shot, "rb") as f:
            w, h = struct.unpack(">II", f.read(24)[16:24])
        inner = ('<img src="../assets/shots/editor.png" width="%d" height="%d" '
                 'alt="محراب مفتوحٌ على ملفٍّ عربيّ: شريطُ النشاط والمستكشف يمينًا، '
                 'والكودُ العربيّ في المحرّر." fetchpriority="high">' % (w, h))
        note = ""
    else:
        inner = _mock_svg()
        note = ('<div class="shot-note">رسمٌ تخطيطيّ للتخطيط — لا لقطةَ شاشة. '
                'حمّل محرابًا لترى الأصل.</div>')
    return ('<div class="shot"><div class="shot-bar"><i></i><i></i><i></i>'
            '<span class="t">محراب — مرحبا.md</span></div>%s%s</div>' % (inner, note))


def _mock_svg():
    """تخطيطُ محراب في SVG: شريطُ النشاط **يمينًا** — وهي الدعوى كلُّها في صورة."""
    g = []
    # شريطُ النشاط (يمينًا) — خمسُ أيقوناتٍ مجرّدة
    g.append('<rect x="1352" y="0" width="48" height="900" fill="#12212B"/>')
    for k in range(5):
        c = "#E3BE68" if k == 0 else "#3A4C55"
        g.append('<rect x="1366" y="%d" width="20" height="20" rx="4" fill="%s"/>'
                 % (26 + k * 46, c))
    # المستكشف
    g.append('<rect x="1132" y="0" width="220" height="900" fill="#12212B"/>')
    g.append('<rect x="1152" y="24" width="86" height="9" rx="4" fill="#5C7078"/>')
    for k, w in enumerate([120, 96, 140, 108, 84, 130]):
        fill = "#31A796" if k == 2 else "#3A4C55"
        g.append('<rect x="%d" y="%d" width="%d" height="9" rx="4" fill="%s"/>'
                 % (1332 - w, 56 + k * 26, w, fill))
    # ألسنةُ التبويب
    g.append('<rect x="0" y="0" width="1132" height="36" fill="#12212B"/>')
    g.append('<rect x="1004" y="0" width="128" height="36" fill="#0F1C24"/>')
    g.append('<rect x="1024" y="14" width="70" height="9" rx="4" fill="#D4DEDF"/>')
    g.append('<rect x="884" y="14" width="58" height="9" rx="4" fill="#5C7078"/>')
    # المحرّر — أسطرٌ من اليسار (الكودُ جزيرةُ LTR) وتعليقٌ عربيٌّ من اليمين
    rows = [(0, 210), (1, 300), (1, 250), (0, 0), (0, 340), (1, 190),
            (1, 270), (0, 0), (0, 230), (1, 320), (1, 160)]
    y = 74
    for indent, w in rows:
        if w:
            g.append('<rect x="%d" y="%d" width="%d" height="10" rx="5" fill="%s"/>'
                     % (64 + indent * 34, y, w, "#31A796" if indent else "#7E939B"))
        y += 30
    # تعليقٌ عربيّ محاذًى لليمين داخل المحرّر — العزلُ الاتّجاهيّ مرئيًّا
    g.append('<rect x="880" y="164" width="190" height="10" rx="5" fill="#5C7078"/>')
    g.append('<rect x="946" y="374" width="124" height="10" rx="5" fill="#5C7078"/>')
    # الطرفيّة
    g.append('<rect x="0" y="640" width="1132" height="260" fill="#12212B"/>')
    g.append('<rect x="0" y="640" width="1132" height="2" fill="#263A42"/>')
    g.append('<rect x="1004" y="662" width="106" height="9" rx="4" fill="#E3BE68"/>')
    for k, w in enumerate([300, 180, 420, 240]):
        g.append('<rect x="64" y="%d" width="%d" height="9" rx="4" fill="#5C7078"/>'
                 % (700 + k * 30, w))
    # شريطُ الحالة
    g.append('<rect x="0" y="876" width="1400" height="24" fill="#182A34"/>')
    g.append('<rect x="1280" y="884" width="104" height="8" rx="4" fill="#31A796"/>')
    return ('<svg class="mock" viewBox="0 0 1400 900" role="img" '
            'aria-label="تخطيطُ محراب: شريطُ النشاط والمستكشف على اليمين، '
            'والمحرّرُ والطرفيّة على اليسار.">'
            '<rect width="1400" height="900" fill="#0F1C24"/>%s</svg>' % "".join(g))


def build_not_found():
    """صفحةُ ‎404‎ — بقِشرة الموقع لا بصفحة nginx العارية.

    ## العطب، مقيسًا

    كلُّ مسارٍ مجهولٍ على `mihrab.dev` كان يردّ:

        <html><head><title>404 Not Found</title>…<center>nginx</center>

    إنجليزيٌّ، يساريٌّ، يقول «‏nginx» — على منتَجٍ **كلُّ دعواه الاتّجاهُ
    والعربيّة**، وفي اللحظة التي تُختبَر فيها العناية. والتحذيرُ من هذا كان
    مكتوبًا بأيدينا في `mihrab.dev.static.conf` منذ أسابيع؛ كُتب الحذرُ ولم
    تُكتَب الصفحة.

    ## ومن يهبط هنا ليس تائهًا بالصدفة

    الأغلبُ صاحبُ **إشارةٍ مرجعيّةٍ من قبل الانتقال**: كان `mihrab.dev` هو
    المحرِّرَ نفسَه، فكلُّ من حفظ `/workbench.html` أو `/out/…` أو `/manifest.json`
    يصل اليومَ إلى لا شيء. ولذلك تُقدَّم الوجهاتُ الثلاثُ صراحةً — ويُقال له أين
    ذهب المحرِّر — بدل «الصفحة غير موجودة» وحدَها.

    وهنا موضعُ ذِكر `docs.mihrab.dev` و`dl.mihrab.dev`: مَن يحتاج أن يسمع أنّهما
    «يبقيان يعملان» هو حاملُ الرابط القديم، وهذا مكانُه لا أعلى صفحةِ التوثيق.
    """
    app = SITE["browser"]["url"]
    _ORIGIN = html.escape(SITE["canonical"].rstrip("/"))
    app_host = app.replace("https://", "").rstrip("/")
    # ── والصفحةُ تعرف أين تقف ──
    # تُقدَّم من الأصلين، ونصُّها يخاطب زائرَ `mihrab.dev`. فمن ضلّ على
    # `app.mihrab.dev` نفسِه كان يقرأ أنّ المحرِّرَ «استقلّ بأصلٍ خاصّ» — وهو
    # واقفٌ عليه. فقرتان: الثانيةُ مخفيّةٌ يُظهرها `docs.js` حين يطابق المضيفُ
    # `data-app-host`. وبلا سكربت تبقى الأولى، وهي صحيحةٌ من الأصل الأوّل.
    body = (
        '<main class="page notfound" data-app-host="%s">' % html.escape(app_host)
        + '<section class="hero">' + (MARK_SVG % "mark-lg")
        + '<h1>لا شيءَ هنا</h1>'
        + '<p class="tagline">الصفحةُ التي طلبتَها ليست في هذا الموضع.</p>'
        + '<p class="lede lede-site">وإن كنتَ تبحث عن <b>محرابِ المتصفّح</b> فقد استقلَّ '
          'بأصلٍ خاصٍّ به — ‏<code>%s</code> — وهذا الموقعُ صار للتوثيق والتنزيل.</p>'
          % html.escape(app_host)
        + '<p class="lede lede-app" hidden>أنتَ على <b>محرابِ المتصفّح</b> نفسِه — '
          '‏<code>%s</code> — لكنّ هذا المسارَ لا يقود إلى شيءٍ فيه. افتح المحرِّرَ '
          'من بابه، أو عُد إلى موقع محراب للتوثيق والتنزيل.</p>'
          % html.escape(app_host)
        + '<div class="cta-row">'
          '<a class="btn btn-primary" href="%s" rel="noopener">افتح محرابَ المتصفّح</a>'
          '<a class="btn btn-soft" href="%s/download/">نزِّل محراب</a>'
          '<a class="btn btn-ghost" href="%s/docs/">تصفّح التوثيق</a>'
          '</div>' % (html.escape(app), _ORIGIN, _ORIGIN)
        + '</section>'
        + '<section class="section">'
          '<h2>روابطُ قديمةٌ ما زالت تعمل</h2>'
          '<p class="sub">إن كنتَ تحمل عنوانًا محفوظًا من قبل الانتقال: '
          '<code>docs.mihrab.dev</code> و<code>dl.mihrab.dev</code> يحوّلان إلى '
          'مواضعهما الجديدة هنا، والمسارُ محفوظٌ كما هو.</p>'
          '</section>'
        + '</main>')
    # ── ولماذا الأصلُ كاملًا لا شرطةٌ من الجذر ──
    # مسارٌ نسبيٌّ ممتنع: `error_page` داخليّةٌ لا تحويل، فالصفحةُ تُقدَّم من **أيّ**
    # عمقٍ طلبَه الزائر وينكسر النسبيُّ على `/a/b/c`.
    #
    # والمطلقُ **من الجذر** (`/assets/…`) كان الخطأ: هذه الصفحةُ تُقدَّم من أصلين
    # — `mihrab.dev` و`app.mihrab.dev` بـ`alias` — وجذرُ الثاني حمولةُ الورشة، لا
    # `assets/` فيها ولا `docs/`. قِيس حيًّا: `app.mihrab.dev/assets/mihrab-home.css`
    # ⇐ ‎404‎. فكانت تصل **بلا ورقةِ أنماطٍ ولا خطوط**، وكلُّ رابطٍ فيها يردّ ‎404‎
    # ثانيةً: حلقةٌ مغلقة، على الصفحة الوحيدة التي وظيفتُها إنقاذُ التائه.
    #
    # فالأصلُ يُكتَب كاملًا. وهي الصفحةُ الوحيدةُ التي يصحّ فيها ذلك: غيرُ قابلةٍ
    # للمرآة أصلًا (عنوانُها المعياريُّ مكتوبٌ صراحةً)، ووظيفتُها أن تدلّ على الدار
    # من خارجها. ويحرس ذلك [W404] في `check_site.py`: كلُّ أصلٍ فيها على أصل
    # الموقع، وكلُّ مضيفٍ تسمح به سياسةُ كلّ `location = /404.html` حيّة.
    # ── والأيقونةُ مضمَّنةٌ لا مطلقة ──
    # الورقةُ والسكربتُ يصلان من `mihrab.dev` لأنّ سياسةَ الورشة تسمح بهما
    # (‏`style-src`/`script-src … https://mihrab.dev`)، أمّا `img-src 'self' data:`
    # فلا — قِيس حيًّا (الجولة ‎15‎) على `app.mihrab.dev/<مفقود>`: «Loading the image
    # https://mihrab.dev/assets/icon.svg violates … img-src» مرّتين، والتبويبُ
    # بلا أيقونة. و`data:` مسموحٌ في السياستين معًا، والأيقونةُ ‎235‎ بايتًا.
    with open(os.path.join(ASSETS, "icon.svg"), encoding="utf-8") as _f:
        _icon = "data:image/svg+xml," + urllib.parse.quote(_f.read().strip())
    return page_shell(
        # ‏بلا « — محراب»: `page_shell` يلحقها، وكانت الترويسةُ تقرأ
        # «لا شيءَ هنا — محراب — محراب».
        "لا شيءَ هنا", body, SITE["canonical"].rstrip("/"),
        "الصفحةُ غير موجودة. محرابُ المتصفّح انتقل إلى أصلٍ خاصٍّ به.",
        canon_path="404.html", with_search=False, icon=_icon)


def build_landing():
    hero = SITE["hero"]
    trust = "".join("<span>%s</span>" % html.escape(t) for t in hero["trust"])

    # ── بطاقةُ «جرّبه الآن» ──
    # تسبق «نزِّل وثبِّت» لأنّها أقصرُ طريقٍ إلى تجربةٍ حقيقيّة. والقيودُ **معها لا
    # بعدها**: القيدُ الذي تُعلنه ميزةُ ثقة، والذي يكتشفه المستخدمُ بنفسه عطبٌ في نظره.
    br = SITE.get("browser")
    browser_card = ""
    if br:
        lims = "".join("<li>%s</li>" % inline(x) for x in br.get("limits", []))
        browser_card = (
            '<section class="section browser-try">'
            '<h2>%s</h2>' % html.escape(br["title"])
            + '<p class="sub">%s</p>' % inline(br["body"])
            + '<p class="cta-row"><a class="btn btn-primary" href="%s">%s</a></p>'
              % (html.escape(br["url"]), html.escape(br["url"].replace("https://", "")))
            + ('<ul class="limits">%s</ul>' % lims if lims else "")
            + '</section>')

    feats = "".join(
        '<div class="feature"><h3>%s</h3><p>%s</p></div>'
        % (html.escape(f["title"]), inline(f["body"]))
        for f in SITE["features"])

    steps = []
    for s in SITE["steps"]:
        # ‏`./` لا `../`: هذه الصفحةُ على الجذر. والمتصفّحُ يُثبّت `..` عند الجذر
        # فيعمل الرابطُ على `mihrab.dev/` بالمصادفة — ويكسر على مرآةٍ تحت بادئة
        # (كـ`almihrab.github.io/mihrab/` لو فُعِّلت) حيث يقفز `..` فوق اسمِ المستودع.
        more = ('<a href="./%s/">اقرأ أكثر ←</a>' % s["href"]) if s.get("href") else ""
        steps.append('<div class="step"><div class="n">%s</div><h3>%s</h3><p>%s</p>%s</div>'
                     % (html.escape(s["n"]), html.escape(s["title"]),
                        inline(s["body"]), more))

    body = (
        '<main class="page">'
        '<section class="hero">' + (MARK_SVG % "mark-lg")
        + '<h1>محراب</h1>'
        + '<p class="tagline">%s</p>' % html.escape(hero["tagline"])
        + '<p class="lede">%s</p>' % html.escape(hero["lede"])
        # النصُّ الابتدائيّ للزرّ محافظ: يعمل بلا جافاسكربت، وsite.js يستبدله
        # بالبناء المطابق لنظام الزائر حين يعرفه. زرٌّ يقول «نزِّل لويندوز» قبل
        # أن نعرف النظامَ يكذب على نصف الزوّار.
        # ثلاثةُ أزرارٍ لا اثنان: كان «نزِّل» وحدَه هو الطريقَ المعروض، وهو
        # **أثقلُ** طريقٍ إلى التجربة (‏٢٠٣ م.ب) بينما أخفُّها (‏٥ م.ب في
        # المتصفّح) مدفونٌ تحت الطيّة. والتعليلُ مكتوبٌ في `site.json` منذ
        # البداية — «تسبق نزِّل وثبِّت لأنّها أقصرُ طريقٍ إلى تجربةٍ حقيقيّة» —
        # لكنّ **البطاقةَ** كانت تسبق و**الزرُّ** لا يسبق.
        #
        # وعلى الجوّال ينقلب الترتيبُ في CSS لا هنا: الترميزُ يبقى واحدًا
        # (‏`order` في الشبكة)، فلا نسختان من الصفحة تتباعدان.
        + '<div class="cta-row">'
          '<a class="btn btn-primary" data-dl-primary href="./download/">نزِّل محراب</a>'
          '<a class="btn btn-soft" href="%s" rel="noopener">جرّبه في المتصفّح</a>'
          '<a class="btn btn-ghost" href="./docs/">تصفّح التوثيق</a>'
          '</div>' % html.escape(SITE["browser"]["url"])
        + '<p class="cta-meta" data-dl-meta></p>'
        + '<div class="trust">%s</div>' % trust
        # (كان هنا شريطُ «محرابٌ استقلّ بنطاقه» — أُزيل بقرار المالك ‎2026-09-22‎؛
        #  رسالةُ الانتقال بقيت في صفحة ‎404‎ لمن يحمل رابطًا قديمًا.)
        + '</section>'
        + hero_visual().replace('src="../assets/', 'src="./assets/')
        + browser_card
        + '<section class="section"><h2>لماذا محراب</h2>'
          '<p class="sub">كلُّ دعوى هنا قابلةٌ للفحص في أوّل دقيقة استعمال.</p>'
          '<div class="feature-grid">%s</div></section>' % feats
        + '<section class="section"><h2>ثلاثُ خطوات</h2>'
          '<p class="sub">من التنزيل إلى أوّل سطرٍ يعمل.</p>'
          '<div class="steps">%s</div></section>' % "".join(steps)
        + '<section class="closer"><h2>ابدأ الآن</h2>'
          # ⚠️ **دعوى «بلا تتبّع» مجرّدةً أوسعُ ممّا نستطيع البرهنةَ عليه.** خادمُ
          # الموقع يكتب سجلَّ طلباتٍ عاديًّا فيه عنوانُ من طلب — وهو ليس تتبّعًا
          # (لا معرّفَ يُوضَع في جهازك، ولا طرفَ ثالثَ يُسلَّم إليه شيء) لكنّه ليس
          # «لا شيء» أيضًا. فتُضيَّق الدعوى إلى ما يُفحَص في هذه الصفحة بعينها:
          # لا كعكة، ولا سكربتَ تتبّع. والسجلُّ يُفصَّل في قسم الخصوصيّة.
          '<p>مجّانيٌّ ومفتوحُ المصدر. بلا حساب، وبلا كعكةٍ ولا سكربتِ تتبّعٍ في هذه الصفحة.</p>'
          '<div class="cta-row"><a class="btn btn-primary" href="./download/">نزِّل محراب</a>'
          '<a class="btn btn-ghost" href="%s">شفرةُ المصدر</a></div></section>' % SITE["repo"]
        + '</main>'
        + data_island("site-platforms", SITE["platforms"])
        + data_island("baked-releases", RELEASES)
    )
    return page_shell(
        "محراب — محرّرُ أكوادٍ عربيُّ الواجهة والاتّجاه", body, ".",
        SITE["hero"]["lede"], active="home", canon_path="",
        with_search=False, extra_js=("site.js",))




def _verify_snippet():
    """مقتطفُ التحقّق بأسماء الملفّات **المنشورة**، لا باسمٍ مُتخيَّل.

    كان مكتوبًا بيدٍ: `Mihrab-Setup.exe` و`mihrab.tar.gz` — وكلاهما اسمٌ لا يستطيع
    القارئُ الحصولَ عليه بأيّ طريق، فمقتطفُ التحقّق نفسُه — وهو موضعُ الثقة — يفشل
    عند أوّل لصقة. ويُشتقّان هنا من المانيفست فلا ينحرفان مع أوّل تغييرٍ في التسمية.
    """
    win = next((a["file"] for a in RELEASES.get("assets", [])
                if a.get("id", "").startswith("win-")), None)
    nix = next((a["file"] for a in RELEASES.get("assets", [])
                if a.get("id", "").startswith(("linux-", "mac-"))), None)
    lines = []
    if win:
        lines += ["# ويندوز (PowerShell)", "Get-FileHash -Algorithm SHA256 .\\" + win, ""]
    if nix:
        lines += ["# لينكس / macOS", "sha256sum " + nix]
    if not lines:
        # لا إصدارَ منشورًا بعد: الأمرُ يُعرَض بقالبٍ صريحٍ لا باسمٍ مُختلَق.
        lines = ["# ويندوز (PowerShell)", "Get-FileHash -Algorithm SHA256 .\\<اسم الملفّ>",
                 "", "# لينكس / macOS", "sha256sum <اسم الملفّ>"]
    return html.escape("\n".join(lines))


# أعدادٌ صغيرةٌ بالحروف: «ثلاثٌ من ثمانٍ» تُقرأ جملةً، و«3 من 8» تُقرأ بيانًا
# في جدول — والفرقُ يهمّ في سطرٍ غرضُه الطمأنة.
_AR_NUM = {1: "واحدةٌ", 2: "اثنتان", 3: "ثلاثٌ", 4: "أربعٌ", 5: "خمسٌ",
           6: "ستٌّ", 7: "سبعٌ", 8: "ثمانٍ"}
# والصيغةُ **مضافةً** غيرُها منوَّنةً: «ثمانٍ» تصحّ وحدَها، فإذا تلاها معدودُها
# صارت «ثماني منصّاتٍ» — و«من ثمانٍ منصّاتٍ» لحنٌ ظاهر. والبقيّةُ تُجرَّد من
# التنوين لا غير. وموقعٌ دعواه العربيّةُ لا يُغتفَر له لحنٌ في سطرِ طمأنة.
_AR_NUM_ADDED = {3: "ثلاثِ", 4: "أربعِ", 5: "خمسِ",
                 6: "ستِّ", 7: "سبعِ", 8: "ثماني"}

_AR_MONTHS = ("يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
              "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر")


def _fmt_date(iso):
    """‏`2026-08-30` ⇐ «30 أغسطس 2026».

    و**مخبوزٌ لا محسوبٌ في المتصفّح**: `site.js` يعيد كتابتَه من المانيفست الحيّ،
    لكنّ من عطّل السكربتات — أو من لم يصله `site.js` بعدُ على اتّصالٍ متواضع —
    كان يقرأ تاريخًا بصيغة ISO بأرقامٍ لاتينيّةٍ يساريّةِ الاتّجاه في جملةٍ
    عربيّة، وهو بعينه ما أُريد إزالتُه. وجدولُ التنزيل كلُّه خُبِز لهذا السبب؛
    التاريخُ وحدَه كان قد بقي خارج القاعدة. ومن لم يعطّلها كان يرى **وميضَ
    تغيّر** بين المخبوز والمحسوب.

    والارتدادُ إلى النصّ كما هو مقصود: تاريخٌ بصيغةٍ غيرِ متوقّعةٍ يُعرَض خامًا
    ولا يختفي — إخفاءُ المعلومة أسوأُ من عرضِها بصيغةٍ ركيكة.
    """
    try:
        y, m, d = (int(x) for x in str(iso).split("-"))
        # ‏`_AR_MONTHS[m - 1]` مع `m = 0` يلتفّ إلى **ديسمبر** بلا خطأ: تاريخٌ
        # خاطئٌ صامتٌ بدل ارتدادٍ صادق. والشرطُ يجعله يرتدّ كما يرتدّ أيُّ مشوَّه.
        if not 1 <= m <= 12:
            raise ValueError(iso)
        return "%d %s %d" % (d, _AR_MONTHS[m - 1], y)
    except (ValueError, IndexError, TypeError):
        return str(iso)


def _fmt_size(n):
    """صياغةُ الحجم بالعربيّة — نفسُ قاعدة `fmtSize` في site.js حرفًا بحرف."""
    if not n or n < 0:
        return ""
    # عشريّةٌ لا ثنائيّة — كما `fmtSize` في site.js: القسمُ على ‎1048576‎ كان يُظهِر
    # أرشيفَ ويندوز (‏203,053,894 بايت) ‎194‎ في الجدول المخبوز و‎203‎ بعد الجلب الحيّ.
    mb = n / 1e6
    return ("%.2f غيغابايت" % (mb / 1000)) if mb >= 1000 else ("%d ميغابايت" % round(mb))


def _baked_dl_rows():
    """صفوفُ جدول التنزيل **مولَّدةً في HTML** من المانيفست المخبوز.

    كانت الصفحةُ تُسلّم الجدولَ كلَّه لجافاسكربت: `data-dl-wrap` مخفيٌّ و`data-dl-empty`
    ظاهرٌ في الأصل. فمن عطّل السكربتات — أو حجبها امتداد، أو انقطع الملفُّ على اتّصالٍ
    متواضع — يقرأ «لا إصدارَ منشورًا بعد» وتحته مباشرةً مقتطفُ تحقّقٍ يسمّي ملفّاتٍ
    بأسمائها الكاملة وأرقامِ إصدارها. صفحةٌ تنفي وتُثبت في شاشةٍ واحدة، والزائرُ
    يستنتج العطب لا الحقيقة. والمبدأُ المكتوبُ في رأس site.js نفسِه — «الصفحةُ كاملةٌ
    قبل أن يعمل هذا الملفّ» — كان منقوضًا هنا وحدَه.

    يرجع (صفوفٌ، أفيه إصدارٌ). وsite.js يمسح `tbody` قبل رسمه فلا ازدواج.
    """
    assets = RELEASES.get("assets") or []
    if not (RELEASES.get("version") and assets):
        return "", False

    by_id = {p["id"]: p for p in SITE["platforms"]}
    ordered = [a for p in SITE["platforms"] for a in assets if a["id"] == p["id"]]
    ordered += [a for a in assets if a not in ordered]

    rows = []
    for a in ordered:
        p = by_id.get(a["id"], {"label": a["id"], "kind": "", "ext": ""})
        kind = p["kind"] + (" · " + p["ext"] if p.get("ext") else "")
        sha = ('<br><span class="sha">SHA-256: %s</span>' % html.escape(a["sha256"])
               if a.get("sha256") else "")
        # الرابطُ نسبيٌّ عمدًا (‏`../dl/…`): مسارٌ مطلقٌ يربط المخرَجَ بمضيفٍ بعينه
        # ويكسر المرآة — والقاعدةُ نفسُها التي تحكم كلَّ روابط الموقع.
        rows.append(
            '<tr><td class="file"><b>%s</b><span class="kind">%s</span>%s</td>'
            '<td class="size">%s</td>'
            '<td class="get"><a class="btn-sm" href="../%s%s" download>نزِّل</a></td></tr>'
            % (html.escape(p["label"]), html.escape(kind), sha,
               html.escape(_fmt_size(a.get("size"))),
               html.escape((RELEASES.get("base") or "dl/").lstrip("/")),
               html.escape(a["file"])))

    have = {a["id"] for a in assets}
    for p in SITE["platforms"]:
        if p["id"] in have:
            continue
        kind = p["kind"] + (" · " + p["ext"] if p.get("ext") else "")
        rows.append(
            '<tr class="absent"><td class="file"><b>%s</b><span class="kind">%s</span></td>'
            '<td class="size">—</td><td class="get">لم يُبنَ بعد لهذا الإصدار</td></tr>'
            % (html.escape(p["label"]), html.escape(kind)))

    return "".join(rows), True


def build_download():
    reqs = "".join("<tr><td>%s</td><td>%s</td></tr>"
                   % (html.escape(a), html.escape(b)) for a, b in SITE["requirements"])

    baked_rows, has_release = _baked_dl_rows()
    # ── وسطرٌ يقول ما يعنيه الرماديّ ──
    # خمسةُ صفوفٍ رماديّةٍ من ثمانيةٍ تُقرأ «مشروعٌ ناقص» لا «قريبًا»: الزائرُ
    # يرى ‎٦٢٪‎ من الجدول «لا». والطيُّ خلف نقرةٍ يعيد العطبَ الذي عولج (الصفُّ
    # الرماديُّ هو الموضعُ الوحيد الذي يتعلّم فيه طالبُ مثبِّت ويندوز الحقيقة)،
    # فالعلاجُ سطرٌ **فوق** الجدول لا إخفاءٌ تحته.
    # ويختفي من تلقائه يومَ تمتلئ الثمانية — لا صيانةَ له.
    _ready = len({a["id"] for a in RELEASES.get("assets", [])})
    _total = len(SITE["platforms"])
    pending_note = ""
    if has_release and _ready < _total:
        pending_note = (
            # ‏`data-ready` هو العددُ الذي **خُبِز** في هذا النصّ. وsite.js يقابله
            # بما في المانيفست الحيّ: إن اختلفا فالسطرُ يصف جدولًا غيرَ المعروض،
            # فيُخفى بدل أن يُكذَّب برقمٍ عتيق. (والصياغةُ بالحروف تعيش هنا، فلا
            # تُعاد كتابتُها في جافاسكربت.)
            '<p class="sub dl-pending" data-ready="%d">%s من %s منصّاتٍ جاهزةٌ '
            'في هذا الإصدار، والباقيةُ تُنشَر حين يخضرّ لها خطُّ البناء — بلا تاريخٍ موعود.</p>'
            % (_ready, _AR_NUM.get(_ready, _ready), _AR_NUM_ADDED.get(_total, _total)))
    stamp = ("الإصدار %s — صدر في %s"
             % (RELEASES["version"], _fmt_date(RELEASES["date"]))
             if RELEASES.get("date") else "الإصدار %s" % RELEASES["version"]) \
        if has_release else "مجّانيٌّ ومفتوحُ المصدر · بلا حساب"

    body = (
        '<main class="page">'
        '<section class="dl-hero"><h1>نزِّل محراب</h1>'
        '<p data-dl-version>%s</p></section>' % html.escape(stamp)

        + '<div class="dl-pick" data-dl-pick hidden></div>'
        + pending_note

        # الجدولُ مرسومٌ في HTML من المخبوز، وsite.js يعيد رسمَه من الحيّ إن وصل.
        + '<div data-dl-wrap%s>' % ("" if has_release else " hidden")
        + '<div class="table-wrap"><table class="dl-table">'
          '<thead><tr><th>المنصّة</th><th>الحجم</th><th><span class="sr-only">'
          'التنزيل</span></th></tr></thead>'
          '<tbody data-dl-table>%s</tbody></table></div></div>' % baked_rows

        # حالةُ الفراغ مكتوبةٌ في HTML لا مولَّدةٌ بجافاسكربت: زائرٌ بلا سكربتات
        # يجب أن يقرأ الحقيقةَ لا صفحةً بيضاء — ولا يقرأ نفيَ إصدارٍ منشورٍ فعلًا.
        + '<div class="dl-empty" data-dl-empty%s>' % ("" if not has_release else " hidden")
        + '<b>لا إصدارَ منشورًا بعد</b>'
          '<p>محراب في طورِ ما قبل الإصدار الأوّل. الشفرةُ كاملةٌ ومفتوحة، ويمكنك بناؤه '
          'بنفسك اليوم — البناءُ الكامل يستغرق نحوَ خمسين دقيقة على جهازٍ حديث.</p>'
          '<a class="btn btn-ghost" href="%s/blob/main/build/README.md">تعليماتُ البناء</a>'
          '</div>' % SITE["repo"]

        # ⤵ «أوّلُ تشغيل» يسبق «تحقّق ممّا نزّلت».
        #    التسلسلُ الزمنيُّ يقول العكسَ (تتحقّق ثمّ تشغّل)، وجُرِّب —
        #    لكنّ الترتيبَ بالحاجة لا بالزمن: **«أوّلُ تشغيل» يحتاجه كلُّ
        #    مستخدمِ ماك وويندوز بلا استثناء، و«تحقّق ممّا نزّلت» يفعله
        #    واحدٌ من مئة**. ودفعُ النادرِ فوق الحتميّ يجعل أوّلَ ما يقرؤه
        #    من نزّل للتوّ شرحًا لا يعنيه. والقسمُ لا يستشهد بما بعده:
        #    يشير إلى عمودٍ في الجدول **فوقه**، وذلك موجودٌ في محلّه.
        # ── «أوّلُ تشغيل» — القيدُ المُعلَن ميزةُ ثقة، والمكتشَفُ عطبٌ في نظر صاحبه ──
        # قِيس: لا `codesign` ولا `notarize` ولا Authenticode في شجرة البناء. فأوّلُ
        # ما يراه مستخدمُ ماك بعد فكّ ‎١٨٣‎ ميغابايت هو «محراب تالف ولا يمكن فتحه.
        # انقله إلى سلّة المهملات» — وهي رسالةُ **عطبٍ** لا رسالةُ أمان، وآخرُ ما
        # يراه من محراب. ومستخدمُ ويندوز يلقى شاشةَ SmartScreen الزرقاء.
        #
        # والمبدأُ مكتوبٌ في `site.json` منذ البداية — القيودُ **مع** الدعوة لا
        # بعدها — وكان مطبَّقًا على نسخة المتصفّح ومنسيًّا على المكتب.
        #
        # ⏳ ويُحذَف هذا القسمُ يومَ يعمل التوقيعُ (‏SignPath للويندوز، وشهادةُ
        # مطوّرٍ من آبل): شرحُ حاجزٍ زال يُعلِّم الزائرَ أن يتجاوز حواجزَ حقيقيّة.
        + '<section class="section dl-first-run"><h2>أوّلُ تشغيل</h2>'
          '<p class="sub">محراب مفتوحُ المصدر وثنائيّاتُه <b>ليست موقَّعةً بشهادةٍ '
          'تجاريّةٍ بعد</b>، فيعترضك نظامُك في المرّة الأولى وحدَها. هذا متوقَّعٌ ولا '
          'يعني أنّ الملفَّ معطوب — وبصمةُ SHA-256 في الجدول أعلاه هي ما يُثبِت '
          'سلامتَه.</p>'
          '<div class="table-wrap"><table><tbody>'
          # رسالتان لا واحدة، ولكلٍّ علاجُها: «المطوّرُ غير موثَّق» تُحلّ من لوحة
          # الأمان؛ و«تالف» رسالةُ **الحجر الصحّيّ** ولا زرَّ لها هناك أصلًا —
          # فمن يُعطى علاجَ الأولى وهو يرى الثانية يبحث عن زرٍّ غيرِ موجود.
          # وأسماءُ اللوحة تختلف بين ‎12‎ و‎13+‎، و«الإعدادات» ليست اسمًا في أيّ نسخة.
          # والأسهلُ أوّلًا: «انقر باليمين ← فتح» يتجاوز الحجرَ بلا طرفيّةٍ في
          # أكثر الحالات. وتقديمُ الأمر النصّيِّ عليه يُخيف من لم يفتح طرفيّةً
          # قطّ — وهو جمهورُ محرابٍ الأوّل — ويجعله يظنّ أنّ التثبيت يحتاج خبرة.
          '<tr><th>ماك</th><td><b>جرّب أوّلًا:</b> انقل محرابًا إلى مجلّد '
          '<b>التطبيقات</b>، ثمّ <b>انقر عليه باليمين ← فتح</b> (لا نقرًا '
          'مزدوجًا)، واختر <b>فتح</b> في النافذة. يكفي هذا في أكثر الحالات.'
          '<br><br>فإن ظهرت «<b>لا يمكن فتحه لأنّ المطوّر غير موثَّق</b>»: افتح '
          '<b>إعدادات النظام ← الخصوصيّة والأمان</b> (أو <b>تفضيلات النظام ← '
          'الأمان والخصوصيّة ← عامّ</b> على macOS 12)، وستجد أسفلَها زرَّ '
          '<b>افتح على أيّ حال</b>.'
          '<br><br>وإن ظهرت «<b>تالف ولا يمكن فتحه</b>» فهي الحجرُ الصحّيّ ولا '
          'زرَّ لها. افتح <b>الطرفيّة</b> — اضغط <b>⌘ + مسافة</b> واكتب '
          '<span dir="ltr">Terminal</span> — والصِق هذا السطرَ مرّةً واحدة:'
          # ‏`<pre>` لا `<code>` مجرّدًا: docs.js يضيف زرَّ «انسخ» إلى كلّ `<pre>`
          # وحدَه. وهذا **الأمرُ الوحيد في الموقع كلِّه الذي نطلب من القارئ
          # تنفيذَه**، وفيه اسمُ ملفٍّ عربيٌّ داخل مسارٍ لاتينيّ — أصعبُ ما
          # يُنسَخ بالتحديد اليدويّ وأسهلُ ما يُخطئ فيه من يكتبه بيده.
          '<pre><code dir="ltr">xattr -dr com.apple.quarantine '
          '/Applications/محراب.app</code></pre>'
          '</td></tr>'
          '<tr><th>ويندوز</th><td>تظهر شاشةُ <b>SmartScreen</b> الزرقاء — على المثبِّت، '
          'وعلى <code>Mihrab.exe</code> من النسخة المحمولة كذلك (الملفّاتُ المستخرَجة من '
          'أرشيفٍ منزَّل تحمل علامةَ الويب). اضغط '
          '<b>مزيدٌ من المعلومات</b> ثمّ <b>تشغيل على أيّ حال</b>.</td></tr>'
          '<tr><th>لينكس</th><td>لا حاجز. وحزمتا <code>.deb</code> و'
          '<code>.rpm</code> تُثبِّتان بمدير الحزم مباشرةً.</td></tr>'
          '</tbody></table></div></section>'

        + '<section class="section dl-verify"><h2>تحقّق ممّا نزّلت</h2>'
          '<p class="sub">بصمةُ SHA-256 لكلّ ملفٍّ منشورةٌ في الجدول أعلاه. قارِنها '
          'بما نزّلتَه قبل التنصيب — تطابقُها يثبت أنّ الملفّ وصلك كما غادرَنا.</p>'
          '<pre><code>%s</code></pre></section>' % _verify_snippet()

        + '<section class="section"><h2>المتطلّبات</h2>'
          '<div class="table-wrap"><table><tbody>%s</tbody></table></div></section>' % reqs

        + '<section class="section"><h2>الخصوصيّة</h2>'
          '<p>محراب لا يجمع قياسَ استعمالٍ ولا يرسل تقاريرَ أعطالٍ تلقائيّة، وخدمةُ '
          'التحديث التلقائيّ معطَّلةٌ فيه. تحديثُ النسخة يكون بتنزيلٍ منك أنت.</p>'
          '</section>'

        + '</main>'
        + data_island("site-platforms", SITE["platforms"])
        + data_island("baked-releases", RELEASES)
    )
    return page_shell(
        "نزِّل محراب", body, "..",
        "نزِّل محراب — محرّرُ الأكواد العربيّ. ويندوز ولينكس وmacOS، مجّانيٌّ ومفتوحُ المصدر.",
        active="download", canon_path="download/",
        with_search=False, extra_js=("site.js",))


# ═════════════════════ صفحة الاختصارات ═════════════════════
def build_keyboard_page():
    """أهمُّ صفحةٍ في الموقع: بديلُ المنبع لها ملفُّ PDF إنجليزيٌّ وLTR معًا.

    ترتيبُ الأعمدة: الوصفُ العربيّ يمينًا لأنّ المستخدم يبحث بالمعنى («أريد تقسيم
    المحرّر») لا بالمفتاح؛ ثمّ الاختصارُ معزولًا في الوسط؛ ثمّ معرّفُ الأمر اللاتينيّ
    باهتًا — يحتاجه من يحرّر `keybindings.json` ولا يزاحم القارئ العابر.
    """
    with open(os.path.join(DATA, "keybindings.json"), encoding="utf-8") as f:
        data = json.load(f)

    out = []
    for group in data["groups"]:
        rows = []
        for e in group["items"]:
            win, mac = e["win"], e.get("mac") or e["win"]
            # ⚠️ **الملاحظةُ في حقلها لا في اسم الأمر.** «فتح ملفّ — وعلى ماك المكتبيّ
            # الأمرُ «فتح…» (workbench.action.files.openFileFolder) يفتح…» جعل الصفَّ
            # ‎5‎ أسطرٍ على ‎1280‎ (والبقيّةُ سطران)، والمعرّفُ اللاتينيُّ داخل النصّ
            # كلمةٌ لا تنكسر فرفع أدنى عرضِ العمود الأوّل إلى ‎292‎: الجدولُ ‎801‎ في
            # حاويةٍ ‎676‎ وعمودُ المعرّف مقصوصٌ في ‎12‎ صفًّا من ‎13‎ (قِيس على الحيّ،
            # الجولة ‎16‎). فالاسمُ قصيرٌ يُمسَح بالعين، والملاحظةُ سطرٌ باهتٌ تحته
            # يُبحَث فيه ولا يُقرأ في نتيجة الالتقاط.
            note = e.get("note") or ""
            search = " ".join([e["ar"], note, e["id"], win, mac])
            # ⚠️ **بترتيب `chordFromEvent` في docs.js** (‏Ctrl، Cmd، Shift، Alt، ثمّ المفتاح).
            # الالتقاطُ يقارن السلسلةَ حرفًا بحرف، و«Shift+Alt+Cmd+C» كما كُتبت في
            # البيانات لا تطابق «Cmd+Shift+Alt+C» كما يبنيها الحدث — فثلاثةُ اختصاراتِ ماك
            # كانت تُلتقَط «لا أمرَ معروفًا» والصفُّ أمام الزائر (الجولة ‎16‎). يُقنَّن ما
            # يُقارَن لا ما يُعرَض. يحرسه [CAP-01].
            # و«—» علامةُ «بلا اختصار» في البيانات لا ضغطة: كانت تُكتب في `data-chords`
            # فيطابقها محرفٌ مطبوعٌ واحد، وتغذّي رحلةَ [CAP-03] ضغطةً وهميّة.
            chords = "|".join(sorted({_canon_chord(c) for c in (win, mac) if c.strip() != "—"}))
            name = '<span class="cmd-name">%s</span>' % html.escape(e["ar"])
            if note:
                # ‏`kbd-note` لا `note`: الأخيرُ صندوقُ تنبيهٍ في التوثيق (خلفيّةٌ وحدٌّ وحشو).
                name += '<small class="kbd-note">%s</small>' % html.escape(note)
            rows.append(
                '<tr data-search="%s" data-chords="%s">'
                '<td>%s</td>'
                '<td class="k"><span class="keys" data-platform="win">%s</span>'
                '<span class="keys" data-platform="mac" hidden>%s</span></td>'
                '<td class="id"><code>%s</code></td></tr>'
                # ⚠️ والمعرّفُ يقبل الكسرَ بعد النقطة: بلا فرصةِ كسرٍ يكون أدنى عرضِ عموده
                # عرضَه كلَّه (‏323 لـ`newUntitledFile`) ومعه عمودُ الاختصار (لا يلتفّ)،
                # فلا يبقى لاسم الأمر وملاحظته إلّا ‎132‎ من ‎676‎ على ‎1280‎ (قِيس محلّيًّا:
                # ‎8‎ أسطر). `<wbr>` لا يُستعمَل إلّا عند الضيق ولا يدخل النصَّ المنسوخ.
                % (html.escape(search), html.escape(chords), name,
                   _chord_inner(win), _chord_inner(mac),
                   html.escape(e["id"]).replace(".", ".<wbr>")))
        out.append(
            '<section class="kbd-section"><h2 id="%s">%s</h2>'
            # ⚠️ `data-kbd-table` ليس زينة: docs.js يبحث عنه ليقرّر أنّه في صفحة
            # الاختصارات، وبدونه يخرج مبكّرًا فيموت مبدِّلُ النظام والترشيحُ
            # و«التقط اختصارًا» معًا — بصمتٍ تامّ، والصفحةُ تبدو سليمة.
            '<div class="table-wrap"><table class="kbd-table" data-kbd-table>'
            '<thead><tr><th>الأمر</th><th>الاختصار</th><th>معرّف الأمر</th></tr></thead>'
            '<tbody>%s</tbody></table></div></section>'
            % (html.escape(group["id"]), html.escape(group["title"]), "".join(rows)))

    toolbar = (
        '<div class="kbd-toolbar">'
        '<div class="grow"><input type="search" id="kbd-filter" '
        'placeholder="رشِّح بالأمر أو بالمفتاح…" aria-label="ترشيح الاختصارات"></div>'
        '<div class="seg" role="group" aria-label="النظام">'
        '<button type="button" data-platform="win" aria-pressed="true">ويندوز / لينكس</button>'
        '<button type="button" data-platform="mac" aria-pressed="false">macOS</button>'
        '</div>'
        '<button class="icon-btn" id="capture-btn" type="button">التقط اختصارًا</button>'
        '<button class="icon-btn print-btn" type="button" onclick="window.print()">اطبع البطاقة</button>'
        '</div>'
        '<div class="capture-box" hidden>'
        '<input type="text" id="capture-field" placeholder="اضغط الاختصار الآن…" '
        'aria-label="التقاط اختصار">'
        '<div class="result dim">سيظهر الأمرُ المطابق هنا.</div></div>'
        '<p class="no-results" hidden>لا اختصارَ يطابق ما كتبت.</p>'
        # ما يُنطَق عند الترشيح — انظر `kbdWord` في docs.js.
        '<div class="sr-only kbd-status" role="status" aria-live="polite"></div>'
    )
    return toolbar + "".join(out), [
        (2, g["id"], g["title"]) for g in data["groups"]]


# ترتيبُ المعدِّلات كما يبنيه `chordFromEvent` في docs.js — والحارسُ [CAP-01] يقرأه من هناك.
_MOD_ORDER = ("Ctrl", "Cmd", "Shift", "Alt")


def _canon_chord(chord):
    """‏«Shift+Alt+Cmd+C» ⇒ «Cmd+Shift+Alt+C»؛ والمتتابعُ («Ctrl+K Ctrl+O») ضغطةً ضغطة."""
    out = []
    for press in chord.split(" "):
        parts = [p.strip() for p in press.split("+") if p.strip()]
        if not parts:
            continue
        mods, key = parts[:-1], parts[-1]
        out.append("+".join([m for m in _MOD_ORDER if m in mods]
                            + [m for m in mods if m not in _MOD_ORDER] + [key]))
    return " ".join(out)


def _chord_inner(chord):
    """الفراغُ يفصل **ضغطتين متتاليتين** (‏`Ctrl+K Ctrl+S`) و`+` يفصل مفاتيحَ الضغطة
    الواحدة. كان القسمُ على `+` وحدَه فتُعرَض «Ctrl + K Ctrl + S»: قبعةٌ واحدةٌ
    مكتوبٌ عليها «K Ctrl» — في ستّةِ صفوفٍ ثلاثةٌ منها في «أساسيّات» (قِيس على
    الحيّ، الجولة ‎16‎). فتُرسَم الضغطتان قبعاتٍ مستقلّةً بينهما «ثمّ»."""
    bits = []
    for j, stroke in enumerate(chord.split()):
        if j:
            bits.append('<span class="then">ثمّ</span>')
        parts = [p.strip() for p in stroke.split("+") if p.strip()]
        for i, p in enumerate(parts):
            if i:
                bits.append('<span class="plus">+</span>')
            bits.append('<kbd class="chord" dir="ltr">%s</kbd>' % html.escape(p))
    return "".join(bits)
