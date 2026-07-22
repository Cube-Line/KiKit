import traceback
import sys
import click

from .common import execute_with_debug

def fabCommand(f):
    """
    为所有制造命令添加相同功能的装饰器
    """
    # Note that the decorators has to be specified in a reverse order
    f = click.argument("outputdir", type=click.Path(file_okay=False))(f)
    f = click.argument("board", type=click.Path(dir_okay=False))(f)

    f = click.option('--drc/--no-drc', is_flag=True, default=True,
        help="在生成输出前运行 DRC 检查。")(f)
    f = click.option("--nametemplate", default="{}",
        help="输出文件命名模板。")(f)
    f = click.option("--debug", is_flag=True, default=False,
        help="打印额外的调试信息")(f)
    return f

@click.command()
@fabCommand
@click.option("--assembly/--no-assembly", help="生成 SMT 贴片文件（需要原理图）")
@click.option("--schematic", type=click.Path(dir_okay=False), help="电路板原理图（贴片文件必需）")
@click.option("--ignore", type=str, default="", help="要从 SMT 贴片中排除的位号列表（逗号分隔）")
@click.option("--field", type=str, default="LCSC",
    help="包含 LCSC 订购代码的元件字段列表（逗号分隔）。使用首个存在的字段")
@click.option("--corrections", type=str, default="JLCPCB_CORRECTION",
    help="包含修正值的元件字段列表（逗号分隔）。使用首个存在的字段")
@click.option("--correctionpatterns", type=click.Path(dir_okay=False))
@click.option("--missingError/--missingWarn", help="如果非忽略元件缺少 LCSC 字段，则报错")
@click.option("--autoname/--no-autoname", is_flag=True, help="基于电路板名称自动命名输出文件")
def jlcpcb(**kwargs):
    """
    为 JLCPCB 准备制造文件，包括其贴片服务
    """
    from kikit.fab import jlcpcb
    from kikit.common import fakeKiCADGui
    app = fakeKiCADGui()
    return execute_with_debug(jlcpcb.exportJlcpcb, kwargs)

@click.command()
@fabCommand
@click.option("--assembly/--no-assembly", help="生成 SMT 贴片文件（需要原理图）")
@click.option("--schematic", type=click.Path(dir_okay=False), help="电路板原理图（贴片文件必需）")
@click.option("--ignore", type=str, default="", help="要从 SMT 贴片中排除的位号列表（逗号分隔）")
@click.option("--corrections", type=str, default="PCBWAY_CORRECTION",
    help="包含修正值的元件字段列表（逗号分隔）。使用首个存在的字段")
@click.option("--correctionpatterns", type=click.Path(dir_okay=False))
@click.option("--manufacturer", type=str, default="Manufacturer",
    help="提取制造商名称的字段列表（逗号分隔）。使用首个存在的字段。")
@click.option("--partNumber", type=str, default="PartNumber",
    help="提取料号的字段列表（逗号分隔）。使用首个存在的字段。")
@click.option("--description", type=str, default="Description",
    help="提取描述的字段列表（逗号分隔）。使用首个存在的字段。")
@click.option("--notes", type=str, default="Notes",
    help="提取备注的字段列表（逗号分隔）。使用首个存在的字段。")
@click.option("--solderType", type=str, default="Type",
    help="提取焊接类型的字段列表（逗号分隔）。使用首个存在的字段。")
@click.option("--footprint", type=str, default="FootprintPCBWay",
    help="为 BOM 提取封装名称的字段列表（逗号分隔）。使用首个存在的字段，否则使用封装库名称。")
@click.option("--nBoards", type=int, default=1,
    help="每拼板的电路板数量（默认为 1）。")
@click.option("--missingError/--missingWarn", help="如果非忽略元件缺少制造商/料号字段，则报错")
def pcbway(**kwargs):
    """
    为 PCBWAY 准备制造文件，包括其贴片服务
    """
    from kikit.fab import pcbway
    from kikit.common import fakeKiCADGui
    app = fakeKiCADGui()
    return execute_with_debug(pcbway.exportPcbway, kwargs)


@click.command()
@fabCommand
def oshpark(**kwargs):
    """
    为 OSH Park 准备制造文件
    """
    from kikit.fab import oshpark
    from kikit.common import fakeKiCADGui
    app = fakeKiCADGui()
    return execute_with_debug(oshpark.exportOSHPark, kwargs)

@click.command()
@fabCommand
@click.option("--schematic", type=click.Path(dir_okay=False), help="电路板原理图（贴片文件必需）")
@click.option("--ignore", type=str, default="", help="要从 SMT 贴片中排除的位号列表（逗号分隔）")
@click.option("--corrections", type=str, default="YY1_CORRECTION",
    help="包含修正值的元件字段列表（逗号分隔）。使用首个存在的字段")
@click.option("--correctionpatterns", type=click.Path(dir_okay=False))
def neodenyy1(**kwargs):
    """
    为 Neoden YY1 贴片机准备制造文件
    """
    from kikit.fab import neodenyy1
    from kikit.common import fakeKiCADGui
    app = fakeKiCADGui()
    return execute_with_debug(neodenyy1.exportNeodenYY1, kwargs)

@click.command()
@fabCommand
def openpnp(**kwargs):
    """
    为 OpenPnP 准备制造文件
    """
    from kikit.fab import openpnp
    from kikit.common import fakeKiCADGui
    app = fakeKiCADGui()
    return execute_with_debug(openpnp.exportOpenPnp, kwargs)

@click.group()
def fab():
    """
    为指定的制造厂导出完整的制造数据
    """
    pass

fab.add_command(jlcpcb)
fab.add_command(pcbway)
fab.add_command(oshpark)
fab.add_command(neodenyy1)
fab.add_command(openpnp)
