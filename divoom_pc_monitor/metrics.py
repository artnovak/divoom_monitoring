from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass

import psutil


@dataclass(slots=True)
class PcMetrics:
    cpu: float
    ram: float
    disk: float
    net_down_kbps: float
    net_up_kbps: float
    gpu: float | None = None
    gpu_temp: float | None = None
    gpu_mem: float | None = None


class MetricsSampler:
    def __init__(self) -> None:
        self._last_net = psutil.net_io_counters()
        self._last_time = time.monotonic()
        psutil.cpu_percent(interval=None)

    def sample(self) -> PcMetrics:
        now = time.monotonic()
        net = psutil.net_io_counters()
        elapsed = max(0.001, now - self._last_time)

        down_kbps = (net.bytes_recv - self._last_net.bytes_recv) * 8 / elapsed / 1000
        up_kbps = (net.bytes_sent - self._last_net.bytes_sent) * 8 / elapsed / 1000

        self._last_net = net
        self._last_time = now

        gpu, gpu_temp, gpu_mem = _sample_nvidia()
        return PcMetrics(
            cpu=psutil.cpu_percent(interval=None),
            ram=psutil.virtual_memory().percent,
            disk=psutil.disk_usage("C:\\").percent,
            net_down_kbps=max(0.0, down_kbps),
            net_up_kbps=max(0.0, up_kbps),
            gpu=gpu,
            gpu_temp=gpu_temp,
            gpu_mem=gpu_mem,
        )


def _sample_nvidia() -> tuple[float | None, float | None, float | None]:
    query = "utilization.gpu,temperature.gpu,memory.used,memory.total"
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                f"--query-gpu={query}",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=1.5,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        return None, None, None

    line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    values = [float(part) for part in re.findall(r"\d+(?:\.\d+)?", line)]
    if len(values) < 4:
        return None, None, None

    util, temp, used, total = values[:4]
    return util, temp, (used / total * 100.0) if total else None
