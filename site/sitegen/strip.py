# -*- coding: utf-8 -*-
"""تجريدُ تعليقات CSS وقتَ البناء — المصدرُ يبقى بتعليله، والزائرُ لا يُنزِّله.

التعليقاتُ ‎66–71%‎ من بايتات أوراق CSS (قِيس 2026-11-25)، وكلُّها سجلُّ قراراتٍ للمطوّر لا يحتاجه
المتصفّح. فتُنزَع هنا عند النسخ إلى `public/assets`، ويبقى المصدرُ كما هو.

**ماسحٌ مستقلٌّ عن ماسح الحارس** (‏`css_strip_comments` في `tests/docs/check_site.py`): الحارسُ
[MIN-01] يجرّد المصدرَ بماسحه ويقارن الناتجَ بالمنشور — ولو كانا شيئًا واحدًا لشهد الماسحُ لنفسه.

**ويرفض بصوتٍ ولا يخمّن**:
- تعليقٌ أو سلسلةٌ لا تُغلَق، و`/*` داخل تعليق (تعليقٌ يُظنّ متداخلًا).
- تعليقٌ **بين محرفَي اسم** (‏`a/**/b`): في CSS لا يُنتج التعليقُ شيئًا فيبقى `a` و`b` رمزين،
  وحذفُه يلصقهما رمزًا واحدًا، وإبدالُه بمسافةٍ يصنع مُركِّبَ السليل في المحدِّد. لا نزعَ آمنًا،
  فيُرفَض ويُعاد صوغُ المصدر.

وما سوى التعليقات يبقى بالبايت: السلاسلُ (‏`content: "/*"`)، و`url(` بلا اقتباس (‏`url(data:…*/…)`
رمزٌ واحد)، والمسافات. وسطرٌ لم يكن فيه إلّا تعليقٌ يُحذف كلُّه، وما بقي بعد التعليق من مسافةٍ
في آخر السطر يُقصّ — فلا تبقى أسطرٌ فارغةٌ مكان سجلّ القرارات.
"""


class StripError(ValueError):
    """مصدرٌ لا يُجرَّد بأمان — يُوقِف البناء."""


def _ident(ch):
    return ch.isalnum() or ch in "-_" or ord(ch) > 127


def strip_css(src, name="?"):
    """⇒ نصُّ `src` بلا تعليقات. يرمي `StripError` بموضعٍ مسمّى عند ما لا يُجرَّد بأمان."""
    out = []
    lines_with_comment = set()   # أرقامُ أسطر المخرَج التي نُزع منها تعليق
    i, n = 0, len(src)

    def where(pos):
        return "%s:%d" % (name, src.count("\n", 0, pos) + 1)

    while i < n:
        c, c2 = src[i], src[i:i + 2]
        if c2 == "/*":
            end = src.find("*/", i + 2)
            if end < 0:
                raise StripError("تعليقٌ لا يُغلَق في %s" % where(i))
            if "/*" in src[i + 2:end]:
                raise StripError("‏`/*` داخل تعليقٍ في %s — تعليقٌ يُظنّ متداخلًا" % where(i))
            prev = out[-1][-1:] if out and out[-1] else ""
            nxt = src[end + 2:end + 3]
            if prev and nxt and _ident(prev) and _ident(nxt):
                raise StripError("تعليقٌ بين محرفَي اسمٍ في %s (‏`%s/*…*/%s`) — نزعُه يلصق رمزين "
                                 "وإبدالُه بمسافةٍ يغيّر المحدِّد؛ يُعاد صوغُ المصدر" % (where(i), prev, nxt))
            # الأسطرُ داخل التعليق تُحذف معه؛ ويُعلَّم السطرُ الحاليّ للقصّ.
            lines_with_comment.add("".join(out).count("\n"))
            i = end + 2
            continue
        if c2 == "*/":
            raise StripError("‏`*/` بلا `/*` يسبقه في %s" % where(i))
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                if src[j] == "\\":
                    j += 1
                elif src[j] == "\n":
                    raise StripError("سلسلةٌ لا تُغلَق في %s" % where(i))
                j += 1
            if j >= n:
                raise StripError("سلسلةٌ لا تُغلَق في %s" % where(i))
            out.append(src[i:j + 1])
            i = j + 1
            continue
        if src[i:i + 4].lower() == "url(":
            j = i + 4
            while j < n and src[j] in " \t\n":
                j += 1
            if j < n and src[j] not in "\"'":
                k = src.find(")", j)
                if k < 0:
                    raise StripError("‏`url(` لا يُغلَق في %s" % where(i))
                out.append(src[i:k + 1])
                i = k + 1
                continue
        out.append(c)
        i += 1

    res = []
    for no, line in enumerate("".join(out).split("\n")):
        if no in lines_with_comment:
            line = line.rstrip(" \t")
            if not line:
                continue           # سطرٌ لم يكن فيه إلّا تعليق
        res.append(line)
    return "\n".join(res)


def strip_js(src, name="?"):
    """⇒ JS بلا تعليقات **الأسطر الكاملة** — سطريًّا، بلا محلِّلٍ ولا تخمين.

    يُحذف سطرٌ يبدأ (بعد المسافة) بـ`//`، وكتلةٌ تبدأ في أوّل سطرها بـ`/*` حتّى السطر الذي
    تُغلَق فيه. وما سوى ذلك يبقى بالبايت، ومنه التعليقُ القصيرُ بعد شيفرةٍ في سطرها: تمييزُه
    يحتاج محلِّلًا (‏`/` قسمةٌ أو تعبيرٌ نمطيٌّ أو بدايةُ تعليق)، وما يوفّره لا يستحقّ ذلك.
    وحذفُ سطرٍ كاملٍ لا يغيّر الإدراجَ التلقائيّ للفاصلة (‏ASI): يبقى بين الجملتين سطرٌ جديد.

    **ويرفض بصوت**:
    - كتلةٌ لا تُغلَق، أو شيفرةٌ بعد `*/` في سطر الإغلاق (حذفُ السطر يحذفها معه).
    - قالبٌ نصّيٌّ (`` ` `` خارج سلسلةٍ في سطرٍ باقٍ): سطرٌ داخل قالبٍ يبدأ بـ`//` أو `/*` نصٌّ
      لا تعليق، والتمييزُ يحتاج محلِّلًا. فإن احتيج القالبُ يومًا وُسِّع هذا عن قصد.
    """
    import re as _re
    lines = src.split("\n")
    out = []
    i = 0
    while i < len(lines):
        st = lines[i].lstrip()
        if st.startswith("//"):
            i += 1
            continue
        if st.startswith("/*"):
            j, k = i, lines[i].index("/*") + 2
            while lines[j].find("*/", k) < 0:
                j, k = j + 1, 0
                if j >= len(lines):
                    raise StripError("تعليقٌ لا يُغلَق في %s:%d" % (name, i + 1))
            if lines[j][lines[j].find("*/", k) + 2:].strip():
                raise StripError("شيفرةٌ بعد `*/` في %s:%d — حذفُ سطر التعليق يحذفها معه" % (name, j + 1))
            i = j + 1
            continue
        if "`" in _re.sub(r"""'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*\"""", "", lines[i]):
            raise StripError("قالبٌ نصّيٌّ في %s:%d — سطرٌ داخله يبدأ بـ`//` نصٌّ لا تعليق، "
                             "والمجرِّدُ السطريّ لا يميّزه" % (name, i + 1))
        out.append(lines[i])
        i += 1
    return "\n".join(out)
