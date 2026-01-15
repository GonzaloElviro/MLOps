"""
Módulo de métricas para monitoreo del modelo ML
"""

from typing import Dict, Optional
from datetime import datetime
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    REGISTRY
)
import time

class ModelMetrics:
    """
    Clase para gestión de métricas del modelo ML
    """
    
    def __init__(self, namespace: str = "mlops", subsystem: str = "inference"):
        self.namespace = namespace
        self.subsystem = subsystem
        
        # Contadores
        self.predictions_total = Counter(
            f'{namespace}_{subsystem}_predictions_total',
            'Total number of predictions',
            ['model_version', 'status']
        )
        
        self.errors_total = Counter(
            f'{namespace}_{subsystem}_errors_total',
            'Total number of errors',
            ['error_type', 'model_version']
        )
        
        # Histogramas para latencia
        self.inference_latency = Histogram(
            f'{namespace}_{subsystem}_inference_latency_seconds',
            'Inference latency in seconds',
            ['model_version'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        )
        
        # Gauges para métricas en tiempo real
        self.active_connections = Gauge(
            f'{namespace}_{subsystem}_active_connections',
            'Number of active connections'
        )
        
        self.model_memory_usage = Gauge(
            f'{namespace}_{subsystem}_model_memory_bytes',
            'Memory usage of the model in bytes',
            ['model_version']
        )
        
        self.cpu_usage = Gauge(
            f'{namespace}_{subsystem}_cpu_usage_percent',
            'CPU usage percentage'
        )
        
        # Métricas de calidad del modelo
        self.prediction_confidence = Histogram(
            f'{namespace}_{subsystem}_prediction_confidence',
            'Confidence score of predictions',
            buckets=[0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
        )
        
        # Métricas de datos (data drift)
        self.feature_distribution = Histogram(
            f'{namespace}_{subsystem}_feature_value',
            'Distribution of feature values',
            ['feature_name'],
            buckets=[-10, -5, -2, -1, 0, 1, 2, 5, 10]
        )
        
        # Métricas de negocio (si aplica)
        self.revenue_impact = Counter(
            f'{namespace}_{subsystem}_revenue_impact_total',
            'Total revenue impact of predictions',
            ['model_version']
        )
    
    def record_prediction(self, 
                         success: bool, 
                         inference_time: float, 
                         model_version: str,
                         confidence: Optional[float] = None):
        """
        Registrar una predicción
        
        Args:
            success: Si la predicción fue exitosa
            inference_time: Tiempo de inferencia en segundos
            model_version: Versión del modelo usado
            confidence: Nivel de confianza (opcional)
        """
        status = "success" if success else "error"
        
        # Actualizar contadores
        self.predictions_total.labels(
            model_version=model_version,
            status=status
        ).inc()
        
        # Registrar latencia si fue exitosa
        if success:
            self.inference_latency.labels(
                model_version=model_version
            ).observe(inference_time / 1000.0)  # Convertir ms a segundos
            
            # Registrar confianza si está disponible
            if confidence is not None:
                self.prediction_confidence.observe(confidence)
        
        # Registrar error si corresponde
        if not success:
            self.errors_total.labels(
                error_type="prediction_failed",
                model_version=model_version
            ).inc()
    
    def record_data_drift(self, feature_name: str, value: float):
        """
        Registrar valores de características para detección de drift
        
        Args:
            feature_name: Nombre de la característica
            value: Valor de la característica
        """
        self.feature_distribution.labels(
            feature_name=feature_name
        ).observe(value)
    
    def record_connection(self):
        """Registrar nueva conexión activa"""
        self.active_connections.inc()
    
    def record_disconnection(self):
        """Registrar desconexión"""
        self.active_connections.dec()
    
    def update_resource_usage(self, memory_bytes: int, cpu_percent: float):
        """
        Actualizar uso de recursos
        
        Args:
            memory_bytes: Uso de memoria en bytes
            cpu_percent: Uso de CPU en porcentaje
        """
        self.model_memory_usage.set(memory_bytes)
        self.cpu_usage.set(cpu_percent)
    
    def get_metrics_summary(self) -> Dict:
        """
        Obtener resumen de métricas actuales
        
        Returns:
            Diccionario con resumen de métricas
        """
        # Nota: En producción, obtendría valores de Prometheus API
        return {
            "timestamp": datetime.now().isoformat(),
            "active_connections": self.active_connections._value.get(),
            "total_predictions": {
                "success": self._get_counter_value(self.predictions_total, "success"),
                "error": self._get_counter_value(self.predictions_total, "error")
            },
            "avg_latency_seconds": self._estimate_average_latency()
        }
    
    def _get_counter_value(self, counter, label_value: str) -> int:
        """Valor estimado del contador (simplificado)"""
        # En producción, consultaría Prometheus
        return 0
    
    def _estimate_average_latency(self) -> float:
        """Latencia promedio estimada (simplificado)"""
        # En producción, consultaría Prometheus
        return 0.0
    
    def expose_metrics(self):
        """Exponer métricas para Prometheus"""
        return generate_latest(REGISTRY)


# Middleware de FastAPI para métricas
class MetricsMiddleware:
    """Middleware para capturar métricas automáticamente"""
    
    def __init__(self, app, metrics: ModelMetrics):
        self.app = app
        self.metrics = metrics
    
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        path = scope['path']
        
        # Incrementar conexiones activas
        self.metrics.record_connection()
        
        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                # Capturar código de estado
                status_code = message['status']
                
                # Registrar métricas basadas en el endpoint
                if path.startswith('/predict'):
                    # Ya se registra en el endpoint
                    pass
                elif path == '/health':
                    self.metrics.predictions_total.labels(
                        model_version="health_check",
                        status="success" if status_code < 400 else "error"
                    ).inc()
                
                # Registrar tiempo de respuesta
                response_time = time.time() - start_time
                if path != '/metrics':  # No registrar métricas del endpoint de métricas
                    self.metrics.inference_latency.labels(
                        model_version="api"
                    ).observe(response_time)
            
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            # Registrar error
            self.metrics.errors_total.labels(
                error_type="middleware_exception",
                model_version="unknown"
            ).inc()
            raise
        finally:
            # Decrementar conexiones activas
            self.metrics.record_disconnection()