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


class AlignmentError(RuntimeError):
    """Word alignment or subtitle generation failed safely."""


class RenderError(RuntimeError):
    """Article-asset scene or final video rendering failed."""


class VisualGenerationError(RuntimeError):
    """An optional visual provider failed without invalidating project data."""
