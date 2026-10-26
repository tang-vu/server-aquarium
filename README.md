# Server Aquarium

A living view of your ODS stack: observe the machine, replay a moment, and ask your ODS model to explain the recorded evidence.

**[Open the public demo](https://tang-vu.github.io/server-aquarium/)** · [Source](https://github.com/tang-vu/server-aquarium) · [CI checks](https://github.com/tang-vu/server-aquarium/actions/workflows/ci.yml)

## Explore

- **Aquarium:** each fish is a service. CPU changes its pace, container RAM changes its size, and confirmed offline services float belly-up. Select a fish or its keyboard-accessible service card.
- **Simulation Studio:** Calm waters, AI inference, Traffic surge and Recovery drill. These are explicitly scripted readings from a fictional 32 GiB host and 16 GiB accelerator. Pause, resume and restart a scene; manual incidents never change a real service.
- **Machine resources:** host RAM, separately labeled WSL runtime RAM, and NVIDIA GPU utilization, VRAM, temperature and power. GPU measurements cover the whole device and other host workloads; no per-container GPU attribution is measured.
- **Flight recorder:** up to 120 captures over a rolling ten-minute window per source, stored in this browser. Scrub the chart, choose a baseline, inspect a recorded moment, and save or import a bounded JSON replay. The main aquarium keeps its current view.
- **AI lab:** explicitly run a prompt through your configured ODS gateway, see streamed text, first-content latency, provider-reported output tokens, total elapsed time and end-to-end output tokens/second. The live aquarium is selected automatically for a real run.
- **Explain this moment:** send one selected replay frame and an optional earlier baseline to ODS. The companion builds bounded evidence and computed changes. The response includes clickable references back to the captured moments. Model interpretation and proposed checks remain separate from observed facts.
- **Reports:** Save replay, Save AI report, Export observations and the fifteen-second aquarium video are explicit local downloads. After recording ends, choose Save video. Video captures the aquarium, not the desktop or microphone.

The public demo uses simulated data and a recorded ODS explanation for its exact sample comparison. Real model requests and real hardware readings require the local companion. Static hosting has no gateway credentials or service-control endpoint.

## Run

Python 3.11+ is the only application dependency. Docker is needed for real ODS service observations. NVIDIA readings use the installed nvidia-smi utility. No npm or Python packages are required to run the app.

~~~sh
python3 companion.py
~~~

On Windows use py companion.py. Open the loopback address printed by the companion (port 4317), then choose **This computer** for real observations.

For AI requests, configure the companion process environment before launching it:

~~~sh
export AQUARIUM_ODS_TOKEN='your-ODS-gateway-key'
export AQUARIUM_ODS_MODEL='ods/current'
python3 companion.py
~~~

PowerShell:

~~~powershell
$env:AQUARIUM_ODS_TOKEN = 'your-ODS-gateway-key'
$env:AQUARIUM_ODS_MODEL = 'ods/current'
py companion.py
~~~

The default gateway uses HTTP loopback port 4000 with the /v1 base path. Set AQUARIUM_ODS_BASE_URL if your ODS gateway has another base URL. Only HTTP/HTTPS loopback targets are accepted; redirects and environment proxies are disabled. For a Qwen route where thinking should be disabled, set AQUARIUM_ODS_DISABLE_THINKING=1. Otherwise that optional template setting is omitted. Explain requests JSON-object output; the selected model/gateway must support that response format.

The companion reads only these explicitly named AI environment settings. It does not load an .env file or discover gateway keys from other apps. Credentials stay in the companion process and are not returned in API responses, frontend files, replays or AI reports. Inference follows the configured ODS route: select a locally hosted model in ODS for local-only inference. Explain sends the selected replay measurements to that route.

AI is optional. Without its configuration, hardware observation, Simulation Studio, history, imports and exports continue to work.

## Read the evidence correctly

Host RAM, WSL runtime RAM, container RAM and VRAM describe different scopes. Windows memory uses GlobalMemoryStatusEx, or a fixed read-only PowerShell CIM query from WSL; Linux memory uses /proc/meminfo. Unsupported RAM/GPU readers stay unavailable. A failed Windows host query never relabels WSL RAM as host RAM.

Docker CPU may exceed 100% across multiple cores. Fish speed and the history chart display cap at 100%; the original value remains in the inspector and replay data. Container RAM percentages use the container/engine limit; byte amounts come from Docker's rounded MemUsage field. Missing values stay unknown and measured zero stays zero. A running container without a healthcheck is Running; a healthy check is not a full application test.

Live collectors poll independently every five seconds. After fifteen seconds without fresh readings, the affected values become unknown and reconnect automatically. Capture timestamps are recorder times; a capture can repeat the latest available sensor sample. Source-specific histories are isolated. Browser background throttling can slow animation and capture cadence. Imported files and the bundled sample are labeled as recorded/imported data.

AI latency starts at submission and ends at first nonempty content, not the role-only stream event. Output token count comes from the gateway's usage receipt; missing usage stays unknown. Tokens per second divides reported output tokens by total elapsed time, including the wait for first content. It is not a standardized cross-model benchmark.

Explanation references are checked against known evidence IDs and link to the supplied replay frames. Computed changes distinguish host RAM from container RAM and unchanged values from increases. Replay data is supplied by the browser or an imported file; the companion does not certify its origin. Citation validation checks structure and reference identity, not the semantic truth of every model sentence. The model has no tools or service-mutation capability.

## Boundaries

The companion binds to loopback, validates exact Host/Origin values, serves a fixed asset list and exposes no service start/stop/restart, shell, file-management or model-switching API. Docker/hardware collection uses fixed read-only commands and bounded timeouts; it reads no credentials, logs or volumes.

Only explicit same-origin JSON requests can start or cancel an AI job. Request bodies are capped at 64 KiB, prompts at 2000 characters, and comparisons at two bounded frames. There is one active request and up to eight in-memory receipts. Stream size, output size and duration are bounded; failed/truncated streams are not reported as successful. Cancellation is cooperative between upstream reads. Refresh can resume an existing per-tab receipt; it does not automatically resubmit the inference.

No analytics, remote fonts, automatic uploads or cloud backend are added by the app. Browser replay storage contains resource readings; AI reports contain generated text, referenced evidence and selected frames. Use explicit downloads to keep a portable copy.

## Validate

~~~sh
python3 -m unittest discover -v
python3 check_frontend.py
node --test test_replay.mjs
~~~

Node.js is needed only for developer checks. CI runs Python 3.11 and Node 24 on Ubuntu and Windows. Tests cover real HTTP boundaries and streamed fixtures, authentication failures, redirects, truncation, cancellation, measured zero versus missing data, evidence/source validation, unchanged container memory, replay bounds, retention and citation references. Fixtures require neither Docker nor a real gateway key. Live/browser validation is recorded separately; green fixture tests do not establish every external runtime contract.

## Collaboration and Dev Jam

**tang-vu leads the contribution**, including project direction, scope, usefulness and quality requirements, collaborating with Codex on reference source, prompts, implementation guidance, analysis, review and browser validation. ODS Portal model/workspace tools performed all application source edits and build steps. Git publication and command/browser QA were executed with Codex assistance; source receipts preserve that provenance.

See DEMO.md for the walkthrough and draft entry. No contest submission has been made, and these artifacts do not establish contest eligibility. Historical manifests describe earlier versions; RELEASE.json describes the current source bundle.
