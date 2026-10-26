# Server Aquarium: 90-second walkthrough

## Story

Observe a real ODS request, replay an incident, then follow an explanation back to its measurements.

## Suggested recording

- **0–10 seconds:** show the aquarium and four Simulation Studio scenes. State that this mode is simulated.
- **10–25 seconds:** in the local companion, run the default AI prompt. The view switches to This computer. Show streamed content, first-content latency, provider-reported tokens and the live whole-device GPU/VRAM readings. Do not describe that GPU activity as measured per-service attribution.
- **25–40 seconds:** open sample replay. Clearly identify the fictional recorded incident. Scrub between the first frame and the Database-offline frame; compare host RAM, GPU/VRAM and service state.
- **40–60 seconds:** choose Explain this moment. ODS interprets the two supplied frames and computed changes. Click an evidence reference to return to its captured moment. Distinguish observed change, model interpretation and proposed checks.
- **60–75 seconds:** show the public demo's recorded ODS explanation for that exact sample. It is labeled recorded and makes no live gateway request. Save replay or Save AI report to demonstrate portable evidence.
- **75–90 seconds:** show the public repository, passing checks and ODS build history. Keep credentials and private runtime reports outside the published material.

## Entry draft

Server Aquarium turns an ODS stack into a living ecosystem. Services become fish whose behavior follows resource readings, while whole-device GPU/VRAM and clearly scoped memory stay visible. Simulation Studio teaches the experience through four safe workloads. Flight recorder lets a user revisit a moment and compare a baseline. AI lab runs genuine ODS inference with measured latency and reported token counts; Explain this moment turns recorded evidence and computed changes into an interpretation with clickable references. A credential-free public demo, replay files and local reports make the experience easy to explore and inspect.

## Provenance

tang-vu leads direction, scope and quality, collaborating with Codex on reference source, prompts, analysis, implementation guidance, review and command/browser validation. ODS Portal model/workspace tools performed source edits and builds. Saved source hashes, prompt/tool receipts and checks record the workflow. Recorded examples use synthetic resource frames and genuine ODS model responses; they are not presented as live public inference or proof of automated root-cause diagnosis.

This is a walkthrough and draft, not a contest submission or eligibility determination.
