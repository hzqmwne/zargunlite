try:
    from zargunlite._version import __version__
except ImportError:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("zargunlite")
    except PackageNotFoundError:
        pass

__all__ = ["__version__"]
