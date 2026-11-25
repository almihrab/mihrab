# -*- coding: utf-8 -*-
"""البحثُ والطباعةُ والتقاطُ الاختصارات وصندوقُ السلوك [PRN-01] [CAP-01..04].

أقسامُ `main()` القديمة بنصّها، بترتيبها في `check_site.py` (‏`SECTIONS`)."""
from .core import *  # noqa: F401,F403

def s34_prn01_print(c):
    _c = vars(c)
    if "_css_get" in _c:
        _css_get = _c['_css_get']
    if "_kb_html" in _c:
        _kb_html = _c['_kb_html']
    if "_rules" in _c:
        _rules = _c['_rules']
    if "_tokens" in _c:
        _tokens = _c['_tokens']
    # ── [PRN-01] الطباعةُ تُخفي مقدّمةَ صفحة الاختصارات لا متنَ كلّ صفحة ──
    # `.content > p` في كتلة الطباعة كانت بلا قيدٍ (الجولة ‎15‎) فتُخفي فقراتِ وعناوينَ
    # وكتلَ **كلّ** صفحةِ توثيقٍ عند الطباعة: `/start/` تُطبَع بلا فقراتها السبع وعناوينها
    # الخمسة وكتلتها. التتالي المصغَّر لا يفهم `:has()` فلا يطابقه — وهذا المقصود: يُقاس
    # أنّ ابنًا مباشرًا لـ`main.content` لا يُخفى في الطباعة **بقاعدةٍ عامّة**، وأنّ القيدَ
    # موجودٌ في الورقة وجدولُه في الصفحة.
    _mc = [("main", {"content"}, False, False)]
    for _tag in ("p", "h2", "pre"):
        _d = _css_get(_rules, _tokens, _mc + [(_tag, set(), False, False)], "display", 1200, prn=True, raw=True)
        check(_d != "none", lambda: "‏`main.content > %s` في الطباعة `display: none` بقاعدةٍ عامّة — متنُ كلّ صفحةِ "
            "توثيقٍ يختفي من الورق [PRN-01]" % _tag)
    _cc = _css_get(_rules, _tokens, _mc, "column-count", 1200, prn=True, raw=True)
    check(_cc in (None, "auto", "1"), lambda: "‏`main.content` في الطباعة أعمدةٌ (%r) بقاعدةٍ عامّة — لصفحة الاختصارات وحدَها [PRN-01]" % _cc)
    with open(os.path.join(OUT, "assets", "mihrab-docs.css"), encoding="utf-8") as _pf:
        _prn_css = css_strip_comments(_pf.read(), "mihrab-docs.css")
    check(re.search(r"\.content:has\(\[data-kbd-table\]\)\s*>\s*p\b", _prn_css), lambda: "قاعدةُ إخفاء مقدّمة صفحة الاختصارات في الطباعة غائبةٌ أو بلا قيد `:has([data-kbd-table])` [PRN-01]")
    check("data-kbd-table" in _kb_html, lambda: "صفحةُ الاختصارات بلا `data-kbd-table` — قيدُ الطباعة لا يجد جدولَه [PRN-01]")
    # ⚠️ **والتتالي المصغَّرُ أعمى عن `:has()`** — فقاعدةٌ بقيدٍ يطابق كلَّ صفحة
    # (‏`.content:has(h1) > p { display: none }`) كانت تمرّ أخضرَ وهي تُخفي متنَ كلّ صفحة
    # من الورق (قِيس بالزرع). فكلُّ `:has(` في كتل الطباعة هو قيدُ الجدول بعينه لا غير.
    for _pm in re.finditer(r"@media\s+print\b[^{]*\{", _prn_css):
        _depth, _k = 1, _pm.end()
        while _depth and _k < len(_prn_css):
            _depth += {"{": 1, "}": -1}.get(_prn_css[_k], 0)
            _k += 1
        for _hm in re.finditer(r":has\(((?:[^()]|\([^()]*\))*)\)", _prn_css[_pm.end():_k]):
            check(_hm.group(1).strip() == "[data-kbd-table]",
                  lambda: "في كتلة الطباعة `:has(%s)` — القيدُ الوحيدُ المقبول `:has([data-kbd-table])`؛ "
                          "غيرُه قد يطابق كلَّ صفحةٍ والتتالي هنا لا يقيسه [PRN-01]" % _hm.group(1))
    _start_html = read("start/index.html")
    check(re.search(r'<main class="content">\s*<h1', _start_html) and "<p>" in _start_html, lambda: "صفحةُ `/start/` ليست `main.content` بفقراتٍ مباشرة — شاهدُ [PRN-01] زال")


def s35_cap01_chord_order(c):
    _c = vars(c)
    if "_docs_js" in _c:
        _docs_js = _c['_docs_js']
    if "_kb_html" in _c:
        _kb_html = _c['_kb_html']
    # ── [CAP-01] ما يُقارَن به الالتقاطُ بترتيب `chordFromEvent` نفسِه ──
    # ‏`data-chords` كانت السلسلةَ كما كُتبت في البيانات («Shift+Alt+Cmd+C»)، والحدثُ
    # يبنيها Ctrl ثمّ Cmd ثمّ Shift ثمّ Alt («Cmd+Shift+Alt+C») — فثلاثةُ اختصاراتِ ماك
    # كانت تُلتقَط «لا أمرَ معروفًا» والصفُّ أمام الزائر. الترتيبُ يُقرأ من docs.js لا يُكتَب.
    _ord = re.findall(r"if \(e\.(ctrl|meta|shift|alt)Key\) \{ parts\.push\('(\w+)'\); \}", _docs_js)
    check([m for m, _ in _ord] == ["ctrl", "meta", "shift", "alt"], lambda: "ترتيبُ المعدِّلات في `chordFromEvent` %r — يُراجَع `_canon_chord` في site/sitegen/pages.py [CAP-01]" % (_ord,))
    _mods = [n for _, n in _ord]
    _chords = [c for m in re.finditer(r'data-chords="([^"]*)"', _kb_html)
               for c in _html.unescape(m.group(1)).split("|") if c]
    check(len(_chords) >= 40, lambda: "عددُ الاختصارات في الصفحة %d — الحارسُ يقيس الهواء [CAP-01]" % len(_chords))
    for _ch in _chords:
        for _press in _ch.split(" "):
            _parts = _press.split("+")
            _pm = _parts[:-1]
            check(all(m in _mods for m in _pm), lambda: "معدِّلٌ لا يعرفه `chordFromEvent` في %r [CAP-01]" % _ch)
            check(_pm == [m for m in _mods if m in _pm], lambda: "‏`data-chords` تحمل %r وترتيبُ معدِّلاتها ليس ترتيبَ `chordFromEvent` (%s) — "
                "الالتقاطُ يقارن حرفًا بحرف فيردّ «لا أمرَ معروفًا» والصفُّ أمام الزائر [CAP-01]"
                % (_ch, "، ".join(_mods)))
            check(_parts[-1], lambda: "اختصارٌ ينتهي بـ`+` في %r [CAP-01]" % _ch)
    # وشاهدُ تفعيل: البياناتُ تحمل ترتيبًا غيرَ قانونيٍّ **عمدًا** (المعروضُ يبقى كما كُتب:
    # «Shift+Alt+Cmd» ترتيبُ ماك المألوف) فيُرى التقنينُ وهو يعمل. من قنّن البياناتِ كلَّها
    # فليُبقِ مثالًا واحدًا أو يُغذِّ الحارسَ به.
    with open(os.path.join(SITE, "data", "keybindings.json"), encoding="utf-8") as _kbf:
        _kb_raw = [e.get(k) for g in json.load(_kbf)["groups"] for e in g["items"]
                   for k in ("win", "mac") if e.get(k)]
    _raw_noncanon = [v for v in _kb_raw for _press in v.split(" ")
                     if _press.split("+")[:-1] != [m for m in _mods if m in _press.split("+")[:-1]]]
    need(_raw_noncanon, lambda: "لا اختصارَ في `keybindings.json` بترتيبٍ غيرِ قانونيّ — شاهدُ تفعيل [CAP-01] زال؛ أبقِ "
        "مثالًا («Shift+Alt+Cmd+C») أو غذِّ الحارسَ بغيره")
    _l = locals()
    for _n in ('_chords',):
        if _n in _l:
            setattr(c, _n, _l[_n])


def s36_cap02_sequences(c):
    _c = vars(c)
    if "_docs_js" in _c:
        _docs_js = _c['_docs_js']
    if "_ime" in _c:
        _ime = _c['_ime']
    if "_kb_html" in _c:
        _kb_html = _c['_kb_html']
    if "_node" in _c:
        _node = _c['_node']
    # ── [CAP-02] الالتقاطُ يلتقط تسلسلَ ضغطتين، ويُلغي التعليقَ حين يجب ──
    # `Ctrl+K` وحدَه ليس اختصارًا وهو بادئةُ تسلسلات؛ كان يُلتقَط «لا أمرَ معروفًا» ولا سبيلَ
    # إلى تسلسلٍ (الجولة ‎16‎). `chordStep` نقيّةٌ **فتُنفَّذ** بـnode على جدول الصفحة
    # المبنيّة نفسِه لا على صندوقٍ مصنوع: Ctrl+K ⇒ انتظار؛ ثمّ Ctrl+S ⇒ «اختصارات لوحة
    # المفاتيح»؛ Ctrl+P فوريّ؛ بعد انقضاء المهلة Ctrl+S ⇒ «حفظ الملفّ»؛ Ctrl+K S ⇒ «حفظ
    # الكلّ»؛ Ctrl+K Ctrl+K ⇒ لا أمرَ ولا تعليقَ ثانٍ. وساكنًا: المهلةُ ‎1–8‎ ث بمفتاحٍ لا
    # قيمة، والتعليقُ يُلغى في Escape وIME وblur والمهلة (الجولة ‎17‎: كان Escape يعود
    # قبل التصفير وblur لا يمسّه، فمن غادر الحقلَ وعاد خلال المهلة دُمجت ضغطتُه في تسلسلٍ
    # لم يقصده). كلُّ فرعٍ قِيس بمُصابه في tests/meta/mutants.json.
    _cs = re.search(r"function chordStep\(chord, pending, entries\) \{.*?\n\t\}", _docs_js, re.S)
    need(_cs, lambda: "لم تُعرَف `chordStep(chord, pending, entries)` في docs.js [CAP-02]")
    _cw = re.search(r"var CHORD_WAIT_MS = (\d+);", _docs_js)
    need(_cw, lambda: "لا `var CHORD_WAIT_MS = N;` في docs.js — المهلةُ رقمٌ مدفون [CAP-02]")
    check(1000 <= int(_cw.group(1)) <= 8000, lambda: "مهلةُ التسلسل %s مث — دون ثانيةٍ لا تُدرَك الضغطةُ الثانية، وفوق ثمانٍ يُدمَج ما لم "
        "يُقصَد [CAP-02]" % _cw.group(1))
    _cp = re.search(r"function clearPending\(\) \{(.*?)\n\t\}", _docs_js, re.S)
    need(_cp and "pendingChord = null;" in _cp.group(1) and "clearTimeout(pendingTimer)" in _cp.group(1), lambda: "‏`clearPending` لا تصفّر التعليقَ ومهلتَه معًا [CAP-02]")
    _cap = re.search(r"captureField\.addEventListener\('keydown', function \(e\) \{(.*?)\n\t\t\}\);", _docs_js, re.S)
    need(_cap, lambda: "معالجُ keydown للالتقاط لم يُعرَف بحدوده [CAP-02]")
    _cap_body = re.sub(r"/\*.*?\*/", "", _cap.group(1), flags=re.S)
    _esc2 = re.search(r"if \(e\.key === 'Escape'\) \{([^}]*)\}", _cap_body)
    _ro = re.search(r"function resetOut\(\) \{(.*?)\n\t\t\}", _docs_js, re.S)
    need(_esc2 and _ro and "resetOut();" in _esc2.group(1) and "clearPending();" in _ro.group(1), lambda: "Escape يُغلق الالتقاطَ ولا يُلغي التعليق — Ctrl+K ثمّ Escape ثمّ فتحٌ وS خلال المهلة "
        "⇒ «Ctrl+K S ← حفظ الكلّ» [CAP-02]")
    check("clearPending();" in _ime.group(1), lambda: "ضغطةُ IME أثناء التعليق لا تُلغيه — تُدمَج الضغطةُ المفهومةُ التالية في تسلسلٍ لم يُقصَد [CAP-02]")
    _dp = re.search(r"function dropPending\(\) \{(.*?)\n\t\t\}", _docs_js, re.S)
    need(_dp and "if (!pendingChord) { return; }" in _dp.group(1) and "clearPending();" in _dp.group(1), lambda: "‏`dropPending` لا تُسقِط التعليقَ أو لا تعود حين لا تعليق [CAP-02]")
    check("لم تصل الضغطةُ الثانية" in _dp.group(1), lambda: "سقوطُ التعليق صامتٌ — السطرُ يبقى يطلب الضغطةَ الثانية [CAP-02]")
    check("captureField.addEventListener('blur', dropPending);" in _docs_js, lambda: "فقدانُ البؤرة لا يُسقِط التعليق — المعالجُ على الحقل وحدَه لكنّ التعليقَ يبقى للعائد خلال "
        "المهلة [CAP-02]")
    check(re.search(r"var step = chordStep\(chord, pendingChord, chordTable\);\n\s*clearPending\(\);", _cap_body), lambda: "المعالجُ لا يستدعي `chordStep(chord, pendingChord, chordTable)` ثمّ يصفّر التعليقَ قبل الحسم [CAP-02]")
    check(re.search(r"if \(step\.wait\) \{.*?pendingChord = chord;.*?pendingTimer = setTimeout\(dropPending, CHORD_WAIT_MS\);\s*return;",
                     _cap_body, re.S), lambda: "فرعُ الانتظار لا يعلّق الضغطةَ بمهلة `CHORD_WAIT_MS` تسقط بـ`dropPending` ويعود [CAP-02]")
    _rows2 = [{"row": _html.unescape(m.group(2)), "chords": _html.unescape(m.group(1)).split("|")}
              for m in re.finditer(r'data-chords="([^"]*)"><td><span class="cmd-name">([^<]*)</span>', _kb_html)]
    check(len(_rows2) >= 40, lambda: "صفوفُ الاختصارات بأسمائها %d — الحارسُ يقيس الهواء [CAP-02]" % len(_rows2))
    _CAP02_JS = _cs.group(0) + "\nvar entries = " + json.dumps(_rows2, ensure_ascii=False) + r""";
function step(c, p) { var s = chordStep(c, p, entries); return [s.chord, s.row, s.wait]; }
var out = [];
out.push(step('Ctrl+K', null));
out.push(step('Ctrl+S', 'Ctrl+K'));
out.push(step('Ctrl+P', null));
out.push(step('Ctrl+S', null));
out.push(step('S', 'Ctrl+K'));
out.push(step('Ctrl+K', 'Ctrl+K'));
out.push(step('F24', null));
process.stdout.write(JSON.stringify(out));
"""
    _CAP02_WANT = [["Ctrl+K", None, True],
                   ["Ctrl+K Ctrl+S", "اختصارات لوحة المفاتيح", False],
                   ["Ctrl+P", "الانتقال السريع إلى ملفّ", False],
                   ["Ctrl+S", "حفظ الملفّ", False],
                   ["Ctrl+K S", "حفظ الكلّ", False],
                   ["Ctrl+K Ctrl+K", None, False],
                   ["F24", None, False]]
    _nr10 = subprocess.run([_node, "-e", _CAP02_JS], capture_output=True, encoding="utf-8",
                           errors="replace", timeout=60)
    need(_nr10.returncode == 0, lambda: "تعذّر تنفيذُ `chordStep` بـnode: %s [CAP-02]" % _nr10.stderr.strip()[-300:])
    _got10 = json.loads(_nr10.stdout)
    check(_got10 == _CAP02_WANT, lambda: "‏`chordStep` على جدول الصفحة ⇒ %r لا %r — المنتظَر: Ctrl+K ينتظر؛ Ctrl+K Ctrl+S "
        "«اختصارات لوحة المفاتيح»؛ Ctrl+P فوريّ؛ Ctrl+S بلا تعليقٍ «حفظ الملفّ»؛ Ctrl+K S "
        "«حفظ الكلّ»؛ Ctrl+K Ctrl+K لا أمرَ ولا انتظار؛ F24 لا شيء [CAP-02]" % (_got10, _CAP02_WANT))


def s37_cap03_key_not_char(c):
    _c = vars(c)
    if "_chords" in _c:
        _chords = _c['_chords']
    if "_docs_js" in _c:
        _docs_js = _c['_docs_js']
    if "_node" in _c:
        _node = _c['_node']
    # ── [CAP-03] الالتقاطُ يقرأ المفتاحَ لا المحرفَ المطبوع ──
    # على لوحةٍ عربيّة `Ctrl+S` تصل `key="س"`، و`Shift` يقلب «`» إلى «~»، وOption على ماك
    # يقلب C إلى «ç» — فكان «Ctrl+Shift+`» (طرفيّةٌ جديدة) و«Cmd+Shift+Alt+C» لا يُلتقَطان
    # أبدًا والصفُّ أمام الزائر. `chordFromEvent` **تُنفَّذ** بأحداثٍ مصنوعة.
    _cfe = re.search(r"\tvar CODE_KEY = \{.*?\n\tfunction chordFromEvent\(e\) \{.*?\n\t\}", _docs_js, re.S)
    need(_cfe, lambda: "لم تُعرَف `CODE_KEY` ثمّ `chordFromEvent` في docs.js [CAP-03]")
    _CAP03 = [({"ctrlKey": True, "key": "س", "code": "KeyS"}, "Ctrl+S"),
              ({"ctrlKey": True, "shiftKey": True, "key": "~", "code": "Backquote"}, "Ctrl+Shift+`"),
              ({"metaKey": True, "shiftKey": True, "altKey": True, "key": "ç", "code": "KeyC"}, "Cmd+Shift+Alt+C"),
              ({"ctrlKey": True, "shiftKey": True, "key": "{", "code": "BracketLeft"}, "Ctrl+Shift+["),
              ({"key": "س", "code": "KeyS"}, "S"),
              ({"key": "F1", "code": "F1"}, "F1"),
              ({"ctrlKey": True, "key": "k", "code": "KeyK"}, "Ctrl+K"),
              # الحرفُ الصغيرُ يُكبَّر: بلا ذلك يُبنى «Ctrl+s» فلا يطابق صفًّا واحدًا بحرف
              ({"ctrlKey": True, "key": "s", "code": "KeyS"}, "Ctrl+S"),
              # المعدِّلُ وحدَه ليس ضغطة: بلا ذلك يُكتب «Ctrl+Control» قبل أن يكمل الزائر
              ({"ctrlKey": True, "key": "Control", "code": "ControlLeft"}, None),
              ({"shiftKey": True, "key": "Shift", "code": "ShiftLeft"}, None),
              ({"key": " ", "code": "Space"}, "Space"),
              # المتصفّحُ يرسل `ArrowUp` والجدولُ يكتب `Up`: بلا ترجمةٍ لا يُلتقَط «Alt+Up» أبدًا
              ({"altKey": True, "key": "ArrowUp", "code": "ArrowUp"}, "Alt+Up"),
              # المفتاحُ الميّت (‏Option+E على ماك) يصل `Dead` لا محرفًا
              ({"metaKey": True, "altKey": True, "key": "Dead", "code": "KeyE"}, "Cmd+Alt+E")]
    # ورحلةُ ذهابٍ وإياب: كلُّ ضغطةٍ في جدول الصفحة تُصنَع حدثًا لاتينيًّا كما يرسله
    # المتصفّح، ثمّ تُعاد بـ`chordFromEvent` فيجب أن تعطي نصَّها نفسَه — وإلّا فصفٌّ في
    # الجدول لا يمكن أن يُلتقَط أبدًا.
    _CODE_OF = {"`": "Backquote", "-": "Minus", "=": "Equal", "[": "BracketLeft", "]": "BracketRight",
                "\\": "Backslash", ";": "Semicolon", "'": "Quote", ",": "Comma", ".": "Period", "/": "Slash"}
    # ⚠️ **الحدثُ كما يرسله المتصفّح، لا كما يكتبه الجدول.** كان الفرعُ الأخير يصنع
    # `key=الرمز` لكلّ ما لم يُعرَف، فمرّت الأسهمُ (المتصفّحُ يرسل `ArrowUp`) والرحلةُ تصدّق
    # نفسَها؛ وكانت ضغطاتُ Shift تُصنَع بالمحرف غيرِ المُزاح فبقي `CODE_KEY` وفرعُ `Digit`
    # بلا حارسٍ فعليّ (قِيس بالزرع). فمع Shift يُرسَل المحرفُ المُزاح على تخطيط US، والمفاتيحُ
    # المسمّاةُ من قائمةٍ صريحة، و**ما لا يُعرَف اسمُ حدثه يُفشِل الحارس** لا يمرّ صامتًا.
    _US_SHIFTED = {"`": "~", "-": "_", "=": "+", "[": "{", "]": "}", "\\": "|", ";": ":", "'": '"',
                   ",": "<", ".": ">", "/": "?", "1": "!", "2": "@", "3": "#", "4": "$", "5": "%",
                   "6": "^", "7": "&", "8": "*", "9": "(", "0": ")"}
    _NAMED = {"Up": "ArrowUp", "Down": "ArrowDown", "Left": "ArrowLeft", "Right": "ArrowRight",
              "Enter": "Enter", "Escape": "Escape", "Tab": "Tab", "Backspace": "Backspace",
              "Delete": "Delete", "Insert": "Insert", "Home": "Home", "End": "End",
              "PageUp": "PageUp", "PageDown": "PageDown"}
    _MODS = {"Ctrl": "ctrlKey", "Cmd": "metaKey", "Shift": "shiftKey", "Alt": "altKey"}
    for _press in sorted({p for c in _chords for p in c.split(" ")}):
        _toks = _press.split("+")
        _key = _toks[-1]
        _ev = {_MODS[t]: True for t in _toks[:-1] if t in _MODS}
        _shift = bool(_ev.get("shiftKey"))
        if re.fullmatch(r"[A-Z]", _key):
            _ev.update(key=_key if _shift else _key.lower(), code="Key" + _key)
        elif re.fullmatch(r"[0-9]", _key):
            _ev.update(key=_US_SHIFTED[_key] if _shift else _key, code="Digit" + _key)
        elif _key in _CODE_OF:
            _ev.update(key=_US_SHIFTED[_key] if _shift else _key, code=_CODE_OF[_key])
        elif _key == "Space":
            _ev.update(key=" ", code="Space")
        elif _key in _NAMED:
            _ev.update(key=_NAMED[_key], code=_NAMED[_key])
        elif re.fullmatch(r"F([1-9]|1[0-9]|2[0-4])", _key):
            _ev.update(key=_key, code=_key)
        else:
            bad("ضغطةٌ في جدول الصفحة لا يُعرَف اسمُ حدثها في المتصفّح: %r — أضِفها إلى "
                "`_NAMED` بما يرسله المتصفّح فعلًا، أو صحّح الجدول [CAP-03]" % _press)
            continue
        _CAP03.append((_ev, _press))
    _js3 = _cfe.group(0) + "\nprocess.stdout.write(JSON.stringify(%s.map(function (o) { return chordFromEvent(" \
        "Object.assign({ctrlKey: false, metaKey: false, shiftKey: false, altKey: false}, o)); })))" \
        % json.dumps([e for e, _ in _CAP03], ensure_ascii=False)
    _nr11 = subprocess.run([_node, "-e", _js3], capture_output=True, encoding="utf-8",
                           errors="replace", timeout=60)
    need(_nr11.returncode == 0, lambda: "تعذّر تنفيذُ `chordFromEvent` بـnode: %s [CAP-03]" % _nr11.stderr.strip()[-300:])
    for (_ev, _want), _got in zip(_CAP03, json.loads(_nr11.stdout)):
        check(_got == _want, lambda: "‏`chordFromEvent(%s)` ⇒ %r لا %r — المحرفُ المطبوعُ قُرئ مفتاحًا [CAP-03]"
            % (json.dumps(_ev, ensure_ascii=False), _got, _want))
    _known = set(_chords) | {p for c in _chords for p in c.split(" ")}
    check({"Ctrl+Shift+`", "Cmd+Shift+Alt+C"} <= _known, lambda: "شاهدا [CAP-03] لم يعودا في جدول الصفحة — يُغذّى الحارسُ بغيرهما")


def s38_cap04_sandbox(c):
    _c = vars(c)
    if "_kb_html" in _c:
        _kb_html = _c['_kb_html']
    if "_node" in _c:
        _node = _c['_node']
    # ── [CAP-04] صندوقٌ سلوكيّ: `docs.js` المشحونُ يُنفَّذ كاملًا على صفحةٍ مزيّفة ──
    # فحوصُ الالتقاط أعلاه تقرأ نصَّ المعالج، فكانت تُخدَع بإبطالٍ لا يمسّ النصّ: سطرُ
    # `blur` تعليقًا، و`if (false) resetOut();`، ومهلةٌ تُظلَّل بعد تعريفها — كلُّها خضراء
    # والميزةُ معطوبة (قِيس بالزرع). فيُشغَّل `tests/docs/docs_sandbox.js` على صفوف الصفحة
    # المبنيّة وفهرس بحثها، ويرسل أحداثًا كما يرسلها المتصفّح، ويقيس ما يقرؤه الزائر:
    # التعليقُ وحسمُه، وإلغاؤه بـEscape وفقدانِ البؤرة والمهلة وIME، والترشيحُ بلا تشكيلٍ
    # ومن وسط الاسم، والأسهمُ وEscape في نتائج البحث.
    def _plain(t):
        return re.sub(r"[ً-ْٰـ]", "", t).replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    _secs = []
    for _sm in re.finditer(r'<section class="kbd-section">(.*?)</section>', _kb_html, re.S):
        _rows = []
        for _tm in re.finditer(r'<tr data-search="([^"]*)"(?: data-chords="([^"]*)")?><td><span class="cmd-name">([^<]*)</span>',
                               _sm.group(1)):
            _rows.append({"search": _html.unescape(_tm.group(1)),
                          "chords": None if _tm.group(2) is None else _html.unescape(_tm.group(2)),
                          "name": _html.unescape(_tm.group(3))})
        _secs.append({"rows": _rows})
    _all_rows = [r for sec in _secs for r in sec["rows"]]
    _by_chord = {c: r["name"] for r in _all_rows if r["chords"] for c in r["chords"].split("|")}
    _save_all, _save_one = _by_chord.get("Ctrl+K S"), _by_chord.get("Ctrl+S")
    # صفٌّ تُطابَق كلمتُه الثانيةُ بلا تشكيل: مطابقةٌ من وسط الاسم **و**بلا شدّةٍ معًا
    _frow = next((r["name"] for r in _all_rows
                  if len(r["name"].split()) > 1 and _plain(r["name"].split()[1]) != r["name"].split()[1]), None)
    if not (_secs and _save_all and _save_one and _frow):
        bad("صفحةُ الاختصارات بلا ما يقيسه الصندوق (أقسام، Ctrl+K S، Ctrl+S، صفٌّ مشكول) [CAP-04]")
    else:
        with open(os.path.join(OUT, "search-index.json"), encoding="utf-8") as _sif:
            _sindex = json.load(_sif)
        # الصندوقُ يقيس الشجرةَ التي يبنيها `_page_tree`؛ وموضعٌ تفترق فيه عن شجرة المتصفّح
        # يجعل أخضرَه شهادةً على صفحةٍ غيرِ المشحونة — فيُقال قبل نتيجته.
        _tree, _tree_errs = _page_tree(_kb_html)
        for _te in _tree_errs:
            bad("keyboard/index.html: %s — الصندوقُ لا يرى ما يراه المتصفّح [CAP-04]" % _te)
        _fx = {"tree": _tree, "save_all": _save_all, "save_one": _save_one,
               "filter_row": _frow, "filter_query": _plain(_frow.split()[1]),
               "filter_query_raw": _frow.split()[1],
               "count_query": _save_all.split()[0],
               "search_query": "محراب", "index": _sindex}
        # الـfixture في مجلّدٍ مؤقّتٍ لا في `site/public`: `deploy_site.sh` يحزم `public/` كلَّه،
        # وحارسٌ يُقتَل بين الكتابة والحذف كان يترك فيه ملفًّا يُشحَن ولا يراه [OUT-03]
        # (يفحص `public/assets` وحدَه).
        import tempfile
        with tempfile.TemporaryDirectory() as _fxd:
            _fxp = os.path.join(_fxd, "cap04-fixture.json")
            with open(_fxp, "w", encoding="utf-8") as _fxf:
                json.dump(_fx, _fxf, ensure_ascii=False)
            try:
                _nr12 = subprocess.run([_node, os.path.join(ROOT, "tests", "docs", "docs_sandbox.js"),
                                        os.path.join(OUT, "assets", "docs.js"), _fxp],
                                       capture_output=True, encoding="utf-8", errors="replace", timeout=60)
                _sb_out, _sb_err = _nr12.stdout, _nr12.stderr
            except subprocess.TimeoutExpired:
                _sb_out, _sb_err = "", "انقضت ‎60‎ ثانية — مؤقّتٌ أو وعدٌ لا ينتهي في الصندوق"
        try:
            _sb = json.loads(_sb_out)
            # و`{}` أو `{"fails": "…"}` كانا `KeyError` أو حروفًا تُعدّ فشولًا لا خطأً مُسمًّى
            if not (isinstance(_sb, dict) and isinstance(_sb.get("fails"), list)
                    and isinstance(_sb.get("ran"), int)):
                raise ValueError(_sb_out)
        except ValueError:
            _sb = {"ran": 0, "fails": ["خرجُ الصندوق ليس JSON بشكل {ran, fails}: %s %s [CAP-04]"
                                       % (_sb_out[-200:], _sb_err[-300:])]}
        for _f in _sb["fails"]:
            bad(_f)
        # بلا فشلٍ مسارُ الصندوق واحدٌ لا يتفرّع (كلُّ تفرّعٍ فيه يمرّ بفشلٍ مُسمًّى)، فعددُه ثابت:
        # ‎42‎. والأرضيّةُ هي العددُ نفسُه — ‎35‎ كانت تُسقط السيناريو (٣) أو (٤) كلَّه صامتًا.
        if not _sb["fails"] and _sb["ran"] < 42:
            bad("الصندوقُ قاس %d توقّعًا لا أقلَّ من ‎42‎ — سيناريو سقط صامتًا [CAP-04]" % _sb["ran"])
