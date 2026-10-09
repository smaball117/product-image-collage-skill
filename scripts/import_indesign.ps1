param(
    [Parameter(Mandatory=$true)][string]$Batch,
    [Parameter(Mandatory=$true)][string]$Template,
    [string]$ProgId = 'InDesign.Application.2025',
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$batchPath = (Resolve-Path -LiteralPath $Batch).Path
$templatePath = (Resolve-Path -LiteralPath $Template).Path
$csvPath = Join-Path $batchPath '图片汇总.csv'
$outputPath = Join-Path $batchPath '待人工调图.indd'
$copyPath = Join-Path $batchPath '模板副本.indd'
$manifestPath = Join-Path $batchPath '.skill\batch.json'
if (-not (Test-Path -LiteralPath $csvPath)) { throw '缺少正式 CSV，先生成并解决映射。' }
$rows = @(Import-Csv -LiteralPath $csvPath -Encoding Unicode)
if ($rows.Count -eq 0) { throw 'CSV 没有记录。' }
$fields = @($rows[0].PSObject.Properties.Name)
$expectedLinks = 0
foreach ($row in $rows) {
    foreach ($field in $fields) {
        if ($field.StartsWith('@') -and $row.$field) {
            if (-not (Test-Path -LiteralPath $row.$field -PathType Leaf)) { throw "图片不存在：$($row.$field)" }
            $expectedLinks++
        }
    }
}
if ($CheckOnly) {
    [pscustomobject]@{ Template=$templatePath; Records=$rows.Count; ExpectedLinks=$expectedLinks; Csv=$csvPath } | ConvertTo-Json
    exit 0
}
if ((Test-Path -LiteralPath $outputPath) -or (Test-Path -LiteralPath $copyPath)) {
    throw '批次已有 ID 文件，先检查已有结果；不要覆盖或重复合并。'
}
# JSON encodes paths as JavaScript string literals without interpolating script code.
$cfg = @{ template=$templatePath; copy=$copyPath; csv=$csvPath; output=$outputPath; fields=$fields; links=$expectedLinks } | ConvertTo-Json -Compress
$script = @'
(function(c){
    var old=app.scriptPreferences.userInteractionLevel;
    try {
        app.scriptPreferences.userInteractionLevel=UserInteractionLevels.NEVER_INTERACT;
        var src=File(c.template), copy=File(c.copy);
        if(!src.copy(copy.fsName))throw Error('Cannot copy template');
        var d=app.open(copy), m=d.dataMergeProperties;
        m.selectDataSource(File(c.csv));
        if(m.dataMergeFields.length!==c.fields.length)throw Error('Template/CSV field count mismatch');
        for(var i=0;i<c.fields.length;i++){
            if(m.dataMergeFields[i].fieldName!==c.fields[i].replace(/^@/,''))throw Error('Field mismatch: '+c.fields[i]);
        }
        d.save();
        m.dataMergePreferences.recordSelection=RecordSelection.ALL_RECORDS;
        m.mergeRecords();
        var result=app.activeDocument;
        if(result.id===d.id)throw Error('No merged document');
        if(result.links.length<c.links)throw Error('Merged document has fewer image links than CSV');
        for(var j=0;j<result.links.length;j++){
            if(result.links[j].status!==LinkStatus.NORMAL)throw Error('Invalid image link: '+result.links[j].name);
        }
        for(var k=0;k<result.stories.length;k++){
            if(/<<[^>]+>>/.test(result.stories[k].contents))throw Error('Unbound text placeholder remains');
        }
        result.save(File(c.output));
        return 'OK|pages='+result.pages.length+'|links='+result.links.length+'|'+result.fullName.fsName;
    } catch(e){return 'ERROR|'+e.message;}
    finally{app.scriptPreferences.userInteractionLevel=old;}
})
'@
$app = New-Object -ComObject $ProgId
$result = $app.DoScript(($script + '(' + $cfg + ')'),1246973031)
if (-not $result.StartsWith('OK|')) { throw "InDesign 未完成：$result。若有启动恢复弹窗，先处理恢复；静默模式不能关闭已有模态弹窗。" }
if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf)) { throw 'ID 输出未保存。' }
if (Test-Path -LiteralPath $manifestPath) {
    $state = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $state.stage = 'waiting_manual_export'
    $state | Add-Member -NotePropertyName indesign_file -NotePropertyValue $outputPath -Force
    $state | Add-Member -NotePropertyName template -NotePropertyValue $templatePath -Force
    $state | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
}
$result
