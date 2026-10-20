import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { AuthRequest } from "../../types/auth";
import { VoidedAuthorizationsPage } from "../VoidedAuthorizationsPage";

vi.mock("../../components/DataTable", () => ({
  DataTable: ({ data, onRestore, onDelete }: {
    data: AuthRequest[];
    onRestore?: (r: AuthRequest) => void;
    onDelete?: (r: AuthRequest) => void;
  }) => <div data-testid="voided-results">
    {data.map((r) => <div key={r.id}>
      {r.patientId}
      {onRestore && <button onClick={() => onRestore(r)}>Restore {r.patientId}</button>}
      {onDelete && <button onClick={() => onDelete(r)}>Delete {r.patientId}</button>}
    </div>)}
  </div>,
}));

function record(id: string, name: string, facility: string, loc: string, voidedAt: string, isVoided = true): AuthRequest {
  return {
    id, patientId: name, facility, loc, isVoided, voidedAt,
    date: new Date("2026-09-01"), dateStr: "2026-09-01",
    memberId: "", authNumber: "", groupNumber: "", dateOfBirth: "",
    payer: "Test Payer", status: "Pending", requestedDays: 0,
    approvedDays: 0, urSpecialist: "Unassigned",
  };
}

const records = [
  record("1", "Alpha Patient", "Facility A", "RTC", "2026-10-05T12:00:00Z"),
  record("2", "Beta Patient", "Facility B", "PHP", "2026-10-19T12:00:00Z"),
  record("3", "Active Patient", "Facility A", "RTC", "", false),
];

describe("VoidedAuthorizationsPage", () => {
  it("filters by name, facility, LOC, and void date", () => {
    render(<VoidedAuthorizationsPage records={records} darkMode={false} isAdmin={false}
      onView={vi.fn()} onRestore={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.getByText("Alpha Patient")).toBeTruthy();
    expect(screen.getByText("Beta Patient")).toBeTruthy();
    expect(screen.queryByText("Active Patient")).toBeNull();
    fireEvent.change(screen.getByLabelText("Search voided authorizations"), { target: { value: "Beta" } });
    expect(screen.queryByText("Alpha Patient")).toBeNull();
    expect(screen.getByText("Beta Patient")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Search voided authorizations"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Facility"), { target: { value: "Facility A" } });
    expect(screen.queryByText("Beta Patient")).toBeNull();
    fireEvent.change(screen.getByLabelText("Facility"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Level of care"), { target: { value: "PHP" } });
    expect(screen.queryByText("Alpha Patient")).toBeNull();
    fireEvent.change(screen.getByLabelText("Level of care"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-10-10" } });
    expect(screen.queryByText("Alpha Patient")).toBeNull();
    expect(screen.getByText("Beta Patient")).toBeTruthy();
  });

  it("only exposes restore and delete actions to Admin", () => {
    const { rerender } = render(<VoidedAuthorizationsPage records={records} darkMode={false} isAdmin={false}
      onView={vi.fn()} onRestore={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.queryByText("Restore Alpha Patient")).toBeNull();
    expect(screen.queryByText("Delete Alpha Patient")).toBeNull();
    rerender(<VoidedAuthorizationsPage records={records} darkMode={false} isAdmin
      onView={vi.fn()} onRestore={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.getByText("Restore Alpha Patient")).toBeTruthy();
    expect(screen.getByText("Delete Alpha Patient")).toBeTruthy();
  });
});
