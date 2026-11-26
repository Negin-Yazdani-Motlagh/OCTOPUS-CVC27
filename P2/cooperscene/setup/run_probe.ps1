# No ControlMaster. Windows OpenSSH rejects those sockets.
# Duo will ask twice. Press 1 each time.

Set-Location $PSScriptRoot

scp -c aes256-ctr -o MACs=hmac-sha2-512 -o IPQoS=none `
  .\remote_probe.sh ei235@bouchet.ycrc.yale.edu:.cs_p2_probe.sh

ssh -tt -c aes256-ctr -o MACs=hmac-sha2-512 -o IPQoS=none `
  ei235@bouchet.ycrc.yale.edu "tr -d '\r' < ~/.cs_p2_probe.sh | bash -l"
