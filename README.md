# MADLAD / Qwen Translation API

FastAPI translator with **selectable MADLAD or experimental Qwen** backends.
The default remains MADLAD. Both backends preserve the existing NestJS
`/v1/translate` and `/v1/translate/batch` API contracts.

## Layout

## แปลเกม / สตรีม และฝึกภาษาอังกฤษ

หลังเปิดเซิร์ฟเวอร์ ไปที่ **http://localhost:8000/stream**

1. เลือก English หรือ Japanese → ไทย และบริเวณซับไตเติล (ล่าง 35%) หรือทั้งภาพ
2. กด **เลือกเกม / สตรีม** แล้วอนุญาตแชร์หน้าต่างเกมหรือแท็บวิดีโอ
3. คำแปลจะแสดงบนภาพตัวอย่าง กด **เปิดป๊อปอัปคำแปล** เพื่อแยกหน้าต่าง
4. เปิด **ซ่อนคำแปล ให้ลองแปลก่อน** เพื่อฝึกอังกฤษ: อ่านประโยค เขียนคำแปล
   ฟังเสียง แล้วกดเฉลย เปรียบเทียบด้วยตัวเอง (ไม่มีการให้คะแนนอัตโนมัติ)
5. โหมดฝึกจะหยุดรับประโยคใหม่จนกด **ประโยคถัดไป**;
   เก็บประโยคไว้ทบทวนแบบพับเฉลยได้ สูงสุด 100 ประโยค รีเฟรชแล้วรายการจะหาย
6. กด **หยุด** หรือหยุดแชร์จากเบราว์เซอร์ เพื่อปิด capture และ OCR

### ข้อกำหนดและข้อจำกัด

- ใช้ desktop Chrome/Edge บน localhost หรือ HTTPS; ต้องอนุญาตแชร์ภาพทุกครั้ง
  ([Screen Capture API](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia)).
- OCR ใช้ [Tesseract.js](https://github.com/naptha/tesseract.js) 5.1.1 ในเบราว์เซอร์
  โหลด library/worker/โมเดลภาษาผ่าน CDN จึงต้องมีอินเทอร์เน็ตครั้งแรก
  ภาพไม่ถูกส่งไป API; ส่งเฉพาะข้อความไปยัง translation provider ที่ตั้งไว้
- ใช้ API เดิม `/v1/translate` และรองรับทั้ง MADLAD / Qwen โดยไม่เปลี่ยนสัญญา API
- ทำงานแบบอ่านภาพต่อเนื่อง (near real time): จบรอบ OCR+แปลแล้วพักตามค่าที่เลือก
  ไม่ใช่รับประกันคำแปลทุก 0.5 วินาที ความหน่วงขึ้นกับเครื่อง โมเดล และข้อความ
  ไม่ส่งหลายเฟรมซ้อนกัน มี cache 100 ข้อความต่อ session และ timeout API 180 วินาที
- ป๊อปอัปเป็นหน้าต่างเบราว์เซอร์ ไม่ใช่ native always-on-top overlay:
  เกม exclusive fullscreen อาจบังหน้าต่าง ใช้โหมด windowed/borderless
  และจัดวางหน้าต่างข้างกันหรือจอที่สอง (ยังไม่ได้ทดสอบกับเกมจริงทุกชนิด)
- เลือกแชร์เฉพาะเกม/แท็บสตรีม ไม่รวมหน้าต่างคำแปล เพื่อหลีกเลี่ยง OCR อ่านตัวเอง
  ภาพป้องกันการจับภาพ/DRM อาจเป็นสีดำ ตัวอักษรเล็กหรือพื้นหลังซับซ้อนอาจอ่านผิด
- เสียงอ่านใช้เสียงอังกฤษที่มีในระบบ/เบราว์เซอร์ โหมดฝึกอังกฤษใช้ source=en
- ไม่มีการบันทึกภาพหรือประโยคถาวร; คำแปลจากโมเดลใช้เป็นแนวทางฝึก ไม่ใช่เฉลยที่รับประกัน

### Tests

```sh
python -m pip install fastapi httpx pydantic-settings
python -m unittest discover -s tests -v
node --test tests/stream.test.mjs
```

Tests mock the OCR/translation engines and screen capture; they verify cache, retries,
study mode, popup rendering, cleanup and static routes without downloading model weights.
For a manual smoke test, share an English subtitle video, verify Thai captions and popup,
enable practice and reveal an answer, then stop sharing and confirm capture ends.

## Backend layout

- `app/services/madlad.py`: original MADLAD backend
- `app/experimental/qwen/`: Qwen via Ollama and its Thai subtitle prompt
- `experiments/translation_comparison/`: repeatable translation comparisons
- `app/main.py`: creates only the selected provider

## Configure in .env

Copy `.env.example` to `.env` (Windows CMD: `copy .env.example .env`).

For the current MADLAD model:

```env
TRANSLATION_PROVIDER=madlad
```

To test Qwen (no MADLAD model weights are loaded):

```env
TRANSLATION_PROVIDER=qwen
QWEN_MODEL=qwen3.5:4b
QWEN_BASE_URL=http://host.docker.internal:11434
```

**Restart FastAPI every time you switch providers.** For Qwen mode,
install and run Ollama on your Windows host first:

```powershell
ollama pull qwen3.5:4b
ollama list
```

Docker Desktop reaches host Ollama via `host.docker.internal:11434`.
If FastAPI runs directly on Windows, use
`QWEN_BASE_URL=http://localhost:11434` instead.
The API checks Ollama and model availability at startup. It never
downloads the model automatically.

## Docker

```powershell
docker compose up -d --build
docker compose logs -f madlad-api
```

The provided compose uses NVIDIA GPU support and retains a Hugging Face
cache volume for MADLAD. Ollama is a **separate host application** and is
not launched by this compose file.

Check which model is active:

```powershell
curl.exe http://localhost:8000/ready
```

Expected `provider`: `madlad` or `qwen`. The `model` field reflects
the selection, and `ready` indicates the provider initialized.

## Test a translation (Windows CMD)

```cmd
curl.exe -X POST "http://localhost:8000/v1/translate" -H "Content-Type: application/json" -d "{\"text\":\"I might have an idea of it.\",\"source\":\"en\",\"target\":\"th\"}"
```

Both providers support source `en` and `ja`, destination `th`, and
`max_new_tokens`. The `num_beams` request field is accepted but
**ignored by Qwen** because Ollama does not expose MADLAD's beam search.
Batch requests are executed sequentially in Qwen mode to minimize VRAM use.

## Compare translations

See `experiments/translation_comparison/README.md`. Generate saved
output once with each backend, then print both versions side by side.

Notes:
- MADLAD limits input by `MAX_INPUT_TOKENS`; Qwen instead uses
  `QWEN_MAX_INPUT_CHARS` (different units).
- Qwen's `device=ollama` identifies the backend, not a GPU claim.
- Output quality is not guaranteed; compare real EN/JA subtitle lines.
- The NestJS subtitle alignment and timestamps are unchanged.

