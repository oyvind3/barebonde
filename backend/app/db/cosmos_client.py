"""
Cosmos DB client and utilities
Handles all document database operations for Barebonde
"""

from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.cosmos.aio import CosmosClient as AsyncCosmosClient
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create the client during application startup, not function indexing.
client = None

# Database and container instances
database = None
users_container = None
farms_container = None
farm_users_container = None
properties_container = None
transactions_container = None
documents_container = None
contracts_container = None
deadlines_container = None
audit_logs_container = None


async def init_cosmos_db():
    """
    Initialize Cosmos DB database and containers
    Creates database and containers if they don't exist
    """
    global client, database, users_container, farms_container, farm_users_container
    global properties_container, transactions_container, documents_container
    global contracts_container, deadlines_container, audit_logs_container
    
    try:
        client = CosmosClient.from_connection_string(settings.cosmos_db_connection_string)
        # Get or create database
        database = client.get_database_client(settings.cosmos_db_database_id)
        logger.info(f"✅ Connected to Cosmos DB database: {settings.cosmos_db_database_id}")
        
        # Create containers with partition keys
        # Users container: partitioned by better_auth_id
        try:
            users_container = database.get_container_client("users")
            logger.info("✅ Users container ready")
        except exceptions.CosmosResourceNotFoundError:
            users_container = database.create_container(
                id="users",
                partition_key=PartitionKey(path="/better_auth_id"),
                offer_throughput=400  # Minimum for Cosmos DB
            )
            logger.info("✅ Created users container")
        
        # Farms container: partitioned by org_number
        try:
            farms_container = database.get_container_client("farms")
            logger.info("✅ Farms container ready")
        except exceptions.CosmosResourceNotFoundError:
            farms_container = database.create_container(
                id="farms",
                partition_key=PartitionKey(path="/org_number"),
                offer_throughput=400
            )
            logger.info("✅ Created farms container")
        
        # FarmUsers container: partitioned by farm_id
        try:
            farm_users_container = database.get_container_client("farm_users")
            logger.info("✅ FarmUsers container ready")
        except exceptions.CosmosResourceNotFoundError:
            farm_users_container = database.create_container(
                id="farm_users",
                partition_key=PartitionKey(path="/farm_id"),
                offer_throughput=400
            )
            logger.info("✅ Created farm_users container")
        
        # Properties container: partitioned by farm_id
        try:
            properties_container = database.get_container_client("properties")
            logger.info("✅ Properties container ready")
        except exceptions.CosmosResourceNotFoundError:
            properties_container = database.create_container(
                id="properties",
                partition_key=PartitionKey(path="/farm_id"),
                offer_throughput=400
            )
            logger.info("✅ Created properties container")
        
        # Transactions container: partitioned by farm_id
        try:
            transactions_container = database.get_container_client("transactions")
            logger.info("✅ Transactions container ready")
        except exceptions.CosmosResourceNotFoundError:
            transactions_container = database.create_container(
                id="transactions",
                partition_key=PartitionKey(path="/farm_id"),
                offer_throughput=400
            )
            logger.info("✅ Created transactions container")
        
        # Documents container: partitioned by farm_id
        try:
            documents_container = database.get_container_client("documents")
            logger.info("✅ Documents container ready")
        except exceptions.CosmosResourceNotFoundError:
            documents_container = database.create_container(
                id="documents",
                partition_key=PartitionKey(path="/farm_id"),
                offer_throughput=400
            )
            logger.info("✅ Created documents container")
        
        # Contracts container: partitioned by farm_id
        try:
            contracts_container = database.get_container_client("contracts")
            logger.info("✅ Contracts container ready")
        except exceptions.CosmosResourceNotFoundError:
            contracts_container = database.create_container(
                id="contracts",
                partition_key=PartitionKey(path="/farm_id"),
                offer_throughput=400
            )
            logger.info("✅ Created contracts container")
        
        # Deadlines container: partitioned by farm_id
        try:
            deadlines_container = database.get_container_client("deadlines")
            logger.info("✅ Deadlines container ready")
        except exceptions.CosmosResourceNotFoundError:
            deadlines_container = database.create_container(
                id="deadlines",
                partition_key=PartitionKey(path="/farm_id"),
                offer_throughput=400
            )
            logger.info("✅ Created deadlines container")
        
        # Audit logs container: partitioned by farm_id
        try:
            audit_logs_container = database.get_container_client("audit_logs")
            logger.info("✅ Audit logs container ready")
        except exceptions.CosmosResourceNotFoundError:
            audit_logs_container = database.create_container(
                id="audit_logs",
                partition_key=PartitionKey(path="/farm_id"),
                offer_throughput=400
            )
            logger.info("✅ Created audit_logs container")
        
        logger.info("✅ Cosmos DB initialization complete")
        
    except exceptions.CosmosResourceExistsError:
        logger.info("✅ Database and containers already exist")
    except Exception as e:
        logger.error(f"❌ Error initializing Cosmos DB: {e}")
        raise


def get_users_container():
    """Get users container"""
    return users_container


def get_farms_container():
    """Get farms container"""
    return farms_container


def get_farm_users_container():
    """Get farm_users container"""
    return farm_users_container


def get_properties_container():
    """Get properties container"""
    return properties_container


def get_transactions_container():
    """Get transactions container"""
    return transactions_container


def get_documents_container():
    """Get documents container"""
    return documents_container


def get_contracts_container():
    """Get contracts container"""
    return contracts_container


def get_deadlines_container():
    """Get deadlines container"""
    return deadlines_container


def get_audit_logs_container():
    """Get audit_logs container"""
    return audit_logs_container
