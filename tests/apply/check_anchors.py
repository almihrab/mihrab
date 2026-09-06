#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L1 — فحص تطبيق مراسي الرُقَع على المنبع المثبَّت (1–2 د، بلا بناء).

**أعلى مردود**: يحوّل «فشل بناء صامت بعد 20 د» إلى «أحمر فوريّ». لكلّ مرقِّع RTL/لغة:
يجهّز نسخة **نظيفة** من ملفّات المنبع التي يمسّها في مجلّد مؤقّت، يشغّل المرقِّع الفعليّ
(كود الإنتاج) عليها، ويتحقّق أنّه: (أ) طبَّق فعلًا (المحتوى تغيّر والوسم حُقن)، (ب) نجح
(خرج 0 — مراسيه طابقت بعددها المتوقَّع)، (ج) idempotent (إعادة التشغيل لا تغيّر شيئًا).

مصدر النظيف (بالأولويّة):
  1) .upstream/vscode (مستودع git، HEAD = نظيف المنبع المثبَّت) — الأوثق والأحدث.
  2) tests/apply/snapshot/ — لقطة مُلتزَمة (لـCI بلا منبع محضَّر). حدّثها بـrefresh_snapshot.py.
إن غاب الاثنان: تخطٍّ برسالة واضحة (خرج 0، غير حاجب) — CI بلا منبع.

**حدّ معروف (كلّ الرُقَع):** HEAD = VSCode النقيّ من مايكروسوفت، بينما البناء الفعليّ يرقّع
شجرة عمل VSCodium (تُطبَّق تعديلات VSCodium غير المُلتزَمة أثناء prepare). لملفّات يعدّلها
VSCodium بكثافة (مثل gettingStarted.ts — يضيف «الإعلانات») تبقى مراسينا الحاليّة متطابقة في
HEAD وشجرة العمل، لكنّ L1 الأخضر لا يبرهن صمود المرساة على الهدف المُعدَّل مستقبلًا ⇒ إن غيّرت
نسخة VSCodium كتلةً مرقَّعة، ينكسر البناء رغم L1 أخضر. التخفيف: L2 (مِجَسّ الحزمة المبنيّة)
وL3 (الوقتيّ) يمسكان الانكسار الفعليّ بعد البناء.

الاستعمال: python tests/apply/check_anchors.py   (خرج 0 = نجاح/تخطٍّ، 1 = انجراف مرساة)
"""
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BUILD = os.path.join(ROOT, "build")
UPSTREAM_VSCODE = os.path.join(ROOT, ".upstream", "vscode")
SNAPSHOT = os.path.join(HERE, "snapshot")
sys.path.insert(0, os.path.dirname(HERE))
import patch_manifest as M  # noqa: E402


def _git_show(relpath):
    """محتوى ملفّ نظيف من .upstream/vscode عند HEAD، أو None إن تعذّر."""
    try:
        out = subprocess.run(
            ["git", "-C", UPSTREAM_VSCODE, "show", f"HEAD:{relpath}"],
            capture_output=True, check=True)
        return out.stdout.decode("utf-8", errors="replace")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _force_snapshot():
    # `--snapshot` مرادفٌ للمتغيّر البيئيّ، ووجودُه ليس ترفًا: **حارسُ الحرّاس** يشغّل
    # الحُرّاسَ عبر صَدَفةِ النظام، وصيغةُ `VAR=x cmd` لا تعمل على cmd.exe في ويندوز —
    # فمُصابٌ يحتاج وضعَ اللقطة كان سيتعذّر زرعُه، أي حارسٌ بلا مُصابٍ بحُجّةٍ بيئيّة.
    return (os.environ.get("MIHRAB_L1_SOURCE", "").strip().lower() == "snapshot"
            or "--snapshot" in sys.argv[1:])


def _pristine_source(relpath):
    """أعِد محتوى الملفّ النظيف من المصدر المتاح (upstream ثمّ snapshot)، أو None.

    MIHRAB_L1_SOURCE=snapshot يُجبِر اللقطة المُلتزَمة (لـCI أو تجاهُل منبع محلّيّ قديم)."""
    if not _force_snapshot() and os.path.isdir(os.path.join(UPSTREAM_VSCODE, ".git")):
        c = _git_show(relpath)
        if c is not None:
            return c, "upstream"
    snap = os.path.join(SNAPSHOT, relpath)
    if os.path.isfile(snap):
        with open(snap, "r", encoding="utf-8", newline="") as f:
            return f.read(), "snapshot"
    return None, None


def _targets_for(name, mode):
    if mode == "root":
        return M.root_target_files(BUILD, name)
    for pname, _m, targets in M.PATCHERS:
        if pname == name:
            return targets
    return []


def _run(patcher, arg):
    r = subprocess.run([sys.executable, os.path.join(BUILD, patcher), arg],
                       capture_output=True)
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", errors="replace")


# ── [CRLF-01] نهاياتُ السطر بُعدٌ في القياس لا تفصيلٌ في التنسيق ──────────────
# ‏`git show` لا يمرّ بمرشّح `smudge`، فالمصدرُ النظيفُ هنا **دائمًا LF** مهما كانت
# شجرةُ العمل. وشجرةُ ويندوز تُستنسَخ بـ`core.autocrlf` مفعَّلًا فسطرُها `\r\n`.
# أي أنّ L1 كان يقيس نهاياتٍ لا تُشحَن على نصف منصّاتنا.
#
# وثمنُ الثغرة قِيس: `patch_welcome_web_entries.py` يحمل مِرساةً فيها `\n` حرفيًّا،
# فمرَّ في L1 أخضرَ ونجح على لينكس **وسقط على ويندوز بعد `npm ci` وترقيعِ المنبع
# كلِّه** — أربعون دقيقةً حتّى الرسالة، ورسالةٌ لا تذكر نهاياتِ السطر.
#
# فكلُّ مرقِّعٍ يُجرَّب مرّتين. والكلفةُ ثوانٍ، والمكسبُ أنّ فئةَ العطب هذه تموت
# عند الحاسوب لا عند البناء.
_EOLS = (("LF", "\n"), ("CRLF", "\r\n"))


def _as_eol(text, eol):
    return text.replace("\r\n", "\n").replace("\n", eol)


def check_patcher(name, mode):
    """يعيد (ok:bool, رسالة) — بعد تجربةِ المرقِّع على LF وعلى CRLF."""
    msgs = []
    for label, eol in _EOLS:
        ok, msg = _check_patcher_eol(name, mode, eol)
        if ok is None:
            return None, msg           # لا مصدرَ نظيف: تخطٍّ واحدٌ يكفي
        if not ok:
            return False, f"[{label}] {msg}"
        msgs.append(msg)
    # الرسالتان متطابقتان عمليًّا؛ تُعرَض إحداهما مع بيانِ أنّ البُعدين قيسا.
    return True, msgs[0] + " · LF+CRLF"


def _check_patcher_eol(name, mode, eol):
    """يعيد (ok:bool, رسالة)."""
    targets = _targets_for(name, mode)
    tmp = tempfile.mkdtemp(prefix="mihrab_l1_")
    try:
        # جهّز الملفّات النظيفة في البنية النسبيّة
        srcs = {}
        for rel in targets:
            content, origin = _pristine_source(rel)
            if content is None:
                return None, f"لا مصدر نظيف لـ{rel} (تخطٍّ)"
            content = _as_eol(content, eol)
            dst = os.path.join(tmp, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8", newline="") as f:
                f.write(content)
            srcs[rel] = (dst, content, origin)

        arg = tmp if mode == "root" else srcs[targets[0]][0]

        rc1, out1 = _run(name, arg)
        if rc1 != 0:
            return False, f"خرج غير صفريّ ({rc1}) — انجراف مرساة؟\n       {out1.strip()[:400]}"
        # تحصين: بعض المرقِّعات متعدّدة المراسي قد تتخطّى مرساةً منجرفة بتحذير وتخرج 0
        # (تطبيق جزئيّ). أيّ تحذير ⇒ فشل (نمنع النجاح الكاذب للتطبيق الجزئيّ).
        if "⚠️" in out1 or "لم تُعثَر" in out1 or "غير متوقَّع" in out1:
            return False, f"تحذير مرساة رغم خرج 0 (تطبيق جزئيّ؟)\n       {out1.strip()[:400]}"

        # (أ) طبَّق فعلًا: محتوى ملفّ واحد على الأقلّ تغيّر
        changed = []
        after = {}
        for rel, (dst, before, _o) in srcs.items():
            with open(dst, "r", encoding="utf-8", newline="") as f:
                a = f.read()
            after[rel] = a
            if a != before:
                changed.append(rel)
        if not changed:
            return False, "لم يتغيّر أيّ ملفّ (المرقِّع لم يطبِّق — مرساة مفقودة صامتًا؟)"

        # (ج) idempotent: إعادة التشغيل تنجح ولا تغيّر شيئًا
        rc2, out2 = _run(name, arg)
        if rc2 != 0:
            return False, f"إعادة التشغيل فشلت ({rc2}) — ليس idempotent\n       {out2.strip()[:300]}"
        for rel, (dst, _b, _o) in srcs.items():
            with open(dst, "r", encoding="utf-8", newline="") as f:
                a2 = f.read()
            if a2 != after[rel]:
                return False, f"إعادة التشغيل غيّرت {rel} (تطبيق مزدوج — ليس idempotent)"

        # ولا يُترَك ملفٌّ **مختلطَ النهايات**: مُرقِّعٌ يحقن سطورَ LF في ملفٍّ
        # بـCRLF يُنتج ملفًّا يُصرَّف ويُشحَن ويُفسِد كلَّ فرقٍ بعده — عطبٌ لا يُرى
        # في المحرّر ويُرى في كلّ مراجعة.
        for rel in changed:
            a = after[rel]
            lone = a.count("\n") - a.count("\r\n")
            crlf = a.count("\r\n")
            if lone and crlf:
                return False, (f"{rel} صار مختلطَ النهايات بعد الترقيع "
                               f"({crlf} CRLF · {lone} LF) — المُدرَجُ لا يتبع الملفّ")

        origin = next(iter(srcs.values()))[2]
        return True, f"طبَّق {len(changed)} ملفّ، idempotent [{origin}]"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_core_diff(diff_rel):
    """رُقعةُ منبعٍ (diff): تُطبَّق نظيفةً على المنبع المثبَّت؟ يعيد (ok, رسالة).

    لا مراسيَ هنا تُفحَص فرديًّا — الفحصُ أقوى: نجهّز الملفّات النظيفة التي يمسّها الـdiff
    في مجلّد مؤقّت ونشغّل `git apply --check` عليه. أيّ انجرافٍ في المنبع يظهر فورًا،
    وبنفس الأداة التي يستعملها البناء (patch_bundle_extensions ⇐ `git apply --3way`).
    """
    targets = M.core_diff_files(ROOT, diff_rel, existing_only=True)
    if not targets:
        return False, "رُقعةٌ بلا ملفّات (شكلٌ غير متوقَّع)"
    tmp = tempfile.mkdtemp(prefix="mihrab_l1_diff_")
    try:
        origin = None
        for rel in targets:
            content, org = _pristine_source(rel)
            if content is None:
                return None, f"لا مصدر نظيف لـ{rel} (تخطٍّ)"
            origin = origin or org
            dst = os.path.join(tmp, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8", newline="") as f:
                f.write(content)
        patch = os.path.join(ROOT, diff_rel.replace("/", os.sep))
        r = subprocess.run(["git", "apply", "--check", "--verbose", patch],
                           cwd=tmp, capture_output=True)
        if r.returncode != 0:
            err = (r.stdout + r.stderr).decode("utf-8", errors="replace").strip()[:500]
            return False, f"لا تُطبَّق على المنبع المثبَّت (انجراف):{chr(10)}       {err}"
        return True, f"تُطبَّق نظيفةً على {len(targets)} ملفًّا [{origin}]"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_CSP_SHA_RE = re.compile(r"'sha256-([A-Za-z0-9+/=]+)'")
_INLINE_SCRIPT_RE = re.compile(r"<script(?![^>]*\ssrc=)[^>]*>(.*?)</script>", re.S)


def check_webview_csp():
    """بصمةُ CSP لمستضيف الـwebview تطابق برنامجَه المضمَّن؟ يعيد (ok, رسالة).

    **ليس فحصَ مرساة — بل كمينٌ يُنزَع قبل أن يقع.** `pre/index.html` يستضيف كلَّ لوحة
    webview في المحرّر، وترويسةُ CSP فيه تسمح ببرنامجٍ مضمَّنٍ واحدٍ ببصمة `sha256-`.
    البصمةُ مصونةٌ **يدويًّا**: لا خطوةَ بناءٍ تعيد حسابها. فأيُّ رقعةِ محرابٍ مستقبليّةٍ
    تلمس جسمَ ذلك البرنامج — ولو بمِحرفٍ — تُبطِل البصمةَ، فيحجب المتصفّحُ البرنامجَ
    وتنطفئ اللوحاتُ كلُّها **صامتةً**: لا خطأً في الطرفيّة ولا لوحًا فارغًا مُعلَّلًا،
    فيُقرأ العطبُ «الامتدادُ لا يعمل» لا «الرقعةُ كسرت CSP».

    والحسابُ على الجسم **بعد تسوية الأسطر إلى LF**: قِيس الطرفان، فبصمةُ CRLF لا تطابق
    الترويسةَ وبصمةُ LF تطابقها حرفًا. وهذا وحدَه فخٌّ ثانٍ على ويندوز، حيث تُسلَّم شجرةُ
    العمل بـCRLF بينما المُسلَّم إلى المتصفّح LF.
    """
    rel = getattr(M, "WEBVIEW_HOST_HTML", None)
    if not rel:
        return None, "لا WEBVIEW_HOST_HTML في البيان (تخطٍّ)"
    content, origin = _pristine_source(rel)
    if content is None:
        return None, f"لا مصدر نظيف لـ{rel} (تخطٍّ)"
    # لو مسَّت رقعةُ نواةٍ هذا الملفَّ، فالمقيسُ هو **ما يُشحَن** لا ما في المنبع.
    touching = [d for d in getattr(M, "CORE_DIFFS", [])
                if rel in M.core_diff_files(ROOT, d, existing_only=True)]
    if touching:
        tmp = tempfile.mkdtemp(prefix="mihrab_csp_")
        try:
            dst = os.path.join(tmp, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8", newline="") as f:
                f.write(content)
            for d in touching:
                r = subprocess.run(["git", "apply", os.path.join(ROOT, d.replace("/", os.sep))],
                                   cwd=tmp, capture_output=True)
                if r.returncode != 0:
                    return False, f"تعذّر تطبيق {os.path.basename(d)} لقياس البصمة"
            with open(dst, "r", encoding="utf-8", newline="") as f:
                content = f.read()
            origin = f"{origin}+{len(touching)} رقعة"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    declared = _CSP_SHA_RE.findall(content)
    scripts = _INLINE_SCRIPT_RE.findall(content)
    if not declared:
        return False, "لا بصمةَ sha256 في ترويسة CSP — أزيلت أو تغيّر شكلُها"
    if not scripts:
        return False, "لا برنامجَ مضمَّنًا في المستضيف — تغيّر شكلُ الملفّ"
    actual = {base64.b64encode(
        hashlib.sha256(s.replace("\r\n", "\n").encode("utf-8")).digest()).decode()
        for s in scripts}
    missing = [d for d in declared if d not in actual]
    if missing:
        return False, ("بصمةُ CSP لا تطابق البرنامجَ المضمَّن — كلُّ لوحات الـwebview "
                       f"ستنطفئ صامتةً.{chr(10)}       المُعلَنة: {missing[0][:16]}… · "
                       f"المحسوبة: {sorted(actual)[0][:16]}…{chr(10)}"
                       "       أعِد حسابَ السطر 8 من index.html: sha256 على جسم البرنامج بعد تسوية LF.")
    return True, f"بصمةُ CSP تطابق البرنامجَ المضمَّن ({len(scripts)} برنامج) [{origin}]"


def main():
    print("═══ L1: تطبيق مراسي الرُقَع على المنبع المثبَّت ═══")
    have_upstream = os.path.isdir(os.path.join(UPSTREAM_VSCODE, ".git")) and not _force_snapshot()
    have_snapshot = os.path.isdir(SNAPSHOT)
    if not have_upstream and not have_snapshot:
        print("  ⏭️  لا .upstream/vscode ولا لقطة — تخطٍّ (شغّل build/prepare أو refresh_snapshot.py).")
        return 0
    print(f"  المصدر: {'upstream (git HEAD)' if have_upstream else 'snapshot مُلتزَمة'}")
    failed = skipped = 0

    # وسمُ اللقطة يُقارَن بالوسم المثبَّت. كان `SNAPSHOT_TAG.txt` **يُكتَب ولا يُقرأ**:
    # لقطةٌ من وسمٍ آخر تجعل كلَّ مرساةٍ أدناه تُقاس على شجرةٍ ليست التي نبني عليها،
    # فتخضرّ ‎18‎ مرساةً على منبعٍ لا وجودَ له. أمسك هذا **حارسُ الحرّاس** بعطبٍ مزروع.
    tag_file = os.path.join(SNAPSHOT, "SNAPSHOT_TAG.txt")
    if have_snapshot and os.path.isfile(tag_file):
        with open(tag_file, encoding="utf-8") as f:
            head = f.readline().strip()
        recorded = head.split(":", 1)[1].strip() if ":" in head else head
        try:
            with open(os.path.join(ROOT, "upstream.json"), encoding="utf-8") as f:
                pinned = json.load(f)["vscodium"]["tag"]
        except (OSError, ValueError, KeyError):
            pinned = None
        if pinned and recorded != pinned:
            failed += 1
            print(f"  ❌ وسمُ اللقطة {recorded} ≠ الوسم المثبَّت {pinned} — "
                  f"اللقطةُ من شجرةٍ أخرى، فكلُّ مرساةٍ بعدها تُقاس على غير ما يُبنى.")
            print("       شغّل: python tests/apply/refresh_snapshot.py")
        elif pinned:
            print(f"  ✅ وسمُ اللقطة يطابق المثبَّت ({pinned})")
    for name, mode, _targets in M.PATCHERS:
        ok, msg = check_patcher(name, mode)
        if ok is None:
            skipped += 1
            print(f"  ⏭️  {name}: {msg}")
        elif ok:
            print(f"  ✅ {name}: {msg}")
        else:
            failed += 1
            print(f"  ❌ {name}: {msg}")
    for diff in getattr(M, "CORE_DIFFS", []):
        ok, msg = check_core_diff(diff)
        name = os.path.basename(diff)
        if ok is None:
            skipped += 1
            print(f"  ⏭️  {name}: {msg}")
        elif ok:
            print(f"  ✅ {name}: {msg}")
        else:
            failed += 1
            print(f"  ❌ {name}: {msg}")
    ok, msg = check_webview_csp()
    if ok is None:
        skipped += 1
        print(f"  ⏭️  بصمةُ CSP للـwebview: {msg}")
    elif ok:
        print(f"  ✅ بصمةُ CSP للـwebview: {msg}")
    else:
        failed += 1
        print(f"  ❌ بصمةُ CSP للـwebview: {msg}")

    total = len(M.PATCHERS) + len(getattr(M, "CORE_DIFFS", [])) + 1
    print(f"─── {total - failed - skipped}/{total} نجحت، {skipped} تخطٍّ، {failed} فشل ───")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
