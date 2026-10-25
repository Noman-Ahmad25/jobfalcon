import { HealthStatusResponse } from '@/types/api';
import {
  AdaptiveDiscoveryRequest,
  AdaptiveDiscoveryResponse,
  CandidateCareerProfile,
  CandidateProfilingRequest,
  CandidateProfilingResponse,
  ConnectorHealthReport,
  DiscoveryQueryPlan,
  DiscoveryRunRequest,
  DiscoveryRunResponse,
  PipelineEvaluationRequest,
  PipelineEvaluationResponse,
  RankingRequest,
  RankingResponse,
  OpportunityExplanation,
  CandidateCareerGapAnalysisResponse,
  CareerImprovementSuggestion,
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

export async function runAdaptiveDiscovery(
  payload: AdaptiveDiscoveryRequest
): Promise<AdaptiveDiscoveryResponse> {
  return fetchFromApi<AdaptiveDiscoveryResponse>('/api/v1/orchestration/discovery/run', {
    method: 'POST',
    body: JSON.stringify(payload),
    timeoutMs: 25000,
  });
}

export async function evaluateAndRankOpportunities(
  payload: RankingRequest
): Promise<RankingResponse> {
  return fetchFromApi<RankingResponse>('/api/v1/ranking/evaluate', {
    method: 'POST',
    body: JSON.stringify(payload),
    timeoutMs: 15000,
  });
}

export async function getOpportunityExplanation(
  userId: string,
  oppId: string,
  useLlm: boolean = true
): Promise<OpportunityExplanation> {
  return fetchFromApi<OpportunityExplanation>(
    `/api/v1/explanation/candidate/${encodeURIComponent(userId)}/opportunity/${encodeURIComponent(oppId)}?use_llm=${useLlm}`,
    {
      method: 'GET',
      timeoutMs: 10000,
    }
  );
}

export async function getLatestExplanations(
  userId: string,
  limit: number = 10,
  useLlm: boolean = true
): Promise<OpportunityExplanation[]> {
  return fetchFromApi<OpportunityExplanation[]>(
    `/api/v1/explanation/candidate/${encodeURIComponent(userId)}/latest?limit=${limit}&use_llm=${useLlm}`,
    {
      method: 'GET',
      timeoutMs: 15000,
    }
  );
}

export async function runCareerGapAnalysis(
  userId: string,
  targetRoles?: string[],
  includeRepoOpportunities: boolean = true
): Promise<CandidateCareerGapAnalysisResponse> {
  return fetchFromApi<CandidateCareerGapAnalysisResponse>(
    `/api/v1/explanation/gap-analysis/candidate/${encodeURIComponent(userId)}/analyze`,
    {
      method: 'POST',
      body: JSON.stringify({
        target_roles: targetRoles,
        include_repo_opportunities: includeRepoOpportunities,
      }),
      timeoutMs: 15000,
    }
  );
}

export async function getCareerImprovementSuggestions(
  userId: string
): Promise<CareerImprovementSuggestion[]> {
  return fetchFromApi<CareerImprovementSuggestion[]>(
    `/api/v1/explanation/gap-analysis/candidate/${encodeURIComponent(userId)}/suggestions`,
    {
      method: 'GET',
      timeoutMs: 10000,
    }
  );
}





