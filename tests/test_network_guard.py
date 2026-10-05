"""Offline tests cannot reach model services, even with a configured credential."""

import socket

import pytest


@pytest.mark.parametrize("host", ["generativelanguage.googleapis.com", "api.openai.com", "192.0.2.1"])
def test_external_dns_is_blocked(host):
    with pytest.raises(RuntimeError, match="External DNS disabled"):
        socket.getaddrinfo(host, 443)


@pytest.mark.parametrize("method", ["connect", "connect_ex"])
def test_external_socket_connection_is_blocked(method):
    with socket.socket() as client:
        with pytest.raises(RuntimeError, match="External network disabled"):
            getattr(client, method)(("192.0.2.1", 443))


def test_loopback_server_still_works():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        with socket.create_connection(server.getsockname(), timeout=1):
            connection, _ = server.accept()
            connection.close()
