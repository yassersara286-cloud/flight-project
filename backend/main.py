from fastapi import FastAPI

app = FastAPI(
    title="Flight Analysis API",
    description="Backend API for predicting and analyzing flight delays.",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Flight Analysis API!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}