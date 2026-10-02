import os
import sys
import threading
import time
import traceback

import gobject


_lock = threading.Lock()
_max_bytes = 2 * 1024 * 1024
_ui_tick_time = 0
_last_thread_dump_time = 0


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


def mark_ui_tick():
    global _ui_tick_time
    _ui_tick_time = time.time()


def ui_tick_age():
    if not _ui_tick_time:
        return None
    return time.time() - _ui_tick_time


def ui_tick_age_text():
    age = ui_tick_age()
    if age is None:
        return "never"
    return "{:.3f}".format(age)


def log(tag, **fields):
    try:
        if not enabled():
            return
        path = _path()
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        millis = int((time.time() % 1) * 1000)
        tid = threading.get_ident()
        parts = ["{}.{:03d}".format(now, millis), "pid={}".format(os.getpid()), "tid={}".format(tid), tag]
        for key, value in fields.items():
            parts.append("{}={}".format(key, _short(value)))
        line = " | ".join(parts) + "\n"
        with _lock:
            _rotate_if_needed(path)
            with open(path, "a", encoding="utf-8", errors="replace") as ff:
                ff.write(line)
    except:
        pass


def dump_all_thread_stacks(reason, **fields):
    try:
        if not enabled():
            return
        path = _path()
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        millis = int((time.time() % 1) * 1000)
        frames = sys._current_frames()
        threads = {thread.ident: thread for thread in threading.enumerate()}
        header = [
            "{}.{:03d}".format(now, millis),
            "pid={}".format(os.getpid()),
            "thread_dump",
            "reason={}".format(_short(reason)),
        ]
        for key, value in fields.items():
            header.append("{}={}".format(key, _short(value)))
        lines = [" | ".join(header) + "\n"]
        for ident, frame in frames.items():
            thread = threads.get(ident)
            name = thread.name if thread else ""
            daemon = thread.daemon if thread else ""
            lines.append(
                "\n--- thread ident={} name={} daemon={} ---\n".format(
                    ident, name, daemon
                )
            )
            lines.extend(traceback.format_stack(frame))
        with _lock:
            _rotate_if_needed(path)
            with open(path, "a", encoding="utf-8", errors="replace") as ff:
                ff.writelines(lines)
    except:
        pass


def dump_if_ui_stale(reason, stale_after=15, interval=60, **fields):
    global _last_thread_dump_time
    try:
        if not enabled():
            return
        age = ui_tick_age()
        if age is None or age < stale_after:
            return
        now = time.time()
        if now - _last_thread_dump_time < interval:
            return
        _last_thread_dump_time = now
        dump_all_thread_stacks(reason, ui_tick_age="{:.3f}".format(age), **fields)
    except:
        pass
