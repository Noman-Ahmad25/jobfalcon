'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Search,
  MapPin,
  Building2,
  ExternalLink,
  Briefcase,
  RotateCw,
  Eye,
} from 'lucide-react';
import {
  CandidateCareerProfile,
  OpportunityCategory,
  OpportunitySearchRequest,
  PolymorphicOpportunity,
  WorkMode,
} from '@/types/domain';
import { searchOpportunities } from '@/lib/api';
import { Badge } from '@/components/ui/Badge';
import { OpportunityDetailModal } from '@/components/ui/OpportunityDetailModal';

interface MarketSearchWorkspaceProps {
  candidateProfile: CandidateCareerProfile;
  candidateName: string;
}

export function MarketSearchWorkspace({
  candidateProfile,
  candidateName,
}: MarketSearchWorkspaceProps) {
  // Search parameters
  const [query, setQuery] = useState<string>('');
  const [location, setLocation] = useState<string>('');
  const [workMode, setWorkMode] = useState<WorkMode | ''>('');
  const [category, setCategory] = useState<OpportunityCategory | ''>('');
  const [maxExperience, setMaxExperience] = useState<string>('any');

  // Results & status
  const [opportunities, setOpportunities] = useState<PolymorphicOpportunity[]>([]);
  const [totalMatches, setTotalMatches] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Selected opportunity for detailed examination
  const [examiningOpportunity, setExaminingOpportunity] = useState<PolymorphicOpportunity | null>(null);

  // Perform intentional search
  const executeSearch = useCallback(
    async (pageIndex: number = 1) => {
      setIsLoading(true);
      setError(null);

      let maxExpMonths: number | undefined;
      if (maxExperience === 'entry') maxExpMonths = 24;
      else if (maxExperience === 'mid') maxExpMonths = 60;

      const req: OpportunitySearchRequest = {
        query: query.trim() || undefined,
        location: location.trim() || undefined,
        work_mode: (workMode as WorkMode) || undefined,
        category: (category as OpportunityCategory) || undefined,
        min_experience_max_months: maxExpMonths,
        page: pageIndex,
        page_size: 15,
      };

      try {
        const resp = await searchOpportunities(req);
        setOpportunities(resp.opportunities);
        setTotalMatches(resp.total);
        setCurrentPage(resp.page);
        setTotalPages(resp.total_pages);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Search failed';
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [query, location, workMode, category, maxExperience]
  );

  // Initial search on mount
  useEffect(() => {
    let isCancelled = false;
    async function loadInitial() {
      try {
        const resp = await searchOpportunities({ page: 1, page_size: 15 });
        if (!isCancelled) {
          setOpportunities(resp.opportunities);
          setTotalMatches(resp.total);
          setCurrentPage(resp.page);
          setTotalPages(resp.total_pages);
          setIsLoading(false);
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          const msg = err instanceof Error ? err.message : 'Search failed';
          setError(msg);
          setIsLoading(false);
        }
      }
    }
    loadInitial();
    return () => {
      isCancelled = true;
    };
  }, []);

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSearch(1);
  };

  const handleResetFilters = () => {
    setQuery('');
    setLocation('');
    setWorkMode('');
    setCategory('');
    setMaxExperience('any');
  };

  return (
    <div className="space-y-6">
      {/* Search Header Banner */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-400 border border-teal-200 dark:border-teal-800/80">
                <Search className="w-4 h-4" />
              </span>
              <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Market Opportunity Search
              </h1>
            </div>
            <p className="text-xs text-zinc-600 dark:text-zinc-400">
              Search and filter authentic career opportunities intentionally for {candidateName} using keyword, location, arrangement, and qualification criteria.
            </p>
          </div>

          <div className="text-right">
            <span className="text-xs font-mono font-semibold text-zinc-800 dark:text-zinc-200">
              {totalMatches} Opportunities Found
            </span>
          </div>
        </div>

        {/* Search & Filter Form */}
        <form onSubmit={handleFormSubmit} className="space-y-3 pt-2">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
            {/* Keyword Input */}
            <div className="md:col-span-5 relative">
              <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-3 pointer-events-none" />
              <input
                type="text"
                placeholder="Search by role title, employer, skill, or keyword..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-2 focus:ring-teal-500 placeholder:text-zinc-400"
              />
            </div>

            {/* Location Input */}
            <div className="md:col-span-3 relative">
              <MapPin className="w-4 h-4 text-zinc-400 absolute left-3 top-3 pointer-events-none" />
              <input
                type="text"
                placeholder="Location (city, country)..."
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-2 focus:ring-teal-500 placeholder:text-zinc-400"
              />
            </div>

            {/* Work Mode */}
            <div className="md:col-span-2">
              <select
                value={workMode}
                onChange={(e) => setWorkMode(e.target.value as WorkMode | '')}
                className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-2 focus:ring-teal-500 cursor-pointer"
              >
                <option value="">Any Work Mode</option>
                <option value="REMOTE">Remote</option>
                <option value="HYBRID">Hybrid</option>
                <option value="ON_SITE">On-Site</option>
              </select>
            </div>

            {/* Experience Level */}
            <div className="md:col-span-2">
              <select
                value={maxExperience}
                onChange={(e) => setMaxExperience(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-2 focus:ring-teal-500 cursor-pointer"
              >
                <option value="any">Any Experience</option>
                <option value="entry">Entry Level (&le; 2 yrs)</option>
                <option value="mid">Mid Level (&le; 5 yrs)</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-2">
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as OpportunityCategory | '')}
                className="px-2.5 py-1 text-xs rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 focus:outline-hidden cursor-pointer"
              >
                <option value="">All Categories</option>
                <option value="FULL_TIME_JOB">Full-Time Job</option>
                <option value="INTERNSHIP">Internship / Co-op</option>
                <option value="APPRENTICESHIP">Apprenticeship</option>
              </select>

              {(query || location || workMode || category || maxExperience !== 'any') && (
                <button
                  type="button"
                  onClick={handleResetFilters}
                  className="text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 hover:underline px-2 py-1"
                >
                  Clear Filters
                </button>
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-xs transition-colors disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Searching...</span>
                </>
              ) : (
                <>
                  <Search className="w-3.5 h-3.5" />
                  <span>Search Market</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Results Feed */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-800 dark:text-rose-300">
          Failed to load market opportunities: {error}
        </div>
      )}

      {isLoading ? (
        <div className="p-12 text-center space-y-3">
          <RotateCw className="w-6 h-6 animate-spin text-teal-600 mx-auto" />
          <p className="text-xs text-zinc-500 font-mono">Searching verified opportunities...</p>
        </div>
      ) : opportunities.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-3">
          <Briefcase className="w-8 h-8 text-zinc-400 mx-auto" />
          <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
            No Opportunities Match Your Current Search
          </h3>
          <p className="text-xs text-zinc-500 max-w-md mx-auto">
            Try adjusting your keyword query, clearing location filters, or running a Personalized Discovery session to discover fresh vacancies from real web search and ATS feeds.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4">
            {opportunities.map((opp) => {
              const origin: string =
                typeof opp.category_specific_attributes?.source_system === 'string'
                  ? opp.category_specific_attributes.source_system
                  : 'Web Search';
              const minExp = opp.eligibility_rules.min_experience_months;
              let expLabel = 'Not stated';
              if (minExp === 0) expLabel = 'Entry level';
              else if (minExp > 0) expLabel = `${minExp / 12}+ yrs exp`;

              return (
                <div
                  key={opp.opportunity_id}
                  className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-2xs hover:border-zinc-300 dark:hover:border-zinc-700 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 group"
                >
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[11px] font-semibold text-teal-700 dark:text-teal-400 bg-teal-50 dark:bg-teal-950/60 border border-teal-200/80 dark:border-teal-800/80 px-2 py-0.5 rounded-md">
                        {opp.eligibility_rules.opportunity_category.replace(/_/g, ' ')}
                      </span>
                      <Badge variant="verified" size="sm" mono>
                        {opp.eligibility_rules.work_mode}
                      </Badge>
                      <span className="text-[11px] text-zinc-500 font-mono">
                        Experience: {expLabel}
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                      {opp.title}
                    </h3>

                    <div className="flex items-center gap-3 text-xs text-zinc-600 dark:text-zinc-400 flex-wrap">
                      <div className="flex items-center gap-1 font-medium text-zinc-900 dark:text-zinc-200">
                        <Building2 className="w-3.5 h-3.5 text-zinc-500" />
                        <span>{opp.company_name}</span>
                        {opp.company_domain_verified && (
                          <span className="text-[10px] text-teal-600 dark:text-teal-400 font-mono">
                            (Verified)
                          </span>
                        )}
                      </div>

                      <span>•</span>

                      <div className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-zinc-400" />
                        <span>
                          {opp.eligibility_rules.location_city_country.length > 0
                            ? opp.eligibility_rules.location_city_country.join(', ')
                            : 'Remote / Unrestricted'}
                        </span>
                      </div>

                      <span>•</span>

                      <span className="text-[11px] font-mono text-zinc-500 capitalize">
                        Via {origin}
                      </span>
                    </div>

                    {/* Skill tags */}
                    {opp.skill_requirements.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap pt-1">
                        {opp.skill_requirements.slice(0, 6).map((req) => (
                          <span
                            key={req.canonical_skill_id}
                            className={`text-[11px] px-2 py-0.5 rounded-md border font-medium ${
                              req.is_mandatory
                                ? 'bg-zinc-100 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700 text-zinc-800 dark:text-zinc-200'
                                : 'bg-blue-50 dark:bg-blue-950/60 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300'
                            }`}
                          >
                            {req.skill_name}
                            {!req.is_mandatory && <span className="text-[9px] opacity-75 font-mono ml-1">pref</span>}
                          </span>
                        ))}
                        {opp.skill_requirements.length > 6 && (
                          <span className="text-[10px] text-zinc-400 font-mono">
                            +{opp.skill_requirements.length - 6} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-center gap-2 shrink-0 border-t sm:border-t-0 pt-3 sm:pt-0 border-zinc-100 dark:border-zinc-800">
                    <button
                      onClick={() => setExaminingOpportunity(opp)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-semibold text-zinc-700 dark:text-zinc-200 transition-colors"
                    >
                      <Eye className="w-3.5 h-3.5 text-teal-600" />
                      <span>Examine Role</span>
                    </button>

                    <a
                      href={opp.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-medium transition-colors"
                    >
                      <span>Direct Apply</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between p-4 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs">
              <span className="text-zinc-500 font-mono">
                Page {currentPage} of {totalPages}
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={currentPage <= 1 || isLoading}
                  onClick={() => executeSearch(currentPage - 1)}
                  className="px-3 py-1 rounded-md border border-zinc-200 dark:border-zinc-700 disabled:opacity-40 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                >
                  Previous
                </button>
                <button
                  disabled={currentPage >= totalPages || isLoading}
                  onClick={() => executeSearch(currentPage + 1)}
                  className="px-3 py-1 rounded-md border border-zinc-200 dark:border-zinc-700 disabled:opacity-40 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Opportunity Examination Modal */}
      {examiningOpportunity && (
        <OpportunityDetailModal
          opportunity={examiningOpportunity}
          candidateProfile={candidateProfile}
          onClose={() => setExaminingOpportunity(null)}
        />
      )}
    </div>
  );
}
