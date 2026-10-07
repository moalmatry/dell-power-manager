"""Battery telemetry and hardware information reader."""
from __future__ import annotations
import glob
import os
from dataclasses import dataclass


@dataclass
class BatteryStats:
    present: bool
    path: str
    capacity: int
    status: str
    health: float
    voltage_volts: float
    power_watts: float
    charge_full_mah: int
    charge_design_mah: int
    cycle_count: int
    ac_online: bool
    model_name: str
    manufacturer: str

    @property
    def status_display(self) -> str:
        if not self.ac_online:
            return f"Discharging ({self.status})"
        if self.status.lower() == "charging":
            return "Charging"
        if self.status.lower() in ("not charging", "idle"):
            return "Plugged in, Idle (Limit Enforced)"
        if self.status.lower() == "full":
            return "Fully Charged"
        return self.status


class BatteryReader:
    @staticmethod
    def find_battery_path() -> str | None:
        """Find the sysfs path for the primary laptop battery."""
        preferred = [
            "/sys/class/power_supply/BAT1",
            "/sys/class/power_supply/BAT0",
        ]
        for p in preferred:
            if os.path.exists(p):
                return p

        candidates = glob.glob("/sys/class/power_supply/BAT*")
        return candidates[0] if candidates else None

    @staticmethod
    def _read_file(path: str, default: str = "") -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            return default

    @classmethod
    def get_stats(cls) -> BatteryStats:
        """Read and return current battery statistics."""
        bat_path = cls.find_battery_path()
        if not bat_path:
            return BatteryStats(
                present=False,
                path="",
                capacity=0,
                status="No Battery",
                health=100.0,
                voltage_volts=0.0,
                power_watts=0.0,
                charge_full_mah=0,
                charge_design_mah=0,
                cycle_count=0,
                ac_online=False,
                model_name="Unknown",
                manufacturer="Unknown",
            )

        # Capacity
        try:
            capacity = int(cls._read_file(os.path.join(bat_path, "capacity"), "0"))
        except ValueError:
            capacity = 0

        # Status
        status = cls._read_file(os.path.join(bat_path, "status"), "Unknown")

        # Voltage
        try:
            voltage_uV = int(cls._read_file(os.path.join(bat_path, "voltage_now"), "0"))
            voltage_volts = round(voltage_uV / 1_000_000.0, 2)
        except ValueError:
            voltage_volts = 0.0

        # Current & Power
        power_watts = 0.0
        try:
            power_uW = cls._read_file(os.path.join(bat_path, "power_now"))
            if power_uW:
                power_watts = round(int(power_uW) / 1_000_000.0, 2)
            else:
                curr_uA = int(cls._read_file(os.path.join(bat_path, "current_now"), "0"))
                power_watts = round((curr_uA * voltage_uV) / 1_000_000_000_000.0, 2)
        except (ValueError, ZeroDivisionError):
            power_watts = 0.0

        # Charge / Energy Full vs Design
        c_full = 0
        c_design = 0
        for prefix in ("charge", "energy"):
            full_str = cls._read_file(os.path.join(bat_path, f"{prefix}_full"))
            design_str = cls._read_file(os.path.join(bat_path, f"{prefix}_full_design"))
            if full_str and design_str:
                try:
                    c_full = int(full_str)
                    c_design = int(design_str)
                    break
                except ValueError:
                    pass

        health = 100.0
        if c_full > 0 and c_design > 0:
            health = round(min(100.0, (c_full / c_design) * 100.0), 1)

        # Cycle Count
        try:
            cycles = int(cls._read_file(os.path.join(bat_path, "cycle_count"), "0"))
        except ValueError:
            cycles = 0

        # AC Online
        ac_online = False
        for ac_path in glob.glob("/sys/class/power_supply/AC*") + glob.glob("/sys/class/power_supply/ADP*"):
            online_str = cls._read_file(os.path.join(ac_path, "online"), "0")
            if online_str == "1":
                ac_online = True
                break

        model = cls._read_file(os.path.join(bat_path, "model_name"), "Dell Battery")
        mfg = cls._read_file(os.path.join(bat_path, "manufacturer"), "Dell")

        return BatteryStats(
            present=True,
            path=bat_path,
            capacity=capacity,
            status=status,
            health=health,
            voltage_volts=voltage_volts,
            power_watts=power_watts,
            charge_full_mah=c_full // 1000 if c_full else 0,
            charge_design_mah=c_design // 1000 if c_design else 0,
            cycle_count=cycles,
            ac_online=ac_online,
            model_name=model,
            manufacturer=mfg,
        )
