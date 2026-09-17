// تأكيدات RTL الوقتيّة (L3) — مشتقّة من docs/rtl/rtl-inventory.md، هندسيّة حتميّة بسماحية.
import { editorGeometry, suggestGap, findWidget, welcomeHeader, explorerSadIcon, titlebarAppicon, editorLetterpress, editorBidi, tabsDropRtl, chromeTypography, arabicInkMetrics, welcomePattern, langRuleProof, bidiLabels, bidiAudit, directionalGlyphs, unicodeHighlight, activateSadTab, activateWelcomeTab,
         bidiPanels, glyphOrder, breadcrumbsBar, key, MOD, escape, sleep, insertText, focusEditor,
openDiffFromScm, confirmDialog, walkthroughAlign, waitFor, resetWorkbench, editorHover,
openExtensionDetails, dialogButtons, statusbarOrder, discardUntitled, pinActiveTab, recoverWelcomeTab,
bidiSweep, documentLangDir, editorInkMetrics, focusOrder, horizontalAnchorRtl, findInputControls, revealLineEndRtl, restoredHorizontalPositionRtl, inputDirectionFollowsContent, releaseNotesRendering } from "./harness.mjs";

// جزء من الجملة الاستعاريّة (يطابق نصّ العنوان الفرعيّ الفعليّ في الترويسة).
// ⚠️ مقترن بـWELCOME_TAGLINE في build/patch_welcome_rtl.py: إعادة صياغة تُسقِط هذا الجزء تكسر المِجَسّ.
const WELCOME_TAGLINE_MARKER = "تكتب فيه";
// الليل المِحرابيّ #0F1C24 = خلفيّة سمة محراب الداكنة (getComputedStyle بلا مسافات).
const MIHRAB_NIGHT_RGB = "rgb(15,28,36)";

const TOL = 3;         // سماحية بكسل للمحاذاة
const GAP_TOL = 3;     // فجوة الاقتراحات المقبولة (0 مثاليّ)

// نتيجة موحّدة
const pass = (name, detail) => ({ name, status: "pass", detail });
const fail = (name, detail) => ({ name, status: "fail", detail });
// bestEffort: تخطٍّ لا يُحجَب حتى في الوضع الصارم (مِجَسّ هشّ بطبيعته — إدخال CDP في RTL).
const skip = (name, detail, bestEffort = false) => ({ name, status: "skip", detail, bestEffort });

// تأكيدات هندسيّة (بلا إدخال) — من قراءة تخطيط واحدة.
export function geometryAssertions(geo) {
  const out = [];
  const ed = geo.editor;
  const mid = ed ? ed.l + ed.w / 2 : 0;

  out.push(geo.dir === "rtl"
    ? pass("قشرة RTL", "workbench dir=rtl")
    : fail("قشرة RTL", `dir=${geo.dir} (متوقَّع rtl)`));

  // غيابُ المحرّر **فشلٌ في تشغيلة المحرّر وتخطٍّ في تشغيلة الترحيب.** التمييز بالحالة لا
  // بالرغبة: إن كانت صفحةُ الترحيب معروضةً فهذه تشغيلةُ ترحيبٍ عمدًا (لا ملفّ يُمرَّر فيها
  // أصلًا)، فالإنذار عن «لا محرّر» ضجيجٌ يُحمِّر تشغيلةً سليمة ويُعلِّم القارئَ تجاهُلَ الأحمر.
  // وإن لم تكن معروضة فالمحرّر مفقودٌ فعلًا وذلك انحدار.
  if (!ed) return [...out, geo.welcomePresent
    ? skip("المحرّر موجود", "تشغيلة ترحيب (لا ملفّ) — الهندسة تُقاس في تشغيلة المحرّر", true)
    : fail("المحرّر موجود", "لا .monaco-editor — هل فُتِح ملفّ؟")];
  out.push(pass("المحرّر موجود", `[${ed.l},${ed.r}] عرض ${ed.w}`));

  // الخريطة المصغّرة يسارًا (م2)
  out.push(geo.minimap && geo.minimap.l <= ed.l + TOL
    ? pass("الخريطة المصغّرة يسارًا", `الحافّة اليسرى ${geo.minimap.l}`)
    : fail("الخريطة المصغّرة يسارًا", geo.minimap ? `left=${geo.minimap.l} (متوقَّع ≈${ed.l})` : "لا خريطة"));

  // المزراب/الأرقام يمينًا (م1)
  out.push(geo.gutter && geo.gutter.l > mid && geo.gutter.r >= ed.r - TOL
    ? pass("المزراب يمينًا", `[${geo.gutter.l},${geo.gutter.r}]`)
    : fail("المزراب يمينًا", geo.gutter ? `[${geo.gutter.l},${geo.gutter.r}] (متوقَّع أقصى اليمين)` : "لا مزراب"));

  out.push(geo.lineNumbers
    ? (geo.lineNumbers.l > mid
      ? pass("أرقام الأسطر يمينًا", `left=${geo.lineNumbers.l}`)
      : fail("أرقام الأسطر يمينًا", `left=${geo.lineNumbers.l} (متوقَّع > ${Math.round(mid)})`))
    : skip("أرقام الأسطر يمينًا", "لا عنصر أرقام مرئيّ"));

  // الشريط العموديّ يمينًا بجانب الأرقام (تعديل المستخدم م5)
  //
  // **عرضُ صفرٍ ليس موضعًا.** كان الفحصُ يتخطّى حين **يغيب** العنصرُ من DOM وحدَها، وVS Code
  // لا يحذفه: يُبقيه ويجعل عرضَه ‎0‎ ما دام المحتوى لا يفيض عموديًّا. وعنصرٌ بعرض صفرٍ
  // رقعتُه عند **أصل** الصندوق القابل للتمرير — أي عند حافّته اليسرى — فيُقرأ «الشريطُ
  // يسارًا» ويُبلَّغ انحدارًا لا وجودَ له. قِسناه: `left=369` و`عرض=0` والصندوق يبدأ عند
  // ‎369‎ بالضبط؛ وحين يفيض المحتوى فعلًا يُقاس `[1044,1058]` — يمينًا كما طُلب في م5.
  // فالتخطّي هنا هو ما نواه كاتبُ الفحص، ورسالتُه مكتوبةٌ منذ البداية ولم تكن تُبلَغ.
  out.push(!geo.scrollbarV || !geo.scrollbarV.w
    ? skip("الشريط العموديّ يمينًا", "غير مرئيّ (لا تمرير عموديّ)")
    : (geo.scrollbarV.l > mid
      ? pass("الشريط العموديّ يمينًا", `[${geo.scrollbarV.l},${geo.scrollbarV.r}] عرض ${geo.scrollbarV.w}`)
      : fail("الشريط العموديّ يمينًا", `left=${geo.scrollbarV.l} عرض=${geo.scrollbarV.w} (متوقَّع يمينًا) · الأسطر تنتهي عند ${geo.linesRight} · الصندوق ${JSON.stringify(geo.scrollableBox)}`)));

  // مسطرة النظرة **مع الشريط العموديّ** (م2، CSS13 — نُقِض ما كان هنا).
  //
  // كان هذا التأكيدُ يشترطها في النصف الأيسر، لأنّ الرقعةَ كانت تنقل العمودَ الملاحيَّ كلَّه
  // إلى الحافّة الأماميّة. وسقط ذلك في مراجعة microsoft/vscode: الشريطُ العموديُّ يبقى يمينًا
  // لأنّ السطرَ اليمينيَّ يحجز عرضَه بـ`padding-right` منبعيًّا، والمسطرةُ **تشرح الشريط**
  // فلا معنى لفصلها عنه — وقد رُئي أثرُ الفصل: شريطٌ معتِمٌ فوق أطراف السطور الطويلة.
  //
  // فالمقياسُ اليومَ نسبةٌ لا نصفٌ: المسطرةُ تلاصق الشريطَ. عتبةُ ‎4px‎ تسمح بحدٍّ أو ظلٍّ
  // ولا تسمح بانزياحٍ حقيقيّ. وشرطُ وجود الشريط أوّلًا شاهدُ تفعيل: بلا شريطٍ مرئيٍّ
  // (لا تمرير عموديّ) لا مشهودَ عليه، فيُتخطّى بدل أن يمرّ على العمى.
  out.push(!geo.overviewRuler
    ? skip("مسطرة النظرة مع الشريط العموديّ", "غير مرئيّة")
    : (!geo.scrollbarV || !geo.scrollbarV.w
      ? skip("مسطرة النظرة مع الشريط العموديّ", "لا شريطَ عموديًّا مرئيًّا — لا مشهودَ عليه")
      : (Math.abs(geo.overviewRuler.l - geo.scrollbarV.l) <= 4
        ? pass("مسطرة النظرة مع الشريط العموديّ",
          `المسطرة ${geo.overviewRuler.l} = الشريط ${geo.scrollbarV.l}`)
        : fail("مسطرة النظرة مع الشريط العموديّ",
          `المسطرة ${geo.overviewRuler.l} ≠ الشريط ${geo.scrollbarV.l} — انفصلا، والمسطرةُ تشرح الشريط`))));

  // منطقة المحتوى بين الخريطة (يسارًا) والمزراب (يمينًا).
  // نقيس **إطار المحتوى** (‏editor-scrollable) لا طبقةَ `.view-lines`: الأخيرة عرضُها عرضُ
  // أطول سطر ويسارُها سالب كلّما فاض السطر — سلوك RTL صحيح كان يُسقِط هذا التأكيد زورًا.
  const cv = geo.contentView || geo.content;
  out.push(cv
    ? ((geo.minimap ? cv.l >= geo.minimap.r - TOL : true) && geo.gutter && cv.l < geo.gutter.l
      ? pass("المحتوى بين الخريطة والمزراب", `[${cv.l},${cv.r}]`)
      : fail("المحتوى بين الخريطة والمزراب", `المحتوى ${cv.l} لا يقع بين الخريطة ${geo.minimap?.r} والمزراب ${geo.gutter?.l}`))
    : skip("المحتوى بين الخريطة والمزراب", "لا إطار محتوى"));

  // شريط الأنشطة يمينًا (القشرة RTL)
  out.push(geo.activityBar
    ? (geo.activityBar.l > mid
      ? pass("شريط الأنشطة يمينًا", `left=${geo.activityBar.l}`)
      : fail("شريط الأنشطة يمينًا", `left=${geo.activityBar.l} (متوقَّع > ${Math.round(mid)})`))
    : skip("شريط الأنشطة يمينًا", "غير مرئيّ"));

  // اتّجاه السطر RTL (م1، Monaco per-line)
  out.push(geo.firstLineDir === "rtl"
    ? pass("اتّجاه السطر RTL", "view-line direction=rtl")
    : fail("اتّجاه السطر RTL", `direction=${geo.firstLineDir} (متوقَّع rtl)`));

  // سمة محراب الداكنة مطبَّقة: خلفيّة المحرّر = الليل المِحرابيّ #0F1C24 = rgb(15,28,36).
  // best-effort: تخطٍّ لا فشل إن اختلفت (قد يبدّل المستخدم السمة يدويًّا؛ الافتراضيّة محراب الداكنة).
  if (geo.editorBg) {
    const bg = geo.editorBg.replace(/\s+/g, "");
    out.push(bg === MIHRAB_NIGHT_RGB
      ? pass("سمة محراب الداكنة مطبَّقة", `خلفيّة المحرّر ${geo.editorBg}`)
      : skip("سمة محراب الداكنة مطبَّقة", `خلفيّة ${geo.editorBg} ≠ الليل المِحرابيّ (سمة أخرى؟)`, true));
  }

  return out;
}

// تأكيدات تفاعليّة (تحتاج إدخالًا) — الاقتراحات والبحث.
export async function interactionAssertions(cdp) {
  const out = [];

  // **قياس الترحيب أوّلًا — قبل أيّ نقر.** مِجَسّ فجوة الاقتراحات ينقر داخل منطقة المحرّر
  // على إحداثيّةٍ عمياء؛ وحين تكون صفحة الترحيب هي المحرّر النشط فقد تقع النقرة على بطاقة
  // جولة فتنتقل الصفحة إلى تفاصيلها، فتختفي حاوية الفئات وتُبلَّغ ترويسة الترحيب «غير
  // موجودة» بعد أن كانت موجودة قبل ثوانٍ. رصدناه حيًّا: المِجَسّ يجدها ثمّ لا يجدها.
  // ترحيب: شعار القوس + الجملة الاستعاريّة (best-effort — يحتاج صفحة Get Started مفتوحة).
  try {
    // صفحة الترحيب تبويبٌ خلفيّ بعد فتح ملفّ، فكان المِجَسّ يُبلَّغ «غير مفتوحة» دائمًا.
    // نُنشِّطها بالنقر (نافذة واحدة، حتميّ) ثمّ نُعيد تبويب العيّنة في نهاية القسم.
    let w = await welcomeHeader(cdp);
    // **التنشيطُ وحده لا يكفي — التصيير يحتاج مهلة.** تشغيلةٌ ثانية على النسخة نفسها
  // تخطّت ثلاثةَ تأكيدات ترحيبٍ رغم وجود التبويب: نُشِّط وقُرئ في اللحظة نفسها،
  // ومحرّرُ التبويب غير النشط لا يُصيَّر — فقرأنا DOM قبل أن يوجد.
  if (!w || !w.present) { if (await recoverWelcomeTab(cdp) && await activateWelcomeTab(cdp)) { await sleep(1500); w = await welcomeHeader(cdp); } }
    if (!w || !w.present) {
      out.push(skip("ترحيب: الشعار والجملة",
        "لا تبويب ترحيب (شغّل بـ--welcome لملفّ مستخدم نظيف)", true));
    } else {
      const okMark = w.markVisible;
      const okSub = !!w.subtitle && w.subtitle.includes(WELCOME_TAGLINE_MARKER);
      if (okMark && okSub) out.push(pass("ترحيب: الشعار والجملة", `شعار ${w.markWidth}px + الجملة الاستعاريّة`));
      else out.push(fail("ترحيب: الشعار والجملة",
        `شعار مرئيّ=${okMark} (عرض ${w.markWidth})، الجملة=${JSON.stringify((w.subtitle || "").slice(0, 24))}`));
    }
  } catch (e) { out.push(skip("ترحيب: الشعار والجملة", "تعذّر: " + e.message, true)); }

  // [القاعدة 19] الزخرفة النجميّة: خافتة، مُبلَّطة، محجوبة، وبلا نزّ تحت الترويسة.
  try {
    let w = await welcomePattern(cdp);
    // **التنشيطُ وحده لا يكفي — التصيير يحتاج مهلة.** تشغيلةٌ ثانية على النسخة نفسها
  // تخطّت ثلاثةَ تأكيدات ترحيبٍ رغم وجود التبويب: نُشِّط وقُرئ في اللحظة نفسها،
  // ومحرّرُ التبويب غير النشط لا يُصيَّر — فقرأنا DOM قبل أن يوجد.
  if (!w || !w.present) { if (await recoverWelcomeTab(cdp) && await activateWelcomeTab(cdp)) { await sleep(1500); w = await welcomePattern(cdp); } }
    if (!w || !w.present) out.push(skip("ترحيب: الزخرفة النجميّة",
      "لا تبويب ترحيب (شغّل بـ--welcome لملفّ مستخدم نظيف)", true));
    else if (!w.hasTile) out.push(fail("ترحيب: الزخرفة النجميّة", "بلا بلاطة SVG"));
    else if (!(w.opacity > 0 && w.opacity <= 0.12)) out.push(fail("ترحيب: الزخرفة النجميّة",
      `شفافيّة ${w.opacity} خارج المدى الخافت (0, 0.12]`));
    else if (!w.hasMask) out.push(fail("ترحيب: الزخرفة النجميّة", "بلا قناع تلاشٍ ⇒ حافّة حادّة/نزّ"));
    else out.push(pass("ترحيب: الزخرفة النجميّة",
      `شفافيّة ${w.opacity}، مُقنَّعة، نزّ ${w.bleedPx}px تحت الترويسة (مُذاب بالقناع)`));
  } catch (e) { out.push(skip("ترحيب: الزخرفة النجميّة", "تعذّر: " + e.message, true)); }

  // [القاعدة 32] محاذاة الجولة «ابدأ في ٩٠ ثانية» — **بلاغُ مستخدم لا مسحُ ماسح.**
  // العطبُ الذي أفلت من كلّ تأكيداتنا: الترتيب سليم والمحاذاة يسار. الحكم بالأثر:
  // أوراقُ نصٍّ متفاوتةُ الأطوال تشترك في حافّةٍ يمنى واحدة ⇒ الفقرة تبدأ من اليمين.
  try {
    let a = await walkthroughAlign(cdp);
    // **التنشيطُ وحده لا يكفي — التصيير يحتاج مهلة.** تشغيلةٌ ثانية على النسخة نفسها
  // تخطّت ثلاثةَ تأكيدات ترحيبٍ رغم وجود التبويب: نُشِّط وقُرئ في اللحظة نفسها،
  // ومحرّرُ التبويب غير النشط لا يُصيَّر — فقرأنا DOM قبل أن يوجد.
  if (!a || !a.present) { if (await recoverWelcomeTab(cdp) && await activateWelcomeTab(cdp)) { await sleep(1500); a = await walkthroughAlign(cdp); } }
    if (!a || !a.present) out.push(skip("ترحيب: محاذاة الجولة",
      "لا جولة محراب مفتوحة (شغّل بـ--welcome لملفّ مستخدم نظيف)", true));
    else if (!a.widths || a.widths < 2) out.push(skip("ترحيب: محاذاة الجولة",
      `أوراق متطابقة الطول (${a.leaves}) — لا تُميّز يمينًا من يسار`, true));
    else if (a.rights < a.lefts) out.push(pass("ترحيب: محاذاة الجولة",
      `${a.leaves} ورقة: حوافّ يمنى ${a.rights} < يسرى ${a.lefts} ⇒ تبدأ من اليمين`));
    else out.push(fail("ترحيب: محاذاة الجولة",
      `النصّ ملصَقٌ يسارًا: حوافّ يمنى ${a.rights} ≥ يسرى ${a.lefts} في ${a.leaves} ورقة`));
  } catch (e) { out.push(skip("ترحيب: محاذاة الجولة", "تعذّر: " + e.message, true)); }



  // فجوة الاقتراحات = صفر (الإصلاح الحاسم rtl19)
  try {
    let s = await suggestGap(cdp);
    if (!s || !s.visible) s = await suggestGap(cdp); // إعادة محاولة واحدة (تقلّل تخطّي التذبذب)
    if (!s || !s.visible) out.push(skip("فجوة الاقتراحات = صفر", "لم تظهر الودجة (لا إكمالات؟)", true));
    else if (s.caretLeft == null) out.push(skip("فجوة الاقتراحات = صفر", "الودجة غير مُجاورة للمؤشّر (إدخال CDP هشّ) — مضمونة أيضًا بعلامة L2", true));
    else if (Math.abs(s.gap) <= GAP_TOL) out.push(pass("فجوة الاقتراحات = صفر", `يمين الودجة ${s.widgetRight} = المؤشّر ${s.caretLeft} (فجوة ${s.gap})`));
    else out.push(fail("فجوة الاقتراحات = صفر", `فجوة ${s.gap}px (يمين ${s.widgetRight} ≠ مؤشّر ${s.caretLeft}) — انحدار! · يسار الودجة ${s.widgetLeft} · الصندوق ${JSON.stringify((await editorGeometry(cdp)).scrollableBox)}`));
  } catch (e) { out.push(skip("فجوة الاقتراحات = صفر", "تعذّر: " + e.message, true)); }

  // ودجة البحث لأعلى-اليسار (مرآة rtl20)
  try {
    let f = await findWidget(cdp);
    if (!f || !f.visible) f = await findWidget(cdp); // إعادة محاولة واحدة
    if (!f || !f.visible) out.push(skip("البحث أعلى-اليسار", "لم تظهر ودجة البحث"));
    else {
      // قرب الحافّة اليسرى فعلًا (المرآة تضعه عند maxRight≈2×شريط+خريطة ≈ 11% من العرض)، لا
      // مجرّد النصف الأيسر — عتبة 25% تمسك المرآة الجزئيّة (مثلًا left=400) دون false-pass.
      const bound = f.editorLeft + f.editorWidth * 0.25;
      if (f.left < bound) out.push(pass("البحث أعلى-اليسار", `left=${f.left} (< ${Math.round(bound)}، قرب الحافّة اليسرى)`));
      else out.push(fail("البحث أعلى-اليسار", `left=${f.left} (≥ ${Math.round(bound)}) — لم يُعكَس لأعلى-اليسار!`));
    }
  } catch (e) { out.push(skip("البحث أعلى-اليسار", "تعذّر: " + e.message)); }

  // مقابضُ حقل البحث لا تركب النصّ (بلاغُ مستخدمٍ حيّ ‎2026-09-10‎ عن جزء البحث).
  //
  // في RTL تُنقَل المقابضُ إلى الحافّة اليسرى، والمساحةُ المحجوزة لها في المنبع **تضييقُ
  // الحقل** لا حشوٌ — فإن بقي التضييقُ في الجهة الأخرى وقعت المقابضُ فوق بداية النصّ.
  // القياسُ تقاطعُ مستطيلين، ويجري على كلّ حقلِ بحثٍ ظاهرٍ في اللحظة.
  try {
    const inputs = await findInputControls(cdp);
    if (!inputs || !inputs.length) out.push(skip("مقابض حقل البحث لا تركب النصّ", "لا حقل بحثٍ ظاهر", true));
    else {
      // سماحيةُ التجاور: حافّتان متلاصقتان تُقرآن أحيانًا بتقاطع بكسلٍ واحد بعد التقريب.
      // والعطبُ المقيس كان ‎66px‎ (عرضَ المقابض كاملًا) لا بكسلًا.
      const bad = inputs.filter(i => i.overlap > TOL);
      if (bad.length) out.push(fail("مقابض حقل البحث لا تركب النصّ",
        bad.map(i => `${i.host}: المقابض [${i.controls}] تتقاطع مع الحقل [${i.field}] بـ${i.overlap}px`).join(" · ")));
      else out.push(pass("مقابض حقل البحث لا تركب النصّ",
        inputs.map(i => `${i.host}: مقابض [${i.controls}] ${i.controlsOnLeadingSide ? "يسارَ" : "بجانب"} الحقل [${i.field}]`).join(" · ")));
    }
  } catch (e) { out.push(skip("مقابض حقل البحث لا تركب النصّ", "تعذّر: " + e.message, true)); }

  // أيقونة ملفّ ص في المستكشف تحمل القوس (best-effort — يحتاج مجلّدًا فيه ملفّ .ص مفتوحًا).
  try {
    const e = await explorerSadIcon(cdp);
    if (!e || !e.present) {
      out.push(skip("أيقونة ملفّ ص (المستكشف)", "لا ملفّ .ص ظاهر (افتح مجلّدًا فيه ملفّ ص)", true));
    } else {
      out.push(e.isSad
        ? pass("أيقونة ملفّ ص (المستكشف)", "القوس مطبَّق على .ص")
        : fail("أيقونة ملفّ ص (المستكشف)", `خلفيّة «${(e.bg || "").slice(0, 40)}» ليست أيقونة القوس`));
    }
  } catch (e) { out.push(skip("أيقونة ملفّ ص (المستكشف)", "تعذّر: " + e.message, true)); }

  // رأس التطبيق: أيقونة شريط العنوان تحمل شعار القوس (code-icon). حاضرة دائمًا مع شريط عنوان مخصّص.
  try {
    const a = await titlebarAppicon(cdp);
    if (!a || !a.present) out.push(skip("رأس التطبيق: شعار القوس", "لا .window-appicon (شريط عنوان أصيل؟)", true));
    else if (!a.wired) out.push(fail("رأس التطبيق: شعار القوس", `مرتبط=false bg=${JSON.stringify(a.bg)}`));
    else if (!a.visible) out.push(skip("رأس التطبيق: شعار القوس", "مرتبط لكن غير مرئيّ (شريط مطويّ/ملء شاشة؟)", true));
    else out.push(pass("رأس التطبيق: شعار القوس", "أيقونة شريط العنوان = code-icon (المحتوى مضمون بـL2)"));
  } catch (e) { out.push(skip("رأس التطبيق: شعار القوس", "تعذّر: " + e.message, true)); }

  // خلفية المحرّر الفارغ: letterpress تحمل القوس (best-effort — مرئيّة فقط بلا محرّر مفتوح).
  try {
    const l = await editorLetterpress(cdp);
    if (!l || !l.present) out.push(skip("خلفية المحرّر: القوس", "لا .letterpress (لا مجموعة محرّر فارغة)", true));
    else if (l.wired) out.push(pass("خلفية المحرّر: القوس", "letterpress مرتبطة (المحتوى مضمون بـL2)"));
    else out.push(fail("خلفية المحرّر: القوس", `bg=${JSON.stringify(l.bg)} ليست letterpress`));
  } catch (e) { out.push(skip("خلفية المحرّر: القوس", "تعذّر: " + e.message, true)); }

  // bidi المحرّر (#24): النصّ العربيّ في السطر مُحاذًى يمينًا (اتّجاه RTL فعليّ) — يحتاج الـfixture.
  try {
    const b = await editorBidi(cdp);
    if (!b || !b.present) out.push(skip("bidi: النصّ العربيّ يمينًا", "لا سطر عربيّ (افتح rtl_fixture.ص)", true));
    else if (!b.hasText) out.push(skip("bidi: النصّ العربيّ يمينًا", "السطر بلا نصّ قابل للقياس", true));
    else {
      // مقارنة الفجوتين (مستقلّة عن حجم النافذة/التمرير/الخطّ، بلا ثابت سحريّ — مراجعة Amelia):
      // النصّ أقرب لليمين منه لليسار ⇒ محاذاة RTL. ترفض الوسط (فجوتان متساويتان) واليسار.
      const rightGap = b.lineRight - b.textRight, leftGap = b.textLeft - b.lineLeft;
      const rightAligned = rightGap < leftGap;
      if (b.dir === "rtl" && rightAligned) out.push(pass("bidi: النصّ العربيّ يمينًا", `النصّ [${b.textLeft},${b.textRight}] أقرب ليمين السطر [${b.lineLeft},${b.lineRight}] (فجوة يمنى ${rightGap} < يسرى ${leftGap})`));
      else out.push(fail("bidi: النصّ العربيّ يمينًا", `dir=${b.dir}، النصّ [${b.textLeft},${b.textRight}] في سطر [${b.lineLeft},${b.lineRight}] (متوقَّع محاذاة يمينًا)`));
    }
  } catch (e) { out.push(skip("bidi: النصّ العربيّ يمينًا", "تعذّر: " + e.message, true)); }

  // التمرير الأفقيّ: المحرّر يفتح عند **بداية** الأسطر لا عند طرفها الفارغ.
  //
  // الصندوقُ بعرض أعرض سطر والأسطرُ اليمينيّة مُحاذاةٌ يمينَه، فـ`scrollLeft = 0` يعرض الفراغ
  // بعد نهايات الأسطر القصيرة — وهو ما يبدأ به المحرّر وما تحمله حالةُ عرضٍ حُفِظت قبل أن
  // يفيض السطر. القياسُ حتميّ: `scrollLeft` عند أقصاه ⇒ النافذة عند الحافّة اليمنى.
  // بلا فيضٍ أفقيّ لا مشهودَ عليه (النافذة أوسع من أطول سطر) فيُتخطّى صراحةً.
  try {
    const h = await horizontalAnchorRtl(cdp);
    if (!h || !h.present) out.push(skip("التمرير الأفقيّ: يفتح عند بداية الأسطر", "لا محرّر", true));
    else if (!h.rtl) out.push(skip("التمرير الأفقيّ: يفتح عند بداية الأسطر", "المحرّر ليس RTL (ملفّ لاتينيّ نشط)", true));
    else if (h.maxScrollLeft <= TOL) out.push(skip("التمرير الأفقيّ: يفتح عند بداية الأسطر",
      `لا فيض أفقيّ (عرض التمرير ${h.scrollW} ≤ الإطار ${h.viewportW}) — لا مشهودَ عليه`));
    else if (Math.abs(h.scrollLeft - h.maxScrollLeft) <= TOL) out.push(pass("التمرير الأفقيّ: يفتح عند بداية الأسطر",
      `scrollLeft=${h.scrollLeft} = أقصاه ${h.maxScrollLeft} (تمرير ${h.scrollW} · إطار ${h.viewportW}) ⇒ النافذة على الحافّة اليمنى`));
    else out.push(fail("التمرير الأفقيّ: يفتح عند بداية الأسطر",
      `scrollLeft=${h.scrollLeft} ≠ أقصاه ${h.maxScrollLeft} (تمرير ${h.scrollW} · إطار ${h.viewportW}) — النافذة على الطرف الفارغ، وبدايةُ السطر تحتاج جرَّ المسطرة`));
  } catch (e) { out.push(skip("التمرير الأفقيّ: يفتح عند بداية الأسطر", "تعذّر: " + e.message, true)); }

  // كشفُ نهايةِ السطر: النافذةُ تتبع المؤشّرَ إلى الطرف الفارغ حين يطلبه القارئُ صراحةً.
  //
  // المرساةُ تُبقي النافذةَ عند بداية الأسطر، لكنّ **نهاية** أعرضِ سطرٍ تقع عند الحافّة
  // اليسرى — أي عند `scrollLeft = 0` بالضبط، وهو الرقمُ الذي تحمله أيضًا الحالاتُ التي لا
  // تعني موضعًا (حالةُ عرضٍ مستعادة، كشفُ مدًى يمتدّ سطورًا). فمن يخلط بينهما يبتلع الكشفَ
  // ويترك المؤشّرَ خارج الشاشة. مقيس: `End` على أعرض سطرٍ ⇒ المؤشّرُ داخل إطار المحتوى.
  try {
    const r = await revealLineEndRtl(cdp);
    if (!r || !r.present) out.push(skip("كشف نهاية السطر يتبع المؤشّر", "لا سطر عربيّ مصيَّر", true));
    else if (!r.rtl) out.push(skip("كشف نهاية السطر يتبع المؤشّر", "المحرّر ليس RTL (ملفّ لاتينيّ نشط)", true));
    else if (!r.moved) out.push(skip("كشف نهاية السطر يتبع المؤشّر", "لم يتحرّك المؤشّر — لم يصل النقرُ/المفتاح إلى المحرّر", true));
    else if (r.inside) out.push(pass("كشف نهاية السطر يتبع المؤشّر",
      `المؤشّر [${r.cursor}] داخل الإطار [${r.viewport}] · scrollLeft=${r.scrollLeft}`));
    else out.push(fail("كشف نهاية السطر يتبع المؤشّر",
      `المؤشّر [${r.cursor}] خارج الإطار [${r.viewport}] (scrollLeft=${r.scrollLeft}) — الكشفُ ابتُلع والكتابةُ تجري حيث لا يُرى`));
  } catch (e) { out.push(skip("كشف نهاية السطر يتبع المؤشّر", "تعذّر: " + e.message, true)); }

  // اتّجاهُ حقل الإدخال يتبع محتواه، وافتراضُه اتّجاهُ التطبيق (رقعة النواة 035).
  //
  // محرابٌ عربيٌّ أصلًا واللاتينيّةُ فيه لاحقة: الحقلُ الفارغ — وما لا محرفَ قويَّ فيه —
  // يقف يمينًا. وهذا ما لا يعطيه `dir="auto"` وحدَه: ارتدادُه المنصوصُ عليه هو اليسار.
  try {
    const d = await inputDirectionFollowsContent(cdp);
    const NAME = "اتّجاه حقل الإدخال يتبع محتواه";
    if (!d || !d.present) out.push(skip(NAME, "لا حقلَ بحثٍ في أيٍّ من السطحين", true));
    else {
      // **ودجةُ بحث المحرّر هي السطحُ ذو الأنياب**: جذرُ `.monaco-editor` يساريٌّ بنيةً، فالفارغُ
      // والمحايدُ فيه يقفان يسارًا بلا الرقعة. وجزءُ البحث يرث اليمينيَّ من القشرة فيُقاس
      // عليه اللاتينيُّ وحدَه حكمًا، وتُقرأ سِمةُ `dir` شاهدًا على أنّ الرقعةَ كتبت شيئًا أصلًا.
      const wrong = [], seen = [];
      const judge = (label, one, full) => {
        if (!one) { seen.push(`${label}: غائب`); return; }
        if (!one.typed) { seen.push(`${label}: لم يصل النصّ`); return; }
        if (full) {
          if (one.empty !== "rtl") { wrong.push(`${label}/فارغ=${one.empty}`); }
          if (one.neutral !== "rtl") { wrong.push(`${label}/أرقامٌ ورموز=${one.neutral}`); }
          if (one.arabic !== "rtl") { wrong.push(`${label}/عربيّ=${one.arabic}`); }
        }
        if (one.latin !== "ltr") { wrong.push(`${label}/لاتينيّ=${one.latin}`); }
        // السِّمةُ لا يكتبها إلّا رقعةُ ‎035‎؛ غيابُها يعني أنّ الحقلَ لم يُلمَس.
        const attrs = one.attrs || [];
        if (attrs.some(a => a !== "rtl" && a !== "ltr")) { wrong.push(`${label}/سِمةُ dir غائبة (${attrs.join(",")})`); }
        seen.push(`${label}: ${full ? `فارغ=${one.empty} · أرقامٌ ورموز=${one.neutral} · عربيّ=${one.arabic} · ` : ""}لاتينيّ=${one.latin}`);
      };
      judge("ودجة المحرّر", d.findWidget, true);
      judge("جزء البحث", d.searchView, false);
      if (!d.findWidget || !d.findWidget.typed) {
        out.push(skip(NAME, `لم يُقَس السطحُ الحاسم (ودجةُ بحث المحرّر) — ${seen.join(" · ") || "لا قياس"}`, true));
      } else if (wrong.length) {
        out.push(fail(NAME, `${wrong.join(" · ")} (المتوقَّع: الافتراضُ يمينًا، واللاتينيُّ وحدَه يسارًا)`));
      } else {
        out.push(pass(NAME, seen.join(" · ")));
      }
    }
  } catch (e) { out.push(skip("اتّجاه حقل الإدخال يتبع محتواه", "تعذّر: " + e.message, true)); }

  // إفلات التبويبات (#18، رقعة mihrab-rtl-tabdrop): حارس اتّجاه الحاوية + انعكاسها الفيزيائيّ.
  try {
    const t = await tabsDropRtl(cdp);
    if (!t || !t.present) out.push(skip("إفلات التبويبات: حاوية RTL", "لا حاوية تبويبات بـ≥2 تبويب (افتح ملفّين+)", true));
    else if (t.dir !== "rtl") out.push(fail("إفلات التبويبات: حاوية RTL", `direction=${t.dir} (متوقَّع rtl) — الحارس لن يُفعَّل!`));
    else if (!t.firstIsPhysicallyRight) out.push(fail("إفلات التبويبات: حاوية RTL",
      `dir=rtl لكنّ تبويب DOM الأوّل ليس أقصى اليمين (first.left=${t.firstLeft} ≤ last.left=${t.lastLeft}) — انهار افتراض انعكاس الـflex!`));
    else out.push(pass("إفلات التبويبات: حاوية RTL",
      `${t.tabCount} تبويب، direction=rtl، تبويب DOM الأوّل أقصى اليمين (first.left=${t.firstLeft} > last.left=${t.lastLeft})`));
  } catch (e) { out.push(skip("إفلات التبويبات: حاوية RTL", "تعذّر: " + e.message, true)); }

  // **يجري بعد مِجَسّات حالةِ الفتح عمدًا:** هذا المِجَسّ يضع موضعًا **ويحفظه**، فلو سبق
  // مِجَسَّ المرساة لقرأ ذاك إزاحةً وأبلغ فشلًا صنعناه نحن (وقع فعلًا في تشغيلة).
  // موضعُ القارئ الأفقيّ يُستعاد كما تركه.
  //
  // المرساةُ تفتح عند بداية الأسطر، والقارئُ إن حرّك الموضعَ فهو له — وحفظُه بين الجلسات
  // يحتاج **مسافةً من بداية الأسطر** لا `scrollLeft` مقيسًا من الطرف الآخر، وإلّا وقع في
  // مكانٍ آخر عند أوّل تكبيرٍ أو تغييرِ حجم. مقيس: التبويبُ يُغلَق ويُعاد فتحُه فتعود المسافة.
  try {
    const r = await restoredHorizontalPositionRtl(cdp);
    if (!r || !r.present) out.push(skip("موضع القارئ الأفقيّ يُستعاد", "لا محرّر", true));
    else if (!r.activated) out.push(skip("موضع القارئ الأفقيّ يُستعاد", "تبويبُ العيّنة ليس نشطًا — لكنّا أغلقنا تبويبًا آخر", true));
    else if (!r.rtl) out.push(skip("موضع القارئ الأفقيّ يُستعاد", "المحرّر ليس RTL (ملفّ لاتينيّ نشط)", true));
    else if (!r.overflow) out.push(skip("موضع القارئ الأفقيّ يُستعاد", `لا فيض أفقيّ (أقصاه ${r.max}) — لا مشهودَ عليه`));
    else if (!r.moved) out.push(skip("موضع القارئ الأفقيّ يُستعاد", "لم تُحرّك العجلةُ الموضعَ — لم يصل الإدخال", true));
    else if (!r.reopened) out.push(skip("موضع القارئ الأفقيّ يُستعاد", "لم يعد تبويبُ العيّنة بعد إغلاقه — لا مقارنةَ صحيحة", true));
    else if (!r.geometryMoved) out.push(skip("موضع القارئ الأفقيّ يُستعاد",
      `لم تتحرّك الحافّةُ بين الحفظ والاستعادة (${r.placedMax}→${r.restoredMax}) — لم يُختبَر الحقلُ في الحالة التي وُجِد لأجلها`, true));
    else if (r.kept) out.push(pass("موضع القارئ الأفقيّ يُستعاد",
      `وُضِع على ${r.placedGap}px من بداية الأسطر، وعاد على ${r.restoredGap}px بعد إغلاق التبويب وتغيُّرِ عرضِ الصندوق (${r.placedMax}→${r.restoredMax}) وإعادةِ فتحه`));
    else out.push(fail("موضع القارئ الأفقيّ يُستعاد",
      `وُضِع على ${r.placedGap}px من بداية الأسطر وعاد على ${r.restoredGap}px (أقصاه ${r.placedMax}→${r.restoredMax}) — الموضعُ ضاع أو انزاح مع الحافّة`));
  } catch (e) { out.push(skip("موضع القارئ الأفقيّ يُستعاد", "تعذّر: " + e.message, true)); }

  // **يجري أخيرًا عمدًا:** يفتح محرّرَ ملاحظاتٍ ويغلقه ويبدّل التبويبَ النشط، فما بعده
  // يرث حالةً لم يطلبها. ويقيس ما لا تبلغه طبقةُ CSS أصلًا: مستندُ الـwebview مستقلٌّ.
  try {
    const NAME = "تصيير ملاحظات الإصدار يمينيًّا";
    const n = await releaseNotesRendering(cdp, Number(process.env.MIHRAB_CDP_PORT || 9222));
    if (!n || !n.present) out.push(skip(NAME, "لا تبويبَ للعيّنة (release_notes_probe.md) — أُطلِقت النسخةُ بلا المُطلِق؟", true));
    else if (!n.opened) out.push(skip(NAME, "لم يُفتَح محرّرُ الملاحظات — لم يصل الأمرُ من اللوحة", true));
    else if (!n.rendered) out.push(skip(NAME, "الـwebview بلا مستندٍ مُصيَّر بعد", true));
    else {
      const wrong = [], seen = [];
      if (n.dir !== "rtl") { wrong.push(`المستند dir=${n.dir}`); }
      else { seen.push("المستند rtl"); }

      // الجدول: المحاذاةُ منطقيّةٌ (`start` لا `left`)، **والخانةُ الأولى في الطرف اليمينيّ**
      // من الجدول — والحكمان معًا لأنّ الأوّلَ وحدَه يمرّ على قاعدةٍ لا تصل إلى العنصر.
      if (n.thAlign !== "start") { wrong.push(`عنوانُ الجدول text-align=${n.thAlign} (المتوقَّع start)`); }
      else if (n.thBox && n.tableBox && n.thBox[1] < n.tableBox[1] - 4) {
        wrong.push(`خانةُ الجدول الأولى ليست في الطرف اليمينيّ (${n.thBox[1]} < ${n.tableBox[1]})`);
      } else { seen.push(`الجدول: start · الخانةُ الأولى تنتهي عند ${n.thBox && n.thBox[1]} = طرفُ الجدول`); }

      if (n.olDir !== "rtl") { wrong.push(`القائمةُ المرقّمة direction=${n.olDir}`); }
      else { seen.push("القائمةُ المرقّمة rtl"); }

      // الاقتباس: الشريطُ على جهة **البداية** (اليمين هنا) وصفرٌ على المقابلة.
      const start = parseFloat(n.bqStart || "0"), end = parseFloat(n.bqEnd || "0");
      if (!(start > 0 && end === 0)) { wrong.push(`شريطُ الاقتباس يمين=${n.bqStart} يسار=${n.bqEnd} (المتوقَّع عرضٌ يمينًا وصفرٌ يسارًا)`); }
      else { seen.push(`شريطُ الاقتباس يمينًا ${n.bqStart}`); }

      // كتلةُ الشيفرة: سطرٌ لاتينيٌّ يبدأ من حافّة كتلته. بلا العزل يُلصَق بالطرف المقابل
      // (قِيس: ‎181px‎ فراغًا قبل أمرِ صَدَفة).
      if (n.preText && n.preBox && n.preText.mada) {
        const gap = n.preText.mada[0] - n.preBox[0];
        if (gap > 40) { wrong.push(`كتلةُ الشيفرة مُلصَقةٌ بالطرف المقابل — فراغٌ ${gap}px قبل سطرٍ لاتينيّ`); }
        else { seen.push(`كتلةُ الشيفرة تبدأ على ${gap}px من حافّتها`); }
      }

      // المحايداتُ في الأطراف: يُقارَن الترتيبُ البصريُّ بالمصدر حرفًا بحرف.
      for (const [label, src, vis] of [["شيفرةٌ سطريّة", n.codeSrc, n.codeVisual], ["رابط", n.linkSrc, n.linkVisual]]) {
        if (!src) { seen.push(`${label}: لا عيّنة`); }
        else if (src.trim() !== (vis || "").trim()) { wrong.push(`${label} ينقلب: «${src.trim()}» يُقرأ «${(vis || "").trim()}»`); }
        else { seen.push(`${label}: «${src.trim()}» كما هو`); }
      }

      if (wrong.length) { out.push(fail(NAME, wrong.join(" · "))); }
      else { out.push(pass(NAME, seen.join(" · "))); }
    }
  } catch (e) { out.push(skip("تصيير ملاحظات الإصدار يمينيًّا", "تعذّر: " + e.message, true)); }


  return out;
}

// ─────────────── تأكيدات التصميم العربيّ (طباعة القشرة + الزخرفة + قياس التشكيل) ───────────────
export async function designAssertions(cdp) {
  const out = [];

  // [AR-03] مكدّس خطّ القشرة: `:lang(ar)` غلب قاعدة المنبع **حيًّا** لا على الورق.
  try {
    const t = await chromeTypography(cdp);
    if (!t || !t.present) out.push(skip("AR-03: مكدّس خطّ القشرة", "لا .monaco-workbench", true));
    // وضع التطوير (رسائل غير مخبوزة) نصّه إنجليزيّ فعلًا ⇒ lang=en **صحيح** لا انحدار.
    // لا نُفشِل هنا ولا نتساهل: الآليّة نفسها تُبرهَن بمِجَسّ langRuleProof أدناه (يقود lang=ar).
    else if (t.lang !== "ar" && !t.baked) out.push(skip("AR-03: مكدّس خطّ القشرة",
      `وضع تطوير (رسائل غير مخبوزة) ⇒ lang=${t.lang} صحيح؛ الآليّة تُفحَص بـlangRuleProof`, true));
    else if (t.lang !== "ar") out.push(fail("AR-03: مكدّس خطّ القشرة",
      `بناء مخبوز لكنّ html lang=${t.lang} (متوقَّع ar) — رُقعة mihrab-html-lang لم تسرِ!`));
    else {
      // الوجه العربيّ الصريح المتوقَّع لمنصّة التشغيل الحاليّة (نفس خريطة حارس L0).
      const FACE = { windows: "Tahoma", mac: "SF Arabic", linux: "Noto Sans Arabic" };
      const want = FACE[t.platform];
      if (!want) out.push(skip("AR-03: مكدّس خطّ القشرة", `منصّة غير معروفة (${t.platform})`, true));
      else if (!t.monacoFont.includes(want)) out.push(fail("AR-03: مكدّس خطّ القشرة",
        `--monaco-font=«${t.monacoFont}» بلا «${want}» — قاعدة المنبع غلبت قاعدتنا!`));
      else if (!/Kawkab Mono/.test(t.monospaceFont)) out.push(fail("AR-03: الوجه الأحاديّ في القشرة",
        `--monaco-monospace-font=«${t.monospaceFont}» بلا Kawkab Mono`));
      else out.push(pass("AR-03: مكدّس خطّ القشرة",
        `${t.platform}/lang=ar · متناسب «${t.monacoFont}» · أحاديّ «${t.monospaceFont}»`));
    }
  } catch (e) { out.push(skip("AR-03: مكدّس خطّ القشرة", "تعذّر: " + e.message, true)); }

  // [AR-03] برهان آليّة القاعدة: نقود `lang` من en إلى ar حيًّا ونطالب بتبدّل المكدّس.
  // **ثنائيّ الاتّجاه عمدًا:** الصيغة السابقة كانت تضبط ar وتتوقّع تبدّلًا، فتنجح في وضع
  // التطوير (يبدأ من en) و**تفشل زورًا على البناء المشحون** حيث lang=ar مخبوزة أصلًا.
  try {
    const r = await langRuleProof(cdp);
    if (!r || !r.present) out.push(skip("AR-03: برهان :lang(ar) حيًّا", "لا قشرة", true));
    else if (!r.changed) out.push(fail("AR-03: برهان :lang(ar) حيًّا",
      `en→ar لم يبدّل المكدّس (بقي «${r.after.font}») — القاعدة لا تُطابِق أو يغلبها المنبع`));
    else out.push(pass("AR-03: برهان :lang(ar) حيًّا",
      `en→ar بدّل المكدّس: «${r.before.font}» ⇒ «${r.after.font}» (اللغة الأصليّة ${r.originalLang})`));
  } catch (e) { out.push(skip("AR-03: برهان :lang(ar) حيًّا", "تعذّر: " + e.message, true)); }

  // [TY-02] حبرُ العربيّة داخل سطر **المحرّر** — حيث يسري `editor.lineHeight` فعلًا.
  // كانت العتبةُ القديمةُ `tashkeelRatio > 1` تقيس **القشرة** وترصد القصَّ بعد وقوعه؛ وهذه
  // تقيس السطحَ الصحيح، وتطلب **هامشًا** لا انعدامَ قصّ، وتقيس **الطرفَين الموثَّقَين في
  // الاشتقاق** (الألفُ بهمزةٍ فوق U+0623 عند ‎+1.265em‎، وتنوينُ الكسر U+064D عند ‎−0.533em‎)
  // لا عيّنةً أرخى منهما.
  try {
    const m = await editorInkMetrics(cdp);
    if (!m || !m.present) out.push(skip("TY-02: حبر العربيّة داخل سطر المحرّر", "لا سطرَ محرّرٍ ظاهر", true));
    else {
      // ‏MARGIN **بدلُ تفاوتِ المنصّات لا نصفُ هامشٍ نظريّ**. كان تعليلُه: «مدى الحبر
      // ‏‎1.798em‎ في سطرٍ ‎1.95em‎ ⇒ هامشٌ ‎7.8٪‎، ونصفُه عتبةً» — وذلك سندٌ ساقط: ‎1.798‎
      // قِيست من كونتوراتٍ منفردةٍ لا تركّب علامةً على قاعدة، والمركَّبُ المقيسُ حيًّا
      // ‏‎2.683em‎ (‏`tests/dx/arabic_ink.measured.json`). فبقيت العتبةُ ‎3.9٪‎ **بمعنًى
      // آخر**: مقدارُ ما نسمح به لتفاوت التنعيم والتقريب بين المنصّات — وهو نفسُه المقسومُ
      // عليه في اشتقاق ‎2.8‎: ‏`2.683 ÷ 0.961 = 41.88 ⇒ 42px ⇒ 42/15 = 2.8`.
      // ‏**والقياسُ بالأسوأ لا بالمتوسّط**: `tashkeel` أصغرُ بـ‎14٪‎ من `extremes`، ولا
      // يُشتقُّ منه شيء — «مَبدأٌ» كلمةٌ عاديّةٌ والكسرتانِ عاديّة، وسطرٌ يسعُهما معًا.
      const MARGIN = 0.039;
      const ratio = Math.max(m.extremesRatio, m.tashkeelRatio);
      const margin = 1 - ratio;
      const d = `سطرُ المحرّر ${m.lineHeightPx}px (${m.lineHeightEm}em) · حبرُ الأطراف ` +
        `${m.extremes}px والمُشكَّلة ${m.tashkeel}px ⇒ نسبة ${ratio} (هامش ${(margin * 100).toFixed(1)}٪` +
        `، كلفة التشكيل +${m.tashkeelExtraPx}px)`;
      if (ratio > 1) {
        out.push(fail("TY-02: حبر العربيّة داخل سطر المحرّر",
          d + " — يتجاوز السطر ⇒ اقتطاعٌ واقع. ارفع editor.lineHeight (الأرضيّة المقيسة 2.683em)"));
      } else if (margin < MARGIN) {
        out.push(fail("TY-02: حبر العربيّة داخل سطر المحرّر",
          d + ` — الهامش دون ${(MARGIN * 100).toFixed(1)}٪: القصُّ لم يقع بعدُ ويقع بأوّل محرفٍ أطول.` +
          " ارفع editor.lineHeight في mihrab-shell (الأرضيّة المقيسة 2.683em)"));
      } else out.push(pass("TY-02: حبر العربيّة داخل سطر المحرّر", d));
    }
  } catch (e) { out.push(skip("TY-02: حبر العربيّة داخل سطر المحرّر", "تعذّر: " + e.message, true)); }

  // [TY-03] أحاديّةُ العرض **مقيسةً في المحرّر**: نظيرُ إنذارِ المستخدم، من جهة الحارس.
  try {
    const m = await editorInkMetrics(cdp);
    if (!m || !m.present) out.push(skip("TY-03: أحاديّة عرض العربيّة في المحرّر", "لا سطرَ محرّرٍ ظاهر", true));
    else {
      const w = m.widths;
      const d = `M=${w.M} · ا=${w["ا"]} · م=${w["م"]} · ص=${w["ص"]} (تفاوت ${(m.monoSpread * 100).toFixed(1)}٪) — «${m.fontFamily}»`;
      if (m.monoSpread > 0.02) out.push(fail("TY-03: أحاديّة عرض العربيّة في المحرّر",
        d + " — الوجهُ الجاري متناسبٌ لا أحاديُّ العرض: تكذب المسطرةُ والمحاذاةُ والتحديدُ الكتليّ بلا خطأٍ واحد"));
      else out.push(pass("TY-03: أحاديّة عرض العربيّة في المحرّر", d));
    }
  } catch (e) { out.push(skip("TY-03: أحاديّة عرض العربيّة في المحرّر", "تعذّر: " + e.message, true)); }

  // [TY-02 مساعِد] حبرُ القشرة — سطحٌ آخرُ بمقبضٍ آخر. ارتفاعُ سطر القشرة مثبَّتٌ منبعيًّا
  // ولا يمسّه `editor.lineHeight`، فالإحالةُ هنا إلى ورقتِنا لا إلى ذلك الإعداد.
  try {
    const m = await arabicInkMetrics(cdp);
    if (!m || !m.present) out.push(skip("طباعة: حبر التشكيل في القشرة", "لا قشرة", true));
    else {
      const d = `حبر المُشكَّلة ${m.tashkeel.height}px ÷ سطر القشرة ${m.lineHeightPx}px = ${m.tashkeelRatio}` +
        ` (لاتينيّ ${m.latinRatio}، كلفة التشكيل +${m.tashkeelExtraPx}px)`;
      if (m.tashkeelRatio > 1) out.push(fail("طباعة: حبر التشكيل في القشرة",
        d + " — يتجاوز سطرَ القشرة ⇒ اقتطاع. المقبضُ هنا `line-height` في patches/mihrab-rtl.css لا editor.lineHeight"));
      else out.push(pass("طباعة: حبر التشكيل في القشرة", d));
    }
  } catch (e) { out.push(skip("طباعة: حبر التشكيل في القشرة", "تعذّر: " + e.message, true)); }

  // [VA-02] لغةُ المستند ودورُ اتّجاهه — **حارسٌ دائمٌ لا برهانُ آليّة**. سمةٌ واحدةٌ تحمل
  // الوصولَ (نطقُ قارئات الشاشة، WCAG 3.1.1) وكلَّ طباعتِنا العربيّة (القاعدة ٢٠ معلَّقةٌ
  // بـ`:lang(ar)`) — وقد سقطت مرّةً صامتةً واجتازت حارسَي L0 وL2 معًا.
  // ويُقسَم إلى توكيدَين: عنوانُ التوكيد أوّلُ نصفِ ثانيةٍ من التشخيص، وتوكيدٌ يحمل ثلاثةَ
  // ادّعاءاتٍ يرسل المطوّرَ يفتّش في السليم حين يسقط على الثالث.
  try {
    const L = await documentLangDir(cdp);
    if (!L || !L.present) out.push(skip("VA-02أ: لغة المستند واتّجاهه", "لا قشرة", true));
    else {
      // **الاتّجاهُ يُفحَص دائمًا**: لا علاقةَ له بخبز اللغة، وربطُه بـ`baked` كان يجعل
      // الحارسَ «الدائم» يتخطّى نفسَه في كلّ تشغيلِ تطوير — أي في أكثر التشغيلات.
      if (L.dir !== "rtl" || L.workbenchDir !== "rtl") {
        out.push(fail("VA-02أ: لغة المستند واتّجاهه",
          `‏dir غير rtl (html=${L.dir}، workbench=${L.workbenchDir}) — الاتّجاهُ يورَّث منهما إلى Shadow DOM والنوافذ المساعِدة`));
      } else if (!L.baked) {
        out.push(skip("VA-02أ: لغة المستند واتّجاهه",
          `‏dir=rtl سليم؛ وlang=${L.lang} صحيحةٌ في وضع التطوير (رسائل غير مخبوزة)`, true));
      } else if (L.lang !== "ar") {
        out.push(fail("VA-02أ: لغة المستند واتّجاهه",
          `‏html lang=${L.lang} في بناءٍ مخبوز — تسقط معه القاعدة ٢٠ كلُّها ونطقُ قارئ الشاشة (WCAG 3.1.1)`));
      } else {
        out.push(pass("VA-02أ: لغة المستند واتّجاهه", `‏lang=ar · html dir=rtl · workbench dir=rtl`));
      }
    }
  } catch (e) { out.push(skip("VA-02أ: لغة المستند واتّجاهه", "تعذّر: " + e.message, true)); }

  // [VA-02ب] **برهانُ تطبيقٍ لا كتابة.** الفحصُ النصّيُّ على اسم المكدّس يكرّر AR-03 ولا
  // يضيف؛ والبرهانُ الحقيقيُّ أنّ الوجهَ الجاري **أحاديُّ العرض للعربيّة** — وهو ما ينكسر
  // بالضبط لو مات محدِّدُ اللغة وسقط المكدّسُ إلى خطّ نظامٍ متناسب.
  try {
    const L = await documentLangDir(cdp);
    if (!L || !L.present) out.push(skip("VA-02ب: الوجه المحزوم مطبَّقٌ فعلًا", "لا قشرة", true));
    else if (L.arabicWidth === null || !L.charWidths) {
      out.push(skip("VA-02ب: الوجه المحزوم مطبَّقٌ فعلًا", "تعذّر القياس (بلا canvas)", true));
    } else {
      const d = `مكدّس «${L.monospaceFont}» · عرضُ «نصاب_الفضة» ${L.arabicWidth}px · ` +
        `تفاوتُ المحارف ${(L.charSpread * 100).toFixed(1)}٪`;
      if (L.charSpread > 0.02) out.push(fail("VA-02ب: الوجه المحزوم مطبَّقٌ فعلًا",
        d + " — الوجهُ الجاري متناسب: المكدّسُ مكتوبٌ ولم يُطبَّق (محدِّدُ اللغة قد يكون مات صامتًا)"));
      else if (!/Kawkab Mono/.test(L.monospaceFont)) out.push(fail("VA-02ب: الوجه المحزوم مطبَّقٌ فعلًا",
        d + " — الوجهُ أحاديُّ العرض لكنّه ليس الوجهَ المحزوم"));
      else out.push(pass("VA-02ب: الوجه المحزوم مطبَّقٌ فعلًا", d));
    }
  } catch (e) { out.push(skip("VA-02ب: الوجه المحزوم مطبَّقٌ فعلًا", "تعذّر: " + e.message, true)); }

  // [VA-03] ترتيبُ التركيز في تخطيطٍ معكوس: التركيزُ يتبع DOM لا البصر، فحيثما كان القلبُ
  // بصريًّا محضًا يقفز قفزاتٍ لا يفسّرها البصر. ونفحص أشدَّ الأسطح استعمالًا بلوحة المفاتيح.
  for (const [name, sel] of [["شريط الأنشطة", ".part.activitybar .composite-bar"],
                             ["أداة البحث", ".editor-widget.find-widget"],
                             ["شريط الحالة", ".part.statusbar"]]) {
    try {
      const f = await focusOrder(cdp, sel);
      if (!f || !f.present) out.push(skip(`VA-03: ترتيب التركيز — ${name}`, "غيرُ ظاهرٍ الآن", true));
      else if (f.count < 2) out.push(skip(`VA-03: ترتيب التركيز — ${name}`,
        `عنصرٌ واحدٌ أو لا شيء (${f.count}) — لا ترتيبَ يُفحَص`, true));
      else if (f.violations.length) out.push(fail(`VA-03: ترتيب التركيز — ${name}`,
        `التركيزُ يقفز يسارًا في تخطيطٍ يُقرأ يمينًا: ${f.violations.slice(0, 3).join(" · ")}` +
        ` (${f.count} عنصرًا في ${f.rows} صفًّا)`));
      else out.push(pass(`VA-03: ترتيب التركيز — ${name}`,
        `${f.count} عنصرًا في ${f.rows} صفًّا — التسلسلُ يتبع البصر (يمينًا ⇐ يسارًا)`));
    } catch (e) { out.push(skip(`VA-03: ترتيب التركيز — ${name}`, "تعذّر: " + e.message, true)); }
  }

  // [TY-07] مسحُ مزجٍ عامّ — يقلب العلاقةَ من «اكتشِف ثمّ عالِج» إلى «امنع الانحدارَ ابتداءً».
  // ثلاثون محدِّدًا مكتوبًا يدويًّا لا تنتهي مطاردتُها: تنتهي دورةٌ وتبدأ أخرى مع كلّ مزامنة،
  // والمستخدمُ هو من يكتشف الباقي (القاعدة ٣٢ نجت من ثلاثين توكيدًا حتّى أبلغ عنها إنسان).
  try {
    const s = await bidiSweep(cdp);
    if (!s || !s.present) out.push(skip("TY-07: مسح المزج العامّ", "لا قشرة", true));
    else if (!s.checked) out.push(skip("TY-07: مسح المزج العامّ",
      `لا نصَّ لاتينيًّا مرئيًّا في حاويةٍ RTL (فُحِص ${s.scanned}) — لا حكم`, true));
    else if (s.flaggedTotal) {
      // **الاقتطاعُ يُعلَن.** عرضُ خمسةٍ من سبعةَ عشرَ بلا قولِ ذلك يجعل المطوّرَ يُصلِح
      // خمسةً ويظنّ السطحَ نظيفًا — وهو «الحدُّ الصامت» الذي يمنعه المستودعُ في L2.
      const shown = s.flagged.map((f) => `«${f.text}» في ${f.selector} (bidi=${f.bidi})`).join(" · ");
      const hidden = s.flaggedTotal > s.flagged.length ? ` (وأُخفي ${s.flaggedTotal - s.flagged.length})` : "";
      out.push(fail("TY-07: مسح المزج العامّ",
        `${s.flaggedTotal} من ${s.checked} نصًّا تنقلب أطرافُه: ${shown}${hidden}`));
    } else out.push(pass("TY-07: مسح المزج العامّ",
      `${s.checked} نصًّا لاتينيًّا في حاويات RTL — كلُّها تُعرَض بترتيبها (مقيسًا بموضع أوّل محرفٍ وآخره)` +
      (s.truncated ? ` ⚠️ توقّف المسحُ عند ${s.visited} عقدة (سقفٌ) — التغطيةُ ناقصة` : "")));
  } catch (e) { out.push(skip("TY-07: مسح المزج العامّ", "تعذّر: " + e.message, true)); }


  // [القاعدة 21] المحايدات: تسمياتٌ محتواها يحدّد اتّجاهه (نقاط «‎…‎» ومسارات مختلطة).
  try {
    const b = await bidiLabels(cdp);
    if (!b) out.push(skip("اتّجاه التسميات المحايدة (bidi)", "تعذّر القياس", true));
    else if (b.wrong.length) out.push(fail("اتّجاه التسميات المحايدة (bidi)",
      `ليست plaintext: ${b.wrong.join("، ")} — ستقفز النقاط/الشُّرَط إلى الطرف الخاطئ`));
    else if (!b.found.length) out.push(skip("اتّجاه التسميات المحايدة (bidi)",
      `لا هدف ظاهر (${b.missing.length} غائبًا — افتح ملفًّا/صفحة الترحيب)`, true));
    else out.push(pass("اتّجاه التسميات المحايدة (bidi)",
      `${b.found.length}/${b.checked} plaintext${b.missing.length ? `، ${b.missing.length} غير ظاهر` : ""}`));
  } catch (e) { out.push(skip("اتّجاه التسميات المحايدة (bidi)", "تعذّر: " + e.message, true)); }

  // [القاعدة 22] الرموز الاتّجاهيّة — تُقاس بالأثر: تدرّج المثلّث مع العمق، وجهة الأدلّة،
  // وانعكاس الأسهم. يحتاج **مجلّدًا مفتوحًا** (‏--folder) وإلّا فلا شجرة تُقاس ⇒ تخطٍّ صريح.
  try {
    const d = await directionalGlyphs(cdp);
    const flipped = Object.entries(d.arrows || {}).filter(([, v]) => v && v.startsWith("matrix(-1"));
    const present = Object.entries(d.arrows || {}).filter(([, v]) => v);
    const bad = present.filter(([, v]) => !v.startsWith("matrix(-1")).map(([k]) => k);
    if (!d || d.depths < 2) {
      out.push(skip("الرموز الاتّجاهيّة (القاعدة 22)",
        `لا شجرة بعمقين على الشاشة (${d ? d.depths : 0}) — شغّل بـ--folder ووسّع مجلّدًا`, true));
    } else if (d.step <= 0) {
      out.push(fail("الرموز الاتّجاهيّة (القاعدة 22)",
        `مثلّث الشجرة لا يتدرّج مع العمق (خطوة ${d.step}px) — يصطفّ في عمود واحد بينما ` +
        `تتدرّج التسميات وحدها`));
    } else if (d.indSide !== null && d.indSide > 40) {
      out.push(fail("الرموز الاتّجاهيّة (القاعدة 22)",
        `أدلّة التشجير على بُعد ${d.indSide}px من حافّة الصفّ — مرساة على الحافّة المقابلة`));
    } else if (bad.length) {
      out.push(fail("الرموز الاتّجاهيّة (القاعدة 22)", `أسهم غير معكوسة: ${bad.join("، ")}`));
    } else {
      out.push(pass("الرموز الاتّجاهيّة (القاعدة 22)",
        `تدرّج المثلّث ${d.step}px/مستوى، الأدلّة على بُعد ${d.indSide}px من حافّة الصفّ، ` +
        `${flipped.length}/${present.length} سهمًا معكوسًا (${5 - present.length} غير ظاهر)`));
    }
  } catch (e) { out.push(skip("الرموز الاتّجاهيّة (القاعدة 22)", "تعذّر: " + e.message, true)); }

  // [AR-04] إبراز يونيكود: صفرُ علامات في ملفّ ص. يُقاس **بالأثر** (عقد .unicode-highlight)
  // لا بقراءة الإعداد. في مساحةٍ موثوقة لا يُثبت الصفرُ شيئًا (الإبراز مُعطَّل أصلًا) ⇒ نُصرّح.
  try {
    const u = await unicodeHighlight(cdp);
    if (!u || !u.present) out.push(skip("إبراز يونيكود [AR-04]", "لا محرّر مفتوح", true));
    else if (!u.arabic) out.push(skip("إبراز يونيكود [AR-04]", "لا سطر عربيّ في المحرّر", true));
    else if (u.marks) out.push(fail("إبراز يونيكود [AR-04]",
      `${u.marks} علامة إبراز على محارف عربيّة — إعفاء [sad] لم يصل`));
    else out.push(pass("إبراز يونيكود [AR-04]",
      `0 علامة على نصّ عربيّ${u.restricted ? " (مساحة مقيَّدة — القياس حاسم)" : " (مساحة موثوقة — القياس مؤيِّد لا حاسم)"}`));
  } catch (e) { out.push(skip("إبراز يونيكود [AR-04]", "تعذّر: " + e.message, true)); }

  // مسح bidi شامل — استكشافيّ لا حاجز: يُبلِّغ عن أوراق النصّ المعرَّضة التي ما زالت
  // `normal`. لا يُفشِل (المسح مرهون بما هو مفتوح على الشاشة الآن، والقائمة تُقرأ لا تُقاس)،
  // لكنّه المصدر الوحيد الذي نشتقّ منه أهداف القاعدة 21 — قياسًا لا تخمينًا.
  try {
    const a = await bidiAudit(cdp);
    if (!a) out.push(skip("مسح bidi شامل", "تعذّر القياس", true));
    else if (!a.atRisk.length) out.push(pass("مسح bidi شامل",
      `${a.scanned} ورقة نصّ، ${a.exposed} معرَّضة، 0 بلا معالجة`));
    else out.push(skip("مسح bidi شامل",
      `${a.exposed}/${a.scanned} معرَّضة، ${a.atRisk.length} توقيعًا بلا معالجة: ` +
      a.atRisk.slice(0, 6).map(g => `${g.sig}×${g.n}«${g.sample}»`).join(" | "), true));
  } catch (e) { out.push(skip("مسح bidi شامل", "تعذّر: " + e.message, true)); }

  // أعِد تبويب العيّنة العربيّة نشطًا: قسمُ الترحيب قد يكون بدّله، وما بعده يقيس نصًّا عربيًّا.
  try { await activateSadTab(cdp); } catch { /* */ }

  // فتات المسار: **يُطالَب بأن يكون مأهولًا** لا بأن يكون نظيفًا. سطحٌ بلا بندٍ واحد
  // يُبلِّغ «‎0 معرَّضة» زورًا — وهو بالضبط ما خدعَنا فيه أوّل قياس (الترحيب كان نشطًا،
  // ولا URI ⇒ الشريط مخفيّ). التنشيط أعلاه شرطُ صحّة هذا القياس لا زينة.
  try {
    const b = await breadcrumbsBar(cdp);
    if (!b || !b.present) out.push(skip("فتات المسار: مأهول ومتّجه", "لا .breadcrumbs-control", true));
    else if (b.hidden || !b.items.length) out.push(skip("فتات المسار: مأهول ومتّجه",
      `مخفيّ=${b.hidden} بنود=${b.items.length} — لا محرّر بـURI نشط (ترحيب؟)`, true));
    else {
      // البنود تتدرّج **من اليمين إلى اليسار** في قشرة RTL: أوّل بندٍ منطقيّ أقصى اليمين.
      const desc = b.items.every((it, i) => i === 0 || it.left < b.items[i - 1].left);
      const raw = b.items.filter(it => it.ub === "normal").map(it => it.t);
      if (!desc) out.push(fail("فتات المسار: مأهول ومتّجه",
        `ترتيب البنود ليس يمينًا←يسارًا: ${b.items.map(i => `${i.t}@${i.left}`).join(" ")}`));
      else if (raw.length) out.push(fail("فتات المسار: مأهول ومتّجه",
        `${raw.length} بندًا بـunicode-bidi:normal (${raw.join("، ")}) — محايداتُ المسار ستقفز`));
      else out.push(pass("فتات المسار: مأهول ومتّجه",
        `${b.items.length} بندًا (عرض ${b.w}) متدرّجًا يمينًا←يسارًا، ` +
        `آخرها «${b.items.at(-1).t}» بترتيب ${b.items.at(-1).ltr ? "LTR" : "RTL"}`));
    }
  } catch (e) { out.push(skip("فتات المسار: مأهول ومتّجه", "تعذّر: " + e.message, true)); }

  return out;
}


// ───────── القاعدة 24: أسطح اللوحات (بحث · امتدادات · مشاكل) ─────────
//
// هذه الأسطح **لم تُقَس أصلًا** قبل هذه الدفعة: مِجَسّاتنا كلّها كانت على المحرّر والمستكشف
// والترحيب، فبقيت اللوحات نقطةً عمياء حتى مسحناها بماسحٍ عامّ فأعادت خمسة أسطح معطوبة.
//
// **نفتحها باختصارات المفاتيح لا بلوحة الأوامر عمدًا.** أسماء الأوامر تُخبَز عربيّةً في
// البناء المشحون وتبقى إنجليزيّة في وضع التطوير، فمِجَسٌّ يكتب «‎View: Show Extensions‎»
// كان سيعمل عندنا ويتخطّى صامتًا عند المستخدم — وهو بالضبط صنفُ الأخضر الكاذب الذي
// كلّفنا أكثر ما كلّف في هذه الجلسة. الاختصارات لا تتغيّر بتغيّر اللغة.
// كلُّ عنصر: [الاسم، سلسلةُ ضغطاتٍ [رمز، code، مُعدِّلات]]. السلسلة لا ضغطةٌ واحدة لأنّ
// محرّر الاختصارات يُفتَح بوترٍ (‏Ctrl+K ثمّ Ctrl+S).
// مِجَسُّ الهويّة: يعدّد الحاوياتِ المرئيّة ذاتَ المعرِّفات/الأصناف الثابتة (لا نصوصًا:
// النصُّ يُترجَم فيسقط في أحد المسارين، كما تعلّمنا من أسماء الأوامر).
const ID_PROBE = `(() => {
  const out = [];
  for (const el of document.querySelectorAll('[id^="workbench."], .composite, .quick-input-widget, .settings-editor, .keybindings-editor, .search-view, .markers-panel, .extensions-viewlet, .terminal-outer-container, .monaco-diff-editor, .gettingStartedContainer, .context-view, .suggest-widget, .action-widget, .zone-widget, .editor-widget.find-widget, .notifications-list-container, .monaco-dialog-box, .repl, .output-view')) {
    const r = el.getBoundingClientRect();
    if (r.width < 20 || r.height < 20) continue;
    out.push((el.id ? '#' + el.id : '') + '.' + [...el.classList].slice(0, 3).join('.'));
  }
  const q = document.querySelector('.quick-input-box .monaco-inputbox input, .quick-input-box input, .quick-input-box .view-line');
  if (q) out.push('QUERY=' + JSON.stringify((typeof q.value === 'string' ? q.value : q.textContent || '').replace(/\\u200b/g, '')));
  return [...new Set(out)].join(' | ');
})()`;

// مقدّمةُ البصمة: تُحقَن في كلّ تقييم — مرّةً للانتظار ومرّةً للتأكيد، بالنصّ نفسه، حتّى
// لا ينتظرَ الطقمُ شرطًا ويؤكّدَ آخر.
const FP = (expr) => `(() => {
  const V = s => [...document.querySelectorAll(s)].some(e => { const r = e.getBoundingClientRect(); return r.width > 20 && r.height > 20; });
  const ID = s => { const e = document.getElementById(s); if (!e) return false; const r = e.getBoundingClientRect(); return r.width > 20 && r.height > 20; };
  const Q = () => { const e = document.querySelector(".quick-input-box input"); return e ? e.value : null; };
  try { return !!(${expr}); } catch { return false; }
})()`;

// العنصرُ الرابع (اختياريّ): **بصمةُ هويّة** — تعبيرٌ يُقيَّم في الصفحة ويجب أن يصدق بعد
// المحفّز، وإلّا فالسطحُ المفتوح ليس السطحَ المقصود. انظر شرحَ الحارس في الحلقة أدناه.
const PANELS = [
  ["الامتدادات", [[88, "KeyX", MOD.CTRL | MOD.SHIFT]], null, `ID("workbench.view.extensions")`],
  ["البحث", [[70, "KeyF", MOD.CTRL | MOD.SHIFT]], null, `ID("workbench.view.search")`],
  ["المشاكل", [[77, "KeyM", MOD.CTRL | MOD.SHIFT]], null, `ID("workbench.panel.markers")`],
  ["لوحة الأوامر", [[80, "KeyP", MOD.CTRL | MOD.SHIFT]], "query", `V(".quick-input-widget") && Q() && Q().startsWith(">")`],
  ["الإعدادات", [[188, "Comma", MOD.CTRL]], null, `V(".settings-editor")`],
  ["الاختصارات", [[75, "KeyK", MOD.CTRL], [83, "KeyS", MOD.CTRL]], null, `V(".keybindings-editor")`],
  // الدفعة الثانية: أسطحٌ في **اللوحة السفلى** وفي جزء المصادر لم يبلغها المسحُ الأوّل
  // لأنّنا فتحنا الشريطَ الجانبيّ وحده. اللوحة السفلى نطاقٌ أصلًا (‏`.part.panel`) لكنّها
  // كانت فارغةً في كلّ تشغيلاتنا — نطاقٌ بلا محتوًى يُبلِّغ «نظيف» بلا أن يمسح شيئًا.
  ["المخرجات", [[85, "KeyU", MOD.CTRL | MOD.SHIFT]], null, `ID("workbench.panel.output")`],
  ["وحدة التصحيح", [[89, "KeyY", MOD.CTRL | MOD.SHIFT]], null, `ID("workbench.panel.repl")`],
  ["الطرفيّة", [[192, "Backquote", MOD.CTRL]], null, `V(".terminal-outer-container")`],
  // **جزءُ التنقيح بلا جلسة — سطحُنا نحن لا سطحُ المنبع** ‏[DG-01]. `workbench.view.debug`
  // كان خارجَ القائمة كلَّها، وفيه **كتلةُ `viewsWelcome` التي كتبناها بأنفسنا** («شغّل ملفّ
  // ص المفتوح بلا إعدادٍ ولا ملفّ launch.json») — نصٌّ عربيٌّ فيه اسمُ ملفٍّ لاتينيٌّ محايدُ
  // الطرفين، أي عائلةُ القاعدة 30 حرفيًّا. أن يبقى نصُّنا نحن غيرَ ممسوحٍ أسوأُ من بقاء
  // نصِّ المنبع.
  //
  // **والبصمةُ مقترنةٌ لا مجرّدةٌ من الحاوية:** الكتلةُ مشروطةٌ بـ`editorLangId == sad`،
  // فحاويةٌ حاضرةٌ بلا نصِّنا تعني أنّ الشرطَ لم يتحقّق — والمسحُ حينها يمسح فراغًا ويُبلّغ
  // «نظيف». فنشترط عربيّةً داخل ورقةِ الترحيب نفسِها.
  //
  // وما **لا** يبلغه هذا المدخل: لوحاتُ المتغيّرات وكومةِ الاستدعاء والمراقبة — لا تُصيَّر
  // إلّا في **جلسةِ تنقيحٍ حيّة**، ولا جلسةَ في مسحِ اللوحات. موضعُها `debug_panes.live.mjs`
  // الذي يبني مساحتَه ويطلق جلستَه بنفسِه. (النطاقُ بلا محتوًى يُبلِّغ «نظيف» بلا أن يمسح.)
  ["جزء التنقيح (ترحيبُنا)", [[68, "KeyD", MOD.CTRL | MOD.SHIFT]], null,
   `[...document.querySelectorAll("#workbench\\\\.view\\\\.debug .welcome-view-content, #workbench\\\\.view\\\\.debug .monaco-list-row")].some(e => /[\\u0600-\\u06ff]/.test(e.textContent || ""))`],
  // التحكّم بالمصادر وترٌ في الإصدارات الحديثة (‏Ctrl+Shift+G ثمّ G) لا ضغطةٌ واحدة.
  ["التحكّم بالمصادر", [[71, "KeyG", MOD.CTRL | MOD.SHIFT], [71, "KeyG", 0]], null, `ID("workbench.view.scm")`],
  // **قائمة السياق بالمفتاح لا بالفأرة.** ‏Shift+F10 يفتحها على العنصر المركَّز عليه، فلا
  // نحتاج إحداثيّاتٍ تتغيّر بتغيّر التخطيط. وهي سطحٌ كثيفُ الخلط: تسميةٌ عربيّة يمينًا
  // واختصارٌ لاتينيّ يسارًا في الصفّ نفسه (قِسنا 17 ورقة). أضفناها لأنّنا كنّا قد أدخلنا
  // ‏`.context-view` في النطاق **بلا أن نفتحها قطّ** — وهو بعينه الفخّ الذي وثّقناه
  // للوحة السفلى: نطاقٌ بلا محتوًى يُبلِّغ «نظيف» بلا أن يمسح شيئًا.
  ["قائمة السياق", [[69, "KeyE", MOD.CTRL | MOD.SHIFT], [121, "F10", MOD.SHIFT]], null, `V(".context-view.monaco-menu-container")`],
  // ‏Ctrl+P غير Ctrl+Shift+P: الأولى تعرض **مساراتِ ملفّات** والثانية أسماءَ أوامر.
  // المسارُ صنفُ نصٍّ آخر بالكامل (شرطات مائلة ونقاط وامتدادات) — محايداتٌ في الطرفين.
  ["فتح سريع (مسارات)", [[80, "KeyP", MOD.CTRL]], "query", `V(".quick-input-widget") && Q() && !Q().startsWith(">")`],
  // **الإشعارات — بالنقر لا بالمفتاح.** `notifications.showList` بلا اختصارٍ افتراضيّ،
  // واسمُ الأمر يُترجَم فيسقط في أحد المسارين. زرُّ الجرس في شريط الحالة معرّفٌ ثابت
  // (‏`#status.notifications`) لا يتغيّر بتغيّر اللغة. وكنّا نصف هذا السطح «انتهازيًّا»
  // لأنّ قياسًا ملوَّثًا أوهمَنا أنّه لا يُملأ — وفيه إشعارُ محرابٍ نفسه دائمًا.
  ["الإشعارات", [], "click:#status\\.notifications a", `V(".notifications-list-container")`],
  // **ودجة البحث في المحرّر — أوّلُ سطحٍ في حاوية LTR ندخله.** نصُّها واجهةٌ مترجَمة
  // داخل حاوية المحرّر التي أبقيناها LTR عمدًا لحماية الكود، وعدّادُها («‏3 من 146»)
  // كان يُقرأ «‏3 146 من». تحتاج تركيزًا في المحرّر ثمّ استعلامًا يُعطي نتائج، فلها
  // وضعُها الخاصّ: `findWidget` ينقر أكبرَ `.view-lines` (لا إحداثيّةً ثابتة) ثمّ Ctrl+F.
  ["ودجة البحث في المحرّر", [], "find:ا", `V(".editor-widget.find-widget.visible")`],
  // **الثلاثةُ التي «تعذّر فتحُها» — وما كان التعذّرُ إلّا ظنًّا.** كانت `.suggest-widget`
  // و`.action-widget` و`.zone-widget` في نطاق الماسح **بلا أن تُفتَح قطّ**، وعلّلنا ذلك
  // بأنّ إدخال CDP النصّيّ لا يبلغ `native-edit-context`. القياسُ نقض التعليل: المحفّزات
  // الثلاثة لا تحتاج كتابةً أصلًا — تركيزٌ في المحرّر ثمّ وترُ مفاتيح. و«نطاقٌ بلا محتوًى
  // يُبلِّغ نظيفًا بلا أن يمسح شيئًا» هو الفخُّ نفسه الذي وثّقناه للوحة السفلى مرّتين.
  // ‏(‏`Shift+F12` و`Alt+F12` و`F2` جُرِّبت ولم تفتح شيئًا — لا خادمَ مراجع في العيّنة —
  // فلم نُدرِجها: مِجَسٌّ لا يفتح سطحَه يُحتسَب «لم ينفتح» لا تغطية.)
  ["اقتراحات المحرّر", [], "editor:32,Space,2", `V(".suggest-widget.visible")`],
  ["إجراءات الكود", [], "editor:190,Period,2", `V(".action-widget")`],
  ["نظرة المشاكل", [], "editor:119,F8,0", `V(".zone-widget")`],
  // ── عدساتُ الكود [LN-01]: سطحٌ **نصنعه بأنفسنا** ولم يُقَس قطّ ─────────────────────
  // ‏`SadMainCodeLensProvider` يضع «▶ شغّل» و«🔨 ابنِ» فوق دالّة البداية في كلّ ملفّ ص،
  // وامتدادُ `merge-conflict` المحزوم يضع عدساتِه العربيّة فوق كتلة التعارض. وهو الفردُ
  // الخامسُ من عائلة «القاعدة 30» (عربيٌّ في حاوية LTR) التي قِيست فوُجدت مكسورةً في
  // أربعة أسطحٍ متتالية — ولم يُفتَح هذا الخامسُ ولا مرّة.
  //
  // **أرخصُ محفِّزٍ في القائمة كلِّها:** لا وترَ ولا نقرة — تنشيطُ تبويب العيّنة وحده يكفي،
  // فالعدسةُ تظهر تلقائيًّا فوق `دالة رئيسية()` في العيّنة القائمة. لكنّ التنشيطَ **شرطٌ
  // لا زينة**: التبويبُ غير النشط لا يُصيَّر أصلًا (الدرسُ نفسُه المدفوعُ في صفحة الترحيب).
  //
  // **والبصمةُ تشترط عربيّةً في ورقةٍ لا مجرّدَ وجودِ الحاوية:** المنبعُ يصيّر
  // `'no commands'` حين تُحلّ الرموزُ بلا أوامر، فحاويةٌ حاضرةٌ ليست عدسةً مأهولة.
  // وحلُّ العدسات **غيرُ متزامنٍ** وتالٍ لتنشيط الامتداد، فالبصمةُ تُنتظَر لا تُفترَض.
  ["عدسات الكود", [], "codelens",
   `[...document.querySelectorAll(".codelens-decoration a")].some(a => /[\\u0600-\\u06ff]/.test(a.textContent || ""))`],
  // ── محرّرُ المقارنة: سطحُ محرّرٍ كاملٌ لم يبلغه مِجَسّ ──────────────────────────
  // يُفتَح بنقر مَورِدٍ متغيّر في جزء التحكّم بالمصادر — لا اسمَ أمرٍ مترجَمًا في الطريق.
  // نمسح **أوراقَ واجهته وحدها** (شريطُ الأسطر المطويّة ومراجعةُ المقارنة) لا سطورَه:
  // سطورُ المقارنة كودُ المستخدم، وقد تعلّمنا من `.view-lines` و`.xterm-rows` أنّها تُغرِق
  // الماسحَ ببلاغاتٍ كاذبة. يشترط مستودعًا ذا تغييرات، وإلّا فـ«لم ينفتح» بصراحة.
  ["محرّر المقارنة", [], "scm-diff", `V(".monaco-diff-editor")`],
  // ── الحوار المشروط: **والعذرُ الثاني الذي نقضه القياس** ────────────────────────
  // كُتب هنا ثلاثةَ أعذارٍ لعدم قياسه، أوسطُها: «الدفترُ الجديد لا يتّسخ بـ`insertText`
  // لأنّ المحرّر يستعمل `native-edit-context`». قِسناه فاتّسخ من أوّل محرف (‏`dirty` على
  // التبويب). والعذرُ الأوّل («`Ctrl+W` يأكل تبويبَ العيّنة») صحيحٌ للعيّنة لا للدفتر:
  // الدفترُ الجديد ملكُنا وحدنا، وإغلاقُه لا يمسّ ملفًّا للمستخدم.
  //
  // وما كان يحجب السطحَ فعلًا شيءٌ آخر لم يخطر في الأعذار الثلاثة: افتراضُ
  // `window.dialogStyle` = `native` ⇒ **الحوارُ حوارُ ويندوز**، بلغته وباتّجاه LTR، لا
  // أثرَ له في DOM. أي أنّ محرابًا كان يخرج من التعريب كلِّه في لحظة فقدِ عمل. رقّعنا
  // الافتراضَ (`build/patch_dialog_style.py`)، فصار الحوارُ عربيًّا RTL — وصار قابلًا
  // للقياس أصلًا. فإن عاد «لم ينفتح» فهو انحدارُ الرُقعة لا هشاشةُ مِجَسّ.
  //
  // يبقى آخرَ سطحٍ في القائمة، ويُغلَق بـ`Escape` (إلغاءُ الإغلاق) داخل مِجَسّه: مودالٌ
  // متروكٌ مفتوحًا يُعطّل كلَّ ما بعده — قِسنا ذلك أيضًا (تعطّل أوّلُ وترٍ تالٍ بمهلة).
  ["الحوار المشروط", [], "dialog", `V(".monaco-dialog-box")`],
  // ── صفحةُ الترحيب: سطحُ **النثر الكتليّ**، وحيث للمحاذاة مقامٌ كبير ────────────────
  // ‏`.gettingStartedContainer` أُدخِلت النطاقَ حارسًا دائمًا لأنّ بلاغَ المستخدم وقع فيها
  // (القاعدة 32). لكنّ إدخالَ النطاق وحده **لا يقيس شيئًا**: قِسناه فكان إسهامُها صفرًا
  // في الوصفة القياسيّة — لأنّ محرابًا يفتحها تبويبًا **غيرَ نشط** حين يُمرَّر ملفّ، ومحرّرُ
  // التبويب غير النشط لا يُصيَّر أصلًا. وهو الفخُّ الموثَّق ثلاث مرّاتٍ هنا: نطاقٌ بلا
  // محتوًى يُبلِّغ «نظيف» بلا أن يمسح شيئًا. فالسطحُ يحتاج **محفِّزًا** كغيره: تنشيطُ تبويبه.
  // يبقى بعد الحوار مباشرةً وآخرَ القائمة، ثمّ يُعاد تنشيطُ تبويب العيّنة بعد الحلقة حتّى
  // لا تَرِث التأكيداتُ التالية محرّرًا نشطًا ليس محرّرَ نصّ.
  ["صفحة الترحيب (نثر)", [], "welcome", `V(".gettingStartedContainer")`],
  // **التحويم — سطحٌ كان في النطاق منذ الجولة الأولى بلا أن يُفتَح قطّ.** كنّا نعلّل ذلك
  // بأنّ حركةَ الفأرة المُصطنَعة لا تُنتج تحويمًا في Monaco (قِسناه على هدفين مستقلّين)،
  // فبقي يُبلَّغ ضمن «‏0 معرَّضة» وهو **مجهولٌ لا نظيف**. وللتحويم أمرٌ باختصارٍ ثابت.
  ["تحويم المحرّر", [], "hover", `V(".monaco-hover")`],
  // **صفحةُ تفاصيل الامتداد** — نثرٌ عريضٌ آخر في جزء المحرّر. أوراقُ اللوحات تشرنق على
  // محتواها فلا فسحةَ فيها تُقاس؛ والنثرُ العريض هو حيث للمحاذاة مقامٌ أصلًا.
  ["تفاصيل الامتداد (نثر)", [], "ext-details", `V(".extension-editor")`],
];

export async function panelAssertions(cdp) {
  const out = [];
  const offenders = [];
  const misaligned = [];
  let alignable = 0;
  let opened = 0;
  const notOpened = [];
  // **القياس الخامل** — ما يمسحه الماسح بلا أيّ محفّز. الأسطحُ الحاضرة دائمًا (شريط
  // الحالة، التلميح، فتات المسار) تُعيد نصوصها في كلّ تشغيلة؛ فلو اكتفينا بـ`scanned > 0`
  // لحُسِب كلُّ محفّزٍ فاشلٍ سطحًا مفتوحًا. نطرح هذا الأساس من كلّ قياسٍ تالٍ.
  let baseline = new Set();
  try { await escape(cdp); await sleep(500);
        const b = await bidiPanels(cdp);
        if (b && b.texts) baseline = new Set(b.texts); } catch { /* */ }
  for (const [label, chord, mode, fingerprint] of PANELS) {
    try {
      // **الإرجاعُ إلى حالٍ معلومة قبل كلّ سطح** — لا `escape` وحدها. أثرُ السطح السابق
      // (لوحةٌ سفلى مفتوحة، ودجةُ بحثٍ عالقة) كان يتراكم فتقيسُ التشغيلةُ الثانية حالةً
      // غيرَ الأولى، وقد أهدرنا بذلك ثلاثَ تشغيلات.
      await resetWorkbench(cdp);
      if (typeof mode === "string" && mode.startsWith("click:")) {
        const sel = mode.slice(6);
        await cdp.evaluate(`document.querySelector(${JSON.stringify(sel)})?.click(), 1`);
      } else if (typeof mode === "string" && mode.startsWith("editor:")) {
        // ودجاتٌ تُصيَّر **داخل** حاوية المحرّر: تحتاج تركيزًا فيه أوّلًا، وإلّا ابتلع
        // الشريطُ الجانبيُّ المركَّزُ عليه الوترَ فيُبلَّغ «لم ينفتح» بلا سبب ظاهر.
        if (!(await focusEditor(cdp))) { notOpened.push(label); continue; }
        const [vk, code, mods] = mode.slice(7).split(",");
        await key(cdp, +vk, code, +mods);
      } else if (mode === "scm-diff") {
        if (!(await openDiffFromScm(cdp))) { notOpened.push(label); continue; }
      } else if (mode === "codelens") {
        // تنشيطُ تبويب العيّنة ثمّ **انتظارُ البصمة صراحةً**: `activateSadTab` تعود صادقةً
        // لمجرّد وجود التبويب، وحلُّ العدسات يقع بعده بمهلةٍ غيرِ محدّدة. ومن لم ينتظر
        // البصمةَ هنا يقيس نطاقًا فارغًا ويُبلِّغ «نظيف» — الفخُّ الموثَّقُ أربعَ مرّاتٍ أعلاه.
        if (!(await activateSadTab(cdp))) { notOpened.push(label); continue; }
        if (!(await waitFor(cdp, FP(fingerprint), 12000))) {
          notOpened.push(label + " (لم تُحَلّ عدسةٌ عربيّةٌ في المهلة)"); continue;
        }
      } else if (mode === "hover") {
        if (!(await editorHover(cdp))) { notOpened.push(label); continue; }
      } else if (mode === "ext-details") {
        if (!(await openExtensionDetails(cdp))) { notOpened.push(label); continue; }
      } else if (mode === "welcome") {
        // تنشيطٌ **بإقرارِ التصيير** لا بنجاح النقرة: activateWelcomeTab يعود true لمجرّد
        // وجود التبويب، وقِسنا تشغيلةً انفتح فيها التبويب ولم يُصيَّر `.gettingStartedContainer`
        // في مهلة البصمة — فيُبلَّغ «لم ينفتح» بلا سبب. محاولةٌ ثانية بعد إفلاتٍ للتصيير.
        let okW = await activateWelcomeTab(cdp) && await waitFor(cdp, FP(fingerprint), 4000);
        if (!okW) { await recoverWelcomeTab(cdp); await sleep(800); okW = await activateWelcomeTab(cdp); }
        if (!okW) { notOpened.push(label); continue; }
      } else if (mode === "dialog") {
        const ok = await confirmDialog(cdp);
        if (!ok) { notOpened.push(label); continue; }
        // الأثرُ يُزال بعد القياس لا قبل التشغيلة التالية — انظر `discardUntitled`.
      } else if (typeof mode === "string" && mode.startsWith("find:")) {
        await findWidget(cdp);
        await key(cdp, 70, "KeyF", MOD.CTRL);
        await sleep(900);
        // **الإقرارُ يُقرأ لا يُهمَل.** حقلُ البحث حقلٌ حقيقيّ فيُقَرّ تلقائيًّا، لكنّ
        // تجاهُلَ الحكم يُعيدنا إلى ما قبل الإصلاح: ودجةٌ بلا استعلامٍ صحيح تُمسَح ويُبلَّغ
        // «‏0 معرَّضة» — خضرةٌ على سطحٍ لم يُقَس فعلًا. «لم ينفتح» أصدقُ منها.
        if ((await insertText(cdp, mode.slice(5))) === false) { notOpened.push(label + " (لم يُقَرّ الاستعلام)"); continue; }
      } else {
        for (const [vk, code, mods] of chord) { await key(cdp, vk, code, mods); await sleep(300); }
      }
      // **انتظارُ الشرط لا الزمن.** كانت هنا مهلةٌ ثابتة ‎2500ms‎ لعشرين سطحًا: تُبطئ
      // التشغيلةَ بلا داعٍ حيث السطحُ فوريّ، ولا تكفي حيث يتأخّر. والبصمةُ نفسها هي
      // الشرطُ — فننتظرها ثمّ نؤكّدها، وإن تأخّرت مضينا وترك الحكمَ للحارس أدناه.
      if (fingerprint) await waitFor(cdp, FP(fingerprint), 6000);
      else await sleep(2500);
      // لوحة الأوامر لا تُظهر شارة العدد قبل استعلام — بلا كتابةٍ يُمسَح سطحٌ فارغ ويُبلَّغ
      // «‎0 معرَّضة» زورًا. نكتب استعلامًا ثابتًا (لاتينيًّا: الأوامر تُخبَز عربيّةً في
      // البناء المشحون وإنجليزيّةً في التطوير، و«‎git‎» يطابق في الاثنين).
      // ولوحةُ الأوامر والفتحُ السريع كذلك: استعلامٌ لم يُقَرّ ⇒ نتائجُ استعلامٍ آخر
      // (أو لا نتائج)، فيُمسَح سطحٌ ليس السطحَ المقصود ويُحتسَب نظيفًا.
      if (mode === "query") {
        if ((await insertText(cdp, "git")) === false) { notOpened.push(label + " (لم يُقَرّ الاستعلام)"); continue; }
        await sleep(1500);
      }
      await sleep(700);
      // **استقرارٌ لا انتظارٌ ثابت.** قراءةٌ واحدة بعد مهلةٍ ثابتة أعطتنا خضرةً كاذبة:
      // لوحةُ المشاكل في أوّل فتحٍ لها تُصيَّر متأخّرةً، فمُسِحت قبل أن توجد رسالتُها
      // وأُبلِغ «‎14/14 · 0 معرَّضة» — بينما تشغيلةٌ تالية على النسخة نفسها أعادت ستّ
      // أوراق. نقرأ حتى يثبت عددُ الأوراق قراءتين متتاليتين (أو تنفد المحاولات).
      let r = await bidiPanels(cdp);
      for (let i = 0; i < 4; i++) {
        await sleep(900);
        const again = await bidiPanels(cdp);
        if (again && r && again.scanned === r.scanned) { r = again; break; }
        r = again;
      }
      // ‏`scanned === 0` ⇒ السطح لم يُفتَح (اختصارٌ ابتلعه المحرّر مثلًا)، فلا نحتسبه
      // «مسحًا نظيفًا». وإلّا صار كلُّ اختصارٍ فاشل نجاحًا صامتًا.
      if (!r || !r.scanned) { notOpened.push(label); continue; }
      // **الشرطُ الحاسم: نصٌّ جديد.** سطحٌ يُعيد ما في الأساس وحده لم ينفتح مهما كان
      // `scanned` كبيرًا. أمسك هذا الشرطُ حوارَ التأكيد الذي كان يُحتسَب زورًا.
      const fresh = (r.texts || []).filter(t => !baseline.has(t));
      // **«لم ينفتح» و«انفتح بلا نصٍّ يُمسَح» حالتان مختلفتان، وخلطُهما أضاع علينا ثلاثَ
      // تشغيلات.** كان محرّرُ المقارنة يُبلَّغ «لم ينفتح» بينما `.monaco-diff-editor` في
      // الصفحة فعلًا — النقصُ في **النطاق** لا في المحفّز. نُميّزهما في النصّ صراحةً.
      if (!fresh.length) { notOpened.push(label + " (انفتح بلا نصٍّ في النطاق)"); continue; }
      // **بصمةُ الهويّة — «انفتح شيء» غيرُ «انفتح هذا».** الحارسُ أعلاه يُثبت أنّ نصًّا
      // جديدًا ظهر، لا أنّه نصُّ السطح المقصود. وقد أمسكنا حالةً واحدة بالمصادفة (تفريغٌ
      // أعمى محا بادئةَ «‏>» فصارت لوحةُ الأوامر بحثَ ملفّات، والطقمُ أخضر) — فلولا شاهدٌ
      // إيجابيّ لَما ظهرت. لذا يحمل كلُّ سطحٍ تعبيرًا يجب أن يصدق بعد محفّزه.
      // ‏MIHRAB_ID_DUMP=1 يطبع الهويّاتِ المرشّحة بدل التأكيد — بها كُتبت البصماتُ قياسًا
      // لا تخمينًا (ما لم يُقَس منها كان سيُبلَّغ «لم ينفتح» زورًا).
      if (process.env.MIHRAB_ID_DUMP) {
        const d = await cdp.evaluate(ID_PROBE);
        console.log(`  [هويّة] ${label} :: ${d}`);
      } else if (fingerprint) {
        // ‏`V`/`ID` يشترطان **حجمًا مرئيًّا** لا وجودًا في DOM: ودجةُ البحث في المحرّر
        // موجودةٌ دائمًا (قِسناها حاضرةً في كلّ سطحٍ سبقها)، فمجرّدُ العثور عليها ليس دليلَ
        // فتح — و`.visible` هو الفارق. و`Q` نصُّ حقل الإدخال السريع: به وحده تُميَّز لوحةُ
        // الأوامر (بادئة «‏>») من الفتح السريع، وهما ودجةٌ واحدة بصنفٍ واحد.
        const okId = await cdp.evaluate(FP(fingerprint));
        if (!okId) { notOpened.push(label + " (انفتح سطحٌ آخر)"); continue; }
      }
      opened++;
      for (const o of r.offenders) offenders.push({ ...o, surface: label });
      for (const m of (r.misaligned || [])) misaligned.push({ ...m, surface: label });
      alignable += (r.alignable || 0);
      // أثرُ مِجَسّ الحوار (ملفٌّ بلا عنوان متّسخ) يُزال فورَ قياسه: تركُه يزاحم تبويبَ
      // المعاينة فيبتلع **صفحةَ الترحيب** — مِجَسٌّ أسقط سطحَ مِجَسٍّ آخر، وقد قِسناه.
      if (mode === "dialog") await discardUntitled(cdp);
    } catch { notOpened.push(label); }
  }
  // **سطحٌ مُعلَنٌ غيرَ مقيس أصدقُ من سطحٍ أخضرَ لم يُفتَح.** التحويمُ مُدرَجٌ ليُحاوَل في
  // كلّ تشغيلة (فإن صار قابلًا للفتح يومًا دخل القياسَ تلقائيًّا)، لكنّ إخفاقَه لا يُدفَن
  // في «لم تنفتح» بل يُبلَّغ سطرًا مستقلًّا في الحصيلة: الفجوةُ المرئيّة تُطالِب، والمدفونةُ
  // تُنسى — وقد بقي هذا السطحُ «نظيفًا» في كلّ تشغيلاتنا وهو مجهولٌ لا نظيف.
  if (notOpened.some(n => n.startsWith("تحويم المحرّر")))
    out.push(skip("تحويم المحرّر — غير مقيس (فجوة معلَنة)",
      "‏.monaco-hover قائمةٌ بحجم 0×0 دائمًا؛ لم يفتحها فأرةٌ مُصطنَعة (هدفان) ولا وترُ الأمر (ص وjson) — القياسُ سلبيّ لا صامت", true));

  // **تنظيفٌ لازم لا مجاملة.** آخرُ سطحٍ في القائمة مودالٌ يحجب النافذة؛ لولا هذا
  // الإغلاق لتعطّل كلُّ تأكيدٍ بعد `panelAssertions` بمهلةِ `Input.dispatchKeyEvent`.
  await escape(cdp); await sleep(400);
  // وسطحُ الترحيب يترك **تبويبَه** نشطًا لا مجرّدَ لوحةٍ مفتوحة، فنعيد تبويبَ العيّنة
  // قبل أيّ تأكيدٍ تالٍ: محرّرٌ نشطٌ ليس محرّرَ نصّ يُسقِط مِجَسّاتٍ لا علاقةَ لها بالترحيب.
  try { await activateSadTab(cdp); await sleep(600); } catch { /* */ }
  if (!opened) out.push(skip("محايدات اللوحات (القاعدة 24)", "لم يُفتَح أيّ سطح", true));
  // **الفشلُ يذكر ما لم ينفتح أيضًا.** كانت الرسالةُ تذكر المعرَّضَ وحده، فتُخفي أنّ
  // سطحًا لم يُفتَح أصلًا خلف رقمٍ في البسط — أي تُخفي ثغرةَ تغطيةٍ خلف عطبٍ آخر.
  else if (offenders.length) out.push(fail("محايدات اللوحات (القاعدة 24)",
    `${opened}/${PANELS.length} أسطح · ${offenders.length} ورقة معرَّضة بلا معالجة: ` +
    // **آخرُ ثلاثِ حلقاتٍ من السلسلة لا واحدة.** الورقةُ وحدها (`span.monaco-highlighted-label`)
    // تتكرّر في عشرات الأسطح فلا تدلّ على قاعدةٍ تُكتَب؛ وسلسلةُ الآباء هي ما يُحدّد المحدِّد.
    offenders.slice(0, 5).map(o =>
      `[${o.surface}] ${o.path.split(" > ").slice(-3).join(" > ")}«${o.text}» (bidi=${o.bidi} انقلاب=${o.reordered} قصّ=${o.clipped} رتابة=${o.monoDiag})`).join(" | ") +
    (notOpened.length ? ` · لم تنفتح: ${notOpened.join("، ")}` : "")));
  else out.push(pass("محايدات اللوحات (القاعدة 24)",
    `${opened}/${PANELS.length} أسطح مسحت، 0 ورقة معرَّضة` +
    (notOpened.length ? ` · لم تنفتح: ${notOpened.join("، ")}` : "")));

  // **البُعد الثالث معمَّمًا: من أيّ حافّةٍ يبدأ السطر؟** جاء بلاغُ جولة الترحيب من
  // المستخدم لا من الماسح، لأنّ كلّ ما نسأل عنه كان `direction` وترتيبَ المحارف. هذا
  // التأكيد يطرح سؤالَ المحاذاة على **كلّ** الأسطح التي نفتحها، بالحبر لا بالإعلان:
  // ورقةٌ في فقرةٍ RTL حبرُها ملتصقٌ بالحافّة اليسرى وبينه وبين اليمنى فسحةٌ حقيقيّة.
  if (!opened) out.push(skip("محاذاة اللوحات: تبدأ من اليمين", "لم يُفتَح أيّ سطح", true));
  // **لا نُعلن نظافةً بلا موضوعٍ يُقاس.** ورقةٌ صندوقُها بمقاس حبرها لا محاذاةَ فيها؛
  // وجُلُّ أوراق اللوحات كذلك (عناصرُ مرنة أو سطريّة تنكمش على نصّها). فإن لم تحمل
  // أيُّ ورقةٍ فسحةً، فالسؤالُ لم يُطرح على شيء — تخطٍّ صريح لا خضرةٌ كاذبة. وهو
  // الحارسُ نفسه الذي فرضه `scanned` في بُعد الانقلاب، مطبَّقًا على البُعد الجديد.
  else if (!alignable) out.push(skip("محاذاة اللوحات: تبدأ من اليمين",
    `${opened}/${PANELS.length} أسطح · لا ورقةَ تحمل فسحةً تُقاس فيها المحاذاة`, true));
  else if (misaligned.length) out.push(fail("محاذاة اللوحات: تبدأ من اليمين",
    `${opened}/${PANELS.length} أسطح · ${misaligned.length}/${alignable} ورقة ملصَقةً يسارًا: ` +
    misaligned.slice(0, 5).map(m =>
      `[${m.surface}] ${m.path.split(" > ").slice(-3).join(" > ")} ta=${m.ta} فسحة ${m.headGap}px«${m.text}»`).join(" | ")));
  else out.push(pass("محاذاة اللوحات: تبدأ من اليمين",
    `${opened}/${PANELS.length} أسطح · ${alignable} ورقة ذات فسحة، 0 ملصَقةً يسارًا`));

  // شاهدٌ **بصريّ** على حقل بحث الامتدادات: `getComputedStyle` وحده لا يكفي هنا — قِسنا
  // أنّه يعيد `plaintext` على `.view-line` بينما العرض لا يتغيّر (سمة `dir` من Monaco
  // تغلبها)، فالتأكيد على الخاصّية المحسوبة كان سينجح زورًا. نقيس ترتيب المحارف نفسه.
  try {
    await escape(cdp);
    await key(cdp, 88, "KeyX", MOD.CTRL | MOD.SHIFT);
    await sleep(2000);
    // **نكتب الاستعلام بأنفسنا لا نقيس ما تركه المستخدم.** قِسنا أوّلًا ما كان في الحقل
    // فكان استعلامًا مختلطًا خلّفه مِجَسٌّ يدويّ سابق — أي أنّ نتيجة الفحص كانت رهنَ حالةٍ
    // عابرة لا رهنَ الشيفرة. `@builtin` هو ما أصلحناه وما ندّعيه، فهو ما نقيسه.
    const focused = await cdp.evaluate(`(() => {
      const el = document.querySelector(".suggest-input-container .native-edit-context,"
        + " .suggest-input-container textarea");
      if (!el) return false;
      el.focus();
      return !!document.activeElement && el.contains(document.activeElement)
        || document.activeElement === el;
    })()`);
    await sleep(400);
    // ⚠️ **حارسٌ مكلفٌ تعلّمناه بالخسارة.** كان `Ctrl+A` ثمّ `insertText` يُرسَلان بلا
    // شرط. وحين لا ينفتح جزءُ الامتدادات (أو لا يُركَّز حقلُه) يذهب الاثنان إلى
    // **المحرّر**: «حدِّد الكلّ» ثمّ استبدالٌ بـ«‎@builtin‎» — أي محوُ الملفّ المفتوح.
    // رصدناه حيًّا: وجدنا `package.json` موسَّخًا بعد تشغيلةٍ على ملفّ مستخدمٍ نظيف،
    // ولم يكن في المِجَسّ ما يُوسِّخ سواه. القرص سليمٌ (المخزن غير محفوظ) لكنّ التشغيلة
    // تُفسَد وما بعدها يُقاس على ملفٍّ ممسوح.
    if (!focused) {
      out.push(skip("ترتيب استعلام الامتدادات (القاعدة 24)",
        "لم يُركَّز حقلُ بحث الامتدادات — تخطٍّ بدل إرسال Ctrl+A إلى المحرّر", true));
    } else {
    // ‏**`Ctrl+A` صار داخل الإقرار لا قبله.** لو بقي هنا لقرأ الإقرارُ الحقلَ **بعد**
    // التحديد — والتحديدُ لا يمحو، فيقرأ النصَّ القديم ويتّخذه مرجعًا. الاستبدالُ
    // وإقرارُه فعلٌ واحدٌ لا فعلان.
    // **إقرارٌ على النصّ المُصيَّر، لا مهلةٌ ثابتة.** هنا وقعت الشذوذةُ التي أضاعت
    // تشغيلتين: «‏ك@builtinتابت» — استعلامٌ حُقن في حقلٍ يحمل بقيّةَ سابقه. فإن لم
    // يُقَرّ بعد المحاولات، **تخطٍّ صريح**: قياسُ ترتيبٍ على نصٍّ ليس نصَّنا لا معنى له،
    // وإعلانُه نجاحًا أو فشلًا كلاهما كذب.
    // ‏`.view-line` لا الحاوية: الحاويةُ تضمّ **نصَّ الإرشاد** («البحث عن إضافات…»)
    // فلا تطابق شيئًا أبدًا. قِسناه: الحاوية تعود «…المتجر@builtin» والسطرُ «@builtin».
    const typed = await insertText(cdp, "@builtin",
      { selector: ".suggest-input-container .view-line", replace: true });
    await sleep(600);
    const g = typed === false ? null : await glyphOrder(cdp, ".suggest-input-container .view-line");
    if (typed === false) out.push(skip("ترتيب استعلام الامتدادات (القاعدة 24)",
      "لم يُقَرّ وصولُ «@builtin» إلى حقل البحث (سباق إدخال) — لا يُقاس ترتيبُ نصٍّ ليس نصَّنا", true));
    else if (!g) out.push(skip("ترتيب استعلام الامتدادات (القاعدة 24)", "لا حقل اقتراح مفتوح", true));
    else if (!/^[؀-ۿ]/.test(g.text) && !g.ltr)
      out.push(fail("ترتيب استعلام الامتدادات (القاعدة 24)",
        `«${g.text}» يُعرَض معكوسًا (أوّل محرف عند ${g.first}، آخره عند ${g.last}) — ` +
        `صيغة الترشيح «@…» تُقرأ خطأً`));
    else out.push(pass("ترتيب استعلام الامتدادات (القاعدة 24)",
      `«${g.text}» بترتيب ${g.ltr ? "LTR" : "RTL"} مطابقٍ لأوّل حرفٍ قويّ فيه`));
    }
  } catch (e) { out.push(skip("ترتيب استعلام الامتدادات (القاعدة 24)", "تعذّر: " + e.message, true)); }

  // أعِد المستكشف وتبويب العيّنة: تركُ لوحةٍ مفتوحة يغيّر ما تقيسه أيّ تشغيلة تالية.
  try { await escape(cdp); await key(cdp, 69, "KeyE", MOD.CTRL | MOD.SHIFT); await sleep(800);
        await activateSadTab(cdp); } catch { /* */ }
  return out;
}

/**
 * **بُعدٌ ثالثٌ للترتيب: أين يقع البند، لا كيف يُكتَب.** كلُّ ما قِسناه حتّى الآن يسأل عن
 * اتّجاه النصّ داخل الورقة؛ وسطحان يبقيان صحيحَي النصّ منقلبَي **الترتيب** فلا يمسّهما
 * ماسحُنا: أزرارُ الحوار (الفعلُ المؤكِّد يجب أن يكون أيمنَ إخوته في RTL، والتركيزُ عليه)
 * وشريطُ الحالة (البنودُ المُرساةُ `left` منطقيًّا تُصيَّر يمينًا). كلاهما يُقرَأ أوّلًا
 * في تجربة المستخدم، وكلاهما كان خارج السؤال.
 */
export async function rtlOrderAssertions(cdp) {
  const out = [];
  // شريطُ الحالة أوّلًا: حاضرٌ دائمًا فلا يحتاج محفّزًا.
  try {
    const sb = await statusbarOrder(cdp);
    if (!sb || !sb.present) out.push(skip("شريط الحالة: مرساة البنود", "لا شريط حالة"));
    else if (!sb.nLeft || !sb.nRight)
      out.push(skip("شريط الحالة: مرساة البنود",
        `مجموعةٌ فارغة (يسار ${sb.nLeft}، يمين ${sb.nRight}) — لا يُقارَن ترتيبٌ بمجموعةٍ واحدة`, true));
    else if (sb.leftMid > sb.rightMid)
      out.push(pass("شريط الحالة: مرساة البنود",
        `dir=${sb.dir} · ‏${sb.nLeft} بندًا «left» عند ${sb.leftMid}px يمينَ ${sb.nRight} بندًا «right» عند ${sb.rightMid}px`));
    else
      out.push(fail("شريط الحالة: مرساة البنود",
        `المرساة لم تنقلب: «left» عند ${sb.leftMid}px ليست يمينَ «right» عند ${sb.rightMid}px`));
  } catch (e) { out.push(skip("شريط الحالة: مرساة البنود", e.message)); }
  // الحوارُ يحتاج فتحًا، ويُغلَق فورًا: مودالٌ متروكٌ يُعطّل كلَّ ما بعده (مقيس).
  try {
    if (!(await confirmDialog(cdp))) {
      out.push(skip("ترتيب أزرار الحوار (RTL)", "لم يظهر الحوار — راجع رُقعة dialogStyle", true));
    } else {
      const d = await dialogButtons(cdp);
      const bs = (d && d.buttons) || [];
      if (bs.length < 2) out.push(skip("ترتيب أزرار الحوار (RTL)", `${bs.length} زرًّا — لا ترتيبَ يُقاس`, true));
      else {
        // ترتيبُ DOM هو ترتيبُ الأولويّة؛ في RTL يجب أن يقابله ترتيبٌ بصريّ **متناقص**.
        const desc = bs.every((b, i) => i === 0 || bs[i - 1].left > b.left);
        const names = bs.map(b => `«${b.t}»@${b.left}`).join(" ← ");
        if (desc) out.push(pass("ترتيب أزرار الحوار (RTL)", `dir=${d.dir} · ${bs.length} أزرار من اليمين: ${names}`));
        else out.push(fail("ترتيب أزرار الحوار (RTL)", `الأوّل ليس أيمنَ إخوته: ${names}`));
      }
      await escape(cdp); await sleep(400);
      await discardUntitled(cdp);
    }
  } catch (e) { out.push(skip("ترتيب أزرار الحوار (RTL)", e.message, true)); }
  try { await escape(cdp); await activateSadTab(cdp); } catch { /* */ }
  return out;
}

export async function runAll(cdp) {
  // نُنشِّط تبويب العيّنة العربيّة أوّلًا: محراب يستعيد المحرّر النشط من الحالة المحفوظة،
  // فقد يكون ملفًّا لاتينيًّا مهما كان ترتيب الوسائط (مقيس) — وحينها تُبلَّغ مِجَسّات
  // ‏bidi و[AR-04] «لا سطر عربيّ» زورًا. النقر حتميّ ومستقلّ عن الحالة.
  try { await activateSadTab(cdp); } catch { /* لا تبويب عيّنة — المِجَسّات تتخطّى بنفسها */ }
  // **ثبِّت تبويب العيّنة (`Ctrl+K Enter` = keepEditor).** الملفّات التي تُمرَّر في سطر
  // الأوامر تُفتَح في وضع **المعاينة**، ووضعُ المعاينة تبويبٌ واحدٌ يُستبدَل بأيّ محرّرٍ
  // جديد. ومِجَسّاتنا تفتح **الإعداداتِ والاختصاراتِ وهما محرّران لا لوحتان**، فكانتا
  // تبتلعان تبويبَ العيّنة في كلّ تشغيلة. رصدناه بمقارنة تشغيلتين متتاليتين على النسخة
  // نفسها: الأولى تجد العيّنة والثانية لا تجدها، فتنقلب خمسةُ تأكيداتٍ إلى تخطٍّ بلا
  // سببٍ ظاهر في التقرير — وهو صنفُ التدهور الصامت الذي يُقرأ «تحسُّنًا» لأنّ الأحمر يقلّ.
  // **بنقرةٍ مزدوجة على التبويب لا بوترِ مفاتيح.** جرّبنا `Ctrl+K Enter` فلم يثبّت في
  // التشغيلة الأولى (الوترُ يُبتلَع حين يكون التركيز في المحرّر لحظتَها)، فبقي العطب.
  // النقرةُ المزدوجة هي إيماءةُ التثبيت نفسُها التي يستعملها المستخدم، وتصل الـDOM مباشرةً.
  try {
    await cdp.evaluate(`(() => {
      const t = [...document.querySelectorAll(".tabs-container .tab")]
        .find(x => /\\u0635\\b|\\.\\u0635/.test(x.textContent || ""));
      if (!t) return 0;
      for (const type of ["mousedown", "mouseup", "click", "dblclick"])
        t.dispatchEvent(new MouseEvent(type, { bubbles: true, detail: type === "dblclick" ? 2 : 1 }));
      return 1;
    })()`);
    await sleep(600);
  } catch { /* */ }
  // **وتبويبُ الترحيب يُثبَّت كذلك — بقياسٍ ردّه علينا التشغيلُ المتتابع.** تشغيلةٌ ثانية
  // على النسخة نفسها أبلغت «صفحة الترحيب: لم تنفتح» بينما الأولى قاستها: السببُ أنّ
  // ‏`.extension-editor` وغيرَه يُفتَح في **تبويب المعاينة**، وتبويبُ المعاينة واحدٌ يُستبدَل
  // — فابتلع الترحيبَ. تثبيتُه (نقرةٌ مزدوجة) يجعل التشغيلتين قابلتين للمقارنة، وهو
  // شرطُ أن يُقرأ اختلافُ التشغيلتين انحدارًا لا صدفة.
  // ⚠️ تسميةُ التبويب **«مرحباً»** لا «ترحيب» (قِسناها)، ونقرتُه المزدوجة **لا تُثبِّته**
  // (قِسناها كذلك). فالتثبيتُ بالارتباط `Ctrl+K Shift+Enter` عبر activateWelcomeTab ثمّ
  // pinActiveTab، وشاهدُه ذهابُ صفِّ `italic` — لا مجرّدُ إرسالِ المفاتيح.
  try {
    await recoverWelcomeTab(cdp);
    if (await activateWelcomeTab(cdp)) {
      const pin = await pinActiveTab(cdp);
      if (!pin.pinnedAfter) console.log(`  [تنبيه] تثبيتُ الترحيب لم يُثبَّت: ${JSON.stringify(pin)}`);
    }
    await activateSadTab(cdp); await sleep(400);
  } catch { /* */ }
  const geo = await editorGeometry(cdp);
  const results = geometryAssertions(geo);
  const inter = await interactionAssertions(cdp);
  const design = await designAssertions(cdp);
  // اللوحات آخرًا: فتحُها يبدّل الشريط الجانبيّ واللوحة السفلى، فتقديمها يفسد ما بعدها.
  const panels = await panelAssertions(cdp);
  const ux = await rtlOrderAssertions(cdp);
  return [...results, ...inter, ...design, ...panels, ...ux];
}
