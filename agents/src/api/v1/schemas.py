from pydantic import BaseModel, Field
from typing import Optional

class BarcodeRequest(BaseModel):
    barcode: str
    
class BarcodeResponse(BaseModel):
    barcode: str
    product_info: str

class RAGQueryRequest(BaseModel):
    product_info: str
    collection_id: Optional[str] = "default"
    system_prompt: Optional[str] = "system_common_prompt"
    analysis_type: Optional[str] = "description"
    
class RAGQueryResponse(BaseModel):
    product_info: str
    rag_response: str
    collection_id: str

class Ingredient(BaseModel):
    name: str
    rating: str
    note: str

class ProductAnalysisResponse(BaseModel):
    product_description: str
    safe_ingredients: list[Ingredient] = []
    neutral_ingredients: list[Ingredient] = []
    caution_ingredients: list[Ingredient] = []
    avoid_ingredients: list[Ingredient] = []
    
class RecommendationRequest(BaseModel):
    query: str = Field(..., description="User's request for product recommendation, e.g., 'средство для сухой чувствительной кожи'")
    collection_id: str = Field(default="global_collection", description="ID of the RAG collection to search in")
class RoutineRequest(BaseModel):
    query: str = Field(..., description="User request for routine, e.g., 'жирная кожа акне'")
    collection_id: str = Field(default="global_collection")