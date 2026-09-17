$ErrorActionPreference = 'Stop'
$root = 'C:\Users\iop\Downloads\Compressed\第四届龙智杯参赛资料'
$main = Join-Path $root '龙智杯第四届参赛资料-0810更新高倍速平台\☆公开☆第四届“龙智杯”智能空战大赛-高倍速训练版'
$demo = Join-Path $root '龙智杯第四届参赛资料-0810更新高倍速平台\☆公开☆第四届“龙智杯”智能空战大赛-Python策略开发示例模板\PythonstrategyDemo'
$py   = 'C:\Users\iop\Anaconda3\python.exe'
$base = Join-Path $demo 'tmp\recovered_20260913\baseline\AIStrategy_baseline_runnable.py'
$von  = Join-Path $demo 'tmp\variants_20260917\AIStrategy_gates_on.py'
$voff = Join-Path $demo 'tmp\variants_20260917\AIStrategy_gates_off.py'
$log  = Join-Path $root '.gates_progress.log'
$resolvedRoot = (Resolve-Path -LiteralPath $main).Path

function Log($m) { Add-Content -LiteralPath $log -Value ("{0} {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) }

Add-Content -LiteralPath $log -Value ("=== gates A/B start {0} ===" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
Log ("gates_on  sha12 = {0}" -f (Get-FileHash -LiteralPath $von).Hash.Substring(0,12))
Log ("gates_off sha12 = {0}" -f (Get-FileHash -LiteralPath $voff).Hash.Substring(0,12))
Log ("原版       sha12 = {0}" -f (Get-FileHash -LiteralPath $base).Hash.Substring(0,12))

# 3 rounds, order alternates each round so drift cancels
$jobs = @(
    @{ v = 'on';  dir = 'red' }, @{ v = 'on';  dir = 'blue' },
    @{ v = 'off'; dir = 'red' }, @{ v = 'off'; dir = 'blue' },
    @{ v = 'off'; dir = 'red' }, @{ v = 'off'; dir = 'blue' },
    @{ v = 'on';  dir = 'red' }, @{ v = 'on';  dir = 'blue' },
    @{ v = 'on';  dir = 'red' }, @{ v = 'on';  dir = 'blue' },
    @{ v = 'off'; dir = 'red' }, @{ v = 'off'; dir = 'blue' }
)

foreach ($job in $jobs) {
    $strategy = if ($job.v -eq 'on') { $von } else { $voff }
    if ($job.dir -eq 'red') { $map = @{ 1 = $strategy; 2 = $strategy; 3 = $base; 4 = $base } }
    else                    { $map = @{ 1 = $base; 2 = $base; 3 = $strategy; 4 = $strategy } }

    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $arch = Join-Path $main ("Evaluation\gates_{0}_plus_{1}_{2}" -f $job.v, $job.dir, $stamp)
    New-Item -ItemType Directory -Path $arch -Force | Out-Null
    Log ("batch start gates={0} plus={1} arch={2}" -f $job.v, $job.dir, (Split-Path -Leaf $arch))

    Get-ChildItem -LiteralPath (Join-Path $main 'AcmiRecord') -Filter '*.acmi' -ErrorAction SilentlyContinue | ForEach-Object { [System.IO.File]::Delete($_.FullName) }
    Get-ChildItem -LiteralPath (Join-Path $main 'Result') -ErrorAction SilentlyContinue | ForEach-Object { [System.IO.File]::Delete($_.FullName) }

    foreach ($i in 1..4) {
        Copy-Item -LiteralPath $map[$i] -Destination (Join-Path $main ("ACAS_0{0}\Pythonstrategy\AIStrategy0{0}.py" -f $i)) -Force
    }
    foreach ($i in 1..4) {
        foreach ($sub in @('__pycache__','ace_mappo\__pycache__')) {
            $t = Join-Path $main ("ACAS_0{0}\Pythonstrategy\{1}" -f $i, $sub)
            if ([System.IO.Directory]::Exists($t)) {
                $r = [System.IO.Path]::GetFullPath($t)
                if (-not $r.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) { throw "UNSAFE $r" }
                [System.IO.Directory]::Delete($r, $true)
            }
        }
    }
    $h = (1..4 | ForEach-Object { (Get-FileHash -LiteralPath (Join-Path $main ("ACAS_0{0}\Pythonstrategy\AIStrategy0{0}.py" -f $_))).Hash.Substring(0,12) }) -join ','
    Log ("slot hashes {0}" -f $h)

    $p = Start-Process -FilePath (Join-Path $main 'Simplat.exe') -WorkingDirectory $main `
         -RedirectStandardOutput (Join-Path $arch 'Simplat.stdout.txt') `
         -RedirectStandardError  (Join-Path $arch 'Simplat.stderr.txt') `
         -PassThru -Wait -WindowStyle Hidden
    Log ("sim exit={0} at {1}" -f $p.ExitCode, (Get-Date -Format 'HH:mm:ss'))

    New-Item -ItemType Directory -Path (Join-Path $arch 'Result'), (Join-Path $arch 'AcmiRecord') -Force | Out-Null
    Move-Item -LiteralPath (Join-Path $main 'Result\SimuResultReport.txt') -Destination (Join-Path $arch 'Result\SimuResultReport.txt') -Force
    Get-ChildItem -LiteralPath (Join-Path $main 'AcmiRecord') -Filter '*.acmi' | ForEach-Object {
        Move-Item -LiteralPath $_.FullName -Destination (Join-Path $arch ("AcmiRecord\{0}" -f $_.Name)) -Force
    }
    foreach ($f in @('SimuConfig.txt','InitConfig.txt','AreaConfig.txt')) {
        Copy-Item -LiteralPath (Join-Path $main $f) -Destination (Join-Path $arch $f) -Force
    }
    Copy-Item -LiteralPath $strategy -Destination (Join-Path $arch 'AIStrategy_used.py') -Force
    & $py (Join-Path $root 'analyze_manual100.py') $arch --out (Join-Path $arch 'analysis') *> (Join-Path $arch 'analyze.log')
    Log ("batch done gates={0} plus={1}" -f $job.v, $job.dir)
}

foreach ($i in 1..4) {
    Copy-Item -LiteralPath $voff -Destination (Join-Path $main ("ACAS_0{0}\Pythonstrategy\AIStrategy0{0}.py" -f $i)) -Force
}
Log 'restored gates_off (current committed source) to all slots'
Log 'ALL DONE'
