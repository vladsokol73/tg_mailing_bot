from pathlib import Path
from typing import Dict, Any
import os
from yaml import safe_load
from dotenv import load_dotenv
from dataclasses import dataclass

load_dotenv()

@dataclass
class BotConfig:
    token: str
    admin_ids: list[int]

@dataclass
class DatabaseConfig:
    host: str
    port: int
    name: str
    user: str
    password: str

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

class Config:
    def __init__(self):
        self.BASE_DIR = Path(__file__).parent
        self.config_data = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_path = os.getenv('CONFIG_PATH', self.BASE_DIR / "static/config.yaml")
        with open(config_path, 'r') as f:
            return safe_load(f)

    @property
    def base_image_path(self) -> Path:
        return Path(os.getenv('BASE_IMAGE_PATH', self.BASE_DIR / "static/base.png"))

    @property
    def output_dir(self) -> Path:
        return Path(os.getenv('OUTPUT_DIR', self.BASE_DIR / "output"))

    @property
    def generation_settings(self) -> Dict[str, Any]:
        return self.config_data['generation_settings']

    @property
    def main_number_settings(self) -> Dict[str, Any]:
        return self.config_data['main_number']

    @property
    def subtracted_number_settings(self) -> Dict[str, Any]:
        return self.config_data['subtracted_number']

    @property
    def multiplied_number_settings(self) -> Dict[str, Any]:
        return self.config_data['multiplied_number']

    @property
    def fail_image_settings(self) -> Dict[str, Any]:
        return self.config_data['fail_image']

    @property
    def bot(self) -> BotConfig:
        """Настройки бота"""
        # Получаем токен из конфига или переменной окружения
        token = os.getenv('BOT_TOKEN', self.config_data['telegram']['token'])
        
        # Получаем список админов из переменной окружения
        admin_ids_str = os.getenv('BOT_ADMIN_IDS', '')
        admin_ids = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]
        
        # Если список пуст, берем из конфига
        if not admin_ids and 'admin_ids' in self.config_data['telegram']:
            admin_ids = self.config_data['telegram']['admin_ids']
        
        return BotConfig(
            token=token,
            admin_ids=admin_ids
        )

    @property
    def database(self) -> DatabaseConfig:
        """Настройки базы данных из переменных окружения"""
        return DatabaseConfig(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', '5432')),
            name=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
