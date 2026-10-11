"""GsCore-style command candidates precede regex and block later handlers."""

import re


async def dispatch_message(commands, regex_handlers, bot, event, raw_text):
    # The SDK's trie yields a shorter matching prefix before its descendants.
    matching = sorted((keyword for keyword in commands if raw_text.startswith(keyword)), key=len)
    if matching:
        keyword = matching[0]
        event.command = keyword
        event.text = raw_text[len(keyword) :].strip()
        await commands[keyword][0](bot, event)
        return
    for pattern, callback in regex_handlers.items():
        match = re.search(pattern, raw_text)
        if match:
            event.command = ""
            event.text = ""
            event.regex_dict = match.groupdict()
            await callback(bot, event)
            return
    raise AssertionError(f"No command matched: {raw_text}")
