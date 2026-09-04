# نشرُ محرابِ الويب — `mihrab.dev`

> **حالةُ هذا المجلّد:** ملفّاتُه **لم تُطبَّق على الخادم بعد**. كُتِبت من قياسٍ محلّيّ،
> ثمّ روجِعت هندسيًّا فوُجد فيها ثلاثةُ أعطابٍ كانت تُسقِط `sad-lang.org` لحظةَ التطبيق
> — صُحِّحت. ما قِيس مذكورٌ بوصفه قياسًا، وما لم يُقَس مذكورٌ بوصفه غيرَ مؤكَّد.

## الحالةُ المقيسة (2026-09-05) — من الخادم نفسِه

```
mihrab.dev · www · docs · dl · *.webview  →  176.106.227.73  ✅ منتشرة
CAA: 0 issue "letsencrypt.org" · 0 issuewild "letsencrypt.org"  ✅

nginx 1.24.0 (Ubuntu) · ستّةُ مواقعَ قائمة:
   kadah · sad-academy · sad-lang · sad-registry · sad-website · sila-hub
إدراجُ nginx.conf:  conf.d/*.conf  ثمّ  sites-enabled/*
لا `default_server` على 443 في أيٍّ منها     ⇒ الأوّلُ أبجديًّا يملك الافتراضيّ
`kadah` يضع listen 443 ssl http2            ⇒ HTTP/2 مفعَّلٌ سلفًا على المقبس
certbot: authenticator = nginx (لا webroot)
14006 مشغولٌ بـ«Node Dashboard» · 14007 حُرّ  ⇒ نستعمل 14007
لا add_header في http{} — كلُّها داخل كتل المواقع ⇒ لا تعارضَ وراثة
```

و`https://mihrab.dev` يقدّم اليومَ الشهادةَ الموقَّعةَ ذاتيًّا `CN=192.168.33.20`
(الكتلةُ الافتراضيّة). **لا تفتحه في متصفّح**: `.dev` في قائمة HSTS المحمَّلة ⇒ رفضٌ
قاطعٌ بلا زرِّ تجاوز، وبعضُ المتصفّحات تُبقي أثرَ الفشل فيبدو عطبًا دائمًا بعد
إصلاح الشهادة. استعمل `http://` أثناء الإعداد.

### ⚠️ أخطرُ ما كشفه القياس: موضعُ الملفّات

`conf.d/` تُحمَّل **قبل** `sites-enabled/`، ولا كتلةَ `default_server` على 443. فأوّلُ
كتلةٍ بترتيب التحليل تصير الخادمَ الافتراضيَّ لكلّ Host مجهول. ووضعُ كتلِ محرابٍ في
`conf.d/` يجعلها تسبق المواقعَ الستّةَ **فيصير محرابٌ الافتراضيّ**: كلُّ طلبٍ بترويسة
Host غيرِ معروفةٍ يُمرَّر إلى محرِّرٍ يفتح طرفيّةً على الخادم.

| يُوضَع في | ماذا |
|---|---|
| `conf.d/00-mihrab-shared.conf` | الخريطةُ والمجمَّعُ والحدود — **يجب** أن تسبق |
| `sites-enabled/mihrab-acme` | كتلةُ 80 |
| `sites-enabled/mihrab` | كتلُ 443 — و«mihrab» تلي «kadah» أبجديًّا فالترتيبُ سليم |
| `sites-enabled/mihrab-webview` | المرحلة ٤ |

## الملفّات — ولماذا هي منفصلة

الفصلُ ليس تنظيمًا: **ملفٌّ واحدٌ يعني عطبًا واحدًا يُسقِط كلَّ المواقع.** ‏nginx
يقرأ الشهادةَ عند التحميل ويرفض الإقلاعَ على أيّ خطأ.

| الملفّ | المرحلة |
|---|---|
| [`preflight.sh`](preflight.sh) | **٠** — قياساتٌ تسبق كلَّ شيء |
| [`nginx/00-default-tls.conf.example`](nginx/00-default-tls.conf.example) | ٠ — فقط إن أثبت الفحصُ غيابَ `default_server` |
| [`nginx/00-mihrab-shared.conf`](nginx/00-mihrab-shared.conf) | ١ — الخريطةُ والمجمَّعُ والحدود |
| [`nginx/01-mihrab-acme.conf`](nginx/01-mihrab-acme.conf) | ١ — المنفذ 80 وتحدّي ACME |
| [`nginx/mihrab.dev.conf`](nginx/mihrab.dev.conf) | ٣ — بعد صدور الشهادة |
| [`nginx/webview.mihrab.dev.conf`](nginx/webview.mihrab.dev.conf) | ٤ — بعد wildcard بـDNS-01 |
| [`systemd/mihrab-web.service`](systemd/mihrab-web.service) | ٢ |

## بناءُ لينكس — مقيسٌ ناجح

بُني في WSL Ubuntu 24.04 وأُنتِج `vscode-reh-web-linux-x64` (‏370 م.ب). وقِيس:

```
nameLong = محراب · defaultLocale = ar · version = 1.126.05953
nls.messages.json  20519/21922 (93%)
nls.messages.js    20519/21922 (93%)   ← ما يصل المتصفّح
[dir=rtl] 130 · الخطُّ موصولٌ بملفّ · xterm مُرقَّع · حارسُ [WEB-01] أخضر
```

وأُقلِع الخادمُ وقِيس في متصفّحٍ حقيقيّ: `dir=rtl`، شريطُ النشاط يمينًا، 665 محرفًا
عربيًّا من 1089 مرئيّة، ولوحُ الترحيب يعمل ومنتقي المجلّدات يقرأ نظامَ ملفّات لينكس.

**ولم يلزم تعديلُ سطرٍ لأجل لينكس**: خطوةُ التعريب (ط-0د) وحارسُ `[WEB-01]` يلتقطان
`vscode-reh-web-*` أيًّا كان هدفُها — وهذا ما كان يُرجى من التعميم لا من التخصيص.

### تبعيّاتُ البيئة (خارجَ ما يجلبه `build.sh` بنفسه)

```bash
apt-get install -y build-essential pkg-config \
  libx11-dev libxkbfile-dev libsecret-1-dev libkrb5-dev libnss3 libgbm1 xz-utils
curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal   # ‏CLI مكتوبٌ بـRust
```

⚠️ و**لا تبنِ على `/mnt/c`**: طبقةُ 9p أبطأُ بمراتب، والروابطُ الصلبة لا تعبر إليها
(`git clone --local` يفشل بـ«Invalid cross-device link»). استنسخ إلى نظام ملفّات لينكس.

وثلاثُ تبعيّاتٍ كانت **مبثوثةً لا معلَنة**، كشفتها أربعُ محاولات: `python` في
`build.sh` عندنا، و`python` في الشيفرة المحقونة، و`rustup`. الأوّلان أُصلِحا في
المستودع فلا يتكرّران؛ والثالثُ تبعيّةُ بيئةٍ مذكورةٌ أعلاه.

## ما ينقص المحتوى

⚠️ **وأدواتُ ص ويندوزيّةٌ فقط** (`sad-run.exe` · `sad-lsp.exe` · `sad-build.exe`).
فبناءُ لينكس يسقط سقوطًا رشيقًا، والحصيلةُ **محرِّرٌ عربيٌّ معكوسُ الاتّجاه يعمل، لكنّه
لا يُصرِّف ص ولا يُشغِّلها ولا خادمَ لغةٍ فيه**. إطلاقٌ عامٌّ يحتاج بناءَ سلسلة ص
للينكس — مسارٌ مستقلّ.

## الترتيب — ملزِم

```bash
# ٠ · قِس، ثمّ احتفظ بنسخة
sudo bash preflight.sh
tar czf ~/nginx-$(date +%F).tgz /etc/nginx

# ١ · المشتركاتُ وكتلةُ 80 وحدَها ⇒ ثمّ الشهادة
sudo cp nginx/00-mihrab-shared.conf /etc/nginx/conf.d/
sudo cp nginx/01-mihrab-acme.conf   /etc/nginx/sites-available/mihrab-acme
sudo ln -sf /etc/nginx/sites-available/mihrab-acme /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot certonly --nginx -d mihrab.dev -d www.mihrab.dev   # مُصادِقُ nginx — مقيس
sudo certbot certificates          # ⚠️ اقرأ اسمَ السلالة، لا تفترضه

# ٢ · الخدمة (بعد نسخ بناء لينكس إلى /opt/mihrab/web)
sudo cp systemd/mihrab-web.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now mihrab-web

# ٣ · كتلُ 443
sudo cp nginx/mihrab.dev.conf /etc/nginx/sites-available/mihrab
sudo ln -sf /etc/nginx/sites-available/mihrab /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# ٤ · wildcard ثمّ الـwebview (يحتاج DNS-01)
```

**وبعد كلِّ نسخة، بلا استثناء:** `nginx -t && systemctl reload nginx`. ولا `restart`
إلّا و`nginx -t` نظيف — `reload` يُبقي العمّالَ القدامى يخدمون إن فشل الجديد، و`restart`
لا يفعل.

## الشهادة: قرارٌ واحدٌ يستحقّ الانتباه

‏`mihrab.dev` و`www` بمُصادِقِ `nginx` — وهو ما يستعمله `sad-lang.org` فعلًا (مقيسٌ من ملفّ تجديده). أمّا `*.webview.mihrab.dev`
فـ**يستلزم DNS-01** — ‏HTTP-01 لا يصدر wildcard أصلًا. وواجهةُ Namecheap البرمجيّة
تشترط قائمةَ IP بيضاءَ فتتعطّل صامتةً عند تغيّر عنوانك، والاكتشافُ يقع بعد انتهاء
الشهادة. **أوصي بنقل الـDNS إلى Cloudflare** واستعمال `certbot-dns-cloudflare`.

وإن نُقل: اجعل `@` و`*.webview` **«‏DNS only» (سحابةٌ رماديّة)**. الوكيلُ يقيّد اتّصالات
WebSocket الطويلة، ومحرابُ الويب يقوم كلُّه عليها ⇒ انقطاعاتٌ تبدو عشوائيّةً ويصعب
ردُّها إلى سببها. أمّا `docs` و`dl` فتوكيلُهما نافع.

## الـwebviews: تبعيّةٌ قائمةٌ تُقطَع في المرحلة ٤

مقيسٌ في `product.json` **للمكتبيّ والويب معًا**: محتوى كلّ webview يُجلَب من
`vscode-cdn.net` ومن إيداعِ insider ليس إيداعَنا — والملفّاتُ نفسُها مشحونةٌ عندنا.
التفصيلُ ومسارُ القطع في [`nginx/webview.mihrab.dev.conf`](nginx/webview.mihrab.dev.conf).

## ما لا يفعله هذا كلُّه

النطاقُ والشهادةُ لا يُسكِتان تحذيرَ SmartScreen عند تنزيل المثبِّت. ذاك شأنُ
[توقيع الشيفرة](../docs/سياسة-توقيع-الشيفرة.md)، وهو مسارٌ مستقلّ.
