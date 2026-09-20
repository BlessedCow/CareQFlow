import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AuthRequest } from "../../../types/auth";
import { FollowUpDashboard } from "../FollowUpDashboard";
import { getFollowUpItems, type FollowUpListItem } from "../followUpModels";

function auth(
  overrides: Partial<AuthRequest> & Pick<AuthRequest, "id" | "patientId">
): AuthRequest {
  const { id, patientId, ...rest } = overrides;

  return {
    memberId: `MEM-${id}`,
    authNumber: `AUTH-${id}`,
    groupNumber: "",
    dateOfBirth: "1990-01-01",
    date: new Date("2026-09-01T00:00:00"),
    dateStr: "2026-09-01",
    facility: "Default Facility",
    payer: "Default Insurance",
    loc: "RTC",
    status: "Approved",
    requestedDays: 5,
    approvedDays: 5,
    urSpecialist: "Test User",
    ...rest,
    id,
    patientId,
  };
}

const deniedAuth = auth({
  id: "1",
  patientId: "Denial Client",
  facility: "Clearpath Recovery Institute",
  payer: "Aetna Behavioral Health",
  loc: "RTC",
  status: "Denied",
  approvedDays: 0,
  denialDate: "2026-09-10",
  denialThroughDate: "2026-09-12",
  denialReasonCategory: "Not Medically Necessary",
  denialSource: "Concurrent Auth",
});

const p2pAuth = auth({
  id: "2",
  patientId: "P2P Client",
  facility: "Aura Horizon Recovery Center",
  payer: "Optum Behavioral Health",
  insurancePlan: "Optum Choice",
  loc: "DTX",
  status: "Approved",
  p2pRequested: true,
  p2pScheduledAt: "2026-09-15T14:00:00",
  p2pDeadline: "2026-09-16",
  p2pOutcome: "Overturned",
});

const appealAuth = auth({
  id: "3",
  patientId: "Appeal Client",
  facility: "Pinecrest Behavioral Health",
  payer: "Carelon Behavioral Health",
  loc: "PHP",
  status: "Denied",
  approvedDays: 0,
  denialDate: "2026-09-17",
  denialReasonCategory: "Lower LOC Recommended",
  denialSource: "Concurrent Auth",
  appealSubmitted: true,
  appealDeadline: "2026-09-20",
  appealOutcome: "Pending",
});

const retroAuth = auth({
  id: "4",
  patientId: "Retro Client",
  facility: "Serenoa Healing Center",
  payer: "Humana Behavioral Health",
  loc: "IOP",
  status: "Approved",
  retroRequested: true,
  retroDeadline: "2026-09-25",
  retroOutcome: "Pending",
});

const data = [deniedAuth, p2pAuth, appealAuth, retroAuth];

function renderDashboard(
  followUpItems: FollowUpListItem[] = getFollowUpItems(data)
) {
  const onSelectAuth = vi.fn();

  render(
    <FollowUpDashboard
      data={data}
      darkMode={false}
      selectedAuth={null}
      followUpItems={followUpItems}
      onSelectAuth={onSelectAuth}
    />
  );

  return { onSelectAuth };
}

describe("FollowUpDashboard", () => {
  it("shows current workflow counts", () => {
    renderDashboard();

    expect(
      screen.getByRole("button", { name: /Denials 2/i })
    ).toBeInTheDocument();

    expect(screen.getByRole("button", { name: /P2P 1/i })).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: /Appeals 1/i })
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: /Retro Auths 1/i })
    ).toBeInTheDocument();
  });

  it("filters by one summary card and deselects it on second click", () => {
    renderDashboard();

    const denialCard = screen.getByRole("button", {
      name: /Denials 2/i,
    });

    fireEvent.click(denialCard);

    expect(denialCard).toHaveAttribute("aria-pressed", "true");

    expect(screen.getByText("Denial: Denial Client")).toBeInTheDocument();
    expect(screen.getByText("Denial: Appeal Client")).toBeInTheDocument();

    expect(screen.queryByText("P2P: P2P Client")).not.toBeInTheDocument();
    expect(screen.queryByText("Appeal: Appeal Client")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Retro Auth: Retro Client")
    ).not.toBeInTheDocument();

    fireEvent.click(denialCard);

    expect(denialCard).toHaveAttribute("aria-pressed", "false");

    expect(screen.getByText("P2P: P2P Client")).toBeInTheDocument();
    expect(screen.getByText("Appeal: Appeal Client")).toBeInTheDocument();
    expect(screen.getByText("Retro Auth: Retro Client")).toBeInTheDocument();
  });

  it("supports selecting multiple summary cards", () => {
    renderDashboard();

    fireEvent.click(
      screen.getByRole("button", {
        name: /P2P 1/i,
      })
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: /Appeals 1/i,
      })
    );

    expect(screen.getByText("P2P: P2P Client")).toBeInTheDocument();
    expect(screen.getByText("Appeal: Appeal Client")).toBeInTheDocument();

    expect(screen.queryByText("Denial: Denial Client")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Retro Auth: Retro Client")
    ).not.toBeInTheDocument();
  });

  it("searches client, facility, insurance, insurance plan, and LOC", () => {
    renderDashboard();

    const search = screen.getByPlaceholderText(
      "Search client, facility, insurance, or LOC"
    );

    fireEvent.change(search, {
      target: { value: "P2P Client" },
    });

    expect(screen.getByText("P2P: P2P Client")).toBeInTheDocument();
    expect(screen.queryByText("Denial: Denial Client")).not.toBeInTheDocument();

    fireEvent.change(search, {
      target: { value: "Clearpath" },
    });

    expect(screen.getByText("Denial: Denial Client")).toBeInTheDocument();
    expect(screen.queryByText("P2P: P2P Client")).not.toBeInTheDocument();

    fireEvent.change(search, {
      target: { value: "Optum Choice" },
    });

    expect(screen.getByText("P2P: P2P Client")).toBeInTheDocument();
    expect(screen.queryByText("Denial: Denial Client")).not.toBeInTheDocument();

    fireEvent.change(search, {
      target: { value: "IOP" },
    });

    expect(screen.getByText("Retro Auth: Retro Client")).toBeInTheDocument();
    expect(screen.queryByText("P2P: P2P Client")).not.toBeInTheDocument();
  });

  it("filters follow-up work by due-date range", () => {
    renderDashboard();

    const dateInputs = screen.getAllByDisplayValue("");

    const startDate = dateInputs.find(
      (input) => input.getAttribute("type") === "date"
    );

    const endDate = dateInputs
      .filter((input) => input.getAttribute("type") === "date")
      .at(1);

    expect(startDate).toBeDefined();
    expect(endDate).toBeDefined();

    fireEvent.change(startDate!, {
      target: { value: "2026-09-15" },
    });

    fireEvent.change(endDate!, {
      target: { value: "2026-09-20" },
    });

    expect(screen.getByText("P2P: P2P Client")).toBeInTheDocument();
    expect(screen.getByText("Denial: Appeal Client")).toBeInTheDocument();
    expect(screen.getByText("Appeal: Appeal Client")).toBeInTheDocument();

    expect(screen.queryByText("Denial: Denial Client")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Retro Auth: Retro Client")
    ).not.toBeInTheDocument();
  });

  it("shows the empty filtered state when nothing matches", () => {
    renderDashboard();

    fireEvent.change(
      screen.getByPlaceholderText("Search client, facility, insurance, or LOC"),
      {
        target: { value: "does not exist" },
      }
    );

    expect(screen.getByText("No matching items")).toBeInTheDocument();
    expect(
      screen.getByText("No follow-up items match the current filters.")
    ).toBeInTheDocument();
  });

  it("opens the authorization selected from the work queue", () => {
    const { onSelectAuth } = renderDashboard();

    fireEvent.click(screen.getByText("P2P: P2P Client"));

    expect(onSelectAuth).toHaveBeenCalledTimes(1);
    expect(onSelectAuth).toHaveBeenCalledWith(p2pAuth);
  });
});
