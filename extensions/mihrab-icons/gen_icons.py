#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مولّد عائلة أيقونات محراب — مصدر الحقيقة الوحيد لملفّات ‎icons/*.svg‎ المشتقّة والخريطة.

**المشكلة التي يحلّها [AR-06]:** كانت السمة تُخرِّط نوعًا واحدًا فقط، وهي **الافتراضيّة**.
فكلّ ما عداه — ‎json، md، py، png، توml… — يقع على أيقونة الصفحة العامّة نفسها. أي أنّ مستكشف
محراب كان **أقلّ إفادةً من المحرّر القياسيّ** (‏seti يغطّي عشرات الأنواع): الشجرة تصير صفًّا من
صفحاتٍ متطابقة، ويضيع أسرع مؤشّر بصريّ يملكه المبرمج للتمييز بين ملفّات المشروع.

**المبدأ:** لا نلاحق تغطية seti. نغطّي **ما يقع فعلًا في مشروعٍ عاديّ**: مصدر، بيانات/إعداد،
توثيق، صورة، سجلّ/قفل. خمس عائلات، لا أكثر — كلٌّ منها **لونٌ من لوحة السمة نفسها** (لا ألوان
مخترَعة)، فتقرأ الشجرة كامتدادٍ للسمة لا كطقمٍ غريب عنها.

**البنية:** كلّ أيقونة = إطار الصفحة العامّ نفسه (‏file.svg‎ حرفيًّا، محافظةً على وحدة الشكل)
‏+ **علامة** صغيرة داخله تدلّ على العائلة. الإطار يبقى محايد اللون، والعلامة وحدها ملوّنة:
فيبقى التمييز سريعًا في حجمٍ 16px بلا ضجيج لونيّ.


الاستعمال:  python extensions/mihrab-icons/gen_icons.py
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
ICONS = os.path.join(HERE, "icons")
THEME = os.path.join(HERE, "mihrab-icon-theme.json")
BANNER = "مولَّد بـgen_icons.py — لا تحرّره يدويًّا"

# إطار الصفحة: منقول حرفيًّا من icons/file.svg كي لا ينحرف الشكل بين المشتقّ والأصل.
FRAME = ('  <path d="M6 3 h13 l8 8 v24 a2 2 0 0 1 -2 2 H6 a2 2 0 0 1 -2 -2 V5 a2 2 0 0 1 2 -2 z"\n'
         '        fill="none" stroke="{s}" stroke-width="1.8" stroke-linejoin="round"/>\n'
         '  <path d="M19 3 v8 h8" fill="none" stroke="{s}" stroke-width="1.8" stroke-linejoin="round"/>')
FRAME_DARK, FRAME_LIGHT = "#8CA0A6", "#5E7278"   # مطابقان لـfile.svg / file-light.svg

# ألوان العلامات — **مأخوذة من لوحة السمة** (extensions/mihrab-themes/gen_themes.py):
# الداكنة تستعمل قيم DARK، والفاتحة قيم LIGHT، فيتّسق المستكشف مع تلوين الشيفرة نفسه.
MARK = {
    #  عائلة        داكن       فاتح        مصدر القيمة في لوحة السمة
    "code":   ("#6FB2D8", "#255F87"),   # cls — صنف/نوع
    "data":   ("#E3BE68", "#8A5A0E"),   # kw  — كلمة مفتاحيّة
    "doc":    ("#D4DEDF", "#43565A"),   # var — متغيّر
    "image":  ("#7FD1C1", "#0E776A"),   # fn  — دالّة
    "meta":   ("#738991", "#626B75"),   # cm  — تعليق
}

# العلامة داخل الإطار (نطاق الرسم المتاح ‎x∈[8,23]، y∈[16,32]‎ — تحت لسان الطيّ).
GLYPH = {
    # مصدر: قوسان زاويّان ‹ › — اصطلاح عالميّ للشيفرة، يقرأ في 16px.
    "code":  '  <path d="M13 20 L9 24 L13 28 M19 20 L23 24 L19 28" fill="none" stroke="{c}"'
             ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    # بيانات/إعداد: ثلاث حِزَم أفقيّة متدرّجة — جدولٌ/سِجلّ.
    "data":  '  <path d="M9 20 h14 M9 24 h14 M9 28 h9" fill="none" stroke="{c}"'
             ' stroke-width="2" stroke-linecap="round"/>',
    # توثيق: أسطر نصّ (الأخير أقصر) — فقرة.
    "doc":   '  <path d="M9 21 h14 M9 25 h14 M9 29 h7" fill="none" stroke="{c}"'
             ' stroke-width="1.6" stroke-linecap="round"/>',
    # صورة: أفق وشمس — مشهد.
    "image": '  <circle cx="12" cy="21" r="2" fill="{c}"/>\n'
             '  <path d="M8 29 l5 -6 l4 4 l3 -3 l4 5 z" fill="{c}"/>',
    # سجلّ/قفل: قُفل مبسّط — ملفّات لا تُحرَّر يدويًّا.
    "meta":  '  <path d="M12 23 v-2 a4 4 0 0 1 8 0 v2" fill="none" stroke="{c}"'
             ' stroke-width="1.8" stroke-linecap="round"/>\n'
             '  <rect x="10" y="23" width="12" height="8" rx="1.6" fill="none" stroke="{c}"'
             ' stroke-width="1.8"/>',
}

# الامتدادات لكلّ عائلة — **ما يقع في مشروعٍ عاديّ فعلًا** لا كلّ ما في الوجود.
EXTENSIONS = {
    "code":  ["py", "js", "mjs", "cjs", "ts", "mts", "cts", "sh", "bash", "ps1", "c", "h",
              "cpp", "hpp", "rs", "go", "java", "rb", "lua"],
    "data":  ["json", "jsonc", "yaml", "yml", "toml", "ini", "cfg", "conf", "xml", "csv",
              "env", "properties"],
    "doc":   ["md", "markdown", "txt", "rst", "adoc", "pdf", "html", "htm", "css"],
    "image": ["svg", "png", "jpg", "jpeg", "gif", "webp", "ico", "bmp", "avif"],
    "meta":  ["log", "lock", "gitignore", "gitattributes", "editorconfig", "map"],
}
# أسماء ملفّات بعينها تغلب الامتداد (‏LICENSE بلا امتداد، والقفل ملفٌّ مولَّد لا بيانات).
FILE_NAMES = {
    "doc":  ["README.md", "LICENSE", "LICENSE.md", "CHANGELOG.md", "CONTRIBUTING.md"],
    "meta": ["package-lock.json", ".gitignore", ".gitattributes", ".editorconfig"],
}


def svg(family, dark):
    frame = FRAME_DARK if dark else FRAME_LIGHT
    color = MARK[family][0 if dark else 1]
    surface = "الداكنة" if dark else "الفاتحة"
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<!-- {BANNER} | عائلة «{family}» على الأرضيّة {surface} -->\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 40" width="32" height="40">\n'
            f'{FRAME.format(s=frame)}\n'
            f'{GLYPH[family].format(c=color)}\n'
            f'</svg>\n')


def main():
    written = []
    for family in MARK:
        for dark in (True, False):
            name = f"{family}.svg" if dark else f"{family}-light.svg"
            path = os.path.join(ICONS, name)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(svg(family, dark))
            written.append(name)

    theme = json.load(open(THEME, encoding="utf-8"))
    defs = theme["iconDefinitions"]
    for family in MARK:
        defs[f"mihrab-{family}"] = {"iconPath": f"./icons/{family}.svg"}
        defs[f"mihrab-{family}-light"] = {"iconPath": f"./icons/{family}-light.svg"}

    # الخريطة تُبنى من الصفر في كلّ توليد (لا دمج) — فحذف امتدادٍ من الجدول يحذفه من السمة،
    # ولا تبقى مراجع يتيمة لأيقونات لم تعد تُولَّد.
    def build(light):
        sfx = "-light" if light else ""
        ext = {}
        for family, exts in EXTENSIONS.items():
            for e in exts:
                ext[e] = f"mihrab-{family}{sfx}"
        names = {}
        for family, files in FILE_NAMES.items():
            for n in files:
                names[n] = f"mihrab-{family}{sfx}"
        return ext, names

    ext, names = build(False)
    theme["fileExtensions"], theme["fileNames"] = ext, names
    theme.pop("languageIds", None)
    lext, lnames = build(True)
    theme["light"]["fileExtensions"], theme["light"]["fileNames"] = lext, lnames
    theme["light"].pop("languageIds", None)

    with open(THEME, "w", encoding="utf-8", newline="\n") as f:
        json.dump(theme, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"✅ وُلِّدت {len(written)} أيقونة، وخُرِّط {len(ext)} امتدادًا و{len(names)} اسم ملفّ.")


if __name__ == "__main__":
    main()
