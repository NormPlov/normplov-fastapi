from fastapi import HTTPException


class FileError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class FileNotFoundError(FileError):
    def __init__(self, file_path: str):
        super().__init__(f"File not found: {file_path}")


class FileExtensionError(FileError):
    def __init__(self, allowed_extensions: list[str]):
        allowed = ", ".join(allowed_extensions)
        super().__init__(f"Invalid file extension. Allowed extensions: {allowed}")


class FileSizeError(FileError):
    def __init__(self, max_size: int):
        super().__init__(f"File size exceeds the maximum limit of {max_size} bytes.")


class FileUploadError(FileError):
    def __init__(self, reason: str):
        super().__init__(f"File upload failed: {reason}")


def handle_file_error(exc: FileError):

    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=exc.message)
    elif isinstance(exc, FileExtensionError):
        return HTTPException(status_code=400, detail=exc.message)
    elif isinstance(exc, FileSizeError):
        return HTTPException(status_code=413, detail=exc.message)
    elif isinstance(exc, FileUploadError):
        return HTTPException(status_code=500, detail=exc.message)
    else:
        return HTTPException(status_code=500, detail="An unknown file error occurred.")
