import { useEffect, useRef, useState, type ChangeEvent } from "react";
import {
  deleteAuthDocument,
  downloadAuthDocument,
  fetchAuthDocuments,
  uploadAuthDocument,
  type AuthDocumentRecord,
  type AuthDocumentType,
} from "../api/authDocuments";
import { cn } from "../utils/cn";

interface AuthorizationDocumentsSectionProps {
  authId: string;
  darkMode: boolean;
  canManage: boolean;
}

const DOCUMENT_TYPE_OPTIONS: { value: AuthDocumentType; label: string }[] = [
  { value: "auth_request", label: "Auth Request" },
  { value: "approval_letter", label: "Approval Letter" },
  { value: "denial_letter", label: "Denial Letter" },
  { value: "other", label: "Other" },
];

function formatDocumentType(value: AuthDocumentType) {
  return (
    DOCUMENT_TYPE_OPTIONS.find((option) => option.value === value)?.label ??
    "Document"
  );
}

function formatFileSize(value: number) {
  if (value < 1024) {
    return `${value} B`;
  }

  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }

  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDateTime(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

export function AuthorizationDocumentsSection({
  authId,
  darkMode,
  canManage,
}: AuthorizationDocumentsSectionProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<AuthDocumentRecord[]>([]);
  const [selectedDocumentType, setSelectedDocumentType] =
    useState<AuthDocumentType>("approval_letter");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [isUploadingDocument, setIsUploadingDocument] = useState(false);
  const [downloadingDocumentId, setDownloadingDocumentId] = useState<
    number | null
  >(null);
  const [deletingDocumentId, setDeletingDocumentId] = useState<number | null>(
    null
  );
  const [documentError, setDocumentError] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;

    async function loadDocuments() {
      setIsLoadingDocuments(true);
      setDocumentError(null);

      try {
        const loadedDocuments = await fetchAuthDocuments(authId);

        if (isCurrent) {
          setDocuments(loadedDocuments);
        }
      } catch {
        if (isCurrent) {
          setDocumentError("Unable to load authorization documents.");
        }
      } finally {
        if (isCurrent) {
          setIsLoadingDocuments(false);
        }
      }
    }

    void loadDocuments();

    return () => {
      isCurrent = false;
    };
  }, [authId]);

  const resetFileInput = () => {
    setSelectedFile(null);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setDocumentError(null);
    setSelectedFile(event.target.files?.[0] ?? null);
  };

  const handleUploadDocument = async () => {
    if (!selectedFile) {
      setDocumentError("Select a PDF document before uploading.");
      return;
    }

    if (
      selectedFile.type !== "application/pdf" &&
      !selectedFile.name.toLowerCase().endsWith(".pdf")
    ) {
      setDocumentError("Only PDF documents can be uploaded.");
      return;
    }

    setIsUploadingDocument(true);
    setDocumentError(null);

    try {
      const uploadedDocument = await uploadAuthDocument(
        authId,
        selectedDocumentType,
        selectedFile
      );
      setDocuments((currentDocuments) => [
        uploadedDocument,
        ...currentDocuments,
      ]);
      resetFileInput();
    } catch {
      setDocumentError("Unable to upload authorization document.");
    } finally {
      setIsUploadingDocument(false);
    }
  };

  const handleDownloadDocument = async (documentRecord: AuthDocumentRecord) => {
    setDownloadingDocumentId(documentRecord.id);
    setDocumentError(null);

    try {
      await downloadAuthDocument(authId, documentRecord);
    } catch {
      setDocumentError("Unable to download authorization document.");
    } finally {
      setDownloadingDocumentId(null);
    }
  };

  const handleDeleteDocument = async (documentRecord: AuthDocumentRecord) => {
    setDeletingDocumentId(documentRecord.id);
    setDocumentError(null);

    try {
      await deleteAuthDocument(authId, documentRecord.id);
      setDocuments((currentDocuments) =>
        currentDocuments.filter((document) => document.id !== documentRecord.id)
      );
    } catch {
      setDocumentError("Unable to delete authorization document.");
    } finally {
      setDeletingDocumentId(null);
    }
  };

  return (
    <section>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3
            className={cn(
              "text-sm font-semibold",
              darkMode ? "text-gray-100" : "text-gray-900"
            )}
          >
            Authorization Documents
          </h3>
          <p
            className={cn(
              "mt-1 text-xs",
              darkMode ? "text-gray-400" : "text-gray-500"
            )}
          >
            Store approval, denial, auth request, or other payer letters as
            encrypted PDFs.
          </p>
        </div>
      </div>

      {canManage && (
        <div
          className={cn(
            "mt-4 rounded-xl border p-3",
            darkMode
              ? "border-gray-700 bg-gray-950"
              : "border-gray-200 bg-gray-50"
          )}
        >
          <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,2fr)_auto] md:items-end">
            <label className="space-y-1 text-sm">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Document Type
              </span>
              <select
                value={selectedDocumentType}
                disabled={isUploadingDocument}
                onChange={(event) =>
                  setSelectedDocumentType(
                    event.target.value as AuthDocumentType
                  )
                }
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              >
                {DOCUMENT_TYPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1 text-sm">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                PDF Document
              </span>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                disabled={isUploadingDocument}
                onChange={handleFileChange}
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
              onClick={handleUploadDocument}
              disabled={isUploadingDocument || !selectedFile}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60",
                darkMode
                  ? "bg-blue-600 text-white hover:bg-blue-500"
                  : "bg-blue-600 text-white hover:bg-blue-700"
              )}
            >
              {isUploadingDocument ? "Uploading..." : "Upload PDF"}
            </button>
          </div>
        </div>
      )}

      {documentError && (
        <div
          className={cn(
            "mt-3 rounded-xl border px-4 py-3 text-sm",
            darkMode
              ? "border-red-900/70 bg-red-950/40 text-red-200"
              : "border-red-200 bg-red-50 text-red-700"
          )}
        >
          {documentError}
        </div>
      )}

      {isLoadingDocuments ? (
        <p
          className={cn(
            "mt-3 text-sm",
            darkMode ? "text-gray-400" : "text-gray-500"
          )}
        >
          Loading authorization documents...
        </p>
      ) : documents.length === 0 ? (
        <p
          className={cn(
            "mt-3 text-sm",
            darkMode ? "text-gray-400" : "text-gray-500"
          )}
        >
          No authorization documents uploaded yet.
        </p>
      ) : (
        <div className="mt-3 space-y-3">
          {documents.map((documentRecord) => (
            <div
              key={documentRecord.id}
              className={cn(
                "flex flex-col gap-3 rounded-xl border p-3 sm:flex-row sm:items-center sm:justify-between",
                darkMode
                  ? "border-gray-700 bg-gray-950"
                  : "border-gray-200 bg-gray-50"
              )}
            >
              <div>
                <div
                  className={cn(
                    "text-sm font-semibold",
                    darkMode ? "text-gray-100" : "text-gray-900"
                  )}
                >
                  {documentRecord.original_filename}
                </div>
                <div
                  className={cn(
                    "mt-1 text-xs",
                    darkMode ? "text-gray-400" : "text-gray-500"
                  )}
                >
                  {formatDocumentType(documentRecord.document_type)} ·{" "}
                  {formatFileSize(documentRecord.file_size_bytes)} · Uploaded{" "}
                  {formatDateTime(documentRecord.created_at)}
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => handleDownloadDocument(documentRecord)}
                  disabled={downloadingDocumentId === documentRecord.id}
                  className={cn(
                    "rounded-lg px-3 py-2 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60",
                    darkMode
                      ? "bg-gray-800 text-gray-100 hover:bg-gray-700"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  )}
                >
                  {downloadingDocumentId === documentRecord.id
                    ? "Downloading..."
                    : "Download"}
                </button>

                {canManage && (
                  <button
                    type="button"
                    onClick={() => handleDeleteDocument(documentRecord)}
                    disabled={deletingDocumentId === documentRecord.id}
                    className={cn(
                      "rounded-lg px-3 py-2 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60",
                      darkMode
                        ? "bg-red-950/50 text-red-200 hover:bg-red-900/60"
                        : "bg-red-50 text-red-700 hover:bg-red-100"
                    )}
                  >
                    {deletingDocumentId === documentRecord.id
                      ? "Deleting..."
                      : "Delete"}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
