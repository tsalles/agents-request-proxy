import os
import json
import requests
from fastapi import FastAPI, Request, HTTPException, Depends, Header, Security
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv

import logging

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Create a logger
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

# Load mappings from environment variable
MAPPINGS_ENV = os.getenv("ROUTER_MAPPINGS", '{}')
try:
    mappings = json.loads(MAPPINGS_ENV).get("mappings", [])
    PATH_MAPPING = {k: v for mapping in mappings for k, v in mapping.items()}
    print('Loading the following mappings:')
    for k, v in PATH_MAPPING.items():
        print(f"  > {k} -> {v}")
except json.JSONDecodeError:
    PATH_MAPPING = {}

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def validate_api_key(api_key: str = Security(api_key_header)):
    if api_key !=  os.getenv("API_KEY", "NOT DEFINED"):
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

@app.api_route("/agent/{path:path}", methods=["GET", "POST"])
async def agent(path: str, request: Request, api_key: str = Depends(validate_api_key)):
    base_url = PATH_MAPPING.get(path)
    if not base_url:
        raise HTTPException(status_code=404, detail="Path not found")

    target_url = f"{base_url}/acs/llms/agent"

    try:
        body = await request.json()
        if 'data' in body:
            if 'context' in body['data']:
                if 'messages' not in body['data']['context']:
                    body['data']['context']['messages'] = []
                if 'system' in body['data']['context']:
                    if 'dialog_turn_counter' in body['data']['context']['system']:
                        body['data']['context']['system']['dialog_turn_counter'] = int(body['data']['context']['system']['dialog_turn_counter'])
                else:
                     body['data']['context']['system']['dialog_turn_counter'] = 0

        response = requests.request(
            method=request.method,
            url=target_url,
            headers={key: value for key, value in request.headers.items() if key.lower() != "host"},
            data=json.dumps(body),
            params=request.query_params
        )
        result = response.json()
        if 'data' in result:
            if 'output' in result['data'] and 'text' in result['data']['output']:
                result['data']['output']['text'] = '\n'.join(result['data']['output']['text'])
        logging.info(f'{target_url} {body} {result}')
        return result
    except requests.RequestException as e:
        logging.info(f'ERROR: {request}')
        raise HTTPException(status_code=500, detail=f"Error forwarding request: {str(e)}")

@app.api_route("/context-retrieval/{path:path}", methods=["GET", "POST"])
async def context_retrieval(path: str, request: Request, api_key: str = Depends(validate_api_key)):
    base_url = PATH_MAPPING.get(path)
    if not base_url:
        raise HTTPException(status_code=404, detail="Path not found")

    target_url = f"{base_url}/acs/llms/contextual_retrieval"

    try:
        logging.info(f"Forwarding: {request.method} {target_url}")
        response = requests.request(
            method=request.method,
            url=target_url,
            headers={key: value for key, value in request.headers.items() if key.lower() != "host"},
            data=await request.body(),
            params=request.query_params
        )
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error forwarding request: {str(e)}")


@app.get("/health/liveness")
async def liveness_probe():
    return JSONResponse(
        content={"status": "alive"},
        status_code=status.HTTP_200_OK,
    )


@app.get("/health/readiness")
async def readiness_probe():
    return JSONResponse(
        content={"status": "ready"},
        status_code=status.HTTP_200_OK,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
