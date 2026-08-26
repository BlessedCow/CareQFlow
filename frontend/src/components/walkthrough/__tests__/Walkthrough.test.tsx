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

    expect(screen.getByText("Step 1 of 21")).toBeInTheDocument();
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

    expect(onPageChange).toHaveBeenCalledWith("settings");
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

  it("requires the highlighted action before continuing", async () => {
    const facilitiesCard = document.createElement("div");
    facilitiesCard.dataset.walkthrough = "registered-facilities";
    facilitiesCard.dataset.walkthroughCount = "1";
    document.body.appendChild(facilitiesCard);

    const insurancesCard = document.createElement("div");
    insurancesCard.dataset.walkthrough = "registered-insurances";
    insurancesCard.dataset.walkthroughCount = "1";
    document.body.appendChild(insurancesCard);

    const addAuthorizationButton = document.createElement("button");
    addAuthorizationButton.dataset.walkthrough = "add-authorization";
    addAuthorizationButton.textContent = "Add Authorization";
    document.body.appendChild(addAuthorizationButton);

    renderWalkthrough();

    const advance = () => {
      fireEvent.click(
        screen.getByRole("button", {
          name: "Next",
        })
      );
    };

    advance();

    expect(
      screen.getByRole("heading", {
        name: "Dashboard",
      })
    ).toBeInTheDocument();

    advance();

    expect(
      screen.getByRole("heading", {
        name: "Settings",
      })
    ).toBeInTheDocument();

    advance();

    await waitFor(() => {
      expect(
        screen.getByText("This section is configured. Press Next to continue.")
      ).toBeInTheDocument();
    });

    advance();

    await waitFor(() => {
      expect(
        screen.getByText("This section is configured. Press Next to continue.")
      ).toBeInTheDocument();
    });

    advance();

    expect(
      screen.getByRole("heading", {
        name: "Web Portals",
      })
    ).toBeInTheDocument();

    advance();

    expect(
      screen.getByRole("heading", {
        name: "Authorizations",
      })
    ).toBeInTheDocument();

    advance();

    expect(
      screen.getByRole("heading", {
        name: "Add an authorization",
      })
    ).toBeInTheDocument();

    const nextButton = screen.getByRole("button", {
      name: "Next",
    });

    expect(nextButton).toBeDisabled();

    fireEvent.click(addAuthorizationButton);

    expect(
      screen.getByText("Step completed. Press Next to continue.")
    ).toBeInTheDocument();

    expect(nextButton).toBeEnabled();

    facilitiesCard.remove();
    insurancesCard.remove();
    addAuthorizationButton.remove();
  });

  it("unlocks a configuration step when an item is added", async () => {
    const addAuthorizationButton = document.createElement("button");
    addAuthorizationButton.dataset.walkthrough = "add-authorization";
    document.body.appendChild(addAuthorizationButton);

    const facilitiesCard = document.createElement("div");
    facilitiesCard.dataset.walkthrough = "registered-facilities";
    facilitiesCard.dataset.walkthroughCount = "0";
    document.body.appendChild(facilitiesCard);

    renderWalkthrough();

    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    fireEvent.click(addAuthorizationButton);

    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(
      screen.getByRole("heading", {
        name: "Add your facilities",
      })
    ).toBeInTheDocument();

    const nextButton = screen.getByRole("button", {
      name: "Next",
    });

    expect(nextButton).toBeDisabled();

    facilitiesCard.dataset.walkthroughCount = "1";

    await waitFor(() => {
      expect(nextButton).toBeEnabled();
    });

    expect(
      screen.getByText("This section is configured. Press Next to continue.")
    ).toBeInTheDocument();

    addAuthorizationButton.remove();
    facilitiesCard.remove();
  });
});
