@echo off
REM Starts the Whisper Live Docker container, reusing if possible.

echo Checking for existing Whisper Live container (whisperlive_server)...
docker ps -a --filter name=^whisperlive_server$ --format "{{.Names}}" | findstr . > nul

if %errorlevel% equ 0 (
    echo Found existing container. Attempting to start and attach...
    docker start -ai whisperlive_server
) else (
    echo No existing container found or failed to check.
    echo Running container for the first time (will download model)...
    echo Assigning name 'whisperlive_server' for future reuse.
    REM Run WITHOUT --rm and WITH --name
    docker run -it --gpus all -p 9090:9090 --name whisperlive_server ghcr.io/collabora/whisperlive-gpu:latest
)

if %errorlevel% neq 0 (
    echo.
    echo Docker command failed. Please check Docker Desktop status and GPU drivers/toolkit.
)

echo.
echo Container session finished or failed to start.

pause 