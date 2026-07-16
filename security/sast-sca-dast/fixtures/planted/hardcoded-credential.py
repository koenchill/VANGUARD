# Planted SAST-flaggable issue — hardcoded credential (do not use in production).
# Semgrep / secret scanners must flag this file when scanned as a deliberate find.

AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
DATABASE_PASSWORD = "SuperSecretPassword123!"


def connect():
    return {"user": "admin", "password": DATABASE_PASSWORD, "key": AWS_ACCESS_KEY_ID}
