# Developer Guide: Creating a Specialist Agent Preset

As you build more complex systems with AEGIS, you'll find that a single "generalist" agent can become inefficient. If an agent has dozens of tools to choose from, its planning prompt becomes noisy, increasing the chance of confusion and errors.

The solution is the **Agentic Mixture of Experts (MoE)** pattern. You create a high-level "Orchestrator" agent that delegates tasks to a team of "Specialist" agents. Each specialist is an expert in a narrow domain because it can only see and use a small, curated set of tools.

This guide will walk you through the process of creating a new **Specialist Agent Preset**. We'll build a `DatabaseAgent` that is an expert at nothing but interacting with a SQL database.

## The Goal

Our goal is to create a new agent preset that:
1.  Is an expert in a specific domain (SQL).
2.  Is "blind" to all other irrelevant tools (like `gui_action` or `synthesize_speech`).
3.  Can be called by an Orchestrator agent to handle database-related sub-tasks.

## Step 1: Identify the Tools for Your Specialist

The first step is to decide which tools your specialist needs. Look through the full inventory in the AEGIS UI's "Tools" tab and pick only the ones that are directly relevant to the agent's domain.

For our `DatabaseAgent`, we will assume we have a set of SQL tools (or we can use `run_remote_command` as a stand-in). A perfect, minimal set of tools would be:

-   `run_sql_query`: To execute a query.
-   `get_table_schema`: To inspect a table.
-   `list_tables`: To see what tables are in the database.
-   `invoke_llm`: A crucial "utility" tool. This allows the specialist to summarize the results of its database queries before returning a clean, concise answer to the Orchestrator.

## Step 2: Create the Preset File

Agent presets are defined as YAML files in the `presets/` directory.

1.  **Create a New File:**
    Create a new file named `presets/database_agent.yaml`.

2.  **Define the Basic Structure:**
    Every preset needs a basic graph structure. For most specialists, the `default.yaml` preset is a perfect starting point. Copy its contents into your new file.

  ```yaml
  # presets/database_agent.yaml
    name: "Database Specialist Agent"
    description: "A specialist agent that can only see and use database-related tools. It can answer questions by querying a SQL database."
    state_type: "aegis.agents.task_state.TaskState"
    entrypoint: "plan"

    nodes:
      - id: "plan"
        tool: "reflect_and_plan"
      - id: "execute"
        tool: "execute_tool"
      - id: "summarize"
        tool: "summarize_result"

    edges:
      - ["plan", "execute"]
      - ["summarize", "__end__"]

    condition_node: "execute"
    condition_map:
      continue: "plan"
      end: "summarize"
  ```

## Step 3: Define the `tool_allowlist`

This is the most important step. We will now add a `runtime` block to the preset and define the `tool_allowlist`. This is the magic that transforms a generalist agent into a specialist.

When the `reflect_and_plan` step runs for an agent using this preset, it will see the `tool_allowlist` and will only show the agent the tools from this list in its prompt.

Add the following to the bottom of your `presets/database_agent.yaml` file:

```yaml
# ... (rest of the file from above) ...

# This agent's runtime configuration specifies a tool allow-list.
# It will only see these tools in its prompt, making it more focused and reliable.
runtime:
  tool_allowlist:
    - "run_remote_command" # A proxy for a real 'run_sql_query' tool
    - "read_remote_file" # A proxy for a real 'get_table_schema' tool
    - "get_remote_directory_listing" # A proxy for a real 'list_tables' tool
    - "invoke_llm" # For summarizing results
```

**Note:** We are using general-purpose tools like `run_remote_command` as stand-ins for more specific, hypothetical tools like `run_sql_query`. This demonstrates that you can create specialists from any combination of existing tools.

## Step 4: Use Your Specialist Agent

Your new specialist agent is now ready to be used. You can use it in two ways:

### A. Direct Invocation (for Testing)

You can test your specialist directly from the AEGIS UI.

1.  **Start AEGIS** and go to the **Launch** tab.
2.  **Agent Preset:** You will now see your **`Database Specialist Agent`** in the dropdown. Select it.
3.  **Backend Profile:** Choose a backend (e.g., `vllm_local`).
4.  **Task Prompt:** Give it a prompt that is specific to its domain:
    > `"Find out the schema of the 'users' table on the 'ubuntu-qemu' machine."`

When you launch this task, you can inspect the `reflect_and_plan` step in the provenance report in the Artifacts tab. You will see that the "Available Tools" section of the prompt is now very short—it only contains the four tools from your allow-list. This makes it much easier for the agent to succeed.

### B. Delegation from an Orchestrator (The MoE Pattern)

The real power of a specialist is realized when it's called by an Orchestrator. The Orchestrator uses the `dispatch_subtask_to_agent` tool.

1.  **Use the Orchestrator Preset:** In the Launch tab, select the `Orchestrator Agent` preset.
2.  **Give it a Complex Prompt:**
    > `"I need a report on our active users. First, query the database on the 'ubuntu-qemu' machine to get the top 5 most recent users. Then, look up the public IP address of our server. Combine these two pieces of information into a final report."`
3.  **Launch the Task.**

The Orchestrator agent will now execute the following logic:
-   **Step 1:** It will realize the first part of the task is about databases. It will call `dispatch_subtask_to_agent(prompt="query the database on 'ubuntu-qemu'...", preset="database_agent")`.
-   **Step 2:** The `DatabaseAgent` will run in its own sub-task, use its specialized tools, and return a summary: `"The top 5 users are Alice, Bob, and Charlie."`
-   **Step 3:** The Orchestrator receives this summary. It now plans its next step, which is to call the `get_public_ip` tool.
-   **Step 4:** It combines the results and finishes.

---

By following this pattern, you can build a team of highly reliable, specialized agents. This makes your overall system more robust, easier to debug, and capable of solving much more complex, multi-domain problems.