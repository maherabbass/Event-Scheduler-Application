from pydantic_settings import BaseSettings, SettingsConfigDict

# Localhost origins are always safe to allow — no attacker reaches localhost.
# Hardcoding them means developers never need to touch CORS config.
_LOCALHOST_ORIGINS: list[str] = [
    "http://localhost:3000",
    "http://localhost:4173",  # vite preview
    "http://localhost:5173",  # vite dev
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:4173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
]


class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/events"

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    # Primary frontend URL — used for the OAuth callback redirect AND as the
    # default CORS origin.  Must match the deployed frontend (Netlify/Vercel).
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    # Additional explicit CORS origins, comma-separated.
    EXTRA_CORS_ORIGINS: str = ""

    # Regex matching dynamic origins such as Netlify deploy-preview URLs.
    CORS_ORIGIN_REGEX: str = ""

    AI_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        """Explicit allowed origins: localhost variants + FRONTEND_URL + extras."""
        seen: set[str] = set()
        origins: list[str] = []
        for raw in [*_LOCALHOST_ORIGINS, self.FRONTEND_URL, *self.EXTRA_CORS_ORIGINS.split(",")]:
            origin = raw.strip()
            if origin and origin not in seen:
                seen.add(origin)
                origins.append(origin)
        return origins

    @property
    def cors_origin_regex(self) -> str | None:
        """Regex for dynamic origins (Netlify previews, etc.). None = disabled."""
        return self.CORS_ORIGIN_REGEX.strip() or None


settings = Settings()
