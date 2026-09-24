**PDF Metadata Editor**

A simple, local GUI app to quickly view and update PDF metadata on your machine.

![App Screenshot](assets/screenshot.png)
<!-- If the image does not render in your Markdown preview, ensure the file `assets/screenshot.png` exists in the repo. The correct Markdown syntax is: `![App Screenshot](assets/screenshot.png)` -->

Quick start

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the app:

Use a virtualenv (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Find PyQt6's Qt "platforms" plugin directory (needed on macOS):

```bash
python -c "import PyQt6, os, glob; print(glob.glob(os.path.join(os.path.dirname(PyQt6.__file__),'**','platforms'), recursive=True))"
```

Start the app (replace the path below with the one printed above if needed):

```bash
export QT_QPA_PLATFORM_PLUGIN_PATH=/path/to/PyQt6/Qt6/plugins/platforms
python main.py
```

One-line start command (finds plugin path automatically and runs the GUI):

```bash
export QT_QPA_PLATFORM_PLUGIN_PATH=$(python -c "import PyQt6, os, glob; p=glob.glob(os.path.join(os.path.dirname(PyQt6.__file__),'**','platforms'), recursive=True); print(p[0] if p else '')") && python main.py
```

App name: PDF Metadata Modifier

Quick verify (syntax):

```bash
python -m py_compile main.py
```

What it does (simple):
- Lets you open or drag-and-drop PDF files into the app.
- Shows the PDF's metadata (Title, Author, Subject, Keywords, Producer) and a read-only "Where From" (Finder origin on macOS).
- You can edit any metadata fields and save them — the app writes a new PDF with the same filename into a dated folder.
- A Settings page stores default values and an output directory; you can apply defaults to files or save the current values as new defaults.
- "One-Click Process All" applies configured defaults to every loaded file and saves outputs into `OUTPUT_DIR/YYYY-MM-DD/` (or the source folder if no output dir is set).

New features
- Standard metadata: The editor now displays the common PDF fields by default: Title, Author, Subject, Keywords, Creator, Producer, CreationDate, ModDate, and Trapped.
- Raw Metadata: A read-only `Raw Metadata` panel shows all metadata keys/values (normalized) for each loaded PDF and updates live when you edit fields.
- Custom fields: Add arbitrary custom metadata keys at runtime using the "Add Custom Field" button — new fields are persisted to your `settings.json` defaults so they appear on next launch.
- Where From: The "Where From" field shows Finder's origin information on macOS (via `mdls`) and remains read-only because it's not standard PDF metadata.

User-friendly steps:
1. Install dependencies and start the app (see commands above).
2. Drag-and-drop PDFs or click "Add Files".
3. Select a file to view metadata. Edit fields directly.
4. Click "Save Metadata for Selected" to save that file, or "One-Click Process All" to process all listed files.
5. Find saved files in the configured output directory inside a folder named with today's date.

Adding custom metadata fields
- Click `Add Custom Field`, enter the new key name (e.g. `DocumentGroup`), and press OK.
- The new field will appear in the editor, update the `Raw Metadata` panel as you type, and will be saved to `settings.json` when you use "Save Current As Defaults".

Settings example
- A full example with the standard metadata keys is provided at [settings.example.json](settings.example.json).
	Copy it to `settings.json` (or use the app Settings dialog) to pre-populate defaults.

Notes/Troubleshooting
- If you see a Qt plugin error about "cocoa", re-run the "Find PyQt6 platforms" command and set `QT_QPA_PLATFORM_PLUGIN_PATH` before launching.
- The app uses macOS `mdls` to display "Where From" — that field is read-only and not written back to PDFs.
 - If the Dock or app icon shows a question mark on macOS: create a macOS application bundle with the icon embedded (recommended). Example using `pyinstaller`:

```bash
# install pyinstaller inside your venv
pip install pyinstaller
# build a one-file app and provide a 512x512 PNG or .icns icon
pyinstaller --noconfirm --onefile --windowed --icon=assets/icon.ico main.py
```

On macOS you may prefer to convert the icon to an `.icns` bundle and use that with `--icon` so the Dock shows the icon correctly.
 - Preserve file timestamps: the app now preserves original file modification and access times when saving metadata. Note: macOS creation date (birthtime) may not be preserved on all filesystems; packaging as an app does not change this behavior.

Packaging for macOS (recommended steps)
1. Generate icons (requires `cairosvg` and `pillow`):

```bash
pip install cairosvg pillow
python scripts/generate_icons.py
```

2. Build the app bundle using PyInstaller (inside your venv):

```bash
pip install pyinstaller
./scripts/build_macos.sh
```

Notes & limitations:
- The produced binary is a standalone executable but may require code-signing and notarization for distribution.
- macOS Dock icon will appear correctly if `assets/icon.icns` is present when building.
- Some macOS metadata (creation/birth time) cannot be reliably preserved across all filesystems; we preserve atime/mtime.

Build & Run (macOS)

After building with PyInstaller the app bundle and executable are placed in `dist/`.

- Open the app bundle (normal macOS launch):

```bash
open dist/main.app
```

- Run the bundled binary from Terminal to see stdout/stderr (useful for debugging):

```bash
# run the binary inside the .app bundle
dist/main.app/Contents/MacOS/main
# or run the standalone executable PyInstaller produced
./dist/main
```

- If PyInstaller warns about `--onefile` + macOS bundles, prefer `--onedir`:

```bash
pyinstaller --noconfirm --windowed --onedir --icon=assets/icon.icns main.py
```

- Notes:
	- The built app does not require setting `QT_QPA_PLATFORM_PLUGIN_PATH` at runtime — PyInstaller bundles Qt plugins.
	- Ensure `assets/icon.icns` existed at build time to get a correct Dock icon.
	- If `open` appears to do nothing, run the bundle binary from Terminal to capture logs.

Contributing
------------

This project follows a typical open-source workflow. Please use the following steps to propose changes via pull requests:

1. Fork the repository to your account.
2. Create a feature branch from `main`:

```bash
git checkout -b feature/your-feature-name
```

3. Make your changes, run tests (if any), and ensure the app still runs locally.
4. Commit with a clear message and push your branch to your fork.
5. Open a Pull Request against `aliawais0007/pdf-meta-editor:main` describing the change and any testing steps.

Pull Request Guidelines
-----------------------
- Keep changes focused and small. One feature or fix per PR.
- Include screenshots for UI changes.
- Add tests or manual verification steps where applicable.
- Rebase or merge the latest `main` before requesting review to avoid merge conflicts.

Maintainer Workflow (how updates are merged)
-------------------------------------------
- Reviewers will review the PR and request changes if needed.
- Once approved, the maintainer will merge the PR (merge commit, squash, or rebase depending on project preference).
- For breaking changes, documentation updates and a changelog entry are required.

Before publishing changes to `main`, I'll show you the updated `README.md` and the screenshot addition so you can confirm. Once you approve, I will commit the README update and push it as a PR-style change (we'll push to `main` or a feature branch per your preference).


