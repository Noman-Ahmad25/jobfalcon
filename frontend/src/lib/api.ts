import { HealthStatusResponse } from '@/types/api';
import {
  CandidateCareerProfile,
  CandidateProfilingRequest,
  CandidateProfilingResponse,
  ConnectorHealthReport,
  DiscoveryQueryPlan,
  DiscoveryRunRequest,
  DiscoveryRunResponse,
  PipelineEvaluationRequest,
  PipelineEvaluationResponse,
} from '@/types/domain';

const DEFAULT_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 5000;

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function fetchFromApi<T>(
  endpoint: string,
  options: RequestInit & { timeoutMs?: number } = {}
): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...fetchOptions } = options;
  const url = `${DEFAULT_API_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      },
    });

    if (!response.ok) {
      let errorDetails: unknown = null;
      try {
        errorDetails = await response.json();
      } catch {
        errorDetails = await response.text();
      }
      throw new ApiError(
        `API request to ${endpoint} failed with HTTP ${response.status}`,
        response.status,
        errorDetails
      );
    }

    return (await response.json()) as T;
  } catch (error: unknown) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError(`Request to ${endpoint} timed out after ${timeoutMs}ms`, 408);
    }
    const message = error instanceof Error ? error.message : 'Unknown network failure';
    throw new ApiError(`Failed to connect to backend at ${url}: ${message}`);
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function getBackendHealth(): Promise<HealthStatusResponse> {
  return fetchFromApi<HealthStatusResponse>('/api/v1/healthz');
}

export async function getBackendReadiness(): Promise<HealthStatusResponse> {
  return fetchFromApi<HealthStatusResponse>('/api/v1/readyz');
}

export async function evaluateOpportunitiesPipeline(
  payload: PipelineEvaluationRequest
): Promise<PipelineEvaluationResponse> {
  return fetchFromApi<PipelineEvaluationResponse>('/api/v1/opportunities/evaluate', {
    method: 'POST',
    body: JSON.stringify(payload),
    timeoutMs: 8000,
  });
}

export async function extractCandidateProfile(
  payload: CandidateProfilingRequest
): Promise<CandidateProfilingResponse> {
  return fetchFromApi<CandidateProfilingResponse>('/api/v1/profile/extract', {
    method: 'POST',
    body: JSON.stringify(payload),
    timeoutMs: 15000,
  });
}

export async function getCandidateProfile(
  userId: string
): Promise<CandidateCareerProfile> {
  return fetchFromApi<CandidateCareerProfile>(`/api/v1/profile/${encodeURIComponent(userId)}`, {
    method: 'GET',
    timeoutMs: 5000,
  });
}

export async function getDiscoveryConnectors(): Promise<ConnectorHealthReport[]> {
  return fetchFromApi<ConnectorHealthReport[]>('/api/v1/discovery/connectors', {
    method: 'GET',
    timeoutMs: 5000,
  });
}

export async function generateDiscoveryPlan(payload: {
  candidate_profile?: CandidateCareerProfile | null;
  user_id?: string | null;
}): Promise<DiscoveryQueryPlan> {
  return fetchFromApi<DiscoveryQueryPlan>('/api/v1/discovery/plan', {
    method: 'POST',
    body: JSON.stringify(payload),
    timeoutMs: 8000,
  });
}

export async function runDiscovery(
  payload: DiscoveryRunRequest
): Promise<DiscoveryRunResponse> {
  return fetchFromApi<DiscoveryRunResponse>('/api/v1/discovery/run', {
    method: 'POST',
    body: JSON.stringify(payload),
    timeoutMs: 15000,
  });
}



