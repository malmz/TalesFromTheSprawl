import json
import os

nof_errors = 0
nof_warnings = 0

def log_error(text):
    global nof_errors
    nof_errors += 1
    print(f"ERROR: {text}")

def log_warning(text):
    global nof_warnings
    nof_warnings += 1
    print(f"WARNING: {text}")

def get_next_field(data):
    if data.startswith("\""):
        # Do smart stuff
        val = ""
        is_escaped = False
        for i in range(1, len(data)):
            if data[i] == "\"" and not is_escaped:
                if i+1 == len(data) or data[i+1] == ",":
                    return (val, data[i+2:])
                elif data[i+1] == "\"":
                    is_escaped = True
                else:
                    log_error(f"Invalid format on field found: {data} (see col {i})")
            else:
                is_escaped = False
                val += data[i]
        return (val, "")
    else:
        val = data.split(",")[0]
        return (val, data[len(val)+1:])

def get_all_fields(row):
    result = []
    while row:
        (field, row) = get_next_field(row)
        result.append(field)
    return result

def get_json_from_row(row):
    (_name, _larp_name, main_handle, money_str, alt_handles_str, burners_str, npc_handles_str, secondary_handles_money_str, groups_str, is_tacoma) = get_all_fields(row)
    # tremors = '{"handles": [["tremors", 20000], ["alison_sterling", 300]], "npc_handles": [["gm_natalie", 10000], ["kdw", 50000], ["dewalt", 50000], ["eezy", 500], ["allison_sterling", 5000], ["tree_of_light", 50000], ["mr_silver", 2000]], "burners": [["johnson140", 10]], "groups": [], "shops_owner": [], "shops_employee": ["trinity_taskbar"]}'

    print(f"====== Processing handle {main_handle} ({_name}) ===========")

    if not main_handle:
        log_error("Missing main handle!")
        main_handle = _name.split(" ")[0].lower()

    try:
        money = int(money_str)
    except Exception as e:
        money = 0
        log_warning(f"Unable to parse money amount: '{money_str}'")

    alt_handles_names = [x.strip() for x in alt_handles_str.split(",") if x.strip()]
    burners_names = [x.strip() for x in burners_str.split(",") if x.strip()]
    npc_handles_names = [x.strip() for x in npc_handles_str.split(",") if x.strip()]

    alt_handles = []
    burners = []
    npc_handles = []

    for handle_data in secondary_handles_money_str.split(","):
        if not handle_data:
            # Empty, let's skip it!
            continue

        name, money_str = [x.strip() for x in handle_data.split(":")]
        if name in alt_handles_names:
            alt_handles.append((name, int(money_str)))
            alt_handles_names.remove(name)
        elif name in burners_names:
            burners.append((name, int(money_str)))
            burners_names.remove(name)
        elif name in npc_handles_names:
            npc_handles.append((name, int(money_str)))
            npc_handles_names.remove(name)
        else:
            log_error("Found money amount for handle but it is not declared as alt handle, npc handle or burner")

    for name in alt_handles_names:
        alt_handles.append((name, 0))
    for name in burners_names:
        burners.append((name, 0))
    for name in npc_handles_names:
        npc_handles.append((name, 0))

    print(f"INFO: {len(alt_handles_names)+len(burners_names)+len(npc_handles_names)} handles are without money entry")

    groups = [group.strip().replace("?", "") for group in groups_str.split(",") if group.strip()]
    shops = []
    if "trinity_taskbar" in groups:
        shops.append("trinity_taskbar")
        groups.remove("trinity_taskbar")
    if is_tacoma.strip():
        groups.append("tacoma")

    data = {
        "handles": [(main_handle, money)] + alt_handles,
        "npc_handles": npc_handles,
        "burners": burners,
        "groups": groups,
        "shops_owner": [],
        "shops_employee": shops
    }
    json_data = json.dumps(data)

    print()

    return main_handle, json_data

def create_conf_file(out_file, rows):
    with open(out_file, "w") as out:
        for row in rows:
            handle, data = get_json_from_row(row)
            out.write(f"{handle} = '{data}'\n\n")


if __name__ == "__main__":
    input_file = "prepare/source.csv" if os.path.basename(os.getcwd()) != "prepare" else "source.csv"
    with open(input_file, "r") as file:
        lines = file.readlines()
    create_conf_file("known_handles.conf", lines)

    print(f"Finished with {nof_errors} errors and {nof_warnings} warnings")

