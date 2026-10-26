# Server Aquarium

A calm, interactive view of your ODS stack. Each fish is a service: CPU changes its pace, container RAM changes its size, and confirmed stopped services float belly-up. A separate machine-resources row shows host RAM, NVIDIA GPU load, VRAM, temperature and power. Select a fish or keyboard-accessible service card to inspect its observations.

## Run

Python 3.11+ is the only application dependency. Docker is needed for real service observations. NVIDIA GPU readings require the installed nvidia-smi utility; no Python packages are required.

~~~sh
python3 companion.py
~~~

On Windows use py companion.py. Open **http://127.0.0.1:4317**, then choose **This computer**. The default **Demo aquarium** uses explicitly simulated service, RAM and GPU data; its CPU spike, outage and recovery controls never change a real service. The static ODS preview and opening index.html directly support this demo. Live data requires the companion URL.

## Simulation Studio

The Demo aquarium has four selectable scenes: Calm waters, AI inference, Traffic surge and Recovery drill. Workload values evolve every 1.5 seconds with explicitly simulated host RAM, GPU/VRAM and per-service memory. AI inference emphasizes the Model Engine; Traffic surge highlights resource pressure in Portal, Database and Background Worker. The 24-second Recovery drill takes Database offline from second 6 to 13, reconnects it and returns to healthy flow.

Pause simulation freezes the workload, its progress and fish motion. Resume continues the scene. Restart scene resets its time and manual incidents. CPU spike and Outage hold a selected service in that state until Recover all, Restart scene or choosing another scene. Recover all returns to Calm waters. Attention remains a service-resource filter. The simulated hardware is a fictional 32 GiB host and 16 GiB accelerator, not a claim about the current computer. Switching to This computer hides the studio and resumes the independent live collectors.

The demo adds a procedural reef, light caustics, drifting glints, fish wakes and an inference halo. Reduced-motion preferences stop decorative motion; numerical observations still update unless paused. Demo rendering and incident controls make no changes to the machine or its real services.

## Use it

- The machine-resources row shows used/total host RAM and available RAM; on WSL it separately labels the ODS WSL runtime RAM. NVIDIA cards show GPU utilization, used/total VRAM, temperature and power for each detected device.
- Choose a service to see CPU, container RAM in bytes and percentage of its limit, Docker state/health and the last 60 CPU observations. Selection survives refreshes, resize and expanded view.
- **Attention** filters service CPU or RAM above 70%, stopped, unhealthy, starting or stale services. It is a visual advisory, not an incident detector or a GPU alert.
- **Export observations** saves local JSON with current machine readings, per-container RAM amounts/limits, service session histories and up to 100 activity events.
- **Record report** saves up to 15 seconds of local WebM showing the aquarium, service observations and a compact machine RAM/GPU/VRAM summary. It works in demo and live modes, captures neither the desktop nor audio, and can be stopped early. After recording finishes, choose **Save video** to download the WebM.
- Day/night, Feed, expanded view and Escape work without changing service state. Keyboard focus and reduced-motion preferences are supported.

## Read the data correctly

The three memory scopes are distinct: physical host RAM; ODS WSL runtime RAM, when applicable; and each container's memory usage/limit. Windows host RAM comes from GlobalMemoryStatusEx on native Windows, or a fixed read-only PowerShell CIM query when running inside WSL. Linux RAM comes from /proc/meminfo. A failed WSL host query stays unavailable; runtime RAM is never relabeled as host RAM.

GPU readings describe the **whole device, shared by all host workloads**. They are not measured per-container GPU attribution. The current reader supports NVIDIA through nvidia-smi; unsupported or unavailable GPU sensors show an explicit unavailable state. Demo hardware is labeled simulated. Missing numbers remain an em dash; measured zero remains zero. GPU utilization, VRAM, temperature and power are separate readings and do not imply which service caused them.

Service CPU is Docker's percentage and can exceed 100% across multiple cores; fish speed saturates at 100%. Container RAM percentage is relative to the container/engine limit; amounts are parsed from Docker's rounded MemUsage field. A running container without a healthcheck is labeled Running; a healthy check does not verify the whole application.

In This computer mode, service and machine sensors poll independently every five seconds. GPU or Docker failure does not erase successful readings from the other sensor. After 15 seconds without fresh observations, the affected values become unknown and the view reconnects automatically. Retained stale services become Unknown and unconfirmed running counts become em dashes. Before a first valid response, counts are unknown; a valid empty list is true zero. Histories are session-local, disappear on reload and clear on source changes. Collection is bounded to 64 eligible ODS services and 16 GPUs.

## Privacy and boundaries

The companion binds only to 127.0.0.1:4317 and validates exact Host/Origin values. It serves a fixed asset list and exposes only read-only GET APIs for service telemetry and machine hardware. Docker collection uses a Compose-project-filtered listing and a resource sample for validated discovered running IDs. Hardware collection uses fixed argument lists for nvidia-smi and, on WSL, the read-only PowerShell host-memory query; native Windows and Linux memory use local OS interfaces. Subprocesses use shell=False and bounded timeouts. There are no service mutations, shell commands supplied by browser input, environment/credential/log/volume reads, analytics, external fonts, remote assets or automatic uploads.

## Validate

~~~sh
python3 -m unittest -v test_companion test_hardware
~~~

The 27 fixture/HTTP tests cover Docker fields, RAM units/limits, missing versus measured zero, multicore CPU, health distinctions, stopped/foreign containers, failed collection, read-only HTTP boundaries and client disconnects; hardware tests also cover GPU parsing, multiple devices, independent sensor failures, native Windows memory, and the Windows-host versus WSL-runtime distinction. Browser checks and exact source hashes are recorded separately; static publication alone is not a browser test.

Frontend: index.html, styles.css, aquarium-art.js, app.js, aquarium-scene.js, telemetry.js, hardware.js, demo.js (simulation scenes and artwork) and recording.js. Local bridge: companion.py and hardware.py. Tests: test_companion.py and test_hardware.py. DEMO.md contains the walkthrough. demo-manifest.json and server-aquarium-demo.zip describe this Simulation Studio release; earlier source-manifest.json and final archives belong to the previous release.

## Collaboration and Dev Jam

**tang-vu leads the contribution**, including project direction, usefulness and quality requirements, collaborating with Codex on implementation guidance, reference source in prompts, review and browser validation. The ODS Portal model and workspace tools performed all application source edits and build steps. Saved Portal prompts/tool receipts document that workflow.

DEMO.md provides a walkthrough and draft entry text. No contest entry or public deployment has been submitted; contest eligibility is not determined by these artifacts.