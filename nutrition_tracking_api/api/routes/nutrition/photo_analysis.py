"""Роут для распознавания блюд на фото."""

from typing import Annotated, Any

from fastapi import APIRouter, File, UploadFile

from nutrition_tracking_api.api.schemas.nutrition.photo_analysis import PhotoAnalysisOut
from nutrition_tracking_api.api.services.nutrition.photo_analysis import PhotoAnalysisService

router = APIRouter(tags=["photo-analysis"], prefix="/foods")


@router.post(
    "/analyze-photo/",
    summary="Распознать блюда на фото",
    response_model=PhotoAnalysisOut,
)
def analyze_photo(
    photo: Annotated[UploadFile, File(description="Фото блюда (jpeg/png/webp)")],
) -> Any:
    """Отправляет фото в vision LLM и возвращает список распознанных блюд с КБЖУ."""
    return PhotoAnalysisService().analyze(photo)
