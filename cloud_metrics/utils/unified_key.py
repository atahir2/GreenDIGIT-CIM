def to_gd(unified_key: str) -> str:
    if not unified_key:
        return "gd.unknown.unknown.unknown"
    parts = [p.strip() for p in str(unified_key).split(".") if p.strip()]
    if not parts:
        return "gd.unknown.unknown.unknown"
    if parts[0].lower() == "gd":
        need = parts[1:4] if len(parts) >= 4 else (parts[1:4] or ["unknown","unknown","unknown"])
        return "gd." + ".".join(p.lower() for p in need)
    if len(parts) >= 4:  # std.cat.sub.short
        return "gd." + ".".join(p.lower() for p in parts[1:4])
    if len(parts) == 3:  # cat.sub.short
        return "gd." + ".".join(p.lower() for p in parts)
    return "gd.unknown.unknown.unknown"
