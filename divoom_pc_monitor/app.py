from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Optional

import typer
from PIL import Image, ImageDraw
from rich.console import Console

from .device import DivoomBleDevice
from .games import GameDetector
from .metrics import MetricsSampler
from .notifications import TelegramAlert, WindowsTelegramWatcher
from .render import DashboardRenderer, render_game, render_telegram, text3
from .serial_device import DivoomSerialDevice


cli = typer.Typer(add_completion=False)
console = Console()


def _load_address(address: Optional[str]) -> str:
    return address or "B1:21:81:29:E2:4A"


@cli.command()
def scan() -> None:
    """Show nearby Divoom-like BLE devices."""
    asyncio.run(DivoomBleDevice().find())


@cli.command()
def test(
    address: Optional[str] = typer.Option(None, "--address", "-a"),
    port: str = typer.Option("COM7", "--port", "-p"),
    ble: bool = typer.Option(False, "--ble"),
    text: str = typer.Option("OK", "--text", "-t"),
) -> None:
    """Send a tiny test card to the display."""
    img = Image.new("RGB", (16, 16), (3, 5, 13))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 15, 15), outline=(0, 222, 255))
    text3(draw, (4, 5), text[:2].upper(), (230, 244, 255))
    device = DivoomBleDevice(address=_load_address(address)) if ble else DivoomSerialDevice(port=port)
    asyncio.run(device.send_image(img, delay_ms=1000))
    console.print("[green]Test frame sent.[/green]")


@cli.command()
def tg_test(
    port: str = typer.Option("COM7", "--port", "-p"),
    sender: str = typer.Option("Telegram", "--sender", "-s"),
) -> None:
    """Show the Telegram overlay once, without waiting for a real notification."""
    img = render_telegram(sender, count=1, tick=0)
    asyncio.run(DivoomSerialDevice(port=port).send_image(img, delay_ms=1000))
    console.print("[green]Telegram test frame sent.[/green]")


@cli.command()
def game_status() -> None:
    """Print the currently detected League or Steam game."""
    status = GameDetector().current()
    if status is None:
        console.print("[yellow]No active League match or Steam game detected.[/yellow]")
        return
    console.print(
        f"[green]{status.kind}[/green] title={status.title!r} "
        f"subtitle={status.subtitle!r} mode={status.mode!r} "
        f"kda={status.kills}/{status.deaths}/{status.assists} "
        f"elapsed={status.elapsed_seconds}"
    )


@cli.command()
def game_test(
    port: str = typer.Option("COM7", "--port", "-p"),
    kind: str = typer.Option("lol", "--kind"),
    tick: int = typer.Option(0, "--tick"),
) -> None:
    """Show a sample game overlay once."""
    img = render_game(
        kind=kind,
        title="LOL" if kind == "lol" else "STM",
        subtitle="Ahri" if kind == "lol" else "Steam",
        elapsed_seconds=742,
        tick=tick,
        mode="RIFT",
        champion="Ahri",
        kills=3,
        deaths=1,
        assists=7,
    )
    asyncio.run(DivoomSerialDevice(port=port).send_image(img, delay_ms=1000))
    console.print("[green]Game test frame sent.[/green]")


@cli.command()
def preview(path: Path = typer.Option(Path("preview.png"), "--path", "-p")) -> None:
    """Render one dashboard frame as a PNG for quick visual checks."""
    metrics = MetricsSampler().sample()
    img = DashboardRenderer().render(metrics, tick=1, now=time.monotonic())
    img.resize((256, 256), Image.Resampling.NEAREST).save(path)
    console.print(f"[green]Saved[/green] {path.resolve()}")


@cli.command()
def run(
    address: Optional[str] = typer.Option(None, "--address", "-a"),
    port: str = typer.Option("COM7", "--port", "-p"),
    ble: bool = typer.Option(False, "--ble"),
    fps: float = typer.Option(1.0, "--fps", min=0.2, max=4.0),
    telegram: bool = typer.Option(True, "--telegram/--no-telegram"),
    frames: Optional[int] = typer.Option(None, "--frames", min=1),
) -> None:
    """Run realtime PC monitoring on the DitooMic."""
    asyncio.run(
        _run(
            address=_load_address(address),
            port=port,
            ble=ble,
            fps=fps,
            telegram=telegram,
            frames=frames,
        )
    )


async def _run(address: str, port: str, ble: bool, fps: float, telegram: bool, frames: int | None) -> None:
    device = DivoomBleDevice(address=address) if ble else DivoomSerialDevice(port=port)
    sampler = MetricsSampler()
    renderer = DashboardRenderer()
    games = GameDetector()
    alerts: asyncio.Queue[TelegramAlert] = asyncio.Queue()
    current_alert: TelegramAlert | None = None
    alert_count = 0

    if telegram:
        watcher = WindowsTelegramWatcher(alerts)
        allowed = await watcher.start()
        if allowed:
            console.print("[cyan]Telegram Windows notifications are being watched.[/cyan]")
        else:
            console.print("[yellow]Windows notification access is not enabled; metrics will still run.[/yellow]")

    target = address if ble else port
    console.print(f"[green]Streaming to DitooMic at {target}. Press Ctrl+C to stop.[/green]")
    tick = 0
    interval = 1.0 / fps
    sent = 0
    while frames is None or sent < frames:
        try:
            async with device.session() as session:
                while frames is None or sent < frames:
                    frame_started = time.monotonic()
                    while not alerts.empty():
                        current_alert = await alerts.get()
                        alert_count += 1

                    metrics = sampler.sample()
                    game = games.current()
                    if current_alert and current_alert.alive():
                        image = render_telegram(current_alert.sender, alert_count, tick)
                    elif game:
                        image = render_game(
                            game.kind,
                            game.title,
                            game.subtitle,
                            game.elapsed_seconds,
                            tick,
                            game.mode,
                            game.champion,
                            game.kills,
                            game.deaths,
                            game.assists,
                        )
                    else:
                        current_alert = None
                        alert_count = 0
                        image = renderer.render(metrics, tick=tick, now=time.monotonic())

                    await session.send_image(image, delay_ms=max(250, int(interval * 1000)))
                    await asyncio.sleep(max(0.0, interval - (time.monotonic() - frame_started)))
                    tick += 1
                    sent += 1
        except Exception as exc:
            console.print(f"[red]Divoom send failed:[/red] {exc}")
            await asyncio.sleep(2.5)


if __name__ == "__main__":
    cli()
