param(
    [Parameter(Mandatory=$true)][string]$LibraryDirectory,
    [Parameter(Mandatory=$true)][string]$DefinitionDirectory
)
$ErrorActionPreference = 'Stop'
Add-Type -LiteralPath (Join-Path $LibraryDirectory 'Microsoft.AnalysisServices.Core.dll')
Add-Type -LiteralPath (Join-Path $LibraryDirectory 'Microsoft.AnalysisServices.Tabular.dll')
function Get-Settings($relation) {
    [ordered]@{
        fromCardinality = $relation.FromCardinality.ToString()
        toCardinality = $relation.ToCardinality.ToString()
        crossFilteringBehavior = $relation.CrossFilteringBehavior.ToString()
        isActive = $relation.IsActive
    }
}
$model = [Microsoft.AnalysisServices.Tabular.TmdlSerializer]::DeserializeModelFromFolder($DefinitionDirectory)
[ordered]@{
    assembly_version = [Microsoft.AnalysisServices.Tabular.SingleColumnRelationship].Assembly.GetName().Version.ToString()
    constructor = Get-Settings ([Microsoft.AnalysisServices.Tabular.SingleColumnRelationship]::new())
    relationships = @($model.Relationships | ForEach-Object {
        [ordered]@{ name = $_.Name; settings = Get-Settings $_ }
    })
} | ConvertTo-Json -Depth 5
