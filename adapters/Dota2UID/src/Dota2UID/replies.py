"""Host-neutral adapter replies; the discovery bridge owns SDK message conversion."""

from dataclasses import dataclass

from dota2forge_renderer import ImageArtifact


@dataclass(frozen=True, repr=False)
class TextReply:
    text: str


@dataclass(frozen=True, repr=False)
class ImageReply:
    artifact: ImageArtifact


type Reply = TextReply | ImageReply
