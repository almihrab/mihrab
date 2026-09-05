# نشرُ محرابِ الويب **بخادم** — مسارٌ متقاعد

> # ⛔ لا تنفّذ ما في هذه الوثيقة. [MIHRAB-DEPLOY-RETIRED]
>
> ‏`mihrab.dev` يخدم اليومَ **بناءً ثابتًا بلا خادم**. وخدمةُ `mihrab-web.service`
> **أُوقِفت وعُطِّلت** على الخادم، وكتلةُ الوسيط `mihrab.dev.conf` لم تعد مركَّبة.
>
> والمراحلُ ٢–٤ أدناه تأمر حرفيًّا بـ`systemctl enable --now mihrab-web` وبنسخ
> `mihrab.dev.conf` إلى **المسار نفسِه** الذي يكتب فيه `static_deploy.sh`. فتنفيذُها
> اليومَ يدوس الكتلةَ الحيّة **ويعيد فتح نظامِ ملفّاتٍ وطرفيّةٍ خلف عنوانٍ عامّ** —
> وهو سطحُ الهجوم الذي أُوقِف النشرُ الأوّلُ لأجله. ليست وثيقةً متقادمة؛ هي وثيقةٌ
> **ضارّةٌ إن نُفِّذت**.
>
> **المسارُ القائم:** [`النشر-الثابت.md`](النشر-الثابت.md).
>
> ولا تُحذَف هذه: قياسُ الخادم فيها (‏nginx 1.24.0 · ترتيبُ إدراج `conf.d` قبل
> `sites-enabled` · غيابُ `default_server` على 443 · تكرارُ قصاصة certbot) **صحيحٌ
> ومكلفُ الاكتساب**، وهو الأرضُ التي تقوم عليها الكتلةُ الثابتة. تُقرأ سِجلًّا، لا
> تعليمات. والحذفُ يُغري بإعادة الاختراع.

> **حالةُ الملفّات (تاريخيًّا):** كُتِبت من قياسٍ محلّيّ، ثمّ روجِعت هندسيًّا فوُجد فيها
> ثلاثةُ أعطابٍ كانت تُسقِط `sad-lang.org` لحظةَ التطبيق — صُحِّحت، ثمّ طُبِّقت فعلًا
> ونجحت، ثمّ تقاعدت بقرار.

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

كلُّ مرحلةٍ تنتهي بتحقّقٍ يقيس أنّها نجحت. ولا تُبدأ التاليةُ قبل أن يخضرّ.

### ٠ · قِسْ واحتفظ بنسخة — **مُنفَّذة ✅** (2026-09-05)

```bash
sudo bash preflight.sh
# نسخةُ الإعداد. `--exclude=./ssl` مقصود: مفتاحٌ خاصٌّ لا يُقرأ بلا root ولا نلمس
# المجلّدَ إطلاقًا. وبدونه يخرج tar بـ2 فتكون «نسخةٌ» لا يُوثَق بها.
tar czf ~/mihrab-nginx-config-$(date +%F-%H%M).tgz --exclude=./ssl -C /etc/nginx .
```

**ما قِيس:** ‏nginx 1.24.0 · ستّةُ مواقعَ · لا `default_server` على 443 ·
`kadah` تضع `http2` على المقبس ⇒ مفعَّلٌ سلفًا · `certbot` بمُصادِقِ `nginx` ·
‏14006 مشغولٌ و14007 حُرّ · لا `add_header` في `http{}` ·
و`options-ssl-nginx.conf` و`ssl-dhparams.pem` **موجودان** (كان افتراضًا فصار قياسًا).

**والنسخةُ الاحتياطيّةُ لم تُقبَل حتّى استُعيدت فعلًا:** فُكَّت في مجلّدٍ مؤقّتٍ
وقُورنت بايتيًّا بـ`/etc/nginx` — **26 ملفًّا، صفرُ اختلافات**، والوصلاتُ الستُّ فيها.
نسخةٌ لم تُجرَّب استعادتُها ليست نسخة.

التراجعُ في أيّ لحظة:

```bash
sudo tar xzf ~/mihrab-nginx-config-<الطابع>.tgz -C /etc/nginx
sudo nginx -t && sudo systemctl reload nginx
```

### ١ · المشتركاتُ وكتلةُ 80 ⇒ ثمّ الشهادة

**أوّلًا — نقلُ الملفّات إلى الخادم.** لا نسخةَ من المستودع هناك، والأوامرُ النسبيّةُ
تفشل (`cp: cannot stat 'nginx/…'`). من جهاز التطوير:

```bash
ssh -p 2000 saleh@176.106.227.73 'mkdir -p /tmp/mihrab-deploy'
scp -P 2000 deploy/nginx/*.conf deploy/systemd/*.service     saleh@176.106.227.73:/tmp/mihrab-deploy/
```

**ثمّ على الخادم** — والترتيبُ داخلَ هذه الكتلة ملزِم:

```bash
# (أ) المشتركات: خريطةُ الترقية والمجمَّع. تُحمَّل قبل كتل الخدمة.
sudo cp /tmp/mihrab-deploy/00-mihrab-shared.conf /etc/nginx/conf.d/

# (ب) كتلةُ 80 — **الملفُّ قبل الوصلة**. عكسُ الترتيب يُنشئ وصلةً معلَّقةً
#     (`ln -sf` لا يتحقّق من الهدف) فيفشل `nginx -t` وتُصبح كلُّ مواقعك على
#     حافّة السقوط عند أوّل restart. أُوقِع فعلًا.
sudo cp /tmp/mihrab-deploy/01-mihrab-acme.conf /etc/nginx/sites-available/mihrab-acme
sudo ln -sf /etc/nginx/sites-available/mihrab-acme /etc/nginx/sites-enabled/

# (ج) بوّابة: لا تتابع قبل «syntax is ok» و«test is successful».
sudo nginx -t && sudo systemctl reload nginx

# (د) الشهادة — بمُصادِقِ nginx (مقيسٌ من ملفّ تجديد sad-lang.org)
sudo certbot certonly --nginx -d mihrab.dev -d www.mihrab.dev
sudo certbot certificates
```

**تحقّق:**

```bash
curl -sI http://mihrab.dev/ | head -2          # ⇒ 301 إلى https
for h in sad-lang.org sila-hub.dev kadah.tech; do
  printf '%-16s %s\n' "$h" "$(curl -sk -o /dev/null -w '%{http_code}' https://$h/)"
done
```

> **اسمُ السلالة مقيسٌ سلفًا:** `certbot certificates` على هذا الخادم يُظهِر
> `sad-lang.org` و`sila-hub.dev` فقط — فلا تصادمَ، والسلالةُ ستكون `mihrab.dev`
> بالضبط. ومساراتُ `mihrab.dev.conf` صحيحةٌ كما هي.

**التراجعُ عن هذه المرحلة وحدَها:**

```bash
sudo rm -f /etc/nginx/sites-enabled/mihrab-acme /etc/nginx/conf.d/00-mihrab-shared.conf
sudo nginx -t && sudo systemctl reload nginx
```

### ٢ · الخدمة

**٢-أ · مستخدمٌ ببيتٍ حقيقيّ** — بلا بيتٍ يفشل `git` والطرفيّةُ داخل الخدمة:

```bash
sudo useradd --system --home-dir /var/lib/mihrab --shell /bin/bash mihrab
```

**٢-ب · رمزُ الاتّصال** — ليس تحسينًا: بدونه كلُّ من يبلغ العنوانَ يحصل على طرفيّة:

```bash
sudo install -d -m 750 -o mihrab -g mihrab /etc/mihrab
openssl rand -hex 32 | sudo tee /etc/mihrab/token >/dev/null
sudo chown mihrab:mihrab /etc/mihrab/token && sudo chmod 600 /etc/mihrab/token
sudo cat /etc/mihrab/token        # احفظه — يلزمك لفتح المحرِّر أوّلَ مرّة
```

**٢-ج · نقلُ البناء** (‏370 م.ب) — من الجهاز الذي بنى:

```bash
# على جهاز البناء، حيث المصدر vscode-reh-web-linux-x64:
rsync -az --delete -e 'ssh -p 2000'   .upstream/vscode-reh-web-linux-x64/ saleh@176.106.227.73:/tmp/mihrab-web/

# ثمّ على الخادم — /opt لا يُكتَب إلّا بـsudo، فنُدرِج عبر /tmp:
sudo install -d -o mihrab -g mihrab /opt/mihrab /opt/mihrab/data
sudo rsync -a --delete /tmp/mihrab-web/ /opt/mihrab/web/
sudo chown -R mihrab:mihrab /opt/mihrab/web
rm -rf /tmp/mihrab-web
```

**٢-د · التشغيل:**

```bash
sudo cp /tmp/mihrab-deploy/mihrab-web.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now mihrab-web
```

**تحقّق:**

```bash
systemctl is-active mihrab-web                      # ⇒ active
ss -ltn | grep 14007                                # ⇒ 127.0.0.1 فقط
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:14007/   # ⇒ 403
journalctl -u mihrab-web -n 30 --no-pager
```

**‏403 هو الجواب الصحيح** — قِيس على بناء لينكس نفسِه: الخادمُ يردّ 403 على كلّ مسارٍ
بلا رمز، و`?tkn=<الرمز>` يردّ 302. **فـ200 هنا يعني أنّ الرمزَ لا يعمل** — أوقف
الخدمةَ وراجع `/etc/mihrab/token` قبل أن تفتح المرحلةَ ٣.

### ٣ · كتلُ 443

> **طبقةُ العزل آمنة — قِيست.** بناءُ لينكس يردّ **404** على `/issues` و`/license`
> و`/releases` و`/repo` (برمزٍ صالح)، فلا يخدم شيئًا عليها ⇒ التحويلاتُ لا تحجب وظيفة.

```bash
sudo cp /tmp/mihrab-deploy/mihrab.dev.conf /etc/nginx/sites-available/mihrab
sudo ln -sf /etc/nginx/sites-available/mihrab /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**تحقّق — وهنا يظهر محرابٌ لأوّل مرّة:**

```bash
curl -sI https://mihrab.dev/ | head -3
curl -sI https://www.mihrab.dev/ | grep -i location        # ⇒ يحوّل إلى الجذر
curl -sI https://mihrab.dev/issues | grep -i location      # ⇒ github
curl -sk -o /dev/null -w '%{http_version}\n' https://mihrab.dev/   # ⇒ 2
# والأهمُّ: أنّ المواقعَ الستّةَ ما زالت تعمل
for h in sad-lang.org sila-hub.dev kadah.tech; do
  printf '%-16s %s\n' "$h" "$(curl -sk -o /dev/null -w '%{http_code}' https://$h/)"
done
```

**ثمّ افتح `https://mihrab.dev/?tkn=<الرمز>` في متصفّح.** إن ظهر سطحُ المكتب ثمّ
**تجمّد**، فالسببُ ترويستا `Upgrade`/`Connection` — راجع `00-mihrab-shared.conf`.

### ٤ · الـwildcard والـwebview

**الشهادةُ أوّلًا** — والمزوّدُ قرارٌ لم يُتَّخذ بعد (انظر «الشهادة» أدناه)، لكنّ
**نطاقَ الأمر لا يعتمد على المزوّد**، فهو مكتوبٌ هنا كي يُحرَس:

```bash
# ‏Cloudflare (الموصى به):
sudo certbot certonly --dns-cloudflare   --dns-cloudflare-credentials /etc/mihrab/cloudflare.ini   --cert-name webview.mihrab.dev -d '*.webview.mihrab.dev'
```

⛔ **ولا تجمع معها اسمًا آخر.** `-d '*.webview.mihrab.dev' -d mihrab.dev` يبدو محترمًا
للاحتواء وهو نقضُه: مفتاحٌ واحدٌ يُنتحَل بتسرُّبه الموقعُ كلُّه. سلالتان لا سلالة.
ويحرس ذلك فحصُ `[DEP-01]` في الطبقة الساكنة — يقرأ هذا السطرَ نفسَه.

وبعد صدور الشهادة:

```bash
sudo cp /tmp/mihrab-deploy/webview.mihrab.dev.conf /etc/nginx/sites-available/mihrab-webview
sudo ln -sf /etc/nginx/sites-available/mihrab-webview /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**ثمّ — وليس قبلَه — تعديلُ المستودع:** `webviewContentExternalBaseUrlTemplate` في
`product-overrides/product.json`، وروابطُ المنتَج إلى `mihrab.dev/issues` وأخواتِها.

---

**وبعد كلِّ نسخة، بلا استثناء:** `sudo nginx -t && sudo systemctl reload nginx`.
ولا `restart` إلّا و`nginx -t` نظيف — `reload` يُبقي العمّالَ القدامى يخدمون إن فشل
الجديد، و`restart` لا يفعل، فتسقط المواقعُ الستّةُ معه.

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
