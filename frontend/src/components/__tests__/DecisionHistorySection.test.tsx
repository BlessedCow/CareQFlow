import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchAuthDecisionSnapshots } from "../../api/authDecisionSnapshots";
import { DecisionHistorySection } from "../DecisionHistorySection";

vi.mock("../../api/authDecisionSnapshots", () => ({
  fetchAuthDecisionSnapshots: vi.fn(),
}));

const mockedFetchAuthDecisionSnapshots = vi.mocked(
  fetchAuthDecisionSnapshots
);

describe("DecisionHistorySection", () => {
  beforeEach(() => {
    mockedFetchAuthDecisionSnapshots.mockReset();
  });

  it("renders root and follow-up decision lineage", async () => {
    mockedFetchAuthDecisionSnapshots.mockResolvedValue([
      {
        id: 10,
        auth_id: 1,
        auth_event_id: 2,
        facility: "Facility A",
        insurance: "Payer A",
        insurance_plan: "Gold",
        loc: "RTC",
        auth_type: "Concurrent",
        outcome: "Denied",
        requested_days: 5,
        approved_days: 0,
        denied_days: 5,
        decision_at: "2026-09-01T12:00:00+00:00",
        denial_reason_category: "Medical Necessity",
        denial_source: "Payer Review",
        days_at_current_loc: 10,
        total_treatment_days: 10,
        source: "automatic",
        snapshot_role: "root",
        review_type: "concurrent",
        parent_snapshot_id: null,
        root_snapshot_id: 10,
        follow_up_decision_at: null,
        reviewed_from: null,
        reviewed_to: null,
        reviewed_loc: null,
        retro_reason: null,
        context_derivation_version: 2,
        context_provenance: "loc_episode",
        created_at: "2026-09-01T12:00:00+00:00",
        updated_at: "2026-09-01T12:00:00+00:00",
      },
      {
        id: 11,
        auth_id: 1,
        auth_event_id: 3,
        facility: "Facility A",
        insurance: "Payer A",
        insurance_plan: "Gold",
        loc: "RTC",
        auth_type: "Concurrent",
        outcome: "P2P Overturned",
        requested_days: 5,
        approved_days: 0,
        denied_days: 5,
        decision_at: "2026-09-01T12:00:00+00:00",
        denial_reason_category: "Medical Necessity",
        denial_source: "Payer Review",
        days_at_current_loc: 10,
        total_treatment_days: 10,
        source: "automatic",
        snapshot_role: "follow_up",
        review_type: "p2p",
        parent_snapshot_id: 10,
        root_snapshot_id: 10,
        follow_up_decision_at: "2026-09-03T15:00:00+00:00",
        reviewed_from: null,
        reviewed_to: null,
        reviewed_loc: null,
        retro_reason: null,
        context_derivation_version: 2,
        context_provenance: "inherited_root",
        created_at: "2026-09-03T15:00:00+00:00",
        updated_at: "2026-09-03T15:00:00+00:00",
      },
    ]);

    render(
      <DecisionHistorySection
        authId="1"
        darkMode={false}
      />
    );

    expect(
      await screen.findByText("Decision History")
    ).toBeInTheDocument();

    expect(screen.getAllByText("Denied").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("P2P Overturned")).toBeInTheDocument();
    expect(screen.getByText("Peer to Peer")).toBeInTheDocument();
    expect(screen.getByText("Parent decision #10")).toBeInTheDocument();

    expect(mockedFetchAuthDecisionSnapshots).toHaveBeenCalledWith(
      "1"
    );
  });

  it("shows an empty state when no decisions exist", async () => {
    mockedFetchAuthDecisionSnapshots.mockResolvedValue([]);

    render(
      <DecisionHistorySection
        authId="1"
        darkMode={false}
      />
    );

    expect(
      await screen.findByText(
        "No immutable decision snapshots recorded yet."
      )
    ).toBeInTheDocument();
  });
});