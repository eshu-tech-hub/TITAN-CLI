class PipelineError(Exception):
    """Base exception for pipeline engine failures."""


class PipelineValidationError(PipelineError, ValueError):
    """Raised when pipeline input or configuration is invalid."""


class PipelineStageError(PipelineError):
    """Raised when a pipeline stage encounters an error."""


class PipelineAbortedError(PipelineError):
    """Raised when pipeline execution is aborted by user or hook."""


class PipelineExecutionError(PipelineError):
    """Base for execution-level pipeline errors."""


class PipelineRecoverableError(PipelineExecutionError):
    """Raised when a stage fails but may succeed on retry."""


class PipelineFatalError(PipelineExecutionError):
    """Raised when a stage fails and pipeline cannot continue."""


class PipelineBrokerError(PipelineExecutionError):
    """Raised when a broker interaction fails during pipeline execution."""


class PipelineTimeoutError(PipelineExecutionError):
    """Raised when a pipeline stage exceeds its time limit."""
