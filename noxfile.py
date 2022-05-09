import nox

nox.options.session = []

@nox.session
def lint(session):
    session.install("flake8", "black")
    session.run("black", "pyrex")
    session.run("flake8", "pyrex", "--ignore", "E,W293,W503")
