# aegis/tools/wrappers/__init__.py
"""
The `wrappers` package contains higher-level tools that compose primitives
or other wrappers to perform more complex, multi-step tasks.

These tools are designed to provide more convenient, goal-oriented actions
for the agent, such as "backup a remote file" (which combines checking for
existence and then copying) or "run a port scan" (which composes a shell
command with specific arguments).
"""
