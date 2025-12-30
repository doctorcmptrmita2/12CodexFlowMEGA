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
                        Defaults to /config/models.yaml relative to project root
        """
        if config_path is None:
            # Default: assume running from project root
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "models.yaml"
        
        self.config_path = Path(config_path)
        self._stages: Dict[str, StageConfig] = {}
        self._default_stage: str = "plan"
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}"
            )
        
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

