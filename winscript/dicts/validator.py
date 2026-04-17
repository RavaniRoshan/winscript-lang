VALID_BACKENDS = {"cdp", "com", "uia"}
# Scalar types and known object types. "list" is a valid container and checked separately.
VALID_TYPES = {"string", "int", "float", "bool", "dict", "list", "any",
               "Tab", "Workbook", "Sheet", "Window", "Element"}

def validate_dict(data: dict) -> list[str]:
    """
    Validate a parsed .wsdict file.
    Returns a list of error strings — empty list means valid.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["dict file must be a YAML mapping at the top level"]

    # ── top-level keys ──────────────────────────────────────────────────────
    for key in ("meta", "connection", "objects"):
        if key not in data:
            errors.append(f"top-level key '{key}' is required")

    if errors:
        # Can't do much more without the required keys
        return errors

    # ── meta ────────────────────────────────────────────────────────────────
    meta = data["meta"]
    if not isinstance(meta, dict):
        errors.append("meta must be a mapping")
    else:
        for field in ("name", "version", "backend"):
            if not meta.get(field):
                errors.append(f"meta.{field} is required")

        backend = meta.get("backend", "")
        if backend and backend not in VALID_BACKENDS:
            errors.append(
                f"meta.backend must be one of {sorted(VALID_BACKENDS)}, got '{backend}'"
            )

    # ── connection ──────────────────────────────────────────────────────────
    conn = data["connection"]
    if not isinstance(conn, dict):
        errors.append("connection must be a mapping")
    elif not conn.get("method"):
        errors.append("connection.method is required")

    # ── objects ─────────────────────────────────────────────────────────────
    objects = data["objects"]
    if not isinstance(objects, dict) or not objects:
        errors.append("objects must be a non-empty mapping")
        return errors

    root_count = sum(
        1 for obj in objects.values()
        if isinstance(obj, dict) and obj.get("is_root")
    )
    if root_count == 0:
        errors.append("at least one object must have is_root: true")
    if root_count > 1:
        errors.append("only one object may have is_root: true")

    for obj_name, obj_data in objects.items():
        if not isinstance(obj_data, dict):
            errors.append(f"objects.{obj_name} must be a mapping")
            continue

        # Commands
        seen_commands: set[str] = set()
        for i, cmd in enumerate(obj_data.get("commands", [])):
            if not isinstance(cmd, dict):
                errors.append(f"objects.{obj_name}.commands[{i}] must be a mapping")
                continue
            cmd_name = cmd.get("name", "")
            if not cmd_name:
                errors.append(f"objects.{obj_name}.commands[{i}].name is required")
            if not cmd.get("syntax"):
                errors.append(f"objects.{obj_name}.command '{cmd_name}' is missing syntax")
            has_method = any(
                cmd.get(k) for k in ("cdp_method", "com_method", "uia_method")
            )
            if not has_method:
                errors.append(
                    f"objects.{obj_name}.command '{cmd_name}' must have "
                    "at least one of cdp_method, com_method, uia_method"
                )
            if cmd_name in seen_commands:
                errors.append(
                    f"objects.{obj_name} has duplicate command name '{cmd_name}'"
                )
            seen_commands.add(cmd_name)

        # Properties
        for i, prop in enumerate(obj_data.get("properties", [])):
            if not isinstance(prop, dict):
                errors.append(f"objects.{obj_name}.properties[{i}] must be a mapping")
                continue
            prop_name = prop.get("name", "")
            if not prop_name:
                errors.append(f"objects.{obj_name}.properties[{i}].name is required")

            prop_type = str(prop.get("type", ""))
            base_type = prop_type.split("[")[0].strip()  # unwrap list[X] → X check
            if base_type.lower() not in {t.lower() for t in VALID_TYPES} and not prop_type[0].isupper():
                errors.append(
                    f"objects.{obj_name}.property '{prop_name}' has unknown type '{prop_type}'"
                )

    return errors
