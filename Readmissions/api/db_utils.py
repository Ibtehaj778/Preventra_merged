import os

import certifi
from pymongo import MongoClient, DESCENDING


def get_db_name() -> str:
    """The product database. Lives here rather than as a literal in each entry
    point: the API and the loader scripts must agree, and a name set for one but
    not the others means the dashboard reads an empty database and says nothing
    about why."""
    return os.environ.get("MONGO_DB", "neuroshield")


def get_mongo_client(uri: str) -> MongoClient:
    """
    TLS is only enabled for non-local hosts (e.g. MongoDB Atlas). A local/dev
    Mongo instance (localhost, 127.0.0.1) doesn't speak TLS, so forcing
    tlsCAFile there breaks the connection with an SSL handshake failure.
    """
    if "localhost" in uri or "127.0.0.1" in uri:
        return MongoClient(uri)

    # Atlas here intermittently fails the TLS handshake on a single replica-set
    # node, which pymongo surfaces as AutoReconnect rather than routing around
    # it. The explicit options below give server selection room to find a
    # healthy node and let a failed read or write be retried once by the driver
    # instead of reaching the caller as a 500.
    return MongoClient(
        uri,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=20000,
        socketTimeoutMS=45000,
        retryReads=True,
        retryWrites=True,
    )


def get_latest_batch_date(db, collection_name: str):
    """Returns the most recent batch_date string in the given collection, or None."""
    doc = db[collection_name].find_one(sort=[("batch_date", DESCENDING)])
    if not doc:
        return None
    return doc["batch_date"]
