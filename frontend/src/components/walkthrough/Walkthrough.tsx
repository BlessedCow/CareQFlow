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
  requiredAction?: "click" | "count-increase-if-empty";
}

const WALKTHROUGH_STEPS: WalkthroughStep[] = [
    {
      title: "Welcome to CareQueue",
      description:
        "This walkthrough will guide you through the basic CareQueue setup and authorization workflow. You can skip the walkthrough at any time.",
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
      title: "Settings",
      description:
        "Start in Settings by configuring the facilities and insurance plans used by your organization.",
      page: "settings",
      target: '[data-walkthrough="nav-settings"]',
    },
    {
      title: "Add your facilities",
      description:
        "Facilities are used when creating authorization records. If no facilities are registered yet, add at least one facility before continuing.",
      page: "settings",
      target: '[data-walkthrough="registered-facilities"]',
      requiredAction: "count-increase-if-empty",
    },
    {
      title: "Add your insurances",
      description:
        "Insurance names registered here become available when creating and filtering authorization records. If none are registered yet, add at least one before continuing.",
      page: "settings",
      target: '[data-walkthrough="registered-insurances"]',
      requiredAction: "count-increase-if-empty",
    },
    {
      title: "Web Portals",
      description:
        "You can also register payer web portals here. Add the portals your organization uses when applicable. This setup is optional.",
      page: "settings",
      target: '[data-walkthrough="registered-web-portals"]',
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
        'Click "Add Authorization" to open the authorization form. The walkthrough will wait here until you open it.',
      page: "authorizations",
      target: '[data-walkthrough="add-authorization"]',
      requiredAction: "click",
    },
    {
      title: "Authorization form",
      description:
        "This form contains the information used to track an authorization, including the client, facility, insurance, level of care, authorization dates, and payer workflow details.",
      page: "authorizations",
      target: '[data-walkthrough="authorization-form"]',
    },
    {
      title: "Client information",
      description:
        "Enter the client's identifying information here. Client Name and other required fields must be completed before the authorization can be saved.",
      page: "authorizations",
      target: '[data-walkthrough="auth-client-name"]',
    },
    {
      title: "Facility",
      description:
        "Select the facility associated with this authorization. These options come from the facilities you registered in Settings.",
      page: "authorizations",
      target: '[data-walkthrough="auth-facility"]',
    },
    {
      title: "Level of care",
      description:
        "Choose the current level of care for the authorization, such as DTX, RTC, PHP, or IOP.",
      page: "authorizations",
      target: '[data-walkthrough="auth-loc"]',
    },
    {
      title: "Insurance",
      description:
        "Select the payer for this authorization. These options come from the insurances you registered in Settings.",
      page: "authorizations",
      target: '[data-walkthrough="auth-insurance"]',
    },
    {
      title: "Authorization type",
      description:
        "Choose the authorization type. Initial is used for a new authorization, LOC Change creates a level of care change workflow, and Retro is used for retro authorization work.",
      page: "authorizations",
      target: '[data-walkthrough="auth-type"]',
    },
    {
      title: "Submission method",
      description:
        "Choose how the authorization was submitted. CareQueue can show additional fields for web portals, phone calls, voicemail, or fax depending on this selection.",
      page: "authorizations",
      target: '[data-walkthrough="auth-submission-method"]',
    },
    {
      title: "PDF intake",
      description:
        "For a new initial authorization, you can optionally select a supported PDF and ask CareQueue to propose values for the form. The PDF is processed in memory and you review the extracted values before applying them.",
      page: "authorizations",
      target: '[data-walkthrough="pdf-intake"]',
    },
    {
      title: "Save the authorization",
      description:
        "When the required information is complete, use the save button here to create the authorization. You do not need to save a real authorization to complete this walkthrough.",
      page: "authorizations",
      target: '[data-walkthrough="auth-form-actions"]',
    },
    {
      title: "Concurrent reviews and level of care changes",
      description:
        "Existing authorization workflows can later be continued through concurrent reviews, timeline events, and level of care changes. The walkthrough will cover these workflows separately.",
      page: "authorizations",
      target: '[data-walkthrough="authorization-form"]',
    },
    {
      title: "Denials, P2P, appeals, and retro follow-up",
      description:
        "CareQueue also includes a dedicated workflow for denials, peer-to-peer reviews, appeals, retro authorizations, and follow-up activity.",
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
      title: "You're ready to use CareQueue",
      description:
        "The basic setup walkthrough is complete. You can now create and manage authorization workflows using the facilities and payers you configured.",
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
  const [requiredActionCompleted, setRequiredActionCompleted] = useState(false);


  const step = WALKTHROUGH_STEPS[stepIndex];
  const isFirstStep = stepIndex === 0;
  const isLastStep = stepIndex === WALKTHROUGH_STEPS.length - 1;
  const requiresAction = step.requiredAction !== undefined;
  const canContinue = !requiresAction || requiredActionCompleted;

  useEffect(() => {
    if (activePage !== step.page) {
      onPageChange(step.page);
    }
  }, [activePage, onPageChange, step.page]);

  useEffect(() => {
    setRequiredActionCompleted(false);
  }, [stepIndex]);

  useEffect(() => {
    let timeoutId: number | undefined;
    let target: HTMLElement | null = null;
    let countObserver: MutationObserver | null = null;
  
    const handleRequiredAction = () => {
      if (step.requiredAction === "click") {
        setRequiredActionCompleted(true);
      }
    };
  
    const updateTargetRect = () => {
      if (!target) {
        setTargetRect(null);
        return;
      }
  
      setTargetRect(target.getBoundingClientRect());
    };
  
    if (!step.target) {
      setTargetRect(null);
    } else {
      target = document.querySelector<HTMLElement>(step.target);
  
      if (!target) {
        setTargetRect(null);
      } else {
        if (typeof target.scrollIntoView === "function") {
          target.scrollIntoView({
            block: "center",
            inline: "nearest",
          });
        }
  
        if (step.requiredAction === "click") {
          target.addEventListener("click", handleRequiredAction);
        }
  
        if (step.requiredAction === "count-increase-if-empty") {
          const initialCount = Number(target.dataset.walkthroughCount ?? "0");
  
          if (initialCount > 0) {
            setRequiredActionCompleted(true);
          } else {
            countObserver = new MutationObserver(() => {
              if (!target) {
                return;
              }
  
              const currentCount = Number(
                target.dataset.walkthroughCount ?? "0"
              );
  
              if (currentCount > initialCount) {
                setRequiredActionCompleted(true);
              }
            });
  
            countObserver.observe(target, {
              attributes: true,
              attributeFilter: ["data-walkthrough-count"],
            });
          }
        }
  
        timeoutId = window.setTimeout(() => {
          updateTargetRect();
        }, 50);
      }
    }
  
    window.addEventListener("resize", updateTargetRect);
    window.addEventListener("scroll", updateTargetRect, true);
  
    return () => {
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
  
      countObserver?.disconnect();
  
      if (target && step.requiredAction === "click") {
        target.removeEventListener("click", handleRequiredAction);
      }
  
      window.removeEventListener("resize", updateTargetRect);
      window.removeEventListener("scroll", updateTargetRect, true);
    };
  }, [activePage, step.requiredAction, step.target]);
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

        {requiresAction && (
          <div
            className={cn(
              "mt-3 rounded-lg border px-3 py-2 text-sm",
              requiredActionCompleted
                ? darkMode
                  ? "border-green-900 bg-green-950/40 text-green-200"
                  : "border-green-200 bg-green-50 text-green-700"
                : darkMode
                ? "border-blue-900 bg-blue-950/40 text-blue-200"
                : "border-blue-200 bg-blue-50 text-blue-700"
            )}
          >
            {requiredActionCompleted
              ? step.requiredAction === "count-increase-if-empty"
                  ? "This section is configured. Press Next to continue."
                  : "Step completed. Press Next to continue."
              : step.requiredAction === "count-increase-if-empty"
                  ? "Add at least one item in the highlighted section to continue."
                  : "Complete the highlighted action to continue."}
          </div>
        )}

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
              disabled={isSaving || !canContinue}
              onClick={() => void handleNext()}
              className={cn(
                "rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700",
                (isSaving || !canContinue) && "cursor-not-allowed opacity-50"
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
