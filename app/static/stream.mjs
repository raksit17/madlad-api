import { TranslationSession } from "./session.mjs";

const el = Object.fromEntries(["source", "region", "interval", "start", "stop",
  "popup", "status", "video", "caption", "practice", "original", "attempt",
  "reveal", "listen", "next", "answer", "save", "saved"].map(id => [id, document.getElementById(id)]));
let active = null, popup = null, current = null, revealed = false;
const saved = new Set();
const status = text => { el.status.textContent = text; };

function render() {
  const hidden = el.practice.checked && !revealed;
  el.original.textContent = current?.original || "รอข้อความจากเกม";
  el.answer.textContent = hidden ? "ลองแปลก่อน แล้วกดเฉลย" : current?.translated || "";
  el.caption.textContent = hidden ? current?.original || "รอข้อความจากเกม" : current?.translated || "รอข้อความจากเกม";
  if (popup && !popup.closed) {
    popup.document.getElementById("text").textContent = el.caption.textContent;
    popup.document.getElementById("original").textContent = current?.original || "";
  }
}

async function translate(text, source, session) {
  const controller = new AbortController();
  session.request = controller;
  const timeout = setTimeout(() => controller.abort(), 180000);
  try {
    const response = await fetch("/v1/translate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, source, target: "th", num_beams: 1 }),
      signal: controller.signal,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "แปลไม่สำเร็จ (" + response.status + ")");
    if (typeof data.translated !== "string" || !data.translated.trim()) throw new Error("API ส่งคำแปลว่าง");
    return data.translated;
  } finally {
    clearTimeout(timeout);
    session.request = null;
  }
}

function stop() {
  const session = active;
  active = null;
  if (session) {
    clearTimeout(session.timer);
    session.request?.abort();
    session.stream?.getTracks().forEach(track => track.stop());
    if (session.worker) void session.worker.terminate().catch(() => {});
  }
  el.video.srcObject = null;
  el.start.disabled = false;
  el.stop.disabled = true;
  el.source.disabled = false;
  current = null;
  revealed = false;
  el.attempt.value = "";
  window.speechSynthesis?.cancel();
  render();
  status("หยุดการแชร์และแปลแล้ว");
}

async function tick(session) {
  if (active !== session) return;
  try {
    // Freeze the study card until the learner explicitly asks for another sentence.
    if (!(el.practice.checked && current) && el.video.readyState >= 2) {
      const started = performance.now();
      const video = el.video;
      const bottom = el.region.value === "bottom";
      const y = bottom ? Math.floor(video.videoHeight * .65) : 0;
      const height = video.videoHeight - y;
      const scale = Math.min(1, 1920 / video.videoWidth);
      session.canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
      session.canvas.height = Math.max(1, Math.round(height * scale));
      session.canvas.getContext("2d").drawImage(video, 0, y, video.videoWidth, height,
        0, 0, session.canvas.width, session.canvas.height);
      status("กำลังอ่านข้อความจากภาพ…");
      const { data } = await session.worker.recognize(session.canvas);
      if (active !== session) return;
      // Low confidence / empty frames must clear old subtitles.
      const text = data.confidence >= 35 ? data.text : "";
      status("กำลังแปล…");
      const result = await session.translations.read(text, session.source);
      if (active !== session) return;
      if (result?.original !== current?.original) {
        revealed = false;
        el.attempt.value = "";
      }
      current = result;
      render();
      status(result ? "แปลแล้ว • " + ((performance.now() - started) / 1000).toFixed(1) + " วินาที" : "ยังไม่พบข้อความที่อ่านได้");
    }
  } catch (error) {
    if (active !== session) return;
    current = null;
    render();
    status("อ่าน/แปลไม่สำเร็จ: " + error.message + " — จะลองใหม่อัตโนมัติ");
  } finally {
    // Schedule after completion, never enqueue stale frames behind slow inference.
    if (active === session) session.timer = setTimeout(() => tick(session), Number(el.interval.value));
  }
}

el.start.addEventListener("click", async () => {
  if (!navigator.mediaDevices?.getDisplayMedia) {
    status("เบราว์เซอร์นี้แชร์ภาพไม่ได้ กรุณาใช้ Chrome/Edge บน localhost หรือ HTTPS");
    return;
  }
  const session = { source: el.source.value, canvas: document.createElement("canvas") };
  active = session;
  el.start.disabled = true;
  el.stop.disabled = false;
  el.source.disabled = true;
  try {
    // Must be called directly from the user gesture, before loading OCR.
    const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
    if (active !== session) { stream.getTracks().forEach(track => track.stop()); return; }
    session.stream = stream;
    stream.getVideoTracks()[0].addEventListener("ended", () => { if (active === session) stop(); });
    el.video.srcObject = stream;
    await el.video.play();
    if (active !== session) return;
    status("กำลังโหลดตัวอ่านข้อความครั้งแรก…");
    if (!window.Tesseract) throw new Error("โหลด OCR ไม่สำเร็จ ตรวจสอบอินเทอร์เน็ตแล้วรีเฟรช");
    const worker = await window.Tesseract.createWorker(session.source === "ja" ? "jpn" : "eng");
    if (active !== session) { await worker.terminate(); return; }
    session.worker = worker;
    session.translations = new TranslationSession((text, source) => translate(text, source, session));
    void tick(session);
  } catch (error) {
    if (active !== session) return;
    stop();
    status("เริ่มไม่ได้: " + error.message);
  }
});
el.stop.addEventListener("click", stop);
el.region.addEventListener("change", () => { current = null; revealed = false; render(); });
el.practice.addEventListener("change", () => {
  if (el.practice.checked && el.source.value !== "en") {
    el.practice.checked = false;
    status("โหมดฝึกอังกฤษใช้กับ English → ไทย กรุณาหยุดแล้วเปลี่ยนภาษา");
  }
  revealed = false;
  render();
});
el.source.addEventListener("change", () => {
  if (el.source.value !== "en") el.practice.checked = false;
  current = null;
  render();
});
el.reveal.addEventListener("click", () => { revealed = true; render(); });
el.next.addEventListener("click", () => { current = null; revealed = false; el.attempt.value = ""; render(); });
el.listen.addEventListener("click", () => {
  if (!current || current.source !== "en") { status("เลือกประโยคภาษาอังกฤษก่อน"); return; }
  if (!window.speechSynthesis) { status("เบราว์เซอร์นี้ไม่รองรับเสียงอ่าน"); return; }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(current.original);
  utterance.lang = "en-US";
  utterance.rate = .85;
  window.speechSynthesis.speak(utterance);
});
el.save.addEventListener("click", () => {
  if (!current || saved.has(current.original)) return;
  if (saved.size >= 100) { status("เก็บได้สูงสุด 100 ประโยคต่อรอบ"); return; }
  saved.add(current.original);
  const li = document.createElement("li");
  const question = document.createElement("span");
  question.textContent = current.original;
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "เฉลย";
  const answer = document.createElement("p");
  answer.textContent = current.translated;
  details.append(summary, answer);
  li.append(question, details);
  el.saved.prepend(li);
});
el.popup.addEventListener("click", () => {
  if (popup && !popup.closed) { popup.focus(); return; }
  popup = window.open("", "madlad-translation", "popup,width=640,height=260");
  if (!popup) { status("โปรดอนุญาตป๊อปอัปสำหรับเว็บนี้"); return; }
  popup.document.title = "MADLAD • คำแปลสด";
  popup.document.body.replaceChildren();
  popup.document.body.style.cssText = "background:#101827;color:white;font:24px system-ui;padding:20px;white-space:pre-line";
  const original = popup.document.createElement("p");
  original.id = "original";
  original.style.cssText = "font-size:16px;color:#aabbd4";
  const translated = popup.document.createElement("p");
  translated.id = "text";
  popup.document.body.append(original, translated);
  render();
});
window.addEventListener("pagehide", () => { stop(); if (popup && !popup.closed) popup.close(); });
