from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable

import serial
from PIL import Image

from .protocol import make_single_image_packet


@dataclass(slots=True)
class DivoomSerialDevice:
    port: str = "COM7"
    baudrate: int = 9600

    async def send_image(self, image: Image.Image, delay_ms: int = 900) -> None:
        async with self.session() as session:
            await session.send_image(image, delay_ms=delay_ms)

    def session(self) -> "DivoomSerialSession":
        return DivoomSerialSession(self)


class DivoomSerialSession:
    def __init__(self, device: DivoomSerialDevice) -> None:
        self.device = device
        self.serial: serial.Serial | None = None

    async def __aenter__(self) -> "DivoomSerialSession":
        self.serial = serial.Serial(
            self.device.port,
            self.device.baudrate,
            timeout=1,
            write_timeout=3,
        )
        await asyncio.sleep(0.2)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.serial and self.serial.is_open:
            self.serial.close()

    async def send_image(self, image: Image.Image, delay_ms: int = 900) -> None:
        await self.send_packets([make_single_image_packet(image)])

    async def send_packets(self, packets: Iterable[bytes]) -> None:
        if self.serial is None:
            raise RuntimeError("Divoom serial session is not open")
        for packet in packets:
            written = self.serial.write(packet)
            self.serial.flush()
            if written != len(packet):
                raise RuntimeError(f"Only wrote {written}/{len(packet)} bytes to {self.device.port}")
            await asyncio.sleep(0.04)
