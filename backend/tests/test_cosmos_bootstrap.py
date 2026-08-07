import os

os.environ.setdefault("COSMOS_DB_CONNECTION_STRING", "not-used-in-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

from app.db import cosmos_client
from app.db.cosmos_schema import CONTAINER_DEFINITIONS
from scripts import bootstrap_cosmos


class FakeNotFound(Exception):
    pass


class FakeAlreadyExists(Exception):
    pass


class FakeContainer:
    def __init__(self, name, containers):
        self.name = name
        self.containers = containers

    def read(self):
        if self.name not in self.containers:
            raise FakeNotFound()
        return {"partitionKey": {"paths": [self.containers[self.name]]}}


class FakeDatabase:
    def __init__(self, definitions, exists=True):
        self.definitions = {definition.name: definition for definition in definitions}
        self.exists = exists
        self.containers = {}
        self.create_calls = []

    def read(self):
        if not self.exists:
            raise FakeNotFound()
        return {"id": "test-database"}

    def get_container_client(self, name):
        return FakeContainer(name, self.containers)

    def create_container(self, **kwargs):
        name = kwargs["id"]
        if name in self.containers:
            raise FakeAlreadyExists()
        self.create_calls.append(kwargs)
        self.containers[name] = self.definitions[name].partition_key


class FakeClient:
    def __init__(self, database):
        self.database = database
        self.create_database_calls = []

    def get_database_client(self, _database_id):
        return self.database

    def create_database(self, id):
        self.create_database_calls.append(id)
        if self.database.exists:
            raise FakeAlreadyExists()
        self.database.exists = True
        return self.database


def patch_cosmos_exceptions(monkeypatch):
    monkeypatch.setattr(bootstrap_cosmos.exceptions, "CosmosResourceNotFoundError", FakeNotFound)
    monkeypatch.setattr(bootstrap_cosmos.exceptions, "CosmosResourceExistsError", FakeAlreadyExists)


def test_schema_has_unique_containers_and_declares_the_new_identity_resources():
    names = [definition.name for definition in CONTAINER_DEFINITIONS]

    assert len(names) == len(set(names)) == 20
    assert "subscription_usage" not in names
    assert {definition.name: definition.partition_key for definition in CONTAINER_DEFINITIONS if definition.name in {
        "auth_sessions": "/session_partition_id",
        "auth_challenges": "/challenge_partition_id",
        "identity_lookups": "/lookup_partition_id",
        "subscriptions": "/farm_id",
        "farm_settings": "/farm_id",
        "bank_accounts": "/farm_id",
        "farm_invitations": "/farm_id",
    }} == {
        "auth_sessions": "/session_partition_id",
        "auth_challenges": "/challenge_partition_id",
        "identity_lookups": "/lookup_partition_id",
        "subscriptions": "/farm_id",
        "farm_settings": "/farm_id",
        "bank_accounts": "/farm_id",
        "farm_invitations": "/farm_id",
    }


def test_dry_run_reports_missing_resources_without_creating_them(monkeypatch):
    patch_cosmos_exceptions(monkeypatch)
    database = FakeDatabase(CONTAINER_DEFINITIONS, exists=False)
    client = FakeClient(database)
    output = []

    result = bootstrap_cosmos.bootstrap_cosmos(
        connection_string="AccountEndpoint=https://barebonde.documents.azure.com:443/;AccountKey=secret-value;",
        database_id="test-database",
        dry_run=True,
        client_factory=lambda _connection_string: client,
        write=output.append,
    )

    assert result == bootstrap_cosmos.EXIT_SUCCESS
    assert client.create_database_calls == []
    assert database.create_calls == []
    assert "secret-value" not in "\n".join(output)
    assert any("would create" in line for line in output)


def test_apply_creates_missing_containers_once_and_is_idempotent(monkeypatch):
    patch_cosmos_exceptions(monkeypatch)
    database = FakeDatabase(CONTAINER_DEFINITIONS)
    client = FakeClient(database)

    result = bootstrap_cosmos.bootstrap_cosmos(
        connection_string="AccountEndpoint=https://barebonde.documents.azure.com:443/;AccountKey=secret-value;",
        database_id="test-database",
        client_factory=lambda _connection_string: client,
        write=lambda _message: None,
    )

    assert result == bootstrap_cosmos.EXIT_SUCCESS
    assert [call["id"] for call in database.create_calls] == [
        definition.name for definition in CONTAINER_DEFINITIONS
    ]
    assert all("offer_throughput" not in call for call in database.create_calls)

    result = bootstrap_cosmos.bootstrap_cosmos(
        connection_string="AccountEndpoint=https://barebonde.documents.azure.com:443/;AccountKey=secret-value;",
        database_id="test-database",
        client_factory=lambda _connection_string: client,
        write=lambda _message: None,
    )

    assert result == bootstrap_cosmos.EXIT_SUCCESS
    assert len(database.create_calls) == len(CONTAINER_DEFINITIONS)


def test_apply_creates_a_missing_database_before_declared_containers(monkeypatch):
    patch_cosmos_exceptions(monkeypatch)
    database = FakeDatabase(CONTAINER_DEFINITIONS, exists=False)
    client = FakeClient(database)

    result = bootstrap_cosmos.bootstrap_cosmos(
        connection_string="AccountEndpoint=https://barebonde.documents.azure.com:443/;AccountKey=secret-value;",
        database_id="test-database",
        client_factory=lambda _connection_string: client,
        write=lambda _message: None,
    )

    assert result == bootstrap_cosmos.EXIT_SUCCESS
    assert client.create_database_calls == ["test-database"]
    assert len(database.create_calls) == len(CONTAINER_DEFINITIONS)


def test_partition_key_conflict_fails_without_mutation(monkeypatch):
    patch_cosmos_exceptions(monkeypatch)
    database = FakeDatabase(CONTAINER_DEFINITIONS)
    database.containers["users"] = "/wrong_partition_key"
    client = FakeClient(database)

    result = bootstrap_cosmos.bootstrap_cosmos(
        connection_string="AccountEndpoint=https://barebonde.documents.azure.com:443/;AccountKey=secret-value;",
        database_id="test-database",
        dry_run=True,
        client_factory=lambda _connection_string: client,
        write=lambda _message: None,
    )

    assert result == bootstrap_cosmos.EXIT_PARTITION_KEY_CONFLICT
    assert database.create_calls == []


def test_validate_only_fails_when_database_is_missing(monkeypatch):
    patch_cosmos_exceptions(monkeypatch)
    database = FakeDatabase(CONTAINER_DEFINITIONS, exists=False)
    client = FakeClient(database)

    result = bootstrap_cosmos.bootstrap_cosmos(
        connection_string="AccountEndpoint=https://barebonde.documents.azure.com:443/;AccountKey=secret-value;",
        database_id="test-database",
        validate_only=True,
        client_factory=lambda _connection_string: client,
        write=lambda _message: None,
    )

    assert result == bootstrap_cosmos.EXIT_MISSING_RESOURCE
    assert client.create_database_calls == []


def test_runtime_container_getter_never_creates_resources(monkeypatch):
    calls = []

    class Database:
        def get_container_client(self, name):
            calls.append(("get_container_client", name))
            return {"name": name}

    class Client:
        def get_database_client(self, database_id):
            calls.append(("get_database_client", database_id))
            return Database()

    class CosmosClientFactory:
        @staticmethod
        def from_connection_string(connection_string):
            calls.append(("from_connection_string", connection_string))
            return Client()

    monkeypatch.setattr(cosmos_client, "CosmosClient", CosmosClientFactory)
    monkeypatch.setattr(cosmos_client, "client", None)
    monkeypatch.setattr(cosmos_client, "database", None)

    assert cosmos_client.get_users_container() == {"name": "users"}
    assert [call[0] for call in calls] == ["from_connection_string", "get_database_client", "get_container_client"]
