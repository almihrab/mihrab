# -*- coding: utf-8 -*-
"""صفحةُ معاينة «محراب × ألف»."""
import html
import json
import os

from .data import DATA, SITE
from .templates import data_island

# ═════════════════════ صفحةُ معاينة «محراب × ألف» ═════════════════════
# صفحةٌ **قائمةٌ بذاتها**، خارجَ قِشرة الموقع عمدًا: لا ملاحةَ ولا تذييلَ ولا رابطَ
# من الصفحة الرئيسة إليها. غايتُها أن تُرسَل إلى مطوّري لغةٍ بعينها ثمّ تُطوى —
# ووضعُها في الملاحة يجعل بناءَ معاينةٍ يبدو إصدارًا ثانيًا لمحراب.
# ولذلك أيضًا لا تشارك site.css: تغييرُ تنسيقٍ في الموقع بعد أشهرٍ يجب ألّا
# يُفسِد صفحةً منسيّةً لا يفتحها أحدٌ منّا.
# سكربتُ صفحة المعاينة، على مستوى الوحدة ليُكتَب ملفًّا مجاورًا:
# سياسةُ `script-src 'self'` تحجب الداخليَّ، والصفحةُ تُصيَّر بلا جدولِ تنزيلٍ بصمت.
ALIF_JS = """(function(){
  var baked=JSON.parse(document.getElementById("baked").textContent);
  var labels=JSON.parse(document.getElementById("labels").textContent);
  function render(m){
    var host=document.getElementById("dl");
    if(!m||!m.assets||!m.assets.length){
      host.innerHTML='<p class="empty">\\u0644\\u0645 \\u064a\\u064f\\u0631\\u0641\\u064e\\u0639 '+
        '\\u0628\\u0646\\u0627\\u0621\\u064f \\u0645\\u0639\\u0627\\u064a\\u0646\\u0629\\u064d '+
        '\\u0628\\u0639\\u062f.</p>';
      return;
    }
    var base=m.base||"../../dl/preview-alif/";
    var rows=m.assets.map(function(a){
      var mb=(a.size/1e6).toFixed(0);
      return '<tr><td>'+(labels[a.id]||a.id)+'<br><span class="sha">'+
        (a.sha256||"")+'</span></td><td class="num">'+mb+' \\u0645.\\u0628</td>'+
        '<td><a class="btn" href="'+base+a.file+'">\\u0646\\u0632\\u0651\\u0650\\u0644</a></td></tr>';
    }).join("");
    host.innerHTML='<div class="table-wrap"><table><thead><tr>'+
      '<th>\\u0627\\u0644\\u0645\\u0646\\u0635\\u0651\\u0629 \\u0648 SHA-256</th>'+
      '<th>\\u0627\\u0644\\u062d\\u062c\\u0645</th><th></th></tr></thead><tbody>'+
      rows+'</tbody></table></div>';
    if(m.version){
      document.getElementById("ver").textContent=
        "\\u0628\\u0646\\u0627\\u0621\\u064f \\u0627\\u0644\\u0645\\u0639\\u0627\\u064a\\u0646\\u0629 "+
        m.version+(m.date?" \\u00b7 "+m.date:"");
    }
  }
  render(baked);
  fetch("../../dl/preview-alif/releases.json",{cache:"no-store"})
    .then(function(r){return r.ok?r.json():null;})
    .then(function(m){ if(m) render(m); })
    .catch(function(){});
})();
"""


def build_alif_preview():
    with open(os.path.join(DATA, "releases-alif.json"), encoding="utf-8") as f:
        baked = json.load(f)

    labels = {p["id"]: "%s — %s" % (p["label"], p["kind"]) for p in SITE["platforms"]}

    css = """
:root{--bg:#fbfaf7;--fg:#1c1a17;--dim:#6b645c;--line:#e0dcd4;--card:#fff;
--accent:#7a5c2e;--accent-fg:#fff;--warn-bg:#fdf6e3;--warn-line:#e8d9b0}
:root:not([data-theme="light"]){color-scheme:light dark}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
--bg:#16150f;--fg:#f0ece3;--dim:#a49c8e;--line:#332f26;--card:#1e1c15;
--accent:#d8b46a;--accent-fg:#1a1710;--warn-bg:#241f14;--warn-line:#4a3f26}}
:root[data-theme="dark"]{--bg:#16150f;--fg:#f0ece3;--dim:#a49c8e;--line:#332f26;
--card:#1e1c15;--accent:#d8b46a;--accent-fg:#1a1710;--warn-bg:#241f14;--warn-line:#4a3f26}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font-family:"IBM Plex Sans Arabic","Noto Sans Arabic","Segoe UI",Tahoma,system-ui,sans-serif;
font-size:17px;line-height:1.85;-webkit-font-smoothing:antialiased}
.wrap{max-width:52rem;margin:0 auto;padding:3.5rem 1.25rem 5rem;
display:flex;flex-direction:column;gap:2.5rem}
.tag{display:inline-block;font-size:.8rem;padding:.2rem .7rem;
border:1px solid var(--accent);color:var(--accent);border-radius:999px}
h1{font-size:clamp(1.9rem,5vw,2.7rem);line-height:1.3;margin:.7rem 0 0;text-wrap:balance}
h2{font-size:1.3rem;margin:0 0 .6rem;text-wrap:balance}
p{margin:.6rem 0}
.lead{font-size:1.1rem;color:var(--dim)}
section{border-top:1px solid var(--line);padding-top:1.8rem}
.note{background:var(--warn-bg);border:1px solid var(--warn-line);
border-radius:.6rem;padding:1rem 1.2rem}
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.95rem}
th,td{text-align:right;padding:.7rem .6rem;border-bottom:1px solid var(--line);
vertical-align:top}
th{font-size:.85rem;color:var(--dim);font-weight:600}
td.num{font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--dim)}
/* لا `Courier New`: على أندرويد اسمٌ مستعارٌ لـserif-monospace فتصير البصمةُ سيريفيّة — كما في `--font-mono` */
code,.sha{font-family:"Mihrab Code Arabic",ui-monospace,"Cascadia Mono",Consolas,monospace;
font-size:.82rem;word-break:break-all;color:var(--dim);direction:ltr;
display:inline-block;unicode-bidi:isolate}
.btn{display:inline-block;background:var(--accent);color:var(--accent-fg);
text-decoration:none;padding:.45rem 1.1rem;border-radius:.45rem;font-size:.95rem;
white-space:nowrap}
.btn:hover{filter:brightness(1.08)}
@media(pointer:coarse){.btn{min-height:44px;display:inline-flex;align-items:center}}
.btn:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
ul{margin:.5rem 0;padding-inline-start:1.3rem}
li{margin:.35rem 0}
.yes::marker{content:"\\2713\\a0 "}
.dim{color:var(--dim)}
.empty{color:var(--dim)}
footer{border-top:1px solid var(--line);padding-top:1.5rem;font-size:.88rem;color:var(--dim)}
a{color:var(--accent)}
@media print{.btn{display:none}}
"""


    ext = baked.get("alif_extension", {})
    rt = baked.get("alif_runtime", {})
    body = """<div class="wrap">
<header>
  <span class="tag">بناءُ معاينةٍ مؤقّت</span>
  <h1>محراب، ولغةُ ألف تعمل فيه من أوّل تشغيل</h1>
  <p class="lead">نزِّل التطبيق وافتح ملفَّ ألف. لا تثبيتَ امتدادٍ ولا إعدادَ سوق —
  امتدادُ لغة ألف مشحونٌ داخل هذا البناء.</p>
  <p class="dim" id="ver"></p>
</header>

<section>
  <h2>التنزيل</h2>
  <div id="dl"><p class="empty">لم يُرفَع بناءُ معاينةٍ بعد.</p></div>
  <p class="dim">قارِن بصمةَ SHA-256 بما نزّلتَه قبل التنصيب:
  <code>sha256sum</code> على لينكس وmacOS، و<code>Get-FileHash -Algorithm SHA256</code>
  على ويندوز. والحزمُ <b>غيرُ موقّعة</b> بعد، فيتوقّع ويندوز وmacOS تحذيرًا عند أوّل تشغيل.</p>
</section>

<section>
  <h2>ما يعمل فورًا، وما يحتاج ألفَ نفسَها</h2>
  <p>الامتدادُ يحلّل ألفَ محلّيًّا، فأكثرُها لا يحتاج شيئًا خارجَ التطبيق:</p>
  <ul>
    <li class="yes">إبرازُ الصياغة، ومقتطفاتُ البُنى، وسمةُ أيقونات ألف</li>
    <li class="yes">فحصٌ ساكنٌ فوريّ: بنيةُ الكتل، وتوازنُ الأقواس، والنصوصُ غير المغلقة</li>
    <li class="yes">إكمالٌ يطابق دون تفريقٍ بين صور الهمزة والألف، ويتجاهل التشكيل</li>
    <li class="yes">فهرسةُ رموز المشروع: الانتقالُ إلى التعريف والبحثُ عبر الملفّات</li>
    <li class="yes">تنبيهٌ على كلمات ألف 5 المتغيّرة (مثل <code>لاجل</code> ← <code>لكل</code>) بإصلاحٍ سريع</li>
  </ul>
  <p>وواحدٌ يحتاج ما هو خارجَ محراب:</p>
  <ul>
    <li class="yes"><b>تشغيلُ البرنامج</b> — مفسّرُ ألف مشحونٌ في هذا البناء، فيعمل
    <code>تشغيل ملفّ ألف</code> بلا تنزيلٍ ولا إعداد. ومن أراد مفسّرَه فالإعدادُ
    <code>alif.executablePath</code> أسبقُ من المشحون، وكذلك ثنائيٌّ في مشروعك.</li>
    <li><b>خادمُ ألف اللغويّ الخارجيّ</b> مطفأٌ افتراضيًّا
    (<code>alif.lsp.enabled</code>) — والمحلّلُ المدمج يعمل بدونه.</li>
  </ul>
</section>

<section class="note">
  <h2>ما هذه الصفحة، وما ليست</h2>
  <p><b>بناءُ تجريبٍ مؤقّت، لا إصدارٌ من إصدارات محراب.</b> لا تُذكر هذه الصفحةُ في
  موقع محراب ولا يُوصَل إليها من ملاحته، وقد تُطوى متى انتهى غرضُها.</p>
  <p>ومحرابٌ منصّةٌ تستضيف اللغات: الوضعُ الطبيعيُّ أن تُثبَّت لغةُ ألف من سوق
  Open VSX المفتوح كأيّ امتداد، لا أن تُشحن داخل التطبيق. وهذا البناءُ يتخطّى تلك
  الخطوةَ لغرضٍ واحد: أن تجرّبوا محرابًا بلا مقدّمات.</p>
</section>

<footer>
  <p>امتدادُ لغة ألف من <a href="{src}">{src_short}</a> بترخيص MIT، مأخوذٌ في هذا
  البناء من الإصدار {ver} وبصمتُه مثبَّتةٌ في شفرةِ بنائنا:
  <span class="sha">{sha}</span></p>
  <p>ومفسّرُ ألف من <a href="{rt_src}">{rt_src_short}</a>، الإصدار {rt_ver}،
  مشحونٌ في <code>bin/</code> داخل الامتداد وبصمةُ حزمةِ كلِّ منصّةٍ مثبَّتةٌ كذلك.</p>
  <p>محراب — منصّةُ تطويرٍ عربيّةٌ مفتوحةُ المصدر (MIT) ·
  <a href="https://github.com/almihrab/mihrab">المستودع</a></p>
</footer>
</div>""".format(
        src=html.escape(ext.get("source", "")),
        src_short=html.escape(ext.get("source", "").replace("https://github.com/", "")),
        ver=html.escape(ext.get("version", "")),
        sha=html.escape(ext.get("sha256", "")),
        rt_src=html.escape(rt.get("source", "")),
        rt_src_short=html.escape(rt.get("source", "").replace("https://github.com/", "")),
        rt_ver=html.escape(rt.get("version", "")))

    return (
        "<!doctype html>"
        '<html lang="ar" dir="rtl"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex">'
        "<title>محراب × لغة ألف — بناءُ معاينة</title>"
        # الصفحةُ خارج `page_shell` فلا تَرِث ورقةَ الخطوط — وكانت تُعرَض بخطّ
        # النظام وحدَها من بين صفحات الموقع، وهي التي يصلها زائرٌ آتٍ من صفحةٍ
        # بالخطّ المورَّد. والمسارُ نسبيٌّ كما في `preview-alif.js` أسفلَه.
        '<link rel="stylesheet" href="../../assets/fonts.css">'
        "<style>%s</style></head><body>" % css
        + body
        + data_island("baked", baked)
        + data_island("labels", labels)
        # ⛔ لا `<script>` داخليًّا: سياسةُ الجذر `script-src 'self'` بلا `'unsafe-inline'`
        #    تحجبه، فتُصيَّر الصفحةُ ‎200‎ بعنوانٍ ونصٍّ **وبلا جدول تنزيلٍ البتّة** — بلا
        #    رسالةِ خطأٍ ولا شيءٍ أحمر. قِيس على الصفحة المنشورة. والعلاجُ ما فُعل
        #    بسكربت الإقلاع [WEB-09]: ملفٌّ مجاور.
        + '<script src="../../assets/preview-alif.js"></script></body></html>')
