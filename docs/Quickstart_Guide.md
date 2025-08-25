# AEGIS Quickstart Guide (Standalone)

Welcome to AEGIS! This guide will help you get the agentic framework up and running in a standalone capacity. In this mode, AEGIS acts as a powerful "brain" that connects to an external or commercial AI backend, like OpenAI's API.

This setup is perfect for users who want to leverage the power of AEGIS's agentic logic without setting up a local model-serving stack. By the end of this guide, you will be able to run a fully autonomous agent task powered by a commercial AI provider.

## How AEGIS Works

AEGIS is a framework for building and running autonomous agents. It works by following a "thought cycle" that is defined by a workflow, or **Preset**. A typical workflow looks like this:

1.  **Plan:** The agent looks at the main goal and its history, then asks the AI backend (e.g., GPT-4) to decide on the single next action to take.
2.  **Execute:** The agent runs the tool it decided on (e.g., `write_to_file` or `run_local_command`).
3.  **Observe:** The agent records the result of the tool's action.
4.  **Repeat:** The agent loops back to the planning step, now with new information in its history, until the goal is complete.

Our job in this guide is to configure AEGIS to use your chosen AI backend for that crucial "Plan" step.

## Prerequisites

Before you start, you'll need to have a few things installed on your machine:

-   **Docker & Docker Compose:** For running the containerized agent.
-   **`git`:** For cloning the repository.
-   **An AI Backend with an API Key:** This guide assumes you will be using a service with an OpenAI-compatible API (like OpenAI itself, Together AI, or Perplexity). You will need an API key from your chosen provider.

## Step 1: Get the Code

First, clone the AEGIS repository to your local machine and navigate into the directory.

```bash
git clone https://github.com/your-username/AEGIS.git
cd AEGIS
```bash

## Step 2: Configure Your Backend Connection

AEGIS needs to know how to connect to your chosen AI backend. All backend configurations are managed in the `backends.yaml` file.

1.  **Review `backends.yaml`:**
    Open this file to see the pre-configured profiles. The one we care about for this guide is `openai_gpt4`.
    ```yaml
    # aegis/backends.yaml
    - profile_name: openai_gpt4
      type: openai
      model: gpt-4-turbo
      api_key: ${OPENAI_API_KEY}
      # ... other settings
    ```
    This profile tells AEGIS to use its built-in `OpenAIProvider`, which knows how to talk to OpenAI's API. The `${OPENAI_API_KEY}` is a placeholder that tells AEGIS to look for your secret key in an environment variable.

2.  **Create Your `.env` File:**
    This file is where you will securely store your API key. Copy the example file to create your own:
    ```bash
    cp .env.example .env
    ```
    Now, open the new `.env` file with a text editor and add your API key.
    ```env
    # AEGIS/.env

    # --- Backend API Keys ---
    OPENAI_API_KEY=sk-youractualapikey...
    ```
    When the AEGIS container starts, it will automatically load this file and make the secret key available to the `openai_gpt4` profile.

## Step 3: Start the AEGIS Service

You're now ready to build and run the AEGIS container. This command reads your `docker-compose.yml` and `.env` files to start the server correctly.

docker compose up --build -d
```bash
docker compose up --build -d
```

The first time you run this, Docker will download the necessary base images and build the AEGIS application, which may take a few minutes. Subsequent starts will be much faster.

## Step 4: Access the UI and Verify

Once the service is running, you can access the AEGIS dashboard in your browser.

-   Navigate to **`http://localhost:8000`**

You should see the main dashboard. To verify that the agent is ready:

- Open the **"Tools"** tab and confirm the tool registry is populated (you should see `run_local_command`, `read_file`, `get_public_ip`, etc.).
- Inspect the logs for successful startup messages. If running with Docker Compose:

docker compose logs aegis --tail=200
```bash
docker compose logs aegis --tail=200
```

- Confirm the HTTP API responds:

```bash
curl -s http://localhost:8000/api/backends | jq .
```

If any of these checks fail, consult the `logs/` directory and the container logs for stack traces.

## Step 5: Run Your First Task

Let's give the agent a simple, multi-step task to perform.

1.  **Navigate to the "Launch" Tab:**
    This is the main control panel for running agent tasks.

2.  **Configure the Task:**
    -   **Agent Preset:** Choose `Default Agent Flow`. This is a simple and reliable plan-and-execute loop.
    -   **Backend Profile:** This is the most important step. Choose `openai_gpt4` from the dropdown. This tells the agent to use the OpenAI backend you configured for its "thinking."
    -   **Agent Model:** For the OpenAI provider, the model is already defined in the backend profile (`gpt-4-turbo`), so this selection is less critical.
    -   **Task Prompt:** Enter a simple, safe goal for the agent. For example:
        > `Write a short Python script to a file named 'hello.py' that prints 'Hello from AEGIS!', and then run the script.`

3.  **Launch the Task:**
    Click the **"Launch Task"** button.

You can now watch the agent's progress in the **"Live Task Logs"** panel on the right. You will see the agent think, choose the `write_to_file` tool, then the `run_local_command` tool, and finally the `finish` tool. The agent is making live API calls to your chosen backend for each planning step.

When it's done, the final result and a step-by-step history of its execution will appear on the left.

## Next Steps

You have now successfully run a fully autonomous agent task using a standalone AEGIS instance! From here, you can explore the other presets, try more complex prompts, or move on to the **Combined BEND + AEGIS Quickstart Guide** to learn how to run the entire system locally without relying on external APIs.

To stop the AEGIS service at any time, run:
```bash
docker compose down
```

## Troubleshooting common startup issues

- Ports already in use: Ensure `8000` is free or change `docker-compose.yml` to map to a different host port.
- Missing environment variables: Ensure `.env` has the required keys and that `docker compose` is started from the repo root.
- Slow model pull: If the backend needs to download models (BEND), the first start may take many minutes; check network activity and the BEND logs.
