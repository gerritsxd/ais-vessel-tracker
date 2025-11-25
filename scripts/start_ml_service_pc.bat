@echo off
REM Start ML Service on PC for VPS proxy
REM This allows VPS to use PC resources for ML training/predictions

echo ================================================================================
echo ML PREDICTOR SERVICE (PC)
echo ================================================================================
echo.
echo Starting ML service on port 5001...
echo VPS should be configured to proxy requests to this service.
echo.
echo Press Ctrl+C to stop the service.
echo ================================================================================
echo.

cd /d "%~dp0\.."

REM Run from project root - the script handles paths correctly
python src\services\ml_service_pc.py --host 0.0.0.0 --port 5001

pause

