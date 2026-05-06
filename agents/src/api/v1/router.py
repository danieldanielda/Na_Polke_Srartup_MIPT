import logging
import asyncio
from fastapi import HTTPException, APIRouter
from fastapi.responses import JSONResponse
from langfuse import Langfuse

from crew import BarcodeLookupCrew
from src.crews.recommendation_crew import RecommendationCrew
from src.crews.product_analysis_crew import ProductAnalysisCrew
from src.api.v1.schemas import BarcodeRequest, BarcodeResponse, RAGQueryRequest, RecommendationRequest
from src.settings.config import CrewSettings
from src.crews.routine_crew import RoutineArchitectCrew
from src.api.v1.schemas import RoutineRequest

settings = CrewSettings()

langfuse_client = Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
    host=settings.langfuse_host
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/search_barcode")
async def search_barcode(request: BarcodeRequest) -> BarcodeResponse:
    barcode = request.barcode.strip()
    if not barcode.isdigit():
        raise HTTPException(status_code=400, detail="Barcode must contain only digits")

    try:
        inputs = {"barcode": barcode}
        result = await asyncio.to_thread(
            lambda: BarcodeLookupCrew().crew().kickoff(inputs=inputs)
        )

        response_result = BarcodeResponse(
            barcode=barcode,
            product_info=str(result)
        )
        return response_result
    except Exception as e:
        logging.error(f"Error during barcode lookup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process barcode")


@router.post("/analyze_product")
async def analyze_product(request: RAGQueryRequest) -> JSONResponse:
    if not request.product_info or not request.product_info.strip():
        raise HTTPException(status_code=400, detail="Product info cannot be empty")

    try:
        crew_inputs = {
            "product_info": request.product_info,
            "collection_id": request.collection_id,
            "system_prompt": request.system_prompt,
            "analysis_type": request.analysis_type
        }

        crew_result = await asyncio.to_thread(
            ProductAnalysisCrew().run_with_monitoring,
            inputs=crew_inputs,
            analysis_type=request.analysis_type
        )

        if request.analysis_type == "summary":
            return JSONResponse(content={"summary": crew_result.raw})
        elif hasattr(crew_result, 'pydantic') and crew_result.pydantic:
            return JSONResponse(content=crew_result.pydantic.model_dump())
        elif hasattr(crew_result, 'json_dict') and crew_result.json_dict:
            return JSONResponse(content=crew_result.json_dict)
        else:
            return JSONResponse(content={"result": str(crew_result.raw)})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during product analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to perform product analysis: {str(e)}")
    

@router.post("/recommend_products")
async def recommend_products(request: RecommendationRequest):
    """
    Endpoint to get product recommendations based on user query.
    """
    user_query = request.query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        inputs = {
            "user_query": user_query,
            "collection_id": getattr(request, 'collection_id', "global_collection"),
            "system_prompt": "system_common_prompt" 
        }

        result = await asyncio.to_thread(
            RecommendationCrew().run_monitored,
            inputs=inputs
        )

        return JSONResponse(content={"recommendations": result.raw})

    except Exception as e:
        logger.error(f"Error during product recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")
    
    
@router.post("/build_routine")
async def build_routine(request: RoutineRequest):
    """
    Builds a full skincare routine based on user query.
    """
    user_query = request.query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        inputs = {
            "user_query": user_query,
            "collection_id": request.collection_id
        }

        result = await asyncio.to_thread(
            RoutineArchitectCrew().run_monitored, 
            inputs=inputs
        )

        return JSONResponse(content={"routine": result.raw})

    except Exception as e:
        logger.error(f"Error during routine building: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to build routine: {str(e)}")