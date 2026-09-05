// إقلاعُ محرابٍ في المتصفّح — بلا خادم.
//
// ‏`create()` هي كلُّ ما يُصدِّره بناءُ `vscode-web` المنبعيّ. وما نمرّره لها هنا هو
// **كلُّ هويّة محراب**: لا `product.json` في هذا البناء، فالإعدادُ يأتي من الصفحة.
//
// وما لا يُمرَّر مقصودٌ كذلك: لا `remoteAuthority` — ومن غيابه ينشأ كلُّ شيءٍ آخر.
// مضيفُ الامتدادات يعمل في **عاملِ ويب** لا في عمليّةِ Node، فلا طرفيّةَ ولا تصريفَ
// ولا خادمَ لغةٍ أصليّ. وهذا هو الثمنُ المدفوعُ عن قصد مقابل ألّا يكون خلف الصفحة
// جهازٌ يُخترَق.
//
// ⚠️ مصدرُ الحقيقة. ‏`build/patch_web_host.py` ينسخه إلى الشجرة المبنيّة ويؤكّد
//    التطابق. لا يُحرَّر هناك.

const boot = globalThis.__mihrabBoot || { ok() {}, fail() {} };

// ── الهويّة: مصدرٌ واحدٌ لا اثنان ──
// كانت مكتوبةً هنا حرفيًّا، فافترقت عن `product-overrides/product.json` في خمسةِ
// مفاتيح خلال أسبوع: روابطُ توثيقٍ لا وجودَ لها، و`controlUrl` — قائمةُ الإضافات
// المحظورة من Eclipse، وهي **حمايةٌ** لا زينة — سقطت بصمت.
// فصار البناءُ يشتقُّ `product.web.js` من ملفّ التجاوزات نفسِه، ونقرؤه هنا. الانحرافُ
// ممتنعٌ بالبناء لا بالانضباط.
const product = globalThis._MIHRAB_PRODUCT;
if (!product) {
  boot.fail('إعدادُ المنتَج غيرُ محمَّل (product.web.js) — بناءٌ ناقص.');
  throw new Error('mihrab: _MIHRAB_PRODUCT missing');
}

// أصلُنا موثوقٌ بداهةً: بدونه يستجوب المستخدمَ حوارُ حمايةِ روابطَ عند كلّ نقرةٍ
// داخليّة. ويُقرأ من `location` لا يُكتَب نصًّا — الحزمةُ نفسُها قد تُخدَم من نطاقٍ
// آخر أو من مسارٍ فرعيّ.
const trusted = (product.linkProtectionTrustedDomains || []).slice();
if (trusted.indexOf(location.origin) < 0) { trusted.push(location.origin); }

try {
  // استيرادٌ **ديناميّ** لا ساكن: الساكنُ يُقيَّم قبل أن يُنفَّذ سطرٌ واحدٌ من هذا
  // الملفّ، فلو فشل تحميلُ الحزمة (404 أو نوعُ MIME خاطئ — أرجحُ عطبِ نشرٍ ثابت)
  // ما بلغَنا الخبرُ أصلًا. وشاشةُ الإقلاع في `index.html` تلتقط ما يفلت من هنا.
  const { create } = await import('./out/vs/workbench/workbench.web.main.internal.js');

  create(document.body, {
    productConfiguration: { ...product, linkProtectionTrustedDomains: trusted },

    // ── الـwebviews تُخدَم من أصلِنا ──
    // ⚠️ تركُ هذا فارغًا **لا** يخدمها محلّيًّا كما ظُنّ أوّلَ مرّة: المنبعُ يرتدّ إلى
    // `https://{{uuid}}.vscode-cdn.net/…` (environmentService.ts). فمعاينةُ Markdown
    // كانت تُرسل عنوانَ الزائر إلى شبكة مايكروسوفت ثمّ ترجع 404، والقرارُ المُعلَن
    // «لا شبكةَ منبع» يُنقَض في الموضع الذي يعلنه.
    // وأصولُ الـwebview مشحونةٌ في شجرتنا أصلًا، فتُخدَم منها.
    //
    // والثمنُ يُقال لا يُخفى: بلا نطاقٍ فرعيٍّ لكلّ webview (‏`{{uuid}}`) تشترك
    // الـwebviews مع الورشة في الأصل نفسِه — فلا عزلَ بينها وبين تخزينِ الورشة.
    // وهذا مقبولٌ هنا لأنّ الامتدادات تعمل في عاملٍ يملك واجهةَ المحرِّر كاملةً على
    // أيّ حال. العزلُ الحقيقيُّ يحتاج شهادةَ wildcard ونطاقًا فرعيًّا لكلّ إطار.
    webviewEndpoint: new URL('out/vs/workbench/contrib/webview/browser/pre/',
                             document.baseURI).toString(),

    // ── ما يفتحه أوّلَ مرّة ──
    // مساحةٌ فارغةٌ لا مجلّد: لا نظامَ ملفّاتٍ على خادمٍ نفتح منه. والزائرُ يفتح
    // مجلّدًا من **جهازه** عبر File System Access.
    workspaceProvider: {
      workspace: undefined,
      trusted: true,
      async open() { return false; }
    },

    windowIndicator: {
      label: '$(globe) محراب في المتصفّح',
      tooltip: 'محرابٌ يعمل في متصفّحك — بلا خادمٍ وبلا تثبيت',
      command: ''
    },

    // الاسمُ الصحيح `enableWorkspaceTrust` لا `workspaceTrustEnabled`: الأخيرُ ليس في
    // ‏`IWorkbenchConstructionOptions` فيُتجاهَل صامتًا، وكانت النتيجةُ تتحقّق
    // بالمصادفة (`disableWorkspaceTrust = !options.enableWorkspaceTrust`) لا بالقرار.
    // ولا شيءَ يُنفَّذ خارج عاملِ الويب أصلًا، فالسؤالُ عن الثقة بلا معنًى هنا.
    enableWorkspaceTrust: false,

    configurationDefaults: {
      'window.commandCenter': true,
      // اسمُ السمة **حرفيٌّ** ويجب أن يطابق `label` في mihrab-themes/package.json.
      // كان «محراب الداكن» والصوابُ «محراب الداكنة»، فكانت الورشةُ ترتدّ إلى
      // ‏Dark Modern — أي أنّ محرابَ المتصفّح كان يبدو VS Code. يحرسه [WEB-03].
      'workbench.colorTheme': 'محراب الداكنة',
      'workbench.iconTheme': 'mihrab-icons',
      // لوحُ الترحيب **موجودٌ ومعرَّبٌ في هذه الشجرة** (رقعتا welcome_rtl و
      // walkthroughs_drop تعملان على `src/` فتدخلان الشجرتين). و`'none'` كانت تُخفيه
      // فتترك الزائرَ الأوّلَ أمام فراغ.
      'workbench.startupEditor': 'welcomePageInEmptyWorkbench',
      'editor.fontFamily': "'Kawkab Mono', 'Noto Sans Mono', monospace",
      'editor.fontLigatures': false,
      'files.autoSave': 'afterDelay'
    },

    developmentOptions: { logLevel: 3 }   // Info: لا ضجيجَ في وحدة التحكّم
  });

  // ‏`create` لا تعيد وعدًا بالجاهزيّة؛ فنُخفي شاشةَ الإقلاع حين تظهر الورشةُ فعلًا لا
  // حين تعود الدالّة — الفرقُ ثوانٍ على اتّصالٍ بطيء.
  const seen = new MutationObserver(() => {
    if (document.querySelector('.monaco-workbench')) {
      seen.disconnect();
      boot.ok();
      capabilityNotice();
    }
  });
  seen.observe(document.body, { childList: true, subtree: true });
} catch (err) {
  boot.fail('تعذّر إقلاعُ المحرِّر: ' + ((err && err.message) || err));
  console.error('[محراب]', err);
}

// ── قُل ما لا يعمل **قبل** أن يُجرَّب ──
// «فتح مجلّد» مطبوعٌ على الشاشة الأولى، ويفشل على فايرفوكس وسفاري. وحوارُ المنبع
// حين يظهر يَعِد بـ«مستودعٍ بعيد» لا وجودَ له هنا، ويُحيل إلى وثيقةٍ إنجليزيّةٍ على
// ‏aka.ms. فالتحذيرُ يسبق الضغطةَ ولا يتبعها.
//
// شريطٌ في الصفحة لا إشعارُ ورشة: طبقةُ الإقلاع لا تملك خدماتِ الورشة، وهذا يعمل
// أيًّا كان ما يجري بالداخل.
function capabilityNotice() {
  // **مفتاحان لا مفتاحٌ واحد.** كان الشرطُ `if (!noFolders && seen)`، فزائرُ فايرفوكس
  // يرى الشريطَ في **كلّ زيارةٍ مهما ضغط «فهمت»** — وزرٌّ لا يفي بوعده يعلّم
  // المستخدمَ ألّا يثق بالأزرار. فلكلّ رسالةٍ إغلاقُها.
  const KEY = 'mihrab.web.notice.v1';
  const KEY_FS = 'mihrab.web.notice.nofs.v1';
  const noFolders = !('showDirectoryPicker' in globalThis);
  const key = noFolders ? KEY_FS : KEY;
  try { if (localStorage.getItem(key)) { return; } } catch { /* تخزينٌ محجوب */ }

  // سطرٌ رئيسٌ لحالةِ الزائر، وسطرٌ ثانٍ أخفتُ **لا يسقط أبدًا**.
  // كانت الرسالتان بديلتين، فزائرُ فايرفوكس لا يرى قطُّ «ملفّاتُك تبقى على جهازك» —
  // وهي أثمنُ ما تقوله الصفحة: قيدُ المجلّدات إزعاج، وأمانُ الملفّات **سببُ البقاء**.
  // فكان الاعتذارُ يطرد الوعد. وتسعُ كلماتٍ خافتةٍ ليست جدارَ نصّ.
  const lead = noFolders
    ? 'متصفّحك لا يفتح المجلّدات — تحتاج Chrome أو Edge. '
      + 'ويبقى فتحُ الملفّات المفردة وسحبُها إلى النافذة يعمل.'
    : 'محرابٌ يعمل في متصفّحك بلا خادم — ولا طرفيّةَ ولا تشغيل: تلك في نسخة المكتب.';
  const tail = 'ملفّاتُك تبقى على جهازك؛ لا خادمَ خلف هذه الصفحة يقرؤها.';

  const bar = document.createElement('div');
  bar.setAttribute('role', 'status');
  bar.dir = 'rtl';
  // ⚠️ `bottom: 0` كان **يحجب شريطَ الحالة كاملًا** — ومعه مؤشّرُ «محراب في
  //    المتصفّح»، أي أنّه يحجب الجملةَ التي يقولها هو نفسُه. وشريطُ حالةِ الورشة
  //    ‏22px، فنرتفع فوقه. (والحلُّ الصحيحُ بانرٌ داخل تخطيط الورشة — يحتاج امتدادَ
  //    ويبٍ لا نملكه بعد؛ مسجَّلٌ دَينًا.)
  bar.style.cssText = 'position:fixed;inset-inline:0;bottom:22px;z-index:9998;'
    + 'background:#13302b;color:#cfe8e3;border-top:1px solid #2ec4a6;'
    + 'padding:.85rem 1.2rem;display:flex;gap:1rem;align-items:center;'
    + 'font:13px/1.9 "Noto Sans Arabic",system-ui,sans-serif';

  const body = document.createElement('div');
  body.style.flex = '1';
  const l1 = document.createElement('div');
  l1.textContent = lead;
  const l2 = document.createElement('div');
  l2.textContent = tail;
  l2.style.cssText = 'opacity:.7;font-size:12px';
  body.appendChild(l1);
  body.appendChild(l2);

  const close = document.createElement('button');
  close.type = 'button';
  close.textContent = 'فهمت';
  close.style.cssText = 'font:inherit;color:#0d1f1c;background:#2ec4a6;border:0;'
    + 'border-radius:4px;padding:.3rem 1rem;cursor:pointer';
  close.addEventListener('click', () => {
    bar.remove();
    try { localStorage.setItem(key, '1'); } catch { /* تخزينٌ محجوب */ }
  });

  bar.appendChild(body);
  bar.appendChild(close);
  document.body.appendChild(bar);
}
