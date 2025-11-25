"""
FileForge GUI - Modern Tkinter Interface
=========================================

A professional, modern GUI for the FileForge file converter.
Features drag-and-drop support, batch conversion, and a clean dark theme.

Usage:
    python -m fileforge.gui

Or import and run:
    from fileforge.gui import main
    main()
"""

from __future__ import annotations

import os
import sys
import threading
import logging
from pathlib import Path
from typing import (
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Any,
)
from dataclasses import dataclass, field
from enum import Enum

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Configure module logger
logger = logging.getLogger(__name__)

# =============================================================================
# Constants and Theme Configuration
# =============================================================================

# Application Info
APP_NAME = "FileForge"
APP_VERSION = "1.0.0"

# Window Dimensions
WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 700
WINDOW_DEFAULT_WIDTH = 1000
WINDOW_DEFAULT_HEIGHT = 750

# UI Constants
PADDING_SMALL = 5
PADDING_MEDIUM = 10
PADDING_LARGE = 15
PADDING_XLARGE = 20

# Font Configuration
FONT_FAMILY = "Segoe UI"  # Modern Windows font, falls back on other systems
FONT_SIZE_SMALL = 9
FONT_SIZE_NORMAL = 10
FONT_SIZE_LARGE = 12
FONT_SIZE_XLARGE = 14
FONT_SIZE_TITLE = 18


class ThemeColors:
    """Dark theme color palette for the application."""

    # Background colors
    BG_PRIMARY = "#1e1e2e"       # Main background (darker)
    BG_SECONDARY = "#2a2a3e"     # Secondary panels
    BG_TERTIARY = "#363650"      # Cards, frames
    BG_INPUT = "#2d2d44"         # Input fields
    BG_HOVER = "#3d3d5c"         # Hover state

    # Foreground colors
    FG_PRIMARY = "#ffffff"       # Primary text
    FG_SECONDARY = "#b4b4c4"     # Secondary text
    FG_MUTED = "#8888a0"         # Muted/disabled text
    FG_PLACEHOLDER = "#666680"   # Placeholder text

    # Accent colors
    ACCENT_PRIMARY = "#7c3aed"   # Primary accent (purple)
    ACCENT_HOVER = "#8b5cf6"     # Accent hover
    ACCENT_PRESSED = "#6d28d9"   # Accent pressed
    ACCENT_LIGHT = "#a78bfa"     # Light accent

    # Status colors
    SUCCESS = "#22c55e"          # Green
    SUCCESS_LIGHT = "#4ade80"
    WARNING = "#f59e0b"          # Amber
    WARNING_LIGHT = "#fbbf24"
    ERROR = "#ef4444"            # Red
    ERROR_LIGHT = "#f87171"
    INFO = "#3b82f6"             # Blue
    INFO_LIGHT = "#60a5fa"

    # Border colors
    BORDER_DEFAULT = "#3d3d5c"
    BORDER_FOCUS = "#7c3aed"
    BORDER_ERROR = "#ef4444"

    # Special elements
    DROP_ZONE_BG = "#2a2a3e"
    DROP_ZONE_ACTIVE = "#363650"
    DROP_ZONE_BORDER = "#4a4a6a"
    DROP_ZONE_BORDER_ACTIVE = "#7c3aed"

    # Progress bar
    PROGRESS_BG = "#3d3d5c"
    PROGRESS_FG = "#7c3aed"


# Format mapping for conversion
FORMAT_CATEGORIES = {
    "image": {
        "extensions": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"],
        "outputs": ["PNG", "JPG", "WEBP", "BMP", "GIF"],
        "description": "Image files",
    },
    "document": {
        "extensions": [".pdf"],
        "outputs": ["TXT", "PNG (pages)"],
        "description": "PDF documents",
    },
    "data": {
        "extensions": [".csv", ".json", ".xlsx", ".xls"],
        "outputs": ["CSV", "JSON", "XLSX"],
        "description": "Data files",
    },
}


# =============================================================================
# Helper Classes
# =============================================================================

@dataclass
class FileItem:
    """Represents a file in the conversion queue."""

    path: Path
    size: int
    format_type: str  # 'image', 'document', 'data'
    status: str = "pending"  # 'pending', 'converting', 'success', 'error'
    error_message: Optional[str] = None
    output_path: Optional[Path] = None


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_file_category(file_path: Path) -> Optional[str]:
    """Determine the format category of a file."""
    ext = file_path.suffix.lower()

    for category, info in FORMAT_CATEGORIES.items():
        if ext in info["extensions"]:
            return category

    return None


def get_output_formats(category: str) -> List[str]:
    """Get available output formats for a category."""
    return FORMAT_CATEGORIES.get(category, {}).get("outputs", [])


# =============================================================================
# Custom Styled Widgets
# =============================================================================

class ModernButton(tk.Canvas):
    """A modern styled button with hover effects."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str,
        command: Optional[Callable] = None,
        width: int = 120,
        height: int = 36,
        bg_color: str = ThemeColors.ACCENT_PRIMARY,
        hover_color: str = ThemeColors.ACCENT_HOVER,
        pressed_color: str = ThemeColors.ACCENT_PRESSED,
        fg_color: str = ThemeColors.FG_PRIMARY,
        font_size: int = FONT_SIZE_NORMAL,
        corner_radius: int = 4,
        disabled: bool = False,
        **kwargs
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget("bg") if hasattr(parent, "cget") else ThemeColors.BG_PRIMARY,
            highlightthickness=0,
            **kwargs
        )

        self.text = text
        self.command = command
        self._width = width
        self._height = height
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.pressed_color = pressed_color
        self.fg_color = fg_color
        self.font_size = font_size
        self.corner_radius = corner_radius
        self._disabled = disabled
        self._current_bg = bg_color

        self._draw_button()
        self._bind_events()

    def _draw_button(self):
        """Draw the button with rounded corners."""
        self.delete("all")

        r = self.corner_radius
        w = self._width - 1
        h = self._height - 1

        # Draw rounded rectangle using arcs and rectangle fills
        # This creates a smoother, more square appearance

        # Main rectangle (center)
        self.create_rectangle(
            r, 0, w - r, h,
            fill=self._current_bg, outline=""
        )
        # Left and right sides
        self.create_rectangle(
            0, r, r, h - r,
            fill=self._current_bg, outline=""
        )
        self.create_rectangle(
            w - r, r, w, h - r,
            fill=self._current_bg, outline=""
        )

        # Corner arcs (pie slices for smooth rounded corners)
        # Top-left
        self.create_arc(
            0, 0, r * 2, r * 2,
            start=90, extent=90,
            fill=self._current_bg, outline=""
        )
        # Top-right
        self.create_arc(
            w - r * 2, 0, w, r * 2,
            start=0, extent=90,
            fill=self._current_bg, outline=""
        )
        # Bottom-left
        self.create_arc(
            0, h - r * 2, r * 2, h,
            start=180, extent=90,
            fill=self._current_bg, outline=""
        )
        # Bottom-right
        self.create_arc(
            w - r * 2, h - r * 2, w, h,
            start=270, extent=90,
            fill=self._current_bg, outline=""
        )

        # Draw text
        self.create_text(
            (w + 1) // 2,
            (h + 1) // 2,
            text=self.text,
            fill=self.fg_color if not self._disabled else ThemeColors.FG_MUTED,
            font=(FONT_FAMILY, self.font_size, "bold"),
            tags="text"
        )

    def _bind_events(self):
        """Bind mouse events for hover and click effects."""
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, event):
        if not self._disabled:
            self._current_bg = self.hover_color
            self._draw_button()
            self.config(cursor="hand2")

    def _on_leave(self, event):
        if not self._disabled:
            self._current_bg = self.bg_color
            self._draw_button()
            self.config(cursor="")

    def _on_press(self, event):
        if not self._disabled:
            self._current_bg = self.pressed_color
            self._draw_button()

    def _on_release(self, event):
        if not self._disabled:
            self._current_bg = self.hover_color
            self._draw_button()
            if self.command:
                self.command()

    def set_disabled(self, disabled: bool):
        """Enable or disable the button."""
        self._disabled = disabled
        if disabled:
            self._current_bg = ThemeColors.BG_TERTIARY
        else:
            self._current_bg = self.bg_color
        self._draw_button()
        self.config(cursor="" if disabled else "hand2")

    def set_text(self, text: str):
        """Update button text."""
        self.text = text
        self._draw_button()


class ModernEntry(tk.Frame):
    """A modern styled entry field with placeholder support."""

    def __init__(
        self,
        parent: tk.Widget,
        placeholder: str = "",
        width: int = 200,
        **kwargs
    ):
        super().__init__(parent, bg=ThemeColors.BG_INPUT, **kwargs)

        self.placeholder = placeholder
        self._has_focus = False
        self._showing_placeholder = True

        # Create inner frame for border effect
        self.inner_frame = tk.Frame(
            self,
            bg=ThemeColors.BG_INPUT,
            highlightbackground=ThemeColors.BORDER_DEFAULT,
            highlightthickness=1,
            highlightcolor=ThemeColors.BORDER_FOCUS,
        )
        self.inner_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Create entry widget
        self.entry = tk.Entry(
            self.inner_frame,
            bg=ThemeColors.BG_INPUT,
            fg=ThemeColors.FG_PLACEHOLDER,
            insertbackground=ThemeColors.FG_PRIMARY,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            relief=tk.FLAT,
            width=width // 8,
        )
        self.entry.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # Show placeholder
        if placeholder:
            self.entry.insert(0, placeholder)

        # Bind events
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)

    def _on_focus_in(self, event):
        self._has_focus = True
        if self._showing_placeholder:
            self.entry.delete(0, tk.END)
            self.entry.config(fg=ThemeColors.FG_PRIMARY)
            self._showing_placeholder = False
        self.inner_frame.config(highlightbackground=ThemeColors.BORDER_FOCUS)

    def _on_focus_out(self, event):
        self._has_focus = False
        if not self.entry.get():
            self.entry.insert(0, self.placeholder)
            self.entry.config(fg=ThemeColors.FG_PLACEHOLDER)
            self._showing_placeholder = True
        self.inner_frame.config(highlightbackground=ThemeColors.BORDER_DEFAULT)

    def get(self) -> str:
        """Get the entry value (excluding placeholder)."""
        if self._showing_placeholder:
            return ""
        return self.entry.get()

    def set(self, value: str):
        """Set the entry value."""
        self.entry.delete(0, tk.END)
        if value:
            self.entry.insert(0, value)
            self.entry.config(fg=ThemeColors.FG_PRIMARY)
            self._showing_placeholder = False
        else:
            self.entry.insert(0, self.placeholder)
            self.entry.config(fg=ThemeColors.FG_PLACEHOLDER)
            self._showing_placeholder = True

    def set_state(self, state: str):
        """Set the state of the entry ('normal' or 'disabled')."""
        self.entry.config(state=state)


class ModernScale(tk.Frame):
    """A modern styled scale/slider widget."""

    def __init__(
        self,
        parent: tk.Widget,
        from_: int = 0,
        to: int = 100,
        value: int = 50,
        label: str = "",
        command: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, bg=ThemeColors.BG_SECONDARY, **kwargs)

        self.command = command
        self._value = tk.IntVar(value=value)

        # Label row
        if label:
            label_frame = tk.Frame(self, bg=ThemeColors.BG_SECONDARY)
            label_frame.pack(fill=tk.X, pady=(0, 5))

            tk.Label(
                label_frame,
                text=label,
                bg=ThemeColors.BG_SECONDARY,
                fg=ThemeColors.FG_SECONDARY,
                font=(FONT_FAMILY, FONT_SIZE_SMALL),
            ).pack(side=tk.LEFT)

            self.value_label = tk.Label(
                label_frame,
                text=str(value),
                bg=ThemeColors.BG_SECONDARY,
                fg=ThemeColors.ACCENT_LIGHT,
                font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
            )
            self.value_label.pack(side=tk.RIGHT)

        # Scale widget - using ttk for better appearance
        self.scale = ttk.Scale(
            self,
            from_=from_,
            to=to,
            orient=tk.HORIZONTAL,
            variable=self._value,
            command=self._on_change,
        )
        self.scale.pack(fill=tk.X)

    def _on_change(self, value):
        int_value = int(float(value))
        if hasattr(self, 'value_label'):
            self.value_label.config(text=str(int_value))
        if self.command:
            self.command(int_value)

    def get(self) -> int:
        return self._value.get()

    def set(self, value: int):
        self._value.set(value)
        if hasattr(self, 'value_label'):
            self.value_label.config(text=str(value))


class ModernCombobox(tk.Frame):
    """A modern styled combobox/dropdown."""

    def __init__(
        self,
        parent: tk.Widget,
        values: List[str] = None,
        default: str = "",
        label: str = "",
        command: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, bg=ThemeColors.BG_SECONDARY, **kwargs)

        self.command = command
        self._value = tk.StringVar(value=default)

        if label:
            tk.Label(
                self,
                text=label,
                bg=ThemeColors.BG_SECONDARY,
                fg=ThemeColors.FG_SECONDARY,
                font=(FONT_FAMILY, FONT_SIZE_SMALL),
            ).pack(anchor=tk.W, pady=(0, 5))

        # Combobox
        self.combobox = ttk.Combobox(
            self,
            textvariable=self._value,
            values=values or [],
            state="readonly",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
        )
        self.combobox.pack(fill=tk.X)

        if command:
            self.combobox.bind("<<ComboboxSelected>>", lambda e: command(self._value.get()))

    def get(self) -> str:
        return self._value.get()

    def set(self, value: str):
        self._value.set(value)

    def set_values(self, values: List[str]):
        self.combobox["values"] = values
        if values and not self._value.get():
            self._value.set(values[0])

    def set_state(self, state: str):
        self.combobox.config(state=state)


class DropZone(tk.Canvas):
    """A drag-and-drop zone for file selection."""

    def __init__(
        self,
        parent: tk.Widget,
        on_drop: Callable[[List[str]], None],
        on_browse: Callable[[], None],
        width: int = 400,
        height: int = 200,
        **kwargs
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=ThemeColors.DROP_ZONE_BG,
            highlightthickness=2,
            highlightbackground=ThemeColors.DROP_ZONE_BORDER,
            **kwargs
        )

        self.on_drop = on_drop
        self.on_browse = on_browse
        self._width = width
        self._height = height
        self._is_active = False

        self._draw_content()
        self._bind_events()
        self._setup_dnd()

    def _draw_content(self):
        """Draw the drop zone content."""
        self.delete("all")

        center_x = self._width // 2
        center_y = self._height // 2 - 20

        # Draw dashed border
        dash_pattern = (8, 4)
        border_color = ThemeColors.DROP_ZONE_BORDER_ACTIVE if self._is_active else ThemeColors.DROP_ZONE_BORDER

        # Draw icon (folder/file icon using text)
        icon_text = "+"
        self.create_text(
            center_x,
            center_y - 20,
            text=icon_text,
            fill=ThemeColors.ACCENT_LIGHT if self._is_active else ThemeColors.FG_MUTED,
            font=(FONT_FAMILY, 36, "bold"),
            tags="icon"
        )

        # Draw primary text
        primary_text = "Drop files here" if self._is_active else "Drag & Drop Files Here"
        self.create_text(
            center_x,
            center_y + 30,
            text=primary_text,
            fill=ThemeColors.FG_PRIMARY if self._is_active else ThemeColors.FG_SECONDARY,
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"),
            tags="primary"
        )

        # Draw secondary text
        self.create_text(
            center_x,
            center_y + 55,
            text="or click to browse",
            fill=ThemeColors.FG_MUTED,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            tags="secondary"
        )

        # Draw supported formats
        self.create_text(
            center_x,
            center_y + 85,
            text="Supports: PNG, JPG, WEBP, PDF, CSV, JSON, XLSX",
            fill=ThemeColors.FG_MUTED,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            tags="formats"
        )

    def _bind_events(self):
        """Bind mouse events."""
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _setup_dnd(self):
        """Setup drag and drop if tkinterdnd2 is available."""
        try:
            # Try to register drop target
            self.drop_target_register("DND_Files")
            self.dnd_bind("<<DropEnter>>", self._on_drag_enter)
            self.dnd_bind("<<DropLeave>>", self._on_drag_leave)
            self.dnd_bind("<<Drop>>", self._on_dnd_drop)
        except (AttributeError, tk.TclError):
            # tkinterdnd2 not available
            pass

    def _on_click(self, event):
        self.on_browse()

    def _on_enter(self, event):
        self.config(cursor="hand2")

    def _on_leave(self, event):
        self.config(cursor="")

    def _on_drag_enter(self, event):
        self._is_active = True
        self.config(
            bg=ThemeColors.DROP_ZONE_ACTIVE,
            highlightbackground=ThemeColors.DROP_ZONE_BORDER_ACTIVE
        )
        self._draw_content()
        return event.action

    def _on_drag_leave(self, event):
        self._is_active = False
        self.config(
            bg=ThemeColors.DROP_ZONE_BG,
            highlightbackground=ThemeColors.DROP_ZONE_BORDER
        )
        self._draw_content()

    def _on_dnd_drop(self, event):
        self._is_active = False
        self.config(
            bg=ThemeColors.DROP_ZONE_BG,
            highlightbackground=ThemeColors.DROP_ZONE_BORDER
        )
        self._draw_content()

        # Parse dropped files
        files = self._parse_drop_data(event.data)
        if files:
            self.on_drop(files)

        return event.action

    def _parse_drop_data(self, data: str) -> List[str]:
        """Parse the dropped file data."""
        files = []

        # Handle different formats
        if data.startswith("{"):
            # Tcl list format with braces
            import re
            matches = re.findall(r'\{([^}]+)\}|(\S+)', data)
            for match in matches:
                file_path = match[0] if match[0] else match[1]
                if file_path and os.path.isfile(file_path):
                    files.append(file_path)
        else:
            # Space-separated or newline-separated
            for item in data.replace("\r\n", "\n").split("\n"):
                item = item.strip()
                if item and os.path.isfile(item):
                    files.append(item)

        return files


class FileListView(tk.Frame):
    """A modern file list view using Treeview."""

    def __init__(
        self,
        parent: tk.Widget,
        on_remove: Callable[[List[str]], None],
        **kwargs
    ):
        super().__init__(parent, bg=ThemeColors.BG_SECONDARY, **kwargs)

        self.on_remove = on_remove
        self._files: Dict[str, FileItem] = {}

        # Create Treeview with scrollbar
        self.tree_frame = tk.Frame(self, bg=ThemeColors.BG_SECONDARY)
        self.tree_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbar
        self.scrollbar = ttk.Scrollbar(self.tree_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Treeview
        self.tree = ttk.Treeview(
            self.tree_frame,
            columns=("name", "size", "type", "status"),
            show="headings",
            selectmode="extended",
            yscrollcommand=self.scrollbar.set,
        )
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.scrollbar.config(command=self.tree.yview)

        # Configure columns
        self.tree.heading("name", text="File Name", anchor=tk.W)
        self.tree.heading("size", text="Size", anchor=tk.W)
        self.tree.heading("type", text="Type", anchor=tk.W)
        self.tree.heading("status", text="Status", anchor=tk.W)

        self.tree.column("name", width=250, minwidth=150)
        self.tree.column("size", width=80, minwidth=60)
        self.tree.column("type", width=80, minwidth=60)
        self.tree.column("status", width=100, minwidth=80)

        # Bind right-click menu
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Delete>", self._on_delete_key)

        # Context menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Remove Selected", command=self._remove_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Clear All", command=self._clear_all)

    def add_file(self, file_item: FileItem):
        """Add a file to the list."""
        file_key = str(file_item.path)

        if file_key in self._files:
            return  # Already exists

        self._files[file_key] = file_item

        # Determine status display
        status_display = {
            "pending": "Pending",
            "converting": "Converting...",
            "success": "Done",
            "error": "Error",
        }.get(file_item.status, file_item.status)

        # Insert into tree
        self.tree.insert(
            "",
            tk.END,
            iid=file_key,
            values=(
                file_item.path.name,
                format_file_size(file_item.size),
                file_item.format_type.capitalize(),
                status_display,
            ),
        )

    def update_file_status(self, file_path: str, status: str, error: str = None):
        """Update the status of a file."""
        if file_path in self._files:
            self._files[file_path].status = status
            self._files[file_path].error_message = error

            status_display = {
                "pending": "Pending",
                "converting": "Converting...",
                "success": "Done",
                "error": f"Error: {error[:20]}..." if error and len(error) > 20 else f"Error: {error}" if error else "Error",
            }.get(status, status)

            self.tree.set(file_path, "status", status_display)

    def get_files(self) -> List[FileItem]:
        """Get all files in the list."""
        return list(self._files.values())

    def get_pending_files(self) -> List[FileItem]:
        """Get files that are pending conversion."""
        return [f for f in self._files.values() if f.status == "pending"]

    def clear(self):
        """Clear all files from the list."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._files.clear()

    def _show_context_menu(self, event):
        """Show the context menu."""
        if self.tree.selection():
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def _on_delete_key(self, event):
        """Handle delete key press."""
        self._remove_selected()

    def _remove_selected(self):
        """Remove selected files."""
        selected = self.tree.selection()
        removed_paths = []

        for item in selected:
            if item in self._files:
                removed_paths.append(item)
                del self._files[item]
            self.tree.delete(item)

        if removed_paths:
            self.on_remove(removed_paths)

    def _clear_all(self):
        """Clear all files."""
        if messagebox.askyesno("Clear All", "Are you sure you want to clear all files?"):
            removed_paths = list(self._files.keys())
            self.clear()
            self.on_remove(removed_paths)


class ProgressPanel(tk.Frame):
    """A panel showing conversion progress."""

    def __init__(self, parent: tk.Widget, **kwargs):
        super().__init__(parent, bg=ThemeColors.BG_SECONDARY, **kwargs)

        # Status label
        self.status_label = tk.Label(
            self,
            text="Ready",
            bg=ThemeColors.BG_SECONDARY,
            fg=ThemeColors.FG_SECONDARY,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            anchor=tk.W,
        )
        self.status_label.pack(fill=tk.X, pady=(0, 8))

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        # Details label
        self.details_label = tk.Label(
            self,
            text="",
            bg=ThemeColors.BG_SECONDARY,
            fg=ThemeColors.FG_MUTED,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            anchor=tk.W,
        )
        self.details_label.pack(fill=tk.X)

    def set_status(self, text: str):
        """Set the status text."""
        self.status_label.config(text=text)

    def set_progress(self, value: float):
        """Set the progress value (0-100)."""
        self.progress_var.set(value)

    def set_details(self, text: str):
        """Set the details text."""
        self.details_label.config(text=text)

    def reset(self):
        """Reset the progress panel."""
        self.set_status("Ready")
        self.set_progress(0)
        self.set_details("")

    def set_indeterminate(self, enabled: bool):
        """Set the progress bar to indeterminate mode."""
        self.progress_bar.config(mode="indeterminate" if enabled else "determinate")
        if enabled:
            self.progress_bar.start(10)
        else:
            self.progress_bar.stop()


# =============================================================================
# Main Application Window
# =============================================================================

class FileForgeApp:
    """Main application class for FileForge GUI."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self._conversion_thread: Optional[threading.Thread] = None
        self._is_converting = False
        self._cancel_requested = False

        # Configure root window
        self._configure_window()
        self._configure_styles()
        self._create_ui()
        self._setup_converters()

    def _configure_window(self):
        """Configure the main window."""
        self.root.title(f"{APP_NAME} - Universal File Converter")
        self.root.geometry(f"{WINDOW_DEFAULT_WIDTH}x{WINDOW_DEFAULT_HEIGHT}")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.configure(bg=ThemeColors.BG_PRIMARY)

        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"+{x}+{y}")

        # Set window icon if available
        try:
            # Try to set a simple icon
            pass  # Icon handling can be added later
        except Exception:
            pass

    def _configure_styles(self):
        """Configure ttk styles for the dark theme."""
        style = ttk.Style()

        # Try to use a theme that supports customization
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Configure colors
        style.configure(
            ".",
            background=ThemeColors.BG_SECONDARY,
            foreground=ThemeColors.FG_PRIMARY,
            fieldbackground=ThemeColors.BG_INPUT,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
        )

        # Treeview style
        style.configure(
            "Treeview",
            background=ThemeColors.BG_INPUT,
            foreground=ThemeColors.FG_PRIMARY,
            fieldbackground=ThemeColors.BG_INPUT,
            rowheight=28,
        )
        style.configure(
            "Treeview.Heading",
            background=ThemeColors.BG_TERTIARY,
            foreground=ThemeColors.FG_PRIMARY,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
        )
        style.map(
            "Treeview",
            background=[("selected", ThemeColors.ACCENT_PRIMARY)],
            foreground=[("selected", ThemeColors.FG_PRIMARY)],
        )

        # Combobox style
        style.configure(
            "TCombobox",
            fieldbackground=ThemeColors.BG_INPUT,
            background=ThemeColors.BG_INPUT,
            foreground=ThemeColors.FG_PRIMARY,
            arrowcolor=ThemeColors.FG_PRIMARY,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", ThemeColors.BG_INPUT)],
            foreground=[("readonly", ThemeColors.FG_PRIMARY)],
        )

        # Scale style
        style.configure(
            "TScale",
            background=ThemeColors.BG_SECONDARY,
            troughcolor=ThemeColors.PROGRESS_BG,
        )

        # Progress bar style
        style.configure(
            "TProgressbar",
            background=ThemeColors.PROGRESS_FG,
            troughcolor=ThemeColors.PROGRESS_BG,
            borderwidth=0,
            thickness=8,
        )

        # Scrollbar style
        style.configure(
            "TScrollbar",
            background=ThemeColors.BG_TERTIARY,
            troughcolor=ThemeColors.BG_INPUT,
            arrowcolor=ThemeColors.FG_SECONDARY,
        )

    def _create_ui(self):
        """Create the main user interface."""
        # Main container
        self.main_container = tk.Frame(self.root, bg=ThemeColors.BG_PRIMARY)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=PADDING_LARGE, pady=PADDING_LARGE)

        # Header
        self._create_header()

        # Bottom area - Progress and actions (pack first with side=BOTTOM)
        self._create_bottom_area()

        # Content area (two columns) - pack after bottom so it fills remaining space
        self.content_frame = tk.Frame(self.main_container, bg=ThemeColors.BG_PRIMARY)
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=(PADDING_MEDIUM, 0))

        # Left column - File selection and list
        self._create_left_column()

        # Right column - Options
        self._create_right_column()

    def _create_header(self):
        """Create the header section."""
        header_frame = tk.Frame(self.main_container, bg=ThemeColors.BG_PRIMARY)
        header_frame.pack(fill=tk.X, pady=(0, PADDING_MEDIUM))

        # App title
        title_label = tk.Label(
            header_frame,
            text=APP_NAME,
            bg=ThemeColors.BG_PRIMARY,
            fg=ThemeColors.ACCENT_LIGHT,
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
        )
        title_label.pack(side=tk.LEFT)

        # Subtitle
        subtitle_label = tk.Label(
            header_frame,
            text=" - Universal File Converter",
            bg=ThemeColors.BG_PRIMARY,
            fg=ThemeColors.FG_SECONDARY,
            font=(FONT_FAMILY, FONT_SIZE_LARGE),
        )
        subtitle_label.pack(side=tk.LEFT, pady=(4, 0))

        # Version
        version_label = tk.Label(
            header_frame,
            text=f"v{APP_VERSION}",
            bg=ThemeColors.BG_PRIMARY,
            fg=ThemeColors.FG_MUTED,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
        )
        version_label.pack(side=tk.RIGHT)

    def _create_left_column(self):
        """Create the left column with file selection."""
        self.left_frame = tk.Frame(
            self.content_frame,
            bg=ThemeColors.BG_SECONDARY,
            highlightthickness=0,
        )
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, PADDING_SMALL))

        # Inner padding
        inner_frame = tk.Frame(self.left_frame, bg=ThemeColors.BG_SECONDARY)
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

        # Section title
        section_title = tk.Label(
            inner_frame,
            text="Input Files",
            bg=ThemeColors.BG_SECONDARY,
            fg=ThemeColors.FG_PRIMARY,
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"),
        )
        section_title.pack(anchor=tk.W, pady=(0, PADDING_MEDIUM))

        # Drop zone
        self.drop_zone = DropZone(
            inner_frame,
            on_drop=self._on_files_dropped,
            on_browse=self._browse_files,
            width=450,
            height=150,
        )
        self.drop_zone.pack(fill=tk.X, pady=(0, PADDING_MEDIUM))

        # File list section title
        list_title_frame = tk.Frame(inner_frame, bg=ThemeColors.BG_SECONDARY)
        list_title_frame.pack(fill=tk.X, pady=(PADDING_SMALL, PADDING_SMALL))

        tk.Label(
            list_title_frame,
            text="Selected Files",
            bg=ThemeColors.BG_SECONDARY,
            fg=ThemeColors.FG_PRIMARY,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
        ).pack(side=tk.LEFT)

        self.file_count_label = tk.Label(
            list_title_frame,
            text="(0 files)",
            bg=ThemeColors.BG_SECONDARY,
            fg=ThemeColors.FG_MUTED,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
        )
        self.file_count_label.pack(side=tk.LEFT, padx=(PADDING_SMALL, 0))

        # File list
        self.file_list = FileListView(
            inner_frame,
            on_remove=self._on_files_removed,
        )
        self.file_list.pack(fill=tk.BOTH, expand=True)

    def _create_right_column(self):
        """Create the right column with options."""
        self.right_frame = tk.Frame(
            self.content_frame,
            bg=ThemeColors.BG_SECONDARY,
            width=320,
        )
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(PADDING_SMALL, 0))
        self.right_frame.pack_propagate(False)

        # Inner padding
        inner_frame = tk.Frame(self.right_frame, bg=ThemeColors.BG_SECONDARY)
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

        # Section title
        section_title = tk.Label(
            inner_frame,
            text="Conversion Options",
            bg=ThemeColors.BG_SECONDARY,
            fg=ThemeColors.FG_PRIMARY,
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"),
        )
        section_title.pack(anchor=tk.W, pady=(0, PADDING_MEDIUM))

        # Output format selection
        self.output_format = ModernCombobox(
            inner_frame,
            values=[],
            label="Output Format",
            command=self._on_format_changed,
        )
        self.output_format.pack(fill=tk.X, pady=(0, PADDING_MEDIUM))

        # Separator
        separator = tk.Frame(inner_frame, bg=ThemeColors.BORDER_DEFAULT, height=1)
        separator.pack(fill=tk.X, pady=PADDING_MEDIUM)

        # Image options frame
        self.image_options_frame = tk.Frame(inner_frame, bg=ThemeColors.BG_SECONDARY)
        self.image_options_frame.pack(fill=tk.X, pady=(0, PADDING_MEDIUM))

        # Quality slider
        self.quality_scale = ModernScale(
            self.image_options_frame,
            from_=1,
            to=100,
            value=85,
            label="Quality",
        )
        self.quality_scale.pack(fill=tk.X, pady=(0, PADDING_MEDIUM))

        # Resize options
        resize_label = tk.Label(
            self.image_options_frame,
            text="Resize (optional)",
            bg=ThemeColors.BG_SECONDARY,
            fg=ThemeColors.FG_SECONDARY,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
        )
        resize_label.pack(anchor=tk.W, pady=(0, PADDING_SMALL))

        resize_frame = tk.Frame(self.image_options_frame, bg=ThemeColors.BG_SECONDARY)
        resize_frame.pack(fill=tk.X)

        # Width entry
        width_frame = tk.Frame(resize_frame, bg=ThemeColors.BG_SECONDARY)
        width_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, PADDING_SMALL))

        tk.Label(
            width_frame,
            text="Width",
            bg=ThemeColors.BG_SECONDARY,
            fg=ThemeColors.FG_MUTED,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
        ).pack(anchor=tk.W)

        self.width_entry = ModernEntry(width_frame, placeholder="Auto")
        self.width_entry.pack(fill=tk.X)

        # Height entry
        height_frame = tk.Frame(resize_frame, bg=ThemeColors.BG_SECONDARY)
        height_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            height_frame,
            text="Height",
            bg=ThemeColors.BG_SECONDARY,
            fg=ThemeColors.FG_MUTED,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
        ).pack(anchor=tk.W)

        self.height_entry = ModernEntry(height_frame, placeholder="Auto")
        self.height_entry.pack(fill=tk.X)

        # Separator
        separator2 = tk.Frame(inner_frame, bg=ThemeColors.BORDER_DEFAULT, height=1)
        separator2.pack(fill=tk.X, pady=PADDING_MEDIUM)

        # Output directory
        output_dir_label = tk.Label(
            inner_frame,
            text="Output Directory",
            bg=ThemeColors.BG_SECONDARY,
            fg=ThemeColors.FG_SECONDARY,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
        )
        output_dir_label.pack(anchor=tk.W, pady=(0, PADDING_SMALL))

        output_dir_frame = tk.Frame(inner_frame, bg=ThemeColors.BG_SECONDARY)
        output_dir_frame.pack(fill=tk.X)

        self.output_dir_entry = ModernEntry(output_dir_frame, placeholder="Same as input")
        self.output_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, PADDING_SMALL))

        self.browse_output_btn = ModernButton(
            output_dir_frame,
            text="...",
            command=self._browse_output_dir,
            width=40,
            height=32,
            bg_color=ThemeColors.BG_TERTIARY,
            hover_color=ThemeColors.BG_HOVER,
        )
        self.browse_output_btn.pack(side=tk.RIGHT)

    def _create_bottom_area(self):
        """Create the bottom area with progress and action buttons."""
        bottom_frame = tk.Frame(self.main_container, bg=ThemeColors.BG_PRIMARY)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(PADDING_MEDIUM, 0))

        # Progress panel
        progress_container = tk.Frame(bottom_frame, bg=ThemeColors.BG_SECONDARY)
        progress_container.pack(fill=tk.X, pady=(0, PADDING_MEDIUM))

        self.progress_panel = ProgressPanel(progress_container)
        self.progress_panel.pack(fill=tk.X, padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

        # Action buttons
        buttons_frame = tk.Frame(bottom_frame, bg=ThemeColors.BG_PRIMARY)
        buttons_frame.pack(fill=tk.X)

        # Clear button
        self.clear_btn = ModernButton(
            buttons_frame,
            text="Clear All",
            command=self._clear_all,
            width=100,
            bg_color=ThemeColors.BG_TERTIARY,
            hover_color=ThemeColors.BG_HOVER,
        )
        self.clear_btn.pack(side=tk.LEFT, padx=(0, PADDING_SMALL))

        # Spacer
        spacer = tk.Frame(buttons_frame, bg=ThemeColors.BG_PRIMARY)
        spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Cancel button (hidden by default)
        self.cancel_btn = ModernButton(
            buttons_frame,
            text="Cancel",
            command=self._cancel_conversion,
            width=100,
            bg_color=ThemeColors.ERROR,
            hover_color=ThemeColors.ERROR_LIGHT,
        )
        # Not packed initially

        # Convert button
        self.convert_btn = ModernButton(
            buttons_frame,
            text="Convert",
            command=self._start_conversion,
            width=140,
            height=40,
            font_size=FONT_SIZE_LARGE,
        )
        self.convert_btn.pack(side=tk.RIGHT)

    def _setup_converters(self):
        """Setup converter instances."""
        try:
            from fileforge.converters import (
                ImageConverter,
                DocumentConverter,
                DataConverter,
                get_supported_formats,
            )

            self.image_converter = ImageConverter()
            self.document_converter = DocumentConverter()
            self.data_converter = DataConverter()
            self.get_supported_formats = get_supported_formats
            self._converters_available = True
        except ImportError as e:
            logger.warning(f"Could not import converters: {e}")
            self._converters_available = False
            messagebox.showwarning(
                "Warning",
                "Converter modules not found. Some features may be unavailable.\n\n"
                "Make sure the fileforge package is properly installed."
            )

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def _on_files_dropped(self, files: List[str]):
        """Handle files dropped into the drop zone."""
        self._add_files(files)

    def _browse_files(self):
        """Open file browser dialog."""
        filetypes = [
            ("All Supported", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif;*.pdf;*.csv;*.json;*.xlsx;*.xls"),
            ("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif"),
            ("PDF Documents", "*.pdf"),
            ("Data Files", "*.csv;*.json;*.xlsx;*.xls"),
            ("All Files", "*.*"),
        ]

        files = filedialog.askopenfilenames(
            title="Select Files to Convert",
            filetypes=filetypes,
        )

        if files:
            self._add_files(list(files))

    def _add_files(self, file_paths: List[str]):
        """Add files to the conversion queue."""
        added_count = 0
        categories_found = set()

        for file_path in file_paths:
            path = Path(file_path)

            if not path.exists():
                continue

            category = get_file_category(path)
            if category is None:
                continue

            try:
                size = path.stat().st_size
            except OSError:
                size = 0

            file_item = FileItem(
                path=path,
                size=size,
                format_type=category,
            )

            self.file_list.add_file(file_item)
            categories_found.add(category)
            added_count += 1

        # Update file count
        total_files = len(self.file_list.get_files())
        self.file_count_label.config(text=f"({total_files} file{'s' if total_files != 1 else ''})")

        # Update output format options based on categories
        if categories_found:
            self._update_output_formats(categories_found)

        if added_count > 0:
            self.progress_panel.set_status(f"Added {added_count} file(s)")

    def _on_files_removed(self, removed_paths: List[str]):
        """Handle files removed from the list."""
        total_files = len(self.file_list.get_files())
        self.file_count_label.config(text=f"({total_files} file{'s' if total_files != 1 else ''})")

        # Update output formats
        if total_files > 0:
            categories = set(f.format_type for f in self.file_list.get_files())
            self._update_output_formats(categories)
        else:
            self.output_format.set_values([])

    def _update_output_formats(self, categories: set):
        """Update available output formats based on selected file types."""
        formats = []

        for category in categories:
            category_formats = get_output_formats(category)
            for fmt in category_formats:
                if fmt not in formats:
                    formats.append(fmt)

        self.output_format.set_values(formats)

        # Show/hide image options based on categories
        if "image" in categories:
            self.image_options_frame.pack(fill=tk.X, pady=(0, PADDING_MEDIUM))
        else:
            self.image_options_frame.pack_forget()

    def _on_format_changed(self, value: str):
        """Handle output format change."""
        # Show/hide relevant options based on format
        pass

    def _browse_output_dir(self):
        """Browse for output directory."""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir_entry.set(directory)

    def _clear_all(self):
        """Clear all files and reset the form."""
        self.file_list.clear()
        self.file_count_label.config(text="(0 files)")
        self.output_format.set_values([])
        self.output_dir_entry.set("")
        self.width_entry.set("")
        self.height_entry.set("")
        self.quality_scale.set(85)
        self.progress_panel.reset()

    def _start_conversion(self):
        """Start the conversion process."""
        files = self.file_list.get_pending_files()

        if not files:
            messagebox.showwarning("No Files", "Please add files to convert.")
            return

        output_format = self.output_format.get()
        if not output_format:
            messagebox.showwarning("No Format", "Please select an output format.")
            return

        if not self._converters_available:
            messagebox.showerror("Error", "Converters not available.")
            return

        # Get options
        options = {
            "quality": self.quality_scale.get(),
            "width": self._parse_int(self.width_entry.get()),
            "height": self._parse_int(self.height_entry.get()),
            "output_dir": self.output_dir_entry.get() or None,
            "output_format": output_format,
        }

        # Disable UI during conversion
        self._set_ui_state(False)
        self._is_converting = True
        self._cancel_requested = False

        # Show cancel button
        self.cancel_btn.pack(side=tk.RIGHT, padx=(0, PADDING_SMALL))

        # Start conversion in background thread
        self._conversion_thread = threading.Thread(
            target=self._run_conversion,
            args=(files, options),
            daemon=True,
        )
        self._conversion_thread.start()

    def _parse_int(self, value: str) -> Optional[int]:
        """Parse string to int, return None if invalid."""
        try:
            return int(value) if value else None
        except ValueError:
            return None

    def _run_conversion(self, files: List[FileItem], options: Dict[str, Any]):
        """Run the conversion process in a background thread."""
        from fileforge.converters import (
            ImageConversionOptions,
            DataConversionOptions,
            ImageFormat,
            DataFormat,
        )

        total = len(files)
        success_count = 0
        error_count = 0

        output_format = options["output_format"]
        output_dir = options["output_dir"]

        for idx, file_item in enumerate(files):
            if self._cancel_requested:
                break

            file_path = str(file_item.path)

            # Update status
            self.root.after(0, lambda f=file_path: self.file_list.update_file_status(f, "converting"))
            self.root.after(0, lambda i=idx, t=total, n=file_item.path.name: self._update_progress(i, t, f"Converting {n}..."))

            try:
                # Determine output path
                if output_dir:
                    out_dir = Path(output_dir)
                else:
                    out_dir = file_item.path.parent

                out_dir.mkdir(parents=True, exist_ok=True)

                # Get proper extension
                ext_map = {
                    "PNG": ".png", "JPG": ".jpg", "JPEG": ".jpg",
                    "WEBP": ".webp", "BMP": ".bmp", "GIF": ".gif",
                    "TXT": ".txt", "PNG (pages)": ".png",
                    "CSV": ".csv", "JSON": ".json", "XLSX": ".xlsx",
                }
                new_ext = ext_map.get(output_format, f".{output_format.lower()}")
                output_path = out_dir / f"{file_item.path.stem}{new_ext}"

                # Progress callback
                def progress_callback(current: int, total: int, message: str):
                    if total > 0:
                        pct = (current / total) * 100
                        self.root.after(0, lambda p=pct: self.progress_panel.set_progress(p))

                # Perform conversion based on type
                if file_item.format_type == "image":
                    img_options = ImageConversionOptions(
                        quality=options["quality"],
                        width=options["width"],
                        height=options["height"],
                    )

                    result = self.image_converter.convert(
                        file_item.path,
                        output_path,
                        output_format=ImageFormat.from_extension(new_ext),
                        options=img_options,
                        progress_callback=progress_callback,
                    )

                elif file_item.format_type == "document":
                    if output_format == "TXT":
                        result = self.document_converter.pdf_to_text(
                            file_item.path,
                            output_path,
                            progress_callback=progress_callback,
                        )
                    elif output_format == "PNG (pages)":
                        # Output to directory for images
                        result = self.document_converter.pdf_to_images(
                            file_item.path,
                            out_dir / file_item.path.stem,
                            progress_callback=progress_callback,
                        )
                    else:
                        raise ValueError(f"Unsupported document output: {output_format}")

                elif file_item.format_type == "data":
                    data_options = DataConversionOptions()

                    result = self.data_converter.convert(
                        file_item.path,
                        output_path,
                        output_format=DataFormat.from_extension(new_ext),
                        options=data_options,
                        progress_callback=progress_callback,
                    )
                else:
                    raise ValueError(f"Unknown file type: {file_item.format_type}")

                # Check result
                if result.is_success:
                    self.root.after(0, lambda f=file_path: self.file_list.update_file_status(f, "success"))
                    success_count += 1
                else:
                    error_msg = result.error_message or "Unknown error"
                    self.root.after(0, lambda f=file_path, e=error_msg: self.file_list.update_file_status(f, "error", e))
                    error_count += 1

            except Exception as e:
                logger.exception(f"Conversion error for {file_path}")
                error_msg = str(e)
                self.root.after(0, lambda f=file_path, e=error_msg: self.file_list.update_file_status(f, "error", e))
                error_count += 1

        # Conversion complete
        self.root.after(0, lambda: self._conversion_complete(success_count, error_count, self._cancel_requested))

    def _update_progress(self, current: int, total: int, message: str):
        """Update progress panel from main thread."""
        if total > 0:
            percent = ((current + 1) / total) * 100
            self.progress_panel.set_progress(percent)
        self.progress_panel.set_status(message)
        self.progress_panel.set_details(f"File {current + 1} of {total}")

    def _conversion_complete(self, success: int, errors: int, cancelled: bool):
        """Handle conversion completion."""
        self._is_converting = False

        # Hide cancel button
        self.cancel_btn.pack_forget()

        # Re-enable UI
        self._set_ui_state(True)

        # Update progress panel
        if cancelled:
            self.progress_panel.set_status("Conversion cancelled")
            messagebox.showinfo("Cancelled", "Conversion was cancelled.")
        elif errors == 0:
            self.progress_panel.set_status(f"Completed! {success} file(s) converted successfully.")
            self.progress_panel.set_progress(100)
            messagebox.showinfo("Success", f"Successfully converted {success} file(s)!")
        else:
            self.progress_panel.set_status(f"Completed with {errors} error(s). {success} succeeded.")
            messagebox.showwarning(
                "Completed with Errors",
                f"Converted {success} file(s) successfully.\n{errors} file(s) had errors."
            )

    def _cancel_conversion(self):
        """Cancel the current conversion."""
        if self._is_converting:
            self._cancel_requested = True
            self.progress_panel.set_status("Cancelling...")

    def _set_ui_state(self, enabled: bool):
        """Enable or disable UI elements during conversion."""
        state = "normal" if enabled else "disabled"

        self.convert_btn.set_disabled(not enabled)
        self.clear_btn.set_disabled(not enabled)
        self.browse_output_btn.set_disabled(not enabled)
        self.output_format.set_state("readonly" if enabled else "disabled")
        self.width_entry.set_state(state)
        self.height_entry.set_state(state)


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for the FileForge GUI."""
    # Try to use tkinterdnd2 for drag and drop support
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        # Fall back to standard Tk if tkinterdnd2 is not available
        root = tk.Tk()
        logger.info("tkinterdnd2 not available, drag and drop will be limited")

    # Create and run the application
    app = FileForgeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
