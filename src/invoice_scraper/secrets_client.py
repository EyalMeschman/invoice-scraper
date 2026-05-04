import logging
import os

from google.cloud import secretmanager

from invoice_scraper.utils import get_project_root


class GoogleSecretsClient:
    """Wrapper for Google Secret Manager client."""

    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_PATH")
        if credentials_path:
            full_path = os.path.join(get_project_root(), credentials_path)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = full_path
        self.client = secretmanager.SecretManagerServiceClient()

    def get_secret(self, secret_name: str, version: str = "latest") -> str:
        name = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
        response = self.client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
