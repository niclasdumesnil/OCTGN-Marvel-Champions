<#
Génère les dos de cartes badgés « BETA » à partir des dos officiels.

Utilitaire ponctuel : les PNG produits sont versionnés dans ce dossier et
copiés dans le staging par build.py (clé `fichiers_remplaces` de config.json).
À relancer seulement si upstream change ses dos de cartes.

    powershell -File tools/beta/assets/generer-badges.ps1
#>
[CmdletBinding()] param(
    [string]$Texte = "BETA"
)
Add-Type -AssemblyName System.Drawing

$racineRepo = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$source = Join-Path $racineRepo "055c536f-adba-4bc2-acbf-9aefb9756046\cards"
$sorties = @("back.png", "altback.png", "vilback.png")

foreach ($nom in $sorties) {
    $cheminSource = Join-Path $source $nom
    if (-not (Test-Path $cheminSource)) { Write-Warning "absent : $nom"; continue }

    $origine = [System.Drawing.Image]::FromFile($cheminSource)
    $image = New-Object System.Drawing.Bitmap($origine.Width, $origine.Height)
    $g = [System.Drawing.Graphics]::FromImage($image)
    $g.DrawImage($origine, 0, 0, $origine.Width, $origine.Height)
    $origine.Dispose()

    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAlias

    # Bandeau en bas, proportionnel à la hauteur de la carte
    $hauteurBandeau = [math]::Max(18, [int]($image.Height * 0.13))
    $y = $image.Height - $hauteurBandeau
    $fond = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(225, 200, 30, 30))
    $g.FillRectangle($fond, 0, $y, $image.Width, $hauteurBandeau)
    $liseret = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 255, 255, 255)), 2
    $g.DrawLine($liseret, 0, $y, $image.Width, $y)

    # Texte centré dans le bandeau
    $taille = [int]($hauteurBandeau * 0.62)
    $police = New-Object System.Drawing.Font("Arial", $taille, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
    $format = New-Object System.Drawing.StringFormat
    $format.Alignment = [System.Drawing.StringAlignment]::Center
    $format.LineAlignment = [System.Drawing.StringAlignment]::Center
    $encre = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $zone = New-Object System.Drawing.RectangleF(0, $y, $image.Width, $hauteurBandeau)
    $g.DrawString($Texte, $police, $encre, $zone, $format)

    $destination = Join-Path $PSScriptRoot $nom
    $image.Save($destination, [System.Drawing.Imaging.ImageFormat]::Png)
    "$nom -> $($image.Width)x$($image.Height)"

    $g.Dispose(); $image.Dispose(); $fond.Dispose(); $liseret.Dispose(); $police.Dispose(); $encre.Dispose()
}
