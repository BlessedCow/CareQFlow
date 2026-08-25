import { useEffect, useState } from "react";
import type { AppPage } from "../../types/navigation";
import { cn } from "../../utils/cn";

interface WalkthroughProps {
  darkMode: boolean;
  role: string;
  activePage: AppPage;
  onPageChange: (page: AppPage) => void;
  onComplete: () => Promise<void>;
  onSkip: () => Promise<void>;
}

interface WalkthroughStep {
  title: string;
  description: string;
  page: AppPage;
  target?: string;
}

const WALKTHROUGH_STEPS: WalkthroughStep[] = [
  {
    title: "Welcome to CareQueue",
    description:
      "This walkthrough introduces the main workflow areas in CareQueue. You can move backward or forward at any time, or skip the walkthrough entirely.",
    page: "dashboard",
  },
  {
    title: "Dashboard",
    description:
      "The Dashboard gives you a high-level view of authorization workload, upcoming reviews, trends, and recent activity.",
    page: "dashboard",
    target: '[data-walkthrough="nav-dashboard"]',
  },
  {
    title: "Authorizations",
    description:
      "The Authorizations page is the main work queue. This is where authorization records are created, reviewed, edited, and followed over time.",
    page: "authorizations",
    target: '[data-walkthrough="nav-authorizations"]',
  },
  {
    title: "Add an authorization",
    description:
      "Use Add Authorization to create a new authorization record. The form includes client, payer, facility, level of care, authorization dates, submission details, and workflow information.",
    page: "authorizations",
    target: '[data-walkthrough="add-authorization"]',
  },
  {
    title: "PDF intake",
    description:
      "When creating a new initial authorization, CareQueue can review a PDF and propose values for the form. The PDF is processed in memory and the extracted information must be reviewed before it is applied.",
    page: "authorizations",
    target: '[data-walkthrough="add-authorization"]',
  },
  {
    title: "Concurrent reviews and level of care changes",
    description:
      "Existing authorization records can be continued through timeline events and concurrent review workflow. Level of care changes create a new authorization record linked to the prior workflow context.",
    page: "authorizations",
    target: '[data-walkthrough="nav-authorizations"]',
  },
  {
    title: "Denials, P2P, appeals, and retro follow-up",
    description:
      "Use this workflow to track denials, peer-to-peer reviews, appeals, retro authorizations, follow-up dates, and related outcomes.",
    page: "denials-pipeline",
    target: '[data-walkthrough="nav-denials-pipeline"]',
  },
  {
    title: "Calendar",
    description:
      "The Calendar helps you track review dates, LCDs, and upcoming authorization activity across your work queue.",
    page: "calendar",
    target: '[data-walkthrough="nav-calendar"]',
  },
  {
    title: "Settings",
    description:
      "Settings contains the registered options used throughout CareQueue, along with workflow display, security, and account preferences.",
    page: "settings",
    target: '[data-walkthrough="nav-settings"]',
  },
  {
    title: "Registered Facilities",
    description:
      "Add the facilities your organization works with here. These facilities become available when creating authorization records.",
    page: "settings",
    target: '[data-walkthrough="registered-facilities"]',
  },
  {
    title: "Registered Insurances",
    description:
      "Add payer and insurance names here before creating authorization records. These values populate the insurance selections throughout the application.",
    page: "settings",
    target: '[data-walkthrough="registered-insurances"]',
  },
  {
    title: "Web Portals",
    description:
      "Register payer portal names here. These options can then be selected when documenting web portal submissions.",
    page: "settings",
    target: '[data-walkthrough="registered-web-portals"]',
  },
  {
    title: "You're ready to use CareQueue",
    description:
      "You can now begin configuring your facilities and payers, creating authorizations, tracking reviews, and managing follow-up work.",
    page: "dashboard",
  },
];

export function Walkthrough({
  darkMode,
  role,
  activePage,
  onPageChange,
  onComplete,
  onSkip,
}: WalkthroughProps) {
  const [stepIndex, setStepIndex] = useState(0);
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const step = WALKTHROUGH_STEPS[stepIndex];
  const isFirstStep = stepIndex === 0;
  const isLastStep = stepIndex === WALKTHROUGH_STEPS.length - 1;

  useEffect(() => {
    if (activePage !== step.page) {
      onPageChange(step.page);
    }
  }, [activePage, onPageChange, step.page]);

  useEffect(() => {
    let timeoutId: number | undefined;

    const updateTarget = () => {
      if (!step.target) {
        setTargetRect(null);
        return;
      }

      const target = document.querySelector<HTMLElement>(step.target);

      if (!target) {
        setTargetRect(null);
        return;
      }

      target.scrollIntoView({
        block: "center",
        inline: "nearest",
      });

      timeoutId = window.setTimeout(() => {
        setTargetRect(target.getBoundingClientRect());
      }, 50);
    };

    updateTarget();

    window.addEventListener("resize", updateTarget);
    window.addEventListener("scroll", updateTarget, true);

    return () => {
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }

      window.removeEventListener("resize", updateTarget);
      window.removeEventListener("scroll", updateTarget, true);
    };
  }, [activePage, step.target]);

  const handleNext = async () => {
    setError(null);

    if (!isLastStep) {
      setStepIndex((currentIndex) => currentIndex + 1);
      return;
    }

    setIsSaving(true);

    try {
      await onComplete();
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to complete walkthrough."
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleSkip = async () => {
    setError(null);
    setIsSaving(true);

    try {
      await onSkip();
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to skip walkthrough."
      );
    } finally {
      setIsSaving(false);
    }
  };

  const highlightPadding = 8;

  return (
    <>
      {targetRect ? (
        <>
          <div
            className="fixed left-0 right-0 top-0 z-40 bg-black/60"
            style={{
              height: Math.max(0, targetRect.top - highlightPadding),
            }}
          />

          <div
            className="fixed bottom-0 left-0 z-40 bg-black/60"
            style={{
              top: Math.max(0, targetRect.top - highlightPadding),
              width: Math.max(0, targetRect.left - highlightPadding),
            }}
          />

          <div
            className="fixed bottom-0 right-0 z-40 bg-black/60"
            style={{
              top: Math.max(0, targetRect.top - highlightPadding),
              left: Math.min(
                window.innerWidth,
                targetRect.right + highlightPadding
              ),
            }}
          />

          <div
            className="fixed bottom-0 z-40 bg-black/60"
            style={{
              top: Math.min(
                window.innerHeight,
                targetRect.bottom + highlightPadding
              ),
              left: Math.max(0, targetRect.left - highlightPadding),
              right: Math.max(
                0,
                window.innerWidth - targetRect.right - highlightPadding
              ),
            }}
          />

          <div
            aria-hidden="true"
            className="pointer-events-none fixed z-50 rounded-xl border-2 border-blue-400 shadow-[0_0_0_4px_rgba(59,130,246,0.25)]"
            style={{
              top: targetRect.top - highlightPadding,
              left: targetRect.left - highlightPadding,
              width: targetRect.width + highlightPadding * 2,
              height: targetRect.height + highlightPadding * 2,
            }}
          />
        </>
      ) : (
        <div className="fixed inset-0 z-40 bg-black/60" />
      )}

      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="carequeue-walkthrough-title"
        className={cn(
          "fixed bottom-6 right-6 z-[60] w-[calc(100%-3rem)] max-w-md rounded-2xl border p-5 shadow-2xl",
          darkMode
            ? "border-gray-700 bg-gray-900 text-gray-100"
            : "border-gray-200 bg-white text-gray-900"
        )}
      >
        <div
          className={cn(
            "mb-3 text-xs font-semibold uppercase tracking-wide",
            darkMode ? "text-blue-300" : "text-blue-600"
          )}
        >
          Step {stepIndex + 1} of {WALKTHROUGH_STEPS.length}
        </div>

        <h2 id="carequeue-walkthrough-title" className="text-lg font-semibold">
          {step.title}
        </h2>

        <p
          className={cn(
            "mt-2 text-sm leading-6",
            darkMode ? "text-gray-300" : "text-gray-600"
          )}
        >
          {step.description}
        </p>

        {role === "Read Only" && step.page === "authorizations" && (
          <p
            className={cn(
              "mt-3 rounded-lg border px-3 py-2 text-xs",
              darkMode
                ? "border-blue-900 bg-blue-950/40 text-blue-200"
                : "border-blue-200 bg-blue-50 text-blue-700"
            )}
          >
            Your Read Only role can view authorization information but cannot
            create or modify authorization records.
          </p>
        )}

        {error && (
          <p
            role="alert"
            className={cn(
              "mt-3 rounded-lg border px-3 py-2 text-sm",
              darkMode
                ? "border-red-900 bg-red-950/40 text-red-200"
                : "border-red-200 bg-red-50 text-red-700"
            )}
          >
            {error}
          </p>
        )}

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            disabled={isSaving}
            onClick={() => void handleSkip()}
            className={cn(
              "text-sm font-medium",
              darkMode
                ? "text-gray-400 hover:text-gray-200"
                : "text-gray-600 hover:text-gray-900",
              isSaving && "cursor-not-allowed opacity-50"
            )}
          >
            Skip walkthrough
          </button>

          <div className="flex gap-2">
            {!isFirstStep && (
              <button
                type="button"
                disabled={isSaving}
                onClick={() => setStepIndex((currentIndex) => currentIndex - 1)}
                className={cn(
                  "rounded-lg border px-4 py-2 text-sm font-medium",
                  darkMode
                    ? "border-gray-700 text-gray-200 hover:bg-gray-800"
                    : "border-gray-300 text-gray-700 hover:bg-gray-100",
                  isSaving && "cursor-not-allowed opacity-50"
                )}
              >
                Back
              </button>
            )}

            <button
              type="button"
              disabled={isSaving}
              onClick={() => void handleNext()}
              className={cn(
                "rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700",
                isSaving && "cursor-not-allowed opacity-50"
              )}
            >
              {isSaving ? "Saving..." : isLastStep ? "Finish" : "Next"}
            </button>
          </div>
        </div>
      </section>
    </>
  );
}
