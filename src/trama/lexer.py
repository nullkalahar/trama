"""Lexer da linguagem trama.

Características:
- palavras-chave com/sem acento são equivalentes;
- keywords são case-insensitive;
- comentários de linha com "#" e "//";
- strings com escapes básicos;
- rastreamento de linha/coluna para erros.
"""

from __future__ import annotations

import unicodedata

from .token import Token


KEYWORDS: dict[str, str] = {
    "funcao": "FUNCAO",
    "retorne": "RETORNE",
    "se": "SE",
    "senao": "SENAO",
    "enquanto": "ENQUANTO",
    "para": "PARA",
    "em": "EM",
    "verdadeiro": "VERDADEIRO",
    "falso": "FALSO",
    "nulo": "NULO",
    "fim": "FIM",
    "pare": "PARE",
    "continue": "CONTINUE",
}

SINGLE_CHAR_TOKENS: dict[str, str] = {
    "(": "ABRE_PAREN",
    ")": "FECHA_PAREN",
    ",": "VIRGULA",
    ":": "DOIS_PONTOS",
    ".": "PONTO",
    ";": "PONTO_VIRGULA",
    "=": "IGUAL",
    "+": "MAIS",
    "-": "MENOS",
    "*": "ASTERISCO",
    "/": "BARRA",
    ">": "MAIOR",
    "<": "MENOR",
}

DOUBLE_CHAR_TOKENS: dict[str, str] = {
    "==": "IGUAL_IGUAL",
    "!=": "DIFERENTE",
    ">=": "MAIOR_IGUAL",
    "<=": "MENOR_IGUAL",
}


class LexError(ValueError):
    """Erro de análise léxica."""


def _normalizar_palavra(valor: str) -> str:
    """Normaliza para comparação de palavras-chave.

    Regras:
    - lowercase
    - remove diacríticos (ex.: função -> funcao, senão -> senao)
    """
    decomposed = unicodedata.normalize("NFD", valor.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _is_ident_start(ch: str) -> bool:
    return ch == "_" or ch.isalpha()


def _is_ident_part(ch: str) -> bool:
    return ch == "_" or ch.isalnum()


def tokenizar(codigo: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    linha = 1
    coluna = 1
    tamanho = len(codigo)

    def avancar(quantidade: int = 1) -> None:
        nonlocal i, coluna
        i += quantidade
        coluna += quantidade

    while i < tamanho:
        ch = codigo[i]

        if ch in {" ", "\t", "\r"}:
            avancar()
            continue

        if ch == "\n":
            tokens.append(Token("NOVA_LINHA", "\n", linha, coluna))
            i += 1
            linha += 1
            coluna = 1
            continue

        if ch == "#":
            while i < tamanho and codigo[i] != "\n":
                avancar()
            continue

        if ch == "/" and i + 1 < tamanho and codigo[i + 1] == "/":
            avancar(2)
            while i < tamanho and codigo[i] != "\n":
                avancar()
            continue

        if i + 1 < tamanho:
            duo = codigo[i : i + 2]
            if duo in DOUBLE_CHAR_TOKENS:
                tokens.append(Token(DOUBLE_CHAR_TOKENS[duo], duo, linha, coluna))
                avancar(2)
                continue

        if ch in SINGLE_CHAR_TOKENS:
            tokens.append(Token(SINGLE_CHAR_TOKENS[ch], ch, linha, coluna))
            avancar()
            continue

        if ch == '"':
            col_inicio = coluna
            i += 1
            coluna += 1
            acumulado: list[str] = []

            while i < tamanho:
                atual = codigo[i]
                if atual == '"':
                    break
                if atual == "\n":
                    raise LexError(f"String não terminada na linha {linha}, coluna {col_inicio}")
                if atual == "\\":
                    if i + 1 >= tamanho:
                        raise LexError(
                            f"Escape inválido na string na linha {linha}, coluna {col_inicio}"
                        )
                    esc = codigo[i + 1]
                    escapes = {
                        '"': '"',
                        "\\": "\\",
                        "n": "\n",
                        "t": "\t",
                        "r": "\r",
                    }
                    if esc not in escapes:
                        raise LexError(
                            f"Escape inválido '\\{esc}' na linha {linha}, coluna {coluna}"
                        )
                    acumulado.append(escapes[esc])
                    i += 2
                    coluna += 2
                    continue
                acumulado.append(atual)
                i += 1
                coluna += 1

            if i >= tamanho:
                raise LexError(f"String não terminada na linha {linha}, coluna {col_inicio}")

            texto = "".join(acumulado)
            tokens.append(Token("TEXTO", texto, linha, col_inicio))
            i += 1
            coluna += 1
            continue

        if ch.isdigit():
            col_inicio = coluna
            inicio = i
            has_dot = False
            while i < tamanho and (codigo[i].isdigit() or codigo[i] == "."):
                if codigo[i] == ".":
                    if has_dot:
                        raise LexError(
                            f"Número real inválido na linha {linha}, coluna {col_inicio}"
                        )
                    has_dot = True
                    if i + 1 >= tamanho or not codigo[i + 1].isdigit():
                        raise LexError(
                            f"Número real inválido na linha {linha}, coluna {col_inicio}"
                        )
                i += 1
                coluna += 1
            numero = codigo[inicio:i]
            tokens.append(Token("NUMERO", numero, linha, col_inicio))
            continue

        if _is_ident_start(ch):
            col_inicio = coluna
            inicio = i
            while i < tamanho and _is_ident_part(codigo[i]):
                i += 1
                coluna += 1
            lexema = codigo[inicio:i]
            normalizado = _normalizar_palavra(lexema)
            tipo = KEYWORDS.get(normalizado, "IDENT")
            tokens.append(Token(tipo, lexema, linha, col_inicio))
            continue

        raise LexError(f"Caractere inesperado '{ch}' na linha {linha}, coluna {coluna}")

    tokens.append(Token("EOF", "", linha, coluna))
    return tokens
