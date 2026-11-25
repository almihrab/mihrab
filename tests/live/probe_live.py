#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مجسُّ الحيّ [LIVE-01] — يسأل الخادمَ لا الشجرة.

عشرُ جولاتٍ من الحرّاس قاست الشجرةَ، وأربعةٌ من أعطاب الجولة العاشرة كانت على سطوحٍ
لا يقيسها أيُّ حارس: الخادمُ الحيّ (الخطوطُ ‎404‎، صفحةُ ‎404‎ nginx العارية)، والشهادةُ
(تنتهي ‎2026-12-19‎ ومجسُّ التجديد يسأل عن نطاقٍ آخر)، وCI الحيّ (أحمرُ ثلاثَ عشرةَ
دفعة). قياسُ المحلّل: ‎85%‎ من الوقائع وجدها وكيلٌ يقيس بيده لا حارس. وهذا المجسُّ هو
الصنفُ الوحيد الذي يستحيل فيه التطابقُ الذاتيّ: شاهدُه الشبكةُ لا الشجرة.

يحتاج شبكةً فلا يدخل `quick`؛ موطنُه الوظيفةُ المجدوَلةُ في `docs-pages.yml` وتشغيلٌ
محلّيٌّ صريح. خمسةُ أسئلة:
  ١) الشهادةُ تبقى ≥ ‎30‎ يومًا.
  ٢) `fonts.css` الحيّ = المبنيّ (أو، بلا مخرَجٍ محلّيّ، يعلن الأوجهَ التي تعد بها الشجرة).
  ٣) مسارٌ لا وجودَ له يردّ ‎404‎ **بصفحتنا** لا بصفحة nginx العارية — على الأصلين.
  ٤) كلُّ ملفٍّ في المانيفست الحيّ يُخدَم (‏200/206 على HEAD).
  ٥) آخرُ تشغيلٍ لمصفوفة البناء على `main` ناجح (إن وُجد `gh`؛ وإلّا يُعلَن التخطّي).
"""
import datetime as _dt
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITE = os.path.join(ROOT, "site")
with open(os.path.join(SITE, "data", "site.json"), encoding="utf-8") as _f:
    _site = json.load(_f)
ORIGIN = _site["canonical"].rstrip("/")
HOST = ORIGIN.split("//", 1)[-1]
APP = "https://app." + HOST
UA = "mihrab-live-probe/1 (+https://github.com/almihrab/mihrab)"
TIMEOUT = 20
fails, notes = [], []


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """لا يتبع التحويل: ‎301/302‎ تُرفَع `HTTPError` برمزها وترويساتها فتُلتقَط في `get`."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_NOFOLLOW = urllib.request.build_opener(_NoRedirect)


def get(url, method="GET", follow=True):
    # ‏`follow=False` لمن يسأل عن التحويل نفسِه: `urlopen` يتبع ‎301‎ افتراضيًّا فيرى ‎200‎
    # الوجهةِ بدل التحويل — قِيس بخادمٍ محلّيٍّ يردّ ‎301‎ — فيعمى عن `Location`.
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
    _open = urllib.request.urlopen if follow else _NOFOLLOW.open
    try:
        with _open(req, timeout=TIMEOUT) as r:
            return r.status, dict(r.headers), (r.read() if method == "GET" else b"")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), (e.read() if method == "GET" else b"")


def check(cond, msg):
    (notes if cond else fails).append(("✅ " if cond else "❌ ") + msg)


# ── ١) الشهادة ──
try:
    ctx = ssl.create_default_context()
    with socket.create_connection((HOST, 443), timeout=TIMEOUT) as sock:
        with ctx.wrap_socket(sock, server_hostname=HOST) as ss:
            cert = ss.getpeercert()
    exp = _dt.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=_dt.timezone.utc)
    days = (exp - _dt.datetime.now(_dt.timezone.utc)).days
    check(days >= 30, "شهادةُ %s تنتهي بعد %d يومًا (%s) — التجديدُ يُفحَص على الخادم [LIVE-01]"
          % (HOST, days, exp.date()))
except (OSError, ssl.SSLError, KeyError, ValueError) as e:
    fails.append("❌ تعذّر قراءةُ شهادة %s: %s [LIVE-01]" % (HOST, e))

# ── ٢) fonts.css الحيّ مقابل الشجرة ──
st, hd, body = get(ORIGIN + "/assets/fonts.css")
live_css = body.decode("utf-8", "replace")
faces_live = re.findall(r'url\("fonts/([^"]+)"\)', live_css)
with open(os.path.join(SITE, "sitegen", "fonts.py"), encoding="utf-8") as _b:
    _bpy = _b.read()
_i = _bpy.index("FONT_FACES = [")
wanted = sorted(set(re.findall(r'\("([^"]+\.woff2)"', _bpy[_i:_bpy.index("]", _i)])))
check(st == 200, "‏/assets/fonts.css الحيّ يردّ %d [LIVE-01]" % st)
missing = [w for w in wanted if w not in faces_live]
check(not missing, "الأوجهُ التي تَعِد بها الشجرة (%d) مُعلَنةٌ حيًّا — ينقص: %s [LIVE-01]"
      % (len(wanted), "، ".join(missing) or "لا شيء"))
for fn in wanted:
    s2, _h, _ = get(ORIGIN + "/assets/fonts/" + fn, "HEAD")
    check(s2 == 200, "‏%s حيًّا ⇒ %d [LIVE-01]" % (fn, s2))
s3, h3, _ = get(ORIGIN + "/assets/fonts/" + wanted[0], "HEAD") if wanted else (0, {}, b"")
if wanted:
    check(h3.get("Access-Control-Allow-Origin") in ("*", APP),
          "ترويسةُ CORS على الخطوط حيًّا = %r (تحتاجها صفحةُ 404 من %s) [LIVE-01]"
          % (h3.get("Access-Control-Allow-Origin"), APP))

# ── ٣) صفحةُ 404 صفحتُنا على الأصلين ──
for base in (ORIGIN, APP):
    s4, h4, b4 = get(base + "/mihrab-live-probe-no-such-page-%d/" % int(_dt.datetime.now().timestamp()))
    txt = b4.decode("utf-8", "replace")
    ours = "محراب" in txt and "<center>nginx</center>" not in txt
    check(s4 == 404, "‏%s: مسارٌ مفقودٌ يردّ %d [LIVE-01]" % (base, s4))
    check(ours, "‏%s: صفحةُ 404 صفحتُنا لا nginx العارية [LIVE-01]" % base)

# ── ٣ج) النطاقاتُ الفرعيّة تصل وجهتَها [SUB-01] ──
# `dl.mihrab.dev/dl/releases.json` كان يُحوَّل إلى `/dl/dl/…` و`docs.mihrab.dev/start/`
# إلى `/docs/start/` — ‎404‎ كلاهما بعد ‎301‎ (قياسُ سالي). يُتبَع التحويلُ هنا عمدًا
# ويُشترَط ‎200‎ في الوجهة.
for _u in ("https://dl.mihrab.dev/dl/releases.json", "https://dl.mihrab.dev/",
           "https://docs.mihrab.dev/", "https://docs.mihrab.dev/start/"):
    try:
        s8, _h8, _ = get(_u, "HEAD", follow=True)
    except OSError as e:
        fails.append("❌ %s: %s [SUB-01]" % (_u, e))
        continue
    check(s8 == 200, "‏%s ⇒ %d بعد اتّباع التحويل [SUB-01]" % (_u, s8))

# ── ٤) المانيفستُ الحيّ يُخدَم ──
s5, _h5, b5 = get(ORIGIN + "/dl/releases.json")
check(s5 == 200, "‏/dl/releases.json حيًّا ⇒ %d [LIVE-01]" % s5)
if s5 == 200:
    try:
        man = json.loads(b5.decode("utf-8"))
        base = (man.get("base") or "dl/").strip("/")
        for a in man.get("assets", []):
            if not a.get("file"):
                continue
            s6, _h6, _ = get("%s/%s/%s" % (ORIGIN, base, a["file"]), "HEAD")
            check(s6 in (200, 206), "‏%s ⇒ %d [LIVE-01]" % (a["file"], s6))
    except ValueError as e:
        fails.append("❌ المانيفستُ الحيّ ليس JSON: %s [LIVE-01]" % e)

# ── ٥) آخرُ مصفوفةِ بناءٍ على main ──
try:
    r = subprocess.run(["gh", "run", "list", "--workflow", "build-matrix.yml", "--branch", "main",
                        "--limit", "1", "--json", "conclusion,headSha,createdAt"],
                       capture_output=True, timeout=60, cwd=ROOT)
    if r.returncode == 0 and r.stdout.strip():
        run = json.loads(r.stdout)[0]
        check(run.get("conclusion") == "success",
              "آخرُ مصفوفةِ بناءٍ على main: %s (%s، %s) [LIVE-01]"
              % (run.get("conclusion"), run.get("headSha", "")[:7], run.get("createdAt", "")[:10]))
    else:
        notes.append("⏭️  gh غيرُ متاح أو بلا صلاحيّة — سؤالُ CI متخطًّى مُعلَنًا [LIVE-01]")
except (OSError, subprocess.SubprocessError, ValueError, IndexError):
    notes.append("⏭️  gh غيرُ متاح — سؤالُ CI متخطًّى مُعلَنًا [LIVE-01]")

for n in notes:
    print("  " + n)
for f in fails:
    print("  " + f)
print("─── الحيّ: %d ✅ · %d ❌ ───" % (len(notes), len(fails)))
sys.exit(1 if fails else 0)
