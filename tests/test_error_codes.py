
import pytest
from error_codes import ErrorCodes

def test_file_not_found_error_code():
    assert ErrorCodes.FILE_NOT_FOUND.value == 7
    assert ErrorCodes.FILE_NOT_FOUND.name == "FILE_NOT_FOUND"
