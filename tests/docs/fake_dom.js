/* صفحةٌ مزيّفةٌ لصندوق السلوك [CAP-04] — أدنى ما يلزم `docs.js`، بلا اعتماديّات (لا jsdom).
 *
 * عناصرُ بأصنافٍ وسماتٍ وأبناء (والنصُّ عقدُ `#text`)، ومحدِّدُ CSS بسيط (وسم، ‎.صنف، ‎#معرّف،
 * ‎[سمة]، والسليل)، وفقاعةُ أحداث، وبؤرةٌ بترتيب المتصفّح، ومؤقّتاتٌ تُقدَّم باليد — وبناءُ الصفحة
 * من شجرة `keyboard/index.html` المبنيّة (يحلّلها `_page_tree` في الحارس). السيناريوهاتُ في
 * `docs_sandbox.js`.
 */
'use strict';

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
function buildPage(fx) {
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

function pendingTimers() { return timers; }
function getDocument() { return doc; }

module.exports = { El, walk, match, setTimeout_, clearTimeout_, fireTimers, pendingTimers,
	buildPage, getDocument, key, input };
