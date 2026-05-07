from langfuse import Langfuse
from config.settings import settings


def create_langfuse_client() -> Langfuse:
    """Create Langfuse client from settings. Returns disabled client if keys not configured."""
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        return Langfuse(enabled=False)

    return Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST,
    )


langfuse = create_langfuse_client()


def flush_langfuse():
    """Flush pending Langfuse events. Call on application shutdown."""
    try:
        langfuse.flush()
    except Exception:
        pass
