# aegis/schemas/machine.py
"""
Machine manifest schema with multi-NIC / multi-IP support.

Backward compatible:
- Legacy fields `ip` and `port` are accepted. If `interfaces` is empty,
  they are migrated into a single 'primary' interface at model init.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from pydantic.config import ConfigDict


class NetworkInterface(BaseModel):
    """Represents a named network interface/address tuple."""

    name: str = Field(default="primary", description="Logical name for the interface")
    address: str = Field(..., description="Hostname or IP address")
    port: Optional[int] = Field(default=None, description="Optional port override")
    is_primary: bool = Field(default=False, description="Mark as the default interface")
    meta: Dict[str, Any] | None = Field(default=None, description="Arbitrary metadata")

    model_config = ConfigDict(extra="allow")


class MachineManifest(BaseModel):
    """
    Machine definition that supports multiple logical interfaces.

    Backward compatibility:
    - Legacy `ip` and `ssh_port` fields are accepted. If `interfaces` is empty,
      a single 'primary' interface is synthesized from them.
    """

    id: Optional[str] = Field(default=None, description="Optional stable machine id")
    name: str = Field(..., description="Human-friendly name/alias")
    platform: Optional[str] = None
    provider: Optional[str] = None
    type: Optional[str] = None
    shell: Optional[str] = Field(default="bash")
    username: Optional[str] = None
    password: Optional[str] = None

    # Legacy single-endpoint fields (optional)
    ip: Optional[str] = Field(default=None)
    ssh_port: Optional[int] = Field(default=None)

    # New multi-interface field
    interfaces: List[NetworkInterface] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy(cls, data: Any) -> Any:
        """Convert legacy ip/ssh_port to interfaces if none were provided."""
        if not isinstance(data, dict):
            return data
        interfaces = data.get("interfaces")
        ip = data.get("ip") or data.get("address")
        ssh_port = data.get("ssh_port") or data.get("port")
        # If interfaces already present and non-empty, leave as-is
        if interfaces:
            return data
        if ip:
            data["interfaces"] = [
                {
                    "name": "primary",
                    "address": ip,
                    "port": ssh_port or 22,
                    "is_primary": True,
                }
            ]
        return data

    @model_validator(mode="after")
    def _ensure_primary(self) -> "MachineManifest":
        """Guarantee exactly one primary interface if any exist."""
        if self.interfaces:
            prims = [i for i in self.interfaces if i.is_primary]
            if not prims:
                # mark the first as primary
                self.interfaces[0].is_primary = True
            elif len(prims) > 1:
                # keep the first as primary, clear the rest
                seen = False
                for i in self.interfaces:
                    if i.is_primary and not seen:
                        seen = True
                    else:
                        i.is_primary = False
        return self

    # Convenience accessors (non-breaking)
    def primary_interface(self) -> NetworkInterface:
        for nic in self.interfaces:
            if nic.is_primary:
                return nic
        if self.interfaces:
            return self.interfaces[0]
        raise ValueError(
            f"Machine '{self.id or self.name}' has no interfaces configured"
        )

    def get_interface(self, name: Optional[str]) -> NetworkInterface:
        if name:
            for nic in self.interfaces:
                if nic.name == name:
                    return nic
            raise KeyError(
                f"No interface named '{name}' on machine '{self.id or self.name}'"
            )
        return self.primary_interface()
