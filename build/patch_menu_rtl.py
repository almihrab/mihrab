#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""رُقعة نواة محراب: اتّجاه القوائم المنسدلة/السياقيّة في RTL — RTL-2 (الطبقة 3).

تطبّق تعديلين على src/vs/base/browser/ui/menu/menu.ts:

(1) تعاقب القائمة الفرعيّة يسارًا (mihrab-rtl-submenu): expandDirection ← Left عند RTL.

(2) قواعد CSS للاتّجاه داخل مولّد `getMenuWidgetCSS` (mihrab-rtl-menu-css): السبب الجذريّ
    أنّ القوائم السياقيّة تُصيَّر في **Shadow DOM**، فقواعد CSS على مستوى المستند (mihrab-rtl.css)
    لا تخترق الظلّ. لكنّ ناتج `getMenuWidgetCSS` يُحقَن **داخل** الظلّ (وفي الضوء أيضًا). نحقن
    قواعد RTL هناك بمحدِّد مزدوج على نمط `:host-context(.hc-black)` في المصدر: `:host-context([dir=rtl])`
    للظلّ (يفحص سمة مضيف الظلّ وأسلافه) و`.monaco-workbench[dir=rtl]` للضوء؛ مع `direction:rtl`
    صريحة لعكس ترتيب flex: النصّ يمين، الاختصار/المؤشّر الفرعيّ يسارًا، سهم الفرعيّة مقلوب، الصحّ يمينًا.

لماذا تعذّرت طبقة أدنى: (1) منطق JS؛ (2) CSS في الظلّ لا يصله المستند — لا سبيل من mihrab-rtl.css.

idempotent (وسمان مستقلّان)، كتابة ذرّيّة، Python 3.12-آمن، واعٍ بـCRLF.
الاستعمال: python patch_menu_rtl.py <مسار menu.ts>
"""
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# كلّ تعديل: (وسم، مرساة سطر-واحد-أو-أكثر بـ\n، استبدال بـ\n). تُطابَق نهاية سطر الملفّ وقت التشغيل.
EDITS = [
    # (1) تعاقب الفرعيّة يسارًا.
    (
        "mihrab-rtl-submenu",
        (
            # المسافة البادئة تبويبتان منذ 1.143 (كانت ثلاثًا حتّى 1.126: الكتلة فُكّ تداخُلها).
            "\t\tconst { top, left } = this.calculateSubmenuMenuLayout("
            "new Dimension(window.innerWidth, window.innerHeight), Dimension.lift(viewBox), "
            "entryBoxUpdated, this.expandDirection);"
        ),
        (
            "\t\t// mihrab-rtl-submenu: في RTL اجعل القائمة الفرعيّة تتعاقب يسارًا (متّسقًا مع اتّجاه القراءة).\n"
            "\t\tconst mihrabExpand = getWindow(this.element).getComputedStyle(this.element).direction === 'rtl'\n"
            "\t\t\t? { horizontal: HorizontalDirection.Left, vertical: this.expandDirection.vertical }\n"
            "\t\t\t: this.expandDirection;\n"
            "\t\tconst { top, left } = this.calculateSubmenuMenuLayout("
            "new Dimension(window.innerWidth, window.innerHeight), Dimension.lift(viewBox), "
            "entryBoxUpdated, mihrabExpand);"
        ),
    ),
    # (2) قواعد CSS للاتّجاه داخل مولّد getMenuWidgetCSS (تُحقَن قبل إغلاق قالب النصّ).
    (
        "mihrab-rtl-menu-css",
        ".monaco-menu .action-item {\n\tcursor: default;\n}`;",
        (
            ".monaco-menu .action-item {\n\tcursor: default;\n}\n\n"
            "/* mihrab-rtl-menu-css: اتّجاه عناصر القائمة في RTL. تُحقَن ضمن مولّد CSS القائمة كي\n"
            "   تصل حتى القوائم في Shadow DOM (السياقيّة). محدِّد مزدوج على نمط :host-context(.hc-black)\n"
            "   في المصدر: :host-context([dir=rtl]) للظلّ (يفحص سمة مضيف الظلّ وأسلافه) و\n"
            "   .monaco-workbench[dir=rtl] للضوء. نضبط direction:rtl صراحةً لضمان انعكاس ترتيب flex\n"
            "   (label/keybinding) لا مجرّد المحاذاة؛ ثمّ النصّ يمين، الاختصار/المؤشّر يسارًا،\n"
            "   السهم مقلوب، الصحّ يمينًا. */\n"
            ':host-context([dir="rtl"]) .monaco-menu .monaco-action-bar.vertical,\n'
            '.monaco-workbench[dir="rtl"] .monaco-menu .monaco-action-bar.vertical {\n'
            "\tdirection: rtl;\n"
            "\ttext-align: right;\n"
            "}\n"
            ':host-context([dir="rtl"]) .monaco-menu .monaco-action-bar.vertical .keybinding,\n'
            ':host-context([dir="rtl"]) .monaco-menu .monaco-action-bar.vertical .submenu-indicator,\n'
            '.monaco-workbench[dir="rtl"] .monaco-menu .monaco-action-bar.vertical .keybinding,\n'
            '.monaco-workbench[dir="rtl"] .monaco-menu .monaco-action-bar.vertical .submenu-indicator {\n'
            "\ttext-align: left;\n"
            "}\n"
            ':host-context([dir="rtl"]) .monaco-menu .monaco-action-bar.vertical .submenu-indicator.codicon::before,\n'
            '.monaco-workbench[dir="rtl"] .monaco-menu .monaco-action-bar.vertical .submenu-indicator.codicon::before {\n'
            "\tmargin-left: -20px;\n"
            "\tmargin-right: auto;\n"
            "\ttransform: scaleX(-1);\n"
            "}\n"
            ':host-context([dir="rtl"]) .monaco-menu .monaco-action-bar.vertical .menu-item-check,\n'
            '.monaco-workbench[dir="rtl"] .monaco-menu .monaco-action-bar.vertical .menu-item-check {\n'
            "\tleft: auto;\n"
            "\tright: 0;\n"
            "}`;"
        ),
    ),
]


def main() -> int:
    if len(sys.argv) != 2:
        print("الاستعمال: python patch_menu_rtl.py <مسار menu.ts>", file=sys.stderr)
        return 2
    path = sys.argv[1]
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            text = f.read()
    except OSError as e:
        print(f"⚠️ تعذّر فتح {path}: {e}", file=sys.stderr)
        return 1

    nl = "\r\n" if "\r\n" in text else "\n"
    changed = False
    for mark, anchor, replacement in EDITS:
        if mark in text:
            continue  # مُطبَّق مسبقًا
        a = anchor.replace("\n", nl)
        if a not in text:
            print(f"⚠️ لم تُعثَر مرساة «{mark}» في menu.ts — ربّما تغيّر المنبع.", file=sys.stderr)
            return 1
        text = text.replace(a, replacement.replace("\n", nl), 1)
        changed = True

    if not changed:
        print("مُرقَّع مسبقًا — تخطٍّ.")
        return 0

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

    print("✅ رُقِّع menu.ts (تعاقب الفرعيّة يسارًا + CSS اتّجاه القائمة في الضوء والظلّ).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
