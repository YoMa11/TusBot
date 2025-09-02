# ---- Shell ----
SHELL := /bin/bash

# ---- Config ----
PROJECT_NAME ?= tustus_bot_inline_PRO
PY           ?= python3
VENV         ?= .venv
PIP          ?= $(VENV)/bin/pip
PYBIN        ?= $(VENV)/bin/python
RELEASE_SH   ?= releases.sh   # נשתמש בו כברירת מחדל; ניפול ל-release.sh אם צריך

# --- configurable defaults (תואם releases.sh) ---
CHMOD        ?=
# אל תכלול DB בברירת מחדל (ניתן להחליף ל-INCLUDE_DB=1 בפקודה)
INCLUDE_DB   ?= 0
# bump kind: patch|minor|major (default patch)
BUMP         ?= patch
# שמירת stage? 0=no (default), 1=yes
KEEP         ?= 0
# space-separated patterns to exclude from the release package (מידע בלבד; ההחרגות בפועל נעשות בסקריפט)
EXCLUDE_PATTERNS ?= old/ *.zip .venv/ __pycache__/ .DS_Store *.pyc bot.log bot.err.log _debug_* .pytest_cache .mypy_cache .ruff_cache

#file location 
OUT_DIR ?= /Users/yossimantsour/Desktop/tusbot

# ---- Targets ----
.PHONY: help venv install install-jobqueue install-scrape run start stop scrape \
        release release-major release-minor release-patch release-set version \
        rmaj rmin rpatch rdb clean

help:
	@echo "Targets:"
	@echo "  make venv                  # יוצר סביבה וירטואלית"
	@echo "  make install               # מתקין תלותים מ-requirements.txt"
	@echo "  make install-jobqueue      # מתקין python-telegram-bot[job-queue]"
	@echo "  make install-scrape        # מתקין חבילות עבור רינדור JS (requests-html, lxml_html_clean)"
	@echo "  make run                   # מריץ את הבוט (מעדיף botctl.sh, אחרת app.py)"
	@echo "  make start / make stop     # הפעלה/כיבוי דרך botctl.sh (אם קיים)"
	@echo "  make scrape                # ריצת דיבוג סקרייפר (debug_scrape_once.py)"
	@echo "  make version               # מציג גרסת פרוייקט עכשווית (מ-VERSION/ZIP)"
	@echo "  make release               # יוצר ZIP עם גרסה חדשה (ברירת מחדל: patch)"
	@echo "     פרמטרים: BUMP=major|minor|patch (default patch), INCLUDE_DB=0|1, CHMOD=777, KEEP=1"
	@echo "  make release-major         # מעלה גרסת Major"
	@echo "  make release-minor         # מעלה גרסת Minor"
	@echo "  make release-patch         # מעלה גרסת Patch"
	@echo "  make release-set VERSION=X.Y.Z  # קובע גרסה ידנית"
	@echo "  make clean                 # ניקוי קבצי ביניים"

venv:
	@test -d $(VENV) || $(PY) -m venv $(VENV)
	@echo "✅ venv ready: $(VENV)"

install: venv
	$(PIP) install --upgrade pip
	@test -f requirements.txt && $(PIP) install -r requirements.txt || echo "ℹ️ no requirements.txt"

install-jobqueue: venv
	$(PIP) install 'python-telegram-bot[job-queue]'

install-scrape: venv
	$(PIP) install requests-html 'lxml[html_clean]' lxml_html_clean || true

# ---- Run helpers ----
run: venv
	@if [[ -x ./botctl.sh ]]; then \
		chmod +x ./botctl.sh; \
		./botctl.sh run; \
	elif [[ -f app.py ]]; then \
		$(PYBIN) app.py; \
	else \
		echo "❌ no botctl.sh or app.py found"; exit 1; \
	fi

start: venv
	@if [[ -x ./botctl.sh ]]; then \
		chmod +x ./botctl.sh; ./botctl.sh start; \
	else echo "❌ botctl.sh not found or not executable"; exit 1; fi

stop:
	@if [[ -x ./botctl.sh ]]; then \
		chmod +x ./botctl.sh; ./botctl.sh stop; \
	else echo "❌ botctl.sh not found or not executable"; exit 1; fi

scrape: venv
	@if [[ -f debug_scrape_once.py ]]; then \
		$(PYBIN) debug_scrape_once.py; \
	else \
		echo "❌ debug_scrape_once.py not found"; exit 1; \
	fi

version:
	@ver=""; \
	if [[ -f VERSION ]]; then ver=$$(tr -d '\n' < VERSION); \
	elif ls -1 $(PROJECT_NAME)_v*.zip >/dev/null 2>&1; then \
	  ver=$$(ls -1 $(PROJECT_NAME)_v*.zip | \
	    sed -E 's/.*_v([0-9]+\.[0-9]+\.[0-9]+)\.zip/\1 \0/' | sort -V | tail -n1 | awk '{print $$1}'); \
	fi; \
	if [[ -n "$$ver" ]]; then \
	  echo "📦 version: $$ver"; \
	else \
	  echo "ℹ️ version: unknown"; fi

# ---- Release flows (wraps releases.sh / release.sh) ----
# בוחר אוטומטית releases.sh; אם לא קיים, נופל ל-release.sh
_define_release = \
	script=""; \
	if [[ -x ./$(RELEASE_SH) ]]; then script=./$(RELEASE_SH); \
	elif [[ -x ./release.sh ]]; then script=./release.sh; \
	else echo "❌ releases.sh/release.sh not found"; exit 1; fi; \
	chmod +x $$script; \
	BUMP=$(BUMP) INCLUDE_DB=$(INCLUDE_DB) CHMOD=$(CHMOD) KEEP=$(KEEP) $$script $(1)


release:
	@chmod +x ./release.sh
	@BUMP=$(if $(BUMP),$(BUMP),patch) INCLUDE_DB=$(if $(INCLUDE_DB),$(INCLUDE_DB),0) CHMOD=$(CHMOD) OUT_DIR=$(OUT_DIR) ./release.sh

release-major:
	@chmod +x ./release.sh
	@BUMP=major INCLUDE_DB=$(if $(INCLUDE_DB),$(INCLUDE_DB),0) CHMOD=$(CHMOD) OUT_DIR=$(OUT_DIR) ./release.sh

release-minor:
	@chmod +x ./release.sh
	@BUMP=minor INCLUDE_DB=$(if $(INCLUDE_DB),$(INCLUDE_DB),0) CHMOD=$(CHMOD) OUT_DIR=$(OUT_DIR) ./release.sh

release-patch:
	@chmod +x ./release.sh
	@BUMP=patch INCLUDE_DB=$(if $(INCLUDE_DB),$(INCLUDE_DB),0) CHMOD=$(CHMOD) OUT_DIR=$(OUT_DIR) ./release.sh

release-set:
	@test -n "$(VERSION)" || (echo "❌ Missing VERSION=X.Y.Z"; exit 1)
	@chmod +x ./release.sh
	@OUT_DIR=$(OUT_DIR) ./release.sh --set $(VERSION)


# קיצורים
rmaj:   ; @$(MAKE) release BUMP=major
rmin:   ; @$(MAKE) release BUMP=minor
rpatch: ; @$(MAKE) release BUMP=patch
rdb:    ; @$(MAKE) release INCLUDE_DB=1

clean:
	@find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	@find . -name ".pytest_cache" -type d -prune -exec rm -rf {} +
	@rm -rf *.egg-info
	@echo "🧹 clean done"
