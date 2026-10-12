# Select Papers and Reviews for a Learning Goal

Use this workflow to find introductory papers, recommend reviews, learn a technology, or explore a specific research question. Search with tools actually available on the host. Daily discovery stays in its existing funnel; this is bounded learning-oriented paper selection.

## 1. Turn the request into a decision question

Reuse the current request, conversation in the same task, and authorized reading background. Do not guess the advisor's research direction, course, or the user's expertise. Record the current intent (understand a field, learn a technology, address a research question, or catch up on recent work), the question to answer, existing background, prerequisite burden, specified scope, and exclusions. Usually one sentence is enough. Ask only when missing information would materially change the recommendation. A previous search's topic and ranking do not automatically become current preferences.

Example: The user understands Transformers and wants to learn about Agent memory, but has not chosen an implementation approach. Frame the decision as “first understand what memory stores, how it is updated and retrieved, and how it is evaluated,” without assuming vector retrieval is the only option.

## 2. Search a little and inspect candidate contents early

1. Split the request into concepts such as objects, mechanisms, and goals; add synonyms and abbreviations. Search for major mechanisms separately before combining terms, so an AND query does not become too narrow.
2. For a beginner, first find overviews and basic taxonomies, then narrow by category, key term, or gap. When the question is already specific, search the relevant mechanism or setting directly. For foundational work, follow references from verified reviews; for time-sensitive tasks, prioritize recent formal publications and current versions. The number of search rounds need not be fixed.
3. Match the query to the tool: use short natural-language queries for general search and only Boolean syntax supported by the current database. Record the actual source, date, and query; do not pass web-search syntax directly to an API.
4. Use arXiv or author pages to identify specific versions; use official venue records to verify identity and publication track. Aggregators and project lists may surface candidates, but verify important facts against primary sources.
5. Screen by title and abstract, then inspect the paper sections that most affect selection for any primary reading. For a paper, check the question, method, key comparison, and limitations. For a review, check scope, taxonomy definitions, one substantive comparison, literature cutoff, and limitations. If only the abstract is available, keep it as a candidate; do not claim the body was quality-checked.

Topic-based selection does not use the daily three-day window. See the next section for common recency ranges and priority orders for foundational versus time-sensitive topics. Confirm the relationship between arXiv and the formal publication. Remove duplicate results, but do not merge evidence from different versions. Report search failures, limited samples, and no-results cases separately.

Stop when the evidence is sufficient to answer the selection question and another narrowing round adds no substantively complementary content. Continue only to address a concrete gap. The number of papers or databases does not prove search completeness; do not expand the scope just to fill a list.

## 3. Check shared quality criteria and reorder priorities by context

Relevance, reliable identity, and evidence that supports the conclusion are baseline requirements. Order venue reputation, paper-level impact, recency, prerequisite burden, and material availability according to the current reader and task; do not use a fixed weighted score. With no special goal, a common starting point is reliable leading venues, work from the past three years, and credible evidence of impact. These are starting preferences, not hard requirements for every task.

| Current context | Suggested priority order | Effect on recommendations |
|---|---|---|
| General field orientation or paper/review recommendations | Fit to the question and content quality → reliable leading venue and past three years → verified paper-level impact → reading burden | Start with recent reliable work; state venue, year, and citations, and explain trade-offs when a criterion cannot be met. |
| Foundational field, core concepts, or methods | Foundational value and fit → venue reputation and long-term citations → clarity for the reader → year | Older foundational work may be the primary reading; use a recent review to complete the map. Do not replace the best original work just to meet a three-year window. |
| Application, fast-changing technology, or recent progress | Fit to current task/environment and recency → body evidence and conditions → venue reputation and citation impact | The past three years are usually a necessary window; shorten it further when change is rapid and state the cutoff. Do not automatically downgrade new work for having few citations; label unpublished work accurately. |
| Implementation, reproduction, or checking a specific claim | Matching method/settings → actual version and evidence → available code/data and conditions → venue, impact, year | Choose the original source that answers or enables the current task; do not substitute another paper solely because it is more famous or newer. |

These are decision examples; combine or adjust them for the actual task. State what matters most in this search before screening. The user's explicit hard requirements for venue, year, citation threshold, and so on always take precedence. If the user requires all three criteria simultaneously, do not reinterpret them as “any one of the three.”

| Dimension | Common high-quality starting point | Verification and scope |
|---|---|---|
| Relevance and readable evidence | Directly answers the selection question; key body sections of the primary-reading candidate have been checked | Exclude famous but irrelevant work. If only an abstract was checked, retain it as “candidate pending verification,” not as a verified primary reading. |
| Venue | For computer science, first consider current CCF A formal journals/conferences; in other fields, use an authoritative, sourced list or a user-provided list | Check reputation for the discipline and task; being outside a list does not mean low quality. Record journal/conference type, list version, and actual publication track. Do not present preprints, Workshop, Demo, Short, or Findings as formal full papers in a list. Do not assume a permanent ranking. |
| Recency | A common starting window is formal publications from the current year and previous two years, ending on the search date | On 2026-10-12, this window is 2024-01-01 through 2026-10-12. Do not apply it to foundational learning; narrow or state a cutoff for time-sensitive work. Record arXiv first-posted date, formal publication date, and literature cutoff separately. A new upload does not make an old study new. |
| Citation impact | Check paper-level citations, source, and query date; when normalized data exists, prefer influential papers of the same type, year, and field | OpenAlex citation_normalized_percentile top 10% can signal high impact; it is not a universal quality threshold. Do not add counts from different databases or select the maximum. Mark missing data as unknown, not zero. |
| Actual content quality | Mechanism is clear, key comparisons/settings support the claim, and limitations can be located | The three metadata dimensions above do not replace reading the body. Resolve retractions, major corrections, or identity conflicts before recommending. |

Choose the primary reading according to this search's priorities. For foundational learning, it may be older; for a recent application, it may be a new, well-supported paper with few citations but a matching setting. **Foundational classic**, **recent candidate**, and **preprint** describe source or maturity; they are not fixed secondary recommendation tiers. Explain why the paper fits and which criteria are weaker or unknown. Do not imply it satisfies all three criteria, and do not relax hard conditions or body-quality requirements to fill a quota.

If the user sets hard requirements (for example, only formal CCF A full papers from the past three years with at least a given number of citations), filter by those requirements first, then rank by relevance. If the strict result is empty or citation counts cannot be checked, report zero verified primary readings; a separate pending-verification list is allowed. Do not quietly count classic exceptions or preprints as strict matches. Few citations on a new paper may reflect time to accumulate citations, but do not waive an explicit user threshold.

Define the paper-level meaning of “citation rate” first: cumulative citations, recent annual growth, and same-year/same-field percentile are different measures. If only total citations and publication year are available, a rough cumulative-citations/(current year - publication year + 1) value within the same field and paper type may be useful. State that it is not field-normalized impact; do not annualize a paper published only weeks ago. Prefer to save source values and their definitions instead of only a self-calculated ranking.

Metadata sources in practice: verify venue and track from the publisher, conference proceedings, or official OpenReview acceptance record; cross-check DOI identity with Crossref and computer-science bibliography information with dblp; use OpenAlex for citations and normalized same-year/field impact, with Semantic Scholar as a cross-check. Record the sources actually checked and any gaps. dblp does not provide citation rankings; Crossref metadata does not prove peer review is complete. If an API is unavailable, use an official page. Do not create an account or treat network failure as zero citations. See [Method Sources](method-sources.md) for source and scope details.

## 4. Judge quality from content and fit from the goal

| Work | Inspect | Decision for the reader |
|---|---|---|
| Research paper | Clear question/contribution; explainable mechanism; comparisons, settings, and evidence that support claims; limits of applicability | What concept, method, or evaluation approach can the reader learn? What prerequisites are needed now? |
| Review | Clear scope and cutoff; defined taxonomy; comparison among branches; stated controversies and limitations | Is a broad map needed first or a specific topic? Does it duplicate existing reading? |

Judge identity reliability, content quality, relevance to the goal, and material availability separately. Venue, citation count, and year can inform selection but do not replace content checks; do not disguise an overall score as objective quality. Label preprints accurately. If the source is unavailable, state its relevance and the checks that could not be completed.

## 5. Recommendations

Usually start with one primary reading and a few complementary papers; adjust to the question, time, and user request. Do not pad a short list. For each paper, provide the exact title and original source, version actually read, reason for selection, what the reader can learn, differences from other candidates, necessary prerequisites, and scope of material checked. Reasons should point to the paper's taxonomy, method, or evidence, not merely say “worth exploring” or “broadens perspective.”

Keep an internal candidate table with the question, priority order, hard requirements, title, DOI/arXiv ID, actual version, matched question, formal and first-posted years, venue type/track/list source, citation count and normalized signal/source/date, body sections checked, primary-reading status, source/maturity label, and trade-off rationale. Include enough venue, year, and impact information in the response for a reader to verify a recommendation. Mark unknown fields accurately; do not imply verification through wording. Keep the full search record for later review but do not paste logs into the response. Save records only when the user requests it or project conventions require it; do not initialize a personal ledger for every candidate or save this search's choices as persistent research preferences.

### Trade-off example (not a result of an actual search)

If candidate A covers writing, managing, and retrieving memory and its relevant body sections have been checked, it may be the primary reading. B discusses retrieval alone and may complement it. C is newer but focuses mainly on a financial application; explain why it is deferred when the current goal is to learn the taxonomy. Candidate names, citation counts, and section locations must come from a real search; do not treat A/B/C as actual papers.

After a paper is selected, use the single-paper reading workflow. For a complete review guide, switch to survey-protocol.
