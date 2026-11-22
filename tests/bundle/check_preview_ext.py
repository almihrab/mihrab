#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L2 — بوّابةُ مخرَجٍ لإضافاتِ بناءِ المعاينة: ما جُهِّز وصل الحزمةَ **صالحًا**.

كلُّ ما يُحقَن في محراب له بوّابةُ مخرَج — الهويّة، والرُقَع — وإضافةُ
المعاينةِ كانت وحدَها بلا واحدة. والسطرُ الذي يُطمئن في السجلّ («إضافةُ معاينةٍ
مُجهَّزة») هو سجلُّ **التجهيز** في build.sh، لا سجلُّ الوصول: أيُّ عطبٍ بعده — في
حلقةِ الحقن، أو في جمعِ gulp، أو في شجرةِ منبعٍ مرقَّعةٍ سلفًا لا يُعاد ترقيعُها —
يُنتج حزمةً تحمل اسمَ «‑alif» وليس فيها ألف، وسيرًا أخضرَ يكتشفه المُجرِّب لا نحن.

    MIHRAB_EXTRA_EXT_DIRS=... python tests/bundle/check_preview_ext.py <جذرُ المخرَج>

المدخلُ هو **نفسُه** الذي أعطيناه للبناء: بوّابةٌ تفحص ما تشتهي بدل ما طُلب لا تحرس.
"""
import glob
import json
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def app_extensions_dir(dist):
    """‏extensions/ داخل الحزمة. macOS يلفّ كلَّ شيء في *.app، وما عداه مسطّح."""
    direct = os.path.join(dist, "resources", "app", "extensions")
    if os.path.isdir(direct):
        return direct
    for app in sorted(glob.glob(os.path.join(dist, "*.app"))):
        d = os.path.join(app, "Contents", "Resources", "app", "extensions")
        if os.path.isdir(d):
            return d
    return None


def referenced_paths(pkg):
    """الملفّاتُ التي يَعِد بها package.json. وجودُ المجلّدِ لا يعني وصولَ محتواه:
    نسخٌ ناقصٌ يترك package.json وحدَه، والإضافةُ تُحمَّل ثمّ تنهار عند أوّل استعمال."""
    out = []
    for key in ("main", "browser"):
        if pkg.get(key):
            out.append(pkg[key])
    contrib = pkg.get("contributes") or {}
    for key in ("grammars", "snippets", "themes", "iconThemes", "productIconThemes"):
        for item in contrib.get(key) or []:
            if isinstance(item, dict) and item.get("path"):
                out.append(item["path"])
    for lang in contrib.get("languages") or []:
        if isinstance(lang, dict) and lang.get("configuration"):
            out.append(lang["configuration"])
    return out


BINARIES = ("alif.exe", "alif")


def staged_binary(src):
    """‏(اسمٌ، حجمٌ) لمفسّرٍ مشحونٍ في `bin/` بالمصدر، أو None إن لم يُشحن.

    التوقّعُ يُشتقّ من المُجهَّز لا يُفترَض: إضافةٌ بلا مفسّرٍ مشحونٍ حالةٌ مشروعة،
    وما يُشحن فيجب أن يصل. ولو ثبّتنا الاسمَ لصار كلُّ إضافةٍ أخرى ساقطةً."""
    for name in BINARIES:
        candidate = os.path.join(src, "bin", name)
        if os.path.isfile(candidate):
            return name, os.path.getsize(candidate)
    return None


def verify(dist, staged_dirs):
    """يعيد (رمزَ الخروج، أسطرَ التقرير). منطقٌ واحدٌ يستدعيه CI والمطوّر."""
    lines = []
    if not staged_dirs:
        return 1, ["❌ البوّابةُ استُدعيت بلا MIHRAB_EXTRA_EXT_DIRS — "
                   "لا شيءَ لتفحصه، وصمتُها هنا هو العطبُ الذي جاءت لتمنعه."]
    ext_root = app_extensions_dir(dist)
    if ext_root is None:
        return 1, ["❌ لا extensions/ في الحزمة: %s" % dist]

    failed = 0
    for src in staged_dirs:
        name = os.path.basename(src.rstrip("/\\"))
        dst = os.path.join(ext_root, name)
        if not os.path.isdir(dst):
            failed += 1
            lines.append("❌ %s: مُجهَّزةٌ ولم تصل الحزمة (%s)" % (name, dst))
            continue
        dst_pkg = os.path.join(dst, "package.json")
        if not os.path.isfile(dst_pkg):
            failed += 1
            lines.append("❌ %s: وصلت بلا package.json — ماسحُ الإضافاتِ يتجاهلها" % name)
            continue
        with open(dst_pkg, encoding="utf-8") as f:
            got = json.load(f)
        src_pkg = os.path.join(src, "package.json")
        if os.path.isfile(src_pkg):
            with open(src_pkg, encoding="utf-8") as f:
                want = json.load(f)
            for key in ("name", "version", "publisher"):
                if want.get(key) != got.get(key):
                    failed += 1
                    lines.append("❌ %s: %s في الحزمة %r ≠ المُجهَّز %r"
                                 % (name, key, got.get(key), want.get(key)))
        missing = [p for p in referenced_paths(got)
                   if not os.path.isfile(os.path.join(dst, p.lstrip("./")))]
        if missing:
            failed += 1
            lines.append("❌ %s: ملفّاتٌ يَعِد بها package.json ولم تصل: %s"
                         % (name, "، ".join(missing)))
        # المفسّرُ المشحون: لا يذكره package.json فلا يراه فحصُ
        # referenced_paths — وهو فرقُ «أفتح ملفَ ألف فيعمل» و«أفتحه فيُلوَّن».
        expected_bin = staged_binary(src)
        if expected_bin:
            bin_name, bin_size = expected_bin
            arrived = os.path.join(dst, "bin", bin_name)
            if not os.path.isfile(arrived):
                failed += 1
                lines.append("❌ %s: مفسّرٌ مُجهَّزٌ ولم يصل الحزمة (bin/%s)" % (name, bin_name))
            elif os.path.getsize(arrived) != bin_size:
                failed += 1
                lines.append("❌ %s: المفسّرُ وصل مبتورًا: %d بايت ≠ %d المُجهَّز"
                             % (name, os.path.getsize(arrived), bin_size))
            elif os.name != "nt" and not os.access(arrived, os.X_OK):
                # حزمُ gulp والنسخُ قد تُسقِط بتَّ التنفيذ، فيصل ملفٌّ موجودٌ لا يعمل.
                failed += 1
                lines.append("❌ %s: المفسّرُ وصل بلا بتِّ تنفيذ: bin/%s" % (name, bin_name))
        if not failed:
            detail = " ومعها المفسّر" if expected_bin else ""
            lines.append("✅ %s %s وصلت الحزمة كاملةً%s" % (name, got.get("version", ""), detail))
    return (1 if failed else 0), lines


def main():
    if len(sys.argv) < 2:
        print("الاستعمال: python tests/bundle/check_preview_ext.py <جذرُ المخرَج>")
        return 2
    staged = [d.strip() for d in os.environ.get("MIHRAB_EXTRA_EXT_DIRS", "").splitlines()
              if d.strip()]
    code, lines = verify(sys.argv[1], staged)
    print("─── بوّابةُ إضافاتِ المعاينة ───")
    for ln in lines:
        print("  " + ln)
    return code


if __name__ == "__main__":
    sys.exit(main())
