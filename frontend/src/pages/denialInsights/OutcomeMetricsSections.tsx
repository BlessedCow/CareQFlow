import type {
  DenialInsightsFollowUpMetrics,
  DenialInsightsSummary,
  FollowUpMetricSummary,
} from "../../api/denialInsights";
import { cn } from "../../utils/cn";

interface OutcomeMetricsSectionsProps {
  darkMode: boolean;
  followUpMetrics: DenialInsightsFollowUpMetrics;
  retroRootMetrics: DenialInsightsSummary;
}

function formatRate(value: number | null) {
  if (value === null) {
    return "—";
  }

  return `${(value * 100).toFixed(1)}%`;
}

function FollowUpMetricCard({
  darkMode,
  title,
  metrics,
  showOverturnRate,
}: {
  darkMode: boolean;
  title: string;
  metrics: FollowUpMetricSummary;
  showOverturnRate: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border p-5",
        darkMode ? "border-gray-800 bg-gray-950" : "border-gray-200 bg-gray-50"
      )}
    >
      <h3 className="font-semibold">{title}</h3>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        <div>
          <dt
            className={cn(
              "text-xs uppercase tracking-wide",
              darkMode ? "text-gray-500" : "text-gray-500"
            )}
          >
            Eligible
          </dt>
          <dd className="mt-1 font-semibold">{metrics.eligible_count}</dd>
        </div>

        <div>
          <dt
            className={cn(
              "text-xs uppercase tracking-wide",
              darkMode ? "text-gray-500" : "text-gray-500"
            )}
          >
            Initiated
          </dt>
          <dd className="mt-1 font-semibold">{metrics.initiated_count}</dd>
        </div>

        <div>
          <dt
            className={cn(
              "text-xs uppercase tracking-wide",
              darkMode ? "text-gray-500" : "text-gray-500"
            )}
          >
            Pending
          </dt>
          <dd className="mt-1 font-semibold">{metrics.pending_count}</dd>
        </div>

        <div>
          <dt
            className={cn(
              "text-xs uppercase tracking-wide",
              darkMode ? "text-gray-500" : "text-gray-500"
            )}
          >
            Resolved
          </dt>
          <dd className="mt-1 font-semibold">{metrics.resolved_count}</dd>
        </div>

        <div>
          <dt
            className={cn(
              "text-xs uppercase tracking-wide",
              darkMode ? "text-gray-500" : "text-gray-500"
            )}
          >
            Upheld / Denied
          </dt>
          <dd className="mt-1 font-semibold">
            {metrics.upheld_count + metrics.denied_count}
          </dd>
        </div>

        <div>
          <dt
            className={cn(
              "text-xs uppercase tracking-wide",
              darkMode ? "text-gray-500" : "text-gray-500"
            )}
          >
            Favorable
          </dt>
          <dd className="mt-1 font-semibold">
            {metrics.overturned_count +
              metrics.approved_count +
              metrics.partially_approved_count}
          </dd>
        </div>

        {showOverturnRate && (
          <div className="col-span-2">
            <dt
              className={cn(
                "text-xs uppercase tracking-wide",
                darkMode ? "text-gray-500" : "text-gray-500"
              )}
            >
              Overturn rate among resolved
            </dt>
            <dd className="mt-1 text-lg font-semibold">
              {formatRate(metrics.overturn_rate)}
            </dd>
          </div>
        )}
      </dl>
    </div>
  );
}

export function OutcomeMetricsSections({
  darkMode,
  followUpMetrics,
  retroRootMetrics,
}: OutcomeMetricsSectionsProps) {
  return (
    <>
      <section
        className={cn(
          "rounded-xl border p-6 shadow-sm",
          darkMode ? "border-gray-800 bg-gray-900" : "border-gray-200 bg-white"
        )}
      >
        <div>
          <h2 className="text-lg font-semibold">Follow-up outcomes</h2>
          <p
            className={cn(
              "mt-1 text-sm",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            Tracks what happened after adverse clinical authorization decisions
            without changing the original denial-rate denominator.
          </p>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          <FollowUpMetricCard
            darkMode={darkMode}
            title="Peer to Peer"
            metrics={followUpMetrics.p2p}
            showOverturnRate
          />

          <FollowUpMetricCard
            darkMode={darkMode}
            title="Appeal"
            metrics={followUpMetrics.appeal}
            showOverturnRate
          />

          <FollowUpMetricCard
            darkMode={darkMode}
            title="Retro Follow-up"
            metrics={followUpMetrics.retro}
            showOverturnRate={false}
          />
        </div>
      </section>

      <section
        className={cn(
          "rounded-xl border p-6 shadow-sm",
          darkMode ? "border-gray-800 bg-gray-900" : "border-gray-200 bg-white"
        )}
      >
        <div>
          <h2 className="text-lg font-semibold">Standalone Retro decisions</h2>
          <p
            className={cn(
              "mt-1 text-sm",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            Retro reviews that began without a prior clinical authorization
            decision are reported separately from denial and follow-up cohorts.
          </p>
        </div>

        <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[
            {
              label: "Retro decisions",
              value: String(retroRootMetrics.decision_count),
            },
            {
              label: "Approved",
              value: String(retroRootMetrics.approved_count),
            },
            {
              label: "Partially approved",
              value: String(retroRootMetrics.partial_count),
            },
            {
              label: "Denied",
              value: String(retroRootMetrics.denied_count),
            },
          ].map((item) => (
            <div
              key={item.label}
              className={cn(
                "rounded-xl border p-4",
                darkMode
                  ? "border-gray-800 bg-gray-950"
                  : "border-gray-200 bg-gray-50"
              )}
            >
              <div
                className={cn(
                  "text-sm",
                  darkMode ? "text-gray-400" : "text-gray-600"
                )}
              >
                {item.label}
              </div>

              <div className="mt-2 text-2xl font-semibold">{item.value}</div>
            </div>
          ))}
        </div>

        <div
          className={cn(
            "mt-4 text-xs",
            darkMode ? "text-gray-500" : "text-gray-500"
          )}
        >
          Denial rate: {formatRate(retroRootMetrics.observed_denial_rate)}
          {" · "}
          Partial approval rate:{" "}
          {formatRate(retroRootMetrics.observed_partial_rate)}
        </div>
      </section>
    </>
  );
}
