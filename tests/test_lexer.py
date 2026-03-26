import pytest

from trama.lexer import LexError, tokenizar


def _tipos(codigo: str) -> list[str]:
    return [t.tipo for t in tokenizar(codigo)]


def test_palavras_chave_com_e_sem_acento_sao_equivalentes() -> None:
    codigo = "função main()\nfim\nfuncao outra()\nfim\nse verdadeiro\nsenao\nsenão\nfim\n"
    tipos = _tipos(codigo)
    assert tipos.count("FUNCAO") == 2
    assert tipos.count("SENAO") == 2


def test_lexema_original_e_preservado() -> None:
    tokens = tokenizar("função x()\nfuncao y()\n")
    lexemas_funcoes = [t.lexema for t in tokens if t.tipo == "FUNCAO"]
    assert lexemas_funcoes == ["função", "funcao"]


def test_tokens_basicos() -> None:
    tipos = _tipos('idade >= 18\nexibir("ok")\n')
    assert tipos == [
        "IDENT",
        "MAIOR_IGUAL",
        "NUMERO",
        "NOVA_LINHA",
        "IDENT",
        "ABRE_PAREN",
        "TEXTO",
        "FECHA_PAREN",
        "NOVA_LINHA",
        "EOF",
    ]


def test_keywords_case_insensitive() -> None:
    tipos = _tipos("FUNÇÃO main()\nSe verdadeiro\nSENAO\nfim\n")
    assert "FUNCAO" in tipos
    assert "SE" in tipos
    assert "SENAO" in tipos


def test_comentarios_hash_e_barra_barra() -> None:
    tipos = _tipos("x = 1 # comentário\n// outro comentário\ny = 2\n")
    assert tipos == [
        "IDENT",
        "IGUAL",
        "NUMERO",
        "NOVA_LINHA",
        "NOVA_LINHA",
        "IDENT",
        "IGUAL",
        "NUMERO",
        "NOVA_LINHA",
        "EOF",
    ]


def test_string_com_escapes() -> None:
    tokens = tokenizar(r'"linha\ncom\tescape e \"aspas\" e \\barra"')
    assert tokens[0].tipo == "TEXTO"
    assert tokens[0].lexema == 'linha\ncom\tescape e "aspas" e \\barra'


def test_operadores_duplos() -> None:
    tipos = _tipos("a == b\nc != d\ne <= f\ng >= h\n")
    assert tipos == [
        "IDENT",
        "IGUAL_IGUAL",
        "IDENT",
        "NOVA_LINHA",
        "IDENT",
        "DIFERENTE",
        "IDENT",
        "NOVA_LINHA",
        "IDENT",
        "MENOR_IGUAL",
        "IDENT",
        "NOVA_LINHA",
        "IDENT",
        "MAIOR_IGUAL",
        "IDENT",
        "NOVA_LINHA",
        "EOF",
    ]


def test_pontuacoes_adicionais() -> None:
    tipos = _tipos("a:b;\nobj.metodo()\n")
    assert tipos == [
        "IDENT",
        "DOIS_PONTOS",
        "IDENT",
        "PONTO_VIRGULA",
        "NOVA_LINHA",
        "IDENT",
        "PONTO",
        "IDENT",
        "ABRE_PAREN",
        "FECHA_PAREN",
        "NOVA_LINHA",
        "EOF",
    ]


def test_numero_real_valido() -> None:
    tokens = tokenizar("valor = 10.25\n")
    numero = [t for t in tokens if t.tipo == "NUMERO"][0]
    assert numero.lexema == "10.25"


def test_numero_real_invalido_com_ponto_final() -> None:
    with pytest.raises(LexError, match="Número real inválido"):
        tokenizar("valor = 10.\n")


def test_numero_real_invalido_com_dois_pontos() -> None:
    with pytest.raises(LexError, match="Número real inválido"):
        tokenizar("valor = 10.2.3\n")


def test_string_nao_terminada() -> None:
    with pytest.raises(LexError, match="String não terminada"):
        tokenizar('"abc')


def test_escape_invalido() -> None:
    with pytest.raises(LexError, match="Escape inválido"):
        tokenizar(r'"abc\q"')


def test_caractere_inesperado() -> None:
    with pytest.raises(LexError, match="Caractere inesperado"):
        tokenizar("x = @\n")
