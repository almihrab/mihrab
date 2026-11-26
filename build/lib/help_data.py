#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بياناتُ المساعدة داخل المحرّر تُولَّد من الموقع، لا تُحفَظ نسخةً ثانية [ON-03]

لوحةُ المساعدة في امتداد الترحيب تعرض المسردَ والاختصارات، ومصدرُهما الوحيد `site/data/`.
كانت نسخةٌ ثانيةٌ محفوظةً في `extensions/mihrab-welcome/data/` ويحرس فحصٌ تطابقَها بالبايت،
فتعديلُ الموقع وحدَه كان يُحمِّر CI بعد وقوعه. فصارت تُكتب هنا في كلّ خطوةٍ تحزم الامتداد:
`build.sh` (المكتبُ والمتصفّحُ معًا: كلاهما من مجلّد `.mihrab-extensions`)، و`dev_sync.py`.
والنسخةُ في المستودع مُتجاهَلة (‏`extensions/mihrab-welcome/.gitignore`).

    python build/lib/help_data.py <مجلّد الامتداد>     # افتراضيًّا extensions/mihrab-welcome
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCE = os.path.join(ROOT, "site", "data")
# ما تقرؤه اللوحة (‏`GLOSSARY_FILE` و`KEYBINDINGS_FILE` في `help-panel.js`)، ومجلّدُه فيها (‏`DATA_DIR`).
FILES = ("glossary.json", "keybindings.json")
DATA_DIR = "data"


def sync(ext_dir):
    """يكتب ملفّاتِ المساعدة في `<ext_dir>/data/` من `site/data/` بالبايت، ويُرجع مساراتها."""
    dst = os.path.join(ext_dir, DATA_DIR)
    os.makedirs(dst, exist_ok=True)
    out = []
    for f in FILES:
        src = os.path.join(SOURCE, f)
        if not os.path.isfile(src):
            raise SystemExit("❌ بياناتُ المساعدة مفقودة في المصدر: site/data/%s [ON-03]" % f)
        shutil.copyfile(src, os.path.join(dst, f))
        out.append(os.path.join(dst, f))
    return out


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "extensions", "mihrab-welcome")
    for p in sync(target):
        print("▶ بياناتُ المساعدة: %s" % p)
