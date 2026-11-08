import { OpportunityEligibilityRules, PolymorphicOpportunity } from '@/types/domain';

/**
 * Normalizes and formats opportunity location according to JobFalcon canonical rules:
 * - Explicit city/location in the listing → Display that location.
 * - Explicit remote position with a specified geographic scope → Display `Remote — [scope]`.
 * - Explicitly remote without geographic scope → Display `Remote`.
 * - Hybrid position → Display the actual location and hybrid designation.
 * - Location absent or unverifiable → Display `Location not specified`.
 *
 * Guarantees that candidate location (e.g. Satna, MP, India) is never inferred
 * or leaked into opportunity display.
 */
export function formatOpportunityLocation(
  oppOrRules?:
    | PolymorphicOpportunity
    | OpportunityEligibilityRules
    | {
        eligibility_rules?: Partial<OpportunityEligibilityRules>;
        display_location?: string;
      }
    | null
): string {
  if (!oppOrRules) return 'Location not specified';

  // Check if object has pre-computed display_location
  if ('display_location' in oppOrRules && oppOrRules.display_location && oppOrRules.display_location.trim()) {
    return oppOrRules.display_location.trim();
  }

  const rules: Partial<OpportunityEligibilityRules> =
    'eligibility_rules' in oppOrRules && oppOrRules.eligibility_rules
      ? oppOrRules.eligibility_rules
      : (oppOrRules as Partial<OpportunityEligibilityRules>);

  if (rules.display_location && rules.display_location.trim()) {
    return rules.display_location.trim();
  }

  const mode = String(rules.work_mode || '').toUpperCase();
  const rawLocs = (rules.location_city_country || [])
    .map((l) => String(l || '').trim())
    .filter((l) => Boolean(l));

  // Case: REMOTE
  if (mode === 'REMOTE') {
    if (rawLocs.length === 0) return 'Remote';

    const rawScope = rawLocs[0];
    const lower = rawScope.toLowerCase();
    if (['remote', 'anywhere', 'worldwide', 'global', 'flexible', 'work from home', 'wfh'].includes(lower)) {
      return 'Remote';
    }

    const cleanScope = rawScope
      .replace(/^remote\s*(?:[-—–:,]|\bin\b|\bwithin\b)?\s*[\(\[]?/i, '')
      .replace(/[\)\]]+$/g, '')
      .replace(/\bonly\b/gi, '')
      .trim();

    if (
      !cleanScope ||
      ['remote', 'anywhere', 'worldwide', 'global', 'flexible', 'work from home', 'wfh'].includes(
        cleanScope.toLowerCase()
      )
    ) {
      return 'Remote';
    }

    return `Remote — ${cleanScope}`;
  }

  // Case: HYBRID
  if (mode === 'HYBRID') {
    if (rawLocs.length === 0) return 'Hybrid (Location not specified)';

    const rawLoc = rawLocs.join(', ');
    const cleanLoc = rawLoc
      .replace(/\(?hybrid\)?/gi, '')
      .replace(/^[\s\-—–,]+|[\s\-—–,]+$/g, '')
      .trim();

    if (!cleanLoc) return 'Hybrid (Location not specified)';
    return `${cleanLoc} (Hybrid)`;
  }

  // Case: ON_SITE or UNSPECIFIED
  if (rawLocs.length === 0) {
    return 'Location not specified';
  }

  return rawLocs.join(', ');
}
