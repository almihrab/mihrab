#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مولِّد أيقونة محراب (.ico + PNG معاينة) من هندسة الشعار «القوس الخالص».
يرسم نفس مسار الـSVG (assets/branding/mihrab-mark-*.svg) بإحداثيّات مطابقة،
فيبقى مصدرًا واحدًا للحقيقة الهندسيّة. أعِد التشغيل عند تغيير الشعار.
    py -3 assets/branding/gen_ico.py
"""
import math
import sys
from pathlib import Path
try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.stderr.write(
        "gen_ico.py يحتاج Pillow (pip install Pillow). الأصول المولَّدة ملتزَمة في المستودع؛\n"
        "لا يلزم تشغيل هذا إلّا عند تغيير هندسة الشعار.\n"
    )
    raise SystemExit(2)

# فرض UTF-8 على المخرجات (كونسول ويندوز قد يكون cp125x فيفشل مع ✓/العربيّة ⇒ توليد
# جزئيّ صامت — البلاطات تُحفَظ بعد أوّل print). نفس كتلة بقيّة مرقِّعات المشروع.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# ── مصدر الحقيقة الهندسيّ: نسخ حرفيّ لبيانات مسار mihrab-mark-*.svg (فضاء 100×128) ──
# كلّ قوس = قطعتا قوس SVG «A r r 0 0 1» بنفس نقاط النهاية ونصف القطر والقمّة ⇒ الأيقونة
# تطابق الشعار المتّجه بكسلًا (مصدر حقيقة واحد، لا مقاربة متساوية الأضلاع).
PAD_X = 14                      # حشو أفقيّ يجعل اللوحة مربّعة 128×128
SS = 8                          # عامل التنعيم الفائق (supersampling)
OUTER = dict(xl=22, xr=78, ys=58, yb=116, apex=(50, 8), r=56, w=6.5)
INNER = dict(xl=35, xr=65, ys=74, yb=116, apex=(50, 50), r=28, w=4.0)
CURSOR = dict(x=47, y=82, w=6, h=30, r=3)
SIZES = [16, 24, 32, 48, 64, 128, 256]

# ألوان النسختين (فاتحة/داكنة) — تطابق SVG
THEMES = {
    "color": dict(stroke=(0x12, 0x7C, 0x6E), inner_a=0.38, cursor=(0xC7, 0x9A, 0x3E)),
    "dark":  dict(stroke=(0x31, 0xA7, 0x96), inner_a=0.42, cursor=(0xE3, 0xBE, 0x68)),
}


def _svg_arc(p1, p2, r, steps=48, fa=0, fs=1):
    """عيّنات قوسٍ دائريّ بدلالة نقطتَي النهاية ونصف القطر — دلالة SVG «A r r 0 fa fs»
    (تحويل endpoint→center حسب مواصفة W3C). يطابق ما يرسمه المتصفّح للـSVG تمامًا."""
    x1, y1 = p1
    x2, y2 = p2
    rx = ry = float(r)
    x1p, y1p = (x1 - x2) / 2.0, (y1 - y2) / 2.0               # منتصف نسبيّ (لا دوران)
    lam = x1p * x1p / (rx * rx) + y1p * y1p / (ry * ry)       # كبّر نصف القطر إن صغُر
    if lam > 1:
        rx *= math.sqrt(lam)
        ry *= math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    coef = math.sqrt(max(0.0, num / den))
    if fa == fs:
        coef = -coef
    cxp, cyp = coef * rx * y1p / ry, -coef * ry * x1p / rx
    cx, cy = cxp + (x1 + x2) / 2.0, cyp + (y1 + y2) / 2.0     # المركز المطلق

    def _ang(ux, uy, vx, vy):
        d = (ux * vx + uy * vy) / (math.hypot(ux, uy) * math.hypot(vx, vy))
        a = math.acos(max(-1.0, min(1.0, d)))
        return -a if (ux * vy - uy * vx) < 0 else a

    ux, uy = (x1p - cxp) / rx, (y1p - cyp) / ry
    vx, vy = (-x1p - cxp) / rx, (-y1p - cyp) / ry
    t1 = _ang(1, 0, ux, uy)
    dt = _ang(ux, uy, vx, vy)
    if not fs and dt > 0:
        dt -= 2 * math.pi
    elif fs and dt < 0:
        dt += 2 * math.pi
    return [(cx + rx * math.cos(t1 + dt * i / steps),
             cy + ry * math.sin(t1 + dt * i / steps)) for i in range(steps + 1)]


def _arch_points(arch):
    """نقاط قوس مدبَّب = فكّ أيسر + قوسا SVG (رِكز→قمّة، قمّة→رِكز) + فكّ أيمن، فضاء المصدر."""
    xl, xr, ys, yb, apex, r = (arch["xl"], arch["xr"], arch["ys"],
                               arch["yb"], arch["apex"], arch["r"])
    pts = [(xl, yb), (xl, ys)]                                # الفكّ الأيسر صعودًا
    pts += _svg_arc((xl, ys), apex, r)                        # القوس الأيسر ← قمّة
    pts += _svg_arc(apex, (xr, ys), r)                        # قمّة → القوس الأيمن
    pts += [(xr, ys), (xr, yb)]                               # الفكّ الأيمن نزولًا
    return pts


def _tx(p):
    return ((p[0] + PAD_X) * SS, p[1] * SS)


def _stroke(draw, arch, rgba):
    pts = [_tx(p) for p in _arch_points(arch)]
    w = int(round(arch["w"] * SS))                # سُمك الخطّ من الأصل (لا وسيط منفصل)
    draw.line(pts, fill=rgba, width=w, joint="curve")
    rad = w / 2.0                                # أطراف مستديرة (linecap=round)
    for e in (pts[0], pts[-1]):
        draw.ellipse([e[0] - rad, e[1] - rad, e[0] + rad, e[1] + rad], fill=rgba)


def _render(theme):
    t = THEMES[theme]
    W = 128 * SS
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    _stroke(d, OUTER, (*t["stroke"], 255))
    inner = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    _stroke(ImageDraw.Draw(inner), INNER, (*t["stroke"], int(255 * t["inner_a"])))
    img.alpha_composite(inner)
    c = CURSOR
    x0, y0 = _tx((c["x"], c["y"]))
    x1, y1 = _tx((c["x"] + c["w"], c["y"] + c["h"]))
    d.rounded_rectangle([x0, y0, x1, y1], radius=c["r"] * SS, fill=(*t["cursor"], 255))
    return img


# ── أيقونتا PWA لمحرابِ المتصفّح ──
# غيرُ شفّافتين عمدًا: «تثبيتُ التطبيق» يضع الأيقونةَ على خلفيّةِ نظامٍ مجهولةِ اللون،
# والقوسُ المفرَّغ يختفي على داكن. والأرضيّةُ هي أرضيّةُ شاشة الإقلاع نفسُها (`#0d1f1c`)
# فلا تُرى قفزةُ لونٍ بين الأيقونة وأوّلِ إطار.
# والعلامةُ عند 60% من الضلع: منطقةُ الأمان القناعيّة (maskable) تقتطع حتّى 20% من كلّ
# حافّة، فما دون ذلك يُقصّ طرفا القوس على أندرويد.
PWA_SIZES = [192, 512]
PWA_GROUND = (0x0D, 0x1F, 0x1C, 255)
PWA_MARK_FRACTION = 0.60


def _pwa(master, px):
    """العلامةُ الداكنةُ مركزيّةً على أرضيّةِ محرابٍ الصلبة، بمقاسِ أيقونةِ PWA."""
    canvas = Image.new("RGBA", (px, px), PWA_GROUND)
    side = int(round(px * PWA_MARK_FRACTION))
    mark = master.resize((side, side), Image.LANCZOS)
    off = (px - side) // 2
    canvas.alpha_composite(mark, (off, off))
    return canvas


def main():
    out = Path(__file__).parent
    for theme in THEMES:
        master = _render(theme)
        if theme == "color":
            base = master.resize((max(SIZES), max(SIZES)), Image.LANCZOS)  # الأساس أكبر مقاس
            ico = out / "mihrab.ico"
            base.save(ico, format="ICO", sizes=[(s, s) for s in SIZES])   # Pillow يُصغّر لكلّ مقاس
            print(f"✓ {ico.name}  ({', '.join(f'{s}px' for s in SIZES)})")
        master.resize((256, 256), Image.LANCZOS).save(out / f"mihrab-mark-{theme}-256.png")
        print(f"✓ mihrab-mark-{theme}-256.png")
        if theme == "color":                                # بلاطات ويندوز (code_*.png)
            for px in (150, 70):
                master.resize((px, px), Image.LANCZOS).save(out / f"mihrab_{px}x{px}.png")
                print(f"✓ mihrab_{px}x{px}.png")
        if theme == "dark":                                 # أيقونتا PWA لمحرابِ المتصفّح
            for px in PWA_SIZES:
                _pwa(master, px).save(out / f"mihrab-pwa-{px}.png")
                print(f"✓ mihrab-pwa-{px}.png")


if __name__ == "__main__":
    main()
