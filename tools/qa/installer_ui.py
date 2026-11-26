"""QMP input and screenshot checkpoints for the observed 1280x800 Calamares UI."""
import hashlib
import time

WIDTH, HEIGHT = 1280, 800
PAGES = ("welcome", "location", "keyboard", "partition", "users", "summary", "install", "finished")
SELECTED = bytes((239, 239, 239))
UNSELECTED = bytes((11, 42, 74))


def pixels(path):
    with path.open("rb") as f:
        if f.readline().strip() != b"P6" or f.readline().split() != [b"1280", b"800"] or f.readline().strip() != b"255":
            raise ValueError("Unexpected Calamares framebuffer")
        raw = f.read()
    if len(raw) != WIDTH * HEIGHT * 3:
        raise ValueError("Truncated framebuffer")
    return raw


def page(path):
    raw = pixels(path)
    rows = [raw[(y * WIDTH + 10) * 3:(y * WIDTH + 10) * 3 + 3] for y in range(100, 374, 39)]
    if rows.count(SELECTED) != 1 or rows.count(UNSELECTED) != 7:
        raise ValueError("Unknown Calamares navigation state")
    return PAGES[rows.index(SELECTED)]


def crop_digest(path, x, y, w, h):
    if not (0 <= x < x+w <= WIDTH and 0 <= y < y+h <= HEIGHT):
        raise ValueError("Invalid screenshot crop")
    raw = pixels(path)
    return hashlib.sha256(b"".join(raw[(row*WIDTH+x)*3:(row*WIDTH+x+w)*3] for row in range(y,y+h))).hexdigest()


# Stable regions compared against three successful discovery frames and the
# unobscured final frame of the failed transaction. Scoped to the pinned ISO.
WELCOME_LOGO = "4cb7285808803abfb0004592b4ef6c1459405fc80bbe517c9600fb33a78610bf"
WELCOME_NEXT = "385639e223df9c5a5debc05753462f0838f595f51841ad0323f62152702b2ffa"


def welcome_ready(path):
    """Sidebar alone cannot distinguish an obscured or inactive installer."""
    return (page(path) == "welcome"
            and crop_digest(path, 430, 300, 420, 290) == WELCOME_LOGO
            and crop_digest(path, 1100, 726, 69, 21) == WELCOME_NEXT)


def click(qmp, x, y):
    if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
        raise ValueError("Click outside framebuffer")
    qmp.call("input-send-event", {"events": [
        {"type": "abs", "data": {"axis": "x", "value": round(x * 32767 / (WIDTH - 1))}},
        {"type": "abs", "data": {"axis": "y", "value": round(y * 32767 / (HEIGHT - 1))}}]})
    time.sleep(0.15)
    qmp.call("input-send-event", {"events": [{"type": "btn", "data": {"down": True, "button": "left"}}]})
    time.sleep(0.15)
    qmp.call("input-send-event", {"events": [{"type": "btn", "data": {"down": False, "button": "left"}}]})
    time.sleep(0.15)


def key(qmp, *keys):
    qmp.call("send-key", {"keys": [{"type": "qcode", "data": k} for k in keys], "hold-time": 70})
    time.sleep(0.12)


def field(qmp, x, y, value):
    if not value or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789" for c in value):
        raise ValueError("Only lowercase ASCII test values accepted")
    click(qmp, x, y)
    key(qmp, "ctrl", "a")
    for c in value:
        key(qmp, c)
