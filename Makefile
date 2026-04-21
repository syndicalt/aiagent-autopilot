.PHONY: dev build clean

dev:
	cd src-tauri && cargo tauri dev

build:
	cd src-tauri && cargo tauri build

clean:
	cd src-tauri && cargo clean
