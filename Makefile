.PHONY: commit

commit:
	@if [ -z "$(msg)" ]; then \
		echo "Error: commit message is required. Usage: make commit msg=\"your message\" tag=\"version\""; \
		exit 1; \
	fi
	@if [ -z "$(tag)" ]; then \
		echo "Error: tag is required. Usage: make commit msg=\"your message\" tag=\"version\""; \
		exit 1; \
	fi
	git add .
	git commit -m "$(msg)"
	git tag -a "$(tag)" -m "$(msg)"
	git push
	git push --tags 