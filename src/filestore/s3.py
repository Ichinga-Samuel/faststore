"""
Amazon S3 storage for FastAPI. This module contains the S3Storage class which is used to upload files to Amazon S3.
"""
from logging import getLogger

from .main import FileStore
from .storage_engines.s3_engine import S3Engine

logger = getLogger(__name__)


class S3Storage(FileStore):
    """
    Amazon S3 storage for FastAPI.

    Properties:
        client (boto3.client): The S3 client.
    """
    StorageEngine = S3Engine
