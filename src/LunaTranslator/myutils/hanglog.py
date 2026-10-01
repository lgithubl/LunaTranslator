import os
import threading
import time

import gobject


_lock = threading.Lock()
_max_bytes = 2 * 1024 * 1024


def enabled(config):
    try:
        return bool(config and config.get("诊断日志", False))
    except:
        return False


def active_config():
    try:
        from myutils.config import globalconfig, translatorsetting

        engines = []
        top = globalconfig.get("toppest_translator")
        if top:
            engines.append(top)
        engines.extend(globalconfig.get("fix_translate_rank_rank", []))
        for engine in engines:
            config = translatorsetting.get(engine, {}).get("args", {})
            if enabled(config):
                return engine, config
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


def log(tag, **fields):
    try:
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
