# -*- coding: utf-8 -*-
"""النصّ: Markdown المضبوط (ومعه اختصاراتُ `{{…}}` في المتن)، والترويسة، ونصُّ فهرس البحث
وبدائلُ المسرد."""
import html
import json
import os
import re

from .data import DATA

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


# ═════════════════════ فهرسُ البحث: النصُّ المجرَّد وبدائلُ المسرد ═════════════════════
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
