# AI_OS 上传脚本 — 把项目推到 VPS
# 用法: .\upload_to_vps.ps1 -Ip "你的VPS_IP"
param(
    [Parameter(Mandatory=$true)]
    [string]$Ip
)

Write-Host "Uploading AI_OS to $Ip ..." -ForegroundColor Green

# 排除不需要上传的文件
$exclude = @(".git", "__pycache__", ".env", "*.pyc")
$args = @("-r", "-P")
foreach ($e in $exclude) { $args += "--exclude=$e" }

# SCP 上传
scp @args "C:\Users\carlo\Desktop\AI_OS\*" "root@${Ip}:/opt/AI_OS/"

if ($?) {
    Write-Host "Upload complete!" -ForegroundColor Green
    Write-Host "Now SSH in and run: cd /opt/AI_OS && chmod +x setup_vps.sh && ./setup_vps.sh"
} else {
    Write-Host "Upload failed. Check your IP and network." -ForegroundColor Red
}
