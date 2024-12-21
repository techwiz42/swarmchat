import uvicorn
from server import app
import os

print(f"BASE_URL: {os.getenv('BASE_URL')}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
