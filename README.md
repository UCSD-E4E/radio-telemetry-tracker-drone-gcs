# Radio Telemetry Tracker Drone Ground Control Station (GCS)

**The Radio Telemetry Tracker Drone Ground Control Station (GCS)** is a desktop application designed to interface with the [**Radio Telemetry Tracker Drone Field Device Software (FDS)**](https://github.com/UCSD-E4E/radio-telemetry-tracker-drone-fds) for wildlife radio tracking. Using this GCS, users can configure radio parameters, send start/stop commands, track GPS data, visualize pings on a map, and control drone operations in real-time or via a built-in simulator.

## Table of Contents
- [Radio Telemetry Tracker Drone Ground Control Station (GCS)](#radio-telemetry-tracker-drone-ground-control-station-gcs)
  - [Table of Contents](#table-of-contents)
  - [System Requirements](#system-requirements)
  - [Installation](#installation)
    - [Option 1: Install from Release (Recommended)](#option-1-install-from-release-recommended)
    - [Option 2: Build from Source](#option-2-build-from-source)
  - [Development](#development)
    - [Setting Up Development Environment](#setting-up-development-environment)
    - [Development Commands](#development-commands)
  - [Troubleshooting](#troubleshooting)
    - [Common Issues](#common-issues)
- [License](#license)

## System Requirements

- **Operating System**: Windows 10/11, Ubuntu 22.04+ (or similar)
- **Python**: 3.13+ (required for all installation methods)
- **Additional Build Requirements** (only if building from source):
  - UV 0.1.0+
  - Node.js 22+
  - npm 10+

## Installation

### Option 1: Install from Release (Recommended)

1. Install using pip:

```bash
# Replace [version] with the version number you want to install
pip install https://github.com/UCSD-E4E/radio-telemetry-tracker-drone-gcs/releases/download/v[version]/radio_telemetry_tracker_drone_gcs-[version]-py3-none-any.whl
```

2. Run the application:

```bash
rtt-drone-gcs
```

### Option 2: Build from Source

1. Clone the repository:

```bash
git clone https://github.com/UCSD-E4E/radio-telemetry-tracker-drone-gcs.git

cd radio-telemetry-tracker-drone-gcs
```

2. Install Python dependencies:

```bash
uv sync
```

3. Build and install frontend:

```bash
cd frontend
npm install
npm run build
cd ..
```

4. Copy frontend dist to package directory:

```bash
mkdir -p radio_telemetry_tracker_drone_gcs/frontend_dist
cp -r frontend/dist/ radio_telemetry_tracker_drone_gcs/frontend_dist/
```

5. Run the application:

```bash
uv run rtt-drone-gcs
```

## Development

### Setting Up Development Environment

1. Follow the "Build from Source" steps 1-3 above (no need to manually copy frontend dist)
2. Install additional development dependencies:

```bash
uv sync --group dev
```

### Development Commands

- **Run with automatic frontend building** (Recommended for development):

```bash
uv run python -m scripts.dev
```

This command will automatically build the frontend and copy it to the correct location before running the app.

- **Run without automatic frontend building** (Useful for testing):

```bash
uv run rtt-drone-gcs
```

⚠️ Remember to rebuild and copy the frontend files when making frontend changes!

- **Run tests**:

```bash
uv run pytest
```

- **Run linter**:

```bash
uv run ruff check .
```

- **Run frontend tests**:

```bash
cd frontend
npm run test
```

## Troubleshooting

### Common Issues

1. **Frontend Not Found Error**
   - If using `rtt-drone-gcs`, ensure you've:
     1. Built the frontend (`npm run build` in frontend directory)
     2. Copied the build to `radio_telemetry_tracker_drone_gcs/frontend_dist`
   - Alternatively, use `uv run python -m scripts.dev` which handles this automatically
   - Try reinstalling the package

2. **Connection Issues**
   - Verify FDS is running and accessible
   - Check COM port settings
   - Look for connection timeout messages in logs

3. **Map Display Problems**
   - Ensure you have an internet connection for initial tile loading
   - Check if offline tile cache is properly configured
   - Verify WebEngine is working (may need graphics driver update)

4. **Build Errors**
   - Verify Python 3.13+ is installed and active
   - Ensure all dependencies are installed (`uv sync`)
   - Check Node.js version (22+) if building frontend
   - Make sure frontend dist is in the correct location

For more detailed troubleshooting, check the application logs or open an issue on GitHub.

# License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

