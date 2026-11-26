[CmdletBinding()]
param(
    [ValidateSet('Install', 'Uninstall')][string]$Mode = 'Install',
    [string]$GameDirectory,
    [switch]$NonInteractive
)
$ErrorActionPreference = 'Stop'
$stagePath = $null
$utf8 = New-Object Text.UTF8Encoding($false)

function Get-HashHex([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-', '').ToLowerInvariant() }
    finally { $algorithm.Dispose(); $stream.Dispose() }
}
function Get-Archive([string]$Directory) {
    foreach ($relative in @('resources\app.asar', 'app.asar')) {
        $candidate = Join-Path $Directory $relative
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    return $null
}
function Test-GameDirectory([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    if (Get-Archive $Path) { return $true }
    return (Test-Path -LiteralPath (Join-Path $Path 'rf.swf') -PathType Leaf)
}
function Find-GameDirectory {
    $found = @(@($PSScriptRoot, (Split-Path $PSScriptRoot -Parent), (Get-Location).Path) |
        Where-Object { Test-GameDirectory $_ } | ForEach-Object { [IO.Path]::GetFullPath($_).TrimEnd('\') } | Select-Object -Unique)
    if ($found.Count -eq 1) { return $found[0] }
    if ($NonInteractive) { throw 'Select a folder containing rf.swf, app.asar or resources\app.asar with -GameDirectory.' }
    Add-Type -AssemblyName System.Windows.Forms
    $picker = New-Object System.Windows.Forms.FolderBrowserDialog
    $picker.Description = 'Select the folder containing rf.swf, app.asar or resources\app.asar'
    $picker.ShowNewFolderButton = $false
    try {
        if ($picker.ShowDialog() -ne [Windows.Forms.DialogResult]::OK) { throw 'Cancelled. No game files were changed.' }
        return $picker.SelectedPath
    } finally { $picker.Dispose() }
}
function Replace-Atomically([string]$Source, [string]$Target) {
    [IO.File]::Replace($Source, $Target, [System.Management.Automation.Language.NullString]::Value, $true)
}
function Strip-Loader([string]$Text) {
    return [regex]::Replace($Text, '(?s)\r?\n?/\* GOLDMINER_COOP_LOADER_BEGIN \*/.*?/\* GOLDMINER_COOP_LOADER_END \*/\r?\n?', '')
}
function Save-State([string]$Path, $State) {
    [IO.File]::WriteAllText($Path, ($State | ConvertTo-Json -Depth 20), $utf8)
}

try {
    $manifest = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'manifest.json')) | ConvertFrom-Json
    if ($manifest.format -ne 'goldminer-flash-overlay-v2') { throw 'Unsupported mod package format.' }
    $allowedNames = @('rf.swf', 'l10n-cjk/rf.swf', 'l10n-latin/rf.swf', 'l10n-pad/rf.swf')
    foreach ($flash in $manifest.flash) {
        if ($flash.name -notin $allowedNames -or $flash.path -ne ('flash/' + $flash.name)) { throw 'Invalid Flash resource path.' }
    }
    if (!$GameDirectory) { $GameDirectory = Find-GameDirectory }
    $GameDirectory = [IO.Path]::GetFullPath($GameDirectory.Trim('"'))
    if (!(Test-GameDirectory $GameDirectory)) { throw 'Select a folder containing rf.swf, app.asar or resources\app.asar.' }
    if (Get-Process -Name GoldMiner -ErrorAction SilentlyContinue) { throw 'Close Gold Miner before installing or uninstalling.' }
    Write-Host ('Game folder: ' + $GameDirectory)
    if ($Mode -eq 'Install') {
        foreach ($file in $manifest.files) {
            $path = Join-Path $PSScriptRoot $file.path
            if ((Get-HashHex $path) -ne $file.sha256) { throw ('Damaged mod file: ' + $file.path) }
        }
    }
    $archivePath = Get-Archive $GameDirectory
    if ($archivePath) {
        if (-not ('GoldMinerArchive' -as [type])) {
            Add-Type -Path (Join-Path $PSScriptRoot 'ArchiveTools.cs') -ReferencedAssemblies System.Web.Extensions
        }
        $resourceDirectory = Split-Path $archivePath -Parent
        $assetDirectory = Join-Path $resourceDirectory 'goldminer-solo-coop'
        $statePath = Join-Path $assetDirectory 'install-state.json'
        $mainBytes = [GoldMinerArchive]::ReadFile($archivePath, 'electron-main.js')
        $packBytes = [GoldMinerArchive]::ReadFile($archivePath, 'main/swf-pack.js')
        $main = $utf8.GetString($mainBytes)
        $pack = $utf8.GetString($packBytes)
        $cleanMain = [GoldMinerArchive]::RemoveHashes($main)
        $cleanPack = Strip-Loader $pack
        if ($Mode -eq 'Uninstall') {
            if ($cleanMain -eq $main -and $cleanPack -eq $pack) {
                Write-Host 'No overlay hooks are installed.' -ForegroundColor Green
                exit 0
            }
            $nextMain = $cleanMain
            $nextPack = $cleanPack
        } else {
            $hashes = [ordered]@{}
            foreach ($flash in $manifest.flash) { $hashes[$flash.name] = $flash.sha256 }
            $nextMain = [GoldMinerArchive]::SetHashes($main, ($hashes | ConvertTo-Json -Compress))
            $loader = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'flash-loader.cjs'))
            $nextPack = $cleanPack + "`n" + $loader.Trim() + "`n"
        }
        $replacements = New-Object 'Collections.Generic.Dictionary[string,byte[]]'
        $replacements.Add('electron-main.js', $utf8.GetBytes($nextMain))
        $replacements.Add('main/swf-pack.js', $utf8.GetBytes($nextPack))
        $stagePath = Join-Path $resourceDirectory ('app.asar.coop-' + [Guid]::NewGuid().ToString('N') + '.tmp')
        [GoldMinerArchive]::Patch($archivePath, $stagePath, $replacements)
        # Validate the named replacement entries, without requiring a known whole-archive hash.
        foreach ($name in $replacements.Keys) {
            if ([Convert]::ToBase64String([GoldMinerArchive]::ReadFile($stagePath, $name)) -ne
                [Convert]::ToBase64String($replacements[$name])) { throw 'Named archive entry validation failed.' }
        }
        if ($Mode -eq 'Install') {
            [IO.Directory]::CreateDirectory($assetDirectory) | Out-Null
            if (!(Test-Path -LiteralPath $statePath)) {
                $backup = $archivePath + '.goldminer-coop-' + [Guid]::NewGuid().ToString('N') + '.bak'
                [IO.File]::Copy($archivePath, $backup)
                if ((Get-HashHex $archivePath) -ne (Get-HashHex $backup)) { throw 'Snapshot backup verification failed.' }
                Save-State $statePath @{ format='goldminer-overlay-state-v2'; backup=$backup }
            }
            foreach ($flash in $manifest.flash) {
                $target = Join-Path $assetDirectory $flash.name
                [IO.Directory]::CreateDirectory((Split-Path $target -Parent)) | Out-Null
                $assetStage = $target + '.installing'
                try {
                    [IO.File]::Copy((Join-Path $PSScriptRoot $flash.path), $assetStage, $true)
                    if ((Get-HashHex $assetStage) -ne $flash.sha256) { throw 'Written Flash resource verification failed.' }
                    if (Test-Path -LiteralPath $target) { Replace-Atomically $assetStage $target }
                    else { [IO.File]::Move($assetStage, $target) }
                } finally { if (Test-Path -LiteralPath $assetStage) { [IO.File]::Delete($assetStage) } }
            }
        }
        Replace-Atomically $stagePath $archivePath
        $stagePath = $null
        if ($Mode -eq 'Install') { Write-Host 'Flash overlay installed. Select Single Player to play co-op.' -ForegroundColor Green }
        else { Write-Host 'Overlay hooks removed. Other current archive entries and backups were preserved.' -ForegroundColor Green }
    } else {
        # Standalone Flash installation: replace existing rf.swf variants only.
        $statePath = Join-Path $GameDirectory '.goldminer-solo-coop-state.json'
        $state = $null
        if (Test-Path -LiteralPath $statePath) { $state = [IO.File]::ReadAllText($statePath) | ConvertFrom-Json }
        if ($Mode -eq 'Uninstall') {
            if (!$state) { Write-Host 'No loose Flash backup was recorded.' -ForegroundColor Green; exit 0 }
            foreach ($item in $state.backups) {
                if (!(Test-Path -LiteralPath $item.backup)) { throw 'A loose Flash backup is missing. No automatic replacement can be made.' }
            }
            foreach ($item in $state.backups) {
                $target = Join-Path $GameDirectory $item.name
                $stagePath = $target + '.coop-' + [Guid]::NewGuid().ToString('N') + '.tmp'
                [IO.File]::Copy($item.backup, $stagePath)
                Replace-Atomically $stagePath $target
                $stagePath = $null
            }
            Write-Host 'Pre-install Flash files restored. Backups retained.' -ForegroundColor Green
        } else {
            $backups = @()
            if ($state) { $backups = @($state.backups) }
            $backupDirectory = Join-Path $GameDirectory '.goldminer-coop-backups'
            foreach ($flash in $manifest.flash) {
                $target = Join-Path $GameDirectory $flash.name
                if (!(Test-Path -LiteralPath $target)) { continue }
                if (!(@($backups | Where-Object { $_.name -eq $flash.name }).Count)) {
                    [IO.Directory]::CreateDirectory($backupDirectory) | Out-Null
                    $backup = Join-Path $backupDirectory ([Guid]::NewGuid().ToString('N') + '.swf')
                    [IO.File]::Copy($target, $backup)
                    $backups += @{ name=$flash.name; backup=$backup }
                    Save-State $statePath @{ format='goldminer-loose-state-v2'; backups=$backups }
                }
                $stagePath = $target + '.coop-' + [Guid]::NewGuid().ToString('N') + '.tmp'
                [IO.File]::Copy((Join-Path $PSScriptRoot $flash.path), $stagePath)
                if ((Get-HashHex $stagePath) -ne $flash.sha256) { throw 'Written Flash file verification failed.' }
                Replace-Atomically $stagePath $target
                $stagePath = $null
            }
            Write-Host 'Loose rf.swf files replaced with the co-op versions.' -ForegroundColor Green
        }
    }
    exit 0
} catch {
    Write-Host ('Operation failed: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
} finally {
    if ($stagePath -and (Test-Path -LiteralPath $stagePath)) { [IO.File]::Delete($stagePath) }
}
