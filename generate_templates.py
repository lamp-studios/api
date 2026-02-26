"""Generate DiamondFire templates for the AI builder system."""
import json, gzip, base64, io


def encode(template):
    data = json.dumps(template, separators=(",", ":")).encode("utf-8")
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(data)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def txt(val, slot):
    return {"item": {"id": "txt", "data": {"name": str(val)}}, "slot": slot}

def num(val, slot):
    return {"item": {"id": "num", "data": {"name": str(val)}}, "slot": slot}

def var(name, scope, slot):
    return {"item": {"id": "var", "data": {"name": name, "scope": scope}}, "slot": slot}

def tag(option, tag_name, action, block, slot=26):
    return {"item": {"id": "bl_tag", "data": {"option": option, "tag": tag_name, "action": action, "block": block}}, "slot": slot}

def game_val(type_name, target, slot):
    return {"item": {"id": "g_val", "data": {"type": type_name, "target": target}}, "slot": slot}

def loc(x, y, z, slot):
    return {"item": {"id": "loc", "data": {"isBlock": False, "loc": {"x": x, "y": y, "z": z, "pitch": 0.0, "yaw": 0.0}}}, "slot": slot}


# ============================================================
# TEMPLATE 1: Command handler (@generate, @usage, @clear)
# ============================================================
cmd_handler = {"blocks": [
    # Player Event: Command
    {"id": "block", "block": "event", "action": "Command"},

    # set_var = : %var(cmd) = event command
    {"id": "block", "block": "set_var", "action": "=", "args": {"items": [
        var("cmd", "local", 0),
        game_val("Event Command", "Default", 1),
    ]}},

    # If starts with "generate "
    {"id": "block", "block": "if_var", "action": "StrStartsWith", "args": {"items": [
        var("cmd", "local", 0),
        txt("generate ", 1),
        tag("True", "Ignore Case", "StrStartsWith", "if_var"),
    ]}},
    {"id": "bracket", "direct": "open", "type": "norm"},

    # Extract prompt: RemoveString "generate " from cmd
    {"id": "block", "block": "set_var", "action": "RemoveString", "args": {"items": [
        var("prompt", "local", 0),
        var("cmd", "local", 1),
        txt("generate ", 2),
    ]}},

    # Get player location as origin
    {"id": "block", "block": "set_var", "action": "=", "args": {"items": [
        var("origin", "local", 0),
        game_val("Location", "Default", 1),
    ]}},

    # Call the build function
    {"id": "block", "block": "call_func", "data": "startBuild", "args": {"items": []}},

    {"id": "bracket", "direct": "close", "type": "norm"},

    # Else if "usage"
    {"id": "block", "block": "if_var", "action": "=", "args": {"items": [
        var("cmd", "local", 0),
        txt("usage", 1),
        tag("True", "Ignore Case", "=", "if_var"),
    ]}},
    {"id": "bracket", "direct": "open", "type": "norm"},
    {"id": "block", "block": "call_func", "data": "showUsage", "args": {"items": []}},
    {"id": "bracket", "direct": "close", "type": "norm"},

    # Else if "clearhistory"
    {"id": "block", "block": "if_var", "action": "=", "args": {"items": [
        var("cmd", "local", 0),
        txt("clearhistory", 1),
        tag("True", "Ignore Case", "=", "if_var"),
    ]}},
    {"id": "bracket", "direct": "open", "type": "norm"},
    {"id": "block", "block": "player_action", "action": "SendMessage", "target": "Default", "args": {"items": [
        txt("&aChat memory cleared!", 0),
    ]}},
    {"id": "bracket", "direct": "close", "type": "norm"},
]}

# ============================================================
# TEMPLATE 2: startBuild function
# ============================================================
# API_URL should be set to your cloudflare tunnel URL
start_build = {"blocks": [
    {"id": "block", "block": "func", "data": "startBuild", "args": {"items": [
        tag("False", "Is Hidden", "dynamic", "func"),
    ]}},

    # Send "generating" message
    {"id": "block", "block": "player_action", "action": "SendMessage", "target": "Default", "args": {"items": [
        txt("&7&oGenerating build... please wait", 0),
    ]}},

    # Build URL: API_URL/?content=PROMPT&username=PLAYER&builtin=true
    {"id": "block", "block": "set_var", "action": "JoinString", "args": {"items": [
        var("url", "local", 0),
        var("API_URL", "saved", 1),
        txt("/?content=", 2),
        var("prompt", "local", 3),
        txt("&username=", 4),
    ]}},

    # Append player name
    {"id": "block", "block": "set_var", "action": "JoinString", "args": {"items": [
        var("url", "local", 0),
        var("url", "local", 1),
        game_val("Name", "Default", 2),
        txt("&builtin=true", 3),
    ]}},

    # Web request
    {"id": "block", "block": "set_var", "action": "HTTPRequest", "args": {"items": [
        var("response", "local", 0),
        var("url", "local", 1),
        tag("GET", "Request Method", "HTTPRequest", "set_var"),
        tag("Body", "Content to Set", "HTTPRequest", "set_var"),
    ]}},

    # Check if response is empty/error
    {"id": "block", "block": "if_var", "action": "StrContains", "args": {"items": [
        var("response", "local", 0),
        txt("error", 1),
        tag("True", "Ignore Case", "StrContains", "if_var"),
    ]}},
    {"id": "bracket", "direct": "open", "type": "norm"},
    {"id": "block", "block": "player_action", "action": "SendMessage", "target": "Default", "args": {"items": [
        txt("&cBuild failed! API error.", 0),
    ]}},
    {"id": "block", "block": "control", "action": "Return", "args": {"items": []}},
    {"id": "bracket", "direct": "close", "type": "norm"},

    # Start the parsing process
    {"id": "block", "block": "start_process", "data": "parseBuild", "args": {"items": []}},
]}

# ============================================================
# TEMPLATE 3: parseBuild process - parse response & place blocks
# ============================================================
parse_build = {"blocks": [
    {"id": "block", "block": "process", "data": "parseBuild", "args": {"items": [
        tag("False", "Is Hidden", "dynamic", "process"),
    ]}},

    # Split response by newlines
    {"id": "block", "block": "set_var", "action": "SplitString", "args": {"items": [
        var("lines", "local", 0),
        var("response", "local", 1),
        txt("\n", 2),
    ]}},

    # Track placed blocks count
    {"id": "block", "block": "set_var", "action": "=", "args": {"items": [
        var("placed", "local", 0),
        num("0", 1),
    ]}},

    # For each line
    {"id": "block", "block": "repeat", "action": "ForEach", "args": {"items": [
        var("line", "local", 0),
        var("lines", "local", 1),
    ]}},
    {"id": "bracket", "direct": "open", "type": "repeat"},

    # Skip #settings lines and empty lines
    {"id": "block", "block": "if_var", "action": "StrStartsWith", "args": {"items": [
        var("line", "local", 0),
        txt("#", 1),
    ]}},
    {"id": "bracket", "direct": "open", "type": "norm"},
    {"id": "block", "block": "control", "action": "Skip", "args": {"items": []}},
    {"id": "bracket", "direct": "close", "type": "norm"},

    # Split by "=" -> [block_id, coords_part]
    {"id": "block", "block": "set_var", "action": "SplitString", "args": {"items": [
        var("parts", "local", 0),
        var("line", "local", 1),
        txt("=", 2),
    ]}},

    # Get block_id (index 1)
    {"id": "block", "block": "set_var", "action": "GetListValue", "args": {"items": [
        var("block_id", "local", 0),
        var("parts", "local", 1),
        num("1", 2),
    ]}},

    # Get coords string (index 2), e.g. "[0,1,2,0,0]"
    {"id": "block", "block": "set_var", "action": "GetListValue", "args": {"items": [
        var("coords_str", "local", 0),
        var("parts", "local", 1),
        num("2", 2),
    ]}},

    # Remove brackets
    {"id": "block", "block": "set_var", "action": "RemoveString", "args": {"items": [
        var("coords_str", "local", 0),
        var("coords_str", "local", 1),
        txt("[", 2),
    ]}},
    {"id": "block", "block": "set_var", "action": "RemoveString", "args": {"items": [
        var("coords_str", "local", 0),
        var("coords_str", "local", 1),
        txt("]", 2),
    ]}},

    # Split coords by ","
    {"id": "block", "block": "set_var", "action": "SplitString", "args": {"items": [
        var("coords", "local", 0),
        var("coords_str", "local", 1),
        txt(",", 2),
    ]}},

    # Get x, y, z as numbers
    {"id": "block", "block": "set_var", "action": "GetListValue", "args": {"items": [
        var("bx", "local", 0), var("coords", "local", 1), num("1", 2),
    ]}},
    {"id": "block", "block": "set_var", "action": "GetListValue", "args": {"items": [
        var("by", "local", 0), var("coords", "local", 1), num("2", 2),
    ]}},
    {"id": "block", "block": "set_var", "action": "GetListValue", "args": {"items": [
        var("bz", "local", 0), var("coords", "local", 1), num("3", 2),
    ]}},

    # Parse to numbers
    {"id": "block", "block": "set_var", "action": "ParseNumber", "args": {"items": [
        var("bx", "local", 0), var("bx", "local", 1),
    ]}},
    {"id": "block", "block": "set_var", "action": "ParseNumber", "args": {"items": [
        var("by", "local", 0), var("by", "local", 1),
    ]}},
    {"id": "block", "block": "set_var", "action": "ParseNumber", "args": {"items": [
        var("bz", "local", 0), var("bz", "local", 1),
    ]}},

    # Calculate placement location: origin + offset
    {"id": "block", "block": "set_var", "action": "ShiftLocation", "args": {"items": [
        var("place_loc", "local", 0),
        var("origin", "local", 1),
        var("bx", "local", 2),
        var("by", "local", 3),
        var("bz", "local", 4),
    ]}},

    # Place the block: SetBlock with block_id at place_loc
    {"id": "block", "block": "game_action", "action": "SetBlock", "args": {"items": [
        var("place_loc", "local", 0),
        var("block_id", "local", 1),
    ]}},

    # Increment counter
    {"id": "block", "block": "set_var", "action": "+=", "args": {"items": [
        var("placed", "local", 0),
        num("1", 1),
    ]}},

    {"id": "bracket", "direct": "close", "type": "repeat"},

    # Done message
    {"id": "block", "block": "set_var", "action": "JoinString", "args": {"items": [
        var("msg", "local", 0),
        txt("&aBuild complete! Placed &e", 1),
        var("placed", "local", 2),
        txt("&a blocks.", 3),
    ]}},
    {"id": "block", "block": "player_action", "action": "SendMessage", "target": "Default", "args": {"items": [
        var("msg", "local", 0),
    ]}},
]}

# ============================================================
# TEMPLATE 4: showUsage function
# ============================================================
show_usage = {"blocks": [
    {"id": "block", "block": "func", "data": "showUsage", "args": {"items": [
        tag("False", "Is Hidden", "dynamic", "func"),
    ]}},

    # Build usage URL
    {"id": "block", "block": "set_var", "action": "JoinString", "args": {"items": [
        var("url", "local", 0),
        var("API_URL", "saved", 1),
        txt("/usage?username=", 2),
        game_val("Name", "Default", 3),
    ]}},

    # Web request
    {"id": "block", "block": "set_var", "action": "HTTPRequest", "args": {"items": [
        var("resp", "local", 0),
        var("url", "local", 1),
        tag("GET", "Request Method", "HTTPRequest", "set_var"),
        tag("Body", "Content to Set", "HTTPRequest", "set_var"),
    ]}},

    # Send result
    {"id": "block", "block": "set_var", "action": "JoinString", "args": {"items": [
        var("msg", "local", 0),
        txt("&6[Usage] &f", 1),
        var("resp", "local", 2),
    ]}},
    {"id": "block", "block": "player_action", "action": "SendMessage", "target": "Default", "args": {"items": [
        var("msg", "local", 0),
    ]}},
]}

# ============================================================
# TEMPLATE 5: locToStr helper function
# ============================================================
loc_to_str = {"blocks": [
    {"id": "block", "block": "func", "data": "locToStr", "args": {"items": [
        tag("False", "Is Hidden", "dynamic", "func"),
    ]}},

    # Get coords from %var(inputLoc)
    {"id": "block", "block": "set_var", "action": "GetCoord", "args": {"items": [
        var("_x", "local", 0),
        var("inputLoc", "local", 1),
        tag("X", "Coordinate Type", "GetCoord", "set_var"),
    ]}},
    {"id": "block", "block": "set_var", "action": "GetCoord", "args": {"items": [
        var("_y", "local", 0),
        var("inputLoc", "local", 1),
        tag("Y", "Coordinate Type", "GetCoord", "set_var"),
    ]}},
    {"id": "block", "block": "set_var", "action": "GetCoord", "args": {"items": [
        var("_z", "local", 0),
        var("inputLoc", "local", 1),
        tag("Z", "Coordinate Type", "GetCoord", "set_var"),
    ]}},

    # Round to integers
    {"id": "block", "block": "set_var", "action": "Floor", "args": {"items": [
        var("_x", "local", 0), var("_x", "local", 1),
    ]}},
    {"id": "block", "block": "set_var", "action": "Floor", "args": {"items": [
        var("_y", "local", 0), var("_y", "local", 1),
    ]}},
    {"id": "block", "block": "set_var", "action": "Floor", "args": {"items": [
        var("_z", "local", 0), var("_z", "local", 1),
    ]}},

    # Join as string: "x,y,z"
    {"id": "block", "block": "set_var", "action": "JoinString", "args": {"items": [
        var("locStr", "local", 0),
        var("_x", "local", 1),
        txt(",", 2),
        var("_y", "local", 3),
        txt(",", 4),
        var("_z", "local", 5),
    ]}},
]}


# ============================================================
# Output all templates
# ============================================================
templates = {
    "1_command_handler": cmd_handler,
    "2_startBuild": start_build,
    "3_parseBuild": parse_build,
    "4_showUsage": show_usage,
    "5_locToStr": loc_to_str,
}

print("=" * 60)
print("DiamondFire AI Builder Templates")
print("=" * 60)
print()
print("SETUP: Set saved variable 'API_URL' to your tunnel URL")
print("  e.g. https://your-tunnel.trycloudflare.com")
print()

for name, tmpl in templates.items():
    encoded = encode(tmpl)
    print(f"--- {name} ---")
    print(encoded)
    print()

# Also save to files
for name, tmpl in templates.items():
    with open(f"template_{name}.txt", "w") as f:
        f.write(encode(tmpl))

print("Templates also saved to template_*.txt files")
print()
print("COMMANDS:")
print("  @generate <prompt>  - AI generates and places a build at your location")
print("  @usage              - Check your daily API usage")
print("  @clearhistory       - Clear your chat memory")
