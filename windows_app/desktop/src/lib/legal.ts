export interface LegalDocument {
  id: "terms_of_service" | "terms_and_conditions" | "privacy_policy";
  title: string;
  file: string;
}

export const LEGAL_DOCUMENTS: LegalDocument[] = [
  { id: "terms_of_service", title: "Terms of Service", file: "/legal/TERMS_OF_SERVICE.md" },
  { id: "terms_and_conditions", title: "Terms and Conditions", file: "/legal/TERMS_AND_CONDITIONS.md" },
  { id: "privacy_policy", title: "Privacy Policy", file: "/legal/PRIVACY_POLICY.md" },
];

export async function loadLegal(file: string): Promise<string> {
  const response = await fetch(file);
  if (!response.ok) throw new Error(`Could not load ${file}`);
  return response.text();
}
