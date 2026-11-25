/* صندوقٌ سلوكيٌّ لـ`docs.js` **المنشور** (‏`site/public/assets/docs.js`) [CAP-04] — يُشغَّل من `check_site.py`.
 *
 * لماذا: كانت فحوصُ الالتقاط والترشيح والأسهم تقرأ **نصَّ** الشيفرة (`"…blur…" in docs_js`)،
 * فتحويلُ السطر إلى تعليقٍ يُبطل الميزةَ والحارسُ أخضر (قِيس بالزرع). هنا يُنفَّذ الملفُّ
 * المشحونُ نفسُه — كما هو، بلا اقتطاع — على شجرة `keyboard/index.html` المبنيّة (يحلّلها
 * `_page_tree` في `site_guard/core.py`)، وتُرسَل إليه أحداثٌ كما يرسلها المتصفّح، وتُقاس النتيجةُ
 * التي يراها الزائر.
 *
 *   node tests/docs/docs_sandbox.js <docs.js> <fixture.json>
 *   ⇒ JSON: { "ran": N, "fails": ["…", …] }
 *
 * والصفحةُ المزيّفةُ والمؤقّتاتُ وأدواتُ الأحداث في `fake_dom.js` (بلا اعتماديّات: لا jsdom ولا شبكة).
 */
'use strict';
const fs = require('fs');
const vm = require('vm');
const { setTimeout_, clearTimeout_, fireTimers, pendingTimers, buildPage, getDocument, key, input }
	= require('./fake_dom.js');

const [, , DOCS_JS, FIXTURE] = process.argv;
const src = fs.readFileSync(DOCS_JS, 'utf8');
const fx = JSON.parse(fs.readFileSync(FIXTURE, 'utf8'));

async function main() {
	const built = buildPage(fx);
	const P = built.P;
	if (built.missing.length) {
		// العقدُ بين `sitegen/pages.py` و`docs.js` انكسر: ما تبحث عنه الشيفرةُ غائبٌ عن الصفحة المبنيّة
		process.stdout.write(JSON.stringify({ ran: 1, fails: ['عقدُ الصفحة: ' + built.missing.join('، ')
			+ ' غائبٌ عن keyboard/index.html المبنيّة وdocs.js يبحث عنه — الميزةُ ميّتةٌ في الموقع [CAP-04]'] }));
		return;
	}
	const fetch_ = () => Promise.resolve({ json: () => Promise.resolve(fx.index) });
	const ctx = {
		document: getDocument(), window: null, navigator: { platform: 'Win32', userAgent: 'sandbox', clipboard: { writeText: () => Promise.resolve() } },
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
	// الحدثُ الأخير — يعبر السيناريوهات كما كان يعبر مقاطعَ الدالّة الواحدة.
	let ev;

	// السيناريوهاتُ بترتيبها — كلٌّ يبني على حالة سابقه (الصندوقُ مفتوحٌ أو مغلق، والتعليقُ قائمٌ
	// أو ساقط)، فالترتيبُ جزءٌ من القياس لا تفصيل.
	const SCENARIOS = [
		['التسلسلُ يُعلَّق ثمّ يُحسَم', function () {
			open();
			expect(getDocument().activeElement === P.field && !P.box.hidden, 'النقرُ على «التقط» لا يفتح الصندوقَ ولا يبئّر الحقل');
			ev = ctrlK();
			expect(ev.defaultPrevented, 'ضغطةُ الالتقاط لا تُمنَع حركتُها الأصليّة');
			expect(/ثمّ…/.test(say()), 'Ctrl+K لا يُعلَّق بادئةً — قال «' + say() + '»');
			S();
			expect(say().indexOf(ALL) !== -1, 'Ctrl+K ثمّ S لا يُحسَم «' + ALL + '» — قال «' + say() + '»');
		}],
		['Escape يُغلق ويُلغي التعليق', function () {
			ctrlK();
			key(P.field, 'Escape', { code: 'Escape' });
			expect(P.box.hidden && getDocument().activeElement === P.btn, 'Escape لا يُغلق الصندوقَ ولا يعيد البؤرةَ إلى الزرّ');
			open();
			// وإعادةُ الفتح تُري التلميحَ الأوّل لا بقيّةَ ما قبل الإغلاق (فقدانُ البؤرة وحدَه يُسقِط
			// التعليقَ لكنّه يكتب «لم تصل الضغطةُ الثانية» — طلبًا لا ينتظره أحد)
			expect(say() === INITIAL && P.out.classList.contains('dim'),
				'Escape لا يعيد سطرَ النتيجة إلى تلميحه الأوّل — بعد إعادة الفتح «' + say() + '»');
			S();
			expect(say().indexOf(ALL) === -1, 'Escape أغلق الالتقاطَ ولم يُلغِ التعليق: S بعده قرأت «' + say() + '»');
		}],
		['فقدانُ البؤرة يُسقِط التعليقَ ويقول ذلك', function () {
			ctrlK();
			P.btn.focus();
			expect(/لم تصل الضغطةُ الثانية/.test(say()), 'فقدانُ البؤرة بعد Ctrl+K لا يُسقِط التعليقَ ولا يقوله — قال «' + say() + '»');
			P.field.focus(); S();
			expect(say().indexOf(ALL) === -1, 'فقدانُ البؤرة لم يُسقِط التعليق: S بعد العودة قرأت «' + say() + '»');
		}],
		['المهلةُ تُسقِط التعليقَ بمداها المعلَن', function () {
			ctrlK();
			const t = fireTimers();
			expect(t.length === 1 && t[0].ms >= 1000 && t[0].ms <= 8000,
				'مهلةُ التعليق ليست مؤقّتًا واحدًا بين ثانيةٍ وثمانٍ — ' + JSON.stringify(t.map(x => x.ms)));
			expect(/لم تصل الضغطةُ الثانية/.test(say()), 'انقضاءُ المهلة لا يُسقِط التعليقَ ولا يقوله — قال «' + say() + '»');
			S();
			expect(say().indexOf(ALL) === -1, 'انقضت المهلةُ ولم يسقط التعليق: S بعدها قرأت «' + say() + '»');
		}],
		['ضغطةُ IME تُسقِط التعليق — بصورها الأربع **كلٌّ وحدَها**: الشرطُ أربعةُ أضلاعٍ', function () {
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
		}],
		['ضغطةٌ واحدةٌ تُحسَم وتُعلِّم صفَّها، وCtrl+K مرّتين لا يُعلَّق ثانيةً', function () {
			key(P.field, 's', C('s', 'KeyS', { ctrlKey: true }));
			expect(say().indexOf(ONE) !== -1, 'Ctrl+S لا يُحسَم «' + ONE + '» — قال «' + say() + '»');
			expect(P.rowsByName[ONE] && P.rowsByName[ONE].classList.contains('kbd-hit'), 'صفُّ «' + ONE + '» لم يُعلَّم `kbd-hit`');
			ctrlK(); ctrlK();
			expect(!/ثمّ…/.test(say()) && pendingTimers().length === 0, 'Ctrl+K Ctrl+K عُلِّق ثانيةً — التسلسلُ ضغطتان لا أكثر');
		}],
		['الترشيح: بلا تشكيل، ومن وسط الاسم، ومنطوقٌ بالعدد', function () {
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
		}],
		['البحث: الأسهمُ تسير، وEscape يطوي ولا يمسح', async function () {
			P.sInput.focus();
			input(P.sInput, fx.search_query);
			await new Promise(r => setImmediate(r));
			await new Promise(r => setImmediate(r));
			const links = P.sResults.querySelectorAll('a');
			expect(!P.sResults.hidden && links.length >= 2, 'البحثُ عن «' + fx.search_query + '» لا يعرض نتيجتين على الأقلّ (' + links.length + ')');
			if (links.length >= 2) {
				ev = key(P.sInput, 'ArrowDown');
				expect(ev.defaultPrevented && getDocument().activeElement === links[0], '↓ من الحقل لا يركّز أوّلَ نتيجة');
				key(links[0], 'ArrowDown');
				expect(getDocument().activeElement === links[1], '↓ بين النتائج لا يسير إلى الثانية');
				key(links[1], 'ArrowUp');
				expect(getDocument().activeElement === links[0], '↑ بين النتائج لا يعود إلى الأولى');
				key(links[0], 'ArrowUp');
				expect(getDocument().activeElement === P.sInput, '↑ من أوّل نتيجةٍ لا يعود إلى الحقل');
				// ‏Escape والبؤرةُ على نتيجة: تُطوى القائمةُ وتعود البؤرةُ إلى الحقل لا إلى body
				key(P.sInput, 'ArrowDown');
				ev = key(links[0], 'Escape');
				expect(ev.defaultPrevented && P.sResults.hidden && getDocument().activeElement === P.sInput,
					'Escape على نتيجةٍ مركَّزة لا يطوي القائمةَ أو لا يعيد البؤرةَ إلى الحقل');
				input(P.sInput, fx.search_query);
				ev = key(P.sInput, 'Escape');
				expect(ev.defaultPrevented && P.sResults.hidden && P.sInput.value === fx.search_query,
					'Escape والنتائجُ ظاهرةٌ لا يمنع الحركةَ الأصليّة (مسحَ السؤال) أو لا يطوي القائمة');
				ev = key(P.sInput, 'Escape');
				expect(!ev.defaultPrevented, 'Escape الثانية والقائمةُ مطويّةٌ تُمنَع — الحقلُ لا يُمسَح كما اعتاد الزائر');
			}
		}],
	];
	// سيناريو ينهار يُسمّى: «انهار الصندوق» وحدَها لا تقول أيَّها.
	for (const [name, run] of SCENARIOS) {
		try { await run(); } catch (e) { fails.push('انهار سيناريو «' + name + '»: ' + (e && e.stack || e) + ' [CAP-04]'); }
	}
	process.stdout.write(JSON.stringify({ ran, fails }));
}
main().catch(e => { process.stdout.write(JSON.stringify({ ran: 0, fails: ['انهار الصندوق: ' + (e && e.stack || e) + ' [CAP-04]'] })); });
