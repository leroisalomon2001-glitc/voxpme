import os
import re

from panoramisk import Manager

AMI_HOST = os.environ.get("AMI_HOST", "host.docker.internal")
AMI_PORT = int(os.environ.get("AMI_PORT", "5038"))
AMI_USERNAME = os.environ.get("AMI_USERNAME", "voxpme-backend")
AMI_PASSWORD = os.environ["AMI_PASSWORD"]

# Parse une ligne du type :
#   Contact:  2002-t002/sip:2002-t002@192.168.1.6:64447;ob   f5e9a850e9 NonQual  nan
# colonnes : <Aor/ContactUri> <Hash> <Status> <RTT>
_CONTACT_LINE_RE = re.compile(
    r"^\s*Contact:\s+(?P<aor>[^/\s]+)/\S+\s+\S+\s+(?P<status>\S+)\s+\S+"
)


async def get_registered_aors() -> dict[str, str]:
    """
    Interroge Asterisk en direct via AMI (Command: pjsip show contacts) et
    retourne {aor_id: status} pour chaque contact actuellement enregistré,
    ex: {"2002-t002": "NonQual"}.

    Pas de persistance realtime des contacts en base : sorcery.conf ne
    mappe pas l'objet 'contact' vers Postgres (seuls endpoint/auth/aor/
    transport/identify le sont, voir journal + vérif du 13/09/2026), donc
    l'état d'enregistrement n'existe qu'en mémoire côté Asterisk. On
    interroge Asterisk en direct à chaque appel plutôt que de lire une
    table qui n'existe pas.

    Lève une exception (ConnectionError, etc.) si l'AMI est injoignable :
    à l'appelant de décider comment dégrader (ex: renvoyer la liste des
    postes sans statut live plutôt que de faire échouer toute la route).
    """
    manager = Manager(
        host=AMI_HOST,
        port=AMI_PORT,
        username=AMI_USERNAME,
        secret=AMI_PASSWORD,
    )
    await manager.connect()
    try:
        resp = await manager.send_action({
            "Action": "Command",
            "Command": "pjsip show contacts",
        })
        output = resp.get("Output", "")
        lines = output if isinstance(output, list) else str(output).split("\n")

        registered: dict[str, str] = {}
        for line in lines:
            match = _CONTACT_LINE_RE.match(line)
            if match and "<" not in match.group("aor"):
                registered[match.group("aor")] = match.group("status")
        return registered
    finally:
        manager.close()