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
import shutil
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
# شاهدُ البناء: وجودُه في `OUT` هو ما يأذن للبناء التالي بمحو المجلّد (انظر `main`).
BUILD_MARK = ".mihrab-site-build"

UPSTREAM_DOCS = "https://github.com/microsoft/vscode-docs/blob/main/"

# ═════════════════════ البيانات ═════════════════════
# النصُّ التسويقيّ ومصفوفةُ المنصّات بياناتٌ لا كود: تغييرُ جملةٍ في الصفحة الأولى
# يجب ألّا يمرَّ بمراجعةِ بايثون.
with open(os.path.join(DATA, "site.json"), encoding="utf-8") as _f:
    SITE = json.load(_f)
with open(os.path.join(DATA, "releases.json"), encoding="utf-8") as _f:
    RELEASES = json.load(_f)

# ⚠️ كلُّ المسارات نسبيّة (`.` و`..`) عمدًا: المخرَجُ نفسُه يُخدَم من
# `mihrab.dev/` ومن `almihrab.github.io/mihrab/` بلا إعادةِ بناء.
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

        # ── اقتباسٌ ⇐ لافتةُ قيد ──
        # كلُّ استعمالٍ لـ`>` في محتوانا واحد: «هذا لا يعمل في نسخة المتصفّح».
        # وكان الراسمُ لا يعرفه أصلًا، فيمرّ **صامتًا** — على خلاف عهد هذا
        # الملفّ نفسِه («وكلُّ ما لا تدعمه هذه الدالّة يُرفَض صراحةً») — فتظهر
        # في سبع صفحاتٍ فقرةٌ تبدأ بـ«‏&gt; » ثمّ تلتحم بالفقرة التي تليها،
        # فيقرأ المبتدئُ علامةً غريبةً وجملتين ملتصقتين في أوّل سطرٍ يراه.
        if stripped.startswith(">"):
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^>\s?", "", lines[i].strip()))
                i += 1
            out.append('<blockquote class="note">%s</blockquote>'
                       % ("<p>%s</p>" % inline(" ".join(q for q in quote if q))))
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
                r"^(#{1,3}\s|```|\||[-*]\s|\d+\.\s|>)", lines[i].strip()):
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
        ("https://sad-lang.org/", "لغةُ ص"),
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
               with_search=True, extra_js=(), with_nav=False):
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
    return page_shell(
        # ‏بلا « — محراب»: `page_shell` يلحقها، وكانت الترويسةُ تقرأ
        # «لا شيءَ هنا — محراب — محراب».
        "لا شيءَ هنا", body, SITE["canonical"].rstrip("/"),
        "الصفحةُ غير موجودة. محرابُ المتصفّح انتقل إلى أصلٍ خاصٍّ به.",
        canon_path="404.html", with_search=False)


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
        # فيعمل الرابطُ على `mihrab.dev/` بالمصادفة — ويكسر على المرآة
        # `almihrab.github.io/mihrab/` حيث يقفز `..` فوق اسمِ المستودع.
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
        # **أثقلُ** طريقٍ إلى التجربة (‏١٩٤ م.ب) بينما أخفُّها (‏٥ م.ب في
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
        # ── وشريطُ الانتقال **بعد التعريف لا قبله** ──
        # موضعُه الأوّل كان رأسَ الصفحة، فكانت أوّلُ جملةٍ يقرؤها زائرٌ جديد
        # «محرابٌ استقلّ بنطاقه»: خبرٌ عن انتقالٍ لا يعرف أنّه وقع، عن نطاقٍ لم
        # يزره قطّ — قبل الشعار والاسم والوصف. وصاحبُ الإشارة المرجعيّة الذي
        # كُتب الشريطُ لأجله **أقلُّ** بكثيرٍ من الزائر الجديد في موقعٍ يُطلَق
        # اليوم، فكان الثمنُ يدفعه الأغلبُ لينتفع الأقلّ.
        #
        # وهنا يبقى فوق الطيّة — أوّلَ ما يقع عليه بصرُ الباحث عن المحرِّر بعد
        # أن يتأكّد أنّه في المكان الصحيح — ولا يسبق التعريفَ بالمنتَج.
        # وعلى `/docs/` و`/download/` يبقى في الرأس: من بلغهما يعرف ما محراب.
        + MOVE_NOTE
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
# وقد وقع الانتقالُ الذي كان الشريطُ يَعِد به، فانقلب معناه: صار يُقدَّم **من**
# الوجهة نفسِها ويَعِد بالوصول إليها، ويرتبط بالصفحة التي عليها القارئ. فيقول الآنَ
# ما صار صحيحًا: أنت في الدار، والمحرِّرُ جارُها.
MOVE_NOTE = (
    '<aside class="move-note">'
    '<b>محرابٌ استقلّ بنطاقه.</b> التوثيقُ والثنائيّاتُ هنا على '
    '<code>mihrab.dev</code>، ومحرابُ المتصفّح على '
    '<a href="https://app.mihrab.dev">app.mihrab.dev</a>.'
    '</aside>'
)
# وجملةُ «`docs.mihrab.dev` و`dl.mihrab.dev` يبقيان يعملان» نُزِعت من الشريط
# وانتقلت إلى صفحة ‎404‎: هي رسالةٌ **لمن يحمل الرابطَ القديم**، ومن يقرؤها أوّلَ
# مرّةٍ يُدخَل في رأسه أربعةُ نطاقاتٍ حيث يكفيه اثنان. والذي يحتاجها لا يمرّ على
# `/docs/`؛ يهبط حيث لا شيءَ — وهناك تنتظره.


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
    mb = n / 1048576.0
    return ("%.2f غيغابايت" % (mb / 1024)) if mb >= 1024 else ("%d ميغابايت" % round(mb))


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
        + MOVE_NOTE +
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
        # ما يراه مستخدمُ ماك بعد فكّ ‎١٧٥‎ ميغابايت هو «محراب تالف ولا يمكن فتحه.
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
        '<button class="icon-btn print-btn" type="button" onclick="window.print()">اطبع البطاقة</button>'
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
# ── نطاقا المحارف ──
# الأوجهُ المورَّدةُ **مقلَّمة**: ملفُّ العربيّة لا يحمل حرفًا لاتينيًّا وبالعكس.
# وبلا `unicode-range` يصير الوجهان المتشاركان في الاسم والوزن **متنازعَين**:
# المتصفّحُ يأخذ الأخيرَ ويهمل الأوّلَ تمامًا (ليس سقوطًا بين وجهَي العائلة
# الواحدة — السقوطُ يكون إلى العائلة التالية في السلسلة). فيُعرَض نصفُ الموقع
# بخطِّ النظام ونصفُه بالخطّ المُورَّد، وهو **أسوأُ من عدم التوريد**: قبله كان
# الموقعُ متّسقًا بخطٍّ واحدٍ غيرِ مقصود، وبعده يصير مختلطًا في السطر الواحد.
#
# والمدى يقول للمتصفّح: «هذا الوجهُ لهذه المحارف» — فيُحمَّل ملفُّ العربيّة
# لصفحةٍ عربيّة، وملفُّ اللاتينيّة عند أوّل رقمٍ أو `mihrab.dev`. وذلك مكسبٌ
# ثانٍ: من لا يرى لاتينيًّا لا ينزّل ملفَّه.
# ⚠️ **ولا تداخُلَ بين المدَيَين.** مقطعٌ يطالب به الوجهان في العائلة والوزن
# نفسِهما يفوز فيه الأخيرُ إعلانًا — فكانت `U+200C-200E` و`U+2010-2011` و`U+204F`
# و`U+FEFF` مُسنَدةً فعليًّا إلى الملفّ اللاتينيّ، ومنها **`U+204F` وهي فاصلةٌ
# منقوطةٌ معكوسة** تُستعمل في النصوص السامّية. وأثرُها اليومَ معدومٌ (لا يرد منها في المخرَج إلا `U+200E`
# مرّتين، وهو محرفُ اتّجاهٍ عديمُ الشكل) — لكنّه لغمٌ لا عطبٌ واقع. فنُزِعت
# المقاطعُ المشتركةُ من `_UR_LA` وبقيت للعربيّة حيث تنتمي.
_UR_AR = ("U+0600-06FF,U+0750-077F,U+0870-088E,U+0890-0891,U+0898-08E1,"
          "U+08E3-08FF,U+200C-200E,U+2010-2011,U+204F,U+2E41,U+FB50-FDFF,"
          "U+FE70-FEFF,U+102E0-102FB,U+10E60-10E7E,U+1EE00-1EEBB")
_UR_LA = ("U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,"
          "U+0304,U+0308,U+0329,U+2000-200B,U+200F,U+2012-204E,"
          "U+2050-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,"
          "U+FFFD")

# ── واسمُ عائلةٍ ثانٍ للملفَّين العربيَّين، لسلسلة أحاديّ المسافة ──
# `IBM Plex Mono` و`Cascadia Mono` و`Consolas` بلا محارفَ عربيّة، فكان العربيُّ
# في كتل الشيفرة يسقط إلى `Courier New`: خطٌّ ذو أذنابٍ على متنٍ سنسريف — سطرٌ
# متّسقُ العرض **غيرُ متّسق الأسرة**، في `.محراب/settings.json` وفي
# `اطبع "السلام عليكم"`. والعلاجُ بصفرِ بايتٍ إضافيّ: **الملفّان العربيّان
# نفسُهما** تحت اسمٍ ثانٍ يقف أوّلَ `--font-mono`. والمتصفّحُ لا ينزّل الملفَّ
# مرّتين: التخزينُ على العنوان لا على اسم العائلة.
#
# ⚠️ ومداه **أضيقُ** من `_UR_AR` عمدًا: كتلُ الخطّ العربيّ وحدَها. فلا يمرّ به
# حرفٌ لاتينيٌّ ولا رقمٌ لاتينيٌّ ولا مسافةٌ ولا واصلة — وكلُّ ما يُحاذى رأسيًّا في
# كتلة شيفرةٍ يبقى في الخطّ أحاديّ المسافة، فالمحاذاةُ لا تُمَسّ رياضيًّا. ولذلك
# سقطت منه `U+200C-200E` و`U+2010-2011` و`U+204F` و`U+2E41`: الأُولى عديمةُ
# الشكل فلا فرق، والواصلاتُ والفاصلتان المعكوستان (‏`204F` و`2E41`) لها عرضٌ
# يُحاذى فتبقى لأحاديّ المسافة. ويحرس الضيقَ [FNT-01] على `fonts.css` المبنيّة
# لا على هذا المتغيّر. (وما لا يسقط: الأرقامُ العربيّة `٠–٩` — انظر لغمَها
# في `assets/fonts/README.md`.)
_UR_AR_MONO = ("U+0600-06FF,U+0750-077F,U+0870-088E,U+0890-0891,U+0898-08E1,"
               "U+08E3-08FF,U+FB50-FDFF,U+FE70-FEFF,U+102E0-102FB,"
               "U+10E60-10E7E,U+1EE00-1EEBB")
MONO_AR_FAMILY = "Mihrab Code Arabic"

FONT_FACES = [
    ("plex-arabic-400.woff2", "IBM Plex Sans Arabic", 400, _UR_AR),
    ("plex-arabic-600.woff2", "IBM Plex Sans Arabic", 600, _UR_AR),
    ("plex-latin-400.woff2", "IBM Plex Sans Arabic", 400, _UR_LA),
    ("plex-latin-600.woff2", "IBM Plex Sans Arabic", 600, _UR_LA),
    ("plex-arabic-400.woff2", MONO_AR_FAMILY, 400, _UR_AR_MONO),
    ("plex-arabic-600.woff2", MONO_AR_FAMILY, 600, _UR_AR_MONO),
]
# الملفّاتُ الفريدة: وجهان يتشاركان ملفًّا يُنسَخ مرّةً ويُعَدّ مرّة.
FONT_FILES = []
for _fn, _fam, _wt, _ur in FONT_FACES:
    if _fn not in FONT_FILES:
        FONT_FILES.append(_fn)


def _faces_word(n):
    """تمييزُ العدد: ‏3–10 جمعٌ مجرور، وما فوقه مفردٌ منصوب — كما في `hitsWord`."""
    if n == 1:
        return "وجهٍ واحد"
    if n == 2:
        return "وجهَين"
    return "%d أوجه" % n if n <= 10 else "%d وجهًا" % n


def _files_word(n, total):
    """‏«4/4 ملفًّا» لحنٌ بالقاعدة نفسِها التي تُصحَّح بها الأوجهُ في السطر ذاته:
    ‏3–10 تمييزُها جمعٌ مجرور («4 ملفّات»)، لا مفردٌ منصوب."""
    if n == total:
        return ("الملفُّ الواحد" if total == 1 else
                "الملفّان" if total == 2 else
                "الملفّاتُ الـ%d كلُّها" % total if total <= 10 else
                "الـ%d ملفًّا كلُّها" % total)
    return "%d من %d %s" % (n, total,
                             "ملفّات" if total <= 10 else "ملفًّا")


def write_fonts_css(dst_assets):
    """يولّد `fonts.css` من الملفّات **الموجودة فعلًا** وينسخها.

    ولا يكتب `@font-face` لملفٍّ غائب: وجهٌ يشير إلى ملفٍّ غير موجود لا يفشل بصوت —
    بل يُطلق 404 في كلّ فتحةِ صفحة ثمّ يسقط صامتًا إلى خطٍّ آخر، فيبدو الموقعُ سليمًا
    وهو يعرض خطًّا لم نصمّم عليه. والسقوطُ الصريح في سلسلة `--font-ar` أشرفُ من ذلك.
    """
    src_dir = os.path.join(ASSETS, "fonts")
    faces, present = [], []
    for fn, family, weight, urange in FONT_FACES:
        if os.path.isfile(os.path.join(src_dir, fn)):
            if fn not in present:
                present.append(fn)
            faces.append(
                '@font-face{font-family:"%s";src:url("fonts/%s") format("woff2");'
                'font-weight:%d;font-display:swap;unicode-range:%s}'
                % (family, fn, weight, urange))

    if present:
        dst_dir = os.path.join(dst_assets, "fonts")
        os.makedirs(dst_dir, exist_ok=True)
        for fn in present:
            with open(os.path.join(src_dir, fn), "rb") as f_in, \
                    open(os.path.join(dst_dir, fn), "wb") as f_out:
                f_out.write(f_in.read())
        # ── ونصُّ الرخصة **يسافر مع الملفّات** ──
        # ‏OFL‑1.1 البندُ ٢ يشترط مصاحبةَ الإشعار والرخصة لكلّ نسخةٍ يُعاد
        # توزيعُها، **والنشرُ على الويب إعادةُ توزيع**. فلا يكفي إيداعُ `OFL.txt`
        # في المصدر: حلقةُ `main()` العامّةُ تتخطّى المجلّدات، وهذه الدالّةُ تنسخ
        # ملفّاتِ `FONT_FACES` وحدَها — فكان الخطُّ يصل الزائرَ عاريًا من إشعاره.
        # والقاعدةُ مكتوبةٌ في `.gitignore` («إلزامٌ قانونيٌّ لا نظافةٌ اختياريّة»)
        # ومطبَّقةٌ على `patches/fonts/` منذ البداية، وغابت عن هذا المجلّد وحدَه.
        for _doc in ("OFL.txt", "README.md"):
            _src = os.path.join(src_dir, _doc)
            if os.path.isfile(_src):
                with open(_src, "rb") as f_in,                         open(os.path.join(dst_dir, _doc), "wb") as f_out:
                    f_out.write(f_in.read())
        assert os.path.isfile(os.path.join(dst_dir, "OFL.txt")), (
            "أوجهٌ مورَّدةٌ بلا `site/assets/fonts/OFL.txt` — إرفاقُ الرخصة شرطٌ "
            "قانونيٌّ لإعادة التوزيع، والنشرُ إعادةُ توزيع")

    header = ('@charset "UTF-8";\n'
              "/* مولَّد من build.py — لا تحرّره. %s مورَّدة، في %s. */\n"
              % (_files_word(len(present), len(FONT_FILES)), _faces_word(len(faces))))
    with open(os.path.join(dst_assets, "fonts.css"), "w", encoding="utf-8", newline="\n") as f:
        f.write(header + "\n".join(faces) + "\n")

    # ⚠️ ولا يُقال «يسقط إلى Noto Sans Arabic»: ‏Noto Sans Arabic **غيرُ منصَّبٍ
    #    على ويندوز**، وأكثرُ جمهورِ محرابٍ على ويندوز — فالسقوطُ الفعليُّ هناك
    #    إلى `Segoe UI`. والرسالةُ التي تطمئن المطوّرَ بأنّ البديلَ هو ما اختاره
    #    تُخفي أنّ الأغلبيّةَ ترى خطًّا ثالثًا لم يُصمَّم عليه شيء.
    #
    # **والنقصُ الجزئيُّ أسوأُ من التامّ**: وجهٌ عربيٌّ بلا نظيرِه اللاتينيِّ يجعل
    # السطرَ الواحدَ بخطَّين — ولذلك يُسمّى الناقصُ بالاسم لا بالعدد.
    if len(present) != len(FONT_FILES):
        missing = [fn for fn in FONT_FILES if fn not in present]
        print("  ⚠️  %d/%d ملفِّ خطٍّ مورَّد — ينقص: %s. "
              "وما ينقص يُعرَض بخطّ النظام (‏Segoe UI على ويندوز)، فيصير السطرُ "
              "المختلَطُ بخطَّين. ضَع woff2 في site/assets/fonts/."
              % (len(present), len(FONT_FILES), "، ".join(missing)))
    else:
        print("  ✅ %s مورَّدة في %s — الموقعُ يُعرَض كما صُمِّم."
              % (_files_word(len(present), len(FONT_FILES)), _faces_word(len(faces))))


# ═════════════════════ البناء ═════════════════════
def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


_GLOSSARY_CACHE = None


def glossary_aliases(text):
    """بدائلُ المسرد الممنوعةُ لكلّ مصطلحٍ معتمَدٍ ورد في النصّ — لفهرس البحث وحدَه.

    والكلمةُ المفردةُ المنتهيةُ بتاءٍ مربوطة تُلحَق بجمعها السالم (‏«الإضافة» ⇐
    «الإضافات»): ما على الشاشة جمعٌ في الغالب (عنوانُ الشريط الجانبيّ)، والبحثُ
    مطابقةُ نصٍّ لا صرف. ولا يُجمَع المركَّب ولا ما لا ينتهي بالتاء."""
    global _GLOSSARY_CACHE
    if _GLOSSARY_CACHE is None:
        gpath = os.path.join(DATA, "glossary.json")
        terms = []
        if os.path.isfile(gpath):
            with open(gpath, encoding="utf-8") as f:
                terms = json.load(f).get("terms", [])
        _GLOSSARY_CACHE = [(t["ar"], t.get("forbidden", [])) for t in terms if t.get("forbidden")]
    out = []
    for ar, forbidden in _GLOSSARY_CACHE:
        if ar not in text:
            continue
        for w in forbidden:
            if w not in out:
                out.append(w)
            if " " not in w and w.endswith("ة"):
                plural = w[:-1] + "ات"
                if plural not in out:
                    out.append(plural)
    return " ".join(out)


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
        # ⚠️ **النصُّ كاملًا لا ‎1200‎ محرفًا.** كان القطعُ يُسقط ما بعد ‎1200‎ من كلّ صفحة:
        # تسعٌ من ثلاثَ عشرةَ صفحةً أطولُ من ذلك (‏`folders` ‎2103‎، و`keyboard` ‎6107‎ —
        # فجدولُ الاختصارات كلُّه، ‎80%‎ من الصفحة التي بُني الموقعُ لأجلها، لم يكن في
        # بحث الموقع أصلًا). والفهرسُ كاملًا ‎24‎ ألفَ محرف ≈ ‎43‎ كيلوبايت، يُجلَب مرّةً
        # عند أوّل تبئير (قِيس في الجولة الحاديةَ عشرة).
        # و`alt` بدائلُ المسرد الممنوعة: حزمةُ اللغة المورَّدة تعرض على الشاشة «الإضافات»
        # والمسردُ يعتمد «الامتداد» (‏`_gap` في `glossary.json`) — فمن قرأ الكلمةَ في
        # المحرِّر وكتبها هنا كان يقرأ «لا نتائج» (قِيس: «الإضافة» صفرٌ، «الامتداد» ‎4‎).
        # البدائلُ لا تظهر في المتن ولا في النتائج؛ يقرؤها البحثُ وحدَه، فلا تُناقض المسرد.
        page_text = strip_tags(body_html)
        index.append({
            "url": slug + "/",
            "title": SLUG_TITLE[slug],
            "section": SLUG_SECTION[slug],
            "text": page_text,
            "alt": glossary_aliases(SLUG_TITLE[slug] + " " + page_text),
        })

    if check_only:
        print("✅ %d صفحة سليمة." % len(pages))
        return 0

    # ── والمخرَجُ يبدأ فارغًا: ما لم يُبنَ هذه المرّة لا يُنشَر ──
    # `deploy_site.sh` يحزم `site/public/` كلَّه ويَعِد: «ما لم يُبنَ هذه المرّة
    # ليس موجودًا هناك». وكان الوعدُ كاذبًا: البناءُ يكتب فوق الموجود ولا يمحو
    # شيئًا، فصفحةٌ حُذفت من `content/` — أو أصلٌ أُعيدت تسميتُه — يبقى في
    # `public/` ويُنشَر إلى الأبد، بلا خطأٍ في أيّ طبقة.
    #
    # ⚠️ والمحوُ **مشروطٌ بشاهد**: ملفُّ `BUILD_MARK` الذي يكتبه هذا البناءُ نفسُه.
    # مجلّدٌ غيرُ فارغٍ بلا شاهدٍ ليس مخرَجًا سابقًا بل شيءٌ لا نعرفه —
    # `MIHRAB_SITE_OUT` قد يشير إلى أيّ مكان — فيُرفَض بصوتٍ ولا يُمحى.
    # ويحرس الوجهين [OUT-01] ببناءين حقيقيَّين في مجلّدٍ مؤقّت.
    if os.path.isdir(OUT):
        if os.listdir(OUT) and not os.path.isfile(os.path.join(OUT, BUILD_MARK)):
            raise SystemExit(
                "مجلّدُ المخرَج غيرُ فارغٍ وليس من بناءٍ سابق (لا %s فيه) — لن يُمحى: %s"
                % (BUILD_MARK, OUT))
        # **المحتوى لا المجلّد**: `rmtree(OUT)` كان يمحو المجلّدَ نفسَه، فأيُّ
        # مقبضٍ مفتوحٍ عليه (خادمُ معاينةٍ بمجلّد عملٍ داخله، مستكشفُ ملفّات)
        # يُفشِل `rmdir` الأخيرَ على ويندوز بعد أن مُحي المحتوى — فيبقى `public/`
        # فارغًا **بلا شاهد** ويرفض البناءُ التالي مخرَجَه هو. قِيس فعلًا.
        # وثلاثةُ أشياءَ قِيست على ويندوز/بايثون 3.12:
        #   · **الشاهدُ يُمحى آخرًا**: `listdir` يضعه أوّلًا، فأيُّ فشلٍ في المنتصف
        #     كان يترك `public/` غيرَ فارغٍ **بلا شاهد** — والبناءُ التالي يرفض
        #     مخرَجَه هو حتّى يتدخّل أحد.
        #   · **الوصلةُ (‏junction) ليست `islink`** على ويندوز، و`rmtree` يرفضها
        #     بصوت (‏3.12) لكنّ الأمانَ لا يُترَك لرفض المكتبة: تُفكّ بـ`rmdir` من
        #     غير أن يُمَسّ هدفُها.
        #   · **ملفٌّ للقراءة فقط** يُفشِل `os.remove` بـ`PermissionError`؛ يُرفَع
        #     عنه البتُّ ويُعاد — فهو بقايا بناءٍ سابقٍ لا ملكيّةَ لأحدٍ فيه.
        def _rm_readonly(fn, path, _exc):
            os.chmod(path, 0o666)
            fn(path)

        def _wipe(path):
            if os.path.islink(path) or getattr(os.path, "isjunction", lambda _p: False)(path):
                # `unlink` يفكّ الوصلةَ الثلاثةَ (ملفٍّ، مجلّدٍ، junction) على ويندوز وهو
                # العمليّةُ القياسيّةُ على POSIX — بينما `rmdir` على وصلةِ مجلّدٍ يردّ
                # `ENOTDIR` في لينكس فيسقط `deploy_site.sh` و`docs-pages.yml` عند أوّل
                # وصلة (قياسُ أيمليا). والهدفُ لا يُمَسّ في الحالتين.
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path, onexc=_rm_readonly)
            else:
                try:
                    os.remove(path)
                except PermissionError:
                    os.chmod(path, 0o666)
                    os.remove(path)

        for _e in os.listdir(OUT):
            if _e != BUILD_MARK:
                _wipe(os.path.join(OUT, _e))
        _mk = os.path.join(OUT, BUILD_MARK)
        if os.path.exists(_mk):
            os.remove(_mk)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, BUILD_MARK), "w", encoding="utf-8", newline="\n") as f:
        f.write("مولَّد من site/build.py — وجودُه يأذن للبناء التالي بمحو هذا المجلّد.\n")
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
                          active="docs", canon_path=slug + "/", with_nav=True)
        d = os.path.join(OUT, slug)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(page)

    # ── مركزُ التوثيق: `/docs/` ──
    # الجذرُ صار للمنتج، والتوثيقُ نزل درجةً. ومسارُ كلِّ صفحةِ توثيق **لم يتغيّر**
    # (`/start/` ‏· `/keyboard/`…) عمدًا: تلك المسارات مخبوزةٌ في product.json وفي
    # قائمة «مساعدة» داخل المحرّرات المشحونة سلفًا، ونقلُها يكسرها بلا فائدة.
    docs_body = (
        '<main class="home">' + MOVE_NOTE + (MARK_SVG % "mark-lg")
        + "<h1>توثيق محراب</h1>"
        + '<p class="tagline">للمِحرابِ اتّجاه، ولكودِك وِجهة.</p>'
        + '<p class="tagline-sub">مكانٌ صافٍ تكتب فيه بالعربيّة كما تُفكّر بها.</p>'
        # ── لا `autofocus` ──
        # كان يخطف البؤرةَ إلى حقلٍ **لا يعمل بلا جافاسكربت**، فيصير أوّلَ ما
        # يقع عليه قارئُ الشاشة ونقطةَ انطلاق التنقّل بلوحة المفاتيح: وعدٌ
        # يُقدَّم قبل أن يكون قابلًا للوفاء. وعلى الجوّال يرفع لوحةَ المفاتيح
        # فيحجب نصفَ الشاشة قبل أن يقرأ الزائرُ سطرًا. والفهرسُ الكامل أدناه
        # هو الطريقُ الذي يعمل دائمًا، فلا حاجةَ إلى خطفِ البؤرة أصلًا.
        # ⚠️ لا `id` هنا: صفحةُ `/docs/` تحمل صندوقَي بحثٍ — واحدًا في الترويسة
        #    وهذا — وكانا يتقاسمان `id="site-search"` و`id="search-results"`.
        #    و`getElementById` يردّ **الأوّلَ** أي حقلَ الترويسة، فالحقلُ الأوسطُ
        #    الضخم — أبرزُ عنصرٍ تفاعليٍّ في الصفحة — يبتلع الكتابةَ ولا يردّ أبدًا.
        #    و`docs.js` صار يربط كلَّ `.search-box` بنتائجه **المجاورة**.
        + '<div class="home-search search-box">'
          '<input type="search" class="search-input" '
          'placeholder="ابحث في التوثيق…" aria-label="بحث" '
          'role="combobox" aria-expanded="false" aria-autocomplete="list" '
          'aria-controls="home-search-results">'
          '<div class="search-results" id="home-search-results" hidden></div>'
          '<div class="sr-only search-status" role="status" aria-live="polite">'
          '</div></div>'
        # ── سطرٌ واحدٌ بدل شبكةِ بطاقات ──
        # كانت ثلاثُ بطاقاتٍ هي الطريقَ الوحيدَ إلى التوثيق قبل أن يُضاف الفهرسُ
        # أدناه. وبعده صارت **تكرارًا مزخرفًا لأوّل ثلاثة سطورٍ ممّا تحتها**:
        # «البدء في دقيقة» يظهر ثلاثَ مرّاتٍ في شاشةٍ واحدة — بطاقةً، وسطرًا في
        # عمود «ابدأ»، وسطرًا في تذييل «ابدأ». فيُحتفَظ بالدعوة ويُلغى التكرار،
        # وتُكسَب شاشةٌ كاملة.
        + '<p class="docs-lede">جديدٌ على محراب؟ ابدأ من '
          '<a href="../start/">البدء في دقيقة</a>.</p>'
        # ── وسطرُ وصفٍ تحت كلّ قسم، لا تحت كلّ رابط ──
        # الفهرسُ ثلاثةَ عشرَ **عنوانًا عاريًا**، وقد حلّ محلّ بطاقاتٍ كانت تحمل
        # وصفًا. ومن لم يستعمل محرّرًا حديثًا لا يعرف ما «الإكمال والتلميحات»
        # ولا «مصادر التحكّم». وصفٌ لكلّ رابطٍ يعيد ازدحامَ البطاقات، ووصفٌ
        # لكلّ **قسمٍ** يكفي: ثلاثةُ أسطرٍ تُعطي الخريطةَ بلا ضجيج.
        + '<div class="docs-index">'
        + "".join(
            '<section><h2>%s</h2><p class="sec-note">%s</p><ul>%s</ul></section>'
            % (html.escape(section), html.escape(DOCS_SECTION_NOTE.get(section, "")),
               "".join('<li><a href="../%s/">%s</a></li>' % (slug, html.escape(title))
                       for slug, title in items))
            for section, items in NAV)
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
    write(os.path.join(OUT, "404.html"), build_not_found())
    write(os.path.join(OUT, "download", "index.html"), build_download())
    write(os.path.join(OUT, "preview", "alif", "index.html"), build_alif_preview())
    write(os.path.join(OUT, "assets", "preview-alif.js"), _ALIF_JS)

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
# سكربتُ صفحة المعاينة، على مستوى الوحدة ليُكتَب ملفًّا مجاورًا:
# سياسةُ `script-src 'self'` تحجب الداخليَّ، والصفحةُ تُصيَّر بلا جدولِ تنزيلٍ بصمت.
_ALIF_JS = """(function(){
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
font-family:"IBM Plex Sans Arabic","Noto Sans Arabic","Segoe UI",Tahoma,system-ui,sans-serif;
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
code,.sha{font-family:"Mihrab Code Arabic",ui-monospace,"Cascadia Mono",Consolas,"Courier New",monospace;
font-size:.82rem;word-break:break-all;color:var(--dim);direction:ltr;
display:inline-block;unicode-bidi:isolate}
.btn{display:inline-block;background:var(--accent);color:var(--accent-fg);
text-decoration:none;padding:.45rem 1.1rem;border-radius:.45rem;font-size:.95rem;
white-space:nowrap}
.btn:hover{filter:brightness(1.08)}
@media(pointer:coarse){.btn{min-height:44px;display:inline-flex;align-items:center}}
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
        # الصفحةُ خارج `page_shell` فلا تَرِث ورقةَ الخطوط — وكانت تُعرَض بخطّ
        # النظام وحدَها من بين صفحات الموقع، وهي التي يصلها زائرٌ آتٍ من صفحةٍ
        # بالخطّ المورَّد. والمسارُ نسبيٌّ كما في `preview-alif.js` أسفلَه.
        '<link rel="stylesheet" href="../../assets/fonts.css">'
        "<style>%s</style></head><body>" % css
        + body
        + data_island("baked", baked)
        + data_island("labels", labels)
        # ⛔ لا `<script>` داخليًّا: سياسةُ الجذر `script-src 'self'` بلا `'unsafe-inline'`
        #    تحجبه، فتُصيَّر الصفحةُ ‎200‎ بعنوانٍ ونصٍّ **وبلا جدول تنزيلٍ البتّة** — بلا
        #    رسالةِ خطأٍ ولا شيءٍ أحمر. قِيس على الصفحة المنشورة. والعلاجُ ما فُعل
        #    بسكربت الإقلاع [WEB-09]: ملفٌّ مجاور.
        + '<script src="../../assets/preview-alif.js"></script></body></html>')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


if __name__ == "__main__":
    sys.exit(main())
