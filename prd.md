# PRD: Personal AI Job Hunter (codename: sweet-catcher)

## Problem

Searching for jobs manually is repetitive, scattered, and hard to measure. The user has to visit many sites, apply different filters, judge whether each role is worth pursuing, adapt their resume, track applications, and remember follow-ups. Technology job descriptions make this worse: they are long, full of redundant requirements, often have mislabeled seniority, and use ambiguous language — so it is hard to know whether to apply, which experiences to highlight, which requirements are truly critical, which gaps hurt the application, which skills recur across the market, and what state each application is in. The result is wasted time, inconsistent decisions, and almost no visibility into one's own job-search funnel.

## Product Vision

A personal, AI-assisted application copilot that discovers, triages, explains, prepares, and tracks job applications end to end — transparent and human-controlled, never an opaque job-spam bot.

## Goals and Success Metrics

| Goal | Metric | Target |
|------|--------|--------|
| Automate daily job discovery across configured sources | Successful daily runs; jobs discovered per day; source error rate | Daily run completes with at least one real source plus the mock connector operational; source failures isolated, pipeline survives |
| Reduce manual triage effort | Share of new jobs auto-analyzed; fit-score coverage | 100% of newly discovered jobs receive an explainable fit score and a recommendation |
| Surface high-fit opportunities reliably | Recommendation distribution; number of high-fit jobs | Every analyzed job is classified as must_apply / apply / consider / low_priority / reject, with confidence and rationale |
| Prepare tailored resumes without fabrication | Unsupported claims in delivered resume; claim-validation pass rate | Zero unsupported claims in any approved tailored resume — every claim backed by master-profile evidence |
| Maintain full funnel visibility | Status changes recorded; follow-up suggestions issued | Every status change recorded as an event; follow-up suggested after 7 business days without response |
| Operate locally at zero mandatory API cost | Mandatory paid-API dependencies; local startup | Zero mandatory paid-LLM dependencies; full stack starts via Docker Compose |
| Keep AI outputs reliable | Invalid-JSON rate; retry count | All agent outputs schema-validated; invalid outputs retried up to 3 times before a deterministic fallback |

## Scope

### In Scope (MVP)

- Create, edit, and version a structured master professional profile.
- Configure global job-search criteria.
- Daily job collection from at least one real source plus a mock connector.
- Normalization of jobs from different sources into a common schema.
- Deduplication of jobs.
- Reliable relational persistence as the source of truth.
- Explainable fit analysis: requirement extraction, real-seniority inference, configurable scoring, recommendation, and positive/negative signals.
- Tailored-resume suggestion with mandatory claim validation and a master-vs-tailored diff.
- Application funnel: status state machine plus full event history.
- Basic dashboard, job filters, and basic market analytics.
- Tasks, follow-ups, and notifications (dashboard, with optional email).
- Minimal structured logging and observability.
- Local execution via Docker Compose using open-source models.

### Out of Scope

Deferred features (not in V1):

- Full multi-user support and any billing.
- Browser extension and native mobile app.
- Automatic application submission.
- Deep authenticated LinkedIn integration.
- Advanced recommendations based on real recruiter feedback.

Explicit non-goals (the system must never do these, in any version):

- Submit applications automatically without human approval.
- Invent experiences, projects, certifications, or skills.
- Bypass authentication, CAPTCHAs, paywalls, rate limits, or platform terms of use.
- Promise hiring or approval, or replace human judgment.
- Auto-register on job sites without explicit authorization.
- Modify the master profile without user confirmation.
- Depend on paid LLMs as a mandatory dependency.
- Store credentials in plaintext.

## Users and Stakeholders

- **Primary user — junior tech job seeker** (AI/ML, software, data, backend, automation, and adjacent areas). Needs to discover relevant roles with far less manual effort, understand what helps or hurts each application, adapt their resume per job truthfully, and keep control of the funnel and follow-ups. Success: more high-fit applications submitted with less effort and clear pipeline visibility.
- **Reviewer / approver** (the same person, in a review role). Needs to review and approve AI-generated materials — tailored resume, fit analysis, risks, optional cover letter — before anything is marked ready, and to audit how decisions were made. Success: nothing sensitive happens without explicit approval, and every automated decision is transparent and traceable.
- **Operator / self-hoster** (the same person, in an ops role). Needs the system to run locally via Docker Compose with open-source models, reliable persistence, and minimal operational burden. Success: reproducible local startup, source failures isolated, and structured logs that make troubleshooting straightforward.

## Functional Requirements

**A. Master profile and resume data**
1. The system shall let the user create, edit, and version a structured master profile (experiences, projects, technical and interpersonal skills, education, certifications, languages, links, and job preferences), recording every relevant change as a new version or audit-log entry.
2. The system shall let the user import master-profile data from pasted text, PDF, DOCX, Markdown, or structured JSON, supporting at minimum structured manual entry in V1.

**B. Search criteria and job discovery**
3. The system shall let the user configure global search criteria, including keywords, allowed and blocked seniorities, allowed and blocked areas, countries and cities, work mode, minimum salary, accepted languages, required and desired technologies, blocked and favorite companies, active sources, and run frequency.
4. The system shall run scheduled discovery (default daily, user-adjustable) that loads active criteria, invokes source connectors, stores raw payloads, normalizes results, deduplicates, persists new jobs, updates existing ones, and enqueues fit analysis.
5. The system shall collect jobs through pluggable source connectors that implement a common interface, classify their errors, and isolate failures so that one failing source does not stop the pipeline.
6. The system shall let the user add a job manually (URL, title, company, description, notes) and analyze it identically to auto-collected jobs.

**C. Normalization and deduplication**
7. The system shall normalize each job from any source into a common internal schema (title, company, source, URL, description, location, work mode, inferred seniority, contract type, publication and discovery dates, required and desired requirements, responsibilities, benefits, salary, technologies, languages, status, and raw content).
8. The system shall deduplicate jobs using canonical URL, source external ID, normalized description hash, and title-plus-company-plus-location similarity; it shall preserve the history of alternative sources and flag probable duplicates by confidence threshold.

**D. Job analysis and fit**
9. The system shall extract structured requirements from each job (hard and soft skills, minimum experience, education, languages, responsibilities, core and peripheral technologies, required versus desired, and alignment signals), each with a confidence value.
10. The system shall infer each job's real seniority independently of its title — using required years of experience, autonomy, scope, leadership mentions, and complexity — and raise an alert when title and requirements disagree.
11. The system shall compute a configurable fit score from 0 to 100 from weighted components (skill, seniority, experience, location, work mode, language, domain, education) minus penalties, applying the defined score caps.
12. The system shall accompany every score with an explanation containing a summary, top strengths, top gaps, risks, a recommendation, and the evidence used.
13. The system shall classify each job into a recommendation of must_apply, apply, consider, low_priority, or reject, with confidence and rationale.
14. The system shall list the factors that favor the application, each with a description, estimated impact, supporting evidence, and the related master-profile section.
15. The system shall list the factors that hurt the application, each with a description, severity, suggested mitigation, and the missing or weak evidence.

**E. Tailored resume and anti-fabrication**
16. The system shall generate a job-tailored resume that may reorder, regroup, and rephrase real content but shall never invent experiences, alter dates, create certifications, fabricate metrics, or inflate seniority; every professional claim must be backed by master-profile evidence, and any unsupported claim is removed or rewritten as a gap.
17. The system shall produce a diff between the master resume and each tailored resume, showing what was included, removed, or rewritten, and why.
18. The system shall require explicit human approval of the tailored resume, fit analysis, risks, and optional cover letter before an application is marked ready.

**F. Application funnel**
19. The system shall track each application through the defined status set, persisting status, priority, fit score, recommendation, linked materials, and timestamps.
20. The system shall enforce a state machine that permits only valid status transitions and rejects invalid ones.
21. The system shall record every status change as an event capturing previous status, new status, date, origin, note, and actor.
22. The system shall create tasks such as review resume, apply to a job, send follow-up, prepare interview, and deliver technical test.
23. The system shall suggest follow-ups after configurable inactivity, defaulting to 7 business days for applied, interviewed, or test-submitted states.

**G. Dashboard, filters, and analytics**
24. The system shall present a dashboard with key metrics: jobs discovered today and this week, high-fit jobs, open and submitted applications, interviews, rejections, response rate, upcoming tasks, top technologies, and top gaps.
25. The system shall let the user filter jobs by company, title, fit score, status, location, work mode, seniority, source, date, technology, recommendation, and open or closed application.
26. The system shall compute market analytics: most-requested technologies, most-common requirements and seniorities, recurring companies and locations, and the user's recurring gaps.
27. The system shall suggest study priorities derived from recurring gaps.

**H. Export, attachments, and audit**
28. The system shall export jobs, applications, analyses, tailored resumes, and metrics as CSV and JSON, and resumes as PDF.
29. The system shall store attachments: submitted resume, cover letter, original job description, technical test, feedback, and optional screenshots.
30. The system shall record an audit entry for every automated action, capturing timestamp, input, output, responsible agent, model used, prompt version, profile version, confidence, and errors.

## Non-Functional Requirements

1. **Single-user:** V1 is optimized for a single user.
2. **Modularity and low coupling:** each module (collection, parsing, normalization, analysis, scoring, resume, application, dashboard, notifications) is replaceable through clear interfaces.
3. **Strong typing:** all code is strongly typed (for example, type hints with Pydantic DTOs in Python).
4. **Testability:** each component has unit tests, written before implementation (test-first, per the standards).
5. **Observability:** structured JSON logs are mandatory, with the defined fields (timestamp, level, service, module, run_id, job_id, application_id, source, duration, error type, trace id); metrics and tracing (OpenTelemetry) are recommended.
6. **Security:** secrets come from environment variables; `.env` is never committed; external credentials are encrypted; credentials are never stored in plaintext; logs must not expose tokens, passwords, cookies, or full personal documents.
7. **Reliable persistence:** a relational database is the single source of truth.
8. **Idempotency:** recurring jobs are idempotent, using a discovery run id, deduplication keys, and analysis and resume-variant idempotency keys.
9. **Fault tolerance:** a single source or single job failure must not stop the batch or pipeline; jobs are retryable.
10. **Performance and capacity (initial):** at least 10 sources, 5,000 stored jobs, 500 jobs analyzed per day, and 1 user.
11. **Portability:** full local execution via Docker Compose.
12. **Cost:** the system operates with no mandatory paid-API dependency.
13. **Privacy:** personal data stays local by default; exports happen on demand.
14. **AI-output reliability:** agent outputs are validated against schemas, with retries (up to 3) and a deterministic fallback where applicable.

## Technical Constraints

1. **Framework.Standard is mandatory and binding.** All development follows the standards in `.standards/` (the standards submodule), which supersede any stack, directory-structure, naming, or style preference expressed in this PRD. Where this PRD and the standard conflict, the functional requirements here are preserved and the implementation is adapted to the standard, with the conflict documented.
2. **Open-source, local or self-hosted models only.** No mandatory dependency on paid LLM APIs; model serving runs on a local runtime (the exact runtime is an open question).
3. **Local execution via Docker Compose is required.**
4. **A relational database is the system of record.**
5. **Human approval is mandatory before any application is submitted;** the system never auto-submits.
6. **No fabrication of professional information;** claim validation against master-profile evidence is mandatory.
7. **Compliance:** the system must not bypass CAPTCHAs, authentication, paywalls, or rate limits, and must respect site terms and robots directives where applicable; it prefers official APIs, public feeds, and structured pages over fragile scraping, using browser automation only when necessary.
8. **All output in English** (identifiers, comments, documentation, commits), per the standards.

Recommended-but-not-yet-decided technologies (for example Python/FastAPI, PostgreSQL with pgvector, Redis, a background-worker library, and a local inference runtime) are intentionally left out of this list and tracked under Open Questions, to be fixed at the SPEC stage per Framework.Standard.

## Open Questions

Each item is to be resolved by the **project owner/developer** at the SPEC stage, in line with Framework.Standard:

1. Backend framework — FastAPI or an alternative?
2. Frontend — Next.js for a fuller product, or a simpler MVP option such as Streamlit?
3. Background workers — Dramatiq, Celery, or another?
4. Local inference runtime — Ollama or vLLM for the initial environment?
5. Vector store — pgvector (integrated in PostgreSQL) or a dedicated store such as Qdrant?
6. PDF export — WeasyPrint, Playwright, or another library?
7. Authentication — simple local auth, or no auth in V1?
8. Notifications — internal-only (dashboard), or also email in V1?
9. First real source connector — which source ships first in V1 (the standard prioritizes public-API and simple-HTML sources such as Greenhouse, Lever, or Ashby)?
