import click

@click.command()
@click.argument("board", type=click.Path(dir_okay=False, exists=True))
@click.option("--show/--hide", "-s", help="显示/隐藏匹配模式的位号")
@click.option("--pattern", "-p", type=str, help="位号的正则表达式")
def references(board, show, pattern):
    """
    显示或隐藏电路板上匹配模式的位号。
    """
    from kikit import modify
    from kikit.common import fakeKiCADGui
    app = fakeKiCADGui()

    b = modify.pcbnew.LoadBoard(board)
    modify.references(b, show, pattern)
    b.Save(board)

@click.command()
@click.argument("board", type=click.Path(dir_okay=False, exists=True))
@click.option("--show/--hide", "-s", help="显示/隐藏匹配模式的数值")
@click.option("--pattern", "-p", type=str, help="数值的正则表达式")
def values(board, show, pattern):
    """
    显示或隐藏电路板上匹配模式的数值。
    """
    from kikit import modify
    from kikit.common import fakeKiCADGui
    app = fakeKiCADGui()

    b = modify.pcbnew.LoadBoard(board)
    modify.values(b, show, pattern)
    b.Save(board)

@click.group()
def modify():
    """
    修改电路板项目
    """
    pass

modify.add_command(references)
modify.add_command(values)
