import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Walkthrough } from "../Walkthrough";
import type { AppPage } from "../../../types/navigation";

function renderWalkthrough({
  onComplete = vi.fn().mockResolvedValue(undefined),
  onSkip = vi.fn().mockResolvedValue(undefined),
  onPageChange = vi.fn(),
}: {
  onComplete?: () => Promise<void>;
  onSkip?: () => Promise<void>;
  onPageChange?: (page: AppPage) => void;
} = {}) {
  render(
    <Walkthrough
      darkMode={false}
      role="UR"
      activePage="dashboard"
      onPageChange={onPageChange}
      onComplete={onComplete}
      onSkip={onSkip}
    />
  );

  return {
    onComplete,
    onSkip,
    onPageChange,
  };
}

describe("Walkthrough", () => {
  it("starts with the welcome step", () => {
    renderWalkthrough();

    expect(
      screen.getByRole("heading", {
        name: "Welcome to CareQueue",
      })
    ).toBeInTheDocument();

    expect(screen.getByText("Step 1 of 13")).toBeInTheDocument();
  });

  it("moves forward and backward through steps", () => {
    renderWalkthrough();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      })
    );

    expect(
      screen.getByRole("heading", {
        name: "Dashboard",
      })
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Back",
      })
    );

    expect(
      screen.getByRole("heading", {
        name: "Welcome to CareQueue",
      })
    ).toBeInTheDocument();
  });

  it("requests the page required by the current step", () => {
    const onPageChange = vi.fn();

    renderWalkthrough({
      onPageChange,
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      })
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      })
    );

    expect(onPageChange).toHaveBeenCalledWith("authorizations");
  });

  it("allows the walkthrough to be skipped", async () => {
    const onSkip = vi.fn().mockResolvedValue(undefined);

    renderWalkthrough({
      onSkip,
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Skip walkthrough",
      })
    );

    await waitFor(() => {
      expect(onSkip).toHaveBeenCalledTimes(1);
    });
  });

  it("shows skip errors without closing the walkthrough", async () => {
    const onSkip = vi
      .fn()
      .mockRejectedValue(new Error("Unable to skip walkthrough."));

    renderWalkthrough({
      onSkip,
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Skip walkthrough",
      })
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unable to skip walkthrough."
    );

    expect(
      screen.getByRole("heading", {
        name: "Welcome to CareQueue",
      })
    ).toBeInTheDocument();
  });
});
