param(
    [string]$InputPath = (Join-Path $PSScriptRoot "github_painter.sh"),
    [string]$OutputPath = (Join-Path (Split-Path $PSScriptRoot -Parent) "Assets/github-painter-banner.svg"),
    [int]$Year = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Web

$pattern = "git commit --date='([^']+)'"
$counts = @{}

foreach ($line in Get-Content $InputPath) {
    if ($line -match $pattern) {
        $rawDate = $matches[1] -replace " GMT[+-]\d{4} \(.+\)$", ""
        $date = [DateTime]::ParseExact($rawDate, "ddd MMM dd yyyy HH:mm:ss", [System.Globalization.CultureInfo]::InvariantCulture)
        $key = $date.ToString("yyyy-MM-dd")

        if ($counts.ContainsKey($key)) {
            $counts[$key]++
        }
        else {
            $counts[$key] = 1
        }
    }
}

if ($counts.Count -eq 0) {
    throw "No git commit dates were found in $InputPath"
}

if ($Year -eq 0) {
    $Year = ([DateTime]::ParseExact(($counts.Keys | Sort-Object | Select-Object -First 1), "yyyy-MM-dd", [System.Globalization.CultureInfo]::InvariantCulture)).Year
}

$yearStart = [DateTime]::new($Year, 1, 1)
$yearEnd = [DateTime]::new($Year, 12, 31)
$gridStart = $yearStart.AddDays(-[int]$yearStart.DayOfWeek)
$gridEnd = $yearEnd.AddDays(6 - [int]$yearEnd.DayOfWeek)
$weekCount = [int](($gridEnd - $gridStart).Days / 7) + 1

$cell = 14
$gap = 4
$step = $cell + $gap
$left = 74
$top = 78
$headerHeight = 34
$legendTop = $top + (7 * $step) + 24
$panelWidth = ($weekCount * $step) + 80
$panelHeight = $legendTop + 44
$width = $left + ($weekCount * $step) + 56
$height = $panelHeight + 36

$palette = @(
    "#161b22",
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353"
)

$monthLabels = for ($month = 1; $month -le 12; $month++) {
    $monthStart = [DateTime]::new($Year, $month, 1)
    if ($monthStart -lt $gridStart -or $monthStart -gt $gridEnd) {
        continue
    }

    [PSCustomObject]@{
        Label = $monthStart.ToString("MMM", [System.Globalization.CultureInfo]::InvariantCulture)
        X = $left + ([int](($monthStart - $gridStart).Days / 7) * $step)
    }
}

$dayLabels = @(
    @{ Label = "Sun"; Row = 0 },
    @{ Label = "Tue"; Row = 2 },
    @{ Label = "Thu"; Row = 4 },
    @{ Label = "Sat"; Row = 6 }
)

$maxCommits = ($counts.Values | Measure-Object -Maximum).Maximum

$svg = [System.Text.StringBuilder]::new()
[void]$svg.AppendLine('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + $width + ' ' + $height + '" role="img" aria-labelledby="title desc">')
[void]$svg.AppendLine('  <title id="title">GitHub Painter Preview</title>')
[void]$svg.AppendLine('  <desc id="desc">Static banner generated from scripts/github_painter.sh using a GitHub-style contribution grid.</desc>')
[void]$svg.AppendLine('  <defs>')
[void]$svg.AppendLine('    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">')
[void]$svg.AppendLine('      <stop offset="0%" stop-color="#0d1117"/>')
[void]$svg.AppendLine('      <stop offset="100%" stop-color="#111827"/>')
[void]$svg.AppendLine('    </linearGradient>')
[void]$svg.AppendLine('  </defs>')
[void]$svg.AppendLine('  <rect width="' + $width + '" height="' + $height + '" fill="url(#bg)"/>')
[void]$svg.AppendLine('  <rect x="20" y="20" width="' + ($width - 40) + '" height="' + ($height - 40) + '" rx="18" fill="#0b1220" stroke="#30363d"/>')
[void]$svg.AppendLine('  <text x="' + $left + '" y="48" fill="#f0f6fc" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="700">GitHub Painter Preview</text>')
[void]$svg.AppendLine('  <text x="' + ($width - 32) + '" y="48" text-anchor="end" fill="#8b949e" font-family="Segoe UI, Arial, sans-serif" font-size="14">' + $Year + ' contribution layout from script</text>')

foreach ($month in $monthLabels) {
    [void]$svg.AppendLine('  <text x="' + $month.X + '" y="' + ($top - 20) + '" fill="#8b949e" font-family="Segoe UI, Arial, sans-serif" font-size="12">' + $month.Label + '</text>')
}

foreach ($day in $dayLabels) {
    $y = $top + ($day.Row * $step) + 11
    [void]$svg.AppendLine('  <text x="34" y="' + $y + '" fill="#8b949e" font-family="Segoe UI, Arial, sans-serif" font-size="12">' + $day.Label + '</text>')
}

for ($date = $gridStart; $date -le $gridEnd; $date = $date.AddDays(1)) {
    $key = $date.ToString("yyyy-MM-dd")
    $count = if ($counts.ContainsKey($key)) { [int]$counts[$key] } else { 0 }
    $level = if ($count -le 0) { 0 } elseif ($count -eq 1) { 1 } elseif ($count -eq 2) { 2 } elseif ($count -eq 3) { 3 } else { 4 }
    $week = [int](($date - $gridStart).Days / 7)
    $row = [int]$date.DayOfWeek
    $x = $left + ($week * $step)
    $y = $top + ($row * $step)
    $tooltip = $date.ToString("yyyy-MM-dd") + " : " + $count + " commit(s)"

    [void]$svg.AppendLine('  <rect x="' + $x + '" y="' + $y + '" width="' + $cell + '" height="' + $cell + '" rx="3" fill="' + $palette[$level] + '" stroke="#0b1220" stroke-width="1">')
    [void]$svg.AppendLine('    <title>' + [System.Web.HttpUtility]::HtmlEncode($tooltip) + '</title>')
    [void]$svg.AppendLine('  </rect>')
}

$legendX = $left
[void]$svg.AppendLine('  <text x="' + $legendX + '" y="' + $legendTop + '" fill="#8b949e" font-family="Segoe UI, Arial, sans-serif" font-size="12">Less</text>')
for ($i = 0; $i -lt $palette.Count; $i++) {
    $x = $legendX + 34 + ($i * ($cell + 6))
    [void]$svg.AppendLine('  <rect x="' + $x + '" y="' + ($legendTop - 11) + '" width="' + $cell + '" height="' + $cell + '" rx="3" fill="' + $palette[$i] + '" stroke="#0b1220" stroke-width="1"/>')
}
[void]$svg.AppendLine('  <text x="' + ($legendX + 34 + ($palette.Count * ($cell + 6)) + 6) + '" y="' + $legendTop + '" fill="#8b949e" font-family="Segoe UI, Arial, sans-serif" font-size="12">More</text>')

$footer = "Max commits on one day: $maxCommits   Source: scripts/github_painter.sh"
[void]$svg.AppendLine('  <text x="' + ($width - 32) + '" y="' + ($legendTop + 1) + '" text-anchor="end" fill="#8b949e" font-family="Segoe UI, Arial, sans-serif" font-size="12">' + $footer + '</text>')
[void]$svg.AppendLine('</svg>')

$outputDirectory = Split-Path $OutputPath -Parent
if ($outputDirectory -and -not (Test-Path $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
}

[System.IO.File]::WriteAllText($OutputPath, $svg.ToString(), [System.Text.UTF8Encoding]::new($false))
Write-Host "Wrote $OutputPath"
