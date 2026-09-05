#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""‏[DR-08] رياضيّاتُ الأعمدة في xterm تحسب من اليسار — تُصحَّح للصفوف اليمينيّة.

## العطبُ ولماذا لا تكفي ورقةُ الأنماط

بعد تحويل الطرفيّة إلى مسار DOM [DR-05/ب] صارت الحروفُ تتّصل، وبقواعد اتّجاهٍ
لكلّ صفٍّ يُرسى السطرُ العربيُّ يمينًا. **لكنّ ما يُصلحه التخطيطُ لا يُصلح الحساب**:
xterm يترجم بين البكسل والعمود بمقدارٍ من **يسار** الشاشة دائمًا:

  • `Mouse.getCoordsRelativeToElement` ⇒ `clientX - rect.left - paddingLeft`
  • `DomRenderer._createSelectionElement` ⇒ `style.left = colStart * cellWidth`

فعلى صفٍّ يُصيَّر يمينيًّا ينعكس كلُّ شيء: قِيس أنّ نقرةً مزدوجةً عند `x=975` على
أوّل حرفٍ عربيٍّ تُنتج مستطيلَي تحديدٍ عند `x=368` و`x=166`. أي أنّ المستخدمَ يرى
النصَّ صحيحًا **ويحدّد غيرَه** — وهو أسوأُ من عرضٍ مقلوبٍ يعرف صاحبُه أنّه مقلوب.

## لماذا رقعةٌ على المشحون لا على المصدر

‏`node_modules/@xterm/xterm/package.json` يعلن `main: lib/xterm.js`، و
`terminalInstance.ts` يحمّله بـ`importAMDNodeModule('@xterm/xterm','lib/xterm.js')`.
فالمشحونُ **حزمةٌ مبنيّةٌ مصغَّرة** (‏٣٨٥ ك.ب في سطرٍ واحد) لا مصدرٌ يُصرَّف معنا.
و`node_modules` يُعاد تثبيتُه بـ`npm ci` في كلّ بناءٍ نظيف، فلا يُرقَّع هناك:
يُرقَّع **بعد الحزم** على `$APP_DIR/node_modules/...` — و`npm ci` لا يلمس المخرَج.

## ثلاثةُ أسيجةٍ تمنع هذا من أن يصير رقعةً عمياء

  ‏(أ) **حارسُ إصدار**: الرقعةُ مقيسةٌ على `6.1.0-beta.285` وحدَه. إصدارٌ آخرُ ⇒
      إجهاضٌ صريح، لا محاولةُ تخمين. المُصغِّرُ يبدّل الأسماءَ بين النسخ.
      وأثبتَ الحارسُ نفسَه في ترقية المنبع إلى 1.126: قفز xterm من ‏beta.213 إلى
      ‏beta.285، فأوقف البناءَ باسم السبب. وقد تغيّرت مِرساةُ الفأرة فعلًا —
      ‏`getCoords` صارت `return …, c}` بعد أن كانت `… , c):void 0}` — بينما بقيت
      دلالاتُ الوسائط (`s` العنصر · `r` الأعمدة · `o` الصفوف) كما قِيست. ولو كان
      الحارسُ متساهلًا لمرّت المِرساةُ الأولى بلا تطبيق، ولبقي التحديدُ مقلوبًا
      في بناءٍ كلُّ فحوصِه خضراء.
  ‏(ب) **كلُّ مِرساةٍ مرّةً واحدةً بالضبط**. مِرساةٌ تقع مرّتين تعني أنّنا نرقّع
      موضعًا لم نقرأه — والفشلُ حينها أسلمُ من النجاح.
  ‏(ج) **وسمُ تكرار**: إعادةُ التشغيل على ملفٍّ مُرقَّعٍ تمرّ بلا عمل.

## وما لا تُصلحه — يُقال ولا يُدَّعى

القلبُ **مرآةٌ حسابيّة**: `العمود ⟵ الأعمدة + 1 − العمود`. وهي صحيحةٌ تمامًا على
سطرٍ عربيٍّ خالص، و**تقريبيّةٌ على سطرٍ مختلط** (عربيٌّ فيه مقاطعُ لاتينيّة): هناك
لا يكفي الانعكاسُ بل تلزم خريطةُ ترتيبٍ بصريٍّ ⟷ منطقيٍّ كاملةٌ من خوارزميّة
الاتّجاه. والسطورُ اللاتينيّةُ الخالصةُ لا تُمَسّ إطلاقًا (تبقى يساريّةً وحسابُها كما هو).

الاستعمال:  python build/patch_xterm_bidi.py <APP_DIR>
"""
import io
import json
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

SUPPORTED_VERSION = "6.1.0-beta.285"
MARK = "/*mihrab-bidi*/"

# ── المُساعِد: أهذا الصفُّ يمينيّ؟ ────────────────────────────────────────────
# يُحقن مرّةً في رأس الحزمة. والقرارُ **من نصّ الصفّ المُصيَّر** لا من الإعدادات:
# هو المصدرُ نفسُه الذي تقرؤه `unicode-bidi: plaintext` في المتصفّح، فلا يفترق
# الحسابُ عن التخطيط. وقاعدةُ الاختيار قاعدةُ المواصفة: **أوّلُ محرفٍ قويّ**.
HELPER = (
    MARK
    + "(function(){var G=typeof globalThis!=='undefined'?globalThis:window;"
    + "G.__mihrabRtlText=function(t){if(!t)return false;for(var i=0;i<t.length;i++){"
    + "var c=t.charCodeAt(i);"
    + "if((c>=0x0590&&c<=0x08FF)||(c>=0xFB1D&&c<=0xFDFF)||(c>=0xFE70&&c<=0xFEFC))return true;"
    + "if((c>=0x41&&c<=0x5A)||(c>=0x61&&c<=0x7A)||(c>=0x00C0&&c<=0x024F))return false;}"
    + "return false;};"
    + "G.__mihrabRtlRow=function(el,y){try{if(!el||!el.querySelector)return false;"
    + "var rows=el.querySelector('.xterm-rows')||"
    + "(el.parentElement&&el.parentElement.querySelector('.xterm-rows'));"
    + "if(!rows||!rows.children||!rows.children[y])return false;"
    + "return G.__mihrabRtlText(rows.children[y].textContent);}catch(e){return false;}};"
    + "})();"
)

# ── المِرساةُ الأولى: إحداثيّاتُ الفأرة ⟵ عمود ──────────────────────────────
# ‏`s` عنصرُ الشاشة · `r` عددُ الأعمدة · `c[1]` الصفُّ (‏1-based بعد التقريب).
# القلبُ **بعد** التثبيت في المدى لا قبله، وإلّا خرج العمودُ عن الحدّ.
MOUSE_OLD = ("c[1]=Math.min(Math.max(c[1],1),o),c}")
MOUSE_NEW = ("c[1]=Math.min(Math.max(c[1],1),o),"
             + MARK + "(function(){try{if(globalThis.__mihrabRtlRow(s,c[1]-1))"
             + "c[0]=r+1-c[0];}catch(e){}})(),"
             + "c}")

# ── المِرساةُ الثانية: مستطيلُ التحديد ───────────────────────────────────────
# ‏`e` رقمُ الصفّ · `o` إزاحةُ العمود بالبكسل. على صفٍّ يمينيٍّ تُقاس الإزاحةُ من
# اليمين. و**لا يُستعمل `right`**: جُرِّب فوُضِع المستطيلُ في غير موضعه لأنّ الصندوقَ
# الحاوي ليس الشاشةَ كما بدا. فالحسابُ صريحٌ من عرض اللوحة: `canvas − o − n`.
SEL_OLD = "r.style.left=`${o}px`,"
SEL_NEW = (MARK + "r.style.left=`${(globalThis.__mihrabRtlRow&&globalThis.__mihrabRtlRow(this._screenElement||this._rowContainer,e))?(this.dimensions.css.canvas.width-o-n):o}px`,")


def fail(msg):
    print("❌ " + msg, file=sys.stderr)
    sys.exit(1)


def main(app_dir):
    pkg_dir = os.path.join(app_dir, "node_modules", "@xterm", "xterm")
    lib = os.path.join(pkg_dir, "lib", "xterm.js")
    meta = os.path.join(pkg_dir, "package.json")
    if not os.path.isfile(lib):
        fail("لا حزمةَ xterm مشحونة في " + lib)

    # البناءُ الثابت (`vscode-web`) يشحن `lib/` و`css/` **بلا `package.json`** — قِيس
    # على 1.126: مجلّدان فقط. فسقوطُ الإصدار ليس سقوطَ الحزمة.
    #
    # ولا يُتخطّى الترقيعُ لذلك: **المراسي أصدقُ من رقم الإصدار**. شرطُ «وقعت مرّةً
    # واحدةً بالضبط» أدناه يرفض أيَّ حزمةٍ ليست ما قِيس — والمُصغِّرُ يبدّل الأسماءَ
    # بين النسخ فيسقط العددُ فورًا. فحصُ الإصدارِ فحصٌ رخيصٌ سابق، لا الفحصَ الحاسم.
    version = None
    if os.path.isfile(meta):
        version = json.load(io.open(meta, encoding="utf-8")).get("version")
        if version != SUPPORTED_VERSION:
            fail("‏xterm " + str(version) + " لا " + SUPPORTED_VERSION + " — الرقعةُ مقيسةٌ "
                 "على هذا الإصدار وحدَه، والمُصغِّرُ يبدّل الأسماءَ بين النسخ. "
                 "أعِد قياسَ المراسي ثمّ حدِّث SUPPORTED_VERSION.")
    else:
        version = SUPPORTED_VERSION + " (غيرُ معلَن)"
        print("  ℹ️ لا package.json في هذه الشجرة — بوّابةُ الإصدار متخطّاةٌ بسببٍ "
              "معلَن، وعدُّ المراسي أدناه هو الفحصُ الحاسم.")

    src = io.open(lib, encoding="utf-8", newline="").read()
    if MARK in src:
        print("  ⏭️ xterm مُرقَّعٌ سلفًا بـbidi (لا عمل)")
        return 0

    for name, anchor in (("إحداثيّاتُ الفأرة", MOUSE_OLD), ("مستطيلُ التحديد", SEL_OLD)):
        n = src.count(anchor)
        if n != 1:
            fail("مِرساةُ «" + name + "» وقعت " + str(n) + " مرّةً لا مرّةً واحدة — "
                 "الحزمةُ ليست ما قِيس. لا يُرقَّع موضعٌ لم يُقرأ.")

    out = HELPER + src.replace(MOUSE_OLD, MOUSE_NEW, 1).replace(SEL_OLD, SEL_NEW, 1)

    tmp = lib + ".mihrab-tmp"
    io.open(tmp, "w", encoding="utf-8", newline="").write(out)
    os.replace(tmp, lib)          # ذرّيّة: لا حزمةَ نصفَ مكتوبةٍ لو انقطع
    print("  ✅ xterm " + version + ": رياضيّاتُ الأعمدة تعرف الصفَّ اليمينيّ "
          "(‏فأرة + تحديد) [DR-08]")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        fail("الاستعمال: python build/patch_xterm_bidi.py <APP_DIR>")
    sys.exit(main(sys.argv[1]))
