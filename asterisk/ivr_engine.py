#!/usr/bin/env python3
"""
VoxPME - Moteur SVI (AGI) - version finale, alignée sur le schéma réel
------------------------------------------------------------------------
Appelé depuis le dialplan avec le SLUG du tenant en argument :

    exten => s,1,Answer()
     same => n,AGI(ivr_engine.py,t001)
     same => n,Hangup()

Lit le menu "point d'entrée" du tenant dans ivr_menus.options (JSONB),
et navigue dynamiquement. Aucune régénération de dialplan nécessaire 
pour modifier le contenu du SVI : tout est en base.

Dépendances : psycopg2
Installation : pip install psycopg2-binary --break-system-packages

CORRECTIF (voir historique) :
  GET DATA et STREAM FILE ne renvoient PAS le digit de la même façon :
    - GET DATA   -> "200 result=<digits>"           (le(s) chiffre(s) TEL(S) QUEL(S), pas de code ASCII)
    - STREAM FILE-> "200 result=<code_ascii> endpos=<pos>" (code ASCII du digit qui a interrompu la lecture)
  L'ancienne version appliquait chr(int(result)) dans les deux cas, ce qui
  corrompait systématiquement le digit renvoyé par GET DATA (ex: "1" -> chr(1),
  un caractère de contrôle invisible, au lieu de rester "1").
"""

import sys
import os
import psycopg2
import psycopg2.extras

DB_DSN = os.environ.get(
    "VOXPME_DB_DSN",
    "dbname=voxpme user=voxpme_app password=Leroi5alomon# host=127.0.0.1",
)


class AGI:
    def __init__(self):
        self.env = {}
        while True:
            line = sys.stdin.readline().strip()
            if line == "":
                break
            key, _, value = line.partition(":")
            self.env[key.strip()] = value.strip()

    def _send(self, command):
        sys.stdout.write(command + "\n")
        sys.stdout.flush()
        return sys.stdin.readline().strip()

    def answer(self):
        self._send("ANSWER")

    def get_data(self, filename, timeout_ms, max_digits=1):
        """GET DATA renvoie directement le(s) chiffre(s) pressés (pas un code ASCII)."""
        res = self._send(f'GET DATA "{filename}" {timeout_ms} {max_digits}')
        return self._extract_get_data_digits(res)

    def stream_file(self, filename, escape_digits="0123456789#*"):
        """STREAM FILE renvoie le CODE ASCII du digit qui a interrompu la lecture."""
        res = self._send(f'STREAM FILE "{filename}" "{escape_digits}"')
        return self._extract_stream_digit(res)

    def hangup(self):
        self._send("HANGUP")

    def exec_app(self, app, args=""):
        self._send(f'EXEC {app} "{args}"')

    @staticmethod
    def _extract_get_data_digits(agi_response):
        """Pour GET DATA : 'result=1' signifie que le chiffre '1' a été pressé.
        On ne convertit PAS via chr() ici - le résultat est déjà le digit littéral.
        Retourne "" si timeout ou aucun digit."""
        try:
            result_part = agi_response.split("result=")[1]
            digits = result_part.split(" ")[0].split("(")[0].strip()
            return digits
        except IndexError:
            return ""

    @staticmethod
    def _extract_stream_digit(agi_response):
        """Pour STREAM FILE : 'result=49' signifie code ASCII 49 = '1'."""
        try:
            result_part = agi_response.split("result=")[1]
            code = int(result_part.split(" ")[0].split("(")[0])
            return chr(code) if code > 0 else ""
        except (IndexError, ValueError):
            return ""


def get_tenant_id(conn, slug):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM tenants WHERE slug=%s AND statut='actif'", (slug,))
        row = cur.fetchone()
        return row[0] if row else None


def get_menu(conn, tenant_id, menu_id=None, entry_point=False):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if entry_point:
            cur.execute(
                "SELECT * FROM ivr_menus WHERE tenant_id=%s AND is_entry_point=TRUE",
                (tenant_id,),
            )
        else:
            cur.execute(
                "SELECT * FROM ivr_menus WHERE tenant_id=%s AND id=%s",
                (tenant_id, menu_id),
            )
        return cur.fetchone()


def log_event(conn, tenant_id, channel, menu_id, digit, result):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO ivr_call_events (tenant_id, channel, menu_id, digit_pressed, result)
               VALUES (%s, %s, %s, %s, %s)""",
            (tenant_id, channel, menu_id, digit, result),
        )
    conn.commit()


def run_menu(agi, conn, tenant_id, tenant_slug, menu_id, channel, depth=0):
    if depth > 10:
        agi.hangup()
        return

    menu = get_menu(conn, tenant_id, menu_id=menu_id)
    if not menu:
        agi.hangup()
        return

    options = {opt["digit"]: opt for opt in (menu["options"] or [])}
    attempts = 0

    while attempts < menu["max_attempts"]:
        digit = agi.get_data(
            menu["message_accueil"], menu["digit_timeout_s"] * 1000, max_digits=1
        )
        digit = digit.strip()  # sécurité anti espace/retour à la ligne résiduel

        print(f"DEBUG DTMF: digit={digit!r}", file=sys.stderr, flush=True)

        if digit == "":
            attempts += 1
            log_event(conn, tenant_id, channel, menu["id"], "", "timeout")
            if attempts < menu["max_attempts"]:
                agi.stream_file(menu["timeout_sound"])
            continue

        option = options.get(digit)
        if not option:
            attempts += 1
            log_event(conn, tenant_id, channel, menu["id"], digit, "invalid")
            if attempts < menu["max_attempts"]:
                agi.stream_file(menu["invalid_sound"])
            continue

        log_event(conn, tenant_id, channel, menu["id"], digit, "ok")
        return dispatch_action(agi, conn, tenant_id, tenant_slug, menu["id"], option, channel, depth)

    log_event(conn, tenant_id, channel, menu["id"], "", "max_attempts")
    apply_fallback(agi, tenant_slug, menu)


def dispatch_action(agi, conn, tenant_id, tenant_slug, current_menu_id, option, channel, depth):
    action = option["action_type"]
    value = option.get("action_value")

    if action in ("goto_menu", "go_back"):
        return run_menu(agi, conn, tenant_id, tenant_slug, int(value), channel, depth + 1)

    if action == "repeat_menu":
        return run_menu(agi, conn, tenant_id, tenant_slug, current_menu_id, channel, depth + 1)

    if action == "dial_extension":
        # value = extension (ex. "1001") -> identifiant PJSIP complet = "1001-t001"
        agi.exec_app("Dial", f"PJSIP/{value}-{tenant_slug},30")
        return

    if action == "dial_queue":
        agi.exec_app("Queue", f"{value},t,,,60")
        return

    if action == "dial_external":
        agi.exec_app("Dial", f"PJSIP/{value}@trunk-{tenant_slug},30")
        return

    if action == "voicemail":
        agi.exec_app("VoiceMail", f"{value}@{tenant_slug}")
        return

    if action == "hangup":
        agi.hangup()
        return

    agi.hangup()


def apply_fallback(agi, tenant_slug, menu):
    if menu["fallback_action"] == "voicemail":
        agi.exec_app("VoiceMail", f"{menu['fallback_value']}@{tenant_slug}")
    elif menu["fallback_action"] == "dial_extension":
        agi.exec_app("Dial", f"PJSIP/{menu['fallback_value']}-{tenant_slug},30")
    else:
        agi.hangup()


def main():
    agi = AGI()
    tenant_slug = sys.argv[1] if len(sys.argv) > 1 else agi.env.get("agi_arg_1")
    channel = agi.env.get("agi_channel", "unknown")

    if not tenant_slug:
        agi.hangup()
        return

    conn = psycopg2.connect(DB_DSN)
    try:
        agi.answer()
        tenant_id = get_tenant_id(conn, tenant_slug)
        if not tenant_id:
            agi.hangup()
            return
        entry_menu = get_menu(conn, tenant_id, entry_point=True)
        if not entry_menu:
            agi.hangup()
            return
        run_menu(agi, conn, tenant_id, tenant_slug, entry_menu["id"], channel)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
