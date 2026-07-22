# KiKit – KiCAD 自动化工具

![KiKit Logo](https://github.com/yaqwsx/KiKit/raw/master/kikit/resources/graphics/kikitIcon_64x64.png)

KiKit 是一个 Python 库、KiCAD 插件和 CLI 工具，用于自动完成标准 KiCAD 工作流程中的若干任务，例如：

- 拼板，支持常规形状和不规则形状的电路板（参见[示例](https://yaqwsx.github.io/KiKit/latest/panelization/examples/)）
- 基于制造商预设自动导出制造数据
- KiCAD 多板项目
- 构建电路板展示页面（参见[由 KiKit 生成的示例展示页面](https://roboticsbrno.github.io/RB0002-BatteryPack)）

![KiKit Promo](https://github.com/yaqwsx/KiKit/blob/master/docs/resources/promo.jpg?raw=true)

## 你喜欢 KiKit 吗？它为你节省时间了吗？

如果是，请考虑：

- [**在 GitHub Sponsors 上支持我**](https://github.com/sponsors/yaqwsx)
- 或成为我的 [Patreon](https://patreon.com/yaqwsx) 赞助者，
- 或请我喝杯咖啡：[![ko-fi](https://www.ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/E1E2181LU)

您的支持将使我能够分配时间来妥善维护此类项目。

PS：请务必查看我的其他 KiCAD 和 PCB 相关项目：

- [Pinion](https://github.com/yaqwsx/Pinion/)
- [PcbDraw](https://github.com/yaqwsx/PcbDraw/)
- [JlcParts](https://github.com/yaqwsx/jlcparts)

## 安装

KiKit 以 [PyPi 包](https://pypi.org/project/KiKit/) 形式提供。但由于 KiCAD 的打包方式，在某些平台上需要使用特定的 Python 解释器进行安装。

请按照详细的[安装指南](https://yaqwsx.github.io/KiKit/latest/installation/intro/)进行操作，其中涵盖了基于您所使用平台的安装方法。

## 为什么应该使用它？

KiKit 能做的所有事情，也可以通过 KiCAD 中的 Pcbnew 完成。但您必须手动操作。一个常见场景是创建拼板。互联网上的大多数教程都引导您使用 Pcbnew 的"附加电路板"功能。然而，这种方法劳动密集、容易出错，而且每当您更改电路板时，都必须重新操作。

使用 KiKit，如果您有简单的布局（例如网格），只需调用 CLI 命令，或编写几条 Python 指令，如"在此放置电路板"、"在此添加连接桥"、"通过邮票孔/V-cut 分离电路板"，即可完成。这个过程是可重复的，而且实际上比手工绘制拼板简单得多。KiKit 还允许您轻松地一次性导出所有 Gerber 文件。

然后您可以编写 Makefile，只需调用 `make` 即可获取所有制造数据和电路板展示页面。

## 功能列表

- 通过附加电路板和基板碎片（连接桥）创建拼板
- 支持任意形状的电路板
- 轻松创建邮票孔 / V-CUT
- 与手工创建拼板相比，您的拼板将能通过 DRC（因为使用 KiKit 时，同一电路板不同实例的走线拥有不同的网络）
- 如果您在一个文件中有多个电路板，可以将其分离
- 简化 [KiCAD 多板项目](https://yaqwsx.github.io/KiKit/latest/multiboard/)
- [自动导出 Gerber 和贴片数据](https://yaqwsx.github.io/KiKit/latest/fabrication/intro/)
- [3D 打印自定位焊膏钢网](https://yaqwsx.github.io/KiKit/upstream/latest/stencil/#3d-printed-stencils)
- [带定位治具的钢网](https://yaqwsx.github.io/KiKit/latest/stencil/#steel-stencils)
- 创建强大的 shell 脚本或 Makefile 来自动化您的工作流程……
- ……或通过 [KiCAD 中的 GUI](https://yaqwsx.github.io/KiKit/latest/panelization/gui/) 调用功能。

## 如何使用？

首先阅读[拼板文档](https://yaqwsx.github.io/KiKit/latest/panelization/intro/)。该页面将指导您了解 CLI、GUI 和脚本的使用方法。也请务必查看[示例](https://yaqwsx.github.io/KiKit/latest/panelization/examples/)。还有一份关于如何使用[拼板操作插件](https://yaqwsx.github.io/KiKit/latest/panelization/gui/)的简要说明。如果您对生成焊膏钢网感兴趣，请参阅[钢网文档](https://yaqwsx.github.io/KiKit/latest/stencil/)。

## 致谢

本项目的支持者：

- [我的 GitHub 赞助者](https://github.com/sponsors/yaqwsx) 以及
- [<img src="https://nlnet.nl/logo/banner.svg" width="150"/>](https://nlnet.nl/project/KiKit/#ack)

## KiKit 无法正常工作或表现异常？

请先查看[常见问题](https://yaqwsx.github.io/KiKit/latest/faq/)。如果您的问题在那里没有找到答案，欢迎在 GitHub 上提出 issue。

如果您希望 KiKit 拥有当前路线图中没有的功能，或者需要准备自定义拼板脚本（例如多设计拼板、特定排列的拼板），可以考虑雇佣我来完成这项工作。请通过电子邮件联系我，我们可以进一步讨论细节。
