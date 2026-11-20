# Envoie une archive d'application au hub (banque A) par SSH et la prepare pour le prochain demarrage.
# Usage :
#   .\deployer-app.ps1 -Archive app.ctapp            # installe (next), sans redemarrer
#   .\deployer-app.ps1 -Archive app.ctapp -Reboot    # installe puis redemarre pour l'essai
#   .\deployer-app.ps1 -Status                       # etat des versions
# L'essai est unique : sans HEALTH_OK, le hub abandonne la version et redemarre une fois sur l'actuelle.
param(
    [string]$Archive,
    [switch]$Reboot,
    [switch]$Status
)
$ErrorActionPreference = 'Stop'
$project = Resolve-Path (Join-Path $PSScriptRoot '..\..\..')
$key = Join-Path $project 'analyse-2026-11-17\acces-admin\ram-boot\cozytouch-admin-rsa2048'
$known = Join-Path $project 'analyse-2026-11-18\persistance-banque-a\prive\known-hosts-banque-a'
$sshArgs = "-p 2222 -i `"$key`" -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 " +
           "-o StrictHostKeyChecking=yes -o `"UserKnownHostsFile=$known`" root@<IP_HUB>"

function Invoke-Hub([string]$command, [string]$stdinFile) {
    $redirect = if ($stdinFile) { " < `"$stdinFile`"" } else { '' }
    # cmd.exe transmet les octets tels quels ; PowerShell 5.1 les convertirait en texte.
    # La sortie du hub va a l'ecran : sinon PowerShell la renverrait avec le code de retour.
    cmd.exe /c "ssh $sshArgs `"$command`"$redirect" | Out-Host
    return $LASTEXITCODE
}

if ($Status -or -not $Archive) {
    exit (Invoke-Hub 'ct-update status' $null)
}
$file = Resolve-Path $Archive
$sha = (Get-FileHash -Algorithm SHA256 $file).Hash.ToLowerInvariant()
Write-Host "Archive $file sha256=$sha"
$rc = Invoke-Hub "ct-update install $sha" $file
if ($rc -ne 0) { Write-Host "Installation refusee (code $rc)"; exit $rc }
$null = Invoke-Hub 'ct-update status' $null
if ($Reboot) {
    Write-Host 'Redemarrage pour l''essai de la nouvelle version...'
    $null = Invoke-Hub 'ct-update reboot' $null
    Write-Host 'Suivre ensuite : .\deployer-app.ps1 -Status (mode=current et la nouvelle version apres HEALTH_OK)'
}
