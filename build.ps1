# PowerShell скрипт для збірки всіх компонентів в exe файли

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Збірка Parent Control в один exe файл" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Перевіряємо чи PyInstaller встановлено
try {
    $null = Get-Command pyinstaller -ErrorAction Stop
} catch {
    Write-Host "Помилка: PyInstaller не знайдено!" -ForegroundColor Red
    Write-Host "Встановіть його: pip install pyinstaller" -ForegroundColor Yellow
    exit 1
}

# Перевіряємо чи spec файл існує
$specFile = "parent_control.spec"
if (-not (Test-Path $specFile)) {
    Write-Host "Помилка: $specFile не знайдено!" -ForegroundColor Red
    exit 1
}

Write-Host "Збірка: Parent Control (parent_control.exe)" -ForegroundColor Cyan
Write-Host ""

try {
    pyinstaller --clean $specFile
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Cyan
        Write-Host "Підсумок збірки:" -ForegroundColor Cyan
        Write-Host "============================================================" -ForegroundColor Cyan
        Write-Host "✓ Проект успішно зібрано в один exe файл!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Зібраний exe файл знаходиться в директорії 'dist/':" -ForegroundColor Cyan
        Write-Host "  - dist/parent_control.exe"
        Write-Host ""
        Write-Host "Для запуску скопіюйте exe файл разом з:" -ForegroundColor Yellow
        Write-Host "  - config.json (або створіть новий при першому запуску)"
        Write-Host "  - .env файл з BOT_TOKEN"
        Write-Host ""
        Write-Host "Запуск:" -ForegroundColor Cyan
        Write-Host "  parent_control.exe"
        Write-Host "  або"
        Write-Host "  parent_control.exe --no-gui  # без GUI"
    } else {
        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Cyan
        Write-Host "Помилка збірки!" -ForegroundColor Red
        Write-Host "============================================================" -ForegroundColor Cyan
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "Помилка при збірці: $_" -ForegroundColor Red
    exit 1
}

