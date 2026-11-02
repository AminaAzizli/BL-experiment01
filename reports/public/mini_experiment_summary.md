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
- Recorded sessions included: 75
- Each line reports sample counts, verified success rate, and mean behavioral measures for that condition.

## Condition comparisons
- ai | A | T1 | high_experience | gpt-6-luna: 4/4 verified successes; 0 unverified; mean actions 6.75; mean duration 9.99s; mean retries 0.75.
- ai | A | T1 | low_digital_experience | gpt-6-luna: 4/4 verified successes; 0 unverified; mean actions 6.75; mean duration 11.54s; mean retries 0.75.
- ai | A | T1 | low_patience | gpt-6-luna: 4/4 verified successes; 0 unverified; mean actions 7.0; mean duration 10.73s; mean retries 1.0.
- ai | A | T1 | low_risk_tolerance | gpt-6-luna: 4/4 verified successes; 0 unverified; mean actions 6.75; mean duration 11.14s; mean retries 0.75.
- ai | A | T1 | neutral_baseline | gpt-6-luna: 4/6 verified successes; 0 unverified; mean actions 11.0; mean duration 30.74s; mean retries 1.67.
- ai | A | T5 | high_experience | gpt-6-luna: 3/3 verified successes; 0 unverified; mean actions 9.33; mean duration 14.13s; mean retries 0.33.
- ai | A | T5 | low_digital_experience | gpt-6-luna: 3/3 verified successes; 0 unverified; mean actions 9.33; mean duration 17.04s; mean retries 0.33.
- ai | A | T5 | low_patience | gpt-6-luna: 3/3 verified successes; 0 unverified; mean actions 9.33; mean duration 15.47s; mean retries 0.33.
- ai | A | T5 | low_risk_tolerance | gpt-6-luna: 3/3 verified successes; 0 unverified; mean actions 9.33; mean duration 16.0s; mean retries 0.33.
- ai | A | T5 | neutral_baseline | gpt-6-luna: 4/4 verified successes; 1 unverified; mean actions 7.2; mean duration 11.67s; mean retries 0.0.
- ai | B | T1 | high_experience | gpt-6-luna: 3/3 verified successes; 0 unverified; mean actions 6.33; mean duration 9.29s; mean retries 0.33.
- ai | B | T1 | low_digital_experience | gpt-6-luna: 3/3 verified successes; 0 unverified; mean actions 7.67; mean duration 14.14s; mean retries 1.0.
- ai | B | T1 | low_patience | gpt-6-luna: 3/3 verified successes; 0 unverified; mean actions 7.0; mean duration 10.35s; mean retries 1.0.
- ai | B | T1 | low_risk_tolerance | gpt-6-luna: 3/3 verified successes; 0 unverified; mean actions 6.67; mean duration 10.84s; mean retries 0.67.
- ai | B | T1 | neutral_baseline | gpt-6-luna: 3/3 verified successes; 0 unverified; mean actions 7.0; mean duration 10.65s; mean retries 0.67.
- ai | B | T5 | high_experience | gpt-6-luna: 3/3 verified successes; 0 unverified; mean actions 6.33; mean duration 8.94s; mean retries 0.0.
- ai | B | T5 | low_digital_experience | gpt-6-luna: 3/3 verified successes; 0 unverified; mean actions 7.0; mean duration 10.19s; mean retries 0.67.
- ai | B | T5 | low_patience | gpt-6-luna: 3/3 verified successes; 0 unverified; mean actions 6.0; mean duration 8.76s; mean retries 0.0.
- ai | B | T5 | low_risk_tolerance | gpt-6-luna: 3/3 verified successes; 0 unverified; mean actions 7.0; mean duration 10.82s; mean retries 0.67.
- ai | B | T5 | neutral_baseline | gpt-6-luna: 3/3 verified successes; 0 unverified; mean actions 6.33; mean duration 8.89s; mean retries 0.33.
- human | A | T1 | human_participant | unknown: 1/1 verified successes; 0 unverified; mean actions 3.0; mean duration 53.0s; mean retries 2.0.
- human | A | T5 | human_participant | unknown: 1/3 verified successes; 0 unverified; mean actions 5.0; mean duration 29.0s; mean retries 2.33.
- human | B | T1 | human_participant | unknown: 1/1 verified successes; 0 unverified; mean actions 1.0; mean duration 15.0s; mean retries 0.0.
- human | B | T5 | human_participant | unknown: 1/1 verified successes; 0 unverified; mean actions 1.0; mean duration 8.0s; mean retries 0.0.

## Limitations
- These are small, local demonstration samples; no statistical-significance claim is made.
- Behavioral indicators do not establish subjective frustration or usability causality.
- Aggregates omit session identifiers, run IDs, event payloads, timestamps, screenshots, and model transcripts.
