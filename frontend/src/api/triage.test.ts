import { describe, expect, it } from "vitest";
import { isFirstPass, missedVocabCsv, timerColor, type ItemResult } from "./triage";

describe("soft timer", () => {
  it("turns amber at the target and red 30 s past it", () => {
    expect(timerColor(49, 50)).toBe("normal");
    expect(timerColor(50, 50)).toBe("amber");
    expect(timerColor(79, 50)).toBe("amber");
    expect(timerColor(80, 50)).toBe("red");
  });
});

describe("first pass", () => {
  it("counts answers kept from the first visit", () => {
    expect(isFirstPass("B", undefined)).toBe(true); // never left the question
    expect(isFirstPass("B", "B")).toBe(true);
    expect(isFirstPass("C", "B")).toBe(false); // changed on a later visit
    expect(isFirstPass("B", null)).toBe(false); // skipped, answered later
  });
});

describe("Anki export", () => {
  const vocab = (word: string) => ({ word, pos: "verb", meaning_en: "to stop, restrain", meaning_ru: "сдерживать", example: 'He said "stop".' });
  const item = (correct: boolean, words: string[]) => ({ correct, vocab: words.map(vocab) }) as unknown as ItemResult;

  it("lists each missed word once, CSV-escaped", () => {
    const csv = missedVocabCsv([item(false, ["check", "survey"]), item(true, ["arrest"]), item(false, ["Check"])])!;
    const lines = csv.trim().split("\n");
    expect(lines[0]).toBe("word,part_of_speech,meaning_en,meaning_ru,example_sentence");
    expect(lines.slice(1).map((l) => l.split(",")[0])).toEqual(["check", "survey"]);
    expect(lines[1]).toBe('check,verb,"to stop, restrain",сдерживать,"He said ""stop""."');
  });

  it("returns null when no words-in-context question was missed", () => {
    expect(missedVocabCsv([item(true, ["check"]), item(false, [])])).toBeNull();
  });
});
