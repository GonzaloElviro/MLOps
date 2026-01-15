"""
Registro y gestión de modelos ML
"""

import os
import pickle
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import glob

class ModelRegistry:
    def __init__(self, models_dir: str = "/app/models"):
        self.models_dir = models_dir
        self.models: Dict[str, Any] = {}
        self.metadata: Dict[str, Dict] = {}
        self._load_models()
    
    def _load_models(self):
        """Cargar todos los modelos disponibles"""
        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir, exist_ok=True)
            return
        
        # Buscar archivos de modelo
        model_files = glob.glob(os.path.join(self.models_dir, "*.pkl"))
        
        for model_file in model_files:
            try:
                # Cargar modelo
                with open(model_file, 'rb') as f:
                    model = pickle.load(f)
                
                # Cargar metadatos
                metadata_file = model_file.replace('.pkl', '.json')
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                else:
                    # Metadatos por defecto
                    metadata = {
                        'version': os.path.basename(model_file).replace('.pkl', ''),
                        'loaded_at': datetime.now().isoformat(),
                        'file': model_file
                    }
                
                # Guardar en registro
                model_id = metadata['version']
                self.models[model_id] = model
                self.metadata[model_id] = metadata
                
                print(f"✅ Modelo cargado: {model_id}")
                
            except Exception as e:
                print(f"⚠️  Error cargando modelo {model_file}: {e}")
    
    def get_model(self, version: Optional[str] = None) -> Tuple[Any, Dict]:
        """
        Obtener modelo por versión
        
        Args:
            version: Versión del modelo (None para el más reciente)
        
        Returns:
            Tupla (modelo, metadatos)
        """
        if not self.models:
            return None, {}
        
        if version is None:
            # Obtener modelo más reciente
            latest_version = self._get_latest_version()
            version = latest_version
        
        if version in self.models:
            return self.models[version], self.metadata[version]
        
        return None, {}
    
    def get_latest_model(self) -> Optional[Dict]:
        """Obtener metadatos del modelo más reciente"""
        latest_version = self._get_latest_version()
        if latest_version:
            return self.metadata[latest_version]
        return None
    
    def _get_latest_version(self) -> Optional[str]:
        """Determinar la versión más reciente"""
        if not self.metadata:
            return None
        
        # Ordenar por timestamp de carga
        sorted_versions = sorted(
            self.metadata.items(),
            key=lambda x: x[1].get('loaded_at', ''),
            reverse=True
        )
        
        return sorted_versions[0][0] if sorted_versions else None
    
    def get_available_models(self) -> list:
        """Listar todos los modelos disponibles"""
        return [
            {
                'version': version,
                'loaded_at': metadata.get('loaded_at'),
                'features': metadata.get('features', [])
            }
            for version, metadata in self.metadata.items()
        ]
    
    def check_for_new_models(self) -> bool:
        """
        Verificar si hay nuevos modelos en el directorio
        
        Returns:
            True si hay nuevos modelos
        """
        current_count = len(self.models)
        self._load_models()  # Recargar
        return len(self.models) > current_count