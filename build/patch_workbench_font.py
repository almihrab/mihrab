#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""‏[AR-02] الخطُّ العربيُّ المحزوم يُحمَّل فعلًا — لا `data:` تحجبها سياسةُ الأمان.

## العطبُ ولماذا لم يُرَ سنةً كاملة

‏`patch_bundle_extensions.py` يحقن `@font-face` لـKawkab Mono **قبل** التحزيم، بمصدر
‏`data:` URI. والاختيارُ كان صحيحًا لمشكلتِه: `esbuild` يحلّ `url()` النسبيَّ زمنَ البناء
ولا مُحمِّلَ عنده لـ`.woff2` ⇒ «No loader is configured». لكنّ `workbench.html` يحمل
‏`font-src 'self' vscode-remote-resource: …` — **بلا `data:`**. فالمتصفّحُ يحجب الخطَّ.

وقِيس حيًّا في النسخة المشحونة، لا استُنتج:

    document.fonts ⇒ ["Kawkab Mono:error"]
    securitypolicyviolation ⇒ "font-src data"

**ولماذا لم يُرَ:** `editor.fontFamily` يبدأ بـKawkab ثمّ `Cascadia Mono`. وكانت
‏Cascadia تُصيّر العربيّةَ بعرضٍ موحّدٍ تحت Chromium 142، فبدا الأمرُ سليمًا وحارسُ
‏`TY-03` أخضر. وفي Chromium 148 (ترقية المنبع 1.126) كفّت عن ذلك، فانكشف العطبُ
الأصليُّ فجأةً كأنّه انحدارُ ترقية — وهو أقدمُ منها. أمّا `VA-02ب` فكان أحمرَ طوالَ
الوقتِ بتعليلٍ خاطئ («محدِّدُ اللغة قد يكون مات صامتًا») — والسببُ الحقيقيُّ هذا.

## لماذا رقعةٌ بعد الحزم لا توسيعُ السياسة

الطريقُ الأقصرُ كان إضافةَ `data:` إلى `font-src`. رُفض: توسيعُ سياسةِ أمانٍ في النافذة
الرئيسة ثمنٌ دائمٌ لمشكلةِ أداةِ بناءٍ مؤقّتة، والخطوطُ مُحلِّلاتٌ ثنائيّةٌ معقّدةٌ وسطحُ
هجومٍ معروف. وبعد الحزم لا `esbuild` بعدُ، فـ`url()` النسبيُّ يعمل، و`'self'` يغطّيه
أصلًا. وهذه سابقةُ `patch_xterm_bidi.py` نفسُها: ما لا يُصلَحُ في المصدرِ يُصلَحُ في المشحون.

**ومكسبٌ ثانٍ مقيس:** حذفُ الـbase64 يُنقِص `workbench.desktop.main.css` نحوَ ‏142 ك.ب.

## وما لا يُصلحه — يُقال ولا يُدَّعى

وضعُ التطوير (‏`launch.mjs`) يبقى على `data:` المحجوبة: الورقةُ هناك تُحمَّل من المصدر
بلا تحزيم. فالمشحونُ — وهو ما يصلُ المستخدم — يُصلَح، والتطويرُ يبقى ساقطًا لبقيّة
المكدّس. يُذكَر كي لا يُقرأ اختلافُ القياس بين الوضعين انحدارًا.

الاستعمال:  python build/patch_workbench_font.py <APP_DIR>
"""
import io
import os
import re
import shutil
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# ثلاثُ أوراقٍ لا واحدة — بعددِ الأشجار التي تُشحَن: المكتبيّ، وبناءُ الخادم
# (`vscode-reh-web-*`)، والبناءُ الثابت (`vscode-web`). والعطبُ نفسُه في الثلاث —
# سياسةُ الويب `font-src 'self' blob:` لا تحوي `data:` هي الأخرى.
#
# والثالثةُ أُضيفت متأخّرة، وكان غيابُها صامتًا مرّتين: الأداةُ تخرج بـ«لا ورقةَ أنماطٍ
# محزومة»، والحارسُ في L2 كان يعدّ قواعدَ الاتّجاه في **ورقةٍ لا تحمّلها الصفحةُ
# الثابتة أصلًا** فيبقى أخضر. يُختار كلُّ موجودٍ لا أوّلُه.
CSS_CANDIDATES = (
    os.path.join("out", "vs", "workbench", "workbench.desktop.main.css"),
    os.path.join("out", "vs", "code", "browser", "workbench", "workbench.css"),
    os.path.join("out", "vs", "workbench", "workbench.web.main.internal.css"),
)
FONT_SRC_REL = os.path.join("extensions", "mihrab-welcome", "media", "kawkab-mono.woff2")
# احتياطٌ من المستودع نفسِه: البناءُ الثابت (`vscode-web`) لا يشحن `mihrab-welcome`
# (يحتاج Node) فلا نسخةَ للخطّ في شجرته — والخطُّ لازمٌ فيها كما في أختَيها.
FONT_SRC_REPO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "patches", "fonts", "kawkab-mono.woff2")
FONT_NAME = "kawkab-mono.woff2"
WOFF2_MAGIC = b"wOF2"

# المِرساة: قاعدةُ `@font-face` التي حقنها patch_bundle_extensions قبل التحزيم.
# تُطابَق بجسمها كلِّه (‏base64 طويل) لا برأسها وحدَه، فلا يُستبدَل نصفُ قاعدة.
RULE_RE = re.compile(r'@font-face\{font-family:Kawkab Mono;[^}]*\}')
NEW_RULE = ('@font-face{font-family:Kawkab Mono;font-style:normal;font-weight:400;'
            'font-display:swap;src:url(' + FONT_NAME + ') format("woff2")}')


def fail(msg):
    print("❌ " + msg, file=sys.stderr)
    sys.exit(1)


def _sheets_with_rule(app_dir):
    """كلُّ ورقةٍ في `out/` تحمل قاعدةَ Kawkab — **مسحًا لا قائمةً**.

    ‏**والقائمةُ المكتوبةُ بيدٍ تُغلِق ما عُرِف يومَ كُتِبت لا ما يجيء.** كانت
    ثلاثةَ أسماء، ثمّ قِيست ورقةٌ رابعةٌ خارجَها في الشجرة الثابتة:

        out/vs/sessions/sessions.web.main.internal.css
        @font-face{font-family:Kawkab Mono;…;src:url(data:font/woff2;base64,…)}

    وأثرُها اليومَ صفرٌ في السلوك (‏`boot.js` لا يستوردها) و≈112 ك.ب ميتةٍ في
    شجرةٍ تُنشَر. لكنّ **الصنفَ** هو [AR-02] بعينه: سياستُنا `font-src 'self'`
    بلا `data:`، فيومَ تُفتَح تلك الواجهةُ — والنواةُ تضيفها لا نحن — تُصيَّر
    عربيّتُها بلاتينيٍّ ساقطٍ **بصمت**، وتُقرأ انحدارَ ترقيةٍ وهي أقدمُ منها.
    وذاك التشخيصُ الخاطئُ عينُه كلّف سنةً في المرّة الأولى.

    والمسحُ مقصورٌ على `out/`: امتداداتُ المنبع تحمل خطوطَها ولا شأنَ لنا بها.
    """
    hits = []
    out = os.path.join(app_dir, "out")
    if not os.path.isdir(out):
        return hits
    for dp, dn, fn in os.walk(out):
        dn[:] = [d for d in dn if d != "node_modules"]
        for f in fn:
            if not f.endswith(".css"):
                continue
            p = os.path.join(dp, f)
            try:
                txt = io.open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if RULE_RE.search(txt) or NEW_RULE in txt:
                hits.append(p)
    return sorted(hits)


def main(app_dir):
    found = _sheets_with_rule(app_dir)
    if not found:
        # ‏القائمةُ القديمةُ تبقى **أرضيّةَ تشخيصٍ** لا معيارَ انتقاء: غيابُ كلّ
        # ورقةٍ يعني بناءً بلا خطٍّ (سقوطٌ رشيقٌ معلَن) أو شجرةً ليست ما قِيس،
        # وذكرُ المرشَّحين المعروفين يفرّق بين الحالتَين للقارئ.
        _known = [r for r in CSS_CANDIDATES
                  if os.path.isfile(os.path.join(app_dir, r))]
        if not _known:
            fail("لا ورقةَ أنماطٍ محزومة تحت " + app_dir + "/out — والمعروفُ منها: "
                 + " · ".join(CSS_CANDIDATES))
        print("  ⏭️ لا قاعدةَ @font-face لـKawkab Mono في أيّ ورقة — "
              "بناءٌ بلا خطٍّ عربيّ (سقوطٌ رشيق).")
        return 0
    rc = 0
    for css in found:
        rc = _patch_one(css, app_dir) or rc
    return rc


def _patch_one(css, app_dir):

    src = io.open(css, encoding="utf-8", newline="").read()

    if NEW_RULE in src:
        print("  ⏭️ الخطُّ العربيُّ موصولٌ بملفٍّ سلفًا (لا عمل)")
        return 0

    hits = RULE_RE.findall(src)
    if len(hits) != 1:
        # صفرٌ = الخطُّ لم يُحقَن أصلًا (بناءٌ بلا خطّ — سقوطٌ رشيقٌ معلَن في
        # patch_bundle_extensions). أكثرُ من واحدةٍ = الورقةُ ليست ما قِيس.
        if not hits:
            print("  ⏭️ لا قاعدةَ @font-face لـKawkab Mono في المحزوم — "
                  "بناءٌ بلا خطٍّ عربيّ (سقوطٌ رشيق).")
            return 0
        fail("قاعدةُ @font-face وقعت " + str(len(hits)) + " مرّةً لا مرّةً واحدة — "
             "الورقةُ ليست ما قِيس. لا يُستبدَل موضعٌ لم يُقرأ.")

    font_src = os.path.join(app_dir, FONT_SRC_REL)
    if not os.path.isfile(font_src):
        font_src = FONT_SRC_REPO
    if not os.path.isfile(font_src):
        fail("القاعدةُ محقونةٌ ولا ملفَّ خطٍّ لنسخه: " + os.path.join(app_dir, FONT_SRC_REL) +
             " ولا " + FONT_SRC_REPO + " — لا يُترك مصدرٌ يشير إلى ملفٍّ غيرِ موجود.")
    with io.open(font_src, "rb") as f:
        head = f.read(4)
    if head != WOFF2_MAGIC:
        fail("ملفُّ الخطّ ليس WOFF2 سليمًا (بصمةُ الصيغة لا تطابق): " + font_src)

    font_dst = os.path.join(os.path.dirname(css), FONT_NAME)
    tmp_font = font_dst + ".mihrab-tmp"
    shutil.copyfile(font_src, tmp_font)
    os.replace(tmp_font, font_dst)

    out = RULE_RE.sub(lambda _m: NEW_RULE, src, count=1)
    tmp = css + ".mihrab-tmp"
    io.open(tmp, "w", encoding="utf-8", newline="").write(out)
    os.replace(tmp, css)          # ذرّيّة: لا ورقةَ نصفَ مكتوبةٍ لو انقطع

    saved = (len(src) - len(out)) / 1024.0
    print("  ✅ الخطُّ العربيُّ المحزوم يُحمَّل من ملفٍّ مجاور (‏%s) — "
          "لا data: تحجبها CSP [AR-02]؛ الورقةُ أخفُّ %.0f ك.ب" % (FONT_NAME, saved))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        fail("الاستعمال: python build/patch_workbench_font.py <APP_DIR>")
    sys.exit(main(sys.argv[1]))
