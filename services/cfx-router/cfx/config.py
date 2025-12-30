"""
CF-X Router Configuration Module
Loads models.yaml and provides stage→model mapping
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class StageConfig:
    """Configuration for a CF-X stage"""
    model: Optional[str]
    description: str
    max_tokens: Optional[int]
    temperature: Optional[float]


class Config:
    """CF-X Router configuration manager"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration from models.yaml
        
        Args:
            config_path: Optional path to models.yaml. 
                        Defaults to /config/models.yaml or environment variable
        """
        if config_path is None:
            # Try environment variable first
            config_path = os.getenv("CFX_CONFIG_PATH")
            
            # If not set, try common paths
            if not config_path:
                possible_paths = [
                    "/config/models.yaml",  # Container path (copied by Dockerfile)
                    "config/models.yaml",  # Local path (in services/cfx-router/config/)
                    "../config/models.yaml",  # Relative from services/cfx-router
                    "../../config/models.yaml",  # From app directory
                ]
                
                # Try to find config file
                for path in possible_paths:
                    if os.path.exists(path):
                        config_path = path
                        break
                
                # If still not found, use default
                if not config_path:
                    config_path = "/config/models.yaml"  # Will use fallback
        
        self.config_path = Path(config_path)
        self._stages: Dict[str, StageConfig] = {}
        self._default_stage: str = "plan"
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            # Fallback to default config if file not found
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Configuration file not found: {self.config_path}. Using default stage mappings."
            )
            
            # Use default config
            self._stages = {
                "plan": StageConfig(
                    model="claude-3-5-sonnet-20241022",
                    description="Architect stage",
                    max_tokens=4096,
                    temperature=0.7
                ),
                "code": StageConfig(
                    model="deepseek-chat",
                    description="Developer stage",
                    max_tokens=16384,
                    temperature=0.3
                ),
                "review": StageConfig(
                    model="gpt-4o-mini",
                    description="Reviewer stage",
                    max_tokens=4096,
                    temperature=0.2
                ),
                "direct": StageConfig(
                    model=None,
                    description="Direct mode (disabled)",
                    max_tokens=None,
                    temperature=None
                )
            }
            self._default_stage = "plan"
            return
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # Load stage configurations
        stages_data = data.get("stages", {})
        for stage_name, stage_data in stages_data.items():
            self._stages[stage_name] = StageConfig(
                model=stage_data.get("model"),
                description=stage_data.get("description", ""),
                max_tokens=stage_data.get("max_tokens"),
                temperature=stage_data.get("temperature")
            )
        
        # Load default stage
        self._default_stage = data.get("default_stage", "plan")
    
    def get_stage_config(self, stage: str) -> Optional[StageConfig]:
        """
        Get configuration for a specific stage
        
        Args:
            stage: Stage name (plan, code, review, direct)
        
        Returns:
            StageConfig if found, None otherwise
        """
        return self._stages.get(stage)
    
    def get_model_for_stage(self, stage: str) -> Optional[str]:
        """
        Get model name for a specific stage
        
        Args:
            stage: Stage name
        
        Returns:
            Model name if found, None otherwise
        """
        config = self.get_stage_config(stage)
        return config.model if config else None
    
    def get_default_stage(self) -> str:
        """Get default stage name"""
        return self._default_stage
    
    def is_stage_valid(self, stage: str) -> bool:
        """Check if stage name is valid"""
        return stage in self._stages
    
    def list_stages(self) -> list[str]:
        """List all available stage names"""
        return list(self._stages.keys())


# Global config instance (lazy-loaded)
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance (singleton)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

