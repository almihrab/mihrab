#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""رُقعة نواة محراب: مجلّد إعدادات المشروع `.محراب` بتوافقٍ خلفيّ — الطبقة 3.

## القرار

  • مشروعٌ **جديد** ⇒ `.محراب`.
  • مشروعٌ **قائم** ⇒ يُقرَأ `.vscode` (و`.mihrab`) كما هو، ولا يُكسَر.
  • وُجد الاثنان ⇒ **الجديد يسود مفتاحًا مفتاحًا، والقديم يُقرَأ للمفقود.**

## لماذا هذه رقعةٌ في أربعة عشر ملفًّا لا تبديلُ ثابتٍ واحد

المنبع يُصرِّح `FOLDER_CONFIG_FOLDER_NAME = '.vscode'` مرّةً — ثمّ يكتب `'.vscode'`
سلسلةً حرفيّة في ثلاثين موضعًا آخر لا تمرّ على الثابت أصلًا: إنشاءُ `tasks.json`،
ومسارُ `launch.json`، وتوصياتُ الامتدادات، وقصاصاتُ مساحة العمل، وتسميةُ `mcp.json`،
وتجاوزُ ترميز UTF-8، ونمطُ الموافقة التلقائيّة في الوكيل.

فلو بُدّل الثابتُ وحده لصار محراب **يقرأ من `.محراب` ويكتب في `.vscode`** — وهو أسوأُ
من ترك الأمر كلِّه: يحفظ المستخدمُ تهيئةَ تنقيحٍ فلا يراها المحرّرُ، ولا رسالةَ خطأ،
ولا شيءَ في السجلّ. عطبٌ صامت. فإمّا النقلُ كاملًا وإمّا لا نقل.

## البنية

  (أ) `mihrabConfigFolder.ts` (‏base/common) — الأسماءُ الثلاثة وترتيبُ أسبقيّتها.
      في base لأنّ من مستهلكيه ما هو في platform، وقواعدُ الطبقات تمنع platform
      من استيراد workbench.
  (ب) `mihrabConfigFolderResolve.ts` (‏platform/configuration/common) — أينَ يُكتَب:
      الموجودُ فعلًا، وإلّا `.محراب`. فمشروعٌ قديم لا يكتسب مجلّدًا ثانيًا بجانب
      مجلّده.
  (ج) **الدمجُ بأسبقيّة** في `FolderConfiguration`: نموذجُ إعداداتٍ لكلّ اسمٍ موجود،
      تُدمَج بترتيب الأسبقيّة (`ConfigurationModel.merge` — الأخيرُ يغلب). فلا يضيع
      إعدادٌ صامتًا حين يوجد المجلّدان.

## حدٌّ معلوم (مذكورٌ لا مخفيّ)

`CachedFolderConfiguration` (مسارُ التخزين المؤقّت للاتّصال البعيد/الوِب) يُخزّن
المجلّدَ الأساسيّ وحده. فمساحةُ عملٍ بعيدةٌ تعتمد `.vscode` فقط قد تفقد طبقةَ
التوافق في أوّل إقلاعٍ بلا اتّصال، حتّى يُحلَّ الملفُّ فعليًّا. لا يمسّ هذا سطحَ
المكتب المحلّيّ (وهو منصّة محراب المقيسة).

idempotent (وسمٌ لكلّ ملفّ)، كتابةٌ ذرّيّة، Python 3.12-آمن، CRLF-محفوظ.
الاستعمال: python patch_config_folder.py <جذر مصدر vscode>
"""
import os
import shutil
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

HERE = os.path.dirname(os.path.abspath(__file__))

# مصدرُ ملفّات الـTS الجديدة. المرقِّع يعمل في موضعين: من مستودع محراب (build/)،
# ومن داخل شجرة المنبع بعد أن ينسخه build.sh (‏.mihrab-core بجانبه). فالبحثُ لا
# الافتراض: مسارٌ ثابتٌ واحد كان سيعمل محلّيًّا ويخفق في البناء الحقيقيّ وحده.
_CORE_CANDIDATES = [
    os.path.join(os.path.dirname(HERE), "patches", "core"),
    os.path.join(HERE, ".mihrab-core"),
]
CORE = next((p for p in _CORE_CANDIDATES if os.path.isdir(p)), _CORE_CANDIDATES[0])

# ملفّاتٌ جديدة تُنسَخ إلى شجرة المنبع (لا مراسي لها — تُفحَص بالوجود في L0/L2).
NEW_FILES = [
    ("mihrabConfigFolder.ts", "src/vs/base/common/mihrabConfigFolder.ts"),
    ("mihrabConfigFolderResolve.ts",
     "src/vs/platform/configuration/common/mihrabConfigFolderResolve.ts"),
]

_CFG = "src/vs/workbench/services/configuration"

# كلّ ملفّ: (المسار النسبيّ، الوسم، [(قديم، جديد، العدد المتوقَّع)]).
FILES = [
    # ── (أ) الثابت: مصدرُ الاسم الواحد ──────────────────────────────────────
    (
        _CFG + "/common/configuration.ts",
        "mihrab-cfgfolder-const",
        [
            (
                "export const FOLDER_CONFIG_FOLDER_NAME = '.vscode';",
                (
                    "// mihrab-cfgfolder-const: الاسمُ المعتمَد يأتي من مصدر الحقيقة الواحد.\n"
                    "// القراءةُ تشمل `.mihrab` و`.vscode` أيضًا — انظر الدمجَ بأسبقيّة في\n"
                    "// browser/configuration.ts (‏FolderConfiguration). هذا الثابتُ هو ما\n"
                    "// **يُكتَب فيه** ويُعرَض، لا كلُّ ما يُقرَأ.\n"
                    "export const FOLDER_CONFIG_FOLDER_NAME = MIHRAB_CONFIG_FOLDER_NAME;"
                ),
                1,
            ),
            (
                "import { IAnyWorkspaceIdentifier } from "
                "'../../../../platform/workspace/common/workspace.js';",
                (
                    "import { IAnyWorkspaceIdentifier } from "
                    "'../../../../platform/workspace/common/workspace.js';\n"
                    "import { MIHRAB_CONFIG_FOLDER_NAME } from "
                    "'../../../../base/common/mihrabConfigFolder.js'; // mihrab-cfgfolder-const"
                ),
                1,
            ),
        ],
    ),
    # ── (ب) الدمجُ بأسبقيّة: قلبُ التوافق الخلفيّ ────────────────────────────
    (
        _CFG + "/browser/configuration.ts",
        "mihrab-cfgfolder-merge",
        [
            (
                "import { equals } from '../../../../base/common/objects.js';",
                (
                    "import { equals } from '../../../../base/common/objects.js';\n"
                    "import { CONFIG_FOLDER_NAMES_BY_PRECEDENCE } from "
                    "'../../../../base/common/mihrabConfigFolder.js'; // mihrab-cfgfolder-merge\n"
                    "import { resolveConfigFolderName } from "
                    "'../../../../platform/configuration/common/mihrabConfigFolderResolve.js'; "
                    "// mihrab-cfgfolder-merge"
                ),
                1,
            ),
            # حقلُ الطبقات الأدنى أسبقيّةً (‏.vscode و.mihrab).
            (
                "\tprivate folderConfiguration: CachedFolderConfiguration | "
                "FileServiceBasedConfiguration;",
                (
                    "\tprivate folderConfiguration: CachedFolderConfiguration | "
                    "FileServiceBasedConfiguration;\n"
                    "\t// mihrab-cfgfolder-merge: طبقاتُ التوافق الخلفيّ — الأسماءُ الأدنى أسبقيّةً\n"
                    "\t// (‏.vscode و.mihrab). تُقرَأ وتُدمَج **تحت** المجلّد المعتمَد، فيسود الجديدُ\n"
                    "\t// مفتاحًا مفتاحًا ويُقرَأ القديمُ للمفقود. بدونها يفقد كلُّ مستودعٍ قائمٍ\n"
                    "\t// في العالم إعداداتِه لحظةَ فتحه في محراب.\n"
                    "\tprivate mihrabUnderlays: FileServiceBasedConfiguration[] = [];"
                ),
                1,
            ),
            # تمهيدُ ذاكرة الحلّ المتزامنة لهذا الجذر (يستعملها مدير التنقيح).
            (
                "\t\tthis.scopes = WorkbenchState.WORKSPACE === this.workbenchState ? "
                "FOLDER_SCOPES : WORKSPACE_SCOPES;",
                (
                    "\t\tthis.scopes = WorkbenchState.WORKSPACE === this.workbenchState ? "
                    "FOLDER_SCOPES : WORKSPACE_SCOPES;\n"
                    "\t\t// mihrab-cfgfolder-merge: مهِّد ذاكرةَ الحلّ لهذا الجذر مبكّرًا — المواضعُ\n"
                    "\t\t// المتزامنة (‏get uri() في مدير التنقيح) تقرأ منها. الإخفاقُ لا يضرّ:\n"
                    "\t\t// تعيد الذاكرةُ حينئذٍ الاسمَ المعتمَد، ومسارُ الإنشاء غيرُ متزامنٍ أصلًا.\n"
                    "\t\tresolveConfigFolderName(fileService, workspaceFolder.uri).catch(() => "
                    "undefined);"
                ),
                1,
            ),
            # الطبقات تُبنى مع التهيئة الأساسيّة وتُنصت للتغيّر مثلها.
            (
                (
                    "\tprivate createFileServiceBasedConfiguration(fileService: IFileService, "
                    "uriIdentityService: IUriIdentityService, logService: ILogService) {\n"
                    "\t\tconst settingsResource = uriIdentityService.extUri.joinPath("
                    "this.configurationFolder, `${FOLDER_SETTINGS_NAME}.json`);"
                ),
                (
                    "\t// mihrab-cfgfolder-merge: تهيئةٌ لكلّ اسمٍ أدنى أسبقيّةً من المعتمَد.\n"
                    "\t// نبنيها كلَّها بلا سؤالٍ عن الوجود: `FileServiceBasedConfiguration` تعامل\n"
                    "\t// الملفَّ المفقود كـ'{}' وتراقب مجلّدَه — فلو أنشأه المستخدمُ لاحقًا التُقط\n"
                    "\t// حيًّا. والسؤالُ المسبق كان سيُدخل سباقًا: مجلّدٌ يظهر بعد الفحص لا يُرى أبدًا.\n"
                    "\tprivate mihrabCreateUnderlays(fileService: IFileService, "
                    "uriIdentityService: IUriIdentityService, logService: ILogService): void {\n"
                    "\t\tconst primary = uriIdentityService.extUri.basename(this.configurationFolder);\n"
                    "\t\tfor (const name of CONFIG_FOLDER_NAMES_BY_PRECEDENCE) {\n"
                    "\t\t\tif (name === primary) {\n"
                    "\t\t\t\tcontinue;\n"
                    "\t\t\t}\n"
                    "\t\t\tconst folder = uriIdentityService.extUri.joinPath("
                    "this.workspaceFolder.uri, name);\n"
                    "\t\t\tconst settingsResource = uriIdentityService.extUri.joinPath(folder, "
                    "`${FOLDER_SETTINGS_NAME}.json`);\n"
                    "\t\t\tconst standAlone: [string, URI][] = [TASKS_CONFIGURATION_KEY, "
                    "LAUNCH_CONFIGURATION_KEY, MCP_CONFIGURATION_KEY].map(key => ([key, "
                    "uriIdentityService.extUri.joinPath(folder, `${key}.json`)]));\n"
                    "\t\t\tconst underlay = this._register(new FileServiceBasedConfiguration("
                    "folder.toString(), settingsResource, standAlone, { scopes: this.scopes, "
                    "skipRestricted: this.isUntrusted() }, fileService, uriIdentityService, "
                    "logService));\n"
                    "\t\t\tthis._register(underlay.onDidChange(() => "
                    "this.onDidFolderConfigurationChange()));\n"
                    "\t\t\tthis.mihrabUnderlays.push(underlay);\n"
                    "\t\t}\n"
                    "\t}\n"
                    "\n"
                    "\tprivate createFileServiceBasedConfiguration(fileService: IFileService, "
                    "uriIdentityService: IUriIdentityService, logService: ILogService) {\n"
                    "\t\tif (!this.mihrabUnderlays.length) {\n"
                    "\t\t\tthis.mihrabCreateUnderlays(fileService, uriIdentityService, logService);\n"
                    "\t\t}\n"
                    "\t\tconst settingsResource = uriIdentityService.extUri.joinPath("
                    "this.configurationFolder, `${FOLDER_SETTINGS_NAME}.json`);"
                ),
                1,
            ),
            # القراءة: الطبقاتُ أوّلًا ثمّ المعتمَد فوقها (الأخيرُ يغلب).
            (
                (
                    "\tloadConfiguration(): Promise<ConfigurationModel> {\n"
                    "\t\treturn this.folderConfiguration.loadConfiguration();\n"
                    "\t}"
                ),
                (
                    "\tasync loadConfiguration(): Promise<ConfigurationModel> {\n"
                    "\t\t// mihrab-cfgfolder-merge: الترتيبُ حرفيًّا هو الأسبقيّة — الأخيرُ يغلب في\n"
                    "\t\t// ConfigurationModel.merge. فلا تعكسه: عكسُه يجعل .vscode يغلب .محراب.\n"
                    "\t\tconst models = await Promise.all([...this.mihrabUnderlays, "
                    "this.folderConfiguration].map(c => c.loadConfiguration()));\n"
                    "\t\tconst [base, ...rest] = models;\n"
                    "\t\treturn rest.length ? base.merge(...rest) : base;\n"
                    "\t}"
                ),
                1,
            ),
            (
                (
                    "\treparse(): ConfigurationModel {\n"
                    "\t\tconst configurationModel = this.folderConfiguration.reparse({ scopes: "
                    "this.scopes, skipRestricted: this.isUntrusted() });\n"
                    "\t\tthis.updateCache();\n"
                    "\t\treturn configurationModel;\n"
                    "\t}"
                ),
                (
                    "\treparse(): ConfigurationModel {\n"
                    "\t\tconst options = { scopes: this.scopes, skipRestricted: this.isUntrusted() };\n"
                    "\t\t// mihrab-cfgfolder-merge: أُعيد التحليلَ للطبقات كلِّها لا للمعتمَد وحده —\n"
                    "\t\t// وإلّا بقيت إعداداتُ .vscode مُحلَّلةً بثقةٍ قديمة بعد تغيّر الثقة بالمجلّد.\n"
                    "\t\tconst underlayModels = this.mihrabUnderlays.map(c => c.reparse(options));\n"
                    "\t\tconst configurationModel = this.folderConfiguration.reparse(options);\n"
                    "\t\tthis.updateCache();\n"
                    "\t\treturn underlayModels.length ? underlayModels[0].merge("
                    "...underlayModels.slice(1), configurationModel) : configurationModel;\n"
                    "\t}"
                ),
                1,
            ),
            (
                (
                    "\tgetRestrictedSettings(): string[] {\n"
                    "\t\treturn this.folderConfiguration.getRestrictedSettings();\n"
                    "\t}"
                ),
                (
                    "\tgetRestrictedSettings(): string[] {\n"
                    "\t\t// mihrab-cfgfolder-merge: إعدادٌ مقيَّد في .vscode مقيَّدٌ أيضًا — الاتّحادُ\n"
                    "\t\t// لا المعتمَدُ وحده، وإلّا صار مجلّدٌ غيرُ موثوقٍ يُنفَّذ منه إعدادٌ خطر.\n"
                    "\t\tconst all = this.folderConfiguration.getRestrictedSettings().concat("
                    "...this.mihrabUnderlays.map(c => c.getRestrictedSettings()));\n"
                    "\t\treturn [...new Set(all)];\n"
                    "\t}"
                ),
                1,
            ),
        ],
    ),
    # ── (ج) مسارُ إعدادات المجلّد المعروض في محرّر التفضيلات ─────────────────
    (
        "src/vs/workbench/services/preferences/common/preferences.ts",
        "mihrab-cfgfolder-prefs",
        [
            (
                "export const FOLDER_SETTINGS_PATH = '.vscode/settings.json';",
                (
                    "// mihrab-cfgfolder-prefs: نسخةٌ ثانيةٌ من المسار كان المنبع يكتبها حرفيًّا\n"
                    "// بمعزلٍ عن FOLDER_CONFIG_FOLDER_NAME — فتتباعد النسختان بلا أن يشتكي شيء.\n"
                    "export const FOLDER_SETTINGS_PATH = "
                    "`${MIHRAB_CONFIG_FOLDER_NAME}/settings.json`;"
                ),
                1,
            ),
            # مرساةُ الاستيراد على URI: استيرادُ IStringDictionary أُزيل في 1.143.
            (
                "import { URI } from '../../../../base/common/uri.js';",
                (
                    "import { URI } from '../../../../base/common/uri.js';\n"
                    "import { MIHRAB_CONFIG_FOLDER_NAME } from "
                    "'../../../../base/common/mihrabConfigFolder.js'; // mihrab-cfgfolder-prefs"
                ),
                1,
            ),
        ],
    ),
    # ── (د) توصياتُ الامتدادات ──────────────────────────────────────────────
    (
        "src/vs/workbench/services/extensionRecommendations/common/workspaceExtensionsConfig.ts",
        "mihrab-cfgfolder-extrec",
        [
            (
                "export const EXTENSIONS_CONFIG = '.vscode/extensions.json';",
                (
                    "// mihrab-cfgfolder-extrec: مسارُ ملفّ التوصيات.\n"
                    "export const EXTENSIONS_CONFIG = "
                    "`${MIHRAB_CONFIG_FOLDER_NAME}/extensions.json`;"
                ),
                1,
            ),
            (
                "import { distinct } from '../../../../base/common/arrays.js';",
                (
                    "import { distinct } from '../../../../base/common/arrays.js';\n"
                    "import { MIHRAB_CONFIG_FOLDER_NAME } from "
                    "'../../../../base/common/mihrabConfigFolder.js'; // mihrab-cfgfolder-extrec"
                ),
                1,
            ),
        ],
    ),
    # ── (هـ) مسارُ launch.json: عرضًا وإنشاءً ────────────────────────────────
    (
        "src/vs/workbench/contrib/debug/browser/debugConfigurationManager.ts",
        "mihrab-cfgfolder-debug",
        [
            (
                "import { distinct } from '../../../../base/common/arrays.js';",
                (
                    "import { distinct } from '../../../../base/common/arrays.js';\n"
                    "import { configFolderNameSync, resolveConfigFileResource } from "
                    "'../../../../platform/configuration/common/mihrabConfigFolderResolve.js'; "
                    "// mihrab-cfgfolder-debug"
                ),
                1,
            ),
            (
                "\t\treturn resources.joinPath(this.workspace.uri, '/.vscode/launch.json');",
                (
                    "\t\t// mihrab-cfgfolder-debug: جالبٌ متزامن ⇒ الذاكرةُ المُمهَّدة من\n"
                    "\t\t// FolderConfiguration. الإنشاءُ لا يعتمد عليه (‏openConfigFile غيرُ\n"
                    "\t\t// متزامن ويحلّ فعليًّا) فأسوأُ ما يُنتجه مسارٌ يُعرَض لا ملفٌّ يُكتَب خطأً.\n"
                    "\t\treturn resources.joinPath(this.workspace.uri, "
                    "`/${configFolderNameSync(this.workspace.uri)}/launch.json`);"
                ),
                1,
            ),
            (
                (
                    "\t\tconst resource = this.uri;\n"
                    "\t\tlet created = false;"
                ),
                (
                    "\t\t// mihrab-cfgfolder-debug: الحلُّ الفعليّ هنا لا الجالبُ المتزامن — هذا هو\n"
                    "\t\t// المسارُ الذي **يُنشئ** الملفّ، ومشروعٌ فيه .vscode يجب أن يبقى فيه لا أن\n"
                    "\t\t// يكتسب مجلّدًا ثانيًا بجانبه لا يعرفه زملاءُ صاحبه.\n"
                    "\t\tconst resource = await resolveConfigFileResource("
                    "this.fileService, this.workspace.uri, 'launch.json');\n"
                    "\t\tlet created = false;"
                ),
                1,
            ),
            (
                "\"Unable to create 'launch.json' file inside the '.vscode' folder ({0}).\"",
                "\"Unable to create 'launch.json' file inside the workspace "
                "configuration folder ({0}).\"",
                1,
            ),
        ],
    ),
    # ── (و) المهامّ: ستّةُ مواضع + الإنشاء ──────────────────────────────────
    (
        "src/vs/workbench/contrib/tasks/browser/abstractTaskService.ts",
        "mihrab-cfgfolder-tasks",
        [
            (
                "import { Action } from '../../../../base/common/actions.js';",
                (
                    "import { Action } from '../../../../base/common/actions.js';\n"
                    "import { configFolderNameSync, resolveConfigFileResource } from "
                    "'../../../../platform/configuration/common/mihrabConfigFolderResolve.js'; "
                    "// mihrab-cfgfolder-tasks"
                ),
                1,
            ),
            (
                "\t\t\tawait this._textFileService.create([{ resource: "
                "workspaceFolder.toResource('.vscode/tasks.json'), value: content }]);",
                (
                    "\t\t\t// mihrab-cfgfolder-tasks: مسارُ الإنشاء ⇒ حلٌّ فعليّ لا افتراض.\n"
                    "\t\t\tawait this._textFileService.create([{ resource: "
                    "await resolveConfigFileResource(this._fileService, workspaceFolder.uri, "
                    "'tasks.json'), value: content }]);"
                ),
                1,
            ),
            (
                "\t\t\treturn task.getWorkspaceFolder()!.toResource('.vscode/tasks.json');",
                (
                    "\t\t\tconst mihrabFolder = task.getWorkspaceFolder()!; "
                    "// mihrab-cfgfolder-tasks\n"
                    "\t\t\treturn mihrabFolder.toResource("
                    "`${configFolderNameSync(mihrabFolder.uri)}/tasks.json`);"
                ),
                1,
            ),
            (
                "this._workspaceFolders[0].toResource('.vscode/tasks.json')",
                "this._workspaceFolders[0].toResource("
                "`${configFolderNameSync(this._workspaceFolders[0].uri)}/tasks.json`)",
                1,
            ),
            (
                "selection.folder.toResource('.vscode/tasks.json')",
                "selection.folder.toResource("
                "`${configFolderNameSync(selection.folder.uri)}/tasks.json`)",
                1,
            ),
            (
                "folder.toResource('.vscode/tasks.json')",
                "folder.toResource(`${configFolderNameSync(folder.uri)}/tasks.json`)",
                2,
            ),
        ],
    ),
    (
        "src/vs/workbench/contrib/tasks/common/taskConfiguration.ts",
        "mihrab-cfgfolder-taskcfg",
        [
            (
                "import * as nls from '../../../../nls.js';",
                (
                    "import * as nls from '../../../../nls.js';\n"
                    "import { MIHRAB_CONFIG_FOLDER_NAME } from "
                    "'../../../../base/common/mihrabConfigFolder.js'; // mihrab-cfgfolder-taskcfg"
                ),
                1,
            ),
            (
                "\t\t\tfile: '.vscode/tasks.json',",
                "\t\t\tfile: `${MIHRAB_CONFIG_FOLDER_NAME}/tasks.json`,",
                1,
            ),
            (
                "file: '.vscode/tasks.json', workspaceFolder: context.workspaceFolder",
                "file: `${MIHRAB_CONFIG_FOLDER_NAME}/tasks.json`, "
                "workspaceFolder: context.workspaceFolder",
                3,
            ),
        ],
    ),
    # ── (ز) MCP: التسمية المعروضة ───────────────────────────────────────────
    (
        "src/vs/workbench/contrib/mcp/browser/mcpWorkbenchService.ts",
        "mihrab-cfgfolder-mcp",
        [
            (
                "import { CancellationToken } from '../../../../base/common/cancellation.js';",
                (
                    "import { CancellationToken } from "
                    "'../../../../base/common/cancellation.js';\n"
                    "import { configFolderNameSync } from "
                    "'../../../../platform/configuration/common/mihrabConfigFolderResolve.js'; "
                    "// mihrab-cfgfolder-mcp"
                ),
                1,
            ),
            (
                "\t\t\t\t\tlabel: `${workspaceFolder.name}/.vscode/mcp.json`,",
                "\t\t\t\t\tlabel: `${workspaceFolder.name}/"
                "${configFolderNameSync(workspaceFolder.uri)}/mcp.json`, "
                "// mihrab-cfgfolder-mcp",
                1,
            ),
        ],
    ),
    # ── (ح) القصاصات: تُقرَأ من الموجود لا من المفترَض ──────────────────────
    (
        "src/vs/workbench/contrib/snippets/browser/snippetsService.ts",
        "mihrab-cfgfolder-snippets",
        [
            (
                "import { IJSONSchema } from '../../../../base/common/jsonSchema.js';",
                (
                    "import { IJSONSchema } from '../../../../base/common/jsonSchema.js';\n"
                    "import { resolveConfigFolderName } from "
                    "'../../../../platform/configuration/common/mihrabConfigFolderResolve.js'; "
                    "// mihrab-cfgfolder-snippets"
                ),
                1,
            ),
            (
                "\t\t\tconst snippetFolder = folder.toResource('.vscode');",
                (
                    "\t\t\t// mihrab-cfgfolder-snippets: الموجودُ فعلًا — فمستودعٌ قديم لا تختفي\n"
                    "\t\t\t// قصاصاتُ مساحة عمله لحظةَ فتحه في محراب.\n"
                    "\t\t\tconst snippetFolder = folder.toResource("
                    "await resolveConfigFolderName(this._fileService, folder.uri));"
                ),
                1,
            ),
        ],
    ),
    (
        "src/vs/workbench/contrib/snippets/browser/commands/configureSnippets.ts",
        "mihrab-cfgfolder-snipcmd",
        [
            (
                "import { isValidBasename } from "
                "'../../../../../base/common/extpath.js';",
                (
                    "import { isValidBasename } from "
                    "'../../../../../base/common/extpath.js';\n"
                    "import { configFolderNameSync } from "
                    "'../../../../../platform/configuration/common/"
                    "mihrabConfigFolderResolve.js'; // mihrab-cfgfolder-snipcmd"
                ),
                1,
            ),
            (
                "\t\t\t\turi: folder.toResource('.vscode')",
                "\t\t\t\turi: folder.toResource(configFolderNameSync(folder.uri)) "
                "// mihrab-cfgfolder-snipcmd",
                1,
            ),
        ],
    ),
    # ── (ط) امتداداتُ مساحة العمل ───────────────────────────────────────────
    (
        "src/vs/workbench/contrib/extensions/browser/workspaceRecommendations.ts",
        "mihrab-cfgfolder-wsext",
        [
            (
                "import { EXTENSION_IDENTIFIER_PATTERN } from "
                "'../../../../platform/extensionManagement/common/extensionManagement.js';",
                (
                    "import { EXTENSION_IDENTIFIER_PATTERN } from "
                    "'../../../../platform/extensionManagement/common/extensionManagement.js';\n"
                    "import { MIHRAB_CONFIG_FOLDER_NAME } from "
                    "'../../../../base/common/mihrabConfigFolder.js'; // mihrab-cfgfolder-wsext"
                ),
                1,
            ),
            (
                "const WORKSPACE_EXTENSIONS_FOLDER = '.vscode/extensions';",
                "const WORKSPACE_EXTENSIONS_FOLDER = "
                "`${MIHRAB_CONFIG_FOLDER_NAME}/extensions`; // mihrab-cfgfolder-wsext",
                1,
            ),
        ],
    ),
    # ── (ي) تجاوزُ ترميز UTF-8: للأسماء الثلاثة ─────────────────────────────
    (
        "src/vs/workbench/services/textfile/browser/textFileService.ts",
        "mihrab-cfgfolder-encoding",
        [
            (
                "import { localize } from '../../../../nls.js';",
                (
                    "import { localize } from '../../../../nls.js';\n"
                    "import { CONFIG_FOLDER_NAMES_BY_PRECEDENCE } from "
                    "'../../../../base/common/mihrabConfigFolder.js'; "
                    "// mihrab-cfgfolder-encoding"
                ),
                1,
            ),
            (
                "\t\t\tdefaultEncodingOverrides.push({ parent: joinPath(folder.uri, "
                "'.vscode'), encoding: UTF8 });",
                (
                    "\t\t\t// mihrab-cfgfolder-encoding: الأسماءُ الثلاثة. تجاوزٌ يشمل الجديدَ\n"
                    "\t\t\t// وحده يترك settings.json في مستودعٍ قديم يُقرَأ بترميز النظام —\n"
                    "\t\t\t// فيتلف أيُّ نصٍّ عربيّ فيه بصمت.\n"
                    "\t\t\tfor (const mihrabCfgName of CONFIG_FOLDER_NAMES_BY_PRECEDENCE) {\n"
                    "\t\t\t\tdefaultEncodingOverrides.push({ parent: joinPath(folder.uri, "
                    "mihrabCfgName), encoding: UTF8 });\n"
                    "\t\t\t}"
                ),
                1,
            ),
        ],
    ),
    # ── (ك) القياس: يُبلِّغ عن الأسماء الثلاثة ──────────────────────────────
    (
        "src/vs/workbench/contrib/telemetry/browser/telemetry.contribution.ts",
        "mihrab-cfgfolder-telemetry",
        [
            (
                "import { Registry } from '../../../../platform/registry/common/platform.js';",
                (
                    "import { Registry } from "
                    "'../../../../platform/registry/common/platform.js';\n"
                    "import { CONFIG_FOLDER_NAMES_BY_PRECEDENCE } from "
                    "'../../../../base/common/mihrabConfigFolder.js'; "
                    "// mihrab-cfgfolder-telemetry"
                ),
                1,
            ),
            (
                (
                    "\t\t\tif (isEqualOrParent(resource, folder.toResource('.vscode'))) {\n"
                    "\t\t\t\tconst filename = basename(resource);\n"
                    "\t\t\t\tif (TelemetryContribution.ALLOWLIST_WORKSPACE_JSON.indexOf("
                    "filename) > -1) {\n"
                    "\t\t\t\t\treturn `.vscode/${filename}`;\n"
                    "\t\t\t\t}\n"
                    "\t\t\t}"
                ),
                (
                    "\t\t\t// mihrab-cfgfolder-telemetry: الأسماءُ الثلاثة — وإلّا سقطت ملفّاتُ\n"
                    "\t\t\t// المجلّد الجديد من قائمة السماح فصارت تُبلَّغ باسمها الكامل.\n"
                    "\t\t\tfor (const mihrabCfgName of CONFIG_FOLDER_NAMES_BY_PRECEDENCE) {\n"
                    "\t\t\t\tif (isEqualOrParent(resource, folder.toResource(mihrabCfgName))) {\n"
                    "\t\t\t\t\tconst filename = basename(resource);\n"
                    "\t\t\t\t\tif (TelemetryContribution.ALLOWLIST_WORKSPACE_JSON.indexOf("
                    "filename) > -1) {\n"
                    "\t\t\t\t\t\treturn `${mihrabCfgName}/${filename}`;\n"
                    "\t\t\t\t\t}\n"
                    "\t\t\t\t}\n"
                    "\t\t\t}"
                ),
                1,
            ),
        ],
    ),
    # ── (ل) التشخيص (‏platform/node) ────────────────────────────────────────
    (
        "src/vs/platform/diagnostics/node/diagnosticsService.ts",
        "mihrab-cfgfolder-diag",
        [
            (
                "import * as fs from 'fs';",
                (
                    "import * as fs from 'fs';\n"
                    "import { CONFIG_FOLDER_NAMES_BY_PREFERENCE } from "
                    "'../../../base/common/mihrabConfigFolder.js'; // mihrab-cfgfolder-diag"
                ),
                1,
            ),
            (
                "\t\tconst launchConfig = join(folder, '.vscode', 'launch.json');",
                (
                    "\t\t// mihrab-cfgfolder-diag: أوّلُ اسمٍ موجود بترتيب الأفضليّة.\n"
                    "\t\tlet launchConfig = join(folder, "
                    "CONFIG_FOLDER_NAMES_BY_PREFERENCE[0], 'launch.json');\n"
                    "\t\tfor (const mihrabCfgName of CONFIG_FOLDER_NAMES_BY_PREFERENCE) {\n"
                    "\t\t\tconst mihrabCandidate = join(folder, mihrabCfgName, 'launch.json');\n"
                    "\t\t\ttry {\n"
                    "\t\t\t\tawait fs.promises.access(mihrabCandidate);\n"
                    "\t\t\t\tlaunchConfig = mihrabCandidate;\n"
                    "\t\t\t\tbreak;\n"
                    "\t\t\t} catch (e) {\n"
                    "\t\t\t\t// غيرُ موجود: التالي.\n"
                    "\t\t\t}\n"
                    "\t\t}"
                ),
                1,
            ),
        ],
    ),
    # ── (م) أنماطُ الموافقة التلقائيّة: قاعدةُ أمانٍ لا تجميل ────────────────
    # نمطٌ يطابق `.vscode` وحده يصير **ثقبًا** لحظةَ تسمية المجلّد باسمه الجديد:
    # يعود الوكيلُ يعدّل settings.json وlaunch.json بموافقةٍ تلقائيّة. الأسماءُ
    # مكتوبةٌ حرفيًّا هنا لأنّ القيمة افتراضُ إعدادٍ مُسجَّل (لا مجالَ لاستدعاء دالّة).
    #
    # منذ 1.143 جمع المنبعُ النمطَ في موضعٍ واحد: ALWAYS_CHECKED_EDIT_PATTERNS في
    # platform/chat/common/chatSettings.ts، ويستورده chat.shared.contribution.ts
    # وagentHost/node/sessionPermissions.ts معًا (كان كلٌّ منهما يكتبه حرفيًّا حتّى 1.126).
    # فرقعةٌ واحدة هناك تسدّ الثقبين.
    (
        "src/vs/platform/chat/common/chatSettings.ts",
        "mihrab-cfgfolder-permglob",
        [
            (
                "\t'**/.vscode/*.json': false,",
                "\t'**/{.محراب,.mihrab,.vscode}/*.json': false, "
                "// mihrab-cfgfolder-permglob",
                1,
            ),
        ],
    ),
    (
        "src/vs/workbench/contrib/chat/browser/chat.shared.contribution.ts",
        # الوسمُ هنا هو النصُّ المُرقَّع نفسُه: لم يبقَ في الملفّ إلّا سلسلةٌ داخل
        # localize، ولا يُحقَن فيها تعليق. والمطابقةُ بالاحتواء، فتبقى idempotent.
        "such as `**/{.محراب,.mihrab,.vscode}/*.json`.",
        [
            # وصفُ الإعداد يذكر النمطَ الافتراضيّ حرفيًّا: تركُه يجعل التوثيقَ
            # المدمج يصف افتراضًا لم يعد قائمًا — وهو أسوأ من غيابه.
            (
                "such as `**/.vscode/*.json`.",
                "such as `**/{.محراب,.mihrab,.vscode}/*.json`.",
                1,
            ),
        ],
    ),
]


def _read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def _write_atomic(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, path)


def _apply(root, relpath, mark, edits):
    """يطبّق تعديلات ملفٍّ واحد. يعيد True نجاحًا (أو تخطّيًا)، False إخفاقًا."""
    path = os.path.join(root, relpath.replace("/", os.sep))
    try:
        text = _read(path)
    except OSError as e:
        print(f"⚠️ تعذّر فتح {relpath}: {e}", file=sys.stderr)
        return False

    if mark in text:
        print(f"  ⏭️  {relpath} — مُرقَّع مسبقًا.")
        return True

    nl = "\r\n" if "\r\n" in text else "\n"
    for old, new, count in edits:
        old_nl = old.replace("\n", nl)
        found = text.count(old_nl)
        if found != count:
            print(f"⚠️ {relpath}: المرساة وُجدت {found} مرّة والمتوقَّع {count} — "
                  f"تغيّر المنبع؟\n   المرساة: {old.splitlines()[0][:100]}", file=sys.stderr)
            return False
        text = text.replace(old_nl, new.replace("\n", nl), count)

    try:
        _write_atomic(path, text)
    except OSError as e:
        print(f"⚠️ تعذّر كتابة {relpath}: {e}", file=sys.stderr)
        return False
    print(f"  ✅ {relpath}")
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print("الاستعمال: python patch_config_folder.py <جذر مصدر vscode>", file=sys.stderr)
        return 2
    root = sys.argv[1]

    ok = True
    for src_name, dest_rel in NEW_FILES:
        src = os.path.join(CORE, src_name)
        dest = os.path.join(root, dest_rel.replace("/", os.sep))
        if not os.path.isfile(src):
            print(f"⚠️ مفقود: {src}", file=sys.stderr)
            ok = False
            continue
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(src, dest)
            print(f"  ✅ نُسخ {dest_rel}")
        except OSError as e:
            print(f"⚠️ تعذّر نسخ {dest_rel}: {e}", file=sys.stderr)
            ok = False

    for relpath, mark, edits in FILES:
        if not _apply(root, relpath, mark, edits):
            ok = False

    if not ok:
        print("❌ رقعة مجلّد الإعدادات لم تكتمل.", file=sys.stderr)
        return 1
    print("✅ رُقِّع مجلّد إعدادات المشروع (.محراب مع توافقٍ خلفيّ لـ.vscode).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
