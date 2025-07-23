# AEGIS UI & CLI Guide

AEGIS gives you two main ways to interact with your autonomous agents: a graphical **Web UI** for interactive use and a **Command-Line Interface (CLI)** for scripting and automation. This guide will walk you through both.

## Part 1: The Web UI

The web UI is the easiest way to get started with AEGIS. It's a comprehensive dashboard for launching tasks, monitoring the agent, and exploring its capabilities.

### Accessing the UI

Once you have the AEGIS stack running, simply open your browser and navigate to:

-   **`http://localhost:8000`**

### Exploring the Tabs

The UI is organized into several tabs, each with a specific purpose.

#### 🏠 Dashboard

This is your main landing page. It provides an at-a-glance view of the system, including:
-   **Recent Activity:** A list of the most recently completed agent tasks. You can click on any task to jump directly to its artifacts.
-   **System Status:** A panel showing key details about the running AEGIS server, such as its platform and current working directory.

#### 🚀 Launch

This is the most important tab—it's the agent's control panel. Here's how to use it:

1.  **Agent Preset:** Choose the agent's "personality" or workflow from this dropdown. The `Verified Agent Flow`, for example, is a robust workflow that double-checks its own work.
2.  **Backend Profile:** Select which AI backend you want the agent to use for this task (e.g., `vllm_local` to use your BEND stack, or `openai_gpt4` to use OpenAI).
3.  **Agent Model:** Choose which specific model you want the agent to use. This list is synchronized with the model manifest.
4.  **Task Prompt:** This is where you give the agent its high-level goal. Be as descriptive as you need to be.
5.  **Enable Safe Mode:** A checkbox that, when enabled, prevents the agent from using any tools marked as "unsafe" (like `run_local_command`).
6.  **Advanced: Execution Overrides:** An optional text box where you can provide a JSON object to override runtime settings for this specific task (e.g., `{"iterations": 20}`).

Once you click **"Launch Task"**, the right-hand **"Live Task Logs"** panel will stream the agent's internal monologue in real-time. When the task is complete, the final summary and a step-by-step history will appear on the left.

**Human-in-the-Loop (HITL) Mode:**
If you run a task with a preset like `human_in_the_loop`, the launch panel will transform when the agent needs your help.
-   The main form will be replaced by a **"Task Paused"** panel.
-   It will display the **Agent's Question**.
-   You can type your answer or instructions into the **"Your Response"** text area and click **"Resume Task"** to let the agent continue.

#### 🗺️ Graph

This tab provides a visual, interactive flowchart of the agent presets. It's a great way to understand how an agent "thinks" by showing the different steps (nodes) and the transitions (edges) between them.

#### 🧰 Tools

This tab is the agent's "résumé." It lists every single tool the agent has available, including its name, description, and the exact input format it expects. It's the perfect place to see what your agent is capable of.

#### 🧠 Presets

This is an editor that lets you view and modify the agent's core behavior. You can select a preset from the left to see its underlying graph configuration as JSON.

#### ✏️ Config Editor

This provides a way to live-edit the core YAML configuration files (`backends.yaml`, `config.yaml`, etc.) directly from the UI. Changes are saved to the host machine and will be picked up on the next agent run.

#### 📦 Artifacts

This tab is an archive of all past task runs. You can see a list of every task and expand any of them to view:
-   **Summary:** A human-readable report of the task.
-   **Provenance:** A machine-readable JSON file containing a detailed, step-by-step log of the entire task, perfect for auditing and analysis.

---

## Part 2: The Command-Line Interface (CLI)

The CLI is a powerful tool for scripting, automation, and running tests. All commands are run from the AEGIS repository root.

### `run-task`

This is the CLI equivalent of the "Launch" tab. It runs an agent task based on a YAML file.

1.  **Create a Task File:**
    Create a file named `my_task.yaml` with the following structure:
    ```yaml
    # my_task.yaml
    task:
      prompt: "Write a haiku about autonomous agents to a file named haiku.txt."

    config: "default" # The preset to use (e.g., default, verified_flow)

    execution:
      backend_profile: "vllm_local" # The backend to use
      llm_model_name: "llama3" # The model to use
      iterations: 5
    ```

2.  **Run the Task:**
    ```bash
    python -m aegis.cli run-task my_task.yaml
    ```The agent will execute the task, printing its progress to the console.

### `list-tools`

Lists all available tools in a clean table format.

```bash
python -m aegis.cli list-tools
```

### `validate-config`

A crucial safety check. This command proactively loads and validates all of your YAML configuration files (`backends.yaml`, `machines.yaml`, all presets, etc.) and reports any errors. Run this after making changes to your configuration to ensure everything is correct before starting the server.

```bash
python -m aegis.cli validate-config
```

### `run-evals`

Runs the automated evaluation suite against a LangFuse dataset. This is used to test the agent's performance and catch regressions.

```bash
# Example: Run the 'file_ops_tests' dataset using gpt-4 as the judge
python -m aegis.cli run-evals file_ops_tests --judge-model openai_gpt4
```

### `new-tool`

An interactive command to create a boilerplate Python file for a new tool in the `plugins/` directory.

```bash
python -m aegis.cli new-tool
```

### `validate-tool`

Checks a single tool file for syntax errors and ensures its registration metadata is correct.

```bash
python -m aegis.cli validate-tool plugins/my_new_tool.py```