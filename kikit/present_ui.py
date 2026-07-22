import click

@click.command()
@click.argument("outdir", type=click.Path(file_okay=False))
@click.option("--description", "-d", type=click.Path(dir_okay=False),
    required=True, help="包含页面文本的 markdown 文件")
@click.option("--board", "-b", type=(str, str, click.Path(dir_okay=False)),
    multiple=True, help="<名称> <注释> <kicad_pcb 文件> 包含在生成的页面中。")
@click.option("--resource", "-r", type=click.Path(dir_okay=True), multiple=True,
    help="额外的资源文件（例如描述中引用的图片）。")
@click.option("--template", type=click.Path(), default="default",
    help="模板目录路径或内置模板名称。详见 doc/present.md 了解模板规范。")
@click.option("--repository", type=str, help="仓库 URL")
@click.option("--name", type=str, help="电路板名称（用于标题等）", required=True)
def boardpage(**kwargs):
    """
    基于 markdown 描述构建电路板展示页面，包含电路板源文件和 Gerber 文件的下载链接。
    """
    from kikit import present
    from kikit.common import fakeKiCADGui
    app = fakeKiCADGui()

    return present.boardpage(**kwargs)

@click.group()
def present():
    """
    准备电路板展示
    """
    pass

present.add_command(boardpage)
