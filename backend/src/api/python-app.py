from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

# Healthcheck endpoint
@app.get("/healthcheck")
async def healthcheck():
    return {"status": "ok"}

handler = Mangum(app)
