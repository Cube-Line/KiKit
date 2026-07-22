import wx
import wx.adv

class MissingKiKitDialog(wx.Dialog):
    def __init__(self, parent=None):
        wx.Dialog.__init__(self, parent, id=wx.ID_ANY, title=u"未找到 KiKit 安装！",
                           pos=wx.DefaultPosition, size=wx.Size(500, 300), style=wx.DEFAULT_DIALOG_STYLE)

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        bSizer1 = wx.BoxSizer(wx.VERTICAL)

        self.staticText = wx.StaticText(
            self, wx.ID_ANY, u"未找到 KiKit 后端！您可能仅通过 PCM 安装了 KiKit。\n\n请按照下方链接的安装指南进行操作。在完成安装之前，KiKit 功能将不可用。安装完成后，请重新启动 KiCAD。", wx.DefaultPosition, wx.DefaultSize, 0)
        self.staticText.Wrap(-1)

        bSizer1.Add(self.staticText, 1, wx.ALL | wx.EXPAND, 5)

        self.hyperlink = wx.adv.HyperlinkCtrl(self, wx.ID_ANY, u"https://yaqwsx.github.io/KiKit/latest/installation/intro/",
                                              u"https://yaqwsx.github.io/KiKit/latest/installation/intro/", wx.DefaultPosition, wx.DefaultSize, wx.adv.HL_ALIGN_CENTRE | wx.adv.HL_DEFAULT_STYLE)
        bSizer1.Add(self.hyperlink, 0, wx.ALL | wx.EXPAND, 5)

        self.okButton = wx.Button(
            self, wx.ID_ANY, u"确定", wx.DefaultPosition, wx.DefaultSize, 0)
        bSizer1.Add(self.okButton, 0, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(bSizer1)
        self.Layout()

        self.Centre(wx.BOTH)

        self.okButton.Bind(wx.EVT_BUTTON, self.OnOK)

    def OnOK(self, event):
        if self.IsModal():
            self.EndModal(0)
        else:
            self.Close(True)


try:
    from kikit.actionPlugins import importAllPlugins

    importAllPlugins()
except ImportError:
    dialog = MissingKiKitDialog()
    dialog.ShowModal()
    dialog.Destroy()

if __name__ == "__main__":
    # Run test dialog
    app = wx.App()

    dialog = MissingKiKitDialog()
    dialog.ShowModal()
    dialog.Destroy()
