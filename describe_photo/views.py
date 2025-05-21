import json
import logging
import tempfile
from typing import Dict, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from starlette.responses import JSONResponse
from pydantic import BaseModel, field_validator
from common.image_utils import ImageProcessor
from common.tcp_utils import send_request_to_server

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class RequestPayload(BaseModel):
    prompts: List[str]
    temperature: float = 0.3
    max_new_tokens: int = 128
    repeats: int = 1

    @field_validator('prompts')
    @classmethod
    def check_prompts_non_empty(cls, v):
        if not v:
            raise ValueError("prompts must contain at least one string")
        return v

    @field_validator('repeats')
    @classmethod
    def check_repeats(cls, v):
        if v < 1:
            raise ValueError("repeats must be at least 1")
        return v

@router.post("/process_photo")
async def process_photo(
    image_file: UploadFile = File(...),
    payload: str = Form(...)
):
    """Handle photo description requests."""
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
            'temperature': request_data.temperature,
            'max_new_tokens': request_data.max_new_tokens
        }

        # Log parameters
        logger.info("Configuration parameters:")
        for key, value in params.items():
            logger.info(f"  {key}: {value}")
        logger.info(f"  repeats: {request_data.repeats}")

        # Save uploaded image file temporarily
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file_path = os.path.join(temp_dir, image_file.filename)
            with open(input_file_path, 'wb') as f:
                f.write(await image_file.read())

            # Process image
            image_base64 = ImageProcessor.process_image(input_file_path)

            # Prepare messages
            messages = [{'role': 'user', 'content': ["Describe the image.", image_base64]}]
            for prompt in request_data.prompts:
                messages.append({'role': 'user', 'content': [prompt]})

            # Log messages
            logger.info("Messages to be sent to server:")
            for msg in messages:
                logger.info(f"  Role: {msg['role']}")
                logger.info(f"  Content: {[c[:100] + '...' if len(c) > 100 else c for c in msg['content']]}")

            results = []
            for repeat in range(request_data.repeats):
                logger.info(f"Processing repeat {repeat + 1}/{request_data.repeats}")
                # Send request to server
                try:
                    response = await send_request_to_server(messages, params)
                except Exception as e:
                    logger.error(f"Failed to connect to model service on repeat {repeat + 1}: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Model service error: {str(e)}")
                
                logger.info(f"Received response from model service (repeat {repeat + 1}): {response}")

                if response.get('status') != 'success':
                    logger.error(f"Model service failed on repeat {repeat + 1}: {response}")
                    raise RuntimeError(f"Server processing failed: {response}")

                if 'response' not in response:
                    logger.error(f"No response data received from model service (repeat {repeat + 1})")
                    raise RuntimeError("No response data received")

                descriptions = response['response'] if isinstance(response['response'], list) else [response['response']]
                for i, (prompt, desc) in enumerate(zip(request_data.prompts, descriptions)):
                    results.push({'prompt': prompt, 'description': desc})

            # Return browser-readable payload
            return JSONResponse({
                'status': 'success',
                'descriptions': results,
                'metadata': {'prompts': request_data.prompts, 'repeats': request_data.repeats}
            })

    except Exception as e:
        logger.error(f"Error in processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))