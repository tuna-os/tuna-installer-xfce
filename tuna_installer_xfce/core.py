"""Backend plumbing shared by every page: catalog, disks, offline stores,
recipe emission, and fisherman invocation. See ../INSTALLER-FRONTENDS.md."""

import json
import os
import shlex
import subprocess
import tempfile

IN_FLATPAK = os.path.exists("/.flatpak-info")

FISHERMAN_CMD = (
    ["pkexec", "/app/bin/fisherman"]
    if IN_FLATPAK
    else ["sudo", "/usr/local/bin/fisherman"]
)

IMAGES_JSON_PATHS = [
    os.environ.get("FISHERMAN_IMAGES_PATH", ""),
    os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
                 "tuna-installer/images.json"),
    "/etc/tuna-installer/images.json",
    "/app/share/fisherman/data/images.json",
    "/usr/share/fisherman/data/images.json",
]

OFFLINE_STORES_FILE = "/etc/tuna-installer/offline-stores"
OFFLINE_STORES_ENV = "TUNA_OFFLINE_STORES"
OFFLINE_STORE_DEFAULT = "/usr/share/tuna-installer/oci-store"


def host_run(argv, **kwargs):
    """Run a command on the host, crossing the sandbox boundary if needed."""
    if IN_FLATPAK:
        argv = ["flatpak-spawn", "--host"] + argv
    return subprocess.run(argv, capture_output=True, text=True, **kwargs)


# --- image catalog -----------------------------------------------------------

class ImageNode:
    """One entry of images.json with root->leaf field inheritance resolved.

    Current images.json uses registry+tag; older files use imgref. Handle both.
    """

    def __init__(self, raw, parent=None):
        self.name = raw.get("name", "")
        self.desc = raw.get("desc", "")
        self.subtitle = raw.get("subtitle", "")
        p = parent
        self.registry = raw.get("registry") or (p.registry if p else "")
        tag = raw.get("tag", "")
        self.imgref = raw.get("imgref") or (f"{self.registry}:{tag}" if self.registry and tag else "")
        self.flatpaks = raw.get("flatpaks") or (p.flatpaks if p else "")
        self.bootloader = raw.get("bootloader") or (p.bootloader if p else "")
        self.filesystem = raw.get("filesystem") or (p.filesystem if p else "")
        self.composefs = raw.get("composefs", p.composefs if p else False)
        self.needs_user_creation = raw.get(
            "needs_user_creation", p.needs_user_creation if p else True)
        self.children = [ImageNode(c, self) for c in raw.get("children", [])]

    def is_leaf(self):
        return bool(self.imgref) and not self.children

    def leaves(self):
        if self.is_leaf():
            yield self
        for c in self.children:
            yield from c.leaves()


def load_catalog():
    """Return (default_image, fallback_flatpaks, [ImageNode]) or Nones."""
    for path in IMAGES_JSON_PATHS:
        if path and os.path.exists(path):
            with open(path) as f:
                raw = json.load(f)
            nodes = [ImageNode(n) for n in raw.get("images", [])]
            return raw.get("default_image", ""), raw.get("fallback_flatpaks", []), nodes
    return "", [], []


# --- offline / live-ISO detection --------------------------------------------

def live_iso_image():
    """Return the running bootc image ref when booted from live media, else None.

    Live-ISO mode means the recipe may omit `image` entirely (bootc installs
    the running container)."""
    r = host_run(["bootc", "status", "--json"])
    if r.returncode != 0:
        return None
    try:
        status = json.loads(r.stdout)
        booted = status.get("status", {}).get("booted") or {}
        ref = booted.get("image", {}).get("image", {}).get("image", "")
    except (json.JSONDecodeError, AttributeError):
        return None
    if not ref:
        return None
    with open("/proc/cmdline") as f:
        live = "rd.live.image" in f.read()
    return ref if (live or os.path.exists("/run/ostree-live")) else None


def offline_stores():
    """Paths of embedded OCI stores present on this medium."""
    stores = []
    env = os.environ.get(OFFLINE_STORES_ENV, "")
    if env:
        stores += env.split(":")
    if os.path.exists(OFFLINE_STORES_FILE):
        with open(OFFLINE_STORES_FILE) as f:
            stores += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    stores.append(OFFLINE_STORE_DEFAULT)
    return [s for s in dict.fromkeys(stores) if os.path.isdir(s)]


def offline_images(stores):
    """Set of image refs available across the given store roots."""
    refs = set()
    for store in stores:
        r = host_run(["podman", "images", "--root", store, "--format", "json"])
        if r.returncode != 0:
            continue
        try:
            for img in json.loads(r.stdout):
                refs.update(img.get("Names") or [])
        except json.JSONDecodeError:
            continue
    return refs


# --- disks --------------------------------------------------------------------

def candidate_disks():
    """Installable disks: real disks, not the live medium, not removable-boot."""
    r = host_run(["lsblk", "-J", "-b", "-o",
                  "NAME,PATH,SIZE,MODEL,TYPE,RM,MOUNTPOINTS,TRAN"])
    if r.returncode != 0:
        return []
    disks = []
    for dev in json.loads(r.stdout).get("blockdevices", []):
        if dev.get("type") != "disk":
            continue
        mounts = json.dumps(dev.get("mountpoints", []))
        if "/run/initramfs/live" in mounts or "/run/media/iso" in mounts:
            continue
        disks.append({
            "path": dev["path"],
            "model": (dev.get("model") or "Unknown disk").strip(),
            "size": int(dev.get("size") or 0),
            "transport": dev.get("tran") or "",
        })
    return disks


def human_size(nbytes):
    val, unit = float(nbytes), "B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if val < 1000 or unit == "TB":
            break
        val /= 1000
    return f"{val:.1f} {unit}".replace(".0 ", " ")


# --- recipe -------------------------------------------------------------------

def write_recipe(recipe):
    """Write the recipe 0600 under XDG_RUNTIME_DIR; return its path.

    The recipe may hold a LUKS passphrase and a user password — never put it
    somewhere world-readable."""
    base = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    rundir = os.path.join(base, "tuna-installer")
    os.makedirs(rundir, mode=0o700, exist_ok=True)
    fd, path = tempfile.mkstemp(dir=rundir, suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(recipe, f, indent=2)
    os.chmod(path, 0o600)
    return path


def fisherman_argv(recipe_path):
    return FISHERMAN_CMD + [recipe_path]


def fisherman_shell(recipe_path):
    return " ".join(shlex.quote(a) for a in fisherman_argv(recipe_path))
