# Operational Guide: Observability & Debugging

An autonomous agent can feel like a "black box." When it works, it's magic. When it fails, it can be frustrating to figure out why. The AEGIS framework is built to be highly observable, giving you the tools you need to open that black box and understand exactly what's happening.

This guide will walk you through a typical debugging workflow for an agent task using the tools built directly into AEGIS.

## The Two Key Views: The UI and The Provenance Report

Effective debugging in AEGIS involves using two different views together:

1.  **The AEGIS UI (`http://localhost:8000`):** This is your **control panel and real-time monitor**. It's where you launch tasks and, most importantly, watch the live, structured logs stream in from the agent as it works.
2.  **The Provenance Report (`reports/<task_id>/provenance.json`):** This is your **microscope and flight data recorder**. After a task is complete, this machine-readable JSON file gives you a perfect, step-by-step record of the agent's *entire* thought process.

## Scenario: Debugging a Failed Task

Let's imagine you give the agent the following prompt:

> "Read the contents of the file at '/etc/non_existent_file.txt' on the 'ubuntu-qemu' machine and tell me what it says."

This task is designed to fail, because the file doesn't exist. Let's see how we would debug this.

### Step 1: Launch the Task in AEGIS

1.  Navigate to the **Launch** tab in the AEGIS UI.
2.  Select the `Verified Agent Flow` preset.
3.  Select the `vllm_local` backend profile.
4.  Enter the prompt above.
5.  Click **"Launch Task"**.

As the agent runs, you will see structured JSON logs appear in the **Live Task Logs** panel. These logs provide real-time insight. You might see an `INFO` log for the `ToolStart` event, followed quickly by an `ERROR` log for the `ToolEnd` event, giving you your first clue that something went wrong during execution.

### Step 2: Open the Artifacts in the UI

Once the task completes, navigate to the **Artifacts** tab.

1.  You will see a new entry at the top of the list for your recent task. The status will likely be `FAILURE` or `PARTIAL`.
2.  Click on the entry to expand it.

### Step 3: Analyze the Provenance Report

Click on the **Provenance** tab within the expanded artifact view. This shows you the detailed JSON report of the task. This is the heart of the debugging process.

Here's how to read it:

1.  **`task_prompt`:** The top-level key confirms the exact goal you gave the agent.
2.  **`events`:** This is an array containing the step-by-step history. Find the event that failed.
    -   **`thought`:** You can see the agent's reasoning *before* it acted. Did it correctly decide to use `read_remote_file`?
    -   **`tool_name` and `tool_args`:** You can verify the exact tool and arguments it used (e.g., `{"machine_name": "ubuntu-qemu", "file_path": "/etc/non_existent_file.txt"}`).
    -   **`observation`:** This is the most important field for debugging. Here, you will see the full error message returned by the tool, something like `[ERROR] ToolExecutionError: Remote command failed with exit code 1. Output: [STDERR]\ncat: /etc/non_existent_file.txt: No such file or directory`.
    -   **`status`:** This will be marked as `failure`.

### Step 4: Form a Hypothesis

From the provenance report, we have a complete picture:

-   We can see from the `thought` that the agent correctly understood the goal.
-   We can see that it correctly chose the `read_remote_file` tool.
-   We can see that the tool failed with a "No such file or directory" error.

Our hypothesis is simple: **The agent's plan was correct, but the state of the world (the file's non-existence) caused a tool failure.**

If the agent had made a different mistake (e.g., hallucinating a tool name like `read_a_file`), we would have seen a `ToolNotFoundError` in the `observation`. If it had produced bad JSON for its plan, we would see a `PlannerError` and the task would have likely failed before any tools were even run.

By using the live logs for real-time monitoring and the detailed provenance report for post-mortem analysis, you can move from guessing what the agent did to knowing *exactly* what it did, why it did it, and where it went wrong.