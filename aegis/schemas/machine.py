# aegis/schemas/machine.py
"""
Schema defining the expected format for machine manifest entries.

Each machine entry describes a physical or virtual system available for agent
deployment. This module also includes a collection wrapper for batch loading
multiple machines.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class MachineManifest(BaseModel):
    """
    Represents a single machine definition from the manifest.

    This Pydantic model validates each entry in the `machines.yaml` file.
    Secrets like passwords are now optional and can be resolved from environment
    variables by the `machine_loader` utility.

    :ivar name: Agent-facing nickname (must be unique).
    :vartype name: str
    :ivar ip: Resolvable IP address or hostname for the guest OS.
    :vartype ip: str
    :ivar platform: Operating system of the guest (`linux`, `windows`, `mac`).
    :vartype platform: str
    :ivar provider: Source environment (`qemu`, `esxi`, `vmware`, `proxmox`, `physical`).
    :vartype provider: str
    :ivar type: Logical host type for routing: `vm`, `physical`, or `container`.
    :vartype type: str
    :ivar shell: Shell interpreter to be used for commands: `bash`, `sh`, `zsh`, `powershell`.
    :vartype shell: str
    :ivar username: Username for guest login.
    :vartype username: str
    :ivar password: Optional password for login. Can be an env var placeholder.
    :vartype password: Optional[str]
    :ivar esxi_password: Optional password for ESXi/vCenter API.
    :vartype esxi_password: Optional[str]
    :ivar ssh_port: SSH port number.
    :vartype ssh_port: Optional[int]
    :ivar known_hosts_file: Path to a custom known_hosts file for this machine.
    :vartype known_hosts_file: Optional[str]
    :ivar vmtools_path: Path to guest agent (e.g., `qemu-guest-agent`, `vmtoolsd.exe`).
    :vartype vmtools_path: Optional[str]
    :ivar esxi_host: IP or hostname of the ESXi or vCenter host.
    :vartype esxi_host: Optional[str]
    :ivar esxi_user: Username for the ESXi/vCenter API.
    :vartype esxi_user: Optional[str]
    :ivar tags: List of labels for filtering or routing.
    :vartype tags: List[str]
    :ivar notes: Freeform human-readable comment or description field.
    :vartype notes: Optional[str]
    """

    name: str
    ip: str
    platform: str
    provider: str
    type: str
    shell: str
    username: str

    password: Optional[str] = None
    esxi_password: Optional[str] = None

    ssh_port: Optional[int] = 22
    known_hosts_file: Optional[str] = Field(
        default=None, description="Path to a custom known_hosts file for this machine."
    )
    vmtools_path: Optional[str] = None

    esxi_host: Optional[str] = None
    esxi_user: Optional[str] = None

    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
