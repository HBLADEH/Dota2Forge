"""Durable routes constructed only from trusted event fields, never command text."""

import base64
import binascii
import json

from dota2forge_core import InvalidIdentityError, PlatformIdentity, SubscriptionEvent

from .commands import Caller
from .config import Config


def destination(caller: Caller, config: Config) -> str:
    caller.identity(config)
    if caller.conversation_kind == "direct":
        target = caller.user_id
    elif caller.conversation_kind == "group" and caller.conversation_id:
        target = caller.conversation_id
    else:
        raise InvalidIdentityError()
    PlatformIdentity(config.namespace, "route", "route", target)
    fields = [
        caller.platform_key,
        caller.connection_id,
        caller.bot_self_id,
        caller.user_id,
        caller.conversation_kind,
        target,
    ]
    encoded = "d2f1." + base64.urlsafe_b64encode(
        json.dumps(fields, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    ).decode("ascii").rstrip("=")
    if len(encoded) > 512:
        raise InvalidIdentityError()
    return encoded


def delivery_route(event: SubscriptionEvent, config: Config) -> Caller:
    encoded = event.key.destination
    try:
        if not encoded.startswith("d2f1.") or len(encoded) > 512:
            raise InvalidIdentityError()
        fields = json.loads(
            base64.b64decode(
                encoded[5:] + "=" * (-len(encoded[5:]) % 4), altchars=b"-_", validate=True
            )
        )
        if (
            not isinstance(fields, list)
            or len(fields) != 6
            or any(not isinstance(value, str) for value in fields)
        ):
            raise InvalidIdentityError()
        caller = Caller(
            fields[0],
            fields[2],
            fields[3],
            fields[1],
            conversation_kind=fields[4],
            conversation_id=fields[5],
        )
        if caller.identity(config) != event.key.identity or destination(caller, config) != encoded:
            raise InvalidIdentityError()
        return caller
    except (ValueError, TypeError, binascii.Error):
        raise InvalidIdentityError() from None
