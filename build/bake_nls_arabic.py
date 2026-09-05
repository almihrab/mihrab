#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""خبز ترجمة الواجهة العربيّة داخل nls.messages.json الافتراضيّ (مساهمة بناء — الطبقة 2).

السبب الجذريّ: حزمة اللغة في VS Code تُفعَّل فقط حين يُسجَّلها مسحُ الإضافات في
‎userDataPath/languagepacks.json — وهذا يجري **بعد** أوّل إقلاع، فيكون أوّل فتح
إنجليزيًّا دائمًا، والثاني عربيًّا. كذلك «إعادة تحميل النافذة» لا تُعيد حلّ NLS
(يجري في العمليّة الرئيسة عند الإقلاع فقط).

الحلّ: نخبز الترجمة العربيّة داخل nls.messages.json الافتراضيّ وقت البناء، فتصير
العربيّة **الافتراضيّ الحرفيّ للنواة** بلا اعتماد على مسح حزمة لغة ولا إعادة تحميل.
السلاسل غير المترجَمة ترتدّ تلقائيًّا للإنجليزيّة (نفس منطق التشغيل: ‎`||`).

الخوارزميّة الأساس مطابقة لـ‎resolveNLSConfiguration في src/vs/base/node/nls.ts:
  لكلّ [moduleId, keys] في nls.keys.json، ولكلّ key:
    result.push( contents[moduleId]?.[key]  ||  default_messages[idx] )

ارتداد على مستوى المفتاح (يعالج انجراف مسار الوحدة بين إصدار الحزمة 1.85 وإصدار
محراب 1.121): حين يغيب التطابق الحرفيّ ‎(moduleId, key)، نستعمل ترجمة نفس المفتاح من
أيّ وحدة أخرى **فقط إن كانت غير ملتبسة** (المفتاح ذاته ⇐ ترجمة واحدة في كلّ الحزمة).
آمن: لا يخمّن عند تعدّد الترجمات لنفس المفتاح؛ يستردّ سلاسل كـ«ملف/عرض» التي نُقِلت
وحدتها (menubarControl ⇐ menubar.contribution) دون تخمين.

idempotent: يحفظ الإنجليزيّة الأصليّة في nls.messages.en.json ويقرأ منها مصدرَ
الارتداد، فإعادة التشغيل لا تُضاعِف الخبز.

الاستعمال: python bake_nls_arabic.py <مسار resources/app>
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mihrab_brand as brand  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def _read_json(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return json.load(f)


def main() -> int:
    if len(sys.argv) != 2:
        print("الاستعمال: python bake_nls_arabic.py <مسار resources/app>", file=sys.stderr)
        return 2
    app = sys.argv[1]
    out_dir = os.path.join(app, "out")
    keys_file = os.path.join(out_dir, "nls.keys.json")
    msgs_file = os.path.join(out_dir, "nls.messages.json")
    en_backup = os.path.join(out_dir, "nls.messages.en.json")
    i18n_file = os.path.join(
        app, "extensions", "language-pack-ar", "translations", "main.i18n.json"
    )

    for p in (keys_file, msgs_file, i18n_file):
        if not os.path.isfile(p):
            print(f"⚠️ ملفّ مفقود: {p}", file=sys.stderr)
            return 1

    # مصدر الإنجليزيّة للارتداد: النسخة الاحتياطيّة إن وُجدت (يضمن idempotency)،
    # وإلا الأصل الحاليّ (ونحفظه احتياطيًّا قبل الكتابة).
    if os.path.isfile(en_backup):
        default_messages = _read_json(en_backup)
    else:
        default_messages = _read_json(msgs_file)
        # ذرّيّة كبقيّة الكتابات: انقطاعٌ هنا يترك مرجعَ الإنجليزيّة مبتورًا، فتفشل
        # كلُّ إعادةِ تشغيلٍ بعده — بصخبٍ لا صمت، لكن بلا تعافٍ إلّا بإعادة البناء.
        _tmp_en = en_backup + ".tmp"
        with open(_tmp_en, "w", encoding="utf-8", newline="") as f:
            json.dump(default_messages, f, ensure_ascii=False)
        os.replace(_tmp_en, en_backup)
        print("حُفِظت نسخة الإنجليزيّة الأصليّة: nls.messages.en.json")

    nls_keys = _read_json(keys_file)

    # مصدر الحزمة الأصليّة (1.85): النسخة الاحتياطيّة إن وُجدت (idempotency)، وإلا
    # الحاليّة (ونحفظها قبل إعادة التخطيط فوقها).
    i18n_backup = os.path.join(os.path.dirname(i18n_file), "main.i18n.orig.json")
    if os.path.isfile(i18n_backup):
        orig = _read_json(i18n_backup)
    else:
        orig = _read_json(i18n_file)
        _tmp_or = i18n_backup + ".tmp"
        with open(_tmp_or, "w", encoding="utf-8", newline="") as f:
            json.dump(orig, f, ensure_ascii=False)
        os.replace(_tmp_or, i18n_backup)
        print("حُفِظت نسخة الحزمة الأصليّة: main.i18n.orig.json")
    contents = orig.get("contents", {})

    # طبقة الارتداد الثالثة (ملكيّة محراب): ملفّ تكميليّ إنجليزيّ→عربيّ يكمّل السلاسل التي
    # لا تغطّيها حزمة اللغة المنبعيّة (1.85) — أساسًا ميزات أحدث (chat/sessions/agentHost…).
    # يُطبَّق **فقط** حين يفشل التطابق الحرفيّ وارتداد المفتاح معًا، فلا يدوس ترجمة منبعيّة.
    # المفتاح = نصّ الإنجليزيّة المصدر حرفيًّا (يطابق default_messages[idx])؛ يزيل التكرار عبر
    # الوحدات تلقائيًّا. آمن: أيّ سلسلة غير موجودة ترتدّ للإنجليزيّة كالمعتاد.
    supplement: dict[str, str] = {}
    supp_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mihrab_ar_supplement.json")
    if os.path.isfile(supp_file):
        try:
            _sup_raw = _read_json(supp_file)
        except (ValueError, OSError) as _e:
            print(f"⚠️ الملفّ التكميليّ تالف ({supp_file}): {_e} — يُتخطّى (الترجمة المنبعيّة تبقى).",
                  file=sys.stderr)
            _sup_raw = {}
        # نقبل فقط أزواج نصّ→نصّ غير الفارغة (تجاهل التعليقات/الميتاداتا إن وُجدت بمفتاح يبدأ بـ«//»).
        supplement = {
            k: v for k, v in _sup_raw.items()
            if isinstance(k, str) and isinstance(v, str) and v and not k.startswith("//")
        }

    # خريطة ارتداد على مستوى المفتاح: key -> ar، لكن فقط للمفاتيح غير الملتبسة
    # (ترجمة واحدة عبر كلّ الحزمة). المفاتيح متعدّدة الترجمات تُترَك للتطابق الحرفيّ.
    key_votes: dict[str, set] = {}
    for _mid, _d in contents.items():
        if not isinstance(_d, dict):
            continue
        for _k, _v in _d.items():
            if isinstance(_v, str) and _v:
                key_votes.setdefault(_k, set()).add(_v)
    key_fallback = {k: next(iter(v)) for k, v in key_votes.items() if len(v) == 1}

    # حلّ الترجمة لكلّ (module, key) بترتيب nls.keys: حرفيّ أوّلًا ثمّ ارتداد المفتاح.
    # نبني معًا: (1) مصفوفة nls.messages.json المخبوزة، (2) حزمة معاد تخطيطها على بِنية
    # وحدات 1.121 كي يجد مسارُ كاش حزمة اللغة (clp) نفسَ الترجمات بالمطابقة الحرفيّة.
    result = []
    remapped: dict[str, dict] = {}
    idx = 0
    exact = 0
    fallback = 0
    supp = 0
    rebranded = 0
    for module_id, keys in nls_keys:
        mod = contents.get(module_id) or {}
        for key in keys:
            ar = mod.get(key)
            if ar:
                exact += 1
            elif key in key_fallback:
                ar = key_fallback[key]
                fallback += 1
            else:
                # الطبقة الثالثة: ملفّ محراب التكميليّ (بمفتاح نصّ الإنجليزيّة المصدر).
                sup_ar = supplement.get(default_messages[idx])
                if sup_ar:
                    ar = sup_ar
                    supp += 1
            # تطبيعُ الهويّة **قبل** الكتابة وعلى الارتداد الإنجليزيّ أيضًا: حزمةُ اللغة
            # المنبعيّة تُرجمت لـVSCodium، والإنجليزيّةُ الأصليّةُ تحمل الاسمَ كذلك. فلو
            # طُبِّع المترجَمُ وحدَه بقي الاسمُ يظهر في كلّ سلسلةٍ لم تُترجَم — تسرّبٌ
            # يزداد كلّما نقصت التغطية، وهو أسوأُ اتّجاهٍ ممكن.
            out, nb = brand.rebrand(ar if ar else default_messages[idx])
            rebranded += nb
            result.append(out)
            if ar:
                remapped.setdefault(module_id, {})[key] = out
            idx += 1
    translated = exact + fallback + supp

    if idx != len(default_messages):
        print(
            f"⚠️ عدم تطابق: مفاتيح={idx} رسائل={len(default_messages)} — توقّف بلا كتابة.",
            file=sys.stderr,
        )
        return 1

    # (1) كتابة nls.messages.json المخبوزة (المسار الافتراضيّ — أوّل فتح).
    tmp = msgs_file + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        json.dump(result, f, ensure_ascii=False)
    os.replace(tmp, msgs_file)

    # (1ب) بناءُ الويب/الخادم (vscode-reh-web-*) يخدم `out/nls.messages.js` للمتصفّح — ملفٌّ
    # لا وجودَ له في المشحون المكتبيّ. محتواه `globalThis._VSCODE_NLS_MESSAGES=[…]` ثمّ ذيلُ
    # sourceMappingURL. فلو خُبِزت الـjson وحدَها بقيت واجهةُ المتصفّح إنجليزيّةً بالكامل
    # (مقيس: 1/21922 عربيّة). نعيد كتابةَ المصفوفة وحدها ونُبقي الذيلَ كما هو.
    js_file = os.path.join(out_dir, "nls.messages.js")
    if os.path.isfile(js_file):
        with open(js_file, "r", encoding="utf-8", newline="") as f:
            js_src = f.read()
        js_prefix = "globalThis._VSCODE_NLS_MESSAGES="
        close = js_src.rfind("]")
        if not js_src.startswith(js_prefix) or close < 0:
            print(f"❌ بنيةٌ غيرُ متوقَّعة في {js_file} — توقّف بلا كتابة.", file=sys.stderr)
            return 1
        # **الذيلُ يُكتَب لا يُستنسَخ.** كان `js_src[close+1:]` يُبقي سطرَ
        # `sourceMappingURL` كما هو — وهو يشير إلى **إصدارات VSCodium**. فيُخدَم
        # اسمُ المنبع للمتصفّح في ملفٍّ نحن نكتبه، ويُجلَب من طرفٍ ثالثٍ عند فتح
        # أدوات المطوّر. وبوّابةُ الهويّة كانت تفحص الـjson المكتبيّة وحدَها فلم ترَه.
        # ولا بديلَ لدينا نشير إليه (لا ننشر خرائطَ مصدر)، فيُحذَف السطر.
        js_out = js_prefix + json.dumps(result, ensure_ascii=False) + ";\n"

        tmp_js = js_file + ".tmp"
        with open(tmp_js, "w", encoding="utf-8", newline="") as f:
            f.write(js_out)
        os.replace(tmp_js, js_file)
        print("✅ خُبِزت نسخةُ المتصفّح أيضًا: out/nls.messages.js")

    # (2) كتابة main.i18n.json المعاد تخطيطها (مسار كاش حزمة اللغة — الفتحات التالية).
    new_pack = {k: orig[k] for k in orig if k != "contents"}
    new_pack["contents"] = remapped  # مُطبَّعُ الهويّة سلفًا (طُبِّع كلُّ عنصرٍ عند بنائه)
    tmp2 = i18n_file + ".tmp"
    with open(tmp2, "w", encoding="utf-8", newline="") as f:
        json.dump(new_pack, f, ensure_ascii=False)
    os.replace(tmp2, i18n_file)

    # (3) إبطال كاش حزمة اللغة الوقتيّ (CLP) عند تغيّر المحتوى — إصلاح فخّ الإزاحة (off-by-one).
    # صلاحيّة كاش CLP في userDataPath تُشتَقّ من md5(extId + نسخة الحزمة) ومساره يحوي commit
    # المنبع الثابت (languagePacks.ts). فلو تغيّر تخطيط nls أو الترجمة مع ثبات نسخة الحزمة، بقي
    # كاش CLP بائتًا يُزيح الترجمات موضعًا (زرّ «عدم الحفظ» ظهر «حفظ»). نجعل نسخة الحزمة **بصمةَ
    # محتوى**: هاش result المخبوز يلتقط تغيّر التخطيط والترجمة معًا. فأيّ تغيّر يبمب النسخة ⇒ هاش
    # صلاحيّة جديد ⇒ إعادة توليد الكاش تلقائيًّا؛ وثبات المحتوى ⇒ نسخة ثابتة (بلا إبطال زائف).
    # قيد تصميميّ (مراجعة Amelia M1): النسخة **غير رتيبة** (قد تنقص عن الأصل) — لا يضرّ لأنّ الهاش
    # يقارن بالتساوي لا بالترتيب، ويفترض أنّ الحزمة **مدمجة فقط** (محراب محرِّر مغلق بلا سوق يُظلّل
    # النسخة المدمجة بأعلى semver). لو أُضيف سوق لاحقًا، اجعل الـpatch رتيبًا (طابع زمنيّ للبناء).
    pkg_file = os.path.join(app, "extensions", "language-pack-ar", "package.json")
    if os.path.isfile(pkg_file):
        # الأصل (idempotency + مرجع major.minor للحزمة المنبعيّة): يُحفَظ مرّة ذرّيًّا قبل أوّل bump.
        pkg_backup = pkg_file + ".orig"
        if not os.path.isfile(pkg_backup):
            tmp_b = pkg_backup + ".tmp"
            with open(tmp_b, "w", encoding="utf-8", newline="") as f:
                json.dump(_read_json(pkg_file), f, ensure_ascii=False, indent=2)
            os.replace(tmp_b, pkg_backup)
        base_ver = str(_read_json(pkg_backup).get("version", "1.0.0"))
        # حارس المكوّنين (Amelia L2): نسخة مكوّن واحد («1») ⇒ "1.<int>" = semver غير صالح.
        _mm = base_ver.split(".")[:2]
        major_minor = ".".join(_mm) if len(_mm) == 2 else "1.0"
        # بصمة حتميّة من المحتوى المخبوز (نفس المحتوى ⇒ نفس النسخة ⇒ idempotent). تشمل أيضًا
        # ملفّات i18n المحقونة (contents.package) من patch_extension_nls الذي يعمل قبلنا، كي
        # يُبطَل كاش CLP (مفتاحه md5(extId+version)) عند تغيّر ترجمة الامتدادات — لا بالـmtime
        # وحده. [[mihrab-stale-clp-language-cache-gotcha]].
        ext_i18n_dir = os.path.join(
            app, "extensions", "language-pack-ar", "translations", "extensions")
        ext_sig = hashlib.md5()
        if os.path.isdir(ext_i18n_dir):
            for name in sorted(os.listdir(ext_i18n_dir)):
                if name.endswith(".i18n.json"):
                    ext_sig.update(name.encode("utf-8"))
                    with open(os.path.join(ext_i18n_dir, name), "rb") as _ef:
                        ext_sig.update(_ef.read())
        content_sig = hashlib.md5(
            (json.dumps(result, ensure_ascii=False) + ext_sig.hexdigest()).encode("utf-8")
        ).hexdigest()
        new_ver = f"{major_minor}.{int(content_sig[:8], 16)}"  # patch عدد صحيح ≤ ~4.3e9 (semver صالح)
        pkg = _read_json(pkg_file)
        if pkg.get("version") != new_ver:
            pkg["version"] = new_ver
            tmp3 = pkg_file + ".tmp"
            with open(tmp3, "w", encoding="utf-8", newline="") as f:
                json.dump(pkg, f, ensure_ascii=False, indent=2)
            os.replace(tmp3, pkg_file)
            print(f"↻ نسخة حزمة اللغة ⇐ {new_ver} (بصمة محتوى ⇒ إبطال كاش CLP البائت)")
        else:
            print(f"= نسخة حزمة اللغة ثابتة ({new_ver}) — لا تغيّر محتوى، لا إبطال زائف")
    else:
        print("⚠️ لا package.json لحزمة اللغة — تُخطّى بصمة إبطال الكاش (الترجمة مخبوزة سلفًا).",
              file=sys.stderr)

    pct = (translated * 100) // idx if idx else 0
    print(
        f"✅ عُرّبت الواجهة: {translated}/{idx} سلسلة ({pct}%) — حرفيّ={exact}، "
        f"ارتداد-مفتاح={fallback}، تكميليّ-محراب={supp}، تطبيعُ هويّة={rebranded}. "
        f"(nls.messages.json مخبوز + main.i18n.json معاد تخطيطه)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
