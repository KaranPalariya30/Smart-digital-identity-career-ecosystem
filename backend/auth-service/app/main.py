from fastapi import FastAPI

app = FastAPI(
    title="Smart Digital Identity - Authentication Service",
    version="1.0.0"
)


@app.get("/")
def health_check():
    return {
        "message": "Authentication service is running"
    }