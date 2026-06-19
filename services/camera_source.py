from __future__ import annotations


def normalize_camera_source(raw_source: str | int | None):
    if raw_source is None:
        return 0

    if isinstance(raw_source, int):
        return raw_source

    text = str(raw_source).strip()
    if not text:
        return 0

    if text.isdigit() or (text.startswith('-') and text[1:].isdigit()):
        return int(text)

    return text


def is_stream_source(source) -> bool:
    if not isinstance(source, str):
        return False
    lowered = source.strip().lower()
    return lowered.startswith(('http://', 'https://', 'rtsp://', 'mjpeg://')) or '://' in lowered
