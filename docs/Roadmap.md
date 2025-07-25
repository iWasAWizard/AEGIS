# AEGIS Development Roadmap: From Robust Core to Advanced Autonomy

The core framework is now stable, observable, and extensible. This roadmap outlines the next three horizons of development, prioritizing features that deliver the most significant leaps in agent intelligence, capability, and operational maturity.

---

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

**2.3: Dynamic Goal Management**
*   **Why:** A truly autonomous agent should not blindly follow a flawed initial prompt. This feature gives the agent the ability to reflect on its progress and refine its own objectives, a critical step towards genuine problem-solving.
*   **Key Deliverables:**
    *   Create a new tool, `revise_goal(new_goal: str, reason: str)`.
    *   Update the `reflect_and_plan` prompt to encourage the agent to consider whether the original goal is still optimal after several steps.
    *   When the `revise_goal` tool is called, the agent step will update the `task_prompt` within the `TaskState` itself. The new, revised goal will then be used in all subsequent planning prompts.
*   **Impact:** Massively increases agent robustness and adaptability, allowing it to recover from ambiguous or poorly-formed user requests.

**2.4: Advanced Web Browsing Executor**
*   **Why:** Low-level Selenium commands are powerful but require the agent to do too much work. A higher-level, stateful browsing executor will make web-based tasks faster and far more reliable.
*   **Key Deliverables:**
    *   Create a new `StatefulBrowserExecutor` that maintains its own session state (cookies, history) across multiple tool calls.
    *   Create a new, high-level tool, `browse_and_summarize(url: str, objective: str)`, that automates the entire process of navigating, finding relevant content based on an objective, and returning a clean summary.
*   **Impact:** Makes the agent a world-class web scraping and data extraction tool.

---

### **Horizon 3: Ecosystem & Scalability**

**Objective:** To refine the developer experience and prove out future architectural patterns, making the framework easier and faster to extend.

**3.1: Agent SDK (Tool Scaffolding)**
*   **Why:** Manually creating tool files, input schemas, and test files is repetitive. An SDK will automate this, enforcing best practices and dramatically speeding up the process of adding new capabilities.
*   **Key Deliverables:**
    *   Enhance the `aegis.cli new-tool` command to be more comprehensive.
    *   When run, it will generate not only the tool file in `plugins/` but also a corresponding boilerplate test file in `aegis/tests/tools/plugins/`.
    *   Consider using a template engine like `cookiecutter` under the hood to manage the file templates.
*   **Impact:** Improves developer velocity and code quality by standardizing the tool creation process.

**3.2: Native Tool Integration (Proof of Concept)**
*   **Why:** To demonstrate the power of moving beyond shell commands, we will create a proof-of-concept tool that directly uses a Python SDK for a more robust and secure interaction with an external service.
*   **Key Deliverables:**
    *   Choose a target service (e.g., AWS S3).
    *   Create a new tool, `s3_list_buckets`, that uses the `boto3` Python library to list S3 buckets.
    *   This will involve adding `boto3` to `requirements.txt` and handling AWS credentials securely via the `.env` file and Docker Compose.
*   **Impact:** Serves as a template and a proof of concept for a new, more powerful class of tools, paving the way for deep integrations with any service that has a Python SDK.