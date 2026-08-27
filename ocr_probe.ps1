param([string]$ImagePath)
$ErrorActionPreference = 'Stop'
try {
    # Load WinRT types
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    Add-Type -AssemblyName System.Runtime.InteropServices.WindowsRuntime

    # Load the image file
    $storageFileType = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
    $file = [Windows.Storage.StorageFile]::GetFileFromPathAsync($ImagePath).GetAwaiter().GetResult()
    $stream = $file.OpenReadAsync().GetAwaiter().GetResult()
    $decoder = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream).GetAwaiter().GetResult()
    $sb = $decoder.GetSoftwareBitmapAsync().GetAwaiter().GetResult()

    # Create OCR engine
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if ($engine -eq $null) { Write-Host 'OCR_ENGINE_NULL'; exit 1 }

    $lang = $engine.RecognizerLanguage
    Write-Host "LANG_DISPLAY=$($lang.DisplayName)"
    Write-Host "LANG_TAG=$($lang.LanguageTag)"

    # Recognize
    $result = $engine.RecognizeAsync($sb).GetAwaiter().GetResult()
    Write-Host "OCR_TEXT=$($result.Text)"
    Write-Host "OCR_LINES=$($result.Lines.Count)"
    exit 0
} catch {
    Write-Host "PS_ERROR=$($_.Exception.Message)"
    exit 1
}
