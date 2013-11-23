def do_filesize(value):
	bytes = float(value)
	base = 1024
	prefixes = [
		("KiB"),
		("MiB"),
		("GiB"),
		("TiB"),
	]
	for i, prefix in enumerate(prefixes):
		unit = base ** (i + 1)
		if bytes < unit:
			return "%.1f %s" % ((bytes / unit), prefix)
        return "%.1f %s" % ((bytes / unit), prefix)