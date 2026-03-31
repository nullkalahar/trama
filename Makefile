.PHONY: lint check run-example bytecode-example compile-example build-standalone package-deb build-native-stub test-native

check:
	python3 -m py_compile src/trama/*.py tests/test_*.py

run-example:
	PYTHONPATH=src python3 -m trama.cli executar exemplos/ola_mundo.trm

bytecode-example:
	PYTHONPATH=src python3 -m trama.cli bytecode exemplos/ola_mundo.trm

compile-example:
	PYTHONPATH=src python3 -m trama.cli compilar exemplos/ola_mundo.trm -o build/ola.tbc

build-standalone:
	scripts/build_standalone.sh

package-deb:
	scripts/package_deb.sh 0.1.0 amd64

build-native-stub:
	scripts/build_native_stub.sh

test-native:
	bash .local/tests/v2_0_native/run_local_v20_native.sh
