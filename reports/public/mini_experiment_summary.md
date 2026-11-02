# BehaviourLens Mini-Experiment Summary

**Preliminary aggregate demonstration results. These observations are not statistically significant evidence.**

## Research question
Do adjustable AI persona parameters produce stable, measurable behavioural differences, and do those differences correspond to genuine human usability friction?

## Experimental setup
- A and B use the same validated, ordered product catalogue and actions.
- A includes S1, S3, S7, S8, and S10; B improves those interface details.
- Completed mini-experiment tasks are T1 product discovery and T5 cart editing.
- AI outcomes are verified from the rendered cart; unverified attempts are reported separately.
- Persona summaries are grouped by actor, version, task, persona, and model.

## Aggregate results
- Recorded sessions included: 15
- Each line reports sample counts, verified success rate, and mean behavioral measures for that condition.

## Condition comparisons
- ai | A | T1 | high_experience | gpt-6-luna: 1/1 verified successes; 0 unverified; mean actions 7.0; mean duration 10.91s; mean retries 1.0.
- ai | A | T1 | low_digital_experience | gpt-6-luna: 1/1 verified successes; 0 unverified; mean actions 7.0; mean duration 12.0s; mean retries 1.0.
- ai | A | T1 | low_patience | gpt-6-luna: 1/1 verified successes; 0 unverified; mean actions 7.0; mean duration 11.0s; mean retries 1.0.
- ai | A | T1 | low_risk_tolerance | gpt-6-luna: 1/1 verified successes; 0 unverified; mean actions 7.0; mean duration 12.0s; mean retries 1.0.
- ai | A | T1 | neutral_baseline | gpt-6-luna: 1/3 verified successes; 0 unverified; mean actions 15.67; mean duration 51.0s; mean retries 3.0.
- ai | A | T5 | neutral_baseline | gpt-6-luna: 1/1 verified successes; 1 unverified; mean actions 4.5; mean duration 7.5s; mean retries 0.0.
- human | A | T1 | human_participant | unknown: 1/1 verified successes; 0 unverified; mean actions 3.0; mean duration 53.0s; mean retries 2.0.
- human | A | T5 | human_participant | unknown: 1/3 verified successes; 0 unverified; mean actions 5.0; mean duration 29.0s; mean retries 2.33.
- human | B | T1 | human_participant | unknown: 1/1 verified successes; 0 unverified; mean actions 1.0; mean duration 15.0s; mean retries 0.0.
- human | B | T5 | human_participant | unknown: 1/1 verified successes; 0 unverified; mean actions 1.0; mean duration 8.0s; mean retries 0.0.

## Limitations
- These are small, local demonstration samples; no statistical-significance claim is made.
- Behavioral indicators do not establish subjective frustration or usability causality.
- Aggregates omit session identifiers, run IDs, event payloads, timestamps, screenshots, and model transcripts.
