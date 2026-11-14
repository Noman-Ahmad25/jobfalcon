/**
 * Human-readable label formatting for technical domain identifiers,
 * connector names, work modes, and activity metadata.
 *
 * Keeps backend schemas and API contracts untouched while ensuring the UI
 * displays polished, consistent, and natural language labels across all viewports.
 */

export function formatWorkMode(mode?: string | null): string {
  if (!mode) return 'Remote';
  const upper = mode.toUpperCase().trim();
  switch (upper) {
    case 'ON_SITE':
    case 'ONSITE':
    case 'ON-SITE':
      return 'On-site';
    case 'REMOTE':
      return 'Remote';
    case 'HYBRID':
      return 'Hybrid';
    default:
      return mode
        .toLowerCase()
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

export function formatSourceSystem(source?: string | null): string {
  if (!source) return 'Direct ATS';
  const clean = source.toLowerCase().trim();
  switch (clean) {
    case 'jobspy_mcp':
    case 'jobspy':
      return 'JobSpy';
    case 'web_search':
    case 'web':
    case 'searxng':
      return 'Web search';
    case 'ats_career_page':
    case 'ats_career_pages':
    case 'ats_direct':
    case 'ats':
      return 'Direct ATS';
    case 'linkedin':
      return 'LinkedIn';
    case 'indeed':
      return 'Indeed';
    case 'glassdoor':
      return 'Glassdoor';
    case 'ziprecruiter':
      return 'ZipRecruiter';
    case 'google':
      return 'Google Jobs';
    case 'real_connector':
      return 'Verified Connector';
    case 'mocked_fallback':
      return 'Mocked Fallback';
    default:
      return source
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

export function formatOpportunityCategory(category?: string | null): string {
  if (!category) return 'Full-time Job';
  const upper = category.toUpperCase().trim();
  switch (upper) {
    case 'FULL_TIME_JOB':
    case 'FULL_TIME':
      return 'Full-time Job';
    case 'PART_TIME_JOB':
    case 'PART_TIME':
      return 'Part-time Job';
    case 'INTERNSHIP':
      return 'Internship';
    case 'CONTRACT':
      return 'Contract';
    default:
      return category
        .toLowerCase()
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

export function formatActionType(action?: string | null): string {
  if (!action) return '';
  const upper = action.toUpperCase().trim();
  switch (upper) {
    case 'SAVED':
      return 'Saved';
    case 'APPLIED':
      return 'Applied';
    case 'DISMISSED':
      return 'Dismissed';
    case 'SOFT_OVERRIDDEN':
      return 'Soft Override';
    case 'SOFT_REJECTED':
      return 'Soft Rejected';
    case 'HARD_REJECTED':
      return 'Ineligible';
    case 'RECOMMENDED':
      return 'Recommended';
    default:
      return action
        .toLowerCase()
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

export function formatMemoryType(type?: string | null): string {
  if (!type) return '';
  const upper = type.toUpperCase().trim();
  switch (upper) {
    case 'ROLE_GOAL':
      return 'Role Goal';
    case 'DOMAIN_PREFERENCE':
      return 'Domain Preference';
    case 'WORK_PREFERENCE':
      return 'Workplace Preference';
    case 'SALARY_PREFERENCE':
      return 'Salary Preference';
    default:
      return type
        .toLowerCase()
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

export function formatProvenanceLevel(level?: string | null): string {
  if (!level) return '';
  const upper = level.toUpperCase().trim();
  switch (upper) {
    case 'VERIFIED':
      return 'Verified';
    case 'USER_PROVIDED':
    case 'USER_EXPLICIT':
      return 'User Provided';
    case 'AI_INFERRED':
    case 'INFERRED_FROM_FEEDBACK':
      return 'Feedback Inferred';
    case 'OUTDATED':
      return 'Outdated';
    case 'UNVERIFIED':
      return 'Unverified';
    default:
      return level
        .toLowerCase()
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

/**
 * Clean up internal connector/source identifiers embedded in agent narrative summaries.
 */
export function formatAgentSummary(summary?: string | null): string {
  if (!summary) return '';
  return summary
    .replace(/'web_search'/g, "'Web search'")
    .replace(/\bweb_search\b/g, 'Web search')
    .replace(/'jobspy_mcp'/g, "'JobSpy'")
    .replace(/\bjobspy_mcp\b/g, 'JobSpy')
    .replace(/'ats_career_page'/g, "'Direct ATS'")
    .replace(/\bats_career_page\b/g, 'Direct ATS')
    .replace(/'ats_career_pages'/g, "'Direct ATS'")
    .replace(/\bats_career_pages\b/g, 'Direct ATS')
    .replace(/'ats_direct'/g, "'Direct ATS'")
    .replace(/\bats_direct\b/g, 'Direct ATS');
}
