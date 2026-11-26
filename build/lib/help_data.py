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
import json
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


def mismatch(ext_dir):
    """⇒ سببُ الإخفاق نصًّا، أو "" إن حمل `<ext_dir>/data/` بياناتِ المساعدة كما في `site/data/`.

    **بالمحتوى لا بالبايت:** بناءُ VS Code يمرّر JSON الامتدادات بـ`minifyExtensionResources`
    (‏`jsonc.parse` ثمّ `JSON.stringify`): سطرٌ واحدٌ بلا مسافات، والمعنى واحد. واللوحةُ تقرأ المعنى
    (‏`JSON.parse`). وترتيبُ مفاتيح الكائن لا يُقارَن (‏`dict`)، وترتيبُ المصفوفات يُقارَن — منه
    ترتيبُ العرض في اللوحة. يستعمله فحصُ الحزمة (‏`tests/bundle/check_injected.py`)."""
    for f in FILES:
        src = os.path.join(SOURCE, f)
        got = os.path.join(ext_dir, DATA_DIR, f)
        if not os.path.isfile(src):
            return "لا site/data/%s في المصدر" % f
        if not os.path.isfile(got):
            return "%s/%s غائبٌ عن الحزمة" % (DATA_DIR, f)
        # كلُّ طرفٍ يُقرأ وحدَه: تالفٌ في المصدر لا يُنسَب إلى الحزمة.
        try:
            with open(src, encoding="utf-8") as fh:
                want = json.load(fh)
        except ValueError as e:
            return "site/data/%s ليس JSON صالحًا في المصدر: %s" % (f, e)
        try:
            with open(got, encoding="utf-8") as fh:
                have = json.load(fh)
        except ValueError as e:
            return "%s/%s ليس JSON صالحًا في الحزمة: %s" % (DATA_DIR, f, e)
        if want != have:
            return "%s/%s في الحزمة يخالف site/data/%s محتوًى" % (DATA_DIR, f, f)
    return ""


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "extensions", "mihrab-welcome")
    for p in sync(target):
        print("▶ بياناتُ المساعدة: %s" % p)
