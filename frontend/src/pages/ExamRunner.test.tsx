import { ApiError } from "../api/client";
import * as exam from "../api/exam";
import { Autosave } from "./ExamRunner";

const state = { answer: "A", flagged: false, eliminated: [], time_ms: 10 };

afterEach(() => vi.restoreAllMocks());

test("autosave retries after a network error", async () => {
  vi.useFakeTimers();
  const save = vi.spyOn(exam, "saveItem").mockRejectedValueOnce(new TypeError("offline")).mockResolvedValue(undefined);
  const statuses: string[] = [];
  const s = new Autosave(1, (x) => statuses.push(x), () => {});
  await s.save(7, state);
  expect(statuses.at(-1)).toBe("offline");
  expect(s.unsaved()).toBe(1);
  await vi.advanceTimersByTimeAsync(3000); // automatic retry
  expect(save).toHaveBeenCalledTimes(2);
  expect(statuses.at(-1)).toBe("saved");
  expect(s.unsaved()).toBe(0);
  s.dispose();
  vi.useRealTimers();
});

test("autosave reports a server-closed module and drops bad entries", async () => {
  const onClosed = vi.fn();
  vi.spyOn(exam, "saveItem").mockRejectedValueOnce(new ApiError(422, "bad")).mockRejectedValueOnce(new ApiError(409, "closed"));
  const s = new Autosave(1, () => {}, onClosed);
  void s.save(1, state);
  await s.save(2, state);
  expect(onClosed).toHaveBeenCalledOnce();
  expect(s.unsaved()).toBe(0);
});
