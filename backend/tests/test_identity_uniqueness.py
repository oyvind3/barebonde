import os

from azure.cosmos import exceptions

os.environ.setdefault("COSMOS_DB_CONNECTION_STRING", "not-used-in-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("IDENTITY_HMAC_KEY", "test-identity-hmac-key")

from app.services.identity_service import IdentityError, IdentityService, normalize_email


class Memory:
    def __init__(self): self.items = {}; self.fail_user_create = False
    def read_item(self, *, item, partition_key):
        value=self.items.get(item)
        if not value or partition_key not in {value.get("lookup_partition_id"),value.get("better_auth_id")}: raise exceptions.CosmosResourceNotFoundError(message="missing",response=None)
        return dict(value)
    def create_item(self,item):
        if self.fail_user_create: raise RuntimeError("unavailable")
        if item["id"] in self.items: raise exceptions.CosmosResourceExistsError(message="exists",response=None)
        self.items[item["id"]]=dict(item);return item
    def upsert_item(self,item): self.items[item["id"]]=dict(item);return item
    def query_items(self, **_): return []

def test_email_normalization_is_casefolded_and_whitespace_safe():
    users,lookups=Memory(),Memory(); service=IdentityService(users_container=users,lookups_container=lookups)
    first=service.resolve_email_identity(email=" Ola@Example.no ",first_name="Ola")
    second=service.resolve_email_identity(email="OLA@example.no",first_name="Other")
    assert normalize_email(" Ola@Example.no ")=="ola@example.no"
    assert first["user_id"]==second["user_id"] and len(users.items)==1 and len(lookups.items)==1

def test_failed_user_creation_after_lookup_claim_never_creates_a_user():
    users,lookups=Memory(),Memory(); users.fail_user_create=True
    service=IdentityService(users_container=users,lookups_container=lookups)
    try: service.resolve_email_identity(email="ola@example.no")
    except IdentityError: pass
    else: raise AssertionError("expected controlled identity failure")
    assert users.items=={} and len(lookups.items)==1
