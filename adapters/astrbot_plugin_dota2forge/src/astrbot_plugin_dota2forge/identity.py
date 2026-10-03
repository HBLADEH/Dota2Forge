"""Only trusted host event fields can identify a binding owner."""

import hashlib
import json
from dataclasses import dataclass

from dota2forge_core import InvalidIdentityError, PlatformIdentity


@dataclass(frozen=True, repr=False)
class Caller:
    platform: str
    connection_id: str
    bot_id: str
    user_id: str
    mentioned_other: bool = False
    conversation_kind: str = ""
    conversation_id: str = ""
    is_admin: bool = False

    def identity(self, namespace: str) -> PlatformIdentity:
        if self.mentioned_other is not False:
            raise InvalidIdentityError()
        PlatformIdentity(namespace, self.platform, self.bot_id, self.user_id)
        PlatformIdentity(namespace, self.platform, self.connection_id, self.user_id)
        # Encode both opaque fields without delimiter collisions or ID truncation.
        encoded = json.dumps([self.connection_id, self.bot_id], ensure_ascii=True).encode("ascii")
        bot = "astrbot-" + hashlib.sha256(encoded).hexdigest()
        return PlatformIdentity(namespace, self.platform, bot, self.user_id)

    def session(self) -> tuple[str, str] | None:
        if self.conversation_kind == "FriendMessage":
            return (self.conversation_kind, self.user_id)
        if self.conversation_kind == "GroupMessage" and self.conversation_id:
            try:
                PlatformIdentity("validation", "astrbot", "validation", self.conversation_id)
            except InvalidIdentityError:
                return None
            return (self.conversation_kind, self.conversation_id)
        return None
