import { API_BASE_URL, authenticatedFetch } from "./client";

export type AuthDocumentType =
  | "auth_request"
  | "approval_letter"
  | "denial_letter"
  | "other";

export interface AuthDocumentRecord {
  id: number;
  auth_id: number;
  document_type: AuthDocumentType;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  created_at: string;
  updated_at: string;
}

interface AuthDocumentListResponse {
  documents: AuthDocumentRecord[];
}

function documentUrl(authId: string, suffix = "") {
  return `${API_BASE_URL}/api/auths/${encodeURIComponent(
    authId
  )}/documents${suffix}`;
}

function getErrorMessage(action: string, response: Response) {
  return `Failed to ${action}: ${response.status}`;
}

export async function fetchAuthDocuments(
  authId: string
): Promise<AuthDocumentRecord[]> {
  const response = await authenticatedFetch(documentUrl(authId));

  if (!response.ok) {
    throw new Error(getErrorMessage("load authorization documents", response));
  }

  const data = (await response.json()) as AuthDocumentListResponse;
  return data.documents;
}

export async function uploadAuthDocument(
  authId: string,
  documentType: AuthDocumentType,
  file: File
): Promise<AuthDocumentRecord> {
  const params = new URLSearchParams({
    document_type: documentType,
    filename: file.name,
  });

  const response = await authenticatedFetch(
    `${documentUrl(authId)}?${params.toString()}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/pdf",
      },
      body: file,
    }
  );

  if (!response.ok) {
    throw new Error(getErrorMessage("upload authorization document", response));
  }

  return (await response.json()) as AuthDocumentRecord;
}

export async function deleteAuthDocument(
  authId: string,
  documentId: number
): Promise<void> {
  const response = await authenticatedFetch(
    documentUrl(authId, `/${documentId}`),
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    throw new Error(getErrorMessage("delete authorization document", response));
  }
}

export async function downloadAuthDocument(
    authId: string,
    documentRecord: AuthDocumentRecord
  ): Promise<void> {
    const response = await authenticatedFetch(
      documentUrl(authId, `/${documentRecord.id}/pdf`)
    );
  
    if (!response.ok) {
      throw new Error(getErrorMessage("download authorization document", response));
    }
  
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = window.document.createElement("a");
  
    link.href = objectUrl;
    link.download =
      documentRecord.original_filename || "authorization-document.pdf";
    link.rel = "noopener noreferrer";
    window.document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  }