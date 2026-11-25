# -*- coding: utf-8 -*-
"""المساراتُ وبياناتُ الموقع والتنقّل."""
import json
import os

# جذرُ `site/` لا مجلّدُ هذه الوحدة: درجتان فوق `sitegen/data.py`. وكلُّ مسارٍ مطلقٌ منه،
# فالبناءُ لا يتعلّق بمجلّد العمل.
SITE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(SITE_DIR, "content")
ASSETS = os.path.join(SITE_DIR, "assets")
DATA = os.path.join(SITE_DIR, "data")
# ‏`MIHRAB_SITE_OUT` يسمح بالبناء إلى مجلّدٍ مؤقّت: حارسُ [SITE-01] يبني في
# كلّ تشغيلٍ للطبقة الساكنة **ليُثبِت أنّ الموقعَ يُبنى**، ولا يجوز أن يدوس
# مخرَجًا قائمًا لأجل فحص.
OUT = os.environ.get("MIHRAB_SITE_OUT") or os.path.join(SITE_DIR, "public")
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

# ⚠️ كلُّ المسارات نسبيّة (`.` و`..`) عمدًا: المخرَجُ نفسُه يصلح من
# `mihrab.dev/` ومن أيّ مرآةٍ تحت بادئة (كـ`almihrab.github.io/mihrab/` — غيرُ
# مفعَّلةٍ اليوم، انظر `site/README.md`) بلا إعادةِ بناء.
# مسارٌ مطلقٌ واحد يربط المخرَج بمضيفٍ بعينه ويكسر مرآةً كهذه صامتًا.

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
