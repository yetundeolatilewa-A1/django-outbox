"""django-outbox: transactional outbox and reliable webhook delivery for Django."""

__version__ = "0.1.0"
__all__ = ["__version__", "publish"]


def publish(*args, **kwargs):
    """Lazy wrapper so ``from django_outbox import publish`` works before apps load."""
    from .publish import publish as _publish

    return _publish(*args, **kwargs)
