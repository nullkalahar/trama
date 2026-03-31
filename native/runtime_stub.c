#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc >= 2 && strcmp(argv[1], "--diagnostico-runtime") == 0) {
        puts("runtime_backend=nativo_stub");
        puts("python_host_required=nao");
        return 0;
    }
    puts("trama nativo (stub) - use --diagnostico-runtime");
    return 0;
}
