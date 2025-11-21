from typing import Optional
from adapters.db import DBAdapter
from adapters.auth import AuthAdapter
from adapters.storage import StorageAdapter

class DependencyManager:
    db: Optional[DBAdapter] = None
    auth: Optional[AuthAdapter] = None
    storage: Optional[StorageAdapter] = None

manager = DependencyManager()
