from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import config

app = FastAPI(title="Cloud Pixel Canvas API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return "Pixel Canvas API"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
