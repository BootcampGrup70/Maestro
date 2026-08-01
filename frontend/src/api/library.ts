import { api } from "./client";
import type {
  LibraryWorkflow,
  LibraryWorkflowDetail,
  WorkflowPublishInput,
  WorkflowUpdateInput,
  WorkflowImportInput,
  WorkflowImportResult,
} from "./types";

// Fixed vocabulary — publishing and the Library search filter both draw from this
// same list, so tag filtering actually matches (freeform tags don't).
export const LIBRARY_TAGS = [
  "research",
  "coding",
  "writing",
  "planning",
  "automation",
  "data-analysis",
  "customer-support",
  "qa-testing",
  "devops",
  "creative",
] as const;

export type LibraryTag = (typeof LIBRARY_TAGS)[number];

export const libraryApi = {
  list: (params?: { tag?: string; search?: string }) => {
    const qs = new URLSearchParams();
    if (params?.tag) qs.set("tag", params.tag);
    if (params?.search) qs.set("search", params.search);
    const query = qs.toString();
    return api.get<LibraryWorkflow[]>(`/library${query ? `?${query}` : ""}`);
  },
  get: (id: string) => api.get<LibraryWorkflowDetail>(`/library/${id}`),
  publish: (data: WorkflowPublishInput) => api.post<LibraryWorkflow>("/library", data),
  update: (id: string, data: WorkflowUpdateInput) => api.patch<LibraryWorkflow>(`/library/${id}`, data),
  delete: (id: string) => api.delete<void>(`/library/${id}`),
  import: (id: string, data?: WorkflowImportInput) =>
    api.post<WorkflowImportResult>(`/library/${id}/import`, data),
};
