param([string]$ReleaseDirectory = "release")

$ErrorActionPreference = "Stop"
$releaseRoot = (Resolve-Path -LiteralPath $ReleaseDirectory).Path
$installer = Get-ChildItem -LiteralPath $releaseRoot -Filter "Super Video Pro Setup *.exe" -File |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
$application = Get-ChildItem -LiteralPath (Join-Path $releaseRoot "win-unpacked") -Filter "Super Video Pro.exe" -File |
  Select-Object -First 1

if (-not $installer) { throw "Signed NSIS installer was not produced" }
if (-not $application) { throw "Signed unpacked application executable was not produced" }

$lines = @("Super Video Pro Authenticode verification", "Verified: $([DateTime]::UtcNow.ToString('o'))")
foreach ($target in @($installer, $application)) {
  $signature = Get-AuthenticodeSignature -LiteralPath $target.FullName
  if ($signature.Status -ne "Valid") {
    throw "Authenticode verification failed for $($target.Name): $($signature.Status) $($signature.StatusMessage)"
  }
  if (-not $signature.SignerCertificate) { throw "Signer certificate is missing for $($target.Name)" }
  if (-not $signature.TimeStamperCertificate) { throw "Trusted timestamp is missing for $($target.Name)" }
  $lines += "$($target.Name) | Status=Valid | Subject=$($signature.SignerCertificate.Subject) | Thumbprint=$($signature.SignerCertificate.Thumbprint) | TimestampSubject=$($signature.TimeStamperCertificate.Subject)"
}

$reportPath = Join-Path $releaseRoot "authenticode-report.txt"
Set-Content -LiteralPath $reportPath -Value $lines -Encoding utf8
Write-Host "Authenticode verification passed for installer and application executable."
