import json
import time
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

def stream_from_file(filename: str):
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f) # This turns the whole file into a Python dictionary

    # 1. Yield the Init (using the game_info from the file)
    roles = {pid: info['role'] for pid, info in data['game_info'].items()}
    yield json.dumps({"type": "init", "actual_roles": roles}) + "\n"
    time.sleep(1)

    # 2. Loop through the steps automatically
    for step in data['steps']:
        yield json.dumps(step) + "\n"
        time.sleep(0.5) # Speed it up so you don't have to wait forever

    # 3. Yield the Final (using the rewards from the file)
    yield json.dumps({
        "type": "final", 
        "rewards": data['rewards'], 
        "winners": "Mafia" if data['rewards']["1"] == 1 else "Village"
    }) + "\n"

@app.get("/start-game")
async def start_game():
    # Just make sure your JSON file is in the same folder!
    return StreamingResponse(stream_from_file("game_log.json"), media_type="application/x-ndjson")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)