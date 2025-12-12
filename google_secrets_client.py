import logging
import os
from dotenv import load_dotenv
from google.cloud import secretmanager
from utils import get_project_root

load_dotenv(".env.defaults")
load_dotenv(".env", override=True)


class GoogleSecretsClient:
    """Wrapper for Google Secret Manager client."""

    def __init__(self, logger: logging.Logger):
        """
        Initialize Secret Manager client.
        """
        # Set up authentication
        self._logger = logger
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_PATH")
        if credentials_path:
            full_path = os.path.join(get_project_root(), credentials_path)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = full_path
        self.client = secretmanager.SecretManagerServiceClient()

    def get_secret(self, secret_name: str, version: str = "latest") -> str:
        """
        Retrieve a secret from Google Secret Manager.
        """
        # Build the resource name
        name = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"

        # Access the secret version
        response = self.client.access_secret_version(request={"name": name})

        # Decode the secret payload
        secret_value = response.payload.data.decode("UTF-8")

        return secret_value
