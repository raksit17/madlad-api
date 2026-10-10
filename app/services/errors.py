"""Errors shared by MADLAD and experimental translation providers."""


class InputTooLongError(Exception):
    pass


class BatchTooLargeError(Exception):
    pass


class TranslationBackendError(Exception):
    """The configured upstream translation provider is unavailable or failed."""

    pass
