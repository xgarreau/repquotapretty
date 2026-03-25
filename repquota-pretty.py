#!/usr/bin/env python3
"""
repquota-pretty.py — Affichage lisible de la sortie de repquota -a
Usage:
    repquota -a | repquota-pretty.py
    repquota-pretty.py < repquota_output.txt
    repquota-pretty.py repquota_output.txt
"""

import sys
import re
import argparse


# ── Couleurs ANSI ──────────────────────────────────────────────────────────────

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    YELLOW  = "\033[93m"
    GREEN   = "\033[92m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"

    @classmethod
    def disable(cls):
        for attr in ("RESET", "BOLD", "DIM", "RED", "YELLOW", "GREEN",
                      "CYAN", "MAGENTA", "WHITE", "GRAY"):
            setattr(cls, attr, "")


# ── Conversion tailles ─────────────────────────────────────────────────────────

def human_size(kb: int) -> str:
    """Convertit des Ko en taille lisible."""
    if kb == 0:
        return f"{C.DIM}—{C.RESET}"
    units = [("To", 1024**3), ("Go", 1024**2), ("Mo", 1024), ("Ko", 1)]
    for suffix, divisor in units:
        if kb >= divisor:
            val = kb / divisor
            if val >= 100:
                return f"{val:.0f} {suffix}"
            elif val >= 10:
                return f"{val:.1f} {suffix}"
            else:
                return f"{val:.2f} {suffix}"
    return f"{kb} Ko"


def human_count(n: int) -> str:
    """Nombre de fichiers, lisible."""
    if n == 0:
        return f"{C.DIM}—{C.RESET}"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def pct_bar(used: int, limit: int, width: int = 20) -> str:
    """Barre de progression avec couleur selon le taux."""
    if limit == 0:
        return f"{C.DIM}{'░' * width} illimité{C.RESET}"
    pct = min(used / limit * 100, 100)
    filled = round(pct / 100 * width)
    empty = width - filled

    if pct >= 95:
        color = C.RED
    elif pct >= 80:
        color = C.YELLOW
    else:
        color = C.GREEN

    bar = f"{color}{'█' * filled}{C.GRAY}{'░' * empty}{C.RESET}"
    pct_str = f"{pct:5.1f}%"
    if pct >= 95:
        pct_str = f"{C.RED}{C.BOLD}{pct_str}{C.RESET}"
    elif pct >= 80:
        pct_str = f"{C.YELLOW}{pct_str}{C.RESET}"
    else:
        pct_str = f"{C.GREEN}{pct_str}{C.RESET}"

    return f"{bar} {pct_str}"


# ── Parsing ────────────────────────────────────────────────────────────────────

def parse_repquota(lines: list[str]) -> list[dict]:
    """Parse la sortie de repquota -a."""
    entries = []
    current_device = None
    current_block_grace = None
    current_inode_grace = None

    header_re = re.compile(
        r"\*\*\* Report for (?:user|group) quotas on device (.+)"
    )
    grace_re = re.compile(
        r"Block grace time:\s*(.+?);\s*Inode grace time:\s*(.+)"
    )
    # Format: user  +/-  block_used  block_soft  block_hard  [grace]  file_used  file_soft  file_hard  [grace]
    # Le +/- peut être --, +-, -+ ou ++
    entry_re = re.compile(
        r"^(\S+)\s+([+-][+-])\s+"
        r"(\d+)\s+(\d+)\s+(\d+)\s*"
        r"(\S+)?\s*"
        r"(\d+)\s+(\d+)\s+(\d+)\s*"
        r"(\S+)?\s*$"
    )

    for line in lines:
        line = line.rstrip()

        m = header_re.match(line)
        if m:
            current_device = m.group(1)
            continue

        m = grace_re.match(line)
        if m:
            current_block_grace = m.group(1)
            current_inode_grace = m.group(2)
            continue

        m = entry_re.match(line)
        if m:
            block_flag = m.group(2)[0]  # '+' = over soft limit blocks
            inode_flag = m.group(2)[1]  # '+' = over soft limit inodes

            entries.append({
                "device":       current_device,
                "block_grace_policy": current_block_grace,
                "inode_grace_policy": current_inode_grace,
                "user":         m.group(1),
                "block_over":   block_flag == '+',
                "inode_over":   inode_flag == '+',
                "block_used":   int(m.group(3)),
                "block_soft":   int(m.group(4)),
                "block_hard":   int(m.group(5)),
                "block_grace":  m.group(6) or "",
                "file_used":    int(m.group(7)),
                "file_soft":    int(m.group(8)),
                "file_hard":    int(m.group(9)),
                "file_grace":   m.group(10) or "",
            })

    return entries


# ── Affichage ──────────────────────────────────────────────────────────────────

def print_report(entries: list[dict], sort_by: str = "used", show_zero: bool = False):
    """Affiche le rapport formaté."""
    if not entries:
        print(f"{C.RED}Aucune entrée trouvée. Vérifiez le format d'entrée.{C.RESET}")
        return

    # Grouper par device
    devices: dict[str, list[dict]] = {}
    for e in entries:
        devices.setdefault(e["device"], []).append(e)

    for device, dev_entries in devices.items():
        # Filtrer les entrées sans usage si demandé
        if not show_zero:
            dev_entries = [e for e in dev_entries if e["block_used"] > 0 or e["file_used"] > 0]

        if not dev_entries:
            continue

        # Tri
        if sort_by == "used":
            dev_entries.sort(key=lambda e: e["block_used"], reverse=True)
        elif sort_by == "pct":
            def sort_pct(e):
                if e["block_soft"] > 0:
                    return e["block_used"] / e["block_soft"]
                return -1  # illimité en bas
            dev_entries.sort(key=sort_pct, reverse=True)
        elif sort_by == "name":
            dev_entries.sort(key=lambda e: e["user"])
        elif sort_by == "files":
            dev_entries.sort(key=lambda e: e["file_used"], reverse=True)

        # Totaux
        total_used = sum(e["block_used"] for e in dev_entries)
        total_files = sum(e["file_used"] for e in dev_entries)

        # En-tête device
        print()
        print(f"{C.BOLD}{C.CYAN}{'═' * 90}{C.RESET}")
        print(f"{C.BOLD}{C.CYAN}  📁 {device}{C.RESET}")
        grace_info = dev_entries[0].get("block_grace_policy", "")
        if grace_info:
            print(f"{C.DIM}  Grace: blocs={grace_info}, "
                  f"inodes={dev_entries[0].get('inode_grace_policy', '')}{C.RESET}")
        print(f"{C.DIM}  Total utilisé: {human_size(total_used)} — "
              f"{human_count(total_files)} fichiers — "
              f"{len(dev_entries)} utilisateurs actifs{C.RESET}")
        print(f"{C.BOLD}{C.CYAN}{'═' * 90}{C.RESET}")
        print()

        # En-têtes colonnes
        print(f"  {C.BOLD}{'Utilisateur':<16} {'Utilisé':>10}  "
              f"{'Quota':>10}  {'Espace':^32}  "
              f"{'Fichiers':>10}  {'Quota F.':>10}{C.RESET}")
        print(f"  {C.DIM}{'─' * 16} {'─' * 10}  {'─' * 10}  "
              f"{'─' * 32}  {'─' * 10}  {'─' * 10}{C.RESET}")

        for e in dev_entries:
            user = e["user"]
            b_used = e["block_used"]
            b_soft = e["block_soft"]
            b_hard = e["block_hard"]
            f_used = e["file_used"]
            f_soft = e["file_soft"]

            # Indicateur d'alerte
            alert = ""
            if e["block_over"]:
                alert = f" {C.RED}⚠ DÉPASSÉ{C.RESET}"
                if e["block_grace"]:
                    alert += f" {C.RED}({e['block_grace']}){C.RESET}"

            # Le quota affiché = soft s'il existe, sinon hard
            quota_ref = b_soft if b_soft > 0 else b_hard

            bar = pct_bar(b_used, quota_ref)

            f_quota_str = human_count(f_soft) if f_soft > 0 else f"{C.DIM}—{C.RESET}"

            print(f"  {C.WHITE}{user:<16}{C.RESET} "
                  f"{human_size(b_used):>10}  "
                  f"{human_size(quota_ref):>10}  "
                  f"{bar}  "
                  f"{human_count(f_used):>10}  "
                  f"{f_quota_str:>10}"
                  f"{alert}")

        print()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Affichage lisible de repquota -a",
        epilog="Exemples:\n"
               "  repquota -a | %(prog)s\n"
               "  %(prog)s repquota.txt\n"
               "  %(prog)s --sort pct --no-color < repquota.txt\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", nargs="?", default="-",
                        help="Fichier d'entrée (défaut: stdin)")
    parser.add_argument("-s", "--sort", choices=["used", "pct", "name", "files"],
                        default="used",
                        help="Tri: used (défaut), pct, name, files")
    parser.add_argument("-z", "--show-zero", action="store_true",
                        help="Afficher les utilisateurs sans usage")
    parser.add_argument("--no-color", action="store_true",
                        help="Désactiver les couleurs ANSI")

    args = parser.parse_args()

    if args.no_color or not sys.stdout.isatty():
        C.disable()

    # Lecture
    if args.file == "-":
        lines = sys.stdin.readlines()
    else:
        with open(args.file, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

    entries = parse_repquota(lines)
    print_report(entries, sort_by=args.sort, show_zero=args.show_zero)


if __name__ == "__main__":
    main()