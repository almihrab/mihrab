"use strict";
/**
 * إقلاعُ محراب المبكّر [WEB-09] — **ملفٌّ مستقلٌّ لا كتلةٌ داخل الصفحة**.
 *
 * ## لماذا خرج من `index.html`
 * سياسةُ أمانِ المحتوى على الصفحة تحتاج `'unsafe-inline'` في `script-src` ما دام فيها
 * سكربتٌ داخليّ — وذلك المفتاحُ يُبطِل أنفعَ ما في السياسة: يسمح لأيّ حقنٍ ناجحٍ أن
 * يُنفَّذ. والبدائلُ ثلاثة: نونس (يحتاج خادمًا يولّده لكلّ طلب، ولا خادمَ خلف هذه
 * الصفحة أصلًا)، أو بصمةُ `sha256` (تتغيّر مع كلّ تعديل حرفٍ في هذا الكود، فتُنسى
 * فتُشَلّ الصفحةُ بصمت)، أو ملفٌّ مجاورٌ يغطّيه `'self'`. والثالثُ وحدَه يبقى صحيحًا
 * بلا صيانة.
 *
 * ## والترتيبُ محفوظ
 * وسمٌ **كلاسيكيٌّ** (لا `type="module"`) قبل وسوم الوحدات: الكلاسيكيُّ ينفَّذ عند
 * بلوغ المُحلِّل إيّاه، والوحداتُ مؤجَّلةٌ بحكم التعريف. فـ`_VSCODE_FILE_ROOT` مضبوطٌ
 * قبل أن تُحمَّل أوّلُ وحدة — وهو شرطُ حلِّ مساراتِ العمّال والأصول.
 *
 * ⚠️ مصدرُ الحقيقة هنا. `build/patch_web_host.py` ينسخه ويؤكّد تطابقَه بايتًا ببايت.
 */
// لازمٌ **قبل** أيّ وحدة: الحزمةُ تحلّ مساراتِ العمّال والأصولِ منه.
globalThis._VSCODE_FILE_ROOT = new URL('out/', document.baseURI).toString();
// ولغةُ النواة: `out/nls.messages.js` مخبوزٌ عربيًّا، فليُعلَن ذلك. بدونه تعود
// `platform.language` إلى `'en'` فوق واجهةٍ عربيّة — واختلافُهما يقلب قراراتٍ
// تعتمد اللغةَ لا الاتّجاه.
globalThis._VSCODE_NLS_LANGUAGE = 'ar';
performance.mark('mihrab/willLoadWorkbench');

// ── شاشةُ الإقلاع: آلةُ حالةٍ صغيرةٌ **مضمَّنةٌ هنا لا في `boot.js`** ──
// والسببُ واحدٌ حاسم: أخطرُ عطبِ نشرٍ ثابتٍ هو ألّا تُحمَّل الحزمةُ أصلًا (404 أو
// نوعُ MIME خاطئ). عندها لا يُنفَّذ `boot.js` إطلاقًا — فلو سكن المُلتقِطُ فيه لَما
// وُجد من يبلّغ، ورأى الزائرُ شريطًا يدور إلى الأبد.
(function () {
  var hint = document.getElementById('mihrab-hint');
  var boot = document.getElementById('mihrab-boot');
  var done = false, failed = false;

  // مراحلُ صادقةٌ بلا ادّعاءِ نسبة: لا نعرف كم نزل، فنقول ما نعرف فقط.
  var STAGES = [
    [3000,  'تُحمَّل الحزمة — نحو ٥ م.ب في أوّل زيارة.'],
    [15000, 'ما زال التحميل جاريًا. تُخزَّن الحزمةُ في متصفّحك، فلن تتكرّر هذه الانتظارة.'],
    [60000, 'طال الأمر أكثر من المعتاد — الاتّصال بطيءٌ على ما يبدو. الانتظارُ ما زال مُجديًا.'],
    // بلا هذه كان بين الستّين والمئةِ وعشرين صمتٌ كامل، ثمّ ينقلب «الانتظارُ
    // مُجدٍ» فشلًا **فجأة**. والتمهيدُ للفشل جزءٌ من الصدق.
    [100000, 'قاربنا حدَّ الانتظار. إن لم يكتمل خلال ثوانٍ فسنعرض لك خيارَ إعادة المحاولة.']
  ];
  var timers = STAGES.map(function (s) {
    return setTimeout(function () {
      if (!done && !failed && hint) { hint.textContent = s[1]; }
    }, s[0]);
  });

  // 120 ثانيةً لا 30. والحسابُ صُحِّح بعد قياس: 4.6 م.ب **تنزيلًا** (لا 17 على
  // القرص — nginx يضغط) ⇒ نحو 5 ث على 1 م.ب/ث، ونحو 15 ث على شبكةٍ جوّالةٍ
  // بطيئة. فالمئةُ وعشرون هامشٌ سخيٌّ عمدًا: الشبكاتُ تتعثّر وتستأنف، ومهلةٌ
  // ضيّقةٌ تقتل إقلاعًا سليمًا ثمّ تلوم المستخدم. والرقمُ الأوّلُ كان مبنيًّا على
  // حجم القرص — عددٌ صحيحٌ عن الشيء الخطأ.
  var deadline = setTimeout(function () {
    fail('لم يكتمل تحميلُ محراب. قد يكون الاتّصالُ انقطع، أو منع المتصفّحُ جزءًا من الملفّات.');
  }, 120000);

  // ⛔ **لا `aria-busy` على `#mihrab-boot`.** وُضِعت هنا ظنًّا أنّها تُحسِّن
  //    الوصول، وهي تعكس نيّتَها: `aria-busy="true"` على السلف يأمر قارئَ الشاشة
  //    بـ**كتم** التحديثات الحيّة في شجرته. و`#mihrab-hint` بداخله يحمل
  //    `role="status" aria-live="polite"` — فالمراحلُ الأربعُ التي كُتبت لتُطمئن
  //    الكفيفَ كانت تُكتَم جميعًا، ومعها `role="alert"` عند الفشل (لأنّ الرايةَ
  //    لا تُرفَع أبدًا). صمتٌ مئةً وعشرين ثانيةً ثمّ صمتٌ آخر.
  //    والحالةُ تُقال بالنصّ المتدرّج نفسِه؛ لا حاجةَ إلى رايةٍ تكتمه.

  function clearTimers() { timers.forEach(clearTimeout); clearTimeout(deadline); }

  function ok() {
    if (done) { return; }
    done = true; clearTimers();
    if (boot) { boot.classList.add('gone'); setTimeout(function () { boot.remove(); }, 400); }
    performance.mark('mihrab/didLoadWorkbench');
  }

  function fail(msg, detail) {
    // ⛔ الشرطُ الحاكم: لا تُرسَم شاشةُ فشلٍ فوق ورشةٍ **تعمل**. الشاشةُ
    // `inset:0; z-index:9999`، فرسمُها على إقلاعٍ سليمٍ يحجب المحرِّرَ حجبًا كاملًا
    // وإلى الأبد بلا مخرج. وأيُّ خطأٍ ثانويٍّ من امتدادٍ كان يفعل ذلك.
    if (done || failed || document.querySelector('.monaco-workbench')) { return; }
    failed = true; clearTimers();
    if (!boot) { return; }
    boot.innerHTML = '';
    var h = document.createElement('div'); h.className = 'name'; h.textContent = 'محراب';
    var e = document.createElement('div'); e.className = 'err';
    e.setAttribute('role', 'alert'); e.textContent = msg;
    // تفصيلٌ تقنيٌّ **دون** الجملة لا داخلَها: يقرأ الإنسانُ الأولى، ويصوّر
    // المُبلِّغُ الثانية. و`dir=ltr` لأنّ اسمَ الملفّ لاتينيٌّ في سطرٍ عربيّ.
    if (detail) {
      var d = document.createElement('div');
      d.dir = 'ltr';
      d.style.cssText = 'opacity:.55;font:12px ui-monospace,monospace;direction:ltr';
      d.textContent = detail;
      e.appendChild(document.createElement('br'));
      e.appendChild(d);
    }
    var b = document.createElement('button');
    b.type = 'button'; b.textContent = 'أعِد المحاولة';
    b.addEventListener('click', function () { location.reload(); });
    boot.appendChild(h); boot.appendChild(e); boot.appendChild(b);
    b.focus();
  }

  // ⚠️ **الوسيطُ الثالث `true` هو كلُّ الفائدة.** أخطاءُ الموارد — وسمُ
  // `<script>` يرجع 404 أو نوعَ MIME خاطئًا — **لا تصعد** إلى `window`؛ تُرى في
  // طور الالتقاط وحدَه. فمستمِعٌ بلا `capture` لا يرى العطبَ الذي كُتب لأجله،
  // ويبقى الزائرُ أمام شريطٍ يدور ١٢٠ ثانيةً كاملة. (وهذا ما وقع فعلًا: نُقلت
  // آلةُ الحالة إلى هنا خصّيصًا لالتقاطه، ثمّ لم تلتقطه.)
  //
  // وبلا `{ once: true }`: أوّلُ خطأٍ ليس بالضرورة الحاسم، وحرقُ المُلتقِط عليه
  // يُعمينا عن الفشل الحقيقيّ. والحراسةُ في `fail` هي التي تمنع الإنذارَ الكاذب.
  addEventListener('error', function (ev) {
    var t = ev.target;
    // موردٌ سقط: `ev.target` وسمٌ لا `window`، ولا رسالةَ فيه.
    if (t && t !== globalThis && (t.tagName === 'SCRIPT' || t.tagName === 'LINK')) {
      var src = t.src || t.href || '';
      console.error('[محراب] موردٌ لم يُحمَّل:', src);
      // موردٌ من الحزمة ⇒ فشلٌ حاسم. وأصلٌ خارجيٌّ (سوقُ الإضافات) ⇒ لا.
      if (src.indexOf(location.origin) === 0 || src.charAt(0) === '/') {
        // جملةٌ للإنسان، واسمُ الملفّ للمُبلِّغ في سطرٍ ثانٍ (‏`fail` يرسمه).
        // اسمُ حزمةٍ داخليٍّ في متن الرسالة يُحمِّل الزائرَ تشخيصَ عطبِ خادمِنا.
        fail('لم يكتمل تنزيلُ محراب. جرّب إعادةَ التحميل — وإن تكرّر '
             + 'فالعطبُ عندنا لا عندك.', src.split('/').pop());
      }
      return;
    }
    console.error('[محراب]', ev.message || ev);
    fail('تعذّر تحميلُ المحرِّر. جرّب إعادةَ التحميل.');
  }, true);
  addEventListener('unhandledrejection', function (ev) {
    console.error('[محراب]', (ev.reason && ev.reason.message) || ev.reason);
    fail('تعذّر تحميلُ المحرِّر. جرّب إعادةَ التحميل.');
  });

  globalThis.__mihrabBoot = { ok: ok, fail: fail };
})();
