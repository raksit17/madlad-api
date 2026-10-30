import test from "node:test";
import assert from "node:assert/strict";
import { TranslationSession, normalizeText } from "../app/static/session.mjs";

test("OCR whitespace is normalized and blank frames clear subtitles", async () => {
  assert.equal(normalizeText(" Hello\n world  "), "Hello world");
  const session = new TranslationSession(() => { throw new Error("should not translate"); });
  assert.equal(await session.read("\n ", "en"), null);
});
test("repeated subtitles are translated once, language changes use separate keys", async () => {
  const calls = [];
  const session = new TranslationSession(async (text, source) => {
    calls.push([text, source]); return "คำแปล";
  });
  assert.equal((await session.read("Hello\nworld", "en")).translated, "คำแปล");
  await session.read("Hello world ", "en");
  await session.read("Hello world", "ja");
  assert.equal(calls.length, 2);
});
test("failed translations are retried, never cached", async () => {
  let calls = 0;
  const session = new TranslationSession(async () => {
    if (++calls === 1) throw new Error("offline");
    return "สวัสดี";
  });
  await assert.rejects(session.read("Hello", "en"), /offline/);
  assert.equal((await session.read("Hello", "en")).translated, "สวัสดี");
});
test("large OCR output is rejected before inference; cache stays bounded", async () => {
  const session = new TranslationSession(async text => text);
  await assert.rejects(session.read("a".repeat(2001), "en"), /มากเกินไป/);
  for (let i = 0; i < 101; i++) await session.read(String(i), "en");
  assert.equal(session.cache.size, 100);
  assert.equal(session.cache.has("en:0"), false);
});

test("browser controller handles capture, practice, popup and cleanup", async () => {
  class Element {
    constructor() { this.value = ""; this.textContent = ""; this.checked = false; this.handlers = {}; this.children = []; this.style = {}; }
    addEventListener(name, fn) { this.handlers[name] = fn; }
    append(...children) { this.children.push(...children); }
    prepend(child) { this.children.unshift(child); }
    replaceChildren() { this.children = []; }
    getContext() { return { drawImage() {} }; }
    async play() {}
  }
  const elements = new Map();
  const document = {
    getElementById(id) { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); },
    createElement() { return new Element(); },
  };
  const e = id => document.getElementById(id);
  e("source").value = "en"; e("region").value = "bottom"; e("interval").value = "1000";
  Object.assign(e("video"), { readyState: 2, videoWidth: 1920, videoHeight: 1080 });
  let timer, stopped = 0, terminated = 0, requests = 0, recognitions = 0;
  const track = { stop() { stopped++; }, addEventListener() {} };
  const popupElements = new Map();
  const popupDocument = {
    body: new Element(), createElement() { return new Element(); },
    getElementById(id) {
      return this.body.children.find(child => child.id === id);
    },
  };
  const popup = { document: popupDocument, closed: false, close() { this.closed = true; } };
  const originals = new Map();
  function install(key, value) {
    originals.set(key, Object.getOwnPropertyDescriptor(globalThis, key));
    Object.defineProperty(globalThis, key, { value, configurable: true, writable: true });
  }
  install("document", document);
  install("window", {
    Tesseract: { async createWorker() { return {
      async recognize() { recognitions++; return { data: { confidence: 95, text: "Hello world" } }; },
      async terminate() { terminated++; },
    }; } },
    addEventListener() {}, open() { return popup; },
  });
  install("navigator", { mediaDevices: { async getDisplayMedia() { return { getTracks: () => [track], getVideoTracks: () => [track] }; } } });
  install("fetch", async () => { requests++; return { ok: true, async json() { return { translated: "สวัสดีโลก" }; } }; });
  install("setTimeout", fn => { timer = fn; return 1; });
  install("clearTimeout", () => {});
  const flush = async () => { for (let i = 0; i < 20; i++) await Promise.resolve(); };
  try {
    await import("../app/static/stream.mjs");
    e("popup").handlers.click();
    e("practice").checked = true;
    await e("start").handlers.click();
    await flush();
    assert.equal(e("original").textContent, "Hello world");
    assert.equal(e("caption").textContent, "Hello world");
    assert.equal(popupDocument.getElementById("text").textContent, "Hello world");
    assert.equal(requests, 1);
    timer(); await flush();
    assert.equal(recognitions, 1, "practice must freeze current sentence");
    e("reveal").handlers.click();
    assert.equal(e("answer").textContent, "สวัสดีโลก");
    e("save").handlers.click();
    assert.equal(e("saved").children.length, 1);
    e("next").handlers.click();
    timer(); await flush();
    assert.equal(recognitions, 2);
    assert.equal(requests, 1, "same subtitle comes from cache");
    e("stop").handlers.click();
    await flush();
    assert.equal(stopped, 1);
    assert.equal(terminated, 1);
    assert.equal(e("video").srcObject, null);
    assert.equal(e("start").disabled, false);
    assert.equal(e("caption").textContent, "รอข้อความจากเกม");
  } finally {
    for (const [key, descriptor] of originals) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else delete globalThis[key];
    }
  }
});
