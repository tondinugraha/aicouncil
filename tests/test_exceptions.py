"""Tests for the custom exception hierarchy."""

from aicouncil.exceptions import (
    AgentLoadError,
    AiCouncilError,
    ConfigError,
    CouncilError,
    ModelUnavailableError,
    OpenRouterError,
)


class TestExceptionHierarchy:
    """Verify exception inheritance chain."""

    def test_base_exception(self):
        err = AiCouncilError("base error")
        assert isinstance(err, Exception)
        assert str(err) == "base error"

    def test_open_router_error_inherits_from_base(self):
        err = OpenRouterError("api failure")
        assert isinstance(err, AiCouncilError)
        assert isinstance(err, Exception)

    def test_model_unavailable_inherits_from_open_router(self):
        err = ModelUnavailableError("model down")
        assert isinstance(err, OpenRouterError)
        assert isinstance(err, AiCouncilError)

    def test_config_error_inherits_from_base(self):
        err = ConfigError("bad config")
        assert isinstance(err, AiCouncilError)
        assert not isinstance(err, OpenRouterError)

    def test_agent_load_error_inherits_from_base(self):
        err = AgentLoadError("bad agent")
        assert isinstance(err, AiCouncilError)
        assert not isinstance(err, OpenRouterError)

    def test_council_error_inherits_from_base(self):
        err = CouncilError("council failed")
        assert isinstance(err, AiCouncilError)
        assert not isinstance(err, OpenRouterError)

    def test_all_exceptions_are_catchable_by_base(self):
        exceptions = [
            OpenRouterError("a"),
            ModelUnavailableError("b"),
            ConfigError("c"),
            AgentLoadError("d"),
            CouncilError("e"),
        ]
        for exc in exceptions:
            try:
                raise exc
            except AiCouncilError:
                pass  # All should be caught here

    def test_model_unavailable_not_caught_by_config_error(self):
        try:
            raise ModelUnavailableError("model down")
        except ConfigError:
            assert False, "ModelUnavailableError should not be caught by ConfigError"
        except OpenRouterError:
            pass  # Correct: caught by parent
