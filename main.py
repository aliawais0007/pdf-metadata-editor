import sys
import json
import os
import subprocess
import shutil
from pathlib import Path
import ctypes

from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QLineEdit,
    QTextEdit,
    QFormLayout,
    QListWidget,
    QMessageBox,
)

from pypdf import PdfReader, PdfWriter

APP_DIR = Path(__file__).parent
SETTINGS_PATH = APP_DIR / "settings.json"


def load_settings():
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"defaults": {}, "output_dir": ""}


def save_settings(data):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.settings = settings

        layout = QVBoxLayout()

        form = QFormLayout()
        self.fields = {}
        for key, val in settings.get("defaults", {}).items():
            le = QLineEdit(val)
            le.setMinimumWidth(360)
            self.fields[key] = le
            form.addRow(QLabel(key), le)

        layout.addLayout(form)

        out_layout = QHBoxLayout()
        self.out_dir = QLineEdit(settings.get("output_dir", ""))
        self.out_dir.setMinimumWidth(360)
        out_btn = QPushButton("Browse")
        out_btn.clicked.connect(self.browse)
        out_layout.addWidget(QLabel("Output Directory"))
        out_layout.addWidget(self.out_dir)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        btns = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

        self.setLayout(layout)

    def browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select output directory")
        if d:
            self.out_dir.setText(d)

    def save(self):
        for k, widget in self.fields.items():
            self.settings["defaults"][k] = widget.text()
        self.settings["output_dir"] = self.out_dir.text()
        save_settings(self.settings)
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Metadata Editor")
        # use QtGui to create a simple app icon
        # try to load an SVG icon from assets, otherwise fall back to generated pixmap
        try:
            icon_path = APP_DIR / "assets" / "icon.svg"
            if icon_path.exists():
                self.setWindowIcon(QtGui.QIcon(str(icon_path)))
            else:
                pix = QtGui.QPixmap(64, 64)
                pix.fill(QtGui.QColor("#2b7a78"))
                self.setWindowIcon(QtGui.QIcon(pix))
        except Exception:
            pix = QtGui.QPixmap(64, 64)
            pix.fill(QtGui.QColor("#2b7a78"))
            self.setWindowIcon(QtGui.QIcon(pix))
        self.settings = load_settings()
        # store the last-loaded original metadata for the selected file
        self._original_meta = {}
        # reduce Cocoa layout warnings by constraining button heights
        try:
            QApplication.instance().setStyleSheet('''
                /* Buttons */
                QPushButton { min-height: 26px; max-height: 36px; padding: 8px 12px; border-radius: 8px; border: 1px solid #ddd; background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fafafa, stop:1 #f0f0f0); color: #111; }
                QPushButton[primary="true"] { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2b7a78, stop:1 #1f5f5b); color: white; border: 1px solid #1a5e58; }
                QPushButton[primary="true"]:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3aa89f, stop:1 #27897f); }
                QPushButton[primary="true"]:pressed { background: #18605a; }
                QPushButton:pressed { background: #e8e8e8; }

                /* File list */
                QListWidget { background: white; border: 1px solid #ddd; }
                QListWidget::item { padding: 6px; }
                QListWidget::item:selected { background: #cfeee7; color: #000; }
                QListWidget::item:hover { background: #eef9f4; }

                /* Line edits and text */
                QLineEdit, QTextEdit { border: 1px solid #ccc; border-radius: 4px; padding: 4px; }
            ''')
        except Exception:
            pass

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout()
        central.setLayout(layout)

        left = QVBoxLayout()
        right = QVBoxLayout()

        # file list (supports drag & drop)
        class FileListWidget(QListWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setAcceptDrops(True)
                self.setAlternatingRowColors(True)
                self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
                self.setUniformItemSizes(True)
                self.setSpacing(4)

            def dragEnterEvent(self, event):
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()
                else:
                    super().dragEnterEvent(event)

            def dragMoveEvent(self, event):
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()
                else:
                    super().dragMoveEvent(event)

            def dropEvent(self, event):
                if event.mimeData().hasUrls():
                    for url in event.mimeData().urls():
                        path = url.toLocalFile()
                        if path and path.lower().endswith('.pdf'):
                            # create item with icon and store full path in UserRole
                            icon = QtGui.QIcon(str(APP_DIR / 'assets' / 'icon.png')) if (APP_DIR / 'assets' / 'icon.png').exists() else QtGui.QIcon()
                            item = QtWidgets.QListWidgetItem(icon, os.path.basename(path))
                            item.setToolTip(path)
                            item.setData(QtCore.Qt.ItemDataRole.UserRole, path)
                            self.addItem(item)
                    event.acceptProposedAction()
                else:
                    super().dropEvent(event)

        self.file_list = FileListWidget()
        left.addWidget(QLabel("Files"))
        left.addWidget(self.file_list)

        # file list controls
        file_controls = QHBoxLayout()
        add_btn = QPushButton("Add Files")
        add_btn.clicked.connect(self.add_files)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_selected)
        clear_btn = QPushButton("Clear List")
        clear_btn.clicked.connect(self.clear_list)
        # mark action buttons as primary for styling (use string values for style selector)
        add_btn.setProperty('primary', 'true')
        remove_btn.setProperty('primary', 'false')
        clear_btn.setProperty('primary', 'false')
        file_controls.addWidget(add_btn)
        file_controls.addWidget(remove_btn)
        file_controls.addWidget(clear_btn)
        left.addLayout(file_controls)

        # process and settings buttons
        process_btn = QPushButton("One-Click Process All")
        process_btn.clicked.connect(self.process_all)
        process_btn.setProperty('primary', 'true')
        left.addWidget(process_btn)

        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings)
        settings_btn.setProperty('primary', 'false')
        left.addWidget(settings_btn)

        # simple status / count label
        self.file_count_label = QLabel("0 files")
        left.addWidget(self.file_count_label)

        layout.addLayout(left, 1)

        # metadata editor
        self.form = QFormLayout()
        self.meta_fields = {}
        # Standard PDF metadata fields to show by default
        standard_keys = [
            "Title",
            "Author",
            "Subject",
            "Keywords",
            "Creator",
            "Producer",
            "CreationDate",
            "ModDate",
            "Trapped",
        ]
        # Start with standard keys, then include any user-saved defaults not already present
        keys = []
        for k in standard_keys:
            keys.append(k)
        for k in list(self.settings.get("defaults", {}).keys()):
            if k not in keys and k != "Where From":
                keys.append(k)

        # add macOS Finder "Where From" (read-only) so users can see origin
        keys.append("Where From")

        for key in keys:
            le = QLineEdit()
            le.setMinimumWidth(380)
            if key == "Where From":
                le.setReadOnly(True)
            self.meta_fields[key] = le
            self.form.addRow(QLabel(key), le)

        # Raw metadata display (read-only) for any non-standard or extra keys
        self.raw_meta = QTextEdit()
        self.raw_meta.setReadOnly(True)
        self.raw_meta.setMinimumWidth(380)
        self.form.addRow(QLabel("Raw Metadata"), self.raw_meta)

        # Connect field changes to update the raw metadata view
        for k, widget in self.meta_fields.items():
            # Only track editable fields (exclude Where From)
            if k != "Where From":
                widget.textChanged.connect(self._update_raw_meta)

        override_btn = QPushButton("Override with Defaults")
        override_btn.clicked.connect(self.override_defaults)

        save_btn = QPushButton("Save Metadata for Selected")
        save_btn.clicked.connect(self.save_metadata_selected)

        save_defaults_btn = QPushButton("Save Current As Defaults")
        save_defaults_btn.clicked.connect(self.save_current_as_defaults)

        right.addLayout(self.form)
        # button to add custom metadata fields
        add_custom_btn = QPushButton("Add Custom Field")
        add_custom_btn.clicked.connect(self.add_custom_field)
        # ensure these right-side action buttons appear styled
        add_custom_btn.setProperty('primary', 'false')
        override_btn.setProperty('primary', 'false')
        save_btn.setProperty('primary', 'false')
        save_defaults_btn.setProperty('primary', 'false')
        right.addWidget(add_custom_btn)
        right.addWidget(override_btn)
        right.addWidget(save_btn)
        right.addWidget(save_defaults_btn)

        layout.addLayout(right, 2)

        self.file_list.itemSelectionChanged.connect(self.load_selected_metadata)
        # update UI state when list changes
        self.file_list.model().rowsInserted.connect(lambda: self._update_file_ui())
        self.file_list.model().rowsRemoved.connect(lambda: self._update_file_ui())
        self.file_list.model().modelReset.connect(lambda: self._update_file_ui())
        # connect selection change to enable/disable controls
        self.file_list.itemSelectionChanged.connect(self._update_file_ui)

        # store references to buttons for state toggling
        self._process_btn = process_btn
        self._remove_btn = remove_btn

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select PDF files", filter="PDF Files (*.pdf)")
        icon = QtGui.QIcon(str(APP_DIR / 'assets' / 'icon.png')) if (APP_DIR / 'assets' / 'icon.png').exists() else QtGui.QIcon()
        existing = [self.file_list.item(i).data(QtCore.Qt.ItemDataRole.UserRole) for i in range(self.file_list.count())]
        for f in files:
            if not f.lower().endswith('.pdf'):
                continue
            if f in existing:
                continue
            item = QtWidgets.QListWidgetItem(icon, os.path.basename(f))
            item.setToolTip(f)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, f)
            self.file_list.addItem(item)
            existing.append(f)
        self._update_file_ui()

    def load_selected_metadata(self):
        items = self.file_list.selectedItems()
        if not items:
            # still update UI state
            self._update_file_ui()
            return
        path = items[0].data(QtCore.Qt.ItemDataRole.UserRole) or items[0].toolTip()
        try:
            reader = PdfReader(path)
            info = reader.metadata or {}
            # pypdf returns metadata dict with keys like '/Title'
            # populate known fields
            for k, widget in self.meta_fields.items():
                if k == "Where From":
                    widget.setText(self._get_where_from(path))
                else:
                    widget.setText(info.get(f"/{k}", ""))

            # show raw metadata (all keys/values) in JSON-like text
            try:
                # normalize keys (strip leading slash) for readability
                normalized = { (kk[1:] if kk.startswith('/') else kk): vv for kk, vv in info.items() }
                # store the original metadata so _update_raw_meta can show both original and current
                self._original_meta = normalized
                self.raw_meta.setPlainText(json.dumps(normalized, indent=2, ensure_ascii=False))
            except Exception:
                # fallback to simple string representation
                self.raw_meta.setPlainText(str(info))

            # Ensure raw metadata also reflects any editable field changes
            self._update_raw_meta()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to read PDF: {e}")
        finally:
            self._update_file_ui()

    def _update_file_ui(self):
        # update file count and enable/disable buttons based on state
        count = self.file_list.count()
        self.file_count_label.setText(f"{count} file{'s' if count != 1 else ''}")
        # enable process button only when there are files
        try:
            self._process_btn.setEnabled(count > 0)
            self._remove_btn.setEnabled(bool(self.file_list.selectedItems()))
        except Exception:
            pass

    def remove_selected(self):
        items = self.file_list.selectedItems()
        if not items:
            return
        for it in items:
            row = self.file_list.row(it)
            self.file_list.takeItem(row)
        self._update_file_ui()

    def clear_list(self):
        if self.file_list.count() == 0:
            return
        if QMessageBox.question(self, "Confirm", "Clear the entire file list?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.file_list.clear()
        self._update_file_ui()

    def override_defaults(self):
        defaults = self.settings.get("defaults", {})
        for k, widget in self.meta_fields.items():
            if k == "Where From":
                continue
            # Only override fields that are present in stored defaults
            if k in defaults:
                widget.setText(defaults.get(k, ""))

    def save_metadata_selected(self):
        items = self.file_list.selectedItems()
        if not items:
            QMessageBox.information(self, "No selection", "Please select a file first")
            return
        # use the stored full path (UserRole) rather than the displayed name
        path = items[0].data(QtCore.Qt.ItemDataRole.UserRole) or items[0].toolTip() or items[0].text()
        ok = self._write_metadata(path, open_folder=True, reload_ui=True)
        if ok:
            QMessageBox.information(self, "Saved", "Metadata saved")

    def process_all(self):
        count = self.file_list.count()
        if count == 0:
            QMessageBox.information(self, "No files", "Add files first")
            return
        # confirm bulk operation
        if QMessageBox.question(self, "Confirm", f"Process {count} files?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        success_count = 0
        fail_count = 0
        # For batch processing we apply configured defaults only (do not reuse current editor values)
        for i in range(count):
            item = self.file_list.item(i)
            path = item.data(QtCore.Qt.ItemDataRole.UserRole) or item.toolTip()
            if not os.path.isfile(path) or not path.lower().endswith('.pdf'):
                continue
            ok = self._write_metadata(path, apply_defaults_only=True)
            if ok:
                success_count += 1
            else:
                fail_count += 1

        # after batch processing, open the dated output folder if any files succeeded
        if success_count > 0:
            base_out = self.settings.get("output_dir") or os.path.dirname(self.file_list.item(0).data(QtCore.Qt.ItemDataRole.UserRole) or self.file_list.item(0).toolTip())
            date_str = QtCore.QDate.currentDate().toString("yyyy-MM-dd")
            out_dir = os.path.join(base_out, date_str)
            try:
                subprocess.run(["open", out_dir])
            except Exception:
                pass

        # report results
        if fail_count == 0:
            QMessageBox.information(self, "Done", f"Processed {success_count} files")
        else:
            QMessageBox.information(self, "Done", f"Processed {success_count} files, {fail_count} failures")

    def _write_metadata(self, path, apply_defaults=False, open_folder: bool = False, reload_ui: bool = False, apply_defaults_only: bool = False):
        try:
            # basic validation
            if not os.path.isfile(path):
                raise FileNotFoundError(f"File not found: {path}")
            if not path.lower().endswith('.pdf'):
                raise ValueError("Not a PDF file")
            reader = PdfReader(path)
            writer = PdfWriter()
            for p in reader.pages:
                writer.add_page(p)

            meta = {}
            defaults = self.settings.get("defaults", {})
            for k, widget in self.meta_fields.items():
                # skip macOS Finder "Where From" when writing PDF metadata
                if k == "Where From":
                    continue
                if apply_defaults_only:
                    # batch mode: use configured defaults only
                    val = defaults.get(k, "")
                else:
                    val = widget.text() or ""
                    if apply_defaults and not val:
                        val = defaults.get(k, "")
                meta[f"/{k}"] = val

            writer.add_metadata(meta)

            # Save inside the output directory under a dated folder (YYYY-MM-DD)
            base_out = self.settings.get("output_dir") or os.path.dirname(path)
            date_str = QtCore.QDate.currentDate().toString("yyyy-MM-dd")
            out_dir = os.path.join(base_out, date_str)
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, os.path.basename(path))
            # write to output
            with open(out_path, "wb") as f:
                writer.write(f)
            # Preserve original atime and mtime (and permission bits) when possible
            try:
                shutil.copystat(path, out_path)
            except Exception:
                try:
                    # fallback: copy atime/mtime using os.utime
                    st = os.stat(path)
                    os.utime(out_path, (st.st_atime, st.st_mtime))
                except Exception:
                    pass
            # Optionally open the output folder (macOS)
            if open_folder:
                try:
                    subprocess.run(["open", out_dir])
                except Exception:
                    pass
            # If requested reload metadata for the saved file into the UI
            if reload_ui:
                try:
                    # if the saved file is selected, reload its metadata
                    self.load_selected_metadata()
                except Exception:
                    pass
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to write PDF: {e}")
            return False

    def open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            self.settings = load_settings()
            # update fields to reflect possible new defaults
            for k, widget in self.meta_fields.items():
                widget.setText(self.settings.get("defaults", {}).get(k, ""))

    def save_current_as_defaults(self):
        # Take current meta field values and save into settings as defaults
        for k, widget in self.meta_fields.items():
            if k == "Where From":
                continue
            self.settings.setdefault("defaults", {})[k] = widget.text()
        save_settings(self.settings)
        QMessageBox.information(self, "Saved", "Current values saved as defaults")

    def add_custom_field(self):
        # Prompt user for a new metadata key name
        key, ok = QtWidgets.QInputDialog.getText(self, "Add Custom Field", "Field name:")
        if not ok or not key:
            return
        key = key.strip()
        if key in self.meta_fields:
            QMessageBox.information(self, "Exists", f"Field '{key}' already exists")
            return
        # create new QLineEdit, add to form and wire it
        le = QLineEdit()
        le.setMinimumWidth(380)
        self.meta_fields[key] = le
        # insert before the Raw Metadata row (which is last)
        # find row index of Raw Metadata and insert above it
        # PyQt's QFormLayout doesn't provide a direct insertRow index method; append and re-order is acceptable here
        self.form.insertRow(self.form.rowCount() - 1, QLabel(key), le)
        le.textChanged.connect(self._update_raw_meta)
        # ensure adjacent buttons (if any future) get styled as buttons not labels
        # there are no immediate adjacent buttons here, but set a property to keep styling consistent
        le.setProperty('customField', 'true')
        # save this new custom field into defaults so it persists in settings
        self.settings.setdefault('defaults', {})[key] = ""
        save_settings(self.settings)

    def _update_raw_meta(self):
        # Build a metadata dict from current editable fields and display it
        try:
            current = {}
            for k, widget in self.meta_fields.items():
                if k == "Where From":
                    continue
                val = widget.text()
                if val:
                    current[k] = val

            # Present both the original loaded metadata and the current edited values
            combined = {
                "original": self._original_meta if isinstance(self._original_meta, dict) else {},
                "current": current,
            }
            self.raw_meta.setPlainText(json.dumps(combined, indent=2, ensure_ascii=False))
        except Exception:
            # fallback: do nothing
            pass

    def _get_where_from(self, path: str) -> str:
        # Try to read macOS Finder "Where From" metadata using mdls
        try:
            out = subprocess.check_output(["mdls", "-name", "kMDItemWhereFroms", "-raw", path], text=True)
            # mdls prints '(null)' when missing
            if not out or out.strip() == "(null)":
                return ""
            # output is often a plist-like array: ("https://example.com/...",)
            # Strip surrounding parentheses and quotes
            cleaned = out.strip()
            # remove starting ( and ending ) if present
            if cleaned.startswith("(") and cleaned.endswith(")"):
                cleaned = cleaned[1:-1].strip()
            # remove surrounding quotes
            cleaned = cleaned.strip().strip('"')
            return cleaned
        except Exception:
            return ""


def main():
    app = QApplication(sys.argv)
    # Set application name (appears in menu/dock on some platforms)
    try:
        QtCore.QCoreApplication.setApplicationName("PDF Metadata Modifier")
        QtCore.QCoreApplication.setOrganizationName("PDFMetadata")
    except Exception:
        pass
    # set app-level icon so macOS dock/window shows it (use SVG if available)
    try:
        png_path = APP_DIR / "assets" / "icon.png"
        svg_path = APP_DIR / "assets" / "icon.svg"
        if png_path.exists():
            app.setWindowIcon(QtGui.QIcon(str(png_path)))
        elif svg_path.exists():
            app.setWindowIcon(QtGui.QIcon(str(svg_path)))
    except Exception:
        pass

    # Note: setting the macOS Dock icon reliably requires an application bundle
    # with the icon embedded (e.g. an `.icns` resource). For development the
    # `QApplication.setWindowIcon()` call above is used; to get a proper Dock
    # icon create an app bundle (see README pyinstaller instructions).

    w = MainWindow()
    w.resize(900, 700)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
