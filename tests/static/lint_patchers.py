#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0 — فحص ساكن لطبقة رقعة محراب (ثوانٍ، بلا بناء، بلا منبع، صالح لـCI).

يمسك: مرقِّع معطوب نحويًّا، وسم مكرّر/عدّ خاطئ في FILES، JSON غير صالح، **انجراف مانيفست
حزمة اللغة عن الملفّات**، قواعد CSS غير مقصورة على RTL، ومانيفست الرُقَع غير متّسق.

الاستعمال: python tests/static/lint_patchers.py   (خرج 0 = نجاح، 1 = فشل)
لا يعتمد pytest (أسرار CI صفريّة) — إطار فحص بسيط داخليّ.
"""
import json
import os
import py_compile
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
ROOT = os.path.dirname(os.path.dirname(HERE))  # جذر mihrab-ide
BUILD = os.path.join(ROOT, "build")



# أوامرُ المنبع المسموحُ استدعاؤها من روابط `command:` في خطوات الجولة. تُسرَد بالاسم
# لا بقاعدةٍ عامّة: `workbench.*` كان سيُمرِّر خطأً مطبعيًّا في اسمٍ لا نملكه.
UPSTREAM_CMDS_IN_WALKTHROUGH = ("workbench.action.openSettings",)
sys.path.insert(0, os.path.dirname(HERE))  # tests/
import patch_manifest as M  # noqa: E402

# أصنافُ الهويّة المحقونة — من المانيفست لا نسخةً محلّيّة [VA-05].
IDENTITY_CLASSES = M.IDENTITY_CLASSES

_checks = []


def check(name):
    def deco(fn):
        _checks.append((name, fn))
        return fn
    return deco


def _read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


# ───────────────────────── L0-1: صياغة المرقِّعات ─────────────────────────
@check("كلّ مرقِّعات build/ تُصرَّف (Python)")
def _compile_all():
    pys = [f for f in os.listdir(BUILD) if f.endswith(".py")]
    assert pys, "لا مرقِّعات في build/"
    for f in pys:
        py_compile.compile(os.path.join(BUILD, f), doraise=True)


@check("لا شاهدة خلفيّة في تعليقٍ داخل قالب نصّيّ (فخّ أسقط ملفَّين فعلًا)")
def _no_backtick_in_templates():
    """يمنع فخًّا **وقعنا فيه مرّتين** فأسقط الملفّ كلَّه بـSyntaxError.

    ‏JS ونحن نكتب DOM/CSS داخل قوالب نصّيّة (`` evaluate(`…`) `` و``webview.html = `…` ``)،
    ونشرح داخلها بالعربيّة. وأيّ شاهدةٍ خلفيّة في تعليقٍ **داخل القالب** تُنهي القالب هناك،
    فينهار ما بعده نحويًّا ويصير الخطأ في سطرٍ لا علاقة له بالسبب — أضلَّنا مرّتين:
    مرّةً في `chat.js` (أمسكها اختبار الوحدة) ومرّةً في `harness.mjs` (أمسكها التشغيل الحيّ).
    الفحص ساكن ورخيص، فيسبق الاثنين.

    نمسح **سطور التعليق وحدها** داخل القوالب: الشاهدة في شيفرةٍ فعليّة داخل القالب قد تكون
    مقصودة (قالب متداخل)، أمّا في تعليقٍ فلا فائدة منها أبدًا — البديل ‎U+200E‎ حولها.
    """
    import re as _re
    targets = [os.path.join(ROOT, "tests", "runtime", "harness.mjs"),
               os.path.join(ROOT, "tests", "runtime", "launch.mjs"),
               os.path.join(ROOT, "tests", "runtime", "rtl.spec.mjs"),
               os.path.join(ROOT, "extensions", "mihrab-nebras", "chat.js")]
    OPEN = _re.compile(r"(?:evaluate\(|html\s*=\s*|return\s+)`")
    for path in targets:
        if not os.path.isfile(path):
            continue
        inside, offenders = False, []
        for i, line in enumerate(_read(path).split("\n"), 1):
            if not inside:
                m = OPEN.search(line)
                # ⚠️ **القالبُ ذو السطر الواحد يُغلَق في سطره.** كان الفحص يفتح الحالة ثمّ
                # `continue` بلا فحص الإغلاق، فيبقى «داخل قالب» حتى يصادف سطرًا يُغلِق —
                # فيُبلِّغ عن كلّ تعليقٍ بينهما زورًا. أوقعَنا فيه أوّلُ سطرٍ من صنف
                # ``evaluate(`…`), 1`` أضفناه: أشعل إنذارًا على تعليقٍ قديمٍ سليم بعده
                # بأربعين سطرًا. **الحارسُ الكاذب أخطرُ من غيابه**: يُعلِّم القارئَ أنّ
                # حمرةَ هذا الفحص ضجيج، فيتجاهلها يوم تصدق.
                if m and "`" not in line[m.end():]:
                    inside = True
                continue
            # نهاية القالب: سطر يُغلقه (`)` أو `;` بعد شاهدة) — تقريبٌ كافٍ لملفّاتنا.
            if _re.search(r"`\s*[);]", line) or line.strip() == "`;":
                inside = False
                continue
            if line.lstrip().startswith("//") and "`" in line:
                offenders.append(i)
        assert not offenders, (
            f"{os.path.basename(path)}: شاهدة خلفيّة في تعليقٍ داخل قالب نصّيّ عند "
            f"السطور {offenders} — تُنهي القالب وتُسقِط الملفّ بـSyntaxError")


@check("لا هروب نمطيّ بشرطةٍ واحدة داخل قالب نصّيّ (فرعُ كشفٍ ماتَ صامتًا)")
def _no_single_escape_in_templates():
    """يمنع الفخّ **الأخطر** في قوالبنا: لا يُسقِط الملفّ، بل يُضعِف الكشف صامتًا.

    ما نكتبه داخل ``evaluate(`…`)`` يمرّ بمرحلتَي تأويل: قالبُ JS عندنا، ثمّ الشيفرة في
    الصفحة. فـ`\\p{L}` بشرطةٍ واحدة يبتلعها القالب ويصل إلى الصفحة `p{L}` — **صنفُ محارفٍ
    حرفيّ** لا فئةٌ يونيكوديّة. لا خطأ نحويّ ولا تحذير: تعبيرٌ صحيحٌ يطابق شيئًا آخر.

    وقع هذا عندنا مرّتين وكلتاهما كلَّفت:
      • `\\s` ⇒ `s` ⇒ `split(/s+/)` شَطَر أسماءَ الأصناف على حرف «s» فصار
        ‎composite-bar‎ ⇒ ‎compo.ite-bar‎، وأعاد الماسحُ ‎25‎ بلاغًا كاذبًا.
      • `\\p{L}` ⇒ `p{L}` ⇒ `strong` صار `null` في كلّ نصٍّ خالٍ من ‎p/L‎، فـ`startsLTR`
        `False` أبدًا، ففرعُ «المحايد الطرفيّ» **ميّتٌ كلُّه** — والفحص أخضر.

    الثاني هو الأسوأ: أخضرُ يعني «مسحنا ولم نجد» بينما الحقيقة «لم نبحث». فلا نتّكل على
    أن نتذكّر المضاعفة — نفرضها ساكنًا.

    نحصر الحروف المرصودة في `pPsSdDwWbB` (لا معنى لأيٍّ منها كهروبٍ نصّيّ)، ونستثني
    `\\n` و`\\t` و`\\u` — فهذه مقصودةٌ حرفيًّا داخل القوالب.
    """
    import re as _re
    targets = [os.path.join(ROOT, "tests", "runtime", "harness.mjs"),
               os.path.join(ROOT, "tests", "runtime", "launch.mjs"),
               os.path.join(ROOT, "tests", "runtime", "rtl.spec.mjs"),
               os.path.join(ROOT, "extensions", "mihrab-nebras", "chat.js")]
    OPEN = _re.compile(r"(?:evaluate\(|html\s*=\s*|return\s+)`")
    # شرطةٌ **فردٌ** (عددٌ زوجيّ من الشرطات قبلها ⇒ مُضاعَفة ⇒ سليمة) يتبعها حرفُ فئة.
    BAD = _re.compile(r"(?<!\\)(?:\\\\)*\\([pPsSdDwWbB])")
    for path in targets:
        if not os.path.isfile(path):
            continue
        inside, offenders = False, []
        for i, line in enumerate(_read(path).split("\n"), 1):
            if not inside:
                # نفس تصحيح القالب ذي السطر الواحد المشروح في `_no_backtick_in_templates`.
                m = OPEN.search(line)
                if m and "`" not in line[m.end():]:
                    inside = True
                continue
            if _re.search(r"`\s*[);]", line) or line.strip() == "`;":
                inside = False
                continue
            if line.lstrip().startswith("//"):
                continue                      # الشرح لا يصل الصفحةَ فلا يضرّ
            for m in BAD.finditer(line):
                if m.group(0).count("\\") % 2:   # فردٌ فعلًا
                    offenders.append((i, m.group(1)))
        assert not offenders, (
            f"{os.path.basename(path)}: هروبٌ بشرطةٍ واحدة داخل قالب نصّيّ عند "
            f"{offenders} — يصل الصفحةَ حرفًا عاديًّا فيموت فرعُ الكشف صامتًا. ضاعِف الشرطة.")


# ───────────────────── L0-2: سلامةُ رُقَع المنبع (diff) ─────────────────────
@check("رُقَعُ المنبع (CORE_DIFFS) موجودةٌ وسليمةُ الشكل ولا تمسّ غير src/")
def _core_diffs_shape():
    for diff in getattr(M, "CORE_DIFFS", []):
        path = os.path.join(ROOT, diff.replace("/", os.sep))
        assert os.path.isfile(path), f"رُقعةُ منبعٍ مفقودة: {diff}"
        with open(path, "r", encoding="utf-8", newline="") as f:
            text = f.read()
        assert text.startswith("diff --git "), f"ليست diff موحَّدة: {diff}"
        files = M.core_diff_files(ROOT, diff)
        assert files, f"رُقعةٌ بلا ملفّات: {diff}"
        for rel in files:
            assert rel.startswith("src/"), f"رُقعةُ منبعٍ تمسّ خارج src/: {rel} ({diff})"
        # وسمُ محرابٍ في شيفرةٍ يُفترَض أنّها منبعيّةٌ صرفة = دَينٌ لا يُرفَع.
        for token in ("mihrab", "محراب"):
            assert token not in text.lower() if token == "mihrab" else token not in text, (
                f"رُقعةُ المنبع {diff} تحوي «{token}» — لن تُقبَل في الرفع")


@check("كلُّ رُقعةِ منبعٍ موصولةٌ: تُنسَخ في build.sh وتُطبَّق في كتلة الحقن فشلًا لا تخطّيًا")
def _core_diffs_wired():
    """رُقعةٌ في `patches/core/` لا ينسخها أحدٌ ولا يطبّقها أحدٌ **تُقرأ كأنّها تعمل**.

    والمسارُ موضعان لا واحد: `build.sh` ينسخها إلى جوار شجرة المنبع باسمٍ مُنقَّط،
    و`patch_bundle_extensions.py` يطبّقها من داخل الشجرة بعد الـreset. وسقوطُ أيٍّ منهما
    لا يُفشِل بناءً ولا يترك أثرًا في سجلّه — يخرج المنتجُ ناقصَ الإصلاح وحسب.

    ويُفحَص كذلك أنّ الفشلَ **قاتلٌ**: `git apply` لرقعةٍ انجرفت مرساتُها يجب أن يوقف
    البناء، لا أن يمرّ فيَشحن إصلاحًا لم يُطبَّق.
    """
    diffs = getattr(M, "CORE_DIFFS", [])
    assert diffs, "لا رُقَعَ منبعٍ في المانيفست — عمِيَ الفحص"
    build_sh = _read(os.path.join(ROOT, "build/build.sh"))
    inject = _read(os.path.join(ROOT, "build/patch_bundle_extensions.py"))
    for diff in diffs:
        # اسمُ الوجهة يُقرأ من `build.sh` نفسِه لا يُخمَّن: السطرُ الذي يذكر الرقعةَ هو
        # الذي يسمّي الملفَّ المنقوط، فالمِجَسُّ يتبع الصياغةَ ولا يفرضها.
        lines = [ln for ln in build_sh.splitlines() if diff in ln]
        assert lines, f"build.sh لا ينسخ رُقعةَ المنبع {diff} — تصل الشجرةَ من العدم؟"
        m = re.search(r'\$UP/(\.[\w.-]+\.patch)', lines[0])
        assert m, f"سطرُ نسخِ {diff} في build.sh لا يسمّي ملفَّ وجهةٍ منقوطًا: {lines[0].strip()}"
        dest = m.group(1)
        assert dest in inject, (
            f"‏{dest} يُنسَخ ولا يُطبَّق: لا ذكرَ له في كتلة الحقن — رقعةٌ تُشحَن ولا تُقرأ ({diff})")
        applied = [ln for ln in inject.splitlines() if dest in ln and "git apply" in ln]
        assert applied, f"‏{dest} مذكورٌ في كتلة الحقن بلا `git apply` — لا يُطبَّق ({diff})"
        assert "exit 1" in applied[0], (
            f"تطبيقُ {dest} لا يُفشِل البناء عند الخطأ — انجرافُ مرساةٍ يمرّ صامتًا ({diff})")
        # ورقعةٌ بلا سطرٍ في جدول `patches/README.md` دَينٌ لا يعرفه أحدٌ بعد أشهر.
        assert os.path.basename(diff) in _read(os.path.join(ROOT, "patches/README.md")), (
            f"‏{diff} غيرُ مذكورٍ في patches/README.md — رقعةٌ تُشحَن بلا مبرَّرٍ مكتوب")


# ───────────────────── L0-2ب: بنية FILES في مرقِّعات الجذر ─────────────────────
@check("FILES في مرقِّعات الجذر سليمة (وسوم فريدة، عدّ موجب، شكل صحيح)")
def _editor_files_shape():
    import importlib.util
    root_patchers = [n for n, m, _t in M.PATCHERS if m == "root"]
    assert root_patchers, "لا مرقِّعَ جذرٍ في المانيفست"
    for patcher in root_patchers:
        _check_files_shape(patcher)


def _check_files_shape(patcher):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_root_" + patcher.replace(".", "_"), os.path.join(BUILD, patcher))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    attr = M.ROOT_PATCHER_FILES_ATTR.get(patcher, "FILES")
    files = getattr(mod, attr, None)
    assert files, f"{attr} مفقودة/فارغة في {patcher}"
    marks = []
    for entry in files:
        assert len(entry) == 3, f"إدخال FILES ليس ثلاثيًّا: {entry[:1]}"
        relpath, mark, edits = entry
        # ‏`src/` ليست الجذرَ الوحيد: بياناتُ نسخةِ ويندوز تُكتَب في سكربتات البناء
        # (`build/lib/electron.ts`) وفي مواردِ Rust (`cli/build.rs`)، لا في مصدر المحرّر.
        # وحصرُ المسار في `src/` كان سيمنع رقعةً صحيحةً بحجّةٍ شكليّة.
        assert isinstance(relpath, str) and relpath.startswith(("src/", "build/", "cli/")),             f"مسار غير صالح: {relpath}"
        assert isinstance(mark, str) and mark, f"وسم غير صالح لـ{relpath}"
        marks.append(mark)
        assert edits, f"لا تعديلات لـ{relpath}"
        for e in edits:
            assert len(e) == 3, f"تعديل ليس ثلاثيًّا في {relpath}"
            old, new, count = e
            # **والمرساةُ قد تكون صورًا لا صورةً واحدة.** مرقِّعٌ يعمل على شجرتين
            # (نظيفةٍ من مايكروسوفت في L1 وdev_sync · ومعالَجةٍ بـVSCodium في البناء)
            # يحتاج صورتين للنصّ نفسِه. تُفحَص كلُّ صورةٍ بالشروط نفسِها — فالتعميمُ
            # يوسّع ما يُقبَل شكلًا ولا يُرخي شيئًا ممّا يُفحَص.
            forms = old if isinstance(old, (tuple, list)) else (old,)
            assert forms, f"مرساة فارغة في {relpath}"
            for form in forms:
                assert isinstance(form, str) and form, f"مرساة فارغة في {relpath}"
                assert form != new, f"مرساة == استبدال في {relpath} (لا عمل)"
            assert isinstance(new, str) and new, f"استبدال فارغ في {relpath}"
            assert isinstance(count, int) and count > 0, f"عدّ غير موجب في {relpath}"
    # لا نُلزِم «الاستبدالُ يحوي المرساةَ أو الوسم»: مرقِّعاتُ الجذر تختلف في آليّة
    # الـidempotency (وسمٌ في الملفّ · ثابتٌ مستورَد · استبدالٌ كامل)، وL1 يبرهنها فعليًّا
    # بإعادة تشغيل المرقِّع والتأكّد أنّ شيئًا لم يتغيّر — وهو برهانٌ لا ادّعاء.
    # المسارات لا تتكرّر (إدخالان لملفٍّ واحد ⇒ الثاني يُتخطّى بالوسم فيموت صامتًا).
    # أمّا الوسمُ نفسُه فقد يتكرّر عبر ملفّاتٍ عمدًا (رقعةٌ واحدة بوسمٍ واحد لملفّين).
    paths = [e[0] for e in files]
    assert len(paths) == len(set(paths)), f"مساراتٌ مكرّرة في {patcher}: {paths}"


# ───────── L0-2أ: وسم إصدار الرُقَع مضمَّن في كتلة الحقن ─────────
@check("إصدار رُقَع النواة: VERSION_MARK حاضر في INJECT (لا حقنٌ بائت)")
def _core_patch_version_embedded():
    """رفعُ CORE_PATCH_VERSION دون تحديث التعليق داخل INJECT خطأٌ **حدث فعلًا**.

    ‏patch_bundle_extensions يتحقّق منه وقت التشغيل ويُجهض — لكنّ ذلك يقع داخل `build.sh`
    بعد دقائق من التجهيز. هنا يصير الفشلُ ثانيتين. (ولو غاب الحارسان معًا لبقي البناءُ
    يستعمل حقنًا بائتًا بلا الرُقَع الجديدة — نجاحٌ كاذب، أسوأ من إخفاق.)
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_pbe", os.path.join(BUILD, "patch_bundle_extensions.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.VERSION_MARK in mod.INJECT, (
        f"«{mod.VERSION_MARK}» غير موجود في INJECT — حدّث التعليق داخل الكتلة مع رفع الإصدار.")

    # **والاتّجاهُ المعاكس — وهو الذي وقع.** الفحصُ أعلاه يمسك «رُفِع الإصدارُ ونُسِي
    # التعليق». أمّا «وُسِّعت الكتلةُ ونُسِي الإصدارُ» فكان يمرّ صامتًا: يرى المرقِّعُ
    # وسمَه الحاليَّ في `build.sh` المُرقَّع من بناءٍ سابق فيتخطّى، ولا يُستعاد الملفُّ
    # نظيفًا، ولا تُحقَن الرقعةُ الجديدة. البناءُ ينجح والرقعةُ غائبة.
    #
    # قِيس يوم 2026-09-04: أُضيفت رقعةُ بيانات نسخةِ ويندوز إلى INJECT بلا رفعِ الإصدار،
    # فبُني ‎1.126.05942‎ كاملًا والثنائيّاتُ ما زالت تقول «VSCodium» و«Microsoft
    # Corporation». وما كشفه إلّا حارسُ L2 الذي كُتب للرقعة نفسِها.
    # **لا بصمةَ مكتوبةً بيد بعد اليوم.** حُرِس هذا الموضعُ ببصمةٍ ثابتةٍ ثمّ بسجلٍّ
    # بالإصدارات، وكلاهما يسأل «هل حدّثتَ الثابت؟» لا «هل تغيّر المحتوى؟» — وجُرِّب
    # المسارُ الذي يُبطلهما (تغييرُ الحقن ثمّ نسخُ البصمة الجديدة من رسالة الخطأ)
    # فمرّ أخضرَ والوسمُ لم يتحرّك. فصار الوسمُ **مشتقًّا من المحتوى**، والخطوةُ
    # اليدويّةُ التي كانت تُنسى لم تعد موجودة.
    #
    # فما يبقى للحارس شيئان: أنّ الاشتقاق يعمل، وأنّ الوسمَ فعلًا داخلَ الحقن.
    import hashlib
    expect = mod._derive_mark(mod._INJECT_TEMPLATE)
    assert mod.VERSION_MARK == expect, (
        f"الوسمُ ليس مشتقًّا من القالب ({mod.VERSION_MARK} ≠ {expect}) — "
        f"أُعيد إلى الكتابة اليدويّة، فعاد بابُ «حقنٍ يُتخطّى صامتًا».")
    assert "{MARK}" not in mod.INJECT, "موضعُ الوسم لم يُستبدَل — سيُحقَن `{MARK}` حرفيًّا"
    assert mod._INJECT_TEMPLATE.count("{MARK}") == 1,         "موضعُ الوسم ليس واحدًا في القالب — الاشتقاقُ يفترض موضعًا واحدًا"
    # وحسّاسيّةٌ فعليّة: حرفٌ واحدٌ يغيّر الوسم.
    mutated = mod._INJECT_TEMPLATE.replace("محراب:", "محراب :", 1)
    assert mod._derive_mark(mutated) != mod.VERSION_MARK,         "الاشتقاقُ لا يتأثّر بتغيّر المحتوى — دالّةٌ ميّتة"
    del hashlib

    # **وما يقرؤه `build.sh` فعلًا.** الطبقةُ تستورد الوحدةَ، و`build.sh` كان يقرأ
    # نصَّها بـ`sed` بحثًا عن `CORE_PATCH_VERSION = "…"`. فلمّا صار الوسمُ مشتقًّا
    # اختفى الثابتُ من النصّ وسقط البناءُ بـ«تعذّر الاشتقاق» — والطبقاتُ الأربعُ
    # خضراء. صار `build.sh` **يسأل الوحدةَ** لا يقرأ نصَّها؛ وهذا يشترط بقاءَ ذلك.
    sh = _read(os.path.join(BUILD, "build.sh"))
    assert "sed -n 's/.*CORE_PATCH_VERSION" not in sh, (
        "‏build.sh يقرأ CORE_PATCH_VERSION من نصّ الملفّ — والثابتُ مشتقٌّ لا مكتوب. "
        "اسأل الوحدةَ باستيرادها.")
    assert "m.CORE_PATCH_VERSION" in sh, (
        "‏build.sh لا يشتقّ CORE_PATCH_VERSION من الوحدة — مصدرُ الحقيقة انفصل، "
        "فيحرس البناءُ وسمًا غيرَ الذي يُحقَن.")


# ───────── L0-2ب: قائمة الجولات المُسقَطة (لا تبتلع محتوى الوصول) ─────────
@check("إسقاط جولات المنبع: القائمة مقصورة على التعريفيّة ولا تمسّ SetupAccessibility")
def _walkthroughs_drop_scope():
    """الخطر الحقيقيّ هنا ليس فشلَ المرساة (يمسكه L1) بل **توسُّع القائمة**.

    `SetupAccessibility` هي الجولة الوحيدة التي تشرح أدوات الوصول، ومحراب لا يوفّر بديلًا
    عنها؛ إسقاطها يحذف محتوًى لا يُعوَّض. و`notebooks` وظيفيّة لا تعريفيّة ومحكومة بسياق.
    فنُثبّت القائمة على الثلاثة التعريفيّة بالضبط، ونمنع انجرافها بصمت.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_wd", os.path.join(BUILD, "patch_walkthroughs_drop.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    dropped = set(mod.DROPPED_IDS)
    assert dropped == {"Setup", "SetupWeb", "Beginner"}, (
        f"قائمة الجولات المُسقَطة انجرفت: {sorted(dropped)} — "
        "التوسيع قرارٌ يحتاج تبريرًا (خاصّةً SetupAccessibility: محتوى وصول بلا بديل).")
    # الاستبدال يجب ألّا يُبقي مرجعًا للمصفوفة الأصليّة في حساب الترتيب (وإلّا انزاح الترتيب).
    assert "order: mihrabWalkthroughs.length - index" in mod.REPLACEMENT, (
        "حساب الترتيب لا يستعمل المصفوفة المُرشَّحة — سينزاح ترتيب الجولات الباقية.")
    assert "order: walkthroughs.length" not in mod.REPLACEMENT, (
        "بقي مرجعٌ للمصفوفة غير المُرشَّحة في حساب الترتيب.")
    assert mod.MARK in mod.REPLACEMENT, "الوسم غائب عن الاستبدال — يسقط idempotency."


# ───────────────────── L0-3: اتّساق مانيفست الرُقَع ─────────────────────
@check("مانيفست الرُقَع متّسق (كلّ مرقِّع موجود على القرص)")
def _manifest_consistency():
    for name, mode, _targets in M.PATCHERS:
        assert os.path.isfile(os.path.join(BUILD, name)), f"مرقِّع مفقود: {name}"
        assert mode in ("file", "root"), f"وضع غير معروف لـ{name}: {mode}"
    for name in M.BUILD_PATCHERS:
        assert os.path.isfile(os.path.join(BUILD, name)), f"مرقِّع بناء مفقود: {name}"
    # رُقَعُ المنبع موجودةٌ وملفّاتُها قابلةٌ للاشتقاق:
    for diff in getattr(M, "CORE_DIFFS", []):
        assert os.path.isfile(os.path.join(ROOT, diff.replace("/", os.sep))), f"رُقعةُ منبعٍ مفقودة: {diff}"
        assert M.core_diff_files(ROOT, diff), f"رُقعةٌ بلا ملفّات: {diff}"


# ──────── L0-3ب: تقريرُ المنبع يواكب الرُقَع ────────
UPSTREAM_REPORT = os.path.join(ROOT, "docs", "اقتراحات تعديلات المصدر", "README.md")


def _report_drop_column():
    """عمودُ «الرُقَع التي يُسقطها» من الجدول الموجز وحده — لا كلُّ التقرير ولا كلُّ الجدول.

    قصرُ الفحص على هذا العمود مقصود من الطرفين: ذِكرُ الرقعة عَرَضًا في فقرةٍ لا يعني أنّ
    لها مقترحًا مقابلًا (فيمرّ الفحصُ كذبًا)، و`dir` و`nameShort` في عمود الوصف أسماءُ
    خصائصَ لا رُقَعٍ (فيُخفق كذبًا). العمودُ الثالث وحده هو الربطُ رقعةً↔مقترحًا.
    """
    text = _read(UPSTREAM_REPORT)
    i = text.find("## الجدول الموجز")
    assert i >= 0, "لا «## الجدول الموجز» في تقرير المنبع — تغيّرت بنيتُه فعمِيَ الفحص."
    j = text.find("\n## ", i + 1)
    rows = [ln for ln in text[i:j if j > 0 else len(text)].splitlines()
            if ln.lstrip().startswith("|")]
    assert len(rows) >= 5, f"الجدول الموجز شبهُ فارغ ({len(rows)} سطرًا) — عمِيَ الفحص."
    cells = []
    for ln in rows:
        parts = ln.split("|")
        assert len(parts) >= 6, f"صفٌّ بأعمدةٍ غيرِ متوقَّعة في الجدول الموجز: {ln[:60]}"
        cells.append(parts[3])
    return "\n".join(cells)


@check("تقريرُ المنبع يغطّي كلّ رقعة (رقعةٌ بلا مقترحٍ = دَينٌ خفيّ)")
def _upstream_report_covers_patchers():
    """طلبُ المستخدم: «التقرير يُحدَّث بعد كلّ إضافةِ رقعةٍ في محراب».

    بلا حارسٍ يبقى ذلك وعدًا يعتمد على الذاكرة: تُضاف رقعةٌ، ويُنسى بندُها، فيبدو
    التقريرُ كاملًا وهو ناقص — وهذا أسوأ من غيابه، لأنّه يُطمئن. القائمةُ تُشتقّ من
    **القرص** لا من المانيفست: `patch_cli_macapp` مثلًا ليس في المانيفست (يرقّع
    VSCodium لا vscode) ومع ذلك يستحقّ بندًا (م-١٠).
    """
    assert os.path.isfile(UPSTREAM_REPORT), (
        "تقريرُ اقتراحات المنبع مفقود: docs/اقتراحات تعديلات المصدر/README.md")
    table = _report_drop_column()

    stems = {f[len("patch_"):-3] for f in os.listdir(BUILD)
             if f.startswith("patch_") and f.endswith(".py")}
    stems |= {f[:-3] for f in M.BUILD_PATCHERS if not f.startswith("patch_")}
    missing = sorted(s for s in stems if f"`{s}`" not in table)
    assert not missing, (
        "رُقَعٌ بلا بندٍ في الجدول الموجز — أضِف لكلٍّ مقترحَ المنبع الذي يُسقطها: "
        + " · ".join(missing))


@check("تقريرُ المنبع لا يذكر رقعةً زائلة (بندٌ ميّت يوهم بدَينٍ لم يعد قائمًا)")
def _upstream_report_has_no_stale_rows():
    table = _report_drop_column()
    known = set(os.listdir(BUILD))
    stale = []
    for tok in re.findall(r"`([^`]+)`", table):
        if "." in tok or "/" in tok:   # ملفّاتٌ ومساراتٌ لا أسماءُ رُقَع
            continue
        if f"patch_{tok}.py" not in known and f"{tok}.py" not in known:
            stale.append(tok)
    assert not stale, (
        "أسماءُ رُقَعٍ في الجدول الموجز بلا ملفٍّ في build/ — أُزيلت الرقعةُ ولم يُحدَّث "
        "التقرير، أو أُخطئ الاسم: " + " · ".join(sorted(set(stale))))


def _report_proposal_heads(text):
    """عناوينُ البنود: `[(الرقم، المحرفُ الذي يليه مباشرةً، الموضع)]`.

    **مستخرِجٌ واحدٌ يستهلكه حارسان** عمدًا. كانا يعرّفان الصيغةَ مرّتين — أحدُهما
    `find("## م-N)")` نصًّا والآخرُ تعبيرًا نمطيًّا — فانجرفا: عنوانٌ بشَرطةٍ سقط من
    الأوّل بصمت. تعريفان لعرفٍ واحدٍ ينجرفان حتمًا؛ فليكن التعريفُ هنا وحدَه.

    و**لا `\\s*` بين الرقم والمحرف**: `## م-٢٥ ) عنوان` بمسافةٍ واحدة كان يمرّ من فحص
    الصيغة (المسافةُ تُبتلَع فيُرى القوس) ولا يطابقه `find` — أي عينُ الثقب. و`(.?)`
    لا `(.)` كي يُلتقَط عنوانٌ عارٍ في آخر السطر بدل أن يفلت من الفحصين معًا.
    """
    return [(m.group(1), m.group(2), m.start())
            for m in re.finditer(r"(?m)^##[ \t]+م-([٠-٩]+)(.?)", text)]


def _report_table_nums(text):
    """أرقامُ البنود في الجدول الموجز، بترتيب ورودها (التكرارُ محفوظٌ عمدًا)."""
    i = text.find("## الجدول الموجز")
    j = text.find("\n## ", i + 1)
    rows = [ln for ln in text[i:j if j > 0 else len(text)].splitlines()
            if ln.lstrip().startswith("|")]
    return [m.group(1) for ln in rows for m in [re.search(r"\[م-([٠-٩]+)\]", ln)] if m]


@check("تقريرُ المنبع: لكلّ صفٍّ في الجدول قسمٌ مكتوب (لا فهرسَ يحيل إلى فراغ)")
def _upstream_report_rows_have_sections():
    """الصفُّ وحده ليس بندًا. حذفُ قسم «م-13» كاملًا مع إبقاء صفّه كان يمرّ أخضرَ —
    فيبدو التقريرُ مغطّيًا وهو فهرسٌ يحيل إلى لا شيء. (رصدَته مراجعةٌ هندسيّة بطفرة.)
    """
    text = _read(UPSTREAM_REPORT)
    nums = _report_table_nums(text)
    assert len(nums) >= 10, f"لم أستخرج أرقامَ البنود من الجدول ({len(nums)}) — عمِيَ الفحص."
    pos = {n: k for n, nxt, k in _report_proposal_heads(text) if nxt == ")"}
    thin = []
    for n in nums:
        k = pos.get(n, -1)
        if k < 0:
            thin.append(f"م-{n} (لا قسم)")
            continue
        end = text.find("\n## ", k + 1)
        body = [ln for ln in text[k:end if end > 0 else len(text)].splitlines()[1:]
                if ln.strip() and ln.strip() != "---"]
        # المقياسُ **الفراغُ** لا الطول: حدُّ 400 محرفٍ جرّبناه فأخفق على م-12 وم-14 وهما
        # قسمان تامّان قصيران (عطبُ سطرين لا يحتاج صفحة). ثلاثةُ أسطرٍ ومئةُ محرفٍ تفصل
        # «قسمٌ مكتوب» عن «عنوانٌ يليه فاصل» بلا حكمٍ على الإسهاب.
        if len(body) < 3 or len(" ".join(body)) < 100:
            thin.append(f"م-{n} (قسمٌ فارغ)")
    assert not thin, (
        "بنودٌ في الفهرس بلا متنٍ مكتوب — مقترحٌ بلا نصٍّ لا يُرفَع ولا يُسقِط رقعة: "
        + " · ".join(thin))


@check("تقريرُ المنبع: مراسي الفهرس تحلّ إلى عناوينَ موجودة")
def _upstream_report_anchors_resolve():
    """رابطٌ ميّتٌ في فهرسٍ من ٥٠٠ سطرٍ لا يُكتشَف بالقراءة. المرساةُ تُشتقّ من العنوان
    بقاعدة GitHub: خفضُ الحالة، حذفُ الترقيم، والمسافةُ شَرطة."""
    text = _read(UPSTREAM_REPORT)
    # كلُّ مستويات العناوين لا `## ` وحدَها: أوّلُ عنوانٍ فرعيٍّ برابطٍ **صحيح** كان
    # يُسقِط الفحصَ أحمرَ كاذبًا. ولاحقةُ التكرار (`-1`) كما تفعل GitHub.
    heads, seen = set(), {}
    for ln in text.splitlines():
        m = re.match(r"(#{2,6})\s+(.*)", ln)
        if not m:
            continue
        slug = re.sub(r"[^\w؀-ۿ\s-]", "", m.group(2).strip().lower(), flags=re.UNICODE)
        slug = re.sub(r"\s+", "-", slug.strip())
        n = seen.get(slug, 0)
        seen[slug] = n + 1
        heads.add(slug if n == 0 else f"{slug}-{n}")
    dead = sorted({a for a in re.findall(r"\]\(#([^)]+)\)", text) if a not in heads})
    assert not dead, "مراسٍ في الفهرس لا عنوانَ لها: " + " · ".join(dead)


@check("تقريرُ المنبع: رقمُ البند مفتاحٌ — لا تكرارَ ولا صيغةَ عنوانٍ شاذّة")
def _upstream_report_numbers_are_keys():
    """‏رقمُ البند هو ما نُحيل به إليه من الوثائق ومن رسائل الالتزام ومن الرُقَع. فإن
    حمَله بندان صار المرجعُ ملتبسًا، **والأسوأُ أنّ الحارسَ القائمَ يعمى عنده**:
    `_upstream_report_rows_have_sections` يبحث عن `## م-{n})` فيجد أوّلَ صاحبِ الرقم
    ويمرّ أخضرَ، بينما البندُ الثاني قد يكون بلا قسمٍ أصلًا. وهذا ما وقع فعلًا: بندان
    برقم `م-١٨`، وأحدُهما عنوانُه بشَرطةٍ لا بقوس (`## م-١٨ — …`) فما طابقه فحصُ
    المتن قطُّ — ومع ذلك كان اللوحُ كلُّه أخضر.

    ولذلك يؤكِّد هذا الفحصُ **الصيغةَ** كذلك لا التكرارَ وحدَه: عنوانُ بندٍ لا ينتهي
    رقمُه بقوسٍ هو عنوانٌ خارجَ مدى كلِّ حارسٍ يعتمد `## م-N)`، أي ثقبٌ صامتٌ في
    التغطية لا مسألةَ ذوقٍ في التنسيق.
    """
    text = _read(UPSTREAM_REPORT)
    # شاهدُ تفعيلٍ موجَب قبل أيّ توكيدٍ سالب: لو تغيّرت بنيةُ العناوين فلم نستخرج شيئًا
    # لصار «لا تكرار» صادقًا على الفراغ — وهو أخضرُ كاذبٌ من الصنف الذي نطارده هنا.
    # وشاهدان لأنّ العَرَضَ كان في **الجدول والعناوين معًا**؛ فحصُ العناوين وحدَه كان
    # يترك صفَّين برقمٍ واحدٍ يمرّان خضراوين، وهما نصفُ ما بُلِّغ.
    heads = _report_proposal_heads(text)
    table = _report_table_nums(text)
    assert len(heads) >= 10, (
        f"لم أستخرج عناوينَ البنود ({len(heads)}) — تغيّرت بنيةُ التقرير فعمِيَ الفحص.")
    assert len(table) >= 10, (
        f"لم أستخرج صفوفَ الجدول ({len(table)}) — تغيّرت بنيتُه فعمِيَ نصفُ الفحص.")

    odd = sorted({f"م-{n}" for n, nxt, _ in heads if nxt != ")"})
    assert not odd, (
        "عناوينُ بنودٍ بصيغةٍ لا تُطابِق `## م-N)` — وهي الصيغةُ التي تبحث عنها حرّاسُ "
        "التغطية، فالبندُ يبقى بلا فحصِ متنٍ وهو يبدو مغطّى: " + " · ".join(odd))

    nums = [n for n, _, _ in heads]
    dup = sorted({f"م-{n}" for n in nums if nums.count(n) > 1}
                 | {f"م-{n}" for n in table if table.count(n) > 1})
    assert not dup, (
        "رقمُ بندٍ يحمله عنوانان أو صفّان — المرجعُ يصير ملتبسًا وفحصُ المتن يعمى عن "
        "الثاني: " + " · ".join(dup))

    # والاتّجاهُ المعاكس: قسمٌ لا صفَّ له. `rows_have_sections` يمشي جدولًا ⇐ قسمًا وحده،
    # فبندٌ يُكتَب متنُه ويُنسى صفُّه يبقى غيرَ مذكورٍ في الجدول الموجز — وهو الجدولُ الذي
    # يقرؤه حارسُ تغطية الرُقَع. فيصير البندُ موجودًا ومحجوبًا في آن.
    orphan = sorted({f"م-{n}" for n in nums} - {f"م-{n}" for n in table})
    assert not orphan, (
        "أقسامُ بنودٍ بلا صفٍّ في الجدول الموجز — المتنُ مكتوبٌ والفهرسُ لا يذكره: "
        + " · ".join(orphan))


@check("تقريرُ المنبع: أعدادُ الملفّات في الجدول = ما يمسّه المرقِّع فعلًا")
def _upstream_report_counts_match():
    """‏«٩ ملفّات» و«١٦ ملفًّا» أرقامٌ منسوخةٌ يدويًّا تتقادم بصمتٍ عند تغيّر `FILES` —
    فيُرفَع إلى المنبع مقترحٌ يَعِد بإسقاط تسعةٍ وهي أحدَ عشر. (رصدَته مراجعةٌ هندسيّة.)
    """
    ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    table = _report_drop_column()
    # أرقامٌ عربيّةٌ **ولاتينيّة**: حصرُها في `[٠-٩]` كان يُمرِّر «(11 ملفًّا)» أخضرَ.
    # و«ملف» بلا شدّةٍ ولا تنوين ليطابق «ملفّات» و«ملفًّا» معًا.
    pairs = [(s, n) for cell in table.splitlines()
             for s, n in re.findall(r"`([a-z_]+)`\s*\(([٠-٩\d]+)\s*ملف", cell)]
    assert pairs, "لا عددَ ملفّاتٍ في عمود الرُقَع — تغيّرت صياغةُ الجدول فعمِيَ الفحص."
    unchecked = []
    for stem, num in pairs:
        patcher = f"patch_{stem}.py"
        # لا تخطٍّ صامت: رقمٌ لمرقِّعٍ لا نعرف كيف نتحقّق منه يُعلَن، لا يُبتلَع — وهو
        # عينُ «التخطّي الصامت» الذي أُزيل من L2. (رصدَته مراجعةٌ هندسيّة.)
        if patcher not in M.ROOT_PATCHER_FILES_ATTR:
            unchecked.append(f"{stem} ({num})")
            continue
        actual = len(M.root_target_files(BUILD, patcher))
        claimed = int(num.translate(ARABIC_DIGITS))
        assert claimed == actual, (
            f"التقرير يقول إنّ `{stem}` يمسّ {claimed} ملفًّا، و`FILES` تقول {actual} "
            "— رقمٌ متقادمٌ في مقترحٍ يُرفَع إلى المنبع")
    assert not unchecked, (
        "أعدادُ ملفّاتٍ في الجدول لا مصدرَ يتحقّق منها (المرقِّعُ ليس مرقِّعَ جذرٍ ذا `FILES`) "
        "— اذكرها بلا رقمٍ أو اجعلها مشتقّة: " + " · ".join(unchecked))


# ───────────────────── L0-4: صحّة JSON ─────────────────────
@check("product.json و package.json صالحة JSON")
def _json_valid():
    paths = [os.path.join(ROOT, "product-overrides", "product.json")]
    ext = os.path.join(ROOT, "extensions")
    if os.path.isdir(ext):
        for d in os.listdir(ext):
            pj = os.path.join(ext, d, "package.json")
            if os.path.isfile(pj):
                paths.append(pj)
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            json.load(f)
    # product.json: عربيّ افتراضيّ (انحدار تعريب)
    prod = json.load(open(os.path.join(ROOT, "product-overrides", "product.json"), encoding="utf-8"))
    assert prod.get("defaultLocale") == "ar", "defaultLocale ليس 'ar' (انحدار تعريب)"


# ───────── L0-4ب: هويّةُ التحديث والروابط — «حدِّث» يجب ألّا يجلب المنبع ─────────
@check("هويّة المنتج: المُحدِّث معطَّل ولا رابطَ يشير إلى المنبع")
def _product_identity_not_upstream():
    """
    ⚠️ عطبٌ حقيقيّ أبلغه المستخدم: زرُّ «تحديث التطبيق» كان يُنزِّل **المنبع** لا محرابًا.

    السبب: `updateUrl` يُورَث من VSCodium إلى تغذيةِ إصداراته، و`commit` موجود — فالمُحدِّث
    **يعمل** ويستبدل محرابًا بـVSCodium بلا أن يسأل. ولا تغذيةَ تحديثٍ لمحراب، فالصوابُ
    تعطيلُه صراحةً (‏`updateUrl: null` ⇒ `State.Disabled(MissingConfiguration)`) لا توجيهُه
    إلى عنوانٍ لا وجود له — وعنوانٌ ميّت يعطي «فشل التحديث» بدل «لا تحديث»، وهما ليسا سواء.

    وروابطُ الهويّة (تنزيل/إبلاغ/رخصة/ملاحظات) من الصنف نفسه: رابطٌ يقود المستخدمَ إلى
    منتجٍ آخر عطبُ هويّة، لا تجميل.
    """
    prod = json.load(open(os.path.join(ROOT, "product-overrides", "product.json"), encoding="utf-8"))
    assert "updateUrl" in prod and prod["updateUrl"] is None, \
        "updateUrl ليس null — المُحدِّث سيعمل على تغذية المنبع ويستبدل محرابًا"
    assert prod.get("serverDownloadUrlTemplate", "x") is None, \
        "serverDownloadUrlTemplate ليس null — لا بناءَ خادمٍ لمحراب"
    upstream = ("vscodium", "microsoft", "visualstudio")
    for k, v in prod.items():
        if k.startswith("_comment") or not isinstance(v, str):
            continue
        if k.endswith(("Url", "UrlTemplate")) or k.endswith(("UrlLinux", "UrlMac", "UrlWin")):
            low = v.lower()
            assert not any(u in low for u in upstream), f"{k} يشير إلى المنبع: {v}"


# مفاتيحُ توثيقٍ **يجب** أن تكون مُصرَّحةً في التجاوزات — لا يكفي أن تكون سليمةً إن وُجدت.
# القيمةُ: None ⇒ يجب تصفيرُها، "url" ⇒ يجب أن تكون سلسلةً غيرَ فارغة.
MUST_DECLARE_URLS = {
    "documentationUrl": "url",
    "keyboardShortcutsUrlWin": "url",
    "keyboardShortcutsUrlLinux": "url",
    "keyboardShortcutsUrlMac": "url",
    "tipsAndTricksUrl": None,
    "introductoryVideosUrl": None,
}


@check("هويّة المنتج: مفاتيح التوثيق مُصرَّحة (لا وراثةَ صامتة من المنبع)")
def _product_docs_urls_declared():
    """
    الفحصُ السابق يمنع أن **يشير** مفتاحٌ *موجود* إلى المنبع — لكنّه أعمى عن المفاتيح
    **الموروثة**: مفتاحٌ لا نُصرّح به أصلًا لا يمرّ على الحلقة، فيبقى على قيمة المنبع
    ويقود المستخدمَ إلى code.visualstudio.com. وهذا بالضبط موضعُ العطب الذي أُبلغ عنه:
    «مرجع اختصارات لوحة المفاتيح» كان يفتح ملفَّ PDF إنجليزيًّا وLTR معًا.

    فالحارسُ هنا معكوسُ ذاك: يُلزم **الحضور** لا يفحص القيمة وحدها. وما يُصفَّر يُصفَّر
    عمدًا: `helpActions.ts` يشتقّ `AVAILABLE = !!product.X`، فالتصفيرُ يحذف بندَ القائمة
    كلَّه — أشرفُ من وعدٍ بالعربيّة يُسلَّم إنجليزيّة.
    """
    prod = json.load(open(os.path.join(ROOT, "product-overrides", "product.json"), encoding="utf-8"))
    for key, want in MUST_DECLARE_URLS.items():
        assert key in prod, (
            f"{key} غير مُصرَّح في product-overrides — سيُورَث من المنبع ويقود إلى مايكروسوفت.")
        if want is None:
            assert prod[key] is None, (
                f"{key} يجب أن يكون null حتّى يوجد بديلٌ عربيّ (التصفير يحذف بندَ القائمة).")
        else:
            assert isinstance(prod[key], str) and prod[key].strip(), f"{key} ليس عنوانًا صالحًا."


# ───────────── L0-5: مانيفست حزمة اللغة ↔ الملفّات (فحص Amelia مؤتمَتًا) ─────────────
@check("موقع التوثيق: كلّ رابطٍ في product.json يقابل صفحةً مولَّدة (لا 404)")
def _docs_urls_resolve_to_pages():
    """
    وعدُنا في خطّة التعريب: «كلُّ صفحةٍ تُفتَح من داخل محرابٍ تصل إلى صفحةٍ عربيّة،
    لا إلى 404 ولا إلى إنجليزيّة». والوعدُ بلا حارسٍ ينكسر عند أوّل إعادة تسمية:
    نعيد تسميةَ ملفٍّ في `site/content` فيصير بندُ «مرجع الاختصارات» في القائمة
    رابطًا ميّتًا — ولا شيءَ يصرخ حتّى يشتكي مستخدم.
    """
    prod = json.load(open(os.path.join(ROOT, "product-overrides", "product.json"), encoding="utf-8"))
    content = os.path.join(ROOT, "site", "content")
    if not os.path.isdir(content):
        return  # لا موقع في هذا الفرع — تخطٍّ
    # ‏**الأصلُ يُقرأ ولا يُكتَب هنا.** كان مكتوبًا بيدٍ (`sadlang.github.io/mihrab-ide/`)،
    # ثمّ انتقل الأصلُ إلى `sad-lang.org/mihrab/` وصارت تلك مرآةً — فتوقّف الفحصُ عن
    # مطابقة رابطٍ واحد وبقي **أخضرَ يقيس صفرًا**. مصدرُ الحقيقة `site/data/site.json`،
    # وهو ما يبنى منه `rel=canonical` في كلّ صفحة.
    site_root = json.load(open(os.path.join(ROOT, "site", "data", "site.json"),
                               encoding="utf-8"))["canonical"]
    if not site_root.endswith("/"):
        site_root += "/"
    slugs = {fn[:-3] for fn in os.listdir(content) if fn.endswith(".md")}
    # وصفحاتٌ تُولَّد بلا ملفِّ محتوى (‏`docs/` و`download/`) — تُقرأ من المولِّد نفسِه
    # لا من قائمةٍ ثانيةٍ تنجرف.
    slugs |= set(re.findall(r'write\(os\.path\.join\(OUT,\s*"([^"]+)",\s*"index\.html"',
                            _read(os.path.join(ROOT, "site", "build.py"))))
    seen = 0
    for k, v in prod.items():
        if not isinstance(v, str) or not v.startswith(site_root):
            continue
        seen += 1
        rest = v[len(site_root):].strip("/")
        if not rest:
            continue  # الجذر: الصفحة الأولى، تُولَّد دائمًا
        assert rest in slugs, (
            f"{k} يشير إلى /{rest}/ ولا ملفَّ site/content/{rest}.md — رابطٌ ميّت في القائمة.")
    # شاهدُ تفعيلٍ موجَب: بلا رابطٍ واحدٍ مطابقٍ للأصل، الفحصُ أعلاه أخضرُ على العدم.
    assert seen >= 3, (
        f"‏{seen} روابطَ فقط في product.json تبدأ بأصل الموقع «{site_root}» — "
        "إمّا انتقل الأصلُ ولم يُنقَل معه، وإمّا حُذفت روابطُ القائمة. "
        "وفحصُ «لا 404» بلا روابطَ يفحصها أخضرُ على العدم.")


@check("مجلّد الإعدادات: الرقعة موصولة فعلًا (نسخٌ + استدعاء + وحدتا TS)")
def _config_folder_patch_wired():
    """
    ثغرةٌ صامتة بامتياز: الرقعةُ نفسُها قد تكون سليمةً تمامًا — تجتاز L1 بستّةَ عشرَ
    ملفًّا وidempotent — ثمّ **لا تعمل أبدًا** لأنّ سطرَ استدعائها ناقصٌ من كتلة الحقن.
    حينئذٍ يبقى كلُّ شيءٍ أخضر ويظلّ البناءُ المشحون على `.vscode`، ولا شيءَ يشتكي.

    وشرطٌ ثانٍ: وحدتا TS الجديدتان تُنسَخان إلى شجرة المنبع. لو غابتا لفشل البناءُ
    بصوتٍ عالٍ (استيرادٌ لملفٍّ غير موجود) — وهذا مقبول؛ لكنّ الفحصَ هنا أرخصُ من
    اكتشافه بعد أربعين دقيقةَ بناء.
    """
    patcher = os.path.join(BUILD, "patch_config_folder.py")
    if not os.path.isfile(patcher):
        return  # لا رقعة في هذا الفرع — تخطٍّ
    core = os.path.join(ROOT, "patches", "core")
    for name in ("mihrabConfigFolder.ts", "mihrabConfigFolderResolve.ts"):
        assert os.path.isfile(os.path.join(core, name)), (
            f"patches/core/{name} مفقود — الرقعة تستورده ولا تنسخه.")

    build_sh = _read(os.path.join(BUILD, "build.sh"))
    assert "patch_config_folder.py" in build_sh, (
        "build.sh لا ينسخ patch_config_folder.py إلى شجرة المنبع.")
    assert "$ROOT/patches/core" in build_sh, (
        "build.sh لا ينسخ patches/core (وحدتا TS) — استيرادٌ لملفٍّ غير موجود.")

    bundle = _read(os.path.join(BUILD, "patch_bundle_extensions.py"))
    assert ".mihrab-patch-config-folder.py ." in bundle, (
        "كتلة الحقن لا **تستدعي** رقعة مجلّد الإعدادات — نسخٌ بلا تشغيل: كلّ الفحوص "
        "خضراء والبناء المشحون يبقى على .vscode.")


@check("موقع التوثيق: مصطلحاتُ الترجمة من المسرد (لا انفصال عن الواجهة)")
def _docs_glossary_respected():
    """
    الشرطُ الذي يُفشِل مشروعَ التعريب إن أُغفِل: توثيقٌ يقول «لوحة الأوامر» وواجهةٌ
    تقول «لوحة الأوامر السريعة» **أسوأُ من توثيقٍ إنجليزيّ** — لأنّه يُشكِّك المستخدمَ
    في فهمه هو. فالمسردُ مصدرُ حقيقةٍ واحد، وهذا الفحصُ يمسك البدائلَ الممنوعة.
    """
    gpath = os.path.join(ROOT, "site", "data", "glossary.json")
    content = os.path.join(ROOT, "site", "content")
    if not (os.path.isfile(gpath) and os.path.isdir(content)):
        return
    terms = json.load(open(gpath, encoding="utf-8"))["terms"]
    bad = []
    for fn in sorted(os.listdir(content)):
        if not fn.endswith(".md"):
            continue
        text = open(os.path.join(content, fn), encoding="utf-8").read()
        for t in terms:
            for wrong in t.get("forbidden", []):
                if wrong in text:
                    bad.append(f"{fn}: «{wrong}» ⇐ المعتمد «{t['ar']}»")
    assert not bad, "مصطلحاتٌ خارج المسرد:\n    " + "\n    ".join(bad)


@check("حزمة اللغة: كلّ ترجمة معلَنة موجودة، ولا ملفّ غير معلَن")
def _langpack_manifest_matches_files():
    pkg_dir = os.path.join(ROOT, "extensions", "language-pack-ar")
    if not os.path.isdir(pkg_dir):
        return  # لا حزمة لغة في هذا الفرع — تخطٍّ
    pkg = json.load(open(os.path.join(pkg_dir, "package.json"), encoding="utf-8"))
    locs = pkg.get("contributes", {}).get("localizations", [])
    declared = set()
    for loc in locs:
        for tr in loc.get("translations", []):
            rel = tr["path"].lstrip("./")
            declared.add(os.path.normpath(rel))
            assert os.path.isfile(os.path.join(pkg_dir, rel)), f"ترجمة معلَنة مفقودة: {rel}"
    # لا يتيم: كلّ ملفّ i18n في translations/ معلَن
    tdir = os.path.join(pkg_dir, "translations")
    on_disk = set()
    for root, _dirs, files in os.walk(tdir):
        for fn in files:
            if fn.endswith(".i18n.json"):
                rel = os.path.relpath(os.path.join(root, fn), pkg_dir)
                on_disk.add(os.path.normpath(rel))
    orphan = on_disk - declared
    assert not orphan, f"ملفّات ترجمة غير معلَنة في المانيفست: {sorted(orphan)[:5]}"


# ───────────────────── L0-6: lint طبقة CSS ─────────────────────
def _strip_css_comments(text):
    out, i, n = [], 0, len(text)
    while i < n:
        if text[i:i + 2] == "/*":
            j = text.find("*/", i + 2)
            i = (j + 2) if j != -1 else n
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


@check("لقطة L1 مواكِبة لوسم المنبع المثبَّت (upstream.json)")
def _snapshot_matches_upstream():
    # يُغلق حلقيّة L1-في-CI: لو رُقِّي المنبع دون refresh_snapshot، يصير الفحص على لقطة
    # قديمة بلا معنى. نُلزِم أنّ وسم اللقطة = وسم upstream.json (وإلّا: حدِّث اللقطة).
    tag_file = os.path.join(os.path.dirname(HERE), "apply", "snapshot", "SNAPSHOT_TAG.txt")
    up_file = os.path.join(ROOT, "upstream.json")
    if not os.path.isfile(tag_file) or not os.path.isfile(up_file):
        return  # لا لقطة/منبع في هذا الفرع — تخطٍّ
    up_tag = json.load(open(up_file, encoding="utf-8")).get("vscodium", {}).get("tag", "")
    snap_tag = ""
    for line in open(tag_file, encoding="utf-8"):
        if "tag:" in line:
            snap_tag = line.split("tag:", 1)[1].strip()
            break
    assert snap_tag == up_tag, (
        f"لقطة L1 ({snap_tag}) ≠ وسم المنبع ({up_tag}) — شغّل refresh_snapshot.py بعد ترقية المنبع")


@check("mihrab-rtl.css: أقواس متوازنة وكلّ قاعدة مقصورة على [dir=rtl]")
def _css_lint():
    css_path = os.path.join(ROOT, M.CSS_PATCH)
    text = _read(css_path)
    assert text.count("{") == text.count("}"), "أقواس CSS غير متوازنة"
    body = _strip_css_comments(text)
    # استخرج المحدّدات على المستوى الأعلى (قبل كلّ '{' بعمق 0)
    selectors, depth, buf = [], 0, []
    for ch in body:
        if ch == "{":
            if depth == 0:
                selectors.append("".join(buf).strip())
                buf = []
            depth += 1
        elif ch == "}":
            depth -= 1
            buf = []
        elif depth == 0:
            buf.append(ch)
    selectors = [s for s in selectors if s]
    assert len(selectors) >= 15, f"عدد قواعد CSS منخفض بشكل مريب: {len(selectors)}"
    for sel in selectors:
        # تخطَّ القواعد الشرطيّة (@media/@supports…) — محدّداتها الداخليّة تُفحَص بذاتها.
        if sel.lstrip().startswith("@"):
            continue
        # افحص **كلّ جزء بفاصلة** لا السلسلة كاملةً: «.foo, [dir=rtl] .bar» يحوي [dir=rtl]
        # لكنّ .foo عالميّ متسرّب — الفحص على المجموع يمرّره خطأً (نجاح كاذب).
        for part in sel.split(","):
            part = part.strip()
            if not part:
                continue
            # **لا استثناءَ بعد اليوم** [VA-05]: كان هنا إعفاءٌ لأصناف الهويّة، وقد نُقِلت
            # قواعدُها إلى `patches/mihrab-identity.css`. فصارت هذه الورقةُ **اتّجاهًا خالصًا**
            # وصار الشرطُ مطلقًا. وقاعدةُ هويّةٍ تُكتَب هنا سهوًا تسقط هنا صراحةً.
            assert '[dir="rtl"]' in part, (
                f"جزء محدّد غير مقصور على RTL (تسرّب عالميّ): «{part[:60]}» ضمن «{sel[:40]}…» — "
                f"إن كانت قاعدةَ هويّةٍ لا اتّجاه فمكانُها {M.IDENTITY_CSS} [VA-05]")
    # وحارسٌ معاكس: الأصنافُ نفسُها لا تعود إلى هنا من الباب الآخر.
    for idc in IDENTITY_CLASSES:
        assert idc not in body, (
            f"صنفُ هويّةٍ «{idc}» عاد إلى {M.CSS_PATCH} — مكانُه {M.IDENTITY_CSS} [VA-05]")


@check("محرّرُ الدمج [SC-02]: انعكاسُ اللوحات مقبولٌ عن قياس — فلا قاعدةَ تردُّه بيدٍ")
def _merge_editor_not_flipped_back():
    """يحرس القرارَ التاسع في `docs/rtl/typography-decisions.md` **ساكنًا**.

    القرارُ بالقبول قرارُ **إبقاءٍ**، وأخطرُ ما يصيبه أن يُنقَض ضمنًا بيدٍ حسنةِ النيّة:
    يقرأ أحدُهم القاعدةَ 3 (لوحا الفرق يُثبَّتان LTR) فيقيس عليها محرّرَ الدمج ويضيف
    قاعدةً «تُصلِح» الانعكاس — فيُلغى قرارٌ مبنيٌّ على قياسٍ حيٍّ بسطرٍ لا قياسَ خلفه.

    والقلبُ هنا **مشتقٌّ من `dir=rtl` على الجذر وحدَه**؛ فما يُمنَع هو **ردُّه يدويًّا**:
    ‏`direction` أو `flex-direction: row-reverse` أو `order` على حاويات اللوحات.
    والمنعُ على `mihrab-rtl.css` — الورقةُ الوحيدةُ التي تملك سطحَ العناصر المنبعيّة.
    """
    body = _strip_css_comments(_read(os.path.join(ROOT, M.CSS_PATCH)))
    import re as _re
    # ‏**شاهدُ تفعيلٍ موجَبٌ قبل التأكيد السالب.** حكمُ هذا الفحص كلُّه «لا قاعدةَ تفعل
    # كذا»، والصوابُ **ألّا توجد** كتلةُ `.merge-editor` أصلًا — فالقرارُ قرارُ إبقاء.
    # فلا يصلح وجودُ الكتلة شاهدًا، ويصلح **أنّ المِسطرة ترى الورقة**: بلا كتلةٍ واحدةٍ
    # مُحلَّلةٍ يمرّ الفحصُ أخضرَ سواءٌ أكانت الورقةُ نظيفةً أم كان المحلِّلُ أعمى (انتقلت
    # الورقةُ، أو كُتبت بصياغةٍ متداخلةٍ لا يفهمها التعبيرُ النمطيّ). وهما حالان لا
    # يفرّق بينهما إلّا هذا التوكيد.
    blocks = [(m.group(1), m.group(2)) for m in _re.finditer(r"([^{}]*)\{([^{}]*)\}", body)]
    assert len(blocks) >= 20, (
        f"‏{len(blocks)} كتلةً فقط حُلِّلت من {M.CSS_PATCH} — المِسطرةُ لا ترى الورقة، "
        "وكلُّ تأكيدات هذا الفحص السالبةِ بعدها تمرّ على العمى لا على النظافة [SC-02].")
    touching = [b for b in blocks if "merge-editor" in b[0]]
    # كلُّ كتلةٍ محدِّدُها يمسّ `.merge-editor`: يُفحَص متنُها لا اسمُها.
    for sel, decls in touching:
        for prop, bad in (("direction", None),
                          ("flex-direction", "row-reverse"),
                          ("order", None)):
            hit = _re.search(r"(?<![\w-])" + prop + r"\s*:\s*([^;]+)", decls)
            if not hit:
                continue
            val = hit.group(1).strip()
            if bad is not None and bad not in val:
                continue
            raise AssertionError(
                f"قاعدةٌ تردُّ انعكاسَ محرّر الدمج يدويًّا: «{sel.strip()[:60]}» ⇐ {prop}: {val} — "
                "القرارُ التاسع [SC-02] قبِل الانعكاسَ عن قياسٍ حيّ (كلُّ لوحةٍ تحمل اسمَها ظاهرًا، "
                "فالموضعُ زائدٌ عن الاسم). إن كان معك قياسٌ ينقضه فانقض القرارَ في الوثيقة أوّلًا.")


@check("mihrab-identity.css [VA-05]: هويّةٌ خالصةٌ — أصنافُنا وحدَها وبلا خاصّيّةٍ اتّجاهيّة")
def _identity_css_lint():
    """يحرس **الحدَّين** اللذين يجعلان فصلَ الورقتين صادقًا لا محاسبيًّا.

    الفصلُ بلا حارسٍ يصير بابًا خلفيًّا: قاعدةُ اتّجاهٍ تُكتَب هنا فتنجو من قصر `[dir="rtl"]`
    المفروضِ على الورقة الأخرى — أي أنّ التنظيمَ نفسَه يصير ثغرة. فالشرطان:

      ‏(١) **كلُّ محدّدٍ يستهدف صنفًا نملكه.** فلا قاعدةَ عالميّةٌ تمسّ عنصرًا منبعيًّا. وهذا
          هو ما يُبرّر غيابَ `[dir="rtl"]` أصلًا: لا سطحَ للتسرّب.
      ‏(٢) **لا خاصّيّةَ اتّجاهيّةً واحدة.** `direction`/`text-align`/`float`/`clear`، والحوافُّ
          والحشواتُ والإزاحاتُ **الفيزيائيّةُ الجانبيّة** (`left`/`right`). أمّا `margin: 0 auto`
          فمتماثلٌ حول المحور ⇒ لا اتّجاه فيه، ويُقبَل.
    """
    path = os.path.join(ROOT, M.IDENTITY_CSS)
    text = _read(path)
    assert text.count("{") == text.count("}"), "أقواس CSS غير متوازنة في ورقة الهويّة"
    body = _strip_css_comments(text)
    selectors, depth, buf = [], 0, []
    decls = []
    for ch in body:
        if ch == "{":
            if depth == 0:
                selectors.append("".join(buf).strip())
                buf = []
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                decls.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    selectors = [s for s in selectors if s]
    assert selectors, f"{M.IDENTITY_CSS} بلا قواعد — الفصلُ بلا محتوًى فصلٌ صوريّ"
    for sel in selectors:
        for part in sel.split(","):
            part = part.strip()
            if not part:
                continue
            assert any(idc in part for idc in IDENTITY_CLASSES), (
                f"محدّدٌ في {M.IDENTITY_CSS} لا يستهدف صنفَ هويّةٍ مملوكًا: «{part[:60]}» — "
                f"أصنافُ الهويّة المعلَنة: {', '.join(IDENTITY_CLASSES)}")
            assert "[dir=" not in part, (
                f"محدّدٌ مقصورٌ على اتّجاهٍ في ورقة الهويّة: «{part[:60]}» — مكانُه {M.CSS_PATCH}")
    # الخاصّيّاتُ الاتّجاهيّة المحظورة. `margin`/`padding` تُفحَص بالاختصار الجانبيّ وحدَه:
    # `margin: 0 auto` و`margin-bottom` غيرُ اتّجاهيّتَين، و`margin-left` اتّجاهيّة.
    # ‏`transform:` في القائمة **عن قصدٍ لا احتياطًا**: `scaleX(-1)` هو أداةُ القلب الأولى
    # في هذا المستودع (القاعدتان ٨ و٢٢ في ورقة الاتّجاه) — فقاعدةُ هويّةٍ تقلب رمزًا به
    # كانت تمرّ من الباب الخلفيّ نفسِه الذي بُني هذا الحارسُ لسدّه.
    BANNED = ("direction:", "text-align:", "float:", "clear:", "unicode-bidi:",
              "writing-mode:", "text-indent:", "flex-direction:", "order:", "transform:",
              "margin-left:", "margin-right:", "padding-left:", "padding-right:",
              "border-left:", "border-right:", "left:", "right:", "inset:", "inset-inline",
              "margin-inline", "padding-inline")
    for d in decls:
        flat = "".join(d.split()).lower()
        for prop in BANNED:
            assert prop not in flat, (
                f"خاصّيّةٌ اتّجاهيّةٌ «{prop.rstrip(':')}» في {M.IDENTITY_CSS} — "
                f"ورقةُ الهويّة لا تحمل اتّجاهًا؛ مكانُها {M.CSS_PATCH} [VA-05]")


@check("ورقة الهويّة [VA-05]: محقونةٌ في مسار البناء كلِّه — لا ملفًّا يتيمًا")
def _identity_css_wired():
    """ملفٌّ مُنشأٌ ولا يُنسَخ ولا يُستورَد **أسوأُ من عدمه**: يُقرأ في المستودع كأنّه يعمل.

    فالفصلُ لا يكتمل بإنشاء ملفّ، بل بأن يبلغ الحزمةَ. والمواضعُ الأربعةُ هي المسارُ كلُّه:
    التهيئة (‏`build.sh`) ← الحقن (‏`patch_bundle_extensions.py`) ← الاستيراد
    (‏`patch_workbench_rtl.py`) ← ومزامنةُ التطوير (‏`dev_sync.py`).
    """
    base = os.path.basename(M.IDENTITY_CSS)
    # المِجَسُّ **جذرُ الاسم** لا المسارُ الكامل: التهيئةُ والحقنُ يمرّان على الورقتين
    # بحلقةٍ (`for _sheet in mihrab-rtl mihrab-identity`) فلا يَرِد المسارُ حرفيًّا —
    # ومِجَسٌّ على نصٍّ حرفيٍّ كان سيُفشِل صياغةً **أصحَّ** من التي كتبناه لأجلها.
    stem = base[:-len(".css")] if base.endswith(".css") else base
    wiring = [
        ("build/build.sh", stem, "تهيئةُ الورقة في مجلّد المنبع"),
        ("build/patch_bundle_extensions.py", stem, "نسخُها إلى media/ في كتلة الحقن"),
        ("build/patch_workbench_rtl.py", "media/" + base, "استيرادُها في workbench.ts"),
    ]
    for rel, needle, what in wiring:
        text = _read(os.path.join(ROOT, rel))
        assert needle in text, f"{what}: لا ذكرَ لـ«{needle}» في {rel} — ورقةُ الهويّة يتيمة [VA-05]"
    # dev_sync يشتقّ الاسمَ من المانيفست لا يكتبه — فالفحصُ على المرجع لا على النصّ.
    dev = _read(os.path.join(ROOT, "build/dev_sync.py"))
    assert "IDENTITY_CSS" in dev, "dev_sync.py لا يزامن ورقةَ الهويّة — بيئةُ التطوير تفقد الشعار"
    # **وترتيبُ الاستيراد جزءٌ من العقد لا تفصيل**: ورقةُ الهويّة تأتي ثانيةً كي تفوز عند
    # تساوي الخصوصيّة. وعكسُ السطرين تغييرٌ صامتٌ لا يُسقِط بناءً ولا مِجَسًّا.
    wb = _read(os.path.join(ROOT, "build/patch_workbench_rtl.py"))
    i_rtl = wb.find("media/" + os.path.basename(M.CSS_PATCH))
    i_id = wb.find("media/" + base)
    assert 0 <= i_rtl < i_id, (
        "ترتيبُ استيراد الورقتين معكوسٌ في patch_workbench_rtl.py — الهويّةُ يجب أن تأتي "
        "بعد الاتّجاه كي تفوز عند تساوي الخصوصيّة [VA-05]")
    # **والوسمُ لا يكفي وحدَه للـidempotency بعد نموّ الرُقعة**: شجرةٌ رُقِّعت قبل VA-05
    # تحمل الوسمَ وتنقصها ورقةُ الهويّة، فالتخطّي بالوسم كان يترك الشعارَ غائبًا بلا خطأ.
    assert "IDENTITY_IMPORT in text" in wb, (
        "patch_workbench_rtl.py يتخطّى بالوسم وحدَه — شجرةٌ مُرقَّعةٌ بنسخةٍ أقدم لن تُكمَل، "
        "فتخرج ترويسةُ الترحيب بلا شعارٍ ولا رسالةَ خطأ [VA-05]")
    # **والمِجَسُّ الخامس**: مِجَسّات L2 هي دليلُ الوصول الوحيد بعد التحزيم — سقوطُها من
    # `check_injected.py` يترك الاستيرادَ بلا شاهد.
    inj = _read(os.path.join(ROOT, "tests/bundle/check_injected.py"))
    for cls in IDENTITY_CLASSES:
        assert cls in inj, (
            f"مِجَسُّ «{cls}» سقط من توكيدات L2 — لا دليلَ على وصول ورقة الهويّة [VA-05]")


@check("إبراز يونيكود [AR-04]: إعفاء ص من nonBasicASCII — مقصورًا على اللغة لا عالميًّا")
def _unicode_highlight():
    """‏[AR-04] يحرس إعفاءً **مقيسًا** من `editor.unicodeHighlight` — وحدَّه في آن.

    **العطب:** `editor.unicodeHighlight.nonBasicASCII` افتراضُه `inUntrustedWorkspace`، وهو
    يُبرِز **كلّ** محرف خارج ‎U+0020–U+007E‎. وقياسنا على مِلفّ ص واقعيّ: **62% من محارفه
    غير-ASCII**. أي أنّ فتح مجلّد ص غير موثوق — وهي الحالة الافتراضيّة لأيّ مشروع مُنزَّل —
    يُغرِق الملفّ كلَّه في إبرازات تحذير. وهذا مسارٌ قاطع لا احتماليّ: في
    `unicodeTextModelHighlighter.ts` يعود `shouldHighlightNonBasicASCII` بـNonBasicASCII
    **قبل** استدلال سياق الكلمة، فلا شيء يُنقِذ منه.

    **ولماذا اقتصر الإصلاح على هذا المفتاح وحده — قياسٌ لا حَدْس:**
      • ‏`ambiguousCharacters` **تبقى مفعَّلة**، والعربيّةُ المُلتبِسة تُعفى **بالاسم** عبر
        `allowedCharacters` داخل `[sad]` وحدها. وهذا **تصحيحُ قياسٍ سابقٍ كان يكذب**:
        قلنا «كلمة واحدة من 1238» اعتمادًا على استدلال سياق الكلمة (يُعفي الكلمة التي لا
        ASCII فيها وفيها محرفٌ غير-مُلتبِس). والشرطُ في المنبع هو **`!hasBasicASCIICharacters`**
        — أي **محرفُ ASCII واحدٌ يُبطِل الإعفاء كلَّه** — ومعرّفاتُ ص تُكتب `نصاب_الفضة`،
        والشرطةُ السفليّة ASCII. فأعدنا القياس بمحاكاة قاعدة المنبع حرفيًّا، **والمجموعةُ
        مسمّاةٌ لأنّ النسبة بلا مجموعةٍ ادّعاء**:
            نواة نهلة (‏c:\\s_lang\\nahla، 174 ملفّ ص):  77690 من 607018 كلمة = **12.8%**
            أمثلة مستودع اللغة (6 ملفّات):              59 من 843 = 7.0%
            هذا المستودع (ملفّ تجهيزٍ واحد):             0 من 107 = 0.0%
        (وقلنا أوّلًا «59 من 950 على مصادر ص في المستودع» — والمجموعةُ كانت أمثلةَ
        مستودع اللغة لا هذا المستودع. صحّحته مراجعةٌ هندسيّة، والرقمُ الحاكم هو نهلة:
        أكبرُ شيفرةِ ص حقيقيّة عندنا.) وكلُّ المُعلَّم معرّفاتُ snake_case عربيّة.
        (ورصده المستخدم على نسخةٍ حيّة: «مستطيلٌ أصفر حول كلّ حرف ا».)

        فالإعفاء لـ17 نقطة كودٍ من كتل العربيّة (‏0600–06FF · 0750–077F · 08A0–08FF —
        اليومَ كلُّها في الأولى) وردت في `_common`، وللقوسين
        المزخرفين ﴾﴿ **بالاسم** (يُكتبان عمدًا لاقتباس آية). ونُبقي بقيّةَ **صور العرض**
        (‏FB50+/FE70+) مُعلَّمةً عمدًا: لا تُنتجها لوحةُ مفاتيحَ عربيّة، فوجودُها إشارةٌ
        تستحقّ التنبيه لا ضجيجًا. والحمايةُ من trojan-source باقيةٌ لكلّ ما عداها —
        وأهمُّها للعربيّة `invisibleCharacters` (‏RLM/LRO وأخواتُها تقلب ترتيبَ السطر
        بصريًّا) ولم تُمسّ.

        **وفخٌّ ظنَنّاه قائمًا فلم يكن — مُثبَتُ النفي بالقراءة، ومكتوبٌ هنا كي لا يُبعَث:**
        الإصلاحُ السريع «استثنِ هذا المحرف» (`excludeCharFromBeingHighlighted`) يكتب فعلًا
        في إعدادات المستخدم **عالميًّا** بلا `overrideIdentifier` — وهذا صحيح. واستنتجنا
        منه أنّ نقرةً واحدةً في md تُبطِل إعفاءَنا المحصورَ في `[sad]` **ذرّيًّا**، فبنينا
        عليه توسيعًا للنطاقات وبندًا رابعًا في م-13. **والاستنتاجُ خطأ:** الدمجُ بين
        المصادر وبين تجاوزات اللغة **عميقٌ لا ذرّيّ** — `ConfigurationModel.merge` (‏:156)
        و`createOverrideConfigurationModel` (‏:203) كلاهما يمرّ بـ`mergeContents` (‏:219)
        وهي تعاود النزول في كلّ قيمةٍ كائنًا. فقيمةُ المستخدم `{«а»: true}` **تتّحد**
        بمحارفنا التسعةَ عشرَ ولا تحلّ محلَّها. والمفاتيحُ الذرّيّةُ حقًّا هي البوليانيّة،
        ولا مسارَ في الواجهة يكتب `nonBasicASCII: true` (أوامرُ التعطيل تكتب `false` فقط).
        فلا فخَّ هنا. (رصدَته مراجعةٌ هندسيّة، وتحقّقناه بقراءة الملفّ لا بالثقة.)

        **وأسبقيّةُ النطاق اللغويّ أقوى ممّا ظنَنّا مرّتين:** `getConsolidatedConfigurationModel`
        (‏:990) يدمج المصادرَ كلَّها **ثمّ** يستدعي `.override(id)`، فمحتوى النطاق اللغويّ
        يُطبَّق فوق المتن أيًّا كان مصدرُه. أي أنّ افتراضَنا `[sad]` يغلب **قيمةَ المستخدم
        العامّة** لا العكس. والحالةُ الوحيدةُ التي تغلبنا: قيمةٌ بنطاقِ لغةٍ في إعدادات
        المستخدم/المشروع — وعليها وحدَها يُنذر حارسُ `unicode-guard.js`.

        **ما بقي من التوسيع، بحيثيّةٍ أخرى:** `[markdown]` و`[plaintext]` و`[git-commit]`
        و`[git-rebase]` تأخذ `nonBasicASCII: false` **وحدَه** — لا إعفاءً بالاسم. السببُ
        ليس الفخّ بل أنّ المفتاح افتراضُه `inUntrustedWorkspace`، وأيُّ مشروعٍ مُنزَّلٍ غيرُ
        موثوقٍ ابتداءً، فيغرق README عربيٌّ كلُّه بالمستطيلات. والنثرُ لا يُنفَّذ. ورسالةُ
        الالتزام تُحرَّر داخل المحرّر وتخلط عربيًّا بلاتينيٍّ ملتصق — وهو النمطُ الذي
        يتجاوز إعفاءَ سياق الكلمة. أمّا `[json]`/`[jsonc]` فتُركتا عمدًا: `tasks.json`
        و`devcontainer.json` هما ما يقرؤه المراجعُ **قبل** منحِ الثقة، وإسكاتُهما يُسقِط
        الإشارةَ في موضع القرار.

        **والضجيجُ خارجَ هذه النطاقات مقيسٌ لا مُقدَّر:** ‏md ‏0.05% · ts ‏0.25% ·
        json ‏0.07% من الكلمات — النثرُ العربيُّ بلا snake_case، ونمطُ «الـHTML» وحده
        يُبطِل إعفاءَ سياق الكلمة بحرفٍ لاتينيٍّ ملتصق.

        **وإبقاءُ `invisibleCharacters` مفعَّلةً مقيسٌ أيضًا** (كان ادّعاءً يُكرَّر): في
        ‏174 ملفّ ص من نواة نهلة (‏4.88 مليون محرف) وُجدت ‏312 علامةً خفيّةً فقط —
        ‏192 LRM و120 RLM، أي ‏0.006% من المحارف ونحوُ علامتين في الملفّ. فالكلفةُ على
        المستخدم لا تُذكَر، والفائدةُ حقيقيّة: هذه العلاماتُ تقلب ترتيبَ السطر بصريًّا.
      • ‏`allowedLocales: {ar: true}` **عديم الأثر** لا حلّ: بيانات المحليّات في
        `strings.ts` لا تحوي `ar` أصلًا (‏cs/de/es/fr/it/ja/ko/pl/pt-BR/ru/tr/zh…)،
        والمُرشِّح `Object.hasOwn(data, l)` يُسقِط أيّ محليّة غير موجودة. أثبتناه بالقراءة.

    **ولماذا مقصورًا على `[sad]`:** خيارات المحرّر `LANGUAGE_OVERRIDABLE`
    (‏editorConfigurationSchema.ts:19)، فالإعفاء ينحصر في اللغة التي **غير-ASCII هي متنُها**.
    إسقاطه عالميًّا يُطفئ حمايةً حقيقيّة في كلّ لغة أخرى — ولذا يمنعه هذا الفحص صراحةً.
    """
    shell = os.path.join(ROOT, "extensions", "mihrab-shell", "package.json")
    sad_pkg = os.path.join(ROOT, "extensions", "sad-lang", "package.json")
    if not (os.path.isfile(shell) and os.path.isfile(sad_pkg)):
        return
    # مُعرّف اللغة من مصدره الوحيد (مساهمة sad-lang) لا من سلسلة مُختلَقة — كما في _lang_identity.
    lang_id = json.load(open(sad_pkg, encoding="utf-8"))["contributes"]["languages"][0]["id"]
    defaults = json.load(open(shell, encoding="utf-8")).get("contributes", {}).get("configurationDefaults", {})
    KEY = "editor.unicodeHighlight.nonBasicASCII"
    # نطاقان لا واحد، وبصلاحيّتين مختلفتين:
    #   • `[sad]`: الإطفاءُ الشامل **والإعفاءُ بالاسم** — متنُ الملفّ عربيّ، ومعرّفاتُه
    #     snake_case عربيّةٌ تُبرَز بالملتبِس (قياسُ نهلة: 12.8% من الكلمات).
    #   • `[markdown]`/`[plaintext]`: الإطفاءُ الشامل **وحدَه**. النثرُ العربيّ لا يُبرَز
    #     بالملتبِس أصلًا (قاعدةُ سياق الكلمة تُعفيه)، لكنّ `nonBasicASCII` يُبرِز كلَّ
    #     غير-ASCII في مساحةِ عملٍ **غير موثوقة** — وهي حالُ أيّ مشروعٍ مُنزَّل — فيغرق
    #     ملفُّ README عربيٌّ كلُّه. والإعفاءُ بالاسم هناك ممنوع، انظر أدناه.
    # ‏`git-commit`/`git-rebase`: رسالةُ الالتزام تُحرَّر **داخل** المحرّر، ورسائلُ هذا
    # المشروع نفسِه عربيّةٌ مخلوطةٌ بلاتينيّ ملتصق (`macOS`، أسماءُ ملفّات) — وهو النمطُ
    # الذي يتجاوز إعفاءَ سياق الكلمة. واللغتان مشحونتان في `git-base`. (اقتراحُ مراجعةِ
    # تجربةِ المستخدم، وهو الوحيدُ من قائمتها الذي رجّحته بالاحتمال لا بالإمكان.)
    PROSE_SCOPES = ("markdown", "plaintext", "git-commit", "git-rebase")
    SCOPES = (lang_id,) + PROSE_SCOPES
    scoped_all = {sc: defaults.get(f"[{sc}]", {}) for sc in SCOPES}
    scoped = scoped_all[lang_id]
    for sc, s in scoped_all.items():
        assert s.get(KEY) is False, (
            f"لا إعفاء `{KEY}: false` داخل `[{sc}]` في mihrab-shell — فتح مجلّدٍ "
            f"غير موثوق يُبرِز 62% من محارف الملفّ كتحذير يونيكود [AR-04]")
    assert KEY not in defaults, (
        f"‏`{KEY}` مضبوط **عالميًّا** — هذا يُطفئ حماية التماثل البصريّ في كلّ لغة. "
        f"احصره في `[{lang_id}]` وأخواتها [AR-04]")
    # مجموعةٌ **مغلقة**: نطاقٌ لغويٌّ جديدٌ يحمل مفاتيحَ إبراز يونيكود يجب أن يُخفق حتّى
    # يُقرَّر عمدًا. بلا هذا كان يمرّ `"[yaml]": {nonBasicASCII: false}` أخضرَ — أي توسّعٌ
    # صامتٌ في إسقاط الحماية بلا قرارٍ ولا حيثيّة. (رصدَته مراجعةٌ هندسيّة بطفرةٍ مرّت.)
    PREFIX = "editor.unicodeHighlight."
    stray = sorted(k for k, v in defaults.items()
                   if k.startswith("[") and k not in {f"[{sc}]" for sc in SCOPES}
                   and isinstance(v, dict) and any(x.startswith(PREFIX) for x in v))
    assert not stray, (
        "نطاقاتٌ لغويّةٌ تضبط إبرازَ يونيكود خارج المجموعة المقرَّرة — كلُّ نطاقٍ إسقاطُ "
        "حمايةٍ يحتاج حيثيّة: " + " ".join(stray) + " [AR-04]")
    # حارسُ التعافي (`unicode-guard.js`) يفحص النطاقاتِ بالاسم كي يكشف ما يُظلِّلها. نطاقٌ
    # يُضاف هنا ولا يُضاف هناك يبقى بلا تشخيصٍ ولا إصلاح: يرى المستخدمُ الإطاراتِ ويقول له
    # الأمرُ «لم أجد شيئًا». فالقائمتان مصدرٌ واحدٌ يُفحَص تطابقُه.
    guard_js = os.path.join(ROOT, "extensions", "mihrab-welcome", "unicode-guard.js")
    if os.path.isfile(guard_js):
        m = re.search(r"const LANGS = \[([^\]]*)\]", _read(guard_js))
        assert m, "لا `LANGS` في unicode-guard.js — انجرف شكلُها فعمِيَ فحصُ التطابق [AR-04]"
        guard_langs = set(re.findall(r'"([^"]+)"', m.group(1)))
        assert guard_langs == set(SCOPES), (
            "نطاقاتُ القشرة ≠ نطاقاتُ حارس التعافي — نطاقٌ بلا تشخيص: "
            f"{sorted(set(SCOPES) ^ guard_langs)} [AR-04]")

    # الحماية التي نُبقيها عمدًا: لا نُطفئ الملتبِس ولا الخفيّ، لا عالميًّا ولا في نطاق.
    for keep in ("editor.unicodeHighlight.ambiguousCharacters",
                 "editor.unicodeHighlight.invisibleCharacters"):
        assert keep not in defaults, (
            f"‏`{keep}` مُعطَّل — الإعفاء بالاسم (allowedCharacters) يكفي لإسكات الضجيج، "
            f"والإطفاء يُسقِط حماية التماثل البصريّ/المحارف الخفيّة كلَّها [AR-04]")
        for sc, s in scoped_all.items():
            assert keep not in s, (
                f"‏`{keep}` مُعطَّل في `[{sc}]` — الإعفاء بالاسم يكفي، والإطفاء يُسقِط "
                f"حماية التماثل البصريّ/المحارف الخفيّة كلَّها [AR-04]")

    # ── الإعفاء بالاسم: مشتقٌّ من جدول المنبع لا مكتوبٌ بالحدس ──
    # لو أضاف المنبع نقطةَ كودٍ عربيّةً جديدةً إلى `_common` لبقيت قائمتُنا ناقصةً **بصمت**،
    # وعاد المستطيلُ الأصفر إلى حرفٍ بعينه دون أن يُخفق شيء. فنشتقّ المتوقَّع من مصدره.
    ALLOWED_KEY = "editor.unicodeHighlight.allowedCharacters"
    assert ALLOWED_KEY not in defaults, (
        f"‏`{ALLOWED_KEY}` مضبوط **عالميًّا** — يُسقِط الحماية في كلّ لغة. "
        f"احصره في `[{lang_id}]` [AR-04]")
    # الغيابُ إخفاقٌ لا تخطٍّ: لولا هذا التوكيد لمرّ حذفُ الإعفاء كلِّه أخضرَ — وهي نفسُ
    # الفجوة الصامتة التي وُجد هذا الفحص ليسدّها.
    allowed = scoped.get(ALLOWED_KEY)
    assert allowed, (
        f"لا `{ALLOWED_KEY}` داخل `[{lang_id}]` — يعود المستطيلُ الأصفر حول كلّ ألفٍ "
        f"وهاءٍ في معرّفات ص [AR-04]")
    # **والإعفاءُ بالاسم محصورٌ في ص وحدها.** `shouldHighlightNonBasicASCII` يفحص
    # `allowedCodePoints` **أوّلًا ويعود None** (unicodeTextModelHighlighter.ts:190) — أي
    # قبل الملتبِس والخفيّ معًا. فكلُّ محرفٍ نُعفيه يفقد حمايتَه كاملةً في ذلك النطاق،
    # وقائمتُنا فيها ما يشبه l و o و 0 و 1 و 5 و 7 و * و , و / و . — أدواتُ الانتحال في
    # أمرِ مهمّةٍ أو مسارِ صورة. في ص المقايضةُ مقصودةٌ ومقيسة؛ خارجَها لا مقابلَ لها.
    # (رصدَته مراجعةٌ هندسيّة بقراءة ترتيب الفحص في المنبع.)
    named = sorted(sc for sc in PROSE_SCOPES if ALLOWED_KEY in scoped_all[sc])
    assert not named, (
        f"‏`{ALLOWED_KEY}` في نطاقٍ غير `[{lang_id}]` — الإعفاءُ بالاسم يتخطّى الملتبِسَ "
        "والخفيَّ معًا، فيُسقِط الحمايةَ حيث لا ضجيجَ يبرّرها: "
        + " ".join(f"[{sc}]" for sc in named) + " [AR-04]")
    # القيمةُ تُفحَص لا المفتاح وحده: `validateBooleanMap` في المنبع تقبل `=== true` فقط
    # وتُسقِط ما عداه، فـ`"ا": false` إعفاءٌ **مُبطَل** بمفتاحٍ حاضر — أي مستطيلٌ أصفرُ عائد
    # وحارسٌ أخضر. رصدَته مراجعةٌ هندسيّة بطفرةٍ مرّت.
    falsy = sorted(c for c, v in allowed.items() if v is not True)
    assert not falsy, (
        "مفاتيحُ إعفاءٍ قيمتُها ليست `true` — يُسقِطها المنبع فيعود الإبراز: "
        + " ".join(f"U+{ord(c):04X} «{c}»" for c in falsy) + " [AR-04]")

    # الأقواسُ المزخرفة ﴾﴿ استثناءٌ **بالاسم**: هي في كتلة صور العرض (‏FD3E/FD3F) التي
    # نُبقيها مُعلَّمةً كقاعدة، لكنّ هذين يكتبهما عربيٌّ **عمدًا** لاقتباس آية، بخلاف صور
    # عرض الحروف التي لا تنتجها لوحةُ مفاتيح. فالقاعدةُ بالكتلة والاستثناءُ بالاسم.
    NAMED_EXTRA = {"﴾", "﴿"}

    # مصدرُ الاشتقاق: المنبعُ المثبَّت إن وُجد، وإلّا **لقطةُ L1** المُلتزَمة في المستودع.
    # الارتدادُ ليس ترفًا: `.upstream/` مُتجاهَلٌ في git، فبلا اللقطة يكون لُبُّ هذا الفحص
    # معطَّلًا في CI — يمرّ إعفاءٌ فارغٌ أو سيريليٌّ أخضرَ. (رصدَته مراجعةٌ هندسيّة بطفرة.)
    REL = os.path.join("src", "vs", "base", "common", "strings.ts")
    strings_ts = os.path.join(ROOT, ".upstream", "vscode", REL)
    if not os.path.isfile(strings_ts):
        strings_ts = os.path.join(os.path.dirname(HERE), "apply", "snapshot", REL)
    assert os.path.isfile(strings_ts), (
        "لا `strings.ts` — لا في المنبع المثبَّت ولا في لقطة L1. شغّل "
        "`python tests/apply/refresh_snapshot.py` والتزِم اللقطة [AR-04]")
    # المرساة على **تعريف الحقل** لا على `_common` وحدها: كتلةُ المحارف الخفيّة في الملفّ
    # نفسِه تبدأ ببادئةٍ مشابهة، فمرساةٌ فضفاضة كانت ستطابق الجدولَ الخطأ بلا إخفاق.
    src = open(strings_ts, encoding="utf-8").read()
    m = re.search(r"ambiguousCharacterData\s*=\s*new Lazy[\s\S]*?"
                  r"JSON\.parse\(\s*'(\{.*?\})'\s*\)", src)
    assert m, "تعذّر إيجاد جدول المحارف الملتبِسة في المنبع — تغيّر شكلُه؟ [AR-04]"
    common = json.loads(m.group(1).replace('\\"', '"'))["_common"]
    ambiguous_cps = {common[i] for i in range(0, len(common), 2)}
    # تحقّقٌ من أنّنا أمسكنا الجدولَ الصحيح لا جدولًا آخر بالبنية نفسها.
    assert 0x0627 in ambiguous_cps, "الجدول المُلتقَط لا يحوي الألف — مرساةٌ أمسكت غيرَه [AR-04]"

    # نطاقُ الحروف العربيّة **الثلاثة** لا الكتلة الأساسيّة وحدها: الملحق (0750–077F)
    # والموسَّع-A (08A0–08FF) حروفُ كتابةٍ عربيّةٍ حقيقيّة تُنتجها لوحاتُ مفاتيحَ إقليميّة،
    # فحصرُ الاشتقاق في 0600–06FF كان يَعِد بما لا يفي: إضافةُ المنبع لحرفٍ منهما تمرّ
    # صامتةً. (رصدَته مراجعةٌ هندسيّة بحقن U+0751 في الجدول فمرّ أخضرَ.)
    ARABIC_BLOCKS = ((0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF))
    expected = {chr(cp) for cp in ambiguous_cps
                if any(lo <= cp <= hi for lo, hi in ARABIC_BLOCKS)} | NAMED_EXTRA
    missing = expected - set(allowed)
    assert not missing, (
        "محارفُ عربيّةٌ ملتبِسةٌ في جدول المنبع وليست في الإعفاء ⇒ مستطيلٌ أصفر حولها: "
        + " ".join(f"U+{ord(c):04X} «{c}»" for c in sorted(missing)) + " [AR-04]")
    # الزيادةُ تُقاس على **المتوقَّع** لا على الجدول كلِّه: مقارنةٌ بالجدول كانت ستُمرِّر
    # إعفاءَ «а» السيريليّة أو صورةِ عرضٍ للألف — أي إسقاطَ حمايةٍ في اتّجاهٍ آخر.
    extra = set(allowed) - expected
    assert not extra, (
        "إعفاءٌ لمحارفَ خارج نطاق القرار (إسقاطُ حمايةٍ بلا سبب): "
        + " ".join(f"U+{ord(c):04X} «{c}»" for c in sorted(extra)) + " [AR-04]")


@check("خطّ ص العربيّ المحزوم [AR-02]: config ↔ حقن data:URI ↔ لا url() كاسر للبناء")
def _arabic_font():
    # قيم متوقَّعة (بيانات فحص تطابق مصدر الإعداد؛ استثناء literal مقبول للاختبارات).
    BUNDLED_FONT_FAMILY = "Kawkab Mono"  # الخطّ المحزوم (OFL)، أوّل المكدّس
    STAGED_FONT = ".mihrab-kawkab-mono.woff2"  # المُجهَّز في .upstream/ لاشتقاق base64
    shell = os.path.join(ROOT, "extensions", "mihrab-shell", "package.json")
    if not os.path.isfile(shell):
        return  # لا قشرة في هذا الفرع — تخطٍّ
    defaults = json.load(open(shell, encoding="utf-8")).get("contributes", {}).get("configurationDefaults", {})
    ff = defaults.get("editor.fontFamily")
    assert ff, "لا editor.fontFamily افتراضيّ في mihrab-shell [AR-02]"
    # الخطّ المحزوم أوّل المكدّس (وإلّا لا يُفضَّل عند توفّره)، والمكدّس ينتهي بـmonospace،
    # وفيه احتياطيّ عربيّ لأنظمةٍ بلا الخطّ المحزوم (وإلّا عربيّة رديئة في السقوط الرشيق).
    first = ff.split(",")[0].strip().strip("'\"")
    assert first == BUNDLED_FONT_FAMILY, \
        f"«{BUNDLED_FONT_FAMILY}» ليس أوّل مكدّس editor.fontFamily (لن يُفضَّل عند توفّره): «{first}» [AR-02]"
    assert ff.rstrip().endswith("monospace"), "مكدّس editor.fontFamily لا ينتهي بـmonospace [AR-02]"
    assert ("Segoe UI" in ff) or ("Noto Sans Arabic" in ff), \
        "مكدّس editor.fontFamily بلا احتياطيّ عربيّ (Segoe UI/Noto Sans Arabic) — عربيّة رديئة بلا الخطّ المحزوم [AR-02]"
    assert defaults.get("terminal.integrated.fontFamily") == ff, \
        "terminal.integrated.fontFamily لا يطابق editor.fontFamily (اتّساق أسطح الخطّ) [AR-02]"

    # **حارس الانحدار الحرِج:** الورقة الساكنة يجب ألّا تحوي url() نسبيًّا لـ.woff2 — esbuild
    # (optimize.ts) يحلّ url() في الـCSS المحزوم زمن البناء، و.woff2 بلا loader ⇒ يفشل البناء
    # («No loader…») وغيابُ الملفّ يفشله («Could not resolve»). الحقن الآمن data: URI فقط.
    css_body = _strip_css_comments(_read(os.path.join(ROOT, M.CSS_PATCH)))
    assert "woff2" not in css_body, \
        f"مرجع woff2 عاد إلى {M.CSS_PATCH} الساكنة — url() نسبيّ يكسر بناء esbuild؛ استعمل حقن data:URI [AR-02]"

    # وصل البناء: build.sh يجهّز المصدر (MIHRAB_ARABIC_FONT→staged)، وpatch_bundle يحقن @font-face
    # بمصدر data: URI (base64) مشتقّ من الملفّ المُجهَّز — لا loader ولا رُقعة نواة (يتركه esbuild حرفيًّا).
    build_sh = _read(os.path.join(ROOT, "build", "build.sh"))
    assert "MIHRAB_ARABIC_FONT" in build_sh and STAGED_FONT in build_sh, \
        f"build.sh لا يجهّز الخطّ العربيّ المحزوم (MIHRAB_ARABIC_FONT/{STAGED_FONT}) [AR-02]"
    bundle_py = _read(os.path.join(ROOT, "build", "patch_bundle_extensions.py"))
    assert STAGED_FONT in bundle_py, \
        f"patch_bundle_extensions لا يشتقّ الخطّ من الملفّ المُجهَّز ({STAGED_FONT}) [AR-02]"
    for needle in ("@font-face", BUNDLED_FONT_FAMILY, "data:font/woff2", "base64"):
        assert needle in bundle_py, \
            f"patch_bundle_extensions لا يحقن @font-face بـdata:URI base64 (ينقص «{needle}») — قد يعود url() الكاسر [AR-02]"

    # [AR-01↔AR-02] لوحة المخرجات (webview معزول) تُضمِّن الخطّ المحزوم data:URI من media/ لتعرض
    # به عينه لا بخطّ نظاميّ: build.sh ينسخه إلى welcome/media، وoutput-panel.js يقرؤه ويبنيه.
    welcome = os.path.join(ROOT, "extensions", "mihrab-welcome")
    if os.path.isdir(welcome):
        # نفحص أمر cp **الفعليّ** لا مجرّد ظهور «media/kawkab-mono.woff2» نصًّا (يظهر في سطر
        # log أيضًا) كي لا يمرّ الحارس أخضر لو حُذف النسخ وبقي التسجيل — نجاح كاذب (أسوة بحرّاس
        # أصول الهوية التي تجرّد غير-الكود وتفحص سطر cp حقيقيًّا).
        bsh_code = [ln for ln in build_sh.splitlines() if not ln.lstrip().startswith("#")]
        assert 'WELCOME_MEDIA="$STAGE_EXT/mihrab-welcome/media"' in "\n".join(bsh_code), \
            "build.sh لا يعرّف WELCOME_MEDIA لمجلّد media لوحة الترحيب [AR-01↔AR-02]"
        assert any("cp -f" in ln and "WELCOME_MEDIA/kawkab-mono.woff2" in ln for ln in bsh_code), \
            "build.sh لا ينسخ الخطّ فعلًا إلى media/ لوحة الترحيب (سطر cp لا سطر log) [AR-01↔AR-02]"
        # السلسلةُ صارت من حلقتين بعد [PR-01]: اللوحةُ تفوّض، والوحدةُ المشتركةُ تبني الـURI.
        # ويُفحَص **الطرفان** لا أحدُهما: فحصُ اللوحة وحدَها يمرّ أخضرَ لو صار التفويضُ إلى
        # دالّةٍ لا تبني شيئًا، وفحصُ الوحدة وحدَها يمرّ أخضرَ لو كفّت اللوحةُ عن ندائها.
        panel_js = _read(os.path.join(welcome, "output-panel.js"))
        font_js = _read(os.path.join(welcome, "bundled-font.js"))
        assert "loadFontDataUri" in panel_js, \
            "output-panel.js لا ينادي مُحمِّلَ الخطّ المشترك [AR-01↔AR-02]"
        assert "data:font/woff2" in font_js and "base64" in font_js, \
            "bundled-font.js لا يبني data:URI للخطّ المحزوم [AR-01↔AR-02]"
        # وبصمةُ الصيغة: `readFileSync` ينجح على ملفٍّ مقتطعٍ وعلى كعبٍ فارغ، و«الحمولةُ
        # موجودة» تأكيدٌ ينجح عليهما معًا — فالحارسُ يشترط أن يبقى فحصُ البصمة قائمًا.
        assert "wOF2" in font_js, \
            "bundled-font.js لا يفحص بصمةَ WOFF2 — «قُرئ الملفّ» ليس «الملفُّ خطّ» [AR-02]"
        # و[PR-01] يشترط أن يبقى للتصدير مسارُ فشلٍ صريح: ملفٌّ يُطبَع بخطٍّ ساقطٍ عند غير
        # مُصدِّره أسوأُ من فشلٍ يُصلَح، لأنّ الانحرافَ الصامتَ يُوقَّع عليه.
        assert "required" in font_js, \
            "bundled-font.js فقد سياسةَ الفشل الإلزاميّ — تصديرُ الطباعة يسقط رشيقًا فيكذب [PR-01]"
        print_cmd = _read(os.path.join(welcome, "print-command.js"))
        assert "required: true" in print_cmd, \
            "print-command.js لا يشترط الخطَّ — يُصدَّر ملفٌّ بلا خطّ [PR-01]"
        # الخطّ ثنائيّ يُحقَن وقت البناء (كـbin/) ويُقرأ من extensionPath/media؛ يجب تجاهله في git
        # كي لا يُودَع لو أسقطه مطوّر في media/ (المتعقَّب لوسائط الجولة) للتجربة المحلّيّة.
        gitignore = _read(os.path.join(ROOT, ".gitignore"))
        assert "extensions/mihrab-welcome/media/kawkab-mono.woff2" in gitignore, \
            ".gitignore لا يتجاهل خطّ media المحقون (extensions/mihrab-welcome/media/kawkab-mono.woff2) — خطر إيداعه [AR-01↔AR-02]"


@check("صندوق رسالة الالتزام [SC-01]: المفتاحان اللذان تقبلهما قائمةُ السماح مضبوطان")
def _scm_input_defaults():
    """
    ‏[SC-01] صندوقُ الرسالة في جزء المصادر **لا يقرأ خدمةَ الإعدادات**: `isSimpleWidget: true`
    (‏`scmInput.ts:613`) ⇒ `editorConfiguration.ts:73-88` تبني الخياراتِ من كائنٍ مُمرَّرٍ بلا
    حقن `IConfigurationService`. فما يبلغ الصندوقَ هو ما يقرؤه `SCMInputWidget` بيده في
    **قائمةِ سماحٍ مغلقة** (‏`scmInput.ts:310`). ومن مفاتيحنا الخمسة لا يبلغه إلّا اثنان،
    وبطريقٍ غير مباشر: `scm.inputFontFamily: "editor"` (يُحيل إلى `editor.fontFamily`،
    ‏`scmInput.ts:315-317`) و`scm.inputFontSize`.

    وهذا الحارسُ يمنع **انحدارًا صامتًا** بعينه: إسقاطُ أحد المفتاحين لا يكسر شيئًا ولا
    يُظهِر خطأً — يعود الصندوقُ إلى خطّ القشرة وحجمِ ‎13‎، فيكتب المستخدمُ أطولَ نصٍّ عربيٍّ
    في يومه بوجهٍ لم يُقَس وحجمٍ دون المقيس، ولا حارسَ في الطبقتين الأخريَين يبلغه
    (‏`.view-line` وحدَها ما تفحصه الحرّاسُ الحيّة، والصندوقُ ليس منها).

    ويُقاس التساوي مع `editor.fontSize` لا رقمٌ مكتوبٌ بيده: القياسُ في VA-04 خاصّيّةُ
    **وجهٍ** لا خاصّيّةُ سطح، فانجرافُ أحد الرقمين وحده يكسر الحجّةَ التي بُني عليها.
    """
    shell = os.path.join(ROOT, "extensions", "mihrab-shell", "package.json")
    if not os.path.isfile(shell):
        return
    defaults = json.load(open(shell, encoding="utf-8")).get("contributes", {}).get("configurationDefaults", {})
    fam = defaults.get("scm.inputFontFamily")
    assert isinstance(fam, str) and fam.strip().lower() == "editor", (
        "‏`scm.inputFontFamily` ليس `editor` في mihrab-shell — صندوقُ رسالة الالتزام "
        "يعود إلى خطّ القشرة (افتراضُ المنبع `default`) بدل الوجه المحزوم [SC-01]")
    size = defaults.get("scm.inputFontSize")
    editor_size = defaults.get("editor.fontSize")
    assert size == editor_size, (
        f"‏`scm.inputFontSize`={size} لا يساوي `editor.fontSize`={editor_size} — "
        f"القياسُ في VA-04 خاصّيّةُ وجهٍ لا خاصّيّةُ سطح، فلا يجوز أن ينجرف أحدُهما [SC-01]")


@check("وحدةُ التصحيح [DG-01]: المفاتيحُ الثلاثةُ مضبوطةٌ ومشدودةٌ إلى قياس المحرّر")
def _debug_console_defaults():
    """
    ‏[DG-01] وحدةُ التصحيح **نسخةٌ ثانيةٌ من عطب SC-01**: ‏`repl.ts:750` ينشئ حقلَ الإدخال
    بـ`getSimpleCodeEditorWidgetOptions()` و`simpleEditorOptions.ts:61` يمرّر
    ‏`isSimpleWidget: true`. والفرقُ أنّها **لا تقرأ `editor.*` إطلاقًا** بل ثلاثةَ مفاتيحَ
    خاصّةٍ بها — وهي **مفتوحةٌ لنا كلُّها**، فالبندُ يُغلَق من الطبقة الأولى بلا رقعةٍ ولا
    قاعدة. المقيسُ حيًّا قبلَها: ‏14px · ‏1.429em · ‏Consolas.

    والحارسُ يمنع **انحدارًا صامتًا**: إسقاطُ مفتاحٍ منها لا يرمي خطأً ولا يكسر بناءً —
    تعود وحدةُ التصحيح إلى خطٍّ لاتينيٍّ وارتفاعِ سطرٍ يقصّ التشكيل، في السطح الذي يقرأ
    فيه المستخدمُ **نتيجةَ برنامجه ورسالةَ خطئه**. ولا حارسَ حيٌّ يبلغه في المسار العاديّ
    (‏`debug_panes.live.mjs` يحتاج جلسةَ تنقيحٍ يبنيها بنفسه).

    والأرقامُ **مشدودةٌ إلى قياسِ المحرّر لا مكتوبةٌ بيد**: الحجمُ يساوي `editor.fontSize`
    (‏VA-04)، وارتفاعُ السطر يُقرأ بالبكسل هنا لا بالمضاعِف (‏`debug.console.lineHeight`
    بكسلات، و‎0‎ تعني «احسبه بمعامِل ‎1.4‎») فيجب أن يبلغ حاصلَ الحجم × مضاعِف المحرّر —
    وإلّا انجرف أحدُهما وحدَه وسقطت الحجّةُ التي بُني عليها الآخر.
    """
    shell = os.path.join(ROOT, "extensions", "mihrab-shell", "package.json")
    if not os.path.isfile(shell):
        return
    defaults = json.load(open(shell, encoding="utf-8")).get("contributes", {}).get("configurationDefaults", {})
    fam = defaults.get("debug.console.fontFamily")
    editor_fam = defaults.get("editor.fontFamily")
    assert fam == editor_fam, (
        "‏`debug.console.fontFamily` لا يطابق `editor.fontFamily` — وحدةُ التصحيح تعود "
        "إلى خطٍّ لاتينيٍّ (المقيسُ حيًّا: Consolas) في السطح الذي يقرأ فيه المستخدمُ "
        "مخرَجَ برنامجه [DG-01]")
    size = defaults.get("debug.console.fontSize")
    editor_size = defaults.get("editor.fontSize")
    assert size == editor_size, (
        f"‏`debug.console.fontSize`={size} لا يساوي `editor.fontSize`={editor_size} — "
        f"قياسُ VA-04 خاصّيّةُ وجهٍ لا خاصّيّةُ سطح [DG-01]")
    lh_px = defaults.get("debug.console.lineHeight")
    lh_em = defaults.get("editor.lineHeight")
    assert isinstance(lh_px, (int, float)) and lh_px > 0, (
        "‏`debug.console.lineHeight` غائبٌ أو صفر — والصفرُ يعني في المنبع «احسبه بمعامِل "
        "‎1.4‎»، وهو دون أرضيّة الحبر المقيسة ‎2.683em‎ فيُقصّ التشكيل [DG-01 · TY-02]")
    if isinstance(size, (int, float)) and isinstance(lh_em, (int, float)):
        want = round(size * lh_em)
        assert abs(lh_px - want) <= 1, (
            f"‏`debug.console.lineHeight`={lh_px}px لا يطابق قياسَ المحرّر "
            f"({size} × {lh_em} ≈ {want}px) — الرقمُ يُشتقّ ولا يُكتَب بيد [DG-01 · TY-02]")


@check("حدودُ الكلمة [IN-01]: الفواصلُ بادئتُها المنبعُ حرفًا، وزيادتُها ترقيمٌ لا فاصلُ عدد")
def _word_separators_prefix():
    """
    ‏[IN-01] ‏`editor.wordSeparators` سُلَّميّةٌ من نوع `string`: تجاوزُها **يستبدل**
    الافتراضَ ولا يُضيف إليه (‏`editorOptions.ts:6763` يسجّلها `EditorStringOption`
    بافتراضٍ هو `USUAL_WORD_SEPARATORS`، و`WordCharacterClassifier` يتلو السلسلةَ
    المُمرَّرةَ وحدَها حرفًا حرفًا). فنحن مضطرّون إلى **نسخ ثابتٍ منبعيٍّ** إلى ملفّنا كي
    نزيد عليه اثنَي عشرَ محرفَ ترقيمٍ عربيّ.

    وهذا يفتح بابَ انحدارٍ صامتٍ من جهتين، والحارسُ يسدّهما:

      (أ) **نقصٌ في البادئة.** لو كُتبت الزيادةُ وحدَها («،؛؟») سقط الواحدُ والثلاثون
          محرفًا اللاتينيّة، فصارت `()` و`[]` و`.` جزءًا من الكلمة والتقط النقرُ المزدوجُ
          على `اطبع(نص)` السطرَ كلَّه. عطبٌ فادحٌ لا يرمي خطأً ولا يكسر بناءً.
      (ب) **انجرافُ المنبع.** لو زاد المنبعُ محرفًا إلى `USUAL_WORD_SEPARATORS` بقيت
          نسختُنا ناقصةً بلا إشعار. ولذلك تُقرأ البادئةُ **من ملفّ المنبع نفسِه** — أو من
          لقطة L1 المُلتزَمة (‏`REFERENCE_FILES`) لأنّ `.upstream/` مُتجاهَلٌ في git وبلا
          الارتداد يكون لُبُّ الفحص معطَّلًا في CI صامتًا. الصنفُ نفسُه الذي يحرسه AR-04.

    والشرطُ الثالثُ ليس شكليًّا: **«٫» U+066B و«٬» U+066C ممنوعتان**. هما فاصلا *عدد*
    عربيَّان لا علامتا ترقيم، وإضافتُهما تشقّ ‎٣٫١٤‎ إلى ‎٣‎ — أي تُدخِل انحدارًا في
    أرقام المستخدم ثمنًا لمكسبٍ لا وجودَ له، إذ لا تردان في النثر أصلًا. قِيست الزيادةُ
    محرفًا محرفًا قبل الشحن، وهذان وحدَهما سقطا في القياس.
    """
    shell = os.path.join(ROOT, "extensions", "mihrab-shell", "package.json")
    if not os.path.isfile(shell):
        return
    defaults = json.load(open(shell, encoding="utf-8")).get("contributes", {}).get("configurationDefaults", {})
    ours = defaults.get("editor.wordSeparators")
    assert isinstance(ours, str) and ours, (
        "‏`editor.wordSeparators` غائبٌ من mihrab-shell — يعود حدُّ الكلمة إلى المِسطرة "
        "اللاتينيّة، فيلتقط النقرُ المزدوجُ الفاصلةَ العربيّةَ مع الكلمة [IN-01]")

    REL = os.path.join("src", "vs", "editor", "common", "core", "wordHelper.ts")
    src_path = os.path.join(ROOT, ".upstream", "vscode", REL)
    if not os.path.isfile(src_path):
        src_path = os.path.join(os.path.dirname(HERE), "apply", "snapshot", REL)
    assert os.path.isfile(src_path), (
        "لا `wordHelper.ts` — لا في المنبع المثبَّت ولا في لقطة L1. شغّل "
        "`python tests/apply/refresh_snapshot.py` والتزِم اللقطة [IN-01]")
    m = re.search(r"USUAL_WORD_SEPARATORS\s*=\s*'((?:\\.|[^'\\])*)'",
                  open(src_path, encoding="utf-8").read())
    assert m, "تعذّر إيجاد `USUAL_WORD_SEPARATORS` في المنبع — تغيّر شكلُه؟ [IN-01]"
    upstream = m.group(1).replace("\\\\", "\\").replace("\\'", "'")
    # تحقّقٌ من أنّنا أمسكنا الثابتَ الصحيح لا سلسلةً أخرى بالاسم نفسِه.
    assert "(" in upstream and "." in upstream and len(upstream) >= 20, (
        f"الثابتُ المُلتقَط لا يشبه قائمةَ فواصل ({upstream!r}) — مرساةٌ أمسكت غيرَه [IN-01]")

    assert ours.startswith(upstream), (
        f"‏`editor.wordSeparators` لا يبدأ بالافتراض المنبعيِّ حرفًا. المنبع: {upstream!r}\n"
        f"وقيمتُنا: {ours!r}\n"
        "والقيمةُ **تستبدل** ولا تضيف — فالنقصُ هنا يجعل الأقواسَ والنقطةَ جزءًا من "
        "الكلمة، وهو عطبٌ لا يرمي خطأً [IN-01]")

    extra = ours[len(upstream):]
    assert extra, (
        "‏`editor.wordSeparators` يساوي الافتراضَ المنبعيَّ بلا زيادة — نسخٌ بلا سبب. "
        "إمّا أن يُزاد الترقيمُ العربيُّ وإمّا أن يُحذَف المفتاحُ كلُّه [IN-01]")
    for ch in ("٫", "٬"):
        assert ch not in extra, (
            f"‏{ch!r} فاصلُ **عدد** عربيٌّ لا علامةُ ترقيم — إضافتُه تشقّ ‎٣٫١٤‎ إلى ‎٣‎ "
            f"بلا مكسبٍ في النثر [IN-01]")
    for ch in "،؛؟":
        assert ch in extra, (
            f"‏{ch!r} غائبٌ عن الزيادة — وهو أكثرُ الترقيم العربيّ ورودًا، والعطبُ الذي "
            f"فُتح البندُ لأجله [IN-01]")


# ───────────── L0-8: سمتا محراب (خريطة الرموز ↔ نحو ص) ─────────────
def _grammar_scopes():
    """كلّ نطاقات (scopes) نحو ص الفعليّة من sad.tmLanguage.json."""
    g = os.path.join(ROOT, "extensions", "sad-lang", "syntaxes", "sad.tmLanguage.json")
    if not os.path.isfile(g):
        return None
    data = json.load(open(g, encoding="utf-8"))
    found = set()

    def walk(o):
        if isinstance(o, dict):
            n = o.get("name")
            if isinstance(n, str) and "." in n:
                found.add(n)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(data)
    return found


@check("سمتا محراب: JSON صالح، مُسهَمتان وافتراضيّة، ونطاقاتها تطابق نحو ص")
def _themes():
    ext = os.path.join(ROOT, "extensions", "mihrab-themes")
    if not os.path.isdir(ext):
        return  # لا إضافة سمات في هذا الفرع — تخطٍّ
    pkg = json.load(open(os.path.join(ext, "package.json"), encoding="utf-8"))
    contrib = pkg.get("contributes", {})
    themes = contrib.get("themes", [])
    assert len(themes) >= 2, f"متوقّع سمتان (داكنة/فاتحة)، وُجد {len(themes)}"
    # الافتراضيّة يجب أن تساوي أحد الـlabels فعلًا (خطأ مطبعيّ ⇒ VS Code يسقط للأساس صامتًا).
    default = contrib.get("configurationDefaults", {}).get("workbench.colorTheme")
    labels = {t.get("label") for t in themes}
    assert default in labels, f"السمة الافتراضيّة «{default}» ليست من labels السمات {labels}"
    # ── السمات المفضَّلة لكلّ وضع نظام — **الوصلة التي بدونها تصير سمتا التباين العالي حبرًا
    # على ورق.** ‏`window.autoDetectHighContrast` مفعَّل افتراضًا؛ فحين يكون نظام التشغيل في
    # وضع التباين العالي، يبدّل VS Code إلى `workbench.preferredHighContrastColorTheme`
    # لا إلى `workbench.colorTheme`. وافتراض ذلك المفتاح هو ثابت المنبع
    # ‏`ThemeSettingDefaults.COLOR_THEME_HC_DARK = 'Default High Contrast'`. أي أنّ **أحوج
    # المستخدمين إلى تصميم مقصود كان يُنقَل تلقائيًّا خارج سمات محراب** — وهو عين الفجوة
    # التي بُنيت سمتا hcDark/hcLight لسدّها. والأمر نفسه لـautoDetectColorScheme (داكن/فاتح).
    # كلّ قيمة تُطابَق بالـlabel: خطأ مطبعيّ ⇒ VS Code يسقط للأساس **صامتًا** بلا خطأ.
    UI_THEME_OF = {"vs-dark": "workbench.preferredDarkColorTheme",
                   "vs": "workbench.preferredLightColorTheme",
                   "hc-black": "workbench.preferredHighContrastColorTheme",
                   "hc-light": "workbench.preferredHighContrastLightColorTheme"}
    defaults = contrib.get("configurationDefaults", {})
    for t in themes:
        key = UI_THEME_OF.get(t.get("uiTheme"))
        if not key:
            continue
        assert defaults.get(key) == t["label"], (
            f"‏`{key}` = «{defaults.get(key)}» لا «{t['label']}» — عند تبديل النظام إلى هذا "
            f"الوضع يخرج المستخدم من سمات محراب إلى سمة المنبع العامّة")
    gscopes = _grammar_scopes()  # نحو ص الفعليّ
    grammar_sad = {s for s in gscopes if s.endswith(".sad")} if gscopes is not None else set()
    # نطاقات نحو لا تُلوَّن عمدًا (حاويات بنيويّة نلوّن محتواها لا هي): تُعفى من التغطية العكسيّة.
    uncolored = {"meta.interpolation.sad"}
    for t in themes:
        assert t.get("label") and t.get("uiTheme") and t.get("path"), f"عقد سمة ناقص: {t}"
        tp = os.path.join(ext, *t["path"].lstrip("./").split("/"))
        assert os.path.isfile(tp), f"ملفّ سمة مفقود: {t['path']}"
        td = json.load(open(tp, encoding="utf-8"))
        assert td.get("name"), f"سمة بلا name: {t['path']}"
        # أنواع سمات VS Code الأربعة (dark/light + نظيراهما عاليا التباين).
        assert td.get("type") in ("dark", "light", "hcDark", "hcLight"),             f"type غير صالح في {t['path']}"
        assert td.get("colors") and td.get("tokenColors"), f"بلا colors/tokenColors: {t['path']}"
        # نطاقات ص في **هذه السمة** (التغطية تُفحَص لكلّ سمة، لا اتّحادهما).
        this_scopes = set()
        for rule in td["tokenColors"]:
            sc = rule.get("scope", [])
            for s in ([sc] if isinstance(sc, str) else sc):
                if s.endswith(".sad"):
                    this_scopes.add(s)
        # (أمام) كلّ نطاق ص في السمة موجود في النحو الفعليّ (لا اختراع/انجراف):
        if gscopes is not None:
            invented = this_scopes - grammar_sad
            assert not invented, (
                f"نطاقات في {t['path']} غير موجودة في نحو ص (مخترَعة/منجرفة): {sorted(invented)}")
            # (خلف) كلّ نطاق نحو ص مُلوَّن في هذه السمة (أو مُعفى) — يمسك نطاقًا جديدًا بلا لون:
            missing = grammar_sad - this_scopes - uncolored
            assert not missing, (
                f"نطاقات نحو ص بلا لون في {t['path']} (سترث افتراضيًّا متنافرًا): {sorted(missing)} "
                f"— أضِف لونًا في gen_themes.py أو أعفِها صراحةً")


@check("طباعة القشرة العربيّة [AR-03]: مكدّس :lang(ar) للمنصّات الثلاث + وحدة الوجه الأحاديّ")
def _arabic_chrome_typography():
    """يحرس القاعدة 20 في mihrab-rtl.css — سدُّ ثغرة `:lang(ar)` الغائبة عن المنبع.

    المنبع (style.css:12-29) يخصّص `--monaco-font` لـzh/ja/ko × (mac/windows/linux) ولا يخصّصه
    للعربيّة. أخطر أثر على **لينكس**: مكدّسه `Ubuntu`/`Droid Sans` بلا محارف عربيّة ⇒ الاختيار
    يؤول إلى fontconfig (غير حتميّ). هذا الفحص يمنع سقوط القاعدة أو نقصان منصّة منها.
    """
    BUNDLED_FONT_FAMILY = "Kawkab Mono"  # يطابق [AR-02] — الوجه المحزوم نفسه
    # المنصّات الثلاث التي يعرّف لها المنبع مكدّسًا؛ نقص أيٍّ منها = منصّة بلا عربيّة حتميّة.
    PLATFORMS = ("windows", "mac", "linux")
    # الوجه العربيّ الصريح المتوقَّع لكلّ منصّة (السند الذي يجعل الناتج حتميًّا لا ضمنيًّا).
    ARABIC_FACE = {"windows": "Tahoma", "mac": "SF Arabic", "linux": "Noto Sans Arabic"}
    css = _strip_css_comments(_read(os.path.join(ROOT, M.CSS_PATCH)))

    for plat in PLATFORMS:
        sel = f'.monaco-workbench[dir="rtl"].{plat}:lang(ar)'
        assert sel in css, (
            f"لا قاعدة `{sel}` في {M.CSS_PATCH} — منصّة {plat} تسقط لمكدّس المنبع "
            f"اللاتينيّ بلا عربيّة معلَنة [AR-03]")
        # جسم كلّ قاعدة تخصّ هذه المنصّة (قاعدتان: المتناسب والأحاديّ).
        bodies = [css[css.index(sel, p) + len(sel):][:css[css.index(sel, p) + len(sel):].index("}")]
                  for p in _all_positions(css, sel)]
        prop = "".join(bodies)
        assert "--monaco-font:" in prop, f"قاعدة {plat}:lang(ar) بلا `--monaco-font` [AR-03]"
        assert "--monaco-monospace-font:" in prop, \
            (f"قاعدة {plat}:lang(ar) بلا `--monaco-monospace-font` — شيفرة ص العربيّة داخل "
             f"القشرة (تلميحات/اختصارات/فتات) ستُعرَض بوجه مغاير للمحرّر [AR-03]")
        assert ARABIC_FACE[plat] in prop, (
            f"مكدّس {plat}:lang(ar) بلا الوجه العربيّ الصريح «{ARABIC_FACE[plat]}» — "
            f"التغطية تعود ضمنيّة/غير حتميّة [AR-03]")

    # وحدة الوجه: الأحاديّ في القشرة يبدأ بالخطّ المحزوم نفسه الذي يبدأ به editor.fontFamily
    # (‏[AR-02]) — وإلّا اختلف وجه المعرّف العربيّ بين المحرّر والتلميح.
    for m in _all_positions(css, "--monaco-monospace-font:"):
        stack = css[m + len("--monaco-monospace-font:"):]
        stack = stack[:stack.index(";")]
        first = stack.split(",")[0].strip().strip("'\"")
        assert first == BUNDLED_FONT_FAMILY, (
            f"«{BUNDLED_FONT_FAMILY}» ليس أوّل مكدّس --monaco-monospace-font (وُجد «{first}») — "
            f"وجه الشيفرة في القشرة يخالف المحرّر [AR-03]")
        assert stack.rstrip().endswith("monospace"), \
            "مكدّس --monaco-monospace-font لا ينتهي بـmonospace [AR-03]"


@check("حشوات تسمية الأيقونة [القاعدة 23]: شارة التزيين والأيقونة والوصف + استثناء التبويب")
def _icon_label_margins():
    """يحرس القاعدة 23 — قيمٌ فيزيائيّة في أكثر ودجةٍ حضورًا في المحرّر.

    ‏`monaco-icon-label` تحمل أسماء الملفّات في المستكشف والتبويبات والفتات والبحث وGit
    ولوحة الأوامر. وثلاث قيمٍ فيها فيزيائيّة تنقلب دلالتها مع القشرة — **رُصدت أوّلًا في
    لقطة البناء المشحون**: شارة «‎+9‎» ملتصقة بالاسم («‎+9rtl_fixture.ص‎»)، ثمّ أُكِّدت من
    ‏`iconlabel.css:105`: `margin: auto 16px 0 5px` ⇒ في RTL ‎16px‎ تفصل الشارة عن الاسم
    و‎5px‎ عن الحافّة، أي عكس المقصود تمامًا.

    **والاستثناء جزءٌ من الحارس لا زينة:** المنبع يُصفِّر `margin-right` في التبويبات/الفتات
    بأولويّة ‎(0,6,1)‎، وهي تغلب قاعدتنا العامّة ‎(0,3,1)‎ وتُلغي فجوة الاسم في RTL. قِسنا
    ذلك حيًّا بعد تطبيق الإصلاح الأوّل (`0 0 0 5px` ⇒ `0 0 0 16px` — ما زالت ملتصقة)، فلزم
    استثناءٌ صريح. سقوطُه يُعيد العطب في التبويبات وحدها بينما يبدو المستكشف سليمًا.
    """
    css = _strip_css_comments(_read(os.path.join(ROOT, M.CSS_PATCH)))
    RTL = '.monaco-workbench[dir="rtl"]'
    assert f"{RTL} .monaco-icon-label::after" in css, \
        "شارة تزيين تسمية الأيقونة بلا عكس في RTL — تلتصق بالحافّة وتنفصل عن الاسم [القاعدة 23]"
    assert "margin-inline: 5px 16px" in css, (
        "قيمتا شارة التزيين ليستا معكوستين (متوقَّع `margin-inline: 5px 16px` — الداخليّة "
        "أوّلًا) [القاعدة 23]")
    assert f"{RTL} .monaco-icon-label-iconpath" in css, \
        "فجوة أيقونة التسمية (`margin-right: 6px`) بلا عكس في RTL [القاعدة 23]"
    assert ".label-description" in css and "margin-inline-start: 0.5em" in css, \
        "فجوة الوصف الخافت (`margin-left: 0.5em`) بلا عكس في RTL [القاعدة 23]"
    # الاستثناء: يجب أن تُصفَّر الجهة **اليسرى** في التبويبات/الفتات وتُعاد اليمنى.
    assert f"{RTL} .part.editor > .content .editor-group-container > .title.tabs .monaco-icon-label::after" in css, (
        "لا استثناء للتبويبات — تصفيرُ المنبع لـ`margin-right` بأولويّة أعلى يُلغي فجوة "
        "الشارة عن الاسم في RTL (مقيس) [القاعدة 23]")


@check("الرموز الاتّجاهيّة [القاعدة 22]: مثلّث الشجرة + أدلّتها + الأسهم المعكوسة — بلا قلبٍ جملة")
def _directional_glyphs():
    """يحرس القاعدة 22 — الأسهم التي لا يمسّها `dir=rtl` لأنّها مرسومة بـ`transform`.

    كلّ بند هنا **مقيس بـCDP حيًّا** قبل كتابته (لا مستنتَج من قراءة المصدر):
      • مثلّث الشجرة: قِسنا صندوق الرمز ‎[1133‥1149]‎ في العمقين ٠ و١ ⇒ لا يتدرّج مع العمق
        (‏`paddingLeft` فيزيائيّة والحافّة اليمنى مثبَّتة). و`scaleX(-1)` على الحاوية يُصلح
        التدرّج **واتّجاه الرمز معًا**؛ قِسنا بعده ‎[1125‥1141]‎ ثمّ ‎[1117‥1133]‎ (خطوة ‎8px‎).
      • أدلّة التشجير: كانت عند ‎x=868‎ بينما صفوف الشجرة عند ‎1155‎ — الحافّة المقابلة.
      • الأسهم: `view-pane-container-collapsed` قِسناه `none` ⇒ صار `matrix(-1,0,0,1,0,0)`.

    ويمنع الفحص **القلب الجملة**: `.codicon-chevron-right` صنفٌ عامّ يخدم استعمالات غير
    اتّجاهيّة، فقلبه يكسر ما لم يكن مكسورًا.
    """
    css = _strip_css_comments(_read(os.path.join(ROOT, M.CSS_PATCH)))
    RTL = '.monaco-workbench[dir="rtl"]'
    # (أ) المثلّث: قلبٌ على الحاوية لا دورانٌ على ::before — الأوّل يُصلح التدرّج أيضًا.
    tw = f"{RTL} .monaco-tl-twistie"
    assert tw in css, "لا قاعدة لمثلّث الشجرة في RTL [القاعدة 22]"
    body = css[css.index(tw) + len(tw):]
    body = body[:body.index("}")]
    assert "scaleX(-1)" in body, (
        "قلب مثلّث الشجرة `scaleX(-1)` غائب — الرمز يشير عكس اتّجاه التوسّع **ولا يتدرّج مع "
        "العمق** (حشوة `paddingLeft` فيزيائيّة تُثبِّت الرمز) [القاعدة 22]")
    assert "translateX(-3px)" in body, (
        "إزاحة المنبع `translateX(3px)` لم تُعكَس إلى `-3px` — قلبُ الحاوية بلا عكس الإزاحة "
        "يزحزح الرمز ‎6px‎ عن محلّه [القاعدة 22]")
    # (ب) أدلّة التشجير: إرساءٌ مقلوب + حدٌّ على الحافّة المقابلة.
    ind = f"{RTL} .monaco-tl-indent"
    assert ind in css, "لا إعادة إرساء لأدلّة التشجير في RTL [القاعدة 22]"
    ind_body = css[css.index(ind) + len(ind):]
    ind_body = ind_body[:ind_body.index("}")]
    assert "left: auto" in ind_body and "right:" in ind_body, (
        "أدلّة التشجير ما زالت مرساةً بـ`left` — تُرسَم على الحافّة المقابلة للشجرة "
        "(قِسنا فارق ‎≈230px‎) [القاعدة 22]")
    assert "border-right:" in css, \
        "حدّ دليل التشجير لم يُنقَل إلى الحافّة المقابلة (border-right) [القاعدة 22]"
    # (ج) الأسهم المخصَّصة للاتّجاه — أصنافٌ سجّلها المنبع لهذا الغرض وحده.
    for icon in ("codicon-breadcrumb-separator", "codicon-view-pane-container-collapsed",
                 "codicon-search-hide-replace", "codicon-suggest-more-info"):
        assert f"{RTL} .{icon}::before" in css, \
            f"السهم الاتّجاهيّ `{icon}` غير معكوس في RTL [القاعدة 22]"
    # زرّ «رجوع» في الجولة: صنفه (`chevron-left`) عامٌّ فيُحصَر بحاويته. كان **آخر سهمٍ بلا
    # عكس في القشرة المشحونة** — أثبته مسحٌ حيّ لكلّ `codicon-chevron/arrow/triangle` الظاهرة
    # (‏3 نتائج: سهما مركز الأوامر معكوسان بالقاعدة 8، وهذا `transform: none`).
    assert f"{RTL} .gettingStartedContainer .prev-button > .codicon-chevron-left::before" in css, \
        "سهم «رجوع» في الجولة غير معكوس — يشير عكس جهة السابق في RTL [القاعدة 22]"
    # (د) لا قلب جملة: الصنف العامّ يخدم استعمالات غير اتّجاهيّة.
    assert ".codicon-chevron-right" not in css, (
        "قلبٌ جملة لـ`.codicon-chevron-right` — الصنف عامّ (زخارف «مزيد»، مؤشّرات فتح) "
        "فقلبه يكسر ما لم يكن مكسورًا؛ اقصِر القلب على الأصناف المخصَّصة [القاعدة 22]")


@check("مسرَد المصطلحات مصدرُ حقيقةٍ للمنتج لا للموقع وحدَه [VA-06]")
def _glossary_governs_product():
    """يحرس VA-06 — ولمحرابٍ مسؤوليّةٌ خاصّةٌ هنا.

    نحن نكتب نصوصَ ثلاثةِ مصادرَ في آن: إضافاتُنا (عربيّةٌ مصنوعة)، وحزمةُ `language-pack-ar`
    (**مورَّدةٌ من طرفٍ ثالث**)، ومعجمُ الإعدادات المشتقّ. فمن الطبيعيِّ أن يظهر المفهومُ
    الواحدُ بثلاثة ألفاظٍ في ثلاث نوافذَ من التطبيق نفسِه. وهذا يضرب **الثقةَ قبل الجمال**:
    المستخدمُ الذي يقرأ «ملحق» و«امتداد» و«إضافة» في مكانٍ واحدٍ يظنّها أشياءَ مختلفة.

    وكان المسرَدُ يحكم **التوثيقَ وحدَه**. هذا الحارسُ يمدّه إلى **نصوص المنتج**: مانيفستات
    إضافاتنا وسلاسلُ `COPY` فيها. ويفحص البدائلَ الممنوعةَ صراحةً — لا يخترع حكمًا.
    """
    gpath = os.path.join(ROOT, "site", "data", "glossary.json")
    if not os.path.isfile(gpath):
        return
    terms = json.load(open(gpath, encoding="utf-8")).get("terms", [])
    assert terms, "المسرَدُ فارغ — عمِيَ الحارس [VA-06]"

    # الأسطحُ المفحوصة: كلُّ نصٍّ **نكتبه نحن** ويراه المستخدم. حزمةُ `language-pack-ar`
    # مستثناةٌ صراحةً: مورَّدةٌ من طرفٍ ثالثٍ ولا نملك صياغتَها — وتوحيدُها بندٌ آخر.
    # **مشيٌ متكرّرٌ لا مستوًى واحد.** الصيغةُ الأولى مشت على المستوى الأوّل وقبلت
    # `package.json` و`*.js` وحدَهما — فعمِيَت عن `media/*.md`، وهو **محتوى الجولة الذي
    # يقرؤه المبتدئ حرفًا حرفًا**. وفاتها انجرافٌ حقيقيٌّ فيه أحدثته الموجةُ نفسُها.
    SKIP_DIRS = {"node_modules", "bin", "data", ".vscode", "__pycache__"}
    targets = []
    ext_root = os.path.join(ROOT, "extensions")
    for name in sorted(os.listdir(ext_root)) if os.path.isdir(ext_root) else []:
        if name == "language-pack-ar":   # مورَّدةٌ من طرفٍ ثالث — لا نملك صياغتَها
            continue
        base = os.path.join(ext_root, name)
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in sorted(files):
                if f.endswith(".test.js") or f == "README.md":
                    continue
                if f == "package.json" or f.endswith(".js") or f.endswith(".md"):
                    targets.append(os.path.join(root, f))
    assert targets, "لا أسطحَ نصٍّ لفحصها — عمِيَ الحارس [VA-06]"

    def _ui_text_only(path):
        """يعيد النصَّ **الذي يراه المستخدم** وحدَه — لا التعليقات.

        فحصُ التعليقات يُنتج ضجيجًا: «الخيارات» في شرحِ خياراتِ `Intl` ليست مصطلحَ واجهة،
        و«التصحيح» في تعليقٍ عن تصحيح خطأٍ برمجيّ ليست `Debug`. وحارسٌ يُنذِر على ما لا
        يراه المستخدمُ يُعلَّم تجاهُلُه — وهو العطبُ نفسُه الذي بُني `BS-01` كلُّه لتفاديه.
        """
        raw = _read(path)
        if path.endswith(".md"):
            return raw     # ماركداون الجولة نصٌّ يراه المستخدم كلُّه
        if path.endswith(".json"):
            # في المانيفست: القيمُ التي تُعرَض وحدَها (لا مفاتيحُ التعليق `_comment*`).
            try:
                data = json.loads(raw)
            except Exception:
                return raw
            shown, UI_KEYS = [], ("title", "shortTitle", "description",
                                  "markdownDescription", "displayName", "detail")
            def walk(node, key=None):
                if isinstance(node, dict):
                    for k, v in node.items():
                        if not str(k).startswith("_comment"):
                            walk(v, k)
                elif isinstance(node, list):
                    for v in node:
                        walk(v, key)
                elif isinstance(node, str) and key in UI_KEYS:
                    shown.append(node)
            walk(data)
            return "\n".join(shown)
        # في JS: تُجرَّد التعليقاتُ السطريّةُ والكتليّة، ويبقى ما بين علامات الاقتباس.
        no_block = re.sub(r"/\*.*?\*/", "\n", raw, flags=re.S)
        return "\n".join(re.sub(r"(^|[^:\"'\\])//.*$", r"\1", ln) for ln in no_block.splitlines())

    hits = []
    for path in targets:
        text = _ui_text_only(path)
        for t in terms:
            for bad in t.get("forbidden", []):
                # نبحث عن اللفظ الممنوع **محاطًا بحدود كلمة عربيّة**: «الإضافة» ممنوعةٌ
                # لـExtension، لكنّ «الإضافات» في سياقٍ آخرَ قد تكون كلمةً عاديّة. فنطلب
                # تطابقًا تامًّا للمقطع بين فواصلَ غيرِ حرفيّة.
                # حدُّ الكلمة: حرفٌ عربيٌّ أو لاتينيٌّ أو رقم. و**علاماتُ الترقيم العربيّة
                # مستثناة** (‏، ؛ ؟ …) رغم وقوعها في كتلة العربيّة — كانت تُقرأ حرفًا فيمرّ
                # لفظٌ ممنوعٌ يليه فاصلة: ثغرةٌ صامتةٌ في الحارس نفسِه.
                for m in re.finditer(re.escape(bad), text):
                    before = text[m.start() - 1] if m.start() else " "
                    after = text[m.end()] if m.end() < len(text) else " "
                    WORD = r"[\w\u0620-\u065F\u0660-\u0669\u066E-\u06D3\u06FA-\u06FF]"
                    if re.match(WORD, before) or re.match(WORD, after):
                        continue
                    line = text[:m.start()].count("\n") + 1
                    hits.append(f"{os.path.relpath(path, ROOT)}:{line} «{bad}» ⇐ المعتمَد «{t['ar']}»")
    assert not hits, (
        "ألفاظٌ ممنوعةٌ في نصوص المنتج (المسرَدُ يحكمها): \n       " + "\n       ".join(hits[:12])
        + ("\n       …" if len(hits) > 12 else "") + " [VA-06]")


@check("كتالوج الأيقونات الاتّجاهيّة [DR-06]: الكتالوج ↔ الورقة في الاتّجاهين")
def _directional_icon_catalog():
    """يحرس DR-06 — نقلُ قاعدةِ القلب من الأذهان إلى الشيفرة.

    كانت القواعدُ ٨ و٢٢ تقلب أيقوناتٍ مسمّاةً واحدةً واحدة، والقرارُ «تُقلَب / لا تُقلَب» موزَّعٌ
    في محدِّدات CSS — فكلُّ أيقونةٍ جديدةٍ رهنُ انتباهِ مَن كتبها. والحارسُ **ثنائيُّ الاتّجاه**
    عمدًا، لأنّ الخطأ ممكنٌ في الجهتين: أيقونةٌ اتّجاهيّةٌ تُنسى فلا تُقلَب، أو أخرى تُقلَب بلا
    مبرّر فيقلب `scaleX(-1)` معها أيَّ نصٍّ أو تدرُّجٍ داخلها.
    """
    cat_path = os.path.join(ROOT, "patches", "directional-icons.json")
    assert os.path.isfile(cat_path), (
        "كتالوجُ الأيقونات الاتّجاهيّة مفقود (patches/directional-icons.json) — تعود القاعدةُ "
        "إلى الأذهان [DR-06]")
    cat = json.load(open(cat_path, encoding="utf-8"))
    css = _strip_css_comments(_read(os.path.join(ROOT, M.CSS_PATCH)))

    # كلُّ قواعد القلب في الورقة: (المحدِّدات، جسمُ القاعدة). القلبُ هو ما يعنينا هنا — لا
    # وجودُ الصنف: صنفٌ في `keep` قد تكون له قاعدةُ لونٍ أو حشوةٍ مشروعةٌ تمامًا.
    FLIP_PROPS = ("scalex(-1)", "matrix(-1", "rotate(180deg)", "rotatey(180deg)",
                  "scale(-1", "scalex( -1")
    flip_rules = []
    for m in re.finditer(r"\{([^{}]*)\}", css):
        body = m.group(1).lower().replace(" ", " ")
        if not any(p in body.replace(" ", "") for p in
                   (x.replace(" ", "") for x in FLIP_PROPS)):
            continue
        start = css.rfind("}", 0, m.start()) + 1
        flip_rules.append(css[start:m.start()])

    # (١) كلُّ ما في الكتالوج **مقلوبٌ فعلًا** — والحكمُ من قواعد القلب لا من ورودِ الصنف
    #     في أيّ مكان. الصيغةُ الأولى بنت `needle` ولم تستعمله، وفحصت أنّ الصنفَ يرد في
    #     الورقة والنطاقَ يرد فيها **منفصلَين** — فمدخلٌ لصنفٍ له قاعدةُ لونٍ فقط كان يمرّ.
    for e in cat.get("flip", []):
        cls, scope = e["class"], e.get("scope")
        assert e.get("why"), f"مدخلٌ بلا مبرّرٍ مكتوب: {cls} [DR-06]"
        cls_re = re.compile(r"\." + re.escape(cls) + r"(?![\w-])")
        assert any(cls_re.search(s_) and (not scope or scope in s_) for s_ in flip_rules), (
            f"‏«{cls}» في الكتالوج ولا **قاعدةَ قلبٍ** له في {M.CSS_PATCH}"
            + (f" بنطاق «{scope}»" if scope else "") +
            " — أيقونةٌ اتّجاهيّةٌ تشير عكسَ اتّجاه القراءة [DR-06]")

    # (٢) وكلُّ ما في `keep` **لا يُقلَب**: قلبُ صنفٍ عامٍّ يكسر ما لم يكن مكسورًا.
    for e in cat.get("keep", []):
        cls = e["class"]
        assert e.get("why"), f"مدخلُ استثناءٍ بلا مبرّرٍ مكتوب: {cls} [DR-06]"
        cls_re = re.compile(r"\." + re.escape(cls) + r"(?![\w-])")
        hit = next((s_ for s_ in flip_rules if cls_re.search(s_)), None)
        assert hit is None, (
            f"‏«{cls}» مُدرَجٌ في `keep` (لا يُقلَب) ومع ذلك يقع في قاعدة قلبٍ: "
            + hit.strip().replace("\n", " ")[:120] +
            " — إمّا انتقل قرارُه فيُنقَل في الكتالوج، وإمّا قلبٌ بلا مبرّر [DR-06]")

    # (٣) **الاتّجاهُ المعاكس:** كلُّ قاعدةِ قلبٍ في الورقة يذكرها الكتالوج. بلا هذا يبقى
    #     الكتالوجُ توثيقًا يتقادم بدل أن يكون مصدرَ حقيقة.
    known = {e["class"] for e in cat.get("flip", [])}
    for selectors in flip_rules:
        classes = set(re.findall(r"\.([a-zA-Z][\w-]*)", selectors))
        # أصنافُ النطاق (`monaco-workbench`، `command-center`) ليست أيقونات؛ يكفي أن يكون
        # **أحدُ** أصناف القاعدة مذكورًا في الكتالوج.
        assert classes & known, (
            "قاعدةُ قلبٍ بلا مدخلٍ في الكتالوج: "
            + selectors.strip().replace("\n", " ")[:120] + " [DR-06]")


@check("اتّجاه التسميات المحايدة [القاعدة 21]: تغطية الأهداف المرصودة + حصر أزرار الأيقونة")
def _bidi_neutrals():
    """يحرس القاعدة 21 — و**انحدارًا رصدناه حيًّا مرّة فلا يعود**.

    الخلاصة المُكلِفة: `unicode-bidi: plaintext` على `.button-link` نفسه (لا على ورقة نصّه)
    يجعل فقرة الزرّ كلَّها LTR فتنقلب الأيقونة من الحافّة القائدة إلى التابعة — أصلحنا النصّ
    وكسرنا التخطيط. فالقاعدة هنا شرطيّة لا مجرّد وجود:

      • الزرّ **ذو الأيقونة** يُستهدَف عبر ابنه النصّيّ فقط: `.button-link > span`.
      • الزرّ **بلا أيقونة** (نصُّه عقدةُ نصّ مباشرة، كـ«‎More...‎») يُستهدَف مباشرةً، لكن
        **مشروطًا بـ`:not(:has(.codicon))`** — فيسقط ذاتيًّا إن اكتسب أيقونة لاحقًا.

    ويمنع الفحص استهداف `.button-link` عاريًا (بلا `>` ولا `:not(`) — وهو الشكل المكسور نفسه.
    """
    css = _strip_css_comments(_read(os.path.join(ROOT, M.CSS_PATCH)))
    # الأهداف التي رُصد عطبها بالقياس الحيّ — سقوط أيٍّ منها انحدارٌ مُثبَت لا احتمال.
    REQUIRED = (
        ".monaco-icon-label .label-name",          # أسماء الملفّات (وتبويبات المحرّر: tab-label
                                                   #  صنفٌ إضافيّ على ResourceLabel ⇒ يرثها)
        ".monaco-icon-label .label-description",   # المسار بجانب الاسم
        ".gettingStartedContainer .button-link > span",
        ".gettingStartedContainer .button-link:not(:has(.codicon))",
        ".part.statusbar .statusbar-item-label",    # اسم فرع Git واللواحق المحايدة
        ".activitybar .badge-content",             # شارة العدد «3K+» — رصدها المسح الشامل
        ".gettingStartedContainer .path.detail",   # مسارات «المفتوحة مؤخّرًا»
    )
    # جسم القاعدة الحاوية لـplaintext (نتحقّق أنّ الأهداف داخلها لا في مكان آخر من الورقة).
    idx = css.find("unicode-bidi: plaintext")
    assert idx >= 0, f"لا `unicode-bidi: plaintext` في {M.CSS_PATCH} — القاعدة 21 سقطت"
    for sel in REQUIRED:
        assert sel in css, (
            f"القاعدة 21 بلا الهدف «{sel}» — نصٌّ رُصد عطبه حيًّا يعود لوراثة اتّجاه الفقرة "
            f"RTL فتقفز محايداته الطرفيّة")

    # حصر أزرار الأيقونة: أيّ `.button-link` يتلقّى plaintext يجب أن يكون إمّا ورقةَ نصّ
    # (`> span`) وإمّا مشروطًا بغياب الأيقونة. الشكل العاري = الانحدار المرصود.
    for m in _all_positions(css, ".button-link"):
        tail = css[m + len(".button-link"):]
        nxt = tail[:2].strip()
        assert nxt.startswith(">") or nxt.startswith(":"), (
            "‏`.button-link` مستهدَف عاريًا في القاعدة 21 — هذا يقلب الأيقونة من الحافّة "
            "القائدة إلى التابعة (انحدار مرصود بلقطة). استعمل `> span` أو "
            "`:not(:has(.codicon))`")


@check("محايدات bidi في اللوحات والقوائم [24+25]: تغطية الأسطح + نطاق حقل الاقتراح")
def _bidi_panels():
    """يحرس القاعدة 24 — أسطحُ اللوحات التي لم تكن مقيسةً حين كُتبت القاعدة 21.

    مسحٌ عامّ حيّ (‏`bidiPanels` في الحزام) أعاد خمسة أسطح، وكلّ هدفٍ هنا مقيسٌ لا مُفترَض:
    اسمُ الامتداد `‎.ipynb Support‎` كان يُعرَض `‎ipynb Support.‎`؛ ووصفُه اللاتينيّ كان
    يُقَصّ من **بدايته**؛ ورسالةُ البحث كانت `‎results in 194 files … 9838‎` والعدد في آخرها.

    وفحصٌ ثانٍ يحرس **نطاق** حقل الاقتراح: `plaintext` على `.view-line` نفسها لا يغلب
    سمة `dir="rtl"` التي يبصمها Monaco (‏`viewLine.ts:181`) — قِسناه: تُحسَب ولا تفعل شيئًا.
    فالهدف الصحيح هو `<span>` الداخليّة. واستهدافُ `.view-line` عاريًا خطأٌ مزدوج: قاعدةٌ
    ميّتة، **و**اتّساعٌ يبتلع محرّر الشيفرة الرئيس (شأنُ `patch_editor_rtl.py`).
    """
    css = _strip_css_comments(_read(os.path.join(ROOT, M.CSS_PATCH)))
    REQUIRED = (
        ".extension-list-item .name",                    # «.ipynb Support» ⇒ «ipynb Support.»
        ".extension-list-item .description",             # قُصَّ من بدايته لا نهايته
        ".suggest-input-container .view-line > span",    # «@builtin» ⇒ «builtin@»
        ".markers-panel .marker-message",                # «error [SYN001]: <source>:19:1»
        ".markers-panel .marker-line",                   # «[Ln 1, Col 1]»
        ".search-view .monaco-list-row a.match",         # سطر المطابقة المقتطَع من الطرفين
        ".search-view .messages .message",               # «329 results…» والعدد يقفز للآخر
        ".pane-header > .title",                         # عناوين الأجزاء مختلطة اللغة
        ".monaco-count-badge",                           # «83 Results» والعدد يقفز للآخر
        ".settings-editor .setting-item-category",       # «Editor:» والنقطتان تقفزان
        ".settings-editor .setting-item-description",    # وصفٌ لاتينيّ يُقَصّ من بدايته
        ".keybindings-editor .when-label",               # تعبير when: && و== وفواصل عليا
        ".keybindings-editor .when-label *",             # النصّ في ابنٍ يعزل بنفسه (مقيس)
        ".keybindings-editor .command-label",            # «Auto Fix...»
        ".pane-body .message-container > .message",      # «No extensions found.»
        # القاعدة 25 — قوائم السياق. أربعةُ بنودٍ من ثلاثة عشر انقلبت وتسعةٌ لم تتحرّك:
        # النقاطُ الثلاث في ذيل نصٍّ لاتينيّ تقفز إلى مقدّمته «‎New File...‎» ⇒ «‎...New File‎».
        ".monaco-menu .action-label",
        ".monaco-menu .action-label *",                  # النصّ في ابنٍ يعزل بنفسه
        ".monaco-menu .keybinding",                      # «Shift+Alt+R» في الصفّ نفسه
        # القاعدة 26 — الإشعارات (المركز والفقاعات معًا). شاهدٌ موجب مقيس: ذيلُ
        # «‎ESLint: unable to resolve configuration...‎» عند ‎198‎ ورأسُه عند ‎207‎ ⇒ النقاط
        # تسبق الرأس بصريًّا؛ وبعد الإصلاح ‎315‎ مقابل ‎95‎ ⇒ تتبعه.
        ".notification-list-item-message",
        ".notification-list-item-message *",             # الرسالة تُصيَّر Markdown في span
        ".notification-list-item-source",                # اسم الامتداد — لاتينيٌّ في صفٍّ عربيّ
        # القاعدة 27 — تلميح التبويب. مقيس: رأسُ المسار ‎C‎ عند ‎732‎ وذيلُه عند ‎685‎ ⇒
        # المسار **مقلوبٌ كلَّه**؛ وبعد الإصلاح ‎522‎ مقابل ‎1007‎.
        ".monaco-hover .hover-contents",
        ".monaco-hover .hover-contents *",
        # القاعدة 28 — رسالة الحالة الفارغة. مقيس: رأسُ الجملة عند 800 والنقطةُ عند 797
        # ⇒ النقطة في مقدّمة الجملة بصريًّا؛ وبعد الإصلاح 320 مقابل 612.
        ".message-box-container",
        ".message-box-container *",
        # القاعدة 29 — شريط العنوان: تسميةٌ محتواها اسمُ مساحة عمل أو **عنوانُ النافذة
        # كاملًا** أو **اسمُ الملفّ** (‏commandCenterControl.ts:216-234). قِسنا
        # ‏`rtl_fixture.ص`: بلا القاعدة ينفصل الامتدادُ العربيّ ويقفز قبل الجذع (899 مقابل 918).
        ".search-label",
        ".window-title",
        # القاعدة 30 — العطبُ المعاكس: نصٌّ **عربيّ** في حاوية **LTR** (ودجات المحرّر).
        # «‏3 من 146» تُقرأ «‏3 146 من» لأنّ الرقم بعد حرفٍ عربيّ يصير `AN` فيلتحق بمقطعه.
        ".find-widget .matchesCount",
        # القاعدة 31 — بقيّةُ ودجات الحاوية LTR، وقد فُتحت أخيرًا بمحفّزاتٍ مقيسة
        # (`Ctrl+.` و`F8`). عنوانُ إجراء الكود تنقلب جملتُه كاملةً فتُرمى التسميةُ
        # العربيّة إلى أقصى اليسار؛ وترويسةُ النظرة «‏1 مشكلة من 10» قاعدةُ W2 نفسها؛
        # ومتنُ المُشخِّص عليه `isolate` من المنبع — تعزل ولا تشتقّ اتّجاهًا.
        ".action-widget .monaco-list-row .title",
        ".zone-widget .peekview-title .dirname",
        ".zone-widget .descriptioncontainer .message div",
    )
    assert "unicode-bidi: plaintext" in css, (
        f"لا `unicode-bidi: plaintext` في {M.CSS_PATCH} — القاعدة 24 سقطت")
    # ⚠️ **الاحتواءُ النصّيُّ وحده حارسٌ كاذب.** كشفه اختبارُ نفيٍ للقاعدة 29: غيّرنا
    # ‏`.search-label` إلى `.search-labelXX` — وهو **صنفٌ غير موجود إطلاقًا** فالقاعدة
    # ميّتة — ومع ذلك أعاد الفحص ‎30/30‎، لأنّ الاسم المكسور يحوي الاسمَ الصحيح جزءًا منه.
    # نشترط أن يلي المُحدِّدَ **فاصلُ مُحدِّدات** (فاصلة أو مسافة أو `{`) لا حرفَ اسم.
    for sel in REQUIRED:
        ok = any(css[p + len(sel):p + len(sel) + 1] in (",", " ", "{", "\n", "\t", ":", ">")
                 for p in _all_positions(css, sel))
        assert ok, (
            f"القاعدة 24 بلا الهدف «{sel}» — سطحٌ رُصد عطبه حيًّا يعود لوراثة اتّجاه "
            f"الفقرة RTL فتقفز محايداته أو يُقَصّ نصُّه من الطرف الخطأ")

    # حصر النطاق: كلّ `.view-line` في الورقة يجب أن يكون داخل حقل الاقتراح **وبـ`> span`**.
    for m in _all_positions(css, ".view-line"):
        # **حدُّ النظر إلى الوراء هو المُحدِّد نفسه لا نافذةٌ بعدد أحرف.** كتبناه أوّلًا
        # بنافذة ‎90‎ حرفًا فسقط الفحص في اختبار النفي: مُحدِّدٌ عارٍ مضافٌ **بعد** الصحيح
        # يرى `.suggest-input-container` في **سطر جاره** فيمرّ. المُحدِّد يبدأ بعد آخر
        # فاصلة/قوس/سطر — فهذا هو المدى الصحيح.
        head = css[max((css.rfind(c, 0, m) for c in ",{}\n"), default=-1) + 1:m]
        tail = css[m + len(".view-line"):m + len(".view-line") + 8].strip()
        # **نطاقان مسموحان لا واحد — والثاني أُضيف بقياسٍ لا بتوسيعِ استثناء.**
        # ‏[SC-01] صندوقُ رسالة الالتزام محرّرُ Monaco **آخر** (‏`.scm-editor-container`)، وليس
        # محرّرَ الشيفرة الرئيس الذي جاء هذا الحصرُ ليحميه. وهو السطحُ الوحيدُ الذي لا تبلغه
        # إعداداتُنا (قائمةُ سماحٍ مغلقة، `scmInput.ts:310`)، فورقةُ الأنماط هي مخرجُه الوحيد
        # في طبقاتنا. وقِيس حيًّا (‏`tests/runtime/scm_input.live.mjs`) أنّ حقن
        # ‏`font-feature-settings` على `.view-line` **يغيّر القيمةَ المحسوبة فعلًا** — فليست
        # قاعدةً ميّتة، بخلاف حالة `plaintext` التي رُصدت في حقل الاقتراح.
        SCM_SCOPE = ".scm-editor-container" in head
        assert ".suggest-input-container" in head or SCM_SCOPE, (
            "‏`.view-line` مستهدَف خارج `.suggest-input-container` و`.scm-editor-container` — "
            "هذا يبتلع محرّر الشيفرة الرئيس، واتّجاه أسطره شأنُ رقعة المنبع [القاعدة 24]")
        # شرطُ `> span` **خاصٌّ بحالة الاتّجاه** لا قاعدةٌ عامّة: سببُه أنّ `plaintext` على
        # ‏`.view-line` لا تغلب سمةَ `dir="rtl"` التي يبصمها Monaco. والوراثةُ الطباعيّة
        # (‏`font-feature-settings`) تسري من العنصر إلى ذرّيّته بلا معارِض — فاشتراطُه هنا
        # كان سيمنع القاعدةَ الوحيدةَ التي **قِيس** أثرُها.
        assert SCM_SCOPE or tail.startswith(">"), (
            "‏`.view-line` مستهدَف عاريًا — عليها سمة `dir=\"rtl\"` من Monaco فلا تفعل "
            "`plaintext` شيئًا (مقيس). الهدف هو `> span` الداخليّة [القاعدة 24]")


def _all_positions(hay, needle):
    """كلّ مواضع `needle` في `hay` (لا أوّلها فقط) — القاعدة مكرّرة لكلّ منصّة."""
    out, i = [], hay.find(needle)
    while i != -1:
        out.append(i)
        i = hay.find(needle, i + 1)
    return out


# ───────── L0-8ب: تباين السمتين وتمايز لوحتهما (أرقام لا ذوق) ─────────
# عتبتان تحرسان قرارَي تصميمٍ سبق أن انكسرا صامتين، فصارا مُلزَمَين عدديًّا:
#   AA_MIN  — WCAG 2.1 معيار 1.4.3 لنصّ عاديّ صغير (كود المحرّر كلّه كذلك).
#   DE_MIN  — أدنى فارق ΔE76 مقبول بين فئتين دلاليّتين. اللوحة السابقة جعلت «مفتاح» و«رقم»
#             على بُعد 9.4 فقط (ذهبان متطابقان عمليًّا) و«نصّ» و«دالّة» على بُعد 11.6؛ عتبة 25
#             هي أدنى فارق يبقى مُدرَكًا على شاشة مكتبيّة مع تفاوت المعايرة.
AA_MIN = 4.5
DE_MIN = 25.0
# سمتا التباين العالي تُلزَمان بعتبة **AAA (‏1.4.6)** لا AA: من يختارهما يختارهما لحاجة بصريّة،
# فالوفاء بالحدّ الأدنى العامّ فيهما يُفرِغهما من معناهما. تُشتقّ العتبة من `type` في ملفّ السمة.
AAA_MIN = 7.0
HC_TYPES = ("hcDark", "hcLight")
# الفئات الدلاليّة الخمس التي يجب أن تتمايز. الرماديّات (تعليق/عامل/متغيّر) مستثناة عمدًا:
# هدوؤها مقصود، وتمايزها بالوظيفة والمَيْل (italic) لا باللون.
SEMANTIC_KINDS = ("keyword", "type", "function", "string", "number")


def _srgb_to_lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _parse_hex(h):
    """‏#RRGGBB → (r,g,b) بايتات. يرفض ما عداه (الشفافيّة #RRGGBBAA غير مدعومة هنا)."""
    h = h.lstrip("#")
    assert len(h) == 6, f"لون غير سداسيّ صريح: #{h}"
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _luminance(h):
    r, g, b = (_srgb_to_lin(c) for c in _parse_hex(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(fg, bg):
    a, b = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _lab(h):
    r, g, b = (_srgb_to_lin(c) for c in _parse_hex(h))
    # sRGB → XYZ (D65) → CIELAB، بمرجع أبيض D65.
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def colors_of(td):
    return td.get("colors", {})


def _delta_e(c1, c2):
    """ΔE76 (إقليديّ في CIELAB) — كافٍ لحارس «هل اللونان متمايزان؟»؛ لا نحتاج دقّة CIEDE2000."""
    return sum((a - b) ** 2 for a, b in zip(_lab(c1), _lab(c2))) ** 0.5


@check("طباعة السطر [TY-02 · DR-05]: ارتفاع سطرٍ يتّسع للتشكيل + قفل مسار GPU")
def _line_height_and_gpu():
    """يحرس رقمين لكلٍّ منهما اشتقاقٌ مكتوب، لا ذوقٌ ولا نسخٌ يدويّ.

    **‏`editor.lineHeight`** مشتقٌّ من مدى الحبر العربيّ **المركَّب**، ويُقرأ من المصدر
    الواحد `tests/dx/arabic_ink.measured.json` لا من رقمٍ منسوخٍ هنا. والرقمُ السابق
    ‎1.798em‎ كان خطأً في الأساس: قِيس من كونتورات الرسوم منفردةً (‏«أ» U+0623 عند
    ‎+1.265‎ وتنوينُ الكسر U+064D عند ‎−0.533‎) فلم يركّب علامةً على قاعدةٍ قطّ، وGPOS
    يرفعها فوق ذلك. والمقيسُ حيًّا ‎2.683em‎. وافتراضُ المنبع ‎1.35‎ (ويندوز/لينكس) دونه
    بمرّتين. فالحدُّ **محسوبٌ لا مختار**.

    والحارسُ **ذو حدّين**: أرضيّةٌ تمنع القصّ، وسقفٌ يمنع الاتّجاهَ الآخر. حارسٌ أُحاديٌّ
    يدفع الرقمَ صعودًا بلا ثمنٍ مرئيّ، وكلُّ زيادةٍ فوق الحاجة أسطرٌ تخرج من الشاشة.

    **‏`experimentalGpuAcceleration`** يُقفَل على `off`: طبقةُ GPU المنبعيّة بلا أيّ معالجة
    اتّجاه، والحمايةُ اليومَ ظرفيّةٌ («مطفأٌ افتراضيًّا في المنبع») لا بنيويّة. ويومَ يقلب
    المنبعُ الافتراضَ يسقط اتّجاهُ المحرّر **في مزامنةٍ روتينيّةٍ بلا سطر خطأٍ واحد**.
    """
    ink = json.load(open(os.path.join(ROOT, "tests", "dx", "arabic_ink.measured.json"),
                        encoding="utf-8"))
    MIN_LINE_HEIGHT = ink["composedInkEm"]   # الأرضيّة المقيسة — تحتها اقتطاعٌ مؤكَّد
    MAX_INK_HEADROOM = 1.10  # السقف: ‎10٪‎ فوق الحاجة المقيسة، فلا يُشترى الأمانُ بأسطر
    MAX_EM_VALUE = 8         # المنبع يقرأ ما دونها مضاعِفَ em (fontInfo.ts:37)
    FONT_SIZES = range(10, 21)  # مدى أحجام الخطّ العمليّ الذي يجب أن تصمد فيه القيمة
    shell = os.path.join(ROOT, "extensions", "mihrab-shell", "package.json")
    if not os.path.isfile(shell):
        return
    defaults = json.load(open(shell, encoding="utf-8")).get("contributes", {}).get(
        "configurationDefaults", {})
    lh = defaults.get("editor.lineHeight")
    assert isinstance(lh, (int, float)), (
        "لا `editor.lineHeight` افتراضيّ — يُورَث افتراضُ المنبع ‎1.35‎ (ويندوز/لينكس) "
        "فيُقتطَع التشكيلُ في التعليقات والسلاسل والتوثيق [TY-02]")
    assert lh < MAX_EM_VALUE, (
        f"‏`editor.lineHeight` = {lh} ‏≥ {MAX_EM_VALUE} فيُقرأ **بكسلات** لا مضاعِفَ em "
        f"(fontInfo.ts:37) — فلا يتبع حجمَ خطّ المستخدم [TY-02]")
    # **الفحصُ بعد التقريب لا قبله.** المنبع يفعل `Math.round(lineHeight)` (fontInfo.ts:43)،
    # فقيمةٌ تساوي الأرضيّةَ بالضبط تنكسر عند أحجامٍ بعينها. والمطلوبُ قيمةٌ تصمد **في كلّ
    # حجمٍ عمليّ** — وهذا سببُ اختيار ‎2.8‎ (‏= 42px عند ‎15‎ بلا كسر) دون ‎2.683‎ نفسِها.
    broken = [s for s in FONT_SIZES if round(lh * s) / s < MIN_LINE_HEIGHT]
    assert not broken, (
        f"‏`editor.lineHeight` = {lh} ينكسر بعد تقريب المنبع عند أحجام {broken} — "
        f"‏`Math.round(lh×size)/size` ينزل دون الأرضيّة المشتقّة {MIN_LINE_HEIGHT} فيُقتطَع "
        f"الحبرُ العلويُّ للعربيّة (أعلاه ‎+1.265em‎ عند «أ») [TY-02]")
    over = [s for s in FONT_SIZES if round(lh * s) / s > MIN_LINE_HEIGHT * MAX_INK_HEADROOM]
    assert not over, (
        f"‏`editor.lineHeight` = {lh} يتجاوز الحاجةَ المقيسة {MIN_LINE_HEIGHT}em بأكثرَ من "
        f"‏{round((MAX_INK_HEADROOM - 1) * 100)}٪ عند أحجام {over} — الأمانُ من القصّ يُشترى "
        f"هنا بأسطرٍ تخرج من الشاشة. الحارسُ ذو حدّين قصدًا: لولا السقفُ لَما مَنَعَ شيئًا "
        f"إلّا في اتّجاهٍ واحد [TY-02]")
    # الاشتقاقُ موثَّقٌ **بجانب القيمة وبمحتواه** لا بذكرِ رمزٍ: رقمٌ بلا سندٍ يصير ذوقًا
    # بعد ستّة أشهر، وتوكيدٌ يقنع بورودِ «TY-02» في أيّ مكانٍ لا يفحص شيئًا.
    note = str(defaults.get("_comment_line_height", ""))
    missing_note = [t for t in ("TY-02", str(MIN_LINE_HEIGHT), str(lh), "1.265", "1.35")
                    if t not in note]
    assert not missing_note, (
        "‏`_comment_line_height` لا يحمل الاشتقاقَ كاملًا (ينقصه: " + " · ".join(missing_note) +
        ") — الرقمُ بلا سندِه يصير ذوقًا [TY-02]")

    # **الاشتقاقُ يسري على كلّ سطحٍ يعرض عربيّةً بالوجه نفسِه، لا على المحرّر وحدَه.**
    # الطرفيّةُ افتراضُها المنبعيّ ‎1‎ (نصفُ ما يحتاجه الحبر)، ولوحةُ مخرجات ص هي **أشدُّ**
    # أسطحنا امتلاءً بالتشكيل — فسطرٌ ضيّقٌ فيهما يقصّ العربيّةَ في السطح الذي بُني لعرضها.
    tlh = defaults.get("terminal.integrated.lineHeight")
    assert isinstance(tlh, (int, float)) and tlh >= MIN_LINE_HEIGHT, (
        f"‏`terminal.integrated.lineHeight` = {tlh!r} دون الأرضيّة المشتقّة {MIN_LINE_HEIGHT} "
        f"— يُقصّ التشكيلُ في مخرجات الطرفيّة [TY-02]")
    _panel_src = _read(os.path.join(ROOT, "extensions", "mihrab-welcome", "output-panel.js"))
    _m = re.search(r"ARABIC_LINE_HEIGHT\s*=\s*([\d.]+)", _panel_src)
    assert _m and float(_m.group(1)) >= MIN_LINE_HEIGHT, (
        "لوحةُ مخرجات ص بلا `ARABIC_LINE_HEIGHT` ≥ الأرضيّة المشتقّة — يُقصّ التشكيلُ في "
        "أشدّ أسطحنا امتلاءً به [TY-02]")
    assert "line-height: ${ARABIC_LINE_HEIGHT}" in _panel_src, (
        "ارتفاعُ سطر لوحة المخرجات مكتوبٌ حرفيًّا لا مشتقٌّ من الثابت — خطرُ انجرافٍ صامت [TY-02]")

    gpu = defaults.get("editor.experimentalGpuAcceleration")
    assert gpu == "off", (
        f"‏`editor.experimentalGpuAcceleration` = {gpu!r} (متوقَّع 'off') — طبقةُ GPU "
        f"المنبعيّة بلا معالجة اتّجاه، ويومَ يقلب المنبعُ الافتراضَ يسقط الاتّجاهُ صامتًا [DR-05]")
    # واسمُ المفتاح مُتحقَّقٌ منه في **اللقطة المتعقَّبة** لا في `.upstream/` — تلك مُتجاهَلةٌ
    # في git وغائبةٌ عن CI، فالتحقّقُ عبرها كان يُتخطّى صامتًا حيث يلزم أكثرَ ما يلزم.
    snap = os.path.join(ROOT, "tests", "apply", "snapshot", "src", "vs", "editor", "common",
                        "config", "editorOptions.ts")
    assert os.path.isfile(snap), (
        "لقطةُ `editorOptions.ts` مفقودة — لا سبيلَ للتحقّق من اسم مفتاح GPU [DR-05]")
    assert "experimentalGpuAcceleration" in _read(snap), (
        "‏`experimentalGpuAcceleration` غيرُ موجودٍ في لقطة `editorOptions.ts` — أُعيدت "
        "تسميتُه في المنبع، فإعدادُنا صار بلا أثر [DR-05]")


@check("حجم الخطّ [VA-04]: مربوطٌ بحصيلة قياسٍ ملتزَمة، لا برقمٍ منسوخٍ في تعليق")
def _font_size_measured():
    """يحرس `editor.fontSize` — **وقد كان آخرَ رقمٍ في الطباعة بلا قياس**.

    ## الحارسُ يقرأ القياسَ، لا يصدّق التعليق
    ‏`tests/dx/arabic_legibility.measured.json` حصيلةٌ **مولَّدةٌ** من كونتورات الوجه
    (‏`arabic_legibility.py --json`). والحارسُ يشتقّ منها حدودَه. ونسخةٌ أولى منه كانت
    تطابق سلاسلَ نصّيّةً في التعليق (`"0.135"`) — أي **ترضى بنسخِ الرقم لا بصحّته**.

    ## والحدُّ الأدنى ليس أرضيّةَ الوضوح
    أرضيّةُ الوضوح المقيسة ‎12px‎، و**افتراضُ المنبع ‎14‎ يعلوها** — فحدٌّ عندها لا يمنع
    شيئًا، ويجعل الرجوعَ إلى ‎14‎ (وهو الانحدارُ الوحيدُ المحتمَل) يمرّ بلا اعتراض. فالحدُّ
    الأدنى هنا **‎15‎**: القرارُ المتّخَذُ بعد القياس. ومن أراد خفضَه يغيّر الحارسَ معه —
    وهذا هو المقصود: أن يكون التغييرُ قرارًا لا انزلاقًا.

    ## والحدُّ الأعلى مقيس
    ‏`14 ÷ bandRatio` = معادلةُ ارتفاع الحبر اللاتينيّ الكاملة. وفوقها كلفةُ أعمدةٍ بلا
    مقابلٍ بصريّ — وتقدُّمُ الوجه ‎0.70em‎ يجعل كلَّ بكسلٍ أغلى ممّا يبدو.
    """
    UPSTREAM_DEFAULT = 14      # افتراضُ المنبع على ويندوز/لينكس — نقطةُ الانطلاق لا الهدف
    DECIDED_SIZE = 15          # القرارُ بعد القياس (‏[قرارات الطباعة §٤])
    shell = os.path.join(ROOT, "extensions", "mihrab-shell", "package.json")
    if not os.path.isfile(shell):
        return
    measured_path = os.path.join(ROOT, "tests", "dx", "arabic_legibility.measured.json")
    assert os.path.isfile(measured_path), (
        "حصيلةُ القياس `tests/dx/arabic_legibility.measured.json` مفقودة — "
        "والقرارُ يستند إليها [VA-04]")
    m = json.load(open(measured_path, encoding="utf-8"))
    for key in ("solidEm", "bandRatio", "floorLegiblePx", "sha256", "unitsPerEm"):
        assert key in m, f"حصيلةُ القياس بلا «{key}» — أُنتِجت بنسخةٍ أقدم من الأداة [VA-04]"

    defaults = json.load(open(shell, encoding="utf-8")).get("contributes", {}).get(
        "configurationDefaults", {})
    size = defaults.get("editor.fontSize")
    assert isinstance(size, (int, float)), (
        "لا `editor.fontSize` افتراضيّ — يُورَث افتراضُ المنبع ‎14‎ الموضوعُ لِـ`x-height` "
        f"لاتينيّ، ونطاقُ الجسم العربيّ في الوجه المحزوم أقصرُ منه (النسبة {m['bandRatio']}) [VA-04]")
    max_size = round(UPSTREAM_DEFAULT / m["bandRatio"])
    assert DECIDED_SIZE <= size <= max_size, (
        f"‏`editor.fontSize` = {size} خارج النطاق [{DECIDED_SIZE}, {max_size}] — الحدُّ "
        f"الأدنى هو القرارُ المتّخَذ بعد القياس (والرجوعُ دونه رجوعٌ إلى افتراض المنبع "
        f"{UPSTREAM_DEFAULT} الذي قِيس عجزُه)، والأعلى `{UPSTREAM_DEFAULT} ÷ "
        f"{m['bandRatio']}` = معادلةُ ارتفاع الحبر اللاتينيّ الكاملة [VA-04]")
    # وأرضيّةُ الوضوح المقيسة لا تُخرَق مهما تغيّر القرار.
    assert size >= m["floorLegiblePx"], (
        f"‏`editor.fontSize` = {size} دون أرضيّة الوضوح المقيسة {m['floorLegiblePx']}px — "
        f"الفارقُ المميِّزُ ({m['solidEm']}em) ينزل تحت ‎1.5px‎ فتلتبس عائلاتُ الرسم [VA-04]")
    # وارتفاعُ السطر يجب أن يصمد **عند هذا الحجم بالذات** بعد تقريب المنبع.
    lh = defaults.get("editor.lineHeight")
    if isinstance(lh, (int, float)):
        floor = json.load(open(os.path.join(ROOT, "tests", "dx", "arabic_ink.measured.json"),
                              encoding="utf-8"))["composedInkEm"]
        assert round(lh * size) / size >= floor, (
            f"‏`lineHeight`={lh} مع `fontSize`={size} يعطي "
            f"{round(lh * size) / size:.3f}em بعد تقريب المنبع — دون الأرضيّة {floor} [TY-02]")
    # **الطرفيّةُ تتبع**: حجّةُ VA-04 خاصّيّةُ **وجهٍ** لا خاصّيّةُ محرّر، والوجهُ نفسُه
    # مضبوطٌ للطرفيّة. فتركُها على ‎14‎ يجعل مخرجاتِ ص العربيّةَ أصغرَ ممّا قِيس أنّه كافٍ.
    tsize = defaults.get("terminal.integrated.fontSize")
    assert tsize == size, (
        f"‏`terminal.integrated.fontSize` = {tsize!r} ≠ `editor.fontSize` = {size} — "
        f"عجزُ ارتفاع الحبر خاصّيّةُ وجهٍ لا خاصّيّةُ محرّر، والوجهُ واحدٌ في السطحين [VA-04]")
    # والسندُ **مربوطٌ بالحصيلة لا منسوخًا**: أرقامُ التعليق تُقارَن بالمقيس.
    note = str(defaults.get("_comment_font_size", ""))
    for key in ("solidEm", "bandRatio"):
        val = str(m[key])
        assert val in note, (
            f"‏`_comment_font_size` لا يذكر «{key}» = {val} كما قِيس — "
            f"السندُ الذي يخالف حصيلتَه سندٌ يكذب [VA-04]")
    assert "VA-04" in note and "arabic_legibility" in note, (
        "‏`_comment_font_size` بلا إحالةٍ إلى البند والأداة [VA-04]")
    # والقياسُ نفسُه موجودٌ وقابلٌ لإعادة التشغيل، **وحصيلتُه منسوبةٌ إلى وجهٍ بعينه**.
    assert os.path.isfile(os.path.join(ROOT, "tests", "dx", "arabic_legibility.py")), (
        "‏`tests/dx/arabic_legibility.py` مفقود — والسندُ يحيل إليه [VA-04]")
    assert len(m["sha256"]) == 64, (
        "بصمةُ الوجه المقيس ناقصة — رقمٌ بلا وجهٍ يُنسَب إليه رقمٌ معلَّق [VA-04]")


@check("اتّجاه المحرّر [DR-02]: الافتراضُ ltr ⇐ rtl تُمنَح صراحةً للغات المضمون العربيّ")
def _editor_direction_defaults_to_ltr():
    """يحرس **شكلَ** الإعداد لا محتواه: الافتراضُ يفشل نحو الأمان لا نحو الخطأ.

    كان هذا الحارسُ نفسُه يفحص قائمةَ استثناءٍ من فرضٍ عالميٍّ `rtl` — ‏سبعةَ أسماءٍ من
    ثمانيةَ عشر — و**كان أخضرَ فوق ‎٥٣‎ لغةً مشحونةً تُصيَّر يمينًا بلا حرفٍ عربيٍّ واحد**
    (‏rust · go · java · csharp · sql · lua · ruby · php · swift · dart · ini · diff · latex
    وسائرُها). وكان فيه أخضرانِ كاذبانِ فوق ذلك: `!= "rtl": return` يجعل **حذفَ المفتاح**
    يُخضِره فراغًا، ويجعل `"auto"` تمرّ صامتة — و`auto` تحت واجهةٍ عربيّةٍ **هي rtl حرفًا**
    (‏`editorOptions.ts`: `isRtlLanguage(platform.language)`)، أي أنّ أخطرَ قيمةٍ ممكنةٍ كانت
    تُنتج العطبَ نفسَه بلا صوت. والمشروعُ يعرف ذلك ومكتوبٌ عنده: `scm_input.live.mjs` يستثني
    تجربةَ `rtl ⇄ auto` لهذا السبب بالذات.

    فالحارسُ اليوم **توكيدٌ لا شرط**: لا `return` مبكرًا إلّا شاهدُ تفعيلٍ موجَب (وجودُ
    القشرة)، وخمسةُ توكيداتٍ تمسك الشكلَ كلَّه — لا أسماءً في قائمةٍ تطول.
    """
    shell = os.path.join(ROOT, "extensions", "mihrab-shell", "package.json")
    assert os.path.isfile(shell), (
        "قشرةُ محراب مفقودة — ولا حارسَ بلا محروس [DR-02]")
    defaults = json.load(open(shell, encoding="utf-8")).get("contributes", {}).get(
        "configurationDefaults", {})

    # (١) المفتاحُ موجودٌ في الجذر. غيابُه ليس «لا رأيَ لنا» بل تسليمٌ لافتراض المنبع —
    #     وهو ما كان الحارسُ القديم يقبله صامتًا.
    assert "editor.textDirection" in defaults, (
        "‏`editor.textDirection` غائبٌ عن جذر `configurationDefaults` — "
        "والصمتُ هنا تسليمٌ لافتراضِ المنبع لا حيادٌ [DR-02]")

    # (٢) وقيمتُه `ltr` **توكيدًا**. و`auto` مرفوضةٌ بالاسم: منطقُها المكتوب يتبع لغةَ
    #     الواجهة لا المستند، فتردّ rtl في محرابٍ عربيٍّ أيًّا كان الملفّ.
    root = defaults["editor.textDirection"]
    assert root == "ltr", (
        f"‏جذرُ `editor.textDirection` = {root!r} والمطلوب 'ltr'. "
        "و'auto' ليست مَخرجًا: هي تتبع لغةَ الواجهة (isRtlLanguage(platform.language)) "
        "فتساوي 'rtl' في واجهةٍ عربيّة — وهي أخطرُ من rtl لأنّها تبدو حيادًا [DR-02]")

    # (٣) و`rtl` تُمنَح صراحةً — قائمةٌ **مغلقةٌ** لسطوحِ المضمون العربيّ في هذا المشروع.
    RTL_CONTENT = ("sad", "markdown", "plaintext", "git-commit", "git-rebase", "scminput")
    missing = [lang for lang in RTL_CONTENT
               if (defaults.get(f"[{lang}]") or {}).get("editor.textDirection") != "rtl"]
    assert not missing, (
        "لغاتُ المضمون العربيّ بلا `rtl` بنطاق لغة: " + " · ".join(missing) +
        " — قلبُ الافتراض بلا منحٍ صريحٍ يسلب العربيّةَ اتّجاهَها [DR-02]")

    # (٤) ولا يعود الاتّجاهُ الجانبيُّ ينمو استثناءاتٍ من جديد: كلُّ كتلةٍ تحمل
    #     `editor.textDirection` يجب أن تكون من القائمة المغلقة وبقيمة `rtl`.
    strays = sorted(
        k[1:-1] for k, v in defaults.items()
        if k.startswith("[") and k.endswith("]") and isinstance(v, dict)
        and "editor.textDirection" in v
        and (k[1:-1] not in RTL_CONTENT or v["editor.textDirection"] != "rtl"))
    assert not strays, (
        "كتلُ اتّجاهٍ خارج القائمة المغلقة: " + " · ".join(strays) +
        " — القائمةُ لا تطول باسمٍ بعد اسم، وذاك هو العطبُ الذي قُلِب الافتراضُ لأجله [DR-02]")

    # (٥) وكلُّ اسمٍ في القائمة **معرِّفُ لغةٍ مشحونٌ فعلًا** — فالكتلةُ المطبعيّةُ ميّتةٌ
    #     بلا أثرٍ ومَن يكتبها يصدّق أنّها تعمل. يُقرأ المشحونُ من امتدادات المنبع،
    #     ويُضاف المضمَّنان في النواة بعد إثباتِ وجودِهما في المصدر لا بالثقة.
    up = os.path.join(ROOT, ".upstream", "vscode")
    ext_dir = os.path.join(up, "extensions")
    if os.path.isdir(ext_dir):
        shipped = set()
        # **ومن مصدرَين لا مصدرٍ واحد.** كان المسحُ يقرأ امتداداتِ المنبع وحدَها، و`sad`
        # لغةُ امتدادٍ من امتداداتنا نحن — لا يظهر هناك إلّا بعد أن ينسخه البناء إلى
        # شجرة المنبع. فالحارسُ كان يقيس **حالةَ بناءٍ سابق** لا حقيقةَ الشحن: يحمرّ على
        # شجرةٍ نظيفةٍ أو أثناء بناءٍ يجري، ويخضرّ لأنّ بناءً قديمًا خلّف نسخةً — والاثنان
        # لا علاقةَ لهما بصحّة القائمة. وامتداداتُ محرابٍ **مشحونةٌ بالتعريف**: تُقرأ من
        # مصدرها في المستودع. (رُصد عند ترقية المنبع إلى 1.126، على شجرةٍ أُعيد ضبطُها.)
        for base in (ext_dir, os.path.join(ROOT, "extensions")):
            if not os.path.isdir(base):
                continue
            for name in os.listdir(base):
                pkg = os.path.join(base, name, "package.json")
                if not os.path.isfile(pkg):
                    continue
                try:
                    data = json.load(open(pkg, encoding="utf-8"))
                except (ValueError, OSError):
                    continue
                for lang in (data.get("contributes") or {}).get("languages") or []:
                    if lang.get("id"):
                        shipped.add(lang["id"])
        builtins = {
            "plaintext": os.path.join(
                up, "src", "vs", "editor", "common", "languages", "modesRegistry.ts"),
            "scminput": os.path.join(
                up, "src", "vs", "workbench", "contrib", "scm", "browser", "scmInput.ts"),
        }
        for lang, src in builtins.items():
            if os.path.isfile(src) and f"'{lang}'" in open(src, encoding="utf-8").read():
                shipped.add(lang)
        assert shipped, "لم يُقرأ معرِّفُ لغةٍ واحدٍ من المنبع — الفحصُ نفسُه معطوب [DR-02]"
        ghosts = [lang for lang in RTL_CONTENT if lang not in shipped]
        assert not ghosts, (
            "أسماءٌ في قائمة rtl ليست معرِّفاتِ لغةٍ مشحونة: " + " · ".join(ghosts) +
            " — كتلةٌ ميّتةٌ تُقرأ عاملةً [DR-02]")

    # (٦) والاقترانُ الذي بدونه يصير القلبُ انحدارًا: الصناديقُ البسيطة «ودجاتٌ» تقرأ
    #     الجذرَ مباشرةً، فلولا `overrideIdentifier` لسلبها قلبُ الجذرِ اتّجاهَها —
    #     صندوقُ الالتزام أوّلَها [SC-01]. الشاهدُ في الرقعة نفسِها.
    patch = os.path.join(ROOT, "patches", "core", "030-simple-editor-rtl-input.patch")
    if os.path.isfile(patch):
        body = open(patch, encoding="utf-8").read()
        reads = [ln for ln in body.splitlines()
                 if ln.startswith("+") and "'editor.textDirection'" in ln]
        assert reads, (
            "رقعةُ ٠٣٠ لا تقرأ `editor.textDirection` للصناديق البسيطة [SC-01 · DR-02]")
        assert all("overrideIdentifier" in ln for ln in reads), (
            "‏`getSimpleEditorOptions` يقرأ `editor.textDirection` بلا `overrideIdentifier` — "
            "فيسري الجذرُ (ltr) وتُهمَل تجاوزاتُ اللغة، ويصير قلبُ الافتراض سَلبًا "
            "لصندوق الالتزام ولحقل الدردشة [SC-01 · DR-02]")
        assert "getSimpleEditorOptions(this.configurationService, 'scminput')" in body, (
            "صندوقُ الالتزام لا يمرّر معرِّفَه — فكتلةُ `[scminput]` ميّتةٌ بلا أثر "
            "[SC-01 · DR-02]")


@check("روابط لوح الحالة [DR-01]: كلّ رابط نسبيّ في milestones.md يحلّ إلى ملفٍّ موجود")
def _milestones_links_resolve():
    """لوحُ الحالة الوحيدُ لا يجوز أن يحيل إلى معدوم.

    وحّدنا المصادرَ في `milestones.md` ثمّ صار أوّلَ ما يقرؤه القادمُ الجديد — فرابطٌ ميّتٌ
    فيه أسوأُ من تناقضٍ في ثلاثة ملفّات: التناقضُ يُكتشَف، والرابطُ الميّتُ يُقرأ إهمالًا.
    """
    path = os.path.join(ROOT, "docs", "milestones.md")
    if not os.path.isfile(path):
        return
    base = os.path.dirname(path)
    dead = []
    for target in re.findall(r"\]\(([^)#]+?)(?:#[^)]*)?\)", _read(path)):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = os.path.normpath(os.path.join(base, urllib.parse.unquote(target)))
        if not os.path.exists(resolved):
            dead.append(target)
    assert not dead, (
        "روابطُ نسبيّةٌ ميّتةٌ في لوح الحالة الوحيد: " + " · ".join(dead) + " [DR-01]")


@check("جردُ الاتّجاه: كلُّ مرقِّع `patch_*_rtl.py` مذكورٌ فيه — لا مرقِّعَ بلا سطرٍ يبرّره")
def _rtl_inventory_names_every_patcher():
    """‏**اتّجاهٌ واحدٌ عمدًا**: مرقِّعٌ موجودٌ وغيرُ مذكور ⇒ فشل.

    والعكسُ لا يُفرَض: الجردُ **يذكر ما زال** أيضًا (‏`editor_rtl` صار رقعةَ نواةٍ
    `.patch`)، وذكرُ التاريخِ صدقٌ لا انجراف. فما يُمسَك هنا هو الصمتُ لا الزيادة.

    والعطبُ المقيسُ الذي وُلد منه هذا الفحص: جدولُ المقاييس كان يسرد سبعةَ أسماءٍ فيها
    `editor_rtl` (‏**غيرُ موجود**) وليس فيها `welcome_rtl` (‏**موجود**) — فالمجموعُ يصادف
    أن يبقى ‎7‎ والقائمةُ خاطئةٌ في عنصرين. مجموعٌ صحيحٌ فوق قائمةٍ كاذبة.
    """
    inv = os.path.join(ROOT, "docs", "rtl", "rtl-inventory.md")
    if not os.path.isfile(inv):
        return
    text = _read(inv)
    names = sorted(f[len("patch_"):-len(".py")] for f in os.listdir(BUILD)
                   if f.startswith("patch_") and f.endswith("_rtl.py"))
    assert names, "لا مرقِّعَ اتّجاهٍ واحدًا في build/ — الفحصُ يحرس العدم."
    # الاستشهادُ بالشولتين المائلتين لا بالورود الحرّ: «welcome_rtl_شيء» يحوي الاسمَ
    # حرفيًّا ولا يستشهد به، فمطابقةُ المتنِ الحرّ تمرّ على تسميةٍ منجرفة.
    missing = [n for n in names if ("`" + n + "`") not in text]
    assert not missing, (
        "مرقِّعاتُ اتّجاهٍ مشحونةٌ ولا يذكرها جردُ الاتّجاه: " + " · ".join(missing)
        + " — والجردُ هو دليلُ إغلاق م٣، فما لا يُذكَر فيه لا يُراجَع عند الدمج.")


@check("صدقُ لوح الحالة [DR-01]: معرّفُ مُصابٍ يُذكَر موجود · وحكمٌ سلبيٌّ مذكورٌ يقرؤه حارس")
def _milestones_claims_are_anchored():
    """‏**لا يقرأ هذا الفحصُ نثرًا ولا يحكم على 🟡 و⏳.**

    الحالاتُ نفسُها (🟢/🟡/⏳/⛔) حكمٌ بشريٌّ لا يُقاس، وفحصٌ يحاول تكذيبَها بتحليل
    جملٍ عربيّةٍ يبطل عند أوّل إعادة صياغة — وتنفيذُه الرخيصُ يقتضي **قائمةً ثانيةً
    مكتوبةً بيدنا**، أي لوحَ حالةٍ ثانيًا ينجرف. وذاك عينُ ما يمنعه [DR-01].

    فيُحرَس **ما يقبل الإرساء** وحدَه — رابطان ثنائيّا الاتّجاه:

      ‏(١) كلُّ معرّفِ مُصابٍ يذكره اللوحُ موجودٌ في `tests/meta/mutants.json`. اللوحُ يسمّي
          حرّاسًا «شُوهدوا وهم يحمرّون»؛ ومعرّفٌ يُعاد تسميتُه أو يُحذَف يُبقي على اللوح
          **دعوى مشاهدةٍ لا شاهدَ لها**.
      ‏(٢) كلُّ ملفِّ حكمٍ **سلبيٍّ** في `docs/` يُذكَر في اللوح، **ويقرؤه حارسٌ حيٌّ** في
          `tests/`. الإغلاقُ السلبيُّ قرارُ «لا يُشحَن هذا»، وقرارٌ بلا حارسٍ يُنقَض
          بيدٍ حسنةِ النيّة بعد ستّة أشهر ولا شيءَ يصرخ. والنموذجُ قائمٌ في `DAP-01`:
          `lint_patchers` يقرأ وجودَ ملفّه، فرفعُ الحكم يبدأ بحذفه.

    وشاهدُ التفعيل قبل التأكيدات: **وُجِد ما يُفحَص أصلًا**.
    """
    board_path = os.path.join(ROOT, "docs", "milestones.md")
    board = _read(board_path)
    spec = json.load(open(os.path.join(ROOT, "tests", "meta", "mutants.json"), encoding="utf-8"))
    known = {m["id"] for m in spec["mutants"]}

    # ‏(١) معرّفاتُ المُصابات — تُلتقَط من الشولات المائلة، فلا نصَّ حرًّا يُخمَّن.
    quoted = set(re.findall(r"`([a-z0-9]+(?:-[a-z0-9]+){2,})`", board))
    cited = {q for q in quoted if q in known or q.replace("-", "_") in known}
    # مرشَّحٌ يشبه معرّفَ مُصابٍ ولا يوجد: إمّا مُصابٌ أُعيدت تسميتُه، وإمّا **اسمُ ملفّ**
    # (‏`lsp-01-02` بادئةُ ملفّ الحكم). فيُستثنى ما يقابله أو يُبادِئ اسمَ ملفٍّ في الشجرة.
    SKIP = {".git", "node_modules", ".upstream", "__pycache__", ".toolchain", "public"}
    stems = set()
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP]  # التقليمُ في المكان: بلا هذا يُمسَح `.upstream`
        stems.update(os.path.splitext(f)[0] for f in files)
    ghosts = sorted(q for q in quoted - cited
                    if "." not in q
                    and not any(st == q or st.startswith(q) for st in stems)
                    and any(q.startswith(pre) for pre in {i.split("-")[0] for i in known}))
    assert not ghosts, (
        "معرّفاتُ مُصاباتٍ يذكرها لوحُ الحالة ولا وجودَ لها في mutants.json: "
        + " · ".join(ghosts) + " — دعوى «شوهد وهو يحمرّ» بلا شاهد [DR-01].")
    assert cited, (
        "لا معرّفَ مُصابٍ واحدًا في لوح الحالة — إمّا زال جدولُ الحرّاس، وإمّا تغيّرت "
        "صياغتُه فصار هذا التأكيدُ أخضرَ على العدم.")

    # ‏(٢) أحكامُ الإغلاق السلبيّ: تُعرَف من عنوان الملفّ نفسِه لا من قائمةٍ عندنا.
    judgments = []
    for name in sorted(os.listdir(os.path.join(ROOT, "docs"))):
        if not name.endswith(".md"):
            continue
        head = _read(os.path.join(ROOT, "docs", name)).splitlines()[0]
        if re.search(r"مُغلَق\S*\s+سلب", head):
            judgments.append(name)
    assert len(judgments) >= 2, (
        f"‏{len(judgments)} ملفَّ حكمٍ سلبيٍّ فقط في docs/ — والمِسطرةُ تتعرّف عليه من "
        "عنوانه الأوّل. إن تغيّرت الصياغةُ فهذا الفحصُ يحرس العدم.")
    unlinked = [n for n in judgments if n not in board and urllib.parse.quote(n) not in board]
    assert not unlinked, (
        "أحكامٌ سلبيّةٌ لا يذكرها لوحُ الحالة الوحيد: " + " · ".join(unlinked)
        + " — قرارُ «لا يُشحَن» غيرُ مرئيٍّ لمن يقرأ اللوح [DR-01].")
    unguarded = []
    for n in judgments:
        seen = False
        for base, _dirs, files in os.walk(os.path.join(ROOT, "tests")):
            if "node_modules" in base or "__pycache__" in base:
                continue
            for f in files:
                if f.endswith((".py", ".mjs", ".js", ".json", ".sh")) and n in _read(os.path.join(base, f)):
                    seen = True
                    break
            if seen:
                break
        if not seen:
            unguarded.append(n)
    assert not unguarded, (
        "أحكامٌ سلبيّةٌ **لا يقرؤها حارسٌ واحد**: " + " · ".join(unguarded)
        + " — «لا يُشحَن هذا» بلا حارسٍ يُنقَض بيدٍ حسنةِ النيّة ولا شيءَ يصرخ. "
        "اكتب حارسًا يفشل حين يُشحَن ما مُنِع، على منوال DAP-01 في هذا الملفّ.")


@check("سمتا محراب: تباين AA لكلّ رمز + تمايز اللوحة (ΔE) + اشتقاق القشرة من اللوحة")
def _theme_contrast():
    ext = os.path.join(ROOT, "extensions", "mihrab-themes")
    if not os.path.isdir(ext):
        return  # لا إضافة سمات في هذا الفرع — تخطٍّ
    pkg = json.load(open(os.path.join(ext, "package.json"), encoding="utf-8"))
    for t in pkg.get("contributes", {}).get("themes", []):
        tp = os.path.join(ext, *t["path"].lstrip("./").split("/"))
        td = json.load(open(tp, encoding="utf-8"))
        label = td.get("name", t["path"])
        bg = td["colors"]["editor.background"]
        # العتبة تتبع نوع السمة: AAA لعاليتَي التباين، AA لغيرهما.
        is_hc = td.get("type") in HC_TYPES
        thr, thr_name = (AAA_MIN, "WCAG AAA") if is_hc else (AA_MIN, "WCAG AA")

        # (1) تباين — كلّ لون رمزٍ نحويّ ودلاليّ على خلفيّة محرّره الفعليّة.
        def _assert_aa(color, what, thr=thr, thr_name=thr_name):
            ratio = _contrast(color, bg)
            assert ratio >= thr, (
                f"[{label}] {what} = {color} على {bg} تباينه {ratio:.2f}:1 < {thr}:1 "
                f"({thr_name}) — أغمِق/فتِّح اللون في gen_themes.py")

        for rule in td["tokenColors"]:
            fg = rule.get("settings", {}).get("foreground")
            if fg:
                _assert_aa(fg, f"نطاق نحويّ «{rule.get('name')}»")
        for kind, val in td.get("semanticTokenColors", {}).items():
            fg = val.get("foreground") if isinstance(val, dict) else val
            if fg:
                _assert_aa(fg, f"رمز دلاليّ «{kind}»")

        # (2) تمايز اللوحة — الفئات الخمس الدلاليّة متباعدة ΔE76 ≥ DE_MIN، وإلّا انهارت
        #     اللوحة إلى كتل متشابهة وضاع معنى التلوين (الانحدار الذي أوقعته لوحة سابقة).
        sem = td.get("semanticTokenColors", {})
        present = {k: sem[k] for k in SEMANTIC_KINDS if isinstance(sem.get(k), str)}
        assert len(present) == len(SEMANTIC_KINDS), (
            f"[{label}] فئات دلاليّة مفقودة من semanticTokenColors: "
            f"{sorted(set(SEMANTIC_KINDS) - set(present))}")
        kinds = sorted(present)
        for i, a in enumerate(kinds):
            for b in kinds[i + 1:]:
                d = _delta_e(present[a], present[b])
                assert d >= DE_MIN, (
                    f"[{label}] «{a}» ({present[a]}) و«{b}» ({present[b]}) متقاربان: "
                    f"ΔE76={d:.1f} < {DE_MIN} — لونان لا يُميَّزان أثناء القراءة؛ "
                    f"باعِد بينهما في gen_themes.py")

        # (3) اشتقاق القشرة من اللوحة — الذهب/الأزرق في عناصر بيئة العمل يجب أن يساويا
        #     نبرتَي «مفتاح»/«نوع» حرفيًّا. تُمسَك بذلك القشرةُ التي تتخلّف عن إعادة تلوين
        #     اللوحة (انجراف حدث فعلًا: بقي #785006/#0B626E من لوحة سابقة بعد تبديلها).
        colors = td["colors"]
        # (2ب) سمة تباين عالٍ بلا `contrastBorder` ليست عالية التباين فعلًا: VS Code يرسم
        #      الحدود حول العناصر انطلاقًا منه؛ بدونه تعود القشرة تعتمد فروق خلفيّة خافتة.
        if is_hc:
            for req in ("contrastBorder", "contrastActiveBorder"):
                assert colors_of(td).get(req), (
                    f"[{label}] سمة عالية التباين بلا «{req}» — لن تُرسَم الحدود "
                    f"فتفقد السمة سبب وجودها")

        for ui_key, kind in (("list.highlightForeground", "keyword"),
                             ("progressBar.background", "keyword"),
                             ("textLink.foreground", "type")):
            if ui_key in colors and kind in present:
                assert colors[ui_key].lower() == present[kind].lower(), (
                    f"[{label}] {ui_key} = {colors[ui_key]} ≠ لون «{kind}» ({present[kind]}) — "
                    f"القشرة منجرفة عن اللوحة؛ اشتقّها في gen_themes.py")


# ───────────── L0-9: سمة أيقونات محراب ─────────────
@check("سمة أيقونات محراب: JSON صالح، خرائط ص/مجلّد/عامّ، SVG موجود، مُعرّف افتراضيّ")
def _icon_theme():
    ext = os.path.join(ROOT, "extensions", "mihrab-icons")
    if not os.path.isdir(ext):
        return  # لا إضافة أيقونات في هذا الفرع — تخطٍّ
    pkg = json.load(open(os.path.join(ext, "package.json"), encoding="utf-8"))
    contrib = pkg.get("contributes", {})
    icons = contrib.get("iconThemes", [])
    assert icons, "لا iconThemes في الحزمة"
    ids = {i.get("id") for i in icons}
    # الافتراضيّة (سمات الأيقونات تُفتَّح بالـid لا الـlabel):
    default = contrib.get("configurationDefaults", {}).get("workbench.iconTheme")
    assert default in ids, f"سمة الأيقونات الافتراضيّة «{default}» ليست من ids {ids}"
    for it in icons:
        assert it.get("id") and it.get("label") and it.get("path"), f"عقد سمة أيقونات ناقص: {it}"
        tp = os.path.join(ext, *it["path"].lstrip("./").split("/"))
        assert os.path.isfile(tp), f"ملفّ سمة الأيقونات مفقود: {it['path']}"
        td = json.load(open(tp, encoding="utf-8"))
        defs = td.get("iconDefinitions", {})
        assert defs, "لا iconDefinitions"
        # الافتراضات الأساسيّة موجودة (ملفّ + مجلّد) وإلّا فالملفّات غير المعرّفة بلا أيقونة:
        assert td.get("file") in defs, "لا أيقونة ملفّ افتراضيّة (file)"
        assert td.get("folder") in defs, "لا أيقونة مجلّد افتراضيّة (folder)"
        # ملفّ ص مخرَّط (بالامتداد ص أو بلغة sad):
        sad_ref = td.get("fileExtensions", {}).get("ص") or td.get("languageIds", {}).get("sad")
        assert sad_ref in defs, "ملفّ ص غير مخرَّط لأيقونة (fileExtensions.ص / languageIds.sad)"

        # **كلّ** مرجع أيقونة (base + light + highContrast، بما فيه folderExpanded) له تعريف —
        # يمنع مرجعًا مكسورًا يمرّ صامتًا (يرتدّ لأيقونة أخرى/يختفي).
        def _refs(block):
            r = set()
            for k in ("file", "folder", "folderExpanded", "rootFolder", "rootFolderExpanded"):
                if block.get(k):
                    r.add(block[k])
            for m in ("fileExtensions", "fileNames", "folderNames",
                      "folderNamesExpanded", "languageIds"):
                r.update((block.get(m) or {}).values())
            return r
        refs = _refs(td)
        for variant in ("light", "highContrast"):
            if isinstance(td.get(variant), dict):
                refs |= _refs(td[variant])
        for r in refs:
            assert r in defs, f"مرجع أيقونة «{r}» بلا تعريف في iconDefinitions ({it['path']})"
        # كلّ iconPath يشير لملفّ SVG موجود وصالح الترويسة:
        for name, d in defs.items():
            ip = d.get("iconPath")
            assert ip, f"iconDefinition «{name}» بلا iconPath"
            svg = os.path.join(ext, *ip.lstrip("./").split("/"))
            assert os.path.isfile(svg), f"أيقونة SVG مفقودة: {ip}"
            head = _read(svg).lstrip()
            assert head.startswith("<?xml") or head.startswith("<svg"), f"ليس SVG صالحًا: {ip}"

        # ── [AR-06] اتّساع التغطية: السمة **افتراضيّة**، فتغطيتها الضيّقة تجعل مستكشف محراب
        # أقلّ إفادةً من المحرّر القياسيّ (‏seti). كانت تُخرِّط نوعًا واحدًا (ص) فتصير الشجرة
        # صفًّا من صفحاتٍ متطابقة. هذا الحدّ الأدنى يمنع الارتداد إلى تلك الحال.
        MIN_EXTENSIONS = 30
        MUST_COVER = ("ص", "json", "md", "py", "svg", "log")   # عائلة واحدة على الأقلّ من كلٍّ
        fe = td.get("fileExtensions", {})
        assert len(fe) >= MIN_EXTENSIONS, (
            f"سمة الأيقونات تُخرِّط {len(fe)} امتدادًا فقط (الحدّ {MIN_EXTENSIONS}) — الشجرة "
            f"تصير صفحاتٍ متطابقة وتضيع أسرع إشارة بصريّة في المستكشف [AR-06]")
        for e in MUST_COVER:
            assert e in fe, f"امتداد «{e}» غير مخرَّط — عائلة كاملة بلا أيقونة [AR-06]"
        # تكافؤ الأرضيّتين: كلّ ما تخرّطه الداكنة تخرّطه الفاتحة (وإلّا سقطت الفاتحة للعامّ).
        lfe = (td.get("light") or {}).get("fileExtensions", {})
        if lfe:
            missing_light = set(fe) - set(lfe)
            assert not missing_light, \
                f"امتدادات مخرَّطة في الداكنة وحدها: {sorted(missing_light)[:6]} [AR-06]"

    # ── المولّد مصدر الحقيقة: الملفّات المشتقّة تحمل رأسه، ولا تُحرَّر يدويًّا (اصطلاح
    # مقتطفات ص نفسه). ‏sad.svg مستثنًى صراحةً — علامة الهوية مكتوبة يدويًّا لا مشتقّة.
    gen = os.path.join(ext, "gen_icons.py")
    if os.path.isfile(gen):
        BANNER = "مولَّد بـgen_icons.py"
        assert BANNER in _read(gen), "رأس المولَّد غير معرَّف في gen_icons.py [AR-06]"
        for fn in sorted(os.listdir(os.path.join(ext, "icons"))):
            if fn.startswith("sad") or fn.startswith("file") or fn.startswith("folder"):
                continue  # أصولٌ يدويّة سابقة للمولّد (الهوية + الافتراضيّان)
            assert BANNER in _read(os.path.join(ext, "icons", fn)), \
                f"‏{fn} بلا رأس المولَّد — حُرِّر يدويًّا فسيُدهَس عند أوّل توليد [AR-06]"


# ───────────── L0-7: أصول الهوية البصريّة (أيقونة التطبيق) ─────────────
@check("أصول الهوية موجودة وسليمة، وكتلة الحقن تنسخها فعلًا")
def _branding_assets():
    # كلّ أصل معلَن موجود؛ والـico ترويسته صالحة (00 00 01 00) — دون اعتماد PIL في CI.
    for src in {s for s, _t in M.BRANDING_ASSETS}:
        p = os.path.join(ROOT, src)
        assert os.path.isfile(p), f"أصل هوية مفقود: {src} (شغّل assets/branding/gen_ico.py)"
        if src.endswith(".ico"):
            with open(p, "rb") as f:
                head = f.read(4)
            assert head == b"\x00\x00\x01\x00", f"ترويسة ICO غير صالحة في {src}: {head!r}"
            assert os.path.getsize(p) > 2000, f"{src} صغير بشكل مريب (ربّما تالف)"
    # كتلة الحقن تنسخ كلّ هدف فعلًا. **جرّد أسطر التعليق** قبل الفحص: تعليق يذكر المسار
    # (winIcon=resources/win32/code.ico) يُرضي فحص السلسلة زورًا حتى لو حُذف أمر cp الفعليّ.
    src_lines = _read(os.path.join(BUILD, "patch_bundle_extensions.py")).splitlines()
    code_only = "\n".join(ln for ln in src_lines if not ln.lstrip().startswith("#"))
    for _src, target in M.BRANDING_ASSETS:
        assert f"cp -f ../.mihrab-branding/" in code_only and f"resources/win32/{target}" in code_only, \
            f"كتلة الحقن لا تنسخ {target} إلى resources/win32/ (أمر cp فعليّ) — أُزيل ربط الهوية؟"


@check("أصول SVG للأسطح (رأس التطبيق + خلفية المحرّر): موجودة وسليمة، وكتلة الحقن تنسخها للوجهة الفعليّة")
def _branding_svg_assets():
    import re
    import xml.dom.minidom
    src_lines = _read(os.path.join(BUILD, "patch_bundle_extensions.py")).splitlines()
    code_only = chr(10).join(ln for ln in src_lines if not ln.lstrip().startswith("#"))
    cp_lines = [ln for ln in code_only.splitlines() if "cp -f" in ln]
    loop_m = re.search("for _lp in ([A-Za-z ]+)", code_only)  # كلمات المتغيّرات فقط (يقف عند ; أو do)
    q = chr(34)
    for src, dest in M.BRANDING_SVG_ASSETS:
        ap = os.path.join(ROOT, src)
        assert os.path.isfile(ap), f"أصل SVG مفقود: {src}"
        body = _read(ap)
        xml.dom.minidom.parseString(body.encode("utf-8"))  # يرفع عند XML غير سليم
        # مِجَسّ ASCII في **مصدر** الأصل يميّز شعار محراب عن أصل VSCodium. (svgo يجرّده في الحزمة ⇒
        # تحقّق المخرَج بتوقيع لونيّ في L2 _surface_svgs لا بهذا المِجَسّ.)
        assert ("id=" + q + "mihrab-arch" + q) in body, f"{src} لا يحمل مِجَسّ mihrab-arch (ليس شعار محراب؟)"
        base = os.path.basename(dest)
        # نفحص الوجهة الفعليّة في سطر cp حقيقيّ (لا مجرّد ظهور الاسم في سطر الفحص القاتل).
        if base.startswith("letterpress-"):
            variant = base[len("letterpress-"):-len(".svg")]  # dark/light/hcDark/hcLight
            templ = os.path.dirname(dest) + "/letterpress-${_lp}.svg"
            assert any(templ in ln for ln in cp_lines), f"لا سطر cp مُعامَل ينسخ letterpress إلى {os.path.dirname(dest)}"
            assert loop_m and variant in loop_m.group(1).split(), f"المتغيّر {variant} غير مُغطّى في حلقة for _lp"
        else:
            assert any(dest in ln for ln in cp_lines), f"لا سطر cp ينسخ إلى الوجهة الحرفيّة {dest} (أُزيل ربط سطح الهوية؟)"


@check("أصول مساحة sessions: موجودة وسليمة، وكتلة الحقن تنسخها للوجهة الفعليّة")
def _branding_sessions_assets():
    import xml.dom.minidom
    src_lines = _read(os.path.join(BUILD, "patch_bundle_extensions.py")).splitlines()
    code_only = chr(10).join(ln for ln in src_lines if not ln.lstrip().startswith("#"))
    cp_lines = [ln for ln in code_only.splitlines() if "cp -f" in ln]
    import re as _re
    fatal_m = _re.search("for _sasset in ([^;]+)", code_only)  # قائمة الفحص القاتل ضدّ الأصل المفقود
    fatal_list = fatal_m.group(1).split() if fatal_m else []
    q = chr(34)
    for src, dest in M.BRANDING_SESSIONS_ASSETS:
        ap = os.path.join(ROOT, src)
        assert os.path.isfile(ap), f"أصل sessions مفقود: {src}"
        body = _read(ap)
        if src.endswith(".svg"):
            xml.dom.minidom.parseString(body.encode("utf-8"))
            assert ("id=" + q + "mihrab-arch" + q) in body, f"{src} بلا مِجَسّ mihrab-arch"
        else:  # vscodeLogoPath.ts: مسار محراب المطموس لا مسار VSCodium
            assert "M14 88" in body, f"{src} لا يحمل مسار قوس محراب (M14 88)"
            assert "M65.566" not in body, f"{src} ما زال يحمل مسار شعار VSCodium (M65.566)"
        assert any(dest in ln for ln in cp_lines), f"لا سطر cp ينسخ إلى وجهة sessions {dest}"
        assert os.path.basename(dest) in fatal_list, f"basename {os.path.basename(dest)} غائب عن قائمة الفحص القاتل for _sasset"

@check("الملفّ التكميليّ للترجمة: JSON صالح، قيم نصّيّة غير فارغة، تكافؤ الحوامل، ووصل الخبز به")
def _ar_supplement():
    import re as _re
    supp_path = os.path.join(BUILD, "mihrab_ar_supplement.json")
    assert os.path.isfile(supp_path), "الملفّ التكميليّ mihrab_ar_supplement.json مفقود"
    data = json.load(open(supp_path, encoding="utf-8"))
    assert isinstance(data, dict), "الملفّ التكميليّ ليس كائن JSON"
    ph = _re.compile(r"\{\d+\}")
    mnem = _re.compile(r"&&(.)")
    # محارف تنسيق غير مرئيّة تلوّث النصّ العربيّ بصمت (لا مكان لها في هذه السلاسل):
    # واصلة ليّنة، مسافة/واصل/فاصل صفريّ العرض، واصل الكلمات، BOM. (ترميز صريح — لا محارف
    # غير مرئيّة في الكود نفسه.)
    INVISIBLE = {
        0x00AD: "SOFT-HYPHEN", 0x200B: "ZWSP", 0x200C: "ZWNJ",
        0x200D: "ZWJ", 0x2060: "WORD-JOINER", 0xFEFF: "BOM",
    }
    for en, ar in data.items():
        assert isinstance(en, str) and isinstance(ar, str) and ar, f"زوج غير نصّيّ/فارغ: {en!r}"
        for cp, nm in INVISIBLE.items():
            assert chr(cp) not in ar, f"محرف غير مرئيّ ({nm}) في الترجمة: {en!r}"
        # تكافؤ الحوامل {n} كـmultiset (لا set) — يمسك اختلال العدد المكرَّر ({0}...{0}).
        assert sorted(ph.findall(en)) == sorted(ph.findall(ar)), \
            f"اختلال حوامل بين الإنجليزيّة والعربيّة: {en!r}"
        # تكافؤ بنية الماركداون/المعرّفات الحرفيّة: رابط `](`، backtick، وبادئة الرابط http.
        for tok in ("](", "`", "http"):
            assert en.count(tok) == ar.count(tok), \
                f"اختلال بنية «{tok}» بين الإنجليزيّة والعربيّة: {en!r}"
        # علامة اختصار &&: يجب بقاء حرف الوصول اللاتينيّ نفسه (لا مجرّد وجود &&).
        assert {c.lower() for c in mnem.findall(en)} == {c.lower() for c in mnem.findall(ar)}, \
            f"اختلّ حرف اختصار && بين الإنجليزيّة والعربيّة: {en!r}"
    # الخبز يجب أن يشير إلى اسم الملفّ التكميليّ (وإلّا فالوصل مقطوع).
    bake_src = _read(os.path.join(BUILD, "bake_nls_arabic.py"))
    assert "mihrab_ar_supplement.json" in bake_src, "bake_nls_arabic.py لا يشير إلى الملفّ التكميليّ"


@check("تكميليّ بيانات الامتدادات: JSON صالح، قيم نصّيّة، تكافؤ الحوامل/البنية، ووصل الحقن به")
def _ext_nls_supplement():
    import re as _re
    supp_path = os.path.join(BUILD, "mihrab_ext_nls_ar.json")
    assert os.path.isfile(supp_path), "الملفّ التكميليّ mihrab_ext_nls_ar.json مفقود"

    # كشف المفاتيح المكرّرة عند المصدر: json.load يحتفظ بآخر قيمة صمتًا فيُسقِط ترجمةً
    # (نزاهة بيانات — 1139 زوجًا محرَّرًا يدويًّا). object_pairs_hook يمسكها قبل الابتلاع.
    def _no_dups(pairs):
        seen = {}
        for k, v in pairs:
            assert k not in seen, f"مفتاح مكرّر في تكميليّ الامتدادات: {k!r}"
            seen[k] = v
        return seen
    data = json.load(open(supp_path, encoding="utf-8"), object_pairs_hook=_no_dups)
    assert isinstance(data, dict), "تكميليّ الامتدادات ليس كائن JSON"
    # حوامل بأسلوبين: {0} و${name} (سلاسل package.nls تستعمل كليهما).
    ph = _re.compile(r"\{\d+\}|\$\{[^}]*\}")
    mnem = _re.compile(r"&&(.)")
    INVISIBLE = {
        0x00AD: "SOFT-HYPHEN", 0x200B: "ZWSP", 0x200C: "ZWNJ",
        0x200D: "ZWJ", 0x2060: "WORD-JOINER", 0xFEFF: "BOM",
    }
    for en, ar in data.items():
        if en.startswith("//"):  # تعليقات مسموحة، تُتخطّى في الحقن
            continue
        assert isinstance(en, str) and isinstance(ar, str) and ar, f"زوج غير نصّيّ/فارغ: {en!r}"
        for cp, nm in INVISIBLE.items():
            assert chr(cp) not in ar, f"محرف غير مرئيّ ({nm}) في الترجمة: {en!r}"
        # تكافؤ الحوامل كـmultiset (يمسك اختلال العدد المكرَّر).
        assert sorted(ph.findall(en)) == sorted(ph.findall(ar)), \
            f"اختلال حوامل بين الإنجليزيّة والعربيّة: {en!r}"
        # تكافؤ بنية الماركداون/المعرّفات الحرفيّة: رابط `](`، backtick، بادئة http،
        # ومرجع الأمر command: (روابط الإجراءات في أوصاف Git يجب ألّا تُترجَم بنيتها).
        for tok in ("](", "`", "http", "command:"):
            assert en.count(tok) == ar.count(tok), \
                f"اختلال بنية «{tok}» بين الإنجليزيّة والعربيّة: {en!r}"
        # تكافؤ حرف اختصار && (mnemonic) كما في حارس النواة _ar_supplement.
        assert {c.lower() for c in mnem.findall(en)} == {c.lower() for c in mnem.findall(ar)}, \
            f"اختلّ حرف اختصار && بين الإنجليزيّة والعربيّة: {en!r}"
    # الحقن يجب أن يشير إلى اسم الملفّ التكميليّ (وإلّا فالوصل مقطوع).
    inj_src = _read(os.path.join(BUILD, "patch_extension_nls.py"))
    assert "mihrab_ext_nls_ar.json" in inj_src, "patch_extension_nls.py لا يشير إلى الملفّ التكميليّ"


@check("تطبيع الهويّة: الوحدة موصولةٌ بكلّ مسارٍ يُكتَب فيه نصٌّ مُصيَّر، والمسارُ المقروء مقصود")
def _brand_wiring():
    assert os.path.isfile(os.path.join(BUILD, "mihrab_brand.py")), \
        "وحدة تطبيع الهويّة مفقودة: build/mihrab_brand.py"
    # النصُّ المُصيَّر يُكتَب في مسارين اثنين لا غير؛ كلاهما يجب أن يمرّ بالتطبيع، وإلّا
    # تسرّب اسمُ التوزيعة الأمّ من المسار المنسيّ — وهو بعينه ما وقع قبل [م1].
    for f in ("bake_nls_arabic.py", "patch_extension_nls.py"):
        src = _read(os.path.join(BUILD, f))
        assert "mihrab_brand" in src, f"{f} لا يستدعي تطبيع الهويّة (تسرّبُ اسمِ المنبع)"
        assert "rebrand" in src, f"{f} يستورد التطبيع ولا يستعمله"
    # **الملفّ المقروء**: حين لا حزمةَ لغةٍ مسجَّلة يقرأ المنبعُ package.nls.json وحدَه
    # (‏extensionsScannerService.ts). كتابةٌ في غيره وحدَه = صفرُ تعريبٍ بمقياسٍ يقول 100%.
    inj = _read(os.path.join(BUILD, "patch_extension_nls.py"))
    assert '_write_json_atomic(pnls, ar_map)' in inj, \
        "الحقن لا يكتب في package.nls.json — وهو الملفّ الوحيد الذي يُقرأ بلا حزمة لغة"
    # بوّابةٌ واحدةٌ يستدعيها البناءُ والاختبار: لا عتبتان تفترقان ولا grep يشهد لبايت.
    assert "def verify(" in inj, "المرقِّع بلا بوّابةِ حكمٍ على المشحون (verify)"
    sh = _read(os.path.join(BUILD, "build.sh"))
    assert "patch_extension_nls.py\" --verify" in sh, \
        "build.sh لا يستدعي بوّابةَ تعريب بيانات الامتدادات على المشحون"
    assert "vscodium" in sh and "تسرّبُ هويّة" in sh, \
        "build.sh بلا حرسٍ على تسرّب اسم التوزيعة الأمّ في المخبوز"
    # ‏`\|` امتدادُ GNU: grep البِسْديّ (macOS) يقرؤه حرفيًّا فيُفشِل بناءً سليمًا. مرّةً
    # وقعنا فيه في الحرس نفسِه الذي حذّر تعليقُه من فخّ PCRE — فليمسكه حارسٌ لا ذاكرة.
    for _ln in sh.splitlines():
        _code = _ln.split("#", 1)[0]           # التعليقاتُ تشرح الفخَّ ولا تقع فيه
        assert not ("grep" in _code and "\\|" in _code), \
            f"نمطُ grep يستعمل \\| (امتدادُ GNU) — يفشل على macOS: {_ln.strip()[:70]}"


# ───────────── L0-15: امتداد ترحيب محراب (الجولة + أوامر الإعداد الأوّل) ─────────────
@check("امتداد ترحيب محراب: JSON صالح، أوامر ↔ JS متطابقة، خطوات الجولة تشير لوسائط موجودة")
def _welcome_ext():
    ext = os.path.join(ROOT, "extensions", "mihrab-welcome")
    if not os.path.isdir(ext):
        return  # لا امتداد ترحيب في هذا الفرع — تخطٍّ
    pkg = json.load(open(os.path.join(ext, "package.json"), encoding="utf-8"))
    contrib = pkg.get("contributes", {})

    # (١) نقطة الدخول main موجودة فعلًا (وإلّا فالأوامر لن تُفعَّل).
    main_rel = pkg.get("main")
    assert main_rel, "لا حقل main في امتداد الترحيب (الأوامر تحتاج نقطة دخول JS)"
    main_path = os.path.join(ext, *main_rel.lstrip("./").split("/"))
    assert os.path.isfile(main_path), f"ملفّ main مفقود: {main_rel}"
    js = _read(main_path)
    # نقطة الدخول تصدّر activate (وإلّا لن يُفعَّل الامتداد إطلاقًا).
    assert "module.exports" in js and "function activate" in js, \
        "نقطة دخول الامتداد لا تصدّر activate (module.exports/function activate)"
    # صحّة نحو JS إن توفّر node (لا يُفشِل حين غيابه — L0 صالح لـCI بلا اعتماد).
    node = shutil.which("node")
    if node:
        r = subprocess.run([node, "--check", main_path], capture_output=True, text=True)
        assert r.returncode == 0, f"خطأ نحويّ في {main_rel}:\n{r.stderr.strip()}"

    # (١ب) الفتح التلقائيّ للجولة يعتمد على تنشيط عند اكتمال الإقلاع؛ بدونه لا تظهر لمستخدم عائد.
    assert "onStartupFinished" in pkg.get("activationEvents", []), \
        "activationEvents لا يحوي onStartupFinished — الجولة لن تُفتَح تلقائيًّا أوّل مرّة"
    assert "maybeShowWelcome" in js and "openWalkthrough" in js, \
        "لا منطق فتح تلقائيّ للجولة (maybeShowWelcome/openWalkthrough) في نقطة الدخول"

    # (١ج) تشغيل ملفّ ص يجب أن يمرّ بالمسار المحلول (المدمج ثمّ PATH) لا باسم ثابت مباشر،
    #      وإلّا ينكسر ربط الثنائيّ المدمج ولا يعمل التشغيل دون تثبيت على PATH.
    #      (أنماط متسامحة مع المسافات كي لا تنكسر بإعادة تنسيق. [N1])
    import re as _re
    # (١ب٢) كلّ أمرٍ معلَنٍ مُسجَّل — كان هذا الحارسُ لنِبراس وحدَه، فأمرٌ يُعلَن في مانيفست
    #       الترحيب بلا `registerCommand` كان يمرّ أخضرَ ويظهر في لوحة الأوامر ثمّ يرمي
    #       «command not found» عند النقر. التسجيلُ قد يمرّ بثابتٍ مسمّى فنحلّه.
    _wcmds = {c.get("command") for c in (pkg.get("contributes", {}).get("commands") or [])}
    assert _wcmds, "لا أوامر معلَنة في امتداد الترحيب"
    # التسجيلُ قد يُنقَل إلى وحدةٍ مستقلّة (نمطُ نِبراس «التسجيل الموزّع»)، فنمسح كلَّ ملفّات
    # JS لا نقطةَ الدخول وحدَها — وإلّا يُسقِط أوّلُ نقلٍ الفحصَ أحمرَ كاذبًا.
    #       والثوابتُ تُجمَع **عبر ملفّات الامتداد كلِّها** لا لكلّ ملفٍّ وحدَه، ويُحَلّ معها
    #       نمطُ الإسناد من وحدةٍ أخرى (`const A = mod.B;`): المستودعُ يضع معرّفَ الأمر في
    #       الوحدة التي تنفّذه ويسنده في نقطة الدخول (مصدرُ حقيقةٍ واحد)، فحصرُ الحلّ في
    #       الحرفيّة داخل الملفّ كان سيُجبِر على تكرار السلسلة — وهو ما يمنعه المستودعُ نفسُه.
    #       والثوابتُ **مفهرَسةٌ بالملفّ** لا مسطَّحةٌ عبره: التسطيحُ يجعل آخرَ ملفٍّ يفوز
    #       صامتًا، وفي الشجرة الحاليّة `STATE_KEY` مُعرَّفٌ بقيمتين مختلفتين في ملفّين.
    #       لا يضرّ اليومَ (ليس وسيطَ `registerCommand`)، لكنّ أوّلَ اسمٍ يتصادم ويكون وسيطًا
    #       يجعل الحارسَ يصادق على خريطةٍ خاطئة. الحلُّ: ابدأ من ملفّ الاستدعاء ثمّ اسقط.
    _wreg = set()
    _wfiles = sorted(f for f in os.listdir(ext) if f.endswith(".js"))
    _wconst = {}   # (ملفّ، اسم) ⇒ حرفيّة
    _walias = {}   # (ملفّ، اسم) ⇒ اسمٌ في وحدةٍ أخرى
    _wmods = {}    # (ملفّ، اسمُ الوحدة المستوردة) ⇒ ملفُّها
    for _jf in _wfiles:
        _js = _read(os.path.join(ext, _jf))
        for _n, _v in _re.findall(r'const\s+([A-Za-z_$][\w$]*)\s*=\s*"([^"]+)"', _js):
            _wconst[(_jf, _n)] = _v
        # إسنادٌ من وحدةٍ أخرى بصيغتَيه الشائعتين: `const A = mod.B;` و`const { B: A } = require(…)`.
        # الثانيةُ اصطلاحُ JS الغالبُ لإعادة التسمية عند التفكيك، وإغفالُها كان يجعل الحارسَ
        # يحمرّ كاذبًا على كودٍ سليم — وحارسٌ يكذب أحمرَ يُعلَّم تجاهُلُه كما يُعلَّم الأخضرُ الكاذب.
        # كلُّ إسنادٍ يحمل **ملفَّ مصدره** حين يُعرَف: بلا ذلك يُحَلّ `OPEN_CMD` من أوّل ملفٍّ
        # أبجديًّا لا من الوحدة المستورَدة — وفي هذه الشجرة يوجد `OPEN_CMD` بقيمتين مختلفتين
        # فعلًا (‏`vscode.open` في نقطة الدخول، و`mihrab.openHelp` في لوحة المساعدة).
        # ‏**ووحدةُ المصدر تُحَلّ من الـrequire لا تُترَك مجهولة**: كان هذا الفرعُ يسجّل
        # ‏`None` مصدرًا، فيسقط الحلُّ إلى «أوّلُ ملفٍّ فيه اسمٌ مطابق». ولمّا صار
        # ‏`SHOW_AGAIN_CMD` مُصدَّرًا من وحدتَي إشعارٍ (الطرفيّة والمقارنة) حَلّ الاسمُ
        # الواحدُ إلى قيمة الأخرى فاحمرّ الحارسُ على **الأمر القديم السليم** — والعطبُ
        # نفسُه الموصوف أعلاه لصيغة التفكيك، بصيغةٍ لم تُغطَّ.
        _wmod = dict(_re.findall(
            r'const\s+([A-Za-z_$][\w$]*)\s*=\s*require\(\s*["\']\./([^"\']+)["\']\s*\)', _js))
        for _n, _obj, _p in _re.findall(
                r'const\s+([A-Za-z_$][\w$]*)\s*=\s*([A-Za-z_$][\w$]*)\.([A-Za-z_$][\w$]*)\s*;', _js):
            _walias[(_jf, _n)] = (_p, _wmod.get(_obj))
        # ‏`const { B: A } = require("./mod.js")` — اصطلاحُ JS الغالبُ لإعادة التسمية عند
        # التفكيك. وإغفالُه كان يجعل الحارسَ يحمرّ كاذبًا على كودٍ سليم، وحارسٌ يكذب أحمرَ
        # يُعلَّم تجاهُلُه كما يُعلَّم الأخضرُ الكاذب.
        for _inner, _src in _re.findall(
                r'const\s*\{([^}]*)\}\s*=\s*require\(\s*["\']\./([^"\']+)["\']\s*\)', _js):
            for _p, _n in _re.findall(r'([A-Za-z_$][\w$]*)\s*:\s*([A-Za-z_$][\w$]*)', _inner):
                _walias[(_jf, _n)] = (_p, _src)

    def _resolve_const(name, home):
        """حرفيّةُ ثابتٍ: من ملفّه أوّلًا، ثمّ عبر الإسناد (بملفّ مصدره)، ثمّ من بقيّة الملفّات."""
        if (home, name) in _wconst:
            return _wconst[(home, name)]
        # ‏`registerCommand(mod.PROP, …)` — تعبيرُ عضوٍ **في موضع الوسيط مباشرةً** بلا ثابتٍ
        # وسيطٍ مسمًّى. كان الحارسُ يعمى عنه فيحمرّ على كودٍ سليم؛ وحارسٌ يكذب أحمرَ يُعلَّم
        # تجاهُلُه كما يُعلَّم الأخضرُ الكاذب. يُحَلّ **بملفّ الوحدة المستوردة أوّلًا**، لأنّ
        # السقوطَ إلى «أوّل اسمٍ مطابق» هو العطبُ الموصوفُ أعلاه بعينه.
        if "." in name:
            _obj, _, _prop = name.partition(".")
            _src = _wmods.get((home, _obj))
            if _src and (_src, _prop) in _wconst:
                return _wconst[(_src, _prop)]
            for (_f3, _n3), _v3 in _wconst.items():
                if _n3 == _prop:
                    return _v3
        alias = _walias.get((home, name))
        if alias:
            prop, src = alias
            # **ملفُّ المصدر أوّلًا** حين يُعرَف — وإلّا فُضّ الاشتباكُ بأوّل ملفٍّ أبجديًّا،
            # وهو خطأٌ صامتٌ حين يتصادم اسمُ ثابتٍ بين وحدتين (وقد تصادم فعلًا).
            if src and (src, prop) in _wconst:
                return _wconst[(src, prop)]
            for (_f, _n), _v in _wconst.items():
                if _n == prop and (not src or _f != home):
                    return _v
        for (_f, _n), _v in _wconst.items():
            if _n == name:
                return _v
        return None

    for _jf in _wfiles:
        _js = _read(os.path.join(ext, _jf))
        for _arg in _re.findall(r"registerCommand\(\s*([^,]+?)\s*,", _js):
            _arg = _arg.strip()
            _lit = _re.fullmatch(r"""["']([^"']+)["']""", _arg)
            _wreg.add(_lit.group(1) if _lit else (_resolve_const(_arg, _jf) or _arg))
    assert not (_wcmds - _wreg), (
        f"أوامرُ معلَنةٌ في مانيفست الترحيب بلا registerCommand: {sorted(_wcmds - _wreg)}")
    for _c in pkg.get("contributes", {}).get("commands", []):
        assert _c.get("title"), f"أمرُ ترحيبٍ بلا عنوان: {_c.get('command')}"
    assert "resolveSadRun" in js, "لا دالّة resolveSadRun (حلّ الثنائيّ المدمج) في نقطة الدخول"
    # [AR-01] التشغيل يُوجَّه إلى لوحة المخرجات العربيّة (bidi صحيح) بدل مهمّة طرفيّة تشوّه العربيّة،
    #         ويجب أن يمرّر المسار المحلول sadRunCmd — وإلّا يتجاهل الثنائيّ المدمج. حارس ضدّ انحدار.
    assert "output-panel" in js and "SadOutputPanel" in js, \
        "runSadFile لا يوجّه إلى لوحة المخرجات العربيّة (output-panel/SadOutputPanel) [AR-01]"
    # اللوحة تُنشأ فعلًا وتُدفَع إلى subscriptions (وإلّا يبقى sadOutput غير مُهيّأ ⇒ runSadFile
    # يرمي زمن التشغيل بينما L0/node --check أخضران — نجاح كاذب). وتُشغَّل بالمسار المحلول sadRunCmd.
    assert _re.search(r"new\s+SadOutputPanel\(", js), \
        "لا إنشاء فعليّ للوحة (new SadOutputPanel) — sadOutput يبقى غير مُهيّأ [AR-01]"
    # اللوحة مُدرَجة في context.subscriptions (وإلّا لا تُغلَق/تُقتَل العمليّة عند التعطيل). نفحص
    # نافذةً بعد push( تغطّي قائمة الوسائط كاملةً (لا regex [^)] الذي يتوقّف عند أوّل قوس مغلق).
    _push_idx = js.find("subscriptions.push(")
    assert _push_idx != -1 and "sadOutput" in js[_push_idx:_push_idx + 600], \
        "لوحة المخرجات غير مُدرَجة في context.subscriptions — لن تُغلَق/تُقتَل عند التعطيل [AR-01]"
    assert _re.search(r"sadOutput\.run\(\s*sadRunCmd", js), \
        "لوحة المخرجات لا تُشغَّل بالمسار المحلول sadRunCmd — قد تتجاهل الثنائيّ المدمج [AR-01]"
    # [SAD-04] أمر «ابنِ» يُوجَّه للّوحة بالمسار المحلول sadBuildCmd، وعدسات الكود «شغّل/ابنِ»
    #          مسجَّلة فوق «دالة رئيسية». حرّاس ضدّ انحدار (المسار المحلول + وجود الميزة).
    assert "resolveSadBuild" in js and _re.search(r"sadOutput\.run\(\s*sadBuildCmd", js), \
        "أمر البناء لا يُوجَّه للّوحة بالمسار المحلول sadBuildCmd (resolveSadBuild) — قد يتجاهل الثنائيّ المدمج [SAD-04]"
    assert "registerCodeLensProvider" in js and "SadMainCodeLensProvider" in js, \
        "لا موفّر عدسات كود (registerCodeLensProvider/SadMainCodeLensProvider) فوق دالّة رئيسية [SAD-04]"
    # [تدقيق #1] خطوة «شغّل» تصف لوحة ص العربيّة (وجهة AR-01) لا «طرفيّة في الأسفل» (تشوّه bidi).
    _step_run = os.path.join(ext, "media", "step-run.md")
    if os.path.isfile(_step_run):
        _sr = _read(_step_run)
        assert "لوحة" in _sr and "طرفيّة في الأسفل" not in _sr, \
            "media/step-run.md لا يصف لوحة المخرجات العربيّة (أو ما زال يَعِد بطرفيّة في الأسفل) — يناقض AR-01 [تدقيق #1]"
    # مهمّة tasks.json المولَّدة يجب أن تُبنى من المُشغّل المحلول (buildTasksJson(sadRunCmd)) لا
    # باسم ثابت — وإلّا عاد تباعد المسارين (المهمّة تفشل رغم توفّر المدمج). حارس ضدّ انحدار.
    assert "buildTasksJson" in js and _re.search(r"command:\s*runCommand", js), \
        "مهمّة tasks.json لا تُبنى من المُشغّل المحلول (buildTasksJson/command: runCommand) — خطر تباعد المسارين"
    # التشغيل يجب أن يصمد حين لا محرّر ص نشط (زرّ الجولة يحتلّ المحرّر فلا نصّ نشط): بحث في
    #      مساحة العمل عن ملفّ ص وفتحه — وإلّا عاد عطل «لا محرّر نشط» في الجولة. حارس ضدّ انحدار.
    assert "findWorkspaceSadFile" in js and "resolveSadDoc" in js, \
        "runSadFile لا يحوي رجوعًا لملفّ مساحة العمل (findWorkspaceSadFile/resolveSadDoc) — زرّ التشغيل في الجولة سيفشل"

    # (١هـ) [BS-01] كاشفُ قلب الاتّجاه موصولٌ فعلًا: الوحدةُ مستهلَكة، والحارسُ **مُنشَأ** (لا
    #       مستورَدًا فقط — استيرادٌ بلا إنشاءٍ يمرّ `node --check` ولا يشخّص شيئًا: نجاحٌ كاذب)،
    #       ومزوّدُ الإجراءات مسجَّل كي يكون للتشخيص مخرَجُ إصلاحٍ لا مجرّدُ لومٍ أحمر.
    assert "bidi-guard" in js and _re.search(r"new\s+(?:[A-Za-z_$][\w$]*\.)?BidiGuard\(", js), \
        "كاشفُ قلب الاتّجاه غيرُ مُنشَأ في نقطة الدخول (new BidiGuard) — لا تشخيصَ لهجمات قلب الاتّجاه [BS-01]"
    assert "registerCodeActionsProvider" in js and "BidiCodeActionProvider" in js, \
        "لا مزوّدَ إجراءاتٍ لتشخيص الاتّجاه — تشخيصٌ بلا إصلاحٍ لومٌ بلا مخرَج [BS-01]"
    # ومُحدِّدُ المزوّد **مشتقٌّ من مخطّطات الحارس** لا مكتوبٌ بيده: `{scheme:"file"}` وحدَه
    # كان يترك ملفًّا غيرَ محفوظ (أوّلُ ما يُلصَق فيه من الشابكة) مُشخَّصًا بلا مصباحِ إصلاح.
    assert "SCANNED_SCHEMES" in js, (
        "مُحدِّدُ مزوّد الإجراءات لا يُشتَقّ من SCANNED_SCHEMES — تشخيصٌ في مخطّطٍ بلا إصلاحٍ فيه [BS-01]")

    # (١و) [DR-03] شارةُ الطرفيّة موصولة، ورسالتُها **تُسمّي القيدَ منبعيًّا**. الثانية ليست
    #      تدقيقَ صياغة: بدونها يستنتج المستخدمُ أنّ **لغةَ ص** لا تُخرِج العربيّةَ صحيحة،
    #      والعطبُ في مكتبة طرفيّةٍ منبعيّةٍ لا في اللغة ولا في برنامجه.
    assert "activateTerminalNotice" in js, \
        "شارةُ الطرفيّة غيرُ موصولة (activateTerminalNotice) — الحدُّ المنبعيُّ يبقى صامتًا [DR-03]"
    _tn = _read(os.path.join(ext, "terminal-notice.js"))
    assert "xterm" in _tn and "لا في لغة ص" in _tn, \
        "رسالةُ الطرفيّة لا تُسمّي القيدَ منبعيًّا (xterm) ولا تُبرِّئ لغةَ ص — تُحمَّل ص وزرَ غيرها [DR-03]"

    # (١ز) [BS-01] الكاشفُ **يميّز** ولا يبرز فقط. وهذا **فحصٌ سلوكيٌّ لا نصّيّ**: توكيدٌ
    #      نصّيٌّ على وجود `MARKS` كان يمرّ أخضرَ لو صارت `new Set()` وشُخِّصت كلُّ علامةٍ
    #      مفردة — أي على الانحدار الذي وُجد الحارسُ لمنعه بعينه. فنُشغِّل الوحدةَ ونسألها.
    #      (علاماتُ الاتّجاه المفردة شرعيّةٌ في نصٍّ عربيّ — ٣١٢ منها في نواة نهلة — وتشخيصُها
    #      ضجيجٌ يُدرِّب على العمى، فيصير التحذيرُ غطاءً للهجوم لا حاجزًا دونه.)
    if node:
        _probe = (
            'const s=require(process.argv[1]);'
            'const c=n=>String.fromCharCode(n);'
            'const A=[["RLM",s.scanBidi("x"+c(0x200F)+"y","sad").length,0],'
            '["FSI..PDI",s.scanBidi(c(0x2068)+"a"+c(0x2069),"sad").length,0],'
            '["PDF-يتيم",s.scanBidi("x"+c(0x202C),"sad").length,0],'
            '["RLO-معلَّق",s.scanBidi("#"+c(0x202E)+"م","sad").length,1],'
            '["تسرُّب",s.scanBidi("/* "+c(0x202E)+" */ x"+c(0x202C)+";","javascript").length,1]];'
            'const bad=A.filter(([,g,w])=>g!==w);'
            'if(bad.length){console.error(JSON.stringify(bad));process.exit(1)}'
        )
        _r = subprocess.run([node, "-e", _probe, os.path.join(ext, "bidi-scan.js")],
                            capture_output=True, text=True)
        assert _r.returncode == 0, (
            "كاشفُ الاتّجاه لا يميّز الشرعيَّ من المتسرّب — [اسم، ما ردّ، المتوقَّع]: "
            f"{_r.stderr.strip() or _r.stdout.strip()} [BS-01]")
    _bs = _read(os.path.join(ext, "bidi-scan.js"))
    assert "MARKS" in _bs and "OPENERS" in _bs and "CLOSERS" in _bs, \
        "كاشفُ الاتّجاه لا يفصل العلاماتِ عن القوالب (MARKS/OPENERS/CLOSERS) [BS-01]"
    # ولا محرفَ خفيًّا **داخل تعبيرٍ نمطيّ** في الوحدتين: صنفٌ نمطيٌّ فيه محرفٌ لا يُرى لا
    # يراه المراجعُ ولا يمسكه `diff` — وهو أوّلُ ما يجب أن يُرى في كاشفِ الخفيّ نفسِه.
    _INVISIBLE = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A)) | {
        0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0x061C}
    for _mod in ("bidi-scan.js", "arabic-normalize.js"):
        for _m in _re.finditer(r"/\[[^\]\n]*\]/[gimsuy]*", _read(os.path.join(ext, _mod))):
            _bad = sorted({hex(ord(c)) for c in _m.group(0) if ord(c) in _INVISIBLE})
            assert not _bad, (
                f"{_mod}: محرفٌ خفيٌّ حرفيٌّ داخل تعبيرٍ نمطيّ ({_bad}) — استعمل ترميز \\u صريحًا")

    # (١ط) [TY-03] كشفُ أحاديّة العرض حيًّا: القياسُ في اللوحة (حيث DOM)، والحكمُ في وحدةٍ
    #      نقيّة. والوصلُ بينهما **يُفحَص**: قياسٌ بلا مستقبِلٍ يُرمى في الفراغ، وحكمٌ بلا
    #      قياسٍ لا يُستدعى أبدًا — وكلاهما يمرّ `node --check` أخضرَ.
    _fp = os.path.join(ext, "font-probe.js")
    assert os.path.isfile(_fp), "وحدةُ كشف أحاديّة العرض مفقودة (font-probe.js) [TY-03]"
    _panel = _read(os.path.join(ext, "output-panel.js"))
    assert "font-probe" in _panel and "measureText" in _panel, \
        "لوحةُ المخرجات لا تقيس عرضَ المحارف — لا كشفَ لسقوطِ الخطّ إلى وجهٍ متناسب [TY-03]"
    assert "onFontProbe" in js and "maybeWarnProportional" in js, \
        "قياسُ الخطّ لا يصل إلى الحكم (onFontProbe/maybeWarnProportional) — قياسٌ يُرمى في الفراغ [TY-03]"
    # وعيّنةُ القياس **مصدرُ حقيقةٍ واحد**: لو كُتبت في اللوحة يدويًّا لانجرفت عن التي يحكم
    # عليها المقيِّم، فيُقاس محرفٌ ويُحكَم على آخر.
    assert _re.search(r'require\(["\']\./font-probe\.js["\']\)\.SAMPLES', _panel), \
        "عيّنةُ قياس الخطّ مكتوبةٌ في اللوحة لا مستورَدةٌ من font-probe — خطرُ انجرافٍ صامت [TY-03]"
    # **ولا يُقاس خطُّ اللوحة نفسِها**: مكدَّسُ `#log` يبدأ بالوجه المحزوم و`@font-face` مُضمَّنٌ
    # في وثيقتها، فقياسُه يعطي «أحاديّ» دائمًا — أي يعمى الكاشفُ عن الحالة التي وُجد لها.
    assert "--vscode-editor-font-family" in _panel, (
        "قياسُ الخطّ يقع على مكدَّس اللوحة لا على خطّ المحرّر — يعطي «أحاديًّا» دائمًا "
        "فيعمى عن سقوط خطّ المستخدم [TY-03]")
    # والقياسُ **بعد تحميل الوجوه**: قبلها يقع على الاحتياطيّ المتناسب ⇒ إنذارٌ كاذبٌ أوّلَ فتحة.
    assert "fonts.ready" in _panel, \
        "قياسُ الخطّ لا ينتظر تحميلَ الوجوه (document.fonts.ready) — إنذارٌ كاذبٌ في أوّل فتحة [TY-03]"
    # ولا يُعلَن نجاحٌ بلا إعادة قياس: الكتابةُ تُقبَل وقد لا تُغيّر شيئًا (وجهٌ غيرُ مثبَّت،
    # أو نطاقٌ أضيقُ يغلب) — وهو درسُ «تمّ والإعدادُ في مكانه» المدفوعُ ثمنُه مرّتين.
    _fpsrc = _read(_fp)
    assert "remeasure" in _fpsrc and "fixedButUnverified" in _fpsrc, (
        "إصلاحُ الخطّ يُعلن نجاحًا بلا إعادة قياس — رسالةُ نجاحٍ بلا أثرٍ تُنهي بحثَ المستخدم [TY-03]")
    assert "requestRemeasure" in _panel and "requestRemeasure" in js, \
        "لا مسارَ لإعادة القياس بين اللوحة والامتداد (requestRemeasure) [TY-03]"

    # (١ي) [TY-04] الأشكالُ السياقيّةُ مثبَّتةٌ صراحةً لا موروثة: إطفاءُ «الروابط» نصيحةٌ
    #      لاتينيّةٌ شائعةٌ **تفكّك الكلمةَ العربيّة** إلى حروفٍ منفصلة.
    _sh = os.path.join(ROOT, "extensions", "mihrab-shell", "package.json")
    if os.path.isfile(_sh):
        _d = json.load(open(_sh, encoding="utf-8")).get("contributes", {}).get(
            "configurationDefaults", {})
        assert _d.get("editor.fontLigatures") is True, (
            "‏`editor.fontLigatures` غيرُ مضبوطٍ صراحةً — الأشكالُ السياقيّةُ في العربيّة "
            "شرطُ قراءةٍ لا زخرفة، وإطفاؤها يفكّك الكلمة [TY-04]")

    # (١ك) [BS-02] تسميةُ محارف الاتّجاه: موصولةٌ و**مطفأةٌ افتراضيًّا**. الإظهارُ الدائمُ
    #      يملأ نصَّ العربيّة السويَّ برقاقاتٍ على علاماتٍ مشروعة — عودةُ الضجيج بابٍ آخر.
    _bd = os.path.join(ext, "bidi-decorate.js")
    assert os.path.isfile(_bd), "وحدةُ تسمية محارف الاتّجاه مفقودة (bidi-decorate.js) [BS-02]"
    assert "BidiMarkerDecorator" in js and "TOGGLE_CMD" in _read(_bd), \
        "مبدِّلُ أسماء محارف الاتّجاه غيرُ موصول [BS-02]"
    assert _re.search(r"this\.enabled\s*=\s*false", _read(_bd)), \
        "تسميةُ محارف الاتّجاه ليست مطفأةً افتراضيًّا — ضجيجٌ يوميٌّ على علاماتٍ مشروعة [BS-02]"

    # (١ل) [BS-03] حارسُ الأسماء معمَّمٌ على الإنشاء وإعادة التسمية، ومنطقُه في **وحدةٍ
    #      نقيّةٍ مشتركة** لا مكرَّرًا: تكرارُه يعني تباعدَ حارسَين يحرسان الشيءَ نفسَه.
    _vn = os.path.join(ext, "validate-name.js")
    assert os.path.isfile(_vn), "وحدةُ تحقّق الأسماء المشتركة مفقودة (validate-name.js) [BS-03]"
    _ng = _read(os.path.join(ext, "name-guard.js"))
    assert "onDidCreateFiles" in _ng and "onDidRenameFiles" in _ng, \
        "حارسُ الأسماء لا يراقب الإنشاءَ وإعادةَ التسمية — محروسٌ في بابٍ ومفتوحٌ في أوسع [BS-03]"
    assert "activateNameGuard" in js, "حارسُ الأسماء غيرُ موصولٍ في نقطة الدخول [BS-03]"

    # (١م) [ON-03] المساعدةُ داخل المحرّر: البياناتُ المحزومةُ **مطابقةٌ بايتًا ببايت**
    #      لـ`site/data/` — وإلّا افترق ما يقرؤه المستخدمُ في المحرّر عمّا يقرؤه في الموقع.
    _hp = os.path.join(ext, "help-panel.js")
    assert os.path.isfile(_hp), "لوحةُ المساعدة مفقودة (help-panel.js) [ON-03]"
    assert "openHelp" in js or "OPEN_HELP_CMD" in js, \
        "أمرُ المساعدة غيرُ موصولٍ في نقطة الدخول [ON-03]"
    import hashlib as _hl2
    for _df in ("glossary.json", "keybindings.json"):
        _a = os.path.join(ROOT, "site", "data", _df)
        _b = os.path.join(ext, "data", _df)
        assert os.path.isfile(_b), f"بياناتُ المساعدة المحزومة مفقودة: data/{_df} [ON-03]"
        if os.path.isfile(_a):
            assert (_hl2.sha256(open(_a, "rb").read()).hexdigest()
                    == _hl2.sha256(open(_b, "rb").read()).hexdigest()), (
                f"‏data/{_df} انجرف عن site/data/{_df} — المساعدةُ في المحرّر تخالف الموقعَ [ON-03]")
        # ولوحةُ المساعدة **تُرشِّح بالتطبيع**: بلا ذلك يبحث المستخدمُ بما يكتبه فلا يجد.
    assert "normalizeArabic" in _read(_hp), \
        "لوحةُ المساعدة لا تستعمل تطبيعَ البحث العربيّ — «لوحه الاوامر» لن تجد «لوحة الأوامر» [ON-03·DX-01]"

    # (١ن) [ON-04] إخبارُ الإصدارات: **بإذنٍ صريح** — محرابٌ لا يمسّ الشبكةَ بلا سؤال.
    _rn = os.path.join(ext, "release-notice.js")
    assert os.path.isfile(_rn), "وحدةُ إخبار الإصدارات مفقودة (release-notice.js) [ON-04]"
    _rnsrc = _read(_rn)
    assert "CONSENT_KEY" in _rnsrc and "askNo" in _rnsrc, \
        "فحصُ الإصدارات بلا إذنٍ صريح — يناقض موقفَ محرابٍ من التتبّع [ON-04]"
    assert "checkForUpdate" in js, "فحصُ الإصدارات غيرُ موصولٍ في نقطة الدخول [ON-04]"

    # (١س) [DX-03] اختصاراتٌ **محايدةٌ للتخطيط**: حرفٌ لاتينيٌّ في اختصارٍ لا يوجد على
    #      لوحةٍ عربيّة — والاختصارُ الذي لا يُعثَر عليه اختصارٌ غيرُ موجود.
    _kbs = pkg.get("contributes", {}).get("keybindings", [])
    assert _kbs, "لا اختصاراتٍ لأوامر ص الأساسيّة — أوامرُ يوميّةٌ بلا مفاتيح [DX-03]"
    _bound = {k.get("command") for k in _kbs}
    for _need in ("mihrab.runSadFile", "mihrab.buildSadFile"):
        assert _need in _bound, f"أمرٌ أساسيٌّ بلا اختصار: {_need} [DX-03]"
    # **التمييزُ الدقيق، لا المنعُ الجملة.** المفتاحُ الحرفيُّ في تركيبةٍ (‏`Ctrl+Shift+B`)
    # **يعمل** على التخطيط العربيّ — VS Code يسقط إلى تخطيطٍ لاتينيٍّ للإرسال حين لا تُنتِج
    # لوحةُ المستخدم حرفًا لاتينيًّا. فالعطبُ فيه **اكتشافيٌّ لا وظيفيّ**: يُعرَض «B» ولوحتُه
    #   تقول «لا». وعلاجُ الاكتشاف توثيقٌ لا تبديلُ مفتاح — ولذلك يوجب الحارسُ:
    #   ‏(١) أن يكون **أمرُ التشغيل** بمفتاحٍ وظيفيٍّ محايدٍ تمامًا (أكثرُ الأوامر تكرارًا).
    #   ‏(٢) ألّا يوجد مفتاحٌ حرفيٌّ **بلا مُعدِّل** (ذاك يُكتَب في الملفّ فيُبتلَع الحرف).
    #   ‏(٣) أن تُسرَد الاختصاراتُ في خطوة الجولة، فيجدها من لا يقرأ لوحتَه.
    _FUNCTION_KEY = _re.compile(r"^f\d{1,2}$")
    _MODIFIERS = {"ctrl", "shift", "alt", "cmd", "meta", "win"}
    _run_key = next((k.get("key", "") for k in _kbs if k.get("command") == "mihrab.runSadFile"), "")
    assert _FUNCTION_KEY.match(_run_key.strip().lower()), (
        f"اختصارُ التشغيل «{_run_key}» ليس مفتاحًا وظيفيًّا — وهو أكثرُ الأوامر تكرارًا، "
        f"فيجب أن يكون محايدًا للتخطيط تمامًا [DX-03]")
    for _k in _kbs:
        for _field in ("key", "mac", "linux", "win"):
            _combo = (_k.get(_field) or "").strip().lower()
            if not _combo:
                continue
            for _chord in _combo.split():
                _parts = [p for p in _chord.split("+") if p]
                if not _parts:
                    continue
                assert (len(_parts) > 1 or _FUNCTION_KEY.match(_parts[-1])
                        or _parts[-1] in _MODIFIERS), (
                    f"اختصارُ «{_k.get('command')}» يستعمل مفتاحًا حرفيًّا بلا مُعدِّل "
                    f"(«{_chord}») — يُبتلَع حرفًا في المحرّر بدل أن يُنفَّذ [DX-03]")
    _steps_md = " ".join(
        _read(os.path.join(ext, "media", m)) for m in os.listdir(os.path.join(ext, "media"))
        if m.endswith(".md"))
    assert _run_key.upper() in _steps_md.upper(), (
        f"اختصارُ التشغيل «{_run_key}» غيرُ مسرودٍ في وسائط الجولة — الاختصارُ الذي لا "
        f"يُعثَر عليه اختصارٌ غيرُ موجود [DX-03]")

    # (١ح) [DX-01] تطبيعُ البحث العربيّ: نسخةُ `sad-lang` **مطابقةٌ بايتًا ببايت**. المستودعُ
    #      يكرّر الوحداتِ بين الامتدادات عمدًا (استقلالُ الامتداد) — وثمنُ ذلك انجرافٌ صامت،
    #      فتُطبَّع الهمزةُ في سطحٍ ولا تُطبَّع في آخر. البصمةُ تجعل الثمنَ صفرًا.
    _sad_ext = os.path.join(ROOT, "extensions", "sad-lang")
    if os.path.isdir(_sad_ext):
        import hashlib as _hl
        _digests = {}
        for _base in (ext, _sad_ext):
            _p = os.path.join(_base, "arabic-normalize.js")
            assert os.path.isfile(_p), f"وحدةُ تطبيع البحث مفقودة: {_p} [DX-01]"
            _digests[_base] = _hl.sha256(open(_p, "rb").read()).hexdigest()
        assert len(set(_digests.values())) == 1, (
            "نسختا arabic-normalize.js متباعدتان (بصمتان مختلفتان) — "
            "سيُطبَّع البحثُ في سطحٍ ولا يُطبَّع في آخر [DX-01]")

    # (١د) طبقة الحزم المدمجة: البناء يحقن sad-run في bin/ داخل الامتداد، وgit يتجاهله، وثابت
    #      المجلّد في JS يطابق ما يحقنه البناء — وإلّا يمرّ L0 أخضر بينما التشغيل المدمج مكسور. [M6]
    # ثابت مجلّد الثنائيّات المدمجة صار في tool-resolve.js (مصدر واحد يتشاركه run/check/build). [تدقيق #2]
    tool_resolve = _read(os.path.join(ext, "tool-resolve.js"))
    assert _re.search(r'BUNDLED_BIN_DIR\s*=\s*"bin"', tool_resolve), \
        "ثابت BUNDLED_BIN_DIR ليس \"bin\" في tool-resolve.js — قد يفترق عن مسار الحقن في build.sh"
    assert "resolveBundledTool" in tool_resolve and "probeTool" in tool_resolve, \
        "tool-resolve.js لا يصدّر محلّل الأدوات المشترك (resolveBundledTool/probeTool) [تدقيق #2]"
    build_sh = _read(os.path.join(ROOT, "build", "build.sh"))
    assert "WELCOME_BIN" in build_sh and "sad-run.exe" in build_sh, \
        "build.sh لا يحوي كتلة حزم sad-run المدمجة (WELCOME_BIN/sad-run.exe)"
    # جسر التشخيص [SAD-02] يحلّ sad-check المدمج من bin/ قبل PATH ⇒ يجب أن يحزمه البناء أيضًا.
    assert "sad-check.exe" in build_sh, \
        "build.sh لا يحزم sad-check.exe المدمج — جسر التشخيص عند الحفظ سيسقط دومًا إلى PATH"
    # أمر البناء [SAD-04] يحلّ sad-build المدمج من bin/ قبل PATH ⇒ يجب أن يحزمه البناء أيضًا.
    assert "sad-build.exe" in build_sh, \
        "build.sh لا يحزم sad-build.exe المدمج — أمر «ابنِ» سيسقط دومًا إلى PATH [SAD-04]"
    gitignore = _read(os.path.join(ROOT, ".gitignore"))
    assert "extensions/mihrab-welcome/bin/" in gitignore, \
        ".gitignore لا يتجاهل الثنائيّ المدمج extensions/mihrab-welcome/bin/ (خطر إيداعه)"

    # (٢) كلّ أمر معلَن في المانيفست مُسجَّل فعلًا (احتواء لا تطابق تامّ: يجوز أن يسجّل JS
    #     أمرًا داخليًّا غير معلَن، لكن كلّ معلَن يجب أن يُنفَّذ). يُعاد استعمال المسح الموزّع
    #     أعلاه (`_wreg`) بدل مسحٍ ثانٍ مقصورٍ على نقطة الدخول: كان الثاني أضيق من الأوّل،
    #     فيمرّ أمرٌ سجّلته وحدةٌ مستقلّةٌ في الأوّل ويسقط في الثاني — تناقضٌ في الحارس نفسِه.
    manifest_cmds = {c.get("command") for c in contrib.get("commands", [])}
    assert manifest_cmds, "لا أوامر معلَنة في امتداد الترحيب"
    missing = manifest_cmds - _wreg
    assert not missing, f"أوامر معلَنة في المانيفست بلا registerCommand في JS: {missing}"
    # كلّ أمر معلَن له عنوان غير فارغ (يظهر في لوحة الأوامر).
    for c in contrib.get("commands", []):
        assert c.get("title"), f"أمر بلا عنوان: {c.get('command')}"

    # (٣) الجولة: خطوات تشير لوسائط ماركداون موجودة، ومعرّفات فريدة، وactivationEvents مربوط.
    walks = contrib.get("walkthroughs", [])
    assert walks, "لا جولات (walkthroughs) في امتداد الترحيب"
    seen_step_ids = set()
    for w in walks:
        assert w.get("id") and w.get("title") and w.get("description"), f"عقد جولة ناقص: {w.get('id')}"
        # ملاحظة: onWalkthrough:<id> يولّده VS Code تلقائيًّا من contributes.walkthroughs (≥1.74)،
        # فلا نُلزِمه صراحةً في activationEvents (كان زائدًا يحذّر منه المحرّر). التنشيط مضمون بـ
        # onStartupFinished (يُفحَص أعلاه) + التوليد التلقائيّ. [تدقيق #6]
        steps = w.get("steps", [])
        assert steps, f"جولة بلا خطوات: {w['id']}"
        for st in steps:
            sid = st.get("id")
            assert sid and sid not in seen_step_ids, f"معرّف خطوة مفقود/مكرّر: {sid}"
            seen_step_ids.add(sid)
            assert st.get("title") and st.get("description"), f"خطوة ناقصة: {sid}"
            md = (st.get("media") or {}).get("markdown")
            assert md, f"خطوة بلا وسيط ماركداون: {sid}"
            mp = os.path.join(ext, *md.lstrip("./").split("/"))
            assert os.path.isfile(mp), f"وسيط جولة مفقود: {md} (للخطوة {sid})"
            # أيّ رابط command: في وصف الخطوة يجب أن يشير لأمر معلَن (لا رابط ميّت).
            # وأوامرُ المنبع المستدعاةُ من الجولة تُسرَد **بالاسم** لا بقاعدةٍ عامّة
            # (`workbench.*` مثلًا): قاعدةٌ عامّةٌ تُمرِّر خطأً مطبعيًّا في اسمٍ منبعيّ،
            # والقائمةُ الصريحةُ تُفشِله. وكلُّ اسمٍ هنا متحقَّقٌ منه في المنبع المثبَّت.
            for cmd in _re.findall(r"command:([A-Za-z0-9_.]+)", st["description"]):
                assert cmd in manifest_cmds or cmd in UPSTREAM_CMDS_IN_WALKTHROUGH, (
                    f"رابط أمر ميّت «{cmd}» في الخطوة {sid}")


@check("هوية لغة ص متّسقة (SAD_LANG_ID/SAD_EXT ↔ contributes.languages في sad-lang)")
def _lang_identity():
    # مصدر الحقيقة لهوية لغة ص = مساهمة اللغة في امتداد sad-lang (لا سلسلة مُختلَقة). كلّ مرآة
    # SAD_LANG_ID/SAD_EXT مكرَّرة في امتدادات محراب يجب أن تطابقه — يمنع التباعد الصامت.
    import re
    sad_lang_pkg = os.path.join(ROOT, "extensions", "sad-lang", "package.json")
    if not os.path.isfile(sad_lang_pkg):
        return  # لا امتداد لغة في هذا الفرع — تخطٍّ
    pkg = json.load(open(sad_lang_pkg, encoding="utf-8"))
    langs = pkg.get("contributes", {}).get("languages", [])
    assert langs, "امتداد sad-lang بلا contributes.languages (مصدر هوية اللغة)"
    lang = langs[0]
    lang_id = lang.get("id")
    exts = lang.get("extensions") or []
    assert lang_id and exts, "تعريف لغة ص ناقص (id/extensions) في sad-lang"
    sad_ext = exts[0]

    mirrors = [
        os.path.join(ROOT, "extensions", "mihrab-nebras", n)
        for n in ("chat.js", "agent.js", "explain-selection.js", "inline-completion.js", "fix-diagnostic.js")
    ] + [os.path.join(ROOT, "extensions", "mihrab-welcome", "extension.js")]
    id_re = re.compile(r'const\s+SAD_LANG_ID\s*=\s*"([^"]*)"')
    ext_re = re.compile(r'const\s+SAD_EXT\s*=\s*"([^"]*)"')
    seen_id = seen_ext = 0
    for f in mirrors:
        if not os.path.isfile(f):
            continue
        js = _read(f)
        for m in id_re.finditer(js):
            seen_id += 1
            assert m.group(1) == lang_id, \
                f"SAD_LANG_ID «{m.group(1)}» في {os.path.basename(f)} ≠ هوية sad-lang «{lang_id}»"
        for m in ext_re.finditer(js):
            seen_ext += 1
            assert m.group(1) == sad_ext, \
                f"SAD_EXT «{m.group(1)}» في {os.path.basename(f)} ≠ امتداد sad-lang «{sad_ext}»"
    # حارس ضدّ التحوّل إلى no-op لو تغيّرت البنية (نقل الملفّات/إعادة تسمية الثابت).
    assert seen_id and seen_ext, \
        "لم يُعثَر على أيّ تصريح SAD_LANG_ID/SAD_EXT في المرايا — تحقّق من بنية الامتدادات"


@check("مقتطفات ص [SAD-03]: معلَنة ↔ ملفّ موجود ↔ JSONC صالح ↔ رأس مولَّد (لا تحرير يدويّ)")
def _sad_snippets():
    ext = os.path.join(ROOT, "extensions", "sad-lang")
    if not os.path.isdir(ext):
        return  # لا إضافة لغة ص في هذا الفرع — تخطٍّ
    pkg = json.load(open(os.path.join(ext, "package.json"), encoding="utf-8"))
    decls = pkg.get("contributes", {}).get("snippets", [])
    assert decls, "لا contributes.snippets في sad-lang — المقتطفات [SAD-03] غير مسجّلة"
    for d in decls:
        assert d.get("language") == "sad", f"مقتطف بلغة غير sad: {d.get('language')}"
        rel = d.get("path")
        assert rel, "إعلان مقتطفات بلا path"
        p = os.path.join(ext, *rel.lstrip("./").split("/"))
        assert os.path.isfile(p), f"ملفّ مقتطفات معلَن مفقود: {rel}"
        raw = _read(p)
        # رأس «مولَّد» (تعليق JSONC) — حارس ضدّ التحرير اليدويّ (المصدر gen_snippets.py في مستودع اللغة).
        assert "gen_snippets.py" in raw and "لا تُحرِّره" in raw, \
            f"ملفّ المقتطفات {rel} بلا رأس مولَّد — قد يكون حُرِّر يدويًّا (يجب توليده من language-truth)"
        # JSONC صالح: نجرّد أسطر التعليقات // ثمّ نحلّل، ونتأكّد أنّ كلّ مقتطف يحمل prefix + body.
        body = "".join(ln for ln in raw.splitlines(keepends=True) if not ln.lstrip().startswith("//"))
        data = json.loads(body)
        assert data, "ملفّ المقتطفات فارغ (لا مقتطفات مولَّدة)"
        for key, snip in data.items():
            assert isinstance(snip, dict) and snip.get("prefix") and snip.get("body"), \
                f"مقتطف «{key}» بلا prefix/body صالح"


# ───────────── L0-17: عميل ص LSP (SAD-01: خادم لغويّ محزوم في sad-lang) ─────────────
@check("عميل ص LSP: main يصدّر activate، تنشيط onLanguage:sad، حلّ الخادم المدمج ↔ حقن build.sh، تشخيص/مزوّدات موصولة")
def _sad_lsp_ext():
    import re as _re
    ext = os.path.join(ROOT, "extensions", "sad-lang")
    if not os.path.isdir(ext):
        return  # لا إضافة لغة ص في هذا الفرع — تخطٍّ
    pkg = json.load(open(os.path.join(ext, "package.json"), encoding="utf-8"))
    contrib = pkg.get("contributes", {})

    # (١) نقطة الدخول main موجودة وتصدّر activate (وإلّا لا يُفعَّل العميل إطلاقًا).
    main_rel = pkg.get("main")
    assert main_rel, "لا حقل main في sad-lang — عميل LSP يحتاج نقطة دخول JS [SAD-01]"
    main_path = os.path.join(ext, *main_rel.lstrip("./").split("/"))
    assert os.path.isfile(main_path), f"ملفّ main مفقود: {main_rel}"
    js = _read(main_path)
    assert "module.exports" in js and "function activate" in js, \
        "نقطة دخول sad-lang لا تصدّر activate"

    # (٢) التنشيط عند فتح لغة ص (وإلّا لا يبدأ الخادم عند تحرير ملفّ ص).
    assert "onLanguage:sad" in pkg.get("activationEvents", []), \
        "activationEvents لا يحوي onLanguage:sad — الخادم لن يبدأ عند فتح ملفّ ص [SAD-01]"

    # (٣) صحّة نحو JS لكلّ ملفّات العميل إن توفّر node (لا يُفشِل حين غيابه).
    js_files = ["extension.js", "sad-lsp-process.js", "lsp-rpc.js", "lsp-protocol.js", "tool-resolve.js"]
    node = shutil.which("node")
    for jf in js_files:
        jp = os.path.join(ext, jf)
        assert os.path.isfile(jp), f"ملفّ عميل LSP مفقود: {jf}"
        if node:
            r = subprocess.run([node, "--check", jp], capture_output=True, text=True)
            assert r.returncode == 0, f"خطأ نحويّ في {jf}:\n{r.stderr.strip()}"

    # (٤) حلّ الخادم المدمج: ثابت مجلّد bin يطابق ما يحقنه build.sh (وإلّا L0 أخضر والحزم مكسور).
    tool_resolve = _read(os.path.join(ext, "tool-resolve.js"))
    assert _re.search(r'BUNDLED_BIN_DIR\s*=\s*"bin"', tool_resolve), \
        "ثابت BUNDLED_BIN_DIR ليس \"bin\" في sad-lang/tool-resolve.js — قد يفترق عن حقن build.sh"
    assert "resolveBundledTool" in tool_resolve and "probeTool" in tool_resolve, \
        "sad-lang/tool-resolve.js لا يصدّر محلّل الأدوات (resolveBundledTool/probeTool)"
    proc_js = _read(os.path.join(ext, "sad-lsp-process.js"))
    assert 'SAD_LSP_EXE = "sad-lsp.exe"' in proc_js, \
        "sad-lsp-process.js لا يحلّ الثنائيّ المدمج باسم sad-lsp.exe — قد يتجاهل حقن build.sh"

    # (٥) البناء يحزم الخادم المدمج، وgit يتجاهله (طبقة الحزم المدمجة، نفس نمط sad-run/check/build).
    build_sh = _read(os.path.join(ROOT, "build", "build.sh"))
    assert "SAD_LSP_SRC" in build_sh and "sad-lsp.exe" in build_sh and "SADLANG_BIN" in build_sh, \
        "build.sh لا يحوي كتلة حزم sad-lsp المدمجة (SAD_LSP_SRC/SADLANG_BIN/sad-lsp.exe) [SAD-01]"
    gitignore = _read(os.path.join(ROOT, ".gitignore"))
    assert "extensions/sad-lang/bin/" in gitignore, \
        ".gitignore لا يتجاهل الخادم المدمج extensions/sad-lang/bin/ (خطر إيداعه) [SAD-01]"

    # (٦) التشخيص موصول: publishDiagnostics → DiagnosticCollection (القيمة الأساسيّة يوم الأوّل).
    assert "createDiagnosticCollection" in js, \
        "extension.js لا يُنشئ DiagnosticCollection — التشخيصات لن تظهر في لوحة المشاكل [SAD-01]"
    assert "M_PUBLISH_DIAGNOSTICS" in js, \
        "extension.js لا يستمع لـpublishDiagnostics — لا تشخيصات حيّة من الخادم [SAD-01]"

    # (٦ب) تنسيق ملكيّة التشخيص [تكامل SAD-01/02]: الخادم يملك التشخيص فيتنحّى جسر فحص-الحفظ.
    #      يجب: (أ) إعداد sad.lsp.diagnostics معلَن، (ب) extension يصدّر isDiagnosticsActive،
    #      (ج) جسر SAD-02 (welcome/diagnostics.js) يستعلمه ويتنحّى — وإلّا ازدواج تشخيص لنفس الخطأ.
    props = (contrib.get("configuration", {}) or {}).get("properties", {})
    assert "sad.lsp.diagnostics" in props, \
        "إعداد sad.lsp.diagnostics غير معلَن — لا مفتاح لملكيّة التشخيص [تكامل SAD-01/02]"
    assert "isDiagnosticsActive" in js, \
        "extension.js لا يصدّر isDiagnosticsActive — جسر SAD-02 لن يعرف متى يتنحّى [تكامل SAD-01/02]"
    welcome_diag = os.path.join(ROOT, "extensions", "mihrab-welcome", "diagnostics.js")
    if os.path.isfile(welcome_diag):
        wd = _read(welcome_diag)
        assert "lspOwnsDiagnostics" in wd and "isDiagnosticsActive" in wd, \
            "جسر SAD-02 لا يتنحّى لخادم LSP (lspOwnsDiagnostics/isDiagnosticsActive) — خطر ازدواج تشخيص [تكامل SAD-01/02]"

    # (٧) المزوّدات مسجَّلة: إكمال/تحويم/تعريف [SAD-01] + الرموز الدلاليّة [SAD-07].
    for reg in ["registerCompletionItemProvider", "registerHoverProvider", "registerDefinitionProvider"]:
        assert reg in js, f"extension.js لا يسجّل {reg} — ميزة LSP ناقصة [SAD-01]"
    # [SAD-07] التلوين الدلاليّ: مزوّد مسجَّل + حارس مطابقة المفتاح (legend) يمنع التلوين الخاطئ +
    #          مُصدِر تغيّر (onDidChangeSemanticTokens) كي تظهر الألوان على الفتح البارد لا بعد أوّل تعديل.
    assert "registerDocumentSemanticTokensProvider" in js and "serverLegendMatches" in js, \
        "extension.js لا يسجّل التلوين الدلاليّ مع حارس المفتاح (registerDocumentSemanticTokensProvider/serverLegendMatches) [SAD-07]"
    assert "onDidChangeSemanticTokens" in js, \
        "المزوّد الدلاليّ بلا onDidChangeSemanticTokens — لا تلوين على الفتح البارد حتى أوّل تعديل [SAD-07]"
    proto = _read(os.path.join(ext, "lsp-protocol.js"))
    assert "SEMANTIC_TOKEN_TYPES" in proto and '"decorator"' in proto, \
        "lsp-protocol.js لا يحوي مفتاح الرموز الدلاليّة SEMANTIC_TOKEN_TYPES [SAD-07]"

    # (٧ب) أحرف تحفيز الإكمال ممرَّرة للمزوّد: بعد إصلاح wordPattern تُحفَّز أحرفُ الكلمة تلقائيًّا، لكنّ
    #      أحرف التحفيز (. : ( ،) ليست أحرف كلمة فلا يُحفَّز الإكمال بعدها إلّا بتمريرها. ثابت مسمّى.
    assert "COMPLETION_TRIGGER_CHARACTERS" in proto, \
        "lsp-protocol.js لا يعرّف COMPLETION_TRIGGER_CHARACTERS — لا أحرف تحفيز للإكمال [SAD-01]"
    assert _re.search(r"\.\.\.COMPLETION_TRIGGER_CHARACTERS", js), \
        "extension.js لا يمرّر أحرف التحفيز لمزوّد الإكمال — لا إكمال تلقائيّ بعد . : ( ، [SAD-01]"

    # (٨) مزامنة كاملة (Full) لا تزايديّة: didChange يرسل النصّ الكامل (تفادي حساب إزاحات UTF-16).
    #     نتحقّق من غياب حساب إزاحات تزايديّة عبر تأكيد إرسال contentChanges بنصّ كامل.
    assert "contentChanges" in js and _re.search(r"contentChanges:\s*\[\{\s*text:", js), \
        "مزامنة المستند ليست كاملة (contentChanges بنصّ كامل) — خطر إزاحات UTF-16 يدويّة [SAD-01]"

    # (٩) كلّ أمر معلَن في المانيفست مُسجَّل فعلًا (احتواء، مع حلّ الثوابت المسمّاة).
    manifest_cmds = {c.get("command") for c in contrib.get("commands", [])}
    _const_str = dict(_re.findall(r'const\s+([A-Za-z_$][\w$]*)\s*=\s*"([^"]+)"', js))
    js_cmds = set()
    for arg in _re.findall(r"registerCommand\(\s*([^,]+?)\s*,", js):
        arg = arg.strip()
        lit = _re.fullmatch(r"""["']([^"']+)["']""", arg)
        if lit:
            js_cmds.add(lit.group(1))
        elif arg in _const_str:
            js_cmds.add(_const_str[arg])
    missing = manifest_cmds - js_cmds
    assert not missing, f"أوامر معلَنة بلا registerCommand في sad-lang: {missing}"
    for c in contrib.get("commands", []):
        assert c.get("title"), f"أمر بلا عنوان: {c.get('command')}"

    # (١٠) إعدادات الخادم معلَنة (المسار الصريح + التتبّع + ملكيّة التشخيص).
    props = (contrib.get("configuration", {}) or {}).get("properties", {})
    assert "sad.lsp.serverPath" in props and "sad.lsp.trace" in props, \
        "إعدادات sad.lsp.serverPath/sad.lsp.trace غير معلَنة في المانيفست [SAD-01]"


# ───────── L0-18ب: [SAD-08] مزوّدٌ مُسجَّلٌ ⇐ قدرةٌ مُعلَنة · و[DAP-01] لا مُهايئَ تنقيحٍ زائف ─────────
@check("عميل ص LSP: كلّ مزوّدٍ مُسجَّلٍ له قدرةٌ مُعلَنة [SAD-08] · ولا مساهمةَ debuggers ما دام DAP-01 مُغلَقًا")
def _sad_capabilities_and_no_fake_debugger():
    import re as _re
    ext = os.path.join(ROOT, "extensions", "sad-lang")
    if not os.path.isdir(ext):
        return  # لا إضافة لغة ص في هذا الفرع — تخطٍّ
    js = _read(os.path.join(ext, "extension.js"))
    proc_js = _read(os.path.join(ext, "sad-lsp-process.js"))

    # (أ) [SAD-08] **نُعلن ما نستهلك.** كان `registerDocumentSemanticTokensProvider` مُسجَّلًا
    #     بينما `semanticTokens` غائبةٌ عن `clientCapabilities()` — مخالفةُ مواصفةٍ قائمة.
    #     والفحصُ **يربط الطرفين** لا يعدّ التسجيلات بالاسم: مزوّدٌ بلا قدرةٍ مُعلَنةٍ يمرّ
    #     اليومَ على خادمٍ متسامح، ويُكتَم غدًا على خادمٍ ملتزمٍ **بحقّ** فتموت الميزةُ صامتة.
    REGISTRATION_TO_CAPABILITY = {
        "registerCompletionItemProvider": "completion",
        "registerHoverProvider": "hover",
        "registerDefinitionProvider": "definition",
        "registerDocumentSymbolProvider": "documentSymbol",
        "registerDocumentSemanticTokensProvider": "semanticTokens",
    }
    for reg, cap in REGISTRATION_TO_CAPABILITY.items():
        if reg not in js:
            continue  # مزوّدٌ غيرُ مشحونٍ لا يُطالَب بقدرة
        assert _re.search(r"\b" + cap + r"\s*:", proc_js), (
            f"مزوّدٌ مُسجَّلٌ بلا قدرةٍ مُعلَنة: {reg} يُسجَّل في extension.js و«{cap}» غائبةٌ عن "
            f"clientCapabilities() في sad-lsp-process.js — خادمٌ ملتزمٌ يكتم القدرةَ فتموت الميزة [SAD-08]"
        )

    # (ب) [DAP-01] الحكمُ السلبيُّ على تنقيح ص **مكتوبٌ ومقيس**: خادمُ `sad --debug-server`
    #     يردّ `verified:true` على نقطة توقّفٍ ولا يُصدِر `stopped` قطّ. فمساهمةُ `debuggers`
    #     تُنتج نقطةَ توقّفٍ حمراءَ «مؤكَّدة» يمرّ البرنامجُ من فوقها — أخضرُ كاذبٌ في الواجهة.
    #     ولا يُشحَن المُهايئُ إلّا بعد رفع الحكم، ورفعُه يبدأ بحذف ملفّ الحكم هذا.
    verdict = os.path.join(ROOT, "docs", "dap-01-تنقيح-ص.md")
    ext_root = os.path.join(ROOT, "extensions")
    manifests = [
        os.path.join(ext_root, d, "package.json")
        for d in sorted(os.listdir(ext_root))
        if os.path.isfile(os.path.join(ext_root, d, "package.json"))
    ]
    with_dbg = [
        os.path.basename(os.path.dirname(m))
        for m in manifests
        if "debuggers" in (json.load(open(m, encoding="utf-8")).get("contributes", {}) or {})
    ]
    if os.path.isfile(verdict):
        assert not with_dbg, (
            f"مساهمةُ debuggers مشحونةٌ في {with_dbg} والحكمُ DAP-01 ما زال قائمًا في "
            f"docs/dap-01-تنقيح-ص.md — مُهايئٌ يبدو تنقيحًا ولا يقف عند سطر. "
            f"ارفع الحكمَ بقياسٍ جديدٍ أوّلًا، أو لا تشحن المُهايئ [DAP-01]"
        )

    # (ج) [LSP-01 · LSP-02] وحكمٌ سلبيٌّ ثانٍ كان **مكتوبًا بلا حارسٍ يقرؤه** — وهو الحالُ
    #     الذي يُنقَض بيدٍ حسنةِ النيّة: يقرأ قادمٌ أنّ الخادم يعلن `renameProvider` فيسجّل
    #     المزوّدَ في سطرٍ واحد. والمقيس: `rename` **يُفسِد ملفّ المستخدم** (يطوي «مُعلِّم»
    #     إلى «معلم»، ويكرّر المديات حرفيًّا، ويُدرِج في مواضعَ صفريّة، ويصمت بلا تحريرات)،
    #     و`references` **يُعلِّم الخطأ** بجعل الاسمين واحدًا. ورفعُ الحكم يبدأ بحذف ملفّه.
    lsp_verdict = os.path.join(ROOT, "docs", "lsp-01-02-مديات-وطيّ.md")
    FORBIDDEN_WHILE_CLOSED = ("registerRenameProvider", "registerReferenceProvider")
    if os.path.isfile(lsp_verdict):
        shipped = [r for r in FORBIDDEN_WHILE_CLOSED if r in js]
        assert not shipped, (
            f"مزوّدٌ مُغلَقٌ سلبًا صار مُسجَّلًا: {shipped} — والحكمُ LSP-01/LSP-02 قائمٌ في "
            f"docs/lsp-01-02-مديات-وطيّ.md. `rename` يُفسِد ملفّ المستخدم و`references` "
            f"يُعلِّم أنّ «معلم» و«مُعلِّم» اسمٌ واحد. ارفع الحكمَ بقياسٍ يستوفي شرطَ إعادة "
            f"الفتح المكتوبَ فيه، أو لا تُسجّل المزوّد [LSP-01]"
        )


# ───────────── L0-19: wordPattern لغة ص عربيّ-الوعي (مانع انحدار الإكمال التلقائيّ) ─────────────
@check("إعداد لغة ص: wordPattern يطابق العربيّة (كائن براية u عند \\p{}) — لا انحدار إكمال تلقائيّ")
def _sad_word_pattern():
    ext = os.path.join(ROOT, "extensions", "sad-lang")
    if not os.path.isdir(ext):
        return  # لا إضافة لغة ص في هذا الفرع — تخطٍّ
    cfg_path = os.path.join(ext, "language-configuration.json")
    assert os.path.isfile(cfg_path), "language-configuration.json مفقود في sad-lang"
    # تحميله يفحص صحّة JSON ضمنًا (هذا الملفّ خارج نطاق حارس _json_valid). [تدقيق Amelia]
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    wp = cfg.get("wordPattern")
    assert wp is not None, \
        "wordPattern غير معرَّف — لن يُكتشف المُدخَل العربيّ ككلمة فلا يُحفَّز الإكمال التلقائيّ"
    # الجذر: VS Code يجمّع wordPattern النصّيّة بـnew RegExp(s, "") بلا راية ⇒ \p{L} يُعامَل حرفيًّا
    #        فلا يطابق العربيّة. الحلّ: صيغة الكائن {pattern, flags:"u"} كي تُمرَّر الراية.
    if isinstance(wp, str):
        assert "\\p{" not in wp and "\\P{" not in wp, (
            "wordPattern صيغة نصّيّة تحوي \\p{...} — تُجمَّع بلا راية u فتُعامَل حرفيًّا ولا تطابق "
            "العربيّة (انحدار الإكمال التلقائيّ). استعمل صيغة الكائن {pattern, flags:'u'}")
        return
    assert isinstance(wp, dict) and isinstance(wp.get("pattern"), str), \
        "wordPattern كائن بلا حقل pattern نصّيّ"
    flags = wp.get("flags", "")
    assert isinstance(flags, str), "wordPattern.flags ليس نصًّا"
    if "\\p{" in wp["pattern"] or "\\P{" in wp["pattern"]:
        assert "u" in flags, (
            "wordPattern يستعمل \\p{...} دون راية u — بلا u تُعامَل حرفيًّا ولا تطابق العربيّة "
            "(انحدار الإكمال التلقائيّ). أضِف flags:'u'")
    # تعزيز سلوكيّ إن توفّر node: النمط يطابق عيّنة عربيّة «فيب» كاملةً فعليًّا. [تدقيق Amelia]
    node = shutil.which("node")
    if node:
        sample = "فيب"  # «فيب»
        script = (
            "const w=%s;const re=new RegExp(w.pattern,w.flags||'');const s=%s;"
            "const m=s.match(re);process.exit(m&&m[0]===s?0:3);"
        ) % (json.dumps(wp), json.dumps(sample))
        r = subprocess.run([node, "-e", script], capture_output=True, text=True)
        assert r.returncode == 0, \
            "wordPattern لا يطابق عيّنة عربيّة «فيب» كاملةً في Node — انحدار الإكمال التلقائيّ"


# ───────────── L0-18: امتداد نِبراس (أوامر ↔ تسجيل موزّع + «أصلِح بنِبراس» SAD-11) ─────────────
@check("امتداد نِبراس: main يصدّر activate، كلّ أمر معلَن مُسجَّل (تسجيل موزّع)، ووصل «أصلِح بنِبراس»")
def _nebras_ext():
    import re as _re
    ext = os.path.join(ROOT, "extensions", "mihrab-nebras")
    if not os.path.isdir(ext):
        return  # لا امتداد نِبراس في هذا الفرع — تخطٍّ
    pkg = json.load(open(os.path.join(ext, "package.json"), encoding="utf-8"))
    contrib = pkg.get("contributes", {})

    # (١) نقطة الدخول main موجودة وتصدّر activate.
    main_rel = pkg.get("main")
    assert main_rel, "لا حقل main في امتداد نِبراس"
    main_path = os.path.join(ext, *main_rel.lstrip("./").split("/"))
    assert os.path.isfile(main_path), f"ملفّ main مفقود: {main_rel}"
    ext_js = _read(main_path)
    assert "module.exports" in ext_js and "function activate" in ext_js, \
        "نقطة دخول نِبراس لا تصدّر activate"

    # (٢) صحّة نحو JS لملفّات الامتداد إن توفّر node.
    js_files = ["extension.js", "agent.js", "fix-diagnostic.js", "explain-selection.js",
                "chat.js", "inline-completion.js", "nebras-process.js", "rpc-client.js"]
    node = shutil.which("node")
    for jf in js_files:
        jp = os.path.join(ext, jf)
        if node and os.path.isfile(jp):
            r = subprocess.run([node, "--check", jp], capture_output=True, text=True)
            assert r.returncode == 0, f"خطأ نحويّ في {jf}:\n{r.stderr.strip()}"

    # (٣) كلّ أمر معلَن مُسجَّل — التسجيل **موزّع** عبر extension.js ووحدات الميزات (مثل fix-diagnostic.js
    #     عبر registerFixDiagnostic)، فنجمع registerCommand من كلّ ملفّات JS (مع حلّ الثوابت المسمّاة).
    manifest_cmds = {c.get("command") for c in contrib.get("commands", [])}
    assert manifest_cmds, "لا أوامر معلَنة في امتداد نِبراس"
    js_cmds = set()
    for jf in js_files:
        jp = os.path.join(ext, jf)
        if not os.path.isfile(jp):
            continue
        js = _read(jp)
        const_str = dict(_re.findall(r'const\s+([A-Za-z_$][\w$]*)\s*=\s*"([^"]+)"', js))
        for arg in _re.findall(r"registerCommand\(\s*([^,]+?)\s*,", js):
            arg = arg.strip()
            lit = _re.fullmatch(r"""["']([^"']+)["']""", arg)
            if lit:
                js_cmds.add(lit.group(1))
            elif arg in const_str:
                js_cmds.add(const_str[arg])
    missing = manifest_cmds - js_cmds
    assert not missing, f"أوامر معلَنة في مانيفست نِبراس بلا registerCommand في JS: {missing}"
    for c in contrib.get("commands", []):
        assert c.get("title"), f"أمر نِبراس بلا عنوان: {c.get('command')}"

    # (٣.٥) [AR-05] لوحة دردشة نِبراس: عربيّة **مقروءة** لا عربيّة الاتّجاه فقط.
    #   ردّ نِبراس نصٌّ مختلط بطبيعته (شرحٌ عربيّ + أسطر شيفرة لاتينيّة)، واللوحة كلّها RTL.
    #   بلا `unicode-bidi: plaintext` تُصيَّر كلّ أسطر الشيفرة في فقرةٍ RTL واحدة فتقفز أقواسها
    #   وفواصلها المنقوطة إلى الطرف المقابل — شيفرة غير قابلة للنسخ بصريًّا. ومع
    #   ‏`white-space: pre-wrap` يصير كلّ سطر **فقرة bidi** مستقلّة، فيأخذ اتّجاهه من محتواه.
    chat_path = os.path.join(ext, "chat.js")
    if os.path.isfile(chat_path):
        chat = _read(chat_path)
        assert 'lang="ar"' in chat and 'dir="rtl"' in chat, \
            "لوحة دردشة نِبراس بلا lang=ar/dir=rtl على <html> [AR-05]"
        # نتحقّق من **جسم قاعدة `.msg` نفسها** لا من ورود السلسلة في مكانٍ ما من الورقة:
        # وجودها على `#ctx` وحده كان سيُرضي فحصًا فضفاضًا بينما الفقاعات ما زالت مكسورة
        # (‏أثبتناه باختبار فشل مقصود).
        msg_rule = _re.search(r"\.msg\s*\{([^}]*)\}", chat)
        assert msg_rule, "لا قاعدة CSS للصنف .msg في لوحة نِبراس [AR-05]"
        assert "unicode-bidi: plaintext" in msg_rule.group(1), \
            ("فقاعات دردشة نِبراس (.msg) بلا `unicode-bidi: plaintext` — أسطر الشيفرة داخل "
             "الردّ العربيّ ستُبعثَر محايداتها في فقرة RTL واحدة [AR-05]")
        assert 'dir="auto"' in chat, \
            "صندوق سؤال نِبراس بلا dir=auto — لصقةُ شيفرة لاتينيّة تُفرَض عليها RTL [AR-05]"
        assert "Noto Sans Arabic" in chat, \
            ("مكدّس خطّ لوحة نِبراس بلا وجه عربيّ صريح — نظير [AR-03]: system-ui وحده لا "
             "يضمن محارف عربيّة على لينكس [AR-05]")
        # ملحوظة: فخّ الشاهدة الخلفيّة داخل قالب HTML (تُنهي القالب ⇒ SyntaxError) **مغطّى
        # أصلًا** بفحص الصحّة النحويّة العامّ في هذا الملفّ — تحقّقنا بفشل مقصود — فلا نكرّره.

    # (٤) [SAD-11] «أصلِح بنِبراس» موصول فعلًا: extension.js يستدعي registerFixDiagnostic (وإلّا يبقى
    #     الأمر مُسجَّلًا في وحدة غير مستدعاة ⇒ «command not found» زمن التشغيل رغم خضرة L0).
    # نطابق **النداء** `registerFixDiagnostic(` لا مجرّد الاسم (كي لا يُرضي الحارسَ سطرُ الاستيراد
    # وحده لو حُذف الاستدعاء الفعليّ). [تشديد مراجعة Amelia]
    assert _re.search(r"registerFixDiagnostic\s*\(", ext_js), \
        "extension.js لا يستدعي registerFixDiagnostic(...) — «أصلِح بنِبراس» غير موصول [SAD-11]"
    assert "mihrab.nebras.fixDiagnostic" in manifest_cmds, \
        "أمر mihrab.nebras.fixDiagnostic غير معلَن في مانيفست نِبراس [SAD-11]"

    # (٥) cwd الخادم = جذر مساحة العمل: الخادم يشتقّ workspaceRoot من process.cwd()، فلا بدّ أن يُمرَّر
    #     cwd (من resolveWorkspaceCwd) إلى cp.spawn — وإلّا يرث مجلّد إطلاق المحرّر فتُرفَض ملفّات المشروع
    #     بـ«المسار خارج مجلّد العمل». حذف الوصلة انحدار صامت (لا اختبار وحدة يمسّ خيارات spawn). [تدقيق Amelia]
    proc_js = _read(os.path.join(ext, "nebras-process.js"))
    # cwd يُحسب من resolveWorkspaceCwd (مع توجيهٍ صريح اختياريّ _cwdOverride من retargetRoot قبله في نفس التعبير).
    assert "resolveWorkspaceCwd" in proc_js and _re.search(r"const\s+cwd\s*=[^;\n]*resolveWorkspaceCwd\(", proc_js), \
        "nebras-process.js لا يحسب cwd من resolveWorkspaceCwd — جذر عمل الوكيل سيكون مجلّد إطلاق المحرّر"
    # إعادة توجيه الجذر (ملفّ مفرد/جذر غير أوّل): retargetRoot معرَّفة في المدير ومستهلَكة في تجهيز الوكيل.
    agent_js_src = _read(os.path.join(ext, "agent.js"))
    assert "retargetRoot" in proc_js and _re.search(r"retargetRoot\s*\(", agent_js_src), \
        "إعادة توجيه الجذر غير موصولة (retargetRoot في nebras-process/agent) — الملفّ المفرد/الجذور غير الأولى ستُرفَض"
    # النمط يُلزِم `cwd` **كمفتاح خيار** (يليه , أو : أو }) داخل نداء spawn نفسه (حتى أوّل ;) —
    # لا مجرّد ورود الكلمة (تعليق «// cwd …» داخل النداء كان يُرضي النمط القديم زورًا).
    assert _re.search(r"cp\.spawn\([^;]*?\bcwd\b\s*[,:}]", proc_js), \
        "nebras-process.js لا يمرّر cwd إلى cp.spawn — الوكيل سيرفض ملفّات المشروع «خارج مجلّد العمل»"
    # عند تغيّر مجلّد العمل أثناء الجلسة: إعادة تشغيل كي لا يبقى الخادم بـcwd بائت. [تدقيق Amelia — فجوة (ج)]
    assert "onDidChangeWorkspaceFolders" in ext_js and "restartIfWorkspaceChanged" in ext_js, \
        "extension.js لا يعيد تشغيل نِبراس عند تغيّر مجلّد العمل (onDidChangeWorkspaceFolders/restartIfWorkspaceChanged) — cwd بائت"


@check("معجم عناوين الإعدادات: موصول، بلا مفاتيح مكرّرة، وبلا نصفِ ترجمة")
def _settings_lexicon_sound():
    """يحرس رقعةَ تعريب عناوين لوحة الإعدادات — وأخطرُ ما فيها يقع صامتًا.

    **المفاتيح المكرّرة** هي العطبُ الأوّل: خريطتان تُبنيان من `Object.entries`، فمفتاحٌ
    مكرّرٌ لا يُخطئ وقتَ التشغيل — الأخيرُ يفوز والأوّلُ يختفي. وقع هذا فعلًا (ثمانيةُ
    مفاتيح) ولم يكشفه إلّا التصريفُ بـ‏`tsc` (‏TS1117). لكنّ التصريفَ يجري في بناءٍ
    كاملٍ يستغرق عشراتِ الدقائق، فالحارسُ هنا يزيحه إلى ثانيةٍ واحدة.

    **الوصل** هو العطبُ الثاني، وهو صامتٌ أيضًا: معجمٌ سليمٌ لا يُستدعى = واجهةٌ
    إنجليزيّةٌ وكلُّ الفحوص خضراء.

    **إملاء حرف الجرّ** ثالثًا: «بـالدفع» و«لـالمحرّر» خطأٌ صريحٌ يراه المستخدم في كلّ
    بندٍ تولّده القاعدة، فنمنع كتابةَ التطويل قبل «ال» في القوالب.
    """
    import importlib.util
    import re as _re

    MARKED = "mihrab-settings-lexicon"
    patcher = os.path.join(BUILD, "patch_settings_labels.py")
    if not os.path.isfile(patcher):
        return  # لا رقعة في هذا الفرع — تخطٍّ

    lex_path = os.path.join(ROOT, "patches", "core", "mihrabSettingsLexicon.ts")
    assert os.path.isfile(lex_path), (
        "patches/core/mihrabSettingsLexicon.ts مفقود — الرقعة تستورده ولا تنسخه.")
    lex = _read(lex_path)

    # ── مفاتيح مكرّرة داخل كلّ خريطة على حدة ──
    for map_name in ("PHRASES", "WORDS", "ADJECTIVES"):
        i = lex.find(f"const {map_name} = new Map")
        assert i >= 0, f"{map_name} غير معرَّفة في المعجم."
        j = lex.find("}))", i)
        assert j > i, f"لم أجد نهاية {map_name}."
        keys = _re.findall(r"^\t'([^']+)':", lex[i:j], _re.M)
        dupes = sorted({k for k in keys if keys.count(k) > 1})
        assert not dupes, (
            f"{map_name}: مفاتيح مكرّرة {dupes} — الأخير يفوز صامتًا وقتَ التشغيل "
            f"(‏tsc يرفضها بـTS1117، لكنّ ذلك بعد بناءٍ كامل).")
        assert keys, f"{map_name} فارغة."
        # لا مفتاحَ بحروفٍ كبيرة: البحثُ يجري بـtoLowerCase فمفتاحٌ كبيرٌ ميّتٌ أبدًا.
        upper = [k for k in keys if k != k.lower()]
        assert not upper, (
            f"{map_name}: مفاتيح بحروفٍ كبيرة {upper[:5]} — المطابقة تجري بعد "
            f"toLowerCase فهي شيفرةٌ ميّتة.")

    # ── القيم عربيّة فعلًا (قيمةٌ لاتينيّة = ترجمةٌ منسيّة تمرّ صامتة) ──
    vals = _re.findall(r"^\t'[^']+': '([^']*)',", lex, _re.M)
    assert vals, "لم أستخرج أيّ قيمة من المعجم — تغيّر شكلُ الملفّ؟"
    non_ar = [v for v in vals if not _re.search(r"[؀-ۿ]", v)]
    assert not non_ar, f"قيمٌ بلا حرفٍ عربيّ: {non_ar[:5]}"

    # ── إملاء حرف الجرّ: لا تطويلَ قبل «ال» في أيّ قالب ──
    # محصورٌ في كتلة القواعد وحدها: التوثيقُ أعلاه يقتبس الخطأَ ليشرحه، فبحثٌ في
    # الملفّ كلّه كان سيصطاد شرحَ العطب بدل العطب.
    _ri = lex.find("const RULES")
    _rj = lex.find("\n];", _ri)
    rules_block = lex[_ri:_rj] if _ri >= 0 else ""
    assert rules_block, "لم أجد كتلة RULES في المعجم."
    bad = _re.findall(r"[بل]ـال", rules_block)
    assert not bad, (
        "قالبٌ يكتب «بـال/لـال» — الصواب «بال» و«لل» عبر joinPreposition.")
    assert "function joinPreposition" in lex, (
        "joinPreposition مفقودة — قواعدُ Allow/For ستُنتج «بـالدفع».")

    # ── الوصل: نسخٌ في build.sh، واستدعاءٌ في كتلة الحقن ──
    build_sh = _read(os.path.join(BUILD, "build.sh"))
    assert "patch_settings_labels.py" in build_sh, (
        "build.sh لا ينسخ patch_settings_labels.py إلى شجرة المنبع.")
    bundle = _read(os.path.join(BUILD, "patch_bundle_extensions.py"))
    assert ".mihrab-patch-settings-labels.py ." in bundle, (
        "كتلة الحقن لا **تستدعي** رقعة عناوين الإعدادات — نسخٌ بلا تشغيل: كلّ الفحوص "
        "خضراء وعناوينُ الإعدادات تبقى إنجليزيّة.")

    src = _read(patcher)
    assert "arabizeSettingText" in src and "wordifyKey" in src, (
        "المرقِّع لا يشير إلى wordifyKey/arabizeSettingText — انجرفت الرقعة عن هدفها.")

    # ── المرساة موجودة في المنبع **فعلًا** ──
    # الصيغةُ الأولى من هذا الفحص كانت تقرأ نصَّ المرقِّع وتزعم أنّها تفحص المنبع —
    # فحصٌ يُطمئن ولا يكشف شيئًا (رصدته المراجعة الهندسيّة). هنا نقرأ ملفَّ المنبع
    # نفسَه، فينكشف انجرافُ `wordifyKey` عند ترقية المنبع لا بعد ساعةِ بناءٍ ضائعة.
    # **وكلُّ مرساةٍ تُقاس في ملفِّها هي.** كانت هذه الحلقةُ تقرأ `preferences.ts` وحدَه
    # ثمّ تفحص فيه مراسيَ **كلِّ** ملفّات المرقِّع — ومنها مرساةٌ تخصّ
    # ‏`preferencesModels.ts`. فبقيت خضراءَ على 1.121 بمصادفةِ ورودِ النصّ في الملفّين،
    # واحمرّت عند الترقية إلى 1.126 على انجرافٍ **لم يقع**: المرساةُ في مكانها من ملفّها،
    # والمرقِّعُ يطبّق (L1 أخضر). وحارسٌ يسمّي عطبًا غيرَ واقعٍ يُرسِل القارئَ إلى إصلاح
    # ما ليس مكسورًا — وهو أسوأُ من صمته.
    spec = importlib.util.spec_from_file_location("_mihrab_settings_labels", patcher)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for _rel, _mark, edits in mod.FILES:
        upstream = os.path.join(ROOT, ".upstream", "vscode", *_rel.split("/"))
        if not os.path.isfile(upstream):
            continue
        text = _read(upstream)
        if MARKED in text:      # مُرقَّعٌ سلفًا — المراسي استُهلكت
            continue
        for old, _new, count in edits:
            found = text.count(old.replace("\n", "\r\n")) + text.count(old)
            assert found >= count, (
                f"مرساةٌ مفقودة من منبع {_rel} (وُجدت {found}/{count}): "
                f"{old.splitlines()[0][:80]} — انجرف المنبع؟")


@check("جالبُ أدوات ص يطابق كلَّ صيغِ تسمية الأصول")
def _fetcher_matches_asset_naming():
    """‏**عطبٌ قِسناه لا افترضناه:** الجالبُ كان يبني رمزًا واحدًا (`windows-x64`) من
    ‏`uname`، وسيرُ عمل إصدار اللغة على فرعه الرئيسيّ يسمّي `…-windows-x86_64.zip`
    و`…-linux-aarch64.tar.gz`. فأوّلُ إصدارٍ يُوسَم يجعل الجالبَ يخرج بـ3 «لا أصلَ
    لهذه المنصّة» — و**خطوةُ الجلب في CI فيها `continue-on-error`**، فالنشرُ يمضي
    بحزمةٍ بلا لغة. شغّلنا النسخةَ السابقة على أسماءٍ اصطناعيّةٍ بالصيغة الجديدة فخرجت
    بـ3 فعلًا، والحاليّةُ جلبت ٤/٤. هذا الفحصُ يمنع عودةَ الصيغة الواحدة صامتةً."""
    src = _read(os.path.join(ROOT, "build", "fetch_sad_tools.sh"))
    # **من كتلةِ الرموز لا من الملفّ كلِّه**: أوّلُ صيغةٍ لهذا الفحص بحثت في النصّ
    # الكامل، فبقيت خضراءَ بعد حذفِ `windows-x86_64` من `TOKENS` — لأنّها مذكورةٌ في
    # تعليقٍ فوقها. قِسنا ذلك بالتحوير، فصار الفحصُ يقرأ الكتلةَ وحدَها.
    block = src.split('case "$PLATFORM/$ARCH" in', 1)
    assert len(block) == 2, "لم تعد كتلةُ رموز المنصّة في الجالب — أين تُبنى TOKENS؟"
    block = block[1].split("esac", 1)[0]
    for pair in (("windows-x86_64", "windows-x64"), ("linux-x86_64", "linux-x64"),
                 ("linux-aarch64", "linux-arm64")):
        for tok in pair:
            assert tok in block, (
                f"جالبُ أدوات ص لا يطابق «{tok}» — إصدارٌ يسمّي أصلَه بها يُقرأ "
                f"«لا أصلَ لهذه المنصّة»، وينشر محرابٌ بلا لغة.")
    # أفضليّةُ العائلة: `sad-full` قبل `sadc`، وإلّا وقع الاختيارُ على حزمةِ مترجمٍ
    # وحدَها فخرج محرابٌ يبني ولا يشغّل.
    fams = src.split("for family in", 1)
    assert len(fams) == 2, "لم تعد حلقةُ أفضليّةِ العائلات في الجالب — أين تُختار الأصول؟"
    line = fams[1].splitlines()[0]
    assert line.index("sad-full") < line.index("sadc"), (
        "‏`sadc` صارت قبل `sad-full` في أفضليّة الأصول — حزمةُ مترجمٍ بلا مفسّر.")


# ───────────────────────── شاهدُ التفعيل ─────────────────────────
# ‏**فحصٌ لا يُنفِّذ توكيدًا واحدًا يقيس صفرًا** — وهو أخضرُ إلى الأبد.
#
# هذا `PF-02` (ثراءُ العيّنة) مطبَّقًا على حرّاس L0: هناك يُرصَد تعبيرٌ نمطيٌّ طُبِّق ولم
# يطابق قطّ، وهنا يُرصَد **فحصٌ رُكِّب ولم يقِس شيئًا**. والحبّةُ في `mutation.mjs` أخشنُ
# من أن تراه: `lint_patchers.py` **ملفٌّ واحد** في عدّ الحرّاس وفيه ستّون فحصًا، فأيُّ
# فحصٍ يولد لا يرى شيئًا يمرّ بلا شاهد — وهي عينُ الفجوة التي أُمسِكت في حلقة
# `node --test`، مكرَّرةً بحجمٍ أكبر.
#
# والقياسُ مباشر: تُتعقَّب أسطرُ هذا الملفّ المنفَّذةُ في كلّ فحص، ويُقاطَع الناتجُ بأسطرِ
@check("رُقَعُ النواة: رأسُ كلّ جزءٍ يطابق عدَّ أسطره (‏@@‎ لا يُحسَب باليد)")
def _core_patch_hunk_headers_are_consistent():
    """‏`git apply` يرفض الرقعةَ كلَّها برسالة «corrupt patch at line N» إن كذب الرأس.

    وقد وقع: عُدِّل جزءٌ في `010-editor-text-direction.patch` وحُسِب الرأسُ باليد فزاد
    سطرًا، فمات البناءُ بعد ثلاث دقائق برسالةٍ تشير إلى **رقمِ سطرٍ في الرقعة** لا إلى
    الرأس الكاذب. والفحصُ هنا يمسكه في جزءٍ من ثانيةٍ ويسمّي الجزءَ والفرق.

    والعدُّ يتخطّى `\\ No newline at end of file` — سطرُ بيانٍ لا سطرُ محتوى.
    """
    core = os.path.join(ROOT, "patches", "core")
    patches = sorted(f for f in os.listdir(core) if f.endswith(".patch"))
    assert patches, "لا رُقَعَ نواةٍ في patches/core — الفحصُ يحرس العدم."
    hunks_seen = 0
    bad = []
    for name in patches:
        lines = _read(os.path.join(core, name)).split("\n")
        i = 0
        while i < len(lines):
            m = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[i])
            if not m:
                i += 1
                continue
            hunks_seen += 1
            want_old = int(m.group(2) or 1)
            want_new = int(m.group(4) or 1)
            old = new = 0
            j = i + 1
            while j < len(lines):
                L = lines[j]
                if L[:2] == "@@" or L[:11] == "diff --git " or L[:6] == "index " \
                        or L[:4] == "--- " or L[:4] == "+++ ":
                    break
                if L[:1] == chr(92):        # ‏\ No newline at end of file
                    j += 1
                    continue
                if L[:1] == "-":
                    old += 1
                elif L[:1] == "+":
                    new += 1
                elif L[:1] == " ":
                    old += 1
                    new += 1
                else:
                    break               # سطرٌ فارغٌ في الذيل أو نصٌّ غريب: نهايةُ الجزء
                j += 1
            if (old, new) != (want_old, want_new):
                bad.append(name + " سطر " + str(i + 1) + ": الرأسُ يقول -"
                           + str(want_old) + " +" + str(want_new) + " والعدُّ -"
                           + str(old) + " +" + str(new))
            i = j
    assert hunks_seen >= 20, (
        str(hunks_seen) + " جزءًا فقط عُدَّ في " + str(len(patches)) + " رقعة — "
        "المِسطرةُ لا تقرأ الرُقَع، وكلُّ توكيدٍ بعدها يمرّ على العمى.")
    assert not bad, ("رؤوسُ أجزاءٍ لا تطابق عدَّ أسطرها ⇒ `git apply` يرفض الرقعةَ "
                     "كلَّها: " + " · ".join(bad))


@check("مسارُ رسم الطرفيّة `off` [DR-05/ب] — ‏WebGL يرسم خليّةً خليّةً فلا تتّصل العربيّة")
def _terminal_gpu_is_off():
    """‏`DR-05` أقفل مسارَ **المحرّر** الرسوميّ بحجّة «طبقةُ GPU بلا معالجة اتّجاه».

    والحجّةُ نفسُها لم تكن مطبَّقةً على الطرفيّة — وهي السطحُ الذي يقرأ فيه المستخدمُ
    مخرَجَ برنامجه. وافتراضُ المنبع `auto` ⇒ WebGL، وقِيس على المشحون: أربعُ لوحاتِ
    رسمٍ وصفرُ صفوفٍ في DOM. ومسارُ WebGL يرسم من **أطلسِ رسومٍ خليّةً خليّة**، فالوصلُ
    السياقيُّ العربيُّ مستحيلٌ بنيويًّا: «مرحبا» ستّةُ حروفٍ منفصلة. وبلّغ المستخدمُ عنه
    بالاسم: «الحروف مقطعة».

    والحارسُ يمنع سقوطَ المفتاح صامتًا: إسقاطُه لا يرمي خطأً ولا يكسر بناءً — تعود
    الطرفيّةُ إلى WebGL وتتقطّع الحروفُ من جديد، ولا حارسَ حيًّا يبلغ هذا السطح.

    ويُقاس مع `editor.experimentalGpuAcceleration`: الحجّةُ واحدةٌ، فانفرادُ أحدهما
    بالقفل يعني أنّ الآخرَ سقط بلا قرار.
    """
    shell = os.path.join(ROOT, "extensions", "mihrab-shell", "package.json")
    assert os.path.isfile(shell), "‏mihrab-shell/package.json مفقود — الفحصُ يحرس العدم."
    defaults = json.load(open(shell, encoding="utf-8")).get(
        "contributes", {}).get("configurationDefaults", {})
    assert len(defaults) >= 20, (
        "‏" + str(len(defaults)) + " مفتاحًا فقط في configurationDefaults — الجردُ لا يُقرأ، "
        "وكلُّ توكيدٍ بعده يمرّ على العمى.")
    term = defaults.get("terminal.integrated.gpuAcceleration")
    assert term == "off", (
        "‏`terminal.integrated.gpuAcceleration` = " + repr(term) + " لا `off` — الطرفيّةُ "
        "ترسم بـWebGL خليّةً خليّةً من أطلسِ رسوم، فتتقطّع الحروفُ العربيّة [DR-05/ب].")
    ed = defaults.get("editor.experimentalGpuAcceleration")
    assert ed == "off", (
        "‏`editor.experimentalGpuAcceleration` = " + repr(ed) + " لا `off` — الحجّةُ واحدةٌ "
        "للسطحين، وانفرادُ الطرفيّة بالقفل يعني أنّ المحرّرَ سقط بلا قرار [DR-05].")


@check("خلطُ الكتابتَين [AR-05]: الرقعةُ تُحاكى فتُقاس — لا يكفي وجودُها")
def _unicode_script_mixing_patch_behaves():
    """يشتقّ مُسنَدَ «هذا خلطُ كتابتَين» **من نصّ الرقعة** ثمّ يشغّله على عيّناتٍ مسمّاة.

    **لماذا محاكاةٌ لا تفتيشُ نصّ.** رقعةٌ تُطبَّق بنجاحٍ وشكلُها سليمٌ قد تكون قد قلبت
    المعنى: توسيعُ المُسنَد يُعفي الكلمةَ المختلطةَ حقًّا فيسقط كشفُ الانتحال — وهو **أخضرُ
    كاذبٌ** لا يمسكه إلّا عدُّ الاتّجاهين معًا. ولذلك التوكيداتُ هنا **من الطرفين**:
    ‏`حقل_اسم` يجب أن يصير صفرًا، و`exampاe` يجب أن **يبقى** واحدًا.

    والمُسنَدُ لا يُكتَب هنا بل يُنتزَع من الأسطر المضافة في الرقعة، فمُصابٌ يبدّل
    `isLowerAsciiLetter` بـ`isBasicASCII` يغيّر خرجَ المحاكاة لا شكلَها.

    وجدولُ الالتباس يُشتقّ من `strings.ts` في المنبع المثبَّت لا يُكتَب بالحدس: لو أضاف
    المنبعُ نقطةً عربيّةً جديدةً إلى `_common` تغيّرت الأرقامُ هنا صوتًا لا صمتًا.
    """
    patch = os.path.join(ROOT, "patches", "core",
                         "033-unicode-word-script-mixing.patch")
    if not os.path.isfile(patch):
        raise AssertionError(
            "لا رقعةَ `033-unicode-word-script-mixing.patch` — يعود المستطيلُ الأصفرُ حول "
            "كلّ ألفٍ وهاءٍ في معرّفات ص خارجَ `[sad]` (‏622 مرسومًا في مفردات.yaml) [AR-05]")
    body = _read(patch)

    # (أ) المِرساةُ المنبعيّة **وشرطُ عدم الإضعاف معًا**. كانت الرقعةُ تحذف عدّادَ المنبع
    #     `hasBasicASCIICharacters` حذفًا، وكان هذا التوكيدُ يشترط الحذف — أي أنّه كان
    #     يحرس تصميمًا **أضعف**: العدّادُ نفسُه يبوّب فحصَ المحارف الخفيّة (دفاعُ
    #     Trojan Source)، فحذفُه يُرخي البوّابتَين معًا وإحداهما ليست من شأن الشكوى.
    #
    #     وصُحّح في جولة microsoft/vscode: العدّادُ **يبقى** للمحارف الخفيّة، ويُضاف
    #     `hasBasicASCIILetters` وحدَه لفحص الالتباس. فالتوكيدُ اليومَ من طرفَين: السطرُ
    #     المنبعيُّ حاضرٌ **سياقًا** (فالرقعةُ ترسو على الموضع المقصود)، و**غيرُ محذوف**
    #     (فالدفاعُ الآخرُ لم يُمَسّ). ومُصابٌ يحذفه يسقط هنا صوتًا لا صمتًا.
    _UPSTREAM_COUNTER = ("				hasBasicASCIICharacters = "
                         "hasBasicASCIICharacters || isBasicASCII;")
    assert (" " + _UPSTREAM_COUNTER) in body, (
        "سطرُ `hasBasicASCIICharacters || isBasicASCII` ليس سياقًا في الرقعة — انجرف "
        "المنبعُ أو رُقِّع موضعٌ آخر، فما يلي من محاكاةٍ يقيس شيئًا لا يقع [AR-05]")
    assert ("-" + _UPSTREAM_COUNTER) not in body, (
        "الرقعةُ تحذف عدّادَ `hasBasicASCIICharacters` — وهو يبوّب فحصَ المحارف الخفيّة "
        "لا فحصَ الالتباس. حذفُه يُرخي دفاعَ Trojan Source بلا داعٍ: الشكوى في الالتباس "
        "وحدَه، وله عدّادُه `hasBasicASCIILetters` [AR-05]")

    # (ب) انتزاعُ المُسنَد من الأسطر المضافة — لا يُكتَب هنا فيُقاس نفسَه.
    m = re.search(r"\+\s*hasBasicASCIILetters = hasBasicASCIILetters(.*?);",
                  body, re.S)
    assert m, ("لا إسنادَ لـ`hasBasicASCIILetters` في الأسطر المضافة — تغيّر شكلُ الرقعة "
               "فعمِيَ الانتزاع، والمحاكاةُ بلا مُسنَدٍ منتزَعٍ حارسٌ يقيس نفسَه [AR-05]")
    expr = re.sub(r"[\r\n+\t ]", "", m.group(1))
    TOKENS = {
        "||strings.isLowerAsciiLetter(codePoint)": lambda c: "a" <= c <= "z",
        "||strings.isUpperAsciiLetter(codePoint)": lambda c: "A" <= c <= "Z",
        "||strings.isAsciiDigit(codePoint)": lambda c: "0" <= c <= "9",
        "||isBasicASCII": lambda c: ord(c) < 128,
        "||false": lambda c: False,
        "||true": lambda c: True,
    }
    preds, rest = [], expr
    while rest:
        for tok, fn in TOKENS.items():
            if rest.startswith(tok):
                preds.append(fn)
                rest = rest[len(tok):]
                break
        else:
            raise AssertionError(
                f"جزءٌ من مُسنَد خلط الكتابتَين لم يُقرأ: «{rest}» — لا يُحاكى ما لا يُفهَم، "
                "والفشلُ هنا أسلمُ من نجاحٍ يقيس غيرَ المشحون [AR-05]")
    assert preds, "مُسنَدٌ فارغ [AR-05]"

    def mixes(word):
        return any(p(c) for c in word for p in preds)

    # (ج) جدولُ الالتباس من مصدره — وشاهدُ تفعيلٍ موجَبٌ قبل أيّ توكيدٍ سالب.
    st = os.path.join(ROOT, ".upstream", "vscode", "src", "vs", "base", "common",
                      "strings.ts")
    if not os.path.isfile(st):
        return                      # لا منبعَ مثبَّتًا: يُفحَص الشكلُ ولا يُدَّعى القياس
    src = _read(st)
    i = src.find('\'{\\"_common\\"')
    j = src.find("]}'", i)
    assert i > 0 and j > i, "تعذّر انتزاعُ جدول الالتباس من strings.ts [AR-05]"
    data = json.loads(src[i + 1:j + 2].replace('\\"', '"'))
    amb = set()
    for key in ("_common", "_default"):
        arr = data[key]
        amb.update(chr(arr[k]) for k in range(0, len(arr), 2))
    assert "ا" in amb and "ه" in amb, (
        "الألفُ والهاءُ ليستا في جدول الالتباس المنبعيّ — إمّا أُصلح المنبعُ (فتسقط الرقعةُ "
        "كلُّها) أو عمِيَ الانتزاع. كلُّ توكيدٍ بعد هذا يمرّ على العمى [AR-05]")

    SEP = set("`~!@#$%^&*()-=+[{]}" + chr(92) + "|;:'\",.<>/?،؛؟٪۔؞؍٭«»﴿﴾") | set(" \t\r\n")

    def sim(text):
        """قاعدةُ المنبع كما هي، بمُسنَدِ الخلط المنتزَع من الرقعة."""
        n, w = 0, []
        for ch in list(text) + [" "]:
            if ch in SEP:
                if w:
                    word = "".join(w)
                    weird = any(ord(c) > 127 and c not in amb for c in word)
                    if not (not mixes(word) and weird):
                        n += sum(1 for c in word if ord(c) > 127 and c in amb)
                w = []
            else:
                w.append(ch)
        return n

    # (د) الطرفُ الأوّل: معرّفاتُ ص تُعفى. (العَرَضُ الذي بلّغ عنه مستخدم.)
    for word in ("حقل_اسم", "خط_مائل", "نصاب_الفضة", "40_تعابير", "اكتب_ذاكرة"):
        assert sim(word) == 0, (
            f"«{word}» ما زال يُبرَز — الشَرطةُ السفليّةُ والأرقامُ غِراءُ معرّفاتٍ لا خلطَ "
            "كتابتَين، والرقعةُ لم تُسقِط المستطيلَ الأصفر [AR-05]")

    # (هـ) الطرفُ الثاني — **وهو ما يمنع الأخضرَ الكاذب**: الخلطُ الحقيقيُّ يبقى مكشوفًا.
    for word, why in (("exampاe", "ألفٌ عربيّةٌ في معرّفٍ لاتينيّ"),
                      ("faiا", "الحيلةُ نفسُها أقصر"),
                      ("contro١", "رقمٌ عربيٌّ يشبه l"),
                      ("pаssword", "«а» سيريليّة"),
                      ("pcb_ديناميّ", "لاتينيٌّ وعربيٌّ في معرّفٍ واحد"),
                      ("صادx", "عربيٌّ ولاتينيٌّ ملتصقان")):
        assert sim(word) >= 1, (
            f"«{word}» لم يعد يُشخَّص ({why}) — وُسِّع المُسنَدُ فأُعفيت الكلمةُ المختلطةُ "
            "حقًّا. هذا **إسقاطُ حمايةٍ** لا إسكاتَ ضجيج [AR-05]")

    # (و) حدُّ الرقعة مكتوبٌ توكيدًا لا نثرًا: كلمةٌ كلُّها ملتبسٌ لا يطالها بندُ الهروب
    # بأيّ صياغة، فتبقى مُشخَّصةً خارج `[sad]`. تثبيتُه هنا يمنع ادّعاءً أوسعَ من المُنجَز.
    assert sim("٥٥") == 2, (
        "تغيّر سلوكُ «٥٥» — حدُّ الرقعة المُعلَن أنّها لا تطال الأرقامَ العربيّةَ المفردة "
        "في النثر. تغيُّرُه يعني أنّ الوثيقةَ صارت تكذب [AR-05]")


@check("اتّجاهُ الطرفيّة [DR-08]: الورقةُ ورقعةُ xterm **معًا** — لا واحدةَ بلا أختها")
def _terminal_direction_sheet_and_patch_are_paired():
    """أخطرُ حالةٍ هنا ليست غيابَهما بل **وجودُ إحداهما وحدَها**.

    الورقةُ تقلب التخطيطَ، ورقعةُ `patch_xterm_bidi.py` تقلب حسابَ الأعمدة. فإن
    شُحنت الورقةُ بلا الرقعة رأى المستخدمُ نصًّا عربيًّا صحيحًا **وحدَّد غيرَه** عند
    النقر (قِيس قبل الرقعة: نقرةٌ عند x=975 ⇒ تحديدٌ عند x=166). وإن شُحنت الرقعةُ
    بلا الورقة فلا صفَّ يمينيًّا أصلًا، فتقيس شيئًا لا يقع.

    ولذلك الاقترانُ نفسُه هو المفحوص، لا كلٌّ على حدة.
    """
    sheet = _read(os.path.join(ROOT, M.CSS_PATCH))
    # شاهدُ تفعيلٍ موجَب: المِسطرةُ ترى الورقةَ أصلًا قبل أيّ تأكيدٍ عليها.
    assert sheet.count("monaco-workbench[dir=") >= 10, (
        "ورقةُ الاتّجاه لا تُقرأ كما يُتوقَّع — كلُّ توكيدٍ بعدها يمرّ على العمى.")

    parts = {
        "direction: rtl على الشاشة": ".monaco-workbench[dir=\"rtl\"] .xterm-screen,",
        "unicode-bidi: plaintext للصفّ": "unicode-bidi: plaintext;",
        "display: inline للعناصر": ".monaco-workbench[dir=\"rtl\"] .xterm-rows span {",
    }
    have_sheet = [k for k, v in parts.items() if v in sheet]
    assert "direction: ltr;" not in sheet.split(".xterm-screen,")[1][:200], (
        "ورقةُ الاتّجاه عادت تفرض `direction: ltr` على الطرفيّة — وهي الحجّةُ التي "
        "سقطت بعد ترقيع حساب الأعمدة [DR-08].")

    patcher = os.path.join(BUILD, "patch_xterm_bidi.py")
    have_patch = os.path.isfile(patcher)
    # موصولٌ لكلِّ شجرةِ خرجٍ تُشحَن — المكتبيُّ **والويب** — لا مرّةً واحدةً في أيِّهما.
    # ووجودُ الاسم في build.sh لم يعد يكفي: بعد أن صار النداءُ مرّتين، صار مُصابُ PF-03
    # (‏terminal-bidi-patch-unwired) يفصل نداءَ المكتبيّ والحارسُ يبقى أخضرَ على نداء
    # الويب — أي حارسٌ يقيس وجودَ اسمٍ لا وصلَ رقعة. فيُطلَب الوجهان بالاسم.
    _bsh = _read(os.path.join(BUILD, "build.sh"))
    _targets = ("$APP_DIR", "$WEB_DIR")
    _unwired = [t for t in _targets
                if 'patch_xterm_bidi.py" "' + t + '"' not in _bsh]
    wired = not _unwired

    if len(have_sheet) == 3 and have_patch and wired:
        # والرقعةُ مقيّدةٌ بإصدارٍ مثبَّت: المُصغِّرُ يبدّل الأسماءَ بين النسخ.
        body = _read(patcher)
        assert 'SUPPORTED_VERSION = "' in body, (
            "رقعةُ xterm بلا حارسِ إصدار — ترقيعُ نصٍّ مصغَّرٍ بلا تثبيتِ نسخةٍ مقامرة.")
        assert "لا مرّةً واحدة" in body, (
            "رقعةُ xterm لا تشترط وقوعَ كلّ مِرساةٍ مرّةً واحدة — قد تُرقّع موضعًا لم يُقرأ.")
        return

    missing = [k for k in parts if k not in have_sheet]
    raise AssertionError(
        "اقترانُ [DR-08] مكسور — والنصفُ أسوأُ من العدم: "
        + ("ناقصٌ من الورقة: " + " · ".join(missing) + ". " if missing else "")
        + ("والمُرقِّع `build/patch_xterm_bidi.py` مفقود. " if not have_patch else "")
        + ("وغيرُ موصولٍ بـbuild.sh لـ: " + " · ".join(_unwired) + ". " if _unwired else ""))


@check("رقعةُ الاتّجاه: جذرُ المحرّر مثبَّتٌ على ltr **بلا شرط** [DR-07]")
def _editor_root_direction_is_unconditional():
    """يمنع عودةَ عطبٍ شُوهد في المشحون: نصٌّ مُصيَّرٌ خارجَ الشاشة.

    النظامُ الإحداثيُّ الداخليُّ للمحرّر يساريٌّ ماديًّا — الأبناءُ المطلقون يوضَعون
    بإزاحات `left` داخل حاويةٍ عرضُها ‎16777216‎ بكسل. فجذرٌ يُحسَب `direction: rtl`
    يرسو بهم في أقصى يمين تلك الحاوية: قِيس `‎.view-lines` عند `x = 16776322`،
    فاختفى كلُّ محرفٍ وبقيت أرقامُ الأسطر وحدَها ظاهرة.

    وكانت القاعدةُ مقصورةً على `.text-direction-rtl`، فبقي المحرّرُ **اليساريّ** داخل
    مستندٍ يمينيّ (‏`<html dir="rtl">` — وهو حالُ محرابٍ دائمًا) يرث `rtl` ويقع في
    العطب نفسِه. ويصيب ذلك كلَّ لغةٍ يفرض عليها `mihrab-shell` اتّجاهًا يساريًّا
    [DR-02] — ‏`html` و`javascript` و`python` و`json`… أي أكثرَ ما يُفتَح.
    """
    p = os.path.join(ROOT, "patches", "core", "010-editor-text-direction.patch")
    assert os.path.isfile(p), "رقعةُ اتّجاه المحرّر مفقودة: " + p
    body = _read(p)
    # شاهدُ تفعيلٍ موجَب: المِسطرةُ ترى ورقةَ أنماط المحرّر داخل الرقعة أصلًا.
    assert "b/src/vs/editor/browser/widget/codeEditor/editor.css" in body, (
        "لا جزءَ لـeditor.css في رقعة الاتّجاه — التوكيدان بعده يمرّان على العمى.")
    # ‏**الأخصُّ أوّلًا**: عودةُ الصيغة المشروطة هي الانحدارُ المقصود، ولو سبقها توكيدٌ
    # عامٌّ لسقط هو أوّلًا برسالةٍ لا تسمّي السبب — ولَما قاس المُصابُ ما زُرع لأجله.
    assert "+.monaco-editor.text-direction-rtl {" not in body, (
        "التثبيتُ عاد مقصورًا على `.text-direction-rtl` — وهذا هو العطبُ بعينه: "
        "المحرّرُ **اليساريّ** داخل مستندٍ يمينيٍّ يبقى بلا تثبيت [DR-07].")
    assert "+.monaco-editor {" in body and "+	direction: ltr;" in body, (
        "جذرُ المحرّر غيرُ مثبَّتٍ على ltr في `editor.css` — النصُّ يُدفَع ‎16.7‎ مليون "
        "بكسل خارجَ الشاشة في كلّ محرّرٍ يساريٍّ داخل واجهةٍ عربيّة [DR-07].")


@check("سماتُ محراب مولَّدةٌ لا مكتوبةٌ بيد · وكلُّ لغةٍ تُلوَّن [TH-01]")
def _themes_are_generated_and_color_every_language():
    """كانت السماتُ الأربعُ تحمل سبعَ قواعد، ستٌّ منها للغة ص وحدَها.

    فكلُّ ملفٍّ ليس ص يُفتَح بلونٍ واحد — وقِيس على المشحون: ملفُّ HTML من ‎13‎ شظيّةً
    كلُّها اللونُ الافتراضيّ. والسمةُ **مفروضةٌ افتراضًا**، فلا يختارها المستخدم ليكتشف
    نقصَها. والفحصُ يرسو على **نطاقاتٍ بالاسم** لا على عددٍ وحدَه: عدٌّ يمرّ على سبعين
    قاعدةً كلُّها لِـص.
    """
    gen_dir = os.path.join(ROOT, "extensions", "mihrab-themes")
    sys.path.insert(0, gen_dir)
    import gen_themes as G  # noqa: E402  (لا أثرَ جانبيًّا: التنفيذُ تحت __main__)

    try:
        G.main(check=True)
    except SystemExit as e:
        raise AssertionError(str(e))

    # نطاقاتٌ لا تخصّ ص: وجودُها هو الفرقُ بين سمةٍ للغةٍ واحدةٍ وسمةٍ لمحرِّر.
    NEEDED = ("markup.heading", "entity.name.tag", "keyword.control",
              "variable", "entity.name.function")
    seen = 0
    for fn, _name, _tt, _pal, _wb, _variant in G.THEME_SET:
        rules = json.load(open(os.path.join(gen_dir, "themes", fn),
                               encoding="utf-8"))["tokenColors"]
        seen += 1
        blob = json.dumps([r.get("scope") for r in rules], ensure_ascii=False)
        missing = [n for n in NEEDED if n not in blob]
        assert not missing, (
            "‏" + fn + ": نطاقاتٌ غيرُ ملوَّنةٍ ⇒ لغاتٌ كاملةٌ بلا لون: "
            + " · ".join(missing) + " [TH-01]")
        # وقواعدُ ص **آخرًا** وإلّا غلبها الأساس، والغلبةُ صامتة.
        tail = json.dumps(rules[-1].get("scope"), ensure_ascii=False)
        assert ".sad" in tail, (
            "‏" + fn + ": آخرُ قاعدةٍ ليست لِـص — الأساسُ يغلب قواعدَنا [TH-01].")
    assert seen == 4, "‏" + str(seen) + " سمةً فُحصت لا أربعًا — الجردُ ناقص."


# `assert`. صفرٌ ⇒ الفحصُ لم يُصدِر حكمًا واحدًا على هذه الشجرة.
#
# ‏**ولا يُحتسَب `raise AssertionError` شاهدًا** عمدًا: الفحصُ السالب («لا قاعدةَ تفعل
# كذا») يمرّ بصفر رفعاتٍ سواءٌ أكانت الشجرةُ نظيفةً أم كانت العيّنةُ فارغةً — وهما حالان
# لا يفرّق بينهما إلّا **شاهدُ تفعيلٍ موجَب**: توكيدٌ أنّ ما يُفحَص وُجِد أصلًا. وهي
# القاعدةُ نفسُها المكتوبةُ في `word_boundaries.live.mjs`.
#
# والإعفاءُ ممكنٌ **بسببٍ مكتوب** — بعقد `uncovered` و`known_absent` نفسِه: قائمةٌ تُقصَر
# ولا تطول إلّا بالتزامٍ مرئيّ. وإعفاءٌ عن فحصٍ زائلٍ يُفشِل كذلك.
ASSERT_FREE_WAIVERS = {
    # "اسمُ الفحص": "لماذا يصحّ أن يقيس صفرًا على شجرةٍ سليمة",
}


@check("نطاقُ شهادة الـwildcard محصورٌ في طبقة الـwebview [DEP-01]")
def _deploy_wildcard_scope_is_contained():
    """شهادةُ wildcard واحدةٌ تنتحل كلَّ اسمٍ تحتها لو تسرّب مفتاحُها.

    الـwebviews تحتاج wildcard لا مفرّ: كلُّ إطارٍ يُحمَّل على أصلٍ عشوائيّ
    (`<uuid>.webview.mihrab.dev`) — عزلُ أمانِ VS Code نفسِه، والأسماءُ تُولَّد وقتَ
    التشغيل فلا تُسجَّل مسبقًا. و`*.mihrab.dev` أبسطُ وأغرى، لكنّ تسرُّبَ مفتاحه
    يُنتحَل به **الموقعُ نفسُه** لا أصولُ الإطارات وحدَها.

    **والنسخةُ الأولى من هذا الحارس كانت تقيس النجمةَ وحدَها — فمرّت أخطرُ صياغة:**

        certbot certonly -d '*.webview.mihrab.dev' -d mihrab.dev -d www.mihrab.dev

    نجمةٌ ضيّقةٌ فيمرّ الفحص، والشهادةُ الناتجةُ مفتاحٌ واحدٌ يغطّي الموقعَ كلَّه — وهي
    **أغرى** من `*.mihrab.dev` لأنّها تبدو محترمةً للاحتواء. فصار المقياسُ الأمرَ
    كلَّه لا الوسيطَ الواحد.
    """
    dep = os.path.join(ROOT, "deploy")
    if not os.path.isdir(dep):
        raise AssertionError("لا مجلّد deploy — الحارسُ يقيس شيئًا غيرَ موجود")

    # **كلُّ ملفٍّ لا امتداداتٍ مختارة**: أوّلُ `Makefile` أو `renew.cron` أو
    # `cloudflare.ini` يُضاف يخرج من المسح بلا أن ينتبه أحد.
    files = []
    for base, dirs, names in os.walk(dep):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for n in sorted(names):
            files.append(os.path.join(base, n))
    assert files, "مجلّد deploy بلا ملفّاتٍ تُقاس"

    ALLOWED = "*.webview.mihrab.dev"
    # ‏IGNORECASE: أسماءُ النطاقات غيرُ حسّاسةٍ للحالة، و`*.Mihrab.dev` كان يمرّ.
    WILD = re.compile(r"\*(?:\.[A-Za-z0-9_-]+)*\.mihrab\.dev", re.IGNORECASE)
    # وصيغةُ nginx الأخرى للشمول: نقطةٌ بادئة = النطاقُ وكلُّ ما تحته.
    DOTPREFIX = re.compile(r"server_name\s+[^;]*(?<![A-Za-z0-9_.-])\.mihrab\.dev", re.IGNORECASE)
    NAME_ARG = re.compile(r"-d\s+['\"]?([^\s'\"]+)")

    seen = 0
    for f in files:
        rel = os.path.relpath(f, ROOT).replace(os.sep, "/")
        try:
            text = _read(f)
        except (UnicodeDecodeError, OSError):
            continue  # ثنائيٌّ لا يحمل إعدادًا
        for i, line in enumerate(text.splitlines(), 1):
            for hit in WILD.findall(line):
                seen += 1
                assert hit.lower() == ALLOWED, (
                    "نطاقُ wildcard موسَّع: «" + hit + "» في " + rel + ":" + str(i)
                    + " — المسموح: «" + ALLOWED + "» وحدَه.")
            assert not DOTPREFIX.search(line), (
                "‏`server_name .mihrab.dev` في " + rel + ":" + str(i)
                + " — النقطةُ البادئة تشمل النطاقَ وكلَّ ما تحته، وهي wildcard بصيغةٍ أخرى.")

            # **الأمرُ كلُّه لا الوسيطُ الواحد**: أيُّ سطرِ certbot يطلب شهادةَ الـwebview
            # يجب ألّا يجمع معها اسمًا آخر — الشهادةُ الواحدة مفتاحٌ واحد.
            if "certbot" in line and "webview" in line:
                names = NAME_ARG.findall(line)
                assert len(names) == 1 and names[0].lower() == ALLOWED, (
                    "شهادةُ الـwebview تجمع أسماءً أخرى في " + rel + ":" + str(i)
                    + ": " + repr(names)
                    + " — مفتاحٌ واحدٌ لأسماءٍ متعدّدة يُنتحَل بتسرُّبه كلُّها."
                    + " أَصدِرها وحدَها: -d '" + ALLOWED + "'")

    # تفعيلٌ موجبٌ **مرسًى لا عدد**: عتبةٌ رقميّةٌ تتقادم مع كلّ تحرير، أمّا هذا
    # السطرُ فوجودُه شرطُ عملِ الطبقة أصلًا.
    wv = os.path.join(dep, "nginx", "webview.mihrab.dev.conf")
    assert os.path.isfile(wv), "كتلةُ الـwebview مفقودة: " + wv
    body = _read(wv)
    assert ("server_name " + ALLOWED + ";") in body, (
        "لا `server_name " + ALLOWED + ";` في " + os.path.relpath(wv, ROOT)
        + " — إمّا أنّ الاسمَ تغيّر (فيُحدَّث الحارس)، أو أنّ الطبقةَ أُلغيت (فيُحذَف صراحةً).")
    assert seen >= 1, "المُطابِقُ لم يرَ نجمةً واحدة — تعبيرٌ نمطيٌّ مات صامتًا"

    # والأمرُ الذي يُتَّخذ فيه القرارُ فعلًا يجب أن يكون **مكتوبًا** كي يُحرَس. كان
    # غائبًا («المرحلةُ ٤ تعتمد على قرارٍ لم يُتَّخذ»)، فكان الحارسُ يفحص موضعَين من
    # ثلاثةٍ ويترك الثالثَ — وهو الحاسم — بلا رقيب.
    readme = _read(os.path.join(dep, "README.md"))
    assert re.search(r"certbot[^\n]*webview", readme), (
        "لا أمرَ certbot للـwildcard في deploy/README.md — الموضعُ الذي يُتَّخذ فيه "
        "القرارُ غيرُ مكتوب، فلا يُحرَس. اكتبه ولو معلَّقًا بانتظار اختيار المزوّد.")

    # وسلالتان لا سلالة، **في الاتّجاهين**: كتلةُ الـwebview لا تستعمل سلالةَ الموقع،
    # وكتلُ الموقع لا تستعمل سلالةَ الـwebview. أيُّ مشاركةٍ تُلغي الاحتواء.
    LIN = re.compile(r"letsencrypt/live/([^/]+)/")
    wv_lin = set(LIN.findall(body))
    assert wv_lin == {"webview.mihrab.dev"}, (
        "سلالةُ شهادة الـwebview ليست منفصلة: " + repr(sorted(wv_lin)))
    site_lin = set(LIN.findall(_read(os.path.join(dep, "nginx", "mihrab.dev.conf"))))
    assert "webview.mihrab.dev" not in site_lin, (
        "كتلُ الموقع تستعمل سلالةَ الـwebview: " + repr(sorted(site_lin))
        + " — الاحتواءُ يعمل في الاتّجاهين أو لا يعمل.")


@check("لا نداءَ `python` مجرَّدًا في أيّ سكربت [PY-01]")
def _no_bare_python_invocation():
    """الصنفُ الذي كسر بناءَ لينكس **مرّتين في ساعة**، وبقي بعدهما في خمسة ملفّات.

    ‏`python` المجرَّد غائبٌ عن أوبونتو 24.04، وعلى توزيعاتٍ أقدمَ هو بايثون 2 —
    والثانيةُ أخبثُ لأنّ الأمرَ يوجد فيفشل المُرقِّعُ بخطأِ صياغةٍ في ملفٍّ سليم.
    وأُصلِح موضعان بالاسم، ثمّ كُتب في رسالة الإيداع «فلا يتكرّران» — وذلك صحيحٌ
    للموضعَين وخاطئٌ للصنف: بقي `python` في جالب أدوات ص وجالب ألف ونشرِ الموقع
    ونشرِ الإصدار، وكلُّها تعمل على لينكس في CI.

    والقاعدة: يُحلّ المفسّرُ بـ`resolve_py_bin` من `build/lib/pybin.sh` ثمّ يُنادى
    `$PY_BIN`. ويُستثنى شكلان: التعريفُ داخل `pybin.sh` نفسِه، ومسارُ ارتدادٍ محروسٌ
    بـ`command -v python` قبله مباشرةً (كما في `sha256.sh`).
    """
    import glob as _g
    roots = [os.path.join(ROOT, "build"), os.path.join(ROOT, "tests")]
    scripts = []
    for r in roots:
        for base, dirs, names in os.walk(r):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules")]
            scripts += [os.path.join(base, n) for n in sorted(names) if n.endswith(".sh")]
    assert scripts, "لا سكربتاتٍ تُقاس — الحارسُ يقيس الهواء"

    # الأمرُ `python` في موضع الفعل: بداية سطر، أو بعد `|` أو `&&` أو `$(` أو `;`.
    CALL = re.compile(r"(?:^|[|;&(]|&&|\|\|)\s*python(?![0-9A-Za-z_.-])")
    GUARD = re.compile(r"command -v python\b")
    offenders = []
    for f in scripts:
        rel = os.path.relpath(f, ROOT).replace(os.sep, "/")
        if rel.endswith("build/lib/pybin.sh"):
            continue  # هنا يُعرَّف الحلُّ نفسُه
        lines = _read(f).splitlines()
        for i, line in enumerate(lines):
            code = line.split("#", 1)[0]
            if not CALL.search(code):
                continue
            # ارتدادٌ محروس: `command -v python` في السطر نفسِه أو الذي قبله.
            window = "\n".join(lines[max(0, i - 1):i + 1])
            if GUARD.search(window):
                continue
            offenders.append(f"{rel}:{i + 1}: {line.strip()[:70]}")

    assert not offenders, (
        "نداءُ `python` مجرَّدًا في:\n       " + "\n       ".join(offenders)
        + "\n       استعمل: . \"$ROOT/build/lib/pybin.sh\" ثمّ resolve_py_bin ثمّ \"$PY_BIN\"")

    # مرسًى موجب: الحلُّ المشترك موجودٌ وموصولٌ ببناءٍ فعليّ. لو حُذف، صار الحارسُ
    # يمنع شيئًا بلا بديل — وذلك أسوأُ من غيابه.
    lib = os.path.join(BUILD, "lib", "pybin.sh")
    assert os.path.isfile(lib), "‏build/lib/pybin.sh مفقود — الحارسُ يمنع بلا بديل"
    assert "resolve_py_bin" in _read(os.path.join(BUILD, "build.sh")), \
        "‏build.sh لا يستدعي resolve_py_bin — الحلُّ موجودٌ وغيرُ موصول"


@check("مُرقِّعاتُ التعريب موصولةٌ بالأشجار الثلاث [WEB-02]")
def _web_patchers_wired_for_both_trees():
    """حذفُ سطرٍ واحدٍ يعيد العطبَ الأصليّ: 1 سلسلة عربيّة من 21922.

    كان الدرسُ مُعمَّمًا على رقعة xterm وحدَها لأنّ مُصابَ PF-03 كشفها، والثلاثةُ
    الباقيةُ بلا حارس. وأخطرُها `bake_nls_arabic`: حذفُه من فرع الويب يعيد الواجهةَ
    إنجليزيّةً بالكامل، ولا يحمرّ شيءٌ في الطبقة الساكنة.
    """
    sh = _read(os.path.join(BUILD, "build.sh"))
    PATCHERS = ("patch_extension_nls.py", "patch_xterm_bidi.py",
                "patch_workbench_font.py", "bake_nls_arabic.py")
    missing = []
    # ثلاثٌ لا اثنتان: `vscode-web` الثابتةُ هي **ما يُنشَر فعلًا** بعد تقاعد النشر
    # بخادم، وكانت خارجَ الحلقة وخارجَ هذا الحارس معًا — فبقي أخضرَ على شجرةٍ تُنشَر
    # بواجهةٍ إنجليزيّةٍ كاملة.
    for target in ("$APP_DIR", "$WEB_DIR", "$_STATIC_DIR"):
        for pat in PATCHERS:
            needle = pat + '" "' + target + '"'
            if needle not in sh:
                missing.append(pat + " ⇐ " + target)
    assert not missing, (
        "مُرقِّعاتٌ غيرُ موصولةٍ في build.sh:\n       " + "\n       ".join(missing)
        + "\n       الشجرتان تُشحَنان معًا، فتُعرَّبان معًا.")

    # وإعادةُ فرض الهويّة كذلك: نجا `serverDownloadUrlTemplate` في الويب لأنّها
    # كانت مربوطةً بالمكتبيّ وحدَه — عطبٌ قِيس في المشحون لا استُنتج.
    #
    # والشجرةُ الثابتةُ **مستثناةٌ هنا بسببٍ لا بسهو**: لا `product.json` فيها إطلاقًا،
    # فالدالّتان تعودان صفرًا بلا عمل. هويّتُها تسكن صفحةَ المضيف، ويفرضها
    # `patch_web_host.py` — ويحرسه الشرطُ الذي يلي.
    for target in ('"$APP_DIR"', '"$WEB_DIR"'):
        assert ("reforce_identity " + target) in sh, \
            "‏reforce_identity غيرُ مُستدعاةٍ لـ" + target + " — الهويّةُ تسقط في شجرةٍ تُشحَن"
        assert ("assert_identity " + target) in sh, \
            "‏assert_identity غيرُ مُستدعاةٍ لـ" + target + " — شجرةٌ تُشحَن بلا بوّابة"

    # وهويّةُ الشجرة الثابتة: تُفرَض ثمّ **تُفحَص** في البناء نفسِه. والبوّابةُ لا
    # تُستدعى إلّا إن استُدعي المُرقِّع، فالشرطان معًا لا أحدُهما.
    assert 'patch_web_host.py" "$_STATIC_DIR"' in sh, \
        "‏patch_web_host.py غيرُ موصولٍ بالشجرة الثابتة — تُنشَر بأيقونة VSCodium ومانيفستِه"
    assert 'patch_web_host.py" --verify "$_STATIC_DIR"' in sh, \
        "‏--verify غيرُ مُستدعًى على الشجرة الثابتة — فرضٌ بلا بوّابة"


@check("لا وجهةَ منبعٍ مضروبةً في رُقَع البناء [BR-05]")
def _no_upstream_repo_in_generated_patches():
    """‏`!!GH_REPO_PATH!!` افتراضُه `VSCodium/vscodium`، ولم نضبطه فورثنا وجهتَه.

    والأثرُ ليس نظريًّا: لوحُ الترحيب كان يجلب `announcements-extra.json` من مستودع
    المنبع في كلّ فتحةٍ أولى — يُخبِره بكلّ زائرٍ جديد، ويعرض إعلاناتِه داخل لوحِنا
    لو نُشرت. قِيس حيًّا على mihrab.dev عبر CDP.

    ولم تمسكه طبقةٌ واحدة: عنوانٌ مضروبٌ في الحزمة المصغَّرة لا مفتاحٌ في
    ‏`product.json` — وبوّاباتُنا تفحص `product.json` والنصَّ المخبوز.
    """
    sh = _read(os.path.join(BUILD, "build.sh"))
    m = re.search(r'export\s+GH_REPO_PATH="([^"]+)"', sh)
    assert m, ("‏build.sh لا يضبط GH_REPO_PATH — يُورَث `VSCodium/vscodium` "
               "فيجلب لوحُ الترحيب إعلاناتِ المنبع ويُخبِره بزائرِنا")
    val = m.group(1)
    assert "vscodium" not in val.lower() and "microsoft" not in val.lower(), \
        "‏GH_REPO_PATH يشير إلى المنبع: " + val

    # مرسًى موجب: الرُقَعُ التي تستهلك العنصرَ النائبَ ما زالت موجودة. لو زالت، صار
    # الحارسُ يفرض متغيّرًا بلا أثر — وذلك يوهم بحمايةٍ لم تعد قائمة.
    pdir = os.path.join(ROOT, ".upstream", "patches")
    if os.path.isdir(pdir):
        users = [n for n in sorted(os.listdir(pdir))
                 if n.endswith(".patch") and "!!GH_REPO_PATH!!" in _read(os.path.join(pdir, n))]
        assert users, ("لا رقعةَ تستعمل !!GH_REPO_PATH!! — إمّا زالت الرُقَعُ فالمتغيّرُ "
                       "بلا أثر، وإمّا صارت تكتب وجهةً حرفيّةً فالحارسُ أعمى")
        # وسطرٌ مُضافٌ يكتب وجهةَ المنبع حرفيًّا يتجاوز العنصرَ النائبَ كلَّه.
        #
        # ‏**استثناءٌ واحدٌ مُعلَنٌ بشرطِ رفعه**: `21-policy-use-custom-lib` يكتب
        # `github.com/VSCodium/vscodium` في ثلاثة حقولٍ من `renderProfileManifest` —
        # ‏`pfm_app_url` و`pfm_documentation_url` و`PayloadDescription`. وهي بيانُ
        # ملفِّ سياسةٍ مؤسّسيّ: «This profile manages محراب. For more information
        # see …/VSCodium». عطبُ هويّةٍ حقيقيّ، لكنّه **نائم**: قِيس أنّ `pfm_app_url`
        # لا يظهر في أيٍّ من الشجرتين المشحونتين (ولا في الويب)، لأنّها أداةُ بناءٍ
        # لتوليد ملفّاتِ سياسةٍ لا نولّدها.
        # ⚠️ يُرفع الاستثناءُ لحظةَ أن يشحن محرابٌ ملفَّ سياسةٍ مؤسّسيّة.
        POLICY_EXEMPT = "21-policy-use-custom-lib.patch"
        for n in sorted(os.listdir(pdir)):
            if not n.endswith(".patch") or n == POLICY_EXEMPT:
                continue
            for i, line in enumerate(_read(os.path.join(pdir, n)).splitlines(), 1):
                if line.startswith("+") and "VSCodium/vscodium" in line:
                    raise AssertionError(
                        "وجهةُ المنبع حرفيّةً في سطرٍ مُضافٍ — "
                        ".upstream/patches/" + n + ":" + str(i)
                        + " — `GH_REPO_PATH` لا يبلغها")

        # ومرسًى للاستثناء نفسِه: يبقى نائمًا ما دام لا يُشحَن. فإن ظهر في شجرةٍ
        # مبنيّةٍ يومًا، سقط سببُ الاستثناء وصار عطبًا حيًّا.
        for tree in (os.path.join(ROOT, ".upstream", "VSCode-win32-x64"),
                     os.path.join(ROOT, ".upstream", "vscode-web")):
            hit = os.path.join(tree, "resources", "app", "out")
            if not os.path.isdir(tree):
                continue
            for base, _dirs, files in os.walk(hit if os.path.isdir(hit) else tree):
                for fn in files:
                    if not fn.endswith((".js", ".json", ".plist", ".mobileconfig")):
                        continue
                    try:
                        with open(os.path.join(base, fn), "rb") as f:
                            if b"pfm_app_url" in f.read():
                                raise AssertionError(
                                    "ملفُّ السياسة صار يُشحَن (" + fn + ") — سقط سببُ "
                                    "استثناء " + POLICY_EXEMPT + "، وهو يحمل وجهةَ المنبع")
                    except OSError:
                        pass

    # وبوّابةُ الأثر في `build.sh`: المتغيّرُ نيّةٌ، والحزمةُ هي ما يُشحَن. ويُقاس
    # **جسمُ البوّابة** لا وسمُها: أوّلُ صياغةٍ قبلت `"[BR-05]" in sh`، والوسمُ يرد
    # في التعليق أعلاه — فحذفُ البوّابة كلِّها كان يمرّ. كشفه مُصابُ PF-03.
    assert 'grep -q "VSCodium/vscodium" "$_bundle"' in sh, \
        "لا بوّابةَ تقيس الحزمةَ المصغَّرة — ضبطُ المتغيّر وحدَه لا يُثبِت أنّه وصل الترقيع"
    for _t in ("$APP_DIR/out/vs/workbench/workbench.desktop.main.js",
               "$STATIC_DIR/out/vs/workbench/workbench.web.main.internal.js"):
        assert _t in sh, "بوّابةُ [BR-05] لا تشمل " + _t


@check("صفحةُ مضيفِ المتصفّح تفي بما تَعِد [WEB-04]")
def _web_host_page_contract():
    """أربعةُ عيوبٍ قِيست في `web/` وكلُّها كانت خارج كلّ طبقة — لأنّ الملفّين جديدان.

    الشجرةُ الثابتةُ بلا `product.json`، فصفحةُ المضيف هي الهويّةُ كلُّها **وسلوكُ
    الإقلاع كلُّه**. وخطأٌ حرفيٌّ واحدٌ فيها لا يُسقِط بناءً ولا يُحمِّر فحصًا: يُسقِط
    السمةَ، أو يحجب المحرِّرَ، أو يجلب إطارًا من شبكة المنبع — صامتًا.
    """
    web = os.path.join(ROOT, "web")
    boot = _read(os.path.join(web, "boot.js"))
    html = _read(os.path.join(web, "index.html"))

    # (أ) اسمُ السمة **حرفيّ**، وانحرافُه يعني ارتدادًا إلى Dark Modern — أي أنّ
    #     محرابَ المتصفّح يبدو VS Code. كان «محراب الداكن» والصوابُ «محراب الداكنة».
    m = re.search(r"'workbench\.colorTheme':\s*'([^']+)'", boot)
    assert m, "‏boot.js بلا سمةٍ افتراضيّة — الورشةُ ترتدّ إلى سمة المنبع"
    theme = m.group(1)
    pkg = json.loads(_read(os.path.join(ROOT, "extensions", "mihrab-themes", "package.json")))
    labels = [t.get("label") for t in pkg.get("contributes", {}).get("themes", [])]
    assert theme in labels, (
        "سمةُ boot.js «" + theme + "» ليست من سمات mihrab-themes " + str(labels)
        + " — الورشةُ سترتدّ إلى سمة المنبع بلا شكوى")

    # (ب) الهويّةُ تُقرأ ولا تُكتَب مرّتين. مفاتيحُ المنتَج الحرفيّةُ هنا تعني نسخةً
    #     ثانيةً من `product-overrides/product.json` تفترق عنها بصمت — وقد افترقت.
    assert "_MIHRAB_PRODUCT" in boot, \
        "‏boot.js لا يقرأ الهويّةَ المشتقّة — عاد يكتبها بنفسه؟"
    for key in ("nameLong", "extensionsGallery", "documentationUrl", "licenseUrl"):
        assert ('"' + key + '"') not in boot and ("'" + key + "'") not in boot \
            and (key + ":") not in boot, \
            "«" + key + "» مكتوبٌ حرفيًّا في boot.js — هويّةٌ ثانيةٌ تنحرف عن product-overrides"
    assert "product.web.js" in html, \
        "‏index.html لا يصل product.web.js — الصفحةُ تُقلِع بلا هويّة"

    # (ج) وجهةُ الـwebview: تركُها فارغةً **لا** يخدمها محلّيًّا — المنبعُ يرتدّ إلى
    #     ‏`{{uuid}}.vscode-cdn.net`. أي أنّ الصمتَ هنا يعني شبكةَ مايكروسوفت.
    # ‏`\b…:` لا `in`: أوّلُ صياغةٍ قبلت `_webviewEndpoint:` — أي أنّ تعطيلَ الحقل
    # بحرفٍ واحدٍ كان يمرّ من تحتها. كشفه مُصابُ PF-03 لا القراءة.
    assert re.search(r"\bwebviewEndpoint:", boot), (
        "لا `webviewEndpoint` في boot.js — والمنبعُ يرتدّ إلى vscode-cdn.net، "
        "فمعاينةُ Markdown تُرسل عنوانَ الزائر إلى شبكة المنبع ثمّ ترجع 404")
    assert "webviewContentExternalBaseUrlTemplate" not in boot, \
        "مفتاحان لوجهةٍ واحدة — `webviewEndpoint` يسبقه فيصير الثاني وهمًا"

    # (د) الاسمُ الصحيحُ للخيار: `workspaceTrustEnabled` ليس في الـAPI فيُتجاهَل صامتًا،
    #     والنتيجةُ كانت تتحقّق بالمصادفة لا بالقرار.
    assert "workspaceTrustEnabled:" not in boot, \
        "‏workspaceTrustEnabled ليس في IWorkbenchConstructionOptions — الاسمُ enableWorkspaceTrust"

    # (هـ) الاستيرادُ ديناميّ: الساكنُ يُقيَّم قبل أن يُنفَّذ سطرٌ من الملفّ، فلا يبلّغ
    #      أحدٌ حين تفشل الحزمةُ نفسُها — وهو أرجحُ عطبِ نشرٍ ثابت.
    assert "await import(" in boot, \
        "استيرادٌ ساكنٌ في boot.js — فشلُ الحزمة يترك الزائرَ أمام شريطٍ يدور إلى الأبد"

    # (و) وشاشةُ الإقلاع لا تُرسَم فوق ورشةٍ تعمل. الشاشةُ inset:0;z-index:9999.
    assert "document.querySelector('.monaco-workbench')" in html, \
        "‏fail() في index.html بلا حارسِ «الورشةُ ظهرت» — شاشةُ فشلٍ تحجب محرِّرًا يعمل"
    # تُجرَّد التعليقاتُ أوّلًا: التعليقُ الذي **يشرح** لماذا لا نستعملها ليس استعمالًا.
    assert not re.search(r"once:\s*true", re.sub(r"//.*", "", html)), \
        "‏{ once: true } على مُلتقِط الأخطاء يحرقه على أوّل خطأٍ ثانويّ فيُعمينا عن الحاسم"

    # (ز) وثلاثةُ وعودٍ للمستخدم: لا منعَ تكبير (WCAG 1.4.4)، ولا فكَّ وصلٍ للعربيّة،
    #     ولا صمتَ أمام زائرٍ بلا جافاسكربت.
    # يُقاس **وسمُ viewport نفسُه** لا الملفُّ كلُّه: التعليقُ الذي يشرح لماذا حُذفا
    # يذكرهما بحكم موضوعه، ومنعُه يجعل الحارسَ يعاقب التوثيق.
    vp = re.search(r'<meta\s+name="viewport"[^>]*>', html)
    assert vp, "لا <meta viewport> — الصفحةُ تُعرَض بعرضِ سطحِ مكتبٍ على الهاتف"
    assert "user-scalable" not in vp.group(0) and "maximum-scale" not in vp.group(0), \
        "منعُ التكبير في <meta viewport> — مخالفةُ WCAG 1.4.4 (تغييرُ حجم النصّ)"
    assert not re.search(r"#mihrab-boot \.name \{[^}]*letter-spacing", html), \
        "‏letter-spacing على «محراب» يفكّ وصلَ حروفها — وهي أوّلُ كلمةٍ يراها الزائر"
    assert "<noscript>" in html, "لا <noscript> — زائرٌ بلا جافاسكربت يرى مستطيلًا صامتًا"

    # (ح) ولوحُ الترحيب: موجودٌ ومعرَّبٌ في هذه الشجرة، و`'none'` كانت تُخفيه فتترك
    #     الزائرَ الأوّلَ أمام فراغٍ لا يشرح شيئًا.
    assert "'workbench.startupEditor': 'none'" not in boot, \
        "‏startupEditor='none' يُخفي لوحَ ترحيبٍ **مبنيًّا ومعرَّبًا** — فراغٌ بلا سبب"


@check("إعدادُ النشر لا يسلّم المحرِّرَ لزائرٍ مجهول [DEP-02]")
def _deploy_does_not_expose_editor():
    """عطبان يوصلان زائرًا مجهولًا إلى طرفيّةٍ على الخادم — وكلاهما كان محروسًا بنثرٍ فقط.

    **(أ) `--without-connection-token`**: خادمُ الويب يفتح طرفيّةً ونظامَ ملفّاتٍ لمن
    يصله. استعملناها محلّيًّا للقياس، ونسخُها إلى وحدةِ الخدمة سطرٌ واحدٌ ينتج تنفيذَ
    شيفرةٍ عن بُعدٍ لأيّ زائر.

    **(ب) `default_server`**: على الخادم المقيس لا كتلةَ `default_server` على 443،
    فأوّلُ كتلةٍ بترتيب التحليل تملك الافتراضيّ. ولو حملت كتلةُ محرابٍ الوسمَ — أو
    وُضعت في `conf.d/` التي تُحمَّل قبل `sites-enabled/` — لصار كلُّ طلبٍ بترويسة
    ‏`Host` مجهولةٍ يُمرَّر إلى المحرِّر.
    """
    dep = os.path.join(ROOT, "deploy")
    assert os.path.isdir(dep), "لا مجلّد deploy"

    # **يُقاس ما يُنسَخ إلى الخادم، لا ما يُقرأ عنه.** النثرُ في `README` وقياساتُ
    # `preflight.sh` تذكر الوسمَين بحكم موضوعها، ومنعُها يجعل الحارسَ يعاقب التوثيق.
    # و`.example` مستثنًى بالاسم: ملفُّ الخادم الافتراضيِّ **يجب** أن يحمل الوسم —
    # وهو كتلةُ حمايةٍ لا كتلةُ محراب، ولا يُنسَخ إلّا بقرارٍ بعد قياس.
    installed = []
    ngx = os.path.join(dep, "nginx")
    if os.path.isdir(ngx):
        installed += [os.path.join(ngx, n) for n in sorted(os.listdir(ngx))
                      if n.endswith(".conf")]
    svc = os.path.join(dep, "systemd")
    if os.path.isdir(svc):
        installed += [os.path.join(svc, n) for n in sorted(os.listdir(svc))
                      if n.endswith(".service")]
    assert installed, "لا ملفّاتِ إعدادٍ تُنسَخ إلى الخادم — الحارسُ يقيس الهواء"

    for f in installed:
        rel = os.path.relpath(f, ROOT).replace(os.sep, "/")
        for i, line in enumerate(_read(f).splitlines(), 1):
            code = line.split("#", 1)[0]
            assert "--without-connection-token" not in code, (
                "‏`--without-connection-token` في " + rel + ":" + str(i)
                + " — على منفذٍ يبلغه العالمُ هذا تنفيذُ شيفرةٍ عن بُعدٍ لأيّ زائر.")
            assert "default_server" not in code, (
                "‏`default_server` في " + rel + ":" + str(i)
                + " — كتلةُ محرابٍ افتراضيّةً تستقبل كلَّ Host مجهول.")

    # **لا تكرارَ لما تضعه قصاصةُ certbot.** كتلةٌ تُدرِج
    # `options-ssl-nginx.conf` ثمّ تعيد توجيهًا فيها ⇒ nginx يرفض بـ«directive is
    # duplicate» **ولا يقلع**. أُوقِع فعلًا على الخادم، وأنقذته البوّابةُ التلقائيّة.
    # والقائمةُ مقروءةٌ من الخادم لا مفترَضة (`options-ssl-nginx.conf` القياسيّة).
    # وضعناها ظنًّا أنّها تحصينٌ من السقوط إلى الافتراضيّات — والقصاصةُ تكفلها،
    # فكانت تعطيلًا لا تحصينًا.
    SNIPPET_SETS = ("ssl_session_cache", "ssl_session_timeout", "ssl_session_tickets",
                    "ssl_protocols", "ssl_prefer_server_ciphers", "ssl_ciphers")
    # وثقبان أُغلِقا بعد قياسِهما لا بعد تخيّلهما:
    #   • `startswith(d + " ")` يشترط **مسافةً حرفيّة**، و`ssl_session_cache<tab>…`
    #     مقبولٌ في nginx تمامًا ⇒ يمرّ من تحت الحارس. صار الفصلُ بأيّ فراغ.
    #   • والفحصُ كان مشروطًا بأن يذكر الملفُّ `options-ssl-nginx.conf` **نصًّا**،
    #     فتكرارٌ في `00-mihrab-shared.conf` (وهو محمَّلٌ في السياق نفسِه ولا يذكرها)
    #     كان خارجَ التغطية. صار السؤالُ عن المجلّد لا عن الملفّ.
    ngx_dir = os.path.join(dep, "nginx")
    if os.path.isdir(ngx_dir):
        confs = [n for n in sorted(os.listdir(ngx_dir)) if n.endswith(".conf")]
        snippet_used = any("options-ssl-nginx.conf" in _read(os.path.join(ngx_dir, n))
                           for n in confs)
        for n in confs if snippet_used else []:
            for i, line in enumerate(_read(os.path.join(ngx_dir, n)).splitlines(), 1):
                head = line.split("#", 1)[0].strip().split(None, 1)
                if head and head[0] in SNIPPET_SETS:
                    raise AssertionError(
                        "‏" + head[0] + " في deploy/nginx/" + n + ":" + str(i)
                        + " مع إدراج options-ssl-nginx.conf — تكرارٌ يمنع nginx من الإقلاع.")

    unit = os.path.join(dep, "systemd", "mihrab-web.service")
    assert os.path.isfile(unit), "وحدةُ الخدمة مفقودة: " + unit
    u = _read(unit)

    # **‏systemd لا يعرف التعليقَ الجانبيّ.** `Key=value  # شرح` يجعل القيمةَ كلَّ ما
    # بعد `=`، فيُرفَض التوجيهُ **ويُتجاهَل بصمت**: لا خطأً ولا فشلَ إقلاع، بل تقييدٌ
    # يُظَنُّ مفعَّلًا وليس كذلك. أُوقِع ثلاث مرّاتٍ في ملفٍّ واحد، وكشفه محرِّكُ
    # ‏systemd في السجلّ لا حارسٌ عندنا:
    #     Failed to parse boolean value, ignoring: true          # ⇐ …
    #     StateDirectory= path is absolute, ignoring: /var/lib/mihrab
    # فسقط `NoNewPrivileges` و`PrivateTmp` و`StateDirectory` من خدمةٍ تُنفِّذ شيفرةَ
    # المستخدم عمدًا.
    INLINE = re.compile(r"^[A-Za-z][A-Za-z0-9]*=.*[ 	]#")
    for i, line in enumerate(u.splitlines(), 1):
        assert not INLINE.match(line), (
            "تعليقٌ جانبيٌّ في " + os.path.relpath(unit, ROOT) + ":" + str(i)
            + " — systemd يبتلعه في القيمة ويتجاهل التوجيهَ صامتًا. ضعه في سطرٍ مستقلّ.")
    # و`StateDirectory` نسبيٌّ لا مطلق (القيمةُ تُلحَق بـ/var/lib).
    for line in u.splitlines():
        if line.startswith("StateDirectory="):
            assert not line.split("=", 1)[1].strip().startswith("/"),                 "‏StateDirectory مطلقٌ — systemd يرفضه («path is absolute»). اجعله نسبيًّا."
    assert "--connection-token-file" in u, \
        "‏ExecStart بلا --connection-token-file — لا رمزَ يحمي الطرفيّة"
    # ‏`StartLimit*` نُقلا إلى [Unit] منذ systemd 229؛ في [Service] يُهمَلان بصمت،
    # فتصير خدمةٌ تسقط عند الإقلاع حلقةَ إعادةِ تشغيلٍ أبديّةً بلا `failed` ظاهر.
    _unit_sec = u.split("[Service]", 1)[0]
    _svc_sec = u.split("[Service]", 1)[1] if "[Service]" in u else ""
    for key in ("StartLimitIntervalSec", "StartLimitBurst"):
        if key in u:
            assert key in _unit_sec and key not in _svc_sec, (
                "‏" + key + " في [Service] — نُقل إلى [Unit] منذ systemd 229 ويُهمَل هنا بصمت.")


@check("مراجعُ المستودع كلُّها على المنظّمة الحاليّة [ORG-01]")
def _repo_references_are_current():
    """سبعةَ عشرَ مرجعًا نُقلت يدويًّا في ثلاثةَ عشرَ ملفًّا — ولا شيءَ يمنع بقاءَ واحد.

    والمراجعُ ليست روابطَ توثيقٍ فقط: أربعةٌ منها في `product-overrides/product.json`
    تصل المستخدمَ في «أبلغ عن مشكلة» و«الترخيص»، واثنان في بيانات ملفّات ويندوز
    التي **تُطبَع في ثنائيّاتٍ موقَّعة**. ومرجعٌ بائتٌ واحدٌ يعمل اليومَ (‏GitHub
    يحوّل بعد النقل) ويسقط يومَ يُعاد استعمالُ الاسم القديم لشيءٍ آخر.

    والفحصُ يقيس **الشجرةَ المتعقَّبة** لا القرصَ: السجلّاتُ ومخرَجاتُ البناء تحوي
    نسخًا قديمةً بحكم كونها لقطاتٍ لما مضى.
    """
    import subprocess
    # **يُبنى من جزأين لا يُكتب حرفيًّا**: الفحصُ يمسح الشجرةَ المتعقَّبة ومنها هذا
    # الملفّ، فكتابةُ الاسم القديم حرفيًّا تجعله يبلّغ عن نفسِه. أُوقِع فعلًا.
    OLD = "sadlang" + "/mihrab" + "-ide"
    NEW = "mihrab-org" + "/mihrab"
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                             capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise AssertionError(f"تعذّر سردُ الملفّات المتعقَّبة: {e}")
    assert out.returncode == 0, "‏git ls-files فشل — لا يمكن قياسُ الشجرة المتعقَّبة"
    tracked = [n.decode("utf-8") for n in out.stdout.split(b"\0") if n]
    assert tracked, "لا ملفّاتٍ متعقَّبة — الحارسُ يقيس الهواء"

    # **سجلُّ المُصابات مستثنًى بالاسم**: هو بحكم وظيفته مخزنُ أعطابٍ مقصودة —
    # مُصابُ `org-reference-stale` يحمل الاسمَ القديمَ عمدًا كي يُزرَع. ومسحُه يجعل
    # الحارسَ يبلّغ عن الأداة التي تحرسه. (أُوقِع فعلًا: احمرّ على شجرةٍ سليمةٍ
    # فأسقط ثمانيةَ مُصاباتٍ أخرى معه.)
    EXEMPT = {"tests/meta/mutants.json"}

    stale = []
    seen_new = 0
    for rel in tracked:
        if rel in EXEMPT:
            continue
        f = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.isfile(f):
            continue
        try:
            text = _read(f)
        except (UnicodeDecodeError, OSError):
            continue  # ثنائيّ
        if OLD in text:
            for i, line in enumerate(text.splitlines(), 1):
                if OLD in line:
                    stale.append(f"{rel}:{i}")
        seen_new += text.count(NEW)

    assert not stale, (
        "مرجعٌ بائتٌ للمستودع القديم في:\n       " + "\n       ".join(stale[:20])
        + "\n       بدِّله إلى " + NEW)
    # تفعيلٌ موجب: لو زالت المراجعُ كلُّها لمرّ الفحصُ أخضرَ بلا معنى. والمرجعُ
    # الأدنى مرسًى حقيقيّ — `product.json` وحدَه يحمل أربعة.
    assert seen_new >= 4, (
        f"لم يُرَ إلّا {seen_new} مرجعًا لـ{NEW} — إمّا أنّ الاسمَ تغيّر (فيُحدَّث "
        f"الحارس) أو أنّ المراجعَ زالت. لا يُترَك أخضرَ فارغًا.")


def _assert_lines():
    return {i + 1 for i, line in enumerate(_read(__file__).splitlines())
            if line.strip().startswith("assert ")}


# ───────────────────────── المشغّل ─────────────────────────
def main():
    print("═══ L0: فحص ساكن لطبقة الرقعة ═══")
    asserts = _assert_lines()
    me = __file__
    failed = 0
    silent = []
    for name, fn in _checks:
        hit = set()

        def _tr(frame, event, arg, _hit=hit, _me=me):
            if frame.f_code.co_filename != _me:
                return None
            if event == "line":
                _hit.add(frame.f_lineno)
            return _tr

        sys.settrace(_tr)
        try:
            fn()
            sys.settrace(None)
            print(f"  ✅ {name}")
            if not (hit & asserts) and name not in ASSERT_FREE_WAIVERS:
                silent.append(name)
        except Exception as e:  # noqa: BLE001
            sys.settrace(None)
            failed += 1
            print(f"  ❌ {name}\n       {type(e).__name__}: {e}")
    print(f"─── {len(_checks) - failed}/{len(_checks)} نجحت ───")
    if silent:
        print(f"  ❌ شاهدُ التفعيل: {len(silent)} فحصًا نجح ولم يُنفّذ توكيدًا واحدًا — يقيس صفرًا:")
        for name in silent:
            print(f"       {name}")
        print("     أضِف شاهدَ تفعيلٍ موجبًا (توكيدًا أنّ ما يُفحَص وُجِد)، أو أعلِنه في "
              "ASSERT_FREE_WAIVERS بسببٍ مكتوب.")
    stale = sorted(set(ASSERT_FREE_WAIVERS) - {n for n, _ in _checks})
    for name in stale:
        print(f"  ❌ إعفاءٌ عن فحصٍ زائل: «{name}» — احذف سطرَ الإعفاء.")
    return 1 if (failed or silent or stale) else 0


if __name__ == "__main__":
    sys.exit(main())
