from typing import List, Optional, Union
from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # API Configuration
    API_V1_STR: str = Field(default="/api/v1", description="API v1 prefix")
    PROJECT_NAME: str = Field(default="Coffee Tasting API", description="Project name")
    VERSION: str = Field(default="0.1.0", description="API version")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8080",
            "http://localhost:5173",  # Vite default
        ],
        description="CORS allowed origins"
    )
    
    @classmethod
    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database
    DATABASE_URL: Optional[PostgresDsn] = Field(
        default=None, description="Database connection URL"
    )
    DATABASE_URL_TEST: Optional[PostgresDsn] = Field(
        default=None, description="Test database connection URL"
    )
    
    # Supabase
    SUPABASE_URL: Optional[str] = Field(
        default=None, description="Supabase project URL"
    )
    SUPABASE_KEY: Optional[str] = Field(
        default=None, description="Supabase anon key"
    )
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = Field(
        default=None, description="Supabase service role key"
    )
    SUPABASE_JWT_SECRET: Optional[str] = Field(
        default=None, description="Supabase JWT secret for token validation"
    )
    
    # Security
    SECRET_KEY: str = Field(
        description="Secret key for JWT token generation"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiration time in minutes"
    )
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(
        default=100, description="Rate limit requests per period"
    )
    RATE_LIMIT_PERIOD: int = Field(
        default=60, description="Rate limit period in seconds"
    )
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() in ("development", "dev", "local")
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")
    
    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT.lower() in ("testing", "test")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()