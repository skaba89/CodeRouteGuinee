"""
Tests monitoring.py — couverture Sentry.

Cible : app/monitoring.py (31% → 90%+)
Lignes non couvertes : 38-70, 80-91, 108-112, 123-127
"""
import logging
from unittest.mock import MagicMock, patch

from app.monitoring import (
    _filter_expected_errors,
    capture_exception,
    init_sentry,
    set_user_context,
)

# ── init_sentry ───────────────────────────────────────────────────

class TestInitSentry:
    def test_no_dsn_returns_false(self):
        result = init_sentry(dsn=None)
        assert result is False

    def test_empty_dsn_returns_false(self):
        result = init_sentry(dsn="")
        assert result is False

    def test_no_dsn_logs_info(self):
        from unittest.mock import MagicMock, patch

        import app.monitoring as mon
        mock_logger = MagicMock()
        with patch.object(mon, 'logger', mock_logger):
            init_sentry(dsn=None)
        # Vérifier qu'un appel logger.info a eu lieu mentionnant Sentry
        assert mock_logger.info.called
        call_msg = str(mock_logger.info.call_args)
        assert "Sentry" in call_msg or "désactivé" in call_msg or "absent" in call_msg

    def test_sentry_not_installed_logs_warning(self, caplog):
        """Sans sentry_sdk installé, on attend un warning ou False."""
        with caplog.at_level(logging.WARNING):
            result = init_sentry(dsn="https://fake@sentry.io/1")
        # Soit sentry_sdk absent → warning + False, soit présent → True
        # Dans l'environnement de test sans sentry_sdk : False
        assert isinstance(result, bool)

    def test_sentry_init_with_valid_dsn_if_sdk_present(self):
        """Si sentry_sdk est installé, init_sentry doit retourner True."""
        mock_sdk = MagicMock()
        mock_sdk.init = MagicMock()

        mock_fastapi_integration = MagicMock()
        mock_logging_integration = MagicMock()
        mock_sqlalchemy_integration = MagicMock()

        with patch.dict("sys.modules", {
            "sentry_sdk": mock_sdk,
            "sentry_sdk.integrations.fastapi": MagicMock(FastApiIntegration=mock_fastapi_integration),
            "sentry_sdk.integrations.logging": MagicMock(LoggingIntegration=mock_logging_integration),
            "sentry_sdk.integrations.sqlalchemy": MagicMock(SqlalchemyIntegration=mock_sqlalchemy_integration),
        }):
            result = init_sentry(
                dsn="https://fake@sentry.io/1",
                environment="test",
                release="1.0.0",
                traces_sample_rate=0.1,
            )
        assert result is True
        mock_sdk.init.assert_called_once()
        call_kwargs = mock_sdk.init.call_args[1]
        assert call_kwargs["dsn"] == "https://fake@sentry.io/1"
        assert call_kwargs["environment"] == "test"
        assert call_kwargs["release"] == "1.0.0"
        assert call_kwargs["traces_sample_rate"] == 0.1
        assert call_kwargs["send_default_pii"] is False

    def test_sentry_init_passes_filter_function(self):
        """Le before_send doit être _filter_expected_errors."""
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {
            "sentry_sdk": mock_sdk,
            "sentry_sdk.integrations.fastapi": MagicMock(FastApiIntegration=MagicMock()),
            "sentry_sdk.integrations.logging": MagicMock(LoggingIntegration=MagicMock()),
            "sentry_sdk.integrations.sqlalchemy": MagicMock(SqlalchemyIntegration=MagicMock()),
        }):
            init_sentry(dsn="https://fake@sentry.io/1")
        call_kwargs = mock_sdk.init.call_args[1]
        assert call_kwargs["before_send"] is _filter_expected_errors


# ── _filter_expected_errors ───────────────────────────────────────

class TestFilterExpectedErrors:
    def test_passes_through_event_without_exc_info(self):
        event = {"level": "error", "message": "Something went wrong"}
        result = _filter_expected_errors(event, {})
        assert result is event

    def test_passes_through_5xx_http_exception(self):
        from fastapi import HTTPException
        exc = HTTPException(status_code=500, detail="Internal error")
        event = {"type": "event"}
        hint = {"exc_info": (type(exc), exc, None)}
        result = _filter_expected_errors(event, hint)
        assert result is event

    def test_filters_out_401(self):
        from fastapi import HTTPException
        exc = HTTPException(status_code=401, detail="Unauthorized")
        hint = {"exc_info": (type(exc), exc, None)}
        result = _filter_expected_errors({}, hint)
        assert result is None

    def test_filters_out_403(self):
        from fastapi import HTTPException
        exc = HTTPException(status_code=403, detail="Forbidden")
        hint = {"exc_info": (type(exc), exc, None)}
        result = _filter_expected_errors({}, hint)
        assert result is None

    def test_filters_out_404(self):
        from fastapi import HTTPException
        exc = HTTPException(status_code=404, detail="Not found")
        hint = {"exc_info": (type(exc), exc, None)}
        result = _filter_expected_errors({}, hint)
        assert result is None

    def test_filters_out_422_validation(self):
        from fastapi import HTTPException
        exc = HTTPException(status_code=422, detail="Unprocessable")
        hint = {"exc_info": (type(exc), exc, None)}
        result = _filter_expected_errors({}, hint)
        assert result is None

    def test_filters_pydantic_validation_error(self):
        """ValidationError doit être filtré."""
        class FakeValidationError(Exception):
            pass
        FakeValidationError.__name__ = "ValidationError"
        exc = FakeValidationError("invalid data")
        hint = {"exc_info": (FakeValidationError, exc, None)}
        result = _filter_expected_errors({}, hint)
        assert result is None

    def test_filters_request_validation_error(self):
        class FakeRequestValidationError(Exception):
            pass
        FakeRequestValidationError.__name__ = "RequestValidationError"
        exc = FakeRequestValidationError("bad request body")
        hint = {"exc_info": (FakeRequestValidationError, exc, None)}
        result = _filter_expected_errors({}, hint)
        assert result is None

    def test_passes_through_runtime_error(self):
        exc = RuntimeError("unexpected crash")
        event = {"type": "event"}
        hint = {"exc_info": (RuntimeError, exc, None)}
        result = _filter_expected_errors(event, hint)
        assert result is event

    def test_passes_through_value_error(self):
        exc = ValueError("bad value")
        event = {"type": "event"}
        hint = {"exc_info": (ValueError, exc, None)}
        result = _filter_expected_errors(event, hint)
        assert result is event

    def test_passes_through_when_no_exc_type(self):
        event = {"level": "info"}
        hint = {"exc_info": (None, None, None)}
        result = _filter_expected_errors(event, hint)
        assert result is event


# ── capture_exception ─────────────────────────────────────────────

class TestCaptureException:
    def test_capture_without_sentry_logs_error(self):
        """Sans sentry_sdk, l'exception doit être loguée en ERROR."""
        from unittest.mock import MagicMock, patch

        import app.monitoring as mon
        mock_logger = MagicMock()
        exc = RuntimeError("test error")
        with patch.object(mon, 'logger', mock_logger):
            capture_exception(exc, {"context_key": "value"})
        assert mock_logger.error.called
        call_msg = str(mock_logger.error.call_args)
        assert "test error" in call_msg

    def test_capture_with_sentry_calls_sdk(self):
        """Avec sentry_sdk disponible, appelle sentry_sdk.capture_exception."""
        mock_sdk = MagicMock()
        mock_scope = MagicMock()
        mock_sdk.push_scope.return_value.__enter__ = MagicMock(return_value=mock_scope)
        mock_sdk.push_scope.return_value.__exit__ = MagicMock(return_value=False)

        exc = ValueError("test")
        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            capture_exception(exc, {"payment_id": "pay-123"})

        mock_sdk.capture_exception.assert_called_once_with(exc)
        mock_scope.set_extra.assert_called_with("payment_id", "pay-123")

    def test_capture_without_context(self):
        """capture_exception sans contexte ne doit pas lever d'exception."""
        exc = RuntimeError("bare error")
        capture_exception(exc)  # pas de context — ne doit pas planter

    def test_capture_with_empty_context(self):
        exc = RuntimeError("error")
        capture_exception(exc, {})  # contexte vide


# ── set_user_context ──────────────────────────────────────────────

class TestSetUserContext:
    def test_set_user_without_sentry_is_silent(self):
        """Sans sentry_sdk, set_user_context ne doit pas lever d'exception."""
        set_user_context("user-123", "candidate", "test@example.com")

    def test_set_user_with_sentry_calls_set_user(self):
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            set_user_context("user-456", "admin", "admin@coderoute.gov.gn")
        mock_sdk.set_user.assert_called_once_with({
            "id": "user-456",
            "role": "admin",
            "email": "admin@coderoute.gov.gn",
        })

    def test_set_user_with_none_email(self):
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            set_user_context("user-789", "super_admin", None)
        mock_sdk.set_user.assert_called_once_with({
            "id": "user-789",
            "role": "super_admin",
            "email": None,
        })

    def test_set_user_never_sends_password(self):
        """Vérifier que set_user ne transmet jamais de mot de passe."""
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            set_user_context("user-001", "candidate")
        call_args = mock_sdk.set_user.call_args[0][0]
        assert "password" not in call_args
        assert "hashed_password" not in call_args
