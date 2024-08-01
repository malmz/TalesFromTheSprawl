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
			not "conf_backup" in file
			and not "known_handles" in file
			and not "artifacts" in file
			and not "crash.conf" in file
		):
			os.remove(file)
