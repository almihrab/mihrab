# -*- coding: utf-8 -*-
"""مانيفست رُقَع محراب — مصدر الحقيقة الوحيد لطبقة الاختبار (L0/L1).

لكلّ مرقِّع يُطبَّق على مصدر المنبع (VSCode داخل VSCodium): كيف يُستدعى (ملفّ مفرد أم
جذر)، وأيّ ملفّات المنبع يمسّها. **مشتقّ حرفيًّا من كتلة الحقن في patch_bundle_extensions.py**
(الأوامر التي يشغّلها build.sh المنبع). حين تُغيّر أهداف مرقِّع، حدّث هنا — واختبار L0
يتحقّق أنّ المانيفست متّسق مع المرقِّعات الفعليّة.

الأوضاع:
  - "file": يُستدعى `python <patcher> <target.ts>` — target واحد.
  - "root": يُستدعى `python <patcher> <root>` — يشتقّ ملفّاته من قائمة FILES داخله.
"""

# (اسم المرقِّع، الوضع، [ملفّات المنبع النسبيّة التي يمسّها])
# ملاحظة: نسخُ ورقتَي الأنماط إلى media/ ليس من عمل `patch_workbench_rtl` (كما كان مكتوبًا
# هنا خطأً) — يفعله `build.sh` تهيئةً و`patch_bundle_extensions` حقنًا. والمرقِّعُ يحقن
# **استيرادَهما** وحدَه. وفحصُ المراسي يحتاج workbench.ts فقط.
PATCHERS = [
    ("patch_main_locale.py", "file", ["src/main.ts"]),
    ("patch_workbench_rtl.py", "file", ["src/vs/workbench/browser/workbench.ts"]),
    ("patch_menubar_rtl.py", "file", ["src/vs/base/browser/ui/menu/menubar.ts"]),
    ("patch_menu_rtl.py", "file", ["src/vs/base/browser/ui/menu/menu.ts"]),
    ("patch_gridview_marker.py", "file", ["src/vs/base/browser/ui/grid/gridview.ts"]),
    ("patch_splitview_rtl.py", "file", ["src/vs/base/browser/ui/splitview/splitview.ts"]),
    ("patch_sash_rtl.py", "file", ["src/vs/base/browser/ui/sash/sash.ts"]),
    ("patch_tabsdrop_rtl.py", "file",
     ["src/vs/workbench/browser/parts/editor/multiEditorTabsControl.ts"]),
    ("patch_welcome_rtl.py", "file",
     ["src/vs/workbench/contrib/welcomeGettingStarted/browser/gettingStarted.ts"]),
    # اتّجاهُ لوح شرح الجولة: مستندُ webview مستقلٌّ لا يرث dir القشرة (والمطهِّر ينزع dir
    # من محتوانا، فلا مَخرجَ من L1). يشتقّ dir/lang من مستند المضيف.
    ("patch_walkthrough_dir.py", "file",
     ["src/vs/workbench/contrib/welcomeGettingStarted/browser/gettingStartedDetailsRenderer.ts"]),
    # إسقاط جولات المنبع التعريفيّة كي تتصدّر جولة محراب صفحةَ الترحيب.
    ("patch_walkthroughs_drop.py", "file",
     ["src/vs/workbench/contrib/welcomeGettingStarted/browser/gettingStartedService.ts"]),
    # تصريح <html lang> من product.defaultLocale (يُفعّل :lang(ar) ويُصلح نطق قارئات الشاشة).
    ("patch_html_lang.py", "file",
     ["src/vs/code/electron-browser/workbench/workbench.ts"]),
    # افتراضُ الحوار المشروط = custom: بدونه يعرض ويندوز حوارَه بلغته وباتّجاه LTR.
    ("patch_dialog_style.py", "file",
     ["src/vs/workbench/electron-browser/desktop.contribution.ts"]),
    # جذر: مجلّد إعدادات المشروع `.محراب` بتوافقٍ خلفيّ. ستّةَ عشرَ ملفًّا لأنّ المنبع
    # يكتب '.vscode' حرفيًّا خارج ثابته — تبديلُ الثابت وحده يجعل المحرّر يقرأ من
    # مكانٍ ويكتب في آخر بلا خطأٍ ولا سجلّ. يُضيف كذلك وحدتَي TS من patches/core/.
    ("patch_config_folder.py", "root", None),
    # عناوين لوحة الإعدادات: مشتقّةٌ حسابيًّا من اسم المفتاح وقت التشغيل، فلا مدخلَ لها
    # في NLS ولا يبلغها خبزُ العربيّة. تُعرَّب بإلحاق استدعاءٍ بمخرَج wordifyKey.
    ("patch_settings_labels.py", "root", None),
    # بياناتُ نسخةِ ويندوز في الثنائيّات المشحونة: المنبعُ يكتب ناشرَه في أربعة
    # مواضعَ (‏حزمةُ Electron · rcedit للوحدات الأصليّة · بناءُ الخادم · مواردُ CLI)،
    # فكان المشحونُ ينسب نفسَه إلى VSCodium وإلى Microsoft Corporation.
    ("patch_win_metadata.py", "root", None),
]

# رُقَع «الجذر» تشتقّ ملفّاتها من قائمة FILES داخلها. لا تُسرَد هنا يدويًّا: نسخةٌ
# يدويّة تتباعد عن الحقيقة صامتةً، فيمرّ فحصُ المراسي على ملفٍّ لم يعد مقصودًا.
ROOT_PATCHER_FILES_ATTR = {
    "patch_config_folder.py": "FILES",
    "patch_settings_labels.py": "FILES",
    "patch_win_metadata.py": "FILES",
}

# مرقِّعات بناء لا تُطبَّق على مصدر vscode مباشرةً (تُستثنى من فحص المراسي L1، لكنّها
# تخضع لفحص الصياغة في L0):
BUILD_PATCHERS = [
    "patch_bundle_extensions.py",  # يرقّع build.sh المنبع (لا مصدر vscode)
    "bake_nls_arabic.py",          # خطوة بعد-بناء على الـartifacts
    "patch_extension_nls.py",      # حقن package.nls.ar.json للامتدادات (بعد-بناء)
    "patch_node_gyp_spectre.py",   # م0
    "patch_npmrc_tolerance.py",    # م0
]

# رُقَعُ **المنبع** (diff موحَّد لا مرقِّع بايثون): تعديلاتٌ مصوغةٌ للرفع إلى microsoft/vscode
# ومحفوظةٌ هنا حتّى تُدمَج. تُطبَّق بـ`git apply --3way` داخل شجرة vscode بعد reset. لا مراسيَ
# لها تُفحَص فرديًّا: الفحصُ أن تُطبَّق نظيفةً على المنبع المثبَّت (L1) — وهو أقوى من مرساة.
#   • 010-editor-text-direction.patch ⇐ المقترح م-٢ (خيار editor.textDirection). وُلِّد من
#     شوكةٍ نظيفة على العقدة نفسها؛ لا يُحرَّر يدويًّا بل يُعاد توليده منها.
#   • 020-nonlatin-word-start.patch ⇐ المقترح م-١٥/ب (حدُّ الكلمة بعد أداة التعريف في
#     المطابقة الضبابيّة). أثرُه مقيسٌ في tests/dx/completion_rank.mjs — قبلَه وبعدَه.
CORE_DIFFS = [
    "patches/core/010-editor-text-direction.patch",
    "patches/core/020-nonlatin-word-start.patch",
    # صناديقُ الإدخال البسيطة (رسالةُ الالتزام · وحدةُ التصحيح · شرطُ نقطة التوقّف · الدردشة):
    # `getSimpleEditorOptions` يقرأ ستّةَ مفاتيحَ من الإعدادات ولا يقرأ `textDirection` ولا
    # `fontLigatures` — فكلُّ صندوقِ كتابةٍ في المنضدة فقرةٌ LTR بأحرفٍ مفكَّكة. وموضعُ الإصلاح
    # اختير هنا لا في `scmInput.ts` وحدَه: أحدَ عشرَ مستهلكًا يعبرون منه دفعةً واحدة.
    "patches/core/030-simple-editor-rtl-input.patch",
    # شجرةُ التنقيح تُحجَّم نصفَ تحجيم [DG-01]: ارتفاعُ الصفّ يتبع
    # `workbench.sideBar.experimental.fontSize` (‏`VariablesDelegate.getHeight` ⇐ `FONT.sidebarSize22`)
    # والحبرُ داخلَه مثبَّتٌ ‎13px‎ في الورقة. فمن كبّر خطَّ شريطه الجانبيّ كبُر صفُّه وبقي حرفُه —
    # وهو السطحُ الوحيدُ في الشريط الذي لا يجيب المفتاحَ الموضوعَ لتحجيمه. والرقعةُ **لا تُنشئ
    # مفتاحًا**: تربط الورقةَ بالمتغيّر الذي يضعه `sidebarPart.ts` سلفًا ويستهلكه بقيّةُ التنقيح.
    "patches/core/031-debug-tree-font-size.patch",
    # صندوقُ الالتزام يلتقط الاتّجاهَ والأشكالَ السياقيّةَ وارتفاعَ السطر **عند الإنشاء ولا
    # يتجدّد** [SC-01 · م-١٧]: المفاتيحُ الثلاثةُ ليست في مُرشِّح تغيّر الإعدادات، ومفتاحان
    # منها ليسا في حمولة `getEditorOptions()` أصلًا — فالمرشِّحُ وحدَه إصلاحٌ فارغٌ لاثنين من
    # ثلاثة. والصندوقُ يعمّر عمرَ الجلسة (‏`RowCache` يُعيد الصفوفَ إلى مخبأ)، فمن غيّر ثمّ
    # أظهر مستودعًا ثانيًا رأى **صندوقَين يختلفان في الاتّجاه** — خللٌ لا تأخير.
    "patches/core/032-scm-input-live-options.patch",
    # بندُ هروبِ إبراز يونيكود يعدّ **أيَّ** محرف ASCII خلطَ كتابتَين [AR-05 · م-١٣/ب]:
    # تعليقُ المنبع نفسُه يقول «لا تخلط الغريبَ بـASCII» — والمقصودُ خلطُ **كتابتَين**، لا
    # وجودُ غِراءِ معرّفات. فالشَرطةُ السفليّةُ في `حقل_اسم` كانت تُسقِط الإعفاءَ فتُصنَّد كلُّ
    # ألفٍ وهاءٍ في معرّفات ص خارج نطاق `[sad]`. والقياسُ على بلاغِ مستخدمٍ حقيقيّ
    # (‏مفردات.yaml): ‎622‎ إبرازًا مرسومًا ⇐ ‎0‎، و‎1567‎ في كلّ ملفّات yaml ⇐ ‎7‎. **وصفرُ
    # حمايةٍ تسقط**: الكلمةُ التي تخلط كتابتَين حقًّا فيها حرفُ ASCII فتبقى مُشخَّصة.
    # والبديلُ المرفوض — رفعُ `allowedCharacters` إلى الجذر — كان يُسقِط الفحصَ الثلاثيَّ
    # كلَّه لتلك النقاط في كلّ لغة، ويمنعه توكيدٌ قائمٌ في AR-04.
    "patches/core/033-unicode-word-script-mixing.patch",
    # الطرفيّةُ حيث لا طرفيّة [WEB-05]: بناؤنا الثابت بلا خادم ⇒ `processSupported` كاذب،
    # وكلُّ أوامر الطرفيّة مُقيَّدةٌ به سلفًا. لكنّ **وصفَ العرض** غيرُ مقيَّد، ومنه يشتقّ
    # `viewsService` لسانَ اللوحة وأمرَ الفتح (‏Ctrl+Backquote) وبندَ قائمة العرض — ثلاثةُ
    # مداخلَ من إغفالٍ واحد. والرابعُ قاعدةُ Ctrl+Shift+C في `terminal.web.contribution.ts`:
    # تُسجَّل على سجلّ الاختصارات مباشرةً فتتخطّى `precondition` الذي يحرس الأمرَ في كلّ
    # مكانٍ آخر. والخامسُ بندُ «طرفيّة جديدة» في قائمة الطرفيّة — إخوتُه الأربعةُ في الكتلة
    # نفسِها يحملون الشرطَ وهو وحدَه لا يحمله. والوعدُ الذي لا خلفيّةَ له أسوأُ من غياب
    # الميزة: لوحٌ يُفتَح ولا يُنتج شيئًا يُقرأ عطبًا في جهاز المستخدم لا حدًّا في المنتَج.
    "patches/core/034-terminal-unavailable-in-web.patch",
]

# طبقة الأنماط (تُفحَص في L0/L2 لا L1):
CSS_PATCH = "patches/mihrab-rtl.css"

# ورقةُ الهويّة البصريّة [VA-05] — **منفصلةٌ عمدًا** عن ورقة الاتّجاه. قواعدُها ليست دَينَ
# اتّجاهٍ (لا تقلب شيئًا)، وخلطُها بالأولى كان يجعل مؤشّرَ صحّة الطبقات يبالغ في الدَّين.
# تُستورَد بعدها في workbench.ts، وتخضع لحارسٍ خاصٍّ يمنع تسلّلَ أيّ خاصّيّةٍ اتّجاهيّة إليها.
IDENTITY_CSS = "patches/mihrab-identity.css"

# أصنافُ الهويّة المحقونة — **مصدرُ حقيقةٍ واحد** لثلاثة قرّاء: حارسا L0 (‏`_css_lint`
# و`_identity_css_lint`) ومِجَسّاتُ L2 في `check_injected.py`. تحقنها `patch_welcome_rtl.py`
# في ترويسة صفحة الترحيب. وكانت مسرودةً في موضعين، ونسختان لحقيقةٍ واحدة تتباعدان صامتتين:
# صنفٌ رابعٌ يُضاف إلى الحارس ولا يُضاف إلى المِجَسّ يمرّ بلا شاهدٍ على وصوله.
IDENTITY_CLASSES = ("mihrab-welcome-mark", "mihrab-welcome-pattern", "mihrab-welcome-lede")

# أصول الهوية البصريّة: يجهّزها build.sh في .mihrab-branding ويحقنها patch_bundle_extensions
# فوق resources/win32/ (electron.ts:winIcon='resources/win32/code.ico' ⇒ أيقونة الـexe؛
# code.iss:SetupIconFile ⇒ المُثبِّت؛ code_*x*.png ⇒ بلاطات ابدأ؛ default.ico ⇒ أيقونة
# المستند الافتراضيّة في المستكشف). تُفحَص في L0 (وجود) وL2 (تطابق بايتيّ مع الحزمة).
# قائمة أزواج (مصدر، هدف في resources/win32/) — الأصل الواحد قد يُنسَخ لهدفين.
BRANDING_ASSETS = [
    ("assets/branding/mihrab.ico", "code.ico"),
    ("assets/branding/mihrab.ico", "default.ico"),
    ("assets/branding/mihrab_150x150.png", "code_150x150.png"),
    ("assets/branding/mihrab_70x70.png", "code_70x70.png"),
]

# أصول SVG لهوية الأسطح غير resources/win32/ (شعار رأس التطبيق + خلفية المحرّر الفارغ).
# (مصدر, مسار الوجهة المنبعيّ داخل src/) — تُحقَن في كتلة INJECT بـcp -f.
BRANDING_SVG_ASSETS = [
    ("assets/branding/mihrab-appicon.svg", "src/vs/workbench/browser/media/code-icon.svg"),
    ("assets/branding/mihrab-letterpress-dark.svg", "src/vs/workbench/browser/parts/editor/media/letterpress-dark.svg"),
    ("assets/branding/mihrab-letterpress-light.svg", "src/vs/workbench/browser/parts/editor/media/letterpress-light.svg"),
    ("assets/branding/mihrab-letterpress-hcDark.svg", "src/vs/workbench/browser/parts/editor/media/letterpress-hcDark.svg"),
    ("assets/branding/mihrab-letterpress-hcLight.svg", "src/vs/workbench/browser/parts/editor/media/letterpress-hcLight.svg"),
]

# أصول مساحة sessions التجريبيّة (شعار حوض الأسماك المطموس + أيقونة Open-in + خلفيّة فارغة).
# (مصدر, وجهة داخل src/). vscodeLogoPath.ts مسار مطموس مملوء يُبنَى في sessions.desktop.main.js.
BRANDING_SESSIONS_ASSETS = [
    ("assets/branding/mihrab-sessions-icon.svg", "src/vs/sessions/browser/media/vscode-icon.svg"),
    ("assets/branding/mihrab-vscodeLogoPath.ts", "src/vs/sessions/contrib/aquarium/browser/vscodeLogoPath.ts"),
    ("assets/branding/mihrab-letterpress-sessions-dark.svg", "src/vs/sessions/contrib/chat/browser/media/letterpress-sessions-dark.svg"),
    ("assets/branding/mihrab-letterpress-sessions-light.svg", "src/vs/sessions/contrib/chat/browser/media/letterpress-sessions-light.svg"),
]


# ملفّاتُ **مرجعٍ** لا ترقيع: لا نمسّها، لكنّ فحوصًا تشتقّ منها توقّعاتِها بدل كتابتها
# بالحدس. تُنسَخ إلى اللقطة مع ملفّات الرُقَع لأنّ `.upstream/` مُتجاهَلٌ في git، وبلا
# نسخةٍ مُلتزَمةٍ يصير الفحصُ المشتقّ معطَّلًا في CI صامتًا.
#   • strings.ts: جدولُ المحارف الملتبِسة (`_common`) ⇐ يشتقّ منه AR-04 قائمةَ الإعفاء.
#   • wordHelper.ts: `USUAL_WORD_SEPARATORS` ⇐ يشتقّ منه IN-01 **بادئةَ** قيمتنا. وقيمةُ
#     `editor.wordSeparators` سُلَّميّةٌ من نوع string: تجاوزُها **يستبدل** الافتراضَ ولا
#     يضيف إليه، فنحن مضطرّون إلى نسخ ثابتٍ منبعيٍّ إلى ملفّنا. ولولا هذا المرجعُ لانحرفت
#     النسخةُ صامتةً لو زاد المنبعُ محرفًا — وهو الصنفُ نفسُه الذي يحرسه strings.ts.
#     ولم يُضَف `cursorWordOperations.ts` ولا `wordCharacterClassifier.ts`: لا فحصَ يشتقّ
#     منهما توقُّعًا، وانجرافُ **الخوارزميّة** يمسكه القياسُ الحيّ (`word_boundaries.live.mjs`)
#     لا مقارنةُ نصّ. ملفُّ مرجعٍ بلا مشتقٍّ منه وزنٌ يُحمَل بلا حراسةٍ تُكتسَب.
#   • webview/pre/index.html: مستضيفُ **كلِّ** لوحات الـwebview، وترويسةُ CSP فيه تحمل
#     `script-src 'sha256-…'` لبرنامجها المضمَّن الوحيد. البصمةُ **مصونةٌ يدويًّا** — ظهرت
#     مرّةً واحدةً في الشجرة كلِّها، ولا خطوةَ بناءٍ تعيد حسابها. فتعديلُ بايتٍ واحدٍ في جسم
#     البرنامج يُبطلها، فيحجب المتصفّحُ البرنامجَ كلَّه وتنطفئ **كلُّ** اللوحات — بلا خطأٍ في
#     الطرفيّة ولا لوحٍ فارغٍ مُعلَّل. كمينٌ صامتٌ يستحقّ حارسًا قبل أن تُكتَب رقعتُه، لا بعدها.
#     ويشتقّ منه `check_webview_csp` توقُّعَه: البصمةُ تُحسَب على الجسم **بعد تسوية الأسطر
#     إلى LF** (‏CRLF يعطي بصمةً أخرى — قِيس الطرفان).
REFERENCE_FILES = [
    "src/vs/base/common/strings.ts",
    "src/vs/editor/common/core/wordHelper.ts",
    "src/vs/workbench/contrib/webview/browser/pre/index.html",
]

# الملفُّ الذي يفحصه حارسُ بصمةِ CSP (‏L1) — مُسمًّى مرّةً ليقرأه الحارسُ والوثائقُ معًا.
WEBVIEW_HOST_HTML = "src/vs/workbench/contrib/webview/browser/pre/index.html"


def root_target_files(build_dir, patcher):
    """يستورد مرقِّعَ جذرٍ ويعيد قائمة الملفّات النسبيّة التي يمسّها (من FILES).

    build_dir: مسار مجلّد build/ (حيث المرقِّع). يعيد قائمة relpaths (بأسلوب src/vs/...).
    """
    import importlib.util
    import os

    attr = ROOT_PATCHER_FILES_ATTR.get(patcher, "FILES")
    path = os.path.join(build_dir, patcher)
    spec = importlib.util.spec_from_file_location(
        "_mihrab_" + patcher.replace(".", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [relpath for (relpath, _mark, _edits) in getattr(mod, attr)]


def core_diff_files(root_dir, diff_relpath, existing_only=False):
    """الملفّاتُ التي يمسّها diff موحَّد (من أسطر `+++ b/...`) — لا تُسرَد يدويًّا.

    existing_only=True يستثني الملفّاتِ التي **يُنشئها** الـdiff (`--- /dev/null`): لا نسخةَ
    نظيفةَ لها في المنبع بحكم التعريف، فطلبُها يُسقِط الفحصَ تخطّيًا كاذبًا.
    """
    import os

    files = []
    path = os.path.join(root_dir, diff_relpath.replace("/", os.sep))
    prev = ""
    with open(path, "r", encoding="utf-8", newline="") as f:
        for line in f:
            if line.startswith("+++ b/"):
                rel = line[6:].strip()
                is_new = prev.startswith("--- /dev/null")
                if rel != "/dev/null" and rel not in files and not (existing_only and is_new):
                    files.append(rel)
            prev = line
    return files
