import sys, os
sys.path.append(os.path.realpath(__file__ + '/../../'))
from pfpp import is_functional, functional, parallelize, ast, function_to_ast

def uses_globals():
    global a

def calling_a_method():
    awesome.callmethod()

def double_assign():
    awesome = 1
    awesome = 2

def some_function():
    pass

def calling_a_function():
    some_function()

def subscript_assignment():
    lines = []
    lines[0] = 1
    x = []
    x[:] = [1,2,3]

def tuple_assignment():
    x = 0
    y = 0
    x, y = 1, 1

def not_functional():
    a = 10
    a = 20

def print_is_a_side_effect():
    print('I produce side effects')

def calls_a_non_functional_function():
    print_is_a_side_effect()

def assigns_to_a_non_functional_function():
    x = print_is_a_side_effect()

def check(fun, expected):
    assert is_functional(fun) == expected, '%s %s supposed to be functional' % \
                            (fun.__name__, expected and 'was' or 'was NOT')

def test_is_functional():
    yield check, calling_a_method, False
    yield check, double_assign, False
    yield check, calling_a_function, True
    yield check, subscript_assignment, False
    yield check, tuple_assignment, False
    yield check, calls_a_non_functional_function, False
    yield check, print_is_a_side_effect, False
    yield check, assigns_to_a_non_functional_function, False
    yield check, uses_globals, False

def the_simplest_function():
    return 10

def pre_simple_parallelization():
    x = the_simplest_function()

def simple_parallelization():
    __rm__.reset()
    __rm__['x'] = __rm__.run(the_simplest_function, [])

def pre_retrieve_results():
    x = the_simplest_function()
    return x

def retrieve_results():
    __rm__.reset()
    __rm__['x'] = __rm__.run(the_simplest_function, [])
    return __rm__['x']

def pre_several_results():
    x = the_simplest_function()
    y = the_simplest_function()
    return x + y

def several_results():
    __rm__.reset()
    __rm__['x'] = __rm__.run(the_simplest_function, [])
    __rm__['y'] = __rm__.run(the_simplest_function, [])
    return __rm__['x'] + __rm__['y']

def ast_dump_scrub(node):
    import re
    d = ast.dump(node)
    return re.sub("FunctionDef\(name='[^']*'", '', d)

def test_parallelization():
    print ast_dump_scrub(parallelize(pre_retrieve_results))
    print ast_dump_scrub(function_to_ast(retrieve_results))
    assert ast_dump_scrub(parallelize(pre_simple_parallelization))== \
           ast_dump_scrub(function_to_ast(simple_parallelization))
    assert ast_dump_scrub(parallelize(pre_retrieve_results))== \
           ast_dump_scrub(function_to_ast(retrieve_results))
    assert ast_dump_scrub(parallelize(pre_several_results))== \
           ast_dump_scrub(function_to_ast(several_results))
