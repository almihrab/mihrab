#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""صفحةُ المضيف وهويّتُها على شجرة `vscode-web` الثابتة (محرابٌ بلا خادم).

‏`vscode-web` **مكتبةٌ لا موقع**: لا `index.html` فيه ولا `product.json`. يُصدِّر
‏`create()` وينتظر أن تكتب أنت الصفحةَ التي تُقلِعه. ومن هذا الغياب ينشأ عملُ هذا
المُرقِّع: كلُّ ما تفرضه بقيّةُ الخطوات على `product.json` لا موضعَ له هنا، فيُفرَض
على أربعةِ ملفّاتٍ **يراها الزائرُ مباشرة**:

  • `index.html` و`boot.js` — يُنسَخان من `web/` في المستودع (مصدرُ الحقيقة).
  • `manifest.json` — يشحنه المنبعُ من `resources/server/`، **ويعيد VSCodium كتابتَه**
    إلى `name/short_name = "VSCodium"` و`lang = "en-US"`. فزرُّ «تثبيتُ التطبيق»
    كان يعرض اسمَ المنبع، ومانيفستٌ إنجليزيٌّ فوق صفحةٍ تقول `lang="ar"`.
  • `favicon.ico` و`code-{192,512}.png` — أيقوناتُ VSCodium حرفيًّا. أيقونةُ التبويب.

ولا حارسَ كان يمسك شيئًا من هذا: طبقةُ L2 تقيس `product.json`، ولا `product.json`
في هذه الشجرة.

    python patch_web_host.py <مسار vscode-web> [--verify]
"""
import json
import os
import re
import shutil
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_WEB = os.path.join(ROOT, "web")
BRAND = os.path.join(ROOT, "assets", "branding")
OVERRIDES = os.path.join(ROOT, "product-overrides", "product.json")

# صفحةُ المضيف: مصدرُها المستودعُ لا الشجرةُ المبنيّة. تُنسَخ في كلّ بناءٍ فلا تنجو
# نسخةٌ قديمةٌ في شجرةٍ لم تُنظَّف.
# ‏`boot-early.js` ثالثُهم [WEB-09]: خرج من `index.html` كي تستغني سياسةُ الأمان
# عن `'unsafe-inline'`. وكلُّهم يُنسَخون من المستودع ويُقارَنون بايتًا ببايت في
# `--verify` — فنسخةٌ نجت من بناءٍ سابقٍ تُرفَض قبل أن تُنشَر.
PAGE_FILES = ("index.html", "boot.js", "boot-early.js")

PRODUCT_JS = "product.web.js"
PRODUCT_PREFIX = "globalThis._MIHRAB_PRODUCT="

# ── الهويّةُ تُشتَقّ ولا تُكتَب مرّتين ──
# كانت مكتوبةً حرفيًّا في `boot.js`، فافترقت عن `product-overrides/product.json` في
# خمسةِ مفاتيح: ثلاثةُ روابطَ إلى صفحاتٍ لا وجودَ لها، و`latestUrlTemplate`، و
# ‏`controlUrl` — قائمةُ الإضافات المحظورة من Eclipse، وهي **حمايةٌ** للمستخدم لا
# زينة. اسمان لهويّةٍ واحدةٍ يفترقان بصمت، فصار المصدرُ واحدًا.
#
# وما يُنتقى: ما له معنًى في متصفّح. مفاتيحُ ويندوز و`darwinBundleIdentifier`
# و`serverApplicationName` لا موضعَ لها في صفحة، وحملُها إليها تشويشٌ لا هويّة.
WEB_PRODUCT_KEYS = (
    "nameShort", "nameLong", "applicationName", "dataFolderName", "urlProtocol",
    "defaultLocale", "quality",
    "extensionsGallery", "linkProtectionTrustedDomains",
    "documentationUrl", "reportIssueUrl", "requestFeatureUrl", "licenseUrl",
    "releaseNotesUrl", "downloadUrl", "twitterUrl",
    "keyboardShortcutsUrlWin", "keyboardShortcutsUrlLinux", "keyboardShortcutsUrlMac",
    "tipsAndTricksUrl", "introductoryVideosUrl", "newsletterSignupUrl",
    "updateUrl", "serverDownloadUrlTemplate",
)

# الأيقونات: (اسمُ الهدف في الشجرة, مصدرُه في المستودع)
# ── [WEB-07] ما لا يُقرأ لا يُشحَن ─────────────────────────────────────────────
# ‏`out/nls.metadata.json` بياناتُ بناءٍ لا بياناتُ تشغيل: صفرُ إشاراتٍ إليه في
# `src/` كلِّه (قِيس)، ومستهلكُه الوحيدُ في المنبع سكربتُ CI يرفعه إلى خدمة الترجمة
# (`build/azure-pipelines/upload-nlsmetadata.ts`). ومع ذلك يخرج في الشجرة الثابتة،
# فيُخدَم من `mihrab.dev` بـ**‏1.9 م.ب** ويحمل «‏VSCodium» ستًّا وتسعين مرّة —
# «‏VSCodium for Web»، «‏Quality type of VSCodium»…
#
# وليس تسرّبًا نظريًّا: ملفٌّ عامٌّ على نطاقنا يُنزَّل بعنوانٍ مباشر، ويُفهرَس، ويقرؤه
# من يسأل «على أيّ شيءٍ بُني محراب؟» فيجد جوابًا **نصفَه صحيحٌ ولا نقوله نحن**.
# ونحن نقول الجوابَ كاملًا في وثائقنا؛ الفرقُ أن يُقال قصدًا لا أن يُنسى.
#
# والحذفُ لا التعريب: التعريبُ يُبقي ‎1.9‎ م.ب من حمولةٍ ميّتةٍ على كلّ نشر، والحذفُ
# يُنهي الفئةَ. وهو **مقصورٌ على الشجرة الثابتة**: المكتبيُّ لا يُخدَم بعنوان.
DEAD_WEIGHT = ("out/nls.metadata.json",)

ICONS = (
    ("favicon.ico", os.path.join(BRAND, "mihrab.ico")),
    ("code-192.png", os.path.join(BRAND, "mihrab-pwa-192.png")),
    ("code-512.png", os.path.join(BRAND, "mihrab-pwa-512.png")),
)

# ‏`display_override` و`display` كما يشحنهما المنبع — لا سببَ لمخالفتهما.
# و`start_url`/`scope` نسبيّان: محرابٌ الثابت قد يُخدَم من جذرِ نطاقٍ أو من مسارٍ
# فرعيّ (‏`/mihrab/`)، ومسارٌ مطلقٌ يكسر الثانيَ صامتًا.
MANIFEST = {
    "name": "محراب",
    "short_name": "محراب",
    "description": "محرِّرُ شيفرةٍ عربيُّ الاتّجاه، يعمل في متصفّحك بلا تثبيت.",
    "lang": "ar",
    "dir": "rtl",
    "start_url": "./",
    "scope": "./",
    "display": "standalone",
    "display_override": ["window-controls-overlay"],
    # أرضيّةُ شاشة الإقلاع نفسُها ⇒ لا قفزةَ لونٍ بين شاشة النظام وأوّلِ إطار.
    "background_color": "#0d1f1c",
    "theme_color": "#0d1f1c",
    "icons": [
        {"src": "code-192.png", "type": "image/png", "sizes": "192x192",
         "purpose": "any maskable"},
        {"src": "code-512.png", "type": "image/png", "sizes": "512x512",
         "purpose": "any maskable"},
    ],
}

LEAKS = ("vscodium", "microsoft")


def fail(msg):
    print("❌ " + msg, file=sys.stderr)
    return 1


def _write_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def _read_overrides():
    """تجاوزاتُ الهويّة بلا مفاتيح التعليق (‏`_comment*` ليست هويّةً ولا تُشحَن)."""
    raw = json.loads(open(OVERRIDES, encoding="utf-8").read())
    return {k: v for k, v in raw.items() if not k.startswith("_comment")}


def _web_product(over):
    return {k: over[k] for k in WEB_PRODUCT_KEYS if k in over}


def apply(web):
    if not os.path.isfile(OVERRIDES):
        return fail("تجاوزاتُ الهويّة مفقودة: " + OVERRIDES)
    prod = _web_product(_read_overrides())
    body = (PRODUCT_PREFIX + json.dumps(prod, ensure_ascii=False, indent=2) + ";\n")
    _write_atomic(os.path.join(web, PRODUCT_JS), body.encode("utf-8"))
    print("  ✓ " + PRODUCT_JS + " (" + str(len(prod)) + " مفتاحًا ⟵ product-overrides)")

    for name in PAGE_FILES:
        src = os.path.join(SRC_WEB, name)
        if not os.path.isfile(src):
            return fail("صفحةُ المضيف مفقودةٌ من المستودع: " + src)
        with open(src, "rb") as f:
            _write_atomic(os.path.join(web, name), f.read())
        print("  ✓ " + name)

    _write_atomic(os.path.join(web, "manifest.json"),
                  (json.dumps(MANIFEST, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print("  ✓ manifest.json (محراب · ar · rtl)")

    for name, src in ICONS:
        if not os.path.isfile(src):
            return fail("أصلُ الأيقونة مفقود: " + src +
                        " — وَلِّدها بـ‏`py -3 assets/branding/gen_ico.py`")
        with open(src, "rb") as f:
            _write_atomic(os.path.join(web, name), f.read())
        print("  ✓ " + name + " ⟵ " + os.path.basename(src))

    for rel in DEAD_WEIGHT:
        dead = os.path.join(web, *rel.split("/"))
        if os.path.isfile(dead):
            kb = os.path.getsize(dead) // 1024
            os.remove(dead)
            print("  ✓ حُذِف " + rel + " (" + str(kb) + " ك.ب — بياناتُ بناءٍ لا تُقرأ) [WEB-07]")
    return 0


def verify(web):
    errs = []

    # ‏[WEB-07] وجودُه يعني أنّ خطوةَ الحذف لم تُشغَّل — أو شجرةٌ نجت من بناءٍ سابق.
    for rel in DEAD_WEIGHT:
        if os.path.isfile(os.path.join(web, *rel.split("/"))):
            errs.append(rel + " ما زال في الشجرة — بياناتُ بناءٍ لا يقرؤها أحد، "
                        "تُخدَم بميغابايتَين وتحمل اسمَ التوزيعة الأمّ [WEB-07]")

    for name in PAGE_FILES:
        dst, src = os.path.join(web, name), os.path.join(SRC_WEB, name)
        if not os.path.isfile(dst):
            errs.append("صفحةُ المضيف غائبةٌ عن الشجرة: " + name +
                        " — البناءُ الثابتُ بلا صفحةٍ حزمةٌ لا يفتحها أحد")
            continue
        with open(dst, "rb") as a, open(src, "rb") as b:
            if a.read() != b.read():
                errs.append(name + " في الشجرة يخالف `web/" + name + "` في المستودع "
                            "— نسخةٌ قديمةٌ نجت من بناءٍ سابق")

    # ── الهويّةُ في الشجرة تطابق المصدرَ الوحيد ──
    ppath = os.path.join(web, PRODUCT_JS)
    if not os.path.isfile(ppath):
        errs.append(PRODUCT_JS + " غائب — الصفحةُ تُقلِع بلا هويّةٍ إطلاقًا")
    else:
        txt = open(ppath, encoding="utf-8").read()
        if not txt.startswith(PRODUCT_PREFIX):
            errs.append(PRODUCT_JS + " لا يبدأ بـ" + PRODUCT_PREFIX)
        else:
            got = json.loads(txt[len(PRODUCT_PREFIX):].rstrip().rstrip(";"))
            want = _web_product(_read_overrides())
            if got != want:
                drift = sorted(set(got) ^ set(want)) or \
                    sorted(k for k in want if got.get(k) != want[k])
                errs.append("هويّةُ الويب انحرفت عن product-overrides في: " +
                            " · ".join(drift))
            for key, expect in (("nameLong", "محراب"), ("defaultLocale", "ar")):
                if got.get(key) != expect:
                    errs.append(PRODUCT_JS + "." + key + " = " + repr(got.get(key)))
            if got.get("updateUrl") is not None:
                errs.append("updateUrl ليس null — تحديثٌ يجرّ منبعًا")
            _sdl = str(got.get("serverDownloadUrlTemplate") or "")
            if any(k in _sdl.lower() for k in LEAKS):
                errs.append("serverDownloadUrlTemplate يشير إلى المنبع: " + _sdl[:90])

    # ── [WEB-10] كلّ عنوانٍ مُبكّرٍ يشير إلى ملفٍّ موجود في الشجرة ──
    # ‏`preload` و`modulepreload` عناوينُ **مكتوبةٌ باليد** في `web/index.html`،
    # ومقابلاتُها في الشجرة يولّدها `gulp` ويسمّيها المنبع. فإعادةُ تسميةٍ
    # واحدةٌ في ترقيةٍ تترك الوسمَ يشير إلى لا شيء — **والمتصفّح لا يشتكي شكوى
    # مرئيّة**: يدفع رحلةً، يقبض 404، يمضي. فيبقى السطرُ في الصفحة سنينَ
    # يكلّف ولا ينفع، وهو **عكسُ ما وُضِع له** بالضبط. ومُلتقِطُ `boot-early.js`
    # يتخطّى التبكيرَ عمدًا (سطر 149 هناك) — فلا حارسَ حيًّا عليه إطلاقًا،
    # وهذا موضعُ الفحص الوحيد الذي يرى الصفحةَ والشجرةَ معًا.
    idx = os.path.join(web, "index.html")
    if os.path.isfile(idx):
        _page = open(idx, encoding="utf-8").read()
        _pre = re.findall(
            r'<link\s(?=[^>]*rel="(?:module)?preload")[^>]*\shref="([^"]+)"', _page)
        if not _pre:
            errs.append("‏لا وسمَ تبكيرٍ في index.html — والفحصُ يقيس صفرًا. "
                        "إن أُسقِط التبكيرُ عمدًا فأسقِط هذا معه بسببٍ مكتوب [WEB-10]")
        for href in _pre:
            if "://" in href or href.startswith("//"):
                errs.append("‏تبكيرٌ إلى أصلٍ خارجيّ: " + href +
                            " — والصفحةُ تخدم من أصلِها وحده [CSP-01]")
                continue
            if not os.path.isfile(os.path.join(web, *href.split("/"))):
                errs.append("‏تبكيرٌ إلى ملفٍّ ليس في الشجرة: " + href +
                            " — رحلةٌ تُدفع لتقبض 404، وتبكيرٌ يُبطِئ بدل أن يُسرِع [WEB-10]")
        # ‏**والخطُّ خاصّةً: تبكيرٌ بلا `crossorigin` يضاعف التنزيل ولا يوفّر.**
        # الخطوطُ تُجلَب في وضع CORS مجهولٍ حتّى من أصلِها، فطلبُ التبكير
        # بلا الرّاية لا يطابق طلبَ `@font-face` فيُنزّل الملفُّ مرّتَين. وهذا
        # عطبٌ **يبدو ناجحًا**: الخطُّ يظهر، والكلفةُ وحدها تضاعفت.
        for m in re.finditer(r'<link\s[^>]*\sas="font"[^>]*>', _page):
            if "crossorigin" not in m.group(0):
                errs.append("‏تبكيرُ خطٍّ بلا `crossorigin` — يُنزّل الخطُّ مرّتَين "
                            "والمظهرُ سليم [WEB-10]")

    mpath = os.path.join(web, "manifest.json")
    try:
        man = json.loads(open(mpath, encoding="utf-8").read())
    except (OSError, ValueError) as e:
        errs.append("تعذّرت قراءةُ manifest.json: " + str(e))
        man = {}
    for key in ("name", "short_name"):
        if man.get(key) != "محراب":
            errs.append("manifest." + key + " = " + repr(man.get(key)) +
                        " — «تثبيتُ التطبيق» يعرض اسمًا ليس اسمَنا")
    if man.get("lang") != "ar":
        errs.append("manifest.lang = " + repr(man.get("lang")) +
                    " فوق صفحةٍ تقول lang=\"ar\"")
    if man.get("dir") != "rtl":
        errs.append("manifest.dir = " + repr(man.get("dir")) + " لا rtl")

    for name, _src in ICONS:
        p = os.path.join(web, name)
        if not os.path.isfile(p):
            errs.append("أيقونةٌ مفقودة: " + name)
            continue
        with open(p, "rb") as f:
            head = f.read(8)
        want = b"\x89PNG" if name.endswith(".png") else b"\x00\x00\x01\x00"
        if not head.startswith(want):
            errs.append(name + " ليس من نوعه المعلَن (توقيعٌ غيرُ مطابق)")

    # تسرّبُ اسمِ المنبع في **ما يُخدَم للزائر**. لا يُستثنى `boot.js` ولا `index.html`:
    # ‏sourceMappingURL أو تعليقٌ منسيٌّ يصل المتصفّحَ كما يصله المتن.
    for name in PAGE_FILES + ("manifest.json", PRODUCT_JS):
        p = os.path.join(web, name)
        if not os.path.isfile(p):
            continue
        low = open(p, encoding="utf-8", errors="replace").read().lower()
        for leak in LEAKS:
            if leak in low:
                errs.append("«" + leak + "» في " + name + " — يصل المتصفّحَ كما هو")

    if errs:
        for e in errs:
            print("❌ " + e, file=sys.stderr)
        return 1
    print("  ✅ صفحةُ المضيف وهويّتُها سليمة (الصفحة · الإقلاع · المانيفست · الأيقونات)")
    return 0


def main(argv):
    args = [a for a in argv if a != "--verify"]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    web = args[0]
    if not os.path.isdir(web):
        return fail("ليس مجلّدًا: " + web)
    if "--verify" in argv:
        return verify(web)
    return apply(web)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
