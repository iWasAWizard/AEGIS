# aegis/utils/manifest_resolver.py
"""
Helper functions to resolve network interfaces from a MachineManifest.

Centralizes the policy for selecting NIC/IP so executors don't each reinvent it.
"""

from __future__ import annotations

from typing import Optional, Tuple, List

from aegis.schemas.machine import MachineManifest, NetworkInterface
from aegis.exceptions import ConfigurationError

__all__ = ["resolve_interface", "resolve_target_host_port"]


def _pick_default_interface(interfaces: List[NetworkInterface]) -> NetworkInterface:
    # Prefer an explicit primary
    for nic in interfaces:
        if getattr(nic, "is_primary", False):
            return nic
    # Then common management names
    preferred = {"mgmt0", "mgmt", "primary", "public", "default"}
    for nic in interfaces:
        if nic.name in preferred:
            return nic
    # Fallback: first
    return interfaces[0]


def resolve_interface(
    manifest: MachineManifest, interface_name: Optional[str] = None
) -> NetworkInterface:
    """
    Choose an interface by name or sensible defaults.

    - If `interface_name` is provided, find it exactly or raise with choices listed.
    - Else, prefer `is_primary=True`, then common names, else the first interface.
    """
    # Defensive: tolerate manifests with no interfaces (should be synthesized by model)
    if not manifest.interfaces:
        # Try legacy single-endpoint fields
        ip = getattr(manifest, "ip", None)
        port = getattr(manifest, "ssh_port", None) or 22
        if ip:
            return NetworkInterface(
                name="primary", address=ip, port=port, is_primary=True
            )
        ident = getattr(manifest, "id", None) or getattr(manifest, "name", "?")
        raise ConfigurationError(f"Machine '{ident}' has no interfaces configured")

    if interface_name:
        for nic in manifest.interfaces:
            if nic.name == interface_name:
                return nic
        names = ", ".join(sorted(n.name for n in manifest.interfaces))
        ident = getattr(manifest, "name", None) or getattr(manifest, "id", "?")
        raise ConfigurationError(
            f"No interface named '{interface_name}' on machine '{ident}'. "
            f"Available: {names}"
        )

    return _pick_default_interface(manifest.interfaces)


def resolve_target_host_port(
    manifest: MachineManifest, interface_name: Optional[str] = None
) -> Tuple[str, int, str]:
    """
    Returns (address, port, nic_name) for convenience.
    """
    nic = resolve_interface(manifest, interface_name)

    # Sanity-check address and normalize port fallback
    address = (nic.address or "").strip()
    if not address:
        ident = getattr(manifest, "id", None) or getattr(manifest, "name", "?")
        raise ConfigurationError(
            f"Selected interface '{nic.name}' on machine '{ident}' has no address."
        )

    port = int(nic.port or getattr(manifest, "ssh_port", None) or 22)
    return address, port, nic.name
