@echo off
REM Batch Script to Start Whisper Live Docker Container

REM Configuration
set ContainerName=whisperlive_server
set ImageName=ghcr.io/collabora/whisperlive-gpu:latest

echo Checking for existing container named '%ContainerName%'...

REM Check if container exists (running or stopped)
docker ps -a --filter "name=%ContainerName%" --format "{{.Names}}" | findstr /I /C:"%ContainerName%" > nul
if %errorlevel% == 0 (
    REM Container exists
    echo Container '%ContainerName%' found.
    REM Check if container is running
    docker ps --filter "name=%ContainerName%" --filter "status=running" --format "{{.Names}}" | findstr /I /C:"%ContainerName%" > nul
    if %errorlevel% == 0 (
        REM Container is already running
        echo Container '%ContainerName%' is already running.
    ) else (
        REM Container exists but is stopped, start it
        echo Starting existing container '%ContainerName%'...
        REM Using 'docker start -ai' will attach the console.
        docker start -ai %ContainerName%
    )
) else (
    REM Container does not exist, run it for the first time
    echo Container '%ContainerName%' not found. Running for the first time...
    echo This may take a while if the model needs to be downloaded.
    REM Run the image directly - timeout is handled by client handshake
    docker run -it --gpus all -p 9090:9090 --name %ContainerName% %ImageName%
)

echo.
REM Pause only if run directly by double-clicking
if "%~dpn0" == "%~dpn0" (
    if not defined PROMPT (
      pause
    )
) 