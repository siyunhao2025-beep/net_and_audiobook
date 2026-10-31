# 远程访问、暂停与恢复

## 连接与工具

使用账户已连接的设备，实际读取小文件后再确认可用。设备列表的last-seen/Online不是请求成功的证据。远程工具返回running/call_id时轮询同一个结果，不能重发写文件/启动进程以免重复任务。长进程保存PID和确切命令，用输出分页查看，不把多秒无输出判为死锁。

Windows复杂命令写成自有脚本再运行，避免多层cmd/PowerShell/python -c引号。选实际已安装的Python绝对路径；设PYTHONIOENCODING=utf-8。Shell的$、反引号和命令替换按代码处理，不把JSON.stringify当shell转义。

## 代理排障

只在当前请求确实有连接错误时检查。ECONNREFUSED到127.0.0.1某端口意味着该配置的本地服务不可达，不证明Node版本坏了，也不证明另一个端口可用。读取系统ProxyEnable/ProxyServer及相关进程监听端口，区分禁用的旧注册表值、HTTP/mixed、SOCKS、DNS、控制/健康检查端口。

用明确代理对目标注册表/服务做有超时的请求，验证成功后只把所需代理传给任务进程。不要猜端口、重装Node、清空所有npm缓存、禁用TLS验证或改系统全局代理。连接窗口需持续运行，最小化即可；不要为了运行另一个任务中断它。公开skill不保留机器进程号、端口、设备ID或真实路径。

## 暂停和估时

`synthesize.py pause`是写标记而不是确认已停；读status直到pipeline为paused或已完成，并确认没有新集被写入。有限的当前请求可以进入缓存。若任务本来空闲，保留paused marker，报告“已阻止后续执行”。用户说开始/继续后才resume。

每集音频与文本/voice/rate/engine计划指纹绑定，只有成品SHA相符才跳过。服务请求缓存也要校验；损坏缓存重取。已经发布但被替代的旧stage不得自动resume。进度估时用最近每段/每集实际吞吐和剩余量给范围，注明网络重试与QA，不把音频3小时误报为生成还需3小时。

## Windows锁与部分写入

某些预览/远程read_file句柄允许读写却不允许rename/delete，os.replace可报WinError5；这不等于权限不足。先完成已有读取、重试短时替换。自有stage元数据可保留.part、校验当前哈希后原位写并立即读回；生产写必须先有原件备份及发布意图。

common.atomic_write依次尝试替换5次，然后做受检查的原位fallback。原位写不是崩溃原子操作：停电/中断可能留下半文件；保留.part、备份及journal，不把无法辨认的哈希当“自己的半文件”直接覆盖。先保存异常文件并核对，按publishing.md处理。

build.lock阻止同stage双进程。锁残留时核验其PID的实际命令与子进程是否仍属于该stage；确认已退出后才删除自有锁。杀PowerShell外壳可能遗留Python子进程，不用force_terminate当万能暂停，也不杀全部Node/Python或修改整目录ACL。
