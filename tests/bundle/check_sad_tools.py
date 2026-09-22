#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوّابةُ أدوات ص: ما جلبَه `fetch_sad_tools.sh` وصل الحزمةَ المشحونة فعلًا.

**العطبُ الذي تمنعه:** `build.sh` يسقط سقوطًا رشيقًا عند غياب الأدوات — وهو صحيحٌ
لبناءٍ محلّيّ، وكارثيٌّ عند النشر: تُرفَع حزمةٌ **بلا لغة** والموقعُ يَعِد بأنّها «جاهزةٌ
في الصندوق». فالسقوطُ الرشيقُ يبقى في البناء، والقطعُ يقع هنا: إن جُلبت أداةٌ ولم تصل
الحزمة، فهذا انحدارُ تحزيمٍ يجب أن يُحمِّر لا أن يُشحَن.

**ولا يُخترَع عطبٌ حين لا مصدر:** بلا `manifest.json` (لم يُشغَّل الجالب، أو لا أصلَ
لهذه المنصّة في الإصدار الرسميّ) يُبلَّغ تخطٍّ **مُعلَنًا** — بخلاف الصمت الذي يقرأ نجاحًا.

الاستعمال: python tests/bundle/check_sad_tools.py [مسار الحزمة]
           MIHRAB_DIST_ROOT=... python tests/bundle/check_sad_tools.py
خرج 0 = وصلت (أو تخطٍّ مُعلَن) · 1 = جُلبت ولم تصل.
"""
import json
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MANIFEST = os.path.join(ROOT, ".upstream", ".sad-tools", "manifest.json")
# أين يشحن build.sh كلَّ أداة (الخادمُ اللغويّ يسكن في sad-lang لا في الترحيب).
HOMES = {
    "sad-run": "mihrab-welcome", "sad-build": "mihrab-welcome",
    "sad-check": "mihrab-welcome", "sad-lsp": "sad-lang",
}


def _app_dir(dist):
    """‏`resources/app` على ويندوز/لينكس، و`Contents/Resources/app` داخل حزمة macOS."""
    direct = os.path.join(dist, "resources", "app")
    if os.path.isdir(direct):
        return direct
    for name in sorted(os.listdir(dist)) if os.path.isdir(dist) else []:
        if name.endswith(".app"):
            mac = os.path.join(dist, name, "Contents", "Resources", "app")
            if os.path.isdir(mac):
                return mac
    return direct


def verify(dist):
    """يعيد (رمزَ الخروج، أسطرَ التقرير)."""
    out = []
    if not os.path.isfile(MANIFEST):
        # ⚠️ التخطّي المُعلَن كان يمرّ **حتّى مع** `MIHRAB_REQUIRE_OFFICIAL_TOOLS=yes`:
        # البوّابةُ لم تكن تعمل إلّا حين يوجد مانيفستٌ وتوجد أدواتٌ دخيلة. فأوّلُ دفعةٍ
        # خضراء بعد إصلاح ‎036‎ كانت ستشحن حزمةً بلا لغة ص بينما الصفحةُ الأولى تَعِد
        # «جاهزةٌ في الصندوق» (قياسُ مدير المنتج). الأحمرُ الصادق خيرٌ من أخضرَ يكذب.
        if os.environ.get("MIHRAB_REQUIRE_OFFICIAL_TOOLS") == "yes":
            return 1, ["❌ لا manifest لأدوات ص والنشرُ يشترطها (MIHRAB_REQUIRE_OFFICIAL_TOOLS=yes). "
                       "الجلبُ فشل غالبًا لغياب رمزٍ يقرأ المستودعَ الخاصّ: أضِف السرَّ "
                       "`SAD_TOOLS_TOKEN` في إعدادات المستودع، أو انشر الأدواتِ علنًا."]
        return 0, ["⏭️  لا manifest لأدوات ص (لم يُجلَب إصدارٌ رسميّ لهذه المنصّة) — تخطٍّ مُعلَن"]
    man = json.load(open(MANIFEST, encoding="utf-8"))
    app = _app_dir(dist)
    if not os.path.isdir(app):
        return 0, [f"⏭️  لا حزمةَ في {dist} — تخطٍّ مُعلَن"]
    missing, ok = [], []
    for fname in sorted(man.get("tools", {})):
        stem = fname.split(".")[0]
        home = HOMES.get(stem)
        if not home:
            continue  # حمولةٌ مجاورة (SDL2.dll…) تُفحَص مع بيتها أدناه
        p = os.path.join(app, "extensions", home, "bin", fname)
        if not os.path.isfile(p):
            missing.append(f"{home}/bin/{fname} (مفقود)")
            continue
        # **بصمةً لا اسمًا**: ملفٌّ بالاسم الصحيح من مصدرٍ آخر (محرّكاتُ جهاز المطوّر
        # مثلًا) يجعل الاسمَ يمرّ بينما المنشورُ ليس الإصدارَ الرسميّ الذي وعدنا به.
        import hashlib
        digest = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
        if digest != man["tools"][fname]:
            missing.append(f"{home}/bin/{fname} (بصمةٌ مغايرة: {digest} ≠ {man['tools'][fname]})")
        else:
            ok.append(f"{home}/bin/{fname}")
    for name in ok:
        out.append(f"  ✅ {name}")
    for name in missing:
        out.append(f"  ❌ {name}")
    if missing:
        out.append("❌ أدواتُ ص جُلبت ولم تصل الحزمةَ كما جُلبت — انحدارُ تحزيم، لا تُنشَر.")
        return 1, out
    out.append(f"✅ أدواتُ ص {man.get('tag', '؟')} في الحزمة ({len(ok)} أداة)")
    # **أدواتٌ في الحزمة ليست من المانيفست** = مصدرٌ غير رسميّ (‏`build.sh` يسقط إلى
    # `../sad-engines-dev/` حين لا يُصدَّر المتغيّر). على جهاز مطوّرٍ هذا مشروع؛ في نشرٍ
    # هو خلطُ مصادرَ صامت: نصفُ الحزمة إصدارٌ رسميٌّ ونصفُها ثنائيٌّ لا يعرفه أحد.
    # قِسناه أوّلَ بناءٍ بالجالب: `sad-lsp.exe` جاء من محرّكات الجهاز والبوّابةُ خضراء.
    strays = []
    for tool, home in sorted(HOMES.items()):
        for fname in (f"{tool}.exe", tool):
            p = os.path.join(app, "extensions", home, "bin", fname)
            if os.path.isfile(p) and fname not in man.get("tools", {}):
                strays.append(f"{home}/bin/{fname}")
    if strays:
        out.append("   ⚠️ من مصدرٍ **غير رسميّ** (لا في مانيفست الإصدار): " + " ".join(strays))
        if os.environ.get("MIHRAB_REQUIRE_OFFICIAL_TOOLS") == "yes":
            out.append("❌ النشرُ يشترط أدواتٍ رسميّةً وحدَها (MIHRAB_REQUIRE_OFFICIAL_TOOLS=yes).")
            return 1, out
    # النقصُ يُعلَن ولا يُفشِل: الإصدارُ الرسميّ لا ينشر الأربعةَ بعد.
    absent = [t for t in HOMES if f"{t}.exe" not in man.get("tools", {})
              and t not in man.get("tools", {})]
    if absent:
        out.append(f"   ⚠️ غيرُ منشورٍ في الإصدار الرسميّ: {' '.join(sorted(absent))}")
    return 0, out


def main():
    dist = (sys.argv[1] if len(sys.argv) > 1 else None) or \
        os.environ.get("MIHRAB_DIST_ROOT") or \
        os.path.join(ROOT, ".upstream", "VSCode-win32-x64")
    code, lines = verify(dist)
    print("═══ بوّابة أدوات ص ═══")
    for ln in lines:
        print(ln)
    return code


if __name__ == "__main__":
    sys.exit(main())
