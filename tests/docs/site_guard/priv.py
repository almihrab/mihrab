# -*- coding: utf-8 -*-
"""دعوى الخصوصيّة وما يكذّبها في المخرَج [PRIV-01/02].

أقسامُ `main()` القديمة بنصّها، بترتيبها في `check_site.py` (‏`SECTIONS`)."""
from .core import *  # noqa: F401,F403

# الوسومُ التي تحرسها أقسامُ هذه الوحدة، بما يمسكه كلٌّ منها — منها يُولَّد جدولُها في
# `site/guide/checks.md` (‏`python tests/docs/check_site.py --list`)، ويحرس التطابقَ [GRD-03].
TAGS = {
    "PRIV-01": "دعوى خصوصيّةٍ في الصفحة الأولى أوسعَ ممّا يُبرهَن عليه",
    "PRIV-02": "ذكرًا للتتبّع خارج الجملة المضبوطة، أو كعكةً، أو مفتاحَ `localStorage` غيرَ مفتاحَي التفضيل",
}

def s06_priv01_claim(c):
    _c = vars(c)
    if "home" in _c:
        home = _c['home']
    # ── [PRIV-01] ⭐ دعوى الخصوصيّة مضبوطةٌ بقدرِ ما يُبرهَن عليه ───────────
    # جملةُ خصوصيّةٍ تكذب أسوأُ من غيابها: «بلا تتبّع» مجرّدةً أوسعُ ممّا نبرهن
    # عليه — الخادمُ يكتب سجلَّ طلباتٍ فيه عنوانُ من طلب. فالدعوى ضُيِّقت إلى ما
    # يُفحَص في الصفحة نفسِها: لا كعكةَ ولا سكربتَ في هذه الصفحة.
    if "بلا حساب، وبلا تتبّع." in home:
        bad("[PRIV-01] الصفحةُ الأولى تُعلن «بلا تتبّع» مجرّدةً — دعوى أوسعُ ممّا "
            "يُبرهَن عليه: الخادمُ يكتب سجلَّ طلباتٍ فيه عنوانُ من طلب. الصيغةُ "
            "المضبوطةُ تحدّد ما يُفحَص في هذه الصفحة: لا كعكةَ ولا سكربتَ تتبّع")
    if "وبلا كعكةٍ ولا سكربتِ تتبّعٍ في هذه الصفحة" not in home:
        bad("[PRIV-01] الصفحةُ الأولى بلا الدعوى المضبوطة — وهي التي تُفحَص فعلًا "
            "بحارسِ «لا سكربتَ داخليًّا في مخرَج الموقع»")


def s07_priv02_claim_and_output(c):
    # ── [PRIV-02] لا دعوى خصوصيّةٍ إلّا المضبوطة، ولا ما يكذّبها في المخرَج ──
    # ‏[PRIV-01] يطابق جملةً واحدةً حرفيًّا، فكانت تمرّ (قِيس بالزرع): دعوى عامّةٌ **بجانب**
    # المضبوطة («… في هذه الصفحة. ولا نتتبّعك أبدًا.»)، وكعكةٌ تُكتب في site.js تكذّب
    # «بلا كعكة» نفسَها. فيُقاس الطرفان: كلُّ ذكرٍ للتتبّع أو الكعكة في نصّ **أيّ** صفحةٍ
    # خارجَ الجملة المضبوطة عطب، وJS المخرَج لا يكتب كعكةً ولا يبلّغ أصلًا آخر، و
    # `localStorage` لمفتاحَي التفضيل وحدَهما (السمةُ والنظام: اختيارٌ لا هويّة).
    _PRIV_OK = "بلا حساب، وبلا كعكةٍ ولا سكربتِ تتبّعٍ في هذه الصفحة"
    _PRIV_WORD = re.compile(r"[نيت]?تتب[ً-ْ]*ع|كعك|كوكي|cookie", re.I)
    for _pf in sorted(glob.glob(os.path.join(OUT, "**", "*.html"), recursive=True)):
        with open(_pf, encoding="utf-8") as _pff:
            _pt = re.sub(r"<(script|style)\b.*?</\1>", " ", _pff.read(), flags=re.S)
        _pt = _html.unescape(re.sub(r"<[^>]+>", " ", _pt)).replace(_PRIV_OK, " ")
        _pt = " ".join(_pt.split())
        for _pm in _PRIV_WORD.finditer(_pt):
            bad("[PRIV-02] %s يذكر «%s» خارج الدعوى المضبوطة: «…%s…»"
                % (os.path.relpath(_pf, OUT).replace(os.sep, "/"), _pm.group(0),
                   _pt[max(0, _pm.start() - 40):_pm.end() + 40]))
    _PRIV_KEYS = {"mihrab-docs-theme", "mihrab-docs-platform"}
    for _jf in sorted(glob.glob(os.path.join(OUT, "assets", "*.js"))):
        with open(_jf, encoding="utf-8") as _jff:
            _jt = _jff.read()
        _jn = "assets/" + os.path.basename(_jf)
        for _pat, _why in ((r"document\.cookie", "يكتب كعكةً أو يقرؤها"),
                           (r"navigator\.sendBeacon|new\s+Image\s*\(|XMLHttpRequest|WebSocket|EventSource",
                            "يبلّغ بقناةٍ غيرِ `fetch` النسبيّ"),
                           (r"""["'`](?:https?:)?//(?!mihrab\.dev[/"'`])""", "فيه عنوانٌ مطلقٌ إلى أصلٍ آخر")):
            for _jm in re.finditer(_pat, _jt):
                bad("[PRIV-02] %s %s: «%s»" % (_jn, _why, _jt[_jm.start():_jm.start() + 60].split("\n")[0]))
        for _km in re.finditer(r"""localStorage\.setItem\(\s*['"]([^'"]*)['"]""", _jt):
            if _km.group(1) not in _PRIV_KEYS:
                bad("[PRIV-02] %s يحفظ في localStorage مفتاحًا غيرَ التفضيلَين: %r" % (_jn, _km.group(1)))
