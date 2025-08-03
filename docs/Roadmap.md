# AEGIS Development Roadmap: From Robust Core to Advanced Autonomy

### **Horizon 1: Foundational Hardening & Measurement**

**Objective:** To establish a production-grade foundation for all future work and implement the core feedback loop for data-driven improvement. This horizon is about ensuring the system is resilient and that we can objectively measure the impact of our changes.

**1.1: Production-Grade State Management**
*   **Why:** The current in-memory store for paused tasks is a critical single point of failure. Moving this to a persistent, external store is the highest priority for enabling reliable, long-running, and complex agentic workflows.
*   **Key Deliverables:**
    *   Integrate a Redis client into the AEGIS application.
    *   Refactor the `/api/launch` and `/api/resume` endpoints to store and retrieve interrupted graph states from Redis instead of the in-memory `INTERRUPTED_STATES` dictionary.
    *   The Redis key should be the `task_id`, and the value should be the serialized, interrupted graph state.
*   **Impact:** Dramatically improves the reliability of Human-in-the-Loop tasks. It is the foundational prerequisite for future features like hierarchical planning and multi-agent systems.

**1.2: Re-integrate Advanced Observability (LangFuse)**
*   **Why:** While basic logging and provenance reports are functional, a dedicated observability platform like LangFuse provides an invaluable, purpose-built UI for tracing, debugging, and analyzing agent behavior. Re-integrating this on a stable BEND foundation is critical for developer velocity and operational insight.
*   **Key Deliverables:**
    *   Perform a clean, stable re-integration of the full LangFuse stack (`langfuse-server`, `clickhouse`, `clickhouse-keeper`, `minio`) into the BEND Docker Compose files, incorporating all learned lessons regarding healthchecks and startup dependencies.
    *   Re-introduce the `langfuse` dependency to AEGIS and restore the `CallbackHandler` logic to the API and CLI execution paths.
    *   Restore the `eval` commands and the evaluation suite, which are dependent on LangFuse Datasets.
*   **Impact:** Restores the "flight data recorder" for the agent, providing deep, visual insight into the agent's reasoning process and unlocking powerful evaluation capabilities.

**1.3: Advanced Evaluation Suite (A/B Testing)**
*   **Why:** To move beyond "gut feeling," we need an objective, data-driven way to prove that a change to a prompt, tool, or preset makes the agent better. A/B testing is the gold standard for this.
*   **Key Deliverables:**
    *   Enhance the `aegis.cli run-evals` command to accept two preset files (e.g., `--preset-a verified_flow.yaml --preset-b new_experimental_flow.yaml`).
    *   The runner will execute the entire dataset against both presets.
    *   Generate a comparative report in the console that shows side-by-side average scores and highlights which tasks had the largest performance difference.
    *   Leverage LangFuse's tagging or metadata features to clearly distinguish between "Run A" and "Run B" traces in the UI.
*   **Impact:** Revolutionizes the development workflow. We can now fine-tune prompts and logic with confidence, backed by quantitative data, massively accelerating performance improvements.

**1.4: Task Repeatability & Introspection**
*   **Why:** Debugging agentic systems requires perfect replication of past runs. We must build tools to capture, replay, and visualize agent sessions deterministically.
*   **Key Deliverables:**
    *   **Session Logger & Replayer:** Create a mechanism to log the exact inputs (model, prompt, tool outputs) for each step of a task, and a corresponding "replayer" to re-run the session with these exact inputs to reproduce behavior.
    *   **Execution Plan Visualizer:** Develop a feature in the UI to render the provenance report as a DAG, showing the flow of execution, branches, and tool calls.
*   **Impact:** Creates a robust debugging and auditing capability, essential for understanding and improving complex agent behavior.

---

### **Horizon 2: Next-Generation Intelligence & Perception**

**Objective:** To fundamentally upgrade the agent's reasoning and sensory capabilities. This horizon moves the agent beyond simple, linear task execution and gives it the ability to see and interact with a much wider range of digital environments.

**2.1: Hierarchical Planning (Sub-goal Decomposition)**
*   **Why:** The agent currently plans one step at a time, which can lead it to get "lost" in complex tasks. Decomposing a large goal into a high-level sequence of sub-goals will enable it to tackle much more ambitious objectives.
*   **Key Deliverables:**
    *   Create a new agent step, `decompose_task`, which is called at the beginning of a run. This step uses an LLM call to break the main prompt into a list of smaller, sequential sub-goals.
    *   Modify the `TaskState` to include `sub_goals: List[str]` and `current_sub_goal_index: int`.
    *   Update the main `reflect_and_plan` prompt to include the current sub-goal, providing a much more focused context for each step.
*   **Impact:** A paradigm shift in agent capability, enabling it to solve complex, long-horizon problems that are currently intractable.

**2.2: Multimodal Perception (Vision)**
*   **Why:** The agent is currently "blind," relying on brittle OCR for screen reading. Integrating a true vision model will allow it to understand icons, images, and graphical UI structures, unlocking robust automation of modern applications.
*   **Key Deliverables:**
    *   Add a Vision Language Model (VLM) service (e.g., LLaVA) to the BEND backend stack.
    *   Create a new tool, `describe_screen_area(coordinates: tuple)`, which captures a screenshot of a screen region and passes it to the VLM.
    *   The tool will return a rich, natural language description of the visual elements in that area.
*   **Impact:** This is the single largest expansion of the agent's sensory input, making it exponentially more effective at GUI automation and web interaction.

**2.3: Self-Reflection & Dynamic Goal Management**
*   **Why:** A truly autonomous agent should not blindly follow a flawed initial prompt. This feature gives the agent the ability to reflect on its progress and refine its own objectives, a critical step towards genuine problem-solving.
*   **Key Deliverables:**
    *   Create a `self_reflection` module that is called after a task fails or partially succeeds. The module will use an LLM to analyze the execution history and produce a "lesson learned" summary.
    *   These lessons will be embedded and stored in the RAG memory, to be retrieved in future, similar tasks.
    *   Create a new tool, `revise_goal(new_goal: str, reason: str)`, that allows the agent to update its own `task_prompt` in the `TaskState` mid-flight.
*   **Impact:** Massively increases agent robustness and adaptability, allowing it to learn from its mistakes and recover from ambiguous user requests.

**2.4: Advanced Prompt Engineering Toolkit**
*   **Why:** The current prompt construction is static. A dynamic, modular system is needed to manage complexity and optimize for performance and cost.
*   **Key Deliverables:**
    *   **Modular PromptBuilder:** Refactor prompt construction into a class that assembles prompts from distinct, reusable sections (e.g., role, tools, context, history).
    *   **Context Compression:** Implement logic to intelligently truncate or summarize long execution histories and tool outputs to stay within token limits.
    *   **Structured Output Enforcement:** Deepen the integration with the `instructor` library to include auto-repair mechanisms for plans that fail Pydantic validation.
*   **Impact:** Provides fine-grained control over the agent's reasoning process, improving reliability and enabling advanced techniques like dynamic role switching.

---

### **Horizon 3: Ecosystem & Scalability**

**Objective:** To refine the developer experience and prove out future architectural patterns, making the framework easier and faster to extend.

**3.1: Agent SDK & Tooling Enhancements**
*   **Why:** Manually creating tool files, input schemas, and test files is repetitive. An SDK will automate this, enforcing best practices and dramatically speeding up the process of adding new capabilities.
*   **Key Deliverables:**
    *   Enhance the `aegis new-tool` command to generate both the tool file in `plugins/` and a corresponding boilerplate test file in `aegis/tests/tools/plugins/`.
    *   **Auto-Tool Discovery:** Solidify the `plugins` directory as the primary mechanism for extending agent capabilities.
    *   **Tool Performance Tracker:** Implement a lightweight mechanism to record tool call latency and error rates, storing this metadata alongside the provenance report.
*   **Impact:** Improves developer velocity and code quality by standardizing the tool creation process and providing data for tool optimization.

**3.2: Native Tool Integration (Proof of Concept)**
*   **Why:** To demonstrate the power of moving beyond shell commands, we will create a proof-of-concept tool that directly uses a Python SDK for a more robust and secure interaction with an external service.
*   **Key Deliverables:**
    *   Choose a target service (e.g., AWS S3).
    *   Create a new tool, `s3_list_buckets`, that uses the `boto3` Python library to list S3 buckets.
    *   This will involve adding `boto3` to `requirements.txt` and handling AWS credentials securely via the `.env` file and Docker Compose.
*   **Impact:** Serves as a template and a proof of concept for a new, more powerful class of tools, paving the way for deep integrations with any service that has a Python SDK.

**3.3: Advanced Model & Infrastructure Management**
*   **Why:** As the number of supported models grows, manual management becomes untenable. The system needs to become self-aware of its models and the hardware it's running on.
*   **Key Deliverables:**
    *   **Model Registry:** Expand `models.yaml` to be a comprehensive registry tracking model formats, quantization levels, context sizes, and aliases.
    *   **Hardware Profiler:** Create a script in BEND that detects CPU cores, RAM, and VRAM at startup and suggests optimal model configurations or parallelism settings.
    *   **Airgap-Ready Deployment:** Develop a build process that can package all Python wheels, models, and binaries into a single archive for deployment on machines without internet access.
*   **Impact:** Radically simplifies deployment and configuration, enabling the stack to run optimally across a wide range of hardware and in restricted environments.