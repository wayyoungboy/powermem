"""
PowerMem Benchmark Server

⚠️ IMPORTANT: This server is NOT the official PowerMem server API.
It is only used for benchmark testing scenarios and should not be used in production.

This server provides REST APIs for managing and searching memories.

Configuration:
    All configuration is done through environment variables. 
    Copy .env.example to .env and modify the values as needed.
    
    Example:
        cp benchmark/server/.env.example benchmark/server/.env
        # Then edit benchmark/server/.env with your settings
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, field_validator
from powermem import Memory

# ============================================================================
# Logging Configuration
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# Environment Variable Loading
# ============================================================================

def load_environment_variables() -> None:
    """Load environment variables from .env file."""
    # Try to load from .env file in the same directory as this script
    script_dir = Path(__file__).parent
    env_path = script_dir / ".env"
    
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        logger.info(f"Loaded environment variables from {env_path}")
    else:
        # Fallback to default behavior (current directory or parent directories)
        load_dotenv()
        logger.info("Loaded environment variables from default locations")

load_environment_variables()

# ============================================================================
# Configuration - Load from environment variables
# ============================================================================

def get_env_str(key: str, default: str = "") -> str:
    """Get environment variable as string."""
    value = os.getenv(key, default)
    if not value and not default:
        raise ValueError(f"{key} environment variable is required")
    return value

def get_env_int(key: str, default: int = 0) -> int:
    """Get environment variable as integer."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid integer value for {key}: {value}, using default: {default}")
        return default

def get_env_float(key: str, default: float = 0.0) -> float:
    """Get environment variable as float."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning(f"Invalid float value for {key}: {value}, using default: {default}")
        return default

def get_env_bool(key: str, default: bool = False) -> bool:
    """Get environment variable as boolean."""
    value = os.getenv(key, "").lower()
    if not value:
        return default
    return value in ("true", "1", "yes", "on")

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_API_KEY = get_env_str("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
LLM_TEMPERATURE = get_env_float("LLM_TEMPERATURE", 0.2)
LLM_MAX_TOKENS = get_env_int("LLM_MAX_TOKENS", 1000)
LLM_TOP_P = get_env_float("LLM_TOP_P", 0.8)
LLM_TOP_K = get_env_int("LLM_TOP_K", 50)

# LLM Base URLs
LLM_BASE_URLS = {
    "openai": os.getenv("OPENAI_LLM_BASE_URL", "https://api.openai.com/v1"),
    "qwen": os.getenv("QWEN_LLM_BASE_URL", "https://dashscope.aliyuncs.com/api/v1"),
    "siliconflow": os.getenv("SILICONFLOW_LLM_BASE_URL", "https://api.siliconflow.cn/v1"),
    "ollama": os.getenv("OLLAMA_LLM_BASE_URL", ""),
    "vllm": os.getenv("VLLM_LLM_BASE_URL", ""),
    "anthropic": os.getenv("ANTHROPIC_LLM_BASE_URL", "https://api.anthropic.com"),
    "deepseek": os.getenv("DEEPSEEK_LLM_BASE_URL", "https://api.deepseek.com"),
}

# Embedding Configuration
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "qwen").lower()
EMBEDDING_API_KEY = get_env_str("EMBEDDING_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
EMBEDDING_DIMS = get_env_int("EMBEDDING_DIMS", 1536)

# Embedding Base URLs
EMBEDDING_BASE_URLS = {
    "qwen": os.getenv("QWEN_EMBEDDING_BASE_URL", "https://dashscope.aliyuncs.com/api/v1"),
    "openai": os.getenv("OPENAI_EMBEDDING_BASE_URL", "https://api.openai.com/v1"),
    "siliconflow": os.getenv("SILICONFLOW_EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1"),
    "huggingface": os.getenv("HUGGINFACE_EMBEDDING_BASE_URL", ""),
    "lmstudio": os.getenv("LMSTUDIO_EMBEDDING_BASE_URL", ""),
    "ollama": os.getenv("OLLAMA_EMBEDDING_BASE_URL", ""),
}

# Database Configuration
DATABASE_PROVIDER = os.getenv("DATABASE_PROVIDER", "oceanbase").lower()
VECTOR_WEIGHT = get_env_float("VECTOR_WEIGHT", 0.5)
FTS_WEIGHT = get_env_float("FTS_WEIGHT", 0.5)

# Token Counting Configuration
TOKEN_COUNTING = get_env_bool("TOKEN_COUNTING", True)

# Application Configuration
HISTORY_DB_PATH = os.getenv("HISTORY_DB_PATH", "history.db")
CONFIG_VERSION = os.getenv("CONFIG_VERSION", "v1.1")

# Reranker Configuration
RERANKER_ENABLED = get_env_bool("RERANKER_ENABLED", True)
RERANKER_PROVIDER = os.getenv("RERANKER_PROVIDER", "qwen")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "qwen3-rerank")
RERANKER_API_KEY = os.getenv("RERANKER_API_KEY", EMBEDDING_API_KEY)

# Sparse Embedding Configuration
SPARSE_VECTOR_ENABLE = get_env_bool("SPARSE_VECTOR_ENABLE", False)
SPARSE_EMBEDDER_PROVIDER = os.getenv("SPARSE_EMBEDDER_PROVIDER", "qwen")
SPARSE_EMBEDDER_API_KEY = os.getenv("SPARSE_EMBEDDER_API_KEY", EMBEDDING_API_KEY)
SPARSE_EMBEDDER_MODEL = os.getenv("SPARSE_EMBEDDER_MODEL", EMBEDDING_MODEL)
SPARSE_EMBEDDING_BASE_URL = os.getenv("SPARSE_EMBEDDING_BASE_URL", EMBEDDING_BASE_URLS.get(SPARSE_EMBEDDER_PROVIDER, ""))
SPARSE_EMBEDDER_DIMS = get_env_int("SPARSE_EMBEDDER_DIMS", 1536)


def load_config() -> Dict[str, Any]:
    """Load and build configuration dictionary from environment variables."""
    # Select vector store based on DATABASE_PROVIDER
    if DATABASE_PROVIDER == "oceanbase":
        vector_store_config = {
            "host": os.getenv("OCEANBASE_HOST", "127.0.0.1"),
            "port": os.getenv("OCEANBASE_PORT", "2881"),
            "user": os.getenv("OCEANBASE_USER", "root@sys"),
            "password": os.getenv("OCEANBASE_PASSWORD", ""),
            "db_name": os.getenv("OCEANBASE_DATABASE", "ai_work"),
            "collection_name": os.getenv("OCEANBASE_COLLECTION", "powermem_collection"),
            "embedding_model_dims": get_env_int("OCEANBASE_EMBEDDING_MODEL_DIMS", EMBEDDING_DIMS),
            "index_type": os.getenv("OCEANBASE_INDEX_TYPE", "HNSW"),
            "vidx_metric_type": os.getenv("OCEANBASE_VECTOR_METRIC_TYPE", "l2"),
            "vector_weight": VECTOR_WEIGHT,
            "fts_weight": FTS_WEIGHT,
        }
        
        # Add sparse vector support if enabled
        if SPARSE_VECTOR_ENABLE:
            vector_store_config["include_sparse"] = True
        
        vector_store = {
            "provider": "oceanbase",
            "config": vector_store_config,
        }
    elif DATABASE_PROVIDER == "postgres":
        vector_store = {
            "provider": "pgvector",
            "config": {
                "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
                "port": os.getenv("POSTGRES_PORT", "5432"),
                "user": os.getenv("POSTGRES_USER", "postgres"),
                "password": os.getenv("POSTGRES_PASSWORD", ""),
                "dbname": os.getenv("POSTGRES_DATABASE", "ai_work"),
                "collection_name": os.getenv("POSTGRES_COLLECTION", "memories"),
                "embedding_model_dims": get_env_int("POSTGRES_EMBEDDING_MODEL_DIMS", EMBEDDING_DIMS),
                "diskann": get_env_bool("POSTGRES_DISKANN", True),
                "hnsw": get_env_bool("POSTGRES_HNSW", True),
            },
        }
    else:
        raise ValueError(
            f"Unsupported DATABASE_PROVIDER: {DATABASE_PROVIDER}. "
            f"Must be 'oceanbase' or 'postgres'"
        )

    # Build LLM configuration
    llm_base_url = LLM_BASE_URLS.get(LLM_PROVIDER, "")
    llm_config = {
        "api_key": LLM_API_KEY,
        "temperature": LLM_TEMPERATURE,
        "model": LLM_MODEL,
    }
    
    # Add provider-specific base URL if available
    if llm_base_url:
        if LLM_PROVIDER == "openai":
            llm_config["openai_base_url"] = llm_base_url
        elif LLM_PROVIDER in ("qwen", "siliconflow", "ollama", "vllm", "deepseek"):
            llm_config[f"{LLM_PROVIDER}_base_url"] = llm_base_url
        elif LLM_PROVIDER == "anthropic":
            llm_config["anthropic_base_url"] = llm_base_url
    
    # Add optional parameters
    if LLM_MAX_TOKENS:
        llm_config["max_tokens"] = LLM_MAX_TOKENS
    if LLM_TOP_P:
        llm_config["top_p"] = LLM_TOP_P
    if LLM_TOP_K:
        llm_config["top_k"] = LLM_TOP_K

    # Build embedder configuration
    embedding_base_url = EMBEDDING_BASE_URLS.get(EMBEDDING_PROVIDER, "")
    embedder_config = {
        "api_key": EMBEDDING_API_KEY,
        "model": EMBEDDING_MODEL,
        "embedding_dims": EMBEDDING_DIMS,
    }
    
    # Add provider-specific base URL if available
    if embedding_base_url:
        if EMBEDDING_PROVIDER == "openai":
            embedder_config["openai_base_url"] = embedding_base_url
        elif EMBEDDING_PROVIDER in ("qwen", "siliconflow", "huggingface", "lmstudio", "ollama"):
            embedder_config[f"{EMBEDDING_PROVIDER}_base_url"] = embedding_base_url

    # Build configuration dictionary
    config = {
        "version": CONFIG_VERSION,
        "vector_store": vector_store,
        "llm": {
            "provider": LLM_PROVIDER,
            "config": llm_config,
        },
        "embedder": {
            "provider": EMBEDDING_PROVIDER,
            "config": embedder_config,
        },
        "history_db_path": HISTORY_DB_PATH,
    }
    
    # Add reranker if enabled
    if RERANKER_ENABLED:
        config["reranker"] = {
            "enabled": True,
            "provider": RERANKER_PROVIDER,
            "config": {
                "api_key": RERANKER_API_KEY,
                "model": RERANKER_MODEL,
            },
        }
    
    # Add sparse embedder if enabled
    if SPARSE_VECTOR_ENABLE:
        config["sparse_embedder"] = {
            "provider": SPARSE_EMBEDDER_PROVIDER,
            "config": {
                "api_key": SPARSE_EMBEDDER_API_KEY,
                "model": SPARSE_EMBEDDER_MODEL,
                "embedding_dims": SPARSE_EMBEDDER_DIMS,
            },
        }
        if SPARSE_EMBEDDING_BASE_URL:
            config["sparse_embedder"]["config"][f"{SPARSE_EMBEDDER_PROVIDER}_base_url"] = SPARSE_EMBEDDING_BASE_URL

    return config


# ============================================================================
# Token Tracking
# ============================================================================


class AsyncTokenTracker:
    """Track token usage for LLM API calls."""

    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.cached_tokens = 0
        self._lock = asyncio.Lock()

    async def track_token(self, usage: Any) -> None:
        """Asynchronously update token count."""
        async with self._lock:
            if hasattr(usage, "prompt_tokens"):
                self.prompt_tokens += usage.prompt_tokens
            if hasattr(usage, "completion_tokens"):
                self.completion_tokens += usage.completion_tokens
            if hasattr(usage, "total_tokens"):
                self.total_tokens += usage.total_tokens
            if hasattr(usage, "prompt_tokens_details") and usage.prompt_tokens_details:
                if hasattr(usage.prompt_tokens_details, "cached_tokens"):
                    self.cached_tokens += usage.prompt_tokens_details.cached_tokens

    def get_token_count(self) -> int:
        """Get total token count."""
        return self.total_tokens

    def get_detailed_stats(self) -> Dict[str, int]:
        """Get detailed token statistics."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cached_tokens": self.cached_tokens,
        }

    def reset(self) -> None:
        """Reset all token counts."""
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.cached_tokens = 0


async_token_tracker = AsyncTokenTracker()


def setup_token_counting() -> None:
    """Setup token counting for OpenAI API if enabled."""
    if not TOKEN_COUNTING:
        logger.info("Token counting is disabled")
        return

    try:
        logger.info("Token counting enabled")
        from openai.resources.chat.completions.completions import Completions
        import openai.resources.chat.chat

        class CountCompletions(Completions):
            """Wrapper for OpenAI Completions to track token usage."""

            def _safe_async_track_token(self, token_count: Any) -> None:
                """Thread-safe async token tracking."""
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(async_token_tracker.track_token(token_count))
                    else:
                        loop.run_until_complete(async_token_tracker.track_token(token_count))
                except RuntimeError:
                    asyncio.run(async_token_tracker.track_token(token_count))

            def create(self, *args: Any, **kwargs: Any) -> Any:
                """Override create to track token usage."""
                resp = super().create(*args, **kwargs)
                if hasattr(resp, "usage") and resp.usage:
                    self._safe_async_track_token(resp.usage)
                return resp

        module = sys.modules["openai.resources.chat.chat"]
        setattr(module, "Completions", CountCompletions)
        logger.info("Token counting setup completed")
    except ImportError:
        logger.warning("OpenAI module not found, token counting will not work")
    except Exception as e:
        logger.error(f"Failed to setup token counting: {e}", exc_info=True)


# ============================================================================
# Initialize Application
# ============================================================================

try:
    DEFAULT_CONFIG = load_config()
    MEMORY_INSTANCE = Memory.from_config(DEFAULT_CONFIG)
    logger.info("Memory instance initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize memory instance: {e}", exc_info=True)
    raise

# Setup token counting
setup_token_counting()

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="PowerMem Benchmark REST APIs",
    description="A REST API for managing and searching memories for benchmark testing scenarios.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================================
# Request/Response Models
# ============================================================================


class Message(BaseModel):
    """Message model for memory storage."""

    role: str = Field(..., description="Role of the message (user or assistant).")
    content: str = Field(..., description="Message content.")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role value."""
        if v.lower() not in ("user", "assistant", "system"):
            raise ValueError("Role must be 'user', 'assistant', or 'system'")
        return v.lower()


class MemoryCreate(BaseModel):
    """Request model for creating memories."""

    messages: List[Message] = Field(..., description="List of messages to store.")
    user_id: Optional[str] = Field(None, description="User identifier.")
    agent_id: Optional[str] = Field(None, description="Agent identifier.")
    run_id: Optional[str] = Field(None, description="Run identifier.")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata.")


class SearchRequest(BaseModel):
    """Request model for searching memories."""

    query: str = Field(..., description="Search query.")
    user_id: Optional[str] = Field(None, description="User identifier.")
    run_id: Optional[str] = Field(None, description="Run identifier.")
    agent_id: Optional[str] = Field(None, description="Agent identifier.")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters.")


# ============================================================================
# Helper Functions
# ============================================================================


def validate_identifiers(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> None:
    """Validate that at least one identifier is provided."""
    if not any([user_id, run_id, agent_id]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one identifier (user_id, agent_id, run_id) is required.",
        )


def build_identifier_params(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build parameters dictionary from identifiers."""
    return {
        k: v
        for k, v in {
            "user_id": user_id,
            "run_id": run_id,
            "agent_id": agent_id,
        }.items()
        if v is not None
    }


# ============================================================================
# API Routes
# ============================================================================


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API documentation."""
    return RedirectResponse(url="/docs")


@app.post("/configure", summary="Configure PowerMem", status_code=status.HTTP_200_OK)
def set_config(config: Dict[str, Any]) -> Dict[str, str]:
    """Set memory configuration."""
    global MEMORY_INSTANCE
    try:
        MEMORY_INSTANCE = Memory.from_config(config)
        logger.info("Configuration updated successfully")
        return {"message": "Configuration set successfully"}
    except Exception as e:
        logger.exception("Error in set_config:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set configuration: {str(e)}",
        )


@app.post("/memories", summary="Create memories", status_code=status.HTTP_201_CREATED)
def add_memory(memory_create: MemoryCreate) -> JSONResponse:
    """Store new memories."""
    validate_identifiers(
        memory_create.user_id,
        memory_create.run_id,
        memory_create.agent_id,
    )

    try:
        params = {
            k: v
            for k, v in memory_create.model_dump().items()
            if v is not None and k != "messages"
        }
        response = MEMORY_INSTANCE.add(
            messages=[m.model_dump() for m in memory_create.messages],
            **params,
        )
        logger.info(f"Memory added successfully: {len(memory_create.messages)} messages")
        return JSONResponse(content=response)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in add_memory:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add memory: {str(e)}",
        )


@app.get("/memories", summary="Get memories", status_code=status.HTTP_200_OK)
def get_all_memories(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve stored memories."""
    validate_identifiers(user_id, run_id, agent_id)

    try:
        params = build_identifier_params(user_id, run_id, agent_id)
        result = MEMORY_INSTANCE.get_all(**params)
        logger.info(f"Retrieved memories for identifiers: {params}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in get_all_memories:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memories: {str(e)}",
        )


@app.get("/memories/{memory_id}", summary="Get a memory", status_code=status.HTTP_200_OK)
def get_memory(memory_id: int) -> Dict[str, Any]:
    """Retrieve a specific memory by ID."""
    try:
        result = MEMORY_INSTANCE.get(memory_id)
        logger.info(f"Retrieved memory with ID: {memory_id}")
        return result
    except Exception as e:
        logger.exception(f"Error in get_memory for ID {memory_id}:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory: {str(e)}",
        )


@app.post("/search", summary="Search memories", status_code=status.HTTP_200_OK)
def search_memories(search_req: SearchRequest) -> Dict[str, Any]:
    """Search for memories based on a query."""
    try:
        params = {
            k: v
            for k, v in search_req.model_dump().items()
            if v is not None and k != "query"
        }
        result = MEMORY_INSTANCE.search(query=search_req.query, **params)
        logger.info(f"Search completed for query: {search_req.query[:50]}...")
        return result
    except Exception as e:
        logger.exception("Error in search_memories:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search memories: {str(e)}",
        )


@app.put("/memories/{memory_id}", summary="Update a memory", status_code=status.HTTP_200_OK)
def update_memory(memory_id: int, updated_memory: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing memory with new content.

    Args:
        memory_id: ID of the memory to update
        updated_memory: New content to update the memory with

    Returns:
        dict: Updated memory data
    """
    try:
        result = MEMORY_INSTANCE.update(memory_id=memory_id, data=updated_memory)
        logger.info(f"Memory updated successfully: ID {memory_id}")
        return result
    except Exception as e:
        logger.exception(f"Error in update_memory for ID {memory_id}:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update memory: {str(e)}",
        )


@app.get(
    "/memories/{memory_id}/history",
    summary="Get memory history",
    status_code=status.HTTP_200_OK,
)
def memory_history(memory_id: int) -> Dict[str, Any]:
    """Retrieve memory history."""
    try:
        result = MEMORY_INSTANCE.history(memory_id=memory_id)
        logger.info(f"Retrieved history for memory ID: {memory_id}")
        return result
    except Exception as e:
        logger.exception(f"Error in memory_history for ID {memory_id}:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory history: {str(e)}",
        )


@app.delete(
    "/memories/{memory_id}",
    summary="Delete a memory",
    status_code=status.HTTP_200_OK,
)
def delete_memory(memory_id: int) -> Dict[str, str]:
    """Delete a specific memory by ID."""
    try:
        MEMORY_INSTANCE.delete(memory_id=memory_id)
        logger.info(f"Memory deleted successfully: ID {memory_id}")
        return {"message": "Memory deleted successfully"}
    except Exception as e:
        logger.exception(f"Error in delete_memory for ID {memory_id}:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete memory: {str(e)}",
        )


@app.delete("/memories", summary="Delete all memories", status_code=status.HTTP_200_OK)
def delete_all_memories(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> Dict[str, str]:
    """Delete all memories for a given identifier."""
    validate_identifiers(user_id, run_id, agent_id)

    try:
        params = build_identifier_params(user_id, run_id, agent_id)
        MEMORY_INSTANCE.delete_all(**params)
        logger.info(f"All memories deleted for identifiers: {params}")
        return {"message": "All relevant memories deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in delete_all_memories:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete memories: {str(e)}",
        )


@app.post("/reset", summary="Reset all memories", status_code=status.HTTP_200_OK)
def reset_memory() -> Dict[str, str]:
    """Completely reset stored memories."""
    try:
        MEMORY_INSTANCE.reset()
        logger.info("All memories reset successfully")
        return {"message": "All memories reset"}
    except Exception as e:
        logger.exception("Error in reset_memory:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset memories: {str(e)}",
        )


@app.get("/token_count", summary="Get token count", status_code=status.HTTP_200_OK)
def get_token_count_endpoint() -> Dict[str, Dict[str, int]]:
    """Get token count statistics."""
    return {"token_count": async_token_tracker.get_detailed_stats()}


@app.post(
    "/reset_token_count",
    summary="Reset token count",
    status_code=status.HTTP_200_OK,
)
def reset_token_count() -> Dict[str, str]:
    """Reset token count statistics."""
    async_token_tracker.reset()
    logger.info("Token count reset successfully")
    return {"message": "Token count reset"}


@app.get("/health", summary="Health check", status_code=status.HTTP_200_OK)
def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": CONFIG_VERSION,
        "database_provider": DATABASE_PROVIDER,
        "llm_provider": LLM_PROVIDER,
        "embedding_provider": EMBEDDING_PROVIDER,
    }
