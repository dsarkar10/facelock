import os
import re
import platform
import subprocess
import tempfile

HOSTS_FILE = "/etc/hosts"
FACELOCK_MARKER = "# facelock-block"


def _sudo_run(args, input_str=None):
    try:
        proc = subprocess.run(
            ["sudo"] + args,
            input=input_str.encode() if input_str else None,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return proc.returncode == 0, proc.stdout, proc.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError) as e:
        return False, "", str(e)


def is_sudo_available():
    try:
        r = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def is_macos():
    return platform.system() == "Darwin"


def is_linux():
    return platform.system() == "Linux"


def _read_hosts():
    if not os.path.exists(HOSTS_FILE):
        return []
    with open(HOSTS_FILE) as f:
        return f.readlines()


def _write_hosts(lines):
    content = "".join(lines)
    ok, _, err = _sudo_run(["tee", HOSTS_FILE], content)
    return ok, err


def apply_domain_block(domain: str):
    clean = domain.strip().lower()
    clean = re.sub(r"^https?://", "", clean)
    clean = clean.rstrip("/").split("/")[0].split("?")[0].split("#")[0]

    rows = _read_hosts()
    new_rows = []
    for line in rows:
        if FACELOCK_MARKER in line and clean in line:
            return True, "Already blocked"
        new_rows.append(line)

    www = f"www.{clean}" if not clean.startswith("www.") else clean
    new_rows.append(f"127.0.0.1\t{clean}\t{FACELOCK_MARKER}\n")
    if www != clean:
        new_rows.append(f"127.0.0.1\t{www}\t{FACELOCK_MARKER}\n")

    ok, err = _write_hosts(new_rows)
    if ok:
        return True, f"Blocked {clean}"
    return False, f"Failed to write hosts file: {err}"


def remove_domain_block(domain: str):
    clean = domain.strip().lower()
    clean = re.sub(r"^https?://", "", clean)
    clean = clean.rstrip("/").split("/")[0].split("?")[0].split("#")[0]

    rows = _read_hosts()
    new_rows = [line for line in rows if not (FACELOCK_MARKER in line and clean in line)]

    if len(new_rows) == len(rows):
        return True, "Not in blocklist"

    ok, err = _write_hosts(new_rows)
    if ok:
        return True, f"Unblocked {clean}"
    return False, f"Failed to write hosts file: {err}"


def apply_ip_block(ip: str, port=None, protocol=None):
    if is_macos():
        rules = []
        if port:
            proto = protocol or "tcp"
            rules.append(f"block drop in proto {proto} from {ip} to any port {port}")
            rules.append(f"block drop out proto {proto} from any to {ip} port {port}")
        else:
            rules.append(f"block drop in from {ip} to any")
            rules.append(f"block drop out from any to {ip}")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".pf.conf", delete=False) as f:
            f.write("\n".join(rules) + "\n")
            tmp = f.name

        try:
            ok, out, err = _sudo_run(["pfctl", "-a", "facelock", "-f", tmp])
            os.unlink(tmp)
            if ok:
                return True, f"Blocked IP {ip}"
            return False, err
        except Exception as e:
            os.unlink(tmp)
            return False, str(e)

    elif is_linux():
        cmd = ["iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"]
        if protocol:
            cmd.insert(-2, "-p")
            cmd.insert(-2, protocol)
        if port:
            cmd.insert(-2, "--dport")
            cmd.insert(-2, str(port))

        ok, _, err = _sudo_run(cmd)
        if ok:
            return True, f"Blocked IP {ip}"
        return False, err
    else:
        return True, f"Stored rule for {ip} (unsupported OS for firewall)"



def remove_ip_block(ip: str, port=None, protocol=None):
    if is_macos():
        ok, _, err = _sudo_run(["pfctl", "-a", "facelock", "-F", "all"])
        if ok:
            return True, f"Removed IP rules for {ip} (all rules flushed)"
        return False, err

    elif is_linux():
        cmd = ["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"]
        if protocol:
            cmd.insert(-2, "-p")
            cmd.insert(-2, protocol)
        if port:
            cmd.insert(-2, "--dport")
            cmd.insert(-2, str(port))

        ok, _, err = _sudo_run(cmd)
        if ok:
            return True, f"Unblocked IP {ip}"
        return False, err
    else:
        return True, f"Removed rule for {ip}"


def get_firewall_status():
    status = {
        "sudo_available": is_sudo_available(),
        "os": platform.system(),
        "domain_blocking": os.path.exists(HOSTS_FILE),
    }

    if is_macos():
        ok, out, _ = _sudo_run(["pfctl", "-a", "facelock", "-s", "rules"])
        status["ip_blocking_enabled"] = ok
        status["active_rules"] = out.strip() if ok else ""
    elif is_linux():
        ok, _, _ = _sudo_run(["iptables", "-L", "INPUT", "-n"])
        status["ip_blocking_enabled"] = ok
    else:
        status["ip_blocking_enabled"] = False

    return status
