def get_mist_session(config):
    """Create an authenticated mistapi.APISession from config."""
    import mistapi

    session = mistapi.APISession(apitoken=config["token"], host=config["host"])
    session.login()
    return session


def get_requests_session(token):
    """Create an authenticated requests.Session with token-based auth."""
    import requests

    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})
    return session
