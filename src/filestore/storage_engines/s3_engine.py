"""AWS S3 storage for FastAPI. This module contains the S3Storage class which is used to upload files to Amazon S3."""

import os
import asyncio
from typing import BinaryIO, TypeVar
from urllib.parse import quote as urlencode
from logging import getLogger
from functools import cache

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from ..datastructures import FileField, UploadFile, FileData
from .storage_engine import StorageEngine

logger = getLogger(__name__)

S3 = TypeVar("S3", bound=BaseClient)


class S3Engine(StorageEngine):
    """Amazon S3 storage for FastAPI.

    Properties:
        client (boto3.client): The S3 client.
    """

    @staticmethod
    @cache
    def client(default_region = "") -> S3:
        """
        Get the S3 client. Make sure the AWS credentials are set in the environment variables.
        This property is cached.

        Returns:
            boto3.client: The S3 client.
        """
        key_id = os.environ.get("AWS_ACCESS_KEY_ID")
        access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        region_name = default_region or os.environ.get("AWS_DEFAULT_REGION")
        return boto3.client('s3', region_name=region_name, aws_access_key_id=key_id, aws_secret_access_key=access_key)

    @staticmethod
    async def _upload(*, client: S3, file_obj: BinaryIO, bucket: str, obj_name: str, extra_args: dict) -> dict:
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
        return await asyncio.to_thread(client.put_object, Body=file_obj, Bucket=bucket, Key=obj_name, **extra_args)

    @staticmethod
    def _background_upload(*, client: S3, file_obj: BinaryIO, bucket: str, obj_name: str,
                                 extra_args: dict):
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
        # with open(file_obj.read(), "rb") as data:
        try:
            with file_obj as f:
                client.put_object(Body=f, Bucket=bucket, Key=obj_name, **extra_args)
        except Exception as e:
            print(e)

    # noinspection PyTypeChecker
    async def upload(self, file_field: FileField, file: UploadFile) -> FileData:
        """Upload a file to the destination of the S3 bucket.

        Args:
            file_field (FileField): A file Field dict.
            file (UploadFile): The file object to upload.

        Returns:
            FileData: The file data.
        """
        try:
            config = file_field.config
            dest = config.get("destination")
            object_name = dest(self.request, self.form, file_field.name, file) if callable(dest) else \
                (f"{dest}/{file.filename}" if dest else file.filename)
            bucket = config.get("AWS_BUCKET_NAME", os.environ.get("AWS_BUCKET_NAME"))
            region = config.get("AWS_DEFAULT_REGION", os.environ.get("AWS_DEFAULT_REGION"))
            extra_args = config.get("extra_args", {})
            msg, meta = "", {}
            client = self.client(default_region=region)
            if config.get("background"):
                print("using background task")
                try:
                    res = None
                    try:
                        ...
                    except Exception as e:
                        print(e, 'reading file failed')
                    print(res, type(res))
                    client.put_object(Body=res, Bucket=bucket, Key=object_name, **extra_args)
                    # client.upload_fileobj(file.file, bucket, object_name, ExtraArgs=extra_args)
                except Exception as e:
                    print('dfbf', e)
                # self.background_tasks.add_task(self._background_upload, client=client, file_obj=file.file, bucket=bucket,
                #                                obj_name=object_name, extra_args=extra_args)
                # print('after background task', file.filename)
                # msg = f"{file.filename} uploading in background"
            else:
                print('uploading file?')
                res = await self._upload(client=client,file_obj=file.file, bucket=bucket, obj_name=object_name,
                                         extra_args=extra_args)
                if (meta := res.get('ResponseMetadata', {})).get('HTTPStatusCode', 0) == 200:
                    msg = f"{file.filename} successfully uploaded"
                else:
                    msg = f"Error uploading {file.filename}"
            url = f"https://{bucket}.s3.{region}.amazonaws.com/{urlencode(object_name.encode('utf8'))}"
            return FileData(filename=file.filename, size=file.size, content_type=file.content_type,
                            field_name=file_field.name, url=url, message=msg, metadata=meta)
        except Exception as err:
            logger.error(f"Error uploading file: {err} in {self.__class__.__name__}")
            return FileData(status=False, message="No files uploaded")
