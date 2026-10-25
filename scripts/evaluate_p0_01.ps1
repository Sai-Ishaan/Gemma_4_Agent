
param(
    [Parameter(Mandatory = $true)]
    [string]$PatchPath
)

$ErrorActionPreference = "Stop"

$MainRepoRoot = Split-Path -Parent $PSScriptRoot
$WorktreePath = Join-Path (Split-Path -Parent $MainRepoRoot) "p0-01-evaluation"
$RunsPath = Join-Path $MainRepoRoot "runs"
$ManifestPath = Join-Path $MainRepoRoot "fixtures\tasks.json"
$ResetScript = Join-Path $PSScriptRoot "reset_p0_01.ps1"

$RunId = [guid]::NewGuid().ToString("N")
$Result = [ordered]@{
    schema_version = "1.0"
    run_id = $RunId
    task_id = "P0-01"
    starting_revision = $null
    patch_path = $null
    baseline = $null
    full_suite_baseline = $null
    patch_applies = $false
    patch_check_output = $null
    tests_after_patch = $null
    changed_paths = @()
    protected_paths_changed = @()
    scope_compliant = $false
    accepted = $false
    diagnostics = [ordered]@{
        baseline_tests_passed = $null
        candidate_tests_passed = $null
        patch_check_passed = $false
        scope_compliant = $false
        full_suite_baseline_passed = $null
    }
    error = $null
    note = "Local first-pass evaluator; not a secure sandbox or hidden-test evaluator."
}

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

function Get-GitStatus {
    param([string]$WorkingDirectory)

    $status = @(Invoke-Git $WorkingDirectory @(
        "status", "--porcelain", "--untracked-files=all"
    ))

    return ($status -join "`n").Trim()
}

function Get-ChangedPaths {
    param([string]$WorkingDirectory)

    $tracked = @(Invoke-Git $WorkingDirectory @(
        "diff", "--name-only"
    ))

    $staged = @(Invoke-Git $WorkingDirectory @(
        "diff", "--cached", "--name-only"
    ))

    $untracked = @(Invoke-Git $WorkingDirectory @(
        "ls-files", "--others", "--exclude-standard"
    ))

    return @(
        @($tracked) + @($staged) + @($untracked) |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            ForEach-Object { $_.Replace('\', '/') } |
            Sort-Object -Unique
    )
}


function Invoke-Pytest {
    param(
        [string]$WorkingDirectory,
        [string[]]$TestArguments = @()
    )

    Push-Location $WorkingDirectory
    try {
        $output = & python -m pytest @TestArguments 2>&1
        $exitCode = $LASTEXITCODE

        return [PSCustomObject]@{
            exit_code = $exitCode
            output = ($output | Out-String).Trim()
        }
    }
    finally {
        Pop-Location
    }
}

function Save-RunResult {
    New-Item -ItemType Directory -Path $RunsPath -Force |
        Out-Null

    $resultPath = Join-Path $RunsPath "P0-01_$RunId.json"

    [PSCustomObject]$Result |
        ConvertTo-Json -Depth 10 |
        Set-Content -LiteralPath $resultPath -Encoding UTF8

    Write-Host "Result file: $resultPath"
}

try {
    # Validate required files and worktree.
    if (-not (Test-Path $ManifestPath -PathType Leaf)) {
        throw "Task manifest not found: $ManifestPath"
    }

    if (-not (Test-Path $ResetScript -PathType Leaf)) {
        throw "Reset script not found: $ResetScript"
    }

    if (-not (Test-Path $WorktreePath -PathType Container)) {
        throw "Evaluation worktree not found: $WorktreePath"
    }

    $ResolvedPatch = (Resolve-Path -LiteralPath $PatchPath).Path

    if (-not (Test-Path $ResolvedPatch -PathType Leaf)) {
        throw "Patch file not found: $PatchPath"
    }

    $Result.patch_path = $ResolvedPatch

    # Require candidate patches to live outside the main repository.
    $mainPrefix = [System.IO.Path]::GetFullPath($MainRepoRoot).TrimEnd('\') + '\'
    $patchFullPath = [System.IO.Path]::GetFullPath($ResolvedPatch)

    if ($patchFullPath.StartsWith(
        $mainPrefix,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Store the candidate patch outside mock_python_repo."
    }

    # Read the authoritative P0-01 task definition.
    $manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
    $tasks = @($manifest.tasks | Where-Object { $_.task_id -eq "P0-01" })

    if ($tasks.Count -ne 1) {
        throw "Expected exactly one P0-01 task in tasks.json."
    }

    $task = $tasks[0]
    $targetCommit = [string]$task.base_revision

    if ($targetCommit -notmatch '^[0-9a-fA-F]{40}$') {
        throw "P0-01 base_revision must be a full 40-character commit hash."
    }

    # Verify the main repository is clean before resetting anything.
    $mainStatus = Get-GitStatus $MainRepoRoot
    if ($mainStatus) {
        throw "Main repository is dirty. Commit or resolve changes first:`n$mainStatus"
    }

    # Refuse to discard any worktree changes.
    $worktreeStatus = Get-GitStatus $WorktreePath
    if ($worktreeStatus) {
        throw "Evaluation worktree is dirty. No changes were removed:`n$worktreeStatus"
    }

    # Verify the worktree root is the expected directory.
    $actualRoot = (Invoke-Git $WorktreePath @(
        "rev-parse", "--show-toplevel"
    ) | Select-Object -First 1).Trim()

    $actualRoot = [System.IO.Path]::GetFullPath(
        $actualRoot.Replace('/', '\')
    ).TrimEnd('\')

    $expectedRoot = [System.IO.Path]::GetFullPath(
        $WorktreePath
    ).TrimEnd('\')

    if (-not $actualRoot.Equals(
        $expectedRoot,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Unexpected evaluation worktree root."
    }

    # Reset only through the existing safety-checked reset script.
    & $ResetScript

    $startingCommit = (Invoke-Git $WorktreePath @(
        "rev-parse", "HEAD"
    ) | Select-Object -First 1).Trim()

    if ($startingCommit -ne $targetCommit) {
        throw "Starting revision differs from the manifest revision."
    }

    $Result.starting_revision = $startingCommit

    # Establish whether the defect is reproducible before evaluating a patch.
    Write-Host "`nRunning targeted P0-01 baseline tests..."

    $baseline = Invoke-Pytest $WorktreePath @(
        "tests/test_discounts.py", "-q"
    )

    $Result.baseline = $baseline
    $Result.diagnostics.baseline_tests_passed = ($baseline.exit_code -eq 0)
    Write-Host $baseline.output

    # Require the two known boundary failures and the observed test counts.
    $expectedFailures = @(
        "test_discount_rate_boundaries\[100-0\.05\]",
        "test_discounted_total"
    ) 

    $failureSignatureMatches = @(
        $expectedFailures | Where-Object {
            $baseline.output -match $_
        }
    ).Count -eq $expectedFailures.Count

    $expectedSummaryMatches = (
        $baseline.output -match "2 failed, 5 passed"
    )

    if (
        $baseline.exit_code -eq 0 -or
        -not $failureSignatureMatches -or
        -not $expectedSummaryMatches
    ) {
        throw "Baseline signature mismatch. Expected exactly the known P0-01 test outcome (2 failures, 5 passes). Candidate patch was not applied."
    }
        # Record the full-suite outcome before applying the candidate patch.
    Write-Host "`nRunning full-suite faulty-baseline tests..."

    $fullBaseline = Invoke-Pytest $WorktreePath
    $Result.full_suite_baseline = $fullBaseline
    $Result.diagnostics.full_suite_baseline_passed = (
        $fullBaseline.exit_code -eq 0
    )

    Write-Host $fullBaseline.output

    if (
        $fullBaseline.exit_code -eq 0 -or
        $fullBaseline.output -notmatch "3 failed, 13 passed"
    ) {
        throw "Full-suite baseline signature mismatch. Candidate patch was not applied."
    }

    # Check that the patch applies without changing any files.
    $checkOutput = & git -C $WorktreePath apply --check $ResolvedPatch 2>&1
    $checkExitCode = $LASTEXITCODE

    $Result.patch_check_output = ($checkOutput | Out-String).Trim()
    $Result.diagnostics.patch_check_passed = ($checkExitCode -eq 0)

    if ($checkExitCode -ne 0) {
        throw "Patch check failed; the patch was not applied."
    }

    & git -C $WorktreePath apply $ResolvedPatch
    if ($LASTEXITCODE -ne 0) {
        throw "Patch application failed."
    }

    $Result.patch_applies = $true

    # Include tracked, staged, and untracked paths in scope checks.
    $changedPaths = @(Get-ChangedPaths $WorktreePath)
    $Result.changed_paths = $changedPaths

    $allowedPath = "src/discounts.py"
    $scopeCompliant = (
        $changedPaths.Count -eq 1 -and
        $changedPaths[0] -ceq $allowedPath
    )

    $protectedPrefixes = @($task.protected_paths | ForEach-Object {
        ([string]$_).Replace('\', '/')
    })

    $protectedChanges = @(
        $changedPaths | Where-Object {
            $changed = $_
            @($protectedPrefixes | Where-Object {
                $prefix = $_
                $changed -eq $prefix.TrimEnd('/') -or
                    $changed.StartsWith($prefix)
            }).Count -gt 0
        }
    )

    $Result.protected_paths_changed = $protectedChanges
    $Result.scope_compliant = $scopeCompliant
    $Result.diagnostics.scope_compliant = $scopeCompliant

    # Test the candidate even when its scope is wrong, to preserve diagnostics.
    Write-Host "`nRunning candidate tests..."
    $candidate = Invoke-Pytest $WorktreePath
    $Result.tests_after_patch = $candidate
    $Result.diagnostics.candidate_tests_passed = ($candidate.exit_code -eq 0)
    Write-Host $candidate.output

    $Result.accepted = (
        $baseline.exit_code -ne 0 -and
        $fullBaseline.exit_code -ne 0 -and
        $candidate.exit_code -eq 0 -and
        $scopeCompliant -and
        $protectedChanges.Count -eq 0
    )

    if (-not $scopeCompliant) {
        $Result.note = "Rejected: changes must be limited to src/discounts.py."
    }
    
    elseif ($protectedChanges.Count -gt 0) {
        $Result.note = "Rejected: one or more protected paths were changed."
    }   
    elseif ($candidate.exit_code -ne 0) {
        $Result.note = "Rejected: candidate test suite did not pass."
    }
    else {
        $Result.note = "Accepted by first-pass baseline, test, and scope criteria only."
    }
}
catch {
    $Result.error = $_.Exception.Message
    Write-Host "Evaluation error: $($Result.error)" -ForegroundColor Yellow
}
finally {
    try {
        Save-RunResult
    }
    catch {
        Write-Host "WARNING: Could not save the JSON result: $($_.Exception.Message)" -ForegroundColor Red
    }
}

if ($Result.error) {
    throw $Result.error
}

Write-Host "`nPrimary acceptance: $($Result.accepted)"
Write-Host "Scope compliant: $($Result.scope_compliant)"
Write-Host "Evaluation worktree has been preserved for inspection."
