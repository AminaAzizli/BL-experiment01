# Stage 0: Research design draft

This file captures the initial research design for BehaviourLens before deeper implementation.

## Core research question

Do adjustable AI persona parameters produce stable, measurable behavioural differences, and do those differences correspond to genuine human usability friction?

## Ground truth structure

- Tier 1: seeded UX issues intentionally planted in Version A.
- Tier 2: human-validated issues after pre-registered comparison rules.
- Decoys: design elements that are good in both versions and should not be reported as problems.

## Seeded issue register (draft)

- S1: vague filter label
- S2: ambiguous delivery-form instructions
- S3: validation error without explanation
- S4: inconsistent genre labels
- S5: poor filter discoverability
- S6: weak add-to-cart feedback
- S7: low-contrast Add to Cart button
- S8: quantity change requires hidden update step
- S9: unhelpful empty search results
- S10: unclear checkout button label

## Decoy register (draft)

- D1: Search box
- D2: Product card layout
- D3: Price display
- D4: Breadcrumb navigation
- D5: Cart remove button
- D6: Name and contact field labels
- D7: Pagination controls

## Task states

- T1: Discovery
- T2: Delivery
- T3: Cart confirmation
- T4: Search
- T5: Cart edit

Each task starts from a defined preloaded state and resets between runs so that task contamination is prevented.

## A/B parity principle

Version A and Version B must share the same products, descriptions, prices, and actions. Only the intended UX features may change, and the parity check must confirm this before the pilot begins.

## Persona configuration draft

- Neutral baseline
- Profile 1: low digital experience
- Profile 2: low patience
- Profile 3: low risk tolerance
- Profile 4: high digital experience + high patience + high risk tolerance

## Pre-registered analysis attention points

- Compare A vs B friction on seeded issues.
- Measure false positives on Version B and decoys.
- Separate task success from UX evaluation.
- Use human difficulty and coder confidence in the scoring process.
- Keep the issue register separate from agent prompts and the judge inputs.

## Immediate implementation note

The first implementation stage includes the backend foundation, Docker support, and a bookstore shell that demonstrates the A/B parity structure. The full human and AI experimental pipeline remains staged after that scaffold.
