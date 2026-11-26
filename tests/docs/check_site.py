#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فحصٌ بنيويّ لمخرَج موقع محراب.

يمسك الأعطالَ التي **لا تظهر في المتصفّح**: زرًّا يقود إلى صفحةٍ لم تُبنَ، ووسمًا
يبحث عنه جافاسكربت ولا يجده فيموت السلوكُ كلُّه صامتًا، ومسارًا مطلقًا يربط المخرَج
بمضيفٍ بعينه فيكسر المرآة. وكلُّها أعطالٌ تمرّ من مراجعةِ العين لأنّ الصفحة تبدو سليمة.

    python tests/docs/check_site.py          # يبني ثمّ يفحص
    python tests/docs/check_site.py --no-build

هذا الملفّ نقطةُ الدخول وحدَها (‏`deploy_site.sh` وCI وحارسُ الحرّاس يستدعونه باسمه). الفحوصُ في
`site_guard/` بأقسامها القديمة من `main()` وبنصّها:
- `core.py`: ‏`check`/`need`/`bad` والعدّادُ والبصمة، و`read`، وشجرةُ الصفحة، وماسحُ CSS، و`report`.
- `out.py`: الحتميّةُ [DET-01] وحدودُ المولِّد [GEN-01] والمطابقةُ لبناءٍ نظيف [OUT-0x] والتجريدُ [MIN-0x].
- `priv.py`: دعوى الخصوصيّة [PRIV-01/02].   ‏`fonts.py`: الأوراق [CSS-01] والخطوط [FNT-01].
- `android.py`: ‏[AND-01..07].   ‏`capture.py`: البحثُ والطباعة والالتقاط وصندوقُ السلوك [CAP-0x].
- `release.py`: ‏404 [W404] والمانيفست [MAN-01] وروابطُ الهويّة ومعاينةُ ألف.
وما يعبر الأقسام (‏≈٢٧ اسمًا) يمرّ في سياقٍ صريح `c`: كلُّ قسمٍ يقرأ ما يحتاجه في أوّله ويكتب ما
يحتاجه غيرُه في آخره.
"""
import os
import sys
import types

# ولا بايتكود بجانب الحارس: ‏`.pyc` يُتحقَّق منه بالحجم وبزمن التعديل بالثواني، فمُصابٌ بالطول
# نفسه يُزرَع في الثانية نفسها قد يُشغَّل قديمُه — فيُقرأ «نجا» وهو لم يُقَس.
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_guard.core import *  # noqa: E402,F401,F403 — ‏test_strip يستورد css_strip_comments و_Stop من هنا
from site_guard import android, capture, fonts, out, priv, release  # noqa: E402
from site_guard import core as _core  # noqa: E402 — القسمُ الجاري وتتبّعُه (‏MIHRAB_GUARD_TRACE)

# الأقسامُ بترتيبها القديم في `main()` — الترتيبُ دلالة: ‏`need` وبوّاباتُ `if fails: return` توقف ما بعدها.
SECTIONS = [
    out.s01_det01_determinism,
    out.s02_gen01_sitegen_bounds,
    out.s03_required_files,
    out.s04_out02_clean_build,
    out.s05_site_js_anchors,
    priv.s06_priv01_claim,
    priv.s07_priv02_claim_and_output,
    out.s08_out03_nothing_foreign,
    out.s09_min01_strip_equivalence,
    out.s10_min02_gzip_cap,
    out.s11_data_island,
    out.s12_no_absolute_paths,
    out.s13_local_assets_exist,
    fonts.s14_css01_stylesheets,
    fonts.s15_fnt01_faces,
    fonts.s16_fnt01_inventory,
    fonts.s17_fnt01_font_faces_promise,
    fonts.s18_fnt01_hash_family_weight,
    fonts.s19_fnt01_pages_load_sheet,
    fonts.s20_fnt01_glyph_coverage,
    fonts.s21_fnt01_license,
    fonts.s22_fnt01_mono_alias,
    android.s23_and01_measured,
    android.s24_and01_no_serif,
    android.s25_and06_letter_spacing,
    android.s26_and07_decimal_size,
    android.s27_and01_copy_edge,
    android.s28_and01_hero_gap,
    android.s29_and02_capture_ime,
    android.s30_and03_ios_card,
    android.s31_and04_touch_targets,
    android.s32_and05_boot_numbers,
    android.s33_and08_search_arrows_filter,
    capture.s34_prn01_print,
    capture.s35_cap01_chord_order,
    capture.s36_cap02_sequences,
    capture.s37_cap03_key_not_char,
    capture.s38_cap04_sandbox,
    release.s39_w404_every_origin,
    release.s40_manifest_platforms,
    release.s41_identity_links,
    out.s42_out01_fresh_output,
    release.s43_alif_pin,
    release.s44_man01_manifest,
]


def _layout():
    """[GRD-01] كلُّ قسمٍ `sNN_…` في وحدات `site_guard` مسجَّلٌ في SECTIONS مرّةً، وبترتيبٍ متّصل.

    قسمٌ يُسقَط من القائمة لا يُرى في العدد ولا في البصمة إن كان فشلُه بـ`bad()` وحدها (قِيس:
    ‎11‎ قسمًا من ‎44‎ يُسقَط أحدُها والحارسُ أخضرُ بالعدد والبصمة نفسيهما). ويُبلَّغ بـ`bad` لا
    `check` عمدًا: ‏`check` يدخل العدّادَ والبصمة، فيصير فحصُ البنية نفسُه فرقًا في `same_guard`."""
    import inspect
    import re as _re
    mods = (android, capture, fonts, out, priv, release)
    defined = {f for m in mods for n, f in vars(m).items()
               if _re.fullmatch(r"s\d\d_\w+", n) and inspect.isfunction(f)}
    errs = []
    lost = sorted(f.__module__ + "." + f.__name__ for f in defined - set(SECTIONS))
    if lost:
        errs.append("قسمٌ معرَّفٌ غيرُ مسجَّل في SECTIONS: %s" % "، ".join(lost))
    nums = [s.__name__[1:3] for s in SECTIONS]
    if nums != ["%02d" % i for i in range(1, len(nums) + 1)]:
        errs.append("SECTIONS ليست s01..s%02d متّصلةً بلا تكرار: %s" % (len(nums), " ".join(nums)))
    return errs


def main():
    """يشغّل الأقسامَ بترتيبها؛ قسمٌ يُرجع قيمةً يُنهي الحارسَ بها. والسياقُ يحمل ما يعبر الأقسام."""
    # بنيةٌ مكسورةٌ توقف الحارسَ **قبل** أيّ قسم: لا يُوثَق بقياسٍ على حارسٍ أُسقط منه قسمٌ أو
    # تكرّر — والإيقافُ صريحٌ هنا لا ضمنيٌّ عند أوّل بوّابة `if fails`.
    _lay = _layout()
    if _lay:
        for _e in _lay:
            bad("[GRD-01] بنيةُ الحارس: " + _e)
        report()
        return 1
    c = types.SimpleNamespace()
    for _sec in SECTIONS:
        _core.current = _sec.__name__
        _r = _sec(c)
        if _r is not None:
            # قسمٌ أنهى الحارسَ ولا عطبَ مجموعًا قطّ: الفشلُ فشلُه هو، مطبوعًا لا بـ`bad`
            # (فشلُ البناء في s02). أمّا بوّابةُ `if fails: return 1` فعطوبُها لأقسامٍ قبلها.
            if _r and not fails:
                _core._mark("return")
            return _r
    _core.current = None
    return 1 if fails else 0


def _run():
    """‏`need` يوقف بعد عرض ما جُمع، وانهيارٌ غيرُ متوقَّعٍ يُعرَض مع ما جُمع قبله."""
    try:
        try:
            return main()
        except _Stop as e:
            _core.current = None  # الإيقافُ سُجِّل في `need` نفسِه
            bad(str(e))
        except Exception:  # noqa: BLE001
            # الانهيارُ يُنسَب إلى قسمه نوعًا مستقلًّا، فلا يُقرأ «احمرّ القسم» تغطيةً — وموضعُه
            # من الاستثناء نفسِه لا من هنا. وخارجَ الأقسام (‏`_layout`) يُسجَّل لـ`<main>`.
            import traceback
            _fr = traceback.extract_tb(sys.exc_info()[2])[-1]
            _core._mark("crash", at="%s:%d" % (os.path.basename(_fr.filename), _fr.lineno))
            _core.current = None
            traceback.print_exc()
            bad("انهار الحارسُ بعد %d عطبٍ مجموع — الانهيارُ أعلاه" % len(fails))
        report()
        return 1
    finally:
        _core.write_trace()


if __name__ == "__main__":
    sys.exit(_run())
