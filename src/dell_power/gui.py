"""Dell Power Manager - GTK3 Graphical User Interface."""
from __future__ import annotations
import sys
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GLib", "2.0")
from gi.repository import GLib, Gtk, Gdk

from .battery import BatteryReader, BatteryStats
from .controller import DellPowerController, PROFILES

CSS_DATA = b"""
window {
    background-color: #f6f8fa;
}
.card {
    background-color: #ffffff;
    border-radius: 12px;
    border: 1px solid #e1e4e8;
    padding: 16px;
    margin-bottom: 12px;
}
.battery-percent {
    font-size: 32px;
    font-weight: bold;
    color: #1a73e8;
}
.battery-subtext {
    font-size: 13px;
    color: #586069;
}
.status-pill {
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 12px;
    font-weight: 600;
}
.status-charging {
    background-color: #e6f4ea;
    color: #137333;
}
.status-discharging {
    background-color: #fce8e6;
    color: #c5221f;
}
.status-idle {
    background-color: #e8f0fe;
    color: #1a73e8;
}
.profile-title {
    font-weight: 600;
    font-size: 14px;
}
.profile-desc {
    font-size: 11px;
    color: #586069;
}
.btn-apply {
    background-color: #1a73e8;
    color: white;
    font-weight: bold;
    border-radius: 8px;
    padding: 10px 24px;
}
"""


class DellPowerWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Dell Power Manager")
        self.set_default_size(480, 640)
        self.set_position(Gtk.WindowPosition.CENTER)

        # HeaderBar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("Dell Power Manager")
        header.set_subtitle("Battery Longevity & Charge Control")
        self.set_titlebar(header)

        # Apply CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS_DATA)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Main Layout
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.add(scrolled)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        scrolled.add(main_box)

        # 1. Telemetry Card
        main_box.pack_start(self._build_telemetry_card(), False, False, 0)

        # 2. Profiles Card
        main_box.pack_start(self._build_profiles_card(), False, False, 0)

        # 3. Action Area
        main_box.pack_start(self._build_actions_card(), False, False, 0)

        # Initial populate & timer
        self._update_telemetry()
        self._sync_active_profile()
        GLib.timeout_add_seconds(2, self._on_timer_tick)

    def _build_telemetry_card(self) -> Gtk.Box:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("card")

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card.pack_start(top_row, False, False, 0)

        self.lbl_percent = Gtk.Label(label="--%")
        self.lbl_percent.get_style_context().add_class("battery-percent")
        top_row.pack_start(self.lbl_percent, False, False, 0)

        v_sub = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.lbl_state = Gtk.Label(label="Reading battery status...")
        self.lbl_state.set_xalign(0.0)
        self.lbl_state.get_style_context().add_class("battery-subtext")
        v_sub.pack_start(self.lbl_state, False, False, 0)

        self.lbl_health = Gtk.Label(label="Health: --%")
        self.lbl_health.set_xalign(0.0)
        self.lbl_health.get_style_context().add_class("battery-subtext")
        v_sub.pack_start(self.lbl_health, False, False, 0)

        top_row.pack_start(v_sub, True, True, 0)

        self.pill_status = Gtk.Label(label="Charging")
        self.pill_status.get_style_context().add_class("status-pill")
        top_row.pack_end(self.pill_status, False, False, 0)

        # Progress bar
        self.progress_battery = Gtk.ProgressBar()
        self.progress_battery.set_show_text(False)
        card.pack_start(self.progress_battery, False, False, 4)

        # Detail Stats Grid
        grid = Gtk.Grid()
        grid.set_column_spacing(24)
        grid.set_row_spacing(4)
        grid.set_margin_top(4)

        self.lbl_power = Gtk.Label(label="Power: -- W", xalign=0.0)
        self.lbl_voltage = Gtk.Label(label="Voltage: -- V", xalign=0.0)
        self.lbl_cycles = Gtk.Label(label="Cycles: 0", xalign=0.0)
        self.lbl_capacity_mah = Gtk.Label(label="Capacity: -- / -- mAh", xalign=0.0)

        for l in (self.lbl_power, self.lbl_voltage, self.lbl_cycles, self.lbl_capacity_mah):
            l.get_style_context().add_class("battery-subtext")

        grid.attach(self.lbl_power, 0, 0, 1, 1)
        grid.attach(self.lbl_voltage, 1, 0, 1, 1)
        grid.attach(self.lbl_capacity_mah, 0, 1, 1, 1)
        grid.attach(self.lbl_cycles, 1, 1, 1, 1)

        card.pack_start(grid, False, False, 0)
        return card

    def _build_profiles_card(self) -> Gtk.Box:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.get_style_context().add_class("card")

        title = Gtk.Label(label="<b>Charging Profiles &amp; Limits</b>", use_markup=True, xalign=0.0)
        card.pack_start(title, False, False, 0)

        self.radio_group = None
        self.profile_radios: dict[str, Gtk.RadioButton] = {}

        # 1. 50% limit (Default Recommended)
        self._add_profile_option(
            card,
            key="limit_50",
            title="🛡️ Limit to 50% (Recommended for AC/Desk)",
            desc="Stops charging at 55%, resumes at 50%. Maximizes battery longevity.",
        )

        # 2. 80% limit
        self._add_profile_option(
            card,
            key="limit_80",
            title="⚖️ Limit to 80% (Balanced Daily Use)",
            desc="Stops charging at 80%, resumes at 75%. Good mix of battery life and mobility.",
        )

        # 3. Primarily AC Use
        self._add_profile_option(
            card,
            key="primarily_ac",
            title="🔌 Primarily AC Use",
            desc="Dell BIOS hardware profile for users who operate primarily on AC power.",
        )

        # 4. Standard 100%
        self._add_profile_option(
            card,
            key="standard",
            title="⚡ Standard (100% Full Charge)",
            desc="Charges battery completely to 100% capacity at normal safe rate.",
        )

        # 5. ExpressCharge
        self._add_profile_option(
            card,
            key="express",
            title="🚀 ExpressCharge (Rapid 100%)",
            desc="Charges to 100% in minimal time using Dell fast-charging algorithm.",
        )

        # 6. Custom limits
        self._add_profile_option(
            card,
            key="custom",
            title="⚙️ Custom Thresholds",
            desc="Configure exact custom start and stop percentages manually.",
        )

        # Custom Spinners Box
        self.custom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.custom_box.set_margin_start(28)
        self.custom_box.set_margin_top(4)

        lbl_start = Gtk.Label(label="Start (%):")
        self.spin_start = Gtk.SpinButton.new_with_range(50, 95, 1)
        self.spin_start.set_value(50)

        lbl_stop = Gtk.Label(label="Stop (%):")
        self.spin_stop = Gtk.SpinButton.new_with_range(55, 100, 1)
        self.spin_stop.set_value(55)

        self.custom_box.pack_start(lbl_start, False, False, 0)
        self.custom_box.pack_start(self.spin_start, False, False, 0)
        self.custom_box.pack_start(lbl_stop, False, False, 0)
        self.custom_box.pack_start(self.spin_stop, False, False, 0)

        card.pack_start(self.custom_box, False, False, 0)
        return card

    def _add_profile_option(self, container: Gtk.Box, key: str, title: str, desc: str):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)

        radio = Gtk.RadioButton.new_from_widget(self.radio_group)
        if self.radio_group is None:
            self.radio_group = radio

        lbl_title = Gtk.Label(label=title, xalign=0.0)
        lbl_title.get_style_context().add_class("profile-title")

        lbl_desc = Gtk.Label(label=desc, xalign=0.0)
        lbl_desc.get_style_context().add_class("profile-desc")
        lbl_desc.set_line_wrap(True)

        vbox.pack_start(lbl_title, False, False, 0)
        vbox.pack_start(lbl_desc, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.pack_start(radio, False, False, 0)
        row.pack_start(vbox, True, True, 0)

        container.pack_start(row, False, False, 2)
        self.profile_radios[key] = radio
        radio.connect("toggled", self._on_radio_toggled, key)

    def _build_actions_card(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        btn_apply = Gtk.Button(label="Apply Settings")
        btn_apply.get_style_context().add_class("suggested-action")
        btn_apply.get_style_context().add_class("btn-apply")
        btn_apply.connect("clicked", self._on_apply_clicked)
        box.pack_start(btn_apply, False, False, 0)

        self.lbl_feedback = Gtk.Label(label="", xalign=0.5)
        self.lbl_feedback.get_style_context().add_class("battery-subtext")
        box.pack_start(self.lbl_feedback, False, False, 0)

        return box

    def _on_radio_toggled(self, radio: Gtk.RadioButton, key: str):
        if radio.get_active():
            self.custom_box.set_sensitive(key == "custom")

    def _sync_active_profile(self):
        cfg = DellPowerController.load_config()
        if cfg.mode == "custom":
            if cfg.custom_start == 50 and cfg.custom_end == 55:
                self.profile_radios["limit_50"].set_active(True)
            elif cfg.custom_start == 75 and cfg.custom_end == 80:
                self.profile_radios["limit_80"].set_active(True)
            else:
                self.profile_radios["custom"].set_active(True)
                self.spin_start.set_value(cfg.custom_start)
                self.spin_stop.set_value(cfg.custom_end)
        elif cfg.mode in self.profile_radios:
            self.profile_radios[cfg.mode].set_active(True)
        else:
            self.profile_radios["limit_50"].set_active(True)

    def _update_telemetry(self):
        stats = BatteryReader.get_stats()
        if not stats.present:
            self.lbl_percent.set_text("N/A")
            self.lbl_state.set_text("No battery detected")
            return

        self.lbl_percent.set_text(f"{stats.capacity}%")
        self.progress_battery.set_fraction(stats.capacity / 100.0)
        self.lbl_state.set_text(f"State: {stats.status_display}")
        self.lbl_health.set_text(f"Battery Health: {stats.health}%")

        self.lbl_power.set_text(f"Power: {stats.power_watts} W")
        self.lbl_voltage.set_text(f"Voltage: {stats.voltage_volts} V")
        self.lbl_cycles.set_text(f"Cycles: {stats.cycle_count}")
        self.lbl_capacity_mah.set_text(f"Capacity: {stats.charge_full_mah} / {stats.charge_design_mah} mAh")

        # Pill styling
        st = self.pill_status.get_style_context()
        st.remove_class("status-charging")
        st.remove_class("status-discharging")
        st.remove_class("status-idle")

        if not stats.ac_online:
            self.pill_status.set_text("On Battery")
            st.add_class("status-discharging")
        elif stats.status.lower() == "charging":
            self.pill_status.set_text("Charging")
            st.add_class("status-charging")
        else:
            self.pill_status.set_text("Limit Active")
            st.add_class("status-idle")

    def _on_timer_tick(self) -> bool:
        self._update_telemetry()
        return True

    def _on_apply_clicked(self, _button):
        selected_key = None
        for k, radio in self.profile_radios.items():
            if radio.get_active():
                selected_key = k
                break

        if not selected_key:
            return

        self.lbl_feedback.set_text("Applying settings to Dell BIOS...")

        if selected_key == "custom":
            start = int(self.spin_start.get_value())
            stop = int(self.spin_stop.get_value())
            ok, msg = DellPowerController.apply_custom_limits(start, stop, notify=True)
        else:
            ok, msg = DellPowerController.apply_profile(selected_key, notify=True)

        if ok:
            self.lbl_feedback.set_markup(f"<span color='#137333'><b>✓ {msg}</b></span>")
        else:
            self.lbl_feedback.set_markup(f"<span color='#c5221f'><b>✗ Error: {msg}</b></span>")


def main():
    app = DellPowerWindow()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
