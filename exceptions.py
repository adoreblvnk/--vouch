class CustomValidationError(Exception):
    """base class for custom exceptions."""
    pass


class UnsupportedFileFormat(CustomValidationError):
    """raised when file is not in the list of supported file formats to be converted into picture format."""
    pass


class TotalKeywordNotFound(CustomValidationError):
    """raised when total keyword is not found in list / raw document."""
    pass


class TotalAmountNotFound(CustomValidationError):
    """raised when total amount (in float type) is not found in list / raw document."""
    pass
