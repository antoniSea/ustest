# Makefile for Useme Bot

.PHONY: setup run scrape generate-proposals check-db start-scheduler stop-scheduler clean help

PYTHON=python3

help:
	@echo "Useme Bot - Automation System"
	@echo "Commands:"
	@echo "  make setup              Install all required dependencies"
	@echo "  make run                Run the web application"
	@echo "  make scrape             Run the scraper once"
	@echo "  make generate-proposals Generate proposals for available jobs"
	@echo "  make check-db           Check database status"
	@echo "  make start-scheduler    Start the background task scheduler"
	@echo "  make stop-scheduler     Stop the background task scheduler"
	@echo "  make process-queue      Process pending tasks in the queue"
	@echo "  make clean              Clean up temporary files"
	@echo "  make help               Show this help"

setup:
	$(PYTHON) -m pip install -r requirements.txt
	chmod +x run_scheduler.sh

run:
	$(PYTHON) app.py

scrape:
	$(PYTHON) scraper.py

generate-proposals:
	$(PYTHON) ai_proposal_generator.py --use-database

check-db:
	$(PYTHON) check_db.py

start-scheduler:
	./run_scheduler.sh start

stop-scheduler:
	./run_scheduler.sh stop

process-queue:
	$(PYTHON) queue_worker.py

clean:
	rm -f *.pyc
	rm -rf __pycache__
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete 