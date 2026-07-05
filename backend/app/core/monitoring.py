"""
Error monitoring (Sentry-optional).

Initializes Sentry only when a DSN is configured AND sentry-sdk is importable; otherwise every
function here is a clean no-op — same graceful-degradation pattern as the Firebase/LLM integrations,
so local dev and tests run with zero external dependency. No PII is sent (send_default_pii=False).
"""
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_enabled = False


def init_monitoring() -> None:
    """Called once at startup. No-op unless SENTRY_DSN is set and sentry-sdk is installed."""
    global _enabled
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=0.0,  # errors only, no performance tracing
            send_default_pii=False,
        )
        _enabled = True
        logger.info("Sentry monitoring initialized (env=%s)", settings.app_env)
    except Exception as exc:  # noqa: BLE001 — monitoring must never break startup
        logger.warning("Sentry init failed (monitoring disabled): %s", exc)


def capture_exception(exc: BaseException, context: dict | None = None) -> None:
    """Report an exception to Sentry. Safe no-op when monitoring is disabled."""
    if not _enabled:
        return
    try:
        import sentry_sdk

        if context:
            with sentry_sdk.push_scope() as scope:
                for key, value in context.items():
                    scope.set_tag(key, str(value))
                sentry_sdk.capture_exception(exc)
        else:
            sentry_sdk.capture_exception(exc)
    except Exception:  # noqa: BLE001 — reporting failures must never propagate
        logger.debug("Sentry capture failed", exc_info=True)


def is_enabled() -> bool:
    return _enabled
