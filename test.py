import lisp


def run(code: str):
    env = {} | lisp.lisp_builtins
    output = []
    for exp in lisp.parse(code):
        if (rv := lisp.eval_(exp, env)) is not None:
            output.append(lisp.repr_(rv))
    return output


def test():
    code = """
    (define square (lambda (x) (* x x)))
    (map square (list 1 2 3))
    """
    assert run(code) == ["(1 4 9)"]

    code = """
    (define cons (lambda (x y)
        ((varargs (#py "tuple")) x y)))
    (car (cons 5 2))
    """
    assert run(code) == ["5"]

    code = """
    (define y 123)
    (if (> y 124) "test1" "test2")
    """
    assert run(code) == ["'test2'"]

    code = """
    (define fact (lambda (x)
        (if (> x 0)
            (* x (fact (- x 1)))
            1)))

    (fact 5)
    """
    assert run(code) == ["120"]

    code = """
    (define count (lambda (item lst)
        (if lst
            (+ (= item (car lst)) (count item (cdr lst)))
            0)))
    (count 4 (quote (1 4 3 4 5)))
    (count (quote the) (quote (the more the merrier the bigger the better)))
    """
    assert run(code) == ["2", "4"]

    code = """
    (define twice (lambda (x) (* 2 x)))
    (twice 5)
    (define repeat (lambda (f) (lambda (x) (f (f x)))))
    ((repeat twice) 10)
    """
    assert run(code) == ["10", "40"]
