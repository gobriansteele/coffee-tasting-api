from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    CORS_ORIGINS: list[str] | str = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8080",
            "http://localhost:5173",  # Vite default
        ],
        description="CORS allowed origins",
    )

    @classmethod
    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        elif isinstance(v, str):
            return [v]
        raise ValueError(v)

    # Supabase
    SUPABASE_URL: str | None = Field(default=None, description="Supabase project URL")
    SUPABASE_KEY: str | None = Field(default=None, description="Supabase anon key")
    SUPABASE_SERVICE_ROLE_KEY: str | None = Field(default=None, description="Supabase service role key")
    SUPABASE_JWT_SECRET: str | None = Field(
        default=None, description="Supabase JWT secret for token validation"
    )

    # Security
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production", description="Secret key for JWT token generation"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiration time in minutes"
    )

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Rate limit requests per period")
    RATE_LIMIT_PERIOD: int = Field(default=60, description="Rate limit period in seconds")

    # Admin API Key (for manual admin operations like embedding trueup)
    ADMIN_API_KEY: str | None = Field(default=None, description="Static API key for admin operations")

    # OpenAI
    OPENAI_API_KEY: str | None = Field(default=None, description="OpenAI API key for recommendation engine")
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small", description="OpenAI embedding model for vector search"
    )

    # ChromaDB
    CHROMA_DB_NAME: str | None = Field(default=None, description="ChromaDB database name")
    CHROMA_API_KEY: str | None = Field(default=None, description="ChromaDB API key")
    CHROMA_TENANT: str | None = Field(default=None, description="ChromaDB tenant ID")

    # Neo4j Graph Database
    NEO4J_URI: str | None = Field(default=None, description="Neo4j Aura connection URI")
    NEO4J_USER: str = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str | None = Field(default=None, description="Neo4j password")

    # Geocoding (OpenCage)
    OPENCAGE_API_KEY: str | None = Field(default=None, description="OpenCage geocoding API key")

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() in ("development", "dev", "local")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT.lower() in ("testing", "test")

    @property
    def neo4j_configured(self) -> bool:
        """Check if Neo4j is properly configured."""
        return bool(self.NEO4J_URI and self.NEO4J_PASSWORD)

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, env_parse_none_str="None")


settings = Settings()
