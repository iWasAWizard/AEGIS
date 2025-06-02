# Machine Manifest Field Reference

This document describes all available fields in the `machines.yaml` manifest used by the Agentic LLM system. Each VM or host entry should include a combination of required and optional keys depending on its platform, provider, and control mode.

## 🧾 Field Summary

| Key             | Required         | Description                                                                                                 |
|-----------------|------------------|-------------------------------------------------------------------------------------------------------------|
| `name`          | ✅                | Agent-facing nickname (must be unique).                                                                     |
| `ip`            | ✅                | Resolvable IP address or hostname for the guest OS.                                                         |
| `platform`      | ✅                | Operating system of the guest VM or host (`linux`, `windows`, `mac`).                                       |
| `provider`      | ✅                | Source environment (`qemu`, `esxi`, `vmware`, `proxmox`, `physical`).                                       |
| `type`          | ✅                | Logical host type for routing: `vm`, `physical`, or `container`.                                            |
| `shell`         | ✅                | Shell interpreter to be used for commands: `bash`, `sh`, `zsh`, `powershell`.                               |
| `username`      | ✅                | Username used for login to the guest.                                                                       |
| `password`      | ✅                | Password for login. Replaceable with key-based auth if needed.                                              |
| `ssh_port`      | ⛔️ (if SSH used) | SSH port number, only required if remote command exec is via SSH.                                           |
| `vmtools_path`  | ⛔️               | Path to guest agent (e.g., `qemu-guest-agent`, `vmtoolsd.exe`) if using hypervisor-guest passthrough tools. |
| `esxi_host`     | ✅ (for ESXi)     | IP or hostname of the ESXi or vCenter host.                                                                 |
| `esxi_user`     | ✅ (for ESXi)     | Username for the ESXi/vCenter API.                                                                          |
| `esxi_password` | ✅ (for ESXi)     | Password for the API login.                                                                                 |
| `tags`          | ⛔️               | List of labels to aid with filtering, routing, or display.                                                  |
| `notes`         | ⛔️               | Freeform human-readable comment or description field.                                                       |

---

## ✅ Example

```yaml
ubuntu-qemu:
  name: ubuntu-qemu
  ip: 10.0.0.6
  platform: linux
  provider: qemu
  type: vm
  shell: bash
  username: root
  password: toor
  ssh_port: 22
  vmtools_path: /usr/bin/qemu-guest-agent
  tags:
    - linux
    - test
  notes: "QEMU lab box used for shell command validation."
```

This structure should be repeated under uniquely named top-level keys for each VM or host target.
