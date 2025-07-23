Understood. Here is the expanded version of the **Combined BEND + AEGIS Quickstart Guide**.

This guide now includes more context on how the two systems connect, clearer instructions for each step, and a more detailed verification process to ensure users have a smooth and successful setup experience.

---

# Quickstart Guide (BEND + AEGIS)

Welcome! This guide will walk you through setting up and running the complete, self-hosted AEGIS and BEND stack. By running both projects together, you get a powerful, fully autonomous agentic system that runs entirely on your own hardware, with no reliance on external cloud services.

This is the recommended setup for getting the most out of the framework.

## How They Work Together

The two projects are designed to be a tightly integrated client-server system. Getting them to communicate is the key to this guide.

-   **BEND (The Backend):** Provides the core, high-horsepower services like the LLM (vLLM), vector database (Qdrant), and agent memory (Redis). It creates a private Docker network for all of its services to talk to each other.
-   **AEGIS (The Frontend/Brain):** Provides the autonomous agent that connects to BEND to think, plan, and execute tasks. Its Docker container is configured to **join BEND's private network**, which is how it's able to find and talk to services like `vllm` and `redis`.

This guide will walk you through starting BEND first, then starting AEGIS and connecting it to BEND's network.

## Prerequisites

Before you start, you'll need to have a few things installed on your machine:

-   **Docker & Docker Compose:** For running the containerized services.
-   **`git`:** For cloning the repositories.
-   **`yq`:** A command-line YAML processor (e.g., `brew install yq`).
-   **(Optional) NVIDIA GPU:** For the best performance, an NVIDIA GPU with drivers and the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) is highly recommended.

## Step 1: Set Up the BEND Backend

First, we need to get the BEND intelligence stack up and running. This will be the "power source" for AEGIS.

1.  **Clone and Prepare BEND:**
    Find a good place for your projects, then clone the BEND repository.
    ```bash
    git clone https://github.com/your-username/BEND.git
    cd BEND
    ```

2.  **Download and Configure a Model:**
    BEND needs to know which language model to serve. We'll use the recommended `llama3` model.
    ```bash
    # Download the GGUF version needed for the KoboldCPP service
    ./scripts/download-model.sh llama3
    
    # Configure the .env file for both vLLM and KoboldCPP
    ./scripts/switch-model.sh llama3
    ```
    This creates the crucial `.env` file that tells Docker Compose which models to load.

3.  **Start the BEND Stack:**
    Now, launch all the BEND services. This command will create the shared Docker network (`bend_bend-net`) that AEGIS will join later.
    -   **For CPU-only:**
        ```bash
        ./scripts/manage.sh up
        ```
    -   **For NVIDIA GPU acceleration (recommended):**
        ```bash
        ./scripts/manage.sh up --gpu
        ```

4.  **Verify BEND:**
    In a new terminal, run the healthcheck to ensure all services are running correctly. **It is important to wait for this step to succeed before starting AEGIS.**
    ```bash
    # Make sure you are in the BEND directory
    cd /path/to/your/BEND
    ./scripts/manage.sh healthcheck
    ```
    vLLM can sometimes take a minute or two to download its model and become healthy. If the healthcheck fails at first, wait a moment and try again. Once all services show `[ OK ]`, your backend is ready.

## Step 2: Set Up the AEGIS Agent Framework

Now, we'll set up AEGIS and connect it to our running BEND instance.

1.  **Clone AEGIS:**
    Navigate back to your main projects folder (the parent directory of BEND) and clone the AEGIS repository. It's important that BEND and AEGIS are in the same parent folder for the scripts to work correctly.
    ```bash
    cd ..
    git clone https://github.com/your-username/AEGIS.git
    cd AEGIS
    ```

2.  **Configure the Environment:**
    AEGIS needs its own `.env` file to know how to connect to BEND's services and your LangFuse instance.
    ```bash
    cp .env.example .env
    ```
    Now, open the new `.env` file. The only thing you **must** do is get your **LangFuse API keys** from the LangFuse UI running at `http://localhost:12012`. Follow the on-screen setup, create a project named `AEGIS`, go to "Project Settings" -> "API Keys", and copy the keys into your `.env` file. It should look something like this:
    ```env
    # AEGIS/.env
    LANGFUSE_PUBLIC_KEY=pk-lf-...your-public-key...
    LANGFUSE_SECRET_KEY=sk-lf-...your-secret-key...
    
    # The BEND_NETWORK_NAME should be correct by default if your BEND
    # folder is named 'BEND'. If you renamed it, update this value.
    BEND_NETWORK_NAME=bend_bend-net
    ```

3.  **Synchronize Model Definitions:**
    To ensure AEGIS knows about the models BEND is serving, run the sync script.
    ```bash
    ./scripts/sync_models.sh
    ```
    This reads `BEND/models.yaml` and updates the local `AEGIS/models.yaml`, creating a single source of truth and preventing configuration mismatches.

## Step 3: Start AEGIS

With both repositories configured, you can now start the AEGIS service.

```bash
# Make sure you are in the AEGIS directory
cd /path/to/your/AEGIS

# This command will build the agent and connect it to BEND's network
docker compose up --build -d
```

## Step 4: Run a Fully Local Task

You now have the complete, self-hosted stack running.

1.  **Open the AEGIS UI:**
    Navigate to **`http://localhost:8000`** in your browser.

2.  **Configure the Task:**
    -   **Agent Preset:** Choose `Verified Agent Flow`.
    -   **Backend Profile:** Choose `vllm_local`. This tells AEGIS to send its requests to the vLLM service running in your BEND stack.
    -   **Agent Model:** Choose `Llama 3 Instruct Family`.
    -   **Task Prompt:** Give it a task that uses its tools. For example:
        > `Use your long-term memory to remember that the secret key is 'blue-banana'. Then, recall the key and finish the task, stating the key in your reason.`

3.  **Launch and Observe:**
    -   Click **"Launch Task"**.
    -   Watch the logs in the AEGIS UI.
    -   For a highly detailed, step-by-step view of the agent's thoughts, open the **LangFuse UI** at `http://localhost:12012`. You will see a new trace appear for your task, allowing you to inspect every tool call and LLM prompt.

## Next Steps

You have now successfully set up and run a fully autonomous, fully self-hosted agentic framework! You can now experiment with more complex prompts, build specialist agents with the MoE pattern, or start developing your own custom tools.

To stop the entire stack, you can run the `down` command in both repositories:
```bash
# In the AEGIS directory
docker compose down

# In the BEND directory
./scripts/manage.sh down
```