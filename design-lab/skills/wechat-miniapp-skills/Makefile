.PHONY: validate test package

validate:
	python3 scripts/validate_skills.py

test:
	python3 -m unittest discover -s tests

package: validate test
	cd .. && zip -r wechat-miniapp-skills.zip wechat-miniapp-skills -x 'wechat-miniapp-skills/.git/*'
