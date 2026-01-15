"""
Microservicio de inferencia ML con FastAPI
"""

import os
import pickle
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from .models.model_registry import ModelRegistry
from .monitoring.metrics import ModelMetrics

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar aplicación
app = FastAPI(
    title="ML Inference Service",
    version="1.0.0",
    description="Microservicio para inferencia de modelos ML"
)

# Inicializar componentes
model_registry = ModelRegistry()
metrics = ModelMetrics()

# Modelos Pydantic para validación
class PredictionRequest(BaseModel):
    """Esquema para datos de predicción"""
    features: Dict[str, Any] = Field(
        ...,
        example={"feature1": 0.5, "feature2": 1.2, "feature3": "category_a"}
    )
    model_version: Optional[str] = Field(
        None,
        description="Versión específica del modelo (opcional)"
    )

class PredictionResponse(BaseModel):
    """Esquema para respuesta de predicción"""
    prediction: Any
    model_version: str
    inference_time_ms: float
    timestamp: datetime

@app.on_event("startup")
async def startup_event():
    """Cargar modelo al iniciar la aplicación"""
    try:
        # Cargar el modelo más reciente
        latest_model = model_registry.get_latest_model()
        if latest_model:
            logger.info(f"Modelo cargado: {latest_model['version']}")
        else:
            logger.warning("No se encontraron modelos disponibles")
    except Exception as e:
        logger.error(f"Error cargando modelo: {e}")

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "service": "ML Inference API",
        "status": "operational",
        "model_count": len(model_registry.get_available_models())
    }

@app.get("/health")
async def health_check():
    """Health check para Kubernetes y load balancers"""
    try:
        # Verificar que hay al menos un modelo cargado
        models = model_registry.get_available_models()
        
        if not models:
            raise HTTPException(status_code=503, detail="No models available")
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(),
            "models_loaded": len(models)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest, background_tasks: BackgroundTasks):
    """
    Endpoint principal para predicciones
    
    Args:
        request: Datos para predicción
        background_tasks: Para tareas asíncronas (métricas)
    
    Returns:
        PredictionResponse: Predicción y metadatos
    """
    start_time = datetime.now()
    
    try:
        # Obtener modelo (versión específica o la más reciente)
        model_version = request.model_version
        model, metadata = model_registry.get_model(model_version)
        
        if model is None:
            raise HTTPException(
                status_code=404,
                detail=f"Modelo no encontrado (versión: {model_version})"
            )
        
        # Preparar datos para predicción
        try:
            input_data = pd.DataFrame([request.features])
            # Aquí iría cualquier preprocesamiento necesario
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error procesando features: {str(e)}"
            )
        
        # Realizar predicción
        try:
            prediction = model.predict(input_data)
            # Para clasificación, obtener probabilidades si están disponibles
            if hasattr(model, 'predict_proba'):
                probabilities = model.predict_proba(input_data)
                result = {
                    "prediction": prediction.tolist(),
                    "probabilities": probabilities.tolist()
                }
            else:
                result = prediction.tolist()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error en predicción: {str(e)}"
            )
        
        # Calcular tiempo de inferencia
        inference_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Registrar métricas en background (no bloqueante)
        background_tasks.add_task(
            metrics.record_prediction,
            success=True,
            inference_time=inference_time,
            model_version=metadata['version']
        )
        
        logger.info(
            f"Predicción exitosa - "
            f"Modelo: {metadata['version']}, "
            f"Tiempo: {inference_time:.2f}ms"
        )
        
        return PredictionResponse(
            prediction=result,
            model_version=metadata['version'],
            inference_time_ms=inference_time,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        # Re-lanzar excepciones HTTP
        background_tasks.add_task(
            metrics.record_prediction,
            success=False,
            inference_time=0,
            model_version=model_version or "unknown"
        )
        raise
        
    except Exception as e:
        # Error interno del servidor
        logger.error(f"Error interno en predicción: {e}")
        background_tasks.add_task(
            metrics.record_prediction,
            success=False,
            inference_time=0,
            model_version=model_version or "unknown"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@app.get("/models")
async def list_models():
    """Listar modelos disponibles"""
    models = model_registry.get_available_models()
    return {"models": models}

@app.get("/metrics")
async def get_metrics():
    """Endpoint para métricas Prometheus"""
    return metrics.get_metrics_summary()