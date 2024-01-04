# FileStore
![GitHub](https://img.shields.io/github/license/ichinga-samuel/faststore?style=plastic)
![GitHub issues](https://img.shields.io/github/issues/ichinga-samuel/faststore?style=plastic)
![PyPI](https://img.shields.io/pypi/v/filestore)
![passing](https://img.shields.io/github/actions/workflow/status/ichinga-samuel/faststore/master.yaml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads)
## Introduction
Simple file storage dependency for FastAPI. Makes use of FastAPI's dependency injection system to provide a simple way
to handle files. Inspired by Multer it allows both single and multiple file uploads through different fields with a 
simple interface. Comes with a default implementation for local file storage, in-memory storage and AWS S3
storage but can be easily extended to support other storage systems.

## Installation

```bash 
pip install filestore

# to use aws s3 storage
pip install filestore[s3]
```
## Usage

```python
from fastapi import FastAPI, File, UploadFile, Depends
from filestore import LocalStorage, Store

app = FastAPI()

# local storage instance for single file upload
loc = LocalStorage(name='book', required=True)

# local storage instance for multiple file upload with a maximum of 2 files from a single field
loc2 = LocalStorage(name='book', required=True, count=2)

# local storage instance for multiple file uploads from different fields
multiple_local = LocalStorage(fields=[{'name': 'author', 'max_count': 2}, {'name': 'book', 'max_count': 1}])


@app.post('/upload_book')
async def upload_book(book=Depends(loc), model=Depends(loc.model)) -> Store:
    return book.store


@app.post('/local_multiple', name='upload', openapi_extra={'form': {'multiple': True}})
async def local_multiple(model=Depends(multiple_local.model), loc=Depends(multiple_local)) -> Store:
    return loc.store
```

## API
FastStore Instantiation. All arguments are keyword arguments.

### FastStore
The base class for building a file storage service. This base class and must be inherited from for custom file
storage services. The upload methods must be implemented in a child class. This class implements a callable instance
makes dependency injection possible.

**\_\_init\_\_**
```python
def __init__(name: str = '', count: int = 1, required: bool = False, fields: list[FileField] = None,
             config: Config = None)
```
Instantiates a FastStore object. All arguments are key word arguments with defaults
**Parameters:**

|Name|Type|Description|Default|
|---|---|---|---|
|`name`|`str`|The name of the file field to expect from the form for a single field upload|`''`|
|`count`|`int`|The maximum number of files to accept for a single field upload|`1`|
|`required`|`bool`|Set as true if the field defined in name is required|`False`|
|`fields`|`list[FileField]`|A list of fields to expect from the form. Usually for multiple file uploads from different fields|`None`|
|`config`|`Config`|The Config dictionary|`None`|

**Note:**
If you provide both name and fields arguments the two are merged together with the name argument taking precedence if there is a name clash.\

**FileField**\
A dictionary representing form fields. 

|Key|Type|Description|Note|
|---|---|---|---|
|`name`|`str`|The name of the field|Required|
|`count`|`int`|The maximum number of files to expect|Defaults to 1|
|`required`|`bool`|Set as true if the field is required|Defaults to false|
|`config`|`Config`|A config dict for individual field|Optional|

**Config**\
The config dictionary is to be passed to faststore class during instantiation or added to individual file field dict

| Key           | Type                                                      | Description                                                                                                                         | Note                                      |
|---------------|-----------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------|
| `storage`     | `StorageEngine`                                           | Storage engine for handling file uploads.                                                                                           | `LocalEngine`, `S3Engine`, `MemoryEngine` |
| `dest`        | `str\|Path`                                               | The path to save the file relative to the current working directory. Defaults to uploads. Specifying destination will override dest | LocalStorage and S3Storage                |
| `destination` | `Callable[[Request, Form, str, UploadFile], str \| Path]` | A destination function for saving the file                                                                                          | Local and Cloud Storage                   |
| `filter`      | `Callable[[Request, Form, str, UploadFile], bool]`        | Remove unwanted files                                                                                                               |
| `max_files`   | `int`                                                     | The maximum number of files to expect. Defaults to 1000                                                                             | Not applicable to FileField config dict   |
| `max_fields`  | `int`                                                     | The maximum number of file fields to expect. Defaults to 1000                                                                       | Not applicable in FileField config dict   |
| `filename`    | `Callable[[Request, Form, str, UploadFile], UploadFile]`  | A function for customizing the filename                                                                                             | Local and Cloud Storage                   |
| `background`  | `bool`                                                    | If true run the storage operation as a background task                                                                              | Local and Cloud Storage                   |
| `extra_args`  | `dict`                                                    | Extra arguments for AWS S3 Storage                                                                                                  | S3Storage                                 |
| `bucket`      | `str`                                                     | Name of storage bucket for cloud storage                                                                                            | Cloud Storage                             |
| `region`      | `str`                                                     | Name of region for cloud storage                                                                                                    | Cloud Storage                             |

**Attributes**

| name             | type                  | description                                                            |
|------------------|-----------------------|------------------------------------------------------------------------|
| fields           | `list[FileField]`     | A list of FileField objects                                            |
| config           | `Config`              | The config dictionary                                                  |
| form             | `FormData`            | The form object                                                        |
| request          | `Request`             | The request object                                                     |
| store            | `Store`               | The result of the file storage operation                               |
| file_count       | `int`                 | The total number of files in the form                                  |
| engine           | `StorageEngine`       | The StorageEngine object for handling uploads                          | 
| StorageEngine    | `Type[StorageEngine]` | The StorageEngine class for handling uploads                           |
| background_tasks | `BackgroundTasks`     | The background task object for running storage tasks in the background |


**\_\_call\_\_**
```python
async def __call__(req: Request, bgt: BackgroundTasks) -> FastStore
```
This method allows you to use a FastStore instance as a dependency for your route function. It sets the result
of the file storage operation and returns an instance of the class.

**model**\
The model property dynamically generates a pydantic model for the FastStore instance. This model can be used as a
dependency for your path function. It is generated based on the fields attribute. It is useful for validating the form
fields and for API documentation. Using this property in your path function will enable SwaggerUI generate the
appropriate form fields

**store**
```python
@store.setter
def store(self, value: FileData)
```
The store property gets and sets the result of the file storage operation. The setter method accepts
a FileData object while the getter method returns a Store object. Any implementation of upload should use this to set
the result of the file storage operation.

**upload**
```python
@abstractmethod
async def upload(self, *, file_field: FileField)
```
This method is an abstract method and must be implemented in a child class. It is used for uploading a single file

**multi_upload**
```python
@abstractmethod
async def multi_upload(self, *, file_fields: list[FileField])
```
This method is an abstract method and must be implemented in a child class. It is used for uploading multiple files

### FileData
This pydantic model represents the result of an individual file storage operation.

|Name|Type|Description|Note|
|---|---|---|---|
|`path`|`str`|The path to the file for local storage|Local Storage|
|`url`|`str`|The url to the file for cloud storage|Cloud Storage|
|`status`|`bool`|The status of the file storage operation|Defaults to true|
|`content_type`|`bool`|The content type of the file|
|`filename`|`str`|The name of the file|
|`size`|`int`|The size of the file|
|`file`|`bytes`|The file object for memory storage|Memory Storage|
|`field_name`|`str`|The name of the form field|
|`metadata`|`dict`|Extra metadata of the file|
|`error`|`str`|The error message if the file storage operation failed|
|`message`|`str`|Success message if the file storage operation was successful|

### Store Class
The response model for the FastStore class. A pydantic model.

|Name|Type|Description|
|---|---|---|
|`file`|`FileData \| None`|The result of a single file upload or storage operation|
|`files`|`Dict[str, List[FileData]]`|The result of multiple file uploads or storage operations|
|`failed`|`Dict[str, List[FileData]]`|The results of a failed file upload or storage operation|
|`error`|`str`|The error message if the file storage operation failed|
|`message`|`str`|Success message if the file storage operation was successful|

**\_\_len\_\_**
```python
def __len__(self) -> int
```
Use the len(obj) function to get the total number of successful file uploads or storage operations.

**Sample Store Object**\
A sample Store object for multiple files uploads in two fields (books and authors).
```json
{
    "file": null,
    "files": {
        "books": [
        {
            "path": "/home/user/test_data/uploads/books/book1.pdf",
            "status": true,
            "content_type": "application/pdf",
            "filename": "book1.pdf",
            "size": 1000,
            "field_name": "books",
            "metadata": {},
            "message": "File uploaded successfully"
        },
        {
            "path": "/home/user/test_data/uploads/books/book2.pdf",
            "status": true,
            "content_type": "application/pdf",
            "filename": "book2.pdf",
            "size": 1000,
            "field_name": "books",
            "metadata": {},
            "message": "File uploaded successfully"
        }
        ],
        "authors": [
        {
            "path": "/home/user/test_data/uploads/authors/author1.png",
            "status": true,
            "content_type": "application/png",
            "filename": "author1.png",
            "size": 1000,
            "field_name": "authors",
            "metadata": {},
            "message": "File uploaded successfully"
        },
        {
            "path": "/home/user/test_data/uploads/authors/author2.png",
            "status": true,
            "content_type": "application/png",
            "filename": "author2.png",
            "size": 1000,
            "field_name": "authors",
            "metadata": {},
            "message": "File uploaded successfully"
        }
        ]
    },
    "failed": {},
    "error": "",
    "message": "Files uploaded successfully"
}
```

### Configuration Functions.
These are functions that can be passed to either the config parameter of the FastStore class or the config 'key' of
the FileField dictionary. They are used for customizing the file storage operation. They have the same signature but
different return types.

#### Destination function
A destination function can be passed to the LocalStorage and S3Storage config parameter 'destination' to create a 
destination for the files in a forms. It can also be passed to the FileField config parameter 'destination' to create a
destination for a single file field.
The function should return a path or string object.

```python
# A destination function
def local_destination(req: Request, form: FormData, field: str, file: UploadFile) -> Path:
    path = Path.cwd() / f'test_data/uploads/{field}'
    path.mkdir(parents=True, exist_ok=True) if not path.exists() else ...
    return path / f'{file.filename}'
```

#### Filename function
This function modifies the filename attribute of the UploadFile object and returns the modified object.
```python
# A filename function
def local_filename(req: Request, form: FormData, field: str, file: UploadFile) -> UploadFile:
    file.filename = f'local_{file.filename}'
    return file
```

#### Filtering
Set a rule for filtering out unwanted files.
```python
# A filter function that only allows files with .txt extension
def book_filter(req: Request, form: FormData, field: str, file: UploadFile) -> bool:
    return file.filename and file.filename.endswith('.txt')
```

#### Example
```python
# initiate a local storage instance with a destination function, a filename function and a filter function.
loc = LocalStorage(
    fields = [{'name': 'book', 'max_count': 2, 'required': True, 'config': {'filter': book_filter}}, {'name': 'image', 'max_count': 2}],
    config={
        'destination': local_destination,
        'filename': local_filename,
    }
)

@app.post('/upload')
# Adding the model parameter to the path function will generate form fields on the swagger ui and openapi docs.
# That can be used to validate the form fields. It does not affect the file storage operation and can be omitted.
async def upload(model=Depends(loc.modle), form: Form = Depends(loc)) -> Store:
    return loc.store
```
### Swagger UI and OpenAPI 
Adding the model property of the faststore instance as a parameter to the route function will add a pydantic model
generated from the form fields to the swagger ui and openapi docs. This just for validation and documentation and does
not actually affect the file storage operation. It can be omitted.

### Error Handling.
Any error that occurs is caught and passed to the error attribute of the FileData class and the status attribute
is set to false indicating a failed operation. The resulting FileData object is added to the *failed* attribute of the
*store* property of the FastStore instance. The error message is also added to the *error* attribute of the *store*

### File Storage Classes
All storage class inherit from the base FastStore class. This class implements the upload and multi_upload methods with a specialized storage engine. The following storage classes are available.


### LocalStorage
This class handles local file storage to the disk.

### S3Storage
This class handles cloud storage to AWS S3. When using this class ensure that the following environment variables
are set. Any extra parameters is passed to the extra_args dict of the config dict.
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`: This is optional as you can specify the region in the config.
- `AWS_BUCKET_NAME`: This is optional as you can specify the bucket name in the config.

```python   
from filestore import S3Storage
s3 = S3Storage(fields=[{'name': 'book', 'max_count': 2, 'required': True}, {'name': 'image', 'max_count': 2}],
               config={'region': 'us-east-1', 'bucket': 'my-bucket', extra_args={'ACL': 'public-read'}})
```

### MemoryStorage
This class handles memory storage. It stores the file in memory and returns the file object in the store object as 
a bytes object.

### Custom Storage Class
You can build your own storage class by inheriting from the FastStore class and implementing the upload and/or multi_uploads.
You can use an inbuilt instance of the StorageEngine class or build your own storage engine class.

### Storage Engine
This is the base class for building a storage engine. It implements the upload and multi_upload methods.
It is an abstract class and must be inherited from. Storage engines are used by the storage classes to handle file uploads.
The following storage engines are available.

### LocalEngine
This class handles local file storage to the disk.

### S3Engine
This class handles cloud storage to AWS S3. When using this class ensure that the appropriate environment variables as specified in the S3 Storage service class are available.

### Build your own storage engine
You can build your own storage class by inheriting from the Storage engine class and implementing the **upload** and 
**multiple_upload** methods. 

### MemoryEngine
This class handles memory storage. It stores the file in memory as a bytes object.

### Background Tasks
You can run the file storage operation as a background task by setting the background key in the config parameter
to True in either the object instance config parameter or the FileField config dict.

### FileStore Class
With the filestore class you can use multiple storage engines to handle file uploads for a single form. This can be done by specifying a 
storage engine in the config parameter the FileField dict. That is to say you can upload a file to local storage and another to cloud storage with same form

```python
from filestore import FileStore, LocalEngine, S3Engine
filestore = FileStore(fields=[{'name': 'books', 'max_count': 2, 'storage': LocalEngine,
                               'config': {'destination': 'test_data/uploads/Books', 'filter': book_filter}},
                              {'name': 'covers', 'max_count': 2, 'storage': S3Engine, 'config': {'destination': 'Covers',
                                                                                            'background': True,
                                                                                            'filter': image_filter}}])
```