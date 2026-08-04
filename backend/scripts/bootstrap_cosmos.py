"""Safely bootstrap and validate the declared Cosmos DB containers.

Run from the repository root after supplying the normal backend Cosmos
environment variables:

    python backend/scripts/bootstrap_cosmos.py --dry-run

The script never deletes, replaces, migrates, or writes application data.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, Sequence
from urllib.parse import urlparse

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from azure.cosmos import CosmosClient, PartitionKey, exceptions

from app.db.cosmos_schema import CONTAINER_DEFINITIONS, ContainerDefinition

EXIT_SUCCESS = 0
EXIT_OPERATION_FAILED = 1
EXIT_PARTITION_KEY_CONFLICT = 2
EXIT_MISSING_RESOURCE = 3

Writer = Callable[[str], None]
ClientFactory = Callable[[str], Any]


def mask_cosmos_endpoint(connection_string: str) -> str:
    """Return a non-sensitive display form of the configured account endpoint."""
    endpoint = next(
        (
            part.split("=", 1)[1].strip()
            for part in connection_string.split(";")
            if part.lower().startswith("accountendpoint=") and "=" in part
        ),
        "",
    )
    hostname = urlparse(endpoint).hostname
    if not hostname:
        return "<endpoint unavailable>"

    visible_prefix = hostname[:3]
    visible_suffix = hostname[-10:] if len(hostname) > 13 else ""
    return f"https://{visible_prefix}…{visible_suffix}"


def _partition_key_paths(properties: dict[str, Any]) -> tuple[str, ...]:
    partition_key = properties.get("partitionKey") or {}
    paths = partition_key.get("paths") or []
    return tuple(str(path) for path in paths)


def _validate_container(
    database: Any,
    definition: ContainerDefinition,
    write: Writer,
) -> int:
    container = database.get_container_client(definition.name)
    try:
        properties = container.read()
    except exceptions.CosmosResourceNotFoundError:
        return EXIT_MISSING_RESOURCE

    actual_paths = _partition_key_paths(properties)
    expected_paths = (definition.partition_key,)
    if actual_paths != expected_paths:
        write(
            f"CONFLICT container={definition.name} "
            f"expected_partition_key={definition.partition_key} "
            f"actual_partition_key={','.join(actual_paths) or '<missing>'}"
        )
        return EXIT_PARTITION_KEY_CONFLICT

    write(f"VALID container={definition.name} partition_key={definition.partition_key}")
    return EXIT_SUCCESS


def bootstrap_cosmos(
    *,
    connection_string: str,
    database_id: str,
    dry_run: bool = False,
    validate_only: bool = False,
    client_factory: ClientFactory = CosmosClient.from_connection_string,
    write: Writer = print,
) -> int:
    """Validate or create declared resources without mutating existing ones."""
    if dry_run and validate_only:
        raise ValueError("dry_run and validate_only cannot be combined")

    mode = "dry-run" if dry_run else "validate-only" if validate_only else "apply"
    write(f"Cosmos endpoint: {mask_cosmos_endpoint(connection_string)}")
    write(f"Database ID: {database_id}")
    write(f"Mode: {mode}")
    write("Containers: " + ", ".join(definition.name for definition in CONTAINER_DEFINITIONS))

    try:
        client = client_factory(connection_string)
        database = client.get_database_client(database_id)
        try:
            database.read()
            database_exists = True
        except exceptions.CosmosResourceNotFoundError:
            database_exists = False

        if not database_exists:
            if dry_run:
                write(f"MISSING database={database_id}; would create it in apply mode.")
                for definition in CONTAINER_DEFINITIONS:
                    write(
                        f"MISSING container={definition.name}; "
                        f"would create with partition_key={definition.partition_key} in apply mode."
                    )
                write("Cosmos dry-run completed without resource changes.")
                return EXIT_SUCCESS
            if validate_only:
                write(f"MISSING database={database_id}")
                return EXIT_MISSING_RESOURCE

            try:
                database = client.create_database(id=database_id)
                write(f"CREATED database={database_id}")
            except exceptions.CosmosResourceExistsError:
                database = client.get_database_client(database_id)
                database.read()
                write(f"VALID database={database_id} (created concurrently)")
        else:
            write(f"VALID database={database_id}")

        missing_definitions: list[ContainerDefinition] = []
        has_partition_key_conflict = False
        for definition in CONTAINER_DEFINITIONS:
            result = _validate_container(database, definition, write)
            if result == EXIT_PARTITION_KEY_CONFLICT:
                has_partition_key_conflict = True
                continue
            if result == EXIT_SUCCESS:
                continue

            missing_definitions.append(definition)

        if has_partition_key_conflict:
            write("ERROR: No missing containers were created because partition-key validation failed.")
            return EXIT_PARTITION_KEY_CONFLICT

        if dry_run:
            for definition in missing_definitions:
                write(
                    f"MISSING container={definition.name}; "
                    f"would create with partition_key={definition.partition_key} in apply mode."
                )
            write("Cosmos dry-run completed without resource changes.")
            return EXIT_SUCCESS

        if validate_only:
            for definition in missing_definitions:
                write(f"MISSING container={definition.name}")
            return EXIT_MISSING_RESOURCE if missing_definitions else EXIT_SUCCESS

        for definition in missing_definitions:
            try:
                create_kwargs: dict[str, Any] = {
                    "id": definition.name,
                    "partition_key": PartitionKey(path=definition.partition_key),
                }
                if definition.default_ttl is not None:
                    create_kwargs["default_ttl"] = definition.default_ttl
                database.create_container(**create_kwargs)
                write(
                    f"CREATED container={definition.name} "
                    f"partition_key={definition.partition_key}"
                )
            except exceptions.CosmosResourceExistsError:
                result = _validate_container(database, definition, write)
                if result != EXIT_SUCCESS:
                    return result

        write("Cosmos bootstrap completed without destructive changes.")
        return EXIT_SUCCESS
    except exceptions.CosmosHttpResponseError:
        write("ERROR: Cosmos operation failed. No resource changes were attempted after the failure.")
        return EXIT_OPERATION_FAILED
    except Exception:
        write("ERROR: Unable to inspect Cosmos resources. Check local configuration and connectivity.")
        return EXIT_OPERATION_FAILED


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate or safely bootstrap Barebonde Cosmos containers.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Read and report without creating resources.")
    mode.add_argument("--validate-only", action="store_true", help="Fail if any declared resource is missing.")
    parser.add_argument("--database-id", help="Override COSMOS_DB_DATABASE_ID for this invocation.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        from app.core.config import settings
    except Exception:
        print("ERROR: Cosmos configuration is unavailable. Set the required local environment variables.")
        return EXIT_OPERATION_FAILED

    database_id = (args.database_id or settings.cosmos_db_database_id).strip()
    if not database_id:
        print("ERROR: A Cosmos database ID is required.")
        return EXIT_OPERATION_FAILED

    return bootstrap_cosmos(
        connection_string=settings.cosmos_db_connection_string,
        database_id=database_id,
        dry_run=args.dry_run,
        validate_only=args.validate_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())
