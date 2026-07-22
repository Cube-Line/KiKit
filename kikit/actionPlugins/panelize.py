import time
import traceback
from kikit.defs import EDA_TEXT_HJUSTIFY_T, EDA_TEXT_VJUSTIFY_T
import pcbnew
from kikit.panelize_ui_impl import loadPresetChain, obtainPreset, mergePresets
from kikit import panelize_ui
from kikit.panelize import NonFatalErrors, appendItem
from kikit.common import PKG_BASE, findBoardBoundingBox, fromMm
from .common import initDialog, destroyDialog
import kikit.panelize_ui_sections
import wx
import json
import tempfile
import shutil
import os
from threading import Thread
from itertools import chain

PLATFORMS = ["Linux/MacOS", "Windows"]

PRESET_STATE_PATH = os.path.expanduser("~/.config/kikit/panelize_state.json")

SECTION_DISPLAY = {
    "Input": "输入",
    "Output": "输出",
    "Layout": "布局",
    "Source": "源",
    "Tabs": "连接条",
    "Cuts": "切割",
    "Framing": "框架",
    "Tooling": "工具孔",
    "Fiducials": "基准点",
    "Text": "文本",
    "Text2": "文本2",
    "Text3": "文本3",
    "Text4": "文本4",
    "Copperfill": "铜填充",
    "Page": "页面",
    "Post": "后处理",
    "Debug": "调试",
}

PARAM_DISPLAY = {
    "Input file": "输入文件",
    "Output file": "输出文件",
    "type": "类型",
    "alternation": "交替方式",
    "hspace": "水平间距",
    "vspace": "垂直间距",
    "space": "间距",
    "hevendiff": "偶数行额外间距",
    "vevendiff": "偶数列额外间距",
    "hbackbone": "水平中框",
    "vbackbone": "垂直中框",
    "hboneskip": "水平中框跳过",
    "vboneskip": "垂直中框跳过",
    "hbonefirst": "首个水平中框",
    "vbonefirst": "首个垂直中框",
    "rotation": "旋转",
    "rows": "行数",
    "cols": "列数",
    "vbonecut": "垂直中框切口",
    "hbonecut": "水平中框切口",
    "renamenet": "网络重命名",
    "renameref": "位号重命名",
    "baketext": "烘焙文本",
    "bakeref": "烘焙旧位号",
    "code": "插件代码",
    "arg": "插件参数",
    "tolerance": "容差",
    "tlx": "左上角 X",
    "tly": "左上角 Y",
    "brx": "右下角 X",
    "bry": "右下角 Y",
    "ref": "参考位号",
    "layer": "层",
    "stack": "层叠",
    "vwidth": "垂直宽度",
    "hwidth": "水平宽度",
    "width": "宽度",
    "mindistance": "最小间距",
    "spacing": "间距",
    "vcount": "垂直数量",
    "hcount": "水平数量",
    "cutout": "切出深度",
    "patchcorners": "角补丁",
    "tabfootprints": "连接条封装",
    "fillet": "圆角",
    "drill": "钻孔直径",
    "offset": "偏移",
    "prolong": "延长",
    "clearance": "间距",
    "cutcurves": "切割曲线",
    "linewidth": "线宽",
    "textthickness": "文本粗度",
    "textsize": "文本大小",
    "endprolongation": "末端延长",
    "textprolongation": "文本侧延长",
    "textoffset": "文本偏移",
    "template": "模板",
    "hoffset": "水平偏移",
    "voffset": "垂直偏移",
    "size": "尺寸",
    "paste": "钢网层",
    "soldermaskmargin": "阻焊边距",
    "coppersize": "铜皮尺寸",
    "opening": "开窗尺寸",
    "hjustify": "水平对齐",
    "vjustify": "垂直对齐",
    "orientation": "方向",
    "text": "文本",
    "anchor": "锚点",
    "plugin": "插件",
    "edgeclearance": "边缘间距",
    "diameter": "直径",
    "threshold": "阈值",
    "copperfill": "铜填充",
    "millradius": "铣削半径",
    "millradiusouter": "外部铣削半径",
    "reconstructarcs": "重建圆弧",
    "refillzones": "重新填充区域",
    "script": "脚本",
    "scriptarg": "脚本参数",
    "origin": "原点",
    "dimensions": "尺寸标注",
    "edgewidth": "边缘线宽",
    "posx": "X 位置",
    "posy": "Y 位置",
    "height": "高度",
    "drawPartitionLines": "绘制分割线",
    "drawBackboneLines": "绘制中框线",
    "drawboxes": "绘制边界框",
    "trace": "跟踪",
    "drawtabfail": "Tab 构建失败可视化",
    "deterministic": "确定性 ID",
    "drawTabFillet": "绘制圆角调试几何",
    "slotwidth": "槽宽",
    "cuts": "切口",
    "chamferwidth": "倒角宽度",
    "chamferheight": "倒角高度",
    "chamfer": "倒角",
}

class ExceptionThread(Thread):
    def run(self):
        self.exception = None
        try:
            super().run()
        except Exception as e:
            self.exception = e
            self.traceback = traceback.format_exc()

def replaceExt(file, ext):
    return os.path.splitext(file)[0] + ext

def pcbnewPythonPath():
    return os.path.dirname(pcbnew.__file__)

def presetDifferential(source, target):
    result = {}
    for sectionName, section in target.items():
        if sectionName not in source:
            result[sectionName] = section
            continue
        updateKeys = {}
        sourceSection = source[sectionName]
        for key, value in section.items():
            if key not in sourceSection or str(sourceSection[key]).lower() != str(value).lower():
                updateKeys[key] = value
        if len(updateKeys) > 0:
            result[sectionName] = updateKeys
    return result


def transplateBoard(source, target, update=lambda x: None):
    CLEAR_MSG = "正在清除旧电路板"
    RENDER_MSG = "正在渲染新电路板"

    target.ClearProject()
    target.DeleteAllFootprints()

    items = chain(
        list(target.GetDrawings()),
        list(target.GetFootprints()),
        list(target.GetTracks()),
        list(target.Zones()))
    for x in items:
        update(CLEAR_MSG)
        target.Remove(x)

    for x in list(target.GetNetInfo().NetsByNetcode().values()):
        update(CLEAR_MSG)
        target.Remove(x)

    update(RENDER_MSG)
    target.SetProperties(source.GetProperties())
    update(RENDER_MSG)
    target.SetPageSettings(source.GetPageSettings())
    update(RENDER_MSG)
    target.SetTitleBlock(source.GetTitleBlock())
    for x in source.GetDrawings():
        update(RENDER_MSG)
        appendItem(target, x)
    for x in source.GetFootprints():
        update(RENDER_MSG)
        appendItem(target, x)
    for x in source.GetTracks():
        update(RENDER_MSG)
        appendItem(target, x)
    for x in source.Zones():
        update(RENDER_MSG)
        appendItem(target, x)

    update(RENDER_MSG)
    d = target.GetDesignSettings()
    d.CloneFrom(source.GetDesignSettings())
    target.SetEnabledLayers(source.GetEnabledLayers())



def drawTemporaryNotification(board, sourceFilename):
    try:
        bbox = findBoardBoundingBox(board)
    except Exception:
        # If the output is empty...
        bbox = pcbnew.BOX2I(pcbnew.VECTOR2I(0, 0), pcbnew.VECTOR2I(0, 0))

    lset = board.GetEnabledLayers()
    lset.AddLayer(pcbnew.Margin)
    board.SetEnabledLayers(lset)

    text = pcbnew.PCB_TEXT(board)
    text.SetLayer(pcbnew.Margin)
    text.SetText(f"仅预览。拼板已保存至 {sourceFilename}")
    text.SetPosition(pcbnew.VECTOR2I(bbox.GetX() + bbox.GetWidth() // 2, bbox.GetY() + bbox.GetHeight()) + pcbnew.VECTOR2I(0, fromMm(2)))
    text.SetTextThickness(fromMm(0.4))
    text.SetTextSize(pcbnew.VECTOR2I(fromMm(3), fromMm(3)))
    text.SetVertJustify(EDA_TEXT_VJUSTIFY_T.GR_TEXT_VJUSTIFY_TOP)
    text.SetHorizJustify(EDA_TEXT_HJUSTIFY_T.GR_TEXT_HJUSTIFY_CENTER)
    board.Add(text)


class SFile():
    def __init__(self, nameFilter):
        self.nameFilter = nameFilter
        self.description = ""
        self.isGuiRelevant = lambda section: True

    def validate(self, x):
        return x

class SInputFile(SFile):
    def __init__(self, nameFilter):
        super().__init__(nameFilter)
        self.description = "输入文件"
        self.isGuiRelevant = lambda section: True

class SOuputFile(SFile):
    def __init__(self, nameFilter):
        super().__init__(nameFilter)
        self.description = "输出文件"
        self.isGuiRelevant = lambda section: True

class ParameterWidgetBase:
    def __init__(self, parent, name, parameter):
        self.name = name
        self.parameter = parameter
        displayName = PARAM_DISPLAY.get(name, name)
        self.label = wx.StaticText(parent,
                                   label=displayName,
                                   size=wx.Size(150, -1),
                                   style=wx.ALIGN_RIGHT)
        self.label.SetToolTip(parameter.description)
        self.fresh = True

    def showIfRelevant(self, preset):
        relevant = self.parameter.isGuiRelevant(preset)
        if self.fresh or self.label.IsShown() != relevant:
            self.label.Show(relevant)
            self.widget.Show(relevant)
            self.fresh = False
            return True
        return False


class TextWidget(ParameterWidgetBase):
    def __init__(self, parent, name, parameter, onChange):
        super().__init__(parent, name, parameter)
        self.widget = wx.TextCtrl(
            parent, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0)
        self.widget.Bind(wx.EVT_TEXT, onChange)

    def setValue(self, value):
        self.widget.ChangeValue(str(value))

    def getValue(self):
        return self.widget.GetValue()


class ChoiceWidget(ParameterWidgetBase):
    def __init__(self, parent, name, parameter, onChange):
        super().__init__(parent, name, parameter)
        self.widget = wx.Choice(parent, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
                                parameter.vals, 0)
        self.widget.SetSelection(0)
        self.widget.Bind(wx.EVT_CHOICE, onChange)

    def setValue(self, value):
        for i, option in enumerate(self.parameter.vals):
            if option.lower() == str(value).lower():
                self.widget.SetSelection(i)
                break

    def getValue(self):
        return self.parameter.vals[self.widget.GetSelection()]


class InputFileWidget(ParameterWidgetBase):
    def __init__(self, parent, name, parameter, onChange):
        super().__init__(parent, name, parameter)
        self.widget = wx.FilePickerCtrl(
            parent, wx.ID_ANY, wx.EmptyString, name,
            parameter.nameFilter, wx.DefaultPosition, wx.DefaultSize,
            wx.FLP_OPEN | wx.FLP_FILE_MUST_EXIST)
        self.widget.Bind(wx.EVT_FILEPICKER_CHANGED, onChange)

    def getValue(self):
        return self.widget.GetPath()

    def setValue(self, value):
        self.widget.SetPath(value)

class OutputFileWidget(ParameterWidgetBase):
    def __init__(self, parent, name, parameter, onChange):
        super().__init__(parent, name, parameter)
        self.widget = wx.FilePickerCtrl(
            parent, wx.ID_ANY, wx.EmptyString, name,
            parameter.nameFilter, wx.DefaultPosition, wx.DefaultSize,
            wx.FLP_SAVE | wx.FLP_OVERWRITE_PROMPT)
        self.widget.Bind(wx.EVT_FILEPICKER_CHANGED, onChange)

    def getValue(self):
        return self.widget.GetPath()

    def setValue(self, value):
        self.widget.SetPath(value)

def obtainParameterWidget(parameter):
    if isinstance(parameter, kikit.panelize_ui_sections.SChoiceBase):
        return ChoiceWidget
    if isinstance(parameter, SInputFile):
        return InputFileWidget
    if isinstance(parameter, SOuputFile):
        return OutputFileWidget
    return TextWidget


class SectionGui():
    def __init__(self, parent, name, section, onResize, onChange):
        self.name = name
        self.parent = parent
        displayName = SECTION_DISPLAY.get(name, name)
        self.container = wx.CollapsiblePane(
            parent, wx.ID_ANY, displayName, wx.DefaultPosition, wx.DefaultSize,
            wx.CP_DEFAULT_STYLE)
        self.container.Collapse(False)

        self.container.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, onResize)
        self.container.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        self.container.GetPane().SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        self.itemGrid = wx.FlexGridSizer(0, 2, 2, 2)
        self.itemGrid.AddGrowableCol(1)
        self.itemGrid.SetFlexibleDirection(wx.BOTH)
        self.itemGrid.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_ALL)

        self.items = {
            name: obtainParameterWidget(param)(
                self.container.GetPane(), name, param, onChange)
            for name, param in section.items()
        }
        for widget in self.items.values():
            self.itemGrid.Add(widget.label, 0,  wx.ALL |
                              wx.ALIGN_CENTER_VERTICAL | wx.EXPAND | wx.RIGHT, 5)
            self.itemGrid.Add(widget.widget, 0,  wx.ALL |
                              wx.ALIGN_CENTER_VERTICAL | wx.EXPAND | wx.RIGHT, 5)

        self.container.GetPane().SetSizer(self.itemGrid)

    def populateInitialValue(self, values):
        for name, widget in self.items.items():
            if name not in values:
                continue
            widget.setValue(values[name])

    def collectPreset(self):
        return {name: widget.getValue() for name, widget in self.items.items()}

    def showOnlyRelevantFields(self):
        changed = False
        preset = self.collectPreset()
        for name, widget in self.items.items():
            if name not in preset:
                continue
            ch = widget.showIfRelevant(preset)
            changed = changed or ch
        if changed:
            # This is hacky, but it is the only reliable way to force collapsible
            # pane to correctly adjust its size
            self.container.Collapse()
            self.container.Expand()
        return changed

    def collectReleventPreset(self):
        preset = self.collectPreset()
        return {name: widget.getValue()
                for name, widget in self.items.items()
                if widget.parameter.isGuiRelevant(preset)}


class PanelizeDialog(wx.Dialog):
    def __init__(self, parent=None, board=None, preset=None):
        wx.Dialog.__init__(
            self, parent, title=f'拼板 (版本 {kikit.__version__})',
            style=wx.DEFAULT_DIALOG_STYLE)
        self.Bind(wx.EVT_CLOSE, self.OnClose, id=self.GetId())

        self.board = board
        self.dirty = False
        self.progressDlg = None
        self.lastPulse = time.time()

        topMostBoxSizer = wx.BoxSizer(wx.VERTICAL)

        middleSizer = wx.BoxSizer(wx.HORIZONTAL)

        maxDisplayArea = wx.Display().GetClientArea()
        self.maxDialogSize = wx.Size(
            min(500, maxDisplayArea.Width),
            min(800, maxDisplayArea.Height - 200))

        self.scrollWindow = wx.ScrolledWindow(
            self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.VSCROLL)
        self.scrollWindow.SetSizeHints(self.maxDialogSize, wx.Size(self.maxDialogSize.width, -1))
        self.scrollWindow.SetScrollRate(5, 5)
        self._buildSections(self.scrollWindow)
        middleSizer.Add(self.scrollWindow, 0, wx.EXPAND | wx.ALL, 5)

        self._buildOutputSections(middleSizer)

        topMostBoxSizer.Add(middleSizer, 1, wx.EXPAND | wx.ALL, 5)
        self._buildBottomButtons(topMostBoxSizer)

        self.SetSizer(topMostBoxSizer)
        self.populateInitialValue(preset)
        self.buildOutputSections()
        self.showOnlyRelevantFields()
        self.OnResize()

        if os.name != "nt":
            self.SetBackgroundColour( wx.SystemSettings.GetColour(wx.SYS_COLOUR_BACKGROUND))


    def _buildOutputSections(self, sizer):
        internalSizer = wx.BoxSizer(wx.VERTICAL)

        cliLabel = wx.StaticText(self, label="KiKit CLI 命令：",
                                 size=wx.DefaultSize, style=wx.ALIGN_LEFT)
        internalSizer.Add(cliLabel, 0, wx.EXPAND | wx.ALL, 2)

        self.platformSelector = wx.Choice(self, wx.ID_ANY, wx.DefaultPosition,
            wx.DefaultSize, PLATFORMS, 0)
        if os.name == "nt":
            self.platformSelector.SetSelection(PLATFORMS.index("Windows"))
        else:
            self.platformSelector.SetSelection(0) # Choose posix by default
        self.platformSelector.Bind(wx.EVT_CHOICE, lambda evt: self.buildOutputSections())
        internalSizer.Add(self.platformSelector, 0, wx.EXPAND | wx.ALL, 2 )

        self.kikitCmdWidget = wx.TextCtrl(
            self, wx.ID_ANY, "KiKit 命令", wx.DefaultPosition, wx.DefaultSize,
            wx.TE_MULTILINE | wx.TE_READONLY)
        self.kikitCmdWidget.SetSizeHints(
            wx.Size(self.maxDialogSize.width,
                    self.maxDialogSize.height // 2),
            wx.Size(self.maxDialogSize.width, -1))
        cmdFont = self.kikitCmdWidget.GetFont()
        cmdFont.SetFamily(wx.FONTFAMILY_TELETYPE)
        self.kikitCmdWidget.SetFont(cmdFont)
        internalSizer.Add(self.kikitCmdWidget, 0, wx.EXPAND | wx.ALL, 2)

        jsonLabel = wx.StaticText(self, label="KiKit JSON 配置（仅包含已变更的键）：",
                                  size=wx.DefaultSize, style=wx.ALIGN_LEFT)
        internalSizer.Add(jsonLabel, 0, wx.EXPAND | wx.ALL, 2)

        self.kikitJsonWidget = wx.TextCtrl(
            self, wx.ID_ANY, "KiKit JSON", wx.DefaultPosition, wx.DefaultSize,
            wx.TE_MULTILINE | wx.TE_READONLY)
        self.kikitJsonWidget.SetSizeHints(
            wx.Size(self.maxDialogSize.width,
                    self.maxDialogSize.height // 2),
            wx.Size(self.maxDialogSize.width, -1))
        cmdFont = self.kikitJsonWidget.GetFont()
        cmdFont.SetFamily(wx.FONTFAMILY_TELETYPE)
        self.kikitJsonWidget.SetFont(cmdFont)
        internalSizer.Add(self.kikitJsonWidget, 0, wx.EXPAND | wx.ALL, 2)

        ieButtonsSizer = wx.BoxSizer(wx.HORIZONTAL)
        ieButtonsSizer.Add((0, 0), 1, wx.EXPAND, 5)

        self.importButton = wx.Button(self, wx.ID_ANY, u"导入 JSON 配置",
            wx.DefaultPosition, wx.DefaultSize, 0)
        try:
            self.importButton.SetBitmap(wx.BitmapBundle(wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN)))
        except:
            self.importButton.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN))
        ieButtonsSizer.Add(self.importButton, 0, wx.ALL, 5)
        self.importButton.Bind(wx.EVT_BUTTON, self.onImport)

        self.exportButton = wx.Button(self, wx.ID_ANY, u"导出 JSON 配置",
            wx.DefaultPosition, wx.DefaultSize, 0)
        try:
            self.exportButton.SetBitmap(wx.BitmapBundle(wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE)))
        except:
            self.exportButton.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE))
        ieButtonsSizer.Add(self.exportButton, 0, wx.ALL, 5)
        self.exportButton.Bind(wx.EVT_BUTTON, self.onExport)

        internalSizer.Add(ieButtonsSizer, 1, wx.EXPAND, 5)

        sizer.Add(internalSizer, 0, wx.EXPAND | wx.ALL, 2)

    def _buildSections(self, parentWindow):
        sectionsSizer = wx.BoxSizer(wx.VERTICAL)

        sections = {
            "Input": {
                "Input file": SInputFile("*.kicad_pcb")
            },
            "Output": {
                "Output file": SOuputFile("*.kicad_pcb")
            }
        }
        sections.update(kikit.panelize_ui_sections.availableSections)

        self.sections = {
            name: SectionGui(parentWindow, name, section,
                             lambda evt: self.OnResize(), lambda evt: self.OnChange())
            for name, section in sections.items()
        }
        for section in self.sections.values():
            sectionsSizer.Add(section.container, 0, wx.ALL | wx.EXPAND, 5)

        parentWindow.SetSizer(sectionsSizer)

    def _buildBottomButtons(self, parentSizer):
        button_box = wx.BoxSizer(wx.HORIZONTAL)
        closeButton = wx.Button(self, label='关闭')
        self.Bind(wx.EVT_BUTTON, self.OnClose, id=closeButton.GetId())
        button_box.Add(closeButton, 1, wx.RIGHT, 10)
        self.okButton = wx.Button(self, label='拼板')
        self.Bind(wx.EVT_BUTTON, self.OnPanelize, id=self.okButton.GetId())
        button_box.Add(self.okButton, 1)

        parentSizer.Add(button_box, 0, wx.ALIGN_RIGHT |
                        wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

    def OnResize(self):
        self.scrollWindow.GetSizer().Layout()
        self.scrollWindow.Fit()
        self.scrollWindow.FitInside()
        self.GetSizer().Layout()
        self.Fit()

    def OnClose(self, event):
        self.EndModal(0)

    def _updatePanelizationProgress(self, message, force=False):
        self.phase = message
        now = time.time()

        if now - self.lastPulse > 1 / 50 or force:
            self.lastPulse = now
            if self.progressDlg is not None:
                self.progressDlg.Pulse(newmsg=f"正在运行 KiKit：{self.phase}")
            if force:
                self.progressDlg.Refresh()
            wx.GetApp().Yield()

    def _panelizationRoutine(self, tempdir, input, panelFile, preset):
        panelize_ui.doPanelization(input, panelFile, preset)

        # KiCAD 6 does something strange here, so we will load an empty
        # file if we read it directly, but we can always make a copy and
        # read that. Copying a file can be lengthy, so we will copy the
        # file in a thread.
        copyPanelName = os.path.join(tempdir, "panel-copy.kicad_pcb")
        shutil.copy(panelFile, copyPanelName)
        try:
            shutil.copy(replaceExt(panelFile, ".kicad_pro"), replaceExt(copyPanelName, "kicad_pro"))
            shutil.copy(replaceExt(panelFile, ".kicad_prl"), replaceExt(copyPanelName, "kicad_prl"))
        except FileNotFoundError:
            # We don't care if we didn't manage to copy the files
            pass
        self.temporary_panel = pcbnew.LoadBoard(copyPanelName)

    def _pulseWhilePcbnewRefresh(self):
        while not self.refreshDone:
            time.sleep(1/50)
            self._updatePanelizationProgress("Pcbnew 正在更新预览")


    def OnPanelize(self, event):
        with tempfile.TemporaryDirectory(prefix="kikit") as dirname:
            try:
                self.progressDlg = wx.ProgressDialog(
                    "正在运行 KiKit", "正在运行 KiKit：",
                    parent=self)
                self._updatePanelizationProgress("正在启动")
                self.progressDlg.Show()

                args = self.kikitArgs()
                preset = obtainPreset([], **args)
                input = self.sections["Input"].items["Input file"].getValue()
                if len(input) == 0:
                    dlg = wx.MessageDialog(
                        None, "未指定输入文件", "错误", wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()
                    return
                panelFile = self.sections["Output"].items["Output file"].getValue()
                if len(panelFile) == 0:
                    dlg = wx.MessageDialog(
                        None, "未指定输出文件", "错误", wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()
                    return
                if os.path.realpath(input) == os.path.realpath(pcbnew.GetBoard().GetFileName()):
                    dlg = wx.MessageDialog(
                        None,
                        f"文件 {input} 与当前打开的电路板相同，无法继续。\n\n" + \
                         "请在没有电路板打开时运行拼板工具。",
                        "错误", wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()
                    return

                # We run as much as possible in a separate thread to not stall
                # the UI...
                thread = ExceptionThread(target=self._panelizationRoutine,
                                         args=(dirname, input, panelFile, preset))
                thread.daemon = True
                thread.start()
                while True:
                    self._updatePanelizationProgress("拼板中")
                    thread.join(timeout=1 / 50)
                    if not thread.is_alive():
                        break
                if thread.exception:
                    raise thread.exception

                # ...however, transplate board and pcbnew.Refresh has to happen
                # in the main thread
                transplateBoard(self.temporary_panel, self.board, self._updatePanelizationProgress)
                drawTemporaryNotification(self.board, panelFile)
                self._updatePanelizationProgress("Pcbnew 即将刷新拼板，界面可能会卡顿", force=True)
                pcbnew.Refresh()
                self._updatePanelizationProgress("完成", force=True)
                self.dirty = True
            except Exception as e:
                dlg = wx.MessageDialog(
                    None, f"无法执行：\n\n{e}", "错误", wx.OK)
                dlg.ShowModal()
                dlg.Destroy()
            finally:
                self.progressDlg.Hide()
                self.progressDlg.Destroy()
                self.progressDlg = None

    def populateInitialValue(self, initialPreset=None):
        preset = loadPresetChain([":default"])
        if initialPreset is not None:
            mergePresets(preset, initialPreset)
        for name, section in self.sections.items():
            if name.lower() not in preset:
                continue
            section.populateInitialValue(preset[name.lower()])
        self.buildOutputSections()

    def showOnlyRelevantFields(self):
        changed = False
        for section in self.sections.values():
            sectionChanged = section.showOnlyRelevantFields()
            changed = changed or sectionChanged
        return changed

    def collectPreset(self, includeInput=False):
        preset = loadPresetChain([":default"])
        if includeInput:
            preset["input"] = {}
            preset["output"] = {}
        for name, section in self.sections.items():
            if name.lower() not in preset:
                continue
            preset[name.lower()].update(section.collectPreset())
        return preset

    def collectReleventPreset(self):
        preset = {}
        for name, section in self.sections.items():
            preset[name.lower()] = section.collectReleventPreset()
        del preset["input"]
        del preset["output"]
        return preset

    def OnChange(self):
        if self.showOnlyRelevantFields():
            self.OnResize()
        self.buildOutputSections()

    def buildOutputSections(self):
        defaultPreset = loadPresetChain([":default"])
        preset = self.collectReleventPreset()
        presetUpdates = presetDifferential(defaultPreset, preset)

        self.kikitJsonWidget.ChangeValue(json.dumps(presetUpdates, indent=4))

        command = self._buildUnixCommand(presetUpdates) \
                    if self.platformSelector.GetSelection() == 0 \
                    else self._buildWindowsCommand(presetUpdates)
        self.kikitCmdWidget.ChangeValue(command)

    def _buildUnixCommand(self, presetUpdates):
        kikitCommand = "kikit panelize \\\n"
        for section, values in presetUpdates.items():
            if len(values) == 0:
                continue
            attrs = "; ".join(
                [f"{key}: {value}" for key, value in values.items()])
            kikitCommand += f"    --{section} '{attrs}' \\\n"

        inputFilename = self.sections["Input"].items["Input file"].getValue()
        if len(inputFilename) == 0:
            inputFilename = "<missingInput>"

        outputFilename = self.sections["Output"].items["Output file"].getValue()
        if len(outputFilename) == 0:
            outputFilename = "<missingOutput>"

        kikitCommand += f"    '{inputFilename}' '{outputFilename}'"

        return kikitCommand

    def _buildWindowsCommand(self, presetUpdates):
        kikitCommand = "kikit panelize^\n"
        for section, values in presetUpdates.items():
            if len(values) == 0:
                continue
            attrs = "; ".join(
                [f"{key}: {value}" for key, value in values.items()])
            kikitCommand += f"    --{section} \"{attrs}\" ^\n"

        inputFilename = self.sections["Input"].items["Input file"].getValue()
        if len(inputFilename) == 0:
            inputFilename = "<missingInput>"

        outputFilename = self.sections["Output"].items["Output file"].getValue()
        if len(outputFilename) == 0:
            outputFilename = "<missingOutput>"

        kikitCommand += f"    \"{inputFilename}\" \"{outputFilename}\""
        return kikitCommand


    def kikitArgs(self):
        defaultPreset = loadPresetChain([":default"])
        preset = self.collectReleventPreset()
        presetUpdates = presetDifferential(defaultPreset, preset)

        args = {}
        for section, values in presetUpdates.items():
            if len(values) == 0:
                continue
            args[section] = values
        return args

    def onExport(self, evt):
        with wx.FileDialog(self, "导出配置", wildcard="KiKit 配置 (*.json)|*.json",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            pathname = fileDialog.GetPath()
            try:
                defaultPreset = loadPresetChain([":default"])
                preset = self.collectReleventPreset()
                presetUpdates = presetDifferential(defaultPreset, preset)
                with open(pathname, "w", encoding="utf-8") as file:
                    json.dump(presetUpdates, file, indent=4)
                wx.MessageBox(f"配置已导出至 {pathname}", "成功",
                    style=wx.OK | wx.ICON_INFORMATION, parent=self)
            except IOError as e:
                wx.MessageBox(f"无法导出至文件 {pathname}：{e}", "错误",
                    style=wx.OK | wx.ICON_ERROR, parent=self)

    def onImport(self, evt):
        with wx.FileDialog(self, "打开 KiKit 配置", wildcard="KiKit 配置 (*.json)|*.json",
                       style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            pathname = fileDialog.GetPath()
            try:
                with open(pathname, "r", encoding="utf-8") as file:
                    preset = json.load(file)
                    self.populateInitialValue(preset)
                    self.OnChange()
            except Exception as e:
                wx.MessageBox(f"无法加载配置：{e}", "错误",
                    style=wx.OK | wx.ICON_ERROR, parent=self)


def _loadPreset():
    try:
        with open(PRESET_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _savePreset(preset):
    try:
        os.makedirs(os.path.dirname(PRESET_STATE_PATH), exist_ok=True)
        with open(PRESET_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(preset, f, indent=2)
    except OSError:
        pass

class PanelizePlugin(pcbnew.ActionPlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preset = _loadPreset()
        self.dirty = False

    def defaults(self):
        self.name = "KiKit：拼板"
        self.category = "KiKit"
        self.description = "创建拼板"
        self.icon_file_name = os.path.join(PKG_BASE, "resources", "graphics", "panelizeIcon_24x24.png")
        self.show_toolbar_button = True

    def Run(self):
        try:
            dialog = None
            if not self.dirty and not pcbnew.GetBoard().IsEmpty():
                dlg = wx.MessageDialog(
                    None,
                    "当前打开的电路板不为空，将被拼板替换。是否继续？\n\n" + \
                    "请注意，拼板工具应在独立的 pcbnew 实例中运行。",
                    "确认",
                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
                ret = dlg.ShowModal()
                dlg.Destroy()
                if ret == wx.ID_NO:
                    return
            dialog = initDialog(lambda: PanelizeDialog(None, pcbnew.GetBoard(), self.preset))
            dialog.ShowModal()
            self.preset = dialog.collectPreset(includeInput=True)
            self.dirty = self.dirty or dialog.dirty
            _savePreset(self.preset)
        except Exception as e:
            dlg = wx.MessageDialog(
                None, f"无法执行：{e}", "错误", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
        finally:
            destroyDialog(dialog)


plugin = PanelizePlugin

if __name__ == "__main__":
    # Run test dialog
    import json
    app = wx.App()

    dialog = PanelizeDialog()
    dialog.ShowModal()
    print(json.dumps(dialog.collectPreset(True), indent=4))


