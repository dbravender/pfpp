import inspect, ast, re, compiler
from pprint import pprint
from copy import copy

# The irony of the pfun module is that its purpose is to detect non-functional code
# but it is written in non-functional code... since Python's ast walkers are object
# oriented ^^

def function_to_ast(fun):
    definition = inspect.getsource(fun)
    lines = definition.split("\n")
    # remove whitespace
    lines[0] = lines[0].rstrip()
    m = re.match('^\s*', lines[0])
    if m:
        space_offset = m.span()[1]
        new_source = []
        for line in lines:
            new_source.append(line[space_offset:])
        return ast.parse("\n".join(new_source))
    else:
        return ast.parse(definition)

class FunctionalVisitor(ast.NodeVisitor):
    def __init__(self, globals):
        self.assigned_vars = []
        self.globals = globals
        self.problems = []
        super(ast.NodeVisitor, self).__init__()
    
    def visit_Print(self, node):
        self.problems.append('prints which is a side-effect')

    def visit_Call(self, node):
        if type(node.func) == ast.Name:
            func = self.globals[node.func.id]
            if not is_functional(func):
                self.problems.append('calls %s which is not strictly functional' % func.__name__)

        if type(node.func) == ast.Attribute:
            if type(node.func.value) == ast.Name:
                self.problems.append('calling "%s.%s" may produce side-effects' % (node.func.value.id, node.func.attr))

    def visit_Assign(self, node):
        for target in node.targets:
            target_names = []
            if type(target) == ast.Tuple:
                for item in target.elts:
                    if type(item) == ast.Name:
                        target_names.append(item.id)
            if type(target) == ast.Name:
                target_names.append(target.id)
            if type(target) == ast.Subscript:
                if type(target.value) == ast.Name:
                    target_names.append(target.value.id)
            for target_name in target_names:
                if target_name in self.assigned_vars:
                    self.problems.append('variable "%s" is assigned to more than once' % target_name)
                else:
                    self.assigned_vars.append(target_name)

def is_functional(fun):
    fv = FunctionalVisitor(fun.func_globals)
    fv.visit(function_to_ast(fun))
    if len(fv.problems):
        for problem in fv.problems:
            print('function %s: %s' % (fun.__name__, problem))
        return False
    return True

def functional(fun):
    ''' a wrapper that will stop execution if a function 
        is not strictly functional'''
    if not is_functional(fun):
        quit('The function "%s" is not strictly functional.' % fun.__name__)
    ast_code = ast.fix_missing_locations(parallelize(fun))
    code = compile(ast_code, '<unknown>', 'exec')
    exec code in fun.func_globals
    return fun.func_globals[fun.__name__]

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

def calls_a_non_functional_function():
    not_functional()

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

import multiprocessing
import multiprocessing.pool

class ResultsManager(object):
    def __init__(self):
        self.results = {}
        self.pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
        print 'results manager invoked'

    def __getitem__(self, item):
        if isinstance(self.results[item], multiprocessing.pool.ApplyResult):
            self.results[item] = self.results[item].get()
        return self.results[item]

    def __setitem__(self, item, value):
        self.results[item] = value

    def run(self, function, args):
        return self.pool.apply_async(function, args)

class ParallelizingTransformer(ast.NodeTransformer):
    def __init__(self):
        self.seen_variables = {}
        super(ast.NodeTransformer, self).__init__()

    def visit_FunctionDef(self, node):
        new_node = copy(node)
        new_node.body = []
        new_node.body.append(ast.Assign(targets=[ast.Name(id='__rm__', ctx=ast.Store())], value=ast.Call(func=ast.Name(id='ResultsManager', ctx=ast.Load()), args=[], keywords=[], starargs=None, kwargs=None)))
        for item in node.body:
            new_node.body.append(self.visit(item))
        return new_node

    def visit_Assign(self, node):
        # we only want to perform parallelization under certain conditions
        if isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):

            original_target = node.targets[0].id
            self.seen_variables[original_target] = True
            original_function = node.value.func.id
            original_args = node.value.args
            new_node = copy(node)
            new_node.targets = [ast.Subscript(value=ast.Name(id='__rm__', ctx=ast.Load()), slice=ast.Index(value=ast.Str(s=original_target)), ctx=ast.Store())]
            new_node.value = ast.Call(func=ast.Attribute(value=ast.Name(id='__rm__', ctx=ast.Load()), attr='run', ctx=ast.Load()), args=[ast.Name(id=node.value.func.id, ctx=ast.Load()), ast.List(elts=[], ctx=ast.Load())], keywords=[], starargs=None, kwargs=None)
            return ast.copy_location(new_node, node)

    def visit_Name(self, node):
        if node.id in self.seen_variables:
            node = ast.Subscript(value=ast.Name(id='__rm__', ctx=ast.Load()), slice=ast.Index(value=ast.Str(s=node.id)), ctx=ast.Load())
        return node

def parallelize(fun):
    pt = ParallelizingTransformer()
    return pt.visit(function_to_ast(fun))

def the_simplest_function():
    return 10

def pre_simple_parallelization():
    x = the_simplest_function()

def simple_parallelization_step1():
    __rm__['x'] = the_simplest_function()

def simple_parallelization_step2():
    __rm__ = ResultsManager()
    __rm__['x'] = __rm__.run(the_simplest_function, [])

def pre_retrieve_results():
    x = the_simplest_function()
    return x

def retrieve_results():
    __rm__ = ResultsManager()
    __rm__['x'] = __rm__.run(the_simplest_function, [])
    return __rm__['x']

def pre_several_results():
    x = the_simplest_function()
    y = the_simplest_function()
    return x + y

def several_results():
    __rm__ = ResultsManager()
    __rm__['x'] = __rm__.run(the_simplest_function, [])
    __rm__['y'] = __rm__.run(the_simplest_function, [])
    return __rm__['x'] + __rm__['y']

def ast_dump_scrub(node):
    import re
    d = ast.dump(node)
    return re.sub("FunctionDef\(name='[^']*'", '', d)

def test_parallelization():
    #print ast_dump_scrub(parallelize(pre_retrieve_results))
    #print ast_dump_scrub(function_to_ast(retrieve_results))
    assert ast_dump_scrub(parallelize(pre_simple_parallelization))== \
           ast_dump_scrub(function_to_ast(simple_parallelization_step2))
    assert ast_dump_scrub(parallelize(pre_retrieve_results))== \
           ast_dump_scrub(function_to_ast(retrieve_results))
    assert ast_dump_scrub(parallelize(pre_several_results))== \
           ast_dump_scrub(function_to_ast(several_results))
def x():
    print 'awesome'
    print('awesome')
    return 10

def y():
    return 20

def z():
    a = x()
    b = y()
    return a + b

z = functional(z)

if __name__ == '__main__':
    #ast = ast.fix_missing_locations(parallelize(pre_retrieve_results))
    #code = compile(ast, '<unknown>', 'exec')
    #exec code in locals()
    #print pre_retrieve_results()
    print z()
