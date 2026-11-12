# IITCMapKitBuild

公开的 macOS arm64 构建入口。`iitc_mapkit` 子模块固定私有仓库提交，不公开源码，也不改变源码授权。

## 首次配置

在 Settings → Secrets and variables → Actions 添加下列 Repository secrets（也支持放在 `Build` Environment secrets）：

| Secret | 内容 |
| --- | --- |
| `IITCMAPKIT_READ_TOKEN` | Resource owner 选 `IITCforApple`，授权访问 `iitc_mapkit` 的 fine-grained PAT，Contents: read；若组织要求审批，需先取得批准 |
| `ARTIFACT_PASSWORD` | 仅用于加密诊断日志的独立长密码 |
| `MACOS_CERTIFICATE_P12_BASE64` | 包含私钥的 Developer ID Application `.p12` 文件的单行 Base64 |
| `MACOS_CERTIFICATE_PASSWORD` | 上述 `.p12` 的导出密码 |
| `NOTARY_APPLE_ID` | Apple Developer 账号的 Apple ID |
| `NOTARY_APP_PASSWORD` | 上述账号的 App 专用密码 |
| `SIGNING_IDENTITY` | 完整证书名称，如 `Developer ID Application: Your Name (TEAMID)` |
| `SIGNING_TEAM_ID` | 对应 Developer Team ID |

后六项可使用 InblessBuild 相同的配置值；签名 identity/team 支持 **Secrets 或 Variables**（Secrets 优先）。GitHub 已保存的 Secrets 无法读回，需要重新从原始凭据填入。不要将凭据提交到 Git 或贴到 Issue。

配置完成后，Actions → Private source build → Run workflow。推送 main 也自动触发。首次未配置 Secrets 时会明确失败，不上传安装包或明文日志。

## 构建和交付

使用 GitHub `xcode-27` Apple Silicon runner（目前为 preview），遵循源码要求的 macOS 27 SDK，并安装 Metal Toolchain。构建 macOS 应用及 Safari 扩展，验证签名和搬移后的资源加载，提交 Apple 公证、装订并验证 App 票据，再创建 ZIP 和 DMG。DMG 也签名、公证、装订并验证。Gatekeeper 检查失败即拒绝收集安装包。

每次成功构建上传五个独立 Actions artifacts，均保留 7 天：

- `IITCMapKit-macos-arm64-logs-encrypted`：仅包含 AES-256、加密文件名的 `IITCMapKit-macos-arm64-logs.7z`。解密后只有 `logs/`（包括源码提交记录），不包含 `packages/`。用 7-Zip 和 `ARTIFACT_PASSWORD` 解密。
- `IITC-MapKit-<version>-macOS-arm64.zip`：不加密的应用 ZIP。
- `IITC-MapKit-<version>-macOS-arm64.zip.sha256`：不加密的 ZIP 校验和。
- `IITC-MapKit-<version>-macOS-arm64.dmg`：不加密的 DMG。
- `IITC-MapKit-<version>-macOS-arm64.dmg.sha256`：不加密的 DMG 校验和。

四个公开产物各只上传对应文件，不上传整个输出目录。只有构建、签名、公证及验证全部成功后才上传安装包和校验和；失败时仅尝试上传加密日志。安装包可公开下载，无需密码；日志内容继续保密。

私有构建日志不打印到公开 Actions 页面；源码仓库地址、固定提交、构建阶段和工具安装信息仍可见。不配置 PR 触发、不缓存私有源码和编译产物、仅推送版本 tag 时自动发布 Release。签名私钥和公证凭据在临时 keychain 中使用并清理。仅使用 GitHub 托管 runner。

iOS 构建和 TestFlight 不在此流程中；Apple 公证针对 macOS 分发。本仓库完成配置不等于公证验收：需要首次 Actions 实际完成且产物通过检查。

## 更新固定源码

完整的版本交付必须遵守 [AGENTS.md](AGENTS.md)：先完成私有源码仓库的验证、安装、版本提交以及 `main` 和版本 tag 推送，再把本仓库 `iitc_mapkit` 子模块固定到源码远端 `main` 的同一提交。提交并推送本仓库 `main`，最后在本仓库创建相同的 `vMAJOR.MINOR.PATCH` tag 并推送 tags。核对远端 gitlink、tag 与源码 `VERSION`，确认 tag 发布流程已触发；仅推送源码仓库 tag 不算完成交付。

```sh
git submodule sync -- iitc_mapkit
git submodule update --init
git -C iitc_mapkit fetch origin
git -C iitc_mapkit checkout <reviewed-commit>
git add iitc_mapkit
git commit -m 'build: 更新 IITCMapKit 源码版本'
git push
```

## Tag 自动发布 Release

在 **IITCMapKitBuild** 仓库推送 `vMAJOR.MINOR.PATCH`（例如 `v1.3.0`）会自动构建并发布对应 GitHub Release。tag 必须与固定源码的 `VERSION` 完全一致；不匹配则失败。源码仓库中的 tag 不会触发此入口。main 推送、手动运行仍只上传 Actions artifacts，不发布 Release。

```sh
# 确保 main 已包含所需源码 gitlink；版本号以该源码 VERSION 为准。
git tag v1.3.0
git push origin v1.3.0
```

`Build` 环境须允许 `main` 分支和 `v*` 标签。PR 触发仍未启用。构建任务保持只读 token；独立发布任务仅在 tag push 且整个构建任务成功时运行，使用 GitHub 自动提供的 token，无需新增 Secret。

发布任务只下载四个公开文件，再验证文件集合与 SHA-256，创建草稿、上传并下载核对后才公开 Release。加密日志不会进入 Release。失败留下的草稿可通过重新运行恢复；已公开的 Release 不会被自动覆盖，重复发布会明确失败。

## 参考

- [Apple 公证流程](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
- [GitHub runner 标签与工具链](https://github.com/actions/runner-images)

The source `Scripts/package-mac-dmg.command` owns the IITC MapKit link-themed
installer layout. This workflow uses it after app notarization, then signs,
notarizes and staples the DMG as before. Display branding does not change the
private source URL, bundle identifiers or signing/notarization boundaries.
