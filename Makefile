SOURCES=$(shell python3 scripts/read-config.py --sources )
FAMILY=$(shell python3 scripts/read-config.py --family )
DRAWBOT_SCRIPTS=$(shell ls documentation/*.py)
DRAWBOT_OUTPUT=$(shell ls documentation/*.py | sed 's/\.py/.png/g')

help:
	@echo "###"
	@echo "# Build targets for $(FAMILY)"
	@echo "###"
	@echo
	@echo "  make build:  Builds the fonts and places them in the fonts/ directory"
	@echo "  make test:   Tests the fonts with fontspector (bundles OFL beside binaries; optional qa/METADATA.pb for GF-style checks)"
	@echo "  make proof:  Creates HTML proof documents in the proof/ directory"
	@echo "  make images: Creates PNG specimen images in the documentation/ directory"
	@echo

build: build.stamp

venv: venv/touchfile

customize: venv
	. venv/bin/activate; python3 scripts/customize.py

build.stamp: venv sources/config.yaml $(SOURCES)
	rm -rf fonts
	(for config in sources/config*.yaml; do . venv/bin/activate; gftools builder $$config; done) \
		&& cp OFL.txt fonts/ \
		&& (test -d fonts/variable && cp -f OFL.txt fonts/variable/ || true) \
		&& (test -d fonts/ttf && cp -f OFL.txt fonts/ttf/ || true) \
		&& touch build.stamp

venv/touchfile: requirements.txt
	test -d venv || python3 -m venv venv
	. venv/bin/activate; pip install -Ur requirements.txt
	touch venv/touchfile

test: build.stamp
	which fontspector || (echo "fontspector not found. Please install it with 'cargo install fontspector'." && exit 1)
	mkdir -p out/ out/fontspector
	@if [ -f qa/METADATA.pb ]; then \
		test -d fonts/variable && cp -f qa/METADATA.pb fonts/variable/METADATA.pb || true; \
		test -d fonts/ttf && cp -f qa/METADATA.pb fonts/ttf/METADATA.pb || true; \
	fi
	TOCHECK=$$(find fonts/variable -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' -o -name 'OFL.txt' -o -name 'METADATA.pb' \) 2>/dev/null | sort); if [ -z "$$TOCHECK" ]; then TOCHECK=$$(find fonts/ttf -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' -o -name 'OFL.txt' -o -name 'METADATA.pb' \) 2>/dev/null | sort); fi; if [ -z "$$TOCHECK" ]; then echo "No font binaries found under fonts/variable or fonts/ttf." && exit 1; fi; fontspector --profile googlefonts -l warn --full-lists --succinct --html out/fontspector/fontspector-report.html --ghmarkdown out/fontspector/fontspector-report.md --badges out/badges $$TOCHECK || echo '::warning file=sources/config.yaml,title=fontspector failures::The fontspector QA check reported errors in your font. Please check the generated report.'

proof: venv build.stamp
	TOCHECK=$$(find fonts/variable -type f 2>/dev/null); if [ -z "$$TOCHECK" ]; then TOCHECK=$$(find fonts/ttf -type f 2>/dev/null); fi ; . venv/bin/activate; mkdir -p out/ out/proof; diffenator2 proof $$TOCHECK -o out/proof

images: venv $(DRAWBOT_OUTPUT)

%.png: %.py build.stamp
	. venv/bin/activate; python3 $< --output $@

clean:
	rm -rf venv
	find . -name "*.pyc" -delete

update-project-template:
	npx update-template https://github.com/googlefonts/googlefonts-project-template/

update: venv
	venv/bin/pip install --upgrade pip-tools
	# See https://pip-tools.readthedocs.io/en/latest/#a-note-on-resolvers for
	# the `--resolver` flag below.
	venv/bin/pip-compile --upgrade --verbose --resolver=backtracking requirements.in
	venv/bin/pip-sync requirements.txt

	git commit -m "Update requirements" requirements.txt
	git push
