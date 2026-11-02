import { HealthStatusResponse } from '@/types/api';
import {
  AdaptiveDiscoveryRequest,
  AdaptiveDiscoveryResponse,
  CandidateCareerProfile,
  CandidateProfileSummary,
  CandidateProfilingRequest,
  CandidateProfilingResponse,
  ConnectorHealthReport,
  DiscoveryQueryPlan,
  DiscoveryRun,
  DiscoveryRunRequest,
  DiscoveryRunResponse,
  PipelineEvaluationRequest,
  PipelineEvaluationResponse,
  RankingRequest,
  RankingResponse,
  OpportunityExplanation,
  CandidateCareerGapAnalysisResponse,
  CareerImprovementSuggestion,
  CareerPathAssessmentResponse,
  RoleTargetAssessment,
  PersonalizedDevelopmentPlan,
  DevelopmentActionItem,
  UpdateActionProgressRequest,
  StructuredProfileCreateRequest,
  OpportunitySearchRequest,
  OpportunitySearchResponse,
  MarketIntelligenceResponse,
  PolymorphicOpportunity,
} from '@/types/domain';

const DEFAULT_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 5000;

// Application boundary: pluggable auth and tenant headers for future BFF / Auth integration
let globalAuthHeaders: Record<string, string> = {};

export function setApiAuthContext(headers: Record<string, string>): void {
  globalAuthHeaders = { ...headers };
}

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
        ...globalAuthHeaders,
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
    timeoutMs: 120000,
  });
}

export async function parseResumeFile(
  file: File
): Promise<{ filename: string; text: string; char_count: number }> {
  const formData = new FormData();
  formData.append('file', file);
  const url = `${DEFAULT_API_URL}/api/v1/profile/parse-resume-file`;
  const res = await fetch(url, {
    method: 'POST',
    body: formData,
    headers: { ...globalAuthHeaders },
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => null);
    throw new Error(errorBody?.detail || `Failed to parse file '${file.name}'`);
  }
  return res.json();
}

export async function getCandidateProfile(
  userId: string
): Promise<CandidateCareerProfile> {
  return fetchFromApi<CandidateCareerProfile>(`/api/v1/profile/${encodeURIComponent(userId)}`, {
    method: 'GET',
    timeoutMs: 5000,
  });
}

export async function getDiscoveryConnectors(live: boolean = false): Promise<ConnectorHealthReport[]> {
  const query = live ? '?live=true' : '';
  return fetchFromApi<ConnectorHealthReport[]>(`/api/v1/discovery/connectors${query}`, {
    method: 'GET',
    timeoutMs: live ? 12000 : 5000,
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
    timeoutMs: 30000,
  });
}

export async function startDiscoveryRun(
  payload: AdaptiveDiscoveryRequest
): Promise<DiscoveryRun> {
  return fetchFromApi<DiscoveryRun>('/api/v1/orchestration/discovery/start', {
    method: 'POST',
    body: JSON.stringify(payload),
    timeoutMs: 10000,
  });
}

export async function getDiscoveryRun(runId: string): Promise<DiscoveryRun> {
  return fetchFromApi<DiscoveryRun>(`/api/v1/orchestration/discovery/runs/${encodeURIComponent(runId)}`, {
    method: 'GET',
    timeoutMs: 8000,
  });
}

export async function getLatestDiscoveryRunForCandidate(
  candidateId: string
): Promise<DiscoveryRun | null> {
  try {
    return await fetchFromApi<DiscoveryRun>(
      `/api/v1/orchestration/discovery/candidate/${encodeURIComponent(candidateId)}/latest-run`,
      {
        method: 'GET',
        timeoutMs: 8000,
      }
    );
  } catch (err: unknown) {
    if (err instanceof ApiError && err.statusCode === 404) {
      return null;
    }
    throw err;
  }
}

export function getDiscoveryRunStreamUrl(runId: string): string {
  return `${DEFAULT_API_URL}/api/v1/orchestration/discovery/runs/${encodeURIComponent(runId)}/stream`;
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

// =============================================================================
// Milestone 12: Career Path Intelligence & Personalized Development Planning
// =============================================================================

export async function getCareerPathAssessment(
  userId: string,
  refresh: boolean = false
): Promise<CareerPathAssessmentResponse> {
  return fetchFromApi<CareerPathAssessmentResponse>(
    `/api/v1/career-path/candidate/${encodeURIComponent(userId)}/assessment?refresh=${refresh}`,
    {
      method: 'GET',
      timeoutMs: 15000,
    }
  );
}

export async function getCareerPathRoles(
  userId: string
): Promise<RoleTargetAssessment[]> {
  return fetchFromApi<RoleTargetAssessment[]>(
    `/api/v1/career-path/candidate/${encodeURIComponent(userId)}/roles`,
    {
      method: 'GET',
      timeoutMs: 10000,
    }
  );
}

export async function getDevelopmentPlan(
  userId: string
): Promise<PersonalizedDevelopmentPlan> {
  return fetchFromApi<PersonalizedDevelopmentPlan>(
    `/api/v1/career-path/candidate/${encodeURIComponent(userId)}/plan`,
    {
      method: 'GET',
      timeoutMs: 10000,
    }
  );
}

export async function generateDevelopmentPlan(
  userId: string,
  targetRoles?: string[],
  includeRepoOpportunities: boolean = true
): Promise<PersonalizedDevelopmentPlan> {
  return fetchFromApi<PersonalizedDevelopmentPlan>(
    `/api/v1/career-path/candidate/${encodeURIComponent(userId)}/plan/generate`,
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

export async function getDevelopmentActions(
  userId: string
): Promise<DevelopmentActionItem[]> {
  return fetchFromApi<DevelopmentActionItem[]>(
    `/api/v1/career-path/candidate/${encodeURIComponent(userId)}/actions`,
    {
      method: 'GET',
      timeoutMs: 10000,
    }
  );
}

export async function updateActionProgress(
  userId: string,
  actionId: string,
  req: UpdateActionProgressRequest
): Promise<DevelopmentActionItem> {
  return fetchFromApi<DevelopmentActionItem>(
    `/api/v1/career-path/candidate/${encodeURIComponent(userId)}/actions/${encodeURIComponent(actionId)}`,
    {
      method: 'PATCH',
      body: JSON.stringify(req),
      timeoutMs: 10000,
    }
  );
}

export async function refreshCareerPathAssessment(
  userId: string,
  targetRoles?: string[],
  includeRepoOpportunities: boolean = true
): Promise<CareerPathAssessmentResponse> {
  return fetchFromApi<CareerPathAssessmentResponse>(
    `/api/v1/career-path/candidate/${encodeURIComponent(userId)}/refresh`,
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

// =============================================================================
// Profile Lifecycle: List, Create, Update, Delete
// =============================================================================

/** List all stored candidate profile summaries from the backend repository. */
export async function listProfiles(): Promise<CandidateProfileSummary[]> {
  return fetchFromApi<CandidateProfileSummary[]>('/api/v1/profile/', {
    method: 'GET',
    timeoutMs: 5000,
  });
}

/** Create a new candidate profile from structured form fields (no LLM). */
export async function createStructuredProfile(
  data: StructuredProfileCreateRequest
): Promise<CandidateCareerProfile> {
  return fetchFromApi<CandidateCareerProfile>('/api/v1/profile/create-structured', {
    method: 'POST',
    body: JSON.stringify(data),
    timeoutMs: 8000,
  });
}

/** Update (overwrite) a stored candidate profile by user_id. */
export async function updateCandidateProfile(
  userId: string,
  profile: CandidateCareerProfile
): Promise<CandidateCareerProfile> {
  return fetchFromApi<CandidateCareerProfile>(
    `/api/v1/profile/${encodeURIComponent(userId)}`,
    {
      method: 'PUT',
      body: JSON.stringify(profile),
      timeoutMs: 8000,
    }
  );
}

/** Permanently delete a candidate profile from the repository. */
export async function deleteCandidateProfile(userId: string): Promise<void> {
  await fetchFromApi<void>(`/api/v1/profile/${encodeURIComponent(userId)}`, {
    method: 'DELETE',
    timeoutMs: 5000,
  });
}

/** Intentional market search for opportunities using chosen criteria. */
export async function searchOpportunities(
  request: OpportunitySearchRequest
): Promise<OpportunitySearchResponse> {
  return fetchFromApi<OpportunitySearchResponse>('/api/v1/opportunities/search', {
    method: 'POST',
    body: JSON.stringify(request),
    timeoutMs: 8000,
  });
}

/** Grounded empirical market demand intelligence. */
export async function getMarketIntelligence(params?: {
  target_role?: string;
  category?: string;
}): Promise<MarketIntelligenceResponse> {
  const query = new URLSearchParams();
  if (params?.target_role) query.set('target_role', params.target_role);
  if (params?.category) query.set('category', params.category);
  const qStr = query.toString();
  return fetchFromApi<MarketIntelligenceResponse>(
    `/api/v1/opportunities/market-intelligence${qStr ? `?${qStr}` : ''}`,
    {
      method: 'GET',
      timeoutMs: 8000,
    }
  );
}

/** Retrieve detailed polymorphic opportunity by identifier. */
export async function getOpportunityById(
  opportunityId: string
): Promise<PolymorphicOpportunity> {
  return fetchFromApi<PolymorphicOpportunity>(
    `/api/v1/opportunities/${encodeURIComponent(opportunityId)}`,
    {
      method: 'GET',
      timeoutMs: 6000,
    }
  );
}



