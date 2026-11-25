# -*- coding: utf-8 -*-
"""الخطوط: نطاقا المحارف، والأوجه، وكتابةُ fonts.css."""
import os

from .data import ASSETS

# ═════════════════════ الخطوط ═════════════════════
# الوجوهُ المطلوبة. الاسمُ ⇒ (العائلة، الوزن).
# ── نطاقا المحارف ──
# الأوجهُ المورَّدةُ **مقلَّمة**: ملفُّ العربيّة لا يحمل حرفًا لاتينيًّا وبالعكس.
# وبلا `unicode-range` يصير الوجهان المتشاركان في الاسم والوزن **متنازعَين**:
# المتصفّحُ يأخذ الأخيرَ ويهمل الأوّلَ تمامًا (ليس سقوطًا بين وجهَي العائلة
# الواحدة — السقوطُ يكون إلى العائلة التالية في السلسلة). فيُعرَض نصفُ الموقع
# بخطِّ النظام ونصفُه بالخطّ المُورَّد، وهو **أسوأُ من عدم التوريد**: قبله كان
# الموقعُ متّسقًا بخطٍّ واحدٍ غيرِ مقصود، وبعده يصير مختلطًا في السطر الواحد.
#
# والمدى يقول للمتصفّح: «هذا الوجهُ لهذه المحارف» — فيُحمَّل ملفُّ العربيّة
# لصفحةٍ عربيّة، وملفُّ اللاتينيّة عند أوّل رقمٍ أو `mihrab.dev`. وذلك مكسبٌ
# ثانٍ: من لا يرى لاتينيًّا لا ينزّل ملفَّه.
# ⚠️ **ولا تداخُلَ بين المدَيَين.** مقطعٌ يطالب به الوجهان في العائلة والوزن
# نفسِهما يفوز فيه الأخيرُ إعلانًا — فكانت `U+200C-200E` و`U+2010-2011` و`U+204F`
# و`U+FEFF` مُسنَدةً فعليًّا إلى الملفّ اللاتينيّ، ومنها **`U+204F` وهي فاصلةٌ
# منقوطةٌ معكوسة** تُستعمل في النصوص السامّية. وأثرُها اليومَ معدومٌ (لا يرد منها في المخرَج إلا `U+200E`
# مرّتين، وهو محرفُ اتّجاهٍ عديمُ الشكل) — لكنّه لغمٌ لا عطبٌ واقع. فنُزِعت
# المقاطعُ المشتركةُ من `_UR_LA` وبقيت للعربيّة حيث تنتمي.
_UR_AR = ("U+0600-06FF,U+0750-077F,U+0870-088E,U+0890-0891,U+0898-08E1,"
          "U+08E3-08FF,U+200C-200E,U+2010-2011,U+204F,U+2E41,U+FB50-FDFF,"
          "U+FE70-FEFF,U+102E0-102FB,U+10E60-10E7E,U+1EE00-1EEBB")
_UR_LA = ("U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,"
          "U+0304,U+0308,U+0329,U+2000-200B,U+200F,U+2012-204E,"
          "U+2050-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,"
          "U+FFFD")

# ── واسمُ عائلةٍ ثانٍ للملفَّين العربيَّين، لسلسلة أحاديّ المسافة ──
# `IBM Plex Mono` و`Cascadia Mono` و`Consolas` بلا محارفَ عربيّة، فكان العربيُّ
# في كتل الشيفرة يسقط إلى `Courier New`: خطٌّ ذو أذنابٍ على متنٍ سنسريف — سطرٌ
# متّسقُ العرض **غيرُ متّسق الأسرة**، في `.محراب/settings.json` وفي
# `اطبع "السلام عليكم"`. والعلاجُ بصفرِ بايتٍ إضافيّ: **الملفّان العربيّان
# نفسُهما** تحت اسمٍ ثانٍ يقف أوّلَ `--font-mono`. والمتصفّحُ لا ينزّل الملفَّ
# مرّتين: التخزينُ على العنوان لا على اسم العائلة.
#
# ⚠️ ومداه **أضيقُ** من `_UR_AR` عمدًا: كتلُ الخطّ العربيّ وحدَها. فلا يمرّ به
# حرفٌ لاتينيٌّ ولا رقمٌ لاتينيٌّ ولا مسافةٌ ولا واصلة — وكلُّ ما يُحاذى رأسيًّا في
# كتلة شيفرةٍ يبقى في الخطّ أحاديّ المسافة، فالمحاذاةُ لا تُمَسّ رياضيًّا. ولذلك
# سقطت منه `U+200C-200E` و`U+2010-2011` و`U+204F` و`U+2E41`: الأُولى عديمةُ
# الشكل فلا فرق، والواصلاتُ والفاصلتان المعكوستان (‏`204F` و`2E41`) لها عرضٌ
# يُحاذى فتبقى لأحاديّ المسافة. ويحرس الضيقَ [FNT-01] على `fonts.css` المبنيّة
# لا على هذا المتغيّر. (وما لا يسقط: الأرقامُ العربيّة `٠–٩` — انظر لغمَها
# في `assets/fonts/README.md`.)
_UR_AR_MONO = ("U+0600-06FF,U+0750-077F,U+0870-088E,U+0890-0891,U+0898-08E1,"
               "U+08E3-08FF,U+FB50-FDFF,U+FE70-FEFF,U+102E0-102FB,"
               "U+10E60-10E7E,U+1EE00-1EEBB")
MONO_AR_FAMILY = "Mihrab Code Arabic"

FONT_FACES = [
    ("plex-arabic-400.woff2", "IBM Plex Sans Arabic", 400, _UR_AR),
    ("plex-arabic-600.woff2", "IBM Plex Sans Arabic", 600, _UR_AR),
    ("plex-latin-400.woff2", "IBM Plex Sans Arabic", 400, _UR_LA),
    ("plex-latin-600.woff2", "IBM Plex Sans Arabic", 600, _UR_LA),
    ("plex-arabic-400.woff2", MONO_AR_FAMILY, 400, _UR_AR_MONO),
    ("plex-arabic-600.woff2", MONO_AR_FAMILY, 600, _UR_AR_MONO),
]
# الملفّاتُ الفريدة: وجهان يتشاركان ملفًّا يُنسَخ مرّةً ويُعَدّ مرّة.
FONT_FILES = []
for _fn, _fam, _wt, _ur in FONT_FACES:
    if _fn not in FONT_FILES:
        FONT_FILES.append(_fn)


def _faces_word(n):
    """تمييزُ العدد: ‏3–10 جمعٌ مجرور، وما فوقه مفردٌ منصوب — كما في `hitsWord`."""
    if n == 1:
        return "وجهٍ واحد"
    if n == 2:
        return "وجهَين"
    return "%d أوجه" % n if n <= 10 else "%d وجهًا" % n


def _files_word(n, total):
    """‏«4/4 ملفًّا» لحنٌ بالقاعدة نفسِها التي تُصحَّح بها الأوجهُ في السطر ذاته:
    ‏3–10 تمييزُها جمعٌ مجرور («4 ملفّات»)، لا مفردٌ منصوب."""
    if n == total:
        return ("الملفُّ الواحد" if total == 1 else
                "الملفّان" if total == 2 else
                "الملفّاتُ الـ%d كلُّها" % total if total <= 10 else
                "الـ%d ملفًّا كلُّها" % total)
    return "%d من %d %s" % (n, total,
                             "ملفّات" if total <= 10 else "ملفًّا")


def write_fonts_css(dst_assets):
    """يولّد `fonts.css` من الملفّات **الموجودة فعلًا** وينسخها.

    ولا يكتب `@font-face` لملفٍّ غائب: وجهٌ يشير إلى ملفٍّ غير موجود لا يفشل بصوت —
    بل يُطلق 404 في كلّ فتحةِ صفحة ثمّ يسقط صامتًا إلى خطٍّ آخر، فيبدو الموقعُ سليمًا
    وهو يعرض خطًّا لم نصمّم عليه. والسقوطُ الصريح في سلسلة `--font-ar` أشرفُ من ذلك.
    """
    src_dir = os.path.join(ASSETS, "fonts")
    faces, present = [], []
    for fn, family, weight, urange in FONT_FACES:
        if os.path.isfile(os.path.join(src_dir, fn)):
            if fn not in present:
                present.append(fn)
            faces.append(
                '@font-face{font-family:"%s";src:url("fonts/%s") format("woff2");'
                'font-weight:%d;font-display:swap;unicode-range:%s}'
                % (family, fn, weight, urange))

    if present:
        dst_dir = os.path.join(dst_assets, "fonts")
        os.makedirs(dst_dir, exist_ok=True)
        for fn in present:
            with open(os.path.join(src_dir, fn), "rb") as f_in, \
                    open(os.path.join(dst_dir, fn), "wb") as f_out:
                f_out.write(f_in.read())
        # ── ونصُّ الرخصة **يسافر مع الملفّات** ──
        # ‏OFL‑1.1 البندُ ٢ يشترط مصاحبةَ الإشعار والرخصة لكلّ نسخةٍ يُعاد
        # توزيعُها، **والنشرُ على الويب إعادةُ توزيع**. فلا يكفي إيداعُ `OFL.txt`
        # في المصدر: حلقةُ `main()` العامّةُ تتخطّى المجلّدات، وهذه الدالّةُ تنسخ
        # ملفّاتِ `FONT_FACES` وحدَها — فكان الخطُّ يصل الزائرَ عاريًا من إشعاره.
        # والقاعدةُ مكتوبةٌ في `.gitignore` («إلزامٌ قانونيٌّ لا نظافةٌ اختياريّة»)
        # ومطبَّقةٌ على `patches/fonts/` منذ البداية، وغابت عن هذا المجلّد وحدَه.
        for _doc in ("OFL.txt", "README.md"):
            _src = os.path.join(src_dir, _doc)
            if os.path.isfile(_src):
                with open(_src, "rb") as f_in,                         open(os.path.join(dst_dir, _doc), "wb") as f_out:
                    f_out.write(f_in.read())
        assert os.path.isfile(os.path.join(dst_dir, "OFL.txt")), (
            "أوجهٌ مورَّدةٌ بلا `site/assets/fonts/OFL.txt` — إرفاقُ الرخصة شرطٌ "
            "قانونيٌّ لإعادة التوزيع، والنشرُ إعادةُ توزيع")

    header = ('@charset "UTF-8";\n'
              "/* مولَّد من site/sitegen/fonts.py — لا تحرّره. %s مورَّدة، في %s. */\n"
              % (_files_word(len(present), len(FONT_FILES)), _faces_word(len(faces))))
    with open(os.path.join(dst_assets, "fonts.css"), "w", encoding="utf-8", newline="\n") as f:
        f.write(header + "\n".join(faces) + "\n")

    # ⚠️ ولا يُقال «يسقط إلى Noto Sans Arabic»: ‏Noto Sans Arabic **غيرُ منصَّبٍ
    #    على ويندوز**، وأكثرُ جمهورِ محرابٍ على ويندوز — فالسقوطُ الفعليُّ هناك
    #    إلى `Segoe UI`. والرسالةُ التي تطمئن المطوّرَ بأنّ البديلَ هو ما اختاره
    #    تُخفي أنّ الأغلبيّةَ ترى خطًّا ثالثًا لم يُصمَّم عليه شيء.
    #
    # **والنقصُ الجزئيُّ أسوأُ من التامّ**: وجهٌ عربيٌّ بلا نظيرِه اللاتينيِّ يجعل
    # السطرَ الواحدَ بخطَّين — ولذلك يُسمّى الناقصُ بالاسم لا بالعدد.
    if len(present) != len(FONT_FILES):
        missing = [fn for fn in FONT_FILES if fn not in present]
        print("  ⚠️  %d/%d ملفِّ خطٍّ مورَّد — ينقص: %s. "
              "وما ينقص يُعرَض بخطّ النظام (‏Segoe UI على ويندوز)، فيصير السطرُ "
              "المختلَطُ بخطَّين. ضَع woff2 في site/assets/fonts/."
              % (len(present), len(FONT_FILES), "، ".join(missing)))
    else:
        print("  ✅ %s مورَّدة في %s — الموقعُ يُعرَض كما صُمِّم."
              % (_files_word(len(present), len(FONT_FILES)), _faces_word(len(faces))))
