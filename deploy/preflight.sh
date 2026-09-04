#!/usr/bin/env bash
# قياساتٌ تسبق أيَّ نسخٍ إلى `/etc/nginx` — تُشغَّل **على الخادم**.
#
# كلُّ سؤالٍ هنا جوابُه يغيّر ما يُنسَخ. والتخمينُ في أيٍّ منها يُسقِط `sad-lang.org`.
#
#   scp -P 2000 deploy/preflight.sh saleh@176.106.227.73:/tmp/
#   ssh -p 2000 saleh@176.106.227.73 'sudo bash /tmp/preflight.sh'

set -uo pipefail
echo "════ قياساتُ ما قبل النشر ════"

echo
echo "── (1) إصدارُ nginx ⇒ أيُّ صيغةِ HTTP/2 ──"
nginx -v 2>&1
echo "   ‏≥ 1.25.1 ⇒ يجوز `http2 on;`   ·   دونه ⇒ اتركه معطَّلًا (الافتراضُ في ملفّاتنا)"

echo
echo "── (2) الخادمُ الافتراضيُّ على 443 ──"
echo "   إن لم يوجد `default_server`، صارت **أوّلُ** كتلةٍ أبجديًّا هي الافتراضيّة —"
echo "   وقد تصير كتلةُ محراب، فيُمرَّر كلُّ Host مجهولٍ إلى محرِّرٍ يفتح طرفيّة."
nginx -T 2>/dev/null | grep -nE 'listen[^;]*443' | head -20
echo "   --- default_server ---"
nginx -T 2>/dev/null | grep -n 'default_server' | head -10 || echo "   ⚠️ لا default_server — انسخ 00-default-tls.conf"

echo
echo "── (3) ترويساتٌ في http{} قد تُلغيها كتلتُنا ──"
echo "   `add_header` في مستوًى أدنى يُلغي وراثةَ كلِّ ترويساتِ ما فوقه."
nginx -T 2>/dev/null | grep -nE '^\s*(add_header|more_set_headers)' | head -20

echo
echo "── (4) هل الخريطةُ معرَّفةٌ سلفًا؟ (التعريفُ مرّتين خطأُ تحميل) ──"
nginx -T 2>/dev/null | grep -n 'connection_upgrade' | head -5 || echo "   غيرُ معرَّفة — انسخ 00-mihrab-shared.conf"

echo
echo "── (5) كيف يجدّد sad-lang.org شهادتَه ⇒ أيَّ طريقةٍ نستعمل لمحراب ──"
if [ -r /etc/letsencrypt/renewal/sad-lang.org.conf ]; then
  grep -E 'authenticator|webroot_path|installer' /etc/letsencrypt/renewal/sad-lang.org.conf
else
  echo "   لا ملفَّ تجديد — تحقّق يدويًّا: certbot certificates"
fi

echo
echo "── (6) الشهاداتُ الموجودة (أسماءُ السلالات كما هي لا كما نفترض) ──"
certbot certificates 2>/dev/null | grep -E 'Certificate Name|Domains|Expiry' || echo "   لا certbot أو لا شهادات"

echo
echo "── (7) هل يستمع أحدٌ على 14006؟ ──"
ss -ltnp 2>/dev/null | grep -E ':14006' || echo "   لا — خدمةُ محرابٍ لم تُشغَّل بعد (متوقَّع)"

echo
echo "── (8) هل يخدم محرابٌ شيئًا على المساراتِ التي سنحجبها؟ ──"
if ss -ltn 2>/dev/null | grep -q ':14006'; then
  for p in /issues /license /releases /repo; do
    printf '   %-12s %s\n' "$p" "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:14006$p")"
  done
  echo "   أيُّ 200 ⇒ احذف التحويلَ الموافقَ من mihrab.dev.conf"
  echo "── (9) هل يضغط الخادمُ ردودَه بنفسِه؟ (يحدّد جدوى gzip عندنا) ──"
  curl -sI -H 'Accept-Encoding: gzip' http://127.0.0.1:14006/ | grep -i 'content-encoding' \
    || echo "   لا Content-Encoding ⇒ ضغطُ nginx نافع"
else
  echo "   يُؤجَّل حتّى تعمل الخدمة"
fi

echo
echo "════ نسخةٌ احتياطيّةٌ قبل أيّ تعديل ════"
echo "   tar czf ~/nginx-\$(date +%F).tgz /etc/nginx"
echo "   وبعد كلِّ نسخة، بلا استثناء:  nginx -t && systemctl reload nginx"
echo "   ولا تستعمل restart إلّا و nginx -t نظيف."
