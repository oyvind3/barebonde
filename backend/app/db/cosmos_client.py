"""Lazy Cosmos DB client access for request handlers.

Resource creation and partition-key validation live exclusively in
``scripts/bootstrap_cosmos.py``. This module only builds client proxies; doing
so never creates a database or container.
"""

from __future__ import annotations

import logging
from typing import Any

from azure.cosmos import CosmosClient

from app.core.config import settings
from app.db.cosmos_schema import get_container_definition

logger = logging.getLogger(__name__)

client: CosmosClient | None = None
database: Any | None = None


def get_cosmos_database() -> Any:
    """Return the configured database proxy without reading or creating it."""
    global client, database

    if database is None:
        client = CosmosClient.from_connection_string(settings.cosmos_db_connection_string)
        database = client.get_database_client(settings.cosmos_db_database_id)
        logger.debug("Cosmos database proxy configured for request handling.")

    return database


def get_container_client(name: str) -> Any:
    """Return a known container proxy without creating or validating resources."""
    definition = get_container_definition(name)
    return get_cosmos_database().get_container_client(definition.name)


def get_users_container() -> Any:
    return get_container_client("users")


def get_farms_container() -> Any:
    return get_container_client("farms")


def get_farm_users_container() -> Any:
    return get_container_client("farm_users")


def get_properties_container() -> Any:
    return get_container_client("properties")


def get_transactions_container() -> Any:
    return get_container_client("transactions")


def get_documents_container() -> Any:
    return get_container_client("documents")


def get_contracts_container() -> Any:
    return get_container_client("contracts")


def get_deadlines_container() -> Any:
    return get_container_client("deadlines")


def get_audit_logs_container() -> Any:
    return get_container_client("audit_logs")


def get_auth_sessions_container() -> Any:
    return get_container_client("auth_sessions")


def get_auth_challenges_container() -> Any:
    return get_container_client("auth_challenges")


def get_identity_lookups_container() -> Any:
    return get_container_client("identity_lookups")


def get_subscriptions_container() -> Any:
    """Return the existing Farm-partitioned subscription container proxy."""
    return get_container_client("subscriptions")


def get_farm_settings_container() -> Any:
    return get_container_client("farm_settings")


def get_bank_accounts_container() -> Any:
    return get_container_client("bank_accounts")
