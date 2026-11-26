.PHONY: check check-host inventory iso

check:
	python3 -m unittest discover -s tests -v

check-host:
	sh tools/check-host.sh

inventory:
	python3 tools/package_inventory.py

iso:
	bash tools/live/local-iso.sh
