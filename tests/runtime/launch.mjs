// مُطلِق محراب للتشغيل الحيّ (L3) — يصرّف، يُطلق، ينتظر CDP، يلتقط، ويقيس.
//
// كان L3 يشترط أن يُطلق **المستخدم** النسخة يدويًّا («صدفة الأتمتة لا تُطلق GUI»). هذا الملفّ
// يرفع ذلك الشرط في وضع التطوير: يُطلق Electron من شجرة المصدر المُزامَنة (build/dev_sync.py)
// عبر `scripts/code.bat`، فيصير تعديلُ تصميمٍ ← رؤيتُه حيًّا دورةً واحدة بلا بناء كامل.
//
// الاستعمال:
//   node tests/runtime/launch.mjs --build            # تصريف ثمّ إطلاق ثمّ لقطة
//   node tests/runtime/launch.mjs --shot welcome     # إطلاق + لقطة باسم
//   node tests/runtime/launch.mjs --spec             # إطلاق + تشغيل تأكيدات rtl.spec
//   node tests/runtime/launch.mjs --eval "expr"      # إطلاق + تقييم تعبير وطبع الناتج
//   node tests/runtime/launch.mjs --keep             # لا تُغلق النسخة عند الانتهاء
//
// الخرج: اللقطات في tests/runtime/artifacts/ (مُتجاهَلة في git).
// خرج 0 = نجاح، 1 = فشل تأكيد، 2 = خطأ تشغيليّ (لا تصريف/لا إطلاق).
import { spawn, spawnSync } from "node:child_process";
import { appendFileSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { CDP, sleep } from "./harness.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const UP = join(ROOT, ".upstream", "vscode");
// مسارُ سلسلةِ الأدوات **يُشتَقّ من `upstream.json`** لا يُكتب هنا. كان مثبَّتًا حرفيًّا
// (`node-v22.22.1-win-x64`)، وترقيةُ المنبع إلى 1.126 نقلت الرقمَ إلى 24.15.0 فصار
// المسارُ يشير إلى مجلّدٍ غيرِ موجود — و`envWithToolchain` تتجاهله بصمتٍ حينها
// (`existsSync` كاذبة)، فيرثُ الطفلُ Node النظامِ بلا كلمة. وNode أقدمُ من أن يصرّف
// ‏`.ts` يُفشِل التصريفَ برسالةٍ لا تذكر Node. نفسُ العطبِ الذي كان في `build.sh`.
const NODE_VERSION = (() => {
  try {
    const up = JSON.parse(readFileSync(join(ROOT, "upstream.json"), "utf8"));
    return up?.toolchain?.node;
  } catch { return null; }
})();
const TOOLCHAIN = NODE_VERSION
  ? join(ROOT, "build", ".toolchain", `node-v${NODE_VERSION}-win-x64`)
  : "";
const ARTIFACTS = join(HERE, "artifacts");
const FIXTURE = join(HERE, "fixtures", "rtl_fixture.ص");
// عيّنةُ تصيير ملاحظات الإصدار: تُفتَح **دائمًا** في تبويبٍ خلفيّ لأنّ مِجَسَّ
// `releaseNotesRendering` يحتاجها نشطةً لحظةَ قياسه، وأمرُ «افتح الملفَّ الحاليَّ
// كملاحظاتِ إصدار» يقرأ المحرّرَ النشط. وفتحُها هنا لا بـ`--tabs` كي يعمل المِجَسّ في
// كلّ تشغيلة لا في التشغيلات التي تذكرها يدويًّا. وهي كذلك التبويبُ الثاني الذي يحتاجه
// مِجَسّ إفلات التبويبات (كان يُتخطّى بلا `--tabs`).
const NOTES_PROBE = join(HERE, "fixtures", "release_notes_probe.md");

const argv = process.argv.slice(2);
const has = f => argv.includes(f);
const val = (f, d) => { const i = argv.indexOf(f); return i >= 0 && argv[i + 1] ? argv[i + 1] : d; };
const PORT = parseInt(val("--port", "9222"), 10);
// مهلة الإقلاع سخيّة عمدًا: أوّل إقلاع بعد تصريف جديد يبني ذاكرة الوحدات ويكون أبطأ بكثير.
const BOOT_TIMEOUT_MS = parseInt(val("--boot-timeout", "180000"), 10);

const log = m => console.log(`▶ ${m}`);
const fail = (m, code = 2) => { console.error(`❌ ${m}`); process.exit(code); };

/** يضع Node المحمول (المطابق لـ.nvmrc) أوّل PATH — Node النظام قد يكون أقدم من أن يصرّف .ts. */
function envWithToolchain() {
  const env = { ...process.env };
  if (existsSync(TOOLCHAIN)) env.PATH = `${TOOLCHAIN};${env.PATH}`;
  return env;
}

/**
 * ⚠️ **الفخّ الذي كان يُوهِم أنّ «صدفة الأتمتة لا تُطلق GUI»:** حين يعمل المُطلِق داخل
 * مضيف امتدادات VS Code (أو أيّ طرفيّة مدمجة فيه)، تكون البيئة موروثةً من Electron مضيفٍ
 * آخر — وفيها `ELECTRON_RUN_AS_NODE=1`. الطفل يرث المتغيّر فيعمل Electron **بوضع Node**
 * لا بوضع تطبيق ⇒ ينهار فورًا بـ:
 *     SyntaxError: The requested module 'electron' does not provide an export named 'Menu'
 * وهي رسالة تبدو كعطبٍ في البناء لا كتلوّث بيئة. وبقيّة `VSCODE_*` (‏IPC_HOOK، PID،
 * NLS_CONFIG، ESM_ENTRYPOINT…) تُوجّه الطفل إلى نسخة المضيف. فننظّف البيئة صراحةً.
 */
function cleanElectronEnv() {
  const env = envWithToolchain();
  delete env.ELECTRON_RUN_AS_NODE;
  for (const k of Object.keys(env)) if (k.startsWith("VSCODE_")) delete env[k];
  // إعدادات وضع التطوير التي يضبطها scripts/code.bat (نُطلق الثنائيّ مباشرةً لا عبره:
  // نتخطّى preLaunch — تصريفنا وElectron جاهزان — ونملك البيئة كاملةً).
  env.NODE_ENV = "development";
  env.VSCODE_DEV = "1";
  env.ELECTRON_ENABLE_LOGGING = "1";
  return env;
}

/** اسم الثنائيّ = product.json:nameShort (‏Mihrab.exe بعد دمج الهوية) — كما يشتقّه code.bat. */
function electronBinary() {
  const prod = JSON.parse(readFileSync(join(UP, "product.json"), "utf8"));
  const exe = `${prod.nameShort || "Code - OSS"}.exe`;
  const bin = join(UP, ".build", "electron", exe);
  if (!existsSync(bin))
    fail(`لا ثنائيّ Electron: ${bin}\n   شغّل: (cd .upstream/vscode && npm run electron)`);
  return bin;
}

function compile() {
  // ‏`compile` **ليس** ما نريد على شجرة VSCodium. صار في 1.126:
  //     compile = npm-run-all2 -lp compile-client compile-copilot
  // و`compile-copilot` يشتغل في `extensions/copilot` — وVSCodium **يحذف** ذلك الامتداد.
  // فالأمرُ يسقط بـENOENT قبل أن يبلغ الطبقةَ التي نقيسها، ورسالتُه عن `package.json`
  // مفقودٍ لا عن شيءٍ يخصّنا. وقِيس على ترقية 1.121 ⇐ 1.126: كان `compile` مرادفًا
  // لـ`compile-client` فمرّ، وصار مركَّبًا فسقط.
  //
  // و`compile-client` هو المقصودُ أصلًا: كلُّ مِجَسّات L3 تقرأ المحرّرَ ومنضدةَ العمل،
  // ولا مِجَسَّ يمسّ امتدادَ copilot. فيُختار صراحةً حين يغيب الامتداد، ويبقى `compile`
  // حين يوجد كي لا نُنقِص شيئًا على شجرةٍ كاملة.
  const hasCopilot = existsSync(join(UP, "extensions", "copilot", "package.json"));
  const task = hasCopilot ? "compile" : "compile-client";
  log(`تصريف شجرة المصدر (npm run ${task}) — قد يطول عند أوّل مرّة…`);
  const r = spawnSync("npm.cmd", ["run", task], {
    cwd: UP, env: envWithToolchain(), stdio: "inherit", shell: false,
  });
  if (r.status !== 0) fail(`فشل التصريف (رمز ${r.status})`);
  log("✅ تمّ التصريف");
}

/** يستفسر CDP دوريًّا حتى تظهر صفحة workbench أو تنفد المهلة. */
async function waitForWorkbench(timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastErr = "لم يبدأ";
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const targets = await res.json();
      if (targets.some(t => t.type === "page" && /workbench(-dev)?\.html/.test(t.url))) return true;
      lastErr = `لا صفحة workbench بعد (${targets.length} هدفًا)`;
    } catch (e) { lastErr = e.message; }
    await sleep(1500);
  }
  fail(`انتهت مهلة الإقلاع (${timeoutMs / 1000}ث): ${lastErr}`);
}

function launch() {
  // مع `--welcome` نبدأ من ملفّ مستخدم نظيف: محراب يستعيد حالة النافذة المحفوظة، فنافذةٌ
  // جديدة على ملفٍّ قديم تُفتَح **فارغة** لا على صفحة الترحيب. الملفّ النظيف يُعيد سلوك
  // أوّل تشغيل (وهو ما نريد فحصه أصلًا: ما يراه المستخدم أوّل مرّة). قِسنا الحالتين.
  if (has("--welcome")) {
    try { rmSync(join(ARTIFACTS, "user-data"), { recursive: true, force: true }); } catch { /* */ }
  }
  if (!existsSync(join(UP, "out", "main.js")))
    fail("لا مخرَج تصريف في .upstream/vscode/out — شغّل بـ--build أوّلًا");
  const bin = electronBinary();
  mkdirSync(ARTIFACTS, { recursive: true });
  const args = [
    ".", // جذر التطبيق في وضع التطوير = شجرة المصدر نفسها
    `--remote-debugging-port=${PORT}`, "--remote-allow-origins=*",
    // مجلّدا مستخدم/امتدادات معزولان: لا نلوّث ملفّ المستخدم الحقيقيّ ولا نرث إعداداته
    // (وإلّا لاختلف ما نراه عن الافتراضيّ الذي نصمّمه — وهو بيت القصيد).
    `--user-data-dir=${join(ARTIFACTS, "user-data")}`,
    `--extensions-dir=${join(ARTIFACTS, "extensions")}`,
  ];
  // ‏--tabs <ملفّ,ملفّ>: ملفّات إضافيّة. لازمٌ لمِجَسّ إفلات التبويبات (يحتاج ≥2 تبويب،
  // وإلّا فلا حاوية تبويبات أصلًا ويُبلَّغ تخطّيًا بلا أن يقيس شيئًا).
  // **تسبق العيّنة عمدًا:** آخر ملفٍّ يُمرَّر هو الذي يصير المحرّر النشط، ونريد العيّنة
  // العربيّة نشطةً — وإلّا صار المحرّر النشط ملفًّا لاتينيًّا فتُبلَّغ مِجَسّات bidi
  // و[AR-04] «لا سطر عربيّ» بينما العيّنة مفتوحة في تبويبٍ خلفيّ (مقيس).
  // مع `--welcome` لا ملفّ ولا مجلّد إطلاقًا: هي تشغيلة صفحة الترحيب وحدها (انظر أعلاه).
  if (!has("--welcome")) {
    const extra = val("--tabs", "");
    if (extra) for (const f of extra.split(",")) if (f.trim()) args.push(resolve(f.trim()));
    args.push(NOTES_PROBE);
    args.push(FIXTURE);
  }
  // ‏--folder <مسار>: يفتح مجلّدًا معه. لازمٌ لأسطح **الشجرة** (المستكشف، الإعدادات، Git):
  // بلا مجلّد لا تُصيَّر عقدة شجرة واحدة فتُبلَّغ مِجَسّاتها «غير ظاهر» زورًا.
  //
  // **الترتيب مقصود ومقيس:** `--folder-uri` **آخر ما يُمرَّر**. وضعُه قبل مسارٍ موضعيّ
  // يُخرِج النسخة فورًا بالرمز ‎-1‎ **بلا سطر سجلّ واحد** — عطبٌ صامت أضاع منّا وقتًا.
  // عزلناه بالتجربة: `--folder` وحده يعمل، و`--tabs` وحده يعمل، واجتماعهما بالترتيب
  // المقلوب يسقط. (مسار العيّنة الموضعيّ في `args` أعلاه يسبق `--folder-uri` أصلًا.)
  const folder = has("--welcome") ? "" : val("--folder", "");
  if (folder) args.push("--folder-uri", "file:///" + resolve(folder).replace(/\\/g, "/"));
  log(`إطلاق: ${bin.split("\\").pop()} (منفذ ${PORT})`);
  // detached مع --keep: بدونه يموت الطفل بموت المُطلِق، فيصير «أبقِ النسخة» بلا معنى
  // (‏ECONNREFUSED عند أوّل --attach لاحق — أخطأنا فيه حيًّا قبل أن نُصلحه).
  const keep = has("--keep");
  const child = spawn(bin, args, {
    cwd: UP, env: cleanElectronEnv(), stdio: ["ignore", "pipe", "pipe"], detached: keep,
  });
  if (keep) child.unref();
  const logFile = join(ARTIFACTS, "electron.log");
  const tap = d => { try { appendFileSync(logFile, d); } catch { /* */ } };
  child.stdout.on("data", tap);
  child.stderr.on("data", tap);
  child.on("exit", c => { if (c) console.error(`  │ خرجت النسخة برمز ${c} — راجع ${logFile}`); });
  return child;
}

/** يلتقط لقطة الصفحة كاملةً ويكتبها PNG. */
async function shot(cdp, name) {
  mkdirSync(ARTIFACTS, { recursive: true });
  const r = await cdp.cmd("Page.captureScreenshot", { format: "png", captureBeyondViewport: false }, 30000);
  const file = join(ARTIFACTS, `${name}.png`);
  writeFileSync(file, Buffer.from(r.data, "base64"));
  log(`📸 ${file}`);
  return file;
}

async function main() {
  if (has("--build")) compile();

  let child = null;
  const attachOnly = has("--attach");
  if (!attachOnly) {
    child = launch();
    await waitForWorkbench(BOOT_TIMEOUT_MS);
    log("✅ صفحة workbench جاهزة");
  }

  const cdp = await CDP.attach(PORT);
  let rc = 0;
  try {
    // استقرار: بيئة العمل تبني أجزاءها بعد أوّل رسم؛ اللقطة الفوريّة تمسك هيكلًا نصف مبنيّ.
    await sleep(parseInt(val("--settle", "4000"), 10));

    if (has("--eval")) {
      const expr = val("--eval", "1");
      const out = await cdp.evaluate(expr);
      console.log(typeof out === "string" ? out : JSON.stringify(out, null, 2));
    }
    if (has("--shot") || (!has("--eval") && !has("--spec"))) {
      await shot(cdp, val("--shot", "mihrab"));
    }
    if (has("--spec")) {
      process.env.MIHRAB_CDP_PORT = String(PORT);
      const { runAll } = await import("./rtl.spec.mjs");
      const results = await runAll(cdp);
      const ICON = { pass: "✅", fail: "❌", skip: "⏭️ " };
      let p = 0, f = 0, s = 0;
      for (const r of results) {
        console.log(`  ${ICON[r.status]} ${r.name}${r.detail ? " — " + r.detail : ""}`);
        if (r.status === "pass") p++; else if (r.status === "fail") f++; else s++;
      }
      console.log(`─── ${p} نجح، ${f} فشل، ${s} تخطٍّ ───`);
      rc = f ? 1 : 0;
    }
  } finally {
    cdp.close();
    if (child && !has("--keep")) {
      log("إغلاق النسخة");
      // قتل شجرة العمليّات: code.bat يُولّد Electron كحفيد، فقتل cmd وحده يترك النافذة حيّة.
      spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
    } else if (child) {
      log("النسخة تعمل (--keep) — أغلقها يدويًّا أو: node tests/runtime/launch.mjs --attach …");
    }
  }
  return rc;
}

main().then(c => process.exit(c)).catch(e => { console.error("خطأ فادح:", e); process.exit(2); });
