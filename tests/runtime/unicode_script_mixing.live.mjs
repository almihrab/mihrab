// L3 حيّ [AR-05]: رقعةُ خلط الكتابتَين — على الحزمة المشحونة لا على المصدر.
//
// **لماذا حيًّا وحارسُ L0 يُحاكي القاعدةَ سلفًا.** المحاكاةُ تُثبت أنّ **نصَّ الرقعة** يعني
// ما نقول؛ ولا تُثبت أنّها طُبِّقت على المشحون، ولا أنّ المُصرَّفَ يسلك سلوكَها، ولا أنّ
// الزخرفةَ تُرسَم. فالمقياسُ هنا **عُقَدُ `.unicode-highlight` المرسومةُ في DOM**.
//
// **وأين تُرسَم — قِيس ولم يُفترَض.** ‏Monaco يُصيّر زخارفَ `className` في `.view-overlays`
// عناصرَ مطلقةَ الموضع، **لا داخل `.view-line`**. وأوّلُ صيغةٍ لهذا الملفّ عدّتها داخل
// السطر فأعطت صفرًا **على الحزمتين معًا** — أي أنّ توكيدات «بلا إطار» كانت ستمرّ خضراءَ
// على مِسطرةٍ عمياء. كشفه شاهدُ التفعيل الموجَب، وهو سببُ وجوده.
//
// **ذراعان لأنّ الصفرَ وحدَه لا يميّز.** ذراعُ العَرَض: ملفٌّ فيه المعرّفاتُ العربيّة وحدَها ⇒ **صفر**.
// وذراعُ الحماية: ملفٌّ فيه أسماءٌ تخلط كتابتَين حقًّا ⇒ **موجب**. الأولى وحدَها تمرّ لو
// أُطفئ الإبرازُ كلُّه؛ والثانيةُ هي التي تمنع ذلك.
//
// **والمساحةُ موثوقة عمدًا** — بخلاف `unicode_guard.live.mjs` الذي يُقلع بـ
// `--disable-workspace-trust`. في غير الموثوقة يصير `nonBasicASCII` مُفعَّلًا فيُبرَز كلُّ
// محرفٍ غير-ASCII، وهو عَرَضٌ آخرُ لا تمسّه هذه الرقعة. والمقيسُ هنا حالُ البلاغ:
// مجلّدٌ موثوقٌ، و`includeStrings` افتراضُه `true` (‏editorOptions.ts:4387) فالسلاسلُ تُبرَز
// والتعليقاتُ وحدَها تُخفى — ولذلك **لا محرفَ ملتبسٌ في تعليقات العيّنتين**.
//
// الاستعمال: node tests/runtime/unicode_script_mixing.live.mjs
//   ‏MIHRAB_EXE=<مسار> يوجّهه إلى حزمةٍ أخرى (لقياس ذراع «قبل» على المثبَّت).
// خرج 0 = نجح · 1 = فشل تأكيد · 2 = خطأ تشغيليّ (لا حزمة/لا إقلاع).
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { sleep, attachAllPages } from "./harness.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const EXE = process.env.MIHRAB_EXE
  || join(ROOT, ".upstream", "VSCode-win32-x64", "Mihrab.exe");
const KEEP = process.argv.includes("--keep");

let failed = 0;
const ok = (cond, name, detail = "") => {
  if (cond) console.log(`  ✅ ${name}`);
  else { failed++; console.log(`  ❌ ${name}${detail ? "\n       " + detail : ""}`); }
};

if (!existsSync(EXE)) { console.error(`❌ لا حزمة مشحونة: ${EXE}`); process.exit(2); }

// ذراعُ العَرَض: المعرّفاتُ العربيّة كما تُكتَب في مصدر الحقيقة — قِيَمًا عاريةً في yaml، وهي
// حيث وقعت الإطاراتُ التي بُلِّغ عنها. ولا حرفَ لاتينيٍّ في أيّ اسمٍ منها.
const ARM_SYMPTOM = [
  "vocab:",
  "  - ثابت: حقل_اسم",
  "  - ثابت: حقل_وسائط",
  "  - ثابت: خط_مائل",
  "  - ثابت: 40_تعابير",
  "  - ثابت: اكتب_ذاكرة",
  "",
].join("\n");

// ذراعُ الحماية: كلُّ سطرٍ اسمٌ يخلط كتابتَين حقًّا. لو صار صفرًا فقد أُسقطت الحمايةُ
// لا الضجيج — وهي الحالةُ التي لا يمسكها عدُّ الصفر وحدَه.
const ARM_GUARD = [
  "vocab:",
  "  - ثابت: pcb_ديناميّ",
  "  - ثابت: صادx",
  "",
].join("\n");

const tmp = mkdtempSync(join(tmpdir(), "mihrab-ar05-"));
const userData = join(tmp, "user-data");
const wsDir = join(tmp, "مشروع");
mkdirSync(join(userData, "User"), { recursive: true });
mkdirSync(wsDir, { recursive: true });
// المساحةُ موثوقةٌ بإطفاء الميزة لا بـ`--disable-workspace-trust`: الرايةُ تُلغي المسارَ
// كلَّه، والإعدادُ يترك `isWorkspaceTrusted()` صادقةً كما في مجلّدٍ وثق به المستخدم.
writeFileSync(join(userData, "User", "settings.json"),
  JSON.stringify({ "security.workspace.trust.enabled": false }, null, 2), "utf8");

/** ‏نفسُ فخِّ `launch.mjs`: بيئةُ Electron مضيفٍ تجعل الطفلَ يعمل بوضع Node بلا نافذة. */
function cleanEnv() {
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  for (const k of Object.keys(env)) if (k.startsWith("VSCODE_")) delete env[k];
  return env;
}

/** يفتح ملفًّا في حزمةٍ جديدة ويعيد `{أسطر، نص، إطارات}` بعد استقرار العدد. */
async function measure(file, port) {
  const proc = spawn(EXE, [
    `--remote-debugging-port=${port}`, "--remote-allow-origins=*",
    `--user-data-dir=${userData}`, "--skip-release-notes", "--disable-updates",
    "--new-window", file,
  ], { detached: false, stdio: "ignore", env: cleanEnv() });

  // أرضيّةٌ زمنيّةٌ قبل قبول الاستقرار: الإبرازُ يُحسَب في عاملٍ منفصلٍ ويُطبَّق مهدَّأً،
  // فقراءتان متطابقتان مبكّرتان تعنيان «لم يُحسَب بعدُ» لا «استقرّ». وقعنا فيه حيًّا.
  const FLOOR_MS = 8000;
  const t0 = Date.now();
  let best = null, prev = null, same = 0;
  for (let i = 0; i < 90; i++) {
    await sleep(500);
    let wins = [];
    try { wins = await attachAllPages(port); } catch { continue; }
    try {
      for (const w of wins) {
        const r = await w.cdp.evaluate(`(() => {
          const lines = Array.from(document.querySelectorAll(".monaco-editor .view-line"));
          return {
            أسطر: lines.length,
            نص: lines.map(l => (l.textContent || "").trim()).join(" | "),
            إطارات: document.querySelectorAll(".monaco-editor .unicode-highlight").length,
          };
        })()`).catch(() => null);
        if (r && r.أسطر > 0) { best = r; break; }
      }
    } finally { for (const w of wins) w.cdp.close(); }
    const sig = best ? `${best.أسطر}:${best.إطارات}` : "-";
    same = sig === prev ? same + 1 : 0;
    prev = sig;
    if (best && same >= 2 && Date.now() - t0 >= FLOOR_MS) break;
  }
  try { proc.kill(); } catch { /* */ }
  await sleep(1500);
  return best || { أسطر: 0, نص: "", إطارات: 0 };
}

(async () => {
  console.log(`▶ [AR-05] خلطُ الكتابتَين — ${EXE}`);
  const fSym = join(wsDir, "معرّفات.yaml");
  const fGuard = join(wsDir, "مختلطة.yaml");
  writeFileSync(fSym, ARM_SYMPTOM, "utf8");
  writeFileSync(fGuard, ARM_GUARD, "utf8");

  const guard = await measure(fGuard, 9338);
  // (١) شاهدُ التفعيل الموجَب — يسبق كلَّ توكيدٍ سالب.
  ok(guard.أسطر > 0, "ذراعُ الحماية مُصيَّرة", JSON.stringify(guard));
  ok(guard.إطارات >= 1,
     `خلطُ الكتابتَين ما زال مُبرَزًا (${guard.إطارات} إطارًا) — شاهدُ تفعيل`,
     "صفرٌ هنا يعني إمّا إبرازًا مُطفأً كلَّه فالتوكيدُ التالي بلا معنى، وإمّا رقعةً "
     + "وُسِّعت فأسقطت كشفَ الانتحال. الأسطرُ: " + guard.نص);

  const sym = await measure(fSym, 9339);
  // (٢) العَرَضُ المُبلَّغ عنه.
  ok(sym.أسطر > 0, "ذراعُ العَرَض مُصيَّرة", JSON.stringify(sym));
  ok(sym.إطارات === 0,
     "المعرّفاتُ العربيّة بلا إطارٍ أصفر",
     `عُدَّ ${sym.إطارات} إطارًا — الرقعةُ لم تبلغ المشحون. الأسطرُ: ${sym.نص}`);

  if (!KEEP) { try { rmSync(tmp, { recursive: true, force: true }); } catch { /* */ } }
  console.log(failed ? `\n❌ ${failed} تأكيدًا فشل` : "\n✅ كلُّ التأكيدات نجحت");
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error("❌ " + e.message); process.exit(2); });
