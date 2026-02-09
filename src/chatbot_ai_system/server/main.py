"""Main FastAPI application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chatbot_ai_system import __version__
from chatbot_ai_system.config import get_settings

from .routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Chatbot AI System",
        description="Production-grade AI chatbot platform with multi-provider LLM support",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(router)

    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting Chatbot AI System v{__version__}")
        logger.info(f"Debug mode: {settings.debug}")
        logger.info(f"Default LLM provider: {settings.default_llm_provider}")

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down Chatbot AI System")
        # Cleanup providers
        from .routes import _providers
        for provider in _providers.values():
            if hasattr(provider, "close"):
                await provider.close()

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "chatbot_ai_system.server.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
