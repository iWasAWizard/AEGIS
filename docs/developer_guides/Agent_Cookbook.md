# Agent Design Patterns & Cookbook

The AEGIS framework provides a powerful set of building blocks. This guide goes beyond the technical details to show you *how to compose* those blocks into sophisticated, reliable, and effective autonomous agents. These are the "recipes" and design patterns that will help you solve complex problems.

## 1. The Verification Loop

**Pattern:** Plan -> Execute -> **Verify** -> **Remediate**

**When to Use It:** This is the go-to pattern for any task where the outcome of an action is critical and not guaranteed. It's the foundation of a **self-correcting** agent. Use this for tasks involving filesystem changes, network configurations, or any action that modifies the state of an external system.

**How It Works:**
Instead of assuming a tool worked correctly, this pattern adds a verification step.

1.  **Plan:** The agent's LLM generates a plan that includes not just the main action, but also a `verification_tool_name`.
    -   *Example Plan:* "I will use `run_remote_command` to start the web service. For verification, I will use `check_port_status` on port 80."
2.  **Execute:** AEGIS runs the main tool (`run_remote_command`).
3.  **Verify:** The `verify_outcome` step then runs the specified verification tool (`check_port_status`). It sends the original goal, the main tool's output, and the verification tool's output to the LLM and asks for a simple judgment: `success` or `failure`.
4.  **Remediate (If Needed):** If the judgment is `failure`, the graph routes to the `remediate_plan` step. The agent is shown the error and asked to formulate a new plan to fix the problem.

**Example Recipe: A Self-Healing Web Server Agent**

-   **Preset:** `verified_flow.yaml`
-   **Prompt:** `"Ensure the web service on machine 'web-server-01' is running and responsive on port 80."`
-   **Execution Flow:**
    1.  **Plan:** Agent decides to run `check_port_status` on `web-server-01:80` as its first action.
    2.  **Execute:** The tool returns `"Port 80 on web-server-01 is Closed"`.
    3.  **Verify:** The agent's own check confirms the service is down. The `verify_outcome` step (or a simple routing rule) sees the failure.
    4.  **Remediate:** The agent is told, "The check failed; the port is closed." It now formulates a new plan: `run_remote_command(command="sudo systemctl start nginx")`. For verification, it again chooses `check_port_status`.
    5.  **Execute:** The command is run.
    6.  **Verify:** `check_port_status` is run again. This time it returns `"Port 80 on web-server-01 is Open"`. The LLM judges this a `success`.
    7.  The agent, having corrected the state, can now `finish`.

## 2. Agentic Mixture of Experts (MoE)

**Pattern:** Orchestrator Agent -> **Delegate** -> Specialist Agent

**When to Use It:** Use this pattern when you have a complex problem that can be broken down into distinct sub-domains. It's the key to building **scalable and maintainable** multi-agent systems. Instead of one "master" agent that knows everything, you create a team of experts.

**How It Works:**
A high-level "Orchestrator" agent is given a complex goal. Its primary job is not to execute low-level tasks, but to delegate them to other, more specialized agents using the `dispatch_subtask_to_agent` tool.

1.  **Orchestrator Agent:** This agent is configured with the `orchestrator.yaml` preset. Its toolset is very small and abstract, consisting mainly of the `dispatch_subtask_to_agent` tool.
2.  **Specialist Agents:** These are other presets (like `database_agent.yaml`) that have a `tool_allowlist` defined. This makes them experts in a narrow domain (e.g., they can only see and use SQL-related tools).
3.  **Delegation:** The Orchestrator receives a goal, breaks it down, and calls `dispatch_subtask_to_agent` with a sub-prompt and the name of the specialist preset to use.

**Example Recipe: A Security Auditing System**

-   **Goal:** `"Perform a security audit on the machine 'ubuntu-qemu'. First, discover its open ports and running services. Then, check its configuration against the company's security baseline document. Finally, generate a report."`
-   **Agents:**
    -   `OrchestratorAgent` (using `orchestrator.yaml`)
    -   `DiscoveryAgent` (a preset with only `nmap` and `scapy` tools)
    -   `ComplianceAgent` (a preset with only `read_remote_file` and `retrieve_knowledge` tools)
-   **Execution Flow:**
    1.  **Orchestrator** receives the goal. It plans its first step: delegate discovery.
    2.  It calls `dispatch_subtask_to_agent(prompt="Find all open ports and services on 'ubuntu-qemu'", preset="discovery_agent")`.
    3.  The **DiscoveryAgent** runs, uses `nmap`, and returns a summary: `"Found SSH on port 22 and Nginx on port 80."`
    4.  **Orchestrator** receives this summary. It plans its next step: delegate compliance checking.
    5.  It calls `dispatch_subtask_to_agent(prompt="The 'ubuntu-qemu' machine is running Nginx. Read its config file at '/etc/nginx/nginx.conf' and compare it to the 'nginx_hardening_guide.pdf' from the knowledge base.", preset="compliance_agent")`.
    6.  The **ComplianceAgent** runs, uses its tools, and returns a summary: `"Compliance check failed: Nginx is running as the wrong user."`
    7.  **Orchestrator** receives this final piece of information and uses the `finish` tool to generate a complete report for the user.

## 3. The "Notebook and Library" Memory Pattern

**Pattern:** Recall Fact -> Retrieve Context -> Act

**When to Use It:** For any task that requires the agent to combine specific, known facts with broad, contextual knowledge. This pattern makes the agent more efficient and its reasoning more powerful.

**How It Works:**
The agent learns to treat its two memory systems differently.

1.  **The Notebook (Redis):** The agent uses `recall_from_memory` when it needs a *specific, precise piece of data* it has learned before (e.g., a username, a file path, an ID). This is a fast, exact lookup.
2.  **The Library (RAG/Qdrant):** The agent uses `query_knowledge_base` when it needs to *understand a concept* or find general information (e.g., "how does this system work?", "what are the steps to configure this service?"). This is a slower, "fuzzy" semantic search.

**Example Recipe: A Document-Driven Configuration Task**

-   **Prompt:** `"Configure the user 'jdoe' on machine 'ubuntu-qemu' according to the 'user_setup_guide.pdf'."`
-   **Execution Flow:**
    1.  **Plan:** The agent knows it needs to understand the setup process. It doesn't need a specific fact yet.
    2.  **Act (Library):** It calls `query_knowledge_base(query="steps to configure a new user")`.
    3.  **Observe:** It gets back the relevant section from the guide: "1. Create the user. 2. Add them to the 'webdev' group. 3. Set their shell to /bin/bash."
    4.  **Plan:** Now it has a series of steps. It plans the first one: `run_remote_command(command="useradd jdoe")`.
    5.  ...it continues executing the steps from the document...
    6.  **Plan:** At the end of the task, the agent decides to remember this user's primary machine.
    7.  **Act (Notebook):** It calls `save_to_memory(key="user_jdoe_primary_machine", value="ubuntu-qemu")`.
    8.  In a future task, if asked "Where does jdoe work?", it can use `recall_from_memory` to get the answer instantly, without needing to search the library again.