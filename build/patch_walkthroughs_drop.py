#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""رُقعة نواة محراب: إسقاط جولات المنبع التعريفيّة — الطبقة 3.

صفحة الترحيب تعرض جولات (walkthroughs) المنبع المدمجة، وثلاثٌ منها تُعرّف بالمحرّر المنبعيّ
لا بمحراب: `Setup` («Get started with VSCodium») و`SetupWeb` و`Beginner`. وجودها يزاحم جولات
محراب على صدارة الصفحة، ويُبقي اسم المنبع وصوته الإنجليزيّ في أوّل سطح
يراه المستخدم. هذه الرُقعة تُرشّحها قبل التسجيل فتبقى جولة محراب هي المتصدّرة.

ما لا يُسقَط عمدًا:
  - `SetupAccessibility`: محكومة بـCONTEXT_ACCESSIBILITY_MODE_ENABLED، ولا بديل لها في محراب.
    إسقاطها يحذف محتوى وصول لا يُعوَّض — إضرارٌ بلا مقابل.
  - `notebooks`: محكومة بـ`userHasOpenedNotebook` (لا تظهر في الترحيب الأوّل)، ومحتواها
    وظيفيّ لا تعريفيّ.

`Setup.next = 'Beginner'` و`SetupAccessibility.next = 'Setup'` يصيران مراجع معلّقة بعد
الترشيح؛ هذا آمن مقيسًا: gettingStarted.ts يبحث عن الفئة بـfind ⇒ undefined ⇒ لا يُصيَّر زرّ
«القسم التالي» أصلًا (لا استثناء ولا زرّ ميّت).

الملفّ المنبعيّ: src/vs/workbench/contrib/welcomeGettingStarted/browser/gettingStartedService.ts
(دالّة registerWalkthroughs، حيث `walkthroughs.forEach(...)`).
لماذا تعذّرت طبقة أدنى: الجولات المدمجة تُسجَّل برمجيًّا من ثابت مستورَد؛ لا إعداد ولا نقطة
امتداد تحجب جولةً مدمجة (نقطة الامتداد تُضيف فقط). أقرب بديل من طبقة 2 هو حذف عناصر من
الصفحة بـCSS — علاجٌ بصريّ يُبقي الجولة مسجَّلة وقابلة للفتح من لوحة الأوامر.

الترشيح على `id` لا على `isFeatured`: المعرّفات ثابتة عبر إصدارات المنبع، بينما `isFeatured`
قد يتبدّل — ولو رشّحنا على العَلَم لأسقطنا `SetupAccessibility` معه (وهي isFeatured أيضًا).

idempotent عبر الوسم mihrab-walkthroughs. كتابة ذرّيّة. Python 3.12-آمن.
الاستعمال: python patch_walkthroughs_drop.py <مسار gettingStartedService.ts>
"""
import json
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

MARK = "mihrab-walkthroughs"

# معرّفات جولات المنبع المُسقَطة. ثابت مسمّى كي تُحرَّر القائمة من موضع واحد؛ يقرؤه
# مِجَسّ L0 أيضًا (فحص أنّ SetupAccessibility ليست فيها).
DROPPED_IDS = ["Setup", "SetupWeb", "Beginner"]

# بلا مسافات عمدًا: مِجَسّ L2 يطابق هذه السلسلة حرفيًّا على الحزمة المُصغَّرة، والمُصغِّر يحذف
# المسافات — فتوليدها هنا بلا مسافات يجعل المصدرَ والحزمةَ متطابقين فلا يعتمد المِجَسّ على
# سلوك المُصغِّر. (اسم المتغيّر لا يصلح مِجَسًّا: esbuild يُعيد تسمية المحلّيّات.)
_IDS_JS = json.dumps(DROPPED_IDS, ensure_ascii=False, separators=(",", ":"))

ANCHOR = (
    "\t\twalkthroughs.forEach(async (category, index) => {\n"
    "\n"
    "\t\t\tthis._registerWalkthrough({\n"
    "\t\t\t\t...category,\n"
    "\t\t\t\ticon: { type: 'icon', icon: category.icon },\n"
    "\t\t\t\torder: walkthroughs.length - index,"
)

REPLACEMENT = (
    "\t\t// mihrab-walkthroughs: ترشيح جولات المنبع التعريفيّة قبل التسجيل (انظر patch_walkthroughs_drop.py).\n"
    "\t\tconst mihrabDroppedWalkthroughs = new Set(" + _IDS_JS + ");\n"
    "\t\tconst mihrabWalkthroughs = walkthroughs.filter(category => !mihrabDroppedWalkthroughs.has(category.id));\n"
    "\n"
    "\t\tmihrabWalkthroughs.forEach(async (category, index) => {\n"
    "\n"
    "\t\t\tthis._registerWalkthrough({\n"
    "\t\t\t\t...category,\n"
    "\t\t\t\ticon: { type: 'icon', icon: category.icon },\n"
    "\t\t\t\torder: mihrabWalkthroughs.length - index,"
)


def main() -> int:
    if len(sys.argv) != 2:
        print("الاستعمال: python patch_walkthroughs_drop.py <مسار gettingStartedService.ts>",
              file=sys.stderr)
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

    nl = "\r\n" if "\r\n" in text else "\n"
    anchor = ANCHOR.replace("\n", nl)
    replacement = REPLACEMENT.replace("\n", nl)
    if anchor not in text:
        print("⚠️ لم تُعثَر مرساة تسجيل الجولات في gettingStartedService.ts — ربّما تغيّر المنبع.",
              file=sys.stderr)
        return 1

    text = text.replace(anchor, replacement, 1)

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

    print("✅ رُقِّع gettingStartedService.ts (إسقاط جولات المنبع: " + "، ".join(DROPPED_IDS) + ").")
    return 0


if __name__ == "__main__":
    sys.exit(main())
