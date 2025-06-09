"""
Schema defining the expected format for machine manifest entries.

Each machine entry describes a physical or virtual system available for agent deployment.
This module also includes a collection wrapper for batch loading multiple machines.
"""

from typing import List, Optional

from pydantic import BaseModel


class MachineManifest(BaseModel):
    """
    Represents a single machine definition from the manifest.

    :param name: Unique agent-facing nickname.
    :param ip: IP address or hostname of the target system.
    :param platform: Operating system (linux, windows, mac).
    :param provider: Environment type (qemu, esxi, vmware, proxmox, physical).
    :param type: Logical machine type (vm, physical, container).
    :param shell: Shell interpreter used on the system (bash, sh, zsh, powershell).
    :param username: Username for login.
    :param password: Password for login (can be replaced with SSH key).
    :param ssh_port: Optional SSH port if using remote shell access.
    :param vmtools_path: Optional path to hypervisor guest agent tool.
    :param esxi_host: Required if using ESXi provider — the vCenter/ESXi hostname.
    :param esxi_user: Required if using ESXi provider — API username.
    :param esxi_password: Required if using ESXi provider — API password.
    :param tags: Optional list of labels or tags.
    :param notes: Optional freeform notes or description.
    """

    name: str
    ip: str
    platform: str
    provider: str
    type: str
    shell: str
    username: str
    password: str

    ssh_port: Optional[int] = None
    vmtools_path: Optional[str] = None

    esxi_host: Optional[str] = None
    esxi_user: Optional[str] = None
    esxi_password: Optional[str] = None

    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class MachineManifestCollection(BaseModel):
    """
    Wrapper for loading a list of machines from a YAML or JSON manifest.

    :param machines: List of machine entries parsed from the manifest.
    """

    machines: List[MachineManifest]
