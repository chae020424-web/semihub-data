# Local offline HTTP server for SEMI-HUB. Requires built-in Windows PowerShell only.
# Listens on loopback only; never allows remote connections.
$ErrorActionPreference = 'Stop'
$folder = Split-Path -Parent $MyInvocation.MyCommand.Path
$mime = @{
 'index.html'='text/html; charset=utf-8'
 'style.css'='text/css; charset=utf-8'
 'bundle.js'='application/javascript; charset=utf-8'
 'roles-data.js'='application/javascript; charset=utf-8'
 'quiz-data.js'='application/javascript; charset=utf-8'
 'jobs-data.js'='application/javascript; charset=utf-8'
 'roles-ui.js'='application/javascript; charset=utf-8'
 'jobs-ui.js'='application/javascript; charset=utf-8'
 'app.js'='application/javascript; charset=utf-8'
}
$port = 8765
$listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $port)
try {
    $listener.Start()
} catch {
    Write-Host ('Port 8765 is unavailable. Close any existing SEMI-HUB window first. ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
Write-Host 'SEMI-HUB is ready at http://127.0.0.1:8765/' -ForegroundColor Green
try { Start-Process 'http://127.0.0.1:8765/' } catch { Write-Host 'Please manually open http://127.0.0.1:8765/' }
try {
    while ($true) {
        $client = $listener.AcceptTcpClient()
        try {
            $client.ReceiveTimeout = 10000
            $client.SendTimeout = 10000
            $stream = $client.GetStream()
            $reader = New-Object System.IO.StreamReader($stream,[System.Text.Encoding]::ASCII,$false,1024,$true)
            $first = $reader.ReadLine()
            if ([string]::IsNullOrEmpty($first)) { continue }
            # Drain HTTP request headers.
            for ($h=0; $h -lt 100; $h++) {
                $line = $reader.ReadLine()
                if ($null -eq $line -or $line -eq '') { break }
            }
            $parts = $first.Split(' ')
            $pathname = if ($parts.Length -ge 2) { $parts[1].Split('?')[0] } else { '/' }
            if ($pathname -eq '/') { $pathname = '/index.html' }
            $name = $pathname.TrimStart('/')
            if ($mime.ContainsKey($name) -and $parts[0] -eq 'GET') {
                $data = [System.IO.File]::ReadAllBytes((Join-Path $folder $name))
                $head = 'HTTP/1.1 200 OK' + "`r`n" + 'Content-Type: ' + $mime[$name] + "`r`n" + 'Content-Length: ' + $data.Length + "`r`n" + 'Cache-Control: no-store' + "`r`n" + 'Connection: close' + "`r`n`r`n"
            } else {
                $data = [System.Text.Encoding]::UTF8.GetBytes('Not Found')
                $head = 'HTTP/1.1 404 Not Found' + "`r`n" + 'Content-Type: text/plain; charset=utf-8' + "`r`n" + 'Content-Length: ' + $data.Length + "`r`n" + 'Connection: close' + "`r`n`r`n"
            }
            $bytes = [System.Text.Encoding]::ASCII.GetBytes($head)
            $stream.Write($bytes,0,$bytes.Length)
            $stream.Write($data,0,$data.Length)
            $stream.Flush()
        } catch { Write-Host ('Request error: ' + $_.Exception.Message) }
        finally { $client.Close() }
    }
} finally { $listener.Stop() }
