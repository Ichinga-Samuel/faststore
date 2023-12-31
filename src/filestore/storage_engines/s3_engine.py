"""AWS S3 storage for FastAPI. This module contains the S3Storage class which is used to upload files to Amazon S3."""

import os
import asyncio
from typing import BinaryIO
from urllib.parse import quote as urlencode
from logging import getLogger
from functools import cache

import boto3

from ..exceptions import FileStoreError
from ..structs import FileField, UploadFile, FileData
from .storage_engine import StorageEngine

logger = getLogger(__name__)


class S3Engine(StorageEngine):
    """Amazon S3 storage for FastAPI.

    Properties:
        client (boto3.client): The S3 client.
    """

    @property
    @cache
    def client(self):
        """
        Get the S3 client. Make sure the AWS credentials are set in the environment variables.
        This property is cached.

        Returns:
            boto3.client: The S3 client.
        """
        key_id = os.environ.get('AWS_ACCESS_KEY_ID')
        access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        region_name = os.environ.get('AWS_DEFAULT_REGION') or self.config.get('region')
        return boto3.client('s3', region_name=region_name, aws_access_key_id=key_id, aws_secret_access_key=access_key)

    async def _upload(self, *, file_obj: BinaryIO, bucket: str, obj_name: str, extra_args: dict) -> dict:
        """
        Private method to upload the file to the destination. This method is called by the upload method.

        Args:
            file_obj (BinaryIO): The file object to upload.
            bucket (str): The name of the bucket to upload the file to.
            obj_name (str): The name of the object.
            extra_args (dict): Extra arguments to pass to the put_object method.

        Returns:
            None: Nothing is returned.
        """
        return await asyncio.to_thread(self.client.put_object, Body=file_obj, Bucket=bucket, Key=obj_name, **extra_args)

    async def _background_upload(self, *, file_obj: BinaryIO, bucket: str, obj_name: str,
                                 extra_args: dict) -> UploadFile:
        """
        Private method to upload the file to the destination. This method is called by the upload method for background
        tasks. Uses upload_fileobj method to upload the file. This allows the file to be uploaded in chunks.

        Args:
            file_obj (BinaryIO): The file object to upload.
            bucket (str): The name of the bucket to upload the file to.
            obj_name (str): The name of the object.
            extra_args (dict): Extra arguments to pass to the put_object method.

        Returns:
            None: Nothing is returned.
        """
        return await asyncio.to_thread(self.client.upload_fileobj, file_obj, bucket, obj_name, ExtraArgs=extra_args)

    # noinspection PyTypeChecker
    async def upload(self, *, file_field: FileField = None) -> FileData:
        """Upload a file to the destination of the S3 bucket.

        Args:
            file_field (FileField): A file Field dict.

        Returns:
            None: Nothing is returned.
        """
        try:
            self.file_field = file_field
            field_name, file = self.file_field['name'], self.file_field['file']
            dest = self.config.get('destination', '')
            object_name = dest(self.request, self.form, field_name, file) if callable(dest) else \
                (f'{dest}/{file.filename}' if dest else file.filename)
            bucket = self.config.get('bucket') or os.environ.get('AWS_BUCKET_NAME')
            region = self.config.get('region') or os.environ.get('AWS_DEFAULT_REGION')
            extra_args = self.config.get('extra_args', {})
            msg, meta = '', {}
            if self.config.get('background'):
                self.background_tasks.add_task(self._background_upload, file_obj=file.file, bucket=bucket,
                                               obj_name=object_name, extra_args=extra_args)
                msg = f'{file.filename} uploading in background'
            else:
                res = await self._upload(file_obj=file.file, bucket=bucket, obj_name=object_name,
                                         extra_args=extra_args)
                if (meta := res.get('ResponseMetadata', {})).get('HTTPStatusCode', 0) == 200:
                    msg = f'{file.filename} successfully uploaded'
                else:
                    msg = f'Error uploading {file.filename}'
            url = f"https://{bucket}.s3.{region}.amazonaws.com/{urlencode(object_name.encode('utf8'))}"
            return FileData(filename=file.filename, size=file.size, content_type=file.content_type,
                            field_name=field_name, url=url, message=msg, metadata=meta)
        except Exception as err:
            logger.error(f'Error uploading file: {err} in {self.__class__.__name__}')
            raise FileStoreError(err)