# Operational Guide: Observability & Debugging

An autonomous agent can feel like a "black box." When it works, it's magic. When it fails, it can be frustrating to figure out why. The AEGIS framework is built to be highly observable, giving you the tools you need to open that black box and understand exactly what's happening.

This guide will walk you through a typical debugging workflow for an agent task.

## The Two Key Views: AEGIS and LangFuse

Effective debugging in AEGIS involves using two different web interfaces together:

1.  **The AEGIS UI (`http://localhost:8000`):** This is your **control panel and high-level summary**. It's where you launch tasks and see the final, human-readable report.
2.  **The LangFuse UI (`http://localhost:12012`):** This is your **microscope and flight data recorder**. It gives you a detailed, step-by-step trace of the agent's *entire* thought process.

You will typically have both of these open in separate browser tabs.

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

After a few moments, the task will complete, and you will see an error in the final summary. The summary might say something like: "The task failed because the tool `read_remote_file` could not find the specified file."

This is a good high-level summary, but it doesn't tell us the full story. Why did the agent choose that tool? What was the exact command it ran? To find out, we need to look at the trace.

### Step 2: Open the Trace in LangFuse

1.  Navigate to the **LangFuse UI** at `http://localhost:12012`.
2.  You should see your `AEGIS` project. Click on it.
3.  Go to the **"Traces"** tab.

You will see a new entry at the top of the list for your recent task. The name of the trace will be the `task_id`. Click on it to open the detailed view.

### Step 3: Analyze the Trace

The LangFuse trace view is the heart of the debugging process. It shows a hierarchical timeline of everything that happened during the task.

![LangFuse Trace View](https://langfuse.com/images/docs/sdk-integration-langchain.png)*(Image courtesy of Langfuse)*

Here's how to read it:

1.  **The Root Span (The Whole Task):** The top-level item represents the entire agent run.
2.  **Nested Spans (The Agent's Steps):** Inside, you will see a series of nested spans. Each one corresponds to a **node** in our agent's graph, like `reflect_and_plan` and `execute_tool`.
3.  **LLM Calls:** Any time the agent thought, you will see an "LLM" span. You can click on this to see:
    -   **Input:** The exact, full prompt that was sent to the language model. You can inspect the history and the tool list the agent saw.
    -   **Output:** The raw JSON `AgentScratchpad` that the model returned.
4.  **Tool Calls:** When a tool was run, you will see a "Tool" span. Click on it to see:
    -   **Input:** The exact arguments that were passed to the tool.
    -   **Output:** The exact observation (result or error) that the tool returned.

**Finding Our Error:**

In our example, you would scroll down the trace and find the span for the `execute_tool` step that ran the `read_remote_file` tool.

-   Clicking on the **Input** for this tool would show you `{"machine_name": "ubuntu-qemu", "file_path": "/etc/non_existent_file.txt"}`. You can confirm the agent passed the correct arguments.
-   Clicking on the **Output** would show you the full error message from the `SSHExecutor`, something like `[ERROR] Remote command failed with exit code 1. Output: [STDERR]\ncat: /etc/non_existent_file.txt: No such file or directory`.

### Step 4: Form a Hypothesis

From the trace, we have a complete picture:

-   We can see from the `reflect_and_plan` step's input that the agent correctly understood the goal.
-   We can see that it correctly chose the `read_remote_file` tool.
-   We can see that the tool failed with a "No such file or directory" error.

Our hypothesis is simple: **The agent's plan was correct, but the state of the world (the file's non-existence) caused a tool failure.**

If the agent had made a different mistake (e.g., hallucinating a tool name like `read_a_file`), we would have seen *that* error in the `execute_tool` output instead. If it had produced bad JSON, we would see a `PlannerError` logged in the trace.

### Step 5: Create a Test Case (Optional but Recommended)

LangFuse makes it easy to turn this failed run into a permanent regression test.

-   In the top right of the trace view, click the **"Save as Test Case"** button.
-   Add it to a new or existing dataset (e.g., `core_failure_tests`).

Now, you can use the `aegis run-evals` CLI command to automatically re-run this exact scenario in the future, ensuring that any changes you make don't reintroduce old bugs.

---

By using the AEGIS and LangFuse UIs together, you move from guessing what the agent did to knowing *exactly* what it did, why it did it, and where it went wrong. This observability is the key to building, debugging, and ultimately trusting your autonomous systems.