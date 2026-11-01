import {
  CandidateCareerProfile,
} from '@/types/domain';

export interface CandidateEntry {
  id: string;
  name: string;
  headline: string;
  role: string;
  summary: string;
  profile: CandidateCareerProfile;
}

export const CANDIDATES: Record<string, CandidateEntry> = {
  'maya-chen-junior': {
    id: 'maya-chen-junior',
    name: 'Maya Chen',
    headline: 'Junior ML & Backend Engineer',
    role: 'Backend & ML Engineer',
    summary: '24 months experience. Strong Python, FastAPI, PyTorch, and PostgreSQL. Target: Backend Engineer. Authorized: US.',
    profile: {
      user_id: 'maya-chen-junior',
      profile_version: 1,
      assessed_skills: [
        {
          canonical_skill_id: 'esco:python',
          skill_name: 'Python',
          proficiency_score: 8.5,
          confidence_score: 0.95,
          evidence_records: [
            {
              evidence_id: 'ev-m-1',
              source_type: 'RESUME_WORK_EXPERIENCE',
              extracted_snippet: 'Built async backend microservices in Python with FastAPI and PostgreSQL handling 5,000 req/sec.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.92,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:fastapi',
          skill_name: 'FastAPI',
          proficiency_score: 8.0,
          confidence_score: 0.90,
          evidence_records: [
            {
              evidence_id: 'ev-m-2',
              source_type: 'RESUME_WORK_EXPERIENCE',
              extracted_snippet: 'Designed and deployed high-throughput OpenAPI compliant endpoints with Pydantic schemas.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.90,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:pytorch',
          skill_name: 'PyTorch',
          proficiency_score: 7.2,
          confidence_score: 0.85,
          evidence_records: [
            {
              evidence_id: 'ev-m-3',
              source_type: 'RESUME_PROJECT',
              extracted_snippet: 'Trained and tuned computer vision classification models on custom datasets using PyTorch.',
              observed_at: '2025-11-20T00:00:00Z',
              verifiability_weight: 0.88,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:postgresql',
          skill_name: 'PostgreSQL',
          proficiency_score: 7.5,
          confidence_score: 0.88,
          evidence_records: [
            {
              evidence_id: 'ev-m-4',
              source_type: 'RESUME_WORK_EXPERIENCE',
              extracted_snippet: 'Designed relational schemas, foreign keys, and indexes for analytical telemetry data.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.85,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:docker',
          skill_name: 'Docker',
          proficiency_score: 7.0,
          confidence_score: 0.82,
          evidence_records: [
            {
              evidence_id: 'ev-m-5',
              source_type: 'RESUME_PROJECT',
              extracted_snippet: 'Containerized multi-service development environments using Docker Compose.',
              observed_at: '2025-12-05T00:00:00Z',
              verifiability_weight: 0.80,
            },
          ],
        },
      ],
      target_career_paths: [
        {
          occupation_code: '15-1252.00',
          title: 'Backend Software Engineer',
          relationship_type: 'TARGET',
          adjacency_similarity: 1.0,
          missing_core_skill_ids: ['esco:distributed-systems', 'esco:redis'],
        },
      ],
      adjacent_career_paths: [
        {
          occupation_code: '15-1251.00',
          title: 'Machine Learning Engineer',
          relationship_type: 'ADJACENT',
          adjacency_similarity: 0.85,
          missing_core_skill_ids: ['esco:mlops', 'esco:cuda'],
        },
      ],
      eligibility_constraints: {
        authorized_country_codes: ['US'],
        requires_visa_sponsorship: false,
        highest_degree_level: 'BACHELORS',
        is_currently_enrolled_student: false,
        total_full_time_experience_months: 24,
        allowed_opportunity_categories: ['FULL_TIME_JOB'],
        allowed_work_modes: ['HYBRID', 'REMOTE'],
        preferred_locations: ['San Francisco, CA', 'Remote'],
      },
      overall_profile_confidence: 0.91,
    },
  },

  'usr_cand_student_02': {
    id: 'usr_cand_student_02',
    name: 'Jordan Patel',
    headline: 'Final Year CS Student & Intern Candidate',
    role: 'Student Software Engineer',
    summary: 'Graduating May 2026. Strong TypeScript, React, Python, and SQL. Seeking New Grad & Internship roles. Authorized: US.',
    profile: {
      user_id: 'usr_cand_student_02',
      profile_version: 1,
      assessed_skills: [
        {
          canonical_skill_id: 'esco:typescript',
          skill_name: 'TypeScript',
          proficiency_score: 8.0,
          confidence_score: 0.88,
          evidence_records: [
            {
              evidence_id: 'ev-j-1',
              source_type: 'RESUME_PROJECT',
              extracted_snippet: 'Built full-stack React and Next.js web applications in TypeScript with Tailwind CSS.',
              observed_at: '2026-02-01T00:00:00Z',
              verifiability_weight: 0.85,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:python',
          skill_name: 'Python',
          proficiency_score: 7.5,
          confidence_score: 0.85,
          evidence_records: [
            {
              evidence_id: 'ev-j-2',
              source_type: 'ACADEMIC_TRANSCRIPT',
              extracted_snippet: 'Completed Advanced Data Structures and Operating Systems projects in Python.',
              observed_at: '2025-12-15T00:00:00Z',
              verifiability_weight: 0.95,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:react',
          skill_name: 'React',
          proficiency_score: 8.0,
          confidence_score: 0.90,
          evidence_records: [
            {
              evidence_id: 'ev-j-3',
              source_type: 'RESUME_PROJECT',
              extracted_snippet: 'Developed interactive data dashboards with client-side state management and responsive charts.',
              observed_at: '2026-01-20T00:00:00Z',
              verifiability_weight: 0.85,
            },
          ],
        },
      ],
      target_career_paths: [
        {
          occupation_code: '15-1252.00',
          title: 'Software Engineer',
          relationship_type: 'TARGET',
          adjacency_similarity: 1.0,
          missing_core_skill_ids: ['esco:ci-cd', 'esco:docker'],
        },
      ],
      adjacent_career_paths: [
        {
          occupation_code: '15-1254.00',
          title: 'Frontend Web Developer',
          relationship_type: 'ADJACENT',
          adjacency_similarity: 0.88,
          missing_core_skill_ids: ['esco:web-accessibility'],
        },
      ],
      eligibility_constraints: {
        authorized_country_codes: ['US'],
        requires_visa_sponsorship: false,
        highest_degree_level: 'HIGH_SCHOOL',
        is_currently_enrolled_student: true,
        expected_graduation_date: '2026-05-15',
        total_full_time_experience_months: 6,
        allowed_opportunity_categories: ['INTERNSHIP', 'FULL_TIME_JOB'],
        allowed_work_modes: ['HYBRID', 'REMOTE', 'ON_SITE'],
        preferred_locations: ['New York, NY', 'Remote'],
      },
      overall_profile_confidence: 0.86,
    },
  },
};

export const DEFAULT_CANDIDATE_ID = 'maya-chen-junior';
