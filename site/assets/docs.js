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
	/* ⚠️ **زرُّ إغلاقٍ داخل الدرج، وقفلُ الخلفيّة.** على الهاتف يقع «القائمة» تحت
	   الدرج المفتوح (قِيس: ‎360‎ و‎412‎) فلا يُغلقه، ولا Escape هناك، ويبقى شريطُ
	   حاجبٍ ‎60‎ بكسلًا. والصفحةُ كانت تمرّ تحت الدرج بالإصبع (‏285–412 بكسلًا)
	   فيفقد الزائرُ موضعَه عند الإغلاق. `html.nav-open` يقفلها مع CSS. */
	var navClose = null;
	if (nav && navBtn) {
		navClose = document.createElement('button');
		navClose.type = 'button';
		navClose.className = 'icon-btn nav-close';
		navClose.setAttribute('aria-label', 'إغلاق القائمة');
		navClose.textContent = '✕ إغلاق';
		nav.insertBefore(navClose, nav.firstChild);
		navClose.addEventListener('click', function () { closeNav(); });
	}
	/* ⚠️ **وما خلف الدرج خاملٌ (`inert`) ما دام مفتوحًا.** قِيس (الجولة ‎14‎، ‎360‎
	   و‎412‎ و‎768‎ بلوحة مفاتيح): بعد آخرِ رابطٍ في الدرج يمضي Tab إلى «app.mihrab.dev»
	   و«انسخ» خلف الحاجب — والجذرُ مقفولُ التمرير فلا تتبع الصفحةُ البؤرةَ: بؤرةٌ
	   لا تُرى. الحاجبُ خارج القائمة فيبقى قابلًا للنقر. */
	function setInert(on) {
		Array.prototype.forEach.call(
			document.querySelectorAll('.site-header, .site-footer, .layout > :not(.site-nav)'),
			function (el) { el.inert = on; });
	}
	function closeNav() {
		if (!nav) { return; }
		nav.classList.remove('open');
		document.documentElement.classList.remove('nav-open');
		setInert(false);
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
			document.documentElement.classList.toggle('nav-open', open);
			if (scrim) { scrim.hidden = !open; }
			navBtn.setAttribute('aria-expanded', String(open));
			setInert(open);
			/* البؤرةُ إلى زرّ الإغلاق: الفاتحُ صار تحت الدرج، ولوحيٌّ بلوحةِ مفاتيحَ
			   يبدأ التبويبَ من داخل ما فُتح لا من خلفه. */
			if (open && navClose) { navClose.focus(); }
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

	/* المنطوقُ سطرٌ قصيرٌ يصف العدد لا القائمةُ كلُّها — انظر التعليل في `sitegen/templates.py`.
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
		   المحرِّر (انظر `alt` في `build.py`، و`glossary_aliases` في `sitegen/text.py`). */
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
		/* ⚠️ **والوعدُ أعلاه كان مكسورًا على Chromium/Edge**: `input[type=search]`
		   يمسح نصَّه بنفسه عند Escape (سلوكٌ أصليّ) ويُطلق `input` فيُخفي النتائج —
		   قِيس على الحيّ (الجولة ‎15‎): بعد Escape واحدة القيمةُ `""`. فتُمنَع
		   الحركةُ الأصليّة **ما دامت النتائجُ ظاهرة**: الضغطةُ الأولى تطوي القائمة
		   وتُبقي السؤال، والثانيةُ — والقائمةُ مطويّة — تمسح النصَّ كما اعتاد الزائر. */
		document.addEventListener('keydown', function (e) {
			if (e.key !== 'Escape') { return; }
			boxes.forEach(function (b) {
				if (!b.results.hidden) {
					e.preventDefault(); show(b, false); announce(b, '');
					if (b.results.contains(document.activeElement)) { b.input.focus(); }
				}
			});
		});
		/* ⚠️ **والأسهمُ تسير في النتائج.** الحقلُ يعلن `role="combobox"
		   aria-autocomplete="list"` — وعدٌ للوحة المفاتيح بأنّ ↓ يدخل القائمة —
		   وكان ↓ وEnter لا يفعلان شيئًا (قِيس على الحيّ: البؤرةُ تبقى في الحقل
		   والعنوانُ لا يتغيّر). فـ↓ من الحقل يركّز أوّلَ نتيجة، و↓/↑ بين النتائج،
		   و↑ من الأولى يعود إلى الحقل؛ وEnter على رابطٍ مركَّزٍ يفتحه بلا شيفرة.
		   Tab يبقى كما هو: الروابطُ في ترتيب التبويب أصلًا. */
		function moveIn(b, from, dir) {
			var links = b.results.querySelectorAll('a');
			if (!links.length) { return false; }
			var i = Array.prototype.indexOf.call(links, from);
			var next = i === -1 ? (dir > 0 ? 0 : links.length - 1) : i + dir;
			if (next < 0) { b.input.focus(); return true; }
			if (next >= links.length) { return true; }
			links[next].focus();
			return true;
		}
		boxes.forEach(function (b) {
			b.input.addEventListener('keydown', function (e) {
				if (e.key !== 'ArrowDown' || b.results.hidden) { return; }
				if (moveIn(b, null, 1)) { e.preventDefault(); }
			});
			b.results.addEventListener('keydown', function (e) {
				if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') { return; }
				var a = e.target.closest ? e.target.closest('a') : null;
				if (a && moveIn(b, a, e.key === 'ArrowDown' ? 1 : -1)) { e.preventDefault(); }
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
	/* الترشيحُ كان صامتًا لقارئ الشاشة: الصفوفُ تُخفى و`.no-results` تُظهَر ولا
	   شيءَ يُنطَق (قِيس على الحيّ: لا `aria-live` في الصفحة إلّا حقلُ الترويسة
	   الفارغ). سطرٌ بالعدد، كصندوق البحث، ومشروطٌ بتغيّر النصّ. */
	var kbdStatus = document.querySelector('.kbd-status');
	function kbdWord(n) {
		if (n === 0) { return 'لا اختصارَ يطابق'; }
		if (n === 1) { return 'اختصارٌ واحد'; }
		if (n === 2) { return 'اختصاران'; }
		if (n <= 10) { return n + ' اختصارات'; }
		return n + ' اختصارًا';
	}

	/* ⚠️ **بلا تشكيلٍ هنا أيضًا.** أسماءُ الأوامر مشكولة («فتح مجلّد»، «حفظ الكلّ»)
	   والزائرُ لا يكتب شدّة: «مجلد» كانت تقرأ «لا اختصارَ يطابق» والصفُّ أمامها
	   (قِيس على الحيّ، الجولة ‎16‎). التطبيعُ نفسُه الذي يطبّقه بحثُ الموقع
	   (‏`plain` أعلاه)، على الطرفين، ومرّةً واحدةً لكلّ صفّ. */
	function filterRows(q) {
		q = plain((q || '').trim().toLowerCase());
		var total = 0;
		Array.prototype.forEach.call(document.querySelectorAll('.kbd-section'), function (sec) {
			var shown = 0;
			Array.prototype.forEach.call(sec.querySelectorAll('tbody tr'), function (tr) {
				if (!tr._hay) { tr._hay = plain((tr.getAttribute('data-search') || '').toLowerCase()); }
				var hay = tr._hay;
				var match = !q || hay.indexOf(q) !== -1;
				tr.hidden = !match;
				if (match) { shown++; }
			});
			sec.hidden = shown === 0;
			total += shown;
		});
		if (emptyMsg) { emptyMsg.hidden = total !== 0; }
		var msg = q ? kbdWord(total) : '';
		if (kbdStatus && kbdStatus.textContent !== msg) { kbdStatus.textContent = msg; }
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

	var CODE_KEY = { Backquote: '`', Minus: '-', Equal: '=', BracketLeft: '[', BracketRight: ']',
		Backslash: '\\', Semicolon: ';', Quote: "'", Comma: ',', Period: '.', Slash: '/' };
	function chordFromEvent(e) {
		var parts = [];
		if (e.ctrlKey) { parts.push('Ctrl'); }
		if (e.metaKey) { parts.push('Cmd'); }
		if (e.shiftKey) { parts.push('Shift'); }
		if (e.altKey) { parts.push('Alt'); }
		var k = e.key;
		if (['Control', 'Shift', 'Alt', 'Meta'].indexOf(k) !== -1) { return null; }
		if (k === ' ') { k = 'Space'; }
		/* ‏المتصفّحُ يرسل `ArrowUp` والجدولُ يكتب `Up` كما يكتبه المحرّر — فكان «Alt+Up»
		   (نقلُ السطر) وكلُّ صفٍّ بسهمٍ لا يُلتقَط أبدًا. */
		if (/^Arrow(Up|Down|Left|Right)$/.test(k)) { k = k.slice(5); }
		/* ⚠️ **المحرفُ المطبوعُ ليس المفتاح.** على لوحةٍ عربيّة `Ctrl+S` تصل `key="س"`،
		   و`Shift` يقلب «`» إلى «~» و«[» إلى «{»، وOption على ماك يقلب C إلى «ç» — فكان
		   «Ctrl+س» و«Ctrl+Shift+~» يُردّان «لا أمرَ معروفًا» والصفُّ أمام الزائر. فإن لم
		   يكن المحرفُ حرفًا لاتينيًّا أو رقمًا يُقرأ موضعُ المفتاح (`e.code`) كما تكتبه
		   البيانات. والمفتاحُ الميّت (‏Option+E/U/N على ماك، و« ` » على لوحاتٍ دوليّة) يصل
		   `Dead` لا محرفًا — فيُقرأ موضعُه كذلك. */
		if ((k.length === 1 && !/^[A-Za-z0-9]$/.test(k)) || k === 'Dead' || k === 'Unidentified') {
			var c = e.code || '';
			if (/^Key[A-Z]$/.test(c)) { k = c.slice(3); }
			else if (/^Digit[0-9]$/.test(c)) { k = c.slice(5); }
			else if (CODE_KEY[c]) { k = CODE_KEY[c]; }
		}
		if (k.length === 1) { k = k.toUpperCase(); }
		parts.push(k);
		return parts.join('+');
	}

	var NO_SOFT_KEY = 'الالتقاطُ يحتاج لوحةَ مفاتيحَ خارجيّة (Bluetooth أو USB) — لوحةُ الشاشة لا تُرسل اختصارات.';
	/* ‏`chordStep` نقيّةٌ (بلا DOM) على مستوى الوحدة كي **تُنفَّذ** بـnode في [CAP-02] على
	   جدول الصفحة نفسِه، والصفوفُ تُقرأ مرّةً لا عند كلّ ضغطة (الجولة ‎17‎: كان
	   `lookup`/`isPrefix` يُعرَّفان داخل المعالج ويقسمان ‎79‎ صفًّا في كلّ ضغطة).
	   والمهلةُ باسمٍ لا رقمٍ مدفون — [CAP-02] يقيس مداها ومُصابُها يُصيب المفتاحَ لا القيمة. */
	var CHORD_WAIT_MS = 5000;
	var pendingChord = null, pendingTimer = null, chordTable = null;
	/* والتعليقُ يُلغى بأربعة: Escape، وضغطةُ IME، وفقدانُ البؤرة، والمهلة — من مكانٍ واحد. */
	function clearPending() {
		pendingChord = null;
		if (pendingTimer) { clearTimeout(pendingTimer); pendingTimer = null; }
	}
	function chordEntries() {
		return Array.prototype.map.call(document.querySelectorAll('tbody tr[data-chords]'), function (tr) {
			return { row: tr, chords: tr.getAttribute('data-chords').split('|') };
		});
	}
	/* ضغطةٌ (مع تعليقٍ سابقٍ أو بلاه) على جدولٍ ⇒ الاختصارُ الكامل، وصفُّه إن وُجد،
	   و`wait` حين لا صفَّ وهي بادئةُ تسلسلٍ ولا تعليقَ قبلها — فالتسلسلُ ضغطتان لا أكثر:
	   `Ctrl+K Ctrl+K` يُحسَم «لا أمرَ» ولا يُعلَّق ثانيةً. */
	function chordStep(chord, pending, entries) {
		if (pending) { chord = pending + ' ' + chord; }
		var row = null, prefix = false;
		entries.forEach(function (en) {
			if (!row && en.chords.indexOf(chord) !== -1) { row = en.row; }
			if (!pending && !prefix) {
				en.chords.forEach(function (x) { if (x.indexOf(chord + ' ') === 0) { prefix = true; } });
			}
		});
		return { chord: chord, row: row, wait: !pending && !row && prefix };
	}
	if (captureBtn && captureBox && captureField) {
		/* ⚠️ **على اللمس: لا لوحةَ شاشةٍ تنبثق، والتنبيهُ قبل الضغطة لا بعدها.**
		   كان النقرُ على «التقط» يستدعي لوحةَ الشاشة (‏type=text) فتأكل ‎40%‎ من
		   ‎640‎، والزائرُ يكتب فيقرأ بعدها أنّ ضغطتَه لم تُفهَم. `inputmode=none`
		   يمنع اللوحةَ الافتراضيّة (‏Chrome 66+، iOS 12.2+ بحسب MDN) ولا يمنع لوحةً ماديّةً:
		   مفاتيحُها تصل إلى الحقل المبأَّر كما هي. والجملةُ تُعرَض فورًا في
		   موضع النتيجة — فلوحيٌّ بلوحةٍ يضغط فتحلّ النتيجةُ محلَّها. */
		var coarse = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
		if (coarse) {
			captureField.setAttribute('inputmode', 'none');
			if (captureOut) { captureOut.textContent = NO_SOFT_KEY; }
		}
		/* الحالةُ الأولى تُحفَظ لتُستعاد: الإغلاقُ بـEscape كان يترك النتيجةَ الأخيرة
		   («Ctrl+K ثمّ… — اضغط الضغطةَ الثانية») فيفتح الزائرُ الصندوقَ بعد دقيقةٍ ويقرأ
		   طلبًا لا ينتظره أحد (قِيس، الجولة ‎17‎). و`dim` للتلميح لا للنتيجة. */
		var initialOut = captureOut ? captureOut.textContent : '';
		function resetOut() {
			clearPending();
			if (captureOut) { captureOut.textContent = initialOut; captureOut.classList.add('dim'); }
		}
		/* انقضاءُ المهلة وفقدانُ البؤرة سواء: التعليقُ يسقط والسطرُ يقول ما حدث. المعالجُ
		   على الحقل وحدَه لكنّ التعليقَ على مستوى الوحدة — بلا `blur` من غادر الحقلَ بعد
		   Ctrl+K وعاد خلال المهلة دُمجت ضغطتُه في تسلسلٍ لم يقصده (الجولة ‎17‎). */
		function dropPending() {
			if (!pendingChord) { return; }
			var c = pendingChord;
			clearPending();
			captureOut.textContent = '';
			var c2 = document.createElement('code');
			c2.textContent = c;
			captureOut.appendChild(c2);
			var s2 = document.createElement('span');
			s2.textContent = ' — لم تصل الضغطةُ الثانية؛ اضغط التسلسلَ من أوّله';
			captureOut.appendChild(s2);
		}
		captureBtn.addEventListener('click', function () {
			captureBox.hidden = false;
			captureField.focus();
		});
		captureField.addEventListener('keydown', function (e) {
			e.preventDefault();
			/* Escape يُغلق صندوقَ الالتقاط ويعيد البؤرةَ إلى زرّه. كان يُلتقَط اختصارًا
			   («Escape — لا أمرَ معروفًا بهذا الاختصار») ويبقى الزائرُ حبيسَ الحقل بلا
			   مخرجٍ إلّا Tab (قِيس على ‎1280‎، الجولة ‎14‎). */
			/* ويُنسى التعليقُ معه: كان Escape أثناء «Ctrl+K ثمّ…» يُغلق الصندوقَ ويُبقي
			   البادئةَ حيّة، فمن أعاد الفتحَ وضغط S وحدَها قرأ «Ctrl+K S ← حفظ الكلّ». */
			if (e.key === 'Escape') { resetOut(); captureBox.hidden = true; captureBtn.focus(); return; }
			/* ⚠️ **لوحةُ الهاتف الافتراضيّة لا تُرسل مفتاحًا.** لوحةُ أندرويد المؤلِّفة
			   (‏IME — Gboard وأخواتها) تُطلق keydown بـ`key="Unidentified"` (‏keyCode 229)
			   لضغطات الحروف — قِيس على لوحة المحاكي الافتراضيّة وحدَها، ولوحاتٌ أخرى قد تُرسل Enter وBackspace
			   مفتاحين حقيقيّين — فكانت النتيجة
			   «Unidentified — لا أمرَ معروفًا بهذا الاختصار»: تدّعي أنّها قرأت
			   اختصارًا ولم تقرأ شيئًا. ولا يُخفى الالتقاطُ باللمس: لوحيٌّ بلوحةِ
			   Bluetooth يُرسل مفاتيحَ حقيقيّة. (قِيس على محاكي أندرويد ‎16‎.)
			   و`Process` معه: هو ما يضعه Chromium وفايرفوكس في `key` أثناء تركيب
			   IME (‏keyCode 229 أيضًا)، و`isComposing` اسمُه في المواصفة — لم يُقَس
			   على فايرفوكس أندرويد ولا iOS، فتُغطّى الصورُ الثلاث ولا يُعتمَد على
			   `keyCode` المهجور وحدَه. */
			if (e.isComposing || e.key === 'Unidentified' || e.key === 'Process' || e.keyCode === 229) {
				/* «خارجيّة» لا «ماديّة»: ما يوصله حاملُ الهاتف لوحةٌ خارجيّة، وهذا اسمُها عنده. */
				/* وضغطةٌ لا تُفهَم تُسقِط التعليقَ: لا تُدمَج المفهومةُ التالية في تسلسلٍ لم يُقصَد. */
				clearPending();
				captureOut.textContent = 'لم تصل ضغطةٌ مفهومة — ' + NO_SOFT_KEY;
				return;
			}
			var chord = chordFromEvent(e);
			if (!chord) { return; }
			/* ⚠️ **التسلسلُ ضغطتان والالتقاطُ كان ضغطةً.** `Ctrl+K` وحدَه ليس اختصارًا
			   لكنّه بادئةُ أربعةٍ (‏`Ctrl+K Ctrl+S`…) و`Cmd+K` بادئةُ اثنين — ستّةُ
			   تسلسلاتٍ في keybindings.json (عُدَّت، الجولة ‎17‎) — فكان يردّ «لا أمرَ
			   معروفًا» ولا يمكن التقاطُ تسلسلٍ أبدًا (قِيس، الجولة ‎16‎). فإن لم تطابق
			   الضغطةُ وحدَها وكانت بادئةَ تسلسلٍ عُلِّقت وانتظرت الثانية كما يفعل المحرّر —
			   إلّا أنّ المحرّرَ ينتظر بلا مهلةٍ حتّى تُفقَد البؤرة، وهنا مهلةُ `CHORD_WAIT_MS` (خمسُ ثوانٍ)
			   **اختيارٌ لا قياس**: حقلٌ في صفحةٍ لا يُبقي حالةً خفيّةً إلى الأبد. */
			if (!chordTable) { chordTable = chordEntries(); }
			var step = chordStep(chord, pendingChord, chordTable);
			clearPending();
			chord = step.chord;
			if (step.wait) {
				pendingChord = chord;
				captureOut.textContent = '';
				captureOut.classList.remove('dim');
				var c1 = document.createElement('code');
				c1.textContent = chord;
				captureOut.appendChild(c1);
				var s1 = document.createElement('span');
				s1.textContent = ' ثمّ… — بادئةُ تسلسل: اضغط الضغطةَ الثانية';
				captureOut.appendChild(s1);
				/* ⚠️ **المهلةُ تُقال لا تُضمَر.** كانت ثلاثَ ثوانٍ تنقضي والرسالةُ باقيةٌ تطلب
				   الضغطةَ الثانية، فيضغط الزائرُ S ويقرأ «S — لا أمرَ معروفًا» — الصفحةُ طلبت
				   ثمّ أنكرت (قِيس، الجولة ‎17‎). فعند الانقضاء تُبدَّل الرسالةُ وتقول ما
				   حدث. وخمسُ ثوانٍ لا ثلاث: قراءةُ الرسالة وحدَها ~‎2‎ ثانية لمن يراها أوّلَ
				   مرّة، ثمّ إيجادُ المفتاح — والمحرّرُ نفسُه لا يُمهل أصلًا. */
				pendingTimer = setTimeout(dropPending, CHORD_WAIT_MS);
				return;
			}
			var found = step.row;
			captureOut.textContent = '';
			captureOut.classList.remove('dim');
			var code = document.createElement('code');
			code.textContent = chord;
			captureOut.appendChild(code);
			var span = document.createElement('span');
			/* الاسمُ وحدَه لا الملاحظةُ التي تحته (‏`.kbd-note`) — النتيجةُ سطرٌ يُقرأ بعينٍ واحدة. */
			span.textContent = found
				? ' ← ' + (found.querySelector('td .cmd-name') || found.querySelector('td')).textContent
				: ' — لا أمرَ معروفًا بهذا الاختصار';
			captureOut.appendChild(span);
			/* الصفُّ المُلتقَط يُعلَّم (‏`.kbd-hit`) حتّى الالتقاطةِ التالية: التمريرُ
			   يضعه وسطَ خمسةِ صفوفٍ والنتيجةُ فوقُ خارجَ الشاشة (قِيس على ‎360‎). */
			var prev = document.querySelector('tr.kbd-hit');
			if (prev) { prev.classList.remove('kbd-hit'); }
			if (found) {
				found.classList.add('kbd-hit');
				if (filterInput) { filterInput.value = ''; filterRows(''); }
				found.scrollIntoView({ block: 'center' });
			}
		});
		captureField.addEventListener('blur', dropPending);
	}
}());
