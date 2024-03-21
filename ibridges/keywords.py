"""Keywords and definitions."""

# Excpetion mapping
exceptions = {
    "PAM_AUTH_PASSWORD_FAILED(None,)": "Wrong password",
    "CAT_PASSWORD_EXPIRED(None,)": "Cached password expired",
    "CAT_INVALID_AUTHENTICATION(None,)": "Cached password is wrong",
    "NetworkException('Client-Server negotiation failure: CS_NEG_REFUSE,CS_NEG_REQUIRE')":
    '"irods_client_server_policy" not set (correctly) in irods_environment.json'
}
