"""Authoritative Azure Cosmos DB container definitions for Barebonde."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContainerDefinition:
    """The immutable shape required for one Cosmos container."""

    name: str
    partition_key: str
    default_ttl: int | None = None


CONTAINER_DEFINITIONS: tuple[ContainerDefinition, ...] = (
    ContainerDefinition("users", "/better_auth_id"),
    ContainerDefinition("farms", "/org_number"),
    ContainerDefinition("farm_users", "/farm_id"),
    ContainerDefinition("properties", "/farm_id"),
    ContainerDefinition("transactions", "/farm_id"),
    ContainerDefinition("documents", "/farm_id"),
    ContainerDefinition("contracts", "/farm_id"),
    ContainerDefinition("deadlines", "/farm_id"),
    ContainerDefinition("audit_logs", "/farm_id"),
    ContainerDefinition("auth_sessions", "/session_partition_id"),
    ContainerDefinition("auth_challenges", "/challenge_partition_id"),
    ContainerDefinition("identity_lookups", "/lookup_partition_id"),
    ContainerDefinition("subscriptions", "/farm_id"),
    ContainerDefinition("farm_settings", "/farm_id"),
    ContainerDefinition("bank_accounts", "/farm_id"),
    ContainerDefinition("farm_invitations", "/farm_id", default_ttl=2592000),
    ContainerDefinition("customers", "/farm_id"),
    ContainerDefinition("sales_invoices", "/farm_id"),
    ContainerDefinition("journal_entries", "/farm_id"),
    ContainerDefinition("accounting_periods", "/farm_id"),
)

CONTAINERS_BY_NAME = {definition.name: definition for definition in CONTAINER_DEFINITIONS}


def get_container_definition(name: str) -> ContainerDefinition:
    """Return a known container definition without accepting ad-hoc names."""
    try:
        return CONTAINERS_BY_NAME[name]
    except KeyError as exc:
        raise ValueError(f"Unknown Cosmos container: {name}") from exc
