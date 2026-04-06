#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <stdbool.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

/*
 * JSMN (JSON parser) - single-header style embed.
 * Source: https://github.com/zserge/jsmn (MIT)
 */
typedef enum {
    JSMN_UNDEFINED = 0,
    JSMN_OBJECT = 1,
    JSMN_ARRAY = 2,
    JSMN_STRING = 3,
    JSMN_PRIMITIVE = 4
} jsmntype_t;

typedef struct {
    jsmntype_t type;
    int start;
    int end;
    int size;
    int parent;
} jsmntok_t;

typedef struct {
    unsigned int pos;
    unsigned int toknext;
    int toksuper;
} jsmn_parser;

#define JSMN_ERROR_NOMEM -1
#define JSMN_ERROR_INVAL -2
#define JSMN_ERROR_PART -3

static void jsmn_init(jsmn_parser *parser) {
    parser->pos = 0;
    parser->toknext = 0;
    parser->toksuper = -1;
}

static jsmntok_t *jsmn_alloc_token(jsmn_parser *parser, jsmntok_t *tokens, size_t num_tokens) {
    if (parser->toknext >= num_tokens) {
        return NULL;
    }
    jsmntok_t *tok = &tokens[parser->toknext++];
    tok->start = tok->end = -1;
    tok->size = 0;
    tok->parent = -1;
    tok->type = JSMN_UNDEFINED;
    return tok;
}

static void jsmn_fill_token(jsmntok_t *token, jsmntype_t type, int start, int end) {
    token->type = type;
    token->start = start;
    token->end = end;
    token->size = 0;
}

static int jsmn_parse_primitive(jsmn_parser *parser, const char *js, size_t len, jsmntok_t *tokens, size_t num_tokens) {
    int start = (int)parser->pos;
    for (; parser->pos < len; parser->pos++) {
        char c = js[parser->pos];
        if (c == '\t' || c == '\r' || c == '\n' || c == ' ' || c == ',' || c == ']' || c == '}') {
            goto found;
        }
        if (c < 32 || c >= 127) {
            parser->pos = (unsigned int)start;
            return JSMN_ERROR_INVAL;
        }
    }
found:
    if (tokens == NULL) {
        parser->pos--;
        return 0;
    }
    jsmntok_t *token = jsmn_alloc_token(parser, tokens, num_tokens);
    if (token == NULL) {
        parser->pos = (unsigned int)start;
        return JSMN_ERROR_NOMEM;
    }
    jsmn_fill_token(token, JSMN_PRIMITIVE, start, (int)parser->pos);
    token->parent = parser->toksuper;
    parser->pos--;
    return 0;
}

static int jsmn_parse_string(jsmn_parser *parser, const char *js, size_t len, jsmntok_t *tokens, size_t num_tokens) {
    int start = (int)parser->pos;
    parser->pos++;
    for (; parser->pos < len; parser->pos++) {
        char c = js[parser->pos];
        if (c == '"') {
            if (tokens == NULL) {
                return 0;
            }
            jsmntok_t *token = jsmn_alloc_token(parser, tokens, num_tokens);
            if (token == NULL) {
                parser->pos = (unsigned int)start;
                return JSMN_ERROR_NOMEM;
            }
            jsmn_fill_token(token, JSMN_STRING, start + 1, (int)parser->pos);
            token->parent = parser->toksuper;
            return 0;
        }
        if (c == '\\') {
            parser->pos++;
            if (parser->pos == len) {
                parser->pos = (unsigned int)start;
                return JSMN_ERROR_PART;
            }
        }
    }
    parser->pos = (unsigned int)start;
    return JSMN_ERROR_PART;
}

static int jsmn_parse(jsmn_parser *parser, const char *js, size_t len, jsmntok_t *tokens, unsigned int num_tokens) {
    int r;
    int i;
    jsmntok_t *token;
    for (; parser->pos < len; parser->pos++) {
        char c = js[parser->pos];
        switch (c) {
            case '{':
            case '[':
                token = jsmn_alloc_token(parser, tokens, num_tokens);
                if (token == NULL) return JSMN_ERROR_NOMEM;
                if (parser->toksuper != -1) {
                    tokens[parser->toksuper].size++;
                    token->parent = parser->toksuper;
                }
                token->type = (c == '{' ? JSMN_OBJECT : JSMN_ARRAY);
                token->start = (int)parser->pos;
                parser->toksuper = (int)(parser->toknext - 1);
                break;
            case '}':
            case ']':
                for (i = (int)parser->toknext - 1; i >= 0; i--) {
                    token = &tokens[i];
                    if (token->start != -1 && token->end == -1) {
                        if ((token->type == JSMN_OBJECT && c == '}') || (token->type == JSMN_ARRAY && c == ']')) {
                            token->end = (int)parser->pos + 1;
                            parser->toksuper = token->parent;
                            break;
                        }
                        return JSMN_ERROR_INVAL;
                    }
                }
                if (i == -1) return JSMN_ERROR_INVAL;
                break;
            case '"':
                r = jsmn_parse_string(parser, js, len, tokens, num_tokens);
                if (r < 0) return r;
                if (parser->toksuper != -1) tokens[parser->toksuper].size++;
                break;
            case '\t':
            case '\r':
            case '\n':
            case ' ':
            case ':':
            case ',':
                break;
            default:
                r = jsmn_parse_primitive(parser, js, len, tokens, num_tokens);
                if (r < 0) return r;
                if (parser->toksuper != -1) tokens[parser->toksuper].size++;
                break;
        }
    }
    for (i = (int)parser->toknext - 1; i >= 0; i--) {
        if (tokens[i].start != -1 && tokens[i].end == -1) return JSMN_ERROR_PART;
    }
    return (int)parser->toknext;
}

typedef enum {
    VAL_NULL,
    VAL_BOOL,
    VAL_NUM,
    VAL_STR,
    VAL_LIST,
    VAL_MAP,
    VAL_BUILTIN_EXIBIR,
    VAL_BUILTIN_CRIAR_TAREFA,
    VAL_BUILTIN_COM_TIMEOUT,
    VAL_BUILTIN_CANCELAR_TAREFA,
    VAL_BUILTIN_DORMIR,
    VAL_FUNC,
    VAL_AWAITABLE,
    VAL_TASK
} ValueType;

typedef struct Value Value;
typedef struct List List;
typedef struct Map Map;
typedef struct Function Function;
typedef struct Env Env;
typedef struct Awaitable Awaitable;
typedef struct Task Task;

struct List {
    size_t len;
    size_t cap;
    Value *items;
};

struct Value {
    ValueType type;
    union {
        bool b;
        double n;
        char *s;
        List *list;
        Map *map;
        Function *fn;
        Awaitable *awaitable;
        Task *task;
    } as;
};

typedef enum {
    AWAITABLE_FN = 1,
    AWAITABLE_DORMIR = 2,
    AWAITABLE_TASK_TIMEOUT = 3
} AwaitableKind;

struct Awaitable {
    AwaitableKind kind;
    Function *fn;
    size_t argc;
    Value *args;
    Env *closure;
    double segundos;
    Task *task;
};

struct Task {
    void *program;
    Awaitable *awaitable;
    pthread_t th;
    pthread_mutex_t mu;
    pthread_cond_t cv;
    bool done;
    bool canceled;
    bool threw;
    Value value;
};

typedef struct {
    char *key;
    Value value;
} MapItem;

struct Map {
    size_t len;
    size_t cap;
    MapItem *items;
};

typedef enum {
    ARG_NONE,
    ARG_NUM,
    ARG_STR,
    ARG_MAKE_FN,
    ARG_TRY
} ArgType;

typedef struct {
    char *display;
    char *code;
    bool is_async;
} ArgMakeFn;

typedef struct {
    int catch_ip;
    int finally_ip;
    char *catch_name;
} ArgTry;

typedef struct {
    ArgType type;
    double n;
    char *s;
    ArgMakeFn make_fn;
    ArgTry try_arg;
} Arg;

typedef struct {
    char *op;
    Arg arg;
} Instr;

struct Function {
    char *code_name;
    char *name;
    bool is_async;
    size_t params_len;
    char **params;
    size_t instr_len;
    Instr *instrs;
    Env *closure;
};

typedef struct {
    Function *entry;
    size_t fn_len;
    Function *functions;
    char *origin_path;
} Program;

typedef struct {
    char *name;
    Value value;
} Binding;

struct Env {
    Env *parent;
    size_t len;
    size_t cap;
    Binding *items;
};

typedef struct {
    int catch_ip;
    int finally_ip;
    char *catch_name;
    int phase; /* 0=try, 1=catch, 2=finally */
    bool has_pending;
    Value pending;
} TryHandler;

typedef struct {
    Function *fn;
    size_t ip;
    Env *env;
    size_t stack_len;
    size_t stack_cap;
    Value *stack;
    size_t handlers_len;
    size_t handlers_cap;
    TryHandler *handlers;
} Frame;

typedef struct {
    bool threw;
    Value value;
} ExecResult;

typedef struct {
    char *path;
    Value exports;
} ModuleCacheEntry;

static int g_tok_count = 0;
static ModuleCacheEntry *g_module_cache = NULL;
static size_t g_module_cache_len = 0;
static size_t g_module_cache_cap = 0;

static void fatal(const char *msg) {
    fprintf(stderr, "Erro nativo: %s\n", msg);
    exit(1);
}

static char *xstrndup(const char *s, size_t n) {
    char *out = (char *)malloc(n + 1);
    if (!out) fatal("sem memória");
    memcpy(out, s, n);
    out[n] = '\0';
    return out;
}

static Value value_null(void) {
    Value v;
    v.type = VAL_NULL;
    return v;
}

static Value value_bool(bool b) {
    Value v;
    v.type = VAL_BOOL;
    v.as.b = b;
    return v;
}

static Value value_num(double n) {
    Value v;
    v.type = VAL_NUM;
    v.as.n = n;
    return v;
}

static Value value_str(char *s) {
    Value v;
    v.type = VAL_STR;
    v.as.s = s;
    return v;
}

static Value value_builtin_exibir(void) {
    Value v;
    v.type = VAL_BUILTIN_EXIBIR;
    return v;
}

static Value value_builtin_criar_tarefa(void) {
    Value v;
    v.type = VAL_BUILTIN_CRIAR_TAREFA;
    return v;
}

static Value value_builtin_com_timeout(void) {
    Value v;
    v.type = VAL_BUILTIN_COM_TIMEOUT;
    return v;
}

static Value value_builtin_cancelar_tarefa(void) {
    Value v;
    v.type = VAL_BUILTIN_CANCELAR_TAREFA;
    return v;
}

static Value value_builtin_dormir(void) {
    Value v;
    v.type = VAL_BUILTIN_DORMIR;
    return v;
}

static Value value_func(Function *fn) {
    Value v;
    v.type = VAL_FUNC;
    v.as.fn = fn;
    return v;
}

static Value value_awaitable(Awaitable *a) {
    Value v;
    v.type = VAL_AWAITABLE;
    v.as.awaitable = a;
    return v;
}

static Value value_task(Task *t) {
    Value v;
    v.type = VAL_TASK;
    v.as.task = t;
    return v;
}

static Awaitable *awaitable_new(Function *fn, Value *args, size_t argc, Env *closure) {
    Awaitable *a = (Awaitable *)calloc(1, sizeof(Awaitable));
    if (!a) fatal("sem memória");
    a->kind = AWAITABLE_FN;
    a->fn = fn;
    a->task = NULL;
    a->argc = argc;
    a->closure = closure;
    a->args = (Value *)calloc(argc ? argc : 1, sizeof(Value));
    if (!a->args) fatal("sem memória");
    for (size_t i = 0; i < argc; i++) {
        a->args[i] = args[i];
    }
    return a;
}

static Awaitable *awaitable_dormir_new(double segundos) {
    Awaitable *a = (Awaitable *)calloc(1, sizeof(Awaitable));
    if (!a) fatal("sem memória");
    a->kind = AWAITABLE_DORMIR;
    a->segundos = segundos < 0 ? 0 : segundos;
    a->argc = 0;
    a->args = NULL;
    a->closure = NULL;
    a->fn = NULL;
    a->task = NULL;
    return a;
}

static Awaitable *awaitable_task_timeout_new(Task *task, double segundos) {
    Awaitable *a = (Awaitable *)calloc(1, sizeof(Awaitable));
    if (!a) fatal("sem memória");
    a->kind = AWAITABLE_TASK_TIMEOUT;
    a->task = task;
    a->segundos = segundos < 0 ? 0 : segundos;
    a->argc = 0;
    a->args = NULL;
    a->closure = NULL;
    a->fn = NULL;
    return a;
}

static List *list_new(void) {
    List *l = (List *)calloc(1, sizeof(List));
    if (!l) fatal("sem memória");
    return l;
}

static void list_push(List *l, Value v) {
    if (l->len == l->cap) {
        l->cap = l->cap == 0 ? 8 : l->cap * 2;
        l->items = (Value *)realloc(l->items, l->cap * sizeof(Value));
        if (!l->items) fatal("sem memória");
    }
    l->items[l->len++] = v;
}

static Map *map_new(void) {
    Map *m = (Map *)calloc(1, sizeof(Map));
    if (!m) fatal("sem memória");
    return m;
}

static char *value_to_key(Value v) {
    char buf[128];
    if (v.type == VAL_STR) return strdup(v.as.s);
    if (v.type == VAL_NUM) {
        snprintf(buf, sizeof(buf), "%.15g", v.as.n);
        return strdup(buf);
    }
    if (v.type == VAL_BOOL) return strdup(v.as.b ? "true" : "false");
    if (v.type == VAL_NULL) return strdup("null");
    return strdup("<obj>");
}

static void map_set(Map *m, Value key, Value val) {
    char *k = value_to_key(key);
    for (size_t i = 0; i < m->len; i++) {
        if (strcmp(m->items[i].key, k) == 0) {
            free(k);
            m->items[i].value = val;
            return;
        }
    }
    if (m->len == m->cap) {
        m->cap = m->cap == 0 ? 8 : m->cap * 2;
        m->items = (MapItem *)realloc(m->items, m->cap * sizeof(MapItem));
        if (!m->items) fatal("sem memória");
    }
    m->items[m->len].key = k;
    m->items[m->len].value = val;
    m->len++;
}

static bool map_get(Map *m, Value key, Value *out) {
    char *k = value_to_key(key);
    for (size_t i = 0; i < m->len; i++) {
        if (strcmp(m->items[i].key, k) == 0) {
            *out = m->items[i].value;
            free(k);
            return true;
        }
    }
    free(k);
    return false;
}

static bool module_cache_get(const char *path, Value *out) {
    for (size_t i = 0; i < g_module_cache_len; i++) {
        if (strcmp(g_module_cache[i].path, path) == 0) {
            *out = g_module_cache[i].exports;
            return true;
        }
    }
    return false;
}

static void module_cache_put(const char *path, Value exports) {
    for (size_t i = 0; i < g_module_cache_len; i++) {
        if (strcmp(g_module_cache[i].path, path) == 0) {
            g_module_cache[i].exports = exports;
            return;
        }
    }
    if (g_module_cache_len == g_module_cache_cap) {
        g_module_cache_cap = g_module_cache_cap == 0 ? 16 : g_module_cache_cap * 2;
        g_module_cache = (ModuleCacheEntry *)realloc(g_module_cache, g_module_cache_cap * sizeof(ModuleCacheEntry));
        if (!g_module_cache) fatal("sem memória");
    }
    g_module_cache[g_module_cache_len].path = strdup(path);
    g_module_cache[g_module_cache_len].exports = exports;
    g_module_cache_len++;
}

static Env *env_new(Env *parent) {
    Env *e = (Env *)calloc(1, sizeof(Env));
    if (!e) fatal("sem memória");
    e->parent = parent;
    return e;
}

static bool env_contains_local(Env *e, const char *name) {
    for (size_t i = 0; i < e->len; i++) {
        if (strcmp(e->items[i].name, name) == 0) return true;
    }
    return false;
}

static void env_set_local(Env *e, const char *name, Value v) {
    for (size_t i = 0; i < e->len; i++) {
        if (strcmp(e->items[i].name, name) == 0) {
            e->items[i].value = v;
            return;
        }
    }
    if (e->len == e->cap) {
        e->cap = e->cap == 0 ? 16 : e->cap * 2;
        e->items = (Binding *)realloc(e->items, e->cap * sizeof(Binding));
        if (!e->items) fatal("sem memória");
    }
    e->items[e->len].name = strdup(name);
    e->items[e->len].value = v;
    e->len++;
}

static bool env_get(Env *e, const char *name, Value *out) {
    for (Env *cur = e; cur != NULL; cur = cur->parent) {
        for (size_t i = 0; i < cur->len; i++) {
            if (strcmp(cur->items[i].name, name) == 0) {
                *out = cur->items[i].value;
                return true;
            }
        }
    }
    return false;
}

static void env_set(Env *e, const char *name, Value v) {
    for (Env *cur = e; cur != NULL; cur = cur->parent) {
        for (size_t i = 0; i < cur->len; i++) {
            if (strcmp(cur->items[i].name, name) == 0) {
                cur->items[i].value = v;
                return;
            }
        }
    }
    env_set_local(e, name, v);
}

static bool token_streq(const char *js, const jsmntok_t *tok, const char *s) {
    size_t n = (size_t)(tok->end - tok->start);
    return strlen(s) == n && strncmp(js + tok->start, s, n) == 0;
}

static char *token_strdup(const char *js, const jsmntok_t *tok) {
    return xstrndup(js + tok->start, (size_t)(tok->end - tok->start));
}

static int tok_skip(jsmntok_t *toks, int i) {
    int j = i + 1;
    while (j < g_tok_count && toks[j].start >= 0 && toks[j].start < toks[i].end) {
        j++;
    }
    return j;
}

static int obj_get(const char *js, jsmntok_t *toks, int obj_i, const char *key) {
    int obj_end = toks[obj_i].end;
    for (int i = obj_i + 1; i < g_tok_count; i++) {
        if (toks[i].start >= obj_end) break;
        if (toks[i].parent == obj_i && toks[i].type == JSMN_STRING) {
            if (token_streq(js, &toks[i], key)) {
                return i + 1;
            }
        }
    }
    return -1;
}

static double parse_num_token(const char *js, jsmntok_t *tok) {
    char *s = token_strdup(js, tok);
    errno = 0;
    char *end = NULL;
    double v = strtod(s, &end);
    if (errno != 0 || end == s) {
        free(s);
        fatal("número inválido em bytecode");
    }
    free(s);
    return v;
}

static int parse_int_or_minus1(const char *js, jsmntok_t *tok) {
    if (tok->type == JSMN_PRIMITIVE && token_streq(js, tok, "null")) return -1;
    return (int)parse_num_token(js, tok);
}

static Arg parse_arg(const char *js, jsmntok_t *toks, int arg_i) {
    Arg a;
    memset(&a, 0, sizeof(a));
    if (arg_i < 0) {
        a.type = ARG_NONE;
        return a;
    }
    jsmntok_t *t = &toks[arg_i];
    if (t->type == JSMN_PRIMITIVE) {
        if (token_streq(js, t, "null")) {
            a.type = ARG_NONE;
            return a;
        }
        a.type = ARG_NUM;
        a.n = parse_num_token(js, t);
        return a;
    }
    if (t->type == JSMN_STRING) {
        a.type = ARG_STR;
        a.s = token_strdup(js, t);
        return a;
    }
    if (t->type == JSMN_ARRAY && t->size >= 2) {
        int p0 = arg_i + 1;
        int p1 = tok_skip(toks, p0);
        int p2 = tok_skip(toks, p1);
        a.type = ARG_MAKE_FN;
        a.make_fn.display = token_strdup(js, &toks[p0]);
        a.make_fn.code = token_strdup(js, &toks[p1]);
        a.make_fn.is_async = false;
        if (p2 < tok_skip(toks, arg_i) && toks[p2].type == JSMN_PRIMITIVE) {
            a.make_fn.is_async = token_streq(js, &toks[p2], "true");
        }
        return a;
    }
    if (t->type == JSMN_OBJECT) {
        int catch_i = obj_get(js, toks, arg_i, "catch_ip");
        int finally_i = obj_get(js, toks, arg_i, "finally_ip");
        int catch_name_i = obj_get(js, toks, arg_i, "catch_name");
        a.type = ARG_TRY;
        a.try_arg.catch_ip = catch_i >= 0 ? parse_int_or_minus1(js, &toks[catch_i]) : -1;
        a.try_arg.finally_ip = finally_i >= 0 ? parse_int_or_minus1(js, &toks[finally_i]) : -1;
        if (catch_name_i >= 0 && toks[catch_name_i].type == JSMN_STRING) {
            a.try_arg.catch_name = token_strdup(js, &toks[catch_name_i]);
        } else {
            a.try_arg.catch_name = strdup("");
        }
        return a;
    }
    a.type = ARG_NONE;
    return a;
}

static Value parse_load_const(const char *js, jsmntok_t *toks, int arg_i) {
    if (arg_i < 0) return value_null();
    jsmntok_t *t = &toks[arg_i];
    if (t->type == JSMN_STRING) return value_str(token_strdup(js, t));
    if (t->type == JSMN_PRIMITIVE) {
        if (token_streq(js, t, "null")) return value_null();
        if (token_streq(js, t, "true")) return value_bool(true);
        if (token_streq(js, t, "false")) return value_bool(false);
        return value_num(parse_num_token(js, t));
    }
    fatal("LOAD_CONST com tipo de arg não suportado no runtime nativo");
    return value_null();
}

static Function parse_function(const char *js, jsmntok_t *toks, int fn_i, const char *code_name) {
    Function fn;
    memset(&fn, 0, sizeof(fn));
    fn.code_name = code_name ? strdup(code_name) : strdup("__entry__");

    int name_i = obj_get(js, toks, fn_i, "name");
    int params_i = obj_get(js, toks, fn_i, "params");
    int async_i = obj_get(js, toks, fn_i, "is_async");
    int inst_i = obj_get(js, toks, fn_i, "instructions");
    if (name_i < 0 || params_i < 0 || async_i < 0 || inst_i < 0) fatal("FunctionCode inválido");

    fn.name = token_strdup(js, &toks[name_i]);
    fn.is_async = token_streq(js, &toks[async_i], "true");

    if (toks[params_i].type != JSMN_ARRAY) fatal("params inválido");
    fn.params_len = (size_t)toks[params_i].size;
    fn.params = (char **)calloc(fn.params_len ? fn.params_len : 1, sizeof(char *));
    int pi = params_i + 1;
    for (size_t i = 0; i < fn.params_len; i++) {
        fn.params[i] = token_strdup(js, &toks[pi]);
        pi = tok_skip(toks, pi);
    }

    if (toks[inst_i].type != JSMN_ARRAY) fatal("instructions inválido");
    fn.instr_len = (size_t)toks[inst_i].size;
    fn.instrs = (Instr *)calloc(fn.instr_len ? fn.instr_len : 1, sizeof(Instr));
    int ii = inst_i + 1;
    for (size_t i = 0; i < fn.instr_len; i++) {
        int op_i = obj_get(js, toks, ii, "op");
        int arg_i = obj_get(js, toks, ii, "arg");
        if (op_i < 0) fatal("instrução sem opcode");
        fn.instrs[i].op = token_strdup(js, &toks[op_i]);

        if (strcmp(fn.instrs[i].op, "LOAD_CONST") == 0) {
            fn.instrs[i].arg.type = ARG_NONE;
            Value v = parse_load_const(js, toks, arg_i);
            if (v.type == VAL_STR) {
                fn.instrs[i].arg.type = ARG_STR;
                fn.instrs[i].arg.s = v.as.s;
            } else if (v.type == VAL_NUM) {
                fn.instrs[i].arg.type = ARG_NUM;
                fn.instrs[i].arg.n = v.as.n;
            } else if (v.type == VAL_BOOL) {
                fn.instrs[i].arg.type = ARG_NUM;
                fn.instrs[i].arg.n = v.as.b ? 1.0 : 0.0;
            } else {
                fn.instrs[i].arg.type = ARG_NONE;
            }
        } else {
            fn.instrs[i].arg = parse_arg(js, toks, arg_i);
        }

        ii = tok_skip(toks, ii);
    }

    return fn;
}

static Program parse_program(const char *js, const char *origin_path) {
    Program p;
    memset(&p, 0, sizeof(p));

    size_t cap = 65536;
    jsmntok_t *toks = (jsmntok_t *)calloc(cap, sizeof(jsmntok_t));
    if (!toks) fatal("sem memória");

    jsmn_parser parser;
    jsmn_init(&parser);
    int n = jsmn_parse(&parser, js, strlen(js), toks, (unsigned int)cap);
    if (n < 0) fatal("JSON inválido em .tbc");
    g_tok_count = n;
    if (n == 0 || toks[0].type != JSMN_OBJECT) fatal("raiz .tbc inválida");

    int entry_i = obj_get(js, toks, 0, "entry");
    int fns_i = obj_get(js, toks, 0, "functions");
    if (entry_i < 0 || fns_i < 0) fatal(".tbc sem entry/functions");

    p.entry = (Function *)calloc(1, sizeof(Function));
    *p.entry = parse_function(js, toks, entry_i, "__entry__");
    p.origin_path = origin_path ? strdup(origin_path) : NULL;

    if (toks[fns_i].type != JSMN_OBJECT) fatal("functions inválido");
    p.fn_len = (size_t)toks[fns_i].size;
    p.functions = (Function *)calloc(p.fn_len ? p.fn_len : 1, sizeof(Function));

    size_t idx = 0;
    int fns_end = toks[fns_i].end;
    for (int i = fns_i + 1; i < g_tok_count && toks[i].start < fns_end; i++) {
        if (toks[i].parent == fns_i && toks[i].type == JSMN_STRING) {
            int key_i = i;
            int val_i = i + 1;
            char *code_name = token_strdup(js, &toks[key_i]);
            p.functions[idx++] = parse_function(js, toks, val_i, code_name);
            free(code_name);
        }
    }
    p.fn_len = idx;

    free(toks);
    return p;
}

static Function *program_find_function(Program *p, const char *code_name) {
    for (size_t i = 0; i < p->fn_len; i++) {
        if (strcmp(p->functions[i].code_name, code_name) == 0) return &p->functions[i];
    }
    return NULL;
}

static bool is_truthy(Value v) {
    switch (v.type) {
        case VAL_NULL: return false;
        case VAL_BOOL: return v.as.b;
        case VAL_NUM: return fabs(v.as.n) > 1e-12;
        case VAL_STR: return v.as.s && v.as.s[0] != '\0';
        case VAL_LIST: return v.as.list && v.as.list->len > 0;
        case VAL_MAP: return v.as.map && v.as.map->len > 0;
        default: return true;
    }
}

static void value_print(Value v) {
    switch (v.type) {
        case VAL_NULL: printf("nulo"); break;
        case VAL_BOOL: printf(v.as.b ? "True" : "False"); break;
        case VAL_NUM: {
            double frac = fabs(v.as.n - floor(v.as.n));
            if (frac < 1e-12) printf("%.0f", v.as.n);
            else printf("%.15g", v.as.n);
            break;
        }
        case VAL_STR: printf("%s", v.as.s ? v.as.s : ""); break;
        case VAL_LIST: printf("[lista:%zu]", v.as.list ? v.as.list->len : 0); break;
        case VAL_MAP: printf("{mapa:%zu}", v.as.map ? v.as.map->len : 0); break;
        case VAL_FUNC: printf("<func %s>", v.as.fn ? v.as.fn->name : "?"); break;
        case VAL_AWAITABLE: printf("<aguardavel>"); break;
        case VAL_BUILTIN_EXIBIR: printf("<builtin exibir>"); break;
        case VAL_BUILTIN_CRIAR_TAREFA: printf("<builtin criar_tarefa>"); break;
        case VAL_BUILTIN_COM_TIMEOUT: printf("<builtin com_timeout>"); break;
        case VAL_BUILTIN_CANCELAR_TAREFA: printf("<builtin cancelar_tarefa>"); break;
        case VAL_BUILTIN_DORMIR: printf("<builtin dormir>"); break;
        case VAL_TASK: printf("<tarefa>"); break;
    }
}

static Value frame_pop(Frame *f) {
    if (f->stack_len == 0) fatal("pilha vazia");
    return f->stack[--f->stack_len];
}

static void frame_push(Frame *f, Value v) {
    if (f->stack_len == f->stack_cap) {
        f->stack_cap = f->stack_cap == 0 ? 32 : f->stack_cap * 2;
        f->stack = (Value *)realloc(f->stack, f->stack_cap * sizeof(Value));
        if (!f->stack) fatal("sem memória");
    }
    f->stack[f->stack_len++] = v;
}

static Value instr_load_const(Instr *in) {
    if (in->arg.type == ARG_NONE) return value_null();
    if (in->arg.type == ARG_NUM) return value_num(in->arg.n);
    if (in->arg.type == ARG_STR) return value_str(strdup(in->arg.s));
    return value_null();
}

static char *read_file(const char *path);

static void frame_push_handler(Frame *f, TryHandler h) {
    if (f->handlers_len == f->handlers_cap) {
        f->handlers_cap = f->handlers_cap == 0 ? 8 : f->handlers_cap * 2;
        f->handlers = (TryHandler *)realloc(f->handlers, f->handlers_cap * sizeof(TryHandler));
        if (!f->handlers) fatal("sem memória");
    }
    f->handlers[f->handlers_len++] = h;
}

static bool frame_handle_throw(Frame *f, Value exc) {
    while (f->handlers_len > 0) {
        TryHandler *h = &f->handlers[f->handlers_len - 1];
        if (h->phase == 2) {
            f->handlers_len--;
            continue;
        }
        if (h->phase == 0) {
            if (h->catch_ip >= 0) {
                h->phase = 1;
                if (h->catch_name && h->catch_name[0] != '\0') {
                    env_set_local(f->env, h->catch_name, exc);
                }
                f->ip = (size_t)h->catch_ip;
                return true;
            }
            if (h->finally_ip >= 0) {
                h->phase = 2;
                h->has_pending = true;
                h->pending = exc;
                f->ip = (size_t)h->finally_ip;
                return true;
            }
            f->handlers_len--;
            continue;
        }
        if (h->phase == 1) {
            if (h->finally_ip >= 0) {
                h->phase = 2;
                h->has_pending = true;
                h->pending = exc;
                f->ip = (size_t)h->finally_ip;
                return true;
            }
            f->handlers_len--;
            continue;
        }
        f->handlers_len--;
    }
    return false;
}

static void frame_end_try_block(Frame *f) {
    if (f->handlers_len == 0) fatal("END_TRY_BLOCK sem handler ativo");
    TryHandler *h = &f->handlers[f->handlers_len - 1];
    if (h->phase != 0) fatal("END_TRY_BLOCK fora da fase try");
    if (h->finally_ip >= 0) {
        h->phase = 2;
        f->ip = (size_t)h->finally_ip;
    } else {
        f->handlers_len--;
    }
}

static void frame_end_catch_block(Frame *f) {
    if (f->handlers_len == 0) fatal("END_CATCH_BLOCK sem handler ativo");
    TryHandler *h = &f->handlers[f->handlers_len - 1];
    if (h->phase != 1) fatal("END_CATCH_BLOCK fora da fase catch");
    if (h->finally_ip >= 0) {
        h->phase = 2;
        f->ip = (size_t)h->finally_ip;
    } else {
        f->handlers_len--;
    }
}

static bool frame_end_finally(Frame *f, Value *pending) {
    if (f->handlers_len == 0) fatal("END_FINALLY sem handler ativo");
    TryHandler h = f->handlers[f->handlers_len - 1];
    f->handlers_len--;
    if (h.has_pending) {
        *pending = h.pending;
        return true;
    }
    return false;
}

static char *path_dirname_dup(const char *path) {
    const char *slash = strrchr(path, '/');
    if (!slash) return strdup(".");
    size_t n = (size_t)(slash - path);
    if (n == 0) n = 1;
    return xstrndup(path, n);
}

static char *join_path(const char *a, const char *b) {
    size_t na = strlen(a);
    size_t nb = strlen(b);
    bool sep = na > 0 && a[na - 1] != '/';
    char *out = (char *)malloc(na + nb + (sep ? 2 : 1));
    if (!out) fatal("sem memória");
    memcpy(out, a, na);
    if (sep) out[na++] = '/';
    memcpy(out + na, b, nb);
    out[na + nb] = '\0';
    return out;
}

static ExecResult run_function(Program *p, Function *start, Value *args, size_t argc, Env *closure);

static bool file_exists(const char *path) {
    struct stat st;
    return stat(path, &st) == 0 && S_ISREG(st.st_mode);
}

typedef struct {
    Task *task;
} TaskRunCtx;

static void *task_thread_main(void *arg) {
    TaskRunCtx *ctx = (TaskRunCtx *)arg;
    Task *t = ctx->task;
    free(ctx);
    pthread_mutex_lock(&t->mu);
    bool canceled = t->canceled;
    pthread_mutex_unlock(&t->mu);
    if (canceled) {
        pthread_mutex_lock(&t->mu);
        t->done = true;
        t->threw = true;
        t->value = value_str(strdup("tarefa_cancelada"));
        pthread_cond_broadcast(&t->cv);
        pthread_mutex_unlock(&t->mu);
        return NULL;
    }
    Program *program = (Program *)t->program;
    Awaitable *a = t->awaitable;
    ExecResult r;
    if (a->kind == AWAITABLE_DORMIR) {
        if (a->segundos > 0) {
            struct timespec ts;
            ts.tv_sec = (time_t)a->segundos;
            ts.tv_nsec = (long)((a->segundos - floor(a->segundos)) * 1000000000.0);
            nanosleep(&ts, NULL);
        }
        r.threw = false;
        r.value = value_null();
    } else {
        r = run_function(program, a->fn, a->args, a->argc, a->closure);
    }
    pthread_mutex_lock(&t->mu);
    t->done = true;
    t->threw = r.threw;
    t->value = r.value;
    pthread_cond_broadcast(&t->cv);
    pthread_mutex_unlock(&t->mu);
    return NULL;
}

static Task *task_new(Program *p, Awaitable *a) {
    Task *t = (Task *)calloc(1, sizeof(Task));
    if (!t) fatal("sem memória");
    t->program = (void *)p;
    t->awaitable = a;
    pthread_mutex_init(&t->mu, NULL);
    pthread_cond_init(&t->cv, NULL);
    t->done = false;
    t->canceled = false;
    t->threw = false;
    t->value = value_null();
    TaskRunCtx *ctx = (TaskRunCtx *)calloc(1, sizeof(TaskRunCtx));
    if (!ctx) fatal("sem memória");
    ctx->task = t;
    if (pthread_create(&t->th, NULL, task_thread_main, ctx) != 0) {
        fatal("falha ao criar thread de tarefa");
    }
    return t;
}

static Value module_to_exports(Env *globals) {
    Map *m = map_new();
    for (size_t i = 0; i < globals->len; i++) {
        if (strcmp(globals->items[i].name, "exibir") == 0) continue;
        if (strcmp(globals->items[i].name, "criar_tarefa") == 0) continue;
        if (strcmp(globals->items[i].name, "com_timeout") == 0) continue;
        if (strcmp(globals->items[i].name, "cancelar_tarefa") == 0) continue;
        if (strcmp(globals->items[i].name, "dormir") == 0) continue;
        if (strcmp(globals->items[i].name, "create_task") == 0) continue;
        if (strcmp(globals->items[i].name, "with_timeout") == 0) continue;
        if (strcmp(globals->items[i].name, "cancel_task") == 0) continue;
        if (strcmp(globals->items[i].name, "sleep") == 0) continue;
        map_set(m, value_str(strdup(globals->items[i].name)), globals->items[i].value);
    }
    Value out;
    out.type = VAL_MAP;
    out.as.map = m;
    return out;
}

static int compilar_trm_nativo_para_tbc(const char *arquivo_fonte, const char *arquivo_saida);

static ExecResult import_module(Program *current_program, Value module_ref) {
    if (module_ref.type != VAL_STR) {
        fatal("IMPORT_NAME exige string");
    }
    const char *ref = module_ref.as.s;
    bool ref_tem_tbc = strstr(ref, ".tbc") != NULL;
    bool ref_tem_trm = strstr(ref, ".trm") != NULL;
    char *candidate_tbc = NULL;
    char *candidate_trm = NULL;
    if (ref_tem_tbc) {
        candidate_tbc = strdup(ref);
    } else if (ref_tem_trm) {
        size_t n = strlen(ref);
        candidate_trm = strdup(ref);
        if (n >= 4) n -= 4;
        candidate_tbc = (char *)malloc(n + 5);
        if (!candidate_tbc) fatal("sem memória");
        memcpy(candidate_tbc, ref, n);
        memcpy(candidate_tbc + n, ".tbc", 5);
    } else {
        size_t n = strlen(ref);
        candidate_tbc = (char *)malloc(n + 5);
        candidate_trm = (char *)malloc(n + 5);
        if (!candidate_tbc || !candidate_trm) fatal("sem memória");
        memcpy(candidate_tbc, ref, n);
        memcpy(candidate_tbc + n, ".tbc", 5);
        memcpy(candidate_trm, ref, n);
        memcpy(candidate_trm + n, ".trm", 5);
    }

    char *full_tbc = NULL;
    char *full_trm = NULL;
    if (candidate_tbc[0] == '/') full_tbc = strdup(candidate_tbc);
    else {
        char *base = current_program->origin_path ? path_dirname_dup(current_program->origin_path) : strdup(".");
        full_tbc = join_path(base, candidate_tbc);
        free(base);
    }
    if (candidate_trm != NULL) {
        if (candidate_trm[0] == '/') full_trm = strdup(candidate_trm);
        else {
            char *base = current_program->origin_path ? path_dirname_dup(current_program->origin_path) : strdup(".");
            full_trm = join_path(base, candidate_trm);
            free(base);
        }
    }

    if (!file_exists(full_tbc) && full_trm != NULL && file_exists(full_trm)) {
        if (compilar_trm_nativo_para_tbc(full_trm, full_tbc) != 0) {
            ExecResult err;
            err.threw = true;
            err.value = value_str(strdup("falha_import_trm_compilacao_nativa"));
            free(candidate_tbc);
            if (candidate_trm) free(candidate_trm);
            free(full_tbc);
            if (full_trm) free(full_trm);
            return err;
        }
    }

    Value cached_module;
    if (module_cache_get(full_tbc, &cached_module)) {
        ExecResult hit;
        hit.threw = false;
        hit.value = cached_module;
        free(candidate_tbc);
        if (candidate_trm) free(candidate_trm);
        free(full_tbc);
        if (full_trm) free(full_trm);
        return hit;
    }

    char *full = full_tbc;

    char *json = read_file(full);
    Program mod = parse_program(json, full);
    Env *globals = env_new(NULL);
    env_set_local(globals, "exibir", value_builtin_exibir());
    env_set_local(globals, "criar_tarefa", value_builtin_criar_tarefa());
    env_set_local(globals, "com_timeout", value_builtin_com_timeout());
    env_set_local(globals, "cancelar_tarefa", value_builtin_cancelar_tarefa());
    env_set_local(globals, "dormir", value_builtin_dormir());
    env_set_local(globals, "create_task", value_builtin_criar_tarefa());
    env_set_local(globals, "with_timeout", value_builtin_com_timeout());
    env_set_local(globals, "cancel_task", value_builtin_cancelar_tarefa());
    env_set_local(globals, "sleep", value_builtin_dormir());
    mod.entry->closure = globals;
    ExecResult entry = run_function(&mod, mod.entry, NULL, 0, globals);
    if (entry.threw) {
        free(json);
        free(candidate_tbc);
        if (candidate_trm) free(candidate_trm);
        free(full_tbc);
        if (full_trm) free(full_trm);
        return entry;
    }
    ExecResult ok;
    ok.threw = false;
    ok.value = module_to_exports(globals);
    module_cache_put(full_tbc, ok.value);
    free(json);
    free(candidate_tbc);
    if (candidate_trm) free(candidate_trm);
    free(full_tbc);
    if (full_trm) free(full_trm);
    return ok;
}

static ExecResult call_value(Program *p, Value callee, Value *args, size_t argc) {
    ExecResult out;
    out.threw = false;
    out.value = value_null();
    if (callee.type == VAL_BUILTIN_EXIBIR) {
        for (size_t i = 0; i < argc; i++) {
            if (i > 0) printf(" ");
            value_print(args[i]);
        }
        printf("\n");
        return out;
    }
    if (callee.type == VAL_BUILTIN_DORMIR) {
        double seg = 0.0;
        if (argc >= 1 && args[0].type == VAL_NUM) seg = args[0].as.n;
        out.value = value_awaitable(awaitable_dormir_new(seg));
        return out;
    }
    if (callee.type == VAL_BUILTIN_CRIAR_TAREFA) {
        if (argc < 1) fatal("criar_tarefa exige 1 argumento");
        Awaitable *a = NULL;
        if (args[0].type == VAL_AWAITABLE) {
            a = args[0].as.awaitable;
        } else if (args[0].type == VAL_FUNC && args[0].as.fn->is_async) {
            a = awaitable_new(args[0].as.fn, NULL, 0, args[0].as.fn->closure);
        } else {
            fatal("criar_tarefa exige valor aguardavel");
        }
        Task *t = task_new(p, a);
        out.value = value_task(t);
        return out;
    }
    if (callee.type == VAL_BUILTIN_CANCELAR_TAREFA) {
        if (argc < 1 || args[0].type != VAL_TASK) fatal("cancelar_tarefa exige tarefa");
        Task *t = args[0].as.task;
        pthread_mutex_lock(&t->mu);
        t->canceled = true;
        pthread_mutex_unlock(&t->mu);
        out.value = value_bool(true);
        return out;
    }
    if (callee.type == VAL_BUILTIN_COM_TIMEOUT) {
        if (argc < 1) fatal("com_timeout exige ao menos 1 argumento");
        if (args[0].type == VAL_TASK) {
            double timeout = (argc >= 2 && args[1].type == VAL_NUM) ? args[1].as.n : 0.001;
            out.value = value_awaitable(awaitable_task_timeout_new(args[0].as.task, timeout));
            return out;
        }
        out.value = args[0];
        return out;
    }
    if (callee.type == VAL_FUNC) {
        Function *fn = callee.as.fn;
        if (fn->is_async) {
            Awaitable *a = awaitable_new(fn, args, argc, fn->closure);
            out.value = value_awaitable(a);
            return out;
        }
        return run_function(p, fn, args, argc, fn->closure);
    }
    fatal("valor não chamável");
    return out;
}

static ExecResult await_value(Program *p, Value v) {
    ExecResult ar;
    ar.threw = false;
    ar.value = value_null();
    if (v.type == VAL_AWAITABLE) {
        Awaitable *a = v.as.awaitable;
        if (a->kind == AWAITABLE_DORMIR) {
            if (a->segundos > 0) {
                struct timespec ts;
                ts.tv_sec = (time_t)a->segundos;
                ts.tv_nsec = (long)((a->segundos - floor(a->segundos)) * 1000000000.0);
                nanosleep(&ts, NULL);
            }
            return ar;
        }
        if (a->kind == AWAITABLE_TASK_TIMEOUT) {
            Task *t = a->task;
            struct timespec ts;
            clock_gettime(CLOCK_REALTIME, &ts);
            double total = a->segundos > 0 ? a->segundos : 0.001;
            ts.tv_sec += (time_t)total;
            ts.tv_nsec += (long)((total - floor(total)) * 1000000000.0);
            if (ts.tv_nsec >= 1000000000L) {
                ts.tv_sec += 1;
                ts.tv_nsec -= 1000000000L;
            }
            pthread_mutex_lock(&t->mu);
            while (!t->done) {
                int rc = pthread_cond_timedwait(&t->cv, &t->mu, &ts);
                if (rc != 0) break;
            }
            if (!t->done) {
                pthread_mutex_unlock(&t->mu);
                ar.threw = true;
                ar.value = value_str(strdup("timeout"));
                return ar;
            }
            ar.threw = t->threw;
            ar.value = t->value;
            pthread_mutex_unlock(&t->mu);
            return ar;
        }
        return run_function(p, a->fn, a->args, a->argc, a->closure);
    }
    if (v.type == VAL_TASK) {
        Task *t = v.as.task;
        pthread_mutex_lock(&t->mu);
        while (!t->done) pthread_cond_wait(&t->cv, &t->mu);
        ar.threw = t->threw;
        ar.value = t->value;
        pthread_mutex_unlock(&t->mu);
        return ar;
    }
    ar.threw = true;
    ar.value = value_str(strdup("valor_nao_aguardavel"));
    return ar;
}

static ExecResult run_function(Program *p, Function *start, Value *args, size_t argc, Env *closure) {
    ExecResult out;
    out.threw = false;
    out.value = value_null();
    if (argc != start->params_len) {
        fatal("aridade inválida");
    }

    Env *env = NULL;
    bool is_entry = (strcmp(start->name, "__entry__") == 0);
    if (is_entry && closure != NULL) {
        env = closure;
    } else {
        env = env_new(closure);
        for (size_t i = 0; i < start->params_len; i++) {
            env_set_local(env, start->params[i], args[i]);
        }
    }

    Frame cur;
    memset(&cur, 0, sizeof(cur));
    cur.fn = start;
    cur.ip = 0;
    cur.env = env;

    while (1) {
        if (cur.ip >= cur.fn->instr_len) {
            out.value = value_null();
            return out;
        }

        Instr *in = &cur.fn->instrs[cur.ip++];

        if (strcmp(in->op, "LOAD_CONST") == 0) {
            frame_push(&cur, instr_load_const(in));
        } else if (strcmp(in->op, "LOAD_NAME") == 0) {
            Value v;
            if (!env_get(cur.env, in->arg.s, &v)) fatal("nome não definido");
            frame_push(&cur, v);
        } else if (strcmp(in->op, "STORE_NAME") == 0) {
            Value v = frame_pop(&cur);
            env_set(cur.env, in->arg.s, v);
        } else if (strcmp(in->op, "POP_TOP") == 0) {
            (void)frame_pop(&cur);
        } else if (strcmp(in->op, "NEGATE") == 0) {
            Value v = frame_pop(&cur);
            if (v.type != VAL_NUM) fatal("NEGATE espera número");
            frame_push(&cur, value_num(-v.as.n));
        } else if (strcmp(in->op, "BINARY_ADD") == 0 || strcmp(in->op, "BINARY_SUB") == 0 || strcmp(in->op, "BINARY_MUL") == 0 || strcmp(in->op, "BINARY_DIV") == 0) {
            Value b = frame_pop(&cur), a = frame_pop(&cur);
            if (a.type == VAL_NUM && b.type == VAL_NUM) {
                if (strcmp(in->op, "BINARY_ADD") == 0) frame_push(&cur, value_num(a.as.n + b.as.n));
                else if (strcmp(in->op, "BINARY_SUB") == 0) frame_push(&cur, value_num(a.as.n - b.as.n));
                else if (strcmp(in->op, "BINARY_MUL") == 0) frame_push(&cur, value_num(a.as.n * b.as.n));
                else frame_push(&cur, value_num(a.as.n / b.as.n));
            } else if (strcmp(in->op, "BINARY_ADD") == 0 && a.type == VAL_STR && b.type == VAL_STR) {
                size_t na = strlen(a.as.s), nb = strlen(b.as.s);
                char *s = (char *)malloc(na + nb + 1);
                memcpy(s, a.as.s, na);
                memcpy(s + na, b.as.s, nb);
                s[na + nb] = '\0';
                frame_push(&cur, value_str(s));
            } else {
                fatal("operação binária inválida");
            }
        } else if (strcmp(in->op, "COMPARE_OP") == 0) {
            Value b = frame_pop(&cur), a = frame_pop(&cur);
            bool ok = false;
            if (a.type == VAL_NUM && b.type == VAL_NUM) {
                if (strcmp(in->arg.s, "IGUAL_IGUAL") == 0) ok = (a.as.n == b.as.n);
                else if (strcmp(in->arg.s, "DIFERENTE") == 0) ok = (a.as.n != b.as.n);
                else if (strcmp(in->arg.s, "MAIOR") == 0) ok = (a.as.n > b.as.n);
                else if (strcmp(in->arg.s, "MAIOR_IGUAL") == 0) ok = (a.as.n >= b.as.n);
                else if (strcmp(in->arg.s, "MENOR") == 0) ok = (a.as.n < b.as.n);
                else if (strcmp(in->arg.s, "MENOR_IGUAL") == 0) ok = (a.as.n <= b.as.n);
            } else if (a.type == VAL_STR && b.type == VAL_STR) {
                int c = strcmp(a.as.s, b.as.s);
                if (strcmp(in->arg.s, "IGUAL_IGUAL") == 0) ok = (c == 0);
                else if (strcmp(in->arg.s, "DIFERENTE") == 0) ok = (c != 0);
                else if (strcmp(in->arg.s, "MAIOR") == 0) ok = (c > 0);
                else if (strcmp(in->arg.s, "MAIOR_IGUAL") == 0) ok = (c >= 0);
                else if (strcmp(in->arg.s, "MENOR") == 0) ok = (c < 0);
                else if (strcmp(in->arg.s, "MENOR_IGUAL") == 0) ok = (c <= 0);
            } else {
                if (strcmp(in->arg.s, "IGUAL_IGUAL") == 0) ok = (a.type == b.type);
                else if (strcmp(in->arg.s, "DIFERENTE") == 0) ok = (a.type != b.type);
            }
            frame_push(&cur, value_bool(ok));
        } else if (strcmp(in->op, "BUILD_LIST") == 0) {
            int n = (int)in->arg.n;
            if (n < 0 || (size_t)n > cur.stack_len) fatal("BUILD_LIST inválido");
            List *l = list_new();
            Value *tmp = (Value *)calloc((size_t)n, sizeof(Value));
            for (int i = n - 1; i >= 0; i--) tmp[i] = frame_pop(&cur);
            for (int i = 0; i < n; i++) list_push(l, tmp[i]);
            free(tmp);
            Value v; v.type = VAL_LIST; v.as.list = l;
            frame_push(&cur, v);
        } else if (strcmp(in->op, "BUILD_MAP") == 0) {
            int n = (int)in->arg.n;
            if (n < 0 || (size_t)(n * 2) > cur.stack_len) fatal("BUILD_MAP inválido");
            Map *m = map_new();
            Value *tmp = (Value *)calloc((size_t)(n * 2), sizeof(Value));
            for (int i = n * 2 - 1; i >= 0; i--) tmp[i] = frame_pop(&cur);
            for (int i = 0; i < n * 2; i += 2) map_set(m, tmp[i], tmp[i + 1]);
            free(tmp);
            Value v; v.type = VAL_MAP; v.as.map = m;
            frame_push(&cur, v);
        } else if (strcmp(in->op, "BINARY_SUBSCR") == 0) {
            Value idx = frame_pop(&cur);
            Value obj = frame_pop(&cur);
            if (obj.type == VAL_LIST && idx.type == VAL_NUM) {
                int i = (int)idx.as.n;
                if (i < 0 || (size_t)i >= obj.as.list->len) fatal("índice fora da lista");
                frame_push(&cur, obj.as.list->items[i]);
            } else if (obj.type == VAL_MAP) {
                Value out;
                if (!map_get(obj.as.map, idx, &out)) fatal("chave inexistente");
                frame_push(&cur, out);
            } else {
                fatal("BINARY_SUBSCR inválido");
            }
        } else if (strcmp(in->op, "JUMP") == 0) {
            cur.ip = (size_t)in->arg.n;
        } else if (strcmp(in->op, "JUMP_IF_FALSE") == 0) {
            Value cond = frame_pop(&cur);
            if (!is_truthy(cond)) cur.ip = (size_t)in->arg.n;
        } else if (strcmp(in->op, "MAKE_FUNCTION") == 0) {
            Function *f = program_find_function(p, in->arg.make_fn.code);
            if (!f) fatal("MAKE_FUNCTION com code_name desconhecido");
            f->closure = cur.env;
            frame_push(&cur, value_func(f));
        } else if (strcmp(in->op, "CALL") == 0) {
            int argc2 = (int)in->arg.n;
            if (argc2 < 0 || (size_t)(argc2 + 1) > cur.stack_len) fatal("CALL inválido");
            Value *argv2 = (Value *)calloc((size_t)argc2, sizeof(Value));
            for (int i = argc2 - 1; i >= 0; i--) argv2[i] = frame_pop(&cur);
            Value callee = frame_pop(&cur);
            ExecResult cr = call_value(p, callee, argv2, (size_t)argc2);
            free(argv2);
            if (cr.threw) {
                if (!frame_handle_throw(&cur, cr.value)) return cr;
                continue;
            }
            frame_push(&cur, cr.value);
        } else if (strcmp(in->op, "AWAIT") == 0) {
            Value v = frame_pop(&cur);
            ExecResult ar = await_value(p, v);
            if (ar.threw && ar.value.type == VAL_STR && strcmp(ar.value.as.s, "valor_nao_aguardavel") == 0) {
                fatal("valor não aguardável em AWAIT");
            }
            if (ar.threw) {
                if (!frame_handle_throw(&cur, ar.value)) return ar;
                continue;
            }
            frame_push(&cur, ar.value);
        } else if (strcmp(in->op, "IMPORT_NAME") == 0) {
            ExecResult ir = import_module(p, value_str(in->arg.s));
            if (ir.threw) {
                if (!frame_handle_throw(&cur, ir.value)) return ir;
                continue;
            }
            frame_push(&cur, ir.value);
        } else if (strcmp(in->op, "THROW") == 0) {
            Value exc = cur.stack_len ? frame_pop(&cur) : value_null();
            if (!frame_handle_throw(&cur, exc)) {
                out.threw = true;
                out.value = exc;
                return out;
            }
            continue;
        } else if (strcmp(in->op, "PUSH_TRY") == 0) {
            if (in->arg.type != ARG_TRY) fatal("PUSH_TRY inválido no runtime nativo");
            TryHandler h;
            h.catch_ip = in->arg.try_arg.catch_ip;
            h.finally_ip = in->arg.try_arg.finally_ip;
            h.catch_name = in->arg.try_arg.catch_name ? in->arg.try_arg.catch_name : strdup("");
            h.phase = 0;
            h.has_pending = false;
            h.pending = value_null();
            frame_push_handler(&cur, h);
        } else if (strcmp(in->op, "END_TRY_BLOCK") == 0) {
            frame_end_try_block(&cur);
        } else if (strcmp(in->op, "END_CATCH_BLOCK") == 0) {
            frame_end_catch_block(&cur);
        } else if (strcmp(in->op, "BEGIN_FINALLY") == 0) {
            if (cur.handlers_len == 0) fatal("BEGIN_FINALLY sem handler ativo");
            cur.handlers[cur.handlers_len - 1].phase = 2;
        } else if (strcmp(in->op, "END_FINALLY") == 0) {
            Value pending = value_null();
            if (frame_end_finally(&cur, &pending)) {
                if (!frame_handle_throw(&cur, pending)) {
                    out.threw = true;
                    out.value = pending;
                    return out;
                }
            }
        } else if (strcmp(in->op, "RETURN_VALUE") == 0) {
            out.value = cur.stack_len ? frame_pop(&cur) : value_null();
            return out;
        } else if (strcmp(in->op, "HALT") == 0) {
            out.value = value_null();
            return out;
        } else {
            fprintf(stderr, "Erro nativo: opcode não suportado no v2.0-base: %s\n", in->op);
            exit(1);
        }
    }
}

static char *read_file(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        perror("fopen");
        exit(1);
    }
    if (fseek(f, 0, SEEK_END) != 0) fatal("fseek falhou");
    long n = ftell(f);
    if (n < 0) fatal("ftell falhou");
    rewind(f);
    char *buf = (char *)malloc((size_t)n + 1);
    if (!buf) fatal("sem memória");
    size_t rd = fread(buf, 1, (size_t)n, f);
    fclose(f);
    buf[rd] = '\0';
    return buf;
}

typedef struct {
    Instr *items;
    size_t len;
    size_t cap;
} InstrBuf;

typedef struct {
    char *name;
    bool is_async;
    char **params;
    size_t params_len;
    InstrBuf code;
    char *code_name;
} FuncBuilder;

static void ib_push(InstrBuf *b, Instr in) {
    if (b->len == b->cap) {
        b->cap = b->cap == 0 ? 16 : b->cap * 2;
        b->items = (Instr *)realloc(b->items, b->cap * sizeof(Instr));
        if (!b->items) fatal("sem memória");
    }
    b->items[b->len++] = in;
}

static Instr mk_instr_none(const char *op) {
    Instr in;
    memset(&in, 0, sizeof(in));
    in.op = strdup(op);
    in.arg.type = ARG_NONE;
    return in;
}

static Instr mk_instr_num(const char *op, double n) {
    Instr in = mk_instr_none(op);
    in.arg.type = ARG_NUM;
    in.arg.n = n;
    return in;
}

static Instr mk_instr_str(const char *op, const char *s) {
    Instr in = mk_instr_none(op);
    in.arg.type = ARG_STR;
    in.arg.s = strdup(s ? s : "");
    return in;
}

static Instr mk_instr_make_function(const char *display, const char *code, bool is_async) {
    Instr in = mk_instr_none("MAKE_FUNCTION");
    in.arg.type = ARG_MAKE_FN;
    in.arg.make_fn.display = strdup(display ? display : "");
    in.arg.make_fn.code = strdup(code ? code : "");
    in.arg.make_fn.is_async = is_async;
    return in;
}

typedef enum {
    TK_EOF = 0,
    TK_NUM,
    TK_STR,
    TK_IDENT,
    TK_PLUS,
    TK_MINUS,
    TK_STAR,
    TK_SLASH,
    TK_LP,
    TK_RP,
    TK_LB,
    TK_RB,
    TK_COMMA
} TokKind;

typedef struct {
    TokKind kind;
    char text[256];
    double num;
} Tok;

typedef struct {
    const char *s;
    size_t len;
    size_t pos;
    Tok cur;
} ExprLex;

static void lex_next(ExprLex *lx) {
    while (lx->pos < lx->len && isspace((unsigned char)lx->s[lx->pos])) lx->pos++;
    if (lx->pos >= lx->len) {
        lx->cur.kind = TK_EOF;
        lx->cur.text[0] = '\0';
        lx->cur.num = 0;
        return;
    }
    char c = lx->s[lx->pos];
    if (isdigit((unsigned char)c)) {
        size_t start = lx->pos;
        while (lx->pos < lx->len && (isdigit((unsigned char)lx->s[lx->pos]) || lx->s[lx->pos] == '.')) lx->pos++;
        size_t n = lx->pos - start;
        if (n >= sizeof(lx->cur.text)) n = sizeof(lx->cur.text) - 1;
        memcpy(lx->cur.text, lx->s + start, n);
        lx->cur.text[n] = '\0';
        lx->cur.kind = TK_NUM;
        lx->cur.num = strtod(lx->cur.text, NULL);
        return;
    }
    if (c == '"') {
        lx->pos++;
        size_t start = lx->pos;
        while (lx->pos < lx->len && lx->s[lx->pos] != '"') {
            if (lx->s[lx->pos] == '\\' && lx->pos + 1 < lx->len) lx->pos += 2;
            else lx->pos++;
        }
        size_t n = lx->pos - start;
        if (n >= sizeof(lx->cur.text)) n = sizeof(lx->cur.text) - 1;
        memcpy(lx->cur.text, lx->s + start, n);
        lx->cur.text[n] = '\0';
        lx->cur.kind = TK_STR;
        if (lx->pos < lx->len && lx->s[lx->pos] == '"') lx->pos++;
        return;
    }
    if (isalpha((unsigned char)c) || c == '_' || (unsigned char)c >= 128) {
        size_t start = lx->pos;
        while (lx->pos < lx->len) {
            unsigned char ch = (unsigned char)lx->s[lx->pos];
            if (isalnum(ch) || ch == '_' || ch >= 128) lx->pos++;
            else break;
        }
        size_t n = lx->pos - start;
        if (n >= sizeof(lx->cur.text)) n = sizeof(lx->cur.text) - 1;
        memcpy(lx->cur.text, lx->s + start, n);
        lx->cur.text[n] = '\0';
        lx->cur.kind = TK_IDENT;
        return;
    }
    lx->pos++;
    lx->cur.text[0] = c;
    lx->cur.text[1] = '\0';
    lx->cur.num = 0;
    switch (c) {
        case '+': lx->cur.kind = TK_PLUS; break;
        case '-': lx->cur.kind = TK_MINUS; break;
        case '*': lx->cur.kind = TK_STAR; break;
        case '/': lx->cur.kind = TK_SLASH; break;
        case '(': lx->cur.kind = TK_LP; break;
        case ')': lx->cur.kind = TK_RP; break;
        case '[': lx->cur.kind = TK_LB; break;
        case ']': lx->cur.kind = TK_RB; break;
        case ',': lx->cur.kind = TK_COMMA; break;
        default: lx->cur.kind = TK_EOF; break;
    }
}

static void comp_expr(ExprLex *lx, InstrBuf *buf);

static void comp_primary(ExprLex *lx, InstrBuf *buf) {
    if (lx->cur.kind == TK_NUM) {
        ib_push(buf, mk_instr_num("LOAD_CONST", lx->cur.num));
        lex_next(lx);
        return;
    }
    if (lx->cur.kind == TK_STR) {
        ib_push(buf, mk_instr_str("LOAD_CONST", lx->cur.text));
        lex_next(lx);
        return;
    }
    if (lx->cur.kind == TK_IDENT) {
        if (strcmp(lx->cur.text, "verdadeiro") == 0) {
            ib_push(buf, mk_instr_num("LOAD_CONST", 1.0));
            lex_next(lx);
            return;
        }
        if (strcmp(lx->cur.text, "falso") == 0) {
            ib_push(buf, mk_instr_num("LOAD_CONST", 0.0));
            lex_next(lx);
            return;
        }
        if (strcmp(lx->cur.text, "nulo") == 0) {
            ib_push(buf, mk_instr_none("LOAD_CONST"));
            lex_next(lx);
            return;
        }
        ib_push(buf, mk_instr_str("LOAD_NAME", lx->cur.text));
        lex_next(lx);
        return;
    }
    if (lx->cur.kind == TK_LP) {
        lex_next(lx);
        comp_expr(lx, buf);
        if (lx->cur.kind != TK_RP) fatal("expressao: ')' esperado");
        lex_next(lx);
        return;
    }
    fatal("expressao primaria invalida");
}

static void comp_postfix(ExprLex *lx, InstrBuf *buf) {
    comp_primary(lx, buf);
    while (1) {
        if (lx->cur.kind == TK_LP) {
            lex_next(lx);
            int argc = 0;
            if (lx->cur.kind != TK_RP) {
                while (1) {
                    comp_expr(lx, buf);
                    argc++;
                    if (lx->cur.kind == TK_COMMA) {
                        lex_next(lx);
                        continue;
                    }
                    break;
                }
            }
            if (lx->cur.kind != TK_RP) fatal("chamada: ')' esperado");
            lex_next(lx);
            ib_push(buf, mk_instr_num("CALL", (double)argc));
            continue;
        }
        if (lx->cur.kind == TK_LB) {
            lex_next(lx);
            comp_expr(lx, buf);
            if (lx->cur.kind != TK_RB) fatal("indexacao: ']' esperado");
            lex_next(lx);
            ib_push(buf, mk_instr_none("BINARY_SUBSCR"));
            continue;
        }
        break;
    }
}

static void comp_unary(ExprLex *lx, InstrBuf *buf) {
    if (lx->cur.kind == TK_IDENT && strcmp(lx->cur.text, "aguarde") == 0) {
        lex_next(lx);
        comp_unary(lx, buf);
        ib_push(buf, mk_instr_none("AWAIT"));
        return;
    }
    comp_postfix(lx, buf);
}

static void comp_term(ExprLex *lx, InstrBuf *buf) {
    comp_unary(lx, buf);
    while (lx->cur.kind == TK_STAR || lx->cur.kind == TK_SLASH) {
        TokKind op = lx->cur.kind;
        lex_next(lx);
        comp_unary(lx, buf);
        ib_push(buf, mk_instr_none(op == TK_STAR ? "BINARY_MUL" : "BINARY_DIV"));
    }
}

static void comp_expr(ExprLex *lx, InstrBuf *buf) {
    comp_term(lx, buf);
    while (lx->cur.kind == TK_PLUS || lx->cur.kind == TK_MINUS) {
        TokKind op = lx->cur.kind;
        lex_next(lx);
        comp_term(lx, buf);
        ib_push(buf, mk_instr_none(op == TK_PLUS ? "BINARY_ADD" : "BINARY_SUB"));
    }
}

static void compilar_expressao(const char *expr, InstrBuf *buf) {
    ExprLex lx;
    memset(&lx, 0, sizeof(lx));
    lx.s = expr;
    lx.len = strlen(expr);
    lx.pos = 0;
    lex_next(&lx);
    comp_expr(&lx, buf);
}

static char *trim(char *s) {
    while (*s && isspace((unsigned char)*s)) s++;
    size_t n = strlen(s);
    while (n > 0 && isspace((unsigned char)s[n - 1])) s[--n] = '\0';
    return s;
}

static bool startswith(const char *s, const char *pfx) {
    return strncmp(s, pfx, strlen(pfx)) == 0;
}

static Program compilar_fonte_trm_nativo(const char *src, const char *origin_path) {
    Program p;
    memset(&p, 0, sizeof(p));
    p.origin_path = origin_path ? strdup(origin_path) : NULL;

    FuncBuilder *fns = NULL;
    size_t fns_len = 0;
    size_t fns_cap = 0;
    FuncBuilder *atual = NULL;

    InstrBuf entry;
    memset(&entry, 0, sizeof(entry));

    char *text = strdup(src);
    if (!text) fatal("sem memória");
    char *save = NULL;
    char *line = strtok_r(text, "\n", &save);
    size_t seq = 1;

    while (line) {
        char *ln = trim(line);
        if (ln[0] == '\0' || startswith(ln, "#") || startswith(ln, "//")) {
            line = strtok_r(NULL, "\n", &save);
            continue;
        }

        if (atual == NULL && startswith(ln, "importe ")) {
            char modulo[512];
            char alias[256];
            memset(modulo, 0, sizeof(modulo));
            memset(alias, 0, sizeof(alias));
            if (sscanf(ln, "importe \"%511[^\"]\" como %255s", modulo, alias) == 2) {
                ib_push(&entry, mk_instr_str("IMPORT_NAME", modulo));
                ib_push(&entry, mk_instr_str("STORE_NAME", alias));
            }
            line = strtok_r(NULL, "\n", &save);
            continue;
        }

        bool is_async = false;
        if (startswith(ln, "assíncrona função ") || startswith(ln, "assincrona funcao ") || startswith(ln, "assíncrona funcao ") || startswith(ln, "assincrona função ")) {
            is_async = true;
        }
        if (startswith(ln, "função ") || startswith(ln, "funcao ") || is_async) {
            char *sig = ln;
            if (is_async) {
                char *p1 = strstr(sig, "função ");
                if (!p1) p1 = strstr(sig, "funcao ");
                if (!p1) fatal("assinatura async invalida");
                sig = p1;
            }
            char *open = strchr(sig, '(');
            char *close = strrchr(sig, ')');
            if (!open || !close || close < open) fatal("assinatura de função invalida");
            char nome[256];
            memset(nome, 0, sizeof(nome));
            if (sscanf(sig, "função %255[^ (]", nome) != 1 && sscanf(sig, "funcao %255[^ (]", nome) != 1) fatal("nome de função inválido");

            if (fns_len == fns_cap) {
                fns_cap = fns_cap == 0 ? 8 : fns_cap * 2;
                fns = (FuncBuilder *)realloc(fns, fns_cap * sizeof(FuncBuilder));
                if (!fns) fatal("sem memória");
            }
            FuncBuilder *fb = &fns[fns_len++];
            memset(fb, 0, sizeof(*fb));
            fb->name = strdup(nome);
            fb->is_async = is_async;
            char code_name[300];
            snprintf(code_name, sizeof(code_name), "%s#%zu", nome, seq++);
            fb->code_name = strdup(code_name);

            size_t nparams = (size_t)(close - open - 1);
            char *params = xstrndup(open + 1, nparams);
            char *psave = NULL;
            char *pp = strtok_r(params, ",", &psave);
            while (pp) {
                char *pname = trim(pp);
                if (pname[0] != '\0') {
                    fb->params = (char **)realloc(fb->params, (fb->params_len + 1) * sizeof(char *));
                    if (!fb->params) fatal("sem memória");
                    fb->params[fb->params_len++] = strdup(pname);
                }
                pp = strtok_r(NULL, ",", &psave);
            }
            free(params);
            atual = fb;
            line = strtok_r(NULL, "\n", &save);
            continue;
        }

        if (atual != NULL && strcmp(ln, "fim") == 0) {
            ib_push(&atual->code, mk_instr_none("LOAD_CONST"));
            ib_push(&atual->code, mk_instr_none("RETURN_VALUE"));
            atual = NULL;
            line = strtok_r(NULL, "\n", &save);
            continue;
        }

        if (atual != NULL) {
            if (startswith(ln, "retorne ")) {
                compilar_expressao(ln + 8, &atual->code);
                ib_push(&atual->code, mk_instr_none("RETURN_VALUE"));
            } else if (startswith(ln, "lance ")) {
                compilar_expressao(ln + 6, &atual->code);
                ib_push(&atual->code, mk_instr_none("THROW"));
            } else {
                char *eq = strchr(ln, '=');
                if (eq && !(eq > ln && eq[-1] == '=') && !(eq[1] == '=')) {
                    char *left = xstrndup(ln, (size_t)(eq - ln));
                    char *name = trim(left);
                    char *rhs = trim(eq + 1);
                    compilar_expressao(rhs, &atual->code);
                    ib_push(&atual->code, mk_instr_str("STORE_NAME", name));
                    free(left);
                } else {
                    compilar_expressao(ln, &atual->code);
                    ib_push(&atual->code, mk_instr_none("POP_TOP"));
                }
            }
        }

        line = strtok_r(NULL, "\n", &save);
    }
    free(text);

    for (size_t i = 0; i < fns_len; i++) {
        ib_push(&entry, mk_instr_make_function(fns[i].name, fns[i].code_name, fns[i].is_async));
        ib_push(&entry, mk_instr_str("STORE_NAME", fns[i].name));
    }
    ib_push(&entry, mk_instr_none("HALT"));

    p.entry = (Function *)calloc(1, sizeof(Function));
    if (!p.entry) fatal("sem memória");
    p.entry->name = strdup("__entry__");
    p.entry->code_name = strdup("__entry__");
    p.entry->is_async = false;
    p.entry->params = NULL;
    p.entry->params_len = 0;
    p.entry->instrs = entry.items;
    p.entry->instr_len = entry.len;

    p.functions = (Function *)calloc(fns_len ? fns_len : 1, sizeof(Function));
    if (!p.functions) fatal("sem memória");
    p.fn_len = fns_len;
    for (size_t i = 0; i < fns_len; i++) {
        p.functions[i].name = fns[i].name;
        p.functions[i].code_name = fns[i].code_name;
        p.functions[i].is_async = fns[i].is_async;
        p.functions[i].params = fns[i].params;
        p.functions[i].params_len = fns[i].params_len;
        p.functions[i].instrs = fns[i].code.items;
        p.functions[i].instr_len = fns[i].code.len;
    }
    free(fns);
    return p;
}

static void write_json_string(FILE *f, const char *s) {
    fputc('"', f);
    for (const char *p = s ? s : ""; *p; p++) {
        if (*p == '"' || *p == '\\') {
            fputc('\\', f);
            fputc(*p, f);
        } else if (*p == '\n') {
            fputs("\\n", f);
        } else if (*p == '\r') {
            fputs("\\r", f);
        } else if (*p == '\t') {
            fputs("\\t", f);
        } else {
            fputc(*p, f);
        }
    }
    fputc('"', f);
}

static void write_arg_json(FILE *f, Arg *a) {
    if (!a || a->type == ARG_NONE) {
        fputs("null", f);
    } else if (a->type == ARG_NUM) {
        fprintf(f, "%.15g", a->n);
    } else if (a->type == ARG_STR) {
        write_json_string(f, a->s);
    } else if (a->type == ARG_MAKE_FN) {
        fputs("[", f);
        write_json_string(f, a->make_fn.display);
        fputs(", ", f);
        write_json_string(f, a->make_fn.code);
        fputs(", ", f);
        fputs(a->make_fn.is_async ? "true" : "false", f);
        fputs("]", f);
    } else if (a->type == ARG_TRY) {
        fputs("{", f);
        fprintf(f, "\"catch_ip\": %d, \"finally_ip\": %d, \"catch_name\": ", a->try_arg.catch_ip, a->try_arg.finally_ip);
        write_json_string(f, a->try_arg.catch_name ? a->try_arg.catch_name : "");
        fputs("}", f);
    } else {
        fputs("null", f);
    }
}

static void write_function_json(FILE *f, Function *fn, int indent) {
    (void)indent;
    fputs("{\"name\": ", f);
    write_json_string(f, fn->name);
    fputs(", \"params\": [", f);
    for (size_t i = 0; i < fn->params_len; i++) {
        if (i) fputs(", ", f);
        write_json_string(f, fn->params[i]);
    }
    fputs("], \"is_async\": ", f);
    fputs(fn->is_async ? "true" : "false", f);
    fputs(", \"instructions\": [", f);
    for (size_t i = 0; i < fn->instr_len; i++) {
        if (i) fputs(", ", f);
        fputs("{\"op\": ", f);
        write_json_string(f, fn->instrs[i].op);
        fputs(", \"arg\": ", f);
        write_arg_json(f, &fn->instrs[i].arg);
        fputs("}", f);
    }
    fputs("]}", f);
}

static int escrever_programa_tbc(const Program *p, const char *out_path) {
    FILE *f = fopen(out_path, "wb");
    if (!f) {
        perror("fopen");
        return 1;
    }
    fputs("{\"entry\": ", f);
    write_function_json(f, p->entry, 2);
    fputs(", \"functions\": {", f);
    for (size_t i = 0; i < p->fn_len; i++) {
        if (i) fputs(", ", f);
        write_json_string(f, p->functions[i].code_name);
        fputs(": ", f);
        write_function_json(f, &p->functions[i], 2);
    }
    fputs("}}\n", f);
    fclose(f);
    return 0;
}

static int compilar_trm_nativo_para_tbc(const char *arquivo_fonte, const char *arquivo_saida) {
    char *src = read_file(arquivo_fonte);
    Program p = compilar_fonte_trm_nativo(src, arquivo_fonte);
    free(src);
    return escrever_programa_tbc(&p, arquivo_saida);
}

static int executar_trm_nativo(const char *arquivo_fonte) {
    char *src = read_file(arquivo_fonte);
    Program p = compilar_fonte_trm_nativo(src, arquivo_fonte);
    free(src);
    Env *globals = env_new(NULL);
    env_set_local(globals, "exibir", value_builtin_exibir());
    env_set_local(globals, "criar_tarefa", value_builtin_criar_tarefa());
    env_set_local(globals, "com_timeout", value_builtin_com_timeout());
    env_set_local(globals, "cancelar_tarefa", value_builtin_cancelar_tarefa());
    env_set_local(globals, "dormir", value_builtin_dormir());
    env_set_local(globals, "create_task", value_builtin_criar_tarefa());
    env_set_local(globals, "with_timeout", value_builtin_com_timeout());
    env_set_local(globals, "cancel_task", value_builtin_cancelar_tarefa());
    env_set_local(globals, "sleep", value_builtin_dormir());
    p.entry->closure = globals;

    ExecResult e = run_function(&p, p.entry, NULL, 0, globals);
    if (e.threw) {
        fprintf(stderr, "Erro nativo: exceção não tratada: ");
        value_print(e.value);
        fprintf(stderr, "\n");
        return 2;
    }
    Value principal;
    if (env_get(globals, "principal", &principal) && principal.type == VAL_FUNC) {
        ExecResult r = call_value(&p, principal, NULL, 0);
        if (r.threw) {
            fprintf(stderr, "Erro nativo: exceção não tratada em principal: ");
            value_print(r.value);
            fprintf(stderr, "\n");
            return 2;
        }
        if (r.value.type == VAL_AWAITABLE || r.value.type == VAL_TASK) {
            ExecResult ar = await_value(&p, r.value);
            if (ar.threw) {
                fprintf(stderr, "Erro nativo: exceção não tratada em principal assíncrona: ");
                value_print(ar.value);
                fprintf(stderr, "\n");
                return 2;
            }
        }
    }
    return 0;
}

static int run_tbc(const char *path) {
    char *json = read_file(path);
    Program p = parse_program(json, path);

    Env *globals = env_new(NULL);
    env_set_local(globals, "exibir", value_builtin_exibir());
    env_set_local(globals, "criar_tarefa", value_builtin_criar_tarefa());
    env_set_local(globals, "com_timeout", value_builtin_com_timeout());
    env_set_local(globals, "cancelar_tarefa", value_builtin_cancelar_tarefa());
    env_set_local(globals, "dormir", value_builtin_dormir());
    env_set_local(globals, "create_task", value_builtin_criar_tarefa());
    env_set_local(globals, "with_timeout", value_builtin_com_timeout());
    env_set_local(globals, "cancel_task", value_builtin_cancelar_tarefa());
    env_set_local(globals, "sleep", value_builtin_dormir());
    p.entry->closure = globals;

    ExecResult none = run_function(&p, p.entry, NULL, 0, globals);
    if (none.threw) {
        fprintf(stderr, "Erro nativo: exceção não tratada: ");
        value_print(none.value);
        fprintf(stderr, "\n");
        free(json);
        return 2;
    }

    Value principal;
    if (env_get(globals, "principal", &principal) && principal.type == VAL_FUNC) {
        ExecResult pcall = call_value(&p, principal, NULL, 0);
        if (pcall.threw) {
            fprintf(stderr, "Erro nativo: exceção não tratada em principal: ");
            value_print(pcall.value);
            fprintf(stderr, "\n");
            free(json);
            return 2;
        }
        if (pcall.value.type == VAL_AWAITABLE || pcall.value.type == VAL_TASK) {
            ExecResult aw = await_value(&p, pcall.value);
            if (aw.threw) {
                fprintf(stderr, "Erro nativo: exceção não tratada em principal assíncrona: ");
                value_print(aw.value);
                fprintf(stderr, "\n");
                free(json);
                return 2;
            }
        }
    }

    free(json);
    return 0;
}

static void usage(void) {
    puts("trama-nativo (v2.0.9)");
    puts("uso:");
    puts("  trama-nativo --diagnostico-runtime");
    puts("  trama-nativo executar-tbc arquivo.tbc");
    puts("  trama-nativo run-tbc arquivo.tbc   # alias de compatibilidade");
    puts("  trama-nativo executar arquivo.trm");
    puts("  trama-nativo run arquivo.trm        # alias de compatibilidade");
    puts("  trama-nativo compilar arquivo.trm -o saida.tbc");
    puts("  trama-nativo compile arquivo.trm -o saida.tbc    # alias de compatibilidade");
    puts("obs:");
    puts("  executar/compilar/executar-tbc rodam no backend nativo.");
}

int main(int argc, char **argv) {
    if (argc >= 2 && strcmp(argv[1], "--diagnostico-runtime") == 0) {
        puts("backend_runtime=nativo_c_vm");
        puts("backend_compilador=nativo_c_compilador");
        puts("requer_python_host=nao");
        puts("runtime_backend=nativo_c_vm");
        puts("compilador_backend=nativo_c_compilador");
        puts("python_host_required=nao");
        return 0;
    }

    if (argc >= 3 && (strcmp(argv[1], "executar-tbc") == 0 || strcmp(argv[1], "run-tbc") == 0)) {
        return run_tbc(argv[2]);
    }

    if (argc >= 3 && (strcmp(argv[1], "executar") == 0 || strcmp(argv[1], "run") == 0)) {
        return executar_trm_nativo(argv[2]);
    }

    if (argc >= 3 && (strcmp(argv[1], "compilar") == 0 || strcmp(argv[1], "compile") == 0)) {
        const char *in = argv[2];
        const char *out = "programa.tbc";
        for (int i = 3; i < argc; i++) {
            if ((strcmp(argv[i], "-o") == 0 || strcmp(argv[i], "--saida") == 0) && i + 1 < argc) {
                out = argv[i + 1];
                i++;
            }
        }
        return compilar_trm_nativo_para_tbc(in, out);
    }

    usage();
    return 0;
}
