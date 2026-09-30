"""Adapter tests use synthetic host fields and keep application sockets blocked."""

import asyncio

import pytest
import pytest_socket
from Dota2UID.commands import Caller


@pytest.fixture
def run_async():
    pytest_socket.enable_socket()
    try:
        loop = asyncio.new_event_loop()
    finally:
        pytest_socket.disable_socket()
    try:
        yield loop.run_until_complete
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()


@pytest.fixture
def config_path(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        'namespace="synthetic-deployment"\nstratz_token="synthetic-token"\n'
        'timeout_seconds=2\n[platforms]\nonebot="qq"\ntelegram="telegram"\n',
        encoding="utf-8",
    )
    return path


@pytest.fixture
def caller():
    return Caller("onebot", "synthetic-bot", "synthetic-user", "synthetic-connection")
