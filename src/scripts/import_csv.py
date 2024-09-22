import csv
import os
from typing import IO, TypedDict, cast

import click
import simplejson
from configobj import ConfigObj


class KnownHandle(TypedDict):
    handles: list[tuple[str, int]]
    npc_handles: list[tuple[str, int]]
    burners: list[tuple[str, int]]
    groups: list[str]
    shops_owner: list[str]
    shops_employee: list[str]


def parse_list(val: str) -> list[str]:
    if val.strip() == "":
        return []
    return [v.strip() for v in val.split(",") if v.strip() != ""]


def parse_keyval(val: str) -> tuple[str, int]:
    key, val = (v.strip() for v in val.split(":"))
    return key, int(val)


def parse_dict(vals: list[str]):
    return {k: v for k, v in map(parse_keyval, parse_list(vals))}


def parse_bool(val: str) -> bool:
    return val == "x"


@click.command()
@click.argument("input", type=click.File("r"), required=True)
@click.argument("output", type=click.File("wb"), default="known_handles.conf")
def import_csv(input: IO, output: IO):
    config = ConfigObj()
    reader = csv.DictReader(input)

    for row in reader:

        def col(v, row=row):
            return cast(str, row[v]).strip()

        (
            player,
            name,
            handle,
            balance,
            alt_handles,
            alt_balance,
            groups,
            tacoma,
            _u_number,
            _server,
            _category,
        ) = (
            col("Spelare"),
            col("Rollnamn"),
            col("Main handle"),
            col("Pengar på main:"),
            parse_list(col("Alternativa handles")),
            parse_dict(col("Pengar på övriga:")),
            parse_list(col("Grupper:")),
            parse_bool(col("Tacoma")),
            col("u-nummer"),
            col("Server"),
            col("Category"),
        )

        click.echo(f"Processing handle {handle} ({name})")

        handles = [(handle, int(balance))] + [
            (v, alt_balance.get(v, 0)) for v in alt_handles
        ]

        all_groups = (
            ["tacoma"] if tacoma else [] + [v for v in groups if v != "trinity_taskbar"]
        )

        shops_owner = ["trinity_taskbar"] if handle == "njal" else []
        employee = ["trinity_taskbar"] if "trinity_taskbar" in groups else []

        known_handle = dict(
            handles=handles,
            npc_handles=[],
            burners=[],
            groups=all_groups,
            shops_owner=shops_owner,
            shops_employee=employee,
            player=player,
            name=name,
        )

        config[handle] = simplejson.dumps(known_handle)

    config.write(outfile=output)


if __name__ == "__main__":
    import_csv()
