import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TikTokRequest(BaseModel):
    url: HttpUrl

class TikTokResponse(BaseModel):
    title: str
    thumbnail: str
    download_url: str

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.post("/api/tiktok", response_model=TikTokResponse)
def download_tiktok(req: TikTokRequest):
    """Fetch TikTok video info and no-watermark download link using tikwm API."""
    try:
        # TikWM public API
        api_url = "https://www.tikwm.com/api/"
        resp = requests.post(api_url, data={"url": str(req.url)}, timeout=20)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Upstream service error")
        data = resp.json()
        if not data or data.get("code") != 0 or not data.get("data"):
            raise HTTPException(status_code=400, detail="Unable to fetch video. Check the URL.")
        d = data["data"]
        title = d.get("title") or "TikTok Video"
        # According to tikwm, 'play' is no-watermark link; prepend host if needed
        play = d.get("play") or d.get("play_addr")
        if play and play.startswith("/" ):
            play = "https://www.tikwm.com" + play
        cover = d.get("cover") or d.get("origin_cover") or d.get("dynamic_cover")
        if cover and cover.startswith("/"):
            cover = "https://www.tikwm.com" + cover
        if not play:
            raise HTTPException(status_code=400, detail="No download link available")
        return {"title": title, "thumbnail": cover or "", "download_url": play}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
