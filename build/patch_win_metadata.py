#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بياناتُ نسخةِ ويندوز في الثنائيّات المشحونة (‏VERSIONINFO) — الطبقة 3.

## العطب، مقيسًا على المشحون

فحصنا `VersionInfo` لكلّ ‎exe/dll‎ في حزمة ‏1.126.05942 فوجدنا ثلاثةَ ملفّاتٍ تحمل
اسمَ منتَجِنا ونسبةَ ناشرٍ ليست لنا:

| الملفّ | ‏ProductName | ‏CompanyName | ‏LegalCopyright |
|---|---|---|---|
| `Mihrab.exe` | محراب | ‏**VSCodium** | ‏(C) 2026 **VSCodium** |
| `…/ripgrep-universal/bin/win32-x64/rg.exe` | محراب | ‏**VSCodium** | ‏(C) 2026 **VSCodium** |
| `bin/mihrab-tunnel.exe` | محراب | ‏**Microsoft Corporation** | ‏(C) 2026 **Microsoft** |

وهذه ليست زينةً في لوحة الخصائص: `CompanyName` هو ما يعرضه ويندوز ناشرًا، وما تقرؤه
أدواتُ الجرد وسياساتُ AppLocker. وملفٌّ باسم `mihrab-tunnel.exe` ينسب نفسَه إلى
مايكروسوفت **نسبةٌ خاطئةٌ لجهةٍ حقيقيّة**، لا مجرّدُ حقلٍ متروك.

## ولماذا الآن

لأنّ التوقيعَ يجعلها تناقضًا لا سهوًا: التوقيعُ سيقول «الناشر: محراب» والملفُّ يقول
«‏VSCodium»، وويندوز يعرض الاثنين في النافذة نفسِها. وشروطُ SignPath للمشاريع المفتوحة
تشترط صراحةً أن تحمل الثنائيّاتُ الموقَّعةُ بياناتِ منتَجٍ صحيحةً ومفروضة.

## ولماذا لم يمسكه حارس

حرّاسُ الهويّة عندنا (‏L0 وL2) يسألون `product.json` والنصَّ المُصيَّر — وهذان صحيحان
تمامًا: `nameLong=محراب`. أمّا `VERSIONINFO` فمَورِدُه مصادرُ البناء لا المنتَج، ولم
يكن في نطاق أيّ فحص. أضفنا الحارسَ مع الرقعة لا بعدها.

## المصادرُ الخمسة

أربعةٌ يضبطها VSCodium بـ`replace` في `prepare_vscode.sh` (فيرث محرابٌ اسمَهم)، والخامس
لم تبلغه يدُهم فبقي على نصّ مايكروسوفت:

  ‏`build/lib/electron.ts`      ⇐ حزمةُ Electron نفسُها (`Mihrab.exe`)
  ‏`build/gulpfile.vscode.ts`   ⇐ `rcedit` على الوحدات الأصليّة المرافقة (`rg.exe`)
  ‏`build/gulpfile.reh.ts`      ⇐ المثلُ لبناء الخادم البعيد
  ‏`build/win32/code.iss`       ⇐ **المثبِّت**: `AppPublisher` وثلاثةُ عناوين
  ‏`cli/build.rs`               ⇐ مواردُ Rust لـ`mihrab-tunnel.exe`

**والخامسُ في الترتيب أوّلُ ما يراه المستخدم**: `AppPublisher` هو عمودُ «الناشر» في
«إضافةُ برامجَ وإزالتها»، وهو في نافذة المثبِّت نفسِها. ولم يظهر في مسحِنا الأوّل لأنّ
الحزمةَ المضغوطةَ لا تحمل مثبِّتًا — ينكشف أوّلَ ما يُبنى واحد.

ويُرقَّع بناءُ الخادم ولو لم يُشحَن اليومَ في سطح المكتب: العطبُ واحدٌ والكلفةُ سطران،
وتركُه يعني أن يعود حين يُنشَر.

## والسنةُ خارجَ المرساة عمدًا

المنبعُ يكتب `Copyright (C) <سنة> VSCodium. All rights reserved`، والسنةُ تتغيّر معه كلّ
عام. فلو رست الرقعةُ على السطر كاملًا لانكسر البناءُ كلَّ أوّلِ يناير بلا سببٍ يخصّنا.
المرساةُ هنا ما **بعد** السنة (` VSCodium. All rights reserved',`)، فتبقى السنةُ متدفّقةً
من المنبع ولا نستبدل إلّا الجهة.

## ولا «All rights reserved»

محرابٌ تحت MIT، و«كلُّ الحقوق محفوظة» نقيضُ ما ترخّصه. النصُّ الجديد يقول الرخصةَ
باسمها — والملفُّ التنفيذيُّ أوّلُ ما يقرؤه من يسأل «لمن هذا البرنامج؟».

يُشغَّل **بعد** `prepare_vscode.sh` (مثلَ بقيّة مرقِّعاتنا) فيرى نصَّ VSCodium لا نصَّ
مايكروسوفت في الثلاثة الأولى. idempotent عبر الوسم `mihrab-win-metadata`. كتابة ذرّيّة.

الاستعمال: python build/patch_win_metadata.py <جذر مصدر vscode>
"""
import io
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

MARK = "mihrab-win-metadata"

# هويّةُ الناشر: **محرابٌ لا لغةُ ص.**
#
# كُتب أوّلًا `Sad Language` قياسًا على `win32AppUserModelId: SadLang.Mihrab`. وذاك خطأٌ
# في القراءة: المعرِّفُ نطاقٌ (‏`المنظّمة.المنتَج`) لا يُعرَض لأحد، و`CompanyName` سطرٌ
# **يقرؤه المطوّر** في خصائص الملفّ.
#
# والفرقُ ليس ذوقًا. يقول README إنّ سلسلةَ ص تُشحَن «تطبيقًا مرجعيًّا للمنصّة لا لغةً
# مفضّلة»، ومحرابٌ «منصّةُ تطويرٍ عربيّةٌ تستضيف اللغات». فناشرٌ اسمُه لغةٌ بعينها ينقض
# ذلك في أوّل نافذةٍ يفتحها من يتفحّص الملفّ — ويصرف مطوّرًا لا يكتب ص عن أداةٍ بُنيت
# له هو أيضًا. حقلٌ واحدٌ يزن ما تزنه صفحةُ تعريف.
#
# ولاتينيٌّ لا عربيّ: قواعدُ AppLocker وأدواتُ الجرد وقواعدُ سمعةِ الناشر تطابق هذا
# الحقلَ نصًّا. والعربيّةُ حاضرةٌ حيث تُقرأ فعلًا — `ProductName` = محراب.
#
# **ولا يُمَسّ معرِّفان**: `win32AppUserModelId` و`darwinBundleIdentifier`. هما نطاقان
# لا سلاسلُ عرض، وتغييرُ الأوّل يفكّ ارتباطَ الاختصارات المثبَّتة في شريط المهامّ،
# والثاني يقطع استمراريّةَ هويّة التطبيق على macOS. وبادئتُهما تسمّي المنظّمةَ الناشرة
# وهي لغةُ ص فعلًا — فالصوابُ إبقاؤهما.
COMPANY = "Mihrab"
COPYRIGHT_TAIL = " Mihrab — MIT License"

# **ولكلّ مرساةٍ صورتان، لأنّ للملفّ حالتين.** يُشغَّل هذا المرقِّعُ في البناء **بعد**
# ‏`prepare_vscode.sh` فيجد نصَّ VSCodium؛ ويُشغَّل في `dev_sync.py` وفي L1 على شجرةٍ
# **نظيفةٍ من مايكروسوفت** فيجد نصَّها هي. وصورةٌ واحدةٌ كانت ستجعل الفحصَ الذي يُفترَض
# أن يحرس الرقعةَ هو أوّلَ ما يسقط عليها. تُجرَّب الصورتان بالترتيب، وواحدةٌ منهما
# يجب أن تقعَ مرّةً واحدةً بالضبط — لا صفرًا ولا اثنتين.
_CO_TS = ("companyName: 'VSCodium',", "companyName: 'Microsoft Corporation',")
_CO_RC = ("'CompanyName': 'VSCodium',", "'CompanyName': 'Microsoft Corporation',")
_CP_TS = (" VSCodium. All rights reserved',", " Microsoft. All rights reserved',")

FILES = [
    # (١) حزمةُ Electron: منها `CompanyName`/`LegalCopyright` في `Mihrab.exe`.
    (
        "build/lib/electron.ts",
        MARK,
        [
            (_CO_TS, "companyName: '" + COMPANY + "', // " + MARK, 1),
            (_CP_TS, COPYRIGHT_TAIL + "',", 1),
        ],
    ),
    # (٢) `rcedit` على الوحدات الأصليّة المرافقة — منها بصمةُ `rg.exe` المشحون.
    (
        "build/gulpfile.vscode.ts",
        MARK,
        [
            (_CO_RC, "'CompanyName': '" + COMPANY + "', // " + MARK, 1),
            (_CP_TS, COPYRIGHT_TAIL + "',", 1),
        ],
    ),
    # (٣) المثلُ لبناء الخادم البعيد — لا يُشحَن في سطح المكتب اليومَ ويُرقَّع كي لا
    #     يعود العطبُ حين يُنشَر.
    (
        "build/gulpfile.reh.ts",
        MARK,
        [
            (_CO_RC, "'CompanyName': '" + COMPANY + "', // " + MARK, 1),
            (_CP_TS, COPYRIGHT_TAIL + "',", 1),
        ],
    ),
    # (٥) **سكربتُ Inno Setup — وهو الأظهرُ من الخمسة.** `AppPublisher` هو ما تعرضه
    #     «إضافةُ برامجَ وإزالتها» في عمود الناشر، وما تقرؤه نافذةُ المثبِّت نفسُها.
    #     وثلاثةُ عناوينَ تحته تقود إلى موقع VSCodium: الناشرُ والدعمُ والتحديثات.
    #     ولم يظهر هذا في مسحِنا الأوّل لأنّه **لا يُشحَن في الحزمة المضغوطة** — يظهر
    #     أوّلَ ما يُبنى مثبِّت، أي في الخطوة التالية بالضبط.
    (
        "build/win32/code.iss",
        MARK,
        [
            (("AppPublisher=VSCodium", "AppPublisher=Microsoft Corporation"),
             "AppPublisher=" + COMPANY + "\n; " + MARK, 1),
            (("AppPublisherURL=https://vscodium.com/",
              "AppPublisherURL=https://code.visualstudio.com/"),
             "AppPublisherURL=https://sad-lang.org/mihrab/", 1),
            (("AppSupportURL=https://vscodium.com/",
              "AppSupportURL=https://code.visualstudio.com/"),
             "AppSupportURL=https://github.com/mihrab-org/mihrab/issues", 1),
            (("AppUpdatesURL=https://vscodium.com/",
              "AppUpdatesURL=https://code.visualstudio.com/"),
             "AppUpdatesURL=https://github.com/mihrab-org/mihrab/releases", 1),
        ],
    ),
    # (٤) مواردُ Rust لـ`mihrab-tunnel.exe`. **الوحيدُ الذي يقول «مايكروسوفت» في المشحون**:
    #     ‏`prepare_vscode.sh` يستبدل في `build/lib/electron.ts` وحدَه، فلم تبلغه يدُهم —
    #     فصورتُه واحدةٌ لا صورتان.
    (
        "cli/build.rs",
        MARK,
        [
            (('res.set("CompanyName", "Microsoft Corporation");',),
             'res.set("CompanyName", "' + COMPANY + '"); // ' + MARK, 1),
            ((' Microsoft. All rights reserved");',),
             COPYRIGHT_TAIL + '");', 1),
        ],
    ),
]


def _read(path):
    with io.open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _write_atomic(path, text):
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

    tmp = path + ".mihrab-tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, path)


def _apply(root, relpath, mark, edits):
    """يطبّق تعديلات ملفٍّ واحد. يعيد True نجاحًا (أو تخطّيًا)، False إخفاقًا."""
    path = os.path.join(root, relpath.replace("/", os.sep))
    try:
        text = _read(path)
    except OSError as e:
        print("⚠️ تعذّر فتح %s: %s" % (relpath, e), file=sys.stderr)
        return False

    if mark in text:
        print("  ⏭️  %s — مُرقَّع مسبقًا." % relpath)
        return True

    for forms, new, count in edits:
        # المرساةُ مرّةً واحدةً بالضبط: مرّتان تعنيان أنّنا نستبدل موضعًا لم نقرأه،
        # والإخفاقُ حينها أسلمُ من النجاح. وتُجرَّب الصورُ بالترتيب — أوّلُ صورةٍ تقع
        # مرّةً هي المقصودة، وصورةٌ تقع مرّتين تُوقِف ولا تُتخطّى.
        hit = None
        for form in forms:
            n = text.count(form)
            if n == count:
                hit = form
                break
            if n > count:
                print("⚠️ %s: المرساة وُجدت %d مرّة والمتوقَّع %d — تغيّر المنبع؟\n"
                      "   المرساة: %s" % (relpath, n, count, form[:100]), file=sys.stderr)
                return False
        if hit is None:
            print("⚠️ %s: لا مرساةَ من %d — تغيّر المنبع؟\n   المُجرَّب: %s"
                  % (relpath, len(forms), " · ".join(f[:60] for f in forms)),
                  file=sys.stderr)
            return False
        text = text.replace(hit, new, count)

    try:
        _write_atomic(path, text)
    except OSError as e:
        print("⚠️ تعذّر كتابة %s: %s" % (relpath, e), file=sys.stderr)
        return False
    print("  ✅ %s" % relpath)
    return True


def main():
    if len(sys.argv) != 2:
        print("الاستعمال: python patch_win_metadata.py <جذر مصدر vscode>", file=sys.stderr)
        return 2
    root = sys.argv[1]

    ok = True
    for relpath, mark, edits in FILES:
        if not _apply(root, relpath, mark, edits):
            ok = False

    if not ok:
        print("❌ رقعةُ بيانات نسخةِ ويندوز لم تكتمل.", file=sys.stderr)
        return 1
    print("✅ رُقِّعت بياناتُ النسخة (‏CompanyName/LegalCopyright ⇐ %s)." % COMPANY)
    return 0


if __name__ == "__main__":
    sys.exit(main())
