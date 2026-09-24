from __future__ import annotations

from unittest.mock import Mock

from acled_client import AcledClient, AcledCredentials


def response(status_code: int, payload: dict) -> Mock:
    result = Mock()
    result.status_code = status_code
    result.json.return_value = payload
    result.text = str(payload)
    return result


def test_authentication_and_one_page() -> None:
    session = Mock()
    session.post.return_value = response(
        200, {"access_token": "access", "refresh_token": "refresh"}
    )
    session.get.return_value = response(
        200,
        {
            "success": True,
            "data": [{"event_id_cnty": "ISR1"}],
            "next_cursor": None,
        },
    )
    client = AcledClient(AcledCredentials("user@example.edu", "secret"), session)

    rows = list(client.iter_events({"country": "Israel"}))

    assert rows == [{"event_id_cnty": "ISR1"}]
    assert session.post.call_count == 1
    assert session.get.call_count == 1


def test_cursor_pagination() -> None:
    session = Mock()
    session.get.side_effect = [
        response(200, {"success": True, "data": [{"id": 1}], "next_cursor": 42}),
        response(200, {"success": True, "data": [{"id": 2}], "next_cursor": None}),
    ]
    client = AcledClient(AcledCredentials(access_token="access"), session)

    rows = list(client.iter_events({"country": "Iran"}))

    assert rows == [{"id": 1}, {"id": 2}]
    assert session.get.call_args_list[1].kwargs["params"]["cursor"] == 42


def test_max_rows_stops_before_next_page() -> None:
    session = Mock()
    session.get.return_value = response(
        200,
        {
            "success": True,
            "data": [{"id": 1}, {"id": 2}],
            "next_cursor": 99,
        },
    )
    client = AcledClient(AcledCredentials(access_token="access"), session)

    rows = list(client.iter_events({}, max_rows=1))

    assert rows == [{"id": 1}]
    assert session.get.call_count == 1
