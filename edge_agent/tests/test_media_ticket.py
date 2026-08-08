from __future__ import annotations

from coderoute_edge.tickets import media_ticket, verify_media_ticket


def test_media_ticket_is_scoped_and_expires() -> None:
    key = b"k" * 32
    expires = 2_000_000_000
    ticket = media_ticket(key, "attempt-1", "a" * 64, expires)
    assert len(ticket) == 64
    assert verify_media_ticket(key, "attempt-1", "a" * 64, expires, ticket, now=1_900_000_000) is True
    assert verify_media_ticket(key, "attempt-2", "a" * 64, expires, ticket, now=1_900_000_000) is False
    assert verify_media_ticket(key, "attempt-1", "b" * 64, expires, ticket, now=1_900_000_000) is False
    assert verify_media_ticket(key, "attempt-1", "a" * 64, expires, ticket, now=2_000_000_001) is False
