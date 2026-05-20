class LearningPipelineError(Exception):
    pass


class InsufficientDataError(LearningPipelineError):
    pass


class PolicyNotTrainedError(LearningPipelineError):
    pass


class ExecutionError(Exception):
    pass


class RateLimitExceededError(ExecutionError):
    pass


class CircuitBreakerOpenError(ExecutionError):
    pass


class ConfidenceTooLowError(ExecutionError):
    pass
