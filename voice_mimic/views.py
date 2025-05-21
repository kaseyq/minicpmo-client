import base64
import json
import logging
import os
import numpy as np
import tempfile
from typing import Dict, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from starlette.responses import JSONResponse
from pydantic import BaseModel, field_validator
from common.audio_utils import AudioProcessor
from common.tcp_utils import send_request_to_server

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class RequestPayload(BaseModel):
    input_mimick_text: List[str]
    temperature: float = 0.3
    sample_rate: int = 16000
    max_new_tokens: int = 128
    sampling: bool = True
    use_tts_template: bool = True
    generate_audio: bool = True
    repeats: int = 1
    mimick_prompt: str = "As a professional voice actor, mimic the voice style, pitch, tone, and speech patterns from reference file for the next message."

    @field_validator('input_mimick_text')
    @classmethod
    def check_texts_non_empty(cls, v):
        if not v:
            raise ValueError("input_mimick_text must contain at least one string")
        return v

    @field_validator('repeats')
    @classmethod
    def check_repeats(cls, v):
        if v < 1:
            raise ValueError("repeats must be at least 1")
        return v

@router.post("/process_audio")
async def process_audio(
    audio_file: UploadFile = File(...),
    payload: str = Form(...)
):
    """Handle audio processing requests."""
    try:
        # Parse payload
        try:
            request_data = RequestPayload(**json.loads(payload))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")
        except ValueError as e:
            logger.error(f"Payload validation error: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

        params = {
            'sampling': request_data.sampling,
            'max_new_tokens': request_data.max_new_tokens,
            'use_tts_template': request_data.use_tts_template,
            'temperature': request_data.temperature,
            'generate_audio': request_data.generate_audio,
            'sample_rate': request_data.sample_rate
        }

        # Log parameters
        logger.info("Configuration parameters:")
        for key, value in params.items():
            logger.info(f"  {key}: {value}")
        logger.info(f"  repeats: {request_data.repeats}")

        # Save uploaded audio file temporarily
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file_path = os.path.join(temp_dir, audio_file.filename)
            with open(input_file_path, 'wb') as f:
                f.write(await audio_file.read())

            # Process audio
            cleaned_audio_path = AudioProcessor.process_audio(input_file_path, temp_dir)
            audio_input = AudioProcessor.load_and_validate_audio(
                cleaned_audio_path,
                sample_rate=params['sample_rate']
            )

            # Prepare messages
            messages = [{'role': 'user', 'content': [request_data.mimick_prompt, audio_input]}];
            for text in request_data.input_mimick_text:
                messages.append({'role': 'user', 'content': [text]});

            # Log messages
            logger.info("Messages to be sent to server:")
            for msg in messages:
                logger.info(f"  Role: {msg['role']}")
                logger.info(f"  Content: {[type(c) if isinstance(c, np.ndarray) else c for c in msg['content']]}")

            results = []
            for repeat in range(request_data.repeats):
                logger.info(f"Processing repeat {repeat + 1}/{request_data.repeats}")
                # Send request to server
                try:
                    response = await send_request_to_server(messages, params)
                except Exception as e:
                    logger.error(f"Failed to connect to model service on repeat {repeat + 1}: {str(e)}")
                    continue
                
                logger.info(f"Received response from model service (repeat {repeat + 1}): {json.dumps(response, default=str)}")

                if response.get('status') != 'success':
                    logger.error(f"Model service failed on repeat {repeat + 1}: {response}")
                    continue

                # Process response
                if 'files' in response:
                    audio_files = response['files']
                    # Try flexible key names
                    for i, text in enumerate(request_data.input_mimick_text):
                        for key in [f'output_audio_path_{i}', 'output_audio_path', f'audio_{i}', 'audio']:
                            if key in audio_files and isinstance(audio_files[key], dict) and 'data' in audio_files[key]:
                                audio_data = audio_files[key]['data']
                                if audio_data.startswith('base64:'):
                                    results.append({
                                        'text': text,
                                        'audio_data': f"data:audio/wav;base64,{audio_data[7:]}"
                                    })
                                    break
                            elif key in audio_files and isinstance(audio_files[key], str) and audio_files[key].startswith('base64:'):
                                results.append({
                                    'text': text,
                                    'audio_data': f"data:audio/wav;base64,{audio_files[key][7:]}"
                                })
                                break
                        else:
                            logger.warning(f"No valid audio data for prompt {i}: {text} (repeat {repeat + 1})")
                else:
                    logger.warning(f"No 'files' in response from model service (repeat {repeat + 1}): {response}")

            if not results:
                logger.error("No valid audio files in response across all repeats")
                raise HTTPException(status_code=500, detail="No valid audio files received; check model service response")

            # Return browser-readable payload
            return JSONResponse({
                'status': 'success',
                'files': results,
                'metadata': {'input_texts': request_data.input_mimick_text, 'repeats': request_data.repeats}
            })

    except Exception as e:
        logger.error(f"Error in processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
