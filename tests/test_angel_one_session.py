from titan.broker.angel_one.session import AngelOneSession


def test_session_authenticated():
    session = AngelOneSession(
        jwt_token="jwt",
        refresh_token="refresh",
        feed_token="feed",
    )

    assert session.authenticated


def test_session_not_authenticated():
    session = AngelOneSession(
        jwt_token="",
        refresh_token="",
        feed_token="",
    )

    assert not session.authenticated