"""Dota2Forge AstrBot library; install the separate bridge for host discovery."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .application import AstrApplication, AstrImageReply, AstrReply, AstrTextReply

__all__ = ["AstrApplication", "AstrImageReply", "AstrReply", "AstrTextReply"]


def __getattr__(name: str) -> object:
    # AstrBot prefers distributions alphabetically, including transitive ones.
    # Do not capture Core/Renderer classes while that preparation is still running.
    if name not in __all__:
        raise AttributeError(name)
    from . import application

    exports: dict[str, object] = {
        "AstrApplication": application.AstrApplication,
        "AstrImageReply": application.AstrImageReply,
        "AstrReply": application.AstrReply,
        "AstrTextReply": application.AstrTextReply,
    }
    return exports[name]
