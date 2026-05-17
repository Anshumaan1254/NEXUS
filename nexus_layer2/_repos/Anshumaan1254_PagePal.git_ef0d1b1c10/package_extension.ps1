# package_extension.ps1
# Packages the Chrome extension into a tar.gz archive.
# Run this script from the root of the extension directory.

$extensionPath = (Resolve-Path .).Path
$archivePath = Join-Path $extensionPath "cognitive-flow.tar.gz"

# Create tar.gz using built‑in tar (Windows 10+)
# -c: create, -z: gzip, -f: file name, -C: change to directory

tar -czf $archivePath -C $extensionPath .

Write-Host "Extension packaged to $archivePath"
