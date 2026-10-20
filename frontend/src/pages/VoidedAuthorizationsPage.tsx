import { useMemo, useState } from "react";
import type { AuthRequest } from "../types/auth";
import { DataTable } from "../components/DataTable";

interface Props {
  records: AuthRequest[];
  darkMode: boolean;
  isAdmin: boolean;
  onRestore: (auth: AuthRequest) => void;
  onDelete: (auth: AuthRequest) => void;
  onView: (auth: AuthRequest) => void;
}

export function VoidedAuthorizationsPage({
  records, darkMode, isAdmin, onRestore, onDelete, onView,
}: Props) {
  const [query, setQuery] = useState("");
  const [facility, setFacility] = useState("");
  const [loc, setLoc] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [dateField, setDateField] = useState<"voidedAt" | "dateStr">("voidedAt");

  const voided = useMemo(() => records.filter((record) => record.isVoided), [records]);
  const facilities = useMemo(() => [...new Set(voided.map((r) => r.facility))].sort(), [voided]);
  const locs = useMemo(() => [...new Set(voided.map((r) => r.loc))].sort(), [voided]);
  const matching = useMemo(() => voided.filter((record) => {
    const search = [record.patientId, record.memberId, record.authNumber,
      record.facility, record.loc, record.payer, record.voidReason ?? ""]
      .join(" ").toLocaleLowerCase();
    const date = dateField === "voidedAt" ? record.voidedAt?.slice(0, 10) : record.dateStr;
    return search.includes(query.trim().toLocaleLowerCase())
      && (!facility || record.facility === facility)
      && (!loc || record.loc === loc)
      && (!from || (date != null && date >= from))
      && (!to || (date != null && date <= to));
  }), [voided, query, facility, loc, from, to, dateField]);

  const fieldClass = `rounded border px-3 py-2 ${darkMode
    ? "border-gray-700 bg-gray-900 text-white" : "border-gray-300 bg-white text-gray-900"}`;
  return (
    <section className="space-y-5 p-4 md:p-6">
      <div>
        <h2 className="text-2xl font-semibold">Voided Authorizations</h2>
        <p className="text-sm opacity-70">Archived clinical history remains available. Only Admins can restore or permanently delete records.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <label className="flex flex-col gap-1 text-sm">Search name, identifiers, payer or reason
          <input aria-label="Search voided authorizations" value={query} onChange={(e) => setQuery(e.target.value)} className={fieldClass} placeholder="Search records" />
        </label>
        <label className="flex flex-col gap-1 text-sm">Facility
          <select value={facility} onChange={(e) => setFacility(e.target.value)} className={fieldClass}>
            <option value="">All facilities</option>{facilities.map((v) => <option key={v}>{v}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">Level of care
          <select value={loc} onChange={(e) => setLoc(e.target.value)} className={fieldClass}>
            <option value="">All LOCs</option>{locs.map((v) => <option key={v}>{v}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">Date basis
          <select value={dateField} onChange={(e) => setDateField(e.target.value as "voidedAt" | "dateStr")} className={fieldClass}>
            <option value="voidedAt">Date voided</option><option value="dateStr">Authorization start date</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">From
          <input type="date" value={from} max={to || undefined} onChange={(e) => setFrom(e.target.value)} className={fieldClass} />
        </label>
        <label className="flex flex-col gap-1 text-sm">To
          <input type="date" value={to} min={from || undefined} onChange={(e) => setTo(e.target.value)} className={fieldClass} />
        </label>
      </div>
      <div className="flex items-center justify-between text-sm">
        <span>{matching.length} of {voided.length} voided records</span>
        <button type="button" className="underline" onClick={() => {setQuery("");setFacility("");setLoc("");setFrom("");setTo("");setDateField("voidedAt");}}>Clear filters</button>
      </div>
      <DataTable data={matching} darkMode={darkMode} onView={onView}
        onRestore={isAdmin ? onRestore : undefined}
        onDelete={isAdmin ? onDelete : undefined} />
    </section>
  );
}
