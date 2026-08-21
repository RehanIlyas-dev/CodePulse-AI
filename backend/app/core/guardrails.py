from fastapi import HTTPException, UploadFile, status

MAX_CODE_LENGTH_BYTES = 500 * 1024  # 500 KB 
MAX_ZIP_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB 
MAX_LINE_LENGTH_CHARACTERS = 1000  # Guard against minified code by checking line lengths

class PayloadGuardrails:
    @staticmethod
    def validate_code_snippet(code: str) -> None:
        
        # --> Validate code snippet size and detect minified code
        code_bytes = code.encode("utf-8")
        if len(code_bytes) > MAX_CODE_LENGTH_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Payload size limit exceeded. Maximum code size allowed is 500 KB."
            )

        # Detect minified code bundles by checking line lengths
        lines = code.splitlines()
        for line in lines[:50]:  # Inspect first 50 lines
            if len(line) > MAX_LINE_LENGTH_CHARACTERS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Minified code detected. Please submit unminified source code."
                )

    @staticmethod
    def validate_zip_upload(file: UploadFile) -> None:
        # --> Validate uploaded zip file size and type
        if not file.filename or not file.filename.endswith(".zip"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported media type. Only .zip file archives are accepted."
            )

        # Measure file size via stream pointer seek without reading full payload into RAM
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        if file_size > MAX_ZIP_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Archive size limit exceeded. Maximum zip size allowed is 10 MB."
            )