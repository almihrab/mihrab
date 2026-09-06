#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""رُقعة نواة محراب: وسم splitview شبكة القشرة/المحرّر — RTL-2 مساعِدة (الطبقة 3).

مُمكِّنة لرُقعتَي splitview+sash العامّتين: تميّز SplitView الذي يُنشئه `gridview`
(شبكة القشرة **وشبكة المحرّر** كلتاهما تستعملان `BranchNode`) بإضافة صنف
`mihrab-grid-sv` على `.el`. عندها تقلب رُقعتا splitview/sash فقط الـSplitView **المستقلّة**
(محرّر الإعدادات، peek، master-detail…) عبر فحص «أقرب `.monaco-split-view2` بلا هذا الوسم»
— فلا تُخطئ باستثناء كلّ ما يقع داخل شبكة المحرّر (عيب `closest('.monaco-grid-view')`).

الملفّ المنبعيّ: src/vs/base/browser/ui/grid/gridview.ts (BranchNode).
idempotent (وسم mihrab-grid-sv)، كتابة ذرّيّة، Python 3.12-آمن.
الاستعمال: python patch_gridview_marker.py <مسار gridview.ts>
"""
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

MARK = "mihrab-grid-sv"

_TAG = "\n\t\t\tthis.splitview.el.classList.add('mihrab-grid-sv'); /* mihrab: وسم splitview الشبكة كي تستثنيه رُقَع RTL */"

# مساران لإنشاء splitview الشبكة في BranchNode: (429) طازج، و(447) استعادة/تسلسل
# (يُستدعى عند فتح نافذة بمحرّر مقسوم محفوظ). نسِم كليهما وإلا انقلبت مجموعات المحرّر
# المستعادة (قلب مزدوج كاسر — رصدته مراجعة Amelia). كلّ عنصر: (مرساة سطر-واحد، إضافة بعده).
EDITS = [
    "\t\t\tthis.splitview = new SplitView(this.element, { orientation, styles, proportionalLayout: splitviewProportionalLayout });",
    "\t\t\tthis.splitview = new SplitView(this.element, { ...options, descriptor });",
]


def main() -> int:
    if len(sys.argv) != 2:
        print("الاستعمال: python patch_gridview_marker.py <مسار gridview.ts>", file=sys.stderr)
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
    for anchor in EDITS:
        if anchor not in text:
            print(f"⚠️ لم تُعثَر مرساة إنشاء SplitView: «{anchor[-45:]}» — ربّما تغيّر المنبع.", file=sys.stderr)
            return 1

    for anchor in EDITS:
        text = text.replace(anchor, anchor + _TAG, 1)

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
    except OSError as e:
        try:
            os.remove(tmp)
        except OSError:
            pass
        print(f"⚠️ تعذّر كتابة {path}: {e}", file=sys.stderr)
        return 1

    print("✅ رُقِّع gridview.ts (وسم mihrab-grid-sv على splitview الشبكة).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
