import base64
import json
import logging
import random


def _tracking_id() -> str:
    return str(base64.b64encode(bytearray(random.randrange(256) for _ in range(16))))[2:-1]

_log = logging.getLogger('contact_agent.send_invite')


def send_invite(li_api, urn_id: str, message: str) -> dict:
    """Send a LinkedIn connection request — calls _post directly to expose HTTP details."""
    try:
        note = message[:300]
        _log.info(f'Sending connection request | urn_id={urn_id!r} | note={len(note)} chars')

        payload = {
            "trackingId": _tracking_id(),
            "message": note,
            "invitations": [],
            "excludeInvitations": [],
            "invitee": {
                "com.linkedin.voyager.growth.invitation.InviteeProfile": {
                    "profileId": urn_id
                }
            },
        }
        res = li_api._post(
            "/growth/normInvitations",
            data=json.dumps(payload),
            headers={"accept": "application/vnd.linkedin.normalized+json+2.1"},
        )

        _log.info(f'LinkedIn HTTP {res.status_code} | urn_id={urn_id}')

        if res.status_code != 201:
            # Log the response body so we know the exact rejection reason
            try:
                body = res.json()
            except Exception:
                body = res.text[:500]
            _log.error(
                f'LinkedIn REJECTED | status={res.status_code} | urn_id={urn_id} | body={body!r}'
            )
            reason = _classify_rejection(res.status_code, body)
            return {"sent": False, "reason": reason, "http_status": res.status_code}

        _log.info(f'Connection request SENT successfully | urn_id={urn_id}')
        return {"sent": True, "reason": "ok"}

    except Exception as e:
        err = str(e)
        _log.error(f'send_invite EXCEPTION — {type(e).__name__}: {err} | urn_id={urn_id}')
        if 'already' in err.lower() or 'pending' in err.lower():
            return {"sent": False, "reason": "already_connected"}
        return {"sent": False, "reason": err}


def _classify_rejection(status: int, body) -> str:
    """Turn a raw LinkedIn HTTP rejection into a readable reason string."""
    body_str = str(body).lower()
    if status == 429:
        return "rate_limited"
    if status == 403:
        return "forbidden_account_restricted"
    if status == 400:
        if 'duplicate' in body_str or 'already' in body_str:
            return "already_connected_or_pending"
        if 'limit' in body_str or 'quota' in body_str:
            return "weekly_invite_limit_reached"
        if 'restricted' in body_str:
            return "account_restricted"
        return f"bad_request: {str(body)[:200]}"
    if status == 301:
        return "session_expired_relogin"
    if status == 401:
        return "session_expired_relogin"
    return f"http_{status}"
