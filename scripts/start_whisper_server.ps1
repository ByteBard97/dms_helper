# PowerShell Script to Start Whisper Live Docker Container

# Configuration
$ContainerName = "whisperlive_server"
$ImageName = "ghcr.io/collabora/whisperlive-gpu:latest"

# Check if the container exists
Write-Host "Checking for existing container named '$ContainerName'..."
$ExistingContainer = docker ps -a --filter "name=$ContainerName" --format "{{.Names}}"

if ($ExistingContainer -eq $ContainerName) {
    # Container exists, check its status
    Write-Host "Container '$ContainerName' found."
    $RunningContainer = docker ps --filter "name=$ContainerName" --filter "status=running" --format "{{.Names}}"

    if ($RunningContainer -eq $ContainerName) {
        # Container is already running
        Write-Host "Container '$ContainerName' is already running."
        # Optional: Attach to it? For now, just inform.
        # Read-Host "Press Enter to exit..."
    } else {
        # Container exists but is stopped, start it
        Write-Host "Starting existing container '$ContainerName'..."
        # Note: Using 'docker start -ai' will attach the console.
        # If you run this script from an IDE terminal, stopping might require
        # stopping the script itself or using 'docker stop' from another terminal.
        docker start -ai $ContainerName
    }
} else {
    # Container does not exist, run it for the first time
    Write-Host "Container '$ContainerName' not found. Running for the first time..."
    Write-Host "This may take a while if the model needs to be downloaded."
    docker run -it --gpus all -p 9090:9090 --name $ContainerName $ImageName --client_timeout 300
}

# Optional: Keep window open if not run interactively
# if (-not $Host.UI.RawUI.KeyAvailable -and $Host.Name -eq "ConsoleHost") {
#     Read-Host "Press Enter to exit..."
# } 