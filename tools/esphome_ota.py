#!/usr/bin/env python3
"""Build and OTA-flash a device through the ESPHome Device Builder on Home Assistant.

The script asks the Supervisor for the ESPHome add-on, opens its ingress websocket,
and runs firmware/install. It does not store the add-on ingress path: that path
changes when the add-on restarts.

Environment:
  HA_URL    Home Assistant base URL. Default: https://ha.pilabs.pl
  HA_TOKEN  Long-lived access token. Required.

Requires the websocket-client package (pip install websocket-client).

Examples:
  python3 tools/esphome_ota.py --dry-run
  python3 tools/esphome_ota.py --configuration intercom.yaml --port OTA
"""
import argparse
import json
import os
import re
import ssl
import sys
import time
from urllib.parse import urlparse

try:
    from websocket import WebSocketTimeoutException, create_connection
except ImportError:
    sys.exit("websocket-client is required: pip install websocket-client")

ANSI = re.compile(r"\x1b\[[0-9;]*m")
SECRET = re.compile(r"(?i)(password|token|encryption key)\s*[:=]\s*\S+")


def redact(text, token):
    text = ANSI.sub("", text)
    if token and token in text:
        text = text.replace(token, "[redacted]")
    return SECRET.sub(r"\1=[redacted]", text).rstrip()


class HomeAssistant:
    def __init__(self, base_url, token):
        parsed = urlparse(base_url)
        if parsed.scheme not in ("https", "http") or not parsed.netloc:
            raise SystemExit(f"HA_URL must be an http(s) URL, got {base_url!r}")
        self.base = base_url.rstrip("/")
        self.token = token
        self.ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        self._id = 0
        self.ws = create_connection(
            f"{self.ws_scheme}://{parsed.netloc}/api/websocket",
            timeout=30,
            sslopt={"cert_reqs": ssl.CERT_REQUIRED} if parsed.scheme == "https" else {},
        )
        hello = json.loads(self.ws.recv())
        if hello.get("type") != "auth_required":
            raise SystemExit(f"Unexpected Home Assistant handshake: {hello.get('type')}")
        self.ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth = json.loads(self.ws.recv())
        if auth.get("type") != "auth_ok":
            raise SystemExit("Home Assistant rejected HA_TOKEN")

    def close(self):
        self.ws.close()

    def supervisor(self, endpoint, method="get", data=None, timeout=90):
        self._id += 1
        payload = {
            "id": self._id,
            "type": "supervisor/api",
            "endpoint": endpoint,
            "method": method,
        }
        if data is not None:
            payload["data"] = data
        self.ws.send(json.dumps(payload))
        self.ws.settimeout(timeout)
        while True:
            message = json.loads(self.ws.recv())
            if message.get("id") != self._id:
                continue
            if not message.get("success"):
                error = message.get("error") or message
                raise SystemExit(f"Supervisor {method} {endpoint} failed: {error}")
            return message.get("result") or {}

    def ingress_session(self):
        result = self.supervisor("/ingress/session", method="post")
        session = result.get("session")
        if not session:
            raise SystemExit("Supervisor did not return an ingress session")
        return session


def esphome_addon(ha):
    listing = ha.supervisor("/addons")
    addons = listing.get("addons") or []
    hits = [
        addon for addon in addons
        if str(addon.get("slug", "")).endswith("_esphome")
        or "esphome" in str(addon.get("name", "")).lower()
    ]
    if not hits:
        raise SystemExit("ESPHome Device Builder add-on is not installed")
    hits.sort(key=lambda addon: (addon.get("state") != "started", addon.get("slug") or ""))
    slug = hits[0]["slug"]
    info = ha.supervisor(f"/addons/{slug}/info")
    if info.get("state") != "started":
        print(f"starting {info.get('name') or slug}", flush=True)
        ha.supervisor(f"/addons/{slug}/start", method="post")
        deadline = time.time() + 90
        while time.time() < deadline:
            info = ha.supervisor(f"/addons/{slug}/info")
            if info.get("state") == "started" and info.get("ingress_entry"):
                break
            time.sleep(1)
        else:
            raise SystemExit(f"{slug} did not start")
    entry = info.get("ingress_entry") or ""
    if not entry.startswith("/api/hassio_ingress/"):
        raise SystemExit(f"{slug} has no ingress entry")
    return info, entry


def dashboard(ha, ingress_entry, session):
    parsed = urlparse(ha.base)
    ws = create_connection(
        f"{ha.ws_scheme}://{parsed.netloc}{ingress_entry.rstrip('/')}/ws",
        timeout=30,
        header=["Cookie: ingress_session=" + session],
        sslopt={"cert_reqs": ssl.CERT_REQUIRED} if parsed.scheme == "https" else {},
    )
    hello = json.loads(ws.recv())
    if "esphome_version" not in hello:
        raise SystemExit("ESPHome dashboard did not send a hello frame")
    return ws, hello


def command(ws, message_id, name, args=None, timeout=30):
    payload = {"command": name, "message_id": message_id}
    if args:
        payload["args"] = args
    ws.send(json.dumps(payload))
    ws.settimeout(timeout)
    while True:
        message = json.loads(ws.recv())
        if message.get("message_id") == message_id and "event" not in message:
            if message.get("error"):
                raise SystemExit(f"{name} failed: {message['error']}")
            return message.get("result")


def device_present(ws, configuration):
    result = command(ws, "devices", "devices/list")
    devices = result
    if isinstance(result, dict):
        devices = result.get("configured") or result.get("devices") or []
    if not isinstance(devices, list):
        raise SystemExit("devices/list returned an unexpected payload")
    for device in devices:
        if device.get("configuration") == configuration or device.get("name") == configuration.removesuffix(".yaml"):
            return device
    known = ", ".join(sorted(device.get("configuration", "") for device in devices))
    raise SystemExit(f"{configuration} is not in the ESPHome dashboard ({known})")


def follow_install(ws, configuration, port, token):
    def send(message_id, name, args=None):
        payload = {"command": name, "message_id": message_id}
        if args:
            payload["args"] = args
        ws.send(json.dumps(payload))

    send("follow", "firmware/follow_jobs", {"snapshot": False})
    send("install", "firmware/install", {"configuration": configuration, "port": port})
    print(f"install requested for {configuration} via {port}", flush=True)

    compile_id = None
    upload_id = None
    ws.settimeout(180)
    deadline = time.time() + 45 * 60
    while time.time() < deadline:
        try:
            message = json.loads(ws.recv())
        except (TimeoutError, WebSocketTimeoutException):
            print("still waiting for the builder", flush=True)
            continue
        if message.get("message_id") == "install" and message.get("error"):
            raise SystemExit(redact(json.dumps(message["error"]), token))
        if message.get("message_id") == "install" and isinstance(message.get("result"), dict):
            compile_id = message["result"].get("job_id") or compile_id
            print(f"compile job {compile_id}", flush=True)
        event = message.get("event")
        job = message.get("data") or {}
        job_id = job.get("job_id")
        if (
            compile_id is None
            and event in ("job_queued", "job_started")
            and job.get("configuration") == configuration
            and job.get("job_type") == "compile"
        ):
            compile_id = job_id
        if (
            event == "job_queued"
            and job.get("job_type") == "upload"
            and job.get("depends_on")
            and job.get("depends_on") == compile_id
        ):
            upload_id = job_id
        if job_id not in {compile_id, upload_id}:
            continue
        if event == "job_output":
            line = redact(job.get("line") or "", token)
            if line:
                print(line, flush=True)
            continue
        if event in ("job_started", "job_completed", "job_failed"):
            print(
                f"{event} {job.get('job_type')} {job.get('status')} exit={job.get('exit_code')}",
                flush=True,
            )
        if event == "job_failed" or job.get("status") in ("failed", "cancelled"):
            detail = job.get("error") or job.get("failure_reason") or event
            raise SystemExit(redact(str(detail), token) or "firmware job failed")
        if job_id == upload_id and event == "job_completed":
            if job.get("status") == "completed" and job.get("exit_code") in (0, None):
                print("OTA complete", flush=True)
                return
            raise SystemExit(
                f"upload finished with status {job.get('status')} exit {job.get('exit_code')}"
            )
    raise SystemExit("timed out waiting for OTA")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration", default="intercom.yaml", help="dashboard YAML file name")
    parser.add_argument("--port", default="OTA", help="install target (OTA or a serial port)")
    parser.add_argument("--dry-run", action="store_true", help="connect and check the device, do not flash")
    args = parser.parse_args()

    token = os.environ.get("HA_TOKEN", "")
    if not token:
        raise SystemExit("HA_TOKEN is not set")
    base_url = os.environ.get("HA_URL", "https://ha.pilabs.pl")

    ha = HomeAssistant(base_url, token)
    try:
        info, entry = esphome_addon(ha)
        session = ha.ingress_session()
    finally:
        ha.close()

    ws, hello = dashboard(ha, entry, session)
    try:
        print(
            f"builder {hello.get('esphome_version')} ({info.get('slug')}, {info.get('state')})",
            flush=True,
        )
        device = device_present(ws, args.configuration)
        runtime = device.get("runtime_state") or {}
        if not isinstance(runtime, dict):
            runtime = {"state": runtime}
        online = runtime.get("state") or device.get("state") or "unknown"
        version = runtime.get("deployed_version") or device.get("current_version") or ""
        print(
            f"{device.get('friendly_name') or device.get('name')} "
            f"{device.get('configuration')} {online} {version}",
            flush=True,
        )
        if args.dry_run:
            command(ws, "ping", "ping")
            print("dry-run ok", flush=True)
            return
        follow_install(ws, args.configuration, args.port, token)
    finally:
        ws.close()


if __name__ == "__main__":
    main()
