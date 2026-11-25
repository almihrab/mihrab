#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""جدولُ حالاتٍ لـ`site/sitegen/strip.py` [MIN-01] — ما يُجرَّد، وما يبقى بالبايت، وما يُرفَض.

    python tests/docs/test_strip.py

لماذا جدولٌ لا الحارسُ وحده: ‏[MIN-01] في `check_site.py` يقيس المجرِّدَ على **مصدر الموقع
الحاليّ**، وهو بلا سلسلةٍ فيها `/*`، ولا `url(` بلا اقتباس، ولا `a/**/b`، ولا قالبٍ نصّيّ، ولا
شيفرةٍ بعد `*/`. فكلُّ فرعٍ من هذه في المجرِّد يُعطَب والحارسُ أخضر (قِيس: ‎16‎ طفرةً كلُّها
تنجو). بل بعضُها لا يراه الحارسُ ولو ظهر في المصدر: ماسحُه يلصق `a/**/b` كالمجرِّد، ويعُدّ كلَّ
سطرٍ يبدأ بـ`/*` تعليقًا كلَّه — فشيفرةٌ بعد `*/` تُحذف وهو راضٍ. هنا يُقاس كلُّ فرعٍ بحالته.
"""
import os
import sys

sys.dont_write_bytecode = True   # لا `__pycache__` في site/sitegen — [GEN-01] يرفضه
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "site"))
from sitegen.strip import StripError, strip_css, strip_js  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

REJ = StripError   # «يُرفَض»

# (الدالّة، المدخل، المتوقَّع بالبايت أو REJ، الوسم) — الوسمُ في سطر الفشل لتُقرأ المُصاباتُ عليه.
CASES = [
    # ── CSS: ما يُجرَّد ──
    (strip_css, "a{color:red}/* x */\nb{}", "a{color:red}\nb{}", "css-strip"),
    (strip_css, "/* سجلّ */\na{}", "a{}", "css-line"),
    (strip_css, "a{}\n/* l1\n   l2 */\nb{}", "a{}\nb{}", "css-line"),
    (strip_css, "a{color:red; /* c */\n}", "a{color:red;\n}", "css-trim"),
    (strip_css, "a{} /**/", "a{}", "css-trim"),
    (strip_css, "a /**/ b{}", "a  b{}", "css-strip"),
    (strip_css, "a{}\n\nb{}", "a{}\n\nb{}", "css-blank"),
    # ── CSS: ما يبقى بالبايت ──
    (strip_css, 'a{content:"/*"}', 'a{content:"/*"}', "css-string"),
    (strip_css, 'a{content:"*/"}', 'a{content:"*/"}', "css-string"),
    (strip_css, "a{content:'/* x */'}", "a{content:'/* x */'}", "css-string"),
    (strip_css, 'a{content:"\\"/*"}', 'a{content:"\\"/*"}', "css-escape"),
    (strip_css, "a{background:url(data:x/*y*/z)}", "a{background:url(data:x/*y*/z)}", "css-url"),
    (strip_css, "a{background:URL(  x*/y)}", "a{background:URL(  x*/y)}", "css-url"),
    (strip_css, 'a{background:url("/*")}', 'a{background:url("/*")}', "css-url"),
    # ── CSS: ما يُرفَض ──
    (strip_css, "a/**/b{}", REJ, "css-ident"),
    (strip_css, "a-/**/b{}", REJ, "css-ident"),
    (strip_css, "a_/**/b{}", REJ, "css-ident"),
    (strip_css, "م/**/b{}", REJ, "css-ident"),
    (strip_css, "a{width:1/**/.5em}", REJ, "css-ident"),
    (strip_css, "a{color:rgb/**/(1,2,3)}", REJ, "css-ident"),
    (strip_css, "a{color:red;/* c */}", "a{color:red;}", "css-sep"),
    (strip_css, "a{}/* c */b{}", "a{}b{}", "css-sep"),
    (strip_css, ".a\\'b{}", ".a\\'b{}", "css-escape"),
    (strip_css, ".a\\/*b*/", REJ, "css-escape"),
    (strip_css, ".a\\ /**/b{}", REJ, "css-escape"),
    (strip_css, "a{color:red/* c */;}", "a{color:red;}", "css-sep"),
    (strip_css, "a{/* c */x:1;/* d */y:2}", "a{x:1;y:2}", "css-sep"),
    (strip_css, "a,/* c */b{}", "a,b{}", "css-sep"),
    (strip_css, "a{}/* x *//* y */b{}", "a{}b{}", "css-sep"),
    # رموزٌ من محرفٍ واحدٍ لا تلتحم: نزعُ التعليق بجانبها آمن
    (strip_css, "a>/*x*/b{}", "a>b{}", "css-sep"),
    (strip_css, "a:/*x*/hover{}", "a:hover{}", "css-sep"),
    (strip_css, "a{b:f(/*x*/)}", "a{b:f()}", "css-sep"),
    (strip_css, "a{color:/*x*/red}", "a{color:red}", "css-sep"),
    (strip_css, "a[/*x*/href]{}", "a[href]{}", "css-sep"),
    # وما يلتحم يُرفض: `(` بعد التعليق دالّة، و`+`/`.`/`-` أرقام
    (strip_css, "a{x:1/**/+2}", REJ, "css-ident"),
    (strip_css, "a{x:a/**/-b}", REJ, "css-ident"),
    (strip_css, "a{content:x\\'}/* c */b{}", "a{content:x\\'}b{}", "css-escape"),
    (strip_css, "a{} /* /* */", REJ, "css-nested"),
    (strip_css, "a{} */", REJ, "css-stray"),
    (strip_css, "a{} /* open", REJ, "css-unclosed"),
    (strip_css, 'a{content:"open}', REJ, "css-unclosed"),
    (strip_css, 'a{content:"x\ny"}', REJ, "css-unclosed"),
    (strip_css, "a{background:url(x", REJ, "css-unclosed"),
    # ── JS: ما يُجرَّد (أسطرٌ كاملة) ──
    (strip_js, "// c\nx();", "x();", "js-line"),
    (strip_js, "\t  // c\nx();", "x();", "js-line"),
    (strip_js, "/* a\n   b */\nx();", "x();", "js-block"),
    (strip_js, "/** a */\nx();", "x();", "js-block"),
    (strip_js, "/*/\n*/\nx();", "x();", "js-block"),
    (strip_js, "x();\n\ny();", "x();\n\ny();", "js-blank"),
    # ── JS: ما يبقى بالبايت ──
    (strip_js, "x(); // ذيل", "x(); // ذيل", "js-keep"),
    (strip_js, "x(); /* a */ y();", "x(); /* a */ y();", "js-keep"),
    (strip_js, "a = 1 / 2;\n// c", "a = 1 / 2;", "js-keep"),
    (strip_js, "s = '`';", "s = '`';", "js-tpl-string"),
    (strip_js, 's = "`";', 's = "`";', "js-tpl-string"),
    (strip_js, "s = 'it\\'s `';", "s = 'it\\'s `';", "js-tpl-string"),
    # ── JS: ما يُرفَض ──
    (strip_js, "/* a */ x();", REJ, "js-after-close"),
    (strip_js, "/* a\n */ x();", REJ, "js-after-close"),
    (strip_js, "/* open\nx();", REJ, "js-unclosed"),
    (strip_js, "s = `a`;", REJ, "js-template"),
    (strip_js, "s = `\n// نصٌّ لا تعليق\n`;", REJ, "js-template"),
    (strip_js, "x(); /* a\n*/", REJ, "js-midopen"),
    (strip_js, 's = "/*";', 's = "/*";', "js-midopen"),
    (strip_js, "x(); /* a */ y(); /* b */ z();", "x(); /* a */ y(); /* b */ z();", "js-midopen"),
    (strip_js, "x(); /* a */ y(); /* b\n*/", REJ, "js-midopen"),
    (strip_js, "x(); /* a\n/* b */\ny();\n*/", REJ, "js-midopen"),
    (strip_js, "s = 'a\\\n// b';", REJ, "js-continuation"),
]


# ‏**وماسحُ الحارس** (‏`css_strip_comments` في check_site.py) شاهدُ [MIN-01] على المجرِّد، فما
# يجهله يعمى عنه الشاهد. والمصدرُ الحاليّ لا يحوي هروبًا خارج تعليق، فلا يُرى فرعُه إلّا هنا.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv, sys.argv = sys.argv, ["check_site.py"]
import check_site as _cs  # noqa: E402
sys.argv = _argv
GUARD_CASES = [
    ("a{content:x\\'}/* c */b{}", "a{content:x\\'}b{}", "guard-escape"),
    ("a{content:'/*'}/* c */b{}", "a{content:'/*'}b{}", "guard-string"),
    ("a{background:url(data:x*/y)}/* c */", "a{background:url(data:x*/y)}", "guard-url"),
]


def main():
    print("╔══ [MIN-01] جدولُ حالات strip.py ══╗")
    fails = []
    for src, want, tag in GUARD_CASES:
        try:
            got = _cs.css_strip_comments(src, "t")
        except _cs._Stop as e:
            got = "توقّف: %s" % e
        if got != want:
            fails.append("[MIN-01/%s] css_strip_comments(%r): %r، والمتوقَّع %r" % (tag, src, got, want))
    for fn, src, want, tag in CASES:
        try:
            got = fn(src, "t")
        except StripError:
            got = REJ
        if got != want:
            fails.append("[MIN-01/%s] %s(%r): %s، والمتوقَّع %s" % (
                tag, fn.__name__, src, "رُفض" if got is REJ else repr(got),
                "الرفض" if want is REJ else repr(want)))
    if fails:
        print("❌ %d حالةً خاطئة من %d:" % (len(fails), len(CASES)))
        for f in fails:
            print("   · %s" % f)
        return 1
    print("╚══ ✅ %d حالةً كما يُتوقَّع ══╝" % (len(CASES) + len(GUARD_CASES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
