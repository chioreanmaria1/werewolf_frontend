import gradio as gr
import re
import requests
import json

def run_streamed_game():
    url = "http://127.0.0.1:8000/start-game"
    # We use 'stream=True' to keep the connection open for the whole game
    with requests.get(url, stream=True) as r:
        for line in r.iter_lines():
            if line:
                # Convert raw text from the server back into a Python dictionary
                yield json.loads(line.decode('utf-8'))

# Initialize player data with pending roles and alive status
players_data = [
    {"id": i, "name": f"P{i}", "role": "Pending...", "status": "Alive", "active": False}
    for i in range(6)
]

def get_player_display(p):
    is_dead = p["status"] == "Dead"
    icon = "🟢 (Active)" if p["active"] else ""
    status_text = "💀 DEAD" if is_dead else "Alive"
    
    line_color = "#ff4b4b" if is_dead else "#0088ff"
    div_color = "#ff4b4b" if is_dead else "#0088ff"
    text_color = "red" if is_dead else "#00eeff"
    
    return f"""
    <div style="border-top: 3px solid {line_color}; padding-top: 12px; margin-top: 10px; background-color: {div_color}; border-radius: 5px; padding: 10px;">
        <h3 style="margin: 0;">{p['name']} {icon}</h3>
        <p style="margin: 5px 0; color: red if is_dead else 'black'"><i>Role:</i> {p['role']} | <i>Status:</i> {status_text}</p>
    </div>
    """

#logic to run the game and stream updates to the UI
def start_ui(chat_history):
    
    for step in run_streamed_game():
        
        # --- Handle Initialization ---
        if "type" in step and step["type"] == "init": 
            actual_roles = step.get("actual_roles", {})
            for p in players_data:
                # CHANGE: JSON keys are always strings (e.g., "0"). 
                # Our p["id"] is an integer (0). We must cast to string to match them.
                p_id_str = str(p["id"])
                if p_id_str in actual_roles:
                    p["role"] = actual_roles[p_id_str]
            
            yield [get_player_display(p) for p in players_data] + [chat_history, "🌑 Game Started!", "Roles assigned."]
            continue

        # --- Handle Game End ---
        if "type" in step and step["type"] == "final":
            # CHANGE: Updated string formatting to clearly show the winners from the server data.
            chat_history.append({"role": "assistant", "content": f"**GAME OVER** - Winners: {step['winners']}"})
            yield [get_player_display(p) for p in players_data] + [chat_history, "🌑 Game Over", f"Rewards: {step['rewards']}"]
            break

        # --- Handle Regular Steps ---
        player_id = step["player_id"]
        observation = step["observation"]
        alive_ids = step.get("alive_ids", [])
        action = step["action"]

        matches = re.findall(r'\[GAME\](.*)', observation) 
        phase = matches[-1].strip() if matches else "Phase: Ongoing"

        for p in players_data:
            p["active"] = (p["id"] == player_id)
            p["status"] = "Alive" if p["id"] in alive_ids else "Dead"
    
        player_name = players_data[player_id]["name"]
        chat_history.append({"role": "assistant", "content": f"**{player_name}**: {action}"})

        # CHANGE: We yield every piece of information to Gradio. 
        # Because run_streamed_game() is slow (0.5s per line), 
        # the UI updates one step at a time, creating the "live" effect.
        yield [get_player_display(p) for p in players_data] + [
            chat_history, f"<h1 style='text-align: center;'>🌑 {phase}</h1>", observation
        ]

with gr.Blocks() as demo:
    status_header = gr.Markdown("<h1 style='text-align: center;'>🌑 Press start</h1>")

    player_ui = []
    with gr.Row():
        for i in range(3):
            player_ui.append(gr.Markdown(get_player_display(players_data[i])))
    with gr.Row():
        for i in range(3, 6):
            player_ui.append(gr.Markdown(get_player_display(players_data[i])))

    gr.HTML("<hr>")
    with gr.Row():
        chat_ui = gr.Chatbot(label="Game Log", height=400, scale=2)
        obs_ui = gr.Textbox(label="What the agent observes", interactive=False, lines=15, scale=1)

    start_btn = gr.Button("▶️ Start Visualizer", variant="primary")
    
    start_btn.click(
        fn=lambda: gr.update(visible=False), outputs=[start_btn]
    ).then(
        fn=start_ui, inputs=[chat_ui], outputs=player_ui + [chat_ui, status_header, obs_ui]
    )

if __name__ == "__main__":
    demo.launch()