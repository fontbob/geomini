# Python command (use py on Windows, or override: make PYTHON=python3 build)
PYTHON ?= py

# Detect venv layout from Python: Windows uses Scripts/, Unix uses bin/
VENV_SUBDIR := $(shell $(PYTHON) -c "import sys; print('Scripts' if sys.platform == 'win32' else 'bin')")
VENV_BIN := venv/$(VENV_SUBDIR)
EXE := $(shell $(PYTHON) -c "import sys; print('.exe' if sys.platform == 'win32' else '')")
VENV_PIP := $(VENV_BIN)/pip$(EXE)
VENV_PYTHON := $(VENV_BIN)/python$(EXE)
VENV_PIP_COMPILE := $(VENV_BIN)/pip-compile$(EXE)
VENV_PIP_SYNC := $(VENV_BIN)/pip-sync$(EXE)

SOURCES=$(shell $(PYTHON) scripts/read-config.py --sources )
FAMILY=$(shell $(PYTHON) scripts/read-config.py --family )
DRAWBOT_SCRIPTS=$(shell ls documentation/*.py)
DRAWBOT_OUTPUT=$(shell ls documentation/*.py | sed 's/\.py/.png/g')

help:
	@echo "###"
	@echo "# Build targets for $(FAMILY)"
	@echo "###"
	@echo
	@echo "  make build:  Builds the fonts and places them in the fonts/ directory"
	@echo "  make test:   Tests the fonts with fontspector"
	@echo "  make proof:  Creates HTML proof documents in the proof/ directory"
	@echo "  make images: Creates PNG specimen images in the documentation/ directory"
	@echo

build: build.stamp

venv: venv/touchfile

customize: venv
	$(VENV_PYTHON) scripts/customize.py

build.stamp: venv sources/config.yaml $(SOURCES)
	rm -rf fonts
	export PATH="$(CURDIR)/$(VENV_BIN):$$PATH"; for config in sources/config*.yaml; do $(VENV_BIN)/gftools$(EXE) builder $$config; done && touch build.stamp

venv/touchfile: requirements.txt
	test -d venv || $(PYTHON) -m venv venv
	$(VENV_PYTHON) -m pip install -Ur requirements.txt
	touch venv/touchfile

test: build.stamp
	@if command -v fontspector >/dev/null 2>&1; then \
		TOCHECK=$$(find fonts/variable -type f 2>/dev/null); [ -z "$$TOCHECK" ] && TOCHECK=$$(find fonts/ttf -type f 2>/dev/null); \
		mkdir -p out/ out/fontspector; \
		fontspector --profile googlefonts -l warn --full-lists --succinct --html out/fontspector/fontspector-report.html --ghmarkdown out/fontspector/fontspector-report.md --badges out/badges $$TOCHECK || echo '::warning file=sources/config.yaml,title=fontspector failures::The fontspector QA check reported errors in your font. Please check the generated report.'; \
	else \
		echo "fontspector not found — skipping QA checks. Install with 'cargo install fontspector' (or use CI for full checks)."; \
	fi

proof: venv build.stamp
	TOCHECK=$$(find fonts/variable -type f 2>/dev/null); if [ -z "$$TOCHECK" ]; then TOCHECK=$$(find fonts/ttf -type f 2>/dev/null); fi ; mkdir -p out/ out/proof; $(VENV_BIN)/diffenator2$(EXE) proof $$TOCHECK -o out/proof

images: venv $(DRAWBOT_OUTPUT)

%.png: %.py build.stamp
	$(VENV_PYTHON) $< --output $@

clean:
	rm -rf venv
	find . -name "*.pyc" -delete

update-project-template:
	npx update-template https://github.com/googlefonts/googlefonts-project-template/

update: venv
	$(VENV_PYTHON) -m pip install --upgrade pip-tools
	# See https://pip-tools.readthedocs.io/en/latest/#a-note-on-resolvers for
	# the `--resolver` flag below.
	$(VENV_PIP_COMPILE) --upgrade --verbose --resolver=backtracking requirements.in
	$(VENV_PIP_SYNC) requirements.txt

	git commit -m "Update requirements" requirements.txt
	git push
