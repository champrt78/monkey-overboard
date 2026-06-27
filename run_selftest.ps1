$godot = "C:\Users\Ray\Desktop\Godot_v4.6-stable_win64_console.exe"
$proj  = "C:\Users\Ray\kimi-repos\monkey-overboard\godot"
$out = "$env:TEMP\mo_out.txt"
$err = "$env:TEMP\mo_err.txt"
$p = Start-Process -FilePath $godot -ArgumentList @('--headless','--path',$proj,'--mo-selftest') `
     -NoNewWindow -PassThru `
     -RedirectStandardOutput $out -RedirectStandardError $err
if (-not $p.WaitForExit(40000)) { $p.Kill() }
Write-Host "--- STDOUT ---"
Get-Content $out
Write-Host "--- STDERR ---"
Get-Content $err
