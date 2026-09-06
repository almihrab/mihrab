#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""رُقعة نواة محراب: اتّجاه القشرة من اليمين (RTL) — مرحلة RTL-0 (الطبقة 3).

الغرض: محراب محرّر عربيّ-أوّلًا، فالاتّجاه من اليمين **هويّة لا خيار**. نضبط
`dir="rtl"` على حاوية .monaco-workbench فيتتالى على معظم القشرة، ونستورد ورقة
`mihrab-rtl.css` (التي تحمي المحرّر/الطرفيّة LTR وتُصلِح الكسور المبكّرة).

الملفّ المنبعيّ: src/vs/workbench/browser/workbench.ts (renderWorkbench).
لماذا تعذّرت طبقة أدنى: لا سبيل لضبط اتّجاه القشرة الجذر من إعداد أو إضافة؛ يجب
على حاوية workbench نفسها قبل بناء الأجزاء.

idempotent عبر الوسم mihrab-rtl. كتابة ذرّيّة (tmp + os.replace). Python 3.12-آمن
(open(..., newline="") لا Path.read_text(newline=)).

الاستعمال: python patch_workbench_rtl.py <مسار workbench.ts>
"""
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

MARK = "mihrab-rtl"

# مرساة الاستيراد: سطر استيراد قائم ومستقرّ قرب رأس الملفّ.
IMPORT_ANCHOR = "import { runWhenWindowIdle } from '../../base/browser/dom.js';"
# ورقتان لا واحدة [VA-05]: الاتّجاه ثمّ الهويّة. **الترتيبُ مقصود** — ورقةُ الهويّة تأتي
# ثانيةً كي تفوز عند تساوي الخصوصيّة، وهي الحالةُ الوحيدة التي قد تتلاقيان فيها.
# الوسمُ `mihrab-rtl` يغطّي السطرين، فالتحقّقُ من الحقن يبقى فحصًا واحدًا لا اثنين.
RTL_IMPORT = "\nimport './media/mihrab-rtl.css'; /* mihrab-rtl */"
IDENTITY_IMPORT = "\nimport './media/mihrab-identity.css'; /* mihrab-rtl */"
IMPORT_INJECT = RTL_IMPORT + IDENTITY_IMPORT

# مرساة ضبط الاتّجاه: بعد إضافة أصناف القشرة مباشرةً، قبل بناء الأجزاء.
DIR_ANCHOR = "\t\tthis.mainContainer.classList.add(...workbenchClasses);"
DIR_INJECT = (
    "\n\t\t// محراب: اتّجاه القشرة من اليمين (RTL-0). الكود يبقى LTR عبر mihrab-rtl.css."
    "\n\t\t// نضبط dir على documentElement (<html>) أيضًا كي يرث كلّ شيء الاتّجاه — بما فيه"
    "\n\t\t// مضيفو Shadow DOM (القوائم السياقيّة) أينما التصقوا، والنوافذ المساعِدة عبر trackAttributes."
    "\n\t\tthis.mainContainer.setAttribute('dir', 'rtl'); /* mihrab-rtl */"
    "\n\t\tthis.mainContainer.ownerDocument.documentElement.setAttribute('dir', 'rtl'); /* mihrab-rtl */"
)


def _write(path: str, text: str) -> bool:
    """كتابةٌ ذرّيّة (‏tmp ثمّ `os.replace`) — تُستعمل في مسارَي الترقيع كليهما."""
    # ── [CRLF-01] المُدرَجُ يتبع نهاياتِ الملفّ ─────────────────────────────
    # سطورُ الحقن مكتوبةٌ بـ`\n` في مصدر المُرقِّع، والملفُّ يُقرأ ويُكتَب بـ
    # `newline=""` (بلا ترجمة) كي يعود كما وُجِد. وشجرةُ ويندوز تُستنسَخ
    # بـ`core.autocrlf` مفعَّلًا، فالحقنُ يُنتج ملفًّا **مختلطَ النهايات**: يُصرَّف
    # ويُشحَن، ولا يُرى في المحرّر، ويُفسِد كلَّ فرقٍ بعده.
    #
    # والقاعدةُ تُقرأ من النصّ نفسِه لا من نسخةٍ سابقة، فتصلح لكلّ مسارٍ يمرّ من
    # هنا وتبقى idempotent: ملفٌّ أغلبُه CRLF يُوحَّد إليه، وملفُّ LF لا يُمَسّ.
    _crlf = text.count("\r\n")
    if _crlf > text.count("\n") - _crlf:
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")

    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp, path)
        return True
    except OSError as e:
        try:
            os.remove(tmp)
        except OSError:
            pass
        print(f"⚠️ تعذّر كتابة {path}: {e}", file=sys.stderr)
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print("الاستعمال: python patch_workbench_rtl.py <مسار workbench.ts>", file=sys.stderr)
        return 2
    path = sys.argv[1]
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            text = f.read()
    except OSError as e:
        print(f"⚠️ تعذّر فتح {path}: {e}", file=sys.stderr)
        return 1

    if MARK in text:
        # **الـidempotency لا تُقاس بوسمٍ واحدٍ حين تنمو الرُقعة.** شجرةٌ رُقِّعت بنسخةٍ
        # أقدم (‏قبل [VA-05]) تحمل الوسمَ وتنقصها ورقةُ الهويّة، فالتخطّي بالوسم وحدَه
        # كان يترك الشعارَ غائبًا **بلا خطأ بناءٍ واحد** — وهو صنفُ العطب الذي يمرّ.
        if IDENTITY_IMPORT in text:
            print("مُرقَّع مسبقًا — تخطٍّ.")
            return 0
        if RTL_IMPORT not in text:
            print("⚠️ الوسمُ موجودٌ ولا استيرادَ لورقة الاتّجاه — شجرةٌ مُرقَّعةٌ بصورةٍ غيرِ "
                  "متوقَّعة؛ أعِد ضبطَ المصدر (git reset) قبل الترقيع.", file=sys.stderr)
            return 1
        text = text.replace(RTL_IMPORT, RTL_IMPORT + IDENTITY_IMPORT, 1)
        if not _write(path, text):
            return 1
        print("✅ أُكمِلت الرُقعة: أُضيف استيرادُ ورقة الهويّة [VA-05].")
        return 0

    for anchor, label in ((IMPORT_ANCHOR, "الاستيراد"), (DIR_ANCHOR, "ضبط الاتّجاه")):
        if anchor not in text:
            print(f"⚠️ لم تُعثَر مرساة «{label}» في workbench.ts — ربّما تغيّر المنبع.", file=sys.stderr)
            return 1

    text = text.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + IMPORT_INJECT, 1)
    text = text.replace(DIR_ANCHOR, DIR_ANCHOR + DIR_INJECT, 1)

    if not _write(path, text):
        return 1

    print("✅ رُقِّع workbench.ts (اتّجاه القشرة RTL + استيرادُ ورقتَي الأنماط).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
