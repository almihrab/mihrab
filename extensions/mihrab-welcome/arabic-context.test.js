"use strict";
const test = require("node:test");
const assert = require("node:assert");
const { hasArabic, PROBE_CHARS } = require("./arabic-context.js");

test("سياقٌ عربيّ: حرفٌ عربيٌّ واحدٌ يكفي، واللاتينيُّ الخالصُ لا", () => {
  assert.strictEqual(hasArabic("const x = 1; // مرحبا"), true);
  assert.strictEqual(hasArabic("ﻻ"), true, "أشكالُ العرض (ب) عربيّة");
  assert.strictEqual(hasArabic("git status\nnothing to commit"), false);
});

test("سياقٌ عربيّ: U+FEFF (علامةُ ترتيب البايت) ليس حرفًا عربيًّا", () => {
  // آخرُ كتلة «أشكال العرض ب» هو U+FEFF؛ نطاقٌ ينتهي عنده يحسب ملفًّا لاتينيًّا
  // يبدأ بعلامة BOM «عربيًّا» فيحرق رسالةَ المرّة الواحدة في غير سياقها.
  assert.strictEqual(hasArabic("﻿{\"name\": \"pkg\"}"), false);
});

test("سياقٌ عربيّ: ما ليس نصًّا لا يُحسَب، وما بعد حدّ الفحص لا يُقرأ", () => {
  assert.strictEqual(hasArabic(undefined), false);
  assert.strictEqual(hasArabic(42), false);
  assert.strictEqual(hasArabic("a".repeat(PROBE_CHARS) + "عربيّ"), false);
  assert.strictEqual(hasArabic("a".repeat(PROBE_CHARS - 1) + "ع"), true);
});
