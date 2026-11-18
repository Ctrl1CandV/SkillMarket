# 常用写法

下面标“已测”的写法，2026-11-18 在 Windows 10、WPS 12.1、agent-desktop 1.3.1 上实际跑过；没标的是按文档写的，用之前先小范围试。

## 文件与目录（PowerShell）

```powershell
Rename-Item  'D:\a\周报.txt' '周报-定稿.txt'
Move-Item    'D:\a\*.csv' 'D:\b\'
Copy-Item    'D:\a\报告.docx' 'D:\a\报告-备份.docx'      # 改文档前先留一份
# 删除进回收站，可以还原（已测）。Remove-Item 是永久删除，要先问用户。
Add-Type -AssemblyName Microsoft.VisualBasic
[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile('D:\a\临时.tmp', 'OnlyErrorDialogs', 'SendToRecycleBin')
[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory('D:\a\旧版本', 'OnlyErrorDialogs', 'SendToRecycleBin')
```

## WPS / Office 文档（COM，后台运行，不出窗口）

WPS 表格读写（已测，打开、读写、保存都在 1 秒多）：

```powershell
$et = New-Object -ComObject KET.Application      # Office 用 Excel.Application
$et.Visible = $false; $et.DisplayAlerts = $false
try {
  $wb = $et.Workbooks.Open('D:\a\账单.csv')        # 新建用 $et.Workbooks.Add()
  $ws = $wb.Worksheets.Item(1)
  $ws.Cells.Item(2, 3).Text                        # 读：显示出来的文字
  $ws.Range('A1:B1').Value2 = @('项目', '金额')     # 写一行
  $ws.Cells.Item(3, 2).Formula = '=SUM(B2:B2)'
  $wb.SaveAs('D:\a\汇总.xlsx', 51)                  # 51 = xlsx；只看不改就 $wb.Close($false)
  $wb.Close($false)
} finally {
  $et.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($et)   # 不释放会留下后台进程
}
```

- WPS 文字用 `KWPS.Application`，演示用 `KWPP.Application`。对象模型和 Word、PowerPoint 的基本一致（`Documents.Open`、`Presentations.Open`、`ExportAsFixedFormat` 导出 PDF），本机没逐项测过。
- 用户正开着这份文件时，先问，或者另存副本再改。
- 本机的 Microsoft Office 没有激活，打开会弹激活向导挡住窗口；同样的事优先交给 WPS。
- 只需要读写文件内容、不需要软件本身时，也可以用 Python 的 openpyxl、python-docx、python-pptx，前提是环境里已经装了；没装先问。

## 系统设置

- 打开某个设置页给用户看，或者接着用 agent-desktop 读：`start ms-settings:display`（已测），其他页如 `ms-settings:sound`、`ms-settings:network`、`ms-settings:appsfeatures`。
- 读当前值：设置页用 agent-desktop `snapshot` 读，连屏幕外的选项（缩放 150%、分辨率）也读得到（已测）。在 PowerShell 里用 `GetDpiForSystem` 查 DPI 不可靠，进程没声明 DPI 感知时会把 150% 读成 100%；`GetDpiForMonitor` 或注册表 `HKCU\Control Panel\Desktop\WindowMetrics\AppliedDPI`（144 = 150%）读得对（pi 试用时实测）。
- 改设置之前先说清要改哪一项、原来是什么值，方便改回去。

## 开发工具

- VS Code：先 `Get-Command code` 确认它指向 VS Code（本机 PATH 里第一个 `code` 是 QoderCN 的），否则写全路径 `%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe`。`code -n <目录>` 开新窗口（已测），`code -g <文件>:<行>` 跳到某行，`code --install-extension <id>` 装扩展。不要靠点它的文件树：无头模式点不动（已测）。
- 其他工具优先用自带命令：`git`、`winget`、`adb`、`gradle`、`dotnet`、`npm` 等。

## agent-desktop 常用组合

```
node ad.mjs list-apps                                   # 开始前记下已在运行的程序
node ad.mjs list-windows --app explorer.exe              # 拿窗口编号
node ad.mjs snapshot --window-id w-123 -i --compact      # 读能操作的元素
node ad.mjs find --window-id w-123 --role button --name 关闭
node ad.mjs click @s1abc:e3                              # 编号来自最近一次读取
node ad.mjs screenshot --window-id w-123 D:\a\shot.png   # 不用切到前台
node ad.mjs wait --window 账单 --app wps.exe             # 等窗口出现
```

实测速度：列窗口约 0.1 秒；读一个窗口 0.4–1.8 秒；点击 0.2–1.3 秒。截图式的电脑操作每一步都要截图、看图、再点，通常要好几秒。
