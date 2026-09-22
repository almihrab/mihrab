/* محراب — توثيق. سلوكُ الصفحة: سمة، درج، بحث، اختصارات.
   بلا اعتماديّات: GitHub Pages يخدم ملفًّا ساكنًا، فلا مسوّغَ لحزمة. */
(function () {
	'use strict';

	/* ── السمة: الداكن افتراضًا، والاختيارُ يُحفَظ ── */
	var root = document.documentElement;
	try {
		var saved = localStorage.getItem('mihrab-docs-theme');
		if (saved) { root.setAttribute('data-theme', saved); }
	} catch (e) { /* تخزينٌ محجوب — نبقى على الافتراضيّ */ }

	/* ── ‏`theme-color` يتبع **الاختيار الصريح** لا نظامَ التشغيل وحدَه ──
	   القالبُ يكتب وسيطَين مشروطَين بـ`prefers-color-scheme`، والمتصفّحُ يأخذ
	   **أوّلَ** ما يطابق. فمن نظامُه داكنٌ ثمّ اختار الفاتحَ يرى صفحةً فاتحةً
	   تحت شريطِ متصفّحٍ داكن — والشريطُ على الجوّال ثلثُ ما فوق الطيّة. فحين
	   يوجد اختيارٌ صريح نكتبه في الوسيطَين معًا: أيُّهما طابق أعطى اللونَ
	   نفسَه. وحين لا اختيار، لا نلمس شيئًا فيعود القرارُ للنظام كما يجب. */
	var THEME_BAR = { dark: '#0F1C24', light: '#F5F0E4' };
	function paintBrowserBar(mode) {
		var metas = document.querySelectorAll('meta[name="theme-color"]');
		if (!metas.length || !THEME_BAR[mode]) { return; }
		Array.prototype.forEach.call(metas, function (m) {
			m.setAttribute('content', THEME_BAR[mode]);
		});
	}
	if (root.getAttribute('data-theme')) { paintBrowserBar(root.getAttribute('data-theme')); }

	/* ── ارتفاعُ الترويسة يُقاس لا يُكتَب ──
	   ‏`.kbd-toolbar` لاصقٌ تحت الترويسة، والمراسي تحتاج هامشَ تمريرٍ بقدرها.
	   وكان `62px` مكتوبًا في CSS يدويًّا وارتفاعُها محسوبٌ من محتواها: أيُّ
	   تغييرٍ في الحشو أو حجم الخطّ يزحزحه صامتًا ويبقى الرقم. (وومضةُ `swap`
	   تزحزحه **ربعَ بكسل** لا أكثر: أطولُ عناصرها فوق ‎560px‎ هو حقلُ البحث،
	   وسطرُه `normal` أي من مقاييس الخطّ — ‎40.00‎ بـPlex و‎38.00‎ بدونه — فالترويسةُ
	   ‎65.00‎ ثمّ ‎64.75‎، وكلتاهما تُقرَّب إلى ‎65‎ فلا يتحرّك شيء. وحيث يُخفى
	   الحقلُ — تحت ‎560px‎ أو بلا سكربت — يعلوها زرُّ «نزِّل» بسطرٍ بالبكسل:
	   ‎64.75‎ ثابتةً. قِيس على ‎1280‎ و‎360‎ و‎320‎ و‎256‎. وعلى اللمس ‎69‎: العلامةُ
	   `.brand` ‎44‎ تحت `pointer: coarse`.) فتُكتَب القيمةُ
	   المقيسةُ في `--header-h`، ويُعاد القياسُ كلَّما تغيّر مقاسُ الترويسة.
	   والرقمُ في CSS احتياطُ من عطّل السكربت. وصفرٌ (طباعة، ترويسةٌ مخفيّة)
	   لا يُكتَب.
	   ⚠️ **وشريطُ الاختصارات يُقاس معها.** `.kbd-toolbar` لاصقٌ تحت الترويسة،
	   والمراسي في صفحة الاختصارات تحتاج هامشَ الاثنين لا الترويسةِ وحدَها: كانت
	   العناوينُ تهبط **خلف الشريط بـ‎53‎ بكسلًا** (قِيس: ‎h2.top 77‎ والشريطُ
	   ينتهي عند ‎130‎). وارتفاعُه يتغيّر مع العرض (كان يلتفّ صفَّين على ‎360‎: ‎112‎،
	   وثلاثةً قبل إخفاء زرّ الطباعة: ‎156‎ — قبل أن يصير الحقلُ وحدَه لاصقًا هناك)
	   — رقمٌ لا يصحّ كتابتُه في CSS
	   مرّةً واحدة. وتحت ‎560px‎ الشريطُ `display: contents` وحقلُ الترشيح وحدَه
	   لاصق — فيُقاس هو (أدناه). */
	var header = document.querySelector('.site-header');
	var toolbar = document.querySelector('.kbd-toolbar');
	function measureHeader() {
		if (header && header.offsetHeight > 0) {
			root.style.setProperty('--header-h', header.offsetHeight + 'px');
		}
		if (toolbar) {
			/* ما يلتصق هو ما يُقاس: الشريطُ كلُّه فوق ‎560px‎، وحقلُ الترشيح `.grow`
			   وحدَه تحتها (الشريطُ `display: contents` هناك فلا صندوقَ له أصلًا،
			   و`offsetHeight` له صفر). وغيرُ اللاصق لا يغطّي شيئًا فهامشُه صفر —
			   وإلّا هبطت المرساةُ تحت العنوان بفراغٍ بقدر شريطٍ ليس فوقها. */
			/* ⚠️ **و`position` المحسوبُ للشريط يبقى `sticky` وهو `contents`** — فمن
			   اختبر `position` وحدَه اختار الشريطَ وكتب صفرًا (قِيس على ‎360‎ و‎320‎:
			   `--toolbar-h: 0` والمرساةُ تهبط عند ‎81‎ **خلف حقلٍ ينتهي عند ‎134‎**،
			   أي ‎53‎ بكسلًا محجوبةً — العطبُ عينُه الذي قِيس على ‎1280‎، عاد على
			   الجوّال). فاللاصقُ هو ما له صندوقٌ **و**يلتصق. */
			var grow = toolbar.querySelector('.grow');
			var tbCS = getComputedStyle(toolbar);
			var stickyEl = tbCS.position === 'sticky' && tbCS.display !== 'contents' ? toolbar
				: (grow && getComputedStyle(grow).position === 'sticky' ? grow : null);
			root.style.setProperty('--toolbar-h', (stickyEl ? stickyEl.offsetHeight : 0) + 'px');
		}
	}
	measureHeader();
	if (typeof ResizeObserver === 'function') {
		var ro = new ResizeObserver(measureHeader);
		if (header) { ro.observe(header); }
		if (toolbar) { ro.observe(toolbar); var g0 = toolbar.querySelector('.grow'); if (g0) { ro.observe(g0); } }
	} else {
		window.addEventListener('resize', measureHeader);
	}

	/* ── التمريرُ الناعم بعد التحميل لا قبله ──
	   ‏`html.loaded` تُفعّل `scroll-behavior: smooth` في CSS. تُكتَب بعد `load`
	   وإطارين: المتصفّح يعيد تطبيقَ مرساة الدخول حتّى `load` (خطوطٌ تُبدَّل وصورٌ
	   تُقاس)، فصنفٌ أبكرُ يجعل إعادةَ التطبيق تلك تمريرةً حيّة. وقبله: `html:focus-within`
	   قِيست فاشلةً — انظر تعليلَها في CSS.
	   ⚠️ **و`document.fonts.ready` قبل الإطارين.** الخطُّ المتأخّر (‏`swap`) يغيّر
	   الأطوالَ فيعيد المتصفّحُ تطبيقَ المرساة **بعد `load`**: قِيس بخطٍّ مؤخَّرٍ ‎6s‎ على
	   ‎360‎ (الجولة الحاديةَ عشرة): `load` عند ‎6164ms‎، وإعادةُ التطبيق ‎5280→5077‎ عند
	   ‎6192‎، والصنفُ عند ‎6197‎ — **خمسُ ملّي ثوانٍ** بين قفزةٍ صامتةٍ وتمريرةٍ حيّةٍ
	   بطول ‎203‎ بكسل، ومهمّةٌ واحدةٌ طويلةٌ على هاتفٍ بطيءٍ تقلب الترتيب. فالوعدُ
	   ينتظر تطبيقَ الخطّ لا تنزيلَه، والإطاران بعده يبقيان للصور. ومن لا `fonts`
	   عنده يمضي فورًا. */
	function markLoaded() {
		var fontsReady = (document.fonts && document.fonts.ready) ? document.fonts.ready : Promise.resolve();
		fontsReady.then(function () {
			requestAnimationFrame(function () { requestAnimationFrame(function () { root.classList.add('loaded'); }); });
		});
	}
	if (document.readyState === 'complete') { markLoaded(); } else { window.addEventListener('load', markLoaded); }

	var themeBtn = document.getElementById('theme-toggle');
	if (themeBtn) {
		/* التسميةُ تصف **الوجهة** لا الحالة. والقالبُ يكتب «فاتح» ابتدائيًّا لأنّ
		   الداكنَ افتراضُنا؛ فإن كان المحفوظُ فاتحًا وجب تصحيحُها قبل أوّل نقرة،
		   وإلّا عرض الزرُّ «فاتح» على صفحةٍ فاتحةٍ أصلًا. */
		var startDark = root.getAttribute('data-theme')
			? root.getAttribute('data-theme') === 'dark'
			: !window.matchMedia('(prefers-color-scheme: light)').matches;
		themeBtn.textContent = startDark ? 'فاتح' : 'داكن';

		themeBtn.addEventListener('click', function () {
			var isDark = root.getAttribute('data-theme')
				? root.getAttribute('data-theme') === 'dark'
				: !window.matchMedia('(prefers-color-scheme: light)').matches;
			var next = isDark ? 'light' : 'dark';
			root.setAttribute('data-theme', next);
			try { localStorage.setItem('mihrab-docs-theme', next); } catch (e) {}
			themeBtn.textContent = next === 'dark' ? 'فاتح' : 'داكن';
			paintBrowserBar(next);
		});
	}

	/* ── درجُ التنقّل على الجوال ── */
	var nav = document.querySelector('.site-nav');
	var navBtn = document.getElementById('nav-toggle');
	var scrim = document.querySelector('.nav-scrim');
	function closeNav() {
		if (!nav) { return; }
		nav.classList.remove('open');
		if (scrim) { scrim.hidden = true; }
		if (navBtn) { navBtn.setAttribute('aria-expanded', 'false'); }
		/* البؤرةُ تعود إلى الزرّ الذي فتح الدرج. كانت تبقى على الرابط داخل درجٍ
		   انزلق خارجَ الشاشة (قِيس على ‎360‎: `Escape` والبؤرةُ على `.nav-app`
		   عند ‎x=384‎ من ‎360‎) — فالتبويبةُ التالية تمضي في قائمةٍ لا يراها أحد. */
		if (navBtn && nav.contains(document.activeElement)) { navBtn.focus(); }
	}
	if (navBtn && nav) {
		navBtn.addEventListener('click', function () {
			var open = nav.classList.toggle('open');
			if (scrim) { scrim.hidden = !open; }
			navBtn.setAttribute('aria-expanded', String(open));
		});
	}
	if (scrim) { scrim.addEventListener('click', closeNav); }
	document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { closeNav(); } });

	/* ── زرّ النسخ في كتل الكود ── */
	Array.prototype.forEach.call(document.querySelectorAll('pre'), function (pre) {
		var btn = document.createElement('button');
		btn.className = 'copy-btn';
		btn.type = 'button';
		btn.textContent = 'انسخ';
		btn.addEventListener('click', function () {
			var code = pre.querySelector('code');
			navigator.clipboard.writeText(code ? code.textContent : pre.textContent).then(function () {
				btn.textContent = 'نُسخ';
				setTimeout(function () { btn.textContent = 'انسخ'; }, 1400);
			});
		});
		pre.appendChild(btn);
	});

	/* ── البحث: فهرسٌ ساكن يُحمَّل عند أوّل استعمال، لا شبكةَ بعده ──

	   ⚠️ **وكلُّ صندوقٍ في الصفحة لا الأوّلُ وحدَه.** كان الربطُ بـ
	   `getElementById('site-search')`، وصفحةُ `/docs/` تحمل صندوقين: واحدًا في
	   الترويسة وآخرَ كبيرًا في وسط الصفحة. فكان الحدثُ يُربَط بحقل الترويسة،
	   و**الحقلُ الأوسطُ الضخم — أبرزُ عنصرٍ تفاعليٍّ في الصفحة — يبتلع الكتابةَ
	   ولا يردّ شيئًا أبدًا**: لا نتائج، ولا رسالة، ولا مؤشّرَ انتظار. حقلٌ يَعِد
	   ولا يفي، في الصفحة التي كلُّ غرضها أن تدلّ.

	   والفهرسُ مشتركٌ بين الصندوقين: طلبٌ واحدٌ لا طلبان، وأوّلُ من يُركَّز عليه
	   يجلبه للجميع. */
	var boxes = [];
	Array.prototype.forEach.call(document.querySelectorAll('.search-box'), function (box) {
		var input = box.querySelector('.search-input') || box.querySelector('input[type="search"]');
		var results = box.querySelector('.search-results');
		var status = box.querySelector('.search-status');
		if (input && results) {
			boxes.push({ input: input, results: results, status: status });
		}
	});
	/* حقلُ الترويسة هو ما يقصده اختصارُ «/»، وهو واحدٌ في كلّ صفحة. */
	var searchInput = document.getElementById('site-search');
	var index = null;
	var indexPending = false;

	function base() { return document.body.getAttribute('data-base') || '.'; }

	function loadIndex() {
		if (index || indexPending) { return; }
		indexPending = true;
		fetch(base() + '/search-index.json')
			.then(function (r) { return r.json(); })
			.then(function (data) {
				index = data;
				/* يُعاد الرسمُ لكلّ صندوقٍ فيه نصّ: قد يكون الزائرُ كتب أثناء
				   الجلب، وقد يكون الصندوقُ غيرَ الذي بدأ الجلب. */
				boxes.forEach(function (b) { render(b, b.input.value); });
			})
			.catch(function () { indexPending = false; });
	}

	/* الإخفاءُ والإظهارُ في موضعٍ واحد: `hidden` و`aria-expanded` يجب أن
	   يتغيّرا معًا، وفصلُهما يترك قارئَ الشاشة يسمع «مطويّ» ونتائجُ ظاهرة. */
	function show(box, on) {
		box.results.hidden = !on;
		box.input.setAttribute('aria-expanded', String(!!on));
		/* ⚠️ **والنتائجُ تحت الطيّة على الجوّال.** صندوقُ `/docs/` الأوسط يقف عند
		   ‎552–603‎ على ‎360×640‎، ونتائجُه تبدأ عند ‎607‎: قِيس (الجولة الحاديةَ عشرة)
		   **‎33‎ بكسلًا مرئيّةً من ‎282‎ وصفرٌ من أربع نتائج** — ومع لوحة المفاتيح
		   المفتوحة لا شيء. فيكتب الزائرُ «الامتداد» ويرى الصفحةَ لم تردّ. فحين يفيض
		   أسفلُ النتائج عن المنظار يُرفَع الصندوقُ إلى ما تحت الترويسة (‏`--header-h`
		   المقيسة + ‎12‎): بعده الحقلُ ‎77–128‎ والنتائجُ ‎132–414‎ (‏‎282‎ بكسلًا كلُّها
		   مرئيّة) والأربعُ كلُّها مرئيّة — أُعيد قياسُها على Chromium 1228 بترويسةٍ
		   ‎65‎ بكسلًا؛ والرقمُ يتبع الترويسةَ المقيسةَ لا قيمةً مكتوبة. ونزولًا فقط:
		   صندوقُ الترويسة لاصقٌ فوق فلا يتحرّك شيء. */
		if (on) {
			var over = box.results.getBoundingClientRect().bottom - window.innerHeight;
			if (over > 0) {
				var hh = parseFloat(getComputedStyle(root).getPropertyValue('--header-h')) || 65;
				var lift = box.input.getBoundingClientRect().top - hh - 12;
				if (lift > 0) { window.scrollBy(0, lift); }
			}
		}
	}

	/* المنطوقُ سطرٌ قصيرٌ يصف العدد لا القائمةُ كلُّها — انظر تعليل `build.py`.
	   والكتابةُ مشروطةٌ بتغيّر النصّ: إعادةُ الإسناد بالقيمة نفسِها تُعيد
	   الإعلانَ في بعض القرّاء، فيُنطَق «٧ نتائج» سبعَ مرّاتٍ على التوالي. */
	function announce(box, msg) {
		if (box.status && box.status.textContent !== msg) {
			box.status.textContent = msg;
		}
	}

	/* ‏«نتيجة/نتيجتان/نتائج» — الإفرادُ والتثنيةُ والجمعُ في العربيّة ثلاثةٌ لا
	   اثنان، و«1 نتائج» لحنٌ يسمعه قارئُ الشاشة بوضوحٍ أشدَّ ممّا تراه العين. */
	function hitsWord(n) {
		if (n === 1) { return 'نتيجةٌ واحدة'; }
		if (n === 2) { return 'نتيجتان'; }
		if (n <= 10) { return n + ' نتائج'; }
		return n + ' نتيجة';
	}

	/* والهمزةُ على الألف تُوحَّد أيضًا: «الاضافة» و«الإضافة» سؤالٌ واحدٌ عند من يكتب
	   من هاتفٍ بلا مفتاح همزة (قِيس: الأولى صفرٌ والثانيةُ ‎4‎ قبل التوحيد). */
	function plain(s) { return s.replace(/[ً-ْٰـ]/g, '').replace(/[أإآ]/g, 'ا'); }

	/* ما طابق عنوانَه يتقدّم: «الطرفية» كانت تُظهِر «الطرفيّة المدمجة» **سادسةً**
	   بعد خمس صفحاتٍ تذكرها عرَضًا — الترتيبُ ترتيبُ الفهرس لا الصلة. */
	function titleRank(p, terms) {
		var t = plain(p.title);
		return terms.every(function (w) { return t.indexOf(w) !== -1; }) ? 0 : 1;
	}

	function render(box, q) {
		var resultsBox = box && box.results;
		if (!resultsBox) { return; }
		q = (q || '').trim();
		if (!q || !index) { show(box, false); resultsBox.innerHTML = ''; announce(box, ''); return; }
		/* ⚠️ **بلا تشكيلٍ في الطرفين.** المتنُ مشكولٌ («قُصُّ السطر»، «نقطةَ توقّفٍ»)
		   والزائرُ لا يكتب حركةً واحدة: «قص السطر» و«نقطة توقف» كانتا تقرآن
		   «لا نتائج» والصفحةُ أمامهما (قِيس في الجولة الحاديةَ عشرة). فتُنزَع
		   الحركاتُ والشدّةُ والتطويلُ من السؤال ومن المتن معًا — ومرّةً واحدةً لكلّ
		   صفحة، لا مع كلّ ضغطة. و`alt` بدائلُ المسرد التي يعرفها الزائرُ من شاشة
		   المحرِّر (انظر `build.py`). */
		var terms = plain(q).split(/\s+/);
		var hits = index.filter(function (p) {
			if (!p._hay) { p._hay = plain(p.title + ' ' + p.section + ' ' + p.text + ' ' + (p.alt || '')); }
			return terms.every(function (t) { return p._hay.indexOf(t) !== -1; });
		}).map(function (p, i) { return { p: p, r: titleRank(p, terms), i: i }; })
			.sort(function (a, b) { return a.r - b.r || a.i - b.i; })
			.map(function (x) { return x.p; })
			.slice(0, 12);

		resultsBox.innerHTML = '';
		if (!hits.length) {
			/* رسالةٌ لا رابط: كانت `<a href="#">` — عنصرٌ يقبل التركيز ويُفعَّل
			   بـEnter فيقفز بالقارئ إلى رأس الصفحة ويُفقِده ما كتب. */
			var none = document.createElement('div');
			none.className = 'dim no-hits';
			none.textContent = 'لا نتائج';
			resultsBox.appendChild(none);
			show(box, true);
			announce(box, 'لا نتائج');
			return;
		}
		hits.forEach(function (p) {
			var a = document.createElement('a');
			a.href = base() + '/' + p.url;
			var strong = document.createElement('span');
			strong.textContent = p.title;
			var sm = document.createElement('small');
			sm.textContent = p.section;
			a.appendChild(strong);
			a.appendChild(sm);
			resultsBox.appendChild(a);
		});
		show(box, true);
		announce(box, hitsWord(hits.length));
	}

	boxes.forEach(function (b) {
		b.input.addEventListener('focus', loadIndex);
		b.input.addEventListener('input', function () { loadIndex(); render(b, this.value); });
	});
	if (boxes.length) {
		/* نقرةٌ خارج الصناديق تُغلقها كلَّها — مستمعٌ واحدٌ لا واحدٌ لكلّ صندوق. */
		document.addEventListener('click', function (e) {
			boxes.forEach(function (b) {
				if (!b.results.contains(e.target) && e.target !== b.input) {
					show(b, false);
				}
			});
		});
		/* ‏`Escape` يُغلق النتائجَ ويُبقي النصّ. كان يُغلق الدرجَ وحدَه، فمن فتح
		   نتائجَ بلوحة المفاتيح لم يملك طريقًا لإغلاقها إلّا مسحَ ما كتب —
		   و`Escape` هو أوّلُ ما تجرّبه اليدُ أمام لوحةٍ منسدلة. والبؤرةُ تبقى
		   في الحقل: من أغلق النتائجَ لم يطلب مغادرةَ البحث. */
		document.addEventListener('keydown', function (e) {
			if (e.key !== 'Escape') { return; }
			boxes.forEach(function (b) {
				if (!b.results.hidden) { show(b, false); announce(b, ''); }
			});
		});
		/* «/» يركّز البحث — عادةٌ راسخة عند من يقرأ توثيقًا تقنيًّا.
		   ويقصد حقلَ الترويسة لأنّه ثابتٌ في كلّ صفحة؛ فإن غاب فأوّلُ صندوق. */
		/* ⚠️ **ويُختار الهدفُ عند الضغطة لا عند التحميل، وظاهرًا.** حقلُ الترويسة
		   `display:none` تحت ‎560px‎، و`focus()` على المخفيّ لا يفعل شيئًا ولا
		   يشكو — فكان `/` يُبتلَع (‏`preventDefault`) بلا أثر، وفي `/docs/`
		   صندوقٌ أوسطُ ظاهرٌ يصلح هدفًا. ومن لا هدفَ ظاهرًا له تبقى ضغطتُه له. */
		/* ⚠️ **وفي صفحة الاختصارات حقلُ الترشيح أوّلًا.** من يقرأ جدولَ الاختصارات
		   ويضغط `/` يريد أن يرشّح **هذا الجدول**، لا أن يبحث في الموقع كلِّه —
		   والحقلُ لاصقٌ أمام عينيه على كلّ عرض، بينما حقلُ الترويسة مخفيٌّ تحت
		   ‎560px‎ فكان `/` هناك ميتًا (قِيس على ‎360‎: البؤرةُ تبقى على `body`). */
		var kbdFilter = document.getElementById('kbd-filter');
		function visibleSearch() {
			var cands = kbdFilter ? [kbdFilter] : [];
			if (searchInput) { cands.push(searchInput); }
			boxes.forEach(function (b) { cands.push(b.input); });
			for (var i = 0; i < cands.length; i++) {
				if (cands[i].offsetParent !== null) { return cands[i]; }
			}
			return null;
		}
		document.addEventListener('keydown', function (e) {
			if (e.key !== '/' || /^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) { return; }
			var target = visibleSearch();
			if (!target || document.activeElement === target) { return; }
			e.preventDefault();
			target.focus();
		});
	}

	/* ════════ صفحة ‎404‎: أين أنا؟ ════════
	   الصفحةُ واحدةٌ تُقدَّم من أصلين. نصُّها الساكن يخاطب زائرَ `mihrab.dev`
	   («محرابُ المتصفّح استقلّ بأصلٍ خاصّ»)، فمن ضلّ **على `app.mihrab.dev`
	   نفسِه** يقرأ أنّ ما يقف عليه انتقل إلى حيث يقف. فحين يطابق المضيفُ مضيفَ
	   المحرِّر تُبدَّل الفقرةُ بأخرى تقول له أين هو. وبلا سكربت يبقى النصُّ
	   العامّ — صحيحٌ من الأصل الأوّل ومحتملٌ من الثاني. */
	var notFound = document.querySelector('main.notfound[data-app-host]');
	if (notFound && location.host === notFound.getAttribute('data-app-host')) {
		var ledeSite = notFound.querySelector('.lede-site');
		var ledeApp = notFound.querySelector('.lede-app');
		if (ledeSite && ledeApp) { ledeSite.hidden = true; ledeApp.hidden = false; }
	}

	/* ════════ صفحة الاختصارات ════════ */
	var kbdTable = document.querySelector('[data-kbd-table]');
	if (!kbdTable) { return; }

	/* النظام: يُخمَّن ابتدائيًّا ثمّ يُحفَظ. عرضُ الجدولين معًا يضاعف طولَ الصفحة
	   ويجعل نصفَها ضجيجًا لكلّ قارئ. */
	var isMacDefault = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
	var platform;
	try { platform = localStorage.getItem('mihrab-docs-platform'); } catch (e) {}
	if (platform !== 'mac' && platform !== 'win') { platform = isMacDefault ? 'mac' : 'win'; }

	function applyPlatform(p) {
		platform = p;
		try { localStorage.setItem('mihrab-docs-platform', p); } catch (e) {}
		Array.prototype.forEach.call(document.querySelectorAll('.keys'), function (el) {
			el.hidden = el.getAttribute('data-platform') !== p;
		});
		Array.prototype.forEach.call(document.querySelectorAll('.seg button[data-platform]'), function (b) {
			b.setAttribute('aria-pressed', String(b.getAttribute('data-platform') === p));
		});
	}
	Array.prototype.forEach.call(document.querySelectorAll('.seg button[data-platform]'), function (b) {
		b.addEventListener('click', function () { applyPlatform(b.getAttribute('data-platform')); });
	});
	applyPlatform(platform);

	/* الترشيح: يُخفي الصفوف، ثمّ يُخفي عنوانَ أيّ قسمٍ خلا من الصفوف. */
	var filterInput = document.getElementById('kbd-filter');
	var emptyMsg = document.querySelector('.no-results');

	function filterRows(q) {
		q = (q || '').trim().toLowerCase();
		var total = 0;
		Array.prototype.forEach.call(document.querySelectorAll('.kbd-section'), function (sec) {
			var shown = 0;
			Array.prototype.forEach.call(sec.querySelectorAll('tbody tr'), function (tr) {
				var hay = (tr.getAttribute('data-search') || '').toLowerCase();
				var match = !q || hay.indexOf(q) !== -1;
				tr.hidden = !match;
				if (match) { shown++; }
			});
			sec.hidden = shown === 0;
			total += shown;
		});
		if (emptyMsg) { emptyMsg.hidden = total !== 0; }
	}
	if (filterInput) {
		filterInput.addEventListener('input', function () { filterRows(this.value); });
	}

	/* «التقط اختصارًا» — نصفُ زيارات هذه الصفحة سؤالُها «ما هذا الاختصار الذي
	   ضغطتُه بالخطأ؟» لا العكس. */
	var captureBtn = document.getElementById('capture-btn');
	var captureBox = document.querySelector('.capture-box');
	var captureField = document.getElementById('capture-field');
	var captureOut = document.querySelector('.capture-box .result');

	function chordFromEvent(e) {
		var parts = [];
		if (e.ctrlKey) { parts.push('Ctrl'); }
		if (e.metaKey) { parts.push('Cmd'); }
		if (e.shiftKey) { parts.push('Shift'); }
		if (e.altKey) { parts.push('Alt'); }
		var k = e.key;
		if (['Control', 'Shift', 'Alt', 'Meta'].indexOf(k) !== -1) { return null; }
		if (k === ' ') { k = 'Space'; }
		if (k.length === 1) { k = k.toUpperCase(); }
		parts.push(k);
		return parts.join('+');
	}

	if (captureBtn && captureBox && captureField) {
		captureBtn.addEventListener('click', function () {
			captureBox.hidden = false;
			captureField.focus();
		});
		captureField.addEventListener('keydown', function (e) {
			e.preventDefault();
			var chord = chordFromEvent(e);
			if (!chord) { return; }
			var found = null;
			Array.prototype.forEach.call(document.querySelectorAll('tbody tr[data-chords]'), function (tr) {
				if (found) { return; }
				var list = tr.getAttribute('data-chords').split('|');
				if (list.indexOf(chord) !== -1) { found = tr; }
			});
			captureOut.textContent = '';
			var code = document.createElement('code');
			code.textContent = chord;
			captureOut.appendChild(code);
			var span = document.createElement('span');
			span.textContent = found
				? ' ← ' + found.querySelector('td').textContent
				: ' — لا أمرَ معروفًا بهذا الاختصار';
			captureOut.appendChild(span);
			if (found) {
				if (filterInput) { filterInput.value = ''; filterRows(''); }
				found.scrollIntoView({ block: 'center' });
			}
		});
	}
}());
