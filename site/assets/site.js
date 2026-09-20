/* محراب — واجهةُ المنتج: تخمينُ النظام، وجلبُ مانيفست الإصدار الحيّ.
   بلا اعتماديّات، وبلا شبكةٍ إلزاميّة: الصفحةُ كاملةٌ قبل أن يعمل هذا الملفّ.

   ⚠️ القاعدةُ الحاكمة هنا: **لا نَعِد بملفٍّ لا نعرف وجودَه.** كلُّ رقمٍ معروض
   (إصدار، حجم، بصمة) يأتي من المانيفست؛ وحين لا مانيفستَ تظهر حالةُ الفراغ
   صراحةً. زرُّ تنزيلٍ يقود إلى 404 أسوأُ من غياب الزرّ. */
(function () {
	'use strict';

	function base() { return document.body.getAttribute('data-base') || '.'; }

	/* ════════════════════════════════════════════════════════════════════
	   §١ — تخمينُ النظام
	   userAgentData أوّلًا: هو المصدرُ الوحيد الذي يميّز ARM64 عن x64 على ويندوز.
	   وuserAgent يكذب هناك عمدًا (كلُّ ويندوز يقول WOW64/x64)، فالتخمينُ يُعرَض
	   للمستخدم ليُنقَض لا ليُفرَض.
	   ════════════════════════════════════════════════════════════════════ */
	var ua = navigator.userAgent || '';
	var guess = { os: 'unknown', arch: 'x64' };

	if (/Windows/i.test(ua)) { guess.os = 'windows'; }
	else if (/Mac OS X|Macintosh/i.test(ua)) { guess.os = 'mac'; }
	else if (/Linux|X11|CrOS/i.test(ua)) { guess.os = 'linux'; }

	if (/arm64|aarch64/i.test(ua)) { guess.arch = 'arm64'; }
	/* macOS لا يفصح عن Apple Silicon في userAgent إطلاقًا — يقول Intel دائمًا.
	   والأغلبيّةُ الساحقة من أجهزة macOS العاملة اليوم Apple Silicon، فالافتراضُ
	   الأنفعُ arm64، والبديلُ ظاهرٌ في الجدول تحته مباشرةً. */
	if (guess.os === 'mac') { guess.arch = 'arm64'; }

	var OS_AR = { windows: 'ويندوز', mac: 'macOS', linux: 'لينكس', unknown: 'نظامك' };

	/* التنقيحُ الدقيق يصل متأخّرًا (وعدٌ غيرُ متزامن). حين يصل نُعيد الرسم. */
	function refineArch(done) {
		var d = navigator.userAgentData;
		if (!d || !d.getHighEntropyValues) { done(); return; }
		d.getHighEntropyValues(['architecture', 'bitness']).then(function (v) {
			if (v && v.architecture === 'arm') { guess.arch = 'arm64'; }
			else if (v && v.architecture === 'x86' && v.bitness === '64') { guess.arch = 'x64'; }
			done();
		}).catch(done);
	}

	/* ════════════════════════════════════════════════════════════════════
	   §٢ — المانيفست
	   ════════════════════════════════════════════════════════════════════ */
	var PLATFORMS = readJson('site-platforms') || [];
	var manifest = readJson('baked-releases') || { version: null, assets: [] };

	function readJson(id) {
		var el = document.getElementById(id);
		if (!el) { return null; }
		try { return JSON.parse(el.textContent); } catch (e) { return null; }
	}

	function platformOf(id) {
		for (var i = 0; i < PLATFORMS.length; i++) {
			if (PLATFORMS[i].id === id) { return PLATFORMS[i]; }
		}
		return null;
	}

	/* عنوانُ الأصل: `origin` في المانيفست يجعل المرآةَ (GitHub Pages) تشير إلى
	   الثنائيّات على الخادم الأصليّ بدل أن تعِد بملفٍّ لا تحمله. */
	function assetUrl(a) {
		var root = manifest.origin
			? manifest.origin.replace(/\/+$/, '') + '/'
			: base().replace(/\/+$/, '') + '/';
		return root + (manifest.base || 'dl/').replace(/^\/+/, '') + a.file;
	}

	function fmtSize(bytes) {
		if (!bytes || bytes < 0) { return ''; }
		var mb = bytes / 1048576;
		return mb >= 1024
			? (mb / 1024).toFixed(2) + ' غيغابايت'
			: Math.round(mb) + ' ميغابايت';
	}

	/* أفضلُ أصلٍ لنظامٍ ومعماريّة. الأولويّة: تطابقٌ تامّ ← نفسُ النظام بمعماريّةٍ
	   أخرى ← لا شيء. و«المثبِّت» يسبق «المحمول» لأنّه ترتيبُ `platforms` في
	   البيانات — والترتيبُ هناك قرارُ محتوى لا قرارُ كود. */
	function bestFor(os, arch) {
		var exact = null, sameOs = null;
		for (var i = 0; i < manifest.assets.length; i++) {
			var a = manifest.assets[i], p = platformOf(a.id);
			if (!p || p.os !== os) { continue; }
			if (p.arch === arch) { if (!exact) { exact = a; } }
			else if (!sameOs) { sameOs = a; }
		}
		return exact || sameOs;
	}

	/* ════════════════════════════════════════════════════════════════════
	   §٣ — الرسم
	   ════════════════════════════════════════════════════════════════════ */
	function el(tag, cls, text) {
		var n = document.createElement(tag);
		if (cls) { n.className = cls; }
		if (text != null) { n.textContent = text; }
		return n;
	}

	function renderPrimary() {
		var btn = document.querySelector('[data-dl-primary]');
		var meta = document.querySelector('[data-dl-meta]');
		if (!btn) { return; }

		var a = manifest.version ? bestFor(guess.os, guess.arch) : null;

		if (!a) {
			/* لا بناءَ لهذا النظام (أو لا إصدارَ أصلًا): الزرُّ يقود إلى الجدول
			   الكامل — وجهةٌ صادقة — لا إلى ملفٍّ مفقود. */
			btn.setAttribute('href', base() + '/download/');
			btn.textContent = manifest.version ? 'كلُّ المنصّات' : 'حالةُ الإصدار';
			if (meta) {
				meta.textContent = manifest.version
					? 'لا بناءَ جاهزٌ لـ' + OS_AR[guess.os] + ' في الإصدار ' + manifest.version + '.'
					: 'لا إصدارَ منشورًا بعد — يمكنك البناءُ من المصدر.';
			}
			return;
		}

		var p = platformOf(a.id);
		btn.setAttribute('href', assetUrl(a));
		btn.setAttribute('download', '');
		btn.textContent = '';
		btn.appendChild(document.createTextNode('نزِّل لـ' + p.label));
		var sz = el('span', 'sz', fmtSize(a.size));
		if (sz.textContent) { btn.appendChild(sz); }

		if (meta) {
			meta.textContent = '';
			meta.appendChild(document.createTextNode(
				'الإصدار ' + manifest.version
				+ (manifest.date ? ' · ' + manifest.date : '')
				+ ' · ' + p.kind + ' · '));
			var all = el('a', null, 'منصّاتٌ أخرى');
			all.href = base() + '/download/';
			meta.appendChild(all);
		}
	}

	function renderPick() {
		var box = document.querySelector('[data-dl-pick]');
		if (!box) { return; }
		var a = manifest.version ? bestFor(guess.os, guess.arch) : null;
		if (!a) { box.hidden = true; return; }
		box.hidden = false;

		var p = platformOf(a.id);
		box.textContent = '';
		var g = el('div', 'guess');
		g.appendChild(document.createTextNode('يبدو أنّك على '));
		g.appendChild(el('b', null, p.label));
		g.appendChild(document.createTextNode(' — إن كان التخمينُ خاطئًا فاختر من الجدول أدناه.'));
		box.appendChild(g);

		var btn = el('a', 'btn btn-primary');
		btn.href = assetUrl(a);
		btn.setAttribute('download', '');
		btn.appendChild(document.createTextNode('نزِّل ' + p.kind + ' ' + p.label));
		var sz = el('span', 'sz', fmtSize(a.size));
		if (sz.textContent) { btn.appendChild(sz); }
		box.appendChild(btn);
	}

	function renderTable() {
		var tbody = document.querySelector('[data-dl-table]');
		var empty = document.querySelector('[data-dl-empty]');
		var wrap = document.querySelector('[data-dl-wrap]');
		var stamp = document.querySelector('[data-dl-version]');
		if (!tbody) { return; }

		var has = manifest.version && manifest.assets.length;
		if (wrap) { wrap.hidden = !has; }
		if (empty) { empty.hidden = !!has; }
		if (!has) { return; }

		if (stamp) {
			stamp.textContent = 'الإصدار ' + manifest.version
				+ (manifest.date ? ' — ' + manifest.date : '');
		}

		var mine = bestFor(guess.os, guess.arch);
		tbody.textContent = '';

		/* الترتيبُ ترتيبُ `platforms` في البيانات لا ترتيبُ المانيفست: رفعُ الملفّات
		   يتمّ بأيّ ترتيبٍ، وترتيبُ الجدول قرارُ تحرير. */
		var ordered = [];
		PLATFORMS.forEach(function (p) {
			manifest.assets.forEach(function (a) { if (a.id === p.id) { ordered.push(a); } });
		});
		manifest.assets.forEach(function (a) {
			if (ordered.indexOf(a) === -1) { ordered.push(a); }
		});

		/* ── والمنصّاتُ التي لا أصلَ لها في هذا الإصدار تُعرَض ولا تُحذَف ──
		   الجدولُ كان يرسم ما في المانيفست وحدَه، فيرى صاحبُ ويندوز — وهو الأغلب —
		   صفًّا محمولًا واحدًا ولا يجد المثبِّت، وقد قرأ في «المتطلّبات» أنّ ويندوز
		   مدعوم. فلا يستنتج «لم يُبنَ بعد»، بل «موجودٌ وأنا لا أُحسِن إيجادَه»: يبحث
		   ثمّ يغادر. وصفٌّ رماديٌّ يقول الحقيقةَ أرحمُ من صفٍّ غائبٍ يكذب بالصمت. */
		var missing = [];
		PLATFORMS.forEach(function (p) {
			for (var i = 0; i < ordered.length; i++) {
				if (ordered[i].id === p.id) { return; }
			}
			missing.push(p);
		});

		ordered.forEach(function (a) {
			var p = platformOf(a.id) || { label: a.id, kind: '', ext: '' };
			var tr = document.createElement('tr');
			if (a === mine) { tr.className = 'mine'; }

			var td1 = el('td', 'file');
			td1.appendChild(el('b', null, p.label));
			td1.appendChild(el('span', 'kind', p.kind + (p.ext ? ' · ' + p.ext : '')));
			if (a.sha256) {
				var sha = el('span', 'sha', 'SHA-256: ' + a.sha256);
				td1.appendChild(document.createElement('br'));
				td1.appendChild(sha);
			}
			tr.appendChild(td1);

			tr.appendChild(el('td', 'size', fmtSize(a.size)));

			var td3 = el('td', 'get');
			var link = el('a', 'btn-sm', 'نزِّل');
			link.href = assetUrl(a);
			link.setAttribute('download', '');
			td3.appendChild(link);
			tr.appendChild(td3);

			tbody.appendChild(tr);
		});

		missing.forEach(function (p) {
			var tr = el('tr', 'absent');
			var td1 = el('td', 'file');
			td1.appendChild(el('b', null, p.label));
			td1.appendChild(el('span', 'kind', p.kind + (p.ext ? ' · ' + p.ext : '')));
			tr.appendChild(td1);
			tr.appendChild(el('td', 'size', '—'));
			tr.appendChild(el('td', 'get', 'لم يُبنَ بعد لهذا الإصدار'));
			tbody.appendChild(tr);
		});
	}

	function renderAll() { renderPrimary(); renderPick(); renderTable(); }

	/* ════════════════════════════════════════════════════════════════════
	   §٤ — التشغيل
	   ارسم من المخبوز فورًا (لا وميضَ ولا انتظار)، ثمّ حدِّث من الحيّ إن وصل.
	   والفشلُ صامتٌ عمدًا: المخبوزُ صحيحٌ حتّى آخر نشرة، وإظهارُ خطأِ شبكةٍ للزائر
	   ضجيجٌ لا يملك حياله شيئًا.
	   ════════════════════════════════════════════════════════════════════ */
	refineArch(renderAll);

	if (document.querySelector('[data-dl-primary],[data-dl-table]')) {
		fetch(base() + '/dl/releases.json', { cache: 'no-cache' })
			.then(function (r) { return r.ok ? r.json() : null; })
			.then(function (live) {
				if (live && live.version && Array.isArray(live.assets)) {
					manifest = live;
					renderAll();
				}
			})
			.catch(function () { /* المخبوزُ يكفي */ });
	}
}());
