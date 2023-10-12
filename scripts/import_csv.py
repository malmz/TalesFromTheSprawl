import csv
from typing import TypedDict
from configobj import ConfigObj
import simplejson


class KnownHandle(TypedDict):
    handles: list[tuple[str, int]]
    npc_handles: list[tuple[str, int]]
    burners: list[tuple[str, int]]
    groups: list[str]
    shop_owner: list[str]
    shop_employee: list[str]


known_handles_obj = ConfigObj("known_handles_export.conf")
known_handles_obj.clear()

with open("tales-data.csv") as data:
    reader = csv.reader(data)
    for row in reader:
        if reader.line_num == 1:
            continue

        (
            player,
            name,
            handle,
            balance,
            alt_handles,
            alt_balance,
            groups,
            tacoma,
            u_number,
            server,
            category,
        ) = row

        alt_handles_list = alt_handles.split(",") if alt_handles != "" else []
        alt_balance_list = [int(b) for b in alt_balance.split(",") if b != ""]
        alt_balance_list.extend([0] * (len(alt_handles_list) - len(alt_balance_list)))

        handles = [(handle, int(balance) if balance != "" else 0)] + list(
            zip(alt_handles_list, alt_balance_list)
        )

        groups_list = groups.split(",")

        filtered_groups = [g for g in groups_list if g != "trinity_taskbar"]
        tacoma_group = ["tacoma"] if tacoma == "x" else []
        all_groups = tacoma_group + filtered_groups

        employee = ["trinity_taskbar"] if "trinity_taskbar" in groups_list else []

        known_handle = KnownHandle(
            handles=handles,
            npc_handles=[],
            burners=[],
            groups=all_groups,
            shop_owner=[],
            shop_employee=employee,
        )

        known_handles_obj[handle] = simplejson.dumps(known_handle)

known_handles_obj.write()
