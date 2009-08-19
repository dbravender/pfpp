import inspect, ast, re, compiler
from pprint import pprint

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
    return fun

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
