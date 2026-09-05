#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""لوحُ الترحيب لا يَعِد بما لا خلفيّةَ له في محرابِ المتصفّح.

**العطب.** بندُ «‏Open Repository…» في `gettingStartedContent.ts` شرطُه
`workspacePlatform == 'webworker'` — وهو **متحقّقٌ عندنا بالضبط**، لأنّ البناءَ
الثابت بلا `remoteAuthority` فمضيفُ الامتدادات عاملُ ويب. وأمرُه
`command:remoteHub.openRepository` من إضافةِ **مايكروسوفت المِلكيّة**، ولا وجودَ لها
في محراب ولا في Open VSX.

فالنتيجةُ سطرٌ في **أوّل ثلاثةٍ يقرؤها الزائرُ الجديد**، بأيقونةٍ ووصفٍ مقنع، ونقرتُه
تُنتج «الأمرُ غيرُ معروف». وهو أسوأُ من زرٍّ معطَّل: يَعِد بميزةٍ مركزيّةٍ ثمّ يُكذّب
نفسَه في أوّل تفاعل.

**والعلاج** `when: 'false'` لا حذفُ البند: أصغرُ تغييرٍ يُبقي البنيةَ كما هي، ويسقط
من تلقائه يومَ يُدمَج مقترحُ المنبع أو تُشحَن إضافةٌ تُنفّذ الأمرَ فعلًا.

    python patch_welcome_web_entries.py <مسار شجرة vscode>
"""
import io
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

REL = os.path.join("src", "vs", "workbench", "contrib", "welcomeGettingStarted",
                   "common", "gettingStartedContent.ts")

# المِرساةُ **بمعرّف البند** لا بالشرط وحدَه: الشرطُ `workspacePlatform == 'webworker'`
# يرد على بنودٍ أخرى مشروعة، واستبدالُه أينما ورد يُطفئ ما يعمل.
ANCHOR = re.compile(
    r"(id:\s*'topLevelGitOpen',(?:.*?\n)*?\s*when:\s*)'workspacePlatform == \\?'webworker\\?''")
DONE = re.compile(r"id:\s*'topLevelGitOpen',(?:.*?\n)*?\s*when:\s*'false'")


def fail(msg):
    print("❌ " + msg, file=sys.stderr)
    return 1


def main(tree):
    path = os.path.join(tree, REL)
    if not os.path.isfile(path):
        return fail("لا ملفَّ محتوى الترحيب: " + path)
    src = io.open(path, encoding="utf-8", newline="").read()

    if DONE.search(src):
        print("  ⏭️ بندُ «فتح المستودع» مُطفَأٌ سلفًا (لا عمل)")
        return 0

    n = len(ANCHOR.findall(src))
    if n != 1:
        return fail("مِرساةُ «topLevelGitOpen» وقعت " + str(n) + " مرّةً لا مرّةً واحدة "
                    "— بنيةُ الملفّ ليست ما قِيس. لا يُرقَّع موضعٌ لم يُقرأ.")

    out = ANCHOR.sub(lambda m: m.group(1) + "'false'", src, count=1)
    tmp = path + ".mihrab-tmp"
    io.open(tmp, "w", encoding="utf-8", newline="").write(out)
    os.replace(tmp, path)
    print("  ✅ «فتح المستودع…» مُطفَأٌ في لوح الترحيب — أمرُه من إضافةٍ لا نشحنها")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
