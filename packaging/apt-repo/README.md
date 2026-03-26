# Repositório APT da trama

Este diretório é a base para o repositório APT local/publicado da `trama`.

Inicialize com:

```bash
scripts/init_apt_repo.sh packaging/apt-repo stable main trama <SEU_GPG_KEY_ID>
```

Publique um pacote `.deb` com:

```bash
scripts/publish_apt_package.sh packaging/apt-repo stable ./build/trama_0.1.0_amd64.deb
```
