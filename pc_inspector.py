"""
PC Inspector & Comparator
Scansiona l'hardware e le impostazioni del PC e le confronta con un altro PC.
Requisiti: pip install psutil wmi py-cpuinfo
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import platform
import psutil
import subprocess
import os
import datetime
import threading
import socket
import re
import sys

# ─── Colori e stile ───────────────────────────────────────────────────────────
BG       = "#0d1117"
PANEL    = "#161b22"
BORDER   = "#30363d"
ACCENT   = "#58a6ff"
GREEN    = "#3fb950"
RED      = "#f85149"
YELLOW   = "#d29922"
TEXT     = "#e6edf3"
MUTED    = "#8b949e"
FONT     = ("Consolas", 10)
FONT_B   = ("Consolas", 10, "bold")
FONT_H   = ("Consolas", 13, "bold")
FONT_SM  = ("Consolas", 9)

# ─── Raccolta dati HW ─────────────────────────────────────────────────────────

def wmic(query):
    """Esegue una query WMIC e restituisce il testo."""
    try:
        out = subprocess.check_output(
            ["wmic"] + query.split() + ["get", "/format:list"],
            stderr=subprocess.DEVNULL, text=True, timeout=10
        )
        return out
    except Exception:
        return ""

def parse_wmic(text):
    """Converte output WMIC in dict."""
    result = {}
    for line in text.strip().splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if k and v:
                if k in result:
                    if not isinstance(result[k], list):
                        result[k] = [result[k]]
                    result[k].append(v)
                else:
                    result[k] = v
    return result

def bytes_to_gb(b):
    try:
        return round(int(b) / (1024**3), 2)
    except Exception:
        return b

def collect_os():
    info = {}
    info["Sistema Operativo"] = platform.system()
    info["Versione OS"] = platform.version()
    info["Release"] = platform.release()
    info["Architettura"] = platform.machine()
    info["Hostname"] = socket.gethostname()
    info["Utente corrente"] = os.environ.get("USERNAME", "N/A")

    # Windows build/edition via WMIC
    p = parse_wmic("os Caption,Version,BuildNumber,OSArchitecture,SerialNumber,RegisteredUser,InstallDate")
    if p:
        info["Edizione Windows"] = p.get("Caption", "N/A")
        info["Build"] = p.get("BuildNumber", "N/A")
        info["Architettura OS"] = p.get("OSArchitecture", "N/A")
        info["Data installazione"] = p.get("InstallDate", "N/A")[:8] if p.get("InstallDate") else "N/A"
        info["Utente registrato"] = p.get("RegisteredUser", "N/A")

    # Uptime
    boot = psutil.boot_time()
    info["Ultimo avvio"] = datetime.datetime.fromtimestamp(boot).strftime("%Y-%m-%d %H:%M:%S")
    return info

def collect_cpu():
    info = {}
    # psutil base
    info["Core fisici"] = str(psutil.cpu_count(logical=False))
    info["Core logici"] = str(psutil.cpu_count(logical=True))
    freq = psutil.cpu_freq()
    if freq:
        info["Frequenza attuale (MHz)"] = str(round(freq.current, 0))
        info["Frequenza max (MHz)"] = str(round(freq.max, 0))

    # WMIC per dettagli
    p = parse_wmic("cpu Name,Manufacturer,MaxClockSpeed,L2CacheSize,L3CacheSize,NumberOfCores,NumberOfLogicalProcessors,SocketDesignation,Caption,ProcessorId,VirtualizationFirmwareEnabled")
    if p:
        info["Modello CPU"] = p.get("Name", "N/A")
        info["Produttore"] = p.get("Manufacturer", "N/A")
        info["Socket"] = p.get("SocketDesignation", "N/A")
        info["Cache L2 (KB)"] = p.get("L2CacheSize", "N/A")
        info["Cache L3 (KB)"] = p.get("L3CacheSize", "N/A")
        info["Virtualizzazione"] = p.get("VirtualizationFirmwareEnabled", "N/A")
        info["ProcessorId"] = p.get("ProcessorId", "N/A")

    # Percentuale utilizzo corrente
    info["Utilizzo CPU (%)"] = str(psutil.cpu_percent(interval=1))
    return info

def collect_ram():
    info = {}
    vm = psutil.virtual_memory()
    info["RAM totale (GB)"] = str(bytes_to_gb(vm.total))
    info["RAM disponibile (GB)"] = str(bytes_to_gb(vm.available))
    info["RAM utilizzata (%)"] = str(vm.percent)

    sw = psutil.swap_memory()
    info["Swap totale (GB)"] = str(bytes_to_gb(sw.total))
    info["Swap usata (%)"] = str(sw.percent)

    # Dettagli moduli RAM via WMIC
    p = parse_wmic("memorychip Capacity,Speed,Manufacturer,MemoryType,FormFactor,DeviceLocator,BankLabel")
    if p:
        caps = p.get("Capacity", [])
        if not isinstance(caps, list): caps = [caps]
        spds = p.get("Speed", [])
        if not isinstance(spds, list): spds = [spds]
        mans = p.get("Manufacturer", [])
        if not isinstance(mans, list): mans = [mans]
        locs = p.get("DeviceLocator", [])
        if not isinstance(locs, list): locs = [locs]

        for i, cap in enumerate(caps):
            slot = locs[i] if i < len(locs) else f"Slot {i}"
            spd  = spds[i] if i < len(spds) else "?"
            man  = mans[i] if i < len(mans) else "?"
            try:
                gb = bytes_to_gb(cap)
            except Exception:
                gb = cap
            info[f"Modulo {slot}"] = f"{gb} GB @ {spd} MHz ({man})"
    return info

def collect_disk():
    info = {}
    # Partizioni
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            info[f"Partizione {part.device}"] = (
                f"{bytes_to_gb(usage.total)} GB totali, "
                f"{bytes_to_gb(usage.used)} GB usati ({usage.percent}%), "
                f"FS: {part.fstype}"
            )
        except Exception:
            pass

    # Dischi fisici via WMIC
    p = parse_wmic("diskdrive Model,Size,InterfaceType,MediaType,SerialNumber,Status,Firmware")
    if p:
        models = p.get("Model", [])
        if not isinstance(models, list): models = [models]
        sizes = p.get("Size", [])
        if not isinstance(sizes, list): sizes = [sizes]
        ifaces = p.get("InterfaceType", [])
        if not isinstance(ifaces, list): ifaces = [ifaces]
        serials = p.get("SerialNumber", [])
        if not isinstance(serials, list): serials = [serials]

        for i, model in enumerate(models):
            sz = bytes_to_gb(sizes[i]) if i < len(sizes) else "?"
            ifs = ifaces[i] if i < len(ifaces) else "?"
            ser = serials[i] if i < len(serials) else "?"
            info[f"Disco fisico {i}"] = f"{model} | {sz} GB | {ifs} | S/N: {ser}"

    # I/O stats
    io = psutil.disk_io_counters()
    if io:
        info["I/O lettura totale (GB)"] = str(bytes_to_gb(io.read_bytes))
        info["I/O scrittura totale (GB)"] = str(bytes_to_gb(io.write_bytes))
    return info

def collect_gpu():
    info = {}

    # ── Metodo 1: PowerShell Get-CimInstance (più affidabile) ─────────────
    ps_out = run_ps(
        "Get-CimInstance -ClassName Win32_VideoController | "
        "Select-Object Name,AdapterCompatibility,AdapterRAM,DriverVersion,"
        "VideoModeDescription,CurrentRefreshRate,VideoProcessor,"
        "Status,InfSection,InstalledDisplayDrivers | "
        "ConvertTo-Csv -NoTypeInformation"
    )

    if ps_out and ps_out.strip():
        lines = [l for l in ps_out.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            gpu_index = 0
            for row in lines[1:]:
                vals = []
                current = ""
                in_quotes = False
                for ch in row:
                    if ch == '"':
                        in_quotes = not in_quotes
                    elif ch == "," and not in_quotes:
                        vals.append(current.strip('"'))
                        current = ""
                        continue
                    else:
                        current += ch
                vals.append(current.strip('"'))

                d = dict(zip(headers, vals))
                name = d.get("Name", f"GPU {gpu_index}").strip()
                if not name:
                    name = f"GPU {gpu_index}"

                prefix = f"GPU {gpu_index} [{name}]"

                # RAM
                raw_ram = d.get("AdapterRAM", "0")
                try:
                    ram_gb = round(int(raw_ram) / (1024**3), 2)
                    info[f"{prefix} – VRAM (GB)"] = str(ram_gb)
                except Exception:
                    info[f"{prefix} – VRAM"] = raw_ram or "N/A"

                info[f"{prefix} – Produttore"]  = d.get("AdapterCompatibility", "N/A")
                info[f"{prefix} – Driver"]      = d.get("DriverVersion", "N/A")
                info[f"{prefix} – Risoluzione"] = d.get("VideoModeDescription", "N/A")
                info[f"{prefix} – Refresh (Hz)"]= d.get("CurrentRefreshRate", "N/A")
                info[f"{prefix} – Processore"]  = d.get("VideoProcessor", "N/A")
                info[f"{prefix} – Stato"]       = d.get("Status", "N/A")
                gpu_index += 1

    # ── Metodo 2: fallback WMIC diretto ───────────────────────────────────
    if not any("GPU" in k for k in info):
        wmic_out = wmic(
            "path win32_videocontroller",
            "Name,AdapterCompatibility,AdapterRAM,DriverVersion,"
            "VideoModeDescription,CurrentRefreshRate,VideoProcessor,Status"
        )
        if wmic_out and wmic_out.strip():
            blocks = []
            current_block = {}
            for line in (wmic_out or "").splitlines():
                line = line.strip()
                if not line:
                    if current_block:
                        blocks.append(current_block)
                        current_block = {}
                elif "=" in line:
                    k, _, v = line.partition("=")
                    current_block[k.strip()] = v.strip()
            if current_block:
                blocks.append(current_block)

            for i, block in enumerate(blocks):
                name = block.get("Name", f"GPU {i}")
                prefix = f"GPU {i} [{name}]"
                raw_ram = block.get("AdapterRAM", "0")
                try:
                    ram_gb = round(int(raw_ram) / (1024**3), 2)
                    info[f"{prefix} – VRAM (GB)"] = str(ram_gb)
                except Exception:
                    info[f"{prefix} – VRAM"] = raw_ram or "N/A"

                info[f"{prefix} – Produttore"]  = block.get("AdapterCompatibility", "N/A")
                info[f"{prefix} – Driver"]      = block.get("DriverVersion", "N/A")
                info[f"{prefix} – Risoluzione"] = block.get("VideoModeDescription", "N/A")
                info[f"{prefix} – Refresh (Hz)"]= block.get("CurrentRefreshRate", "N/A")
                info[f"{prefix} – Processore"]  = block.get("VideoProcessor", "N/A")
                info[f"{prefix} – Stato"]       = block.get("Status", "N/A")

    # ── Metodo 3: fallback PowerShell Get-WmiObject ────────────────────────
    if not any("GPU" in k for k in info):
        ps_wmi = run_ps(
            "Get-WmiObject Win32_VideoController | "
            "ForEach-Object { "
            "  'Name=' + $_.Name; "
            "  'VRAM=' + $_.AdapterRAM; "
            "  'Driver=' + $_.DriverVersion; "
            "  'Status=' + $_.Status; "
            "  '---' "
            "}"
        )
        if ps_wmi and ps_wmi.strip():
            gpu_index = 0
            current = {}
            for line in ps_wmi.splitlines():
                line = line.strip()
                if line == "---":
                    if current:
                        name = current.get("Name", f"GPU {gpu_index}")
                        prefix = f"GPU {gpu_index} [{name}]"
                        try:
                            ram_gb = round(int(current.get("VRAM", 0)) / (1024**3), 2)
                            info[f"{prefix} – VRAM (GB)"] = str(ram_gb)
                        except Exception:
                            pass
                        info[f"{prefix} – Driver"] = current.get("Driver", "N/A")
                        info[f"{prefix} – Stato"]  = current.get("Status", "N/A")
                        gpu_index += 1
                        current = {}
                elif "=" in line:
                    k, _, v = line.partition("=")
                    current[k.strip()] = v.strip()

    if not any("GPU" in k for k in info):
        info["GPU"] = "Nessuna GPU rilevata dai metodi disponibili"

    return info

def collect_motherboard():
    info = {}
    p = parse_wmic("baseboard Manufacturer,Product,Version,SerialNumber")
    if p:
        info["Produttore"] = p.get("Manufacturer", "N/A")
        info["Modello"]    = p.get("Product", "N/A")
        info["Versione"]   = p.get("Version", "N/A")
        info["Seriale"]    = p.get("SerialNumber", "N/A")

    # BIOS — sintassi corretta con i campi DOPO "get"
    try:
        out = subprocess.check_output(
            ["wmic", "bios", "get",
             "Manufacturer,Name,SMBIOSBIOSVersion,ReleaseDate,BIOSVersion",
             "/format:list"],
            stderr=subprocess.DEVNULL, text=True, timeout=10
        )
        b = parse_wmic(out)
        if b:
            info["BIOS – Produttore"] = b.get("Manufacturer", "N/A")
            info["BIOS – Versione"]   = b.get("SMBIOSBIOSVersion",
                                               b.get("BIOSVersion", "N/A"))
            raw_date = b.get("ReleaseDate", "")
            if raw_date and len(raw_date) >= 8:
                # Formato WMIC: 20231205000000.000000+000 → 2023-12-05
                d = raw_date[:8]
                info["BIOS – Data rilascio"] = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            else:
                info["BIOS – Data rilascio"] = "N/A"
    except Exception as e:
        info["BIOS – Errore"] = str(e)

    return info

def run_cmd(args, timeout=15):
    try:
        out = subprocess.check_output(
            args, stderr=subprocess.DEVNULL, timeout=timeout
        )
        # Prova utf-8, poi cp850 (DOS), poi forza con replace
        for enc in ("utf-8", "cp850", "cp1252"):
            try:
                return out.decode(enc)
            except UnicodeDecodeError:
                continue
        return out.decode("utf-8", errors="replace")
    except Exception:
        return ""

def run_ps(cmd, timeout=15):
    try:
        # Forza PowerShell a outputtare UTF-8
        ps_cmd = (
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
            "[Console]::InputEncoding  = [System.Text.Encoding]::UTF8; "
            + cmd
        )
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            stderr=subprocess.DEVNULL, timeout=timeout
        )
        return out.decode("utf-8", errors="replace")
    except Exception:
        return ""

def wmic(alias, fields=""):
    try:
        cmd = ["wmic"] + alias.split()
        if fields:
            cmd += ["get", fields, "/format:list"]
        else:
            cmd += ["get", "/format:list"]
        out = subprocess.check_output(
            cmd, stderr=subprocess.DEVNULL, timeout=10
        )
        # WMIC su Windows italiano può usare utf-16
        for enc in ("utf-16", "utf-8", "cp1252"):
            try:
                return out.decode(enc)
            except (UnicodeDecodeError, UnicodeError):
                continue
        return out.decode("utf-8", errors="replace")
    except Exception:
        return ""

def parse_colon_block(text):
    objects = []
    current = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            if current:
                objects.append(current)
                current = {}
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k:
                current[k] = v
    if current:
        objects.append(current)
    return objects

def collect_network():
    info = {}

    # ── 1. HOSTNAME & DOMINIO ──────────────────────────────────────────────
    info["Hostname"] = socket.gethostname()
    try:
        info["FQDN"] = socket.getfqdn()
    except Exception:
        info["FQDN"] = "N/A"

    comp = parse_wmic("computersystem Name,Domain,Workgroup,PartOfDomain,DNSHostName")
    if comp:
        info["Dominio / Workgroup"] = comp.get("Domain", comp.get("Workgroup", "N/A"))
        info["Parte di un dominio"] = comp.get("PartOfDomain", "N/A")
        info["DNS Hostname"] = comp.get("DNSHostName", "N/A")

    # ── 2. IPCONFIG /ALL (blocchi per interfaccia) ─────────────────────────
    ipconfig_out = run_cmd(["ipconfig", "/all"])
    current_iface = None
    iface_data = {}

    for line in ipconfig_out.splitlines():
        if line and not line.startswith(" ") and ":" in line:
            current_iface = line.strip().rstrip(":")
            iface_data[current_iface] = {}
        elif current_iface and "." in line and ":" in line:
            k, _, v = line.strip().partition(":")
            k = k.strip().rstrip(".")
            v = v.strip()
            if k and v:
                iface_data[current_iface][k] = v

    for iface, fields in iface_data.items():
        prefix = f"[{iface}]"
        for k, v in fields.items():
            info[f"{prefix} {k}"] = v

    # ── 3. POWERSHELL – Get-NetAdapter (per ogni adattatore) ──────────────
    ps_adapters = run_ps(
        "Get-NetAdapter | Select-Object Name,InterfaceDescription,MacAddress,"
        "Status,LinkSpeed,MediaType,PhysicalMediaType,DriverName,DriverVersion,"
        "DriverDate,FullDuplex,MtuSize,VlanID,HardwareInterface,"
        "NdisVersion,AdminStatus,PromiscuousMode | ConvertTo-Csv -NoTypeInformation"
    )
    if ps_adapters:
        lines = [l for l in ps_adapters.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            for row in lines[1:]:
                vals = [v.strip('"') for v in row.split(",")]
                d = dict(zip(headers, vals))
                name = d.get("Name", "Adattatore")
                prefix = f"[{name}] NIC"
                for k, v in d.items():
                    if k != "Name" and v and v != "":
                        info[f"{prefix} – {k}"] = v

    # ── 4. POWERSHELL – Get-NetIPConfiguration (IP/GW/DNS per interfaccia) ─
    ps_ipcfg = run_ps(
        "Get-NetIPConfiguration | ForEach-Object {"
        "  $n = $_.InterfaceAlias;"
        "  $_.AllIPAddresses | ForEach-Object { \"$n|IPAddress|\" + $_.IPAddress };"
        "  \"$n|DefaultGateway|\" + $_.IPv4DefaultGateway.NextHop;"
        "  $_.DNSServer | ForEach-Object { \"$n|DNS|\" + $_.ServerAddresses };"
        "}"
    )
    for line in ps_ipcfg.splitlines():
        parts = line.strip().split("|")
        if len(parts) == 3:
            iface, key, val = parts
            if val and val.strip():
                info[f"[{iface.strip()}] {key}"] = val.strip()

    # ── 5. POWERSHELL – Get-NetIPAddress (tutti gli indirizzi) ────────────
    ps_ipaddr = run_ps(
        "Get-NetIPAddress | Select-Object InterfaceAlias,AddressFamily,"
        "IPAddress,PrefixLength,PrefixOrigin,SuffixOrigin,AddressState,"
        "ValidLifetime,PreferredLifetime | ConvertTo-Csv -NoTypeInformation"
    )
    if ps_ipaddr:
        lines = [l for l in ps_ipaddr.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            for row in lines[1:]:
                vals = [v.strip('"') for v in row.split(",")]
                d = dict(zip(headers, vals))
                iface = d.get("InterfaceAlias", "?")
                ip    = d.get("IPAddress", "?")
                af    = d.get("AddressFamily", "")
                prefix_len = d.get("PrefixLength", "")
                origin = d.get("PrefixOrigin", "")
                state  = d.get("AddressState", "")
                info[f"[{iface}] IP {af} {ip}/{prefix_len}"] = f"Origine: {origin}, Stato: {state}"

    # ── 6. POWERSHELL – Get-NetRoute (tabella di routing) ─────────────────
    ps_routes = run_ps(
        "Get-NetRoute | Where-Object {$_.RouteMetric -lt 999} | "
        "Select-Object InterfaceAlias,DestinationPrefix,NextHop,RouteMetric,Protocol | "
        "ConvertTo-Csv -NoTypeInformation"
    )
    if ps_routes:
        lines = [l for l in ps_routes.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            for i, row in enumerate(lines[1:]):
                vals = [v.strip('"') for v in row.split(",")]
                d = dict(zip(headers, vals))
                iface = d.get("InterfaceAlias", "?")
                dst   = d.get("DestinationPrefix", "?")
                nh    = d.get("NextHop", "?")
                met   = d.get("RouteMetric", "?")
                proto = d.get("Protocol", "?")
                info[f"[Route {i}] {dst}"] = f"Via: {nh}, Iface: {iface}, Metric: {met}, Proto: {proto}"

    # ── 7. POWERSHELL – Get-DnsClient (suffissi DNS) ──────────────────────
    ps_dns = run_ps(
        "Get-DnsClient | Select-Object InterfaceAlias,ConnectionSpecificSuffix,"
        "RegisterThisConnectionsAddress,UseSuffixWhenRegistering | "
        "ConvertTo-Csv -NoTypeInformation"
    )
    if ps_dns:
        lines = [l for l in ps_dns.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            for row in lines[1:]:
                vals = [v.strip('"') for v in row.split(",")]
                d = dict(zip(headers, vals))
                iface = d.get("InterfaceAlias", "?")
                suffix = d.get("ConnectionSpecificSuffix", "")
                reg    = d.get("RegisterThisConnectionsAddress", "")
                if suffix or reg:
                    info[f"[{iface}] DNS Suffix"] = suffix or "—"
                    info[f"[{iface}] DNS RegisterAddress"] = reg

    # ── 8. POWERSHELL – Get-NetAdapterAdvancedProperty (proprietà avanzate)
    ps_adv = run_ps(
        "Get-NetAdapterAdvancedProperty | "
        "Select-Object Name,DisplayName,DisplayValue | "
        "ConvertTo-Csv -NoTypeInformation"
    )
    if ps_adv:
        lines = [l for l in ps_adv.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            for row in lines[1:]:
                vals = [v.strip('"') for v in row.split(",")]
                d = dict(zip(headers, vals))
                name  = d.get("Name", "?")
                prop  = d.get("DisplayName", "?")
                value = d.get("DisplayValue", "")
                if prop and value:
                    info[f"[{name}] Avanzate – {prop}"] = value

    # ── 9. POWERSHELL – TCP Global Settings ───────────────────────────────
    ps_tcp = run_ps(
        "Get-NetTCPSetting | Select-Object SettingName,InitialCongestionWindow,"
        "CongestionProvider,CwndRestart,DelayedAckTimeout,DelayedAckFrequency,"
        "MemoryPressureProtection,AutoTuningLevelLocal,AutoTuningLevelGroupPolicy,"
        "ScalingHeuristics,Timestamps,InitialRto,MaxSynRetransmissions,"
        "MinRto,MaxRetransmissions | ConvertTo-Csv -NoTypeInformation"
    )
    if ps_tcp:
        lines = [l for l in ps_tcp.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            for row in lines[1:]:
                vals = [v.strip('"') for v in row.split(",")]
                d = dict(zip(headers, vals))
                sname = d.get("SettingName", "TCP")
                for k, v in d.items():
                    if k != "SettingName" and v:
                        info[f"[TCP:{sname}] {k}"] = v

    # ── 10. NETSH – Impostazioni globali IP ───────────────────────────────
    ns_global = run_cmd(["netsh", "interface", "ip", "show", "global"])
    for line in ns_global.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k and v:
                info[f"[IP Globale] {k}"] = v

    # ── 11. NETSH – Impostazioni globali TCP ──────────────────────────────
    ns_tcp = run_cmd(["netsh", "interface", "tcp", "show", "global"])
    for line in ns_tcp.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k and v:
                info[f"[TCP Globale] {k}"] = v

    # ── 12. NETSH – Chimney Offload / RSS / NetDMA ────────────────────────
    for subcmd, label in [
        (["netsh", "interface", "tcp", "show", "supplemental"], "TCP Supplemental"),
        (["netsh", "int", "ipv4", "show", "dynamicport", "tcp"], "Porte dinamiche TCP"),
        (["netsh", "int", "ipv4", "show", "dynamicport", "udp"], "Porte dinamiche UDP"),
        (["netsh", "int", "ipv6", "show", "global"],             "IPv6 Globale"),
    ]:
        out = run_cmd(subcmd)
        for line in out.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                k, v = k.strip(), v.strip()
                if k and v:
                    info[f"[{label}] {k}"] = v

    # ── 13. PROXY (netsh winhttp) ─────────────────────────────────────────
    ns_proxy = run_cmd(["netsh", "winhttp", "show", "proxy"])
    for line in ns_proxy.splitlines():
        line = line.strip()
        if line:
            info[f"[Proxy WinHTTP] {line[:60]}"] = ""

    # ── 14. FIREWALL (tutti i profili) ────────────────────────────────────
    ps_fw = run_ps(
        "Get-NetFirewallProfile | Select-Object Name,Enabled,DefaultInboundAction,"
        "DefaultOutboundAction,LogBlocked,LogAllowed,LogFileName,LogMaxSizeKilobytes,"
        "NotifyOnListen,AllowInboundRules,AllowLocalFirewallRules | "
        "ConvertTo-Csv -NoTypeInformation"
    )
    if ps_fw:
        lines = [l for l in ps_fw.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            for row in lines[1:]:
                vals = [v.strip('"') for v in row.split(",")]
                d = dict(zip(headers, vals))
                prof = d.get("Name", "FW")
                for k, v in d.items():
                    if k != "Name" and v:
                        info[f"[Firewall:{prof}] {k}"] = v

    # ── 15. Wi-Fi (se presente) ───────────────────────────────────────────
    wlan_ifaces = run_cmd(["netsh", "wlan", "show", "interfaces"])
    if "SSID" in wlan_ifaces or "Nome" in wlan_ifaces:
        for line in wlan_ifaces.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                k, v = k.strip(), v.strip()
                if k and v:
                    info[f"[Wi-Fi] {k}"] = v

        # Driver Wi-Fi
        wlan_driver = run_cmd(["netsh", "wlan", "show", "drivers"])
        for line in wlan_driver.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                k, v = k.strip(), v.strip()
                if k and v:
                    info[f"[Wi-Fi Driver] {k}"] = v

    # ── 16. Statistiche I/O di rete ──────────────────────────────────────
    net_io = psutil.net_io_counters(pernic=True)
    for iface, counters in net_io.items():
        info[f"[{iface}] Bytes inviati"] = str(bytes_to_gb(counters.bytes_sent)) + " GB"
        info[f"[{iface}] Bytes ricevuti"] = str(bytes_to_gb(counters.bytes_recv)) + " GB"
        info[f"[{iface}] Pacchetti inviati"] = str(counters.packets_sent)
        info[f"[{iface}] Pacchetti ricevuti"] = str(counters.packets_recv)
        info[f"[{iface}] Errori TX"] = str(counters.errout)
        info[f"[{iface}] Errori RX"] = str(counters.errin)
        info[f"[{iface}] Drop TX"] = str(counters.dropout)

    # ── 17. Connessioni attive (porte in ascolto) ─────────────────────────
    try:
        conns = psutil.net_connections(kind="inet")
        listening = [(c.laddr.ip, c.laddr.port, c.type) for c in conns if c.status == "LISTEN"]
        listening_sorted = sorted(set(listening), key=lambda x: x[1])
        ports_str = ", ".join(str(p) for _, p, _ in listening_sorted[:30])
        info["[Porte in ascolto]"] = ports_str or "Nessuna"
    except Exception:
        pass

    return info

def collect_power():
    info = {}
    # Piano energetico attivo
    try:
        out = subprocess.check_output(
            ["powercfg", "/getactivescheme"], text=True, stderr=subprocess.DEVNULL
        )
        info["Piano energetico attivo"] = out.strip()
    except Exception:
        info["Piano energetico attivo"] = "N/A"

    # Batteria
    bat = psutil.sensors_battery()
    if bat:
        info["Batteria (%)"] = str(bat.percent)
        info["In carica"] = str(bat.power_plugged)
        info["Autonomia rimanente (min)"] = str(bat.secsleft // 60) if bat.secsleft != psutil.POWER_TIME_UNLIMITED else "In carica"
    else:
        info["Batteria"] = "Nessuna (PC desktop)"
    return info

def collect_system_settings():
    info = {}
    # Variabili d'ambiente importanti
    for var in ["COMPUTERNAME", "OS", "PROCESSOR_ARCHITECTURE", "PROCESSOR_IDENTIFIER",
                "NUMBER_OF_PROCESSORS", "TEMP", "SystemDrive", "SystemRoot",
                "USERDOMAIN", "USERDNSDOMAIN"]:
        val = os.environ.get(var, "N/A")
        if val != "N/A":
            info[f"ENV: {var}"] = val

    # Fuso orario
    try:
        import time
        info["Fuso orario"] = str(datetime.datetime.now().astimezone().tzinfo)
    except Exception:
        pass

    # Locale
    try:
        import locale
        info["Locale sistema"] = locale.getlocale()[0] or locale.getencoding() or "N/A"
    except Exception:
        pass

    # Lingua sistema via WMIC
    try:
        p = parse_wmic("os Locale,CodeSet,CountryCode,MUILanguages")
        if p:
            info["Locale (hex)"] = p.get("Locale", "N/A")
            info["Codeset"] = p.get("CodeSet", "N/A")
            info["Paese"] = p.get("CountryCode", "N/A")
    except Exception:
        pass
    return info
    
def collect_smb_cpu_diag():
    info = {}

    # ── 1. SMB CLIENT ───────────────
    ps_smb_client = run_ps(
        "Get-SmbClientConfiguration | Select-Object "
        "EnableBandwidthThrottling,EnableByteRangeLockingOnReadOnlyFiles,"
        "EnableLargeMtu,EnableMultiChannel,EnableSecuritySignature,"
        "RequireSecuritySignature,UseOpportunisticLocking,"
        "WindowSizeThreshold,DirectoryCacheLifetime,FileInfoCacheLifetime,"
        "FileNotFoundCacheLifetime,MaxCmdsSets,MaxDatagramSize,"
        "OplocksDisabled,SessionTimeout,DormantFileLimit,"
        "EnableLoadBalanceScaleOut,KeepConn,MaxThreadsPerQueue,"
        "DisableCompression | ConvertTo-Csv -NoTypeInformation"
    )
    if ps_smb_client and ps_smb_client.strip():
        lines = [l for l in ps_smb_client.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            vals    = [v.strip('"') for v in lines[1].split(",")]
            for k, v in zip(headers, vals):
                info[f"[SMB Client] {k}"] = v

    # ── 2. SMB SERVER (se questo PC condivide cartelle) ───────────────────
    ps_smb_server = run_ps(
        "Get-SmbServerConfiguration | Select-Object "
        "EnableSMB1Protocol,EnableSMB2Protocol,RequireSecuritySignature,"
        "EnableSecuritySignature,EncryptData,EnableMultiChannel,"
        "MaxChannelPerSession,ServerHidden,AnnounceServer,"
        "EnableLeasing,EnableOplocks,EnableFcb,"
        "AsynchronousCredits,MaxWorkItems,MaxMpxCount,"
        "DisableCompression | ConvertTo-Csv -NoTypeInformation"
    )
    if ps_smb_server and ps_smb_server.strip():
        lines = [l for l in ps_smb_server.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            vals    = [v.strip('"') for v in lines[1].split(",")]
            for k, v in zip(headers, vals):
                info[f"[SMB Server] {k}"] = v

    # ── 3. SMB CONNESSIONI ATTIVE (versione protocollo negoziata) ─────────
    ps_smb_conn = run_ps(
        "Get-SmbConnection | Select-Object ServerName,ShareName,"
        "Dialect,NumOpens,SmbInstance | ConvertTo-Csv -NoTypeInformation"
    )
    if ps_smb_conn and ps_smb_conn.strip():
        lines = [l for l in ps_smb_conn.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            for i, row in enumerate(lines[1:]):
                vals = [v.strip('"') for v in row.split(",")]
                d = dict(zip(headers, vals))
                srv = d.get("ServerName", f"conn{i}")
                for k, v in d.items():
                    if k != "ServerName":
                        info[f"[SMB Conn {srv}] {k}"] = v

    # ── 4. TCP OFFLOAD / RSS / CHIMNEY (causa principale di blocco CPU) ───
    ps_rss = run_ps(
        "Get-NetAdapterRss | Select-Object Name,Enabled,"
        "NumberOfReceiveQueues,MaxProcessors,"
        "BaseProcessorNumber,MaxProcessorNumber,"
        "NumaNode,Profile | ConvertTo-Csv -NoTypeInformation"
    )
    if ps_rss and ps_rss.strip():
        lines = [l for l in ps_rss.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            for row in lines[1:]:
                vals = [v.strip('"') for v in row.split(",")]
                d = dict(zip(headers, vals))
                name = d.get("Name", "NIC")
                for k, v in d.items():
                    if k != "Name":
                        info[f"[RSS:{name}] {k}"] = v

    # Offload (LSO, checksum, IPsec)
    ps_offload = run_ps(
        "Get-NetAdapterChecksumOffload | "
        "Select-Object Name,IpIPv4Enabled,TcpIPv4Enabled,"
        "TcpIPv6Enabled,UdpIPv4Enabled,UdpIPv6Enabled | "
        "ConvertTo-Csv -NoTypeInformation"
    )
    if ps_offload and ps_offload.strip():
        lines = [l for l in ps_offload.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            for row in lines[1:]:
                vals = [v.strip('"') for v in row.split(",")]
                d = dict(zip(headers, vals))
                name = d.get("Name", "NIC")
                for k, v in d.items():
                    if k != "Name":
                        info[f"[Checksum Offload:{name}] {k}"] = v

    ps_lso = run_ps(
        "Get-NetAdapterLso | Select-Object Name,"
        "IPv4Enabled,IPv6Enabled | ConvertTo-Csv -NoTypeInformation"
    )
    if ps_lso and ps_lso.strip():
        lines = [l for l in ps_lso.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            for row in lines[1:]:
                vals = [v.strip('"') for v in row.split(",")]
                d = dict(zip(headers, vals))
                name = d.get("Name", "NIC")
                for k, v in d.items():
                    if k != "Name":
                        info[f"[LSO:{name}] {k}"] = v

    # ── 5. INTERRUPT MODERATION & AFFINITÀ CPU ───────────────────────────
    ps_intr = run_ps(
        "Get-NetAdapterAdvancedProperty | "
        "Where-Object { $_.DisplayName -match "
        "'Interrupt|Moderation|Affinity|Coalescing|DPC|Throttl|RSS|Queue|Buffer' } | "
        "Select-Object Name,DisplayName,DisplayValue | "
        "ConvertTo-Csv -NoTypeInformation"
    )
    if ps_intr and ps_intr.strip():
        lines = [l for l in ps_intr.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            for row in lines[1:]:
                vals = [v.strip('"') for v in row.split(",")]
                d = dict(zip(headers, vals))
                name = d.get("Name", "NIC")
                prop = d.get("DisplayName", "?")
                val  = d.get("DisplayValue", "")
                if prop and val:
                    info[f"[Interrupt:{name}] {prop}"] = val

    # ── 6. POWER PLAN DETTAGLIATO (C-States, CPU throttling) ─────────────
    pw_active = run_cmd(["powercfg", "/getactivescheme"])
    info["[Power] Piano attivo"] = (pw_active or "").strip()

    pw_proc = run_ps(
        "$guid = (powercfg /getactivescheme) -replace '.*GUID: ([\\w-]+).*','$1';"
        "powercfg /query $guid.Trim() 54533251-82be-4824-96c1-47b60b740d00"
    )
    for line in (pw_proc or "").splitlines():
        line = line.strip()
        if ":" in line and "Impostazione" in line or "Setting" in line or "Current" in line:
            k, _, v = line.partition(":")
            info[f"[Power CPU] {k.strip()}"] = v.strip()

    # Stato C-States / parking
    pw_park = run_ps(
        "$a = (powercfg /getactivescheme) -replace '.*GUID: ([\\w-]+).*','$1';"
        "powercfg /query $a.Trim() 54533251-82be-4824-96c1-47b60b740d00 "
        "0cc5b647-c1df-4637-891a-dec35c318583"
    )
    info["[Power] CPU Parking"] = (pw_park or "N/A").strip()[:200]

    # ── 7. REGISTRY – impostazioni critiche rete ─────────────
    reg_keys = [
        (r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
         "NetworkThrottlingIndex",   "NetworkThrottlingIndex"),
        (r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
         "SystemResponsiveness",     "SystemResponsiveness"),
        (r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
         "LargeSystemCache",         "LargeSystemCache"),
        (r"HKLM\SOFTWARE\Microsoft\MSMQ\Parameters",
         "TCPNoDelay",               "MSMQ TCPNoDelay"),
        (r"HKLM\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters",
         "MaxCmds",                  "SMB MaxCmds"),
        (r"HKLM\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters",
         "MaxThreads",               "SMB MaxThreads"),
        (r"HKLM\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters",
         "DisableBandwidthThrottling","SMB DisableBandwidthThrottling"),
        (r"HKLM\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters",
         "DisableLargeMtu",          "SMB DisableLargeMtu"),
        (r"HKLM\SYSTEM\CurrentControlSet\Services\NDIS\Parameters",
         "MaxNumRssCpus",            "NDIS MaxNumRssCpus"),
        (r"HKLM\SOFTWARE\Microsoft\Windows Defender\Real-Time Protection",
         "DisableRealtimeMonitoring","Defender RealtimeMonitoring disabilitato"),
        (r"HKLM\SOFTWARE\Microsoft\Windows Defender\Real-Time Protection",
         "DisableIOAVProtection",    "Defender IOAVProtection disabilitato"),
        (r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
         "TdrLevel",                 "TDR Level (GPU timeout)"),
        (r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters",
         "TcpAckFrequency",          "TCP AckFrequency"),
        (r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters",
         "TCPNoDelay",               "TCP NoDelay (Nagle off)"),
        (r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters",
         "DefaultTTL",               "TCP DefaultTTL"),
        (r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters",
         "Tcp1323Opts",              "TCP 1323 Options (timestamps/ws)"),
        (r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters",
         "GlobalMaxTcpWindowSize",   "TCP GlobalMaxWindowSize"),
    ]

    for reg_path, value_name, label in reg_keys:
        try:
            out = run_cmd(["reg", "query", reg_path, "/v", value_name])
            for line in (out or "").splitlines():
                if value_name in line:
                    parts = line.strip().split()
                    val = parts[-1] if parts else "N/A"
                    info[f"[Registry] {label}"] = val
                    break
            else:
                info[f"[Registry] {label}"] = "non impostato (default)"
        except Exception:
            info[f"[Registry] {label}"] = "N/A"

    # ── 8. WINDOWS DEFENDER – esclusioni percorsi di rete ─────────────────
    ps_excl = run_ps(
        "(Get-MpPreference).ExclusionPath -join ', '"
    )
    info["[Defender] Esclusioni percorsi"] = (ps_excl or "Nessuna").strip()

    ps_excl_proc = run_ps(
        "(Get-MpPreference).ExclusionProcess -join ', '"
    )
    info["[Defender] Esclusioni processi"] = (ps_excl_proc or "Nessuna").strip()

    # ── 9. OFFLINE FILES / CLIENT SIDE CACHING ───────────────────────────
    try:
        out = run_cmd(["reg", "query",
            r"HKLM\SYSTEM\CurrentControlSet\Services\CSC\Parameters"])
        info["[Offline Files] Configurazione"] = (out or "Non configurato").strip()[:300]
    except Exception:
        info["[Offline Files] Configurazione"] = "N/A"

    # ── 10. QoS THROTTLING ────────────────────────────────────────────────
    ps_qos = run_ps(
        "Get-NetQosPolicy | Select-Object Name,PriorityValue,"
        "IPProtocol,AppPathNameMatchCondition | "
        "ConvertTo-Csv -NoTypeInformation"
    )
    if ps_qos and ps_qos.strip():
        lines = [l for l in ps_qos.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            for i, row in enumerate(lines[1:]):
                vals = [v.strip('"') for v in row.split(",")]
                d = dict(zip(headers, vals))
                name = d.get("Name", f"QoS{i}")
                for k, v in d.items():
                    if k != "Name" and v:
                        info[f"[QoS:{name}] {k}"] = v
    else:
        info["[QoS] Policy attive"] = "Nessuna"

    # ── 11. MMCSS (Multimedia Class Scheduler) ────────────────────────────
    ps_mmcss = run_ps(
        "Get-ItemProperty "
        "'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\*' "
        "| Select-Object PSChildName,Priority,Scheduling,SFIO,BackgroundPriority,"
        "'Clock Rate','GPU Priority','Latency Sensitive' | "
        "ConvertTo-Csv -NoTypeInformation"
    )
    if ps_mmcss and ps_mmcss.strip():
        lines = [l for l in ps_mmcss.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip('"') for h in lines[0].split(",")]
            for row in lines[1:]:
                vals = [v.strip('"') for v in row.split(",")]
                d = dict(zip(headers, vals))
                task = d.get("PSChildName", "task")
                for k, v in d.items():
                    if k != "PSChildName" and v:
                        info[f"[MMCSS:{task}] {k}"] = v

    return info

def full_scan():
    data = {
        "meta": {
            "data_scansione": datetime.datetime.now().isoformat(),
            "hostname": socket.gethostname()
        },
        "Sistema Operativo": collect_os(),
        "CPU": collect_cpu(),
        "RAM": collect_ram(),
        "Dischi": collect_disk(),
        "GPU": collect_gpu(),
        "Scheda Madre & BIOS": collect_motherboard(),
        "Rete": collect_network(),
        "Alimentazione": collect_power(),
        "Impostazioni Sistema": collect_system_settings(),
        "Diagnosi Copia di Rete": collect_smb_cpu_diag(),
    }
    return data

# ─── Confronto ────────────────────────────────────────────────────────────────

def compare_scans(scan_a, scan_b):
    result = {}
    all_cats = set(list(scan_a.keys()) + list(scan_b.keys())) - {"meta"}
    for cat in sorted(all_cats):
        a_cat = scan_a.get(cat, {})
        b_cat = scan_b.get(cat, {})
        all_keys = set(list(a_cat.keys()) + list(b_cat.keys()))
        result[cat] = {}
        for k in sorted(all_keys):
            va = a_cat.get(k, "—")
            vb = b_cat.get(k, "—")
            result[cat][k] = (str(va), str(vb), va == vb)
    return result

# ─── GUI ──────────────────────────────────────────────────────────────────────

class PCInspectorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PC Inspector & Comparator")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(bg=BG)
        self.resizable(True, True)

        self.scan_a = None
        self.scan_b = None

        self._style()
        self._build_header()
        self._build_tabs()
        self._build_status()

    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")

        s.configure(".",
            background=BG, foreground=TEXT,
            font=FONT, fieldbackground=PANEL,
            troughcolor=PANEL, bordercolor=BORDER,
            darkcolor=PANEL, lightcolor=PANEL,
            relief="flat"
        )
        s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=[0, 0, 0, 0])
        s.configure("TNotebook.Tab",
            background=PANEL, foreground=MUTED, padding=[16, 8],
            font=FONT_B, borderwidth=0
        )
        s.map("TNotebook.Tab",
            background=[("selected", BG)],
            foreground=[("selected", ACCENT)],
        )
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=TEXT)
        s.configure("TButton",
            background=ACCENT, foreground="#0d1117",
            font=FONT_B, relief="flat", padding=[14, 7],
            borderwidth=0
        )
        s.map("TButton",
            background=[("active", "#79c0ff"), ("pressed", "#388bfd")],
        )
        s.configure("Danger.TButton",
            background="#da3633", foreground=TEXT,
        )
        s.map("Danger.TButton",
            background=[("active", "#f85149")],
        )
        s.configure("TScrollbar",
            background=BORDER, troughcolor=PANEL, arrowcolor=MUTED, relief="flat"
        )
        s.configure("Treeview",
            background=PANEL, foreground=TEXT, fieldbackground=PANEL,
            font=FONT_SM, rowheight=22, borderwidth=0,
        )
        s.configure("Treeview.Heading",
            background=BORDER, foreground=ACCENT, font=FONT_B,
            relief="flat", padding=[6, 4]
        )
        s.map("Treeview",
            background=[("selected", "#1f2d3d")],
            foreground=[("selected", ACCENT)]
        )

    def _build_header(self):
        hdr = tk.Frame(self, bg=PANEL, height=54)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="⚙  PC Inspector & Comparator",
                 bg=PANEL, fg=ACCENT, font=("Consolas", 14, "bold")).pack(side="left", padx=20)

        ver = tk.Label(hdr, text="v1.0 · Windows Edition - By Andrea Cefalù",
                       bg=PANEL, fg=MUTED, font=FONT_SM)
        ver.pack(side="right", padx=20)

        # Separatore
        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill="x")

    def _build_tabs(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=0, pady=0)

        self.tab_scan   = ttk.Frame(self.nb)
        self.tab_compare = ttk.Frame(self.nb)

        self.nb.add(self.tab_scan,    text="  🖥  Scansiona PC  ")
        self.nb.add(self.tab_compare, text="  🔍  Confronta PC  ")

        self._build_scan_tab()
        self._build_compare_tab()

    def _build_scan_tab(self):
        f = self.tab_scan

        # Barra azioni
        bar = tk.Frame(f, bg=BG)
        bar.pack(fill="x", padx=20, pady=14)

        ttk.Button(bar, text="⚡  Scansiona questo PC", command=self._do_scan).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="💾  Salva JSON", command=self._save_scan).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="📂  Carica JSON", command=self._load_scan_a).pack(side="left")

        self.scan_info_label = tk.Label(bar, text="Nessuna scansione effettuata", bg=BG, fg=MUTED, font=FONT_SM)
        self.scan_info_label.pack(side="right", padx=10)

        # Barra progressso
        self.progress = ttk.Progressbar(f, mode="indeterminate", length=200)

        # Contenuto: Treeview con categorie e dettagli
        pane = tk.Frame(f, bg=BG)
        pane.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        # Lista categorie
        left = tk.Frame(pane, bg=PANEL, width=180, relief="flat",
                        highlightthickness=1, highlightbackground=BORDER)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        tk.Label(left, text="CATEGORIE", bg=PANEL, fg=MUTED,
                 font=("Consolas", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 4))

        self.cat_list = tk.Listbox(left, bg=PANEL, fg=TEXT, font=FONT,
                                   selectbackground="#1f2d3d", selectforeground=ACCENT,
                                   borderwidth=0, highlightthickness=0,
                                   activestyle="none", relief="flat")
        self.cat_list.pack(fill="both", expand=True, padx=2, pady=(0, 6))
        self.cat_list.bind("<<ListboxSelect>>", self._on_cat_select)

        # Dettagli
        right = tk.Frame(pane, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        # Treeview per i dati
        cols = ("chiave", "valore")
        self.detail_tree = ttk.Treeview(right, columns=cols, show="headings",
                                         selectmode="browse")
        self.detail_tree.heading("chiave", text="Impostazione")
        self.detail_tree.heading("valore", text="Valore")
        self.detail_tree.column("chiave", width=280, minwidth=160)
        self.detail_tree.column("valore", width=500, minwidth=200)

        vsb = ttk.Scrollbar(right, orient="vertical", command=self.detail_tree.yview)
        self.detail_tree.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        self.detail_tree.pack(side="left", fill="both", expand=True)

    def _build_compare_tab(self):
        f = self.tab_compare

        # Barra azioni
        bar = tk.Frame(f, bg=BG)
        bar.pack(fill="x", padx=20, pady=14)

        # PC A
        fa = tk.Frame(bar, bg=BG)
        fa.pack(side="left", padx=(0, 16))
        tk.Label(fa, text="PC A:", bg=BG, fg=ACCENT, font=FONT_B).pack(side="left", padx=(0, 6))
        self.lbl_a = tk.Label(fa, text="Non caricato", bg=BG, fg=MUTED, font=FONT_SM)
        self.lbl_a.pack(side="left")
        ttk.Button(fa, text="📂 Carica", command=self._load_a).pack(side="left", padx=(8, 0))

        # PC B
        fb = tk.Frame(bar, bg=BG)
        fb.pack(side="left", padx=(0, 16))
        tk.Label(fb, text="PC B:", bg=BG, fg="#f0883e", font=FONT_B).pack(side="left", padx=(0, 6))
        self.lbl_b = tk.Label(fb, text="Non caricato", bg=BG, fg=MUTED, font=FONT_SM)
        self.lbl_b.pack(side="left")
        ttk.Button(fb, text="📂 Carica", command=self._load_b).pack(side="left", padx=(8, 0))

        ttk.Button(bar, text="🔍  Confronta!", command=self._do_compare).pack(side="left", padx=(8, 0))

        # Legenda
        leg = tk.Frame(bar, bg=BG)
        leg.pack(side="right", padx=10)
        for color, text in [(GREEN, "Identico"), (RED, "Diverso"), (YELLOW, "Solo in uno")]:
            dot = tk.Label(leg, text="●", bg=BG, fg=color, font=("Consolas", 12))
            dot.pack(side="left")
            tk.Label(leg, text=text + "  ", bg=BG, fg=MUTED, font=FONT_SM).pack(side="left")

        # Filtro
        filter_bar = tk.Frame(f, bg=BG)
        filter_bar.pack(fill="x", padx=20, pady=(0, 8))

        tk.Label(filter_bar, text="Mostra:", bg=BG, fg=MUTED, font=FONT_SM).pack(side="left")
        self.filter_var = tk.StringVar(value="all")
        for val, txt in [("all", "Tutto"), ("diff", "Solo differenze"), ("same", "Solo uguali")]:
            rb = tk.Radiobutton(filter_bar, text=txt, variable=self.filter_var, value=val,
                                bg=BG, fg=MUTED, selectcolor=PANEL, activebackground=BG,
                                activeforeground=TEXT, font=FONT_SM, relief="flat",
                                command=self._apply_filter)
            rb.pack(side="left", padx=(8, 0))

        self.diff_count_lbl = tk.Label(filter_bar, text="", bg=BG, fg=MUTED, font=FONT_SM)
        self.diff_count_lbl.pack(side="right", padx=10)

        # Treeview confronto
        cols = ("categoria", "chiave", "pc_a", "pc_b")
        self.cmp_tree = ttk.Treeview(f, columns=cols, show="headings", selectmode="browse")
        self.cmp_tree.heading("categoria", text="Categoria")
        self.cmp_tree.heading("chiave",    text="Impostazione")
        self.cmp_tree.heading("pc_a",      text="PC A")
        self.cmp_tree.heading("pc_b",      text="PC B")
        self.cmp_tree.column("categoria", width=140, minwidth=100)
        self.cmp_tree.column("chiave",    width=220, minwidth=140)
        self.cmp_tree.column("pc_a",      width=320, minwidth=160)
        self.cmp_tree.column("pc_b",      width=320, minwidth=160)

        # Tag colori
        self.cmp_tree.tag_configure("same",    foreground=GREEN)
        self.cmp_tree.tag_configure("diff",    foreground=RED)
        self.cmp_tree.tag_configure("missing", foreground=YELLOW)
        self.cmp_tree.tag_configure("header",  foreground=ACCENT, font=FONT_B)

        vsb2 = ttk.Scrollbar(f, orient="vertical", command=self.cmp_tree.yview)
        hsb2 = ttk.Scrollbar(f, orient="horizontal", command=self.cmp_tree.xview)
        self.cmp_tree.configure(yscrollcommand=vsb2.set, xscrollcommand=hsb2.set)

        vsb2.pack(side="right", fill="y", padx=(0, 4))
        hsb2.pack(side="bottom", fill="x", padx=20, pady=(0, 6))
        self.cmp_tree.pack(fill="both", expand=True, padx=(20, 0), pady=(0, 0))

        self._cmp_data = {}  # cache per il filtro

    def _build_status(self):
        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill="x")
        sbar = tk.Frame(self, bg=PANEL, height=28)
        sbar.pack(fill="x")
        sbar.pack_propagate(False)

        self.status_var = tk.StringVar(value="Pronto.")
        tk.Label(sbar, textvariable=self.status_var, bg=PANEL, fg=MUTED,
                 font=FONT_SM, anchor="w").pack(side="left", padx=12)

    # ── Azioni ─────────────────────────────────────────────────────────────────

    def _set_status(self, msg, color=None):
        self.status_var.set(msg)
        self.update_idletasks()

    def _do_scan(self):
        self._set_status("Scansione in corso…")
        self.progress.pack(padx=20, pady=4, fill="x")
        self.progress.start(12)

        def worker():
            try:
                data = full_scan()
                self.scan_a = data
                self.after(0, lambda: self._show_scan(data))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Errore", str(e)))
            finally:
                self.after(0, self.progress.stop)
                self.after(0, self.progress.pack_forget)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _show_scan(self, data):
        hostname = data.get("meta", {}).get("hostname", "PC")
        ts = data.get("meta", {}).get("data_scansione", "")[:19]
        self.scan_info_label.config(
            text=f"✓ {hostname}  |  {ts}", fg=GREEN
        )
        self._set_status(f"Scansione completata: {hostname}")

        # Popola lista categorie
        self.cat_list.delete(0, "end")
        cats = [k for k in data if k != "meta"]
        for c in cats:
            self.cat_list.insert("end", f"  {c}")
        if cats:
            self.cat_list.select_set(0)
            self._show_category(data[cats[0]])

    def _on_cat_select(self, event):
        if not self.scan_a:
            return
        sel = self.cat_list.curselection()
        if not sel:
            return
        cat = self.cat_list.get(sel[0]).strip()
        if cat in self.scan_a:
            self._show_category(self.scan_a[cat])

    def _show_category(self, cat_data):
        for row in self.detail_tree.get_children():
            self.detail_tree.delete(row)
        for k, v in cat_data.items():
            self.detail_tree.insert("", "end", values=(k, v))

    def _save_scan(self):
        if not self.scan_a:
            messagebox.showwarning("Attenzione", "Effettua prima una scansione.")
            return
        hostname = self.scan_a.get("meta", {}).get("hostname", "scan")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=f"scan_{hostname}_{ts}.json",
            filetypes=[("JSON", "*.json"), ("Tutti", "*.*")]
        )
        if path:
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(self.scan_a, fp, indent=2, ensure_ascii=False)
            self._set_status(f"Salvato: {path}")
            messagebox.showinfo("Salvato", f"Scansione salvata in:\n{path}")

    def _load_scan_a(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json"), ("Tutti", "*.*")]
        )
        if path:
            with open(path, encoding="utf-8") as fp:
                self.scan_a = json.load(fp)
            self._show_scan(self.scan_a)
            self._set_status(f"Caricato: {path}")

    def _load_a(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json"), ("Tutti", "*.*")]
        )
        if path:
            with open(path, encoding="utf-8") as fp:
                self.scan_a = json.load(fp)
            hostname = self.scan_a.get("meta", {}).get("hostname", "PC A")
            ts = self.scan_a.get("meta", {}).get("data_scansione", "")[:10]
            self.lbl_a.config(text=f"{hostname}  ({ts})", fg=ACCENT)
            self._set_status(f"PC A caricato: {hostname}")

    def _load_b(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json"), ("Tutti", "*.*")]
        )
        if path:
            with open(path, encoding="utf-8") as fp:
                self.scan_b = json.load(fp)
            hostname = self.scan_b.get("meta", {}).get("hostname", "PC B")
            ts = self.scan_b.get("meta", {}).get("data_scansione", "")[:10]
            self.lbl_b.config(text=f"{hostname}  ({ts})", fg="#f0883e")
            self._set_status(f"PC B caricato: {hostname}")

    def _do_compare(self):
        if not self.scan_a or not self.scan_b:
            messagebox.showwarning("Attenzione", "Carica entrambe le scansioni prima di confrontare.")
            return
        self._cmp_data = compare_scans(self.scan_a, self.scan_b)
        self._apply_filter()

    def _apply_filter(self):
        if not self._cmp_data:
            return
        mode = self.filter_var.get()

        for row in self.cmp_tree.get_children():
            self.cmp_tree.delete(row)

        total = diff_count = same_count = missing_count = 0

        for cat, items in self._cmp_data.items():
            cat_rows = []
            for k, (va, vb, equal) in items.items():
                total += 1
                if va == "—" or vb == "—":
                    tag = "missing"
                    missing_count += 1
                elif equal:
                    tag = "same"
                    same_count += 1
                else:
                    tag = "diff"
                    diff_count += 1

                if mode == "all":
                    cat_rows.append((k, va, vb, tag))
                elif mode == "diff" and (tag == "diff" or tag == "missing"):
                    cat_rows.append((k, va, vb, tag))
                elif mode == "same" and tag == "same":
                    cat_rows.append((k, va, vb, tag))

            if cat_rows:
                # Header di categoria
                self.cmp_tree.insert("", "end",
                    values=(f"▸ {cat}", "", "", ""),
                    tags=("header",)
                )
                for k, va, vb, tag in cat_rows:
                    self.cmp_tree.insert("", "end",
                        values=("", k, va, vb),
                        tags=(tag,)
                    )

        self.diff_count_lbl.config(
            text=f"Diversi: {diff_count}  |  Uguali: {same_count}  |  Solo in uno: {missing_count}  |  Totale: {total}"
        )
        self._set_status(f"Confronto: {diff_count} differenze su {total} parametri.")


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        import psutil
    except ImportError:
        print("Installa psutil: pip install psutil")
        sys.exit(1)

    app = PCInspectorApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass
