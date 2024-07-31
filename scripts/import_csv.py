import csv
from typing import TypedDict
from configobj import ConfigObj
import simplejson


class KnownHandle(TypedDict):
    handles: list[tuple[str, int]]
    npc_handles: list[tuple[str, int]]
    burners: list[tuple[str, int]]
    groups: list[str]
    shops_owner: list[str]
    shops_employee: list[str]


known_handles_obj = ConfigObj("known_handles3.conf")
known_handles_obj.clear()

with open("tales-data3.csv") as data:
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

        alt_handles_list = [
            (v.strip(), 0)
            for v in (alt_handles.split(",") if alt_handles.strip() != "" else [])
            if v.strip() != ""
        ]
        alt_balance_list = [
            b.strip()
            for b in (alt_balance.split(",") if alt_balance.strip() != "" else [])
            if b.strip() != ""
        ]

        for entry in alt_balance_list:
            h, b = entry.split(":")
            h, b = (h.strip(), int(b.strip()) if b.strip() != "" else 0)
            found = next(
                (
                    (iv, ib, i)
                    for (i, (iv, ib)) in enumerate(alt_handles_list)
                    if iv == h
                ),
                None,
            )

            if found is not None:
                ah, ab, i = found
                alt_handles_list[i] = (ah, b)

        handles = [
            (handle.strip(), int(balance.strip()) if balance.strip() != "" else 0)
        ] + alt_handles_list

        groups_list = [
            v.strip()
            for v in (groups.split(",") if groups.strip() != "" else [])
            if v.strip() != ""
        ]

        filtered_groups = [g for g in groups_list if g != "trinity_taskbar"]
        tacoma_group = ["tacoma"] if tacoma == "x" else []
        all_groups = tacoma_group + filtered_groups

        shops_owner = ["trinity_taskbar"] if handle.strip() == "njal" else []

        employee = ["trinity_taskbar"] if "trinity_taskbar" in groups_list else []

        known_handle = KnownHandle(
            handles=handles,
            npc_handles=[],
            burners=[],
            groups=all_groups,
            shops_owner=shops_owner,
            shops_employee=employee,
        )

        known_handles_obj[handle] = simplejson.dumps(known_handle)

known_handles_obj.write()
