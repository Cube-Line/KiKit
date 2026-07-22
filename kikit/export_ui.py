import click

@click.group()
def export():
    """
    导出 KiCAD 电路板
    """
    pass

@click.command()
@click.argument("boardfile", type=click.Path(dir_okay=False))
@click.argument("outputdir", type=click.Path(file_okay=False), default=None)
def gerber(boardfile, outputdir):
    from kikit.export import gerberImpl
    from kikit.common import fakeKiCADGui
    app = fakeKiCADGui()

    gerberImpl(boardfile, outputdir)

@click.command()
@click.argument("boardfile", type=click.Path(dir_okay=False))
@click.argument("outputdir", type=click.Path(file_okay=False), default=None)
def dxf(boardfile, outputdir):
    """
    将电路板边缘和焊盘导出为 DXF 格式。

    如果未指定输出目录，则使用工作目录。

    此命令设计用于构建 3D 打印钢网。
    """
    from kikit.export import dxfImpl
    from kikit.common import fakeKiCADGui
    app = fakeKiCADGui()

    dxfImpl(boardfile, outputdir)

export.add_command(gerber)
export.add_command(dxf)
