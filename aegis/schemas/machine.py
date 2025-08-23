# aegis/schemas/machine.py
"""
Machine manifest schema with multi-NIC / multi-IP support.

Backward compatible:
- Legacy fields `ip` and `port` are accepted. If `interfaces` is empty,
  they are migrated into a single 'primary' interface at model init.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class NetworkInterface(BaseModel):
    """
    A logical network interface entry for a machine.
    """

    name: str = Field(..., description="Logical label, e.g. 'mgmt0', 'lan1', 'wan'")
    address: str = Field(..., description="IPv4/IPv6 or hostname")
    port: int = Field(22, description="Default port for remote access (SSH, etc.)")
    description: Optional[str] = Field(None, description="Human-friendly notes")
    is_primary: bool = Field(
        False, description="If true, this is the default/primary NIC"
    )
    meta: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Arbitrary executor/protocol-specific metadata (VLAN, subnet, etc.)",
    )


class MachineManifest(BaseModel):
    """
    Declarative description of a machine AEGIS can target.
    """

    # Identity
    id: str = Field(..., description="Unique machine identifier")
    hostname: Optional[str] = Field(
        None, description="Human-readable hostname or management name"
    )

    # Multi-NIC support
    interfaces: List[NetworkInterface] = Field(
        default_factory=list,
        description="One or more logical interfaces with their addresses",
    )

    # Optional platform context
    os: Optional[str] = Field(None, description="e.g., 'linux', 'windows', 'bsd'")
    roles: List[str] = Field(
        default_factory=list, description="Role tags for targeting"
    )
    tags: List[str] = Field(default_factory=list, description="Free-form tags")
    credentials: Optional[Dict[str, Any]] = Field(
        default=None, description="Named credential refs or inline auth material"
    )

    # --- Legacy compatibility (auto-migrated) ---
    ip: Optional[str] = Field(
        None,
        description="LEGACY: single IP/host (will be migrated to interfaces[].address)",
    )
    port: Optional[int] = Field(
        None,
        description="LEGACY: single port (will map to interfaces[].port, default 22)",
    )

    # allow forward-compat extra keys from existing manifests
    model_config = ConfigDict(extra="allow")

    def model_post_init(self, __context: Any) -> None:  # pydantic v2 hook
        # If no interfaces provided but legacy ip/port/hostname present, migrate to a single primary NIC
        if not self.interfaces:
            address = self.ip or self.hostname
            if address:
                self.interfaces.append(
                    NetworkInterface(
                        name="primary",
                        address=str(address),
                        port=int(self.port or 22),
                        is_primary=True,
                    )
                )
        # Ensure exactly one primary if multiple flagged
        primaries = [i for i in self.interfaces if i.is_primary]
        if len(primaries) > 1:
            # Keep the first flagged, clear the rest
            first = True
            for nic in self.interfaces:
                if nic.is_primary:
                    nic.is_primary = first
                    first = False

    # Convenience accessors (non-breaking)
    def primary_interface(self) -> NetworkInterface:
        for nic in self.interfaces:
            if nic.is_primary:
                return nic
        if self.interfaces:
            return self.interfaces[0]
        raise ValueError(f"Machine '{self.id}' has no interfaces configured")

    def get_interface(self, name: Optional[str]) -> NetworkInterface:
        if name:
            for nic in self.interfaces:
                if nic.name == name:
                    return nic
            raise KeyError(f"No interface named '{name}' on machine '{self.id}'")
        return self.primary_interface()
