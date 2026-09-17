// مشغّل اختبارات RTL الوقتيّة (L3) — يتّصل بنسخة Mihrab مُطلَقة بالمنفذ ويشغّل التأكيدات.
//
// **العائق (موثَّق):** صدفة الأتمتة لا تُطلق GUI؛ يُطلقه المستخدم/عدّاء ذو جلسة سطح مكتب:
//   Mihrab.exe --remote-debugging-port=9222 --remote-allow-origins=* tests/runtime/fixtures/rtl_fixture.ص
// ثمّ: node tests/runtime/run.mjs [المنفذ]
//
// الخرج: TAP-ish + ملخّص. خرج 0 = لا فشل (التخطّي غير حاجب)، 1 = فشل تأكيد (انحدار).
import { CDP } from "./harness.mjs";
import { runAll } from "./rtl.spec.mjs";

const PORT = parseInt(process.argv[2] || process.env.MIHRAB_CDP_PORT || "9222", 10);

const ICON = { pass: "✅", fail: "❌", skip: "⏭️ " };

async function main() {
  console.log(`═══ L3: اختبارات RTL الوقتيّة (CDP :${PORT}) ═══`);
  let cdp;
  try {
    cdp = await CDP.attach(PORT);
  } catch (e) {
    console.log(`  ⏭️  تعذّر الاتّصال: ${e.message}`);
    console.log("     أطلق Mihrab بـ--remote-debugging-port=" + PORT + " وافتح fixtures/rtl_fixture.ص، ثمّ أعِد.");
    return 0; // لا نسخة = تخطٍّ غير حاجب (لا فشل زائف في CI بلا سطح مكتب)
  }
  let results;
  try {
    // المنفذُ يصل المِجَسّاتِ التي تحتاج **هدفًا آخر** غير صفحة الـworkbench (مستندُ
    // ملاحظات الإصدار يعيش في هدف `vscode-webview:`). `launch.mjs` يضبطه كذلك.
    process.env.MIHRAB_CDP_PORT = String(PORT);
    results = await runAll(cdp);
  } finally {
    cdp.close();
  }
  let p = 0, f = 0, s = 0;
  for (const r of results) {
    console.log(`  ${ICON[r.status]} ${r.name}${r.detail ? " — " + r.detail : ""}`);
    if (r.status === "pass") p++; else if (r.status === "fail") f++; else s++;
  }
  console.log(`─── ${p} نجح، ${f} فشل، ${s} تخطٍّ ───`);
  const strict = /^(1|true|yes)$/i.test(process.env.MIHRAB_L3_STRICT || "");
  // التخطّي «best-effort» (مِجَسّ هشّ) لا يُحجَب حتى في الوضع الصارم؛ غيره يُحجَب صارمًا.
  const sBlocking = results.filter(r => r.status === "skip" && !r.bestEffort).length;
  const sBest = s - sBlocking;
  if (s > 0) {
    if (sBlocking > 0) console.log(`  ⚠️  ${sBlocking} تخطٍّ قد يُخفي انحدارًا — راجع يدويًّا` +
      (strict ? " (صارم: فشل)." : "، أو MIHRAB_L3_STRICT=1 للحجب."));
    if (sBest > 0) console.log(`  ℹ️  ${sBest} تخطٍّ best-effort (مِجَسّ هشّ، مضمون بطبقة أخرى) — لا يحجب.`);
  }
  return (f || (strict && sBlocking)) ? 1 : 0;
}

main().then(c => process.exit(c)).catch(e => { console.error("خطأ فادح:", e); process.exit(2); });
