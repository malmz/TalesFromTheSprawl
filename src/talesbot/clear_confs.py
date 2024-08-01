import os


def get_all_conf_files():
    return [
        os.path.join(dp, f)
        for dp, dn, filenames in os.walk(".")
        for f in filenames
        if os.path.splitext(f)[1] == ".conf"
    ]


if __name__ == "__main__":
    for file in get_all_conf_files():
        if (
            "conf_backup" not in file
            and "known_handles" not in file
            and "artifacts" not in file
            and "crash.conf" not in file
        ):
            os.remove(file)
