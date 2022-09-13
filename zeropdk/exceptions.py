class ZeroPDKWarning(UserWarning):
    """Warning related to the usage of ZeroPDK. The responsibility falls on the user to fix these warnings."""


class ZeroPDKUserError(Exception):
    """Exception resulting from impossible design inputs for ZeroPDK."""
