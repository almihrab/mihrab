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
import shutil
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# المولِّدُ مقسَّمٌ في `sitegen/`. ولا `__pycache__` في شجرة المصدر: البناءُ يُشغَّل من
# النسخة المصدريّة نفسِها، وما يكتبه بجانبها يظهر في `git status` وفي أدوات الإثبات.
sys.dont_write_bytecode = True

from sitegen.data import ASSETS, BUILD_MARK, CONTENT, NAV, OUT, RELEASES, SLUG_SECTION, SLUG_TITLE
from sitegen.fonts import write_fonts_css
from sitegen.pages import build_download, build_keyboard_page, build_landing, build_not_found
from sitegen.preview import _ALIF_JS, build_alif_preview
from sitegen.templates import (
    DOCS_SECTION_NOTE,
    MARK_SVG,
    drift_banner_html,
    nav_html,
    page_shell,
    src_note_html,
    toc_html,
)
from sitegen.text import glossary_aliases, parse_front_matter, render_md, strip_tags


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

        for _e in sorted(os.listdir(OUT)):
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
    for fn in sorted(os.listdir(ASSETS)):
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
        for fn in sorted(os.listdir(s_dir)):
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
        '<main class="home">' + (MARK_SVG % "mark-lg")
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
    open(os.path.join(OUT, ".nojekyll"), "w", encoding="utf-8").close()

    print("✅ بُني الموقع: صفحةٌ أولى + تنزيل + مركزُ توثيق + %d صفحة → %s"
          % (len(pages), OUT))
    if not RELEASES.get("version"):
        print("  ℹ️  لا إصدارَ في releases.json — صفحةُ التنزيل تعرض حالةَ الفراغ.")
    return 0


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


if __name__ == "__main__":
    sys.exit(main())
