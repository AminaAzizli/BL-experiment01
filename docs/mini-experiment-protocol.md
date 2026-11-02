# BehaviourLens Mini-Experiment Protocol

## Purpose

This local proof-of-concept explores the question: “Do adjustable AI persona parameters produce stable, measurable behavioural differences, and do those differences correspond to genuine human usability friction?” It compares observable behavior, not a participant's unobservable thoughts.

## Conditions

The bookstore has two interface conditions:

- **Version A** includes five implemented usability differences: the vague genre-filter label “Refine” (S1), generic validation guidance (S3), a low-contrast add button (S7), a quantity change that requires an additional Update action (S8), and the ambiguous checkout label “Continue” (S10).
- **Version B** improves those interface details.

Both conditions use exactly the same ordered catalogue: product IDs, names, authors, descriptions, prices, ratings, review counts, stock, and actions. The API computes a parity result from the actual data. Session creation is refused if the check fails.

## Tasks

**T1, Product Discovery:** “Find the book Signal in the Dust and add it to your shopping cart.” The cart starts empty. Search is blank. Success requires the expected product to be in the final cart.

**T5, Cart Editing:** “Change the quantity of the book in your cart from one to two and verify that the cart total has been updated.” One catalogue item starts at quantity one. Success requires quantity two and a subtotal equal to twice that item's unit price.

Each AI repetition has a new session and browser context. Manual runs reset search, filters, and cart for the selected task. T2–T4 remain draft tasks and are not part of this mini-experiment.

## Participants and agent personas

A manual browser run is recorded as `human` only after the user confirms the local consent checkbox. The participant API stores no background responses for this demo. Use fictional form data; interaction event payloads do not store names, phone numbers, addresses, or input values.

AI runs use actor type `ai`, with model, persona name, persona parameters, version, task, and run ID saved to each session. The five persona profiles are `neutral_baseline`, `low_digital_experience`, `low_patience`, `low_risk_tolerance`, and `high_experience`. Personas change exploration and verification strategy only. All personas receive the same task wording for a given task.

The agent uses Playwright against the rendered local page and the OpenAI Responses API. Its browser tool set is restricted to page inspection, accessible-element actions, cart inspection, screenshots, and local navigation. Non-local requests are blocked. The agent does not receive the seeded issue list or a target click sequence.

## What is recorded

The event queue sends stable-ID batches to the API. Events include the event type, task ID, event timestamp, and structured behavioral payload; the session ID is in the event endpoint path. Duplicate retries are ignored by a per-session unique key.

Observed measures include task outcome, completion time, browser action count, retries, errors, search submissions, filters, product exposures, cart changes, validation errors, and screenshots for AI runs. Repeated actions, retries, and validation errors are behavior indicators. They do not automatically mean frustration.

## Evaluation

Task success is checked independently from the agent's text. T1 checks that `book-2` (Signal in the Dust) is present in the cart. T5 checks that the one starting item has quantity two and that the visible subtotal is mathematically correct.

The Tier 1 register contains only S1, S3, S7, S8, and S10 because these are the issues currently implemented in the UI. The deterministic evaluator requires relevant recorded evidence and returns `detected`, `not_detected`, or `insufficient_evidence`; it can abstain. Seeded issues are not the same as Tier 2 usability findings, which require actual evidence review and human validation. Decoys remain separate and should not be called seeded issues.

## Analysis and limitations

Compare success, duration, actions, retries, and errors by version, task, actor, and persona. Keep task performance separate from issue evaluation. The report is descriptive and preliminary. The small number of local demonstrations cannot establish statistical significance, stable persona effects, or human-AI equivalence. Do not interpret a single repeated click as evidence of frustration.

This protocol describes a local software demonstration, not ethics approval or permission to recruit participants. Do not expose the app publicly or use real personal data, accounts, payment details, or purchasing functionality.
