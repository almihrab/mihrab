# نشرُ محرابِ الويب — `mihrab.dev`

> **حالةُ هذا المجلّد:** ملفّاتُه **لم تُطبَّق على الخادم بعد**. كُتِبت من قياسٍ محلّيّ،
> ثمّ روجِعت هندسيًّا فوُجد فيها ثلاثةُ أعطابٍ كانت تُسقِط `sad-lang.org` لحظةَ التطبيق
> — صُحِّحت. ما قِيس مذكورٌ بوصفه قياسًا، وما لم يُقَس مذكورٌ بوصفه غيرَ مؤكَّد.

## الحالةُ المقيسة (2026-09-05)

```
mihrab.dev · www · docs · dl · *.webview  →  176.106.227.73  ✅ منتشرة
CAA: 0 issue "letsencrypt.org" · 0 issuewild "letsencrypt.org"  ✅
sad-lang.org  →  nginx · Let's Encrypt (تنتهي 2026-11-04)
127.0.0.1:14006 — لا شيءَ يستمع بعد
```

و`https://mihrab.dev` يقدّم اليومَ الشهادةَ الموقَّعةَ ذاتيًّا `CN=192.168.33.20`
(الكتلةُ الافتراضيّة). **لا تفتحه في متصفّح**: `.dev` في قائمة HSTS المحمَّلة ⇒ رفضٌ
قاطعٌ بلا زرِّ تجاوز، وبعضُ المتصفّحات تُبقي أثرَ الفشل فيبدو عطبًا دائمًا بعد
إصلاح الشهادة. استعمل `http://` أثناء الإعداد.

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

## عقبةٌ قائمة: البناءُ ومحتواه

‏`build/build.sh` يشتقّ الهدفَ من نظام المضيف، فبناءُ ويندوز يُخرج
`vscode-reh-web-win32-x64` وحدَه. **والخادمُ لينكس** ⇒ يلزم بناءٌ على لينكس
(‏WSL أو حاوية أو الخادمُ نفسُه) يُخرج `vscode-reh-web-linux-x64`. ولا يلزم تعديلُ
شيءٍ لأجله: خطوةُ التعريب (ط-0د) وحارسُ `[WEB-01]` يلتقطان `vscode-reh-web-*` أيًّا
كان هدفُها.

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
sudo cp nginx/00-mihrab-shared.conf nginx/01-mihrab-acme.conf /etc/nginx/conf.d/
sudo nginx -t && sudo systemctl reload nginx
sudo mkdir -p /var/www/certbot
sudo certbot certonly --webroot -w /var/www/certbot -d mihrab.dev -d www.mihrab.dev
sudo certbot certificates          # ⚠️ اقرأ اسمَ السلالة، لا تفترضه

# ٢ · الخدمة (بعد نسخ بناء لينكس إلى /opt/mihrab/web)
sudo cp systemd/mihrab-web.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now mihrab-web

# ٣ · كتلُ 443
sudo cp nginx/mihrab.dev.conf /etc/nginx/conf.d/
sudo nginx -t && sudo systemctl reload nginx

# ٤ · wildcard ثمّ الـwebview (يحتاج DNS-01)
```

**وبعد كلِّ نسخة، بلا استثناء:** `nginx -t && systemctl reload nginx`. ولا `restart`
إلّا و`nginx -t` نظيف — `reload` يُبقي العمّالَ القدامى يخدمون إن فشل الجديد، و`restart`
لا يفعل.

## الشهادة: قرارٌ واحدٌ يستحقّ الانتباه

‏`mihrab.dev` و`www` بـHTTP-01 كما يجري لـ`sad-lang.org`. أمّا `*.webview.mihrab.dev`
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
