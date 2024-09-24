from typing import IO, Any, cast

import click
import simplejson
from configobj import ConfigObj
from tabulate import tabulate

""" with open("known_handles") as known_handles_file:
    with open("handles") as handles_file:
        known_handles = [line.strip() for line in known_handles_file]
        handles = {line.strip() for line in handles_file}

        for known_handle in known_handles:
            if known_handle not in handles:
                print(known_handle)
"""

handles_to_actors = "___handle_to_actor_mapping"


@click.command()
@click.argument("known_handles_file", type=click.File(), required=True)
@click.argument("handles_file", type=click.File(), required=True)
@click.option("-a", "--all", is_flag=True, help="Print all handles, even joined ones")
def main(known_handles_file: IO, handles_file: IO, all: bool):
    known_handles = ConfigObj(known_handles_file)
    handles = ConfigObj(handles_file)

    handles_set = {handle for handle in handles[handles_to_actors]}

    def table_cols(k, v):
        val = cast(dict[str, Any], simplejson.loads(v))
        claimed = k in handles_set
        player = val.get("player")
        name = val.get("name")
        check = click.style("✓", fg="green") if claimed else click.style("x", fg="red")
        return [check, k, name, player]

    rows = [
        table_cols(k, v)
        for k, v in known_handles.items()
        if all or k not in handles_set
    ]

    click.echo(tabulate(rows, headers=[".", "Handle", "Role", "Name"]))


if __name__ == "__main__":
    main()
