from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable

from bleak import BleakClient, BleakScanner
from PIL import Image

from .protocol import AnimationTransfer, make_single_frame_animation, make_single_image_packet


WRITE_CHARACTERISTIC = "49535343-8841-43f4-a8d4-ecbe34729bb3"


@dataclass(slots=True)
class DivoomBleDevice:
    address: str = "B1:21:81:29:E2:4A"
    characteristic: str = WRITE_CHARACTERISTIC
    ble_chunk_size: int = 20
    inter_chunk_delay: float = 0.012
    inter_packet_delay: float = 0.045

    async def find(self, timeout: float = 5.0) -> None:
        devices = await BleakScanner.discover(timeout=timeout)
        for device in devices:
            if device.address.upper() == self.address.upper() or "Ditoo" in (device.name or ""):
                print(f"{device.name or 'unknown'}  {device.address}")

    async def send_image(self, image: Image.Image, delay_ms: int = 900) -> None:
        await self.send_packets([make_single_image_packet(image)])

    async def send_packets(self, packets: Iterable[bytes]) -> None:
        async with self.session() as session:
            await session.send_packets(packets)

    def session(self) -> "DivoomBleSession":
        return DivoomBleSession(self)

    async def _write_stream(self, client: BleakClient, data: bytes) -> None:
        for i in range(0, len(data), self.ble_chunk_size):
            chunk = data[i : i + self.ble_chunk_size]
            await client.write_gatt_char(self.characteristic, chunk, response=False)
            await asyncio.sleep(self.inter_chunk_delay)


class DivoomBleSession:
    def __init__(self, device: DivoomBleDevice) -> None:
        self.device = device
        self.client: BleakClient | None = None

    async def __aenter__(self) -> "DivoomBleSession":
        self.client = BleakClient(self.device.address, timeout=20)
        await self.client.connect()
        if not self.client.is_connected:
            raise RuntimeError(f"Could not connect to {self.device.address}")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    async def send_image(self, image: Image.Image, delay_ms: int = 900) -> None:
        await self.send_packets([make_single_image_packet(image)])

    async def send_packets(self, packets: Iterable[bytes]) -> None:
        if self.client is None:
            raise RuntimeError("Divoom BLE session is not open")
        for packet in packets:
            await self.device._write_stream(self.client, packet)
            await asyncio.sleep(self.device.inter_packet_delay)
