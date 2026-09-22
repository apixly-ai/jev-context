"""Evidence-preserving semantic tools. No model calls occur on import."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("jev-context")
except PackageNotFoundError:
    __version__ = "0.1.0"
