import asyncio
import websockets
import subprocess
import json
import logging

# إعداد الـ logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('matilda_bridge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# قائمة الأوامر المسموح بيها (للأمان)
ALLOWED_COMMANDS = [
    "cd ~/MatildaOS/NeonOS/ && source venv/bin/activate && python3 MatildaDaemon.py",
    "ps aux | grep python3",
    "cat ~/MatildaOS/NeonOS/grok_output.log",
    "cat ~/MatildaOS/NeonOS/grok_errors.log",
    "killall -9 python3"
]

async def handle_connection(websocket, path):
    logger.info("New WebSocket connection established")
    try:
        async for message in websocket:
            logger.info(f"Received message: {message}")
            try:
                # تحليل الرسالة (نتوقع إنها JSON)
                data = json.loads(message)
                command = data.get("command", "")

                # التحقق من الأمر (للأمان)
                if command not in ALLOWED_COMMANDS:
                    response = {"status": "error", "message": f"Command '{command}' not allowed"}
                    await websocket.send(json.dumps(response))
                    logger.warning(f"Unauthorized command: {command}")
                    continue

                # تنفيذ الأمر
                logger.info(f"Executing command: {command}")
                process = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30  # مهلة 30 ثانية للأمر
                )

                # إرجاع النتيجة
                response = {
                    "status": "success",
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                    "returncode": process.returncode
                }
                await websocket.send(json.dumps(response))
                logger.info(f"Command executed: {command}, Return code: {process.returncode}")

            except json.JSONDecodeError:
                response = {"status": "error", "message": "Invalid JSON format"}
                await websocket.send(json.dumps(response))
                logger.error("Invalid JSON format in message")
            except subprocess.TimeoutExpired:
                response = {"status": "error", "message": "Command timed out"}
                await websocket.send(json.dumps(response))
                logger.error(f"Command timed out: {command}")
            except Exception as e:
                response = {"status": "error", "message": str(e)}
                await websocket.send(json.dumps(response))
                logger.error(f"Error executing command: {str(e)}")

    except websockets.exceptions.ConnectionClosed:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

# بدء السيرفر
async def main():
    port = 8000  # Render بيستخدم الـ port 8000 افتراضيًا
    logger.info(f"Starting WebSocket server on port {port}")
    server = await websockets.serve(handle_connection, "0.0.0.0", port)
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
