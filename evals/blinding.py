from __future__ import annotations

import hashlib


def blinded_output_id(output_id: str, seed: int) -> str:
    digest = hashlib.sha256(f"{seed}|{output_id}".encode()).hexdigest()[:16]
    return f"rating_{digest}"
