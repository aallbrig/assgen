.PHONY: demo demo-clean

## demo: record all VHS tapes and produce dist/demo.mp4
demo:
	bash scripts/record-demo.sh

## demo-clean: remove recorded segments and final video
demo-clean:
	rm -rf demos/segments dist/demo.mp4
