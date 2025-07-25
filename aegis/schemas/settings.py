# aegis/schemas/settings.py
"""
Centralized settings management using pydantic-settings.

This module defines a Settings model that automatically loads configuration
values from environment variables or a .env file. This is the single source
of truth for all secrets and environment-specific configurations.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Loads all environment variables into a structured Pydantic model.

    The variable names defined here are automatically sought in the environment
    or in a `.env` file at the project root. Field names are case-insensitive.
    This model is used by utilities like `machine_loader` to resolve secrets
    in configuration files.

    :ivar ADMIN_PASSWORD: Password for the 'Administrator' user on Windows VMs.
    :vartype ADMIN_PASSWORD: str
    :ivar ROOT_PASSWORD: Password for the 'root' user on Linux VMs.
    :vartype ROOT_PASSWORD: str
    :ivar DEPLOY_PASSWORD: Password for the 'deploy' user on physical hosts.
    :vartype DEPLOY_PASSWORD: str
    :ivar ESXI_PASSWORD: Password for the ESXi/vCenter API.
    :vartype ESXI_PASSWORD: str
    """

    ADMIN_PASSWORD: str = "supersecret"
    ROOT_PASSWORD: str = "toor"
    DEPLOY_PASSWORD: str = "changeme"
    ESXI_PASSWORD: str = "vmware123"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


# Create a single, cached instance of the settings to be used by the app.
settings = Settings()
