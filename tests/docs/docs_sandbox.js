/* صندوقٌ سلوكيٌّ لـ`docs.js` **المنشور** (‏`site/public/assets/docs.js`) [CAP-04] — يُشغَّل من `check_site.py`.
 *
 * لماذا: كانت فحوصُ الالتقاط والترشيح والأسهم تقرأ **نصَّ** الشيفرة (`"…blur…" in docs_js`)،
 * فتحويلُ السطر إلى تعليقٍ يُبطل الميزةَ والحارسُ أخضر (قِيس بالزرع). هنا يُنفَّذ الملفُّ
 * المشحونُ نفسُه — كما هو، بلا اقتطاع — على شجرة `keyboard/index.html` المبنيّة (يحلّلها
 * `_page_tree` في check_site.py)، وتُرسَل إليه أحداثٌ كما يرسلها المتصفّح، وتُقاس النتيجةُ
 * التي يراها الزائر.
 *
 *   node tests/docs/docs_sandbox.js <docs.js> <fixture.json>
 *   ⇒ JSON: { "ran": N, "fails": ["…", …] }
 *
 * و«الوثيقةُ» أدنى ما يلزم: عناصرُ بأصنافٍ وسماتٍ وأبناء (والنصُّ عقدُ `#text`)، ومحدِّدُ CSS بسيط (وسم،
 * ‎.صنف، ‎#معرّف، ‎[سمة]، والسليل)، وفقاعةُ أحداث، وبؤرة، ومؤقّتاتٌ تُقدَّم باليد. بلا
 * اعتماديّات: لا jsdom ولا شبكة.
 */
'use strict';
const fs = require('fs');
const vm = require('vm');

const [, , DOCS_JS, FIXTURE] = process.argv;
const src = fs.readFileSync(DOCS_JS, 'utf8');
const fx = JSON.parse(fs.readFileSync(FIXTURE, 'utf8'));

// ── صفحةٌ مزيّفة ─────────────────────────────────────────────────────────────
let doc = null;
class El {
	constructor(tag, attrs) {
		this.tagName = tag.toUpperCase();
		this.attrs = Object.assign({}, attrs || {});
		this.children = [];
		this.parentNode = null;
		this._text = '';
		this._ls = {};
		this.hidden = 'hidden' in this.attrs;
		delete this.attrs.hidden;
		this.value = '';
		this.style = { setProperty() {} };
		this.offsetHeight = 0;
		this.offsetParent = {};
		const self = this;
		this.classList = {
			_s: new Set((this.attrs.class || '').split(/\s+/).filter(Boolean)),
			add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
			contains(c) { return this._s.has(c); },
			toggle(c, on) { const v = on === undefined ? !this._s.has(c) : !!on; if (v) this._s.add(c); else this._s.delete(c); return v; },
		};
		Object.defineProperty(this, 'id', { get() { return self.attrs.id || ''; } });
	}
	get className() { return [...this.classList._s].join(' '); }
	set className(v) { this.classList._s = new Set(String(v).split(/\s+/).filter(Boolean)); }
	get firstChild() { return this.children[0] || null; }
	get textContent() { return this._text + this.children.map(c => c.textContent).join(''); }
	set textContent(v) { this._text = String(v); this.children.forEach(c => { c.parentNode = null; }); this.children = []; }
	set innerHTML(v) { this.textContent = ''; }
	get innerHTML() { return ''; }
	getAttribute(n) { return n in this.attrs ? this.attrs[n] : null; }
	setAttribute(n, v) { this.attrs[n] = String(v); }
	appendChild(c) { if (c.parentNode) c.parentNode.removeChild(c); c.parentNode = this; this.children.push(c); return c; }
	insertBefore(c, ref) { c.parentNode = this; const i = this.children.indexOf(ref); this.children.splice(i < 0 ? this.children.length : i, 0, c); return c; }
	removeChild(c) { this.children = this.children.filter(x => x !== c); c.parentNode = null; return c; }
	contains(n) { for (let x = n; x; x = x.parentNode) { if (x === this) return true; } return false; }
	closest(sel) { for (let x = this; x && x instanceof El; x = x.parentNode) { if (match(x, sel)) return x; } return null; }
	addEventListener(t, fn) { (this._ls[t] = this._ls[t] || []).push(fn); }
	_fire(t, ev) { (this._ls[t] || []).slice().forEach(fn => fn.call(this, ev)); }
	// والمخفيُّ (هو أو سلفُه) لا يقبل البؤرة: `focus()` عليه لا يفعل شيئًا ولا يشكو، كالمتصفّح.
	focus() { for (let x = this; x; x = x.parentNode) { if (x.hidden) return; } doc._focus(this); }
	blur() { if (doc.activeElement === this) doc._focus(doc.body); }
	scrollIntoView() {}
	getBoundingClientRect() { return { top: 0, bottom: 0 }; }
	// كالمتصفّح: المحدِّدُ يُطابَق على الوثيقة كلِّها والنتائجُ من الأحفاد وحدَهم —
	// ‏`box.querySelector('.capture-box .result')` يجد ابنَه وإن كان `.capture-box` هو `box` نفسَه.
	querySelectorAll(sel) { const out = []; walk(this, x => { if (x !== this && match(x, sel)) out.push(x); }); return out; }
	querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
}
function walk(n, f) { f(n); n.children.forEach(c => walk(c, f)); }
// محدِّدٌ بسيط: مركّباتٌ (وسم، ‎.صنف، ‎#معرّف، ‎[سمة] و‎[سمة="ق"]) يفصلها السليل. وما سواه
// (الفاصلة، ‎:not، ‎`>`، وقيمةُ سمةٍ بمسافة) لا يطابق شيئًا **صامتًا** — docs.js لا يحتاجه إلّا
// لـ`inert` خلف الدرج، والدرجُ في الصفحة لكنّ الصندوقَ لا يفتحه (ولا يحاكي `inert`): سيناريو
// يفتحه يحتاج الاثنين أوّلًا. ومحدِّدٌ جديدٌ منها في docs.js يُرى نتيجةً غائبةً لا خطأً.
function compound(el, c) {
	if (/[,:]/.test(c)) return false;
	const m = c.match(/^([a-z0-9]+)?((?:[.#][\w-]+|\[[^\]]+\])*)$/i);
	if (!m) return false;
	if (m[1] && el.tagName !== m[1].toUpperCase()) return false;
	for (const p of (m[2].match(/[.#][\w-]+|\[[^\]]+\]/g) || [])) {
		if (p[0] === '.' && !el.classList.contains(p.slice(1))) return false;
		if (p[0] === '#' && el.id !== p.slice(1)) return false;
		if (p[0] === '[') {
			const a = p.slice(1, -1).match(/^([\w-]+)(?:="([^"]*)")?$/);
			if (!a || !(a[1] in el.attrs)) return false;
			if (a[2] !== undefined && el.attrs[a[1]] !== a[2]) return false;
		}
	}
	return true;
}
function match(el, sel) {
	const parts = sel.trim().split(/\s+/);
	if (!compound(el, parts[parts.length - 1])) return false;
	let x = el.parentNode;
	for (let i = parts.length - 2; i >= 0; i--) {
		while (x && !compound(x, parts[i])) x = x.parentNode;
		if (!x) return false;
		x = x.parentNode;
	}
	return true;
}

// ── المؤقّتات تُقدَّم باليد ───────────────────────────────────────────────────
let timers = [], tseq = 0;
function setTimeout_(fn, ms) { const id = ++tseq; timers.push({ id, fn, ms }); return id; }
function clearTimeout_(id) { timers = timers.filter(t => t.id !== id); }
function fireTimers() { const t = timers; timers = []; t.forEach(x => x.fn()); return t; }

// ── الصفحةُ هي `keyboard/index.html` المبنيّةُ نفسُها ─────────────────────────
// كانت تُصنَع باليد، فإعادةُ تسمية `id="capture-btn"` أو `.result` في `sitegen/pages.py` تُميت
// الالتقاطَ في الصفحة الحقيقيّة والصندوقُ أخضر يصنع الاسمَ القديم بنفسه (قِيس بالزرع). فبايثون
// يحلّل الصفحةَ المبنيّة شجرةً `[وسم، سمات، أبناء]` والنصُّ سلاسل، والصندوقُ يبنيها `El`
// ويجد ما يحتاجه **بمحدِّدات docs.js نفسِها** — وغيابُ أيّها عطبٌ في العقد يُسمّى.
function fromTree(node) {
	if (typeof node === 'string') { const t = new El('#text'); t._text = node; return t; }
	const e = new El(node[0], node[1]);
	node[2].forEach(k => e.appendChild(fromTree(k)));
	return e;
}
function buildPage() {
	const html = fromTree(fx.tree);
	const body = html.querySelector('body');
	doc = {
		documentElement: html, body, activeElement: body, readyState: 'loading', _ls: {},
		// ترتيبُ المتصفّح: ‏`blur` على السابق **والبؤرةُ على body** أثناءه، ثمّ `focus` على الجديد.
		_focus(el) {
			const prev = this.activeElement;
			if (prev === el) return;
			this.activeElement = this.body;
			if (prev && prev !== this.body && prev._fire) prev._fire('blur', { target: prev });
			this.activeElement = el;
			el._fire('focus', { target: el });
		},
		getElementById(id) { let r = null; walk(html, x => { if (!r && x.id === id) r = x; }); return r; },
		querySelectorAll(sel) { const out = []; walk(html, x => { if (match(x, sel)) out.push(x); }); return out; },
		querySelector(sel) { return this.querySelectorAll(sel)[0] || null; },
		createElement(t) { return new El(t); },
		addEventListener(t, fn) { (this._ls[t] = this._ls[t] || []).push(fn); },
	};
	const sInput = doc.getElementById('site-search');
	const sBox = sInput && sInput.closest('.search-box');
	const P = {
		sInput, sResults: sBox && sBox.querySelector('.search-results'),
		filter: doc.getElementById('kbd-filter'), btn: doc.getElementById('capture-btn'),
		field: doc.getElementById('capture-field'), box: doc.querySelector('.capture-box'),
		out: doc.querySelector('.capture-box .result'), empty: doc.querySelector('.no-results'),
		status: doc.querySelector('.kbd-status'), table: doc.querySelector('[data-kbd-table]'),
	};
	const missing = Object.keys(P).filter(k => !P[k]);
	P.rowsByName = {};
	P.rows = doc.querySelectorAll('tbody tr');
	P.rows.forEach(tr => { const n = tr.querySelector('.cmd-name'); if (n) P.rowsByName[n.textContent] = tr; });
	if (!P.rows.length) missing.push('tbody tr');
	return { P, missing };
}

function key(target, k, extra) {
	const ev = Object.assign({ key: k, code: '', ctrlKey: false, metaKey: false, shiftKey: false, altKey: false,
		keyCode: 0, isComposing: false, target, defaultPrevented: false,
		preventDefault() { this.defaultPrevented = true; } }, extra || {});
	for (let x = target; x; x = x.parentNode) x._fire('keydown', ev);
	(doc._ls.keydown || []).forEach(fn => fn(ev));
	// الحركةُ الأصليّة التي تُقاس: ‏Escape في `input[type=search]` يمسح نصَّه ويُطلق `input`
	// (Chromium/Edge) ما لم تُمنَع — بلاها كان شرطُ «السؤالُ باقٍ» صادقًا في الصندوق أيًّا كان.
	if (k === 'Escape' && !ev.defaultPrevented && target.tagName === 'INPUT'
		&& target.attrs.type === 'search' && target.value !== '') {
		target.value = '';
		target._fire('input', { target });
	}
	return ev;
}
function input(el, v) { el.value = v; el._fire('input', { target: el }); }

async function main() {
	const built = buildPage();
	const P = built.P;
	if (built.missing.length) {
		// العقدُ بين `sitegen/pages.py` و`docs.js` انكسر: ما تبحث عنه الشيفرةُ غائبٌ عن الصفحة المبنيّة
		process.stdout.write(JSON.stringify({ ran: 1, fails: ['عقدُ الصفحة: ' + built.missing.join('، ')
			+ ' غائبٌ عن keyboard/index.html المبنيّة وdocs.js يبحث عنه — الميزةُ ميّتةٌ في الموقع [CAP-04]'] }));
		return;
	}
	const fetch_ = () => Promise.resolve({ json: () => Promise.resolve(fx.index) });
	const ctx = {
		document: doc, window: null, navigator: { platform: 'Win32', userAgent: 'sandbox', clipboard: { writeText: () => Promise.resolve() } },
		location: { host: 'mihrab.dev' }, localStorage: { getItem: () => null, setItem() {} },
		getComputedStyle: () => ({ position: 'static', display: 'block', getPropertyValue: () => '' }),
		requestAnimationFrame() {}, setTimeout: setTimeout_, clearTimeout: clearTimeout_, fetch: fetch_,
		Promise, Array, Object, String, Number, JSON, Set, RegExp, Math, parseFloat,
	};
	ctx.window = { matchMedia: () => ({ matches: false }), addEventListener() {}, innerHeight: 800, scrollBy() {} };
	vm.runInNewContext(src, ctx, { filename: 'docs.js' });

	const fails = [];
	let ran = 0;
	const expect = (cond, msg) => { ran++; if (!cond) fails.push(msg + ' [CAP-04]'); };
	const say = () => P.out.textContent;
	const C = (k, code, mods) => Object.assign({ code }, mods || {});
	const open = () => { P.btn._fire('click', {}); };
	const ctrlK = () => key(P.field, 'k', C('k', 'KeyK', { ctrlKey: true }));
	const S = () => key(P.field, 's', { code: 'KeyS' });
	const ALL = fx.save_all, ONE = fx.save_one, INITIAL = P.out.textContent;

	// (١) التسلسلُ يُعلَّق ثمّ يُحسَم
	open();
	expect(doc.activeElement === P.field && !P.box.hidden, 'النقرُ على «التقط» لا يفتح الصندوقَ ولا يبئّر الحقل');
	let ev = ctrlK();
	expect(ev.defaultPrevented, 'ضغطةُ الالتقاط لا تُمنَع حركتُها الأصليّة');
	expect(/ثمّ…/.test(say()), 'Ctrl+K لا يُعلَّق بادئةً — قال «' + say() + '»');
	S();
	expect(say().indexOf(ALL) !== -1, 'Ctrl+K ثمّ S لا يُحسَم «' + ALL + '» — قال «' + say() + '»');

	// (٢) Escape يُغلق ويُلغي التعليق
	ctrlK();
	key(P.field, 'Escape', { code: 'Escape' });
	expect(P.box.hidden && doc.activeElement === P.btn, 'Escape لا يُغلق الصندوقَ ولا يعيد البؤرةَ إلى الزرّ');
	open();
	// وإعادةُ الفتح تُري التلميحَ الأوّل لا بقيّةَ ما قبل الإغلاق (فقدانُ البؤرة وحدَه يُسقِط
	// التعليقَ لكنّه يكتب «لم تصل الضغطةُ الثانية» — طلبًا لا ينتظره أحد)
	expect(say() === INITIAL && P.out.classList.contains('dim'),
		'Escape لا يعيد سطرَ النتيجة إلى تلميحه الأوّل — بعد إعادة الفتح «' + say() + '»');
	S();
	expect(say().indexOf(ALL) === -1, 'Escape أغلق الالتقاطَ ولم يُلغِ التعليق: S بعده قرأت «' + say() + '»');

	// (٣) فقدانُ البؤرة يُسقِط التعليقَ ويقول ذلك
	ctrlK();
	P.btn.focus();
	expect(/لم تصل الضغطةُ الثانية/.test(say()), 'فقدانُ البؤرة بعد Ctrl+K لا يُسقِط التعليقَ ولا يقوله — قال «' + say() + '»');
	P.field.focus(); S();
	expect(say().indexOf(ALL) === -1, 'فقدانُ البؤرة لم يُسقِط التعليق: S بعد العودة قرأت «' + say() + '»');

	// (٤) المهلةُ تُسقِط التعليقَ بمداها المعلَن
	ctrlK();
	const t = fireTimers();
	expect(t.length === 1 && t[0].ms >= 1000 && t[0].ms <= 8000,
		'مهلةُ التعليق ليست مؤقّتًا واحدًا بين ثانيةٍ وثمانٍ — ' + JSON.stringify(t.map(x => x.ms)));
	expect(/لم تصل الضغطةُ الثانية/.test(say()), 'انقضاءُ المهلة لا يُسقِط التعليقَ ولا يقوله — قال «' + say() + '»');
	S();
	expect(say().indexOf(ALL) === -1, 'انقضت المهلةُ ولم يسقط التعليق: S بعدها قرأت «' + say() + '»');

	// (٥) ضغطةُ IME تُسقِط التعليق — بصورها الأربع **كلٌّ وحدَها**: الشرطُ أربعةُ أضلاعٍ
	// (‏isComposing، ‏Unidentified، ‏Process، ‏keyCode 229)، وضغطةٌ تحملها معًا لا ترى ضلعًا محذوفًا.
	[['Unidentified', {}], ['Process', {}], ['a', { code: 'KeyA', isComposing: true }], ['a', { code: 'KeyA', keyCode: 229 }]]
		.forEach(([k, extra]) => {
			const shape = k + ' ' + JSON.stringify(extra);
			ctrlK();
			key(P.field, k, extra);
			expect(/لم تصل ضغطةٌ مفهومة/.test(say()), 'ضغطةُ IME لا تقول إنّها لم تُفهَم (' + shape + ') — قالت «' + say() + '»');
			S();
			expect(say().indexOf(ALL) === -1, 'ضغطةُ IME لم تُسقِط التعليق (' + shape + '): S بعدها قرأت «' + say() + '»');
		});

	// (٦) ضغطةٌ واحدةٌ تُحسَم وتُعلِّم صفَّها، وCtrl+K مرّتين لا يُعلَّق ثانيةً
	key(P.field, 's', C('s', 'KeyS', { ctrlKey: true }));
	expect(say().indexOf(ONE) !== -1, 'Ctrl+S لا يُحسَم «' + ONE + '» — قال «' + say() + '»');
	expect(P.rowsByName[ONE] && P.rowsByName[ONE].classList.contains('kbd-hit'), 'صفُّ «' + ONE + '» لم يُعلَّم `kbd-hit`');
	ctrlK(); ctrlK();
	expect(!/ثمّ…/.test(say()) && timers.length === 0, 'Ctrl+K Ctrl+K عُلِّق ثانيةً — التسلسلُ ضغطتان لا أكثر');

	// (٧) الترشيح: بلا تشكيل، ومن وسط الاسم، ومنطوقٌ بالعدد
	input(P.filter, fx.filter_query);
	const hitRow = P.rowsByName[fx.filter_row];
	expect(hitRow && !hitRow.hidden, 'الترشيحُ بـ«' + fx.filter_query + '» (بلا شدّةٍ ومن وسط الاسم) يُخفي «' + fx.filter_row + '»');
	expect(P.status.textContent !== '' && P.empty.hidden, 'الترشيحُ لا يُنطَق بالعدد أو يُظهر «لا اختصار» وفي الجدول مطابق — «' + P.status.textContent + '»');
	// والسؤالُ يُطبَّع كالمتن: من كتب الكلمةَ بهمزتها أو شدّتها يجد الصفَّ كذلك
	input(P.filter, fx.filter_query_raw);
	expect(hitRow && !hitRow.hidden, 'الترشيحُ بـ«' + fx.filter_query_raw + '» كما كُتبت (بهمزتها أو شدّتها) يُخفي «' + fx.filter_row + '» — السؤالُ لا يُطبَّع');
	// والترشيحُ يُخفي ما لا يطابق، والعددُ المنطوقُ عددُ الظاهر بقواعد العدد العربيّ — كان
	// السيناريو يسأل عن ظهور المطابق وحدَه: `tr.hidden = false` وعددٌ خاطئٌ كانا يمرّان.
	const plainRef = t => t.replace(/[ً-ْٰـ]/g, '').replace(/[أإآ]/g, 'ا').toLowerCase();
	// سؤالان: أحدُهما يطابق صفًّا واحدًا، والآخرُ صفّين فأكثر **في قسمٍ واحد** — بالأوّل وحدَه
	// يتساوى عددُ الصفوف وعددُ الأقسام فيمرّ عدٌّ يجمع الأقسامَ لا الصفوف (قِيس بالزرع).
	[fx.filter_query, fx.count_query].forEach(q => {
		input(P.filter, q);
		const qRef = plainRef(q);
		const want = P.rows.filter(tr => plainRef(tr.getAttribute('data-search') || '').indexOf(qRef) !== -1);
		const shown = P.rows.filter(tr => !tr.hidden && !(tr.closest('.kbd-section') || {}).hidden);
		const other = P.rows.find(tr => want.indexOf(tr) === -1);
		expect(other && other.hidden, 'الترشيحُ بـ«' + q + '» لا يُخفي صفًّا لا يطابقه');
		expect(shown.length === want.length, 'الترشيحُ بـ«' + q + '» يُظهر ' + shown.length + ' صفًّا والمطابقُ ' + want.length);
		const n = shown.length;
		const word = n === 0 ? 'لا اختصارَ يطابق' : n === 1 ? 'اختصارٌ واحد' : n === 2 ? 'اختصاران'
			: n <= 10 ? n + ' اختصارات' : n + ' اختصارًا';
		expect(P.status.textContent === word, 'العددُ المنطوقُ «' + P.status.textContent + '» لا «' + word + '» — ' + n + ' صفًّا ظاهرًا لـ«' + q + '»');
	});
	const allSec = P.rowsByName[fx.save_all] && P.rowsByName[fx.save_all].closest('.kbd-section');
	expect(P.rows.filter(tr => tr.closest('.kbd-section') === allSec
		&& plainRef(tr.getAttribute('data-search') || '').indexOf(plainRef(fx.count_query)) !== -1).length >= 2,
		'سؤالُ العدّ «' + fx.count_query + '» لا يطابق صفّين في قسمٍ واحد — شاهدُ العدّ زال');
	input(P.filter, 'لاشيءيطابقهذاقطعا');
	expect(!P.empty.hidden && P.status.textContent === 'لا اختصارَ يطابق', 'سؤالٌ بلا مطابقٍ لا يُظهر «لا اختصار» ولا يُنطَق');
	input(P.filter, '');

	// (٨) البحث: الأسهمُ تسير، وEscape يطوي ولا يمسح
	P.sInput.focus();
	input(P.sInput, fx.search_query);
	await new Promise(r => setImmediate(r));
	await new Promise(r => setImmediate(r));
	const links = P.sResults.querySelectorAll('a');
	expect(!P.sResults.hidden && links.length >= 2, 'البحثُ عن «' + fx.search_query + '» لا يعرض نتيجتين على الأقلّ (' + links.length + ')');
	if (links.length >= 2) {
		ev = key(P.sInput, 'ArrowDown');
		expect(ev.defaultPrevented && doc.activeElement === links[0], '↓ من الحقل لا يركّز أوّلَ نتيجة');
		key(links[0], 'ArrowDown');
		expect(doc.activeElement === links[1], '↓ بين النتائج لا يسير إلى الثانية');
		key(links[1], 'ArrowUp');
		expect(doc.activeElement === links[0], '↑ بين النتائج لا يعود إلى الأولى');
		key(links[0], 'ArrowUp');
		expect(doc.activeElement === P.sInput, '↑ من أوّل نتيجةٍ لا يعود إلى الحقل');
		// ‏Escape والبؤرةُ على نتيجة: تُطوى القائمةُ وتعود البؤرةُ إلى الحقل لا إلى body
		key(P.sInput, 'ArrowDown');
		ev = key(links[0], 'Escape');
		expect(ev.defaultPrevented && P.sResults.hidden && doc.activeElement === P.sInput,
			'Escape على نتيجةٍ مركَّزة لا يطوي القائمةَ أو لا يعيد البؤرةَ إلى الحقل');
		input(P.sInput, fx.search_query);
		ev = key(P.sInput, 'Escape');
		expect(ev.defaultPrevented && P.sResults.hidden && P.sInput.value === fx.search_query,
			'Escape والنتائجُ ظاهرةٌ لا يمنع الحركةَ الأصليّة (مسحَ السؤال) أو لا يطوي القائمة');
		ev = key(P.sInput, 'Escape');
		expect(!ev.defaultPrevented, 'Escape الثانية والقائمةُ مطويّةٌ تُمنَع — الحقلُ لا يُمسَح كما اعتاد الزائر');
	}
	process.stdout.write(JSON.stringify({ ran, fails }));
}
main().catch(e => { process.stdout.write(JSON.stringify({ ran: 0, fails: ['انهار الصندوق: ' + (e && e.stack || e) + ' [CAP-04]'] })); });
