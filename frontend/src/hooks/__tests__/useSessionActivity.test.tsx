import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { recordSessionActivity } from "../../api/security";
import { useSessionActivity } from "../useSessionActivity";

vi.mock("../../api/security", () => ({
  recordSessionActivity: vi.fn(),
}));

const mockedRecordSessionActivity = vi.mocked(recordSessionActivity);

function SessionActivityHarness({ enabled = true }: { enabled?: boolean }) {
  useSessionActivity(enabled);

  return null;
}

describe("useSessionActivity", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-22T10:00:00.000Z"));

    mockedRecordSessionActivity.mockReset();
    mockedRecordSessionActivity.mockResolvedValue({
      expires_at: "2026-08-22T10:20:00+00:00",
    });
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it("records meaningful browser activity", async () => {
    render(<SessionActivityHarness />);

    window.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "a",
      })
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(mockedRecordSessionActivity).toHaveBeenCalledTimes(1);
  });

  it("throttles repeated activity to once per minute", async () => {
    render(<SessionActivityHarness />);

    window.dispatchEvent(new PointerEvent("pointerdown"));

    await act(async () => {
      await Promise.resolve();
    });

    window.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "a",
      })
    );
    window.dispatchEvent(new WheelEvent("wheel"));

    await act(async () => {
      await Promise.resolve();
    });

    expect(mockedRecordSessionActivity).toHaveBeenCalledTimes(1);

    act(() => {
      vi.advanceTimersByTime(60_000);
    });

    window.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "b",
      })
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(mockedRecordSessionActivity).toHaveBeenCalledTimes(2);
  });

  it("does not record activity when disabled", async () => {
    render(<SessionActivityHarness enabled={false} />);

    window.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "a",
      })
    );
    window.dispatchEvent(new PointerEvent("pointerdown"));
    window.dispatchEvent(new WheelEvent("wheel"));

    await act(async () => {
      await Promise.resolve();
    });

    expect(mockedRecordSessionActivity).not.toHaveBeenCalled();
  });

  it("allows later activity after a failed request", async () => {
    mockedRecordSessionActivity.mockRejectedValueOnce(
      new Error("Request failed.")
    );

    render(<SessionActivityHarness />);

    window.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "a",
      })
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(mockedRecordSessionActivity).toHaveBeenCalledTimes(1);

    act(() => {
      vi.advanceTimersByTime(60_000);
    });

    window.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "b",
      })
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(mockedRecordSessionActivity).toHaveBeenCalledTimes(2);
  });
});
