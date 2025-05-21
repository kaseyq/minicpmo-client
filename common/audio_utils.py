import os
import logging
import subprocess
import numpy as np
import librosa
from .file_utils import FileHandler, AudioProcessingError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioProcessor:
    """Handles audio processing operations."""
    @staticmethod
    def process_audio(input_path: str, temp_dir: str) -> str:
        """Process input audio file with FFmpeg cleaning steps."""
        try:
            FileHandler.log_audio_file_info(input_path, "input stage")
            tmp1_file = os.path.join(temp_dir, 'cleaned1.wav')
            tmp2_file = os.path.join(temp_dir, 'cleaned2.wav')

            cmd1 = [
                "/usr/bin/ffmpeg", "-err_detect", "ignore_err",
                "-i", input_path, "-y", "-c", "copy", tmp1_file
            ]
            logger.info(f"Running FFmpeg command: {' '.join(cmd1)}")
            result1 = subprocess.run(cmd1, capture_output=True, text=True)
            if result1.returncode != 0:
                raise AudioProcessingError(f"FFmpeg error detection failed: {result1.stderr}")

            FileHandler.log_audio_file_info(tmp1_file, "after error detection pass")

            cmd2 = [
                "/usr/bin/ffmpeg", "-y", "-i", tmp1_file,
                "-af", "highpass=f=200, lowpass=f=3000", tmp2_file
            ]
            logger.info(f"Running FFmpeg command: {' '.join(cmd2)}")
            result2 = subprocess.run(cmd2, capture_output=True, text=True)
            if result2.returncode != 0:
                raise AudioProcessingError(f"FFmpeg filtering failed: {result2.stderr}")

            FileHandler.log_audio_file_info(tmp2_file, "after filtering pass")
            return tmp2_file
        except Exception as e:
            logger.error(f"Audio processing error: {str(e)}")
            raise

    @staticmethod
    def load_and_validate_audio(file_path: str, sample_rate: int = 16000) -> np.ndarray:
        """Load and validate audio file."""
        try:
            audio, sr = librosa.load(file_path, sr=sample_rate, mono=True)
            if len(audio.shape) != 1:
                raise AudioProcessingError("Audio must be mono")
            if not np.isfinite(audio).all():
                raise AudioProcessingError("Audio contains invalid values")
            return audio
        except Exception as e:
            logger.error(f"Audio loading error: {str(e)}")
            raise
