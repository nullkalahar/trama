import pytest

from trama.ast_nodes import (
    AssignStmt,
    BinaryExpr,
    CallExpr,
    ExprStmt,
    FunctionDecl,
    Identifier,
    IfStmt,
    Literal,
    Program,
    ReturnStmt,
    WhileStmt,
)
from trama.parser import ParseError, parse


def test_parse_programa_com_funcao_basica() -> None:
    ast = parse("função principal()\n    exibir(\"oi\")\nfim\n")
    assert isinstance(ast, Program)
    assert len(ast.declarations) == 1
    func = ast.declarations[0]
    assert isinstance(func, FunctionDecl)
    assert func.name == "principal"
    assert func.params == []
    assert len(func.body) == 1
    stmt = func.body[0]
    assert isinstance(stmt, ExprStmt)
    assert isinstance(stmt.expression, CallExpr)
    assert isinstance(stmt.expression.callee, Identifier)
    assert stmt.expression.callee.name == "exibir"


def test_parse_funcao_sem_acento() -> None:
    ast = parse("funcao soma(a, b)\nretorne a + b\nfim\n")
    func = ast.declarations[0]
    assert isinstance(func, FunctionDecl)
    assert func.name == "soma"
    assert func.params == ["a", "b"]
    ret = func.body[0]
    assert isinstance(ret, ReturnStmt)
    assert isinstance(ret.value, BinaryExpr)


def test_precedencia_operadores() -> None:
    ast = parse("resultado = 1 + 2 * 3\n")
    stmt = ast.declarations[0]
    assert isinstance(stmt, AssignStmt)
    assert isinstance(stmt.value, BinaryExpr)
    assert stmt.value.operator == "MAIS"
    assert isinstance(stmt.value.right, BinaryExpr)
    assert stmt.value.right.operator == "ASTERISCO"


def test_if_com_senao_sem_acento() -> None:
    codigo = (
        "se verdadeiro\n"
        "    exibir(\"a\")\n"
        "senao\n"
        "    exibir(\"b\")\n"
        "fim\n"
    )
    ast = parse(codigo)
    stmt = ast.declarations[0]
    assert isinstance(stmt, IfStmt)
    assert isinstance(stmt.condition, Literal)
    assert stmt.condition.value is True
    assert len(stmt.then_branch) == 1
    assert stmt.else_branch is not None
    assert len(stmt.else_branch) == 1


def test_while_com_atribuicao() -> None:
    codigo = "enquanto x < 10\nx = x + 1\nfim\n"
    ast = parse(codigo)
    stmt = ast.declarations[0]
    assert isinstance(stmt, WhileStmt)
    assert len(stmt.body) == 1
    assert isinstance(stmt.body[0], AssignStmt)


def test_retorne_sem_valor() -> None:
    ast = parse("função f()\nretorne\nfim\n")
    func = ast.declarations[0]
    assert isinstance(func, FunctionDecl)
    ret = func.body[0]
    assert isinstance(ret, ReturnStmt)
    assert ret.value is None


def test_parse_error_em_fim_ausente() -> None:
    with pytest.raises(ParseError, match="Esperado 'fim'"):
        parse("se verdadeiro\nexibir(\"x\")\n")


def test_parse_error_em_expressao_invalida() -> None:
    with pytest.raises(ParseError, match="Expressão inválida"):
        parse("x =\n")
