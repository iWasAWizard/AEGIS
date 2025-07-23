# **AEGIS Development Roadmap: From Robust Core to Advanced Autonomy**

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

**1.2: Advanced Evaluation Suite (A/B Testing)**
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
    *   This will involve adding `boto3` to `requirements.txt` and handling AWS credentials securely.
*   **Impact:** Serves as a template and a proof of concept for a new, more powerful class of tools, paving the way for deep integrations with any service that has a Python SDK.

---

### **Summary of Effort**

| Roadmap Item                                 | Complexity  | Architectural Impact | Primary Focus                                        |
| :------------------------------------------- | :---------- | :------------------- | :--------------------------------------------------- |
| **H1: Production-Grade State Management**    | **Medium**  | **High**             | Backend, API, State Logic                            |
| **H1: A/B Testing Eval Suite**               | **Medium**  | **Low**              | CLI, Evaluation Scripts, Reporting                   |
| **H2: Hierarchical Planning**                | **High**    | **Very High**        | Core Agent Logic, State, Prompt Engineering          |
| **H2: Multimodal Perception (Vision)**       | **High**    | **High**             | BEND Stack, New Executor, New Tool, Prompt Engineering |
| **H2: Dynamic Goal Management**              | **Medium**  | **High**             | Core Agent Logic, New Tool, Prompt Engineering       |
| **H2: Advanced Web Browsing Executor**       | **Medium**  | **Medium**           | New Executor, Tool Design, State Management          |
| **H3: Agent SDK (Tool Scaffolding)**         | **Low**     | **Low**              | CLI, Developer Tooling                               |
| **H3: Native Tool Integration (PoC)**        | **Low**     | **Low**              | New Tool, Dependency Management                      |

---

### **Horizon 1: Foundational Hardening & Measurement**

#### **1.1: Production-Grade State Management (Redis)**

*   **Complexity:** **Medium**
*   **Architectural Impact:** **High**. This moves a critical piece of state from a fragile, in-memory dictionary to a robust, persistent, external service. It's a fundamental shift in how the system handles interruptions.
*   **Scope of Work:**
    *   **AEGIS API:** Modify `aegis/web/routes_launch.py` and `aegis/web/routes_resume.py` to replace the `INTERRUPTED_STATES` dictionary with calls to a Redis client.
    *   **AEGIS Executors:** A new `RedisExecutor` or a utility in `aegis/utils/` will be needed to manage the connection and serialization/deserialization of the agent state.
    *   **AEGIS Config:** Add `redis` to `requirements.txt`. The `config.yaml` already has a `redis_url`, which is perfect.
    *   **BEND Stack:** No changes needed, as BEND already provides the Redis service.
*   **Key Challenges & Risks:**
    *   **Serialization:** The compiled `Pregel` graph object cannot be directly stored in Redis. We must store the *interrupted state dictionary* and be able to re-instantiate the graph from its configuration upon resumption. This is the main technical hurdle.
    *   **Connection Management:** The Redis client must be robust to connection drops and retries.

#### **1.2: A/B Testing Eval Suite**

*   **Complexity:** **Medium**
*   **Architectural Impact:** **Low**. This is an enhancement to our offline development and testing tools, with no impact on the agent's runtime architecture.
*   **Scope of Work:**
    *   **AEGIS CLI:** Major changes will be in `aegis/run_regression_tests.py` (or a new, dedicated `run_evals.py` script). The `typer` command definition needs to be updated to accept two preset files.
    *   **Evaluation Logic:** The core evaluation loop will need to run the dataset for each preset, store the results, and then generate a comparison.
    *   **Reporting:** A new reporting function will be needed to display a clear, side-by-side summary table in the console using the `rich` library.
*   **Key Challenges & Risks:**
    *   **Output Design:** Designing a console report that is both data-rich and easy to read is non-trivial.
    *   **LangFuse Integration:** Ensuring that the A/B test runs are clearly tagged and distinguishable in the LangFuse UI for deeper analysis.

---

### **Horizon 2: Next-Generation Intelligence & Perception**

#### **2.1: Hierarchical Planning (Sub-goal Decomposition)**

*   **Complexity:** **High**
*   **Architectural Impact:** **Very High**. This introduces a new, higher level of abstraction to the agent's reasoning process. It fundamentally changes the agent's control flow from a simple loop to a nested one.
*   **Scope of Work:**
    *   **AEGIS State:** `aegis/agents/task_state.py` must be updated to include fields for `sub_goals` and the current goal index.
    *   **AEGIS Steps:** A new agent step, `decompose_task.py`, must be created. The core `reflect_and_plan.py` step must be modified to be aware of the current sub-goal. The `check_termination.py` logic will need to be updated to handle advancing to the next sub-goal.
    *   **AEGIS Presets:** Existing presets will need to be updated to include this new initial decomposition step in their graph.
*   **Key Challenges & Risks:**
    *   **Prompt Engineering:** This is the biggest challenge. The meta-prompt for the decomposition step must be incredibly robust to reliably break down a complex goal into a logical, sequential, and complete list of sub-goals. Poor decomposition will doom the entire task.
    *   **State Management:** The logic for advancing the sub-goal index and knowing when the overall task is complete (i.e., all sub-goals are done) adds complexity to the graph's termination conditions.

#### **2.2: Multimodal Perception (Vision)**

*   **Complexity:** **High**. While the AEGIS-side changes are moderate, the lift involves adding and managing a significant new service in the BEND backend.
*   **Architectural Impact:** **High**. It adds an entirely new sensory modality to the agent, fundamentally changing how it can perceive and interact with its environment.
*   **Scope of Work:**
    *   **BEND Stack:** A new VLM service (e.g., LLaVA) must be added to the `docker-compose.yml` and integrated into the `manage.sh` script. This is a non-trivial infrastructure addition.
    *   **AEGIS Tools:** A new tool, `describe_screen_area.py`, needs to be created.
    *   **AEGIS Executors:** This tool will likely require a new, specialized `VLLExecutor` that knows how to handle the multimodal API (sending image data and text).
*   **Key Challenges & Risks:**
    *   **Infrastructure:** VLMs are resource-intensive (VRAM). Adding one to BEND increases the hardware requirements and complexity of the stack.
    *   **API Integration:** The API for querying a VLM is different from a standard LLM. It involves encoding image data (e.g., base64) and sending it alongside the text prompt.
    *   **Prompting for Vision:** Getting consistently useful descriptions from a VLM requires careful prompt engineering.

#### **2.3: Dynamic Goal Management**

*   **Complexity:** **Medium**. The concept is advanced, but the implementation is surprisingly localized within the existing architecture.
*   **Architectural Impact:** **High**. This gives the agent a "self-awareness" that fundamentally alters the human-agent contract. The agent is no longer just an executor but a collaborative problem-solver.
*   **Scope of Work:**
    *   **AEGIS Tools:** A new tool, `revise_goal.py`, must be created.
    *   **AEGIS Steps:** The `execute_tool.py` step needs a special `if tool_name == "revise_goal"` block to handle the unique action of modifying the `TaskState` directly.
    *   **Prompt Engineering:** The `reflect_and_plan.py` prompt needs to be subtly updated to include the *option* of revising the goal, without encouraging the agent to do so unnecessarily.
*   **Key Challenges & Risks:**
    *   **Agent Stability:** The primary risk is creating an agent that gets stuck in a loop of constantly revising its goal without making any progress. The prompt must be carefully crafted to frame this as an exceptional action for when the original goal is truly flawed.

#### **2.4: Advanced Web Browsing Executor**

*   **Complexity:** **Medium**
*   **Architectural Impact:** **Medium**. It's a significant upgrade to an existing capability, introducing the concept of stateful executors that persist across tool calls.
*   **Scope of Work:**
    *   **AEGIS Executors:** A new `StatefulBrowserExecutor.py` must be designed. This is the core of the work.
    *   **AEGIS Tools:** New, higher-level tools like `browse_and_summarize.py` will be built on top of the new executor.
    *   **Core Logic:** The `execute_tool` step might need to be adapted to handle the lifecycle (creation, caching, destruction) of stateful executors.
*   **Key Challenges & Risks:**
    *   **Executor Lifecycle:** Deciding how and when to initialize and tear down the persistent browser session is the main architectural challenge. A poorly managed session could lead to memory leaks or stale state.
    *   **Content Extraction Logic:** The "summarize" part of the tool is a complex problem in itself, likely requiring its own internal LLM calls to distill the relevant information from raw HTML.

---

### **Horizon 3: Ecosystem & Scalability**

#### **3.1: Agent SDK (Tool Scaffolding)**

*   **Complexity:** **Low**
*   **Architectural Impact:** **Low**. This is a pure developer-experience improvement with no effect on the runtime agent.
*   **Scope of Work:**
    *   **AEGIS CLI:** The logic in `aegis/utils/cli_helpers.py` for the `new-tool` command needs to be expanded.
    *   **Templates:** Create template files (`.py.tpl`) for the new tool and its corresponding test file.
*   **Key Challenges & Risks:** Minimal risk. The main challenge is designing good, clean templates that genuinely help developers adhere to best practices.

#### **3.2: Native Tool Integration (Proof of Concept)**

*   **Complexity:** **Low**. This is a well-defined, self-contained task.
*   **Architectural Impact:** **Low** for the PoC, but it sets a high-value precedent for future development.
*   **Scope of Work:**
    *   **AEGIS Config:** Add a new dependency (e.g., `boto3`) to `requirements.txt`.
    *   **AEGIS Tools:** Create a new tool file in `plugins/`. The implementation will be a straightforward wrapper around the SDK calls.
    *   **Security:** Documenting how to handle the associated credentials (e.g., AWS keys) securely via the `.env` file and Docker Compose.
*   **Key Challenges & Risks:** Securely managing credentials is the only significant consideration. The implementation itself is straightforward.