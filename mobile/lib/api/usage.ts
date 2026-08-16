import { apiRequest } from "./client";
import type { UsageSummary } from "./types";

export async function getMyUsage(): Promise<UsageSummary> {
  return apiRequest<UsageSummary>("/api/v1/usage/me");
}
