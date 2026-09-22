"""Explicit setup diagnostics. Offline by default; no credentials in output."""

import importlib.util
import shutil
import sys

from . import __version__
from .provider import Client, ProviderError, credential


def check(live=False):
    try:
        credential()
        configured = True
    except ProviderError:
        configured = False
    result = {
        "ok": True,
        "version": __version__,
        "python": sys.version.split()[0],
        "api_key_configured": configured,
        "ripgrep": shutil.which("rg") is not None,
        "tree_sitter": importlib.util.find_spec("tree_sitter") is not None,
        "live_checked": False,
        "result_cache": False,
        "concurrency_cap": 30,
    }
    if live:
        try:
            with Client() as client:
                response = client.call(
                    {
                        "model": "jev-1.13.0",
                        "state": "The traffic light is red.",
                        "questions": {
                            "color": {
                                "type": "choice",
                                "instructions": "Select the observed color.",
                                "criteria": {"red": "Red", "green": "Green"},
                            }
                        },
                    }
                )
            result.update(
                live_checked=True,
                ok=response["answers"]["color"]["choice"] == "red",
                model=response["model"],
                usage=response["usage"],
                usage_complete=response["usage_complete"],
            )
        except ProviderError as error:
            result.update(ok=False, error_code=error.code)
    return result
