"""Parser recursivo descendente da linguagem trama."""

from __future__ import annotations

from dataclasses import dataclass

from .ast_nodes import (
    AssignStmt,
    AwaitExpr,
    BinaryExpr,
    BreakStmt,
    CallExpr,
    ContinueStmt,
    DictExpr,
    Expr,
    ExprStmt,
    ExportStmt,
    ForStmt,
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
    TypeRef,
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
        if self._match("ASSINCRONA"):
            self._consume("FUNCAO", "Esperado 'função' após 'assíncrona'.")
            return self._function_decl(is_async=True)
        if self._match("FUNCAO"):
            return self._function_decl(is_async=False)
        return self._statement()

    def _function_decl(self, is_async: bool) -> FunctionDecl:
        name = self._consume("IDENT", "Esperado nome da função.")
        self._consume("ABRE_PAREN", "Esperado '(' após nome da função.")
        params: list[str] = []
        param_types: dict[str, TypeRef] = {}
        if not self._check("FECHA_PAREN"):
            while True:
                param = self._consume("IDENT", "Esperado nome de parâmetro.")
                params.append(param.lexema)
                if self._match("DOIS_PONTOS"):
                    param_types[param.lexema] = self._parse_type_ref(until={"VIRGULA", "FECHA_PAREN"})
                if not self._match("VIRGULA"):
                    break
        self._consume("FECHA_PAREN", "Esperado ')' após parâmetros.")
        return_type: TypeRef | None = None
        if self._match("DOIS_PONTOS"):
            return_type = self._parse_type_ref(until={"NOVA_LINHA", "PONTO_VIRGULA"})
        self._consume_optional_separators_or_error("Esperado nova linha após cabeçalho da função.")
        body = self._parse_block(until={"FIM"})
        self._consume("FIM", "Esperado 'fim' para encerrar função.")
        return FunctionDecl(
            name=name.lexema,
            params=params,
            body=body,
            is_async=is_async,
            param_types=(param_types or None),
            return_type=return_type,
            linha=name.linha,
            coluna=name.coluna,
        )

    def _statement(self) -> Stmt:
        if self._match("SE"):
            return self._if_stmt()
        if self._match("ENQUANTO"):
            return self._while_stmt()
        if self._match("PARA"):
            return self._for_stmt()
        if self._match("RETORNE"):
            return self._return_stmt()
        if self._match("PARE"):
            tok = self._previous()
            return BreakStmt(linha=tok.linha, coluna=tok.coluna)
        if self._match("CONTINUE"):
            tok = self._previous()
            return ContinueStmt(linha=tok.linha, coluna=tok.coluna)
        if self._match("LANCE"):
            return self._throw_stmt()
        if self._match("TENTE"):
            return self._try_stmt()
        if self._match("IMPORTE"):
            return self._import_stmt()
        if self._match("EXPORTE"):
            return self._export_stmt()
        return self._assignment_or_expr_stmt()

    def _import_stmt(self) -> ImportStmt:
        kw = self._previous()
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
        names: list[str] | None = None
        if self._match("EXPONDO"):
            names = []
            while True:
                names.append(self._consume("IDENT", "Esperado nome exportado após 'expondo'.").lexema)
                if not self._match("VIRGULA"):
                    break
        return ImportStmt(module=module, alias=alias, names=names, linha=kw.linha, coluna=kw.coluna)

    def _export_stmt(self) -> ExportStmt:
        kw = self._previous()
        names: list[str] = []
        while True:
            names.append(self._consume("IDENT", "Esperado nome após 'exporte'.").lexema)
            if not self._match("VIRGULA"):
                break
        return ExportStmt(names=names, linha=kw.linha, coluna=kw.coluna)

    def _if_stmt(self) -> IfStmt:
        kw = self._previous()
        condition = self._expression()
        self._consume_optional_separators_or_error("Esperado nova linha após condição do 'se'.")
        then_branch = self._parse_block(until={"SENAO", "FIM"})
        else_branch: list[Stmt] | None = None
        if self._match("SENAO"):
            self._consume_optional_separators_or_error("Esperado nova linha após 'senão'.")
            else_branch = self._parse_block(until={"FIM"})
        self._consume("FIM", "Esperado 'fim' para encerrar bloco 'se'.")
        return IfStmt(condition=condition, then_branch=then_branch, else_branch=else_branch, linha=kw.linha, coluna=kw.coluna)

    def _while_stmt(self) -> WhileStmt:
        kw = self._previous()
        condition = self._expression()
        self._consume_optional_separators_or_error("Esperado nova linha após condição do 'enquanto'.")
        body = self._parse_block(until={"FIM"})
        self._consume("FIM", "Esperado 'fim' para encerrar 'enquanto'.")
        return WhileStmt(condition=condition, body=body, linha=kw.linha, coluna=kw.coluna)

    def _for_stmt(self) -> ForStmt:
        kw = self._previous()
        it = self._consume("IDENT", "Esperado identificador de iteração em 'para'.")
        self._consume("EM", "Esperado 'em' em 'para'.")
        iterable = self._expression()
        self._consume_optional_separators_or_error("Esperado nova linha após cabeçalho de 'para/em'.")
        body = self._parse_block(until={"FIM"})
        self._consume("FIM", "Esperado 'fim' para encerrar 'para'.")
        return ForStmt(iterator=it.lexema, iterable=iterable, body=body, linha=kw.linha, coluna=kw.coluna)

    def _return_stmt(self) -> ReturnStmt:
        tok = self._previous()
        if self._check_any({"NOVA_LINHA", "PONTO_VIRGULA", "EOF", "FIM"}):
            return ReturnStmt(value=None, linha=tok.linha, coluna=tok.coluna)
        return ReturnStmt(value=self._expression(), linha=tok.linha, coluna=tok.coluna)

    def _throw_stmt(self) -> ThrowStmt:
        kw = self._previous()
        return ThrowStmt(value=self._expression(), linha=kw.linha, coluna=kw.coluna)

    def _try_stmt(self) -> TryStmt:
        kw = self._previous()
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
            linha=kw.linha,
            coluna=kw.coluna,
        )

    def _assignment_or_expr_stmt(self) -> Stmt:
        if self._check("IDENT") and (self._check_next("IGUAL") or self._check_next("DOIS_PONTOS")):
            name_tok = self._advance()
            annotation: TypeRef | None = None
            if self._match("DOIS_PONTOS"):
                annotation = self._parse_type_ref(until={"IGUAL", "NOVA_LINHA", "PONTO_VIRGULA", "EOF"})
            self._consume("IGUAL", "Esperado '=' em atribuição.")
            value = self._expression()
            return AssignStmt(
                name=name_tok.lexema,
                value=value,
                annotation=annotation,
                linha=name_tok.linha,
                coluna=name_tok.coluna,
            )
        expr = self._expression()
        return ExprStmt(expression=expr)

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
        if self._match("AGUARDE"):
            tok = self._previous()
            return AwaitExpr(expression=self._unary(), linha=tok.linha, coluna=tok.coluna)
        if self._match("MENOS"):
            operator = self._previous().tipo
            tok = self._previous()
            return UnaryExpr(operator=operator, operand=self._unary(), linha=tok.linha, coluna=tok.coluna)
        return self._call()

    def _call(self) -> Expr:
        expr = self._primary()
        while True:
            self._skip_call_continuation_separators()
            if self._match("ABRE_PAREN"):
                args: list[Expr] = []
                self._skip_expr_separators()
                if not self._check("FECHA_PAREN"):
                    while True:
                        self._skip_expr_separators()
                        args.append(self._expression())
                        self._skip_expr_separators()
                        if not self._match("VIRGULA"):
                            break
                        self._skip_expr_separators()
                self._consume("FECHA_PAREN", "Esperado ')' após argumentos.")
                tok = self._previous()
                expr = CallExpr(callee=expr, arguments=args, linha=tok.linha, coluna=tok.coluna)
                continue

            self._skip_call_continuation_separators()
            if self._match("ABRE_COLCHETE"):
                self._skip_expr_separators()
                idx = self._expression()
                self._skip_expr_separators()
                self._consume("FECHA_COLCHETE", "Esperado ']' no índice.")
                tok = self._previous()
                expr = IndexExpr(target=expr, index=idx, linha=tok.linha, coluna=tok.coluna)
                continue

            break
        return expr

    def _primary(self) -> Expr:
        if self._match("NUMERO"):
            lex = self._previous().lexema
            tok = self._previous()
            if "." in lex:
                return Literal(value=float(lex), linha=tok.linha, coluna=tok.coluna)
            return Literal(value=int(lex), linha=tok.linha, coluna=tok.coluna)
        if self._match("TEXTO"):
            tok = self._previous()
            return Literal(value=self._previous().lexema, linha=tok.linha, coluna=tok.coluna)
        if self._match("VERDADEIRO"):
            tok = self._previous()
            return Literal(value=True, linha=tok.linha, coluna=tok.coluna)
        if self._match("FALSO"):
            tok = self._previous()
            return Literal(value=False, linha=tok.linha, coluna=tok.coluna)
        if self._match("NULO"):
            tok = self._previous()
            return Literal(value=None, linha=tok.linha, coluna=tok.coluna)
        if self._match("IDENT"):
            tok = self._previous()
            return Identifier(name=self._previous().lexema, linha=tok.linha, coluna=tok.coluna)
        if self._match("ABRE_PAREN"):
            self._skip_expr_separators()
            expr = self._expression()
            self._skip_expr_separators()
            self._consume("FECHA_PAREN", "Esperado ')' após expressão.")
            return expr
        if self._match("ABRE_COLCHETE"):
            elements: list[Expr] = []
            self._skip_expr_separators()
            if not self._check("FECHA_COLCHETE"):
                while True:
                    self._skip_expr_separators()
                    elements.append(self._expression())
                    self._skip_expr_separators()
                    if not self._match("VIRGULA"):
                        break
                    self._skip_expr_separators()
            self._consume("FECHA_COLCHETE", "Esperado ']' no literal de lista.")
            tok = self._previous()
            return ListExpr(elements=elements, linha=tok.linha, coluna=tok.coluna)
        if self._match("ABRE_CHAVE"):
            entries: list[tuple[Expr, Expr]] = []
            self._skip_expr_separators()
            if not self._check("FECHA_CHAVE"):
                while True:
                    self._skip_expr_separators()
                    key = self._expression()
                    self._skip_expr_separators()
                    self._consume("DOIS_PONTOS", "Esperado ':' no literal de mapa.")
                    self._skip_expr_separators()
                    value = self._expression()
                    entries.append((key, value))
                    self._skip_expr_separators()
                    if not self._match("VIRGULA"):
                        break
                    self._skip_expr_separators()
            self._consume("FECHA_CHAVE", "Esperado '}' no literal de mapa.")
            tok = self._previous()
            return DictExpr(entries=entries, linha=tok.linha, coluna=tok.coluna)

        token = self._peek()
        raise ParseError(f"Expressão inválida na linha {token.linha}, coluna {token.coluna}.")

    def _consume_optional_separators_or_error(self, msg: str) -> None:
        if not self._match("NOVA_LINHA", "PONTO_VIRGULA"):
            raise ParseError(msg)
        self._skip_separators()

    def _skip_separators(self) -> None:
        while self._match("NOVA_LINHA", "PONTO_VIRGULA"):
            pass

    def _skip_expr_separators(self) -> None:
        while self._match("NOVA_LINHA"):
            pass

    def _skip_call_continuation_separators(self) -> None:
        while self._check("NOVA_LINHA") and self._check_next_any({"ABRE_PAREN", "ABRE_COLCHETE"}):
            self._advance()

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

    def _check_next_any(self, types: set[str]) -> bool:
        if self.current + 1 >= len(self.tokens):
            return False
        return self.tokens[self.current + 1].tipo in types

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

    def _parse_type_ref(self, until: set[str]) -> TypeRef:
        tipo = self._consume("IDENT", "Esperado tipo na anotação.")
        args: list[TypeRef] = []
        if self._match("ABRE_COLCHETE"):
            while True:
                args.append(self._parse_type_ref(until={"VIRGULA", "FECHA_COLCHETE"}))
                if not self._match("VIRGULA"):
                    break
            self._consume("FECHA_COLCHETE", "Esperado ']' na anotação de tipo.")
        if self._check_any(until):
            return TypeRef(nome=tipo.lexema, args=args)
        # union opcional simplificada com `|`: tipo_a|tipo_b => uniao[tipo_a,tipo_b]
        if self._match("BARRA_VERTICAL"):
            outros = [self._parse_type_ref(until=until)]
            while self._match("BARRA_VERTICAL"):
                outros.append(self._parse_type_ref(until=until))
            return TypeRef(nome="uniao", args=[TypeRef(nome=tipo.lexema, args=args), *outros])
        return TypeRef(nome=tipo.lexema, args=args)


def parse(codigo: str) -> Program:
    """Pipeline léxico + sintático para produzir AST."""
    tokens = tokenizar(codigo)
    parser = Parser(tokens=tokens)
    return parser.parse()
