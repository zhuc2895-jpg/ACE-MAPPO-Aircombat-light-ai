$ErrorActionPreference = 'Stop'
$root = 'C:\Users\iop\Downloads\Compressed\第四届龙智杯参赛资料'
$main = Join-Path $root '龙智杯第四届参赛资料-0810更新高倍速平台\☆公开☆第四届“龙智杯”智能空战大赛-高倍速训练版'
$demo = Join-Path $root '龙智杯第四届参赛资料-0810更新高倍速平台\☆公开☆第四届“龙智杯”智能空战大赛-Python策略开发示例模板\PythonstrategyDemo'
$py38 = Join-Path $root 'mappo-train38\Scripts\python.exe'
$py   = 'C:\Users\iop\Anaconda3\python.exe'
$nofix = Join-Path $demo 'AIStrategy乐迪plus.py.before-guidefix-20260912.bak'
$log  = Join-Path $root '.ab_progress.log'
$resolvedRoot = (Resolve-Path -LiteralPath $main).Path

function Log($m) { Add-Content -LiteralPath $log -Value ("{0} {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) }

Add-Content -LiteralPath $log -Value ("=== AB campaign start {0} ===" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))

foreach ($variant in @('nofix','fixed','nofix','fixed')) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    if ($variant -eq 'fixed') { $tag = 'Afixed' } else { $tag = 'Bnofix' }
    $arch = Join-Path $main ("Evaluation\{0}_{1}" -f $tag, $stamp)
    New-Item -ItemType Directory -Path $arch -Force | Out-Null
    Log ("batch start variant={0} arch={1}" -f $variant, (Split-Path -Leaf $arch))
    Get-ChildItem -LiteralPath (Join-Path $main 'AcmiRecord') -Filter '*.acmi' -ErrorAction SilentlyContinue | ForEach-Object { [System.IO.File]::Delete($_.FullName) }
    Get-ChildItem -LiteralPath (Join-Path $main 'Result') -ErrorAction SilentlyContinue | ForEach-Object { [System.IO.File]::Delete($_.FullName) }
    $lastArch = $arch

    if ($variant -eq 'fixed') {
        & $py38 (Join-Path $demo 'deploy_ace_mappo.py') *> (Join-Path $arch 'deploy.log')
    } else {
        foreach ($i in 1..4) {
            Copy-Item -LiteralPath $nofix -Destination (Join-Path $main ("ACAS_0{0}\Pythonstrategy\AIStrategy0{0}.py" -f $i)) -Force
        }
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

    $sha = (Get-FileHash -LiteralPath (Join-Path $main 'ACAS_01\Pythonstrategy\AIStrategy01.py')).Hash.Substring(0,16)
    Log ("deployed sha={0}" -f $sha)

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
    & $py (Join-Path $root 'analyze_manual100.py') $arch --out (Join-Path $arch 'analysis') *> (Join-Path $arch 'analyze.log')
    Log ("batch done variant={0}" -f $variant)
}

foreach ($i in 1..4) {
    Copy-Item -LiteralPath (Join-Path $demo 'AIStrategy乐迪plus.py') -Destination (Join-Path $main ("ACAS_0{0}\Pythonstrategy\AIStrategy0{0}.py" -f $i)) -Force
}
if ($lastArch) {
    Copy-Item -LiteralPath (Join-Path $lastArch 'Result\SimuResultReport.txt') -Destination (Join-Path $main 'Result\SimuResultReport.txt') -Force
    Get-ChildItem -LiteralPath (Join-Path $lastArch 'AcmiRecord') -Filter '*.acmi' | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $main ("AcmiRecord\{0}" -f $_.Name)) -Force }
}
Log 'restored fixed build to slots'
Log 'ALL DONE'
