import hashlib
import io

from PIL import Image

from validation.document import generate_hash, hash_bytes


def test_hash_bytes_matches_hashlib_sha256():
    data = b"the quick brown fox jumps over the lazy dog"
    assert hash_bytes(data) == hashlib.sha256(data).hexdigest()


def test_hash_bytes_is_lowercase_hex_with_no_prefix():
    digest = hash_bytes(b"some bytes")
    assert digest == digest.lower()
    assert not digest.startswith("0x")
    assert len(digest) == 64


def test_same_bytes_produce_same_hash():
    data = b"identical payload"
    assert hash_bytes(data) == hash_bytes(data)


def test_one_byte_changed_produces_different_hash():
    original = b"identical payload"
    tampered = b"Identical payload"  # first letter capitalized
    assert hash_bytes(original) != hash_bytes(tampered)


def test_reencoding_image_via_pil_changes_the_hash():
    # EXIF makes the round-trip divergence deterministic: PIL doesn't carry
    # metadata across a save() unless explicitly told to, so a bare re-encode
    # drops it. This is exactly why we hash the raw uploaded bytes, not the
    # PIL object.
    img = Image.new("RGB", (20, 20), color=(10, 20, 30))
    exif = Image.Exif()
    exif[271] = "TestCam"  # Make tag
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    original_bytes = buf.getvalue()

    reloaded = Image.open(io.BytesIO(original_bytes))
    re_encoded_buf = io.BytesIO()
    reloaded.save(re_encoded_buf, format="JPEG")
    re_encoded_bytes = re_encoded_buf.getvalue()

    assert hash_bytes(original_bytes) != hash_bytes(re_encoded_bytes)


def test_generate_hash_changes_when_document_hash_changes():
    base_input = {
        "declaration": "15 tons of furniture",
        "vehicle_reg": "GP 47 BW WX",
        "verdict": "CLEARED",
        "ts": "2026-09-23T07:00:00Z",
    }
    hash_a = generate_hash({**base_input, "document_hash": hash_bytes(b"file-a")})
    hash_b = generate_hash({**base_input, "document_hash": hash_bytes(b"file-b")})
    assert hash_a != hash_b
