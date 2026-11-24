#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""أيُّ المانيفستين يبقى على الخادم عند نشر الموقع: المخبوزُ أم الحيّ؟ [MAN-01]

البناءُ يخبز `dl/releases.json` احتياطًا، و`publish_release.sh` يرفع على الخادم إصدارًا
أحدثَ بين مزامنتين. فالنشرُ يسأل هذه الوحدة ولا يقرّر بنفسه — وكانت المقارنةُ سطورَ بايثون
داخل `deploy_site.sh` بلا اختبار، فقِيس فيها: مرشَّحٌ (‏`1.2.0-rc1`) يحلّ محلَّ النهائيّ،
و`v1.122.0` الحيّ يخسر أمام أيّ مخبوز، والتساوي يمحو أصلًا رُفع بعد آخر مزامنة.

القواعد:
  - الإصدارُ أرقامٌ بنقاط، ببادئة `v` اختياريّة ولاحقةٍ اختياريّة بعد `-`؛ وغيرُ ذلك
    **خطأٌ بصوت** (خروج 2) لا صفرٌ صامت. والأقصرُ يُحشى بأصفار، و`05803` = `5803`.
  - ما حمل لاحقةً أقدمُ من مثيله بلا لاحقة: لا يحلّ مرشَّحٌ محلَّ نهائيّ.
  - الحيُّ الغائبُ أو التالفُ يأخذ المخبوز (مرآةٌ جديدة، أو إصلاحُ ملفٍّ معطوب).
  - **وعند تساوي الإصدار** يبقى الحيُّ إن كان فيه أصلٌ (‏`id`+`file`+`sha256`) ليس في
    المخبوز — رُفع بعد آخر مزامنة — وإلّا فالمخبوزُ (يحمل أصلًا مصحَّحًا لا ينقص شيئًا).

    printf '%s' "$live_json" | python build/lib/manifest_pick.py site/public/dl/releases.json
    ⇒ يطبع `baked` أو `live`، وسببَه على stderr.
"""
import json
import re
import sys

_V = re.compile(r"^v?(\d+(?:\.\d+)*)(?:-([0-9A-Za-z][0-9A-Za-z.-]*))?$")


def parse_version(v):
    # غيرُ النصّ (رقمٌ مجرَّد، قائمة) خطأٌ بصوتٍ كغير المفهوم، لا `AttributeError` يمرّ بلا سبب
    m = _V.match(v.strip()) if isinstance(v, str) else None
    if not m:
        raise ValueError("إصدارٌ غيرُ مفهوم: %r" % (v,))
    return [int(p) for p in m.group(1).split(".")], m.group(2)


def compare(a, b):
    """‏-1 / 0 / 1 كمقارنة a بـb."""
    (na, pa), (nb, pb) = parse_version(a), parse_version(b)
    n = max(len(na), len(nb))
    na, nb = na + [0] * (n - len(na)), nb + [0] * (n - len(nb))
    if na != nb:
        return -1 if na < nb else 1
    if (pa is None) != (pb is None):
        return 1 if pa is None else -1          # النهائيُّ أحدثُ من مرشَّحه
    if pa == pb:
        return 0
    return _cmp_pre(pa, pb)


def _cmp_pre(pa, pb):
    """اللاحقتان قطعةً قطعة، والقطعةُ الرقميّةُ عددٌ لا نصّ (‏`rc10` أحدثُ من ‏`rc2`).

    المقارنةُ النصّيّةُ المجرَّدة كانت تجعل ‏`rc10` أقدمَ من ‏`rc2` فيُترَك الحيُّ الأقدم.
    """
    def key(p):
        return [(0, int(t), "") if t.isdigit() else (1, 0, t)
                for t in re.findall(r"\d+|[^\d.]+", p)]
    ka, kb = key(pa), key(pb)
    return 0 if ka == kb else (-1 if ka < kb else 1)


def _assets(doc):
    return {(a.get("id"), a.get("file"), a.get("sha256"))
            for a in (doc.get("assets") or []) if isinstance(a, dict)}


def pick(baked, live):
    """(القرار، السبب). `baked` قاموس؛ `live` قاموسٌ أو None (غائبٌ أو تالف)."""
    bv = baked.get("version", "")
    parse_version(bv)
    if not live or not live.get("version"):
        return "baked", "لا مانيفستَ حيًّا صالحًا"
    lv = live["version"]
    c = compare(bv, lv)
    if c > 0:
        return "baked", "المخبوزُ (%s) أحدثُ من الحيّ (%s)" % (bv, lv)
    if c < 0:
        return "live", "الحيُّ (%s) أحدثُ من المخبوز (%s)" % (lv, bv)
    extra = _assets(live) - _assets(baked)
    if extra:
        return "live", "الإصدارُ واحد (%s) وفي الحيّ %d أصلًا ليس في المخبوز: %s" % (
            lv, len(extra), ", ".join(sorted(str(e[1]) for e in extra)))
    return "baked", "الإصدارُ واحد (%s) ولا ينقص المخبوزَ أصلٌ من الحيّ" % bv


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("الاستعمال: manifest_pick.py <المخبوز.json>  (والحيُّ على stdin)\n")
        return 2
    with open(argv[1], encoding="utf-8") as f:
        baked = json.load(f)
    raw = sys.stdin.read()
    try:
        live = json.loads(raw) if raw.strip() else None
        if not isinstance(live, dict):
            live = None
    except ValueError:
        live = None
    try:
        choice, why = pick(baked, live)
    except ValueError as e:
        sys.stderr.write("❌ %s\n" % e)
        return 2
    sys.stderr.write("%s\n" % why)
    print(choice)
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    sys.exit(main(sys.argv))
