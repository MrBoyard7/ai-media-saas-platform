# ai-media-saas-sdk (Python)

Official Python SDK for the AI Media SaaS Platform Developer Platform.

## Install

```bash
pip install -e ./sdk/python
```

## Usage

```python
from ai_media_saas_sdk import PlatformClient

with PlatformClient(api_key="sk_live_...") as client:
    print(client.get_balance())
    job = client.generate_lyrics("a summer road trip song", line_count=12)
    print(job["id"], job["status"])
```
