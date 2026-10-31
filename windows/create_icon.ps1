# Draw a self-contained Windows ICO without third-party dependencies.
param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
$folder = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Path $folder -Force | Out-Null
$bitmap = [System.Drawing.Bitmap]::new(128, 128)
$g = [System.Drawing.Graphics]::FromImage($bitmap)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$background = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(25,29,35))
$white = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(247,250,252))
$teal = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(123,205,195))
$borderPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(226,232,238),6)
try {
    $g.Clear([System.Drawing.Color]::Transparent)
    $g.FillEllipse($background,0,0,127,127)
    $points = @(
        [System.Drawing.Point]::new(23,46),
        [System.Drawing.Point]::new(40,31),
        [System.Drawing.Point]::new(58,46),
        [System.Drawing.Point]::new(76,31),
        [System.Drawing.Point]::new(94,46),
        [System.Drawing.Point]::new(111,31)
    )
    $g.DrawLines($borderPen,[System.Drawing.Point[]]$points)
    for ($i=0; $i -lt $points.Count; $i++) {
        $brush = if ($i -eq 0 -or $i -eq 3) { $teal } else { $white }
        $g.FillEllipse($brush,$points[$i].X-8,$points[$i].Y-8,16,16)
    }
    $font = [System.Drawing.Font]::new("Arial",36,[System.Drawing.FontStyle]::Bold,[System.Drawing.GraphicsUnit]::Pixel)
    try {
        $format = [System.Drawing.StringFormat]::new()
        $format.Alignment = [System.Drawing.StringAlignment]::Center
        $format.LineAlignment = [System.Drawing.StringAlignment]::Center
        $g.DrawString("ELP",$font,$white,([System.Drawing.RectangleF]::new(0,67,128,48)),$format)
        $format.Dispose()
    } finally { $font.Dispose() }
    # A PNG-compressed Windows ICO can be written with its 22-byte directory header.
    $stream = [System.IO.MemoryStream]::new()
    try {
        $bitmap.Save($stream,[System.Drawing.Imaging.ImageFormat]::Png)
        $png = $stream.ToArray()
        $file = [System.IO.File]::Open($OutputPath,[System.IO.FileMode]::Create)
        try {
            $writer = [System.IO.BinaryWriter]::new($file)
            $writer.Write([UInt16]0)
            $writer.Write([UInt16]1)
            $writer.Write([UInt16]1)
            $writer.Write([Byte]128)
            $writer.Write([Byte]128)
            $writer.Write([Byte]0)
            $writer.Write([Byte]0)
            $writer.Write([UInt16]1)
            $writer.Write([UInt16]32)
            $writer.Write([UInt32]$png.Length)
            $writer.Write([UInt32]22)
            $writer.Write($png)
            $writer.Flush()
            $writer.Dispose()
        } finally { $file.Dispose() }
    } finally { $stream.Dispose() }
} finally {
    $borderPen.Dispose()
    $background.Dispose()
    $white.Dispose()
    $teal.Dispose()
    $g.Dispose()
    $bitmap.Dispose()
}
Write-Host "Created icon: $OutputPath"
