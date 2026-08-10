# test_core.py - Unit tests for tuna_installer_xfce.core (backend plumbing)
# SPDX-License-Identifier: GPL-3.0-or-later
#
# core.py is the shared backend (catalog, disks, offline stores, recipe
# emission, fisherman invocation) and is pure stdlib — no GTK import — so
# these tests run headlessly in plain pytest.

import json
import os
import subprocess

import pytest

from tuna_installer_xfce import core


# ─── dry_run interlock ───────────────────────────────────────────────────────

class TestDryRun:
    def test_unset_is_false(self, monkeypatch):
        monkeypatch.delenv("TUNA_INSTALLER_DRY_RUN", raising=False)
        assert core.dry_run() is False

    def test_empty_is_false(self, monkeypatch):
        monkeypatch.setenv("TUNA_INSTALLER_DRY_RUN", "")
        assert core.dry_run() is False

    def test_zero_is_false(self, monkeypatch):
        monkeypatch.setenv("TUNA_INSTALLER_DRY_RUN", "0")
        assert core.dry_run() is False

    def test_nonzero_is_true(self, monkeypatch):
        monkeypatch.setenv("TUNA_INSTALLER_DRY_RUN", "1")
        assert core.dry_run() is True


# ─── product name resolution ─────────────────────────────────────────────────

class TestReadPrettyName:
    def test_quoted_value(self, tmp_path):
        f = tmp_path / "os-release"
        f.write_text('ID=fedora\nPRETTY_NAME="TunaOS Skipjack"\n')
        assert core._read_pretty_name(str(f)) == "TunaOS Skipjack"

    def test_unquoted_value(self, tmp_path):
        f = tmp_path / "os-release"
        f.write_text("PRETTY_NAME=Bonito\n")
        assert core._read_pretty_name(str(f)) == "Bonito"

    def test_missing_file_returns_empty(self, tmp_path):
        assert core._read_pretty_name(str(tmp_path / "nope")) == ""

    def test_ignores_other_keys(self, tmp_path):
        f = tmp_path / "os-release"
        f.write_text("NAME=Something\nPRETTY_NAME=\nID=tunaos\n")
        assert core._read_pretty_name(str(f)) == ""


class TestResolveProductName:
    def test_first_path_wins(self, tmp_path, monkeypatch):
        first = tmp_path / "a"
        second = tmp_path / "b"
        first.write_text('PRETTY_NAME="Alpha"\n')
        second.write_text('PRETTY_NAME="Beta"\n')
        monkeypatch.setattr(core, "OS_RELEASE_PATHS", [str(first), str(second)])
        assert core.resolve_product_name() == "Alpha"

    def test_falls_back_when_none_present(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "OS_RELEASE_PATHS", [str(tmp_path / "missing")])
        assert core.resolve_product_name() == core.PRODUCT_NAME_FALLBACK


# ─── offline stores ──────────────────────────────────────────────────────────

class TestOfflineStores:
    def test_env_and_default_dedup_and_dir_filter(self, tmp_path, monkeypatch):
        a = tmp_path / "store-a"
        b = tmp_path / "store-b"
        a.mkdir()
        b.mkdir()
        not_a_dir = tmp_path / "plain-file"
        not_a_dir.write_text("x")
        monkeypatch.setenv("TUNA_OFFLINE_STORES", f"{a}:{b}:{not_a_dir}:{a}")
        monkeypatch.setattr(core, "OFFLINE_STORES_FILE", str(tmp_path / "absent"))
        monkeypatch.setattr(core, "OFFLINE_STORE_DEFAULT", str(tmp_path / "default-missing"))
        stores = core.offline_stores()
        assert stores == [str(a), str(b)]

    def test_config_file_entries(self, tmp_path, monkeypatch):
        a = tmp_path / "from-file"
        a.mkdir()
        cfg = tmp_path / "offline-stores"
        cfg.write_text(f"# comment\n\n{a}\n\n")
        monkeypatch.delenv("TUNA_OFFLINE_STORES", raising=False)
        monkeypatch.setattr(core, "OFFLINE_STORES_FILE", str(cfg))
        monkeypatch.setattr(core, "OFFLINE_STORE_DEFAULT", str(tmp_path / "default-missing"))
        assert core.offline_stores() == [str(a)]


# ─── host commands / catalog ─────────────────────────────────────────────────

class TestOfflineImages:
    def test_parses_names_and_skips_failures(self, monkeypatch):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps([{"Names": ["localhost/one:latest", "localhost/two:1.0"]},
                               {"Names": None}]),
            stderr="")
        monkeypatch.setattr(core, "host_run", lambda argv, **kw: fake)
        assert core.offline_images(["store-a", "store-b"]) == {"localhost/one:latest", "localhost/two:1.0"}

    def test_nonzero_returncode_yields_empty(self, monkeypatch):
        fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="boom", stderr="")
        monkeypatch.setattr(core, "host_run", lambda argv, **kw: fake)
        assert core.offline_images(["store"]) == set()

    def test_invalid_json_yields_empty(self, monkeypatch):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="not json", stderr="")
        monkeypatch.setattr(core, "host_run", lambda argv, **kw: fake)
        assert core.offline_images(["store"]) == set()


class TestCandidateDisks:
    def test_filters_non_disks_and_live_media(self, monkeypatch):
        payload = {
            "blockdevices": [
                {"type": "disk", "path": "/dev/vda", "name": "vda", "size": 10**12, "model": "", "rm": "0", "mountpoints": ["/run/initramfs/live"], "tran": "virtio"},
                {"type": "disk", "path": "/dev/vdb", "name": "vdb", "size": 10**12, "model": "Virtio", "rm": "0", "mountpoints": [], "tran": "virtio"},
                {"type": "part", "path": "/dev/vda1", "name": "vda1", "size": 10**11, "model": "", "rm": "0", "mountpoints": [], "tran": "virtio"},
            ]
        }
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(payload), stderr="")
        monkeypatch.setattr(core, "host_run", lambda argv, **kw: fake)
        disks = core.candidate_disks()
        assert [d["path"] for d in disks] == ["/dev/vdb"]
        assert disks[0]["model"] == "Virtio"
        assert disks[0]["transport"] == "virtio"

    def test_failure_yields_empty(self, monkeypatch):
        fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="lsblk missing")
        monkeypatch.setattr(core, "host_run", lambda argv, **kw: fake)
        assert core.candidate_disks() == []


# ─── human_size formatting ───────────────────────────────────────────────────

class TestHumanSize:
    @pytest.mark.parametrize(
        "nbytes,expected",
        [
            (0, "0 B"),
            (999, "999 B"),
            (1000, "1 KB"),
            (1500, "1.5 KB"),
            (1_000_000, "1 MB"),
            (2_500_000_000, "2.5 GB"),
            (10**12, "1 TB"),
        ],
    )
    def test_formatting(self, nbytes, expected):
        assert core.human_size(nbytes) == expected


# ─── recipe writing ──────────────────────────────────────────────────────────

class TestWriteRecipe:
    def test_writes_0600_json_under_runtime_dir(self, tmp_path, monkeypatch):
        import stat
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        path = core.write_recipe({"image": "localhost/foo:1"})
        assert path.startswith(str(tmp_path / "tuna-installer"))
        mode = stat.S_IMODE(os.stat(path).st_mode)
        assert mode == 0o600, f"recipe must be 0600, got {oct(mode)}"
        assert json.load(open(path)) == {"image": "localhost/foo:1"}

    def test_falls_back_to_tmp_without_runtime_dir(self, monkeypatch):
        import stat
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        path = core.write_recipe({"x": 1})
        assert json.load(open(path)) == {"x": 1}
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


# ─── fisherman invocation ────────────────────────────────────────────────────

class TestFisherman:
    def test_argv_uses_sudo_outside_flatpak(self):
        assert core.fisherman_argv("/run/user/1000/recipe.json") == [
            "sudo", "/usr/local/bin/fisherman", "/run/user/1000/recipe.json"]

    def test_shell_quotes_arguments(self):
        cmd = core.fisherman_shell("/run/user/1000/recipe.json")
        assert cmd == "sudo /usr/local/bin/fisherman /run/user/1000/recipe.json"

    def test_shell_quotes_spaces(self):
        cmd = core.fisherman_shell("/path with spaces/recipe.json")
        assert "'/path with spaces/recipe.json'" in cmd
