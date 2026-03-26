.PHONY: lint check run-example bytecode-example compile-example build-standalone package-deb

check:
	python3 -m py_compile src/trama/*.py tests/test_*.py

run-example:
	PYTHONPATH=src python3 -m trama.cli executar examples/ola_mundo.trm

bytecode-example:
	PYTHONPATH=src python3 -m trama.cli bytecode examples/ola_mundo.trm

compile-example:
	PYTHONPATH=src python3 -m trama.cli compilar examples/ola_mundo.trm -o build/ola.tbc

build-standalone:
	scripts/build_standalone.sh

package-deb:
	scripts/package_deb.sh 0.1.0 amd64
