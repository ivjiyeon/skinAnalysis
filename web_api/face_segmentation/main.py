from fastapi import FastAPI, File
from fastapi.responses import Response, UJSONResponse, FileResponse

from typing import Annotated

from models.face_segmentation.skin_detection import mean_colour, segmented_image

api = FastAPI()

@api.get("/")
def root() -> Response:
    resp = "Face Segmentation API"
    return UJSONResponse(content=resp)

@api.post("/get_mean_colour/")
def get_mean_colour(file: Annotated[bytes, File()]):
    return UJSONResponse(content={"results": list(mean_colour(file))})

@api.post(  "/get_segmented_image/", response_class=FileResponse)
def get_segmented_image(file: Annotated[bytes, File()]):
    return segmented_image(file)