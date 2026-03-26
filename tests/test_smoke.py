from trama.cli import main


def test_cli_sem_argumentos_retorna_zero() -> None:
    assert main([]) == 0
