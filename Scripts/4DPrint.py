"""

    ██╗  ██╗██████╗       ██████╗ ██████╗ ██╗███╗   ██╗████████╗
    ██║  ██║██╔══██╗      ██╔══██╗██╔══██╗██║████╗  ██║╚══██╔══╝
    ███████║██║  ██║█████╗██████╔╝██████╔╝██║██╔██╗ ██║   ██║
    ╚════██║██║  ██║╚════╝██╔═══╝ ██╔══██╗██║██║╚██╗██║   ██║
         ██║██████╔╝      ██║     ██║  ██║██║██║ ╚████║   ██║
         ╚═╝╚═════╝       ╚═╝     ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝   ╚═╝

4DPrint.py by Mr-C4T

This script automates 3D printing cycle by:
- Sending print jobs to a Creality 3D printer via WebSocket
- Waiting for the print to complete
- Triggering a so-arm100 episode replay with phospho API to clear the build plate
- Repeating the cycle as many times as needed

⚙️ powered by Phospho API server
🔗 Install & run the robot API server: https://docs.phospho.ai/installation

🦾 SO-ARM100: https://github.com/TheRobotStudio/SO-ARM100
🤖 Robot body: https://github.com/Mr-C4T/AB-SO-BOT

--- FUTURE IMPROVEMENT ---
TODO: Add support for other printers
TODO: Add option for AI inference instead of episode replay
TODO: Replace sleep with WebSocket status check
"""

import asyncio
import websockets
import json
import requests
import time
import argparse

async def send_gcode_command(printer_ip, printer_port, gcode_path, ws_timeout=10):
    print(f"🖨️ Connecting to Creality printer at {printer_ip}:{printer_port}")
    uri = f"ws://{printer_ip}:{printer_port}/"
    
    payload = {
        "method": 'set',
        'params': {
            'opGcodeFile': f'printprt:{gcode_path}'
        }
    }
    
    try:
        async with websockets.connect(uri, timeout=ws_timeout) as websocket:
            await websocket.send(json.dumps(payload))
            print(f'✉️ Sent payload: {json.dumps(payload)}')
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=ws_timeout)
                print(f'✅ Print command acknowledged: {response}')
            except asyncio.TimeoutError:
                print("❌ Error: No response from WebSocket server within the timeout period.")
    except Exception as e:
        print("❌ Error connecting to the WebSocket server:", e)

def start_print(printer_ip, printer_port, gcode_path, ws_timeout):
    asyncio.run(send_gcode_command(printer_ip, printer_port, gcode_path, ws_timeout))

def trigger_robot(robot_url, robot_id, episode_path, http_timeout=10):
    params = {"robot_id": robot_id}
    headers = {"Content-Type": "application/json"}
    payload = {"episode_path": episode_path}

    print(f'🦾 Sending robot command to retrieve print: {episode_path}')

    try:
        response = requests.post(
            robot_url,
            params=params,
            headers=headers,
            data=json.dumps(payload),
            timeout=http_timeout
        )
        if response.status_code == 200:
            print("✅ Robot task successful.")
            try:
                print("🤖 Response:", response.json())
            except json.JSONDecodeError:
                print("🤖 Response (non-JSON):", response.text)
        else:
            print(f"❌ Robot request failed with status code {response.status_code}.")
            print("🔎 Response:", response.text)

    except requests.exceptions.ConnectTimeout:
        print("⚠️ Could not connect to the robot — connection timed out.")
    except requests.exceptions.ConnectionError:
        print("⚠️ Connection error: Is the robot turned on and reachable at the given IP?")
    except requests.exceptions.RequestException as e:
        print("⚠️ An unexpected error occurred while contacting the robot.")
        print("🔍 Error:", e)


def main():
    parser = argparse.ArgumentParser(
        description="♾️ Automated 3D Printing loop using Robotics 🖨️ Creality Ender3-V3-KE + 🦾 SO-ARM100 via phosphobot",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--printer_ip", default="192.168.1.14", help="Creality printer IP address")
    parser.add_argument("--printer_port", type=int, default=9999, help="Creality WebSocket port")
    parser.add_argument("--gcode_path", default="/usr/data/printer_data/gcodes/M4_V1_PLA_9m.gcode", help="G-code file path on printer")
    parser.add_argument("--robot_url", default="http://192.168.1.27:8020/recording/play", help="Robot control API URL")
    parser.add_argument("--robot_id", type=int, default=0, help="Phosphobot robot ID")
    parser.add_argument("--episode_path", default="/root/phosphobot/recordings/lerobot_v2/example_dataset/data/chunk-000/episode_000000.parquet", help="Robot episode path")
    parser.add_argument("--wait_time", type=int, default=600, help="Time to wait for the print to finish (seconds)")
    parser.add_argument("--repeat", type=int, default=1, help="Number of print cycles to run")
    parser.add_argument("--ws_timeout", type=int, default=10, help="WebSocket response timeout (seconds)")
    parser.add_argument("--http_timeout", type=int, default=10, help="HTTP request timeout (seconds)")

    args = parser.parse_args()
    # Stylized ASCII Art with FILL + OUTLINE
    # Color Constants
    FG_FILL = "\033[0m"     
    FG_OUT = "\033[92m" # Bright Green 
    RESET = "\033[0m"
    print(f'''
    {FG_FILL}██{FG_OUT}╗  {FG_FILL}██{FG_OUT}╗{FG_FILL}██████{FG_OUT}╗{FG_FILL}       ██████{FG_OUT}╗{FG_FILL} ██████{FG_OUT}╗{FG_FILL} ██{FG_OUT}╗{FG_FILL}███{FG_OUT}╗{FG_FILL}   ██{FG_OUT}╗{FG_FILL}████████{FG_OUT}╗{FG_FILL}
    ██{FG_OUT}║{FG_FILL}  ██{FG_OUT}║{FG_FILL}██{FG_OUT}╔══{FG_FILL}██{FG_OUT}╗{FG_FILL}      ██{FG_OUT}╔══{FG_FILL}██{FG_OUT}╗{FG_FILL}██{FG_OUT}╔══{FG_FILL}██{FG_OUT}╗{FG_FILL}██{FG_OUT}║{FG_FILL}████{FG_OUT}╗{FG_FILL}  ██{FG_OUT}║╚══{FG_FILL}██{FG_OUT}╔══╝
    {FG_FILL}███████{FG_OUT}║{FG_FILL}██{FG_OUT}║{FG_FILL}  ██{FG_OUT}║{FG_FILL}█████{FG_OUT}╗{FG_FILL}██████{FG_OUT}╔╝{FG_FILL}██████{FG_OUT}╔╝{FG_FILL}██{FG_OUT}║{FG_FILL}██{FG_OUT}╔{FG_FILL}██{FG_OUT}╗{FG_FILL} ██{FG_OUT}║{FG_FILL}   ██{FG_OUT}║
    {FG_OUT}╚════{FG_FILL}██{FG_OUT}║{FG_FILL}██{FG_OUT}║  {FG_FILL}██{FG_OUT}║╚════╝{FG_FILL}██{FG_OUT}╔═══╝{FG_FILL} ██{FG_OUT}╔══{FG_FILL}██{FG_OUT}╗{FG_FILL}██{FG_OUT}║{FG_FILL}██{FG_OUT}║╚{FG_FILL}██{FG_OUT}╗{FG_FILL}██{FG_OUT}║{FG_FILL}   ██{FG_OUT}║
    {FG_FILL}     ██{FG_OUT}║{FG_FILL}██████{FG_OUT}╔╝      {FG_FILL}██{FG_OUT}║     {FG_FILL}██{FG_OUT}║  {FG_FILL}██{FG_OUT}║{FG_FILL}██{FG_OUT}║{FG_FILL}██{FG_OUT}║ ╚{FG_FILL}████{FG_OUT}║{FG_FILL}   ██{FG_OUT}║
    {FG_OUT}     ╚═╝╚═════╝       ╚═╝     ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝   ╚═╝{RESET}
    ''')
    
    print(f'\t🤖 {FG_OUT}Automated 3D Printing loop using Robotics{RESET} ♾️')

    for i in range(args.repeat):
        print(f'\n🔁 Print cycle {i + 1}/{args.repeat}')
        start_print(args.printer_ip, args.printer_port, args.gcode_path, args.ws_timeout)
        print(f'⏳ Waiting {args.wait_time // 60} minutes for print to complete...')
        time.sleep(args.wait_time) 
        trigger_robot(args.robot_url, args.robot_id, args.episode_path, args.http_timeout)


    print('\n✅ All print & pickup cycles completed.')

if __name__ == "__main__":
    main()
