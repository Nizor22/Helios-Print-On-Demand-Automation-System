"""
Google Cloud Services Package
Provides integration with various Google Cloud services
"""

from .vertex_ai_client import VertexAIClient
from .storage_client import CloudStorageClient
from .firestore_client import FirestoreClient
# Temporarily disabled - packages not installed:
# from .functions_client import CloudFunctionsClient
# from .pubsub_client import PubSubClient
# from .secret_manager import GoogleSecretManagerClient
from .drive_client import GoogleDriveClient
from .sheets_client import GoogleSheetsClient

__all__ = [
    "VertexAIClient",
    "CloudStorageClient", 
    "FirestoreClient",
    # "CloudFunctionsClient",  # Temporarily disabled
    # "PubSubClient",  # Temporarily disabled
    # "GoogleSecretManagerClient",  # Temporarily disabled
    "GoogleDriveClient",
    "GoogleSheetsClient"
]
