.PHONY: check check-host

check:
	python3 -m unittest discover -s tests -v

check-host:
	sh tools/check-host.sh
