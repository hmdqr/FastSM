#!/usr/bin/env python
"""Build script for FastSM using Nuitka - supports Windows and macOS."""

import os
import subprocess
import sys
import shutil
import tempfile
import plistlib
from pathlib import Path

from version import APP_NAME, APP_VERSION, APP_DESCRIPTION, APP_COPYRIGHT, APP_VENDOR


def get_platform():
    """Get the current platform."""
    if sys.platform == "darwin":
        return "macos"
    elif sys.platform == "win32":
        return "windows"
    else:
        return "linux"


def build_windows(script_dir: Path, output_dir: Path, temp_base: Path) -> tuple:
    """Build for Windows using Nuitka.

    Returns:
        Tuple of (success: bool, artifact_path: Path or None)
    """
    # Clean previous dist folder only
    dist_dir = output_dir / "main.dist"
    if dist_dir.exists():
        print("Cleaning previous build...")
        shutil.rmtree(dist_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Get number of CPU cores for parallel compilation
    num_jobs = os.cpu_count() or 4

    # Nuitka command for Windows
    cmd = [
        sys.executable,
        "-m", "nuitka",

        # Output settings
        f"--output-dir={output_dir}",
        f"--output-filename={APP_NAME}.exe",

        # Standalone mode
        "--standalone",

        # Windows GUI application (no console window)
        "--windows-disable-console",

        # Application info
        f"--product-name={APP_NAME}",
        f"--product-version={APP_VERSION}",
        f"--file-description={APP_NAME} - {APP_DESCRIPTION}",
        f"--copyright={APP_COPYRIGHT}",

        # Include required packages
        "--include-package=wx",
        "--include-package=sound_lib",
        "--include-package=accessible_output2",
        "--include-package=models",
        "--include-package=platforms",
        "--include-package=GUI",
        "--include-module=config",
        "--include-package=keyboard_handler",
        "--include-package=mastodon",
        "--include-package=atproto",

        # Include data files
        "--include-package-data=sound_lib",
        "--include-package-data=accessible_output2",

        # Enable plugins
        "--enable-plugin=anti-bloat",

        # Follow imports
        "--follow-imports",

        # Speed optimizations
        f"--jobs={num_jobs}",  # Parallel compilation
        "--lto=no",  # Disable Link Time Optimization for faster builds
        "--assume-yes-for-downloads",  # Don't prompt for downloads

        # Show progress
        "--show-progress",
        "--show-memory",

        # Main script
        str(script_dir / "FastSM.pyw"),
    ]

    # Set environment
    env = os.environ.copy()
    env["NUITKA_CACHE_DIR"] = str(temp_base / "cache")

    print(f"Building {APP_NAME} v{APP_VERSION} for Windows...")
    print(f"Build cache: {temp_base}")
    print(f"Output: {output_dir}")
    print()

    result = subprocess.run(cmd, cwd=script_dir, env=env)

    if result.returncode == 0:
        # Copy docs folder
        docs_src = script_dir / "docs"
        if docs_src.exists():
            docs_dst = dist_dir / "docs"
            print("Copying docs folder...")
            shutil.copytree(docs_src, docs_dst, dirs_exist_ok=True)

        # Copy accessible_output2 lib folder
        try:
            import accessible_output2
            ao2_path = Path(accessible_output2.__file__).parent
            ao2_lib_path = ao2_path / "lib"
            if ao2_lib_path.exists():
                ao2_dst = dist_dir / "accessible_output2" / "lib"
                print("Copying accessible_output2/lib folder...")
                shutil.copytree(ao2_lib_path, ao2_dst, dirs_exist_ok=True)
        except ImportError:
            print("Warning: accessible_output2 not found, skipping lib copy")

        # Create zip file for distribution
        zip_path = create_windows_zip(output_dir, dist_dir)

        return True, zip_path
    return False, None


def create_windows_zip(output_dir: Path, dist_dir: Path) -> Path:
    """Create a zip file of the Windows build for distribution.

    Returns:
        Path to the created zip file
    """
    import zipfile

    zip_name = f"{APP_NAME}-{APP_VERSION}-Windows.zip"
    zip_path = output_dir / zip_name

    # Remove existing zip
    if zip_path.exists():
        print(f"Removing existing zip: {zip_path}")
        zip_path.unlink()

    print(f"Creating zip: {zip_name}...")

    # Create zip file
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through dist directory and add all files
        for file_path in dist_dir.rglob('*'):
            if file_path.is_file():
                # Create archive name relative to dist_dir, inside APP_NAME folder
                arc_name = Path(APP_NAME) / file_path.relative_to(dist_dir)
                zipf.write(file_path, arc_name)

    # Get file size
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Zip created successfully: {zip_path}")
    print(f"Zip size: {zip_size_mb:.1f} MB")

    return zip_path


def build_macos(script_dir: Path, output_dir: Path, temp_base: Path) -> tuple:
    """Build for macOS using Nuitka, creating an app bundle.

    Returns:
        Tuple of (success: bool, artifact_path: Path or None)
    """
    # App bundle path
    app_name = f"{APP_NAME}.app"
    app_path = output_dir / app_name

    # Clean previous build
    if app_path.exists():
        print("Cleaning previous build...")
        shutil.rmtree(app_path)

    # Also clean dist folder
    dist_dir = output_dir / "main.dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Bundle identifier
    bundle_id = f"me.masonasons.{APP_NAME.lower()}"

    # Get number of CPU cores for parallel compilation
    num_jobs = os.cpu_count() or 4

    # Nuitka command for macOS
    cmd = [
        sys.executable,
        "-m", "nuitka",

        # Output settings
        f"--output-dir={output_dir}",
        f"--output-filename={APP_NAME}",

        # Standalone mode
        "--standalone",

        # macOS app bundle
        "--macos-create-app-bundle",
        f"--macos-app-name={APP_NAME}",
        f"--macos-app-version={APP_VERSION}",

        # Application info
        f"--product-name={APP_NAME}",
        f"--product-version={APP_VERSION}",
        f"--file-description={APP_NAME} - {APP_DESCRIPTION}",
        f"--copyright={APP_COPYRIGHT}",

        # Include required packages
        "--include-package=wx",
        "--include-package=models",
        "--include-package=platforms",
        "--include-package=GUI",
        "--include-module=config",
        "--include-package=keyboard_handler",
        "--include-package=mastodon",
        "--include-package=atproto",

        # Enable plugins
        "--enable-plugin=anti-bloat",

        # Follow imports
        "--follow-imports",

        # Speed optimizations
        f"--jobs={num_jobs}",  # Parallel compilation
        "--lto=no",  # Disable Link Time Optimization for faster builds
        "--assume-yes-for-downloads",  # Don't prompt for downloads

        # Show progress
        "--show-progress",
        "--show-memory",

        # Main script
        str(script_dir / "FastSM.pyw"),
    ]

    # Set environment
    env = os.environ.copy()
    env["NUITKA_CACHE_DIR"] = str(temp_base / "cache")

    print(f"Building {APP_NAME} v{APP_VERSION} for macOS...")
    print(f"Build cache: {temp_base}")
    print(f"Output: {output_dir}")
    print()

    result = subprocess.run(cmd, cwd=script_dir, env=env)

    if result.returncode != 0:
        return False, None

    # Find the created app bundle (Nuitka creates it with the name main.app)
    nuitka_app = output_dir / "main.app"
    if nuitka_app.exists():
        # Rename to our app name
        if app_path.exists():
            shutil.rmtree(app_path)
        nuitka_app.rename(app_path)

    if not app_path.exists():
        print("Error: App bundle was not created")
        return False, None

    # Update Info.plist with proper values
    plist_path = app_path / "Contents" / "Info.plist"
    if plist_path.exists():
        print("Updating Info.plist...")
        with open(plist_path, 'rb') as f:
            plist = plistlib.load(f)

        plist.update({
            'CFBundleName': APP_NAME,
            'CFBundleDisplayName': APP_NAME,
            'CFBundleIdentifier': bundle_id,
            'CFBundleVersion': APP_VERSION,
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundleExecutable': APP_NAME,
            'NSHumanReadableCopyright': APP_COPYRIGHT,
            'CFBundlePackageType': 'APPL',
            'LSMinimumSystemVersion': '10.13',
            'NSHighResolutionCapable': True,
            # Accessibility permission for speech
            'NSAppleEventsUsageDescription': f'{APP_NAME} needs accessibility access for screen reader support.',
        })

        with open(plist_path, 'wb') as f:
            plistlib.dump(plist, f)

    # Copy docs folder to Resources
    docs_src = script_dir / "docs"
    resources_dir = app_path / "Contents" / "Resources"
    if docs_src.exists():
        docs_dst = resources_dir / "docs"
        print("Copying docs folder...")
        shutil.copytree(docs_src, docs_dst, dirs_exist_ok=True)

    # Code sign the app
    sign_macos_app(app_path)

    # Create DMG
    dmg_path = create_macos_dmg(output_dir, app_path, script_dir)

    return True, dmg_path


def get_signing_identity():
    """Find a code signing identity."""
    try:
        result = subprocess.run(
            ["security", "find-identity", "-v", "-p", "codesigning"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            output = result.stdout
            # Look for Developer ID Application certificate first
            for line in output.split('\n'):
                if 'Developer ID Application' in line:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        return parts[1]

            # If no Developer ID, try Apple Development
            for line in output.split('\n'):
                if 'Apple Development' in line or 'Mac Developer' in line:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        return parts[1]

            # Last resort: ad-hoc signing
            print("No code signing certificate found. Using ad-hoc signing...")
            return "-"

    except FileNotFoundError:
        print("Warning: 'security' command not found. Skipping code signing.")
        return None

    return "-"


def clear_xattrs(path: Path):
    """Clear extended attributes and quarantine flags from a file/directory."""
    subprocess.run(["xattr", "-cr", str(path)], capture_output=True, text=True)


def sign_macos_app(app_path: Path):
    """Sign the macOS app bundle for distribution."""
    signing_identity = get_signing_identity()
    if not signing_identity:
        return

    is_adhoc = signing_identity == "-"
    print(f"Signing app with identity: {signing_identity}")

    # Clear extended attributes first
    print("Clearing extended attributes...")
    clear_xattrs(app_path)

    # Collect all signable binaries
    binaries = []
    for ext in ['*.so', '*.dylib']:
        binaries.extend(app_path.rglob(ext))

    # Add main executable
    main_exec = app_path / "Contents" / "MacOS" / APP_NAME
    if main_exec.exists():
        binaries.append(main_exec)

    # Sort by depth (deepest first for inside-out signing)
    binaries.sort(key=lambda p: len(p.parts), reverse=True)

    print(f"Processing {len(binaries)} binaries...")

    # Remove ALL signatures first
    for binary in binaries:
        subprocess.run(
            ["codesign", "--remove-signature", str(binary)],
            capture_output=True, text=True
        )

    # Sign each binary individually
    failed = 0
    for binary in binaries:
        if is_adhoc:
            cmd = ["codesign", "--force", "--sign", "-", str(binary)]
        else:
            cmd = ["codesign", "--force", "--sign", signing_identity, str(binary)]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            failed += 1

    if failed > 0:
        print(f"  {failed} binaries failed to sign individually")

    # Finally sign the app bundle
    print("Signing app bundle...")
    if is_adhoc:
        sign_cmd = ["codesign", "--force", "--sign", "-", str(app_path)]
    else:
        sign_cmd = ["codesign", "--force", "--sign", signing_identity, str(app_path)]

    result = subprocess.run(sign_cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("Code signing successful!")
    else:
        print(f"Code signing failed: {result.stderr}")
        print("To run the app, right-click and select 'Open' to bypass Gatekeeper.")


def create_macos_dmg(output_dir: Path, app_path: Path, script_dir: Path) -> Path:
    """Create a DMG disk image for macOS distribution.

    Returns:
        Path to the created DMG file, or None if creation failed
    """
    dmg_name = f"{APP_NAME}-{APP_VERSION}.dmg"
    dmg_path = output_dir / dmg_name

    # Remove existing DMG
    if dmg_path.exists():
        print(f"Removing existing DMG: {dmg_path}")
        dmg_path.unlink()

    print(f"Creating DMG: {dmg_name}...")

    # Create a temporary directory for DMG contents
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Copy the app to temp directory
        temp_app = temp_path / app_path.name
        print("Copying app to staging area...")
        shutil.copytree(app_path, temp_app, symlinks=True)

        # Copy docs folder to DMG root
        docs_src = script_dir / "docs"
        if docs_src.exists():
            docs_dst = temp_path / "Documentation"
            print("Copying documentation to DMG...")
            shutil.copytree(docs_src, docs_dst, dirs_exist_ok=True)

        # Create a symbolic link to /Applications for drag-and-drop install
        applications_link = temp_path / "Applications"
        try:
            applications_link.symlink_to("/Applications")
        except OSError as e:
            print(f"Warning: Could not create Applications symlink: {e}")

        # Calculate volume size (app size + 50MB buffer)
        app_size_mb = sum(f.stat().st_size for f in app_path.rglob('*') if f.is_file()) // (1024 * 1024)
        volume_size_mb = app_size_mb + 50

        # Create DMG using hdiutil
        create_cmd = [
            "hdiutil", "create",
            "-volname", APP_NAME,
            "-srcfolder", str(temp_path),
            "-ov",  # Overwrite
            "-format", "UDZO",  # Compressed
            "-imagekey", "zlib-level=9",  # Maximum compression
            str(dmg_path)
        ]

        result = subprocess.run(create_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"DMG created successfully: {dmg_path}")

            # Get file size
            dmg_size_mb = dmg_path.stat().st_size / (1024 * 1024)
            print(f"DMG size: {dmg_size_mb:.1f} MB")
        else:
            print(f"DMG creation failed: {result.stderr}")
            return None

    # Sign the DMG if we have a signing identity
    sign_macos_dmg(dmg_path)

    return dmg_path


def sign_macos_dmg(dmg_path: Path):
    """Sign the DMG if a signing identity is available."""
    signing_identity = get_signing_identity()
    if not signing_identity or signing_identity == "-":
        print("No Developer ID certificate found. DMG will not be signed.")
        return

    print(f"Signing DMG with identity: {signing_identity}")
    sign_cmd = [
        "codesign",
        "--force",
        "--sign", signing_identity,
        "--timestamp",
        str(dmg_path)
    ]
    sign_result = subprocess.run(sign_cmd, capture_output=True, text=True)
    if sign_result.returncode == 0:
        print("DMG signing successful!")
    else:
        print(f"DMG signing failed: {sign_result.stderr}")


def main():
    """Build FastSM executable using Nuitka."""
    # Get the directory containing this script
    script_dir = Path(__file__).parent.resolve()

    # Detect platform
    platform = get_platform()
    print(f"Detected platform: {platform}")

    # Output directory for final build - in user's home directory
    output_dir = Path.home() / "app_dist" / APP_NAME

    # Use system temp directory for build cache
    temp_base = Path(tempfile.gettempdir()) / "fastsm_build"
    temp_base.mkdir(parents=True, exist_ok=True)

    print(f"Building {APP_NAME} v{APP_VERSION} with Nuitka...")
    print(f"Build cache: {temp_base}")
    print(f"Output: {output_dir}")
    print()

    # Build for current platform
    if platform == "windows":
        success, artifact_path = build_windows(script_dir, output_dir, temp_base)
    elif platform == "macos":
        success, artifact_path = build_macos(script_dir, output_dir, temp_base)
    else:
        print(f"Unsupported platform: {platform}")
        sys.exit(1)

    if success:
        print()
        print("=" * 50)
        print("Build completed successfully!")
        print(f"Output: {output_dir}")

        # Copy artifact to source folder
        if artifact_path and artifact_path.exists():
            dest_path = script_dir / artifact_path.name
            print(f"Copying to source folder: {dest_path}")
            shutil.copy2(artifact_path, dest_path)
            print(f"Artifact copied: {dest_path}")

            if platform == "macos":
                print(f"DMG: {dest_path}")
            elif platform == "windows":
                print(f"Zip: {dest_path}")

        print("=" * 50)
    else:
        print()
        print("=" * 50)
        print("Build failed!")
        print("=" * 50)
        sys.exit(1)


if __name__ == "__main__":
    main()
