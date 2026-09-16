import json
import struct
from pathlib import Path

import pytest

from streamdeck_plugin.video_pedal_plugin import WebSocket, image_data


class Wire:
    def __init__(self, incoming=b""):
        self.incoming = incoming
        self.sent = bytearray()

    def sendall(self, data):
        self.sent.extend(data)

    def recv(self, length):
        # Exercise partial socket reads independently of frame boundaries.
        result, self.incoming = self.incoming[:min(length, 7)], self.incoming[min(length, 7):]
        return result


def decode_client_frame(frame):
    assert frame[0] == 0x81
    assert frame[1] & 0x80
    length = frame[1] & 0x7f
    offset = 2
    if length == 126:
        length = struct.unpack("!H", frame[2:4])[0]
        offset = 4
    elif length == 127:
        length = struct.unpack("!Q", frame[2:10])[0]
        offset = 10
    mask = frame[offset:offset + 4]
    body = frame[offset + 4:]
    assert len(body) == length
    return bytes(b ^ mask[i % 4] for i, b in enumerate(body))


@pytest.mark.parametrize("length", [0, 125, 126, 65535, 65536])
def test_client_frame_lengths(length):
    wire = Wire()
    payload = b"x" * length
    WebSocket(wire)._send_frame(payload)
    assert decode_client_frame(wire.sent) == payload


@pytest.mark.parametrize("length", [125, 126, 65535, 65536])
def test_receives_extended_server_frames_with_partial_reads(length):
    payload = b"x" * length
    header = (bytes([0x81, length]) if length < 126 else
              b"\x81\x7e" + struct.pack("!H", length) if length < 65536 else
              b"\x81\x7f" + struct.pack("!Q", length))
    wire = Wire((header + payload)[3:])
    assert WebSocket(wire, (header + payload)[:3])._receive_frame() == (1, payload)


@pytest.mark.parametrize("name", ["off", "starting", "live", "rec", "loop"])
def test_real_icon_message_survives_wire_encoding(name):
    icon = Path(__file__).resolve().parents[1] / "streamdeck_plugin" / "icons" / f"{name}.png"
    message = {"event": "setImage", "context": "ctx", "payload": {"image": image_data(icon), "target": 0}}
    wire = Wire()
    WebSocket(wire).send_json(message)
    assert json.loads(decode_client_frame(wire.sent)) == message


def test_server_close_is_reported_with_payload():
    with pytest.raises(EOFError, match="bad image"):
        WebSocket(Wire(b"\x88\x0b\x03\xeabad image")).receive_json()
