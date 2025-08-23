# aegis/utils/manifest_resolver.py
"""
Helper functions to resolve network interfaces from a MachineManifest.

Centralizes the policy for selecting NIC/IP so executors don't each reinvent it.
"""

from __future__ import annotations

from typing import Optional

from aegis.schemas.machine import MachineManifest, NetworkInterface
from aegis.exceptions import ConfigurationError


def resolve_interface(
    manifest: MachineManifest, interface_name: Optional[str] = None
) -> NetworkInterface:
    """
    Pick a NetworkInterface by name; fall back to primary; else first; else error.
    """
    if interface_name:
        for nic in manifest.interfaces:
            if nic.name == interface_name:
                return nic
        raise ConfigurationError(
            f"No interface named '{interface_name}' on machine '{manifest.id}'"
        )

    # Primary if available
    for nic in manifest.interfaces:
        if nic.is_primary:
            return nic

    # First defined if any
    if manifest.interfaces:
        return manifest.interfaces[0]

    raise ConfigurationError(f"Machine '{manifest.id}' has no interfaces configured")


def resolve_target_host_port(
    manifest: MachineManifest, interface_name: Optional[str] = None
) -> tuple[str, int, str]:
    """
    Returns (address, port, nic_name) for convenience.
    """
    nic = resolve_interface(manifest, interface_name)
    return nic.address, int(nic.port or 22), nic.name
