Of course. Here is the final developer guide: **Using the Evaluation Suite**.

This guide is essential for promoting a test-driven development culture for the agent. It teaches developers how to use the objective, data-driven tools we've built to measure their changes and ensure that they are actually improving the agent's performance.

---

# Developer Guide: Using the Evaluation Suite

One of the biggest challenges in developing agentic systems is knowing if a change you made—whether to a tool, a prompt, or a preset—actually made the agent *better*. Relying on a "gut feeling" from a few manual tests is not a reliable or scalable strategy.

AEGIS comes with a built-in evaluation suite that allows you to adopt a **test-driven development (TDD)** workflow. It lets you create a "golden set" of test cases and then automatically run your agent against them and score its performance.

This guide will walk you through the complete workflow: creating a test case, running the evaluation, and interpreting the results.

## The Core Components

Our evaluation suite is powered by two key components working together:

1.  **LangFuse Datasets:** LangFuse provides a UI for creating and managing datasets. A dataset is simply a collection of "test cases," where each case has an **input** (the agent's prompt and configuration) and an **expected output** (what a perfect final summary would look like).
2.  **AEGIS Evaluation Runner:** This is the `aegis run-evals` CLI command. It fetches a dataset from LangFuse, runs the AEGIS agent for each test case, and then uses a powerful **LLM-as-judge** to score the agent's actual output against the expected output.

## Step 1: Create Your First Test Case in LangFuse

The best test cases come from real-world agent runs. The workflow is to run a task, find its trace, and save that trace as a permanent test case.

1.  **Perform a "Golden Run":**
    -   Go to the **Launch** tab in the AEGIS UI.
    -   Configure and run a task for which you know the ideal outcome. For example:
        -   **Preset:** `Default Agent Flow`
        -   **Backend:** `vllm_local`
        -   **Prompt:** `Create a file named 'test.txt' and write 'hello' into it.`
    -   Let the agent run to completion.

2.  **Find the Trace in LangFuse:**
    -   Navigate to the LangFuse UI (`http://localhost:12012`).
    -   Go to the **Traces** tab. You will see the trace for the task you just ran.
    -   **Important:** This trace is the *input* for your test case.

3.  **Save the Trace as a Test Case:**
    -   In the top right corner of the trace view, click the **"Save as Test Case"** button.
    -   A dialog will pop up.
        -   **Dataset:** Type a name for a new dataset, for example, `file_ops_tests`, and press Enter.
        -   **Expected Output:** This is crucial. In this box, you will write what the *perfect* final summary from the agent should look like. This is what the judge will compare against. For our example, you might write:
            > `The task was to create a file named 'test.txt' with the content 'hello'. I successfully used the 'write_to_file' tool to create the file with the correct content.`
    -   Click **Save**.

You have now created your first test case. It contains the exact `LaunchRequest` payload as its input and your hand-written summary as its expected output. You can repeat this process to build a comprehensive dataset of tests.

## Step 2: Run the Evaluation Suite

Now that you have a dataset, you can run the evaluation from the AEGIS command line. The `run-evals` command takes two arguments: the name of the dataset and the backend profile to use for the "judge" LLM. A powerful model like GPT-4 or a high-performance local model is recommended for the judge.

1.  **Execute the Command:**
    From the AEGIS repository root, run:
    ```bash
    python -m aegis.cli run-evals file_ops_tests --judge-model openai_gpt4
    ```

2.  **What's Happening in the Background:**
    -   The `AgentEvaluator` fetches the `file_ops_tests` dataset from LangFuse.
    -   It loops through each test case in the dataset.
    -   For each case, it runs the AEGIS agent using the stored **input**.
    -   After the agent finishes, the evaluator takes the agent's **actual output** (its final summary).
    -   It then sends the input, the expected output, and the actual output to the judge LLM (GPT-4 in this case) and asks it to score the agent's performance on a scale of 1-5.
    -   Finally, it logs this score back to the original trace in LangFuse.

## Step 3: Interpret the Results

The real value comes from analyzing the results in the LangFuse UI.

1.  **Go to the "Scoring" Tab:**
    -   In your LangFuse project, navigate to the **Scoring** tab.
    -   You will see a dashboard showing the average scores for your runs over time.

2.  **Analyze Individual Traces:**
    -   Go back to the **Traces** tab.
    -   You will see that the trace for your evaluation run now has a **Score** attached to it (e.g., `Correctness: 5/5`).
    -   Click on the score to see the **rationale** provided by the judge LLM. It will explain *why* it gave that score.

## The TDD Workflow for Agent Development

Now, you can use this suite to safely make changes to the agent.

1.  **Get a Baseline:** Run the evaluation suite on your main branch to get a baseline performance score (e.g., an average of 4.5/5 across all tests).
2.  **Make a Change:** Create a new branch and make a change—modify a tool's logic, edit a prompt in a preset, or refactor an agent step.
3.  **Run the Evals Again:** Run the `aegis run-evals` command on your new branch.
4.  **Compare the Scores:** Go to the LangFuse scoring dashboard. Did your average score go up, down, or stay the same? You can filter by branch to see a direct comparison.
5.  **Make a Decision:**
    -   If the score improved, your change was a success. Merge it.
    -   If the score dropped, your change caused a regression. Use the traces and the judge's rationales to understand what broke, fix it, and re-run the evals.

By following this workflow, you can move from "I think this change made the agent better" to "I have objective data proving this change made the agent better." This is the key to building and maintaining a truly robust and reliable autonomous agent.