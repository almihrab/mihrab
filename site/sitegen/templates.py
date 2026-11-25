# -*- coding: utf-8 -*-
"""قوالبُ الصفحة المشتركة: الترويسة، والتنقّل، والفهرس، والتذييل، والغلاف."""
import html
import json

from .data import NAV, SITE, UPSTREAM_DOCS

# ═════════════════════ القوالب ═════════════════════
MARK_SVG = (
    '<svg class="%s" viewBox="0 0 24 32" fill="none" aria-hidden="true">'
    '<path d="M2 31V14C2 7.4 6.5 2 12 2s10 5.4 10 12v17" stroke="currentColor" '
    'stroke-width="2.2" stroke-linecap="round"/>'
    '<path d="M7 31V15c0-3.4 2.2-6 5-6s5 2.6 5 6v16" stroke="currentColor" '
    'stroke-width="1.4" opacity=".55" stroke-linecap="round"/></svg>'
)


# وصفُ كلّ قسمٍ في فهرس `/docs/` — مفاتيحُه أسماءُ أقسام `NAV` حرفًا بحرف،
# فقسمٌ يُعاد تسميتُه يفقد وصفَه ظاهرًا لا صامتًا (النصُّ يغيب، والعنوانُ يبقى).
DOCS_SECTION_NOTE = {
    "ابدأ": "أوّلُ ملفٍّ وأوّلُ تشغيل، وما تراه على الشاشة.",
    "اكتب": "الكتابةُ والتنقّل والبحث والطرفيّة — ما تقضي فيه يومَك.",
    "اضبط ووسّع": "اجعله لك: المظهرُ والإعداداتُ والامتداداتُ والتنقيح.",
}


def nav_html(active, base):
    # ── ومحرابُ المتصفّح **أوّلَ عنصرٍ في الدرج** ──
    # رابطُ الترويسة إليه يُخفى تحت ‎560px‎ (‏انظر التعليلَ المقيسَ في
    # `mihrab-home.css`: الترويسةُ تفيض ‎143‎ بكسلًا على ‎320px‎ ولا يسع فيه
    # ما يكفي إلّا هذا الرابط). والدرجُ هو المكانُ الذي يفتحه زائرُ الجوّال
    # **حتمًا** لأنّه تنقّلُه الوحيد في صفحات التوثيق — فهو التعويضُ الطبيعيّ.
    # وبدونه نكون أخفينا عن زائر الجوّال الشيءَ الوحيدَ في هذا الموقع الذي
    # يعمل على جهازه.
    #
    # وهو ظاهرٌ على المكتب كذلك ولا ضررَ: الدرجُ قائمةُ تنقّلٍ، ومحرابُ
    # المتصفّح وجهةٌ من وجهاته. و`rel="noopener"` لأنّه أصلٌ آخرُ فعلًا.
    # والسهمُ للعين لا للأذن: قارئُ الشاشة كان ينطق «محرابُ المتصفّح سهمٌ إلى أعلى
    # اليمين» — فيُخفى عنه، ويُقال له بنصٍّ مخفيٍّ ما يعنيه السهم: موقعٌ آخر.
    # ولا «نافذةٌ جديدة»: الرابطُ بلا `target`، يفتح في التبويب نفسِه.
    parts = ['<h2>%s</h2><ul><li><a class="nav-app" href="%s" rel="noopener">'
             '%s <span aria-hidden="true">↗</span>'
             '<span class="sr-only">(موقعٌ آخر)</span></a></li></ul>'
             % (html.escape("جرّب"), html.escape(SITE["browser"]["url"]),
                html.escape("محرابُ المتصفّح"))]
    for section, items in NAV:
        parts.append("<h2>%s</h2><ul>" % html.escape(section))
        for slug, title in items:
            cur = ' aria-current="page"' if slug == active else ""
            parts.append('<li><a href="%s/%s/"%s>%s</a></li>'
                         % (base, slug, cur, html.escape(title)))
        parts.append("</ul>")
    return "".join(parts)


def toc_html(headings):
    if len(headings) < 2:
        return ""
    items = "".join(
        '<li class="lvl-%d"><a href="#%s">%s</a></li>' % (lvl, hid, html.escape(txt))
        for lvl, hid, txt in headings)
    return ('<nav class="site-toc" aria-label="في هذه الصفحة">'
            '<div class="toc-title">في هذه الصفحة</div><ul>%s</ul></nav>' % items)


def src_note_html(meta):
    """تذييلُ النسبة — شرطُ رخصة CC BY، ودليلُ صدقٍ في آنٍ واحد.

    ولا ذكرَ لعلامةِ مايكروسوفت كتسميةٍ للمنتج: الترخيصُ يُجيز النصَّ لا العلامة.
    """
    if not meta.get("source_path"):
        return ""
    url = UPSTREAM_DOCS + meta["source_path"]
    bits = ['تُرجم عن <a href="%s" rel="nofollow">صفحة المنبع</a>' % html.escape(url)]
    if meta.get("translated_at"):
        bits.append('حُدّث %s' % html.escape(meta["translated_at"]))
    bits.append('بترخيص <a href="https://creativecommons.org/licenses/by/3.0/us/" '
                'rel="license nofollow">CC BY 3.0 US</a>')
    return ('<div class="src-note">%s<br>محراب مشروعٌ مستقلٌّ لا صلةَ له بمايكروسوفت.</div>'
            % ' <span class="dot">·</span> '.join(bits))


def drift_banner_html(meta):
    """الانجرافُ الكبيرُ وحده يعترض القارئ فوق المقال. وما دونه يبقى في التذييل."""
    if meta.get("drift") != "major":
        return ""
    return ('<div class="drift-banner"><b>تنبيه</b>'
            '<span>هذه الترجمة أقدمُ من الأصل الإنجليزيّ. '
            'راجِع <a href="%s">صفحة المنبع</a> للتفاصيل المستجدّة.</span></div>'
            % html.escape(UPSTREAM_DOCS + meta.get("source_path", "")))


FOOTER_LINKS = [
    ("المنتج", [
        ("{base}/", "الصفحة الأولى"),
        ("{base}/download/", "نزِّل محراب"),
        # وهو أصلٌ آخرُ فعلًا لا مسارٌ في هذا الموقع، فعنوانُه مطلقٌ عمدًا —
        # ويستثنيه حارسُ الروابط المطلقة في `check_site.py` بالاسم لهذا السبب.
        (SITE["browser"]["url"], "محرابُ المتصفّح"),
        ("{base}/docs/", "التوثيق"),
        ("{base}/keyboard/", "بطاقةُ الاختصارات"),
    ]),
    ("ابدأ", [
        ("{base}/start/", "البدء في دقيقة"),
        ("{base}/interface/", "جولةٌ في الواجهة"),
        ("{base}/settings/", "الإعدادات"),
        ("{base}/extensions/", "الامتدادات"),
    ]),
    ("المشروع", [
        ("%s" % SITE["repo"], "المستودع على GitHub"),
        ("%s/issues/new" % SITE["repo"], "أبلِغ عن عطب"),
        ("%s/blob/main/LICENSE" % SITE["repo"], "الرخصة"),
    ]),
]


def header_html(base, active, with_search, with_nav=False):
    """ترويسةٌ واحدة لكلّ الصفحات.

    البحثُ يظهر في صفحات التوثيق وحدها: حقلُ بحثٍ في صفحةٍ لا فهرسَ لها يَعِد
    بما لا يفي، وحقلٌ فارغٌ في الصفحة الأولى يزاحم الزرَّ الوحيد الذي أتى له الزائر.
    """
    # ‏`id` باقٍ على حقل الترويسة وحدَه: اختصارُ `/` يقصده بالاسم، وهو واحدٌ
    # في كلّ صفحة. وصندوقُ `/docs/` الأوسطُ بلا `id` — انظر التعليل هناك.
    # ‏`aria-expanded` و`role="status"`: قارئُ الشاشة كان لا يُخبَر أنّ نتائجَ
    # ظهرت البتّة — يكتب المستخدمُ ولا شيءَ يُعلَن، فيبدو الحقلُ معطوبًا كما بدا
    # للمبصر حين كان الصندوقُ الأوسطُ ميّتًا. و`status` لا `alert`: إعلانٌ مهذّبٌ
    # ينتظر صمتَ القارئ ولا يقطع ما يقرؤه بعد كلّ ضغطةِ مفتاح.
    # ── ⛔ ولا `aria-live` على **قائمة** النتائج ──
    # كانت `role="status" aria-live="polite"` على الحاوية التي يُعاد بناءُ
    # محتواها كلِّه عند كلّ ضغطةِ مفتاح. فكتابةُ «طرفيّة» — سبعةُ محارف — تُنتج
    # سبعَ إعلاناتٍ متتالية، كلٌّ منها **اثنتا عشرة نتيجةً بعناوينها وأقسامها**:
    # نحو مئةِ سطرٍ منطوقٍ لكلمةٍ واحدة. و`polite` لا تُنقذ — هي تؤجّل ولا
    # تُلغي، فالطابورُ يتراكم ويُنطَق بعد فراغ اليد. وقارئُ الشاشة الذي أُضيف
    # الإعلانُ لأجله يصير أسوأَ حالًا ممّن لا إعلانَ عنده.
    #
    # فالمنطوقُ سطرٌ واحدٌ قصيرٌ يصف العدد، والقائمةُ نفسُها صامتةٌ يبلغها
    # المستخدمُ بـTab كأيّ روابط. و`aria-expanded` باقٍ يصف الحالة.
    # ── ⚠️ والإخفاءُ بلا جافاسكربت يشمل **كلّ** صندوق، لا الأوسطَ وحدَه ──
    # كانت `<noscript>` تُخفي `.home-search` في `/docs/` فقط، وحقلُ الترويسة
    # — وهو في **أربعَ عشرةَ صفحةَ توثيقٍ كلِّها** — يبقى ظاهرًا وهو جافاسكربت
    # خالصٌ لا يجلب فهرسًا ولا يردّ حرفًا. فمن عطّل السكربتات نجا من الحقل في
    # الصفحة الواحدة التي تحته فيها فهرسٌ كامل، ووقع فيه في الثلاثَ عشرةَ
    # التي لا بديلَ فيها إلّا الدرجُ الجانبيّ. وهو العلاجُ عينُه يُطبَّق نصفَ
    # تطبيق. و`.site-links` تُدفَع إلى الحافّة بدلَ الحقل الذاهب كي لا تلتصقَ
    # بالعلامة.
    noscript_hide = ('<noscript><style>.search-box{display:none}'
                     '.site-header .site-links{margin-inline-start:auto}'
                     '</style></noscript>')

    mid = (noscript_hide + '<div class="header-search search-box">'
           '<input type="search" id="site-search" class="search-input" '
           'placeholder="ابحث في التوثيق…  /" aria-label="بحث" '
           'role="combobox" aria-expanded="false" aria-autocomplete="list" '
           'aria-controls="site-search-results">'
           '<div class="search-results" id="site-search-results" hidden></div>'
           '<div class="sr-only search-status" role="status" aria-live="polite">'
           '</div></div>'
           if with_search else '<div class="header-spacer"></div>')

    def link(href, text, cls="", key=None):
        cur = ' aria-current="true"' if key and key == active else ""
        c = ' class="%s"' % cls if cls else ""
        return '<a href="%s"%s%s>%s</a>' % (href, c, cur, html.escape(text))

    # ── ورابطُ المحرِّر **ثابتٌ في الترويسة** ──
    # كان محرابُ المتصفّح — المنتَجُ الذي يعمل اليومَ في كلّ جهازٍ بلا تثبيتٍ ولا
    # انتظار — غيرَ مذكورٍ في الترويسة ولا في التذييل ولا في زرّي الشاشة الأولى.
    # جسرُه الوحيدُ بطاقةٌ **تحت الطيّة**، بعد لقطةِ شاشةٍ بعرض الصفحة. فزائرُ
    # الجوّال — وهو من لا يعنيه التنزيلُ أصلًا — يرى صفحةَ تنزيلٍ لا تخصّه ويغادر،
    # والمحرِّرُ على بعد تمريرةٍ واحدةٍ منه.
    #
    # ‏`rel="noopener"` لأنّه أصلٌ آخرُ فعلًا: عزلُ الأصل هو علّةُ الفصل كلِّه،
    # فلا يُمنَح المفتوحُ مرجعًا إلى نافذتنا.
    links = ('<nav class="site-links" aria-label="أقسام الموقع">%s%s%s</nav>' % (
        link(base + "/docs/", "التوثيق", "docs-link", "docs"),
        '<a class="app-link" href="%s" rel="noopener">جرّبه في المتصفّح</a>'
        % html.escape(SITE["browser"]["url"]),
        link(base + "/download/", "نزِّل", "cta", "download"),
    ))

    # ── زرُّ «القائمة» **حيث يوجد درجٌ يفتحه** ──
    # كان يُطبَع في كلّ صفحة، و`#nav-toggle{display:inline-block}` تحت 900px غيرُ
    # مشروطةٍ بوجود `.site-nav`. فعلى الجوّال تحمل الصفحةُ الأولى و`/docs/`
    # و`/download/` و`404` زرًّا ظاهرًا **لا يفعل شيئًا** (‏docs.js يشترط
    # `navBtn && nav`، وnav معدوم) — وفي الوقت نفسِه يُخفى رابطُ «التوثيق» من
    # الترويسة تحت 900px. فالزائرُ على الهاتف يفقد التوثيقَ من الشريط، يرى زرَّ
    # قائمةٍ، يضغطه… ولا شيء. وزرٌّ ميّتٌ أسوأُ من غيابه: الغيابُ يدفعه للتمرير،
    # والموتُ يقنعه أنّ الموقعَ معطوب. و`aria-controls` كان يشير إلى `site-nav`
    # غيرِ الموجود أصلًا، فقارئُ الشاشة يَعِد بهدفٍ لا وجودَ له.
    nav_btn = ('<button class="icon-btn" id="nav-toggle" type="button" '
               'aria-expanded="false" aria-controls="site-nav">القائمة</button>'
               if with_nav else "")

    return ('<header class="site-header">'
            '<a class="brand" href="%s/">%s<span>محراب</span></a>'
            '%s%s'
            '<button class="icon-btn" id="theme-toggle" type="button">فاتح</button>'
            '%s'
            '</header>' % (base, MARK_SVG % "mark", mid, links, nav_btn))


def footer_html(base):
    cols = []
    for heading, items in FOOTER_LINKS:
        lis = "".join('<li><a href="%s">%s</a></li>'
                      % (href.format(base=base), html.escape(text))
                      for href, text in items)
        cols.append("<div><h4>%s</h4><ul>%s</ul></div>" % (html.escape(heading), lis))
    return (
        '<footer class="site-footer"><div class="footer-in">'
        '<div class="footer-brand">'
        '<a class="brand" href="%s/">%s<span>محراب</span></a>'
        '<p>محرّرُ أكوادٍ عربيُّ الواجهة والاتّجاه، مبنيٌّ على VSCodium. '
        'مجّانيٌّ ومفتوحُ المصدر.</p></div>'
        '%s</div>'
        # النِسبةُ والتبرّؤ في كلّ صفحة لا في صفحات التوثيق وحدها: زائرُ الصفحة
        # الأولى هو من قد يظنّ محرابًا منتجَ مايكروسوفت، لا قارئُ صفحةِ الاختصارات.
        '<div class="footer-legal">محراب مشروعٌ مستقلٌّ لا صلةَ له بمايكروسوفت ولا '
        'برعايتها. مبنيٌّ على <a href="https://vscodium.com/">VSCodium</a>، '
        'والتوثيقُ مترجَمٌ عن <a href="https://github.com/microsoft/vscode-docs">vscode-docs</a> '
        'بترخيص CC BY 3.0 US.</div></footer>'
        % (base, MARK_SVG % "mark", "".join(cols)))


def page_shell(title, body, base, description="", active=None, canon_path="",
               with_search=True, extra_js=(), with_nav=False, icon=None):
    """قالبُ الصفحة.

    `product=True` يضيف ورقةَ أنماط المنتج ويحذف درجَ التوثيق. وفُصلت الورقتان
    عمدًا: التوثيقُ يُقرأ والصفحةُ الأولى تُقنِع، ودمجُهما يجعل كلَّ تعديلٍ تسويقيّ
    يخاطر بتخطيط صفحات التوثيق كلِّها.
    """
    css = ['<link rel="stylesheet" href="%s/assets/fonts.css">' % base,
           '<link rel="stylesheet" href="%s/assets/mihrab-docs.css">' % base,
           '<link rel="stylesheet" href="%s/assets/mihrab-home.css">' % base]
    scripts = ['<script src="%s/assets/docs.js" defer></script>' % base]
    scripts += ['<script src="%s/assets/%s" defer></script>' % (base, j) for j in extra_js]

    full_title = title if title.startswith("محراب") else "%s — محراب" % title
    return """<!doctype html>
<html lang="ar" dir="rtl">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:locale" content="ar_AR">
<meta name="theme-color" content="#F5F0E4" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0F1C24" media="(prefers-color-scheme: dark)">
<link rel="icon" href="{icon}" type="image/svg+xml">
<link rel="canonical" href="{canon}">
{css}
<body data-base="{base}">
{header}
<div class="nav-scrim" hidden></div>
{body}
{footer}
{scripts}
</html>
""".format(title=html.escape(full_title), desc=html.escape(description), base=base,
           icon=html.escape(icon or base + "/assets/icon.svg"),
           canon=html.escape(SITE["canonical"].rstrip("/") + "/" + canon_path),
           css="\n".join(css),
           header=header_html(base, active, with_search, with_nav),
           body=body, footer=footer_html(base), scripts="\n".join(scripts))


# ═════════════════════════════════════════════════════════════════════════
#  واجهةُ المنتج — الصفحةُ الأولى وصفحةُ التنزيل
# ═════════════════════════════════════════════════════════════════════════

def data_island(el_id, obj):
    """بياناتٌ لـsite.js داخل الصفحة لا في طلبٍ ثانٍ.

    `</` تُهرَّب: سلسلةٌ في JSON تحوي `</script>` تُنهي الوسمَ مبكّرًا وتفتح ثغرةَ
    حقنٍ — وهو عطبٌ لا يظهر إلّا حين يكتب أحدُهم وسمًا في نصٍّ تسويقيّ بعد سنة.
    """
    payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return ('<script type="application/json" id="%s">%s</script>'
            % (el_id, payload.replace("</", "<\\/")))
