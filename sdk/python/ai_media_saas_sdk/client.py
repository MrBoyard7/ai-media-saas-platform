"""
Minimal synchronous Python SDK for the AI Media SaaS Platform.

Example
-------
    from ai_media_saas_sdk import PlatformClient

    client = PlatformClient(api_key="sk_live_...", base_url="https://api.yourplatform.com/api/v1")
    job = client.generate_music(prompt="lofi hip-hop beat, 90 bpm", duration_seconds=30)
    print(job["id"], job["status"])

This SDK intentionally has zero dependencies beyond `httpx` so it stays
easy to vendor into customer codebases as part of the Enterprise API
Platform / Developer Platform offering.
"""
from __future__ import annotations

import uuid
from typing import Any

import httpx


class PlatformAPIError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"[{status_code}] {detail}")
        self.status_code = status_code
        self.detail = detail


class PlatformClient:
    def __init__(self, api_key: str, base_url: str = "https://api.yourplatform.com/api/v1", timeout: float = 30.0) -> None:
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> PlatformClient:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        response = self._http.request(method, path, **kwargs)
        if response.status_code >= 400:
            detail = response.json().get("detail", response.text) if response.content else response.text
            raise PlatformAPIError(response.status_code, detail)
        return response.json()

    # --- Wallet ---------------------------------------------------------------
    def get_balance(self) -> int:
        return self._request("GET", "/credits/balance")["balance"]

    # --- Generation -------------------------------------------------------------
    def _generate(self, capability: str, prompt: str, **parameters: Any) -> dict:
        return self._request(
            "POST",
            "/generate",
            json={
                "capability": capability,
                "prompt": prompt,
                "parameters": parameters,
                "idempotency_key": str(uuid.uuid4()),
            },
        )

    def generate_lyrics(self, prompt: str, **parameters: Any) -> dict:
        return self._generate("lyrics", prompt, **parameters)

    def generate_music(self, prompt: str, **parameters: Any) -> dict:
        return self._generate("music", prompt, **parameters)

    def generate_voice(self, prompt: str, **parameters: Any) -> dict:
        return self._generate("voice", prompt, **parameters)

    def generate_video(self, prompt: str, **parameters: Any) -> dict:
        return self._generate("video", prompt, **parameters)

    # --- Jobs -----------------------------------------------------------------
    def get_job(self, job_id: str) -> dict:
        return self._request("GET", f"/jobs/{job_id}")
