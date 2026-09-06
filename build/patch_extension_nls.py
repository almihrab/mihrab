#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حقن ترجمة بيانات الامتدادات المدمجة إلى العربيّة — مساهمة بناء (الطبقة 2).

السبب الجذريّ: مفاتيح `package.nls.json` (عناوين الأوامر، أوصاف الإعدادات، تسميات
القوائم — الأعلى ظهورًا في «الإعدادات» و«لوحة الأوامر») لا تغطّيها حزمة اللغة المنبعيّة
(1.85) إلّا جزئيًّا. أمّا الباقي فيظهر إنجليزيًّا.

## تصحيحُ اكتشافٍ سابق — وكيف نجا الخطأ من كلّ الطبقات

كانت هذه الوحدة تكتب `contents.package` في ملفّ i18n لحزمة اللغة، بناءً على أنّ «حزمة
اللغة نشطةٌ دائمًا في محراب». وهذا **غير صحيح**، وقد وثّقه `patch_html_lang.py` نفسُه من
الجهة المقابلة: محراب لا يُسجِّل حزمةَ لغةٍ أصلًا (‏العربيّةُ **مخبوزةٌ** في
`nls.messages.json`)، فيبقى `configuration.nls.language` غيرَ معرَّف. وفي المنبع
(‏extensionsScannerService.ts:928):

    if (nlsConfiguration.devMode || nlsConfiguration.pseudo || !nlsConfiguration.language)
        return c({ localized: joinPath(extensionLocation, 'package.nls.json'), original: null });

⇒ **‏`package.nls.json` وحدَه هو ما يُقرأ.** ومسارُ حزمة اللغة لا يُسلَك (لا `translations`)،
ومسارُ `package.nls.ar.json` لا يُسلَك كذلك (الحلقةُ لا تبدأ بلا لغة). فكان الفرعان
اللذان تكتبهما هذه الوحدةُ **ميّتَين معًا**، والقياسُ الحيُّ أعطى `0/1602` عربيًّا فيما
يُصيَّر — بينما كان السطرُ يقول «1602/1602 (100%)».

ولماذا لم يمسكه شيء: العدّادُ كان يعدّ ما **يُنوى كتابتُه** لا ما يُقرأ. مقياسٌ يقيس
نفسَه فينجح دائمًا. فالعلاجُ شقّان — الكتابةُ في المسار المقروء، **والعدُّ من الملفّ
المكتوب بعد كتابته**. (وحرسُ ما بعد البناء في build.sh يقرأ المشحون لا سطرَنا هذا.)

## الحلّ

لكلّ امتدادٍ مدمجٍ له `package.nls.json`:
  1. تُحفَظ الإنجليزيّةُ الأصليّةُ مرّةً في `.mihrab-nls-orig.json` — وهي **مصدرُ المفاتيح
     والارتداد** في كلّ تشغيلةٍ بعدها. بها تصير الوحدةُ متساكنةً حتّى على شجرةٍ مُحقونةٍ
     في المكان (كان الفخُّ السابق: قراءةُ قيمنا المحقونة كأنّها «الأصل»).
  2. تُبنى خريطةٌ عربيّةٌ كاملة لكلّ مفتاح، بالأسبقيّة: الترجمةُ الرسميّةُ من حزمة اللغة
     (من نسختها الأصليّة `*.i18n.orig.json`) ⟵ التكميليُّ `mihrab_ext_nls_ar.json`
     (بمفتاح نصّ الإنجليزيّة) ⟵ الإنجليزيّة.
  3. **تُطبَّع الهويّةُ** في كلّ قيمةٍ عبر `mihrab_brand.rebrand` — الترجمةُ المنبعيّةُ
     كُتبت لـVSCodium، وبقاءُ الاسم فيها تسرّبُ هويّةٍ يقرؤه المستخدم.
  4. تُكتب الخريطةُ في `package.nls.json` (**المسارُ المقروء فعلًا**)، وأيضًا في
     `package.nls.ar.json` و`contents.package` لحزمة اللغة — لا تكرارًا بل تحصينًا:
     أيُّ تسجيلِ حزمةِ لغةٍ لاحقٍ أو تمريرِ `--locale=ar` يجد العربيّةَ نفسَها لا
     إنجليزيّةً مختلفةً عمّا على الشاشة.

**إبطال الكاش (كاشان منفصلان):**
  1. كاش مسح الامتدادات المدمجة (extensions.builtin.cache): مفتاحه يشمل mtime مجلّد
     الامتدادات ⇒ يُبطَل تلقائيًّا مع بناء جديد الطابع الزمنيّ.
  2. كاش ترجمة حزمة اللغة (%APPDATA%/clp): مفتاحه md5(extId+**version**) — ثابت عبر
     إعادة البناء ولا يحرّكه mtime. لذا **bake_nls_arabic.py يرفع نسخة language-pack-ar من
     بصمة محتوى تشمل ملفّات i18n المحقونة هنا** (يجب أن يعمل هذا المرقِّع **قبل** bake_nls).
     انظر [[mihrab-stale-clp-language-cache-gotcha]].

الاستعمال: python patch_extension_nls.py <مسار resources/app>  (قبل bake_nls_arabic.py)
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mihrab_brand as brand  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

LANG = "ar"
LP_DIR = "language-pack-" + LANG  # مجلّد حزمة اللغة داخل extensions/
#: محارفُ العربيّة الأساسيّة — شاهدُ «هل هذه القيمةُ معرَّبةٌ فعلًا؟» في العدّ الصادق.
ARABIC = re.compile(r"[؀-ۿ]")
#: أدنى نسبةٍ مقبولةٍ لِما يُصيَّر. القياسُ قبل الإصلاح كان 0%، وبعده 98%. العتبةُ منخفضةٌ
#: عمدًا — مهمّتُها الإمساكُ بسقوط **فئةٍ كاملة** لا بانحدارِ سلسلةٍ أو سلسلتين.
MIN_PCT = 50
#: وعتبةٌ **لكلّ امتدادٍ ذي وزن**: النسبةُ المجمَّعةُ تُخفي سقوطَ امتدادٍ كاملٍ خلف نجاح
#: التسعين الباقية. وليست هذه فرضيّةً: أوّلُ بناءٍ بعد إضافتها أمسك انحدارًا حقيقيًّا —
#: ‏`ms-vscode.js-debug` سقط إلى **0/226** بينما المجموعُ 76% (فوق `MIN_PCT` بارتياح).
#: القياسُ اليوم: أدنى امتدادٍ ذي وزنٍ **97%**. فالعتبةُ 40 هامشٌ واسعٌ عمدًا — مهمّتُها
#: انهيارُ فئةٍ لا انحدارُ سلسلة، وعتبةٌ ضيّقةٌ مخترَعةٌ تُحمِّر على انجراف المنبع بلا سبب.
MIN_EXT_KEYS = 40
MIN_EXT_PCT = 40
#: شاهدٌ يجب أن **يوجد**: غيابُ الملفّ كان يعني تخطّيَ الحرس صمتًا. أظهرُ الامتدادات
#: في الواجهة، وأوّلُ ما انكشف فيه العطب («Clone Repository» إنجليزيّةً وسط عربيّة).
WITNESS = "git"
#: ‏[WEB-08] **والشجرةُ الثابتة تشحن غيرَ ما يشحنه المكتبيّ.** امتدادُ `git` كاملًا
#: يحتاج عمليّةً، فلا يدخل بناءَ المتصفّح إطلاقًا — والشاهدُ المكتبيُّ يفشل هناك على
#: شجرةٍ سليمةٍ تمامًا. وهذا أسوأُ من ثغرة: حارسٌ يُحمِّر بلا عطب يُدرَّب المرءُ على
#: تجاهله، فيصير أوّلَ ما يُتخطّى يومَ يُحمِّر بحقّ.
#:
#: و`markdown-language-features` شاهدٌ لأنّه يستوفي شروطَ الشاهد نفسَها في تلك الشجرة:
#: يُشحَن فيها دائمًا (لا عمليّةَ يحتاجها)، ظاهرٌ في الواجهة (معاينةُ ماركداون —
#: وهي سطحُ الجولات نفسِه)، وله `package.nls.json` بمفاتيحَ ذاتِ وزن.
#:
#: والاختيارُ **يُقاس ولا يُمرَّر رايةً**: رايةٌ تُنسى في نداءٍ واحدٍ تُسكِت الشاهدَ
#: صامتةً، وشكلُ الشجرة حقيقةٌ في القرص لا نيّةٌ في سطر أمر.
WITNESS_WEB = "markdown-language-features"
#: علامةُ الشجرة الثابتة: حزمةُ الورشة التي لا وجودَ لها في مخرَجٍ مكتبيّ.
WEB_TREE_MARK = os.path.join("out", "vs", "workbench", "workbench.web.main.internal.js")


def _witness_for(app):
    """الشاهدُ المناسبُ لشكل الشجرة — من القرص لا من راية."""
    return WITNESS_WEB if os.path.isfile(os.path.join(app, WEB_TREE_MARK)) else WITNESS


def _read_json(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return json.load(f)


def _write_json_atomic(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def _has_arabic(obj):
    """هل في البنية محرفٌ عربيٌّ واحدٌ على الأقلّ؟ (مُميِّزُ «حُقِن هذا الملفّ سلفًا؟»)"""
    return bool(ARABIC.search(json.dumps(obj, ensure_ascii=False)))


def _snapshot_pack(live, backup):
    """لقطةُ ملفّ i18n لحزمة اللغة: تُنشَأ عند أوّل مرورٍ وتُقرأ بعده.

    لا تصلح هنا قاعدةُ «الخالي من العربيّة هو الأصل» التي تحرس `package.nls.json`:
    أصلُ حزمة اللغة **عربيٌّ بطبعه**، فالمُميِّزُ لا يميّز. اللقطةُ الأولى هي المرجع.
    """
    if os.path.isfile(backup):
        return _read_json(backup)
    data = _read_json(live)
    _write_json_atomic(backup, data)
    return data


#: اسمُ نسخةِ الأصل الإنجليزيّ. **ليس `package.nls.en.json`** — وهذا فرقٌ وظيفيٌّ لا ذوقيّ.
#:
#: ‏`findMessageBundles` (‏extensionsScannerService.ts:911) يبحث عن `package.nls.${locale}.json`
#: **متى كانت هناك لغةٌ محلولة**، فيصعد من `en-GB` إلى `en`. فملفٌّ اسمُه `package.nls.en.json`
#: ليس نسخةً احتياطيّةً بل **حزمةُ لغةٍ إنجليزيّةٌ مُعلَنة**: يكفي `--locale=en` كي يُختار،
#: فيقرأ مستخدمُ محرابٍ إنجليزيّةً تسمّي له VSCodium. كان الملفُّ الوحيدَ عندنا على مسارٍ حيٍّ
#: بعلَمٍ واحد. والاسمُ المنقوطُ خارجَ نمط `package.nls.*` لا يطلبه المُحلِّل مهما كانت اللغة.
ORIG_NAME = ".mihrab-nls-orig.json"

#: الاسمُ القديم — يُهاجَر لا يُترَك: شجرةٌ رُقِّعت قبل هذا التغيير تحمله، وحيُّها عربيٌّ
#: محقون. فلو تُجوهِل لَبحث `_snapshot` عن نسخةٍ فلم يجدها ورمى، فتخسر الشجرةُ ترجمتَها.
_LEGACY_ORIG = "package.nls.en.json"


def _orig_path(ext_dir):
    """مسارُ نسخة الأصل، مع ترحيلِ الاسم القديم مرّةً واحدةً إن وُجد."""
    new = os.path.join(ext_dir, ORIG_NAME)
    old = os.path.join(ext_dir, _LEGACY_ORIG)
    if os.path.isfile(old):
        if os.path.isfile(new):
            os.remove(old)          # الجديدُ هو المرجع؛ القديمُ يُزال من المشحون
        else:
            os.replace(old, new)
    return new


def _snapshot(live, backup):
    """يعيد **الأصلَ الإنجليزيّ**، مُنشِئًا نسختَه الاحتياطيّةَ عند الحاجة.

    هذا هو مِفصلُ التساكن كلِّه: بعد أوّل تشغيلةٍ يصير `live` عربيًّا، فقراءةُ الأصل منه
    تجعل التشغيلةَ الثانيةَ تعامل العربيّةَ كأنّها الإنجليزيّةُ المصدر — فتنكسر المفاتيح
    وتُجمَّد أيُّ ترجمةٍ جديدةٍ في التكميليّ.

    والقاعدةُ **حالُ الملفّ الحيّ لا مجرّدُ وجودِ نسخةٍ احتياطيّة**: إن كان الحيُّ خاليًا
    من العربيّة فهو الأصلُ بذاته (منبعٌ جديدٌ نُصِّب فوق شجرةٍ قديمة) ⇒ تُحدَّث النسخة.
    وإلّا فالحيُّ حقنُنا ⇒ تُقرأ النسخة. بلا هذا الشرط تبتلع نسخةٌ بائتةٌ كلَّ مفتاحٍ
    أضافه المنبعُ صمتًا، فيظهر `%key%` خامًا على الشاشة — وكانت سلامتُنا منه معلَّقةً
    على `rm -rf` في سكربتٍ آخر، لا على شرطٍ في هذه الوحدة.
    """
    data = _read_json(live)
    if not _has_arabic(data):
        _write_json_atomic(backup, data)   # الحيُّ هو الأصل: النسخةُ تتبعه لا العكس
        return data
    if os.path.isfile(backup):
        return _read_json(backup)
    # حيٌّ عربيٌّ بلا نسخةٍ احتياطيّة: لا سبيلَ إلى الأصل. لا نُخمّن ولا نكتب فوقه.
    raise ValueError("حيٌّ مُحقَنٌ بلا نسخةٍ أصليّة — لا سبيلَ إلى الإنجليزيّة المصدر")


def _en_value(v):
    """قيمة package.nls قد تكون نصًّا أو {message, comment}."""
    if isinstance(v, dict):
        return v.get("message")
    return v if isinstance(v, str) else None


def _official_pkg(contents):
    """يستخرج ترجمة «package» الرسميّة من contents (نصوص غير فارغة فقط)."""
    out = {}
    pkg = contents.get("package", {}) if isinstance(contents, dict) else {}
    if isinstance(pkg, dict):
        for k, v in pkg.items():
            s = v if isinstance(v, str) else (v.get("message") if isinstance(v, dict) else None)
            if isinstance(s, str) and s:
                out[k] = s
    return out


def _build_map(pk, official, supp):
    """يكوّن خريطةً عربيّةً كاملةً لكلّ مفاتيح package.nls.json، مُطبَّعةَ الهويّة.

    الأسبقيّة لكلّ مفتاح: الترجمةُ الرسميّة ⟵ التكميليّ (بمفتاح نصّ الإنجليزيّة) ⟵
    الإنجليزيّة. **والتطبيعُ يشمل الارتدادَ الإنجليزيَّ أيضًا**: سلسلةٌ إنجليزيّةٌ تقول
    «VSCodium» تُصيَّر كما هي، فتسرّبُ الاسمِ لا يشترط ترجمةً.
    """
    ar_map, n_supp, n_brand = {}, 0, 0
    for key, val in pk.items():
        en = _en_value(val)
        if en is None:
            # صيغةٌ لم نتوقّعها (‏{comment} بلا message، أو قيمةٌ غيرُ نصّيّة). **تُمرَّر
            # كما هي ولا تُسقَط**: الكتابةُ استبدالٌ لا دمج، فإسقاطُ مفتاحٍ يُظهر
            # ‏`%extension.key%` خامًا على الشاشة — ولا يراه العدّاد، بل يرفع نسبتَه
            # لأنّ المقامَ هو المفاتيحُ المكتوبة. صمتٌ يتجمّل.
            ar_map[key] = val
            continue
        if key in official:
            value = official[key]
        elif en in supp:
            value = supp[en]
            n_supp += 1
        else:
            value = en
        value, nb = brand.rebrand(value)
        n_brand += nb
        ar_map[key] = value
    return ar_map, n_supp, n_brand


def _localized(s):
    """هل هذه القيمةُ **مترجَمة**؟ — لا «هل فيها محرفٌ عربيّ؟».

    الفرقُ ليس تدقيقًا: اسمُنا «محراب» عربيٌّ ونحن نحقنه في الارتداد الإنجليزيّ نفسِه.
    فسلسلةٌ إنجليزيّةٌ صِرفةٌ تقول «within VS Code» تصير «within محراب» — عربيّةُ البايت،
    إنجليزيّةُ القراءة. عدُّها مترجَمةً يجعل المقياسَ يشهد لأثر خطوةٍ أخرى، وهو بعينُه
    صنفُ العطب الذي أوجب هذا الملفّ. فنُسقِط اسمَنا قبل الحكم.
    """
    return bool(ARABIC.search(s.replace(brand.NAME, "")))


def measure(ext_dir):
    """يقرأ `package.nls.json` **المكتوبة على القرص** ويعيد قياسًا صادقًا.

    يعيد dict: {ext: (مفاتيح، مترجَمة)}، ولائحةَ تسرّبِ اسمِ التوزيعة الأمّ.
    لا يُبنى على شيءٍ في الذاكرة: مصدرُ الحكم هو ما يقرؤه المحرِّرُ لا ما نوينا كتابتَه.
    """
    per_ext, leaks = {}, []
    if not os.path.isdir(ext_dir):
        return per_ext, leaks
    for e in sorted(os.listdir(ext_dir)):
        if e.startswith("language-pack"):
            continue
        p = os.path.join(ext_dir, e, "package.nls.json")
        if not os.path.isfile(p):
            continue
        try:
            written = _read_json(p)
        except (ValueError, OSError):
            continue
        keys = ar = 0
        for v in written.values():
            s = _en_value(v)
            if not isinstance(s, str):
                continue
            keys += 1
            if _localized(s):
                ar += 1
            for r in brand.residue(s):
                leaks.append(f"{e}: {r} — «{s[:60]}»")
        per_ext[e] = (keys, ar)
    return per_ext, leaks


def verify(app, include_core=True) -> int:
    """بوّابةُ الشحن: تقرأ المشحونَ وتحكم عليه. مصدرُ حكمٍ واحدٌ لكلّ الطبقات.

    أُخرِجت من `build.sh` عمدًا: الحرسُ هناك كان `grep` على **بايتٍ عربيٍّ واحد**،
    وتطبيعُ الهويّة وحدَه (‏«within VS Code» ⇐ «within محراب») كان يُرضيه ولو كانت
    الواجهةُ إنجليزيّةً بالكامل — نجاحٌ كاذبٌ من صنف العطب الذي أُنشئ الحرسُ لمنعه.
    وكان يفشل على macOS أيضًا: `\\|` في النمط امتدادُ GNU لا يعرفه grep البِسْديّ.
    """
    ext_dir = os.path.join(app, "extensions")
    # تسرّبُ `package.nls.json` لا يُقرأ من هنا: `scan_shipped` أدناه يغطّيه ويغطّي معه
    # كلَّ سطحٍ آخر — ومصدرُ حكمٍ واحدٌ للهويّة أصحُّ من اثنين يتباعدان.
    per_ext, _leaks = measure(ext_dir)
    bad = []

    keys = sum(k for k, _a in per_ext.values())
    ar = sum(a for _k, a in per_ext.values())
    # **الصفرُ ليس نجاحًا**: لولا هذا الشرط لَمرّ بناءٌ غيّر فيه المنبعُ تخطيطَ الامتدادات
    # (فلم يُعثَر على أيّ `package.nls.json`) وهو أخضرُ بلا تعريبٍ ولا فحصِ تسرّبٍ أصلًا.
    if not keys:
        bad.append("لا مفاتيح package.nls.json في المشحون — تغيّر تخطيطُ الامتدادات المدمجة؟")
    else:
        pct = ar * 100 // keys
        if pct < MIN_PCT:
            bad.append(f"المجموع: {ar}/{keys} مفتاح مترجَم ({pct}%) — الحدّ {MIN_PCT}%")
    # الشاهدُ يجب أن يوجد: غيابُه كان يعني تخطّيَ الحرس صمتًا. ويُختار بشكل الشجرة
    # [WEB-08]: `git` لا يدخل بناءَ المتصفّح أصلًا (يحتاج عمليّة).
    witness = _witness_for(app)
    if witness not in per_ext:
        bad.append(f"الامتدادُ الشاهد «{witness}» بلا package.nls.json في المشحون")
    # وعتبةٌ لكلّ امتدادٍ ذي وزن: النسبةُ المجمَّعةُ تُخفي سقوطَ امتدادٍ كاملٍ خلف نجاح غيره.
    for e, (k, a) in sorted(per_ext.items()):
        if k >= MIN_EXT_KEYS and a * 100 // k < MIN_EXT_PCT:
            bad.append(f"{e}: {a}/{k} ({a * 100 // k}%) — دون حدّ الامتداد {MIN_EXT_PCT}%")
    # **والهويّةُ تُفحَص في كلّ سطحٍ مشحون لا في المقروء وحدَه.** المسارُ المقروء اليومَ
    # (‏`package.nls.json`) محروسٌ أعلاه؛ وما كُتب تحصينًا — `package.nls.ar.json` وملفّاتُ
    # حزمة اللغة — كان بلا حارسٍ أصلًا، وهو **حيٌّ بإعدادٍ واحد** (‏`nls.language` يُسجِّل
    # الحزمةَ فيُقرأ i18n بدل package.nls). حمايةُ المقروءِ وحدَه حمايةٌ بتاريخِ صلاحيّة.
    shipped_leaks, scan = brand.scan_shipped(app, include_core=include_core)
    if not include_core:
        # **التأجيلُ يُقال ولا يُسكَت عنه**: حارسٌ يتخطّى سطحًا بصمتٍ لا يُميَّز عن حارسٍ
        # فحصه ووجده نظيفًا. والسطحُ المؤجَّلُ محروسٌ فعلًا — في (ي-2) بعد الخبز.
        print(f"  ⏭️ نواةُ nls.messages مؤجَّلةٌ إلى ما بعد الخبز ({scan.get('_deferred_core', 0)} ملفًّا)"
              " — تُحرَس في (ي-2) بـ--verify.")
    for lk in shipped_leaks[:8]:
        bad.append("تسرّبُ اسمِ التوزيعة الأمّ ⇐ " + lk)
    if len(shipped_leaks) > 8:
        bad.append(f"… و{len(shipped_leaks) - 8} تسرّبًا آخر")
    # **وكلُّ ملفٍّ على مسار حلِّ اللغة سطحٌ مُصيَّر، سُمّي نسخةً احتياطيّةً أو لم يُسمَّ.**
    # ‏`findMessageBundles` يطلب `package.nls.${locale}.json` لأيّ لغةٍ يمرّرها المستخدم،
    # فوجودُ ملفٍّ بهذا النمط لغةٍ لا نشحنها يعني شاشةً لم يقسها أحد. المسموحُ لغتُنا وحدَها.
    stray = []
    for e in sorted(os.listdir(ext_dir)):
        d = os.path.join(ext_dir, e)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if (fn.startswith("package.nls.") and fn.endswith(".json")
                    and fn not in ("package.nls.json", "package.nls." + LANG + ".json")):
                stray.append(f"{e}/{fn}")
    for s in stray[:5]:
        bad.append(f"حزمةُ لغةٍ غيرُ مقصودةٍ على مسار الحلّ: {s} — يكفي «--locale» لإظهارها")
    if len(stray) > 5:
        bad.append(f"… و{len(stray) - 5} ملفًّا آخر")
    # **الصفرُ ليس نجاحًا هنا أيضًا**: مسحٌ لم يجد ملفّاتٍ يُخرِج «بلا تسرّب» وهو أعمى.
    # فيُشترَط شاهدٌ من كلّ صنفٍ نكتبه — أيُّ صنفٍ يختفي يعني تغيّرَ تخطيطٍ لا نظافةً.
    # والصنفُ المؤجَّلُ يُشترَط له **شاهدُ تأجيلٍ موجب**: أن يكون المسحُ قد رآه وأجّله عمدًا،
    # لا أن يكون لم يجده. فلو اختفت النواةُ من التخطيط لصار `_deferred_core` صفرًا فيُبلَّغ
    # — وإلّا لصار التأجيلُ بابًا يمرّ منه «الصفرُ نجاحٌ» الذي بُني هذا الحارسُ لمنعه.
    kinds = ["package.nls.json", "package.nls.ar.json", "i18n", "nls.messages"]
    if not include_core:
        kinds.remove("nls.messages")
        if not scan.get("_deferred_core"):
            bad.append("مسحُ الهويّة لم يرَ نواةَ nls.messages أصلًا ليؤجّلها — تخطيطٌ تغيّر، والمسحُ أعمى")
    for kind in kinds:
        if not scan.get(kind):
            bad.append(f"مسحُ الهويّة لم يجد سطحًا من صنف «{kind}» — تخطيطٌ تغيّر، والمسحُ أعمى")

    if bad:
        print("❌ بوّابةُ تعريب بيانات الامتدادات — لا يُشحَن هكذا:", file=sys.stderr)
        for b in bad:
            print("   ✗ " + b, file=sys.stderr)
        return 1
    scanned = sum(v for k, v in scan.items() if k != "_hinges")
    print(f"✅ بوّابةُ الامتدادات: {ar}/{keys} مفتاح مترجَم "
          f"({ar * 100 // keys}%) في {len(per_ext)} امتداد، بلا تسرّبِ هويّة.")
    print(f"   مسحُ الهويّة: {scanned} سطحًا مُصيَّرًا نظيفًا "
          f"(‏{scan.get('i18n', 0)} i18n · {scan.get('package.nls.ar.json', 0)} nls.ar)، "
          f"و{scan['_hinges']} ملفَّ أصلٍ مستثنًى بالاسم.")
    return 0


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--verify":
        return verify(sys.argv[2])
    if len(sys.argv) != 2:
        print("الاستعمال: python patch_extension_nls.py [--verify] <مسار resources/app>",
              file=sys.stderr)
        return 2
    app = sys.argv[1]
    ext_dir = os.path.join(app, "extensions")
    if not os.path.isdir(ext_dir):
        print(f"⚠️ لا مجلّد extensions في {app} — تُخطّى ترجمة البيانات.", file=sys.stderr)
        return 0

    # الملفّ التكميليّ (ملكيّة محراب): إنجليزيّ→عربيّ مسطّح.
    supp = {}
    supp_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mihrab_ext_nls_ar.json")
    if os.path.isfile(supp_file):
        try:
            raw = _read_json(supp_file)
            supp = {k: v for k, v in raw.items()
                    if isinstance(k, str) and isinstance(v, str) and v and not k.startswith("//")}
        except (ValueError, OSError) as e:
            print(f"⚠️ الملفّ التكميليّ للبيانات تالف ({supp_file}): {e} — يُتخطّى.", file=sys.stderr)

    # فهرس ملفّات i18n لحزمة اللغة بالاسم الأساس (المفتاح = ${publisher}.${name} عادةً).
    lp_tr_dir = os.path.join(ext_dir, LP_DIR, "translations", "extensions")
    tr_index = {}
    if os.path.isdir(lp_tr_dir):
        for f in os.listdir(lp_tr_dir):
            if f.endswith(".i18n.json"):
                tr_index[f[:-len(".i18n.json")]] = os.path.join(lp_tr_dir, f)

    total_ext = total_supp = total_brand = n_langpack = 0
    for e in sorted(os.listdir(ext_dir)):
        if e.startswith("language-pack"):
            continue
        ed = os.path.join(ext_dir, e)
        pnls = os.path.join(ed, "package.nls.json")
        if not os.path.isfile(pnls):
            continue
        # الأصلُ الإنجليزيُّ مرجعُ المفاتيح والارتداد في كلّ تشغيلة (تساكنٌ في المكان).
        try:
            pk = _snapshot(pnls, _orig_path(ed))
        except (ValueError, OSError):
            continue

        # المعرّف الحقيقيّ = publisher.name من package.json (حتميّ)، لا تخمين بلاحقة المجلّد.
        pub_id = None
        try:
            pj = _read_json(os.path.join(ed, "package.json"))
            if isinstance(pj.get("publisher"), str) and isinstance(pj.get("name"), str):
                pub_id = f"{pj['publisher']}.{pj['name']}"
        except (ValueError, OSError):
            pub_id = None
        cand = ([pub_id] if pub_id else []) + [f"vscode.{e}", e]
        i18n_path = next((tr_index[c] for c in cand if c in tr_index), None)

        official, doc = {}, None
        if i18n_path:
            try:
                # الترجمةُ الرسميّةُ تُقرأ من النسخة الأصليّة لا من الملفّ الحيّ: الحيُّ يحمل
                # حقنَنا السابق، وقراءتُه تُجمّد التكميليَّ عند أوّل تشغيلة.
                orig = _snapshot_pack(
                    i18n_path, i18n_path[:-len(".i18n.json")] + ".i18n.orig.json")
                official = _official_pkg(orig.get("contents", {}))
                doc = _read_json(i18n_path)
            except (ValueError, OSError):
                print(f"⚠️ ملفّ i18n تالف يُتخطّى: {i18n_path}", file=sys.stderr)
                doc = None

        ar_map, n_supp, n_brand = _build_map(pk, official, supp)
        if not ar_map:
            continue

        # (1) **المسارُ المقروء فعلًا** حين لا حزمةَ لغةٍ مسجَّلة — وهو حالُ محراب دائمًا.
        _write_json_atomic(pnls, ar_map)
        # (2+3) تحصينٌ لِما لو سُجِّلت حزمةُ لغةٍ أو مُرِّر --locale=ar: المساران الآخران
        #       يحملان النصَّ نفسَه، فلا تختلف الشاشةُ عن نفسها بحسب كيفيّة الإقلاع.
        _write_json_atomic(os.path.join(ed, "package.nls." + LANG + ".json"), ar_map)
        if doc is not None:
            contents = doc.setdefault("contents", {})
            if not isinstance(contents, dict):
                contents = doc["contents"] = {}
            # سائرُ المفاتيح (contents.dist/main = ترجمةُ الشيفرة) تُصان وتُطبَّع هويّتُها.
            contents, nb = brand.rebrand_tree(contents)
            doc["contents"] = contents
            contents["package"] = ar_map
            _write_json_atomic(i18n_path, doc)
            n_brand += nb
            n_langpack += 1

        total_ext += 1
        total_supp += n_supp
        total_brand += n_brand

    # ── العدُّ الصادق: من الملفّات **المكتوبة** بعد كتابتها، لا من نيّة الكتابة ──
    # هذا نصفُ الإصلاح لا زينتُه. العدّادُ القديم كان يعدّ مفاتيحَ الخريطة التي بناها
    # ويسمّيها «مترجَمة»، فأعطى 100% بينما المُصيَّرُ 0%. والحكمُ نفسُه (`verify`) يُستدعى
    # من `build.sh` على المشحون — دالّةٌ واحدةٌ لا عتبتان تفترقان.
    per_ext, _leaks = measure(ext_dir)
    rendered_keys = sum(k for k, _a in per_ext.values())
    rendered_ar = sum(a for _k, a in per_ext.values())
    pct = (rendered_ar * 100) // rendered_keys if rendered_keys else 0
    print(
        f"✅ حُقِنت ترجمة بيانات الامتدادات: {total_ext} امتداد "
        f"({n_langpack} منها في حزمة اللغة أيضًا) — "
        f"‹المُصيَّر فعلًا› {rendered_ar}/{rendered_keys} مفتاح مترجَم ({pct}%) "
        f"في package.nls.json. تكميليّ-محراب={total_supp}، تطبيعُ هويّة={total_brand}."
    )
    # مسارُ الحقن يسبق الخبزَ، فلا يُحاسِب على النواة. و`--verify` (بعد الخبز) يُحاسِب.
    return verify(app, include_core=False)


if __name__ == "__main__":
    sys.exit(main())
