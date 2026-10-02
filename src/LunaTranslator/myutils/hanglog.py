import os
import queue
import threading
import time

import gobject


_lock = threading.Lock()
_writer_lock = threading.Lock()
_queue = queue.Queue(maxsize=10000)
_writer_started = False
_max_bytes = 2 * 1024 * 1024


def enabled(config=None):
    try:
        from myutils.config import globalconfig

        return bool(globalconfig.get("diagnostic_log", False))
    except:
        return False


def active_config():
    try:
        from myutils.config import globalconfig

        if enabled():
            return "global", globalconfig
    except:
        pass
    return None, None


def _short(value, limit=220):
    try:
        text = str(value)
    except:
        text = repr(value)
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    if len(text) > limit:
        text = text[:limit] + "...<trimmed>"
    return text


def _path():
    return gobject.getcachedir("logs/hang-diagnostics.log")


def _rotate_if_needed(path):
    try:
        if os.path.getsize(path) <= _max_bytes:
            return
        bak = path + ".1"
        try:
            os.remove(bak)
        except:
            pass
        os.replace(path, bak)
    except FileNotFoundError:
        pass
    except:
        pass


def _write_line(path, line):
    with _lock:
        _rotate_if_needed(path)
        with open(path, "a", encoding="utf-8", errors="replace") as ff:
            ff.write(line)


def _writer():
    while True:
        path, line = _queue.get()
        try:
            _write_line(path, line)
        except:
            pass


def _ensure_writer():
    global _writer_started
    if _writer_started:
        return
    with _writer_lock:
        if _writer_started:
            return
        t = threading.Thread(target=_writer, daemon=True)
        t.start()
        _writer_started = True


def log(tag, **fields):
    try:
        if not enabled():
            return
        _ensure_writer()
        path = _path()
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        millis = int((time.time() % 1) * 1000)
        tid = threading.get_ident()
        parts = ["{}.{:03d}".format(now, millis), "pid={}".format(os.getpid()), "tid={}".format(tid), tag]
        for key, value in fields.items():
            parts.append("{}={}".format(key, _short(value)))
        line = " | ".join(parts) + "\n"
        try:
            _queue.put_nowait((path, line))
        except queue.Full:
            pass
    except:
        pass
