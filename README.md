# MiniCPM-o Frontend

MiniCPM-o Frontend is a FastAPI-based web application that provides voice mimicry and photo description functionalities. It serves as a client interface to interact with a backend model service, processing audio and image inputs to generate mimicked audio outputs or detailed image descriptions.

## Features

- **Voice Mimicry**: Upload an audio file and text prompts to generate audio that mimics the voice style, pitch, and tone of the reference audio.
- **Photo Description**: Upload an image and provide prompts to receive textual descriptions of the image content.
- **CLI and Web Interface**: Supports both command-line interface (CLI) execution and a web-based UI for user interaction.
- **Audio Processing**: Utilizes FFmpeg and Librosa for robust audio cleaning and validation.
- **Image Processing**: Supports PNG and JPEG images with resizing and base64 encoding for efficient handling.
- **Asynchronous Communication**: Communicates with a backend model service via TCP for processing requests.

## Project Structure

```
minicpmo-client/
├── common/                   # Utility modules for audio, image, and TCP operations
├── describe_photo/           # Photo description endpoint and views
├── voice_mimic/              # Voice mimicry endpoint and views
├── static/                   # Static files (HTML, JS, CSS, icons)
├── templates/                # (Empty in provided structure, possibly for future use)
├── __main__.py               # Main application entry point
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

## Requirements

- Python 3.8+
- FFmpeg (for audio processing)
- Dependencies listed in `requirements.txt`:
  - fastapi
  - uvicorn
  - numpy
  - librosa
  - pillow
  - pydantic

## Installation

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd minicpmo-client
   ```

2. **Set Up a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install FFmpeg**:
   - On Ubuntu: `sudo apt-get install ffmpeg`
   - On macOS: `brew install ffmpeg`
   - On Windows: Download from [FFmpeg website](https://ffmpeg.org/download.html) and add to PATH.

## Usage

### Running the Web Server

Start the FastAPI server to access the web interface:

```bash
python -m minicpmo_client
```

The server will run on `http://0.0.0.0:8000`. Open `http://localhost:8000` in a browser to access the landing page with tabs for voice mimicry and photo description.

### CLI Usage

#### Voice Mimicry
To mimic a voice from an audio file and generate audio for given text prompts:

```bash
python -m minicpmo_client --mode voice_mimic --input_file path/to/audio.wav --texts "Hello, world!" "How are you?"
```

Options:
- `--input_file`: Path to the reference audio file (WAV format).
- `--texts`: List of text prompts to be spoken in the mimicked voice.
- `--temperature`: Sampling temperature (default: 0.3).
- `--sample_rate`: Audio sample rate (default: 16000 Hz).
- `--max_new_tokens`: Maximum new tokens for generation (default: 128).

Output audio files are saved as `output_0.wav`, etc., in the current directory.

#### Photo Description
To describe an image with custom prompts:

```bash
python -m minicpmo_client --mode describe_photo --image_file path/to/image.jpg --prompts "Describe the scene." "What objects are present?"
```

Options:
- `--image_file`: Path to the input image (PNG or JPEG).
- `--prompts`: List of description prompts.
- `--temperature`: Sampling temperature (default: 0.3).
- `--max_new_tokens`: Maximum new tokens for generation (default: 128).

Output descriptions are saved as `output_0.txt`, etc., in the current directory.

### Web Interface

- **Voice Mimicry**: Navigate to `/voice-mimic`, upload an audio file, enter text prompts, and submit to receive mimicked audio.
- **Photo Description**: Navigate to `/describe-photo`, upload an image, enter prompts, and submit to receive descriptions.

## Configuration

- **Backend Model Service**: The application communicates with a model service at `localhost:9999` by default. Update the `host` and `port` in `tcp_utils.py` if needed.
- **Static Files**: Served from the `static/` directory, including HTML, JavaScript, CSS, and favicon.
- **Logging**: Configured to output INFO-level logs for debugging and monitoring.

## Development

To contribute or modify the project:

1. Add new endpoints in `voice_mimic/views.py` or `describe_photo/views.py`.
2. Update frontend code in `static/` (e.g., `mimic_voice.js`, `describe_photo.js`).
3. Ensure FFmpeg is available in the system PATH for audio processing.
4. Test CLI commands and web interface thoroughly.

## Notes

- The backend model service must be running and accessible for processing requests.
- Audio files must be in WAV format for voice mimicry.
- Images must be in PNG or JPEG format for photo description.
- Temporary files are managed using `tempfile.TemporaryDirectory` to avoid disk clutter.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details (not provided in the current structure; consider adding one).