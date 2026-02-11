"""Main FastAPI application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from chatbot_ai_system import __version__
from chatbot_ai_system.config import get_settings
from chatbot_ai_system.database.redis import redis_client

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
        
        # Initialize Redis
        await redis_client.connect(settings.redis_url)

        # Initialize Prometheus Instrumentation
        Instrumentator().instrument(app).expose(app)
        
        # Initialize and register MCP clients
        from chatbot_ai_system.tools.mcp_client import MCPClient
        from chatbot_ai_system.tools import registry
        import os
        
        # Filesystem MCP - restrict to current working directory
        fs_client = MCPClient(
            name="filesystem",
            command="npx",
            args=[
                "-y",
                "@modelcontextprotocol/server-filesystem",
                os.getcwd()
            ],
            env=os.environ.copy()
        )
        registry.register_mcp_client(fs_client)
        
        # Git MCP
        git_client = MCPClient(
            name="git",
            command="npx",
            args=["-y", "@mseep/git-mcp-server"],
            env=os.environ.copy()
        )
        registry.register_mcp_client(git_client)
        
        # Fetch MCP
        fetch_client = MCPClient(
            name="fetch",
            command="npx",
            args=["-y", "zcaceres/fetch-mcp"],
            env=os.environ.copy()
        )
        registry.register_mcp_client(fetch_client)
        
        # Refresh tools
        await registry.refresh_remote_tools()
        logger.info("MCP servers registered and tools refreshed")

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down Chatbot AI System")
        
        # Cleanup MCP clients 
        # (The registry or clients should ideally handle this, but for now we rely on process termination 
        # or we could add a cleanup method to registry)
        from chatbot_ai_system.tools import registry
        # We might want to explicitly close them if we had a reference, but they are in the registry's list.
        # Ideally, we'd add a close_all method to registry.
        
        # Cleanup providers
        from .routes import _providers
        for provider in _providers.values():
            if hasattr(provider, "close"):
                await provider.close()
                
        # Close Redis
        await redis_client.close()

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
