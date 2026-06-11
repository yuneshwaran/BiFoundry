import os
from pathlib import Path
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().with_name(".env"))


# Core service configuration
DATABASE_URL = os.getenv("DATABASE_URL")
DEFAULT_PROJECT_NAME = os.getenv("DEFAULT_PROJECT_NAME", "MyProject")
PBIP_SCHEMA_URL = os.getenv(
    "PBIP_SCHEMA_URL",
    "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
)

# Output and work directories
OUTPUT_ROOT = os.getenv("OUTPUT_ROOT", "output_pbip")
WORK_ROOT = os.getenv("WORK_ROOT", ".work")

# API metadata
API_TITLE = os.getenv("API_TITLE", "Metadash PBIP Service")
API_VERSION = os.getenv("API_VERSION", "1.0.0")

# Power BI OAuth configuration
POWER_BI_TENANT_ID = os.getenv("POWER_BI_TENANT_ID", "common")
POWER_BI_CLIENT_ID = os.getenv("POWER_BI_CLIENT_ID", "")
POWER_BI_CLIENT_SECRET = os.getenv("POWER_BI_CLIENT_SECRET")
POWER_BI_REDIRECT_URI = os.getenv("POWER_BI_REDIRECT_URI", "http://localhost:8000/api/powerbi/auth/callback")
POWER_BI_SCOPES = os.getenv(
    "POWER_BI_SCOPES",
    "openid profile offline_access https://analysis.windows.net/powerbi/api/Workspace.Read.All https://analysis.windows.net/powerbi/api/Dataset.Read.All",
)
POWER_BI_API_BASE = os.getenv("POWER_BI_API_BASE", "https://api.powerbi.com/v1.0/myorg")
POWER_BI_AUTHORITY_BASE = os.getenv("POWER_BI_AUTHORITY_BASE", "https://login.microsoftonline.com")
POWER_BI_CLIENT_RETURN_URL = os.getenv("POWER_BI_CLIENT_RETURN_URL", "http://localhost:3000/")

if not DATABASE_URL:
    raise Exception("DATABASE_URL missing")
