"""Parser recursivo descendente da linguagem trama."""

from __future__ import annotations

from dataclasses import dataclass

from .ast_nodes import (
    AssignStmt,
    BinaryExpr,
    BreakStmt,
    CallExpr,
    ContinueStmt,
    DictExpr,
    Expr,
    ExprStmt,
    FunctionDecl,
    Identifier,
    IfStmt,
    ImportStmt,
    IndexExpr,
    ListExpr,
    Literal,
    Program,
    ReturnStmt,
    Stmt,
    ThrowStmt,
    TryStmt,
    UnaryExpr,
    WhileStmt,
)
from .lexer import tokenizar
from .token import Token


class ParseError(ValueError):
    """Erro de análise sintática."""


@dataclass
class Parser:
    tokens: list[Token]
    current: int = 0

    def parse(self) -> Program:
        declarations: list[Stmt] = []
        self._skip_separators()
        while not self._is_at_end():
            declarations.append(self._declaration())
            self._skip_separators()
        return Program(declarations=declarations)

    def _declaration(self) -> Stmt:
        if self._match("FUNCAO"):
            return self._function_decl()
        return self._statement()

    def _function_decl(self) -> FunctionDecl:
        name = self._consume("IDENT", "Esperado nome da função.")
        self._consume("ABRE_PAREN", "Esperado '(' após nome da função.")
        params: list[str] = []
        if not self._check("FECHA_PAREN"):
            while True:
                param = self._consume("IDENT", "Esperado nome de parâmetro.")
                params.append(param.lexema)
                if not self._match("VIRGULA"):
                    break
        self._consume("FECHA_PAREN", "Esperado ')' após parâmetros.")
        self._consume_optional_separators_or_error("Esperado nova linha após cabeçalho da função.")
        body = self._parse_block(until={"FIM"})
        self._consume("FIM", "Esperado 'fim' para encerrar função.")
        return FunctionDecl(name=name.lexema, params=params, body=body)

    def _statement(self) -> Stmt:
        if self._match("SE"):
            return self._if_stmt()
        if self._match("ENQUANTO"):
            return self._while_stmt()
        if self._match("RETORNE"):
            return self._return_stmt()
        if self._match("PARE"):
            return BreakStmt()
        if self._match("CONTINUE"):
            return ContinueStmt()
        if self._match("LANCE"):
            return self._throw_stmt()
        if self._match("TENTE"):
            return self._try_stmt()
        if self._match("IMPORTE"):
            return self._import_stmt()
        return self._assignment_or_expr_stmt()

    def _import_stmt(self) -> ImportStmt:
        if self._match("TEXTO"):
            module = self._previous().lexema
            default_alias = module.rsplit("/", 1)[-1].removesuffix(".trm")
        else:
            ident = self._consume("IDENT", "Esperado nome do módulo ou string no importe.")
            module = ident.lexema
            default_alias = ident.lexema
        alias = default_alias
        if self._match("COMO"):
            alias = self._consume("IDENT", "Esperado alias após 'como'.").lexema
        return ImportStmt(module=module, alias=alias)

    def _if_stmt(self) -> IfStmt:
        condition = self._expression()
        self._consume_optional_separators_or_error("Esperado nova linha após condição do 'se'.")
        then_branch = self._parse_block(until={"SENAO", "FIM"})
        else_branch: list[Stmt] | None = None
        if self._match("SENAO"):
            self._consume_optional_separators_or_error("Esperado nova linha após 'senão'.")
            else_branch = self._parse_block(until={"FIM"})
        self._consume("FIM", "Esperado 'fim' para encerrar bloco 'se'.")
        return IfStmt(condition=condition, then_branch=then_branch, else_branch=else_branch)

    def _while_stmt(self) -> WhileStmt:
        condition = self._expression()
        self._consume_optional_separators_or_error("Esperado nova linha após condição do 'enquanto'.")
        body = self._parse_block(until={"FIM"})
        self._consume("FIM", "Esperado 'fim' para encerrar 'enquanto'.")
        return WhileStmt(condition=condition, body=body)

    def _return_stmt(self) -> ReturnStmt:
        if self._check_any({"NOVA_LINHA", "PONTO_VIRGULA", "EOF", "FIM"}):
            return ReturnStmt(value=None)
        return ReturnStmt(value=self._expression())

    def _throw_stmt(self) -> ThrowStmt:
        return ThrowStmt(value=self._expression())

    def _try_stmt(self) -> TryStmt:
        self._consume_optional_separators_or_error("Esperado nova linha após 'tente'.")
        try_branch = self._parse_block(until={"PEGUE", "FINALMENTE", "FIM"})

        catch_name: str | None = None
        catch_branch: list[Stmt] | None = None
        finally_branch: list[Stmt] | None = None

        if self._match("PEGUE"):
            if self._check("IDENT"):
                catch_name = self._advance().lexema
            self._consume_optional_separators_or_error("Esperado nova linha após 'pegue'.")
            catch_branch = self._parse_block(until={"FINALMENTE", "FIM"})

        if self._match("FINALMENTE"):
            self._consume_optional_separators_or_error("Esperado nova linha após 'finalmente'.")
            finally_branch = self._parse_block(until={"FIM"})

        if catch_branch is None and finally_branch is None:
            token = self._peek()
            raise ParseError(
                f"Bloco 'tente' exige 'pegue' e/ou 'finalmente' (linha {token.linha}, coluna {token.coluna})"
            )

        self._consume("FIM", "Esperado 'fim' para encerrar bloco 'tente'.")
        return TryStmt(
            try_branch=try_branch,
            catch_name=catch_name,
            catch_branch=catch_branch,
            finally_branch=finally_branch,
        )

    def _assignment_or_expr_stmt(self) -> Stmt:
        if self._check("IDENT") and self._check_next("IGUAL"):
            name = self._advance().lexema
            self._advance()  # IGUAL
            value = self._expression()
            return AssignStmt(name=name, value=value)
        return ExprStmt(expression=self._expression())

    def _parse_block(self, until: set[str]) -> list[Stmt]:
        body: list[Stmt] = []
        self._skip_separators()
        while not self._is_at_end() and not self._check_any(until):
            body.append(self._declaration())
            self._skip_separators()
        return body

    def _expression(self) -> Expr:
        return self._equality()

    def _equality(self) -> Expr:
        expr = self._comparison()
        while self._match("IGUAL_IGUAL", "DIFERENTE"):
            operator = self._previous().tipo
            right = self._comparison()
            expr = BinaryExpr(left=expr, operator=operator, right=right)
        return expr

    def _comparison(self) -> Expr:
        expr = self._term()
        while self._match("MAIOR", "MAIOR_IGUAL", "MENOR", "MENOR_IGUAL"):
            operator = self._previous().tipo
            right = self._term()
            expr = BinaryExpr(left=expr, operator=operator, right=right)
        return expr

    def _term(self) -> Expr:
        expr = self._factor()
        while self._match("MAIS", "MENOS"):
            operator = self._previous().tipo
            right = self._factor()
            expr = BinaryExpr(left=expr, operator=operator, right=right)
        return expr

    def _factor(self) -> Expr:
        expr = self._unary()
        while self._match("ASTERISCO", "BARRA"):
            operator = self._previous().tipo
            right = self._unary()
            expr = BinaryExpr(left=expr, operator=operator, right=right)
        return expr

    def _unary(self) -> Expr:
        if self._match("MENOS"):
            operator = self._previous().tipo
            return UnaryExpr(operator=operator, operand=self._unary())
        return self._call()

    def _call(self) -> Expr:
        expr = self._primary()
        while True:
            if self._match("ABRE_PAREN"):
                args: list[Expr] = []
                if not self._check("FECHA_PAREN"):
                    while True:
                        args.append(self._expression())
                        if not self._match("VIRGULA"):
                            break
                self._consume("FECHA_PAREN", "Esperado ')' após argumentos.")
                expr = CallExpr(callee=expr, arguments=args)
                continue

            if self._match("ABRE_COLCHETE"):
                idx = self._expression()
                self._consume("FECHA_COLCHETE", "Esperado ']' no índice.")
                expr = IndexExpr(target=expr, index=idx)
                continue

            break
        return expr

    def _primary(self) -> Expr:
        if self._match("NUMERO"):
            lex = self._previous().lexema
            if "." in lex:
                return Literal(value=float(lex))
            return Literal(value=int(lex))
        if self._match("TEXTO"):
            return Literal(value=self._previous().lexema)
        if self._match("VERDADEIRO"):
            return Literal(value=True)
        if self._match("FALSO"):
            return Literal(value=False)
        if self._match("NULO"):
            return Literal(value=None)
        if self._match("IDENT"):
            return Identifier(name=self._previous().lexema)
        if self._match("ABRE_PAREN"):
            expr = self._expression()
            self._consume("FECHA_PAREN", "Esperado ')' após expressão.")
            return expr
        if self._match("ABRE_COLCHETE"):
            elements: list[Expr] = []
            if not self._check("FECHA_COLCHETE"):
                while True:
                    elements.append(self._expression())
                    if not self._match("VIRGULA"):
                        break
            self._consume("FECHA_COLCHETE", "Esperado ']' no literal de lista.")
            return ListExpr(elements=elements)
        if self._match("ABRE_CHAVE"):
            entries: list[tuple[Expr, Expr]] = []
            if not self._check("FECHA_CHAVE"):
                while True:
                    key = self._expression()
                    self._consume("DOIS_PONTOS", "Esperado ':' no literal de mapa.")
                    value = self._expression()
                    entries.append((key, value))
                    if not self._match("VIRGULA"):
                        break
            self._consume("FECHA_CHAVE", "Esperado '}' no literal de mapa.")
            return DictExpr(entries=entries)

        token = self._peek()
        raise ParseError(f"Expressão inválida na linha {token.linha}, coluna {token.coluna}.")

    def _consume_optional_separators_or_error(self, msg: str) -> None:
        if not self._match("NOVA_LINHA", "PONTO_VIRGULA"):
            raise ParseError(msg)
        self._skip_separators()

    def _skip_separators(self) -> None:
        while self._match("NOVA_LINHA", "PONTO_VIRGULA"):
            pass

    def _match(self, *types: str) -> bool:
        for token_type in types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _consume(self, token_type: str, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        token = self._peek()
        raise ParseError(f"{message} (linha {token.linha}, coluna {token.coluna})")

    def _check(self, token_type: str) -> bool:
        if self._is_at_end():
            return token_type == "EOF"
        return self._peek().tipo == token_type

    def _check_next(self, token_type: str) -> bool:
        if self.current + 1 >= len(self.tokens):
            return False
        return self.tokens[self.current + 1].tipo == token_type

    def _check_any(self, types: set[str]) -> bool:
        if self._is_at_end():
            return "EOF" in types
        return self._peek().tipo in types

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().tipo == "EOF"

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]


def parse(codigo: str) -> Program:
    """Pipeline léxico + sintático para produzir AST."""
    tokens = tokenizar(codigo)
    parser = Parser(tokens=tokens)
    return parser.parse()
