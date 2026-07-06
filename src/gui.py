import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import threading, webbrowser, os, json, urllib.request

from constants import *
import gateway
import config_manager
import codex_repair
import codex_control
import runtime
from version import check_update

class App:
    def __init__(self, root):
        self.root = root
        runtime.ensure_all()
        root.title(APP_NAME + " " + APP_VERSION)
        root.geometry("920x680")
        root.minsize(820, 560)

        style = ttk.Style()
        style.configure("Protected.Treeview", foreground="#666666")

        nb = ttk.Notebook(root)
        nb.pack(fill='both', expand=True, padx=8, pady=8)

        self.status_tab = ttk.Frame(nb)
        self.config_tab = ttk.Frame(nb)
        self.settings_tab = ttk.Frame(nb)
        nb.add(self.status_tab, text="  运行状态  ")
        nb.add(self.config_tab, text="  配置管理  ")
        nb.add(self.settings_tab, text="  设置  ")

        self._build_status()
        self._build_config()
        self._build_settings()
        self.refresh_status()

    # ── Status Tab ──
    def _build_status(self):
        f = self.status_tab
        top = ttk.Frame(f)
        top.pack(fill='x', padx=12, pady=(12, 6))

        self.st_run = tk.StringVar(value="检测中...")
        self.st_pid = tk.StringVar(value="-")
        self.st_url = tk.StringVar(value="-")
        self.st_models = tk.StringVar(value="-")
        self.codex_status = tk.StringVar(value="Codex: 检测中...")

        ttk.Label(top, text="本地模型网关", font=("", 13, "bold")).pack(anchor='w')
        ttk.Label(top, textvariable=self.st_run, font=("", 12)).pack(anchor='w')
        ttk.Label(top, textvariable=self.st_pid).pack(anchor='w')
        ttk.Label(top, textvariable=self.st_url).pack(anchor='w')

        codex_box = ttk.LabelFrame(f, text="Codex Desktop")
        codex_box.pack(fill='x', padx=12, pady=6)
        ttk.Label(codex_box, textvariable=self.codex_status).pack(side='left', padx=12, pady=8)
        self.codex_toggle_btn = ttk.Button(codex_box, text="打开 Codex", command=lambda: self._bg(self._toggle_codex))
        self.codex_toggle_btn.pack(side='left', padx=6, pady=8)
        self.codex_restart_btn = ttk.Button(codex_box, text="重启 Codex", command=lambda: self._bg(self._restart_codex))
        self.codex_restart_btn.pack(side='left', padx=6, pady=8)

        ttk.Label(top, text="模型列表：").pack(anchor='w', pady=(8, 0))
        self.st_model_list = tk.Text(f, height=12, width=80, state='disabled',
                                    font=("Consolas", 10))
        self.st_model_list.pack(fill='both', expand=True, padx=12, pady=6)

        btns = ttk.Frame(f)
        btns.pack(fill='x', padx=12, pady=(0, 12))
        ttk.Button(btns, text="刷新", command=self.refresh_status).pack(side='left', padx=(0, 6))
        ttk.Button(btns, text="启动", command=lambda: self._bg(self._start)).pack(side='left', padx=6)
        ttk.Button(btns, text="停止", command=lambda: self._bg(self._stop)).pack(side='left', padx=6)
        ttk.Button(btns, text="重启", command=lambda: self._bg(self._restart)).pack(side='left', padx=6)

    def refresh_status(self):
        def _do():
            s = gateway.get_status()
            if s["running"] and s["responding"]:
                self.st_run.set("● 运行中 (正常响应)")
                self.root._status_color = "green"
            elif s["running"]:
                self.st_run.set("● 运行中 (无响应)")
                self.root._status_color = "orange"
            else:
                self.st_run.set("● 已停止")
                self.root._status_color = "red"
            self.st_pid.set("PID: " + str(s["pid"] or "-"))
            self.st_url.set("地址: " + s["url"])
            cs = codex_control.get_status()
            if cs["running"]:
                self.codex_status.set("Codex: 运行中 (" + str(cs["count"]) + " 个进程)")
                self.codex_toggle_btn.config(text="停止 Codex")
                self.codex_restart_btn.config(state='normal')
            else:
                self.codex_status.set("Codex: 未运行")
                self.codex_toggle_btn.config(text="打开 Codex")
                self.codex_restart_btn.config(state='disabled')
            self.st_model_list.config(state='normal')
            self.st_model_list.delete('1.0', 'end')
            if s["models"]:
                for m in s["models"]:
                    self.st_model_list.insert('end', m + "\n")
            else:
                self.st_model_list.insert('end', "(无可用模型或网关未运行)\n")
            self.st_model_list.config(state='disabled')

        self._bg(_do)

    def _start(self):
        ok = gateway.start()
        if ok:
            messagebox.showinfo("成功", "网关已启动。")
        else:
            messagebox.showerror("失败", "网关启动失败，请检查配置和程序。")
        self.refresh_status()

    def _stop(self):
        gateway.stop()
        messagebox.showinfo("已停止", "网关已停止。")
        self.refresh_status()

    def _restart(self):
        ok = gateway.restart()
        if ok:
            messagebox.showinfo("成功", "网关已重启。")
        else:
            messagebox.showerror("失败", "网关重启失败。")
        self.refresh_status()

    def _toggle_codex(self):
        if codex_control.is_running():
            ok = codex_control.stop()
            messagebox.showinfo("Codex", "Codex 已停止。" if ok else "已尝试停止 Codex。")
        else:
            ok = codex_control.start()
            if ok:
                messagebox.showinfo("Codex", "Codex 已打开。")
            else:
                messagebox.showerror("Codex", "未能找到或打开 Codex Desktop。")
        self.refresh_status()

    def _restart_codex(self):
        ok = codex_control.restart()
        if ok:
            messagebox.showinfo("Codex", "Codex 已重启。")
        else:
            messagebox.showerror("Codex", "Codex 重启失败。")
        self.refresh_status()

    # ── Config Tab ──
    def _build_config(self):
        f = self.config_tab
        tree_frame = ttk.Frame(f)
        tree_frame.pack(fill='both', expand=True, padx=12, pady=(12, 6))

        cols = ("num", "name", "alias", "upstream", "provider", "type", "url", "ctx", "maxout", "flag")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=10)
        headers = {"num":"#","name":"展示名称","alias":"模型ID","upstream":"上游模型","provider":"供应商",
                   "type":"类型","url":"URL","ctx":"上下文","maxout":"最大输出","flag":"标记"}
        for c in cols:
            self.tree.heading(c, text=headers[c])
        widths = {"num":36,"name":150,"alias":135,"upstream":135,"provider":120,"type":120,
                  "url":210,"ctx":80,"maxout":80,"flag":70}
        for c in cols:
            self.tree.column(c, width=widths[c], stretch=True if c in ("name","url") else False)
        self.tree.tag_configure("builtin", foreground="#6b7280")
        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        btns = ttk.Frame(f)
        btns.pack(fill='x', padx=12, pady=(0, 6))
        ttk.Button(btns, text="刷新", command=self.refresh_config).pack(side='left', padx=(0, 6))
        ttk.Button(btns, text="添加模型", command=self._add_model).pack(side='left', padx=6)
        ttk.Button(btns, text="修改", command=self._modify_model).pack(side='left', padx=6)
        ttk.Button(btns, text="删除", command=self._remove_model).pack(side='left', padx=6)
        ttk.Button(btns, text="查看完整配置", command=self._view_config).pack(side='left', padx=6)

    def refresh_config(self):
        self.tree.delete(*self.tree.get_children())
        try:
            s = config_manager.get_summary()
            for e in s["entries"]:
                tag = ("builtin",) if e.get("built_in") else ()
                self.tree.insert('', 'end', values=(
                    e["number"], e["display_name"], e["alias"], e["upstream"], e["provider_name"],
                    e["section"], e["base_url"],
                    str(e["context_window"] or "-"),
                    str(e["max_output_tokens"] or "-"),
                    "内置" if e.get("built_in") else ""
                ), tags=tag)
        except Exception as ex:
            messagebox.showerror("错误", str(ex))

    def _add_model(self):
        dlg = AddModelDialog(self.root)
        if dlg.result:
            r = dlg.result
            try:
                alias = config_manager.add_model(
                    r["api_type"], r["provider_name"], r["base_url"],
                    r["api_key"], r["model_id"], r["alias"],
                    r["display_name"], r.get("context_window"),
                    r.get("max_output_tokens"))
                gateway.restart()
                messagebox.showinfo("成功", "模型已添加: " + alias)
                self.refresh_config()
            except Exception as ex:
                messagebox.showerror("失败", str(ex))

    def _modify_model(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个模型。")
            return
        vals = self.tree.item(sel[0], 'values')
        if len(vals) > 9 and vals[9] == "内置":
            messagebox.showwarning("受保护", "内置免费模型不可修改。")
            return
        num = int(vals[0])
        dlg = ModifyDialog(self.root, vals)
        if dlg.result:
            r = dlg.result
            try:
                alias = config_manager.modify_model(num, **r)
                gateway.restart()
                messagebox.showinfo("成功", "已修改: " + alias)
                self.refresh_config()
            except Exception as ex:
                messagebox.showerror("失败", str(ex))

    def _remove_model(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个模型。")
            return
        vals = self.tree.item(sel[0], 'values')
        if len(vals) > 9 and vals[9] == "内置":
            messagebox.showwarning("受保护", "内置免费模型不可删除。")
            return
        num = int(vals[0])
        name = vals[1]
        if messagebox.askyesno("确认", "确认删除 " + name + " ?"):
            try:
                alias = config_manager.remove_model(num)
                gateway.restart()
                messagebox.showinfo("成功", "已删除: " + alias)
                self.refresh_config()
            except Exception as ex:
                messagebox.showerror("失败", str(ex))

    def _view_config(self):
        win = tk.Toplevel(self.root)
        win.title("完整配置 (脱敏)")
        win.geometry("700x600")
        txt = tk.Text(win, font=("Consolas", 10), wrap='none')
        txt.pack(fill='both', expand=True)
        sb = ttk.Scrollbar(win, command=txt.yview)
        sb.pack(side='right', fill='y')
        txt.configure(yscrollcommand=sb.set)
        try:
            content = config_manager.get_redacted_config()
            txt.insert('1.0', content)
        except Exception as ex:
            txt.insert('1.0', "Error: " + str(ex))
        txt.config(state='disabled')

    # ── Settings Tab ──
    def _build_settings(self):
        f = self.settings_tab

        # Autostart section
        auto_frame = ttk.LabelFrame(f, text="开机自启")
        auto_frame.pack(fill='x', padx=12, pady=(12, 6))
        self.auto_var = tk.StringVar(value="检测中...")
        ttk.Label(auto_frame, textvariable=self.auto_var).pack(anchor='w', padx=12, pady=6)
        auto_btns = ttk.Frame(auto_frame)
        auto_btns.pack(fill='x', padx=12, pady=(0, 6))
        ttk.Button(auto_btns, text="开启自启", command=self._enable_autostart).pack(side='left', padx=(0, 6))
        ttk.Button(auto_btns, text="关闭自启", command=self._disable_autostart).pack(side='left', padx=6)

        # Port section
        port_frame = ttk.LabelFrame(f, text="网关端口")
        port_frame.pack(fill='x', padx=12, pady=6)
        self.port_var = tk.StringVar()
        ttk.Label(port_frame, text="端口:").pack(side='left', padx=(12, 4), pady=6)
        ttk.Entry(port_frame, textvariable=self.port_var, width=10).pack(side='left', padx=4, pady=6)
        ttk.Button(port_frame, text="应用并重启", command=self._apply_port).pack(side='left', padx=8, pady=6)

        # Codex repair section
        repair_frame = ttk.LabelFrame(f, text="Codex 登录与配置修复")
        repair_frame.pack(fill='x', padx=12, pady=6)
        self.repair_var = tk.StringVar(value="检测中...")
        ttk.Label(repair_frame, textvariable=self.repair_var).pack(anchor='w', padx=12, pady=6)
        repair_btns = ttk.Frame(repair_frame)
        repair_btns.pack(fill='x', padx=12, pady=(0, 6))
        ttk.Button(repair_btns, text="官方登录", command=lambda: self._bg(self._codex_login)).pack(side='left', padx=(0, 6))
        ttk.Button(repair_btns, text="修复为订阅+第三方", command=lambda: self._repair_codex(True)).pack(side='left', padx=6)
        ttk.Button(repair_btns, text="仅 API/跳过登录", command=lambda: self._repair_codex(False)).pack(side='left', padx=6)

        # Version section
        ver_frame = ttk.LabelFrame(f, text="关于")
        ver_frame.pack(fill='x', padx=12, pady=6)
        ttk.Label(ver_frame, text="软件版本: " + APP_VERSION).pack(anchor='w', padx=12, pady=6)
        ttk.Label(ver_frame, text="GitHub: " + GITHUB_OWNER + "/" + GITHUB_REPO).pack(anchor='w', padx=12)
        ttk.Button(ver_frame, text="检查更新", command=lambda: self._bg(self._check_update)).pack(anchor='w', padx=12, pady=6)

        self._refresh_settings()

    def _refresh_settings(self):
        def _do():
            try:
                port = config_manager.get_port()
                self.port_var.set(str(port))
            except Exception:
                self.port_var.set("8317")
            state = gateway.get_scheduled_task_state()
            if state in ("ready", "running"):
                self.auto_var.set("已开启 (登录时自动启动)")
            elif state == "disabled":
                self.auto_var.set("已关闭")
            else:
                self.auto_var.set("未配置")
            issues, needs_fix = codex_repair.check_codex_config()
            if not needs_fix:
                self.repair_var.set("正常 - Codex 已配置使用本网关")
            else:
                self.repair_var.set("需要修复 - " + "; ".join(issues))
        self._bg(_do)

    def _enable_autostart(self):
        ok = gateway.enable_autostart()
        if ok:
            messagebox.showinfo("成功", "已开启开机自启。")
        else:
            messagebox.showerror("失败", "开启自启失败。")
        self._refresh_settings()

    def _disable_autostart(self):
        ok = gateway.disable_autostart()
        if ok:
            messagebox.showinfo("成功", "已关闭开机自启。")
        else:
            messagebox.showwarning("提示", "可能本就没有计划任务。")
        self._refresh_settings()

    def _apply_port(self):
        port = self.port_var.get().strip()
        try:
            port = int(port)
            if port < 1 or port > 65535:
                raise ValueError()
        except ValueError:
            messagebox.showerror("错误", "端口必须是 1-65535 的数字。")
            return
        if messagebox.askyesno("确认", "修改端口需要重启网关，继续?"):
            config_manager.set_port(port)
            gateway.restart()
            messagebox.showinfo("成功", "端口已修改为 " + str(port) + "，网关已重启。")
            self.refresh_status()

    def _repair_codex(self, requires_auth=True):
        ok, msg = codex_repair.repair_codex_config(requires_auth)
        if ok:
            messagebox.showinfo("修复", msg)
        else:
            messagebox.showerror("失败", msg)
        self._refresh_settings()

    def _codex_login(self):
        ok = gateway.run_codex_login()
        if ok:
            messagebox.showinfo("Codex 登录", "已启动 CLIProxyAPI 的 Codex 官方登录流程，请按浏览器提示完成授权。")
        else:
            messagebox.showerror("Codex 登录", "无法启动登录流程。")

    def _check_update(self):
        r = check_update()
        if "error" in r:
            messagebox.showerror("检查更新", "检查失败: " + r["error"])
            return
        if r["has_update"]:
            msg = "发现新版本: " + r["latest_version"] + "\n\n"
            msg += r["release_notes"] + "\n\n"
            if r["download_url"]:
                msg += "点击确定打开下载页面。"
                if messagebox.askyesno("发现更新", msg):
                    webbrowser.open(r["download_url"])
            else:
                msg += "点击确定打开 Release 页面。"
                if messagebox.askyesno("发现更新", msg):
                    webbrowser.open(r["release_url"])
        else:
            messagebox.showinfo("检查更新", "当前版本 " + r["current_version"] + " 已是最新。")

    # ── Helpers ──
    def _bg(self, fn):
        def _run():
            try:
                fn()
            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("错误", str(ex)))
        t = threading.Thread(target=_run, daemon=True)
        t.start()

# ── Add Model Dialog ──
class AddModelDialog:
    def __init__(self, parent):
        self.result = None
        self.win = tk.Toplevel(parent)
        self.win.title("添加第三方模型")
        self.win.geometry("620x520")
        self.win.transient(parent)
        self.win.grab_set()
        self._build()
        self.win.wait_window()

    def _build(self):
        f = self.win
        self.api_type = tk.StringVar(value="responses")
        self.base_url = tk.StringVar()
        self.api_key = tk.StringVar()
        self.model_id = tk.StringVar()
        self.alias = tk.StringVar()
        self.display_name = tk.StringVar()
        self.provider_name = tk.StringVar()
        self.ctx = tk.StringVar()
        self.maxout = tk.StringVar()

        ttk.Label(f, text="接口类型:").grid(row=0, column=0, sticky='w', padx=12, pady=4)
        cb = ttk.Combobox(f, textvariable=self.api_type, state='readonly',
                         values=["responses","openai","claude"], width=18)
        cb.grid(row=0, column=1, padx=12, pady=4)

        fields = [
            ("API Base URL:", self.base_url),
            ("API Key:", self.api_key),
        ]
        for i, (label, var) in enumerate(fields, 1):
            ttk.Label(f, text=label).grid(row=i, column=0, sticky='w', padx=12, pady=4)
            show = '*' if 'Key' in label else ''
            ttk.Entry(f, textvariable=var, width=30, show=show).grid(row=i, column=1, padx=12, pady=4)

        ttk.Label(f, text="上游模型ID:").grid(row=3, column=0, sticky='w', padx=12, pady=4)
        self.model_combo = ttk.Combobox(f, textvariable=self.model_id, width=28)
        self.model_combo.grid(row=3, column=1, padx=12, pady=4)
        ttk.Button(f, text="获取模型列表", command=lambda: threading.Thread(target=self._fetch_models, daemon=True).start()).grid(row=3, column=2, padx=(0, 12), pady=4)

        more_fields = [
            ("Codex alias:", self.alias),
            ("展示名称:", self.display_name),
            ("供应商名称:", self.provider_name),
            ("上下文token(可选):", self.ctx),
            ("最大输出token(可选):", self.maxout),
        ]
        for i, (label, var) in enumerate(more_fields, 4):
            ttk.Label(f, text=label).grid(row=i, column=0, sticky='w', padx=12, pady=4)
            ttk.Entry(f, textvariable=var, width=30).grid(row=i, column=1, padx=12, pady=4)

        ttk.Button(f, text="确定", command=self._ok).grid(row=9, column=0, columnspan=3, pady=16)

    def _fetch_models(self):
        base = self.base_url.get().strip().rstrip("/")
        key = self.api_key.get().strip()
        if not base or not key:
            self.win.after(0, lambda: messagebox.showwarning("提示", "请先填写 URL 和 API Key。"))
            return
        try:
            req = urllib.request.Request(
                base + "/models",
                headers={"Authorization": "Bearer " + key, "User-Agent": APP_NAME},
            )
            resp = urllib.request.urlopen(req, timeout=20)
            data = json.loads(resp.read().decode("utf-8"))
            ids = sorted([
                str(x.get("id") or x.get("name"))
                for x in data.get("data", [])
                if isinstance(x, dict) and (x.get("id") or x.get("name"))
            ])
            if not ids:
                raise ValueError("接口没有返回可识别的模型 ID。")
            def apply():
                self.model_combo["values"] = ids
                self.model_id.set(ids[0])
                messagebox.showinfo("模型列表", "已获取 " + str(len(ids)) + " 个模型。")
            self.win.after(0, apply)
        except Exception as ex:
            self.win.after(0, lambda: messagebox.showwarning("模型列表", "获取失败，可手动填写模型 ID。\n\n" + str(ex)))

    def _ok(self):
        if not self.base_url.get() or not self.api_key.get() or not self.model_id.get():
            messagebox.showwarning("提示", "URL、Key、模型ID 不能为空。")
            return
        alias = self.alias.get().strip() or self.model_id.get().strip()
        display = self.display_name.get().strip() or self.model_id.get().strip()
        ctx = int(self.ctx.get()) if self.ctx.get().strip().isdigit() else None
        maxout = int(self.maxout.get()) if self.maxout.get().strip().isdigit() else None
        self.result = {
            "api_type": self.api_type.get(),
            "base_url": self.base_url.get().strip(),
            "api_key": self.api_key.get().strip(),
            "model_id": self.model_id.get().strip(),
            "alias": alias,
            "display_name": display,
            "provider_name": self.provider_name.get().strip() or "Custom",
            "context_window": ctx,
            "max_output_tokens": maxout,
        }
        self.win.destroy()

# ── Modify Dialog ──
class ModifyDialog:
    def __init__(self, parent, vals):
        self.result = None
        self.vals = vals
        self.win = tk.Toplevel(parent)
        self.win.title("修改模型配置")
        self.win.geometry("480x480")
        self.win.transient(parent)
        self.win.grab_set()
        self._build()
        self.win.wait_window()

    def _build(self):
        f = self.win
        # vals: num, name, alias, upstream, provider, type, url, ctx, maxout, flag
        fields = [
            ("URL:", "base_url", self.vals[6]),
            ("API Key (留空保留):", "api_key", ""),
            ("上游模型名:", "upstream", self.vals[3]),
            ("Codex alias:", "alias", self.vals[2]),
            ("展示名称:", "display_name", self.vals[1]),
            ("供应商名称:", "provider_name", self.vals[4]),
            ("上下文token:", "context_window", self.vals[7] if self.vals[7] != "-" else ""),
            ("最大输出token:", "max_output_tokens", self.vals[8] if self.vals[8] != "-" else ""),
        ]
        self.vars = {}
        for i, (label, key, default) in enumerate(fields):
            ttk.Label(f, text=label).grid(row=i, column=0, sticky='w', padx=12, pady=4)
            v = tk.StringVar(value=default if default else "")
            self.vars[key] = v
            show = '*' if 'Key' in label else ''
            ttk.Entry(f, textvariable=v, width=30, show=show).grid(row=i, column=1, padx=12, pady=4)
        ttk.Button(f, text="确定", command=self._ok).grid(row=len(fields), column=0, columnspan=2, pady=16)

    def _ok(self):
        r = {}
        for key, var in self.vars.items():
            val = var.get().strip()
            if val:
                if key in ("context_window", "max_output_tokens"):
                    if val.isdigit():
                        r[key] = int(val)
                    elif val.upper() == "CLEAR":
                        r[key] = 0
                elif key == "api_key":
                    r[key] = val
                else:
                    r[key] = val
        self.result = r
        self.win.destroy()

def run():
    root = tk.Tk()
    App(root)
    root.mainloop()
