from dataclasses import dataclass
import os
from typing import Any, List
from kikit import plugin
from kikit.units import readLength, readAngle, readPercents
from kikit.defs import Layer, EDA_TEXT_HJUSTIFY_T, EDA_TEXT_VJUSTIFY_T, PAPER_SIZES

class PresetError(RuntimeError):
    pass

ANCHORS = ["tl", "tr", "bl", "br", "mt", "mb", "ml", "mr", "c"]
PAPERS = ["inherit"] + PAPER_SIZES + ["user"]

@dataclass
class FootprintId:
    lib: str
    footprint: str

class SectionBase:
    def __init__(self, isGuiRelevant, description):
        self.description = description
        self.isGuiRelevant = isGuiRelevant

    def validate(self, x: str) -> Any:
        raise NotImplementedError("Validate was not overridden for SectionBase")

class SLength(SectionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, x):
        return readLength(x)

class SPercent(SectionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, x):
        x = x.strip()
        if not x.endswith("%"):
            raise PresetError("Percentage error has to end with %")
        return readPercents(x)

class SLengthOrPercent(SectionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, x):
        x = x.strip()
        if x.endswith("%"):
            return readPercents(x)
        return readLength(x)

class SAngle(SectionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, x):
        return readAngle(x)

class SNum(SectionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, x):
        return int(x)

class SNaturalNum(SNum):
    def validate(self, x):
        val = int(x)
        if val < 0:
            raise PresetError(f"A non-negative number expected, got '{x}'")
        return val

class SStr(SectionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, x):
        return str(x)

class SPlugin(SectionBase):
    seq: int = 0

    def __init__(self, pluginType, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pluginType = pluginType

    def validate(self, x):
        if x == "none":
            return None
        self.seq += 1

        pieces = str(x).rsplit(".", maxsplit=1)
        if len(pieces) != 2:
            raise RuntimeError(f"Invalid plugin specification '{x}'")
        moduleName, pluginName = pieces[0], pieces[1]
        plugin = self.loadFromFile(moduleName, pluginName) if moduleName.endswith(".py") \
                 else self.loadFromModule(moduleName, pluginName)
        if not issubclass(plugin, self.pluginType):
            raise RuntimeError(f"Invalid plugin type specified, {self.pluginType.__name__} expected")
        setattr(plugin, "__kikit_preset_repr", x)
        return plugin

    def loadFromFile(self, file, name):
        import importlib.util

        if not os.path.exists(file):
            raise RuntimeError(f"File {file} doesn't exist")
        spec = importlib.util.spec_from_file_location(
                f"kikit.user.SPlugin_{self.seq}",
                file)
        if spec is None:
            raise RuntimeError(f"Plugin module '{file}' doesn't exist")
        pluginModule = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pluginModule)
        return getattr(pluginModule, name)

    def loadFromModule(self, module, name):
        import importlib
        pluginModule = importlib.import_module(module)
        return getattr(pluginModule, name)

class SChoiceBase(SectionBase):
    def __init__(self, vals, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vals = vals

    def validate(self, s):
        if s not in self.vals:
            c = ", ".join(self.vals)
            raise PresetError(f"'{s}' is not allowed Use one of {c}.")
        return s

class SChoice(SChoiceBase):
    def __init__(self, vals, *args, **kwargs):
        super().__init__(vals, *args, **kwargs)

class SBool(SChoiceBase):
    def __init__(self, *args, **kwargs):
        super().__init__(["True", "False"], *args, **kwargs)

    def validate(self, s):
        if isinstance(s, bool):
            return s
        if isinstance(s, str):
            sl = str(s).lower()
            if sl in ["1", "true", "yes"]:
                return True
            if sl in ["0", "false", "no"]:
                return False
            raise PresetError(f"Uknown boolean value '{s}'")
        raise PresetError(f"Got {s}, expected boolean value")

class SHJustify(SChoiceBase):
    def __init__(self, *args, **kwargs):
        super().__init__(["left", "right", "center"], *args, **kwargs)

    def validate(self, s):
        choices = {
            "left": EDA_TEXT_HJUSTIFY_T.GR_TEXT_HJUSTIFY_LEFT,
            "right": EDA_TEXT_HJUSTIFY_T.GR_TEXT_HJUSTIFY_RIGHT,
            "center": EDA_TEXT_HJUSTIFY_T.GR_TEXT_HJUSTIFY_CENTER
        }
        if s in choices:
            return choices[s]
        raise PresetError(f"'{s}' is not valid justification value")

class SVJustify(SChoiceBase):
    def __init__(self, *args, **kwargs):
        super().__init__(["top", "bottom", "center"], *args, **kwargs)

    def validate(self, s):
        choices = {
            "top": EDA_TEXT_VJUSTIFY_T.GR_TEXT_VJUSTIFY_TOP,
            "center": EDA_TEXT_VJUSTIFY_T.GR_TEXT_VJUSTIFY_CENTER,
            "bottom": EDA_TEXT_VJUSTIFY_T.GR_TEXT_VJUSTIFY_BOTTOM
        }
        if s in choices:
            return choices[s]
        raise PresetError(f"'{s}' is not valid justification value")

class SLayer(SChoiceBase):
    def __init__(self, *args, **kwargs):
        super().__init__(
            [item.name.replace("Layer.", "").replace("_", ".")
                for item in Layer], *args, **kwargs)

    def validate(self, s):
        if isinstance(s, int) or s.isdigit():
            if int(s) in tuple(item.value for item in Layer):
                return Layer(int(s))
            raise PresetError(f"{s} is not a valid layer number")
        if isinstance(s, str):
            try:
                return Layer[s.replace(".", "_")]
            except Exception:
                pass
        raise PresetError(f"Got {s}, expected layer name or number")

class SList(SectionBase):
    def validate(self, x: str) -> Any:
        if isinstance(x, list):
            return [str(v).strip() for v in x]
        return [v.strip() for v in x.split(",")]

class SLayerList(SList):
    def __init__(self, isGuiRelevant, description, shortcuts={}):
        super().__init__(isGuiRelevant, description)
        self._shortcuts = shortcuts

    def validate(self, x: str) -> Any:
        if x in self._shortcuts:
            return self._shortcuts[x]
        return [self.readLayer(x) for x in super().validate(x)]

    def readLayer(self, s: str) -> Layer:
        if isinstance(s, int) or s.isdigit():
            if int(s) in tuple(item.value for item in Layer):
                return Layer(int(s))
            raise PresetError(f"{s} is not a valid layer number")
        if isinstance(s, str):
            try:
                return Layer[s.replace(".", "_")]
            except Exception:
                pass
        raise PresetError(f"Got {s}, expected layer name or number")

class SFootprintList(SList):
    def validate(self, x: str) -> Any:
        result: List[FootprintId] = []
        for v in super().validate(x):
            s = v.split(":", 1)
            if len(s) != 2:
                PresetError(f"'{v}' is not a valid footprint name in the form '<lib>:<footprint>'")
            result.append(FootprintId(s[0], s[1]))
        return result


def validateSection(name, sectionDefinition, section):
    try:
        for key, validator in sectionDefinition.items():
            if key not in section:
                continue
            section[key] = validator.validate(section[key])
    except Exception as e:
        raise PresetError(f"Error in section {name}: {e}")
    return section

def typeIn(values):
    return lambda section: section["type"] in values

def always():
    return lambda section: True

def never():
    return lambda section: False

LAYOUT_SECTION = {
    "type": SChoice(
        ["grid", "plugin"],
        always(),
        "布局类型"),
    "alternation": SChoice(
        ["none", "rows", "cols", "rowsCols"],
        typeIn(["grid", "plugin"]),
        "指定电路板旋转交替方式"),
    "hspace": SLength(
        always(),
        "指定电路板之间的水平间距"),
    "vspace": SLength(
        always(),
        "指定电路板之间的垂直间距"),
    "space": SLength(
        never(),
        "指定电路板之间的双向间距"),
    "hevendiff": SLength(
        always(),
        "偶数行电路板列之间的额外间距"),
    "vevendiff": SLength(
        always(),
        "偶数列电路板行之间的额外间距"),
    "hbackbone": SLength(
        typeIn(["grid", "plugin"]),
        "水平中框宽度（0 表示无中框）"),
    "vbackbone": SLength(
        typeIn(["grid", "plugin"]),
        "垂直中框宽度（0 表示无中框）"),
    "hboneskip": SNaturalNum(
        typeIn(["grid", "plugin"]),
        "每隔指定数量跳过水平中框"),
    "vboneskip": SNaturalNum(
        typeIn(["grid", "plugin"]),
        "每隔指定数量跳过垂直中框"),
    "hbonefirst": SNaturalNum(
        typeIn(["grid", "plugin"]),
        "指定要渲染的第一个水平中框"),
    "vbonefirst": SNaturalNum(
        typeIn(["grid", "plugin"]),
        "指定要渲染的第一个垂直中框"),
    "rotation": SAngle(
        always(),
        "放入拼板前旋转电路板"),
    "rows": SNaturalNum(
        typeIn(["grid", "plugin"]),
        "指定网格布局的行数"),
    "cols": SNaturalNum(
        typeIn(["grid", "plugin"]),
        "指定网格布局的列数"),
    "vbonecut": SBool(
        typeIn(["grid", "plugin"]),
        "在垂直中框中添加切口以便拆分"),
    "hbonecut": SBool(
        typeIn(["grid", "plugin"]),
        "在水平中框中添加切口以便拆分"),
    "renamenet": SStr(
        always(),
        "网络重命名模式"),
    "renameref": SStr(
        always(),
        "位号重命名模式"),
    "baketext": SBool(
        always(),
        "替换文本元素中的变量"
    ),
    "bakeref": SBool(
        always(),
        "在重命名前烘焙旧位号"
    ),
    "code": SPlugin(
        plugin.LayoutPlugin,
        typeIn(["plugin"]),
        "插件规范格式：模块名.插件名"),
    "arg": SStr(
        typeIn(["plugin"]),
        "布局插件的字符串参数")
}

def ppLayout(section):
    section = validateSection("layout", LAYOUT_SECTION, section)
    # The space parameter overrides hspace and vspace
    if "space" in section:
        section["hspace"] = section["vspace"] = section["space"]

SOURCE_SECTION = {
    "type": SChoice(
        ["auto", "rectangle", "annotation"],
        always(),
        "源类型"),
    "tolerance": SLength(
        typeIn(["auto", "annotation"]),
        "容差，按指定量扩大源区域"),
    "tlx": SLength(
        typeIn(["rectangle"]),
        "矩形的左上角 X"),
    "tly": SLength(
        typeIn(["rectangle"]),
        "矩形的左上角 Y"),
    "brx": SLength(
        typeIn(["rectangle"]),
        "矩形的右下角 X"),
    "bry": SLength(
        typeIn(["rectangle"]),
        "矩形的右下角 Y"),
    "ref": SStr(
        typeIn(["annotation"]),
        "指定 KiKit 标注符号的位号"),
    "layer": SLayer(
        typeIn(["annotation"]),
        "指定标注线的层（默认：Edge.Cuts）"),
    "stack": SChoice(
        ["inherit", "2layer", "4layer", "6layer"],
        always(),
        "指定拼板的层数")
}

def ppSource(section):
    section = validateSection("source", SOURCE_SECTION, section)

TABS_SECTION = {
    "type": SChoice(
        ["none", "fixed", "spacing", "full", "corner", "annotation", "plugin"],
        always(),
        "连接条类型"),
    "vwidth": SLength(
        typeIn(["fixed", "spacing", "plugin"]),
        "指定垂直连接条宽度"),
    "hwidth": SLength(
        typeIn(["fixed", "spacing", "plugin"]),
        "指定水平连接条宽度"),
    "width": SLength(
        typeIn(["corner", "plugin"]),
        "指定连接条宽度"),
    "mindistance": SLength(
        typeIn(["fixed", "plugin"]),
        "连接条之间的最小间距。如果连接条过多，将减少数量。"),
    "spacing": SLength(
        typeIn(["spacing", "plugin"]),
        "连接条的最大间距。"),
    "vcount": SNum(
        typeIn(["fixed", "plugin"]),
        "指定方向上的连接条数量。"),
    "hcount": SNum(
        typeIn(["fixed", "plugin"]),
        "指定方向上的连接条数量。"),
    "cutout": SLength(
        typeIn(["fixed", "full", "plugin"]),
        "切入框架的深度"),
    "patchcorners": SBool(
        typeIn(["fixed", "full", "plugin"]),
        "选择是否对全连接条应用角补丁"
    ),
    "tabfootprints": SFootprintList(
        typeIn(["annotation", "plugin"]),
        "指定用于连接条标注的自定义封装。"),
    "fillet": SLength(
        typeIn(["fixed", "spacing", "corner", "annotation", "plugin"]),
        "指定连接条圆角半径（实验性）"
    ),
    "code": SPlugin(
        plugin.TabsPlugin,
        typeIn(["plugin"]),
        "插件规范格式：模块名.插件名"),
    "arg": SStr(
        typeIn(["plugin"]),
        "布局插件的字符串参数")
}

def ppTabs(section):
    section = validateSection("tabs", TABS_SECTION, section)
    if "width" in section:
        section["vwidth"] = section["hwidth"] = section["width"]

CUTS_SECTION = {
    "type": SChoice(
        ["none", "mousebites", "vcuts", "layer", "plugin"],
        always(),
        "切割类型"),
    "drill": SLength(
        typeIn(["mousebites", "plugin"]),
        "钻孔直径"),
    "spacing": SLength(
        typeIn(["mousebites", "plugin"]),
        "孔间距"),
    "offset": SLength(
        typeIn(["mousebites", "vcuts", "plugin"]),
        "切割偏移量"),
    "prolong": SLength(
        typeIn(["mousebites", "layer", "plugin"]),
        "切向延长切割（用于切割铣削圆角）"),
    "clearance": SLength(
        typeIn(["vcuts", "plugin"]),
        "V-cut 周围的铜皮间距"),
    "cutcurves": SBool(
        typeIn(["vcuts", "plugin"]),
        "用直线切割近似曲线"),
    "linewidth": SLength(
        typeIn(["vcuts", "layer", "plugin"]),
        "绘制切割的线宽"),
    "textthickness": SLength(
        typeIn(["vcuts", "plugin"]),
        "文本粗度"),
    "textsize": SLength(
        typeIn(["vcuts", "plugin"]),
        "V-cut 文本大小"),
    "endprolongation": SLength(
        typeIn(["vcuts", "plugin"]),
        "V-cut 无文本端的延长量"),
    "textprolongation": SLength(
        typeIn(["vcuts", "plugin"]),
        "V-cut 文本侧的延长量"),
    "textoffset": SLength(
        typeIn(["vcuts", "plugin"]),
        "文本距 V-cut 的偏移"),
    "template": SStr(
        typeIn(["vcuts", "plugin"]),
        "V-cut 的文本模板"),
    "layer": SLayer(
        typeIn(["vcuts", "layer", "plugin"]),
        "指定绘图层"),
    "code": SPlugin(
        plugin.CutsPlugin,
        typeIn(["plugin"]),
        "插件规范格式：模块名.插件名"),
    "arg": SStr(
        typeIn(["plugin"]),
        "布局插件的字符串参数")
}

def ppCuts(section):
    section = validateSection("cuts", CUTS_SECTION, section)

FRAMING_SECTION = {
    "type": SChoice(
        ["none", "railstb", "railslr", "frame", "tightframe", "plugin"],
        always(),
        "框架类型"),
    "hspace": SLength(
        typeIn(["frame", "railslr", "tightframe", "plugin"]),
        "PCB 与框架之间的水平间距"),
    "vspace": SLength(
        typeIn(["frame", "railstb", "tightframe", "plugin"]),
        "PCB 与框架之间的垂直间距"),
    "space": SLength(
        never(),
        "框架/导轨与 PCB 之间的间距"),
    "width": SLength(
        typeIn(["frame", "railstb", "railslr", "tightframe", "plugin"]),
        "框架宽度"),
    "mintotalheight": SLength(
        typeIn(["frame", "railstb", "tightframe", "plugin"]),
        "拼板最小高度"
    ),
    "mintotalwidth": SLength(
        typeIn(["frame", "raillr", "tightframe", "plugin"]),
        "拼板最小宽度"
    ),
    "maxtotalheight": SLength(
        typeIn(["frame", "railstb", "tightframe", "plugin"]),
        "拼板最大高度"
    ),
    "maxtotalwidth": SLength(
        typeIn(["frame", "raillr", "tightframe", "plugin"]),
        "拼板最大宽度"
    ),
    "slotwidth": SLength(
        typeIn(["tightframe", "plugin"]),
        "铣削槽宽度"),
    "cuts": SChoice(
        ["none", "both", "v", "h"],
        typeIn(["frame", "plugin"]),
        "在框架角部添加切口"),
    "chamferwidth": SLength(
        typeIn(["tightframe", "frame", "railslr", "railstb", "plugin"]),
        "在拼板的四个角添加倒角。指定倒角宽度。"),
    "chamferheight": SLength(
        typeIn(["tightframe", "frame", "railslr", "railstb", "plugin"]),
        "在拼板的四个角添加倒角。指定倒角高度。"),
    "chamfer": SLength(
        never(),
        "在拼板的四个角添加倒角。指定 45° 倒角。"),
    "fillet": SLength(
        typeIn(["tightframe", "frame", "railslr", "railstb", "plugin"]),
        "在拼板的四个角添加圆角。指定圆角半径。"),
    "code": SPlugin(
        plugin.FramingPlugin,
        typeIn(["plugin"]),
        "插件规范格式：模块名.插件名"),
    "arg": SStr(
        typeIn(["plugin"]),
        "布局插件的字符串参数")
}

def ppFraming(section):
    section = validateSection("framing", FRAMING_SECTION, section)
    # The space parameter overrides hspace and vspace
    if "space" in section:
        section["hspace"] = section["vspace"] = section["space"]
    if "chamfer" in section:
        section["chamferwidth"] = section["chamferheight"] = section["chamfer"]

TOOLING_SECTION = {
    "type": SChoice(
        ["none", "3hole", "4hole", "plugin"],
        always(),
        "工具孔类型"),
    "hoffset": SLength(
        typeIn(["3hole", "4hole", "plugin"]),
        "孔的水平偏移"),
    "voffset": SLength(
        typeIn(["3hole", "4hole", "plugin"]),
        "孔的垂直偏移"),
    "size": SLength(
        typeIn(["3hole", "4hole", "plugin"]),
        "孔径"),
    "paste": SBool(
        typeIn(["3hole", "4hole", "plugin"]),
        "在钢网层包含孔"),
    "soldermaskmargin": SLength(
        typeIn(["3hole", "4hole", "plugin"]),
        "阻焊扩展/边距"),
    "code": SPlugin(
        plugin.ToolingPlugin,
        typeIn(["plugin"]),
        "插件规范格式：模块名.插件名"),
    "arg": SStr(
        typeIn(["plugin"]),
        "布局插件的字符串参数")
}

def ppTooling(section):
    section = validateSection("tooling", TOOLING_SECTION, section)

FIDUCIALS_SECTION = {
    "type": SChoice(
        ["none", "3fid", "4fid", "plugin"],
        always(),
        "基准点类型"),
    "hoffset": SLength(
        typeIn(["3fid", "4fid", "plugin"]),
        "基准点的水平偏移"),
    "voffset": SLength(
        typeIn(["3fid", "4fid", "plugin"]),
        "基准点的垂直偏移"),
    "coppersize": SLength(
        typeIn(["3fid", "4fid", "plugin"]),
        "铜皮直径"),
    "opening": SLength(
        typeIn(["3fid", "4fid", "plugin"]),
        "开窗直径"),
    "paste": SBool(
        typeIn(["3fid", "4fid", "plugin"]),
        "在钢网层包含基准点"),
    "code": SPlugin(
        plugin.FiducialsPlugin,
        typeIn(["plugin"]),
        "插件规范格式：模块名.插件名"),
    "arg": SStr(
        typeIn(["plugin"]),
        "布局插件的字符串参数")
}

def ppFiducials(section):
    section = validateSection("fiducials", FIDUCIALS_SECTION, section)

TEXT_SECTION = {
    "type": SChoice(
        ["none", "simple"],
        always(),
        "文本类型"),
    "hoffset": SLength(
        typeIn(["simple"]),
        "文本距锚点的水平偏移"),
    "voffset": SLength(
        typeIn(["simple"]),
        "文本距锚点的垂直偏移"),
    "width": SLength(
        typeIn(["simple"]),
        "字符宽度"),
    "height": SLength(
        typeIn(["simple"]),
        "字符高度"),
    "thickness": SLength(
        typeIn(["simple"]),
        "字符粗度"),
    "hjustify": SHJustify(
        typeIn(["simple"]),
        "文本水平对齐"),
    "vjustify": SVJustify(
        typeIn(["simple"]),
        "文本垂直对齐"),
    "layer": SLayer(
        typeIn(["simple"]),
        "文本层"),
    "orientation": SAngle(
        typeIn(["simple"]),
        "文本方向"),
    "text": SStr(
        typeIn(["simple"]),
        "要渲染的文本"),
    "anchor": SChoice(
        ANCHORS,
        typeIn(["simple"]),
        "定位文本的锚点"),
    "plugin": SPlugin(
        plugin.TextVariablePlugin,
        typeIn(["simple"]),
        "额外文本变量的插件")
}

def ppText(section):
    section = validateSection("text", TEXT_SECTION, section)

COPPERFILL_SECTION = {
    "type": SChoice(
        ["none", "solid", "hatched", "hex"],
        always(),
        "用铜皮填充非电路板区域"),
    "clearance": SLength(
        typeIn(["solid", "hatched", "hex"]),
        "填充与电路板之间的间距"),
    "edgeclearance": SLength(
        typeIn(["solid", "hatched", "hex"]),
        "填充与电路板边缘之间的间距"),
    "layers": SLayerList(
        typeIn(["solid", "hatched", "hex"]),
        "指定要填充铜皮的层",
        {
            "all": Layer.allCu()
        }),
    "width": SLength(
        typeIn(["hatched"]),
        "网纹线宽"),
    "spacing": SLength(
        typeIn(["hatched", "hex"]),
        "网纹线或六边形的间距"),
    "orientation": SAngle(
        typeIn(["hatched"]),
        "线条方向"),
    "diameter": SLength(
        typeIn(["hex"]),
        "六边形直径"
    ),
    "threshold": SPercent(
        typeIn(["hex"]),
        "移除小于阈值的碎片"
    )
}

def ppCopper(section):
    section = validateSection("copperfill", COPPERFILL_SECTION, section)

POST_SECTION = {
    "type": SChoice(
        ["auto"],
        never(),
        "后处理类型"),
    "copperfill": SBool(
        always(),
        "已弃用，请改用 copperfill 配置段。用铜皮填充拼板的未使用区域"),
    "millradius": SLength(
        always(),
        "模拟铣削操作"),
    "millradiusouter": SLength(
        always(),
        "仅在电路板外周边模拟铣削操作"),
    "reconstructarcs": SBool(
        always(),
        "尝试重建圆弧"),
    "refillzones": SBool(
        always(),
        "重新填充拼板中的所有区域"),
    "script": SStr(
        always(),
        "指定自定义后处理脚本路径"),
    "scriptarg": SStr(
        always(),
        "后处理脚本的字符串参数"),
    "origin": SChoice(
        ANCHORS + [""],
        always(),
        "放置辅助原点"),
    "dimensions": SBool(
        always(),
        "在完成的拼板上添加尺寸标注"
    ),
    "edgewidth": SLength(
        always(),
        "指定拼板 Edge.Cuts 的线宽"
    )
}

def ppPost(section):
    section = validateSection("post", POST_SECTION, section)

PAGE_SECTION = {
    "type": SChoice(
        PAPERS,
        always(),
        "纸张尺寸"),
    "anchor": SChoice(
        ANCHORS,
        always(),
        "在页面上定位拼板的锚点"),
    "posx": SLengthOrPercent(
        always(),
        "拼板的 X 位置。长度或页面宽度的百分比。"),
    "posy": SLengthOrPercent(
        always(),
        "拼板的 Y 位置。长度或页面高度的百分比。"),
    "width": SLength(
        typeIn(["user"]),
        "自定义纸张宽度"),
    "height": SLength(
        typeIn(["user"]),
        "自定义纸张高度"),
}

def ppPage(section):
    section = validateSection("page", PAGE_SECTION, section)

DEBUG_SECTION = {
    "type": SChoice(
        ["none"],
        never(),
        ""),
    "drawPartitionLines": SBool(
        always(),
        "绘制分割线"),
    "drawBackboneLines": SBool(
        always(),
        "绘制中框线"),
    "drawboxes": SBool(
        always(),
        "绘制电路板边界框"),
    "trace": SBool(
        always(),
        "打印堆栈跟踪"),
    "drawtabfail": SBool(
        always(),
        "可视化连接条构建失败"
    ),
    "deterministic": SBool(
        always(),
        "使 KiCAD ID 确定性生成"),
    "drawTabFillet": SBool(
        always(),
        "绘制正向/反向连接条和原始框架几何用于圆角调试")
}

def ppDebug(section):
    section = validateSection("debug", DEBUG_SECTION, section)

availableSections = {
    "Layout": LAYOUT_SECTION,
    "Source": SOURCE_SECTION,
    "Tabs": TABS_SECTION,
    "Cuts": CUTS_SECTION,
    "Framing": FRAMING_SECTION,
    "Tooling": TOOLING_SECTION,
    "Fiducials": FIDUCIALS_SECTION,
    "Text": TEXT_SECTION,
    "Text2": TEXT_SECTION,
    "Text3": TEXT_SECTION,
    "Text4": TEXT_SECTION,
    "Copperfill": COPPERFILL_SECTION,
    "Page": PAGE_SECTION,
    "Post": POST_SECTION,
    "Debug": DEBUG_SECTION,
}
