"""Dell Power Manager Command-Line Interface."""
from __future__ import annotations
import argparse
import sys
from .battery import BatteryReader
from .controller import DellPowerController, PROFILES


def print_status():
    stats = BatteryReader.get_stats()
    cfg = DellPowerController.load_config()

    print("=" * 55)
    print("           Dell Power Manager - Battery Status          ")
    print("=" * 55)

    if not stats.present:
        print("  [!] No battery detected on system.")
        print("=" * 55)
        return

    # Visual gauge bar
    bar_width = 30
    filled = int((stats.capacity / 100.0) * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)

    print(f"  Level:      [{bar}] {stats.capacity}%")
    print(f"  State:      {stats.status_display}")
    print(f"  Power:      {stats.power_watts} W @ {stats.voltage_volts} V")
    print(f"  AC Adapter: {'Connected (Online)' if stats.ac_online else 'Disconnected (Battery)'}")
    print("-" * 55)
    print(f"  Health:     {stats.health}% ({stats.charge_full_mah} / {stats.charge_design_mah} mAh)")
    print(f"  Cycles:     {stats.cycle_count}")
    print("-" * 55)

    supported, _ = DellPowerController.check_hardware_support()
    if not supported:
        print("  OS Charge Control: ⚠️  UNSUPPORTED (AMD Firmware Restriction)")
        print("-" * 55)
        print("  [!] HOW TO LIMIT CHARGING ON THIS LAPTOP:")
        print("  Dell G15 5515 (AMD) requires setting limits in BIOS Setup:")
        print("    1. Reboot your laptop and tap F2 repeatedly at Dell logo.")
        print("    2. Navigate to: Power -> Primary Battery Charge Configuration.")
        print("    3. Change to 'Custom' (Start: 50%, Stop: 55% or 60%).")
        print("       (Or choose 'Primarily AC Use').")
        print("    4. Press F10 (Save & Exit).")
        print("  (The Embedded Controller enforces this limit in hardware!)")
        print("=" * 55)
    else:
        if cfg.mode == "custom":
            mode_desc = f"Custom Limit (Start: {cfg.custom_start}%, Stop: {cfg.custom_end}%)"
        else:
            mode_desc = cfg.description or cfg.mode.replace("_", " ").title()

        print(f"  Active Profile: 🛡️  {mode_desc}")
        print("=" * 55)


def main():
    parser = argparse.ArgumentParser(
        prog="dell-power",
        description="Dell Power Manager CLI: Limit battery charging to 50%, 80%, etc., and manage profiles",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status
    subparsers.add_parser("status", help="Show current battery telemetry and active charging policy")

    # limit
    limit_parser = subparsers.add_parser("limit", help="Set charge limit to 50% or 80%")
    limit_parser.add_argument("percent", type=int, choices=[50, 60, 70, 80, 85, 90], help="Target charge limit (e.g. 50 or 80)")

    # custom
    custom_parser = subparsers.add_parser("custom", help="Set custom start and stop charge percentages")
    custom_parser.add_argument("start", type=int, help="Start charging when below this percent (50-95)")
    custom_parser.add_argument("end", type=int, help="Stop charging when reaching this percent (55-100)")

    # mode
    mode_parser = subparsers.add_parser("mode", help="Set predefined charging mode")
    mode_parser.add_argument(
        "name",
        choices=["primarily_ac", "adaptive", "standard", "express"],
        help="Charging profile mode name",
    )

    # apply
    subparsers.add_parser("apply", help="Re-apply saved charging configuration (used by systemd)")

    # gui
    subparsers.add_parser("gui", help="Open graphical interface")

    args = parser.parse_args()

    if not args.command:
        if len(sys.argv) == 1:
            print_status()
            sys.exit(0)
        args.command = "status"

    if args.command == "status":
        print_status()
    elif args.command == "limit":
        target = args.percent
        # Dell custom interval requires start and end (end >= start + 5)
        if target == 50:
            start, end = 50, 55
        elif target == 80:
            start, end = 75, 80
        else:
            start, end = max(50, target - 5), target

        ok, msg = DellPowerController.apply_custom_limits(start, end, notify=True)
        if ok:
            print(f"[✓] {msg}")
        else:
            print(f"[✗] Error: {msg}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "custom":
        ok, msg = DellPowerController.apply_custom_limits(args.start, args.end, notify=True)
        if ok:
            print(f"[✓] {msg}")
        else:
            print(f"[✗] Error: {msg}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "mode":
        ok, msg = DellPowerController.apply_mode(args.name, notify=True)
        if ok:
            print(f"[✓] {msg}")
        else:
            print(f"[✗] Error: {msg}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "apply":
        ok, msg = DellPowerController.reapply_saved(notify=False)
        if ok:
            print(f"[✓] Reapplied saved configuration: {msg}")
        else:
            supported, _ = DellPowerController.check_hardware_support()
            if not supported:
                print(f"[!] Notice: Hardware-level BIOS configuration active ({msg})")
                sys.exit(0)
            print(f"[✗] Error: {msg}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "gui":
        from .gui import main as gui_main
        gui_main()


if __name__ == "__main__":
    main()
