import click
import sys

from .common import execute_with_debug


@click.command()
@click.argument("inputBoard", type=click.Path(dir_okay=False))
@click.argument("outputDir", type=click.Path(dir_okay=True))
@click.option("--pcbthickness", type=float, default=1.6,
    help="PCB 厚度（mm）")
@click.option("--thickness", type=float, default=0.15,
    help="钢网厚度（mm）。决定焊膏量。")
@click.option("--framewidth", type=float, default=1,
    help="定位框宽度")
@click.option("--ignore", type=str, default="",
    help="要从钢网中排除的元件位号列表（逗号分隔）")
@click.option("--cutout", type=str, default="",
    help="基于 courtyar 从钢网中挖空的元件位号列表（逗号分隔）")
@click.option("--frameclearance", type=float, default=0,
    help="钢网定位框间距（mm）")
@click.option("--enlargeholes", type=float, default=0,
    help="将焊盘孔扩大 x mm")
@click.option("--debug", is_flag=True, default=False,
        help="打印额外的调试信息")
def createPrinted(**kwargs):
    """
    创建 3D 打印自定位钢网。
    """
    from kikit import stencil

    return execute_with_debug(stencil.createPrinted, kwargs)


@click.command()
@click.argument("inputBoard", type=click.Path(dir_okay=False))
@click.argument("outputDir", type=click.Path(dir_okay=True))
@click.option("--jigsize", type=(int, int), default=(100, 100),
    help="治具框架尺寸（mm）：<宽> <高>")
@click.option("--jigthickness", type=float, default=3,
    help="治具厚度（mm）")
@click.option("--pcbthickness", type=float, default=1.6,
    help="PCB 厚度（mm）")
@click.option("--registerborder", type=(float, float), default=(3, 1),
    help="定位边框（mm）：<外> <内>")
@click.option("--tolerance", type=float, default=0.05,
    help="按容差值扩大定位区域")
@click.option("--ignore", type=str, default="",
    help="要从钢网中排除的元件位号列表（逗号分隔）")
@click.option("--cutout", type=str, default="",
    help="基于 courtyar 从钢网中挖空的元件位号列表（逗号分隔）")
@click.option("--debug", is_flag=True, default=False,
        help="打印额外的调试信息")
def create(**kwargs):
    """
    创建用于手动焊膏点涂治具的钢网和定位元素。
    更多详情请参阅：https://github.com/yaqwsx/KiKit/blob/master/doc/stencil.md
    """
    from kikit import stencil
    from kikit.common import fakeKiCADGui
    app = fakeKiCADGui()

    return execute_with_debug(stencil.create, kwargs)


@click.group()
def stencil():
    """
    创建焊膏钢网
    """
    pass

stencil.add_command(create)
stencil.add_command(createPrinted)
