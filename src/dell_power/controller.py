"""Dell Power Manager Controller.

Manages SMBIOS battery charging tokens, profiles, and persistence across reboots.
"""
from __future__ import annotations
import glob
import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from typing import Any

GLOBAL_CONFIG_PATH = "/etc/dell-power/config.json"
USER_CONFIG_PATH = os.path.expanduser("~/.config/dell-power/config.json")


@dataclass
class PowerProfile:
    mode: str  # "custom", "primarily_ac", "adaptive", "standard", "express"
    custom_start: int = 50
    custom_end: int = 55
    description: str = ""
    last_applied: float = 0.0


PROFILES: dict[str, dict[str, Any]] = {
    "limit_50": {
        "mode": "custom",
        "start": 50,
        "end": 55,
        "title": "Limit to 50%",
        "description": "Maximum battery health & storage mode (Start: 50%, Stop: 55%)",
    },
    "limit_80": {
        "mode": "custom",
        "start": 75,
        "end": 80,
        "title": "Limit to 80%",
        "description": "Balanced daily longevity mode (Start: 75%, Stop: 80%)",
    },
    "primarily_ac": {
        "mode": "primarily_ac",
        "start": 50,
        "end": 100,
        "title": "Primarily AC Use",
        "description": "Dell BIOS AC mode: lowers charge threshold to protect continuous plug-in use",
    },
    "standard": {
        "mode": "standard",
        "start": 50,
        "end": 100,
        "title": "Standard (100%)",
        "description": "Charges battery to full 100% capacity at normal rate",
    },
    "adaptive": {
        "mode": "adaptive",
        "start": 50,
        "end": 100,
        "title": "Adaptive Charge",
        "description": "Dell BIOS dynamically balances charging based on your usage habits",
    },
    "express": {
        "mode": "express",
        "start": 50,
        "end": 100,
        "title": "ExpressCharge",
        "description": "Rapid fast-charging algorithm to charge to 100% in minimal time",
    },
}


class DellPowerController:
    @staticmethod
    def _get_config_path() -> str:
        if os.geteuid() == 0 or os.path.exists(os.path.dirname(GLOBAL_CONFIG_PATH)):
            return GLOBAL_CONFIG_PATH
        return USER_CONFIG_PATH

    @classmethod
    def load_config(cls) -> PowerProfile:
        candidates = [GLOBAL_CONFIG_PATH, USER_CONFIG_PATH]
        existing = [p for p in candidates if os.path.exists(p)]
        if existing:
            best_path = max(existing, key=lambda p: os.path.getmtime(p))
            try:
                with open(best_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return PowerProfile(
                        mode=data.get("mode", "custom"),
                        custom_start=int(data.get("custom_start", 50)),
                        custom_end=int(data.get("custom_end", 55)),
                        description=data.get("description", ""),
                        last_applied=float(data.get("last_applied", 0.0)),
                    )
            except Exception:
                pass

        # Default is 50% battery health limit
        return PowerProfile(mode="custom", custom_start=50, custom_end=55, description="Limit to 50%")

    @classmethod
    def save_config(cls, profile: PowerProfile):
        for path in [GLOBAL_CONFIG_PATH, USER_CONFIG_PATH]:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(asdict(profile), f, indent=2)
            except OSError:
                pass

    @staticmethod
    def _run_privileged(cmd: list[str]) -> tuple[bool, str]:
        """Runs a command with root privileges (sudo if non-root, or direct if root)."""
        if os.geteuid() == 0:
            full_cmd = cmd
        else:
            full_cmd = ["sudo", "-n"] + cmd

        try:
            res = subprocess.run(full_cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0:
                return True, res.stdout.strip()

            # If sudo -n failed due to password needed and pkexec exists:
            if os.geteuid() != 0 and shutil.which("pkexec"):
                res_pk = subprocess.run(["pkexec"] + cmd, capture_output=True, text=True, check=False)
                if res_pk.returncode == 0:
                    return True, res_pk.stdout.strip()
                return False, res_pk.stderr.strip() or res_pk.stdout.strip()

            return False, res.stderr.strip() or res.stdout.strip()
        except Exception as e:
            return False, str(e)

    @classmethod
    def send_notification(cls, title: str, message: str, icon: str = "battery-charging"):
        """Delivers a desktop notification to all active graphical user sessions."""
        for user_run in glob.glob("/run/user/[0-9]*"):
            uid = os.path.basename(user_run)
            bus = f"unix:path={user_run}/bus"
            try:
                subprocess.run(
                    ["notify-send", "-i", icon, title, message],
                    env={"DBUS_SESSION_BUS_ADDRESS": bus, "PATH": "/usr/bin:/bin"},
                    user=int(uid),
                    check=False,
                )
            except Exception:
                pass

    @classmethod
    def apply_custom_limits(cls, start: int, end: int, notify: bool = True) -> tuple[bool, str]:
        """Sets custom start and stop charging percentage thresholds."""
        if start < 50 or start > 95:
            return False, "Start threshold must be between 50% and 95%."
        if end < 55 or end > 100:
            return False, "Stop threshold must be between 55% and 100%."
        if end - start < 5:
            return False, "Stop threshold must be at least 5% greater than Start threshold."

        smbios_bin = shutil.which("smbios-battery-ctl") or "/usr/sbin/smbios-battery-ctl"
        if not os.path.exists(smbios_bin):
            return False, f"smbios-battery-ctl utility not found at {smbios_bin}."

        # 1. Set interval
        ok1, out1 = cls._run_privileged([smbios_bin, f"--set-custom-charge-interval={start}", str(end)])
        if not ok1:
            return False, f"Failed setting custom interval: {out1}"

        # 2. Set mode to custom
        ok2, out2 = cls._run_privileged([smbios_bin, "--set-charging-mode=custom"])
        if not ok2:
            return False, f"Failed setting custom mode: {out2}"

        # 3. Update configuration
        profile = PowerProfile(
            mode="custom",
            custom_start=start,
            custom_end=end,
            description=f"Custom: Start {start}%, Stop {end}%",
            last_applied=time.time(),
        )
        cls.save_config(profile)

        if notify:
            cls.send_notification(
                "Dell Power Manager",
                f"🛡️ Battery Charge Limit Active: Start {start}%, Stop {end}%",
                "battery-charging",
            )

        return True, f"Custom threshold applied: Start {start}%, Stop {end}%"

    @classmethod
    def apply_mode(cls, mode_name: str, notify: bool = True) -> tuple[bool, str]:
        """Sets standard charging mode: primarily_ac, adaptive, standard, express."""
        valid_modes = {"primarily_ac", "adaptive", "standard", "express"}
        if mode_name not in valid_modes:
            return False, f"Invalid mode '{mode_name}'. Valid choices: {', '.join(valid_modes)}"

        smbios_bin = shutil.which("smbios-battery-ctl") or "/usr/sbin/smbios-battery-ctl"
        if not os.path.exists(smbios_bin):
            return False, f"smbios-battery-ctl utility not found at {smbios_bin}."

        ok, out = cls._run_privileged([smbios_bin, f"--set-charging-mode={mode_name}"])
        if not ok:
            return False, f"Failed setting mode {mode_name}: {out}"

        cfg = cls.load_config()
        cfg.mode = mode_name
        cfg.description = mode_name.replace("_", " ").title()
        cfg.last_applied = time.time()
        cls.save_config(cfg)

        if notify:
            cls.send_notification(
                "Dell Power Manager",
                f"⚡ Battery profile updated: {cfg.description}",
                "battery-charging",
            )

        return True, f"Charging mode '{mode_name}' applied successfully."

    @classmethod
    def apply_profile(cls, profile_key: str, notify: bool = True) -> tuple[bool, str]:
        """Applies a named profile ('limit_50', 'limit_80', 'primarily_ac', etc.)."""
        if profile_key not in PROFILES:
            return False, f"Unknown profile: {profile_key}"

        prof = PROFILES[profile_key]
        if prof["mode"] == "custom":
            return cls.apply_custom_limits(prof["start"], prof["end"], notify=notify)
        else:
            return cls.apply_mode(prof["mode"], notify=notify)

    @classmethod
    def reapply_saved(cls, notify: bool = False) -> tuple[bool, str]:
        """Re-applies the saved profile to BIOS. Used on boot and system resume."""
        cfg = cls.load_config()
        if cfg.mode == "custom":
            return cls.apply_custom_limits(cfg.custom_start, cfg.custom_end, notify=notify)
        else:
            return cls.apply_mode(cfg.mode, notify=notify)
