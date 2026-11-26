# Window 2, after window 1 is sitting at a shell prompt.
$script = Join-Path $PSScriptRoot "remote_probe.sh"
Get-Content -Encoding ASCII $script | ssh -T `
  -o ControlMaster=no `
  -o "ControlPath=//./pipe/bouchet-p2" `
  ei235@bouchet.ycrc.yale.edu "tr -d '\r' | bash -l -s"
