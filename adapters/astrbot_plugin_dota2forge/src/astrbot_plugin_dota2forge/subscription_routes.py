"""Validated opaque event routes, with owner and connection/bot isolation."""

import base64
import binascii
import json

from dota2forge_core import InvalidIdentityError, SubscriptionEvent

from .identity import Caller


def destination(caller: Caller, namespace: str) -> str:
    caller.identity(namespace)
    session = caller.session()
    if session is None:
        raise InvalidIdentityError()
    fields = [caller.platform, caller.connection_id, caller.bot_id, caller.user_id, *session]
    encoded = "d2f1." + base64.urlsafe_b64encode(
        json.dumps(fields, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    ).decode("ascii").rstrip("=")
    if len(encoded) > 512:
        raise InvalidIdentityError()
    return encoded


def delivery_route(event: SubscriptionEvent, namespace: str) -> Caller:
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
            fields[1],
            fields[2],
            fields[3],
            conversation_kind=fields[4],
            conversation_id=fields[5],
        )
        if (
            caller.identity(namespace) != event.key.identity
            or destination(caller, namespace) != encoded
        ):
            raise InvalidIdentityError()
        return caller
    except (ValueError, TypeError, binascii.Error):
        raise InvalidIdentityError() from None
