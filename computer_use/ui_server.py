"""
Minimal Single-File Web UI Server for Autonomous Computer Use Agent.
Zero external dependencies (uses standard library http.server).
Serves a clean HTML interface with an input box, mode selectors, and live agent log stream.
"""

import http.server
import json
import threading
import time
from urllib.parse import parse_qs, urlparse
from agent import GemmaContinuousAgent
import browser_tools

HOST = "127.0.0.1"
PORT = 8080

logs = []
agent_lock = threading.Lock()
agent_running = False

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>browser use</title>
  <style>
    body {
      font-family: monospace;
      background: #fbfbfb;
      color: #222;
      max-width: 800px;
      margin: 40px auto;
      padding: 0 20px;
      line-height: 1.5;
    }
    h2 { margin-bottom: 4px; }
    p { margin-top: 0; color: #666; font-size: 14px; }
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 20px;
    }
    textarea {
      width: 100%;
      height: 70px;
      font-family: inherit;
      font-size: 14px;
      padding: 8px;
      box-sizing: border-box;
      border: 1px solid #ccc;
      border-radius: 4px;
      resize: vertical;
    }
    .controls {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    select, button {
      font-family: inherit;
      font-size: 14px;
      padding: 6px 14px;
      border: 1px solid #999;
      border-radius: 4px;
      background: #fff;
      cursor: pointer;
    }
    button {
      background: #000;
      color: #fff;
      border: 1px solid #000;
    }
    button:disabled {
      background: #888;
      cursor: not-allowed;
    }
    #output {
      background: #fff;
      border: 1px solid #ddd;
      border-radius: 4px;
      padding: 12px;
      min-height: 250px;
      max-height: 450px;
      overflow-y: auto;
      font-size: 13px;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .badge {
      font-weight: bold;
      padding: 2px 5px;
      border-radius: 3px;
      margin-right: 6px;
    }
    .Thought { color: #8e44ad; }
    .ToolCall { color: #d35400; font-weight: bold; }
    .ToolResult { color: #27ae60; font-weight: bold; }
    .AgentMessage { color: #2980b9; font-weight: bold; }
    .Status { color: #7f8c8d; font-style: italic; }
    .tool-result-box {
      margin-top: 6px;
      padding: 8px 12px;
      background: #f7f9fa;
      border: 1px solid #e1e8ed;
      border-radius: 4px;
      font-size: 12px;
      line-height: 1.6;
    }
    .tool-result-header {
      font-weight: bold;
      color: #2c3e50;
      margin-bottom: 4px;
    }
    .key {
      font-weight: bold;
      color: #555;
    }
    details {
      margin-top: 6px;
      cursor: pointer;
    }
    summary {
      color: #34495e;
      font-weight: bold;
      outline: none;
    }
    .snippet-content {
      margin-top: 4px;
      padding: 6px 10px;
      background: #fff;
      border-left: 3px solid #3498db;
      border-radius: 2px;
      color: #333;
      white-space: pre-wrap;
    }
  </style>
</head>
<body>
  <h2>Browser Use</h2>

  <div class="form-group">
    <textarea id="taskInput" placeholder="Enter task instruction (e.g. 'Open Gmail and send email to...', 'Doom scroll Instagram...')..."></textarea>
    <div class="controls">
      <button id="runBtn" onclick="runTask()">Run Agent</button>
      <button onclick="clearLogs()" style="background:#eee;color:#333;border-color:#ccc;">Clear Output</button>
    </div>
  </div>

  <h3>Agent Output Stream</h3>
  <div id="output">Waiting for task...</div>

  <script>
    let pollInterval = null;

    async function runTask() {
      const task = document.getElementById("taskInput").value.trim();
      if (!task) return;
      
      document.getElementById("runBtn").disabled = true;
      document.getElementById("output").textContent = "Starting agent session...\\n";

      await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: task })
      });

      if (!pollInterval) {
        pollInterval = setInterval(fetchLogs, 1000);
      }
    }

    function formatToolResult(rawText) {
      let data = null;
      try {
        let jsonStr = rawText.replace(/'/g, '"').replace(/True/g, 'true').replace(/False/g, 'false').replace(/None/g, 'null');
        data = JSON.parse(jsonStr);
      } catch (e) {
        return null;
      }

      const container = document.createElement("div");
      container.className = "tool-result-box";

      const header = document.createElement("div");
      header.className = "tool-result-header";
      let statusIcon = data.status === "success" ? "✓ " : "✗ ";
      header.textContent = statusIcon + (data.status || "Result");
      if (data.title) header.textContent += " — " + data.title;
      container.appendChild(header);

      if (data.url) {
        const urlDiv = document.createElement("div");
        urlDiv.innerHTML = '<span class="key">URL:</span> <a href="' + data.url + '" target="_blank" style="color:#0066cc;">' + data.url + '</a>';
        container.appendChild(urlDiv);
      }

      if (data.clicked) {
        const clickDiv = document.createElement("div");
        clickDiv.innerHTML = '<span class="key">Clicked:</span> <code>' + data.clicked + '</code>';
        container.appendChild(clickDiv);
      }

      if (data.visible_text_snippet) {
        const snippetDetails = document.createElement("details");
        snippetDetails.open = true;
        const summary = document.createElement("summary");
        summary.textContent = "Extracted Page Content (" + data.visible_text_snippet.length + " chars)";
        snippetDetails.appendChild(summary);

        const snippetContent = document.createElement("div");
        snippetContent.className = "snippet-content";
        let cleanText = data.visible_text_snippet.replace(/\\n\\s*\\n+/g, "\\n").trim();
        snippetContent.textContent = cleanText;
        snippetDetails.appendChild(snippetContent);
        container.appendChild(snippetDetails);
      }

      return container;
    }

    async function fetchLogs() {
      const res = await fetch("/api/logs");
      const data = await res.json();
      const outputDiv = document.getElementById("output");
      outputDiv.innerHTML = "";
      
      data.logs.forEach(log => {
        if (log.type === "Thought") return;

        const item = document.createElement("div");
        item.style.marginBottom = "8px";
        const tag = document.createElement("span");
        tag.className = "badge " + log.type.replace(/\\s+/g, "");
        tag.textContent = "[" + log.type + "]";
        item.appendChild(tag);

        if (log.type === "Tool Result") {
          const formatted = formatToolResult(log.text);
          if (formatted) {
            item.appendChild(formatted);
          } else {
            item.appendChild(document.createTextNode(" " + log.text));
          }
        } else {
          item.appendChild(document.createTextNode(" " + log.text));
        }
        outputDiv.appendChild(item);
      });
      outputDiv.scrollTop = outputDiv.scrollHeight;

      if (!data.running && pollInterval) {
        document.getElementById("runBtn").disabled = false;
        clearInterval(pollInterval);
        pollInterval = null;
      }
    }

    async function clearLogs() {
      await fetch("/api/clear", { method: "POST" });
      document.getElementById("output").textContent = "Output cleared.\\n";
    }
  </script>
</body>
</html>
"""


class AgentHttpHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/" or url.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif url.path == "/api/logs":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            with agent_lock:
                resp = json.dumps({"running": agent_running, "logs": logs})
            self.wfile.write(resp.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        url = urlparse(self.path)
        if url.path == "/api/run":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
            task = data.get("task", "")

            def worker():
                global agent_running
                with agent_lock:
                    agent_running = True
                
                def on_log(log_type, text):
                    with agent_lock:
                        logs.append({"type": log_type, "text": text, "time": time.time()})

                try:
                    agent = GemmaContinuousAgent(headless=True)
                    agent.run(task, loop_steps=15, log_callback=on_log)
                except Exception as e:
                    on_log("Error", str(e))
                finally:
                    browser_tools.close()
                    with agent_lock:
                        agent_running = False

            threading.Thread(target=worker, daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "started"}')

        elif url.path == "/api/clear":
            with agent_lock:
                logs.clear()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "cleared"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def run_server():
    server = http.server.HTTPServer((HOST, PORT), AgentHttpHandler)
    print(f"\n==================================================")
    print(f"UI Server running at: http://{HOST}:{PORT}")
    print(f"Open http://localhost:{PORT} in your browser.")
    print(f"==================================================\n")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
