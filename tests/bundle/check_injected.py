#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L2 — تأكيدات ما بعد البناء: الكود المحقون وصل الحزمة المشحونة فعلًا (ثوانٍ).

L1 يضمن أنّ الرُقَع **طبَّقت على المصدر**؛ L2 يضمن أنّها **نجت من التحزيم/التصغير** إلى
`workbench.desktop.main.{js,css}` المشحون، وأنّ الـartifacts سليمة (exe، عربيّ افتراضيّ).

**تغطية تمثيليّة لا شاملة:** يفحص العلامات القابلة للاكتشاف نصّيًّا (أصناف CSS + سلاسل JS
حرفيّة تنجو من التصغير). الرُقَع العدديّة/المنطقيّة (minimap setLeft، margin، viewLayout…)
لا تُخلّف سلاسل ⇒ تغطّيها الطبقة الوقتيّة L3. سقوط فئة كاملة يُمسَك هنا.

الاستعمال: python tests/bundle/check_injected.py   (يتطلّب بناءً؛ يتخطّى بلطف إن غاب)
"""
import filecmp
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))  # tests/
import patch_manifest as M  # noqa: E402
# وجهة التوزيع. الافتراضيّ هو ما ينتجه build/build.sh؛ و`MIHRAB_DIST_ROOT` يسمح بفحص
# حزمةٍ غُلِّفت في مجلّد آخر — لزِمنا حين حجب قفلُ نظام ملفّات (مقبض مُسرَّب لا تملكه أيّ
# عمليّة) المجلّدَ المعتاد، فغلّفنا جانبًا. لا يغيّر ما يُفحَص، بل أين يُقرأ.
# **يُشتقّ من المنصّة لا يُثبَّت.** كان `VSCode-win32-x64` حرفيًّا، فعلى لينكس — وهي
# المنصّةُ التي تُنتج بناءَ الويب المنشور — لا يوجد المجلّدُ فيصير `packaged=False`
# فتُتخطّى **كلُّ** فحوص `@check` وتُحسَب نجاحًا. أي أنّ خمسةً وسبعين حارسًا يصمتون
# على المنصّة التي يهمّ فيها أن يتكلّموا. والاصطلاحُ يطابق `build/build.sh`.
def _default_dist():
    import platform
    sysname = platform.system()
    arch = {"AMD64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(
        platform.machine(), "x64")
    name = {"Windows": f"VSCode-win32-{arch}",
            "Linux":   f"VSCode-linux-{arch}",
            "Darwin":  f"VSCode-darwin-{arch}"}.get(sysname, f"VSCode-win32-{arch}")
    return os.path.join(ROOT, ".upstream", name)


DIST = os.environ.get("MIHRAB_DIST_ROOT") or _default_dist()
# macOS: المخرَجُ حزمةُ `.app` واسمُها عربيٌّ مشتقٌّ من nameLong، فيُحلّ بالبحث.
if not os.path.isdir(os.path.join(DIST, "resources")) and os.path.isdir(DIST):
    import glob as _g
    _apps = _g.glob(os.path.join(DIST, "*.app", "Contents", "Resources", "app"))
    if _apps:
        DIST = os.path.dirname(os.path.dirname(_apps[0]))
APP = os.path.join(DIST, "resources", "app")
OUT = os.path.join(APP, "out")
# **مصدر بديل لعلامات الحزمة — مكافئ لا تنازل.** مهمّة L2 المُعلَنة أعلاه هي أنّ الحقن
# «نجا من التحزيم/التصغير». وناتج التصغير هو `out-vscode-min/`، ومهمّة التحزيم في
# ‏`build/gulpfile.vscode.ts:262` تنسخه حرفيًّا: `gulp.src(out + '/**')` ثمّ إعادة تسمية
# المجلّد إلى `out/` فقط — بلا أيّ تحويل للمحتوى. فملفّا workbench.desktop.main.{js,css}
# في الاثنين **متطابقان بايتيًّا بالبناء**، ومِجَسّاتُنا نصّيّة عليهما وحدهما.
# فحين تغيب الحزمة (أو يفشل تغليفها لسببٍ بيئيّ كقفل ملفّ) نقرأ ناتج التصغير مباشرةً:
# تغطية العلامات تبقى كاملة، ويبقى ما يحتاج الحزمة فعلًا (exe، أصول win32، الامتدادات
# المشحونة) متخطّىً بصراحة لا مُدّعىً. الترتيب: الحزمة أوّلًا حين توجد.
MIN_OUT = os.path.join(ROOT, ".upstream", "vscode", "out-vscode-min")


def _bundle_pair(rel):
    """مسار (js|css) الحزمة إن وُجد، وإلّا ناتج التصغير المكافئ بايتيًّا."""
    packaged = os.path.join(OUT, *rel)
    return packaged if os.path.isfile(packaged) else os.path.join(MIN_OUT, *rel)


JS = _bundle_pair(("vs", "workbench", "workbench.desktop.main.js"))
CSS = _bundle_pair(("vs", "workbench", "workbench.desktop.main.css"))
EXE = os.path.join(DIST, "Mihrab.exe")
# هوية بصريّة: مجلّد أصول win32 في الحزمة المشحونة (يُقارَن بالمصدر عبر M.BRANDING_ASSETS).
WIN32_OUT = os.path.join(APP, "resources", "win32")

# (وصف، ملفّ، سلسلة يجب وجودها، أدنى عدد)
BUNDLE_MARKERS = [
    # JS — طبقة النواة (الطبقة 3)
    ("workbench dir=rtl (القشرة عربيّة الاتّجاه)", JS, 'setAttribute("dir","rtl")', 1),
    ("استيراد ورقة mihrab-rtl في workbench", JS, "mihrab-rtl", 1),
    # اتّجاهُ نصّ المحرّر: **المِجَسُّ يتبع المُنفِّذ لا الغرض**. كان `.cursors-layer .cursor`
    # يشهد لـ`patch_editor_rtl.py` (تسع ملفّات)؛ وقد حلّت محلّه رُقعةُ المنبع
    # \u200F`010-editor-text-direction.patch`، فسقط المِجَسُّ على أوّل بناءٍ بعدها — أي أنّه صار
    # يُحمِّر **الطريقةَ القديمة** لا غيابَ الميزة. فنشهد بمعرّف الإعداد نفسِه: سلسلةٌ
    # حرفيّةٌ لا يمسّها المُصغِّر، ولا يولّدها المنبعُ قبل الرُقعة (عُدَّت: 3).
    ("محرّر: خيارُ اتّجاه النصّ (رُقعة المنبع م-٢)", JS, "editor.textDirection", 1),
    ("محرّر: تمرير لاصق RTL (sticky content)", JS, "sticky-line-content", 1),
    # مِجَسّ الشعار (ASCII، يصمد أمام التصغير) يثبت أنّ **رُقعة الترويسة شُحنت**. لا يثبت نصّ
    # الجملة نفسه (esbuild يهرّب غير-ASCII إلى \\uXXXX ⇒ لا عربيّة حرفيّة في الحزمة، تحقّقنا).
    # نصّ الجملة يتحقّق منه L1 (السلسلة حرفيًّا في المصدر المُرقَّع) وL3 الوقتيّ (نصّ العنوان الفرعيّ).
    ("ترحيب: عنصر شعار القوس (ترويسة Get Started)", JS, "mihrab-welcome-mark", 1),
    ("ترحيب: طبقة الزخرفة النجميّة المحيطيّة", JS, "mihrab-welcome-pattern", 1),
    ("ترحيب: الشطر الثاني من الجملة (صوتٌ ثانٍ)", JS, "mihrab-welcome-lede", 1),
    # اتّجاهُ لوح شرح الجولة (م-١٦). **لا نشهد باسم المتغيّر** (`mihrabDir` محلّيٌّ يُعيد
    # المُصغِّرُ تسميتَه)، بل بالشظيّة الحرفيّة التي يخرج بها القالبُ نفسُه: `<html dir=` —
    # نصٌّ داخل قالبٍ لا يمسّه التصغير، ولا يولّده المنبعُ قبل الرقعة (عُدَّ: 0).
    ("ترحيب: لوحُ شرح الجولة يرث اتّجاهَ مضيفه (م-١٦)", JS, '<html dir=', 1),
    # والحشوةُ المنطقيّة شاهدٌ ثانٍ مستقلّ: بدونها يبقى نصفُ العطب (اتّجاهٌ صحيحٌ وفجوةٌ
    # في الجهة الخطأ) بينما يخضرّ المِجَسُّ الأوّل — وهو عينُ النجاح الكاذب.
    ("ترحيب: فجوةُ لوح الجولة منطقيّةٌ لا فيزيائيّة", JS, "padding-inline-end: 32px", 1),
    # إسقاط جولات المنبع التعريفيّة. **مِجَسٌّ على المعرّف وحده يُخدَع**: 'Setup' وأخواتها
    # موجودة في الحزمة قبل الرُقعة وبعدها (تعريف الجولات باقٍ — رشّحناه عند التسجيل لا
    # حذفناه). و**اسم المتغيّر لا يصلح** أيضًا: المُصغِّر يُعيد تسمية المحلّيّات. فنطابق
    # **قائمة الإسقاط بترتيبها** — سلسلة لا يولّدها المنبع، وتُولَّد بلا مسافات في المصدر
    # فتطابق المُصغَّر حرفيًّا (انظر _IDS_JS في patch_walkthroughs_drop.py).
    ("ترحيب: ترشيح جولات المنبع قبل التسجيل", JS, '["Setup","SetupWeb","Beginner"]', 1),
    # افتراضُ الحوار المشروط. المِجَسُّ يشمل **اسمَ الإعداد** لا `default:"custom"` وحده:
    # الأخيرُ يرِد لإعداداتٍ أخرى (menuStyle وغيره) فينجح زورًا. عددناه على الحزمة قبل
    # الرُقعة: `…enum:["native","custom"],default:"native"` — أي 0 لصيغتنا.
    ("حوارٌ مشروط عربيّ RTL (dialogStyle=custom)", JS,
     'dialogStyle":{type:"string",enum:["native","custom"],default:"custom"', 1),
    # معجم عناوين الإعدادات. **المِجَسّ مهروبٌ لا حرفيّ**: esbuild يحوّل غيرَ-ASCII إلى
    # ‎\uXXXX بحروفٍ كبيرة، فالبحث بالحرف العربيّ يعطي صفرًا ويبدو أنّ الرقعة لم تصل —
    # وهو بلاغٌ كاذبٌ وقعنا فيه فعلًا. عُدَّ على الحزمة: «المحرّر» مهرَّبًا = 3.
    ("معجم الإعدادات: قيمةٌ عربيّةٌ مشحونة (المحرّر)", JS,
     "\\u0627\\u0644\\u0645\\u062D\\u0631\\u0651\\u0631", 1),
    # التعبيرُ النمطيّ لقاعدة الإضافة: مِجَسٌّ **مزدوجُ الغرض**. وجودُه يثبت شحنَ منطق
    # التركيب لا السلاسل وحدها؛ وصورتُه المهروبة تثبت أنّه لم يُكتَب بالحرف العربيّ —
    # وذلك كان يُسقِط البناءَ كلَّه (‏'Found non-ascii character' من optimize.ts).
    ("معجم الإعدادات: قاعدة الإضافة (تعبيرٌ نمطيٌّ مهروب)", JS,
     "\\u0627\\u0644\\S+", 1),
    # عزلُ الاتّجاه: محرفان بلا عرضٍ ولا صورة، فلا سبيلَ إلى رؤيتهما في لقطةِ شاشة —
    # وجودُهما في الحزمة هو الدليلُ الوحيدُ الممكن قبل القياس الحيّ. ونعدّ صنفَ العزل
    # في التعبير النمطيّ أيضًا: لو كُتب بالحرف لأسقط البناء.
    ("معجم الإعدادات: عزل الاتّجاه FSI", JS, "\\u2068", 1),
    ("معجم الإعدادات: صنفُ العزل مهروبٌ في التعبير النمطيّ", JS,
     "\\u2066-\\u2069", 1),
    # القاعدة 35: عزلٌ **لا** plaintext على سطحَي العنوان. المِجَسّ على القاعدة المدمَجة
    # كما يُخرِجها المُصغِّر (قِسناه على الحزمة)، لا على المصدر: esbuild يدمج المحدِّدات
    # المتجاورة. ويشمل `unicode-bidi:isolate` عمدًا — لو ارتدّت إلى plaintext لانقلب
    # ترتيبُ المقاطع (‏P2 تتخطّى ما بين FSI وPDI) وسقط المِجَسّ.
    ("CSS35: عزلُ سطحَي عنوان الإعداد (isolate لا plaintext)", CSS,
     ".setting-item-label{unicode-bidi:isolate}", 1),

    # CSS — طبقة الأنماط (mihrab-rtl.css)
    # القاعدة 13 أُسقِطت مع 1·7·14·15 (صارت أصيلةً في رُقعة المنبع)، فمِجَسُّها في **الورقة**
    # لم يعد له مشهودٌ عليه. وكان الشاهدُ البديلُ اسمَ الخيار `verticalScrollbarSide` —
    # **وقد سقط الخيارُ نفسُه من الرقعة** في جولة مراجعة microsoft/vscode: الشريطُ العموديُّ
    # يبقى يمينًا في الاتّجاهين لأنّ السطرَ اليمينيَّ يحجز عرضَه بـ`padding-right` منبعيًّا،
    # فنقلُه يحجز جهةً ويرسم في الأخرى. ومعه رُدَّت ملفّاتُ `base/browser/ui/scrollbar` إلى
    # حالة المنبع — أي أنّ الطلبَ لم يعد يمسّ طبقةَ `base` أصلًا (بندٌ كان مفتوحًا في
    # `docs/اقتراحات تعديلات المصدر/README.md` وأُغلِق هنا).
    #
    # فالشاهدُ اليومَ **معرّفُ أمر تبديل الاتّجاه**: سلسلةٌ حرفيّةٌ نملكها وحدَنا، لا يعرفها
    # المنبع، وتنجو من التصغير نجاةَ كلِّ معرّفِ أمر. وهي في الوقت نفسِه تشهد على الشيء
    # الذي يراه المستخدم: مدخلُ «اتّجاه النصّ» في قائمة العرض. (عُدَّ في المصدر: 1.)
    ("محرّر: أمرُ تبديل اتّجاه النصّ (م-٢)", JS, "editor.action.changeTextDirection", 1),
    ("CSS14: أرقام التمرير اللاصق يمينًا", CSS, "sticky-widget-line-numbers", 1),
    ("CSS15: ودجة الاقتراحات RTL", CSS, "suggest-widget{direction:rtl}", 1),
    ("CSS16: مرآة الإشعارات (مقصورة)", CSS, "notifications-toasts:not(.bottom-left)", 1),
    ("CSS16: مرآة الزرّ العائم", CSS, "floating-click-widget", 1),
    # القواعد 17 و19 و33 تسكن **ورقةً ثانية** منذ [VA-05]: `patches/mihrab-identity.css`.
    # وهي تُستورَد في workbench.ts بعد ورقة الاتّجاه، فيدمجها esbuild في ملفّ CSS نفسِه —
    # ولذلك تبقى هذه المِجَسّات الثلاثةُ صالحةً بلا تغيير. **وهي دليلُ الوصول الوحيد**: لو
    # سقط الاستيرادُ الجديد من الرُقعة لَبَقيت الحزمةُ تُبنى بلا خطأ، وسقطت هذه الثلاثةُ وحدَها.
    # **مشتقّةٌ من `M.IDENTITY_CLASSES` لا مكتوبةً**: صنفُ هويّةٍ رابعٌ يُضاف إلى المانيفست
    # ولا يُضاف هنا يبقى بلا شاهدٍ على وصوله إلى الحزمة. (الترتيبُ ثابتٌ فالوصفُ مطابق.)
    *[(f"CSS [هويّة]: {cls}", CSS, cls, 1) for cls in M.IDENTITY_CLASSES],
    # AR-03: مكدّس خطّ القشرة العربيّة — قاعدة واحدة مدمَجة لكلّ منصّة = 3 مطابقات لـ`:lang(ar)`.
    # (المنبع لا يعرّف `:lang(ar)` إطلاقًا — راجع القاعدة 20 — فالمطابقات لنا وحدنا.) الدمج
    # في قاعدة واحدة/منصّة مقصود: مُصغِّر esbuild يدمج القواعد المتجاورة ذات المحدِّد نفسه،
    # فعدّ ٦ كان سيصير ٣ بعد التحزيم ويُسقِط المِجَسّ زورًا.
    ("CSS20: مكدّس خطّ القشرة لـ:lang(ar) [AR-03]", CSS, ":lang(ar)", 3),
    # مِجَسّ الوجه العربيّ الصريح على لينكس — الثغرة الحقيقيّة التي تسدّها القاعدة (مكدّس
    # المنبع هناك بلا محارف عربيّة). سلسلة فريدة لنا لا يعرّفها المنبع.
    ("CSS20: الوجه العربيّ الصريح على لينكس [AR-03]", CSS, "Noto Sans Arabic", 1),
    # القاعدة 21: اتّجاه التسميات المحايدة. المنبع **لا يستعمل** unicode-bidi:plaintext في
    # ‏workbench/base (تحقّقنا) ⇒ كلّ مطابقة لنا. قاعدتان (صناديق الإدخال 4 + التسميات 21).
    ("CSS21: اتّجاه التسميات المحايدة (plaintext)", CSS, "unicode-bidi:plaintext", 2),
    # القاعدة 22: الرموز الاتّجاهيّة. **المِجَسّان أدناه مُختاران بعد فشل مِجَسّين ساذجين
    # على حزمةٍ حقيقيّة** — وهو بالضبط ما وُجدت L2 لأجله:
    #   ‏(١) `translateX(-3px)` سقط لأنّ مُصغِّر esbuild يعيد كتابة الدالّة إلى الشكل العامّ
    #       `translate(-3px)`. فالمِجَسّ على النصّ المصدريّ لا على ناتج التصغير كان وهمًا.
    #   ‏(٢) `codicon-breadcrumb-separator` **نجح زورًا**: المنبع نفسه يعرّف
    #       `.codicon-breadcrumb-separator{color:inherit}`، فالمِجَسّ كان يقيس المنبع لا حقننا.
    # البديلان فريدان لنا قطعًا: السالب في `translate(-3px)` (المنبع `translate(3px)`)،
    # وصنف `codicon-view-pane-container-collapsed` الذي لا ترد له قاعدة CSS ساكنة في المنبع
    # إطلاقًا (يولّده registerIcon زمن التشغيل) — عددناهما على الحزمة: ‎0‎ قبل حقننا.
    ("CSS22: قلب مثلّث الشجرة (تدرّج + اتّجاه)", CSS, "translate(-3px)", 1),
    ("CSS22: عكس الأسهم المخصَّصة للاتّجاه", CSS, "codicon-view-pane-container-collapsed", 1),
    # القاعدة 23: عكس الحشوات الفيزيائيّة في تسمية الأيقونة. القيمتان معًا بهذا الترتيب
    # لا ترِدان في المنبع (قيمته `margin: auto 16px 0 5px` فيزيائيّة، لا منطقيّة).
    ("CSS23: عكس حشوات تسمية الأيقونة", CSS, "margin-inline:5px 16px", 1),
    # القاعدة 24: محايدات bidi في اللوحات. عددنا المرشّحين على الحزمة **قبل** حقن القاعدة:
    #   suggest-input-container .view-line ‎0‎ · extension-list-item .description ‎0‎
    #   markers-panel .marker-line ‎0‎ · search-view .messages .message ‎0‎
    # واستبعدنا `pane-header>.title` — عدده ‎1‎ في المنبع، فكان سينجح زورًا كما فعل
    # `codicon-breadcrumb-separator` في القاعدة 22. المختاران صفران قطعًا.
    ("CSS24: bidi حقل بحث الامتدادات", CSS, "suggest-input-container .view-line", 1),
    ("CSS24: bidi رسائل لوحة المشاكل", CSS, "markers-panel .marker-line", 1),
    # القاعدة 25: قوائم السياق. `.monaco-menu .keybinding` فريدٌ في الحزمة (مقيس) —
    # اخترناه علامةً لأنّه لا يظهر إلّا في كتلتنا، بخلاف `.action-label` الشائع.
    ("CSS25: bidi اختصار بند القائمة", CSS, "monaco-menu .keybinding", 1),
    # القاعدة 26: الإشعارات. `.notification-list-item-source` **يعرّفه المنبع أصلًا**
    # (عدده ‎1‎ قبل الحقن — قِسناه)، فاتّخاذه علامةً عاريةً كان سينجح زورًا كما فعل
    # `codicon-breadcrumb-separator` في القاعدة 22. نُقرِنه ببادئة RTL: ‎0‎ قبل، ‎1‎ بعد.
    ("CSS26: bidi مصدر الإشعار", CSS, "[dir=rtl] .notification-list-item-source", 1),
    # القاعدة 27: التلميحات. `.monaco-hover .hover-contents` عدده ‎7‎ في المنبع، فالبادئة
    # لازمةٌ هنا أيضًا: ‎0‎ قبل الحقن، ‎2‎ بعده (الحاوية وذرّيّتها في السطرين).
    ("CSS27: bidi محتوى التلميح", CSS, "[dir=rtl] .monaco-hover .hover-contents", 2),
    # القاعدة 28: رسالة الحالة الفارغة. `.message-box-container` عدده ‎3‎ في المنبع
    # (‏markers + comments)، فالبادئة لازمة: ‎0‎ قبل الحقن، ‎2‎ بعده.
    ("CSS28: bidi رسالة الحالة الفارغة", CSS, "[dir=rtl] .message-box-container", 2),
    # القاعدة 29: شريط العنوان. `.search-label` عدده ‎1‎ في المنبع و`.window-title` ‎26‎،
    # فالعلامةُ العارية كانت ستنجح زورًا في الاثنين. بالبادئة: ‎0‎ قبل الحقن، ‎1‎ لكلٍّ بعده.
    ("CSS29: bidi تسمية مركز الأوامر", CSS, "[dir=rtl] .search-label", 1),
    ("CSS29: bidi عنوان النافذة", CSS, "[dir=rtl] .window-title", 1),
    # القاعدة 30: عدّاد نتائج البحث. `.matchesCount` عدده ‎8‎ في المنبع، والبادئةُ RTL
    # مع سلسلة الآباء تُميّز قاعدتَنا وحدها: ‎0‎ قبل الحقن، ‎1‎ بعده.
    ("CSS30: bidi عدّاد نتائج البحث", CSS,
     "[dir=rtl] .monaco-editor .find-widget .matchesCount", 1),
    # القاعدة 31: بقيّةُ ودجات الحاوية LTR. الأصنافُ الثلاثة كلُّها موجودةٌ في المنبع
    # (‏`.title` و`.dirname` و`.message` بالمئات)، فلا علامةَ عاريةً تصلح — البادئةُ RTL
    # مع سلسلة الآباء الكاملة تُميّز قواعدنا وحدها: ‎0‎ قبل الحقن، ‎1‎ لكلٍّ بعده.
    ("CSS31: bidi عنوان إجراء الكود", CSS,
     "[dir=rtl] .action-widget .monaco-list-row .title", 1),
    ("CSS31: bidi ترويسة نظرة المشاكل", CSS,
     "[dir=rtl] .zone-widget .peekview-title .dirname", 1),
    ("CSS31: bidi متن رسالة المُشخِّص", CSS,
     "[dir=rtl] .zone-widget .descriptioncontainer .message div", 1),
    # القاعدة 39: مرآةُ **داخل** ودجة البحث [VA-03]. ثلاثُ علاماتٍ لا واحدة، لأنّ العطبَ
    # كان يُقاوَم على ثلاث طبقات: قلبُ الصفّ، ثمّ نقلُ الحاوية المُطلَقة، ثمّ **قلبُ العوامة**
    # (‏`float:left` لا يبالي بالاتّجاه — وهو ما أبقى المقابضَ الثلاثة صاعدةً بعد أوّل قاعدتين).
    # كلُّ سلسلةٍ منها معدومةٌ في المنبع بالبادئة RTL: ‎0‎ قبل الحقن، ‎1‎ بعده.
    ("CSS39: مرآة صفّ ودجة البحث", CSS,
     "[dir=rtl] .monaco-editor .find-widget>.find-part", 1),
    ("CSS39: زرّ فتح الاستبدال إلى اليمين", CSS,
     "[dir=rtl] .monaco-editor .find-widget .button.toggle", 1),
    ("CSS39: قلبُ عوامة مقابض الحقل", CSS,
     "[dir=rtl] .monaco-editor .find-widget .monaco-findInput>.controls .monaco-custom-toggle", 1),
    # وعلامةٌ رابعة: **زرُّ الإغلاق** مُطلَقُ الموضع كالاستبدال، وكان يبقى على `right:4px`
    # فيتراكب مع الاستبدال بعد نقلِه (قِيس حيًّا: ‎[789,807]‎ و‎[783,805]‎ — ستّةَ عشرَ بكسلًا
    # من ثمانيةَ عشر). ولا يكفي أن تُقاس القاعدةُ الأولى: نقلُ أحدِ المُطلَقَين بلا الآخر
    # هو العطبُ بعينه، فلكلٍّ علامتُه.
    ("CSS39: زرّ الإغلاق إلى اليسار", CSS,
     "[dir=rtl] .monaco-editor .find-widget>.button.codicon-widget-close", 1),
    # القاعدة 32: محاذاة صفحة الترحيب والجولة. `text-align:start` **معدومٌ في الحزمة كلِّها
    # قبل حقننا** (قِسناه: ‎0‎) — المنبع يكتب المحاذاة فيزيائيّةً دائمًا، وهو عين العطب.
    # وشارةُ «مميَّزة» علامةٌ ثانية على الجزء الفيزيائيّ من القاعدة (‏`.featured-badge`
    # عدده ‎1‎ في المنبع عاريًا، فالبادئةُ RTL لازمة: ‎0‎ قبل الحقن).
    ("CSS32: محاذاة الجولة منطقيّة لا يسارًا", CSS, "text-align:start", 1),
    ("CSS32: عكس شارة «مميَّزة» في بطاقة الجولة", CSS,
     "[dir=rtl] .part.editor>.content .gettingStartedContainer .gettingStartedSlide"
     " .getting-started-category .featured-badge", 1),
    # القاعدة 36 [LN-01]: عدساتُ الكود. الصنفُ منبعيٌّ وموجودٌ في الحزمة، فالبادئةُ RTL
    # مع سلسلة الآباء الكاملة تُميّز قاعدتَنا وحدَها: ‎0‎ قبل الحقن، ‎1‎ لكلٍّ بعده.
    ("CSS36: bidi عدسات الكود [LN-01]", CSS,
     "[dir=rtl] .monaco-editor .codelens-decoration a", 1),
    ("CSS36: bidi مقاطع عدسة الكود [LN-01]", CSS,
     "[dir=rtl] .monaco-editor .codelens-decoration span", 1),
    # القاعدة 37 [SC-01] **أُسقِطت**: صارت أصيلةً في المصدر برقعة النواة ‎030‎، فحقنُها
    # لم يعد يغيّر القيمةَ المحسوبة (قِيس حيًّا). ومِجَسٌّ على قاعدةٍ لا أثرَ لها يُوهم بحراسة.
    # رقعةُ النواة ‎030‎ [SC-01 · م-١٧]: `getSimpleEditorOptions` صار يقرأ المفتاحين.
    # الشاهدُ **سلسلةُ المفتاح نفسُها**: المصغِّر يُبقي حرفيّاتِ النصّ كما هي، ويُعيد تسميةَ
    # المعرّفات — فسلسلةٌ تُقاس وأمّا اسمُ الدالّة فلا. و`editor.textDirection` لا ترد في
    # المنبع خارجَ رقعتنا ‎010‎، فوجودُها هنا **مرّتين** (‎010‎ و‎030‎) هو ما يميّز الحقن.
    # الاقتباسُ **مقيسٌ لا مفترَض**: كُتبت الإبرةُ أوّلًا بعلامتين مفردتين كما في المصدر،
    # فأحمرّت على حزمةٍ تحوي المفتاحَ فعلًا — المصغِّر يُوحِّد إلى المزدوجة. والعددُ حدٌّ
    # أدنى: ‎3‎ مقيسةٌ لكلٍّ منهما، والواحدُ يكفي شاهدًا على أنّ الرقعةَ بلغت الحزمة.
    ("‏CORE030: اتّجاه صناديق الإدخال البسيطة [SC-01]", JS, '"editor.textDirection"', 3),
    ("‏CORE030: أشكال صناديق الإدخال السياقيّة [SC-01]", JS, '"editor.fontLigatures"', 3),
    # القاعدة 38 [DG-01]: هوامشُ لوحات التنقيح. الأربعُ **مقيسةٌ أثرًا** في
    # ‏`debug_panes.live.mjs`: يُحقَن نصُّ القاعدة **من الملفّ** على جلسةِ تنقيحٍ حيّة،
    # ويُقرأ الصندوقُ قبلُ وبعدُ. وثلاثةُ مرشّحين أُسقِطوا لأنّهم لم يزحزحوا شيئًا.
    #
    # ‏**والمحدِّدُ يُسجَّل هنا بنصّه المشحون**: أوّلُ صياغةٍ كتبناها استعملت `>` بين `.file`
    # و`.file-name` فلم تطابق شيئًا — قاعدةٌ تجتاز الحرّاسَ ولا تفعل. أمسكها التحقّقُ الحيُّ
    # قبل الشحن، وهذا الحارسُ يمسك ضياعَها في التحزيم.
    ("CSS38: هامش اسم الملفّ في كومة الاستدعاء [DG-01]", CSS,
     "[dir=rtl] .debug-pane .debug-call-stack .stack-frame .file-name", 1),
    ("CSS38: هامش كتلة الملفّ [DG-01]", CSS,
     # الرابطةُ `>` كما في `patches/mihrab-rtl.css` — كانت الإبرةُ تكتبها نَسَبًا فلا
     # تطابق المصدرَ نفسَه، أي حارسٌ يترقّب قاعدةً لم تُكتَب قطّ.
     "[dir=rtl] .debug-pane .debug-call-stack .stack-frame > .file:not(:first-child)", 1),
    ("CSS38: هامش قيمة المتغيّر [DG-01]", CSS,
     "[dir=rtl] .debug-pane .monaco-list-row .expression > .value", 1),
    ("CSS38: رابط المصدر في وحدة التصحيح [DG-01]", CSS,
     "[dir=rtl] .repl .repl-tree .group .source", 1),
    # ‏CORE031 [DG-01]: حبرُ شجرة التنقيح يتبع مفتاحَ حجم خطّ الشريط الجانبيّ.
    #
    # **والإبرةُ قاعدةُ macOS لا قاعدةُ الافتراض.** المتغيّرُ نفسُه
    # ‏(`--vscode-workbench-sidebar-font-size`) مستهلَكٌ في المنبع في عشرات المواضع
    # (‏`debugToolBar.css` · `debugViewlet.css` · `actionbar.css`)، فالبحثُ عن اسمه وحدَه
    # **يمرّ خضرةً والرقعةُ ساقطةٌ كلُّها** — حارسٌ يقيس المنبعَ ويظنّه يقيسنا. أمّا
    # ‏`calc(...*11/13)` فلا يكتبه إلّا هذه الرقعة، وهو الذي يُثبِت أنّ نسبةَ macOS
    # حُفِظت بدل أن تُطمَس برقمٍ حرفيّ.
    # **والإبرةُ بالفراغ الذي يكتبه المصغِّرُ فعلًا لا بالذي يُظنّ.** كُتبت أوّلَ مرّةٍ
    # مضغوطةً بلا فراغ (‏`,13px` و`*11/13`) على افتراضِ أنّ التصغيرَ يحذف كلَّ فراغ —
    # والحزمةُ تكتب `‏, 13px` و`* 11 / 13`. فاحمرّ الحارسُ على رقعةٍ **حاضرةٍ فعلًا**،
    # وهو الأحمرُ الكاذبُ الموصوفُ في `_squeeze_combinators` بعينه. والإبرةُ الآن
    # منقولةٌ عن المشحون، والتطبيعُ يوحّد الفراغَ إن تبدّل إعدادُ التصغير.
    ("‏CORE031: حجم خطّ شجرة التنقيح [DG-01]", CSS,
     ".debug-pane .monaco-list-row .expression{font-size:var(--vscode-workbench-sidebar-font-size, 13px)}", 1),
    ("‏CORE031: نسبة macOS محفوظة [DG-01]", CSS,
     "calc(var(--vscode-workbench-sidebar-font-size, 13px) * 11 / 13)", 1),
]


def _squeeze_combinators(s):
    """يحذف الفراغَ حول رابطات CSS (‏`>` `+` `~`) ويوحّد الفراغَ الباقي.

    المصغِّرُ يكتب `‏.a>.b` والمصدرُ يكتب `‏.a > .b` — والمقارنةُ الحرفيّةُ تراهما مختلفين.
    فكانت ثلاثُ قواعدَ من DG-01 **حاضرةً في الحزمة** وتُبلَّغ «غائبةً عن الحزمة (سقطت في
    التحزيم؟)». وأحمرُ كاذبٌ عطبٌ من صنف الأخضر الكاذب لا نقيضُه: كلاهما يفصل الحارسَ
    عن الواقع، وهذا يُعلِّم تجاهُلَه — فيمرّ الغيابُ الحقيقيُّ يومَ يقع.
    التطبيعُ يُجرى على **الطرفين** كي لا يصير تساهلًا في اتّجاهٍ واحد.
    """
    return re.sub(r"\s*([>+~])\s*", r"\1", re.sub(r"\s+", " ", s))


def _count(path, needle):
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        blob = f.read()
    n = blob.count(needle)
    if n:
        return n
    # لا يُطبَّع إلّا **بعد** فشل المطابقة الحرفيّة، ولإبرةٍ فيها رابطةٌ أو فراغ: إبرةٌ
    # بلا فراغٍ (اسمُ دالّةٍ، سلسلةُ نصّ) لا شأنَ لها بتصغير CSS، وتطبيعُها تساهلٌ بلا سبب.
    if not re.search(r"[>+~]|\s", needle):
        return 0
    return _squeeze_combinators(blob).count(_squeeze_combinators(needle))


_checks = []

# ‏**تخطٍّ مُعلَنٌ لا صامت.** بعد أن صار `DIST` مشتقًّا من المنصّة، صارت فحوصُ
# ويندوز تعمل على لينكس فتحمرّ على بناءٍ سليم (‏`Mihrab.exe` · `code.ico` ·
# ‏`VERSIONINFO`). والبديلُ السهل — إعادةُ تثبيت المسار على ويندوز — يُعيد العطبَ
# الأصليّ: صمتُ الطبقة كلِّها على المنصّة التي تُنتج بناءَ الويب المنشور.
# فيُعلَن ما يخصّ منصّةً بعينها، ويُطبَع تخطّيه بسببه.
import platform as _platform

_IS_WIN = _platform.system() == "Windows"


class _Skip(Exception):
    """تخطٍّ **معلَن** من داخل الفحص: شرطُه غيرُ متحقّقٍ في هذه الشجرة.

    يُميَّز عن الفشل عمدًا، ويُطبَع بسببِه ويُخصَم من العدّ — فلا نَدَّعي تغطيةً لم تجرِ
    ولا نُحمِّر بناءً سليمًا لم يُخرِج هدفًا اختياريًّا.
    """


def check(name, win_only=False):
    def deco(fn):
        _checks.append((name, fn, win_only))
        return fn
    return deco


@check("Mihrab.exe منتَج", win_only=True)
def _exe():
    assert os.path.isfile(EXE), f"لا exe: {EXE}"


# الثنائيّاتُ التي تحمل اسمَ منتَجِنا: يجب أن تحمل ناشرَنا معه.
_VERSIONED_BINARIES = [
    "Mihrab.exe",
    os.path.join("bin", "mihrab-tunnel.exe"),
    os.path.join("resources", "app", "node_modules", "@vscode", "ripgrep-universal",
                 "bin", "win32-x64", "rg.exe"),
]
_EXPECTED_COMPANY = "Mihrab"


def _version_fields(path):
    """‏CompanyName/ProductName/LegalCopyright من VS_VERSION_INFO، أو None إن تعذّر.

    **عبر PowerShell لا بقارئٍ محلّيّ الصنع.** جُرِّب قارئُ بايتٍ يبحث عن المفتاح
    بترميز UTF-16LE ثمّ يقرأ ما بعده: نجح على `rg.exe` و`mihrab-tunnel.exe` وأعاد على
    `Mihrab.exe` قيمةَ مفتاحٍ مجاور (`CompanyShortName`) واسمَ منتَجٍ مشوَّشًا — لأنّ
    قسمَ موارد Electron أكبرُ وبنيتُه لا تُقرَأ بالجوار. وحارسٌ يعيد قيمةً خاطئةً
    أسوأُ من حارسٍ لا يعمل. فـ`.VersionInfo` في .NET هو القارئُ الذي يقرأ ما يقرؤه
    ويندوز نفسُه — وهو المرجعُ الذي نحرسه أصلًا.
    """
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if not ps:
        return None
    script = (
        "$v=(Get-Item -LiteralPath $env:MIHRAB_VI_PATH).VersionInfo;"
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
        "Write-Output $v.CompanyName; Write-Output $v.ProductName;"
        "Write-Output $v.LegalCopyright"
    )
    env = dict(os.environ, MIHRAB_VI_PATH=path)
    try:
        r = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-Command", script],
                           capture_output=True, env=env, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    lines = r.stdout.decode("utf-8", "replace").replace("\r", "").split("\n")
    while len(lines) < 3:
        lines.append("")
    return {"CompanyName": lines[0].strip(), "ProductName": lines[1].strip(),
            "LegalCopyright": lines[2].strip()}


@check("ناشرُ الثنائيّات المشحونة هو ناشرُنا [BR-04]", win_only=True)
def _binary_publisher():
    """‏`CompanyName` هو ما يعرضه ويندوز ناشرًا، وما تقرؤه أدواتُ الجرد وسياساتُ AppLocker.

    **وقد قِيس في المشحون** (‏1.126.05942): `Mihrab.exe` و`rg.exe` يقولان «VSCodium»،
    و`bin/mihrab-tunnel.exe` يقول «**Microsoft Corporation**» — ملفٌّ باسمنا واسمُ منتَجِنا
    فيه (محراب) ينسب نفسَه إلى جهةٍ حقيقيّةٍ ليست ناشرَه.

    ولم يمسكه حارسٌ لأنّ حرّاسَ الهويّة يسألون `product.json` والنصَّ المُصيَّر، وهما
    صحيحان تمامًا. أمّا `VERSIONINFO` فمَورِدُه مصادرُ البناء لا المنتَج (أربعةُ مواضعَ:
    حزمةُ Electron · rcedit · بناءُ الخادم · مواردُ CLI) ولم يكن في نطاق أيّ فحص.

    ويزداد وزنُه مع التوقيع: التوقيعُ يقول «الناشر: لغة ص» والملفُّ يقول غيرَه، فيعرض
    ويندوز المتناقضَين في النافذة نفسِها — وشروطُ التوقيع للمشاريع المفتوحة تشترط
    بياناتِ منتَجٍ صحيحةً على كلّ ما يُوقَّع.
    """
    probed = 0
    for rel in _VERSIONED_BINARIES:
        path = os.path.join(DIST, rel)
        if not os.path.isfile(path):
            continue
        fields = _version_fields(path)
        if fields is None:
            print("  ⏭️  لا PowerShell لقراءة VERSIONINFO — تخطٍّ.")
            return
        probed += 1
        co = fields["CompanyName"]
        assert co == _EXPECTED_COMPANY, (
            f"{rel}: CompanyName = {co!r} لا {_EXPECTED_COMPANY!r} — "
            "الملفُّ ينسب نفسَه إلى ناشرٍ ليس ناشرَه")
        cp = fields["LegalCopyright"]
        assert "VSCodium" not in cp and "Microsoft" not in cp, (
            f"{rel}: LegalCopyright ما زال يذكر جهةً أخرى: {cp!r}")
        assert "All rights reserved" not in cp, (
            f"{rel}: LegalCopyright يقول «All rights reserved» ومحرابٌ تحت MIT: {cp!r}")
    # شاهدُ تفعيلٍ موجَب: لا ملفَّ يُقاس ⇒ الفحصُ يمرّ على العمى.
    assert probed, ("لم يُقَس أيُّ ثنائيّ — لا حزمةَ أو تغيّرت المسارات "
                    "(‏_VERSIONED_BINARIES)")
    print(f"  ↳ {probed} ثنائيًّا: CompanyName={_EXPECTED_COMPANY}")


@check("هوية بصريّة: كلّ أصول win32 في الحزمة = مصدر محراب (بايتيًّا)", win_only=True)
def _app_icon():
    for src, target in M.BRANDING_ASSETS:
        sp = os.path.join(ROOT, *src.split("/"))
        tp = os.path.join(WIN32_OUT, target)
        assert os.path.isfile(sp), f"لا أصل مصدر: {src} (شغّل assets/branding/gen_ico.py)"
        assert os.path.isfile(tp), f"لا {target} في الحزمة (لم تُحقَن الهوية؟)"
        assert filecmp.cmp(sp, tp, shallow=False), \
            f"{target} المشحون ≠ {src} (رجعت هوية VSCodium؟)"


# **الحكمُ يُستدعى ولا يُستنسَخ.** عتبتان مكتوبتان في مكانين تفترقان عند أوّل تعديل
# فتصير إحداهما تكذب على الأخرى — وهو صنفُ العطب نفسِه الذي أوجب هذا المِجَسّ. فنستدعي
# ‏`verify` من المرقِّع: بوّابةُ البناء وبوّابةُ الاختبار دالّةٌ واحدةٌ لا نسختان.
sys.path.insert(0, os.path.join(ROOT, "build"))
import patch_extension_nls as _NLS  # noqa: E402
import mihrab_brand as _BRAND  # noqa: E402


@check("بوّابةُ بيانات الامتدادات على المشحون (تعريبٌ في الملفّ المقروء + لا تسرّبَ هويّة)")
def _ext_nls_gate():
    if not os.path.isdir(os.path.join(APP, "extensions")):
        return
    # العطبُ الذي أوجب هذا: كان 0/1602 والسطرُ يقول 100% — لأنّ الحقن ذهب إلى
    # ‏contents.package في حزمةِ لغةٍ **غيرِ مسجَّلة**، وإلى package.nls.ar.json الذي لا
    # يُستشار بلا لغةٍ محلولة (‏extensionsScannerService.ts:928). حكمٌ على المخرَج لا النيّة.
    assert _NLS.verify(APP) == 0, "بوّابةُ تعريب بيانات الامتدادات ردّت المخرَج (التفصيل أعلاه)"


@check("الهويّة: لا اسمَ توزيعةٍ أمٍّ في أيّ سطحٍ مُصيَّرٍ مشحون (لا المقروءِ وحدَه)")
def _no_upstream_brand():
    """كان هذا المِجَسُّ يقرأ `out/nls.messages.json` وحدَه — ملفًّا واحدًا من ‎279‎.

    والباقي ليس زينة: ‏91 ملفَّ `package.nls.ar.json` و95 ملفَّ i18n كُتبت **تحصينًا**
    لو سُجِّلت حزمةُ لغةٍ يومًا. فكان الحرسُ يحمي المسارَ الحيَّ اليومَ ويترك الخامدَ الذي
    يُحييه إعدادٌ واحد (`nls.language`). مسحٌ واحدٌ يغطّي الجميع، من الوحدة نفسِها التي
    تُطبِّع — فلا تتباعد قاعدةُ الكتابة عن قاعدة الفحص.
    """
    # `residue` لا `in`: الاسمُ داخل شَولتين مائلتين أمرٌ يُنسَخ ويُنفَّذ، واستبدالُه يُملي
    # على المستخدم أمرًا لا وجودَ له. الوحدةُ تصونه بحقّ، فحرسٌ يرفضه رفضًا مطلقًا يجعل
    # تلك الصيانةَ شيفرةً لا سبيلَ إلى تفعيلها.
    # و«VS Code» لا يُفحَص هنا: بعضُه إشارةٌ صادقةٌ إلى طرفٍ ثالث (سوقٌ، قناةُ Insiders،
    # نسبةُ سمةٍ إلى صانعها) واستبدالُه كذبٌ لا تعريب. القائمةُ المصانةُ مُعلَنةٌ ومُختبَرةٌ
    # في build/mihrab_brand.py و tests/brand/check_brand.py — دَينٌ مرئيٌّ لا صمت.
    bad, scan = _BRAND.scan_shipped(APP)
    assert not bad, "اسمُ التوزيعة الأمّ يظهر لمستخدم محراب: " + " | ".join(bad[:5])
    # ومسحٌ لم يجد شيئًا ليس مسحًا نظيفًا: يُشترَط شاهدٌ من كلّ صنف.
    for kind in ("nls.messages", "package.nls.json", "package.nls.ar.json", "i18n"):
        assert scan.get(kind), f"مسحُ الهويّة بلا سطحٍ من صنف «{kind}» — تخطيطٌ تغيّر فعمِيَ المِجَسّ"


# الحزمة تُسطّح أصول media/ إلى out/media/<basename> (لا تُمرِّر بنية src)، **وتُحسِّنها بـsvgo**:
# تُجرَّد التعليقات والـ id وviewBox ويُختصر المسار ⇒ لا مطابقة بايتيّة ولا مِجَسّ id يصمد.
# لكنّ svgo يُبقي ألوان stroke وبيانات المسار ⇒ نتحقّق بتوقيع لونيّ مشتقّ من المصدر.
OUT_MEDIA = os.path.join(APP, "out", "media")


def _readtext(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _stroke_colors(svg_text):
    import re
    return {c.lower() for c in re.findall(r'stroke="(#[0-9A-Fa-f]{6})"', svg_text)}


@check("هوية بصريّة: أصول SVG للأسطح (رأس التطبيق + خلفية المحرّر) في الحزمة = شعار محراب")
def _surface_svgs():
    matched, pending = [], []
    for src, dest in M.BRANDING_SVG_ASSETS:
        sp = os.path.join(ROOT, *src.split("/"))
        tp = os.path.join(OUT_MEDIA, os.path.basename(dest))
        assert os.path.isfile(sp), f"لا أصل مصدر: {src}"
        colors = _stroke_colors(_readtext(sp))  # ألوان القوس في مصدر محراب (تُشتَقّ، لا تُكتب حرفيًّا)
        assert colors, f"لا لون stroke في مصدر {src} (بنية SVG غير متوقَّعة؟)"
        if not os.path.isfile(tp):
            pending.append(os.path.basename(dest))
            continue
        shipped = _stroke_colors(_readtext(tp))
        # كلّ لون قوس محرابيّ حاضر في المخرَج المُحسَّن ⇒ شُحن شعار محراب (لا أصل VSCodium الأصليّ
        # ذو التدرّج الأزرق/الرماديّ #B2B2B2 — ألواننا الفيروزيّة غائبة عنه قطعًا).
        (matched if colors <= shipped else pending).append(os.path.basename(dest))
    if matched and pending:
        raise AssertionError(f"شحن جزئيّ لأسطح الهوية: طابق {matched}، وتخلّف {pending} (انحدار؟)")
    if not matched:
        # لا سطح مشحون بعد ⇒ بناء أقدم من v17 (الأسطح تُدخَل بإعادة البناء). L0 يضمن الربط ساكنًا.
        print("  ⏭️  أسطح SVG (رأس/خلفية) غير مشحونة بعد — يحتاج إعادة بناء v17 (الربط مضمون بـL0).")


# حزمة مساحة sessions التجريبيّة: شعار الحوض (VSCODE_LOGO_PATH) يُبنَى فيها كسلسلة مسار.
SESSIONS_BUNDLE = os.path.join(APP, "out", "vs", "sessions", "sessions.desktop.main.js")


@check("هوية بصريّة: شعار حوض sessions في الحزمة = قوس محراب (لا VSCodium)")
def _sessions_aquarium_logo():
    if not os.path.isfile(SESSIONS_BUNDLE):
        print("  ⏭️  حزمة sessions غير مبنيّة — تخطٍّ.")
        return
    txt = _readtext(SESSIONS_BUNDLE)
    if "M14 88" in txt:  # مسار قوس محراب المطموس
        assert "M65.566" not in txt, "الحزمة تحمل مسار محراب ومسار VSCodium معًا (حقن جزئيّ؟)"
        return  # pass: شعار الحوض = محراب
    # لا مسار محراب ⇒ بناء أقدم من v18 (يُدخَل بإعادة البناء). L0 يضمن الربط ساكنًا.
    print("  ⏭️  شعار حوض sessions غير مشحون بعد — يحتاج إعادة بناء v18 (الربط مضمون بـL0).")

@check("سمات محراب: مشحونة (داكنة + فاتحة) + الافتراضيّة معلَنة")
def _themes_shipped():
    d = os.path.join(APP, "extensions", "mihrab-themes")
    if not os.path.isdir(os.path.join(ROOT, "extensions", "mihrab-themes")):
        return  # لا إضافة سمات في هذا الفرع — تخطٍّ (لا يُفشِل)
    assert os.path.isdir(d), "إضافة سمات محراب غير مشحونة في المخرَج (extensions/mihrab-themes)"
    for fn in ("mihrab-dark-color-theme.json", "mihrab-light-color-theme.json"):
        assert os.path.isfile(os.path.join(d, "themes", fn)), f"سمة مفقودة في الحزمة: {fn}"
    pkg = json.load(open(os.path.join(d, "package.json"), encoding="utf-8"))
    assert pkg.get("contributes", {}).get("configurationDefaults", {}).get("workbench.colorTheme"), \
        "السمة الافتراضيّة غير معلَنة في حزمة المخرَج"


@check("سمة أيقونات محراب: مشحونة (SVG + JSON) + الافتراضيّة معلَنة")
def _icons_shipped():
    if not os.path.isdir(os.path.join(ROOT, "extensions", "mihrab-icons")):
        return  # لا إضافة أيقونات في هذا الفرع — تخطٍّ
    d = os.path.join(APP, "extensions", "mihrab-icons")
    assert os.path.isdir(d), "إضافة أيقونات محراب غير مشحونة (extensions/mihrab-icons)"
    tj = os.path.join(d, "mihrab-icon-theme.json")
    assert os.path.isfile(tj), "ملفّ سمة الأيقونات مفقود في الحزمة"
    # الأصول اليدويّة + **عائلة [AR-06] المولَّدة**: `cp -r` في build.sh يجرّد `*.py`
    # (المولّد) ويُبقي الـSVG. سقوطها يعيد المستكشف إلى صفحاتٍ متطابقة بلا أن يُفشِل L0.
    for svg in ("sad.svg", "file.svg", "folder.svg", "folder-open.svg",
                "code.svg", "data.svg", "doc.svg", "image.svg", "meta.svg"):
        assert os.path.isfile(os.path.join(d, "icons", svg)), f"أيقونة SVG مفقودة في الحزمة: {svg}"
    assert not os.path.isfile(os.path.join(d, "gen_icons.py")), \
        "مولّد الأيقونات شُحن مع المنتج (يجب أن يجرّده build.sh مع بقيّة *.py)"
    # افحص **محتوى** الـJSON المشحون لا وجوده فقط (بناء يشحن JSON بائتًا/فارغًا يمرّ وإلّا):
    td = json.load(open(tj, encoding="utf-8"))
    defs = td.get("iconDefinitions", {})
    sad_ref = td.get("fileExtensions", {}).get("ص") or td.get("languageIds", {}).get("sad")
    assert sad_ref in defs, "خريطة ملفّ ص مفقودة/مكسورة في سمة الأيقونات المشحونة"
    pkg = json.load(open(os.path.join(d, "package.json"), encoding="utf-8"))
    default = pkg.get("contributes", {}).get("configurationDefaults", {}).get("workbench.iconTheme")
    ids = {i.get("id") for i in pkg.get("contributes", {}).get("iconThemes", [])}
    assert default in ids, "سمة الأيقونات الافتراضيّة لا تطابق أيّ id في حزمة المخرَج"


@check("أدواتُ ص: ما جُلب من الإصدار الرسميّ وصل الحزمةَ ببصمته")
def _sad_tools_shipped():
    """البوّابةُ نفسُها التي يشغّلها CI، كي لا يكون النشرُ أوّلَ من يكتشف. تنفيذُها
    مشتركٌ في `check_sad_tools.py` — نسخةٌ ثانيةٌ من المنطق تتباعد صامتةً."""
    sys.path.insert(0, HERE)
    from check_sad_tools import verify  # noqa: E402
    code, lines = verify(DIST)
    assert code == 0, "\n       " + "\n       ".join(lines)


@check("قشرة محراب [AR-04]: افتراضاتُ الإعداد في الحزمة = المصدر (إعفاءُ يونيكود وصل فعلًا)")
def _shell_defaults_shipped():
    """‏L0 يحرس المصدر، وهذا يحرس **ما وصل**. الفرقُ ليس نظريًّا: العطبُ الذي أبلغه
    المستخدم (مستطيلٌ أصفر حول كلّ ألف) كان إعفاءً صحيحًا في المصدر لم يبلغ الحزمة.
    وفحصُ وجودِ المجلّد وحده لا يمسك ذلك — فنقارن الافتراضات كائنًا بكائن.
    """
    src = os.path.join(ROOT, "extensions", "mihrab-shell", "package.json")
    # لا تخطٍّ عند الغياب: القشرةُ ليست فرعًا اختياريًّا كالسمات، وحذفُ ملفّها يجب أن
    # يُخفق لا أن يُحوِّل الحارسَ إلى لا-عمليّةٍ صامتة.
    assert os.path.isfile(src), "مصدر قشرة محراب مفقود: extensions/mihrab-shell/package.json"
    d = os.path.join(APP, "extensions", "mihrab-shell")
    assert os.path.isdir(d), "قشرة محراب غير مشحونة (extensions/mihrab-shell)"
    shipped = os.path.join(d, "package.json")
    assert os.path.isfile(shipped), "package.json القشرة مفقود في الحزمة"
    want = json.load(open(src, encoding="utf-8"))["contributes"]["configurationDefaults"]
    got = json.load(open(shipped, encoding="utf-8")).get("contributes", {}).get(
        "configurationDefaults", {})
    # التشخيصُ يشير إلى **أوّل مسارٍ مختلف** لا إلى مفاتيح المستوى الأعلى وحدها: انجرافُ
    # محرفٍ داخل `[sad]` كان يُنتج «مفاتيحُ ناقصة/زائدة: []» — رسالةً تقرأ كأنّ الفحصَ
    # معطوبٌ لا كأنّ الحزمةَ بائتة. (رصدَته مراجعةٌ هندسيّة بأربع طفرات.)
    if got != want:
        def _first_diff(a, b, path=""):
            for k in sorted(set(a) | set(b)):
                p = f"{path}.{k}" if path else k
                if k not in a:
                    return f"{p} (زائدٌ في الحزمة)"
                if k not in b:
                    return f"{p} (مفقودٌ من الحزمة)"
                if isinstance(a[k], dict) and isinstance(b[k], dict):
                    d = _first_diff(a[k], b[k], p)
                    if d:
                        return d
                elif a[k] != b[k]:
                    return f"{p}: المصدر={a[k]!r} الحزمة={b[k]!r}"
            return None
        raise AssertionError(
            "افتراضاتُ قشرة محراب في الحزمة تخالف المصدر — نسخةٌ بائتةٌ شُحنت. "
            f"أوّلُ فرق: {_first_diff(want, got)} [AR-04]")


@check("خطّ AR-02: @font-face بملفٍّ مجاور في CSS المشحون (مشروط بتوريد الخطّ)")
def _arabic_font_shipped():
    # الحقن مشروط بتوريد بايتات الخطّ (سقوط رشيق)؛ لا يمكن جعله غير مشروط وإلّا فشل حين لا خطّ.
    # الإشارة: الملفّ المُجهَّز في .upstream/ (ما نسخه build.sh فعلًا حين وُجد المصدر).
    if not os.path.isfile(CSS):
        return  # لا حزمة — يتخطّى الإطار العامّ أصلًا، وهذا احتياط
    staged = os.path.join(ROOT, ".upstream", ".mihrab-kawkab-mono.woff2")
    src_default = os.path.join(ROOT, "patches", "fonts", "kawkab-mono.woff2")
    if not (os.path.isfile(staged) or os.path.isfile(src_default) or os.environ.get("MIHRAB_ARABIC_FONT")):
        print("  ⏭️  خطّ Kawkab Mono غير مورَّد — @font-face غير محقون (سقوط رشيق مقصود؛ L0 يضمن الوصل).")
        return
    css = _readtext(CSS)
    # **المصدرُ ملفٌّ مجاورٌ لا data: — تصحيحُ عطبٍ مقيسٍ لا تفضيلُ صياغة.** الحقنُ زمنَ
    # البناء (patch_bundle_extensions.py) يكتب data:font/woff2 لأنّ esbuild بلا مُحمِّلٍ
    # لـ.woff2؛ وسياسةُ أمانِ محتوى القشرة لا تسمح بـdata: في font-src — فكان الوجهُ
    # **يُعلَن ولا يُحمَّل** (قِيس حيًّا: document.fonts تردّ «Kawkab Mono:error» و
    # securitypolicyviolation تقول «font-src data»). فصار build/patch_workbench_font.py
    # يكتب الوجهَ ملفًّا بجانب CSS ويعيد كتابة القاعدة ⇒ المصدرُ self بلا توسيعِ CSP [م-٢٥].
    assert "@font-face" in css and "Kawkab Mono" in css, (
        "الخطّ مورَّد لكن @font-face/Kawkab Mono غائب عن CSS المشحون (فشل الحقن زمن البناء؟)")
    assert "kawkab-mono.woff2" in css, (
        "قاعدةُ @font-face لا تشير إلى الملفّ المجاور — لم يعمل patch_workbench_font.py [م-٢٥]")
    assert "data:font/woff2" not in css, (
        "بقي مصدرُ data: في CSS المشحون — تحجبه سياسةُ أمان المحتوى فلا يُحمَّل الوجه [م-٢٥]")
    side = os.path.join(os.path.dirname(CSS), "kawkab-mono.woff2")
    assert os.path.isfile(side) and open(side, "rb").read(4) == b"wOF2", (
        f"لا ملفَّ خطٍّ صالحًا بجانب CSS المشحون: {side} [م-٢٥]")


@check("بصماتُ النزاهة في المشحون تصف ما شُحن فعلًا [PK-01]")
def _integrity_checksums_match():
    """المنبعُ يبصم عشرةَ ملفّاتٍ ويتحقّق منها **عند كلّ إقلاع**.

    فإن اختلفت واحدةٌ عرض «يبدو أن تثبيت Mihrab تالف. يرجى إعادة التثبيت» — إشعارٌ
    يراه كلُّ مستخدمٍ في كلّ مرّة، ويقول له إنّ نسختَه معطوبةٌ وهي سليمة.

    **وقد وقع.** خطوةُ (ط-0أ3) تعيد كتابةَ `workbench.desktop.main.css` بعد التحزيم
    لتصلَ الخطَّ العربيَّ بملفٍّ مجاور، والبصمةُ محسوبةٌ قبلها. قِيس على ‎1.121.05937‎:
    تسعٌ مطابقةٌ وواحدةٌ بائتة — الورقةُ بعينها.

    ولم يمسكه شيء: بقيّةُ مِجَسّات L2 تسأل «أوصلَت الشيفرةُ إلى الحزمة؟» لا «أهي
    النسخةُ التي بُصِمت؟»، ومِجَسُّ L3 يقرأ الإشعاراتِ بـ`some()` فلا يسقط لإشعارٍ
    زائد. وهذا الفحصُ هو الحارسُ الوحيد.

    ويُشغَّل الحسابَ نفسَه الذي يُصلحه `build/refresh_checksums.py` — لا نسخةً
    ثانيةً منه: حارسٌ يعيد كتابةَ ما يحرسه يقيس نفسَه.
    """
    sys.path.insert(0, os.path.join(ROOT, "build"))
    import refresh_checksums as R  # noqa: E402

    pj = os.path.join(APP, "product.json")
    if not os.path.isfile(pj):
        print("  ⏭️  لا product.json مشحون — تخطٍّ.")
        return
    with open(pj, encoding="utf-8-sig") as f:
        recorded = json.load(f).get("checksums") or {}
    assert recorded, "لا مفاتيحَ `checksums` في product.json المشحون — الآليّةُ غائبةٌ لا سليمة"
    stale = []
    for key, want in sorted(recorded.items()):
        f = os.path.join(APP, "out", key)
        assert os.path.isfile(f), f"ملفٌّ مبصومٌ مفقودٌ من المشحون: out/{key}"
        got = R._digest(f)
        if got != want:
            stale.append(f"out/{key} (مسجَّلة {want} · فعليّة {got})")
    assert not stale, (
        "بصماتٌ بائتةٌ في المشحون ⇒ «يبدو أن تثبيت Mihrab تالف» عند كلّ إقلاع: "
        + " · ".join(stale)
        + " — خطوةُ ما بعد بناءٍ كتبت في out/ بعد (ط-0ج)، أو سقط refresh_checksums.py")


@check("product.json المبنيّ: عربيّ افتراضيّ (defaultLocale=ar)")
def _built_locale():
    pj = os.path.join(APP, "product.json")
    assert os.path.isfile(pj), "لا product.json مبنيّ"
    assert json.load(open(pj, encoding="utf-8")).get("defaultLocale") == "ar", \
        "defaultLocale ليس ar في المخرَج (خبز/هوية فشل)"


@check("product.json المبنيّ: «حدِّث» لا يجلب المنبع (المُحدِّث معطَّل + روابطُ محراب)")
def _built_update_identity():
    """
    ⚠️ العطبُ الذي أبلغه المستخدم يعيش في **المشحون** لا في ملفّ التجاوزات: التجاوزُ
    قد يكون سليمًا ودمجُه ساقطًا. فالسؤالُ هنا يُوجَّه إلى ما يُشغّله المستخدم فعلًا.

    وشرطُ التعطيل ليس `updateUrl` وحده: `abstractUpdateService` يعطّل عند `!updateUrl ||
    !commit`. فنقبل غيابَ أيّهما، ونرفض أن يكون العنوانُ حيًّا ويشير إلى منبع.
    """
    pj = os.path.join(APP, "product.json")
    assert os.path.isfile(pj), "لا product.json مبنيّ"
    prod = json.load(open(pj, encoding="utf-8"))
    upd = prod.get("updateUrl")
    assert not upd, f"المُحدِّث فعّال: updateUrl={upd} — «حدِّث» سيستبدل محرابًا بالمنبع"
    # روابطُ الهويّة التي نملكها. (‏keyboardShortcutsUrl*/documentation المتروكةُ عمدًا
    # توثيقُ المحرّر نفسِه لا هويّةُ منتجٍ منافس — تُستثنى صراحةً لا صمتًا.)
    owned = ("downloadUrl", "reportIssueUrl", "licenseUrl", "requestFeatureUrl",
             "releaseNotesUrl", "serverDownloadUrlTemplate", "twitterUrl")
    for k in owned:
        v = prod.get(k)
        if not v:
            continue
        low = str(v).lower()
        assert not any(u in low for u in ("vscodium", "microsoft", "visualstudio")), \
            f"{k} يقود المستخدمَ إلى المنبع: {v}"


@check("product.json المبنيّ: السوقُ مُصرَّحٌ به لا موروثٌ صامتًا (MK-01)")
def _built_gallery():
    """
    ‏[MK-01] المفتاحُ الذي يُنزَّل منه **شيفرةٌ تُنفَّذ في جهاز المستخدم** كان يصل الحزمةَ
    بالميراث وحدَه: صفرُ ذِكرٍ لـ`extensionsGallery` في `product-overrides/` و`build/`
    و`tests/` — فقيمتُه رهنُ قرارِ فرعٍ لا نملكه. صار مُصرَّحًا به، وهذا الحارسُ يقرأ
    **المشحون** لا ملفَّ التجاوزات (التجاوزُ قد يكون سليمًا ودمجُه ساقطًا — القاعدةُ
    نفسُها التي كُتبت لحارس المُحدِّث).

    والسؤالان اللذان يجيب عنهما: (١) أما زال السوقُ حاضرًا أصلًا؟ سقوطُه يُخفي نحوَ خمسٍ
    وعشرين تسجيلةَ عرضٍ وأمرٍ **بلا رسالةِ خطأٍ واحدة** (`extensionGalleryManifestService.ts:30`
    ⇒ `Unavailable` ⇒ مفتاحُ السياق `CONTEXT_HAS_GALLERY`)، فيرى المستخدمُ شريطًا مبتورًا
    ولا يعرف السبب. (٢) وأهو النطاقُ الذي قرّرناه؟ انجرافُه إلى سوقٍ آخر تغييرُ مصدرِ
    شيفرةٍ لا تغييرُ رابط — ولذلك يُقارَن الأصلُ (origin) لا السلسلةُ كاملةً: المسارُ
    قد يتبدّل بترقيةٍ منبعيّة، والمضيفُ لا يجوز أن يتبدّل صامتًا.
    """
    pj = os.path.join(APP, "product.json")
    assert os.path.isfile(pj), "لا product.json مبنيّ"
    prod = json.load(open(pj, encoding="utf-8"))
    gal = prod.get("extensionsGallery") or {}
    svc = gal.get("serviceUrl")
    assert svc, ("لا سوقَ في المشحون (extensionsGallery.serviceUrl غائب) — الشريطُ "
                 "الجانبيّ سيُبتَر صامتًا. إن كان ذلك قرارًا فيجب أن يُكتَب قرارًا "
                 "ويُحدَّث هذا الحارس، لا أن يمرّ سقوطًا.")
    host = urllib.parse.urlparse(svc).netloc.lower()
    assert host == "open-vsx.org", \
        f"السوقُ انجرف إلى مضيفٍ آخر: {svc} — مصدرُ شيفرةٍ تُنفَّذ في جهاز المستخدم"
    trusted = prod.get("linkProtectionTrustedDomains") or []
    assert any(urllib.parse.urlparse(d).netloc.lower() == host for d in trusted), \
        (f"نطاقُ السوق ({host}) خارجَ linkProtectionTrustedDomains — كلُّ نقرةٍ في صفحة "
         f"إضافةٍ تستجوب المستخدمَ بحوارِ ثقةٍ في مسارٍ نمرّ به عمدًا")


# ── [WEB-01] بناءُ الويب مُعرَّبٌ كالمكتبيّ، لا هيكلًا عربيَّ الاتّجاه بواجهةٍ إنجليزيّة ──
_WEB_MIN_AR_PCT = 90       # المكتبيُّ يقيس 94%؛ العتبةُ تحت ذلك بهامشٍ لا تحته بمرحلة
_WEB_MIN_RTL_RULES = 100   # قِيست 130 في الويب والمكتبيّ معًا
_WEB_JS_PREFIX = "globalThis._VSCODE_NLS_MESSAGES="


def _web_dir():
    """مجلّدُ `vscode-reh-web-*` الوحيد، أو None إن لم يُبنَ."""
    hits = sorted(glob.glob(os.path.join(ROOT, ".upstream", "vscode-reh-web-*")))
    hits = [h for h in hits if os.path.isdir(h)]
    if len(hits) > 1:
        raise AssertionError(f"وُجد {len(hits)} مجلّدَ ويبٍ — لا يُقاس ما لم يُحدَّد أيُّه المشحون")
    return hits[0] if hits else None


def _static_dir():
    """شجرةُ `vscode-web` الثابتة — هدفٌ اختياريٌّ لا يُخرجه البناءُ الافتراضيّ."""
    d = os.path.join(ROOT, ".upstream", "vscode-web")
    return d if os.path.isdir(d) else None


_AR_RE = re.compile(r"[؀-ۿ]")


def _ar_ratio(strings):
    ar = sum(1 for x in strings if isinstance(x, str) and _AR_RE.search(x))
    return ar, len(strings)


def _nls_js_array(js):
    """مصفوفةُ الرسائل من `nls.messages.js` — والبادئةُ تُبحَث ولا يُشترَط موضعُها.

    البناءُ الثابت يسبقها بإشعارِ حقوقٍ منبعيٍّ يُحفَظ عمدًا، وشرطُ `startswith` كان
    يُحمِّر شجرةً سليمةً لهذا وحدَه.
    """
    at = js.find(_WEB_JS_PREFIX)
    assert at >= 0, "بنيةُ nls.messages.js تغيّرت — لم تعد تُخبَز حيث تُقرأ"
    close = js.rfind("]")
    assert close > at, "مصفوفةُ الرسائل غيرُ مغلقة في nls.messages.js"
    return json.loads(js[at + len(_WEB_JS_PREFIX):close + 1])


@check("محرابُ المتصفّح مُعرَّبٌ ومعكوسُ الاتّجاه [WEB-01]")
def _web_arabized():
    web = _web_dir()
    assert web is not None, (
        "لا مجلّدَ vscode-reh-web-* في .upstream — البناءُ يُخرجه في كلّ مرّة، فغيابُه "
        "يعني بناءً ناقصًا لا ميزةً غائبة")

    prod = json.loads(_readtext(os.path.join(web, "product.json")))
    assert prod.get("nameLong") == "محراب", f"هويّةُ الويب انجرفت: nameLong={prod.get('nameLong')!r}"
    assert prod.get("defaultLocale") == "ar", f"defaultLocale={prod.get('defaultLocale')!r} لا ar"
    # ‏**مفتاحان قِيسا ناجيَين بقيمة المنبع** في شجرة الويب على 1.126.05942، لأنّ خطوةَ
    # إعادة فرض الهويّة (ط-0ز) كانت مربوطةً بالمكتبيّ وحدَه. وكان هذا الفحصُ أخضرَ
    # عليهما لأنّه لم يسألهما — يفحص اسمًا ولغةً ويسكت عن وجهةِ التنزيل.
    assert prod.get("updateUrl") in (None, "null"),         f"updateUrl في الويب ليس null: {prod.get('updateUrl')!r} — تحديثٌ يجرّ منبعًا"
    _sdl = str(prod.get("serverDownloadUrlTemplate") or "")
    assert not any(k in _sdl.lower() for k in ("vscodium", "microsoft")), (
        f"serverDownloadUrlTemplate يشير إلى المنبع: {_sdl[:90]} — "
        f"محرابٌ المنشور يوزّع المنبعَ باسمه")

    # (1) نواةُ الترجمة — الملفُّ الذي تقرؤه العمليّة
    msgs = json.loads(_readtext(os.path.join(web, "out", "nls.messages.json")))
    ar, tot = _ar_ratio(msgs)
    pct = (ar * 100) // tot if tot else 0
    assert pct >= _WEB_MIN_AR_PCT, (
        f"واجهةُ الويب {pct}% عربيّة ({ar}/{tot}) — دون العتبة {_WEB_MIN_AR_PCT}%. "
        f"خطواتُ ما بعد البناء ربّما عادت مربوطةً بالمكتبيّ وحدَه.")

    # (2) ونسخةُ المتصفّح — الملفُّ الذي **يُخدَم فعلًا** للصفحة. الفصلُ مقصود: خبزُ الأولى
    # وحدَها تركَ الواجهةَ إنجليزيّةً بالكامل (1/21922) والحارسُ لو قاسها وحدَها لكان أخضر.
    js = _readtext(os.path.join(web, "out", "nls.messages.js"))
    jar, jtot = _ar_ratio(_nls_js_array(js))
    jpct = (jar * 100) // jtot if jtot else 0
    assert jpct >= _WEB_MIN_AR_PCT, (
        f"‏nls.messages.js — وهو ما يصل المتصفّح — {jpct}% عربيّة ({jar}/{jtot})")
    # وتسرّبُ الهويّة في **الملفّ الذي يصل المتصفّح**: كان ذيلُه يحمل رابطَ
    # ‏sourceMappingURL إلى إصدارات VSCodium، وبوّابةُ (ي-2) تفحص الـjson المكتبيّة
    # وحدَها فلم ترَه. اسمُ منبعٍ يُخدَم للزائر، وجلبٌ من طرفٍ ثالثٍ عند فتح الأدوات.
    for _leak in ("vscodium", "VSCodium"):
        assert _leak not in js, (
            f"«{_leak}» في out/nls.messages.js — الملفُّ الذي يصل المتصفّح يحمل اسمَ المنبع")

    # (3) الاتّجاه
    wcss = os.path.join(web, "out", "vs", "code", "browser", "workbench", "workbench.css")
    css = _readtext(wcss)
    n_rtl = css.count("[dir=rtl]")
    assert n_rtl >= _WEB_MIN_RTL_RULES, f"قواعدُ الاتّجاه في الويب {n_rtl} < {_WEB_MIN_RTL_RULES}"

    # (4) الخطُّ — سياسةُ الويب `font-src 'self' blob:` تخلو من data: كسياسةِ المكتبيّ
    assert "src:url(kawkab-mono.woff2)" in css, (
        "خطُّ الويب ما زال data: — تحجبه CSP في المتصفّح [AR-02]")
    woff = os.path.join(os.path.dirname(wcss), "kawkab-mono.woff2")
    assert os.path.isfile(woff), f"القاعدةُ تشير إلى ملفٍّ غيرِ موجود: {woff}"
    with open(woff, "rb") as f:
        assert f.read(4) == b"wOF2", "ملفُّ خطِّ الويب ليس WOFF2 سليمًا"


# ── [WEB-03] محرابٌ الثابت (`vscode-web`) — الشجرةُ التي تُنشَر فعلًا ──
# بُنيت هذه الشجرةُ وعاشت خارجَ كلّ حارس: L2 يقيس `product.json`، ولا `product.json`
# فيها. فكانت تُنشَر بواجهةٍ إنجليزيّةٍ كاملةٍ وأيقونةِ VSCodium ومانيفستٍ باسمه —
# والطبقاتُ الخمسُ خضراء.
@check("محرابُ المتصفّح الثابت مُعرَّبٌ وهويّتُه هويّتُنا [WEB-03]")
def _static_arabized():
    web = _static_dir()
    if web is None:
        raise _Skip("لا شجرةَ vscode-web (‏gulp vscode-web-min هدفٌ اختياريّ)")

    # (1) صفحةُ المضيف وهويّتُها — البوّابةُ نفسُها التي يشغّلها البناء، بلا ازدواج.
    rc = subprocess.call([sys.executable,
                          os.path.join(ROOT, "build", "patch_web_host.py"),
                          "--verify", web])
    assert rc == 0, "بوّابةُ صفحة المضيف رفضت الشجرة (التفصيلُ أعلاه)"

    # (2) نواةُ الترجمة، ثمّ **ما يصل المتصفّح**. الفصلُ مقصود: خبزُ الأولى وحدَها
    # ترك الواجهةَ إنجليزيّةً بالكامل مرّةً سابقة.
    msgs = json.loads(_readtext(os.path.join(web, "out", "nls.messages.json")))
    ar, tot = _ar_ratio(msgs)
    pct = (ar * 100) // tot if tot else 0
    assert pct >= _WEB_MIN_AR_PCT, (
        f"الشجرةُ الثابتة {pct}% عربيّة ({ar}/{tot}) — دون العتبة {_WEB_MIN_AR_PCT}%. "
        f"ربّما عادت خطوةُ (ط-0د2) مربوطةً بشجرتين لا بثلاث.")

    js = _readtext(os.path.join(web, "out", "nls.messages.js"))
    jar, jtot = _ar_ratio(_nls_js_array(js))
    jpct = (jar * 100) // jtot if jtot else 0
    assert jpct >= _WEB_MIN_AR_PCT, (
        f"‏nls.messages.js الثابت — وهو ما يصل المتصفّح — {jpct}% عربيّة ({jar}/{jtot})")
    for _leak in ("vscodium", "VSCodium"):
        assert _leak not in js, f"«{_leak}» في nls.messages.js الثابت"

    # (3) الاتّجاهُ والخطُّ في **الورقة التي تحمّلها الصفحةُ فعلًا** — لا في ورقةٍ
    # أخرى. الحارسُ السابقُ كان يقيس `vs/code/browser/workbench/workbench.css`،
    # ولا وجودَ لها في هذه الشجرة.
    wcss = os.path.join(web, "out", "vs", "workbench", "workbench.web.main.internal.css")
    assert os.path.isfile(wcss), (
        "ورقةُ الورشة الثابتة مفقودة — والصفحةُ تصلها بـ<link>، فغيابُها واجهةٌ بلا أنماط")
    css = _readtext(wcss)
    n_rtl = css.count("[dir=rtl]")
    assert n_rtl >= _WEB_MIN_RTL_RULES, f"قواعدُ الاتّجاه في الثابت {n_rtl} < {_WEB_MIN_RTL_RULES}"
    assert "src:url(kawkab-mono.woff2)" in css, (
        "خطُّ الشجرة الثابتة ما زال data: — و`patch_workbench_font` لا يعرف ورقتَها [AR-02]")
    woff = os.path.join(os.path.dirname(wcss), "kawkab-mono.woff2")
    assert os.path.isfile(woff), f"القاعدةُ تشير إلى ملفٍّ غيرِ موجود: {woff}"
    with open(woff, "rb") as f:
        assert f.read(4) == b"wOF2", "ملفُّ خطِّ الشجرة الثابتة ليس WOFF2 سليمًا"

    # (4) وأصولُ الـwebview مشحونةٌ معنا — `boot.js` يوجّه إليها بدل شبكة المنبع،
    # ووجهةٌ فارغةٌ تعني إطارًا أبيضَ في كلّ معاينة.
    pre = os.path.join(web, "out", "vs", "workbench", "contrib", "webview",
                       "browser", "pre", "index.html")
    assert os.path.isfile(pre), (
        "أصولُ الـwebview غائبةٌ عن الشجرة — و`webviewEndpoint` يشير إليها")


def main():
    print("═══ L2: تأكيدات الحزمة المشحونة ═══")
    packaged = os.path.isdir(OUT)
    if not packaged and not os.path.isfile(JS):
        print(f"  ⏭️  لا مخرَج بناء ({OUT}) ولا ناتج تصغير ({MIN_OUT}) — تخطٍّ "
              f"(شغّل build/build.sh أوّلًا).")
        return 0
    failed = 0
    skipped = 0
    ran = 0        # ما جرى فعلًا — لا ما كان يمكن أن يجري
    if not packaged:
        # وضعٌ جزئيّ **مُعلَن**: العلامات تُفحَص على ناتج التصغير (المكافئ بايتيًّا)، وفحوص
        # الحزمة (exe/أصول/امتدادات) تُتخطّى صراحةً. لا ندّعي تغطيةً لم تجرِ.
        print(f"  ⏭️  لا حزمة مُغلَّفة — العلامات تُفحَص على {os.path.relpath(MIN_OUT, ROOT)} "
              f"(نسخة حرفيّة منه في الحزمة)، وفحوص الأصول/exe متخطّاة.")
        for name, fn, _wo in _checks:
            # استثناءٌ مُعلَن: فحوصُ شجرة الويب لا تقرأ `$APP_DIR` إطلاقًا، فربطُها
            # ببوّابةِ «حزمةٌ مكتبيّةٌ مُغلَّفة» يُسكِتها بلا سبب — وهو ما كان يقع على
            # لينكس حيث تُبنى شجرةُ الويب المنشورة.
            if "[WEB-01]" in name or "[WEB-03]" in name:
                try:
                    fn(); ran += 1; print(f"  ✅ {name}")
                except _Skip as e:
                    skipped += 1; print(f"  ⏭️  {name} — {e}")
                except Exception as e:  # noqa: BLE001
                    ran += 1; failed += 1; print(f"  ❌ {name}: {e}")
                continue
            print(f"  ⏭️  {name} — يحتاج حزمة مُغلَّفة.")
    else:
        for name, fn, win_only in _checks:
            if win_only and not _IS_WIN:
                skipped += 1
                print(f"  ⏭️  {name} — يخصّ ويندوز ({_platform.system()}).")
                continue
            try:
                fn()
                ran += 1
                print(f"  ✅ {name}")
            except _Skip as e:
                skipped += 1
                print(f"  ⏭️  {name} — {e}")
            except Exception as e:  # noqa: BLE001
                ran += 1
                failed += 1
                print(f"  ❌ {name}: {e}")
    for desc, path, needle, minc in BUNDLE_MARKERS:
        c = _count(path, needle)
        if c is None:
            failed += 1
            print(f"  ❌ {desc}: ملفّ الحزمة مفقود ({os.path.basename(path)})")
        elif c >= minc:
            print(f"  ✅ {desc} (×{c})")
        else:
            failed += 1
            print(f"  ❌ {desc}: «{needle}» غائب عن الحزمة (سقط في التحزيم/التصغير؟)")
    # العدُّ من الواقع لا من النيّة: `len(_checks)` كان يَعِد بفحوصٍ لم تُشغَّل أصلًا
    # في الوضع غير المُغلَّف، ويطرح المتخطَّى منها فيختلّ الطرفان معًا.
    n = ran + len(BUNDLE_MARKERS)
    _sk = f" · {skipped} متخطًّى بسببٍ معلَن" if skipped else ""
    print(f"─── {n - failed}/{n} نجحت{_sk} ───")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
