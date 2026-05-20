import pytest
from app.core.exceptions import (
    LearningPipelineError,
    InsufficientDataError,
    PolicyNotTrainedError,
    ExecutionError,
    RateLimitExceededError,
    CircuitBreakerOpenError,
    ConfidenceTooLowError,
)


class TestInheritance:
    def test_insufficient_data_inherits_from_learning_pipeline(self):
        assert issubclass(InsufficientDataError, LearningPipelineError)

    def test_policy_not_trained_inherits_from_learning_pipeline(self):
        assert issubclass(PolicyNotTrainedError, LearningPipelineError)

    def test_rate_limit_inherits_from_execution(self):
        assert issubclass(RateLimitExceededError, ExecutionError)

    def test_circuit_breaker_inherits_from_execution(self):
        assert issubclass(CircuitBreakerOpenError, ExecutionError)

    def test_confidence_too_low_inherits_from_execution(self):
        assert issubclass(ConfidenceTooLowError, ExecutionError)

    def test_learning_and_execution_are_separate_hierarchies(self):
        assert not issubclass(ExecutionError, LearningPipelineError)
        assert not issubclass(LearningPipelineError, ExecutionError)

    def test_all_exceptions_inherit_from_exception(self):
        for exc in [
            LearningPipelineError, InsufficientDataError, PolicyNotTrainedError,
            ExecutionError, RateLimitExceededError, CircuitBreakerOpenError,
            ConfidenceTooLowError,
        ]:
            assert issubclass(exc, Exception)


class TestCatchBase:
    def test_catch_learning_base_catches_insufficient_data(self):
        with pytest.raises(LearningPipelineError):
            raise InsufficientDataError("not enough data")

    def test_catch_learning_base_catches_policy_not_trained(self):
        with pytest.raises(LearningPipelineError):
            raise PolicyNotTrainedError("policy not trained")

    def test_catch_execution_base_catches_rate_limit(self):
        with pytest.raises(ExecutionError):
            raise RateLimitExceededError("too many requests")

    def test_catch_execution_base_catches_circuit_breaker(self):
        with pytest.raises(ExecutionError):
            raise CircuitBreakerOpenError("circuit open")

    def test_catch_execution_base_catches_confidence_too_low(self):
        with pytest.raises(ExecutionError):
            raise ConfidenceTooLowError("confidence too low")

    def test_exception_catches_all_custom_exceptions(self):
        for exc_cls in [
            InsufficientDataError, PolicyNotTrainedError,
            RateLimitExceededError, CircuitBreakerOpenError,
            ConfidenceTooLowError,
        ]:
            try:
                raise exc_cls("test")
            except Exception:
                pass

    def test_message_is_preserved(self):
        for exc_cls in [
            InsufficientDataError, PolicyNotTrainedError,
            RateLimitExceededError, CircuitBreakerOpenError,
            ConfidenceTooLowError,
        ]:
            try:
                raise exc_cls("custom message")
            except Exception as e:
                assert str(e) == "custom message"
