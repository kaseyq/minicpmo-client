import json
import logging
import asyncio
import socket
import base64
import numpy as np
from typing import Dict, List
import os
from common import config  # Import configuration

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_request_to_server(messages: List[Dict], params: Dict) -> Dict:
    """Send a request to the model service asynchronously."""
    model_service_config = config.get('model_service', {})
    host = model_service_config.get('host', 'localhost')
    port = model_service_config.get('port', 9999)
    timeout = model_service_config.get('timeout', 300.0)
    
    try:
        logger.info(f"Connecting to model service at {host}:{port}")
        async with asyncio.timeout(timeout):
            reader, writer = await asyncio.open_connection(host, port)
        
        # Prepare request
        for msg in messages:
            for i, item in enumerate(msg['content']):
                if isinstance(item, np.ndarray):
                    msg['content'][i] = f"base64:{base64.b64encode(item.tobytes()).decode('utf-8')}"

        request = {'messages': messages, 'params': params}
        logger.debug(f"Sending request: {json.dumps(request, default=str)[:200]}...")
        writer.write(json.dumps(request).encode('utf-8'))
        await writer.drain()

        # Receive response
        data = b""
        while True:
            chunk = await reader.read(65536)
            data += chunk
            try:
                json.loads(data.decode('utf-8'))
                break
            except json.JSONDecodeError:
                if not chunk:
                    logger.error("Incomplete JSON response from server")
                    raise ValueError("Incomplete JSON response from server")
                continue

        writer.close()
        await writer.wait_closed()

        response = json.loads(data.decode('utf-8'))
        logger.debug(f"Received response: {json.dumps(response, default=str)[:200]}...")
        
        if 'error' in response:
            logger.error(f"Model service error: {response['error']}")
            raise RuntimeError(f"Server error: {response['error']}")
        
        return response
    except asyncio.TimeoutError:
        logger.error(f"Request to model service at {host}:{port} timed out after {timeout} seconds")
        raise RuntimeError(f"Model service timeout after {timeout} seconds")
    except Exception as e:
        logger.error(f"Error communicating with model service at {host}:{port}: {str(e)}")
        raise