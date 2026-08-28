class LLMError(RuntimeError):
    """The configured language-model service could not produce a response."""


class SchemaValidationError(LLMError):
    """Structured data did not satisfy the required product schema."""


class StructuredOutputError(SchemaValidationError):
    """The language-model response was invalid for the requested schema."""


class GroundingError(StructuredOutputError):
    """A purported fact was not supported by verbatim article evidence."""


class TTSError(RuntimeError):
    """Vietnamese speech synthesis or WAV validation failed."""
