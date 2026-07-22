import click
from enum import Enum

class ReportLevel(Enum):
    warning = "warning"
    error = "error"

    def __str__(self):
        return self.value

class EnumType(click.Choice):
    def __init__(self, enum: Enum, case_sensitive=False):
        self.__enum = enum
        super().__init__(choices=[item.value for item in enum], case_sensitive=case_sensitive)

    def convert(self, value, param, ctx):
        if value is None or isinstance(value, Enum):
            return value

        converted_str = super().convert(value, param, ctx)
        return self.__enum(converted_str)

@click.group()
def drc():
    """
    验证电路板的设计规则
    """
    pass

@click.command()
@click.argument("boardfile", type=click.Path(dir_okay=False))
@click.option("--useMm/--useInch", default=True)
@click.option("--strict/--weak", default=False,
    help="检查所有走线错误")
@click.option("--ignoreExcluded/--reportExcluded", default=True,
    help="报告已排除的项目")
@click.option("--level", type=EnumType(ReportLevel), default=ReportLevel.error,
    help="最低报告严重级别")
def run(boardfile, usemm, ignoreexcluded, strict, level):
    """
    检查 DRC 规则。如果没有规则验证失败，进程退出码为 0。

    如果检测到任何错误，进程以非零退出码退出，并在标准输出上打印 DRC 报告。
    """
    from kikit.drc import runImpl
    import sys
    import pcbnew
    from kikit.common import fakeKiCADGui
    app = fakeKiCADGui()

    try:
        board = pcbnew.LoadBoard(boardfile)
        failed = runImpl(board, usemm, ignoreexcluded, strict, level, lambda x: print(x))
        if not failed:
            print("未发现 DRC 错误。")
        else:
            print("发现 DRC 违规。请参阅上面的报告。")
        sys.exit(failed)
    except Exception as e:
        raise e
        sys.stderr.write("发生错误：" + str(e) + "\n")
        sys.exit(1)

drc.add_command(run)
