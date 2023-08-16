from fastapi import FastAPI
from fastapi.responses import Response, UJSONResponse

from .face_segmentation.main import api as face_segmentation_api

app = FastAPI()

app.mount("/face_segmentation", face_segmentation_api)

@app.get("/")
def root() -> Response:
    resp = "Main API"
    return UJSONResponse(content=resp)
