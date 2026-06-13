export type DashboardData = {
  candidates: number;
  accredited_centers: number;
  exam_sessions: number;
  questions: number;
  fraud_alerts: number;
};

export type EntrySummary = {
  total: number;
  by_result: Record<string, number>;
  by_center: Record<string, { allowed: number; denied: number }>;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getDashboard(): Promise<DashboardData> {
  return getJson<DashboardData>('/api/v1/dashboard');
}

export function getEntrySummary(): Promise<EntrySummary> {
  return getJson<EntrySummary>('/api/v1/entries/summary');
}
