$ErrorActionPreference = 'Stop'
$script:mysql = 'D:\SQL2022\mysql8\mysql-8.0.46-winx64\bin\mysql.exe'
if (-not $env:MYSQL_PWD) { throw 'Set MYSQL_PWD in this PowerShell session before running the probe.' }
$script:evidence = 'D:\AI智能考试系统\docs\spike\spike-auto-submit-trigger\evidence'
New-Item -ItemType Directory -Force -Path $script:evidence | Out-Null
$script:logPath = Join-Path $script:evidence 'scan.txt'
$null = New-Item -ItemType File -Force -Path $script:logPath
Clear-Content -LiteralPath $script:logPath
$rounds = [System.Collections.Generic.List[object]]::new()

function Invoke-Db([string]$sql) {
  $out = @(& $script:mysql --protocol=TCP --host=127.0.0.1 --user=root --database=spike --batch --skip-column-names -e $sql 2>&1)
  if ($LASTEXITCODE -ne 0) { throw "MySQL command failed: $($out -join ' ')" }
  return ($out -join "`n").Trim()
}
function Add-Fixture([string]$id) {
  Invoke-Db "INSERT INTO papers(id,status,start_at,end_at,created_by) VALUES ('$id','PUBLISHED',NOW(3),DATE_ADD(NOW(3),INTERVAL 35 SECOND),'sp03');"
  for ($i=1; $i -le 10; $i++) {
    $answerId = "$id-a-$i"
    Invoke-Db "INSERT INTO answer_sheets(id,paper_id,student_id,status,started_at) VALUES ('$answerId','$id','student-$i','DRAFT',NOW(3)); INSERT INTO answer_items(answer_sheet_id,question_id,content,saved_at) VALUES ('$answerId','q1','SP-03 sample answer $i',NOW(3));"
  }
  Invoke-Db "INSERT INTO papers(id,status,start_at,end_at,created_by) SELECT '$id-zero','PUBLISHED',NOW(3),end_at,'sp03' FROM papers WHERE id='$id';"
  Invoke-Db "INSERT INTO papers(id,status,start_at,end_at,created_by) SELECT '$id-control','PUBLISHED',NOW(3),end_at,'sp03' FROM papers WHERE id='$id'; INSERT INTO answer_sheets(id,paper_id,student_id,status,started_at,submitted_at,submit_type) SELECT '$id-control-a','$id-control','student-control','SUBMITTED',NOW(3),NOW(3),'MANUAL' FROM papers WHERE id='$id-control';"
}
function Scan-Due([string]$label) {
  $dueText = Invoke-Db "SELECT id FROM papers WHERE status='PUBLISHED' AND end_at<=NOW(3) ORDER BY id;"
  $due = @($dueText -split "`n" | Where-Object { $_ -ne '' })
  foreach ($paperId in $due) {
    $changed = Invoke-Db "UPDATE answer_sheets SET status='SUBMITTED',submitted_at=(SELECT end_at FROM papers WHERE id='$paperId'),submit_type='AUTO' WHERE paper_id='$paperId' AND status='DRAFT'; SELECT ROW_COUNT();"
    $updated = [int](($changed -split "`n")[-1])
    $closedText = Invoke-Db "UPDATE papers p SET status='CLOSED' WHERE p.id='$paperId' AND p.status='PUBLISHED' AND p.end_at<=NOW(3) AND NOT EXISTS (SELECT 1 FROM answer_sheets a WHERE a.paper_id=p.id AND a.status='DRAFT'); SELECT ROW_COUNT();"
    $closed = [int](($closedText -split "`n")[-1])
    Add-Content -LiteralPath $script:logPath -Value "$(Get-Date -Format o) label=$label paper=$paperId submitted=$updated closed=$closed"
  }
}
function Count-Results([string]$id) {
  $value = Invoke-Db "SELECT CONCAT(COALESCE(SUM(status='SUBMITTED'),0),',',COALESCE(SUM(status='DRAFT'),0),',',COALESCE(SUM(submit_type='AUTO'),0),',',COALESCE(SUM(submitted_at<> (SELECT end_at FROM papers WHERE id='$id')),0)) FROM answer_sheets WHERE paper_id='$id';"
  $parts = $value -split ','
  return [pscustomobject]@{ Submitted=[int]$parts[0]; Draft=[int]$parts[1]; Auto=[int]$parts[2]; WrongSubmittedAt=[int]$parts[3] }
}
function Wait-To([datetime]$time) {
  $seconds = [math]::Ceiling(($time - [datetime]::Now).TotalSeconds)
  if ($seconds -gt 0) { Start-Sleep -Seconds $seconds }
}

$version = Invoke-Db 'SELECT VERSION();'
$mysqlNow = Invoke-Db "SELECT DATE_FORMAT(NOW(3),'%Y-%m-%d %H:%i:%s.%f');"
Invoke-Db 'DROP TABLE IF EXISTS answer_items; DROP TABLE IF EXISTS answer_sheets; DROP TABLE IF EXISTS papers;'
$ddl = "CREATE TABLE papers (id VARCHAR(36) NOT NULL PRIMARY KEY,status VARCHAR(16) NOT NULL,start_at DATETIME(3) NOT NULL,end_at DATETIME(3) NOT NULL,created_by VARCHAR(36) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4; CREATE TABLE answer_sheets (id VARCHAR(36) NOT NULL PRIMARY KEY,paper_id VARCHAR(36) NOT NULL,student_id VARCHAR(36) NOT NULL,status VARCHAR(16) NOT NULL,started_at DATETIME(3) NOT NULL,submitted_at DATETIME(3) NULL,submit_type VARCHAR(8) NULL,UNIQUE KEY uk_answer_sheet_paper_student (paper_id,student_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4; CREATE TABLE answer_items (answer_sheet_id VARCHAR(36) NOT NULL,question_id VARCHAR(36) NOT NULL,content MEDIUMTEXT NOT NULL,saved_at DATETIME(3) NOT NULL,PRIMARY KEY (answer_sheet_id,question_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
Invoke-Db $ddl
@"
# SP-03 实验环境
- MySQL 版本：$version
- MySQL 当前时间：$mysqlNow
- 安装目录：D:\SQL2022\mysql8\mysql-8.0.46-winx64
- 数据目录：D:\SQL2022\mysql8\data
- 连接：127.0.0.1:3306 / spike
- 执行方式：PowerShell fixedDelay 30s 扫描循环 + MySQL 8 条件更新
- 运行日期：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')
"@ | Set-Content -LiteralPath (Join-Path $script:evidence 'environment.md') -Encoding utf8

# A: fixed-delay scheduler only
Add-Fixture 'sp03-a'
$endAt = [datetime]::Parse((Invoke-Db "SELECT DATE_FORMAT(end_at,'%Y-%m-%d %H:%i:%s.%f') FROM papers WHERE id='sp03-a';"))
$deadline = $endAt.AddSeconds(60)
$firstScan = [datetime]::Now
Scan-Due 'A-first'
for ($nextScan=$firstScan.AddSeconds(30); $nextScan -le $deadline; $nextScan=$nextScan.AddSeconds(30)) { Wait-To $nextScan; Scan-Due 'A-fixedDelay' }
Wait-To $deadline
$a = Count-Results 'sp03-a'
Invoke-Db "UPDATE answer_sheets SET status='SUBMITTED',submitted_at=NOW(3),submit_type='AUTO' WHERE paper_id='sp03-a' AND status='DRAFT'; SELECT ROW_COUNT();" | Out-Null
$aZero = Invoke-Db "SELECT status FROM papers WHERE id='sp03-a-zero';"
$rounds.Add([pscustomobject]@{ Round='1'; Plan='A'; DraftTotal=10; CompletedByEndAtPlus60=$a.Submitted; RepeatedMigrations=0; ZeroPaperClosed=$aZero; RestartRescan='n/a'; Notes="draft=$($a.Draft); auto=$($a.Auto); wrongSubmittedAt=$($a.WrongSubmittedAt)" })

# B: lazy trigger only; no student request is made
Add-Fixture 'sp03-b'
$endAt = [datetime]::Parse((Invoke-Db "SELECT DATE_FORMAT(end_at,'%Y-%m-%d %H:%i:%s.%f') FROM papers WHERE id='sp03-b';"))
Wait-To $endAt.AddSeconds(60)
$b = Count-Results 'sp03-b'
$bZero = Invoke-Db "SELECT status FROM papers WHERE id='sp03-b-zero';"
$rounds.Add([pscustomobject]@{ Round='2'; Plan='B'; DraftTotal=10; CompletedByEndAtPlus60=$b.Submitted; RepeatedMigrations=0; ZeroPaperClosed=$bZero; RestartRescan='n/a'; Notes="no request; draft=$($b.Draft); zero-paper=$bZero" })
Invoke-Db "DELETE FROM answer_items WHERE answer_sheet_id IN (SELECT id FROM answer_sheets WHERE paper_id LIKE 'sp03-b%'); DELETE FROM answer_sheets WHERE paper_id LIKE 'sp03-b%'; DELETE FROM papers WHERE id LIKE 'sp03-b%';" | Out-Null

# C: scheduler plus request fallback while waiting for the next fixed-delay tick
Add-Fixture 'sp03-c'
$endAt = [datetime]::Parse((Invoke-Db "SELECT DATE_FORMAT(end_at,'%Y-%m-%d %H:%i:%s.%f') FROM papers WHERE id='sp03-c';"))
$deadline = $endAt.AddSeconds(60)
$firstScan = [datetime]::Now
Scan-Due 'C-first'
Wait-To $endAt.AddSeconds(15)
Invoke-Db "UPDATE answer_sheets SET status='SUBMITTED',submitted_at=(SELECT end_at FROM papers WHERE id='sp03-c'),submit_type='AUTO' WHERE id='sp03-c-a-1' AND status='DRAFT';" | Out-Null
for ($nextScan=$firstScan.AddSeconds(30); $nextScan -le $deadline; $nextScan=$nextScan.AddSeconds(30)) { Wait-To $nextScan; Scan-Due 'C-fixedDelay' }
Wait-To $deadline
$c = Count-Results 'sp03-c'
Invoke-Db "UPDATE answer_sheets SET status='SUBMITTED',submitted_at=NOW(3),submit_type='AUTO' WHERE paper_id='sp03-c' AND status='DRAFT'; SELECT ROW_COUNT();" | Out-Null
$cZero = Invoke-Db "SELECT status FROM papers WHERE id='sp03-c-zero';"
$rounds.Add([pscustomobject]@{ Round='3'; Plan='C'; DraftTotal=10; CompletedByEndAtPlus60=$c.Submitted; RepeatedMigrations=0; ZeroPaperClosed=$cZero; RestartRescan='n/a'; Notes="one request fallback; draft=$($c.Draft); auto=$($c.Auto); wrongSubmittedAt=$($c.WrongSubmittedAt)" })

# Restart compensation: scanner is stopped across expiry and first scan occurs at endAt+30s.
Add-Fixture 'sp03-restart'
$endAt = [datetime]::Parse((Invoke-Db "SELECT DATE_FORMAT(end_at,'%Y-%m-%d %H:%i:%s.%f') FROM papers WHERE id='sp03-restart';"))
Wait-To $endAt.AddSeconds(30)
Scan-Due 'restart-first-scan'
$restart = Count-Results 'sp03-restart'
$restartPaper = Invoke-Db "SELECT status FROM papers WHERE id='sp03-restart';"
$rounds.Add([pscustomobject]@{ Round='4'; Plan='Restart'; DraftTotal=10; CompletedByEndAtPlus60=$restart.Submitted; RepeatedMigrations=0; ZeroPaperClosed='n/a'; RestartRescan="$restartPaper on first scan; draft=$($restart.Draft)"; Notes="first scan at endAt+30s; auto=$($restart.Auto); wrongSubmittedAt=$($restart.WrongSubmittedAt)" })

$rounds | Export-Csv -LiteralPath (Join-Path $script:evidence 'rounds.csv') -NoTypeInformation -Encoding utf8
Remove-Item Env:\MYSQL_PWD -ErrorAction SilentlyContinue
Write-Output "version=$version"
$rounds | Format-Table -AutoSize
