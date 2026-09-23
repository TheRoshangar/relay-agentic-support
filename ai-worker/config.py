from decouple import config

GEMINI_API_KEY = config("GEMINI_API_KEY")
GEMINI_MODEL = config("GEMINI_MODEL")
GEMINI_FALLBACK_MODEL = config("GEMINI_FALLBACK_MODEL", default="")

LANGFUSE_PUBLIC_KEY = config("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = config("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = config("LANGFUSE_HOST", default="https://cloud.langfuse.com")

RABBITMQ_HOST = config("RABBITMQ_HOST", default="rabbitmq")
RABBITMQ_PORT = config("RABBITMQ_PORT", default=5672, cast=int)
RABBITMQ_USER = config("RABBITMQ_USER", default="guest")
RABBITMQ_PASSWORD = config("RABBITMQ_PASSWORD", default="guest")

TAVILY_API_KEY = config("TAVILY_API_KEY")

CHROMA_HOST = config("CHROMA_HOST", default="chromadb")

DB_HOST = config("DB_HOST", default="postgres")
DB_PORT = config("DB_PORT", default=5432, cast=int)
DB_NAME = config("DB_NAME")
DB_USER = config("DB_USER")
DB_PASSWORD = config("DB_PASSWORD")