import argparse
import sys
import uvicorn
import json
import logging
import tempfile
import numpy as np
import librosa
import os
from datetime import datetime
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.responses import Response as StarletteResponse
from voice_mimic.views import router as voice_mimic_router
from describe_photo.views import router as describe_photo_router
from common.file_utils import FileHandler, AudioProcessingError
from common.audio_utils import AudioProcessor
from common.image_utils import ImageProcessor, ImageProcessingError
from common.tcp_utils import send_request_to_server

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MiniCPM-o Frontend")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers with prefixes
app.include_router(voice_mimic_router, prefix="/voice-mimic")
app.include_router(describe_photo_router, prefix="/describe-photo")

@app.get("/")
async def serve_index():
    """Serve the landing page with tabs."""
    return FileResponse("static/index.html")

@app.get("/favicon.ico")
async def favicon():
    """Serve favicon.ico from static directory."""
    favicon_path = os.path.join("static", "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return StarletteResponse(status_code=204)  # No Content if favicon is missing

def run_voice_mimic_cli(args):
    """Run voice mimic CLI logic."""
    params = {
        'sampling': args.sampling,
        'max_new_tokens': args.max_new_tokens,
        'use_tts_template': args.use_tts_template,
        'temperature': args.temperature,
        'generate_audio': args.generate_audio,
        'sample_rate': args.sample_rate
    }

    logger.info("Configuration parameters:")
    for key, value in params.items():
        logger.info(f"  {key}: {value}")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file_path = args.input_file
            if not os.path.exists(input_file_path):
                raise AudioProcessingError(f"Input file not found: {input_file_path}")

            cleaned_audio_path = AudioProcessor.process_audio(input_file_path, temp_dir)
            audio_input = AudioProcessor.load_and_validate_audio(
                cleaned_audio_path,
                sample_rate=params['sample_rate']
            )

            mimick_prompt = "As a professional voice actor, mimick the voice style, pitch, tone, and speech patterns from reference file for the next message."
            messages = [{'role': 'user', 'content': [mimick_prompt, audio_input]}]
            for text in args.texts:
                say_this_prompt = f"Say this \"{text}\""
                messages.append({'role': 'user', 'content': [say_this_prompt]})

            logger.info("Messages to be sent to server:")
            for msg in messages:
                logger.info(f"  Role: {msg['role']}")
                logger.info(f"  Content: {[type(c) if isinstance(c, np.ndarray) else c for c in msg['content']]}")

            response = asyncio.run(send_request_to_server(messages, params))
            
            if response.get('status') != 'success':
                raise RuntimeError(f"Server processing failed: {response}")

            if 'files' not in response or not response['files'].get('output_audio_path'):
                raise RuntimeError("No response data received")

            results = []
            audio_data = response['files']['output_audio_path']['data']
            if not audio_data.startswith('base64:'):
                raise RuntimeError("Response is not base64-encoded audio")
            output_path = f"output_0.wav"
            with open(output_path, 'wb') as f:
                f.write(base64.b64decode(audio_data[7:]))
                
            results.append({
                'text': args.texts[0],
                'output_path': output_path
            })

            logger.info("Processing complete:")
            for result in results:
                logger.info(f"  Text: {result['text']}")
                logger.info(f"  Saved to: {result['output_path']}")

    except Exception as e:
        logger.error(f"Error in CLI execution: {str(e)}")
        raise

def run_describe_photo_cli(args):
    """Run photo description CLI logic."""
    params = {
        'temperature': args.temperature,
        'max_new_tokens': args.max_new_tokens
    }

    logger.info("Configuration parameters:")
    for key, value in params.items():
        logger.info(f"  {key}: {value}")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file_path = args.image_file
            if not os.path.exists(input_file_path):
                raise ImageProcessingError(f"Image file not found: {input_file_path}")

            image_base64 = ImageProcessor.process_image(input_file_path)

            messages = [{'role': 'user', 'content': ["Describe the image.", image_base64]}]
            for prompt in args.prompts:
                messages.append({'role': 'user', 'content': [prompt]})

            logger.info("Messages to be sent to server:")
            for msg in messages:
                logger.info(f"  Role: {msg['role']}")
                logger.info(f"  Content: {[c[:100] + '...' if len(c) > 100 else c for c in msg['content']]}")

            response = asyncio.run(send_request_to_server(messages, params))
            
            if response.get('status') != 'success':
                raise RuntimeError(f"Server processing failed: {response}")

            if 'response' not in response:
                raise RuntimeError("No response data received")

            descriptions = response['response'] if isinstance(response['response'], list) else [response['response']]
            results = []
            for i, (prompt, desc) in enumerate(zip(args.prompts, descriptions)):
                output_path = f"output_{i}.txt"
                with open(output_path, 'w') as f:
                    f.write(f"# Prompt: {prompt}\n# Timestamp: {datetime.now().isoformat()}\n\n{desc}")
                results.append({
                    'prompt': prompt,
                    'description': desc,
                    'output_path': output_path
                })

            logger.info("Processing complete:")
            for result in results:
                logger.info(f"  Prompt: {result['prompt']}")
                logger.info(f"  Description: {result['description'][:100]}...")
                logger.info(f"  Saved to: {result['output_path']}")

    except Exception as e:
        logger.error(f"Error in CLI execution: {str(e)}")
        raise

def parse_args():
    parser = argparse.ArgumentParser(description="MiniCPM-o Frontend CLI")
    parser.add_argument("--mode", choices=["voice_mimic", "describe_photo"], help="Frontend mode")
    parser.add_argument("--input_file", type=str, help="Path to input audio file (voice_mimic mode)")
    parser.add_argument("--texts", type=str, nargs='+', help="List of text prompts (voice_mimic mode)")
    parser.add_argument("--temperature", type=float, default=0.3, help="Sampling temperature")
    parser.add_argument("--sample_rate", type=int, default=16000, help="Audio sample rate (voice_mimic mode)")
    parser.add_argument("--max_new_tokens", type=int, default=128, help="Maximum new tokens")
    parser.add_argument("--sampling", action="store_true", default=True, help="Enable sampling")
    parser.add_argument("--use_tts_template", action="store_true", default=True, help="Use TTS template (voice_mimic mode)")
    parser.add_argument("--generate_audio", action="store_true", default=True, help="Generate audio output (voice_mimic mode)")
    parser.add_argument("--image_file", type=str, help="Path to input image file (describe_photo mode)")
    parser.add_argument("--prompts", type=str, nargs='+', help="List of description prompts (describe_photo mode)")
    return parser

def main():
    parser = parse_args()
    # If no arguments provided, run as server
    if len(sys.argv) == 1:
        uvicorn.run(app, host="0.0.0.0", port=8000)
        return

    args = parser.parse_args()

    if args.mode == "voice_mimic":
        if not args.input_file or not args.texts:
            parser.error("voice_mimic mode requires --input_file and --texts")
        run_voice_mimic_cli(args)
    elif args.mode == "describe_photo":
        if not args.image_file or not args.prompts:
            parser.error("describe_photo mode requires --image_file and --prompts")
        run_describe_photo_cli(args)
    else:
        parser.error("Missing required argument: --mode")

if __name__ == "__main__":
    main()
