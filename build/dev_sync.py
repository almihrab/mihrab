#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مزامنة طبقتَي محراب 2/3 إلى شجرة المنبع للتشغيل الحيّ (dev run) — لا بناء كامل.

الغرض: رؤية محراب **حيًّا** بعد كلّ تعديل تصميم، دون دورة `build.sh` الكاملة (ساعات، ≥30GB).
يجسّد الخطوات نفسها التي تحقنها كتلة INJECT في `patch_bundle_extensions.py` داخل build.sh
المنبع، لكن مباشرةً على `.upstream/vscode` كي يلتقطها `scripts/code.bat` (وضع التطوير).

⚠️ **لا يكرّر قائمة الأهداف**: يشتقّ كلّ شيء من `tests/patch_manifest.py` — مصدر الحقيقة
نفسه الذي يفحصه L0/L1. إضافة مرقِّع هناك تسري هنا تلقائيًّا، فلا ينجرف التشغيل الحيّ عن
البناء الحقيقيّ (وهو الخطر الأوّل لأيّ مسار «مختصر»).

الخطوات (كلّها idempotent — المرقِّعات تتخطّى إن وجدت وسمها):
  1. ورقة الأنماط  patches/mihrab-rtl.css → src/vs/workbench/browser/media/
  2. أصول الهوية   (SVG الأسطح + sessions) → وجهاتها في src/
  3. المرقِّعات      كلّ مرقِّع في PATCHERS على أهدافه
  4. الامتدادات    extensions/mihrab-* + language-pack-ar → <منبع>/extensions/
  5. الهوية        product-overrides/product.json مدموجًا فوق product.json المنبع

الاستعمال:  python build/dev_sync.py [--upstream .upstream/vscode] [--revert]
            --revert يُرجِع product.json وحده (الملفّات المُرقَّعة تُستعاد بـgit checkout).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import patch_manifest as M  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "build", "lib"))
import help_data  # noqa: E402

BUILD = os.path.join(ROOT, "build")
# الامتدادات المحزومة (الطبقة 1) التي تُنسَخ إلى شجرة المنبع كامتدادات مدمجة.
BUNDLED_EXTENSIONS = ("mihrab-shell", "mihrab-themes", "mihrab-icons", "mihrab-welcome",
                      "language-pack-ar")
PRODUCT_BACKUP = "product.json.mihrab-orig"


def log(msg):
    print(f"▶ {msg}")


def sync_css(up):
    """ينسخ ورقتَي الأنماط: الاتّجاه ثمّ الهويّة [VA-05].

    الاسمُ في الوجهة مشتقٌّ من اسم الملفّ في المصدر لا مكتوبًا حرفيًّا — فتبديلُ مسارٍ في
    المانيفست ينتقل إلى هنا وحدَه، ولا يبقى اسمٌ قديمٌ يُنسَخ إليه صامتًا.
    """
    media = os.path.join(up, "src", "vs", "workbench", "browser", "media")
    os.makedirs(media, exist_ok=True)
    for rel in (M.CSS_PATCH, M.IDENTITY_CSS):
        src = os.path.join(ROOT, rel)
        dst = os.path.join(media, os.path.basename(rel))
        shutil.copyfile(src, dst)
        log(f"ورقة الأنماط ← {os.path.relpath(dst, up)}")


def sync_assets(up):
    """أصول SVG للأسطح + مساحة sessions. غياب وجهة sessions ليس فشلًا (مساحة تجريبيّة
    قد تغيب في وسوم منبع أقدم) — نُبلّغ ونتابع، خلافًا للبناء الحقيقيّ الذي يُفشِل."""
    n = 0
    for src_rel, dst_rel in list(M.BRANDING_SVG_ASSETS) + list(M.BRANDING_SESSIONS_ASSETS):
        src, dst = os.path.join(ROOT, src_rel), os.path.join(up, *dst_rel.split("/"))
        if not os.path.isfile(src):
            print(f"  ⚠️ أصل مفقود (تخطٍّ): {src_rel}", file=sys.stderr)
            continue
        if not os.path.isdir(os.path.dirname(dst)):
            print(f"  ⚠️ وجهة غير موجودة في هذا المنبع (تخطٍّ): {dst_rel}", file=sys.stderr)
            continue
        shutil.copyfile(src, dst)
        n += 1
    log(f"أصول الهوية: نُسِخ {n}")


def apply_core_diffs(up):
    """رُقَعُ المنبع (diff موحَّد) — تُطبَّق بـ`git apply --3way` كما في البناء الحقيقيّ.

    مُتسامِحٌ مع «مطبَّقةٌ مسبقًا»: التشغيل الحيّ يُعاد على الشجرة نفسها مرارًا، و`git apply`
    ليس idempotent. نفحص أوّلًا بـ`--check --reverse`: إن نجح فالرقعةُ فيها فعلًا."""
    rc = 0
    for diff_rel in getattr(M, "CORE_DIFFS", []):
        patch = os.path.join(ROOT, *diff_rel.split("/"))
        if not os.path.isfile(patch):
            print(f"  ⚠️ رُقعةُ منبعٍ مفقودة (تخطٍّ): {diff_rel}", file=sys.stderr)
            continue
        name = os.path.basename(diff_rel)
        rev = subprocess.run(["git", "apply", "--check", "--reverse", patch], cwd=up,
                             capture_output=True)
        if rev.returncode == 0:
            print(f"  ⏭️ {name}: مطبَّقةٌ مسبقًا")
            continue
        p = subprocess.run(["git", "apply", "--3way", patch], cwd=up, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        if p.returncode == 0:
            print(f"  ✅ {name}: طُبِّقت")
        else:
            rc = 1
            print(f"  ❌ {name}: {(p.stdout or p.stderr).strip()[:300]}")
    return rc


def sync_patchers(up):
    rc = 0
    for name, mode, targets in M.PATCHERS:
        patcher = os.path.join(BUILD, name)
        args = [os.path.join(up, *t.split("/")) for t in targets] if mode == "file" else [up]
        for arg in args:
            if mode == "file" and not os.path.isfile(arg):
                print(f"  ⚠️ هدف مفقود (تخطٍّ): {os.path.relpath(arg, up)}", file=sys.stderr)
                continue
            p = subprocess.run([sys.executable, patcher, arg], capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            tag = "✅" if p.returncode == 0 else "❌"
            print(f"  {tag} {name}: {(p.stdout or p.stderr).strip().splitlines()[-1] if (p.stdout or p.stderr).strip() else 'تمّ'}")
            if p.returncode != 0:
                rc = 1
    return rc


def sync_extensions(up):
    n = 0
    for ext in BUNDLED_EXTENSIONS:
        src = os.path.join(ROOT, "extensions", ext)
        if not os.path.isdir(src):
            continue
        dst = os.path.join(up, "extensions", ext)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        # نتخطّى ضجيج التطوير، و**نجرّد `*.py` كما يفعل build.sh حرفيًّا**: مولّدات
        # السمات/الأيقونات مصنوعاتُ توليد لا جزءٌ من المنتج. تركُها هنا كان **انحرافًا عن
        # البناء الحقيقيّ** — وهو عين ما وُجد هذا الملفّ ليتجنّبه. أمسكه فحص L2 على أوّل
        # حزمةٍ غُلِّفت من هذه الشجرة: «مولّد الأيقونات شُحن مع المنتج».
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
            "node_modules", "__pycache__", "*.test.js", ".gitignore", "*.py"))
        # [ON-03] بياناتُ المساعدة تُولَّد من `site/data/` كما يفعل build.sh، لا تُنسَخ من نسخةٍ محفوظة.
        if ext == "mihrab-welcome":
            help_data.sync(dst)
        n += 1
    log(f"الامتدادات المدمجة: نُسِخ {n}")


def sync_product(up):
    """يدمج هوية محراب فوق product.json المنبع، بعد حفظ نسخة أصليّة لمرّة واحدة."""
    prod = os.path.join(up, "product.json")
    backup = os.path.join(up, PRODUCT_BACKUP)
    if not os.path.isfile(prod):
        print("  ⚠️ لا product.json في المنبع — تخطٍّ", file=sys.stderr)
        return
    if not os.path.isfile(backup):
        shutil.copyfile(prod, backup)
    # ندمج دائمًا فوق **الأصل** لا فوق ناتج دمج سابق ⇒ إزالة مفتاح من التجاوزات تسري فعلًا.
    base = json.load(open(backup, encoding="utf-8"))
    over = json.load(open(os.path.join(ROOT, "product-overrides", "product.json"), encoding="utf-8"))
    # كلّ مفتاحٍ يبدأ بـ_comment تعليقٌ لا حقلُ منتج (صار أكثر من واحد).
    for k in [k for k in over if k.startswith("_comment")]:
        over.pop(k)
    base.update(over)
    with open(prod, "w", encoding="utf-8", newline="\n") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)
        f.write("\n")
    log(f"هوية المنتج: دُمِج {len(over)} مفتاحًا (nameLong={base.get('nameLong')}, locale={base.get('defaultLocale')})")


def revert_product(up):
    prod, backup = os.path.join(up, "product.json"), os.path.join(up, PRODUCT_BACKUP)
    if os.path.isfile(backup):
        shutil.copyfile(backup, prod)
        log("أُعيد product.json الأصليّ")
    else:
        print("لا نسخة أصليّة محفوظة — لا شيء لإرجاعه", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="مزامنة طبقتَي محراب 2/3 لشجرة المنبع (تشغيل حيّ)")
    ap.add_argument("--upstream", default=os.path.join(ROOT, ".upstream", "vscode"))
    ap.add_argument("--revert", action="store_true", help="أعِد product.json الأصليّ وحسب")
    a = ap.parse_args()
    up = os.path.abspath(a.upstream)
    if not os.path.isdir(os.path.join(up, "src", "vs")):
        print(f"❌ ليست شجرة مصدر vscode: {up}\n   شغّل build/prepare.sh أوّلًا.", file=sys.stderr)
        return 2
    if a.revert:
        revert_product(up)
        return 0

    print(f"═══ مزامنة محراب → {up} ═══")
    sync_css(up)
    sync_assets(up)
    rc = sync_patchers(up)
    rc |= apply_core_diffs(up)
    sync_extensions(up)
    sync_product(up)
    print("═══ " + ("✅ جاهز للتشغيل الحيّ" if rc == 0 else "❌ فشل مرقِّع — راجع أعلاه") + " ═══")
    if rc == 0:
        print("التالي:  node tests/runtime/launch.mjs --build   (تصريف + إطلاق + لقطة)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
