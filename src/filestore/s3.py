# """Amazon S3 storage for FastAPI. This module contains the S3Storage class which is used to upload files to Amazon S3.
# """
# from logging import getLogger
#
# from .main import FastStore
# from .structs import FileData, FileField
# from .exceptions import FileStoreError
# from .storage_engines.s3_engine import S3Engine
#
# logger = getLogger(__name__)
#
#
# class S3Storage(FastStore):
#     """
#     Amazon S3 storage for FastAPI.
#
#     Properties:
#         client (boto3.client): The S3 client.
#     """
#     StorageEngine = S3Engine
#
#     # noinspection PyTypeChecker
#     async def upload(self, *, file_field: FileField):
#         """Upload a file to the destination of the S3 bucket.
#
#         Args:
#             file_field (FileField): The file field to upload.
#
#         Returns:
#             None: Nothing is returned.
#         """
#         try:
#             file_data = await self.engine.upload(file_field=file_field)
#             self.store = file_data
#         except FileStoreError as err:
#             logger.error(f'Error uploading file: {err} in {self.__class__.__name__}')
#             self.store = FileData(status=False, error='Something went wrong', field_name=file_field['name'],
#                                   message=f'Unable to upload {file_field["name"]}')