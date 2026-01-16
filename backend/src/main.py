import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
import aioboto3
from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from adapters.db import DynamoDBAdapter, MongoDBAdapter
from adapters.auth import CognitoAuthAdapter, KeycloakAuthAdapter, LocalMongoAuthAdapter
from adapters.storage import LocalFileStorageAdapter, S3StorageAdapter
from adapters.pubsub import ValkeyPubSubAdapter
from config import config
from routes.auth import auth_router
from routes.canvas import canvas_router
from routes.static import static_router
from wsmanager import manager as ws_manager
from deps import manager as dep_manager

instrumentator = Instrumentator()

logger = logging.getLogger("uvicorn")

async def wait_for_dependency(func, name, retries=10, delay=3):
    for i in range(retries):
        try:
            await func()
            logger.info(f"Connected to {name}")
            return
        except Exception as e:
            logger.warning(f"Waiting for {name} (attempt {i+1}/{retries})... Error: {e}")
            await asyncio.sleep(delay)
    raise RuntimeError(f"Could not connect to {name} after {retries} attempts")

@asynccontextmanager
async def lifespan(app: FastAPI):
    session = aioboto3.Session()

    pubsub_adapter = ValkeyPubSubAdapter(
        host=config.valkey_host, 
        port=config.valkey_port,
        ssl=config.valkey_ssl,
    )
    ws_manager.init_pubsub(pubsub_adapter)

    await wait_for_dependency(ws_manager.start_listening, "Valkey Pubsub")

    match config.environment:
        case "aws":
            async with session.resource("dynamodb", region_name=config.aws_region) as dynamodb, \
                session.client("cognito-idp", region_name=config.aws_region) as cognito, \
                session.client("s3", region_name=config.aws_region) as s3:
                dep_manager.db = DynamoDBAdapter(dynamodb)
                dep_manager.auth = CognitoAuthAdapter(cognito)
                dep_manager.storage = S3StorageAdapter(s3)

                yield

        case "portable":
            dep_manager.db = MongoDBAdapter()
            dep_manager.auth = KeycloakAuthAdapter()

            async with session.client(
                "s3", 
                region_name=config.aws_region, 
                endpoint_url=config.s3_endpoint_url,
                aws_access_key_id=config.minio_access_key,
                aws_secret_access_key=config.minio_secret_key
            ) as s3: # type: ignore
                storage = S3StorageAdapter(s3, bucket_name=config.s3_bucket_name, public_domain=config.s3_public_domain)
                await wait_for_dependency(lambda: storage.ensure_bucket_exists(make_public=True), "MinIO Storage")
                dep_manager.storage = storage

                yield

        case "local":
            dep_manager.db = MongoDBAdapter()
            dep_manager.auth = LocalMongoAuthAdapter(config.mongo_uri, config.mongo_db)
            dep_manager.storage = LocalFileStorageAdapter(config.local_storage_path)

            yield

        case _:
            raise ValueError(f"Unknown environment: {config.environment}")        

    await ws_manager.shutdown()

app = FastAPI(title="Cloud Pixel Canvas API", lifespan=lifespan)

instrumentator.instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")

@api_router.get("/")
async def root():
    return "Pixel Canvas API"

@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # keep the connection alive; clients don't need to send data
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

api_router.include_router(auth_router)
api_router.include_router(canvas_router)

app.include_router(api_router)
app.include_router(static_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
