import { API_BASE_URL, authenticatedFetch } from "./client";

export type PdfCandidateSource = "form_field" | "embedded_text";
export type PdfCandidateConfidence = "high" | "medium" | "low";

export interface PdfIntakeCandidate {
  value: string;
  source: PdfCandidateSource;
  confidence: PdfCandidateConfidence;
  needs_review: boolean;
}

export interface PdfIntakePreview {
  template_id: string | null;
  template_matched: boolean;
  facility: PdfIntakeCandidate | null;
  client_name: PdfIntakeCandidate | null;
  admit_date_range: PdfIntakeCandidate | null;
  date_of_birth: PdfIntakeCandidate | null;
  insurance: PdfIntakeCandidate | null;
  insurance_phone: PdfIntakeCandidate | null;
  authorization_phone: PdfIntakeCandidate | null;
  medical_member_id: PdfIntakeCandidate | null;
  medical_group_number: PdfIntakeCandidate | null;
  behavioral_health_member_id: PdfIntakeCandidate | null;
  behavioral_health_group_number: PdfIntakeCandidate | null;
  has_usable_text: boolean;
}

interface ApiErrorResponse {
  detail?: string;
}

async function getErrorMessage(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as ApiErrorResponse;

    if (typeof data.detail === "string" && data.detail.trim()) {
      return data.detail;
    }
  } catch {
    // Use the safe fallback below.
  }

  return "The PDF could not be processed.";
}

export async function previewPdfIntake(file: File): Promise<PdfIntakePreview> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/pdf-intake/preview`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/pdf",
      },
      body: file,
      cache: "no-store",
    }
  );

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return (await response.json()) as PdfIntakePreview;
}
