import click
import os
import csv
import io
import glob
import traceback
from kikit.panelize_ui_sections import *

PKG_BASE = os.path.dirname(__file__)
PRESETS = os.path.join(PKG_BASE, "resources/panelizePresets")
IS_CLICK_V8 = click.__version__.startswith("8.")

# We would like to support both, click v7 and v8 in order to maximize
# compatibility. However, since click v8.1 there is breaking change in the way
# shell completion works. This functions hides the differences and should allow
# us to use both. Pass to it as **addCompatibleCompletion(completionFunction)
def addCompatibleShellCompletion(completionFn):
    if IS_CLICK_V8:
        import click.shell_completion
        def completion(*args, **kwargs):
            return [click.shell_completion.CompletionItem(x) for x in completionFn(*args, **kwargs)]
        return {"shell_complete": completionFn}
    else:
        return {"autocompletion": completionFn}

def splitStr(delimiter, escapeChar, s):
    """
    Splits s based on delimiter that can be escaped via escapeChar
    """
    # Let's use csv reader to implement this
    reader = csv.reader(io.StringIO(s), delimiter=delimiter, escapechar=escapeChar)
    # Unpack first line
    for x in reader:
        return x


class Section(click.ParamType):
    """
    A CLI argument type for overriding section parameters. Basically a semicolon
    separated list of `key: value` pairs. The first word might omit the key; in
    that case "type" key is used.
    """
    name = "parameter_list"

    def convert(self, value, param, ctx):
        if len(value.strip()) == 0:
            self.fail(f"{value} 不是有效的参数规格",
                param, ctx)
        try:
            values = {}
            for i, pair in enumerate(splitStr(";", "\\", value)):
                if len(pair.strip()) == 0:
                    continue
                s = pair.split(":", 1)
                if i == 0 and len(s) == 1:
                    values["type"] = s[0].strip()
                    continue
                key, value = s[0].strip(), s[1].strip()
                values[key] = value
            return values
        except (TypeError, IndexError):
            self.fail(f"'{pair}' 不是有效的键: 值对",
                param,
                ctx)

class HookPlugin(click.ParamType):
    """
    A CLI argument type for a HookPlugin. The format is <moduleName or
    path>:<plugin name>:<arg>. The arg is optional.
    """
    name = "<module>.<plugin>:[arg]"

    def convert(self, value, param, ctx):
        pieces = value.split(":", maxsplit=1)
        specPieces = pieces[0].rsplit(".", maxsplit=1)
        if len(specPieces) < 2:
            self.fail(f"{value} 不是有效的插件规格")
        module = specPieces[0]
        pluginName = specPieces[1]
        arg = "" if len(pieces) == 2 else pieces[1]
        return (module, pluginName, arg)


def completePath(prefix, fileSuffix=""):
    """
    This is rather hacky and  far from ideal, however, until Click 8 we probably
    cannot do much better.
    """
    paths = []
    for p in glob.glob(prefix + "*"):
        if os.path.isdir(p):
            paths.append(p + "/")
        elif p.endswith(fileSuffix):
            paths.append(p)
    return paths

def pathCompletion(fileSuffix=""):
    def f(ctx, args, incomplete):
        return completePath(incomplete, fileSuffix)
    return f

def completePreset(ctx, args, incomplete):
    presets = [":" + x.replace(".json", "")
        for x in os.listdir(PRESETS)
        if x.endswith(".json") and (x.startswith(incomplete) or x.startswith(incomplete[1:]))]
    if incomplete.startswith(":"):
        return presets
    return presets + completePath(incomplete, ".json")

def lastSectionPair(incomplete):
    """
    Given an incomplete command text of a section, return the last (possibly
    incomplete) key-value pair
    """
    lastSection = incomplete.split(";")[-1]
    x = [x.strip() for x in lastSection.split(":", 1)]
    if len(x) == 1:
        return x[0], ""
    return x

def hasNoSectionPair(incomplete):
    return ";" not in incomplete

def completeSection(section):
    def fun(ctx, args, incomplete):
        if incomplete.startswith("'"):
            incomplete = incomplete[1:]
        key, val = lastSectionPair(incomplete)

        candidates = []
        if hasNoSectionPair(incomplete):
            candidates.extend([x for x in section["type"].vals if x.startswith(incomplete)])
        if len(val) == 0:
            trimmedIncomplete = incomplete.rsplit(";", 1)[0]
            candidates.extend([trimmedIncomplete + x + ":"
                for x in section.keys() if x.startswith(key)])
        return candidates
    return fun

@click.command()
@click.argument("input", type=click.Path(dir_okay=False),
    **addCompatibleShellCompletion(pathCompletion(".kicad_pcb")))
@click.argument("output", type=click.Path(dir_okay=False),
    **addCompatibleShellCompletion(pathCompletion(".kicad_pcb")))
@click.option("--preset", "-p", multiple=True,
    help="拼板预设文件；使用前缀 ':' 选择内置样式。",
    **addCompatibleShellCompletion(completePreset))
@click.option("--plugin", multiple=True, type=HookPlugin(),
    help="拼板过程中使用的钩子插件",
    **addCompatibleShellCompletion(completePreset))
@click.option("--layout", "-l", type=Section(),
    help="覆盖布局设置。",
    **addCompatibleShellCompletion(completeSection(LAYOUT_SECTION)))
@click.option("--source", "-s", type=Section(),
    help="覆盖源设置。",
    **addCompatibleShellCompletion(completeSection(SOURCE_SECTION)))
@click.option("--tabs", "-t", type=Section(),
    help="覆盖标签设置。",
    **addCompatibleShellCompletion(completeSection(TABS_SECTION)))
@click.option("--cuts", "-c", type=Section(),
    help="覆盖切割设置。",
    **addCompatibleShellCompletion(completeSection(CUTS_SECTION)))
@click.option("--framing", "-r", type=Section(),
    help="覆盖边框设置。",
    **addCompatibleShellCompletion(completeSection(FRAMING_SECTION)))
@click.option("--tooling", "-o", type=Section(),
    help="覆盖工具孔设置。",
    **addCompatibleShellCompletion(completeSection(TOOLING_SECTION)))
@click.option("--fiducials", "-f", type=Section(),
    help="覆盖基准点设置。",
    **addCompatibleShellCompletion(completeSection(FIDUCIALS_SECTION)))
@click.option("--text", type=Section(),
    help="覆盖文本设置。",
    **addCompatibleShellCompletion(completeSection(TEXT_SECTION)))
@click.option("--text2", type=Section(),
    help="覆盖文本设置。",
    **addCompatibleShellCompletion(completeSection(TEXT_SECTION)))
@click.option("--text3", type=Section(),
    help="覆盖文本设置。",
    **addCompatibleShellCompletion(completeSection(TEXT_SECTION)))
@click.option("--text4", type=Section(),
    help="覆盖文本设置。",
    **addCompatibleShellCompletion(completeSection(TEXT_SECTION)))
@click.option("--copperfill", "-u", type=Section(),
    help="覆盖铜填充设置。",
    **addCompatibleShellCompletion(completeSection(COPPERFILL_SECTION)))
@click.option("--page", "-P", type=Section(),
    help="覆盖页面设置。",
    **addCompatibleShellCompletion(completeSection(POST_SECTION)))
@click.option("--post", "-z", type=Section(),
    help="覆盖后处理设置。",
    **addCompatibleShellCompletion(completeSection(POST_SECTION)))
@click.option("--debug", type=Section(),
    help="在拼板中包含调试轨迹或绘图。",
    **addCompatibleShellCompletion(completeSection(DEBUG_SECTION)))
@click.option("--dump", "-d", type=click.Path(file_okay=True, dir_okay=False),
    help="将构建的预设转储到 JSON 文件。")
def panelize(input, output, preset, plugin, layout, source, tabs, cuts, framing,
             tooling, fiducials, text, text2, text3, text4, copperfill, page,
             post, debug, dump):
    """
    拼板
    """
    try:
        # Hide the import in the function to make KiKit start faster
        from kikit import panelize_ui_impl as ki
        import sys
        from kikit.common import fakeKiCADGui
        app = fakeKiCADGui()

        preset = ki.obtainPreset(preset,
            layout=layout, source=source, tabs=tabs, cuts=cuts, framing=framing,
            tooling=tooling, fiducials=fiducials, text=text,text2=text2,
            text3=text3, text4=text4, copperfill=copperfill, page=page,
            post=post, debug=debug)

        doPanelization(input, output, preset, plugin)

        if (dump):
            with open(dump, "w", encoding="utf-8") as f:
                f.write(ki.dumpPreset(preset))
    except Exception as e:
        import sys
        from kikit.panelize import NonFatalErrors
        if isinstance(e, NonFatalErrors):
            sys.stderr.write(str(e) + "\n")
        else:
            sys.stderr.write("发生错误：" + str(e) + "\n")
            sys.stderr.write("未生成输出文件\n")
        if isinstance(preset, dict) and preset["debug"]["trace"]:
            traceback.print_exc(file=sys.stderr)
        sys.exit(1)

def doPanelization(input, output, preset, plugins=[]):
    """
    The panelization logic is separated into a separate function so we can
    handle errors based on the context; e.g., CLI vs GUI
    """
    from kikit import panelize_ui_impl as ki
    from kikit.panelize import Panel, NonFatalErrors, PanelError
    import pcbnew
    from pcbnew import LoadBoard
    from itertools import chain

    board = LoadBoard(input)
    if preset["debug"]["deterministic"]:
        pcbnew.KIID.SeedGenerator(42)
    if board is None:
        raise PanelError(f"无法加载电路板 {input}。请检查路径是否正确以及是否有读取权限。")
    panel = Panel(output)

    useHookPlugins = ki.loadHookPlugins(plugins, board, preset)

    useHookPlugins(lambda x: x.prePanelSetup(panel))

    for tabFootprint in preset["tabs"]["tabfootprints"]:
        panel.annotationReader.registerTab(tabFootprint.lib, tabFootprint.footprint)

    panel.inheritDesignSettings(board)
    panel.inheritProperties(board)
    panel.inheritTitleBlock(board)
    panel.inheritLayerNames(board)

    useHookPlugins(lambda x: x.afterPanelSetup(panel))

    sourceArea = ki.readSourceArea(preset["source"], board)
    substrates, framingSubstrates, backboneCuts = \
        ki.buildLayout(preset, panel, input, sourceArea)

    useHookPlugins(lambda x: x.afterLayout(panel, substrates))

    tabCuts = ki.buildTabs(preset, panel, substrates, framingSubstrates)

    useHookPlugins(lambda x: x.afterTabs(panel, tabCuts, backboneCuts))

    preFrameSubstrate = panel.boardSubstrate.substrates

    frameCuts = ki.buildFraming(preset, panel)

    useHookPlugins(lambda x: x.afterFraming(panel, frameCuts))

    ki.buildTabFillets(preset, panel, preFrameSubstrate)

    ki.buildTooling(preset, panel)
    ki.buildFiducials(preset, panel)
    for textSection in ["text", "text2", "text3", "text4"]:
        ki.buildText(preset[textSection], panel)
    ki.buildPostprocessing(preset["post"], panel)

    ki.makeTabCuts(preset, panel, tabCuts)
    ki.makeOtherCuts(preset, panel, chain(backboneCuts, frameCuts))

    useHookPlugins(lambda x: x.afterCuts(panel))

    ki.buildCopperfill(preset["copperfill"], panel)

    ki.setStackup(preset["source"], panel)
    ki.setPageSize(preset["page"], panel, board)
    ki.positionPanel(preset["page"], panel)

    ki.runUserScript(preset["post"], panel)
    useHookPlugins(lambda x: x.finish(panel))

    ki.buildDebugAnnotation(preset["debug"], panel)

    panel.save(reconstructArcs=preset["post"]["reconstructarcs"],
               refillAllZones=preset["post"]["refillzones"],
               edgeWidth=preset["post"]["edgewidth"])

    if panel.hasErrors():
        raise NonFatalErrors(panel.errors)


@click.command()
@click.argument("input", type=click.Path(dir_okay=False))
@click.argument("output", type=click.Path(dir_okay=False))
@click.option("--source", "-s", type=Section(),
    help="指定源设置。")
@click.option("--page", "-P", type=Section(),
    help="覆盖页面设置。",
    **addCompatibleShellCompletion(completeSection(POST_SECTION)))
@click.option("--debug", type=Section(),
    help="在拼板中包含调试轨迹或绘图。")
@click.option("--keepAnnotations/--stripAnnotations", default=True,
    help="保留注释" )
@click.option("--preserveArcs/--looseArcs", default=True,
    help="保留文件中的弧形" )
def separate(input, output, source, page, debug, keepannotations, preservearcs):
    """
    从多板设计中分离出单个电路板。分离后的电路板
    将放置在图纸中央。

    您可以通过边界框或注释指定电路板。有关使用
    的更多详细信息，请参阅文档。
    """
    try:
        from kikit import panelize_ui_impl as ki
        from kikit.panelize import Panel, NonFatalErrors
        from kikit.units import mm
        import pcbnew
        from pcbnew import LoadBoard, VECTOR2I
        from kikit.common import fakeKiCADGui
        app = fakeKiCADGui()

        preset = ki.obtainPreset([], validate=False, source=source, page=page, debug=debug)

        board = LoadBoard(input)
        if preset["debug"]["deterministic"]:
            pcbnew.KIID.SeedGenerator(42)
        sourceArea = ki.readSourceArea(preset["source"], board)

        panel = Panel(output)
        panel.inheritDesignSettings(board)
        panel.inheritProperties(board)
        panel.inheritTitleBlock(board)
        panel.inheritLayerNames(board)

        destination = VECTOR2I(150 * mm, 100 * mm)
        panel.appendBoard(input, destination, sourceArea,
            interpretAnnotations=(not keepannotations),
            netRenamer=lambda i, x: x,
            refRenamer=lambda i, x: x)
        ki.setStackup(preset["source"], panel)
        ki.setPageSize(preset["page"], panel, board)
        ki.positionPanel(preset["page"], panel)

        panel.save(reconstructArcs=preservearcs)

        if panel.hasErrors():
            raise NonFatalErrors(panel.errors)
    except Exception as e:
        import sys
        sys.stderr.write("发生错误：" + str(e) + "\n")
        sys.stderr.write("未生成输出文件\n")
        if isinstance(preset, dict) and preset["debug"]["trace"]:
            traceback.print_exc(file=sys.stderr)
        sys.exit(1)
