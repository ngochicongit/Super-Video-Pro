from newsvid.api import create_app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(create_app(), host="127.0.0.1", port=8787, log_level="info")
