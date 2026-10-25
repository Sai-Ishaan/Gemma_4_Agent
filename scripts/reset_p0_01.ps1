
$ErrorActionPreference = "Stop"
###What it does:
# Path Mapping: It dynamically locates the main repository (mock_python_repo), the task manifest (fixtures\tasks.json), and the isolated sibling worktree (p0-01-evaluation).
##Authoritative Read: It reads tasks.json, parses the JSON data, and extracts the base_revision specifically assigned to task P0-01.
###Integrity Validation: It enforces a strict rule that the target commit hash must be a valid, full 40-character Git commit hash and verifies via git cat-file that the commit actually exists in your Git database before attempting any operations.
# Main repository: mock_python_repo
$MainRepoRoot = Split-Path -Parent $PSScriptRoot
$ManifestPath = Join-Path $MainRepoRoot "fixtures\tasks.json"

# Evaluation worktree is a sibling of mock_python_repo.
$WorktreePath = Join-Path (Split-Path -Parent $MainRepoRoot) "p0-01-evaluation"

function Invoke-Git {
    param(
        [string]$WorkingDirectory,
        [string[]]$GitArguments
    )

    $output = & git -C $WorkingDirectory @GitArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Git command failed: git -C `"$WorkingDirectory`" $($GitArguments -join ' ')"
    }

    return $output
}

# Read the authoritative P0-01 revision from the manifest.
if (-not (Test-Path $ManifestPath)) {
    throw "Task manifest not found: $ManifestPath"
}

$manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
$task = @($manifest.tasks | Where-Object { $_.task_id -eq "P0-01" })

if ($task.Count -ne 1) {
    throw "Expected exactly one P0-01 entry in tasks.json."
}

$TargetCommit = [string]$task[0].base_revision

if ($TargetCommit -notmatch '^[0-9a-fA-F]{40}$') {
    throw "P0-01 base_revision must be a full 40-character Git commit hash."
}

# Confirm the recorded revision exists in the main repository.
Invoke-Git $MainRepoRoot @("cat-file", "-e", "$TargetCommit^{commit}") |
    Out-Null

# Do not create or overwrite a worktree automatically in this first version.
if (-not (Test-Path $WorktreePath -PathType Container)) {
    throw "Evaluation worktree not found: $WorktreePath. Create it with git worktree add first."
}

$ActualRoot = (Invoke-Git $WorktreePath @("rev-parse", "--show-toplevel") |
    Select-Object -First 1).Trim()

$ActualRoot = [System.IO.Path]::GetFullPath(
    $ActualRoot.Replace('/', '\')
).TrimEnd('\')

$ExpectedRoot = [System.IO.Path]::GetFullPath(
    $WorktreePath
).TrimEnd('\')

if (-not $ActualRoot.Equals(
    $ExpectedRoot,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "The target directory is not the expected evaluation worktree. No reset performed."
}
# Safety check: refuse to destroy tracked, staged, or untracked changes.
$status = Invoke-Git $WorktreePath @(
    "status", "--porcelain", "--untracked-files=all"
)

if ($status.Count -gt 0 -and ($status -join "").Trim().Length -gt 0) {
    Write-Host "RESET REFUSED: evaluation worktree has changes:" -ForegroundColor Yellow
    $status | ForEach-Object { Write-Host $_ }
    throw "Commit, back up, or deliberately remove those changes before retrying."
}

# Safe to reset only after confirming the worktree is clean.
Write-Host "Resetting P0-01 evaluation worktree to $TargetCommit"
Invoke-Git $WorktreePath @("reset", "--hard", $TargetCommit) |
    ForEach-Object { Write-Host $_ }

$FinalCommit = (Invoke-Git $WorktreePath @("rev-parse", "HEAD") |
    Select-Object -First 1).Trim()

if ($FinalCommit -ne $TargetCommit) {
    throw "Verification failed: HEAD does not match the P0-01 target revision."
}

$finalStatus = Invoke-Git $WorktreePath @(
    "status", "--porcelain", "--untracked-files=all"
)

if ($finalStatus.Count -gt 0 -and ($finalStatus -join "").Trim().Length -gt 0) {
    throw "Verification failed: evaluation worktree is not clean after reset."
}

Write-Host ""
Write-Host "P0-01 reset: PASS" -ForegroundColor Green
Write-Host "Revision: $FinalCommit"
Write-Host "Worktree: $WorktreePath"
Write-Host "Working tree: clean"