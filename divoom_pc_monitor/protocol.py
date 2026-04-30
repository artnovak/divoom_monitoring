from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from typing import Iterable

from PIL import Image


COMMAND_ANIMATION = 0x8B
COMMAND_SET_IMAGE = 0x44
FRAME_MAGIC = 0xAA


def _checksum(payload: bytes) -> int:
    return sum(payload) & 0xFFFF


def make_packet(command: int, payload: bytes) -> bytes:
    body = struct.pack("<HB", len(payload) + 3, command) + payload
    return b"\x01" + body + struct.pack("<H", _checksum(body)) + b"\x02"


def _bits_per_pixel(color_count: int) -> int:
    return max(1, int(math.ceil(math.log2(max(2, color_count)))))


def _pack_palette_indexes(indexes: Iterable[int], bits_per_pixel: int) -> bytes:
    out = bytearray()
    current = 0
    bit_pos = 0

    for value in indexes:
        for bit in range(bits_per_pixel):
            current |= ((value >> bit) & 1) << bit_pos
            bit_pos += 1
            if bit_pos == 8:
                out.append(current)
                current = 0
                bit_pos = 0

    if bit_pos:
        out.append(current)
    return bytes(out)


def image_to_divoom16_frame(image: Image.Image, delay_ms: int = 900) -> bytes:
    rgb = image.convert("RGB").resize((16, 16), Image.Resampling.NEAREST)
    pixels = list(rgb.getdata())

    palette: list[tuple[int, int, int]] = []
    palette_index: dict[tuple[int, int, int], int] = {}
    for pixel in pixels:
        if pixel not in palette_index:
            if len(palette) >= 255:
                raise ValueError("Divoom 16x16 frame supports up to 255 colors")
            palette_index[pixel] = len(palette)
            palette.append(pixel)

    if len(palette) == 1:
        palette.append((0, 0, 0) if palette[0] != (0, 0, 0) else (1, 1, 1))

    indexes = (palette_index[pixel] for pixel in pixels)
    pixel_data = _pack_palette_indexes(indexes, _bits_per_pixel(len(palette)))
    palette_data = b"".join(bytes(color) for color in palette)

    length = 7 + len(palette_data) + len(pixel_data)
    return (
        bytes([FRAME_MAGIC])
        + struct.pack("<HHBB", length, delay_ms, 0, len(palette))
        + palette_data
        + pixel_data
    )


def image_to_ditoomic_image_args(image: Image.Image) -> bytes:
    rgb = image.convert("RGB").resize((16, 16), Image.Resampling.NEAREST)
    pixels = list(rgb.getdata())

    palette: list[tuple[int, int, int]] = []
    palette_index: dict[tuple[int, int, int], int] = {}
    indexes: list[int] = []
    for pixel in pixels:
        if pixel not in palette_index:
            if len(palette) >= 255:
                raise ValueError("DitooMic 16x16 frame supports up to 255 colors")
            palette_index[pixel] = len(palette)
            palette.append(pixel)
        indexes.append(palette_index[pixel])

    if len(palette) == 1:
        palette.append((0, 0, 0) if palette[0] != (0, 0, 0) else (1, 1, 1))

    frame_payload = (
        b"\x00\x00"  # time code: still image
        + b"\x00"  # palette flag
        + bytes([len(palette)])
        + b"".join(bytes(color) for color in palette)
        + _pack_palette_indexes(indexes, _bits_per_pixel(len(palette)))
    )
    frame_length = len(frame_payload) + 3
    frame = bytes([FRAME_MAGIC]) + struct.pack("<H", frame_length) + frame_payload
    return b"\x00\x0A\x0A\x04" + frame


def make_single_image_packet(image: Image.Image) -> bytes:
    return make_packet(COMMAND_SET_IMAGE, image_to_ditoomic_image_args(image))


def make_single_frame_animation(image: Image.Image, delay_ms: int = 900) -> bytes:
    return image_to_divoom16_frame(image, delay_ms)


@dataclass(slots=True)
class AnimationTransfer:
    animation: bytes
    chunk_size: int = 256

    def packets(self) -> list[bytes]:
        size = len(self.animation)
        packets = [
            make_packet(COMMAND_ANIMATION, bytes([0]) + struct.pack("<I", size)),
        ]

        for offset, chunk in enumerate(
            self.animation[i : i + self.chunk_size]
            for i in range(0, len(self.animation), self.chunk_size)
        ):
            payload = bytes([1]) + struct.pack("<IH", size, offset) + chunk
            packets.append(make_packet(COMMAND_ANIMATION, payload))
        return packets
