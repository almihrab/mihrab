#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مولِّدُ موقع محراب العربيّ — واجهةُ المنتج + التوثيق.

لماذا مولِّدٌ لنا لا قالبٌ جاهز (Docsy/Just-the-Docs/Docusaurus)؟ قرارُ سالي، وسببُه
أنّ دعمَ RTL في تلك القوالب طبقةُ `[dir=rtl]` مضافةٌ لاحقًا: تغطّي التخطيطَ ولا تغطّي
الحالاتِ الحدّيّة — عزلَ bidi، واتّجاهَ الدرج، وتخطيطَ الطباعة. وترقيعُها أطولُ من
كتابةِ ما نملك، وتفرض هويّةً بصريّة تناقض ذهبَ محرابٍ ونقشَه.

الاستعمال:  python site/build.py            → site/public/
            python site/build.py --check    → لا كتابة؛ يتحقّق من السلامة فقط
"""
import html
import json
import os
import re
import struct
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "content")
ASSETS = os.path.join(HERE, "assets")
DATA = os.path.join(HERE, "data")
# ‏`MIHRAB_SITE_OUT` يسمح بالبناء إلى مجلّدٍ مؤقّت: حارسُ [SITE-01] يبني في
# كلّ تشغيلٍ للطبقة الساكنة **ليُثبِت أنّ الموقعَ يُبنى**، ولا يجوز أن يدوس
# مخرَجًا قائمًا لأجل فحص.
OUT = os.environ.get("MIHRAB_SITE_OUT") or os.path.join(HERE, "public")

UPSTREAM_DOCS = "https://github.com/microsoft/vscode-docs/blob/main/"

# ═════════════════════ البيانات ═════════════════════
# النصُّ التسويقيّ ومصفوفةُ المنصّات بياناتٌ لا كود: تغييرُ جملةٍ في الصفحة الأولى
# يجب ألّا يمرَّ بمراجعةِ بايثون.
with open(os.path.join(DATA, "site.json"), encoding="utf-8") as _f:
    SITE = json.load(_f)
with open(os.path.join(DATA, "releases.json"), encoding="utf-8") as _f:
    RELEASES = json.load(_f)

# ⚠️ كلُّ المسارات نسبيّة (`.` و`..`) عمدًا: المخرَجُ نفسُه يُخدَم من
# `sad-lang.org/mihrab/` ومن `almihrab.github.io/mihrab/` بلا إعادةِ بناء.
# مسارٌ مطلقٌ واحد يربط المخرَج بمضيفٍ بعينه ويكسر المرآة صامتًا.

# التنقّل: ثلاثةُ أقسامٍ عليا فقط. أكثرُ من ثلاثةٍ يُجبر المستخدمَ على قرارٍ قبل أن
# يعرف ما يريد. والتسميةُ أفعالُ أمرٍ لا أسماءَ مجرّدة: الفعلُ يخاطب القارئ،
# والاسمُ يصف رفًّا في مكتبة.
NAV = [
    ("ابدأ", [
        ("start", "البدء في دقيقة"),
        ("interface", "جولة في الواجهة"),
        ("folders", "فتح مجلّد ومشروع"),
    ]),
    ("اكتب", [
        ("editing", "أساسيّات المحرّر"),
        ("keyboard", "اختصارات لوحة المفاتيح"),
        ("search", "البحث والاستبدال"),
        ("intellisense", "الإكمال والتلميحات"),
        ("terminal", "الطرفيّة المدمجة"),
    ]),
    ("اضبط ووسّع", [
        ("settings", "الإعدادات"),
        ("themes", "السمات والمظهر"),
        ("git", "Git ومصادر التحكّم"),
        ("debug", "التنقيح"),
        ("extensions", "الامتدادات"),
    ]),
]

SLUG_SECTION = {slug: sec for sec, items in NAV for slug, _t in items}
SLUG_TITLE = {slug: t for _s, items in NAV for slug, t in items}


# ═════════════════════ Markdown — مجموعةٌ فرعيّة مضبوطة ═════════════════════
# لا نستورد مكتبةً: المحتوى ملكُنا وقواعدُه مغلقة، ومولِّدٌ بلا اعتماديّات يعمل في
# أيّ CI بلا تثبيت. وكلُّ ما لا تدعمه هذه الدالّة يُرفَض صراحةً لا يُتجاهَل صامتًا.

_INLINE_CODE = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_KBD = re.compile(r"\{\{([^}]+)\}\}")  # {{Ctrl+Shift+P}} → اختصارٌ معزول


def _chord_html(chord):
    """يبني حاويةَ اختصارٍ معزولةً اتّجاهيًّا.

    المفاتيحُ لا تُترجَم: `Ctrl` يبقى `Ctrl` لا «تحكّم» — فالمكتوبُ على لوحة
    المستخدم لاتينيّ، وترجمتُه تفصل التوثيقَ عن الجهاز.
    """
    parts = [p.strip() for p in chord.split("+") if p.strip()]
    out = []
    for i, p in enumerate(parts):
        if i:
            out.append('<span class="plus">+</span>')
        out.append('<kbd class="chord" dir="ltr">%s</kbd>' % html.escape(p))
    return '<span class="keys">%s</span>' % "".join(out)


def inline(text):
    """يحوّل التعليم السطريّ. ترتيبُ العمليّات مقصود: الكودُ أوّلًا كي لا يُفسَّر ما بداخله."""
    slots = []

    def stash(markup):
        slots.append(markup)
        return "\x00%d\x00" % (len(slots) - 1)

    text = _INLINE_CODE.sub(lambda m: stash("<code>%s</code>" % html.escape(m.group(1))), text)
    text = _KBD.sub(lambda m: stash(_chord_html(m.group(1))), text)
    text = html.escape(text)
    text = _BOLD.sub(r"<b>\1</b>", text)
    text = _LINK.sub(lambda m: '<a href="%s">%s</a>' % (m.group(2), m.group(1)), text)
    return re.sub(r"\x00(\d+)\x00", lambda m: slots[int(m.group(1))], text)


def render_md(src, path_hint):
    """Markdown → (html, headings) — headings تُستعمل لبناء الفهرس الجانبيّ."""
    lines = src.split("\n")
    out, headings = [], []
    i, n = 0, len(lines)
    seen_ids = set()

    def heading_id(txt):
        base = re.sub(r"[^\w؀-ۿ]+", "-", txt).strip("-") or "قسم"
        hid, k = base, 2
        while hid in seen_ids:
            hid, k = "%s-%d" % (base, k), k + 1
        seen_ids.add(hid)
        return hid

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # كتلةُ كود
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            body, i = [], i + 1
            while i < n and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            cls = ' class="lang-%s"' % html.escape(lang) if lang else ""
            out.append("<pre><code%s>%s</code></pre>" % (cls, html.escape("\n".join(body))))
            continue

        # عنوان
        m = re.match(r"^(#{2,3})\s+(.+)$", stripped)
        if m:
            lvl, txt = len(m.group(1)), m.group(2).strip()
            hid = heading_id(txt)
            headings.append((lvl, hid, txt))
            out.append('<h%d id="%s">%s</h%d>' % (lvl, hid, inline(txt), lvl))
            i += 1
            continue

        if stripped.startswith("# "):
            raise SystemExit(
                "%s: عنوانُ h1 يأتي من `title` في الترويسة لا من المتن." % path_hint)

        # جدول
        if stripped.startswith("|"):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            if len(rows) >= 2 and set("".join(rows[1])) <= set("-: "):
                head, body = rows[0], rows[2:]
            else:
                head, body = None, rows
            t = ['<div class="table-wrap"><table>']
            if head:
                t.append("<thead><tr>%s</tr></thead>"
                         % "".join("<th>%s</th>" % inline(c) for c in head))
            t.append("<tbody>")
            for r in body:
                t.append("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in r))
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue

        # قائمة
        if re.match(r"^([-*]|\d+\.)\s+", stripped):
            ordered = bool(re.match(r"^\d+\.\s", stripped))
            items = []
            while i < n and re.match(r"^([-*]|\d+\.)\s+", lines[i].strip()):
                items.append(re.sub(r"^([-*]|\d+\.)\s+", "", lines[i].strip()))
                i += 1
            tag = "ol" if ordered else "ul"
            out.append("<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % inline(x) for x in items), tag))
            continue

        # فقرة
        para = []
        while i < n and lines[i].strip() and not re.match(
                r"^(#{1,3}\s|```|\||[-*]\s|\d+\.\s)", lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        out.append("<p>%s</p>" % inline(" ".join(para)))

    return "\n".join(out), headings


# ═════════════════════ الترويسة (front-matter) ═════════════════════
def parse_front_matter(raw, path_hint):
    if not raw.startswith("---\n"):
        raise SystemExit("%s: لا ترويسةَ front-matter." % path_hint)
    end = raw.find("\n---\n", 4)
    if end == -1:
        raise SystemExit("%s: ترويسةٌ غير مغلقة." % path_hint)
    meta = {}
    for ln in raw[4:end].split("\n"):
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        if ":" not in ln:
            raise SystemExit("%s: سطرُ ترويسةٍ بلا نقطتين: %s" % (path_hint, ln))
        k, v = ln.split(":", 1)
        meta[k.strip()] = v.strip().strip('"')
    return meta, raw[end + 5:]


# ═════════════════════ القوالب ═════════════════════
MARK_SVG = (
    '<svg class="%s" viewBox="0 0 24 32" fill="none" aria-hidden="true">'
    '<path d="M2 31V14C2 7.4 6.5 2 12 2s10 5.4 10 12v17" stroke="currentColor" '
    'stroke-width="2.2" stroke-linecap="round"/>'
    '<path d="M7 31V15c0-3.4 2.2-6 5-6s5 2.6 5 6v16" stroke="currentColor" '
    'stroke-width="1.4" opacity=".55" stroke-linecap="round"/></svg>'
)


def nav_html(active, base):
    parts = []
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
        ("https://sad-lang.org/", "لغةُ ص"),
    ]),
]


def header_html(base, active, with_search):
    """ترويسةٌ واحدة لكلّ الصفحات.

    البحثُ يظهر في صفحات التوثيق وحدها: حقلُ بحثٍ في صفحةٍ لا فهرسَ لها يَعِد
    بما لا يفي، وحقلٌ فارغٌ في الصفحة الأولى يزاحم الزرَّ الوحيد الذي أتى له الزائر.
    """
    mid = ('<div class="header-search search-box">'
           '<input type="search" id="site-search" placeholder="ابحث في التوثيق…  /" '
           'aria-label="بحث">'
           '<div class="search-results" id="search-results" hidden></div></div>'
           if with_search else '<div class="header-spacer"></div>')

    def link(href, text, cls="", key=None):
        cur = ' aria-current="true"' if key and key == active else ""
        c = ' class="%s"' % cls if cls else ""
        return '<a href="%s"%s%s>%s</a>' % (href, c, cur, html.escape(text))

    links = ('<nav class="site-links" aria-label="أقسام الموقع">%s%s</nav>' % (
        link(base + "/docs/", "التوثيق", "docs-link", "docs"),
        link(base + "/download/", "نزِّل", "cta", "download"),
    ))

    return ('<header class="site-header">'
            '<a class="brand" href="%s/">%s<span>محراب</span></a>'
            '%s%s'
            '<button class="icon-btn" id="theme-toggle" type="button">فاتح</button>'
            '<button class="icon-btn" id="nav-toggle" type="button" aria-expanded="false" '
            'aria-controls="site-nav">القائمة</button>'
            '</header>' % (base, MARK_SVG % "mark", mid, links))


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
               with_search=True, extra_js=()):
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
<meta name="theme-color" content="#0F1C24">
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
           canon=html.escape(SITE["canonical"].rstrip("/") + "/" + canon_path),
           css="\n".join(css),
           header=header_html(base, active, with_search),
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
                 'alt="محراب مفتوحٌ على ملفّ لغة ص: شريطُ النشاط والمستكشف يمينًا، '
                 'والكودُ العربيّ في المحرّر." fetchpriority="high">' % (w, h))
        note = ""
    else:
        inner = _mock_svg()
        note = ('<div class="shot-note">رسمٌ تخطيطيّ للتخطيط — لا لقطةَ شاشة. '
                'حمّل محرابًا لترى الأصل.</div>')
    return ('<div class="shot"><div class="shot-bar"><i></i><i></i><i></i>'
            '<span class="t">محراب — مرحبا.ص</span></div>%s%s</div>' % (inner, note))


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
        more = ('<a href="../%s/">اقرأ أكثر ←</a>' % s["href"]) if s.get("href") else ""
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
        + '<div class="cta-row">'
          '<a class="btn btn-primary" data-dl-primary href="./download/">نزِّل محراب</a>'
          '<a class="btn btn-ghost" href="./docs/">تصفّح التوثيق</a>'
          '</div>'
        + '<p class="cta-meta" data-dl-meta></p>'
        + '<div class="trust">%s</div>' % trust
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
          '<p>مجّانيٌّ ومفتوحُ المصدر. بلا حساب، وبلا تتبّع.</p>'
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


# ── شريطُ الانتقال: يُقال للزائر أين هو ولماذا ──
# `docs.mihrab.dev` و`dl.mihrab.dev` يحوّلان إلى هنا. والزائرُ يكتب اسمَ محرابٍ ثمّ
# يجد نفسَه على نطاقٍ اسمُه اسمُ **مشروعٍ آخر**، بلا سطرٍ يفسّر. وذلك ثلاثُ ضرباتٍ
# في لحظة: القفزُ الصامتُ بين نطاقين شكلُ التصيّد المعروف فمن يعرفه يتردّد؛
# ومحرابٌ يقول «انفصلتُ» ثمّ يرسل زائرَه إلى ما انفصل عنه فينقض فعلُه قولَه؛
# ومن حفظ العنوانَ حفظ نطاقَ غيرِنا لا اسمَنا.
#
# **وثابتٌ لا مشروطٌ بـ`document.referrer`**: المُحيلُ يُحجَب في إعداداتٍ كثيرة
# وينقطع عند ‎302‎ عبر النطاقات أحيانًا، فشرطٌ عليه يُخفي الشريطَ عن بعضِ من كُتب
# لهم. وهو صادقٌ لمن وصل مباشرةً كذلك: الصفحةُ **فعلًا** تنتقل قريبًا.
MOVE_NOTE = (
    '<aside class="move-note">'
    '<b>محرابٌ يستقلّ بنطاقه.</b> التوثيقُ والثنائيّاتُ ما زالت تُخدَم من هنا '
    'مؤقّتًا، وتنتقل قريبًا إلى <a href="https://mihrab.dev">mihrab.dev</a>. '
    'والعنوانُ الذي تحفظه اليومَ — <code>docs.mihrab.dev</code> و'
    '<code>dl.mihrab.dev</code> — يبقى يعمل بعد الانتقال.'
    '</aside>'
)


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


def build_download():
    reqs = "".join("<tr><td>%s</td><td>%s</td></tr>"
                   % (html.escape(a), html.escape(b)) for a, b in SITE["requirements"])

    body = (
        '<main class="page">'
        + MOVE_NOTE +
        '<section class="dl-hero"><h1>نزِّل محراب</h1>'
        '<p data-dl-version>مجّانيٌّ ومفتوحُ المصدر · بلا حساب</p></section>'

        '<div class="dl-pick" data-dl-pick hidden></div>'

        '<div data-dl-wrap hidden>'
        '<div class="table-wrap"><table class="dl-table">'
        '<thead><tr><th>المنصّة</th><th>الحجم</th><th></th></tr></thead>'
        '<tbody data-dl-table></tbody></table></div></div>'

        # حالةُ الفراغ مكتوبةٌ في HTML لا مولَّدةٌ بجافاسكربت: زائرٌ بلا سكربتات
        # يجب أن يقرأ الحقيقةَ لا صفحةً بيضاء.
        '<div class="dl-empty" data-dl-empty>'
        '<b>لا إصدارَ منشورًا بعد</b>'
        '<p>محراب في طورِ ما قبل الإصدار الأوّل. الشفرةُ كاملةٌ ومفتوحة، ويمكنك بناؤه '
        'بنفسك اليوم — البناءُ الكامل يستغرق نحوَ خمسين دقيقة على جهازٍ حديث.</p>'
        '<a class="btn btn-ghost" href="%s/blob/main/build/README.md">تعليماتُ البناء</a>'
        '</div>' % SITE["repo"]

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
            search = " ".join([e["ar"], e["id"], win, mac])
            chords = "|".join({win, mac})
            rows.append(
                '<tr data-search="%s" data-chords="%s">'
                '<td>%s</td>'
                '<td class="k"><span class="keys" data-platform="win">%s</span>'
                '<span class="keys" data-platform="mac" hidden>%s</span></td>'
                '<td class="id"><code>%s</code></td></tr>'
                % (html.escape(search), html.escape(chords), html.escape(e["ar"]),
                   _chord_inner(win), _chord_inner(mac), html.escape(e["id"])))
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
        '<button class="icon-btn" type="button" onclick="window.print()">اطبع البطاقة</button>'
        '</div>'
        '<div class="capture-box" hidden>'
        '<input type="text" id="capture-field" placeholder="اضغط الاختصار الآن…" '
        'aria-label="التقاط اختصار">'
        '<div class="result dim">سيظهر الأمرُ المطابق هنا.</div></div>'
        '<p class="no-results" hidden>لا اختصارَ يطابق ما كتبت.</p>'
    )
    return toolbar + "".join(out), [
        (2, g["id"], g["title"]) for g in data["groups"]]


def _chord_inner(chord):
    parts = [p.strip() for p in chord.split("+") if p.strip()]
    bits = []
    for i, p in enumerate(parts):
        if i:
            bits.append('<span class="plus">+</span>')
        bits.append('<kbd class="chord" dir="ltr">%s</kbd>' % html.escape(p))
    return "".join(bits)


# ═════════════════════ الخطوط ═════════════════════
# الوجوهُ المطلوبة. الاسمُ ⇒ (العائلة، الوزن).
FONT_FACES = [
    ("plex-arabic-400.woff2", "IBM Plex Sans Arabic", 400),
    ("plex-arabic-600.woff2", "IBM Plex Sans Arabic", 600),
    ("plex-mono-400.woff2", "IBM Plex Mono", 400),
]


def write_fonts_css(dst_assets):
    """يولّد `fonts.css` من الملفّات **الموجودة فعلًا** وينسخها.

    ولا يكتب `@font-face` لملفٍّ غائب: وجهٌ يشير إلى ملفٍّ غير موجود لا يفشل بصوت —
    بل يُطلق 404 في كلّ فتحةِ صفحة ثمّ يسقط صامتًا إلى خطٍّ آخر، فيبدو الموقعُ سليمًا
    وهو يعرض خطًّا لم نصمّم عليه. والسقوطُ الصريح في سلسلة `--font-ar` أشرفُ من ذلك.
    """
    src_dir = os.path.join(ASSETS, "fonts")
    faces, present = [], []
    for fn, family, weight in FONT_FACES:
        if os.path.isfile(os.path.join(src_dir, fn)):
            present.append(fn)
            faces.append(
                '@font-face{font-family:"%s";src:url("fonts/%s") format("woff2");'
                'font-weight:%d;font-display:swap}' % (family, fn, weight))

    if present:
        dst_dir = os.path.join(dst_assets, "fonts")
        os.makedirs(dst_dir, exist_ok=True)
        for fn in present:
            with open(os.path.join(src_dir, fn), "rb") as f_in, \
                    open(os.path.join(dst_dir, fn), "wb") as f_out:
                f_out.write(f_in.read())

    header = ('@charset "UTF-8";\n'
              "/* مولَّد من build.py — لا تحرّره. %d/%d وجهًا مورَّدًا. */\n"
              % (len(present), len(FONT_FACES)))
    with open(os.path.join(dst_assets, "fonts.css"), "w", encoding="utf-8", newline="\n") as f:
        f.write(header + "\n".join(faces) + "\n")

    if len(present) != len(FONT_FACES):
        print("  ⚠️  %d/%d وجهِ خطٍّ مورَّد — الباقي يسقط إلى Noto Sans Arabic صراحةً. "
              "ورِّد woff2 في site/assets/fonts/ لتفعيلها."
              % (len(present), len(FONT_FACES)))


# ═════════════════════ البناء ═════════════════════
def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def main():
    check_only = "--check" in sys.argv
    pages, index = [], []

    for slug in SLUG_TITLE:
        path = os.path.join(CONTENT, slug + ".md")
        if not os.path.isfile(path):
            raise SystemExit("صفحةٌ في التنقّل بلا ملفّ: %s.md" % slug)

    for fn in sorted(os.listdir(CONTENT)):
        if not fn.endswith(".md"):
            continue
        slug = fn[:-3]
        if slug not in SLUG_TITLE:
            raise SystemExit("ملفٌّ خارج التنقّل: %s — أضِفه إلى NAV أو احذفه." % fn)
        raw = open(os.path.join(CONTENT, fn), encoding="utf-8").read()
        meta, body_md = parse_front_matter(raw, fn)
        body_html, headings = render_md(body_md, fn)
        if slug == "keyboard":
            kbd_html, kbd_heads = build_keyboard_page()
            body_html += kbd_html
            headings += kbd_heads
        pages.append((slug, meta, body_html, headings))
        index.append({
            "url": slug + "/",
            "title": SLUG_TITLE[slug],
            "section": SLUG_SECTION[slug],
            "text": strip_tags(body_html)[:1200],
        })

    if check_only:
        print("✅ %d صفحة سليمة." % len(pages))
        return 0

    os.makedirs(OUT, exist_ok=True)
    # الأصول
    dst_assets = os.path.join(OUT, "assets")
    os.makedirs(dst_assets, exist_ok=True)
    for fn in os.listdir(ASSETS):
        src = os.path.join(ASSETS, fn)
        if os.path.isfile(src):
            with open(src, "rb") as f_in, open(os.path.join(dst_assets, fn), "wb") as f_out:
                f_out.write(f_in.read())
    # ‏`shots/` مجلّد، والحلقةُ أعلاه تتخطّى المجلّدات — فكانت الصفحةُ الأولى تُشير
    # إلى لقطةٍ لا تُنسَخ: مستطيلٌ مكسورٌ فوق الطيّة، بلا خطأٍ في البناء.
    # ‏`fonts/` مستثنًى: `write_fonts_css` ينسخ الموجودَ منه وحده (انظر تعليلَه).
    for sub in ("shots",):
        s_dir = os.path.join(ASSETS, sub)
        if not os.path.isdir(s_dir):
            continue
        d_dir = os.path.join(dst_assets, sub)
        os.makedirs(d_dir, exist_ok=True)
        for fn in os.listdir(s_dir):
            src = os.path.join(s_dir, fn)
            if os.path.isfile(src):
                with open(src, "rb") as f_in, open(os.path.join(d_dir, fn), "wb") as f_out:
                    f_out.write(f_in.read())
    write_fonts_css(dst_assets)

    for slug, meta, body_html, headings in pages:
        base = ".."
        title = SLUG_TITLE[slug]
        article = (
            '<main class="content">'
            + drift_banner_html(meta)
            + "<h1>%s</h1>" % html.escape(title)
            + body_html
            + src_note_html(meta)
            + "</main>"
        )
        layout = ('<div class="layout"><nav class="site-nav" id="site-nav" '
                  'aria-label="التنقّل">%s</nav>%s%s</div>'
                  % (nav_html(slug, base), article, toc_html(headings)))
        page = page_shell(title, layout, base, meta.get("description", ""),
                          active="docs", canon_path=slug + "/")
        d = os.path.join(OUT, slug)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(page)

    # ── مركزُ التوثيق: `/docs/` ──
    # الجذرُ صار للمنتج، والتوثيقُ نزل درجةً. ومسارُ كلِّ صفحةِ توثيق **لم يتغيّر**
    # (`/start/` ‏· `/keyboard/`…) عمدًا: تلك المسارات مخبوزةٌ في product.json وفي
    # قائمة «مساعدة» داخل المحرّرات المشحونة سلفًا، ونقلُها يكسرها بلا فائدة.
    cards = [
        ("start", "البدء في دقيقة", "أوّلُ ملفٍّ وأوّلُ تشغيل."),
        ("keyboard", "اختصارات لوحة المفاتيح", "بطاقةٌ مرجعيّة عربيّة، قابلةٌ للطباعة."),
        ("terminal", "الطرفيّة المدمجة", "شغّل الأوامر دون مغادرة المحرّر."),
    ]
    docs_body = (
        '<main class="home">' + MOVE_NOTE + (MARK_SVG % "mark-lg")
        + "<h1>توثيق محراب</h1>"
        + '<p class="tagline">للمِحرابِ اتّجاه، ولكودِك وِجهة.</p>'
        + '<p class="tagline-sub">مكانٌ صافٍ تكتب فيه بالعربيّة كما تُفكّر بها.</p>'
        + '<div class="home-search search-box">'
          '<input type="search" id="site-search" autofocus '
          'placeholder="ابحث في التوثيق…" aria-label="بحث">'
          '<div class="search-results" id="search-results" hidden></div></div>'
        + '<div class="cards">'
        + "".join('<a class="card" href="../%s/"><b>%s</b><span>%s</span></a>' % c
                  for c in cards)
        + "</div>"
        + '<p class="dim" style="margin-top:48px">التوثيقُ مترجَمٌ عن '
          '<a href="https://github.com/microsoft/vscode-docs">vscode-docs</a> '
          'بترخيص CC BY 3.0 US.</p>'
        + "</main>"
    )
    docs_home = page_shell(
        "توثيق محراب", docs_body, "..",
        "توثيقُ محرّر محراب بالعربيّة: البدء، المحرّر، الاختصارات، الطرفيّة.",
        active="docs", canon_path="docs/")
    write(os.path.join(OUT, "docs", "index.html"), docs_home)

    # ── واجهةُ المنتج ──
    write(os.path.join(OUT, "index.html"), build_landing())
    write(os.path.join(OUT, "download", "index.html"), build_download())
    write(os.path.join(OUT, "preview", "alif", "index.html"), build_alif_preview())

    # مانيفستُ الإصدار بجوار الصفحة: نسخةٌ متماسكة للمرآة. وعلى الخادم الأصليّ
    # يُستبدَل بالحيّ عند رفع بناءٍ جديد — ولذلك يستثني سكربتُ النشر `dl/`.
    write(os.path.join(OUT, "dl", "releases.json"),
          json.dumps(RELEASES, ensure_ascii=False, indent=2) + "\n")

    write(os.path.join(OUT, "search-index.json"),
          json.dumps(index, ensure_ascii=False, separators=(",", ":")))

    # .nojekyll — نحن نولّد HTML جاهزًا، ومعالجةُ Jekyll تحذف ما يبدأ بشرطةٍ سفليّة.
    open(os.path.join(OUT, ".nojekyll"), "w").close()

    print("✅ بُني الموقع: صفحةٌ أولى + تنزيل + مركزُ توثيق + %d صفحة → %s"
          % (len(pages), OUT))
    if not RELEASES.get("version"):
        print("  ℹ️  لا إصدارَ في releases.json — صفحةُ التنزيل تعرض حالةَ الفراغ.")
    return 0


# ═════════════════════ صفحةُ معاينة «محراب × ألف» ═════════════════════
# صفحةٌ **قائمةٌ بذاتها**، خارجَ قِشرة الموقع عمدًا: لا ملاحةَ ولا تذييلَ ولا رابطَ
# من الصفحة الرئيسة إليها. غايتُها أن تُرسَل إلى مطوّري لغةٍ بعينها ثمّ تُطوى —
# ووضعُها في الملاحة يجعل بناءَ معاينةٍ يبدو إصدارًا ثانيًا لمحراب.
# ولذلك أيضًا لا تشارك site.css: تغييرُ تنسيقٍ في الموقع بعد أشهرٍ يجب ألّا
# يُفسِد صفحةً منسيّةً لا يفتحها أحدٌ منّا.
def build_alif_preview():
    with open(os.path.join(DATA, "releases-alif.json"), encoding="utf-8") as f:
        baked = json.load(f)

    labels = {p["id"]: "%s — %s" % (p["label"], p["kind"]) for p in SITE["platforms"]}

    css = """
:root{--bg:#fbfaf7;--fg:#1c1a17;--dim:#6b645c;--line:#e0dcd4;--card:#fff;
--accent:#7a5c2e;--accent-fg:#fff;--warn-bg:#fdf6e3;--warn-line:#e8d9b0}
:root:not([data-theme="light"]){color-scheme:light dark}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
--bg:#16150f;--fg:#f0ece3;--dim:#a49c8e;--line:#332f26;--card:#1e1c15;
--accent:#d8b46a;--accent-fg:#1a1710;--warn-bg:#241f14;--warn-line:#4a3f26}}
:root[data-theme="dark"]{--bg:#16150f;--fg:#f0ece3;--dim:#a49c8e;--line:#332f26;
--card:#1e1c15;--accent:#d8b46a;--accent-fg:#1a1710;--warn-bg:#241f14;--warn-line:#4a3f26}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font-family:"Noto Naskh Arabic","Segoe UI",system-ui,sans-serif;
font-size:17px;line-height:1.85;-webkit-font-smoothing:antialiased}
.wrap{max-width:52rem;margin:0 auto;padding:3.5rem 1.25rem 5rem;
display:flex;flex-direction:column;gap:2.5rem}
.tag{display:inline-block;font-size:.8rem;letter-spacing:.06em;padding:.2rem .7rem;
border:1px solid var(--accent);color:var(--accent);border-radius:999px}
h1{font-size:clamp(1.9rem,5vw,2.7rem);line-height:1.3;margin:.7rem 0 0;text-wrap:balance}
h2{font-size:1.3rem;margin:0 0 .6rem;text-wrap:balance}
p{margin:.6rem 0}
.lead{font-size:1.1rem;color:var(--dim)}
section{border-top:1px solid var(--line);padding-top:1.8rem}
.note{background:var(--warn-bg);border:1px solid var(--warn-line);
border-radius:.6rem;padding:1rem 1.2rem}
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.95rem}
th,td{text-align:right;padding:.7rem .6rem;border-bottom:1px solid var(--line);
vertical-align:top}
th{font-size:.85rem;color:var(--dim);font-weight:600}
td.num{font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--dim)}
code,.sha{font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;
font-size:.82rem;word-break:break-all;color:var(--dim);direction:ltr;
display:inline-block;unicode-bidi:isolate}
.btn{display:inline-block;background:var(--accent);color:var(--accent-fg);
text-decoration:none;padding:.45rem 1.1rem;border-radius:.45rem;font-size:.95rem;
white-space:nowrap}
.btn:hover{filter:brightness(1.08)}
.btn:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
ul{margin:.5rem 0;padding-inline-start:1.3rem}
li{margin:.35rem 0}
.yes::marker{content:"\\2713\\a0 "}
.dim{color:var(--dim)}
.empty{color:var(--dim)}
footer{border-top:1px solid var(--line);padding-top:1.5rem;font-size:.88rem;color:var(--dim)}
a{color:var(--accent)}
@media print{.btn{display:none}}
"""

    js = """
(function(){
  var baked=JSON.parse(document.getElementById("baked").textContent);
  var labels=JSON.parse(document.getElementById("labels").textContent);
  function render(m){
    var host=document.getElementById("dl");
    if(!m||!m.assets||!m.assets.length){
      host.innerHTML='<p class="empty">\\u0644\\u0645 \\u064a\\u064f\\u0631\\u0641\\u064e\\u0639 '+
        '\\u0628\\u0646\\u0627\\u0621\\u064f \\u0645\\u0639\\u0627\\u064a\\u0646\\u0629\\u064d '+
        '\\u0628\\u0639\\u062f.</p>';
      return;
    }
    var base=m.base||"../../dl/preview-alif/";
    var rows=m.assets.map(function(a){
      var mb=(a.size/1048576).toFixed(0);
      return '<tr><td>'+(labels[a.id]||a.id)+'<br><span class="sha">'+
        (a.sha256||"")+'</span></td><td class="num">'+mb+' \\u0645.\\u0628</td>'+
        '<td><a class="btn" href="'+base+a.file+'">\\u0646\\u0632\\u0651\\u0650\\u0644</a></td></tr>';
    }).join("");
    host.innerHTML='<div class="table-wrap"><table><thead><tr>'+
      '<th>\\u0627\\u0644\\u0645\\u0646\\u0635\\u0651\\u0629 \\u0648 SHA-256</th>'+
      '<th>\\u0627\\u0644\\u062d\\u062c\\u0645</th><th></th></tr></thead><tbody>'+
      rows+'</tbody></table></div>';
    if(m.version){
      document.getElementById("ver").textContent=
        "\\u0628\\u0646\\u0627\\u0621\\u064f \\u0627\\u0644\\u0645\\u0639\\u0627\\u064a\\u0646\\u0629 "+
        m.version+(m.date?" \\u00b7 "+m.date:"");
    }
  }
  render(baked);
  fetch("../../dl/preview-alif/releases.json",{cache:"no-store"})
    .then(function(r){return r.ok?r.json():null;})
    .then(function(m){ if(m) render(m); })
    .catch(function(){});
})();
"""

    ext = baked.get("alif_extension", {})
    rt = baked.get("alif_runtime", {})
    body = """<div class="wrap">
<header>
  <span class="tag">بناءُ معاينةٍ مؤقّت</span>
  <h1>محراب، ولغةُ ألف تعمل فيه من أوّل تشغيل</h1>
  <p class="lead">نزِّل التطبيق وافتح ملفَّ ألف. لا تثبيتَ إضافةٍ ولا إعدادَ سوق —
  إضافةُ لغة ألف مشحونةٌ داخل هذا البناء.</p>
  <p class="dim" id="ver"></p>
</header>

<section>
  <h2>التنزيل</h2>
  <div id="dl"><p class="empty">لم يُرفَع بناءُ معاينةٍ بعد.</p></div>
  <p class="dim">قارِن بصمةَ SHA-256 بما نزّلتَه قبل التنصيب:
  <code>sha256sum</code> على لينكس وmacOS، و<code>Get-FileHash -Algorithm SHA256</code>
  على ويندوز. والحزمُ <b>غيرُ موقّعة</b> بعد، فيتوقّع ويندوز وmacOS تحذيرًا عند أوّل تشغيل.</p>
</section>

<section>
  <h2>ما يعمل فورًا، وما يحتاج ألفَ نفسَها</h2>
  <p>الإضافةُ تحلّل ألفَ محلّيًّا، فأكثرُها لا يحتاج شيئًا خارجَ التطبيق:</p>
  <ul>
    <li class="yes">إبرازُ الصياغة، ومقتطفاتُ البُنى، وسمةُ أيقونات ألف</li>
    <li class="yes">فحصٌ ساكنٌ فوريّ: بنيةُ الكتل، وتوازنُ الأقواس، والنصوصُ غير المغلقة</li>
    <li class="yes">إكمالٌ يطابق دون تفريقٍ بين صور الهمزة والألف، ويتجاهل التشكيل</li>
    <li class="yes">فهرسةُ رموز المشروع: الذهابُ إلى التعريف والبحثُ عبر الملفّات</li>
    <li class="yes">تنبيهٌ على كلمات ألف 5 المتغيّرة (مثل <code>لاجل</code> ← <code>لكل</code>) بإصلاحٍ سريع</li>
  </ul>
  <p>وواحدٌ يحتاج ما هو خارجَ محراب:</p>
  <ul>
    <li class="yes"><b>تشغيلُ البرنامج</b> — مفسّرُ ألف مشحونٌ في هذا البناء، فيعمل
    <code>تشغيل ملفّ ألف</code> بلا تنزيلٍ ولا إعداد. ومن أراد مفسّرَه فالإعدادُ
    <code>alif.executablePath</code> أسبقُ من المشحون، وكذلك ثنائيٌّ في مشروعك.</li>
    <li><b>خادمُ ألف اللغويّ الخارجيّ</b> مطفأٌ افتراضيًّا
    (<code>alif.lsp.enabled</code>) — والمحلّلُ المدمج يعمل بدونه.</li>
  </ul>
</section>

<section class="note">
  <h2>ما هذه الصفحة، وما ليست</h2>
  <p><b>بناءُ تجريبٍ مؤقّت، لا إصدارٌ من إصدارات محراب.</b> لا تُذكر هذه الصفحةُ في
  موقع محراب ولا يُوصَل إليها من ملاحته، وقد تُطوى متى انتهى غرضُها.</p>
  <p>ومحرابٌ منصّةٌ تستضيف اللغات: الوضعُ الطبيعيُّ أن تُثبَّت لغةُ ألف من سوق
  Open VSX المفتوح كأيّ إضافة، لا أن تُشحن داخل التطبيق. وهذا البناءُ يتخطّى تلك
  الخطوةَ لغرضٍ واحد: أن تجرّبوا محرابًا بلا مقدّمات.</p>
</section>

<footer>
  <p>إضافةُ لغة ألف من <a href="{src}">{src_short}</a> بترخيص MIT، مأخوذةٌ في هذا
  البناء من الإصدار {ver} وبصمتُه مثبَّتةٌ في شفرةِ بنائنا:
  <span class="sha">{sha}</span></p>
  <p>ومفسّرُ ألف من <a href="{rt_src}">{rt_src_short}</a>، الإصدار {rt_ver}،
  مشحونٌ في <code>bin/</code> داخل الإضافة وبصمةُ حزمةِ كلِّ منصّةٍ مثبَّتةٌ كذلك.</p>
  <p>محراب — منصّةُ تطويرٍ عربيّةٌ مفتوحةُ المصدر (MIT) ·
  <a href="https://github.com/almihrab/mihrab">المستودع</a></p>
</footer>
</div>""".format(
        src=html.escape(ext.get("source", "")),
        src_short=html.escape(ext.get("source", "").replace("https://github.com/", "")),
        ver=html.escape(ext.get("version", "")),
        sha=html.escape(ext.get("sha256", "")),
        rt_src=html.escape(rt.get("source", "")),
        rt_src_short=html.escape(rt.get("source", "").replace("https://github.com/", "")),
        rt_ver=html.escape(rt.get("version", "")))

    return (
        "<!doctype html>"
        '<html lang="ar" dir="rtl"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex">'
        "<title>محراب × لغة ألف — بناءُ معاينة</title>"
        "<style>%s</style></head><body>" % css
        + body
        + data_island("baked", baked)
        + data_island("labels", labels)
        + "<script>%s</script></body></html>" % js)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


if __name__ == "__main__":
    sys.exit(main())
