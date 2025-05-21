import json
import logging
import os
import subprocess
from typing import Dict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioProcessingError(Exception):
    pass

class FileHandler:
    """Handles file-related operations like info retrieval and logging."""
    @staticmethod
    def get_audio_file_info(file_path: str) -> Dict:
        """Retrieve audio file information using ffprobe."""
        try:
            cmd = [
                "/usr/bin/ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(result.stdout)
            
            audio_stream = next((stream for stream in info.get('streams', []) if stream['codec_type'] == 'audio'), None)
            if not audio_stream:
                raise AudioProcessingError("No audio stream found in file")

            file_info = {
                'file_path': file_path,
                'file_size_bytes': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                'duration_seconds': float(info['format'].get('duration', 0)),
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0)),
                'bit_rate': int(info['format'].get('bit_rate', 0)),
                'format_name': info['format'].get('format_name', 'unknown')
            }
            return file_info
        except Exception as e:
            logger.error(f"Error getting audio file info for {file_path}: {str(e)}")
            raise AudioProcessingError(f"Failed to get audio file info: {str(e)}")

    @staticmethod
    def log_audio_file_info(file_path: str, stage: str):
        """Log audio file information for a given processing stage."""
        try:
            info = FileHandler.get_audio_file_info(file_path)
            logger.info(f"Audio file info at {stage}:")
            logger.info(f"  Path: {info['file_path']}")
            logger.info(f"  Size: {info['file_size_bytes']} bytes")
            logger.info(f"  Duration: {info['duration_seconds']:.2f} seconds")
            logger.info(f"  Sample Rate: {info['sample_rate']} Hz")
            logger.info(f"  Channels: {info['channels']}")
            logger.info(f"  Bit Rate: {info['bit_rate']} bps")
            logger.info(f"  Format: {info['format_name']}")
        except AudioProcessingError as e:
            logger.error(f"Failed to log audio file info at {stage}: {str(e)}")
            raise