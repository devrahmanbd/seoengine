import pytest
from app.services.atropos.scored_data_api import ScoredData, ScoredDataBuffer, scored_data_buffer


@pytest.fixture
def fresh_buffer():
    buf = ScoredDataBuffer(max_size=100)
    return buf


class TestScoredData:
    def test_defaults(self):
        sd = ScoredData(state={"a": 1}, action={"b": 2}, reward=1.0, next_state={"a": 2}, done=False)
        assert sd.logprobs is None
        assert sd.distill_data is None

    def test_all_fields(self):
        sd = ScoredData(
            state={"s": 1}, action={"a": 1}, reward=0.5, next_state={"s": 2},
            done=True, logprobs={"p": 0.1}, distill_data={"d": 1},
        )
        assert sd.logprobs == {"p": 0.1}
        assert sd.distill_data == {"d": 1}


class TestScoredDataBuffer:
    def test_append_and_len(self, fresh_buffer):
        sd = ScoredData(state={}, action={}, reward=1.0, next_state={}, done=False)
        fresh_buffer.append(sd)
        assert len(fresh_buffer) == 1

    def test_append_respects_max_size(self):
        buf = ScoredDataBuffer(max_size=3)
        for i in range(5):
            sd = ScoredData(state={"i": i}, action={}, reward=float(i), next_state={}, done=False)
            buf.append(sd)
        assert len(buf) == 3

    def test_extend(self, fresh_buffer):
        items = [
            ScoredData(state={}, action={}, reward=float(i), next_state={}, done=False)
            for i in range(5)
        ]
        fresh_buffer.extend(items)
        assert len(fresh_buffer) == 5

    def test_sample_returns_requested_size(self, fresh_buffer):
        items = [
            ScoredData(state={}, action={}, reward=float(i), next_state={}, done=False)
            for i in range(20)
        ]
        fresh_buffer.extend(items)
        sampled = fresh_buffer.sample(5)
        assert len(sampled) == 5

    def test_sample_returns_all_when_smaller(self, fresh_buffer):
        items = [
            ScoredData(state={}, action={}, reward=float(i), next_state={}, done=False)
            for i in range(3)
        ]
        fresh_buffer.extend(items)
        sampled = fresh_buffer.sample(10)
        assert len(sampled) == 3

    def test_sample_empty_buffer(self, fresh_buffer):
        sampled = fresh_buffer.sample(5)
        assert sampled == []

    def test_clear(self, fresh_buffer):
        sd = ScoredData(state={}, action={}, reward=1.0, next_state={}, done=False)
        fresh_buffer.append(sd)
        fresh_buffer.clear()
        assert len(fresh_buffer) == 0

    def test_thread_safety(self, fresh_buffer):
        import threading
        errors = []

        def add_items():
            try:
                for i in range(50):
                    sd = ScoredData(state={}, action={}, reward=float(i), next_state={}, done=False)
                    fresh_buffer.append(sd)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_items) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(fresh_buffer) <= 100


class TestGlobalBuffer:
    def test_global_exists(self):
        assert scored_data_buffer is not None
        assert isinstance(scored_data_buffer, ScoredDataBuffer)
