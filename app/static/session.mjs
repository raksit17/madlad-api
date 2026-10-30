export function normalizeText(text) {
  return text.replace(/\s+/g, " ").trim();
}

// A bounded, per-capture cache: never share translations between sessions.
export class TranslationSession {
  constructor(translate) {
    this.translate = translate;
    this.cache = new Map();
  }
  async read(raw, source) {
    const text = normalizeText(raw);
    if (!text) return null;
    if (text.length > 2000) throw new Error("ข้อความมากเกินไป กรุณาเลือกบริเวณซับไตเติล");
    const key = source + ":" + text;
    if (this.cache.has(key)) return this.cache.get(key);
    const translated = await this.translate(text, source);
    const result = { original: text, translated, source };
    this.cache.set(key, result);
    if (this.cache.size > 100) this.cache.delete(this.cache.keys().next().value);
    return result;
  }
}
