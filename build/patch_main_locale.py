#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""رُقعة نواة محراب: لغة الواجهة الافتراضيّة من product.defaultLocale.

src/mainImpl.ts (كان src/main.ts حتّى 1.126؛ نُقل حرفيًّا في 1.143) يحلّ لغة الواجهة: --locale ← argv.json.locale ← لغة النظام ← en.
لجعل محراب عربيّ الواجهة افتراضيًّا (دون أن يحدّد المستخدم شيئًا)، نجعل
getUserDefinedLocale يرجع product.defaultLocale عند غياب تحديد المستخدم.
(الطبقة الثالثة — أوّل رُقعة نواة في محراب؛ لا سبيل لضبط اللغة الافتراضيّة من
الطبقتين 1/2 لأنّ الحلّ يجري في النواة قبل تحميل الإضافات.)

idempotent: يتحقّق من الوسم. متوافق مع Python 3.12 (open الصريح، لا newline=).
الاستعمال: python patch_main_locale.py <مسار src/mainImpl.ts>
"""
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

MARK = "mihrab-default-locale"

OLD = (
    "\treturn typeof argvConfig?.locale === 'string' ? "
    "argvConfig.locale.toLowerCase() : undefined;"
)
# نستعمل (product as any) لتفادي خطأ فحص أنواع TS (defaultLocale غير معرَّف في
# IProductConfiguration؛ هو حقل محراب نُضيفه عبر product-overrides).
NEW = (
    "\treturn typeof argvConfig?.locale === 'string' ? "
    "argvConfig.locale.toLowerCase() : "
    "(typeof (product as any).defaultLocale === 'string' ? "
    "(product as any).defaultLocale.toLowerCase() : undefined); "
    "/* mihrab-default-locale */"
)


def main() -> int:
    if len(sys.argv) != 2:
        print("الاستعمال: python patch_main_locale.py <مسار src/mainImpl.ts>", file=sys.stderr)
        return 2
    path = sys.argv[1]
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            text = f.read()
    except OSError as e:
        print(f"⚠️ تعذّر فتح {path}: {e}", file=sys.stderr)
        return 1
    if MARK in text:
        print("مُرقَّع مسبقًا — تخطٍّ.")
        return 0
    if OLD not in text:
        print("⚠️ لم يُعثر على سطر getUserDefinedLocale المتوقّع — ربّما تغيّر mainImpl.ts.", file=sys.stderr)
        return 1
    text = text.replace(OLD, NEW, 1)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError as e:
        try:
            os.remove(tmp)
        except OSError:
            pass
        print(f"⚠️ تعذّر كتابة {path}: {e}", file=sys.stderr)
        return 1
    print("✅ رُقِّع mainImpl.ts (لغة افتراضيّة من product.defaultLocale).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
