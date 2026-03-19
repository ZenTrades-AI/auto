import os

# CRITICAL: Tell Playwright it must look for the browsers inside our local project directory, 
# because Render deletes the default ~/.cache folder where they normally live!
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/render/project/src/pw-browsers"

import queue
from dotenv import load_dotenv
from flask import Flask, request, render_template_string, jsonify
import logging
import threading

import sys
sys.stdout.reconfigure(line_buffering=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# We call it both app and flask_app so Gunicorn won't break
app = Flask(__name__)
flask_app = app

if "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    logger.handlers = gunicorn_logger.handlers
    logger.setLevel(gunicorn_logger.level)

# ==========================================
# 1. Create a Global Queue for Requests
# ==========================================
task_queue = queue.Queue()

def background_worker():
    """
    This function runs continuously in the background.
    It waits for a task to be added to the queue, processes it, and then waits for the next.
    """
    from automation import run_browser
    
    while True:
        # This will block and wait until a new item is added to the queue
        data = task_queue.get()
        logger.info(f"⚙️ Starting queued automation task for: {data}")
        
        try:
            # Run the automation synchronously (one at a time)
            run_browser(data)
        except Exception as e:
            logger.error(f"❌ Error during background task: {e}")
        finally:
            # Mark the task as done so the queue knows it can move on
            task_queue.task_done()
            logger.info("✅ Task completed. Waiting for the next one in queue...")

# ==========================================
# 2. Worker Thread Management
# ==========================================
worker_thread = None
worker_lock = threading.Lock()

def start_worker_if_needed():
    global worker_thread
    with worker_lock:
        if worker_thread is None or not worker_thread.is_alive():
            worker_thread = threading.Thread(target=background_worker, daemon=True)
            worker_thread.start()
            logger.info("🧵 Background worker thread started inside worker context.")

# Simple HTML Form template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Customer Data Extension</title>
    <style>
        body { font-family: 'Inter', Arial, sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: #fff; padding: 25px 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); width: 100%; max-width: 450px; }
        h2 { text-align: center; color: #333; margin-top: 0; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #555; font-weight: bold; }
        input[type="text"] { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; font-size: 14px; transition: border-color 0.3s; }
        input[type="text"]:focus { border-color: #0056b3; outline: none; }
        button { width: 100%; padding: 12px; background-color: #007bff; color: white; border: none; border-radius: 4px; font-size: 16px; font-weight: bold; cursor: pointer; transition: background-color 0.3s; }
        button:hover { background-color: #0056b3; }
        .message { margin-top: 15px; text-align: center; color: green; font-weight: bold; display: none; }
        .error-message { color: red; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Delete Customer</h2>
        <form id="triggerForm">
            <div class="form-group">
                <label for="name">Name</label>
                <input type="text" id="name" name="name" placeholder="Optional">
            </div>
            <div class="form-group">
                <label for="phone">Phone</label>
                <input type="text" id="phone" name="phone" placeholder="Optional">
            </div>
            <div class="form-group">
                <label for="address">Address</label>
                <input type="text" id="address" name="address" placeholder="Optional">
            </div>
            <div class="form-group">
                <label for="customer_id">Customer ID (Required)</label>
                <input type="text" id="customer_id" name="customer_id" required placeholder="Enter the Customer ID...">
            </div>
            <button type="submit">Run Browser Automation</button>
        </form>
        <div id="statusMessage" class="message">Task added to queue!</div>
        <div id="errorMessage" class="message error-message">An error occurred!</div>
    </div>
    
    <script>
        document.getElementById('triggerForm').addEventListener('submit', function(e) {
            e.preventDefault();
            console.log("🟢 Submit button clicked!");
            
            const btn = document.querySelector('button');
            btn.disabled = true;
            btn.innerText = 'Triggering...';
            
            const data = {
                name: document.getElementById('name').value,
                phone: document.getElementById('phone').value,
                address: document.getElementById('address').value,
                customer_id: document.getElementById('customer_id').value
            };
            
            console.log("📦 Form data gathered:", data);
            console.log("🚀 Sending POST request to backend...");
            
            fetch('/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(response => {
                console.log("📥 Received response from server:", response);
                if(response.ok) {
                    const msg = document.getElementById('statusMessage');
                    msg.style.display = 'block';
                    setTimeout(() => { msg.style.display = 'none'; }, 5000);
                    document.getElementById('triggerForm').reset();
                } else {
                    throw new Error('Server returned an error');
                }
            }).catch(error => {
                const msg = document.getElementById('errorMessage');
                msg.style.display = 'block';
                setTimeout(() => { msg.style.display = 'none'; }, 5000);
            }).finally(() => {
                btn.disabled = false;
                btn.innerText = 'Run Browser Automation';
            });
        });
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/run", methods=["POST"])
def run_automation():
    data = request.json
    logger.info(f"📩 Received UI manual trigger with data: {data}")
    print(f"📩 PRINT: Received UI trigger: {data}", flush=True)
    
    # Ensure the background thread is running in this specific Gunicorn worker process
    start_worker_if_needed()

    # ==========================================
    # 3. Add the request to the Queue instead of starting a new thread
    # ==========================================
    task_queue.put(data)
    
    # We can also let the user know their position in the queue
    queue_size = task_queue.qsize()
    
    return jsonify({
        "status": "Task added to queue", 
        "queue_position": queue_size 
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)