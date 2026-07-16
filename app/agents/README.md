# app/agents/

Multi-agent coordinator (`supervisor.py`), sandboxed scope-declared tool wrappers
(`tools.py`), and the G-013 human-in-the-loop approval gate
(`human_in_the_loop.py` + `signing_service.py` + `nonce_store.py`).

Signing keys live only inside the KMS/HSM-backed signing service — never in
application memory. Nonces are consumed atomically (compare-and-delete).
