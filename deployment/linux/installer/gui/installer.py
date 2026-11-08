"""GTK4 wizard for the existing CareQFlow Linux installer."""

from __future__ import annotations

import ipaddress
import os
import time
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

NETWORK_MODES = ("Preserve", "LocalOnly", "SecureLan", "Tailscale")
OPERATIONS = ("install", "upgrade", "repair", "rollback", "uninstall")
INSTALL_SCRIPT = Path(__file__).resolve().parents[1] / "invoke-install.sh"
PACKAGE_ROOT = Path(__file__).resolve().parents[4]
INSTALL_STATE = Path("/etc/carequeue/install-state.env")
INSTALL_DIRECTORY = Path("/opt/carequeue")
PAGES = ("welcome", "operation", "network", "confirm")
LOCAL_ORIGIN = "https://careqflow.local"


def detect_installation() -> tuple[str, str]:
    """Return a cautious installation hint without elevated privileges."""
    try:
        state_exists = INSTALL_STATE.is_file()
    except OSError:
        state_exists = None

    try:
        directory_exists = INSTALL_DIRECTORY.is_dir()
    except OSError:
        directory_exists = None

    if state_exists:
        return (
            "Existing installation detected",
            (
                "An installation state file exists. Its contents may require "
                "administrator access."
            ),
        )

    if directory_exists:
        if state_exists is None:
            return (
                "Existing installation detected",
                (
                    "The application directory exists, but installation state is "
                    "protected or inaccessible. The privileged installer will verify it."
                ),
            )

        return (
            "Possible existing installation",
            (
                "The application directory exists but no installation state file "
                "was found. Verify the installation before proceeding."
            ),
        )

    if state_exists is None or directory_exists is None:
        return (
            "Installation status unavailable",
            (
                "Installation paths could not be fully inspected without administrator "
                "access. The privileged installer will verify them."
            ),
        )

    return (
        "No existing installation detected",
        (
            "No standard installation was found. Custom installation paths "
            "are not detected."
        ),
    )


def build_command(operation: str, network_mode: str, address: str) -> list[str]:
    """Validate wizard inputs and construct arguments without invoking a shell."""
    if operation not in OPERATIONS:
        raise ValueError("Unsupported installation operation.")
    if network_mode not in NETWORK_MODES:
        raise ValueError("Unsupported network mode.")

    command = ["sudo", "bash", str(INSTALL_SCRIPT), operation]
    if operation in {"rollback", "uninstall"}:
        return command

    if network_mode == "Preserve":
        if operation == "install":
            raise ValueError("Choose a network mode for a new installation.")
        return command

    if network_mode == "LocalOnly":
        return command + ["--network-mode", "LocalOnly"]

    try:
        ip = ipaddress.IPv4Address(address.strip())
    except ipaddress.AddressValueError as exc:
        raise ValueError(
            "Enter a valid IPv4 address, without https:// or a port."
        ) from exc

    if network_mode == "SecureLan" and not any(
        ip in ipaddress.IPv4Network(subnet)
        for subnet in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
    ):
        raise ValueError("Secure LAN requires an RFC1918 IPv4 address.")
    if network_mode == "Tailscale" and ip not in ipaddress.IPv4Network("100.64.0.0/10"):
        raise ValueError("Tailscale requires an address in 100.64.0.0/10.")

    return command + [
        "--network-mode",
        network_mode,
        "--application-origin",
        f"https://{ip}",
    ]


def parse_installer_result(raw: str) -> int:
    """Accept only an ordinary shell exit status, never arbitrary data."""
    value = raw.strip()
    if not value.isascii() or not value.isdecimal():
        raise ValueError("Invalid installer result received.")
    code = int(value)
    if not 0 <= code <= 255:
        raise ValueError("Installer exit code is out of range.")
    return code


def interruption_detected(
    *,
    worker_pid: int | None,
    worker_alive: bool,
    terminal_return: int | None,
    elapsed: int,
) -> bool:
    """Flag missing workers, launcher errors, or a terminal that never started."""
    return (
        (worker_pid is not None and not worker_alive)
        or (terminal_return is not None and terminal_return != 0)
        or (worker_pid is None and terminal_return is not None and elapsed >= 8)
    )


def main() -> int:
    try:
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gio, GLib, Gtk
    except (ImportError, ValueError) as exc:
        print(
            "GTK4 bindings are required: install python3-gi and gir1.2-gtk-4.0 "
            "and launch with system python3.",
            file=sys.stderr,
        )
        print(str(exc), file=sys.stderr)
        return 1

    class InstallerWindow(Gtk.ApplicationWindow):
        def __init__(self, application: Gtk.Application) -> None:
            super().__init__(application=application, title="CareQFlow Setup")
            self.set_default_size(620, 500)
            self.page_index = 0
            self.result_directory: tempfile.TemporaryDirectory[str] | None = None
            self.result_path: Path | None = None
            self.worker_pid_path: Path | None = None
            self.started_at: float | None = None
            self.missing_worker_since: float | None = None
            self.terminal_process: subprocess.Popen[bytes] | None = None
            self.running_operation: str | None = None
            self.operation_origin = LOCAL_ORIGIN

            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            root.set_margin_top(24)
            root.set_margin_bottom(24)
            root.set_margin_start(24)
            root.set_margin_end(24)
            self.set_child(root)

            heading = Gtk.Label(label="CareQFlow Linux Setup", xalign=0)
            heading.add_css_class("title-1")
            root.append(heading)

            self.progress = Gtk.Label(xalign=0)
            self.progress.add_css_class("dim-label")
            root.append(self.progress)

            self.stack = Gtk.Stack()
            self.stack.set_vexpand(True)
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
            root.append(self.stack)

            self._create_welcome()
            self._create_operation()
            self._create_network()
            self._create_confirmation()
            self._create_running()
            self._create_result()

            self.status = Gtk.Label(xalign=0)
            self.status.set_wrap(True)
            root.append(self.status)

            controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            controls.set_halign(Gtk.Align.END)
            root.append(controls)

            self.back_button = Gtk.Button(label="Back")
            self.back_button.connect("clicked", self._back)
            controls.append(self.back_button)

            self.open_button = Gtk.Button(label="Open careqflow.local")
            self.open_button.connect("clicked", self._open_application)
            self.open_button.set_visible(False)
            controls.append(self.open_button)

            self.next_button = Gtk.Button(label="Next")
            self.next_button.add_css_class("suggested-action")
            self.next_button.connect("clicked", self._next)
            controls.append(self.next_button)

            self.connect("close-request", self._window_closing)
            self._show_page()

        @staticmethod
        def _page(spacing: int = 12) -> Gtk.Box:
            return Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)

        def _create_welcome(self) -> None:
            page = self._page()
            description = Gtk.Label(
                label="This wizard prepares CareQFlow installation choices. "
                "The existing Linux installer runs in a terminal for administrator "
                "authorization, license acceptance, and setup prompts.",
                xalign=0,
            )
            description.set_wrap(True)
            page.append(description)

            self.installation_title = Gtk.Label(xalign=0)
            self.installation_title.add_css_class("title-3")
            page.append(self.installation_title)
            self.installation_details = Gtk.Label(xalign=0)
            self.installation_details.set_wrap(True)
            page.append(self.installation_details)

            self.stack.add_named(page, "welcome")

        def _create_operation(self) -> None:
            page = self._page()
            page.append(Gtk.Label(label="Choose an operation", xalign=0))
            self.operation = Gtk.DropDown.new_from_strings(
                ("Install", "Upgrade", "Repair", "Rollback", "Uninstall")
            )
            self.operation.connect("notify::selected", self._operation_changed)
            page.append(self.operation)
            note = Gtk.Label(
                label="Upgrade, repair, rollback, and uninstall apply to an "
                "existing installation. The underlying installer performs "
                "its own validation before changing anything.",
                xalign=0,
            )
            note.set_wrap(True)
            page.append(note)
            self.stack.add_named(page, "operation")

        def _create_network(self) -> None:
            page = self._page()
            page.append(Gtk.Label(label="Network access", xalign=0))
            self.network = Gtk.DropDown.new_from_strings(
                ("Preserve existing", "Local Only", "Secure LAN", "Tailscale")
            )
            self.network.set_selected(1)
            self.network.connect("notify::selected", self._network_changed)
            page.append(self.network)

            self.network_hint = Gtk.Label(xalign=0)
            self.network_hint.set_wrap(True)
            page.append(self.network_hint)

            self.address_label = Gtk.Label(label="Server IPv4 address", xalign=0)
            page.append(self.address_label)
            self.address = Gtk.Entry()
            self.address.set_placeholder_text("192.168.1.25 or 100.100.100.100")
            page.append(self.address)
            self.stack.add_named(page, "network")
            self._network_changed()

        def _create_confirmation(self) -> None:
            page = self._page()
            title = Gtk.Label(label="Review your selections", xalign=0)
            title.add_css_class("title-3")
            page.append(title)
            self.summary = Gtk.Label(xalign=0)
            self.summary.set_wrap(True)
            self.summary.set_selectable(True)
            page.append(self.summary)
            note = Gtk.Label(
                label="Continue opens a terminal. No installation changes "
                "occur until you authorize the existing installer there.",
                xalign=0,
            )
            note.set_wrap(True)
            page.append(note)
            self.stack.add_named(page, "confirm")

        def _create_running(self) -> None:
            page = self._page()
            heading = Gtk.Label(label="Installation in progress", xalign=0)
            heading.add_css_class("title-3")
            page.append(heading)
            description = Gtk.Label(
                label="Complete administrator, license, and setup prompts in the "
                "installer terminal. Keep that terminal open until it finishes.",
                xalign=0,
            )
            description.set_wrap(True)
            page.append(description)

            self.activity = Gtk.ProgressBar()
            self.activity.set_show_text(False)
            page.append(self.activity)
            self.running_message = Gtk.Label(xalign=0)
            self.running_message.set_wrap(True)
            page.append(self.running_message)

            self.running_expander = Gtk.Expander(label="View details")
            self.running_diagnostics = Gtk.Label(xalign=0)
            self.running_diagnostics.set_wrap(True)
            self.running_diagnostics.set_selectable(True)
            self.running_expander.set_child(self.running_diagnostics)
            page.append(self.running_expander)
            self.stack.add_named(page, "running")

        def _create_result(self) -> None:
            page = self._page()
            self.result_heading = Gtk.Label(xalign=0)
            self.result_heading.add_css_class("title-2")
            page.append(self.result_heading)
            self.result_details = Gtk.Label(xalign=0)
            self.result_details.set_wrap(True)
            self.result_details.set_selectable(True)
            page.append(self.result_details)
            self.result_expander = Gtk.Expander(label="View details")
            self.result_diagnostics = Gtk.Label(xalign=0)
            self.result_diagnostics.set_wrap(True)
            self.result_diagnostics.set_selectable(True)
            self.result_expander.set_child(self.result_diagnostics)
            page.append(self.result_expander)
            self.stack.add_named(page, "result")

        def _safe_diagnostics(self, outcome: str) -> str:
            operation = self.running_operation or "unknown"
            duration = 0
            if self.started_at is not None:
                duration = int(time.monotonic() - self.started_at)
            return (
                f"Operation: {operation}\n"
                f"Elapsed: {duration} seconds\n"
                f"State: {outcome}\n"
                "Installer output stays in the terminal and is not saved by "
                "the GUI. No clinical data or setup tokens are collected."
            )

        def _finish_operation(
            self, exit_code: int | None, *, details: str = ""
        ) -> None:
            operation = self.running_operation or "operation"
            if exit_code == 0:
                past_tense = {
                    "install": "installed",
                    "upgrade": "upgraded",
                    "repair": "repaired",
                    "rollback": "rolled back",
                    "uninstall": "uninstalled",
                }.get(operation, "updated")
                self.result_heading.set_text(
                    f"CareQFlow was successfully {past_tense}."
                )
                self.result_details.set_text("Installer exit code: 0")
                self.open_button.set_visible(operation != "uninstall")
            else:
                self.result_heading.set_text("CareQFlow operation failed")
                code = str(exit_code) if exit_code is not None else "unavailable"
                self.result_details.set_text(
                    f"Installer exit code: {code}\n"
                    + (details or "Review the installer terminal for error details.")
                )
                self.open_button.set_visible(False)
            self.result_diagnostics.set_text(
                self._safe_diagnostics(
                    "successful" if exit_code == 0 else "failed or interrupted"
                )
            )
            self.stack.set_visible_child_name("result")
            self.progress.set_text("Completed")
            self.status.set_text("")
            self.back_button.set_sensitive(False)
            self.next_button.set_sensitive(True)
            self.next_button.set_label("Finish")
            self._clear_result_directory()

        def _clear_result_directory(self) -> None:
            if self.result_directory is not None:
                self.result_directory.cleanup()
                self.result_directory = None
                self.result_path = None
                self.worker_pid_path = None

        @staticmethod
        def _worker_alive(pid: int) -> bool:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return False
            except PermissionError:
                return True
            return True

        def _poll_install_result(self) -> bool:
            if self.result_path is None:
                return False
            self.activity.pulse()
            elapsed = int(time.monotonic() - (self.started_at or time.monotonic()))
            self.running_message.set_text(
                f"Waiting for installer completion ({elapsed} seconds elapsed)."
            )
            self.running_diagnostics.set_text(
                self._safe_diagnostics("running or awaiting installer prompts")
            )
            try:
                if self.result_path.is_file():
                    raw = self.result_path.read_text(encoding="ascii").strip()
                    try:
                        exit_code = parse_installer_result(raw)
                    except ValueError as exc:
                        self._finish_operation(None, details=str(exc))
                    else:
                        self._finish_operation(exit_code)
                    return False
            except OSError as exc:
                self._finish_operation(
                    None, details=f"Unable to read installer result: {exc}"
                )
                return False

            worker_pid: int | None = None
            if self.worker_pid_path is not None:
                try:
                    if self.worker_pid_path.is_file():
                        worker_pid = int(
                            self.worker_pid_path.read_text(encoding="ascii").strip()
                        )
                except (OSError, ValueError):
                    self._finish_operation(
                        None, details="Unable to read installer process status."
                    )
                    return False

            terminal_return = (
                self.terminal_process.poll()
                if self.terminal_process is not None
                else None
            )
            launcher_failed = terminal_return is not None and terminal_return != 0
            interrupted = interruption_detected(
                worker_pid=worker_pid,
                worker_alive=(
                    self._worker_alive(worker_pid) if worker_pid is not None else False
                ),
                terminal_return=terminal_return,
                elapsed=elapsed,
            )
            if interrupted:
                if self.missing_worker_since is None:
                    self.missing_worker_since = time.monotonic()
                elif time.monotonic() - self.missing_worker_since >= 2:
                    details = (
                        "The installer terminal or operation ended without reporting "
                        "a completion code. It may have been interrupted. "
                        "Inspect the terminal and confirm service health before retrying."
                    )
                    if launcher_failed:
                        details += f" Terminal launcher exit code: {terminal_return}."
                    self._finish_operation(None, details=details)
                    return False
            else:
                self.missing_worker_since = None
            return True

        def _open_application(self, _button: Gtk.Button) -> None:
            try:
                Gio.AppInfo.launch_default_for_uri(self.operation_origin, None)
            except GLib.Error as exc:
                self.status.set_text(f"Unable to open CareQFlow: {exc.message}")

        def _window_closing(self, *_args: object) -> bool:
            if self.stack.get_visible_child_name() == "running":
                self.status.set_text(
                    "An installation is still running. Finish it in the terminal "
                    "before closing this window."
                )
                return True
            self._clear_result_directory()
            return False

        def _operation_changed(self, *_args: object) -> None:
            operation = OPERATIONS[self.operation.get_selected()]
            self.network.set_selected(1 if operation == "install" else 0)
            self._network_changed()

        def _network_changed(self, *_args: object) -> None:
            network_mode = NETWORK_MODES[self.network.get_selected()]
            show_address = network_mode in {"SecureLan", "Tailscale"}
            self.address_label.set_visible(show_address)
            self.address.set_visible(show_address)
            hints = {
                "Preserve": "Keep the currently configured network access mode.",
                "LocalOnly": "Access CareQFlow on this Linux computer.",
                "SecureLan": "Enter a private LAN IPv4 address for HTTPS access.",
                "Tailscale": "Enter the Linux host's Tailscale IPv4 address.",
            }
            self.network_hint.set_text(hints[network_mode])

        def _show_page(self) -> None:
            operation = OPERATIONS[self.operation.get_selected()]
            pages = (
                ("welcome", "operation", "confirm")
                if operation in {"rollback", "uninstall"}
                else PAGES
            )
            self.page_index = min(self.page_index, len(pages) - 1)
            page_name = pages[self.page_index]
            self.stack.set_visible_child_name(page_name)
            self.progress.set_text(f"Step {self.page_index + 1} of {len(pages)}")
            self.back_button.set_sensitive(self.page_index > 0)
            self.next_button.set_label(
                "Open installer terminal" if page_name == "confirm" else "Next"
            )
            self.status.set_text("")
            if page_name == "welcome":
                title, details = detect_installation()
                self.installation_title.set_text(title)
                self.installation_details.set_text(details)
            if page_name == "confirm":
                network = NETWORK_MODES[self.network.get_selected()]
                summary = f"Operation: {operation.capitalize()}"
                if operation not in {"rollback", "uninstall"}:
                    summary += f"\nNetwork: {network}"
                    if network in {"SecureLan", "Tailscale"}:
                        summary += f"\nServer: {self.address.get_text().strip()}"
                self.summary.set_text(summary)

        def _back(self, _button: Gtk.Button) -> None:
            if self.page_index > 0:
                self.page_index -= 1
                self._show_page()

        def _next(self, _button: Gtk.Button) -> None:
            operation = OPERATIONS[self.operation.get_selected()]
            network_mode = NETWORK_MODES[self.network.get_selected()]
            pages = (
                ("welcome", "operation", "confirm")
                if operation in {"rollback", "uninstall"}
                else PAGES
            )

            if self.stack.get_visible_child_name() == "result":
                self.close()
                return

            if self.stack.get_visible_child_name() == "running":
                return

            if self.page_index == len(pages) - 1:
                self._launch()
                return

            if pages[self.page_index] == "network":
                try:
                    build_command(operation, network_mode, self.address.get_text())
                except ValueError as exc:
                    self.status.set_text(str(exc))
                    return

            self.page_index += 1
            self._show_page()

        def _launch(self) -> None:
            operation = OPERATIONS[self.operation.get_selected()]
            network_mode = NETWORK_MODES[self.network.get_selected()]
            try:
                command = build_command(
                    operation, network_mode, self.address.get_text()
                )
                if not INSTALL_SCRIPT.is_file():
                    raise ValueError("Linux installer entry point was not found.")
                if not (PACKAGE_ROOT / "carequeue-release.env").is_file():
                    raise ValueError(
                        "Use the packaged Linux release archive: "
                        "carequeue-release.env is missing."
                    )
                terminal = shutil.which("x-terminal-emulator")
                if terminal is None:
                    raise ValueError(
                        "No x-terminal-emulator was found on this desktop."
                    )

                self.result_directory = tempfile.TemporaryDirectory(
                    prefix="careqflow-installer-"
                )
                self.result_path = Path(self.result_directory.name) / "exit-code"
                self.worker_pid_path = Path(self.result_directory.name) / "worker-pid"

                # No raw installer output is copied to files or sent to the GUI.
                # Record only the terminal worker PID and final exit status.
                wrapper = (
                    'result_file="$1"; pid_file="$2"; shift 2; '
                    'printf "%s\\n" "$BASHPID" > "$pid_file"; '
                    '"$@"; result=$?; '
                    'printf "%s\\n" "$result" > "$result_file"; '
                    'if [ "$result" -ne 0 ]; then '
                    'printf "\\nInstallation failed (exit code %s).\\n" "$result"; '
                    'read -r -p "Press Enter to close this terminal..." _ || true; '
                    'fi; '
                    'exit "$result"'
                )
                self.terminal_process = subprocess.Popen(
                    [
                        terminal,
                        "-e",
                        "bash",
                        "-c",
                        wrapper,
                        "careqflow-installer",
                        str(self.result_path),
                        str(self.worker_pid_path),
                        *command,
                    ],
                    cwd=PACKAGE_ROOT,
                )
            except (ValueError, OSError) as exc:
                self._clear_result_directory()
                self.status.set_text(str(exc))
                return

            self.running_operation = operation
            self.started_at = time.monotonic()
            self.missing_worker_since = None
            self.running_message.set_text("Starting installer terminal...")
            self.running_diagnostics.set_text(self._safe_diagnostics("starting"))
            self.operation_origin = LOCAL_ORIGIN
            if network_mode in {"SecureLan", "Tailscale"} and operation not in {
                "rollback",
                "uninstall",
            }:
                self.operation_origin = f"https://{self.address.get_text().strip()}"
            self.stack.set_visible_child_name("running")
            self.progress.set_text("Running installer")
            self.status.set_text("")
            self.open_button.set_visible(False)
            self.back_button.set_sensitive(False)
            self.next_button.set_sensitive(False)
            GLib.timeout_add(350, self._poll_install_result)

    class InstallerApp(Gtk.Application):
        def __init__(self) -> None:
            super().__init__(application_id="org.careqflow.Installer")

        def do_activate(self) -> None:
            window = InstallerWindow(self)
            window.present()

    return InstallerApp().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
