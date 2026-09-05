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
#
# والفجوةُ `[^{}]*?` لا `(?:.*?\n)*?`: الأخيرةُ **تعبُر البنودَ** — الملفُّ فيه شرطا
# `webworker` (‏184 و264)، فيومَ يتغيّر شرطُ `topLevelGitOpen` في المنبع (وهو ما
# يقترحه م-٢٨ بالضبط) تسقط `DONE` وتقع المِرساةُ مرّةً واحدةً على **البند الخطأ**،
# فيُطفَأ «استكشف الإضافات» ويُطبَع ✅. الدفاعُ بترتيب `DONE` قبل `ANCHOR` مصادفةٌ
# لا تصميم. و`[^{}]` تحبس المطابقةَ داخل حدود البند الواحد.
ANCHOR = re.compile(
    r"(id:\s*'topLevelGitOpen',[^{}]*?when:\s*)'workspacePlatform == \\?'webworker\\?''")
DONE = re.compile(r"id:\s*'topLevelGitOpen',[^{}]*?when:\s*'false'")

# ── وبديلٌ يعمل مكانَ ما أُطفئ ──
# عمودُ «بدء» بعد الإطفاء **بندان** فقط: `topLevelOpenFolder` شرطُه `!isWeb`، و
# `topLevelOpenFolderWeb` شرطُه `workbenchState == 'workspace'` — و`boot.js` يمرّر
# `workspace: undefined` فالحالةُ `empty`. فالفعلُ الذي يتفاخر به شريطُ التنبيه
# («فتح مجلّد يحتاج Chrome أو Edge») **غائبٌ عن أوّل شاشة**.
#
# و`hasWebFileSystemAccess` هو المفتاحُ الصحيح (‏`common/contextkeys.ts`): يراه زائرُ
# Chrome/Edge ولا يراه زائرُ فايرفوكس — وهو **بعينه** الانقسامُ الذي يشرحه الشريط.
# لا وعدَ كاذبًا في أيٍّ من الحالتين.
#
# و`addRootFolder` لا `openFolder`: الثاني يرمي في المتصفّح رسالةً **إنجليزيّةً خامًا**
# (`fileDialogService.ts` ⇐ "Can't open folders…") — وهي أقبحُ من «الأمرُ غيرُ معروف»
# في محرِّرٍ دعواه العربيّة. والأوّلُ هو ما يستعمله المنبعُ نفسُه في حالة الورشة.
NEW_ENTRY = """	{
		id: 'mihrabOpenFolderWeb',
		title: localize('mihrab.openFolderWeb.title', "فتح مجلّداً…"),
		description: localize('mihrab.openFolderWeb.description', "اختر مجلّداً من جهازك. لا يُرفَع شيء — يبقى عندك."),
		when: 'hasWebFileSystemAccess',
		icon: Codicon.folderOpened,
		content: {
			type: 'startEntry',
			command: 'command:workbench.action.addRootFolder',
		}
	},
"""
ENTRY_ID = "mihrabOpenFolderWeb"
INSERT_AT = re.compile(r"(?=\t\{\n\t\tid: 'topLevelGitOpen',)")


def fail(msg):
    print("❌ " + msg, file=sys.stderr)
    return 1


def main(tree):
    path = os.path.join(tree, REL)
    if not os.path.isfile(path):
        return fail("لا ملفَّ محتوى الترحيب: " + path)
    src = io.open(path, encoding="utf-8", newline="").read()

    out = src
    changed = []

    if DONE.search(out):
        print("  ⏭️ بندُ «فتح المستودع» مُطفَأٌ سلفًا")
    else:
        n = len(ANCHOR.findall(out))
        if n != 1:
            return fail("مِرساةُ «topLevelGitOpen» وقعت " + str(n) + " مرّةً لا مرّةً "
                        "واحدة — بنيةُ الملفّ ليست ما قِيس. لا يُرقَّع موضعٌ لم يُقرأ.")
        out = ANCHOR.sub(lambda m: m.group(1) + "'false'", out, count=1)
        changed.append("«فتح المستودع…» مُطفَأ — أمرُه من إضافةٍ لا نشحنها")

    if ENTRY_ID in out:
        print("  ⏭️ بندُ «فتح مجلّداً» موجودٌ سلفًا")
    else:
        m = len(INSERT_AT.findall(out))
        if m != 1:
            return fail("موضعُ الإدراج وقع " + str(m) + " مرّةً لا مرّةً واحدة.")
        out = INSERT_AT.sub(NEW_ENTRY, out, count=1)
        changed.append("«فتح مجلّداً…» مُضافٌ بشرط hasWebFileSystemAccess")

    if not changed:
        return 0
    tmp = path + ".mihrab-tmp"
    io.open(tmp, "w", encoding="utf-8", newline="").write(out)
    os.replace(tmp, path)
    for c in changed:
        print("  ✅ " + c)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
