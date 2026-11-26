$dst = "c:\Users\elyas\OneDrive\Desktop\Negin\Mobihoc_Extention\Mobihoc_Extention\Negin_validation\P2\cooperscene\validation_inference"
$remote = "ei235@bouchet.ycrc.yale.edu"
$opts = @("-c","aes256-ctr","-o","MACs=hmac-sha2-512","-o","IPQoS=none")
$files = @(
  "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/validation_inference/vehicle_1.jsonl",
  "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/validation_inference/vehicle_2.jsonl",
  "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/validation_inference/vehicle_3.jsonl",
  "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/validation_inference/summary.json",
  "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/test_inference/test_boxes_vehicle_1.jsonl",
  "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/test_inference/test_boxes_vehicle_2.jsonl",
  "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/test_inference/test_boxes_vehicle_3.jsonl"
)
$sources = $files | ForEach-Object { "${remote}:$_" }
& scp @opts @sources $dst
Write-Host "COPY_EXIT $LASTEXITCODE"
