"""ElevenLabs text-to-speech for driver audio notifications."""

import streamlit as st
import httpx

ELEVENLABS_KEY = st.secrets.get("ELEVENLABS_KEY", "")
ELEVENLABS_VOICE_ID = st.secrets.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")


def is_configured() -> bool:
    return bool(ELEVENLABS_KEY)


def call_elevenlabs(script: str) -> bytes | None:
    """Generate MP3 audio from clearance script."""
    if not ELEVENLABS_KEY:
        return None
    try:
        r = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            json={
                "text": script,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.75,
                    "similarity_boost": 0.85,
                    "style": 0.2,
                    "use_speaker_boost": True
                }
            },
            headers={
                "xi-api-key": ELEVENLABS_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            },
            timeout=30.0
        )
        r.raise_for_status()
        return r.content
    except Exception as e:
        st.warning(f"ElevenLabs error: {e}")
        return None
