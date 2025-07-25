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

1.  **Clone, Configure Auth:**
    Clone the BEND repository, enter the directory, and create your `.env` file.
    ```bash
    git clone https://github.com/your-username/BEND.git
    cd BEND
    cp .env.example .env
    ```
    Now, **edit the `.env` file** and add your Hugging Face token if you plan to use gated models like Llama 3.

2.  **Download Your Models:**
    Download both the full repository for vLLM and the single GGUF file for KoboldCPP.
    ```bash
    # Download the full Llama 3 repository for vLLM
    ./scripts/download-hf-model.sh "meta-llama/Meta-Llama-3-8B-Instruct"

    # Download the Llama 3 GGUF file for KoboldCPP
    ./scripts/download-gguf-model.sh llama3
    ```

3.  **Configure the Stack:**
    Run the `switch-model.sh` script to configure all services to use the model you just downloaded.
    ```bash
    ./scripts/switch-model.sh llama3
    ```

4.  **Start the BEND Stack:**
    Launch all the BEND services.
    -   **For CPU-only:**
        ```bash
        ./scripts/manage.sh up
        ```
    -   **For NVIDIA GPU acceleration (recommended):**
        ```bash
        ./scripts/manage.sh up --gpu
        ```

5.  **Verify BEND:**
    In a new terminal, run the healthcheck. **Wait for all services to report `[ OK ]` before proceeding.**
    ```bash
    ./scripts/manage.sh healthcheck
    ```

## Step 2: Set Up the AEGIS Agent Framework

Now, we'll set up AEGIS and connect it to our running BEND instance.

1.  **Clone AEGIS:**
    Navigate back to your main projects folder (the parent directory of BEND) and clone the AEGIS repository.
    ```bash
    cd ..
    git clone https://github.com/your-username/AEGIS.git
    cd AEGIS
    ```

2.  **Configure the Environment:**
    AEGIS needs its own `.env` file for secrets. The only secrets used by default are for machine passwords, but you may add your own.
    ```bash
    cp .env.example .env
    ```

3.  **Synchronize Model Definitions:**
    To ensure AEGIS knows about the models BEND is serving, run the sync script.
    ```bash
    ./scripts/sync_models.sh
    ```

## Step 3: Start AEGIS

With both repositories configured, you can now start the AEGIS service.

```bash
# Make sure you are in the AEGIS directory
docker compose up --build -d
```

## Step 4: Run a Fully Local Task

You now have the complete, self-hosted stack running.

1.  **Open the AEGIS UI:**
    Navigate to **`http://localhost:8000`** in your browser.

2.  **Configure the Task:**
    -   **Agent Preset:** Choose `Verified Agent Flow`.
    -   **Backend Profile:** Choose `vllm_local`.
    -   **Agent Model:** Choose `Llama 3 Instruct Family`.
    -   **Task Prompt:** Give it a task that uses its tools. For example:
        > `Use your long-term memory to remember that the secret key is 'blue-banana'. Then, recall the key and finish the task, stating the key in your reason.`

3.  **Launch and Observe:**
    -   Click **"Launch Task"**.
    -   Watch the logs in the AEGIS UI's **Live Task Logs** panel.
    -   When complete, view the detailed results in the **Artifacts** tab.

## Next Steps

You have now successfully set up and run a fully autonomous, fully self-hosted agentic framework!

To stop the entire stack, you can run the `down` command in both repositories:
```bash
# In the AEGIS directory
./manage_stack.sh down

# In the BEND directory
./scripts/manage.sh down
```