import { act, render, screen } from "@testing-library/react";
import { ServerGate } from "./ServerGate";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

test("shows waking-up screen while the server boots, then renders the app", async () => {
  vi.useFakeTimers();
  const fetchMock = vi
    .fn()
    .mockRejectedValueOnce(new TypeError("network"))
    .mockResolvedValueOnce(new Response(null, { status: 502 }))
    .mockResolvedValue(new Response("{}", { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  render(<ServerGate>app content</ServerGate>);
  await act(() => vi.advanceTimersByTimeAsync(1600));
  expect(screen.getByText("Waking up the server…")).toBeInTheDocument();
  expect(screen.queryByText("app content")).not.toBeInTheDocument();

  await act(() => vi.advanceTimersByTimeAsync(6000));
  expect(screen.getByText("app content")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(3);
});

test("fast server skips the wake-up screen", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 200 })));
  render(<ServerGate>app content</ServerGate>);
  expect(await screen.findByText("app content")).toBeInTheDocument();
});
