# Portable Windows desktop launcher

This setup works from **any cloned repository location** and **any Conda
installation directory**. It does not hard-code a drive, username, repository
path or environment name.

## One-time installation

Install ELP Studio and its Python dependencies first, as documented in
[README.md](README.md). Then on Windows:

1. Run **windows/install_elp_studio.cmd** by double-clicking it.
2. If you have more than one Conda environment, the installer will search
   environments for working ELP Studio + Streamlit imports. For precise
   selection, activate the desired environment in Anaconda Prompt before
   running the installer.
3. The installer places an **ELP Studio** shortcut on your Windows Desktop.
4. Double-click the Desktop shortcut whenever you want to open the app.

### Explicit interpreter selection

If environment discovery does not select the desired Python interpreter:

~~~bat
cd /d "PATH\TO\YOUR\CALVADOS-TEA-IDP-simulator"
windows\install_elp_studio.cmd -PythonPath "FULL\PATH\TO\YOUR\CONDA\ENV\python.exe"
~~~

Examples may use a project under C:, D: or an external SSD; no path is baked
into the committed launcher.

The installer validates that the selected interpreter can import both
`streamlit` and `calvados_library_builder`. It will ask for a full Python
path if nothing valid is found.

## How the shortcut works

- Windows shortcut → `wscript.exe` → hidden PowerShell launcher.
- The launcher resolves its own installed repository directory.
- It reads the machine-specific interpreter from
  `.elp_studio_launcher.json` (not committed to Git).
- It starts `python -m streamlit run app.py` from the repository root,
  binding only to `127.0.0.1`, not the local network.
- It uses port 8501 by preference, falling back to another unused port up
  to 8550.
- It waits for Streamlit's health endpoint before opening the default
  browser.
- Subsequent double-clicks reuse a tracked, still-running server.

Local runtime files under `.elp_studio_runtime/` contain the server PID,
port and logs. They are not committed to Git and are useful when debugging.

## Stop ELP Studio

Use `windows\stop_elp_studio.cmd` to stop a server started by the launcher.

Closing the browser tab **does not stop the local server**. You can reopen
ELP Studio from the desktop icon without reinitializing Streamlit.

## Troubleshooting

If the shortcut fails, open these files from the repository:

- `.elp_studio_runtime/launcher.log` — launch errors.
- `.elp_studio_runtime/streamlit_stderr.log` — Streamlit/Python exceptions.
- `.elp_studio_runtime/streamlit_stdout.log` — Streamlit output.

If the interpreter or repository is moved, run the installer again.

If Windows blocks scripts, run the installer from Anaconda Prompt using the
bundled `.cmd` file. The launcher invokes PowerShell with a process-local
execution-policy bypass; it does not permanently change Windows settings.

## Desktop icon

The installer generates `assets/elp_studio.ico` using built-in Windows
graphics APIs, without requiring an image tool or online download. The
generated icon is intentionally not committed to Git.

To customize it, replace `assets/elp_studio.ico` with another valid Windows
ICO and rerun the installer. The installer **does not overwrite** an icon
you've already placed there.

Windows often caches shortcut images; refreshing the desktop, or logging
out and back in, may be needed to see an icon replacement.

## Updating ELP Studio

Pull the latest code from Git in your cloned repository:

~~~bat
git pull origin main
~~~

No shortcut recreation is needed for normal code updates. Rerun setup only
if you move the folder or use a different Python environment.

> Platform limitation: this shortcut setup is for **Windows**. Mac and Linux
> can still launch Streamlit directly with `python -m streamlit run app.py`.
