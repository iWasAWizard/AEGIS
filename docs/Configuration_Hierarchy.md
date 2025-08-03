# AEGIS Configuration Hierarchy

A key feature of the AEGIS framework is its powerful and flexible hierarchical configuration system. This system allows you to set sensible, system-wide defaults while also providing the ability to override those settings for specific agent workflows or even for a single task run. Understanding this hierarchy is crucial for effectively managing and testing your agents.

The agent's final runtime configuration is built by merging settings from three distinct levels. Settings at a higher level of precedence will always override the same settings from a lower level.

**Order of Precedence (Lowest to Highest):**
1.  **System-Wide Defaults (`config.yaml`)**
2.  **Preset-Specific Defaults (`presets/*.yaml`)**
3.  **Launch-Time Overrides (API Request or Test File)**

---

## Level 1: System-Wide Defaults

This is the foundation of the configuration hierarchy. The `defaults` block in the main `config.yaml` file provides the baseline configuration for the entire framework. If no other settings are specified for a particular run, the values from this file will be used.

*   **File:** `aegis/config.yaml`
*   **Example:**
    ```yaml
    # aegis/config.yaml
    defaults:
      # This is the ultimate fallback backend profile.
      backend_profile: "vllm_local"

      # This is the ultimate fallback model key.
      llm_model_name: "hermes"

      iterations: 10
      safe_mode: true
    ```
*   **Role:** To provide a reliable, "works-out-of-the-box" default configuration that ensures the agent can always run, even with a minimal launch request.

---

## Level 2: Preset-Specific Defaults

Each agent preset file (located in the `presets/` directory) can optionally contain its own `runtime` block. These settings override the system-wide defaults from `config.yaml`, allowing you to create presets that are pre-configured for specific backends, models, or behaviors.

*   **File:** `aegis/presets/orchestrator.yaml`
*   **Example:**
    ```yaml
    # aegis/presets/orchestrator.yaml
    name: "Orchestrator Agent"
    description: "A high-level agent that delegates tasks."
    # ... graph structure ...

    runtime:
      # This preset will ALWAYS use vllm_local and hermes by default,
      # overriding the system-wide settings from config.yaml.
      backend_profile: "vllm_local"
      llm_model_name: "hermes"
      iterations: 5 # This preset is for high-level tasks, so it needs fewer steps.
    ```
*   **Role:** To create specialized agent "personalities" or workflows. For example, you can create a `red_team_agent` preset that always runs with `safe_mode: false` and a `tool_allowlist` containing only security tools.

---

## Level 3: Launch-Time Overrides

This is the highest level of precedence. The settings provided in a specific launch request will override everything from the preset and the system defaults. This provides the ultimate level of granular control for a single task run.

This applies to both:
-   The JSON payload sent to the `/api/launch` endpoint.
-   The `execution` block in a `tests/regression/*.yaml` file.

*   **Source:** A specific task launch request.
*   **Example:**
    ```yaml
    # A regression test file: tests/regression/test_openai_run.yaml
    task:
      prompt: "This is a test to run specifically on OpenAI."

    config: "default" # Start with the 'default' preset.

    # This 'execution' block is the final word for this run.
    execution:
      # This will override the system default ('vllm_local') and any
      # settings that might be in the 'default' preset.
      backend_profile: "openai_gpt4"
      iterations: 20 # Give this specific task more steps.
    ```
*   **Role:** To allow for fine-grained control over a single task without needing to create a new preset. This is essential for experimentation, debugging, and running regression tests against specific backend configurations.

---

### **Putting It All Together: A Concrete Example**

Let's trace the configuration for a regression test defined in `test_basic_file_ops.yaml`:

1.  **The Test File (`Level 3`):**
    ```yaml
    # tests/regression/test_basic_file_ops.yaml
    config: "verified_flow"
    execution:
      iterations: 8
      safe_mode: true
    ```
    This file specifies the preset (`verified_flow`) and overrides `iterations` and `safe_mode`. It does **not** specify a `backend_profile` or `llm_model_name`.

2.  **The Preset File (`Level 2`):**
    The `run_regression_tests.py` script loads the `presets/verified_flow.yaml` file. We check it for a `runtime` block. It has one, but it only sets `safe_mode: false`. It does not specify a backend.
    ```yaml
    # presets/verified_flow.yaml
    ...
    runtime:
      safe_mode: false
    ```
    The `safe_mode: true` from the test file (Level 3) will override the `safe_mode: false` from the preset (Level 2).

3.  **The System Default (`Level 1`):**
    Since neither the test file nor the preset specified a `backend_profile` or `llm_model_name`, the system falls back to `config.yaml`, which defines `backend_profile: "vllm_local"` and `llm_model_name: "hermes"`.

**Conclusion:** The `test_basic_file_ops.yaml` test will run using the **`verified_flow`** graph with the following final configuration:
-   `backend_profile`: `"vllm_local"` (from Level 1)
-   `llm_model_name`: `"hermes"` (from Level 1)
-   `iterations`: `8` (from Level 3, overriding the default of 10 from Level 1)
-   `safe_mode`: `true` (from Level 3, overriding the `false` from Level 2 and the `true` from Level 1)