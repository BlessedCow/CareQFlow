import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import {
  PdfIntakeReviewPanel,
  type PdfIntakeFormValues,
} from "./PdfIntakeReviewPanel";
import { usePdfIntakePreview } from "../hooks/usePdfIntakePreview";
import type { NewAuthFormState } from "../hooks/useAuthorizationForm";
import {
  hasAuthorizationFormErrors,
  validateAuthorizationForm,
  type AuthorizationFormErrors,
} from "../utils/authorizationFormValidation";
import { cn } from "../utils/cn";

function formatPhoneNumber(value: string) {
  const digitsOnly = value.replace(/\D/g, "").slice(0, 10);

  if (digitsOnly.length <= 3) {
    return digitsOnly;
  }

  if (digitsOnly.length <= 6) {
    return `${digitsOnly.slice(0, 3)}-${digitsOnly.slice(3)}`;
  }

  return `${digitsOnly.slice(0, 3)}-${digitsOnly.slice(
    3,
    6
  )}-${digitsOnly.slice(6)}`;
}

function findRegisteredOption(value: string, options: string[]): string | null {
  const normalizedValue = value.trim().toLocaleLowerCase();

  if (!normalizedValue) {
    return null;
  }

  return (
    options.find(
      (option) => option.trim().toLocaleLowerCase() === normalizedValue
    ) ?? null
  );
}

interface AddAuthorizationFormProps {
  form: NewAuthFormState;
  darkMode: boolean;
  isCreatingAuth: boolean;
  submitLabel: string;
  allowPdfIntake: boolean;
  registeredFacilities: string[];
  registeredInsurances: string[];
  registeredWebPortals: string[];
  onFieldChange: (
    field: keyof NewAuthFormState,
    value: string | boolean
  ) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
}

export function AddAuthorizationForm({
  form,
  darkMode,
  isCreatingAuth,
  submitLabel,
  allowPdfIntake,
  registeredFacilities,
  registeredInsurances,
  registeredWebPortals,
  onFieldChange,
  onSubmit,
  onCancel,
}: AddAuthorizationFormProps) {
  const [showAuthNotes, setShowAuthNotes] = useState(true);
  const pdfFileInputRef = useRef<HTMLInputElement>(null);
  const [pdfApplyWarning, setPdfApplyWarning] = useState<string | null>(null);
  const [formErrors, setFormErrors] = useState<AuthorizationFormErrors>({});

  const {
    selectedPdfFile,
    pdfIntakePreview,
    isLoadingPdfPreview,
    pdfIntakeError,
    selectPdf,
    requestPreview,
    clearPdfIntake,
  } = usePdfIntakePreview();
  const hasAuthNotes = form.careManagerNotes.trim().length > 0;
  const resetPdfFileInput = () => {
    if (pdfFileInputRef.current) {
      pdfFileInputRef.current.value = "";
    }
  };

  const handleFieldChange = (
    field: keyof NewAuthFormState,
    value: string | boolean
  ) => {
    onFieldChange(field, value);

    if (formErrors[field]) {
      setFormErrors((currentErrors) => {
        const nextErrors = { ...currentErrors };
        delete nextErrors[field];
        return nextErrors;
      });
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    const errors = validateAuthorizationForm(form);

    if (hasAuthorizationFormErrors(errors)) {
      event.preventDefault();
      setFormErrors(errors);
      return;
    }

    setFormErrors({});
    onSubmit(event);
  };
  const handlePdfSelection = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;

    setPdfApplyWarning(null);
    selectPdf(file);
  };

  const handleRequestPdfPreview = async () => {
    await requestPreview();
    resetPdfFileInput();
  };

  const handleCancelPdfIntake = () => {
    clearPdfIntake();
    setPdfApplyWarning(null);
    resetPdfFileInput();
  };

  const handleApplyPdfValues = (values: PdfIntakeFormValues) => {
    const warnings: string[] = [];

    if (values.clientName?.trim()) {
      handleFieldChange("clientName", values.clientName.trim());
    }

    if (values.memberId?.trim()) {
      handleFieldChange("memberId", values.memberId.trim());
    }

    if (values.groupNumber?.trim()) {
      handleFieldChange("groupNumber", values.groupNumber.trim());
    }

    if (values.dateOfBirth?.trim()) {
      handleFieldChange("dateOfBirth", values.dateOfBirth.trim());
    }

    if (values.startDate?.trim()) {
      handleFieldChange("startDate", values.startDate.trim());
    }

    if (values.phoneNumber?.trim()) {
      handleFieldChange("phoneNumber", formatPhoneNumber(values.phoneNumber));
    }

    if (values.facility?.trim()) {
      const matchingFacility = findRegisteredOption(
        values.facility,
        registeredFacilities
      );

      if (matchingFacility) {
        handleFieldChange("facility", matchingFacility);
      } else {
        warnings.push(
          `"${values.facility.trim()}" is not a registered facility.`
        );
      }
    }

    if (values.insurance?.trim()) {
      const matchingInsurance = findRegisteredOption(
        values.insurance,
        registeredInsurances
      );

      if (matchingInsurance) {
        handleFieldChange("insurance", matchingInsurance);
      } else {
        warnings.push(
          `"${values.insurance.trim()}" is not a registered insurance.`
        );
      }
    }

    setPdfApplyWarning(
      warnings.length > 0
        ? `${warnings.join(
            " "
          )} Select an existing option manually or add it in Settings.`
        : null
    );

    clearPdfIntake();
    resetPdfFileInput();
  };
  return (
    <form
      data-walkthrough="authorization-form"
      onSubmit={handleSubmit}
      noValidate
      className={cn(
        "mb-5 grid gap-4 rounded-lg border p-4 md:grid-cols-2",
        darkMode
          ? "border-gray-800 bg-gray-950/60"
          : "border-gray-200 bg-gray-50"
      )}
    >
      {allowPdfIntake && (
        <section
          data-walkthrough="pdf-intake"
          className={cn(
            "rounded-xl border p-4 md:col-span-2",
            darkMode
              ? "border-gray-800 bg-gray-950/40"
              : "border-gray-200 bg-white"
          )}
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h3 className="text-sm font-semibold">Import from PDF</h3>
              <p
                className={cn(
                  "mt-1 text-xs",
                  darkMode ? "text-gray-400" : "text-gray-600"
                )}
              >
                The PDF is processed in memory and is not stored by CareQFlow.
                Review all extracted values before applying them.
              </p>
            </div>

            <div className="flex flex-wrap items-end gap-2">
              <label className="space-y-1 text-sm">
                <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                  PDF file
                </span>
                <input
                  ref={pdfFileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  disabled={isLoadingPdfPreview}
                  onChange={handlePdfSelection}
                  className={cn(
                    "block max-w-full text-sm",
                    darkMode
                      ? "text-gray-300 file:bg-gray-800 file:text-gray-100"
                      : "text-gray-700 file:bg-gray-100 file:text-gray-800",
                    "file:mr-3 file:rounded-lg file:border-0 file:px-3 file:py-2 file:text-sm file:font-medium"
                  )}
                />
              </label>

              <button
                type="button"
                disabled={!selectedPdfFile || isLoadingPdfPreview}
                onClick={() => void handleRequestPdfPreview()}
                className={cn(
                  "rounded-lg px-4 py-2 text-sm font-medium",
                  selectedPdfFile && !isLoadingPdfPreview
                    ? "bg-blue-600 text-white hover:bg-blue-700"
                    : darkMode
                    ? "cursor-not-allowed bg-gray-800 text-gray-500"
                    : "cursor-not-allowed bg-gray-200 text-gray-500"
                )}
              >
                {isLoadingPdfPreview ? "Processing..." : "Review PDF"}
              </button>

              {(selectedPdfFile || pdfIntakeError) && (
                <button
                  type="button"
                  disabled={isLoadingPdfPreview}
                  onClick={handleCancelPdfIntake}
                  className={cn(
                    "rounded-lg border px-3 py-2 text-sm font-medium",
                    darkMode
                      ? "border-gray-700 text-gray-200 hover:bg-gray-900"
                      : "border-gray-300 text-gray-700 hover:bg-gray-100"
                  )}
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {pdfIntakeError && (
            <p
              role="alert"
              className={cn(
                "mt-3 rounded-lg border px-3 py-2 text-sm",
                darkMode
                  ? "border-red-900 bg-red-950/40 text-red-200"
                  : "border-red-200 bg-red-50 text-red-700"
              )}
            >
              {pdfIntakeError}
            </p>
          )}

          {pdfApplyWarning && (
            <p
              role="status"
              className={cn(
                "mt-3 rounded-lg border px-3 py-2 text-sm",
                darkMode
                  ? "border-amber-900 bg-amber-950/40 text-amber-200"
                  : "border-amber-300 bg-amber-50 text-amber-800"
              )}
            >
              {pdfApplyWarning}
            </p>
          )}
        </section>
      )}

      {allowPdfIntake && pdfIntakePreview && (
        <PdfIntakeReviewPanel
          preview={pdfIntakePreview}
          darkMode={darkMode}
          onApply={handleApplyPdfValues}
          onCancel={handleCancelPdfIntake}
        />
      )}
      <label data-walkthrough="auth-client-name" className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Client Name
        </span>

        <input
          type="text"
          value={form.clientName}
          onChange={(event) =>
            handleFieldChange("clientName", event.target.value)
          }
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        />

        {formErrors.clientName && (
          <p role="alert" className="text-xs text-red-600">
            {formErrors.clientName}
          </p>
        )}
      </label>

      <label className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Member ID
        </span>
        <input
          type="text"
          value={form.memberId}
          onChange={(event) => onFieldChange("memberId", event.target.value)}
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        />
      </label>

      <label className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Payer Auth / Reference Number
        </span>
        <input
          type="text"
          value={form.authNumber}
          onChange={(event) => onFieldChange("authNumber", event.target.value)}
          placeholder="Any payer auth, case, or reference number"
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100 placeholder-gray-500"
              : "border-gray-300 bg-white text-gray-900 placeholder-gray-400"
          )}
        />
      </label>

      <label className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Group Number
        </span>
        <input
          type="text"
          value={form.groupNumber}
          onChange={(event) => onFieldChange("groupNumber", event.target.value)}
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        />
      </label>

      <label className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Date of Birth
        </span>
        <input
          type="date"
          value={form.dateOfBirth}
          onChange={(event) =>
            handleFieldChange("dateOfBirth", event.target.value)
          }
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        />
        {formErrors.dateOfBirth && (
          <p role="alert" className="text-xs text-red-600">
            {formErrors.dateOfBirth}
          </p>
        )}
      </label>

      <label className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Programming Days
        </span>
        <select
          value={form.programmingDays}
          onChange={(event) =>
            onFieldChange("programmingDays", event.target.value)
          }
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        >
          <option value="7 days/week">7 days/week</option>
          <option value="M-F">M-F</option>
          <option value="M-Sa">M-Sa</option>
          <option value="MWF">MWF</option>
        </select>
      </label>

      <label data-walkthrough="auth-facility" className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Facility
        </span>
        <select
          value={form.facility}
          onChange={(event) =>
            handleFieldChange("facility", event.target.value)
          }
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        >
          {registeredFacilities.map((facility) => (
            <option key={facility} value={facility}>
              {facility}
            </option>
          ))}
        </select>
        {formErrors.facility && (
          <p role="alert" className="text-xs text-red-600">
            {formErrors.facility}
          </p>
        )}
      </label>

      <label data-walkthrough="auth-loc" className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          LOC
        </span>
        <select
          value={form.loc}
          onChange={(event) => handleFieldChange("loc", event.target.value)}
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        >
          <option value="DTX">DTX</option>
          <option value="RTC">RTC</option>
          <option value="PHP">PHP</option>
          <option value="IOP">IOP</option>
        </select>
        {formErrors.loc && (
          <p role="alert" className="text-xs text-red-600">
            {formErrors.loc}
          </p>
        )}
      </label>

      <label className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Status
        </span>
        <select
          value={form.status}
          onChange={(event) => handleFieldChange("status", event.target.value)}
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        >
          <option value="Pending">Pending</option>
          <option value="Approved">Approved</option>
          <option value="Denied">Denied</option>
          <option value="Needs Review">Needs Review</option>
          <option value="Completed">Completed</option>
          <option value="Discharged">Discharged</option>
        </select>
        {formErrors.status && (
          <p role="alert" className="text-xs text-red-600">
            {formErrors.status}
          </p>
        )}
      </label>

      <label className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Auth Start Date
        </span>
        <input
          type="date"
          value={form.startDate}
          onChange={(event) =>
            handleFieldChange("startDate", event.target.value)
          }
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        />
        {formErrors.startDate && (
          <p role="alert" className="text-xs text-red-600">
            {formErrors.startDate}
          </p>
        )}
      </label>

      <label className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Auth End Date
        </span>
        <input
          type="date"
          value={form.endDate}
          onChange={(event) => handleFieldChange("endDate", event.target.value)}
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        />
        {formErrors.endDate && (
          <p role="alert" className="text-xs text-red-600">
            {formErrors.endDate}
          </p>
        )}
      </label>

      <label className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Review Due Date
        </span>
        <input
          type="date"
          value={form.reviewDueDate}
          onChange={(event) =>
            handleFieldChange("reviewDueDate", event.target.value)
          }
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        />
        {formErrors.reviewDueDate && (
          <p role="alert" className="text-xs text-red-600">
            {formErrors.reviewDueDate}
          </p>
        )}
      </label>

      <label className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Days Requested
        </span>
        <input
          type="number"
          min="0"
          value={form.requestedDays}
          onChange={(event) =>
            onFieldChange("requestedDays", event.target.value)
          }
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        />
      </label>

      <label className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Days Approved
        </span>
        <input
          type="number"
          min="0"
          value={form.approvedDays}
          onChange={(event) =>
            onFieldChange("approvedDays", event.target.value)
          }
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        />
      </label>

      <label data-walkthrough="auth-insurance" className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Insurance
        </span>
        <select
          value={form.insurance}
          onChange={(event) => onFieldChange("insurance", event.target.value)}
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        >
          {registeredInsurances.map((insurance) => (
            <option key={insurance} value={insurance}>
              {insurance}
            </option>
          ))}
        </select>
      </label>

      <label data-walkthrough="auth-type" className="space-y-1 text-sm">
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Auth Type
        </span>
        <select
          value={form.authType}
          onChange={(event) =>
            handleFieldChange("authType", event.target.value)
          }
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        >
          <option value="Initial">Initial</option>
          <option value="LOC Change">LOC Change</option>
          <option value="Retro">Retro</option>
        </select>
        {formErrors.authType && (
          <p role="alert" className="text-xs text-red-600">
            {formErrors.authType}
          </p>
        )}
      </label>

      <label
        data-walkthrough="auth-submission-method"
        className="space-y-1 text-sm"
      >
        <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
          Submission Method
        </span>
        <select
          value={form.submissionMethod}
          onChange={(event) =>
            onFieldChange("submissionMethod", event.target.value)
          }
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
            darkMode
              ? "border-gray-700 bg-gray-900 text-gray-100"
              : "border-gray-300 bg-white text-gray-900"
          )}
        >
          <option value="Web Portal">Web Portal</option>
          <option value="Live Call">Live Call</option>
          <option value="Voicemail">Voicemail</option>
          <option value="Fax">Fax</option>
        </select>
      </label>

      {(form.submissionMethod === "Live Call" ||
        form.submissionMethod === "Voicemail") && (
        <>
          <label className="space-y-1 text-sm">
            <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
              Phone Number
            </span>
            <input
              type="tel"
              inputMode="numeric"
              maxLength={12}
              value={form.phoneNumber}
              onChange={(event) =>
                onFieldChange(
                  "phoneNumber",
                  formatPhoneNumber(event.target.value)
                )
              }
              placeholder="123-456-7890"
              className={cn(
                "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                darkMode
                  ? "border-gray-700 bg-gray-900 text-gray-100"
                  : "border-gray-300 bg-white text-gray-900"
              )}
            />
          </label>

          <label className="space-y-1 text-sm">
            <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
              Extension
            </span>
            <input
              type="text"
              value={form.phoneExtension}
              onChange={(event) =>
                onFieldChange("phoneExtension", event.target.value)
              }
              className={cn(
                "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                darkMode
                  ? "border-gray-700 bg-gray-900 text-gray-100"
                  : "border-gray-300 bg-white text-gray-900"
              )}
            />
          </label>
        </>
      )}

      {form.submissionMethod === "Fax" && (
        <label className="space-y-1 text-sm md:col-span-2">
          <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
            Fax Number
          </span>
          <input
            type="tel"
            inputMode="numeric"
            maxLength={12}
            value={form.faxNumber}
            onChange={(event) =>
              onFieldChange("faxNumber", formatPhoneNumber(event.target.value))
            }
            placeholder="123-456-7890"
            className={cn(
              "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
              darkMode
                ? "border-gray-700 bg-gray-900 text-gray-100"
                : "border-gray-300 bg-white text-gray-900"
            )}
          />
        </label>
      )}

      {form.submissionMethod === "Web Portal" && (
        <>
          <label className="space-y-1 text-sm">
            <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
              Portal
            </span>
            <select
              value={form.webPortal}
              onChange={(event) =>
                onFieldChange("webPortal", event.target.value)
              }
              className={cn(
                "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                darkMode
                  ? "border-gray-700 bg-gray-900 text-gray-100"
                  : "border-gray-300 bg-white text-gray-900"
              )}
            >
              {registeredWebPortals.map((portal) => (
                <option key={portal} value={portal}>
                  {portal}
                </option>
              ))}
              <option value="Other">Other</option>
            </select>
          </label>

          <label className="space-y-1 text-sm">
            <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
              Portal Link
            </span>
            <input
              type="url"
              value={form.webPortalUrl}
              onChange={(event) =>
                onFieldChange("webPortalUrl", event.target.value)
              }
              placeholder={
                form.webPortal === "Other"
                  ? "Enter new portal link"
                  : "Optional portal link"
              }
              className={cn(
                "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                darkMode
                  ? "border-gray-700 bg-gray-900 text-gray-100"
                  : "border-gray-300 bg-white text-gray-900"
              )}
            />
          </label>
        </>
      )}

      <div
        className={cn(
          "space-y-4 rounded-lg border p-4 md:col-span-2",
          darkMode
            ? "border-gray-800 bg-gray-950/40"
            : "border-gray-200 bg-white"
        )}
      >
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.hasCareManager}
            onChange={(event) =>
              onFieldChange("hasCareManager", event.target.checked)
            }
            className="h-4 w-4 rounded border-gray-300"
          />
          <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
            Add Care Team / Care Manager details
          </span>
        </label>

        {form.hasCareManager && (
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Care Manager Name
              </span>
              <input
                type="text"
                value={form.careManagerName}
                onChange={(event) =>
                  onFieldChange("careManagerName", event.target.value)
                }
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              />
            </label>

            <label className="space-y-1 text-sm">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Preferred Contact Method
              </span>
              <select
                value={form.careManagerContactType}
                onChange={(event) =>
                  onFieldChange("careManagerContactType", event.target.value)
                }
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              >
                <option value="Phone">Phone</option>
                <option value="Fax">Fax</option>
              </select>
            </label>

            {form.careManagerContactType === "Phone" && (
              <label className="space-y-1 text-sm">
                <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                  Care Manager Phone
                </span>
                <input
                  type="tel"
                  inputMode="numeric"
                  maxLength={12}
                  value={form.careManagerPhone}
                  onChange={(event) =>
                    onFieldChange(
                      "careManagerPhone",
                      formatPhoneNumber(event.target.value)
                    )
                  }
                  placeholder="123-456-7890"
                  className={cn(
                    "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                    darkMode
                      ? "border-gray-700 bg-gray-900 text-gray-100"
                      : "border-gray-300 bg-white text-gray-900"
                  )}
                />
              </label>
            )}

            {form.careManagerContactType === "Fax" && (
              <label className="space-y-1 text-sm">
                <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                  Care Manager Fax
                </span>
                <input
                  type="tel"
                  inputMode="numeric"
                  maxLength={12}
                  value={form.careManagerFax}
                  onChange={(event) =>
                    onFieldChange(
                      "careManagerFax",
                      formatPhoneNumber(event.target.value)
                    )
                  }
                  placeholder="123-456-7890"
                  className={cn(
                    "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                    darkMode
                      ? "border-gray-700 bg-gray-900 text-gray-100"
                      : "border-gray-300 bg-white text-gray-900"
                  )}
                />
              </label>
            )}

            <div className="space-y-2 text-sm md:col-span-2">
              <div className="flex items-center justify-between gap-3">
                <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                  Care Manager Notes
                </span>

                <button
                  type="button"
                  onClick={() =>
                    setShowAuthNotes((currentValue) => !currentValue)
                  }
                  className={cn(
                    "rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors",
                    darkMode
                      ? "border-gray-700 bg-gray-900 text-gray-200 hover:bg-gray-800"
                      : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                  )}
                >
                  {showAuthNotes
                    ? "Hide Notes"
                    : hasAuthNotes
                    ? "Show Notes"
                    : "Add Notes"}
                </button>
              </div>

              {showAuthNotes && (
                <textarea
                  value={form.careManagerNotes}
                  onChange={(event) =>
                    onFieldChange("careManagerNotes", event.target.value)
                  }
                  placeholder="Example: Leave clinicals as voicemail, fax continued stay review, ask for reviewer extension..."
                  rows={3}
                  className={cn(
                    "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                    darkMode
                      ? "border-gray-700 bg-gray-900 text-gray-100 placeholder-gray-500"
                      : "border-gray-300 bg-white text-gray-900 placeholder-gray-400"
                  )}
                />
              )}
            </div>
          </div>
        )}
      </div>

      <div
        data-walkthrough="auth-form-actions"
        className="flex items-end justify-end gap-2 md:col-span-2"
      >
        <button
          type="button"
          onClick={onCancel}
          className={cn(
            "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
            darkMode
              ? "bg-gray-800 text-gray-200 hover:bg-gray-700"
              : "bg-gray-200 text-gray-800 hover:bg-gray-300"
          )}
        >
          Cancel
        </button>

        <button
          type="submit"
          disabled={isCreatingAuth}
          className={cn(
            "rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-70",
            darkMode
              ? "bg-blue-600 text-white hover:bg-blue-500"
              : "bg-blue-600 text-white hover:bg-blue-700"
          )}
        >
          {isCreatingAuth ? "Saving..." : submitLabel}
        </button>
      </div>
    </form>
  );
}
