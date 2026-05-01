from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Input,
    ListItem,
    ListView,
    SelectionList,
    Static,
    TextArea,
)
from textual.widgets.selection_list import Selection

from text_cleaner import __version__
from text_cleaner.clipboard import ClipboardError, ClipboardService
from text_cleaner.engine import CleanResult, clean_text
from text_cleaner.logging_setup import write_diagnostics
from text_cleaner.profiles import (
    VALID_OPERATIONS,
    Profile,
    ProfileRepository,
    ProfileValidationError,
    ReplacementRule,
    default_profiles,
)

OUTPUT_PREVIEW_CHARS = 4000


# ============================================================================
# Pure helpers (no Textual dependency at runtime)
# ============================================================================


def operation_summary(profile: Profile) -> str:
    if not profile.operations and not profile.replacements:
        return "No operations selected"

    pieces = list(profile.operations)
    if profile.replacements:
        pieces.append(f"{len(profile.replacements)} replacement rule(s)")
    return ", ".join(pieces)


def profile_id_from_name(name: str) -> str:
    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    profile_id = re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")
    profile_id = re.sub(r"_+", "_", profile_id)
    return profile_id or "profile"


def next_profile_id(base: str, profiles: dict[str, Profile]) -> str:
    candidate = base
    suffix = 2
    while candidate in profiles:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def clear_profile_actions(
    profiles: dict[str, Profile],
    profile_id: str,
) -> dict[str, Profile]:
    profile = profiles[profile_id]
    updated = dict(profiles)
    updated[profile_id] = Profile(
        profile.profile_id,
        profile.name,
        profile.description,
    )
    return updated


def delete_profile(
    profiles: dict[str, Profile],
    profile_id: str,
) -> dict[str, Profile]:
    updated = dict(profiles)
    del updated[profile_id]
    return updated


def save_profile_update(
    repository: ProfileRepository,
    profiles: MutableMapping[str, Profile],
    profile_id: str,
    updated: Profile,
) -> None:
    previous = profiles[profile_id]
    try:
        profiles[profile_id] = updated
        repository.save(dict(profiles))
    except ProfileValidationError:
        profiles[profile_id] = previous
        raise


# ============================================================================
# Theme
# ============================================================================
#
# Colors (clean dark, single accent):
#   bg          #0a0e1a   deep slate
#   surface     #131826   panel
#   surface-2   #1c2333   raised panel
#   border      #2a3245   subtle divider
#   text        #e6edf3   primary text
#   muted       #8893a7   secondary text
#   accent      #6ee7ff   cyan
#   accent-soft #1a3744   accent background
#   success     #4ade80   green
#   danger      #f87171   red

APP_CSS = """
/*
 * Lazygit-style: ASCII single-line panel borders, muted palette,
 * active panel gets cyan border, inactive grey. Information-dense,
 * keyboard-first. No decorative chrome.
 *
 * Palette:
 *   bg          #0e1117  near-black
 *   panel-bg    #0e1117  same as bg (panels marked by border, not fill)
 *   border-off  #3a3f4b  inactive panel border
 *   border-on   #5fafff  focused panel border (lazygit cyan)
 *   text        #c9d1d9  primary
 *   muted       #6e7681  secondary
 *   dim         #484f58  very dim
 *   accent-key  #d4a017  yellow for keybind labels
 *   select      #1f2a3d  selected row background
 */

Screen {
    background: #0e1117;
    color: #c9d1d9;
}

#body {
    layout: horizontal;
    height: 1fr;
    padding: 0;
}

/* === Panels === */

.panel {
    background: #0e1117;
    border: solid #3a3f4b;
    padding: 0 1;
}

.panel:focus,
.panel:focus-within {
    border: solid #5fafff;
}

#sidebar {
    width: 34;
    min-width: 28;
    height: 1fr;
}

#sidebar.-collapsed {
    display: none;
}

#profile-list {
    background: transparent;
    border: none;
    height: 1fr;
    padding: 0;
}

#profile-list > ListItem {
    background: transparent;
    padding: 0 1;
    margin: 0;
    border: none;
    height: 1;
}

#profile-list > ListItem .item-name {
    color: #c9d1d9;
    width: 100%;
}

#profile-list > ListItem.--highlight {
    background: #1f2a3d;
}

#profile-list > ListItem.--highlight .item-name {
    color: #ffffff;
    text-style: bold;
}

/* When the list itself doesn't have focus, dim the highlight */
#profile-list:focus > ListItem.--highlight {
    background: #2a3b56;
}

#profile-list:focus > ListItem.--highlight .item-name {
    color: #5fafff;
}

#main {
    height: 1fr;
    layout: vertical;
}

#detail-panel {
    height: 1fr;
}

#detail-content {
    padding: 0 1;
    color: #c9d1d9;
}

.label-col {
    color: #6e7681;
    width: 14;
}

.value-col {
    color: #c9d1d9;
    width: 1fr;
}

.value-muted {
    color: #6e7681;
    width: 1fr;
}

.kv-row {
    layout: horizontal;
    height: auto;
    margin: 0;
}

.kv-section {
    margin: 1 0 0 0;
}

.op-line {
    color: #c9d1d9;
}

.rule-line {
    color: #c9d1d9;
}

.rule-kind-literal {
    color: #6e7681;
}

.rule-kind-regex {
    color: #d4a017;
}

/* === Footer === */

Footer {
    background: #0e1117;
    color: #6e7681;
    height: 1;
}

Footer > .footer--key {
    color: #d4a017;
    background: #0e1117;
    text-style: bold;
}

Footer > .footer--description {
    color: #6e7681;
    background: #0e1117;
}

/* === Modal styling (matches lazygit popup feel) === */

ModalScreen {
    align: center middle;
    background: #0e1117 50%;
}

.modal-card {
    width: 80%;
    max-width: 90;
    height: auto;
    max-height: 90%;
    background: #0e1117;
    border: solid #5fafff;
    padding: 1 2;
}

.modal-card-wide {
    width: 90%;
    max-width: 120;
    height: 85%;
    background: #0e1117;
    border: solid #5fafff;
    padding: 1 2;
}

.modal-title {
    color: #c9d1d9;
    text-style: bold;
    margin-bottom: 1;
}

.modal-hint {
    color: #6e7681;
    margin-bottom: 1;
}

.modal-error {
    color: #f87171;
    margin-bottom: 1;
}

.modal-stats {
    color: #6e7681;
    margin: 1 0 1 0;
}

.field-label {
    color: #6e7681;
    margin: 0;
}

.modal-input {
    background: #0e1117;
    border: solid #3a3f4b;
    color: #c9d1d9;
    margin-bottom: 1;
}

.modal-input:focus {
    border: solid #5fafff;
}

TextArea.modal-textarea {
    background: #0e1117;
    border: solid #3a3f4b;
    color: #c9d1d9;
    height: 1fr;
    min-height: 8;
    margin-bottom: 1;
}

TextArea.modal-textarea:focus {
    border: solid #5fafff;
}

.preview-panel {
    background: #0e1117;
    border: solid #3a3f4b;
    padding: 0 1;
    height: 1fr;
    min-height: 6;
    margin-bottom: 1;
    color: #c9d1d9;
}

SelectionList.modal-select {
    background: #0e1117;
    border: solid #3a3f4b;
    color: #c9d1d9;
    height: 1fr;
    min-height: 10;
    margin-bottom: 1;
    padding: 0 1;
}

SelectionList.modal-select:focus {
    border: solid #5fafff;
}

SelectionList > .selection-list--button-selected {
    color: #5fafff;
}

SelectionList > .selection-list--button-highlighted {
    background: #1f2a3d;
}

DataTable {
    background: #0e1117;
    color: #c9d1d9;
    border: solid #3a3f4b;
}

DataTable:focus {
    border: solid #5fafff;
}

DataTable > .datatable--header {
    background: #0e1117;
    color: #6e7681;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #1f2a3d;
    color: #c9d1d9;
}

#rules-table {
    height: auto;
    min-height: 5;
    max-height: 12;
    margin: 1 0 1 0;
}

.modal-actions {
    layout: horizontal;
    height: auto;
    align: right middle;
    margin-top: 1;
}

.modal-actions Button {
    margin: 0 0 0 1;
    min-width: 10;
}

Button {
    background: transparent;
    color: #c9d1d9;
    border: solid #3a3f4b;
    height: 3;
    padding: 0 2;
}

Button:hover {
    background: #1f2a3d;
    border: solid #5fafff;
}

Button:focus {
    border: solid #5fafff;
    text-style: bold;
}

Button.-primary {
    color: #5fafff;
    border: solid #5fafff;
}

Button.-success {
    color: #4ade80;
    border: solid #4ade80;
}

Button.-error {
    color: #f87171;
    border: solid #f87171;
}
"""


# ============================================================================
# Screens
# ============================================================================


def truncate(text: str, limit: int = OUTPUT_PREVIEW_CHARS) -> str:
    return text if len(text) <= limit else text[:limit] + "\n…"


class ConfirmScreen(ModalScreen[bool]):
    """Yes/No confirmation modal."""

    BINDINGS = [Binding("escape", "dismiss(False)", "Cancel", show=False)]

    def __init__(self, title: str, message: str, confirm_label: str = "Confirm",
                 confirm_variant: str = "primary") -> None:
        super().__init__()
        self.title_text = title
        self.message = message
        self.confirm_label = confirm_label
        self.confirm_variant = confirm_variant

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-card"):
            yield Static(self.title_text, classes="modal-title")
            yield Static(self.message, classes="modal-hint")
            with Horizontal(classes="modal-actions"):
                yield Button("Cancel", id="cancel-btn")
                yield Button(self.confirm_label, variant=self.confirm_variant, id="confirm-btn")

    @on(Button.Pressed, "#cancel-btn")
    def _cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#confirm-btn")
    def _confirm(self) -> None:
        self.dismiss(True)


class InfoScreen(ModalScreen[None]):
    """Plain message + OK."""

    BINDINGS = [Binding("escape,enter", "dismiss", "OK", show=False)]

    def __init__(self, title: str, message: str, *, error: bool = False) -> None:
        super().__init__()
        self.title_text = title
        self.message = message
        self.error = error

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-card"):
            yield Static(self.title_text, classes="modal-title")
            yield Static(self.message, classes="modal-error" if self.error else "modal-hint")
            with Horizontal(classes="modal-actions"):
                yield Button("OK", variant="primary", id="ok-btn")

    @on(Button.Pressed, "#ok-btn")
    def _ok(self) -> None:
        self.dismiss(None)


class PasteScreen(ModalScreen[CleanResult | None]):
    """Multi-line paste → clean → preview → copy/skip."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("ctrl+r", "clean", "Clean", show=True),
    ]

    def __init__(self, profile: Profile) -> None:
        super().__init__()
        self.profile = profile
        self.result: CleanResult | None = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-card-wide"):
            yield Static(f"Paste & Clean — {self.profile.name}", classes="modal-title")
            yield Static(
                "Paste text below, then press Ctrl+R to clean. "
                "Tab to move between fields.",
                classes="modal-hint",
            )
            yield TextArea("", id="paste-input", classes="modal-textarea", show_line_numbers=False)
            yield Static("", id="paste-stats", classes="modal-stats")
            yield Static("", id="paste-preview", classes="preview-panel")
            with Horizontal(classes="modal-actions"):
                yield Button("Cancel", id="cancel-btn")
                yield Button("Clean", variant="primary", id="clean-btn")
                yield Button("Copy", variant="success", id="copy-btn", disabled=True)

    def on_mount(self) -> None:
        self.query_one("#paste-input", TextArea).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_clean(self) -> None:
        self._do_clean()

    @on(Button.Pressed, "#cancel-btn")
    def _cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#clean-btn")
    def _clean(self) -> None:
        self._do_clean()

    @on(Button.Pressed, "#copy-btn")
    def _copy(self) -> None:
        self.dismiss(self.result)

    def _do_clean(self) -> None:
        text = self.query_one("#paste-input", TextArea).text
        self.result = clean_text(text, self.profile)
        report = self.result.report
        self.query_one("#paste-stats", Static).update(
            f"[#6ee7ff]{report.input_chars:,}[/] chars  →  "
            f"[#6ee7ff]{report.output_chars:,}[/] chars  "
            f"([#8893a7]{len(report.operations)} ops applied[/])"
        )
        self.query_one("#paste-preview", Static).update(truncate(self.result.text))
        self.query_one("#copy-btn", Button).disabled = False


class ClipboardPreviewScreen(ModalScreen[bool]):
    """Show cleaned clipboard preview, ask to copy."""

    BINDINGS = [Binding("escape", "dismiss(False)", "Cancel", show=True)]

    def __init__(self, profile: Profile, result: CleanResult) -> None:
        super().__init__()
        self.profile = profile
        self.result = result

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-card-wide"):
            yield Static(
                f"Clipboard preview — {self.profile.name}",
                classes="modal-title",
            )
            r = self.result.report
            yield Static(
                f"[#6ee7ff]{r.input_chars:,}[/] chars  →  "
                f"[#6ee7ff]{r.output_chars:,}[/] chars  "
                f"([#8893a7]{len(r.operations)} ops applied[/])",
                classes="modal-stats",
            )
            yield Static(truncate(self.result.text), classes="preview-panel")
            with Horizontal(classes="modal-actions"):
                yield Button("Cancel", id="cancel-btn")
                yield Button("Copy to clipboard", variant="success", id="copy-btn")

    @on(Button.Pressed, "#cancel-btn")
    def _cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#copy-btn")
    def _copy(self) -> None:
        self.dismiss(True)


class EditProfileScreen(ModalScreen[Profile | None]):
    """Edit name/description/operations."""

    BINDINGS = [Binding("escape", "dismiss(None)", "Cancel", show=True)]

    def __init__(self, profile: Profile, title: str = "Edit profile") -> None:
        super().__init__()
        self.profile = profile
        self.title_text = title

    def compose(self) -> ComposeResult:
        selections = [
            Selection(op, op, op in self.profile.operations)
            for op in sorted(VALID_OPERATIONS)
        ]
        with Vertical(classes="modal-card-wide"):
            yield Static(self.title_text, classes="modal-title")
            yield Static("Display name", classes="field-label")
            yield Input(value=self.profile.name, id="name-input", classes="modal-input")
            yield Static("Description", classes="field-label")
            yield Input(
                value=self.profile.description,
                id="desc-input",
                classes="modal-input",
            )
            yield Static("Operations", classes="field-label")
            yield SelectionList(*selections, id="ops-list", classes="modal-select")
            with Horizontal(classes="modal-actions"):
                yield Button("Cancel", id="cancel-btn")
                yield Button("Save", variant="primary", id="save-btn")

    def on_mount(self) -> None:
        self.query_one("#name-input", Input).focus()

    @on(Button.Pressed, "#cancel-btn")
    def _cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#save-btn")
    def _save(self) -> None:
        name = self.query_one("#name-input", Input).value.strip()
        description = self.query_one("#desc-input", Input).value.strip()
        if not name:
            self.app.push_screen(InfoScreen(
                "Profile error", "Profile name cannot be empty.", error=True,
            ))
            return
        ops = list(self.query_one("#ops-list", SelectionList).selected)
        self.dismiss(Profile(
            self.profile.profile_id,
            name,
            description,
            ops,
            self.profile.replacements,
        ))


class NewProfileScreen(ModalScreen[Profile | None]):
    """Create a new profile (name → description → operations)."""

    BINDINGS = [Binding("escape", "dismiss(None)", "Cancel", show=True)]

    def __init__(self, profiles: dict[str, Profile]) -> None:
        super().__init__()
        self.profiles = profiles

    def compose(self) -> ComposeResult:
        selections = [Selection(op, op, False) for op in sorted(VALID_OPERATIONS)]
        with Vertical(classes="modal-card-wide"):
            yield Static("New profile", classes="modal-title")
            yield Static("Display name", classes="field-label")
            yield Input(placeholder="e.g. Markdown cleanup", id="name-input", classes="modal-input")
            yield Static("Description", classes="field-label")
            yield Input(
                placeholder="Short hint shown in the sidebar",
                id="desc-input",
                classes="modal-input",
            )
            yield Static("Operations", classes="field-label")
            yield SelectionList(*selections, id="ops-list", classes="modal-select")
            with Horizontal(classes="modal-actions"):
                yield Button("Cancel", id="cancel-btn")
                yield Button("Create", variant="primary", id="save-btn")

    def on_mount(self) -> None:
        self.query_one("#name-input", Input).focus()

    @on(Button.Pressed, "#cancel-btn")
    def _cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#save-btn")
    def _save(self) -> None:
        name = self.query_one("#name-input", Input).value.strip()
        if not name:
            self.app.push_screen(InfoScreen(
                "Profile error", "Profile name cannot be empty.", error=True,
            ))
            return
        description = self.query_one("#desc-input", Input).value.strip()
        ops = list(self.query_one("#ops-list", SelectionList).selected)
        profile_id = next_profile_id(profile_id_from_name(name), self.profiles)
        self.dismiss(Profile(profile_id, name, description, ops))


class ReplacementsScreen(ModalScreen[Profile | None]):
    """Manage replacement rules for a profile."""

    BINDINGS = [Binding("escape", "dismiss(None)", "Cancel", show=True)]

    def __init__(self, profile: Profile) -> None:
        super().__init__()
        self.profile = profile
        self.replacements: list[ReplacementRule] = list(profile.replacements)

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-card-wide"):
            yield Static(
                f"Replacements — {self.profile.name}",
                classes="modal-title",
            )
            yield Static(
                "Add literal or regex replacement rules. They run after operations.",
                classes="modal-hint",
            )
            yield DataTable(id="rules-table")
            with Vertical(classes="add-row"):
                yield Static("Add rule", classes="field-label")
                yield Input(placeholder="Find", id="find-input", classes="modal-input")
                yield Input(placeholder="Replace with", id="replace-input", classes="modal-input")
                with Horizontal():
                    yield Button("Add (literal)", variant="primary", id="add-literal-btn")
                    yield Button("Add (regex)", id="add-regex-btn")
                    yield Button("Remove selected", variant="error", id="remove-btn")
                    yield Button("Clear all", id="clear-btn")
            with Horizontal(classes="modal-actions"):
                yield Button("Cancel", id="cancel-btn")
                yield Button("Save", variant="primary", id="save-btn")

    def on_mount(self) -> None:
        table = self.query_one("#rules-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Find", "Replace", "Type")
        self._refresh_table()
        self.query_one("#find-input", Input).focus()

    def _refresh_table(self) -> None:
        table = self.query_one("#rules-table", DataTable)
        table.clear()
        for rule in self.replacements:
            table.add_row(
                rule.find,
                rule.replace,
                "regex" if rule.regex else "literal",
            )

    def _add(self, regex: bool) -> None:
        find = self.query_one("#find-input", Input).value
        replace = self.query_one("#replace-input", Input).value
        if not find:
            self.app.push_screen(InfoScreen(
                "Replacement error", "Find text cannot be empty.", error=True,
            ))
            return
        self.replacements.append(ReplacementRule(find=find, replace=replace, regex=regex))
        self.query_one("#find-input", Input).value = ""
        self.query_one("#replace-input", Input).value = ""
        self._refresh_table()
        self.query_one("#find-input", Input).focus()

    @on(Button.Pressed, "#add-literal-btn")
    def _add_literal(self) -> None:
        self._add(regex=False)

    @on(Button.Pressed, "#add-regex-btn")
    def _add_regex(self) -> None:
        self._add(regex=True)

    @on(Button.Pressed, "#remove-btn")
    def _remove(self) -> None:
        table = self.query_one("#rules-table", DataTable)
        if table.cursor_row < 0 or table.cursor_row >= len(self.replacements):
            return
        del self.replacements[table.cursor_row]
        self._refresh_table()

    @on(Button.Pressed, "#clear-btn")
    def _clear(self) -> None:
        self.replacements.clear()
        self._refresh_table()

    @on(Button.Pressed, "#cancel-btn")
    def _cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#save-btn")
    def _save(self) -> None:
        self.dismiss(Profile(
            self.profile.profile_id,
            self.profile.name,
            self.profile.description,
            self.profile.operations,
            self.replacements,
        ))


class RecoveryScreen(ModalScreen[str]):
    """Shown when no profiles are configured. Returns 'new', 'defaults', or 'quit'."""

    BINDINGS = [Binding("escape", "dismiss('quit')", "Quit", show=True)]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-card"):
            yield Static("No profiles", classes="modal-title")
            yield Static(
                "No profiles are configured. Create a new one, or restore the defaults.",
                classes="modal-hint",
            )
            with Horizontal(classes="modal-actions"):
                yield Button("Quit", id="quit-btn")
                yield Button("New profile", id="new-btn")
                yield Button("Restore defaults", variant="primary", id="defaults-btn")

    @on(Button.Pressed, "#quit-btn")
    def _quit(self) -> None:
        self.dismiss("quit")

    @on(Button.Pressed, "#new-btn")
    def _new(self) -> None:
        self.dismiss("new")

    @on(Button.Pressed, "#defaults-btn")
    def _defaults(self) -> None:
        self.dismiss("defaults")


# ============================================================================
# Main app
# ============================================================================


class TextCleanerApp(App[int]):
    CSS = APP_CSS

    BINDINGS = [
        Binding("q", "quit_app", "Quit"),
        Binding("p", "paste", "Paste"),
        Binding("c", "clipboard", "Clipboard"),
        Binding("e", "edit", "Edit"),
        Binding("r", "replacements", "Replacements"),
        Binding("n", "new_profile", "New"),
        Binding("d", "delete_profile", "Delete"),
        Binding("x", "clear_profile", "Clear"),
        Binding("l", "logs", "Logs"),
        Binding("b", "toggle_sidebar", "Sidebar"),
    ]

    profiles: reactive[dict[str, Profile]] = reactive(dict, recompose=False)
    selected_id: reactive[str | None] = reactive(None, recompose=False)

    def __init__(
        self,
        repository: ProfileRepository,
        clipboard: ClipboardService,
        portable_dir: Path,
        logger: logging.Logger,
        initial_profiles: dict[str, Profile],
    ) -> None:
        super().__init__()
        self.repository = repository
        self.clipboard_service = clipboard
        self.portable_dir = portable_dir
        self.logger = logger
        self._initial_profiles = initial_profiles

    def compose(self) -> ComposeResult:
        with Horizontal(id="body"):
            sidebar = Vertical(id="sidebar", classes="panel")
            sidebar.border_title = " Profiles "
            sidebar.border_subtitle = f" text-cleaner v{__version__} "
            with sidebar:
                yield ListView(id="profile-list")
            main = Vertical(id="main", classes="panel")
            main.border_title = " Profile "
            with main:
                yield VerticalScroll(Static("", id="detail-content"), id="detail-panel")
        yield Footer()

    def on_mount(self) -> None:
        self.profiles = dict(self._initial_profiles)
        if self.profiles:
            self.selected_id = next(iter(self.profiles))
            self._populate_sidebar()
            self.query_one("#profile-list", ListView).focus()
        else:
            self._populate_sidebar()
            self.call_after_refresh(self._handle_recovery)

    # ---- sidebar / details ----

    def _populate_sidebar(self) -> None:
        listview = self.query_one("#profile-list", ListView)
        listview.clear()
        for profile_id, profile in self.profiles.items():
            item = ListItem(
                Static(profile.name, classes="item-name"),
                id=f"item-{profile_id}",
            )
            item.profile_id = profile_id  # type: ignore[attr-defined]
            listview.append(item)
        if self.selected_id and f"item-{self.selected_id}" in {
            child.id for child in listview.children
        }:
            for index, child in enumerate(listview.children):
                if child.id == f"item-{self.selected_id}":
                    listview.index = index
                    break

    def watch_selected_id(self, _old: str | None, new: str | None) -> None:
        self._refresh_details()

    def _refresh_details(self) -> None:
        try:
            content = self.query_one("#detail-content", Static)
        except NoMatches:
            return

        if not self.selected_id or self.selected_id not in self.profiles:
            content.update("[#6e7681]No profile selected.[/]")
            return

        profile = self.profiles[self.selected_id]
        lines: list[str] = []
        label = "[#6e7681]"
        end = "[/]"

        def row(key: str, value: str) -> str:
            return f"{label}{key:<13}{end} {value}"

        lines.append(row("name", f"[b]{profile.name}[/]"))
        lines.append(
            row(
                "description",
                profile.description or f"{label}—{end}",
            )
        )
        lines.append("")

        if profile.operations:
            lines.append(row("operations", profile.operations[0]))
            for op in profile.operations[1:]:
                lines.append(f"{label}{'':<13}{end} {op}")
        else:
            lines.append(row("operations", f"{label}(none){end}"))
        lines.append("")

        if profile.replacements:
            first = profile.replacements[0]
            kind = "regex" if first.regex else "literal"
            lines.append(
                row(
                    "rules",
                    f"[#d4a017]{kind}[/]  {first.find!r} → {first.replace!r}",
                )
            )
            for rule in profile.replacements[1:]:
                kind = "regex" if rule.regex else "literal"
                lines.append(
                    f"{label}{'':<13}{end} [#d4a017]{kind}[/]  "
                    f"{rule.find!r} → {rule.replace!r}"
                )
        else:
            lines.append(row("rules", f"{label}(none){end}"))

        content.update("\n".join(lines))

    @on(ListView.Highlighted, "#profile-list")
    def _profile_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        self.selected_id = getattr(event.item, "profile_id", None)

    # ---- saving helpers ----

    def _save_or_revert(self, updated_profiles: dict[str, Profile],
                       error_title: str = "Profile error") -> bool:
        try:
            self.repository.save(updated_profiles)
        except ProfileValidationError as exc:
            self.push_screen(InfoScreen(error_title, str(exc), error=True))
            return False
        self.profiles = updated_profiles
        self._populate_sidebar()
        self._refresh_details()
        return True

    # ---- actions ----

    def action_quit_app(self) -> None:
        self.exit(0)

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        sidebar.toggle_class("-collapsed")
        if not sidebar.has_class("-collapsed"):
            self.query_one("#profile-list", ListView).focus()

    def action_new_profile(self) -> None:
        def _then(profile: Profile | None) -> None:
            if profile is None:
                return
            updated = {**self.profiles, profile.profile_id: profile}
            saved = self._save_or_revert(updated)
            if saved:
                self.selected_id = profile.profile_id
                self.logger.info("profile_created profile=%s", profile.profile_id)

        self.push_screen(NewProfileScreen(self.profiles), _then)

    def action_edit(self) -> None:
        if not self.selected_id:
            return
        profile = self.profiles[self.selected_id]

        def _then(updated: Profile | None) -> None:
            if updated is None or updated == profile:
                return
            updated_profiles = {**self.profiles, profile.profile_id: updated}
            saved = self._save_or_revert(updated_profiles)
            if saved:
                self.logger.info("profile_edited profile=%s", profile.profile_id)

        self.push_screen(EditProfileScreen(profile), _then)

    def action_replacements(self) -> None:
        if not self.selected_id:
            return
        profile = self.profiles[self.selected_id]

        def _then(updated: Profile | None) -> None:
            if updated is None or updated == profile:
                return
            updated_profiles = {**self.profiles, profile.profile_id: updated}
            saved = self._save_or_revert(updated_profiles)
            if saved:
                self.logger.info(
                    "profile_replacements_updated profile=%s rules=%s",
                    profile.profile_id,
                    len(updated.replacements),
                )

        self.push_screen(ReplacementsScreen(profile), _then)

    def action_clear_profile(self) -> None:
        if not self.selected_id:
            return
        profile = self.profiles[self.selected_id]

        def _then(confirmed: bool) -> None:
            if not confirmed:
                return
            updated = clear_profile_actions(self.profiles, profile.profile_id)
            saved = self._save_or_revert(updated)
            if saved:
                self.logger.info("profile_cleared profile=%s", profile.profile_id)

        self.push_screen(
            ConfirmScreen(
                "Clear profile",
                f"Remove all operations and replacements from '{profile.name}'?",
                confirm_label="Clear",
                confirm_variant="primary",
            ),
            _then,
        )

    def action_delete_profile(self) -> None:
        if not self.selected_id:
            return
        profile = self.profiles[self.selected_id]

        def _then(confirmed: bool) -> None:
            if not confirmed:
                return
            updated = delete_profile(self.profiles, profile.profile_id)
            saved = self._save_or_revert(updated)
            if not saved:
                return
            self.logger.info("profile_deleted profile=%s", profile.profile_id)
            self.selected_id = next(iter(updated)) if updated else None
            if not updated:
                self.call_after_refresh(self._handle_recovery)

        self.push_screen(
            ConfirmScreen(
                "Delete profile",
                f"Delete profile '{profile.name}'? This cannot be undone.",
                confirm_label="Delete",
                confirm_variant="error",
            ),
            _then,
        )

    def action_paste(self) -> None:
        if not self.selected_id:
            return
        profile = self.profiles[self.selected_id]

        def _then(result: CleanResult | None) -> None:
            if result is None:
                self.logger.info("paste_flow_cancelled profile=%s", profile.profile_id)
                return
            self.logger.info(
                "paste_flow profile=%s input_chars=%s output_chars=%s operations=%s",
                profile.profile_id,
                result.report.input_chars,
                result.report.output_chars,
                result.report.operations,
            )
            try:
                self.clipboard_service.write_text(result.text)
            except ClipboardError as exc:
                self.logger.exception("paste_copy_failed profile=%s", profile.profile_id)
                self.push_screen(InfoScreen("Clipboard error", str(exc), error=True))
                return
            self.notify(
                f"Copied {result.report.output_chars:,} chars to clipboard",
                title="Cleaned",
                severity="information",
            )

        self.push_screen(PasteScreen(profile), _then)

    def action_clipboard(self) -> None:
        if not self.selected_id:
            return
        profile = self.profiles[self.selected_id]

        try:
            source = self.clipboard_service.read_text()
        except ClipboardError as exc:
            self.logger.exception("clipboard_flow_failed profile=%s", profile.profile_id)
            self.push_screen(InfoScreen("Clipboard error", str(exc), error=True))
            return

        result = clean_text(source, profile)

        def _then(should_copy: bool) -> None:
            if not should_copy:
                self.logger.info(
                    "clipboard_flow_cancelled profile=%s input_chars=%s "
                    "output_chars=%s operations=%s",
                    profile.profile_id,
                    result.report.input_chars,
                    result.report.output_chars,
                    result.report.operations,
                )
                return
            try:
                self.clipboard_service.write_text(result.text)
            except ClipboardError as exc:
                self.logger.exception("clipboard_flow_failed profile=%s", profile.profile_id)
                self.push_screen(InfoScreen("Clipboard error", str(exc), error=True))
                return
            self.logger.info(
                "clipboard_flow profile=%s input_chars=%s output_chars=%s operations=%s",
                profile.profile_id,
                result.report.input_chars,
                result.report.output_chars,
                result.report.operations,
            )
            self.notify(
                f"{result.report.input_chars:,} → {result.report.output_chars:,} chars",
                title="Clipboard cleaned",
                severity="information",
            )

        self.push_screen(ClipboardPreviewScreen(profile, result), _then)

    def action_logs(self) -> None:
        dump = write_diagnostics(self.portable_dir)
        self.logger.info("diagnostics_written path=%s", dump)
        self.push_screen(InfoScreen("Diagnostics written", str(dump)))

    # ---- recovery ----

    def _handle_recovery(self) -> None:
        def _then(choice: str) -> None:
            if choice == "quit":
                self.exit(0)
            elif choice == "defaults":
                profiles = default_profiles()
                self.repository.save(profiles)
                self.profiles = profiles
                self.selected_id = next(iter(profiles))
                self._populate_sidebar()
                self._refresh_details()
                self.notify("Default profiles restored", severity="information")
            elif choice == "new":
                self.push_screen(NewProfileScreen({}), self._after_recovery_new)

        self.push_screen(RecoveryScreen(), _then)

    def _after_recovery_new(self, profile: Profile | None) -> None:
        if profile is None:
            self.call_after_refresh(self._handle_recovery)
            return
        updated = {profile.profile_id: profile}
        if self._save_or_revert(updated):
            self.selected_id = profile.profile_id


# ============================================================================
# Entry point
# ============================================================================


def load_profiles_for_tui(
    repository: ProfileRepository,
    logger: logging.Logger,
) -> dict[str, Profile] | tuple[None, str]:
    """Load profiles, or return (None, error_message) if the file is invalid."""
    try:
        return repository.load_or_create()
    except ProfileValidationError as exc:
        logger.info(
            "profile_load_failed error_type=%s cause_type=%s config_path=%s",
            type(exc).__name__,
            type(exc.__cause__).__name__ if exc.__cause__ else None,
            getattr(repository, "path", "profiles.toml"),
        )
        return (None, "profiles.toml could not be loaded.")


def run_tui(portable_dir: Path, logger: logging.Logger) -> int:
    repository = ProfileRepository(portable_dir / "profiles.toml")
    clipboard = ClipboardService()

    loaded: Any = load_profiles_for_tui(repository, logger)
    if isinstance(loaded, tuple):
        # Validation error — start with empty profiles; recovery flow kicks in
        initial: dict[str, Profile] = {}
    else:
        initial = loaded

    app = TextCleanerApp(
        repository=repository,
        clipboard=clipboard,
        portable_dir=portable_dir,
        logger=logger,
        initial_profiles=initial,
    )
    return app.run() or 0
