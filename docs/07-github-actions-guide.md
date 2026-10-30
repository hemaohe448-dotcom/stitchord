# 07 给非程序员的操作手册：把代码放到 GitHub 并跑一次 Roidery 构建

> 这次只需要你做 **3 件事**：
> 1. 把 `D:\stitchord` 这个文件夹上传到 GitHub；
> 2. 在 GitHub 网页上点一次“运行”按钮；
> 3. 把运行结果（成功/失败 + 链接）发给我。
>
> 全程不需要写代码，大约 30–60 分钟，大部分时间是在等构建。
> 仓库里没有密码、密钥或别人的私人文件；只有本项目代码和文档（约 0.5 MB，86 个文件）。

---

## 一、先准备两样东西

### 1. GitHub 账号

打开 https://github.com ，点右上角 **Sign up** 注册；已有账号就 **Sign in**。

记住你的用户名（例如 `zhangsan`），后面会用到。

### 2. 安装 GitHub Desktop（推荐小白用这个）

下载地址：https://desktop.github.com/

- 双击安装，如果 Windows 弹出“是否允许”，点“是”；
- 安装完打开，点 **Sign in to GitHub.com**，用浏览器登录你的账号；
- 登录后 GitHub Desktop 会显示你的仓库列表（一开始是空的）。

> 为什么不用命令行？GitHub 现在不允许用账号密码 push，配置 Token 对新手容易卡住；
> GitHub Desktop 用浏览器登录，最省事。

---

## 二、把 `D:\stitchord` 上传到 GitHub

### 第 1 步：让 GitHub Desktop 认识这个文件夹

1. 打开 GitHub Desktop；
2. 左上角菜单 **File → Add local repository…**；
3. 点 **Choose…**，选择 `D:\stitchord`；
4. 如果提示 “This directory appears to be a Git repository”，直接点 **Add repository**。

### 第 2 步：发布到 GitHub

1. 添加后，界面上方会出现 **Publish repository** 按钮（如果没有，点菜单 **Repository → Publish repository…**）；
2. 弹窗里：
   - **Name**：填 `stitchord`
   - **Description**：随便写，例如 `embroidery digitizing web app`
   - **Keep this code private**：
     - 勾选 = 私有仓库（别人看不到代码，Actions 有免费额度）；
     - 不勾选 = 公开仓库（代码公开，Actions 免费，构建时间不计费）。
   - 建议：**不勾选**（这是开源项目，公开更省事；仓库里没有密钥）；
3. 点 **Publish repository**；
4. 等几秒，上传完成。点菜单 **Repository → View on GitHub**，浏览器会打开你的仓库页面。

> 如果上传失败：确认 GitHub Desktop 已登录；公司网络可能需要代理，见文末“常见问题”。

---

## 三、确认 GitHub Actions 是打开的

1. 在仓库页面顶部点 **Actions**；
2. 如果看到 “Workflows aren’t being run on this repository” 或类似提示，点 **Enable Actions** / **I understand my workflows, go ahead and enable them**；
3. 如果左侧没有出现 `roidery-build-gate`，等 1–2 分钟刷新页面（GitHub 需要扫描新文件）。

如果还是看不到：

- 点仓库 **Settings → Actions → General**；
- 在 **Actions permissions** 里选 **Allow all actions and reusable workflows**；
- 点 **Save**。

---

## 四、手动运行构建

1. 点仓库顶部 **Actions**；
2. 左侧列表点 **roidery-build-gate**；
3. 右侧会出现一行提示 “This workflow has a workflow_dispatch event trigger.”，点右边的 **Run workflow**；
4. 弹窗里：
   - **Use workflow from**：选 `main`；
   - 点绿色 **Run workflow**；
5. 刷新页面，列表里会出现一条新的运行记录：
   - 黄色圆点 = 正在运行；
   - 绿色对勾 = 成功；
   - 红色叉 = 失败。

**构建需要 30–60 分钟**（要下载 Rust 依赖并编译 Roidery）。你可以关掉网页，过一会儿再回来看，不需要一直盯着。

> 私有仓库会消耗 Actions 免费额度：Windows 机器按 2 倍计费，一次约 60–120 分钟；
> 免费额度是 2000 分钟/月，够跑十几次。公开仓库不计费。

---

## 五、把结果发给我

### 情况 A：绿色对勾（成功）

1. 点进这条运行记录；
2. 复制浏览器地址栏的 URL（这就是“运行链接”）；
3. 点页面底部 **Artifacts** 里的 **roidery-smoke-dst** 下载（可选，留着做证据）；
4. 点开 **Smoke test SVG -> DST** 这一步，找到类似：
   ```
   DST bytes: 1234
   ```
   把数字复制下来；
5. 把下面模板填好发我。

### 情况 B：红色叉（失败）

1. 点进运行记录；
2. 找到左侧带红色叉的步骤（例如 `Build vectorcraft-cli` 或 `Smoke test SVG -> DST`）；
3. 点它，把右侧日志**最后 30–50 行**复制下来（不用全复制）；
4. 把运行链接一起发我。

### 发给我的模板（直接复制填空）

```text
运行链接：
结论：成功 / 失败
总耗时（页面上会显示，例如 42m 10s）：
如果失败，失败步骤：
日志最后 30 行：
如果成功，DST 字节数：
备注（有报错就贴这里）：
```

也可以把结果直接填到仓库里的 `docs/reviews/roidery-build-result.md`（我可以帮你回填 ADR）。

---

## 六、常见问题（按出现概率排序）

### 1. 点 Publish 后提示要登录 / 没反应

打开 GitHub Desktop → **File → Options → Accounts**，确认已登录；
退出重开一次再试。

### 2. 上传很慢或失败

仓库只有 0.5 MB，正常几秒。如果卡住：

- 检查网络/代理；
- 关掉 VPN 再试，或反过来打开代理；
- 在 GitHub Desktop 里 **Repository → Repository settings** 确认 remote 地址是 `https://github.com/你的用户名/stitchord.git`。

### 3. Actions 页面没有 `roidery-build-gate`

- 确认 `.github/workflows/roidery-build-gate.yml` 已经在仓库里（网页上能看到这个文件）；
- 确认默认分支是 `main`；
- 等 1–2 分钟刷新；
- 确认 Actions 已启用（见第三节）。

### 4. 构建失败，提示找不到 Rust 1.95

把日志发我，我会把 workflow 里的版本改成 runner 上可用的 stable 版本。
不要自己改文件。

### 5. 构建超过 90 分钟被取消

正常，Roidery 很大。把运行链接发我，我会把超时时间调大或换缓存策略。

### 6. 私有仓库提示 minutes 不够

把仓库改成公开（**Settings → General → Danger Zone → Change visibility → Public**），
公开仓库的 Actions 不计费；或者等下个月额度刷新。

### 7. 我不希望代码公开

可以保持 private，按上面额度说明操作；这次构建照样能跑，只是会消耗免费分钟数。

---

## 七、备选：命令行方式（会用 Git 的人）

如果你不想装 GitHub Desktop：

```powershell
cd D:\stitchord
git remote add origin https://github.com/你的用户名/stitchord.git
git push -u origin main
```

GitHub 不再接受账号密码，需要 Personal Access Token：

1. GitHub 网页 → 右上角头像 → **Settings → Developer settings → Personal access tokens → Tokens (classic)**；
2. **Generate new token (classic)**，勾选 `repo` 和 `workflow`；
3. 复制 token（只显示一次），push 时用户名填 GitHub 用户名，密码填 token。

然后按第四、五节在网页上运行、取结果。

---

## 八、安全说明

- 仓库里**没有** `.env`、密钥、Token、客户数据；
- `LICENSE` 是 GPL-3.0，公开仓库符合许可证；
- 研究用的第三方源码克隆在 `.research/`，已被 `.gitignore` 排除，不会上传；
- 如果以后要放密钥，请用 GitHub Secrets，不要提交到仓库。

---

完成以上步骤后，把“运行链接 + 成功/失败 + 日志”发我，我会：

- 成功 → 在 ADR-0006 记录结果，评估是否接入 Roidery 内核；
- 失败 → 根据日志修 workflow（版本、超时、命令），再请你点一次。
