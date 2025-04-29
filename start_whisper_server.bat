@echo off
REM Starts the Whisper Live Docker container for transcription.

echo Starting Whisper Live Docker container...
echo Make sure Docker Desktop is running and has access to GPUs if needed.

docker run -it --rm --gpus all -p 9090:9090 ghcr.io/collabora/whisperlive-gpu:latest

echo Whisper Live container exited.
pause 