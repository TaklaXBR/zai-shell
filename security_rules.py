import re

_BOUNDARY = r"(?=\s|$|;|&|\||['\"])"

DANGEROUS_REGEX = [
    rf"rm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+['\"]?(\/|\/\*|\~|\/home|\/etc|\/usr|\/bin|\/sbin|\/boot|\/var|\/dev|\/sys|\/proc|\/root|\/System|\/Library|\/Volumes)['\"]?{_BOUNDARY}",
    rf"rm\s+-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*\s+['\"]?(\/|\/\*|\~|\/home|\/etc|\/usr|\/bin|\/sbin|\/boot|\/var|\/dev|\/sys|\/proc|\/root|\/System|\/Library|\/Volumes)['\"]?{_BOUNDARY}",
    r"rm\s+.*--no-preserve-root",
    r":\(\)\s*\{\s*:\|:&\s*\}\s*;\s*:",
    r"dd\s+.*of=\/dev\/(sd[a-z]|nvme[0-9]|hd[a-z]|vd[a-z]|disk[0-9]|rdisk[0-9]|zero|null|random)",
    r">\s*\/dev\/(sd[a-z]|nvme[0-9]|hd[a-z]|vd[a-z]|disk[0-9]|rdisk[0-9])",
    r"mkfs(\.[a-zA-Z0-9_-]+)?\s+",
    r"wipefs\s+",
    r"shred\s+.*\/dev\/",
    rf"chmod\s+-[a-zA-Z]*R[a-zA-Z]*\s+(000|777)\s+['\"]?(\/|\/\*)['\"]?{_BOUNDARY}",
    rf"chown\s+-[a-zA-Z]*R[a-zA-Z]*\s+\S+\s+['\"]?(\/|\/\*)['\"]?{_BOUNDARY}",
    rf"mv\s+\/(etc|bin|sbin|usr|boot){_BOUNDARY}",
    r"diskutil\s+(eraseDisk|eraseVolume|zeroDisk)",
    r"del\s+.*\/s.*[a-zA-Z]:\\(\*|\*\.\*|\"|\')?(\s|$)",
    r"del\s+.*[a-zA-Z]:\\(\*|\*\.\*|\"|\')?(\s|$)",
    r"del\s+.*(%systemdrive%|%windir%|%systemroot%)",
    r"(rd|rmdir)\s+.*\/s.*[a-zA-Z]:\\(\"|\')?(\s|$)",
    r"format\s+[a-zA-Z]:",
    r"diskpart.*clean(\s+all)?",
    r"Remove-Item\s+.*-Recurse.*[a-zA-Z]:\\(\*|\*\.\*|\"|\')?(\s|$)",
    r"Remove-Item\s+.*[a-zA-Z]:\\(\*|\*\.\*|\"|\')?(\s|$).*-Recurse",
    r"Remove-Item\s+.*(\$env:SystemDrive|\$env:windir|\$env:SystemRoot)",
    r"Clear-Disk\s+",
    r"Initialize-Disk\s+",
    r"Format-Volume\s+",
    r"vssadmin\s+delete\s+shadows",
    r"bcdedit\s+\/(delete|clean)",
    r"reg\s+delete\s+['\"]?HKLM\\(SYSTEM|SOFTWARE)['\"]?\s+\/f"
]

def is_dangerous(cmd_array):
    if not cmd_array:
        return False
    cmd_str = " ".join(cmd_array)
    for pattern in DANGEROUS_REGEX:
        if re.search(pattern, cmd_str, re.IGNORECASE):
            return True
    return False
