from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import config
from routes.auth import auth_router
from routes.canvas import canvas_router
from routes.static import static_router
from wsmanager import manager

app = FastAPI(title="Cloud Pixel Canvas API")

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
    await manager.connect(websocket)
    try:
        while True:
            # keep the connection alive; clients don't need to send data
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

api_router.include_router(auth_router)
api_router.include_router(canvas_router)

app.include_router(api_router)
app.include_router(static_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
